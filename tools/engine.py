"""Tax engine for count.co.nz programmatic pages.

Single source of truth: the 2026-27 constants are parsed at import time from
the inline <script> in index.html (the calculator itself), so the generated
pages can never drift from what the calculator computes. Future tax years can
be added to TAX_YEARS as literal dicts alongside the parsed current year.

The arithmetic mirrors calcPAYE()/calculate() in index.html; tools/test_engine.py
executes that actual JavaScript via macOS jsc and asserts parity.
"""

import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = REPO_ROOT / "index.html"


def _parse_constants_from_index():
    """Extract BRACKETS, ACC/KiwiSaver/student-loan constants from index.html."""
    src = INDEX_HTML.read_text(encoding="utf-8")

    m = re.search(r"const BRACKETS = \[(.*?)\];", src, re.S)
    if not m:
        raise RuntimeError("Could not find BRACKETS in index.html")
    brackets = []
    for limit, rate in re.findall(
        r"\{\s*limit:\s*([\d.]+|Infinity),\s*rate:\s*([\d.]+)\s*\}", m.group(1)
    ):
        brackets.append(
            (float("inf") if limit == "Infinity" else float(limit), float(rate))
        )
    if len(brackets) != 5:
        raise RuntimeError("Expected 5 PAYE brackets in index.html, got %d" % len(brackets))

    def scalar(name):
        sm = re.search(r"const %s\s*=\s*([\d.]+);" % name, src)
        if not sm:
            raise RuntimeError("Could not find const %s in index.html" % name)
        return float(sm.group(1))

    return {
        "brackets": brackets,           # [(upper_limit, rate), ...] cumulative
        "acc_rate": scalar("ACC_RATE"),
        "acc_cap": scalar("ACC_CAP"),
        "sl_threshold": scalar("SL_THRESH"),
        "sl_rate": scalar("SL_RATE"),
        "min_wage": scalar("MIN_WAGE"),
        "kiwisaver_rates": [3.5, 4, 6, 8, 10],  # employee rates offered by the calculator
        "kiwisaver_default": 3.5,
        "hours_per_week": 40,
        "weeks_per_year": 52,
    }


TAX_YEARS = {
    "2026-27": _parse_constants_from_index(),
    # "2027-28": { ... add literal config here when rates are announced ... },
}

CURRENT_YEAR = "2026-27"


class Engine:
    def __init__(self, year=CURRENT_YEAR):
        self.year = year
        self.c = TAX_YEARS[year]

    # ── Core maths (mirrors calculate() in index.html) ──────────────────────

    def paye(self, annual):
        tax, prev = 0.0, 0.0
        for limit, rate in self.c["brackets"]:
            if annual <= prev:
                break
            tax += (min(annual, limit) - prev) * rate
            prev = limit
        return tax

    def paye_slices(self, annual):
        """Per-bracket breakdown: [(lo, hi, rate, taxed_amount, tax), ...]."""
        slices, prev = [], 0.0
        for limit, rate in self.c["brackets"]:
            if annual <= prev:
                break
            taxed = min(annual, limit) - prev
            slices.append((prev, limit, rate, taxed, taxed * rate))
            prev = limit
        return slices

    def marginal_rate(self, annual):
        for limit, rate in self.c["brackets"]:
            if annual <= limit:
                return rate
        return self.c["brackets"][-1][1]

    def next_bracket(self, annual):
        """(next_limit, next_rate) or None if in the top bracket."""
        for i, (limit, rate) in enumerate(self.c["brackets"]):
            if annual <= limit:
                if limit == float("inf"):
                    return None
                return limit, self.c["brackets"][i + 1][1]
        return None

    def acc(self, annual):
        return min(annual, self.c["acc_cap"]) * self.c["acc_rate"]

    def kiwisaver(self, annual, rate_pct=None):
        if rate_pct is None:
            rate_pct = self.c["kiwisaver_default"]
        return annual * rate_pct / 100.0

    def student_loan(self, annual):
        t = self.c["sl_threshold"]
        return (annual - t) * self.c["sl_rate"] if annual > t else 0.0

    def breakdown(self, annual, kiwisaver_pct=None, with_student_loan=False):
        """Full result dict for a gross annual income (must be > 0)."""
        paye = self.paye(annual)
        acc = self.acc(annual)
        ks = self.kiwisaver(annual, kiwisaver_pct) if kiwisaver_pct else 0.0
        sl = self.student_loan(annual) if with_student_loan else 0.0
        net = annual - paye - acc - ks - sl
        return {
            "annual": annual, "paye": paye, "acc": acc, "ks": ks, "sl": sl,
            "net": net,
            "effective": (paye + acc) / annual,   # matches metaEffective on the site
            "marginal": self.marginal_rate(annual),
        }

    def hourly_to_annual(self, rate):
        return rate * self.c["hours_per_week"] * self.c["weeks_per_year"]

    @property
    def hours_per_year(self):
        return self.c["hours_per_week"] * self.c["weeks_per_year"]


# ── Formatting (matches index.html's nf/fm/fp via Intl en-NZ) ────────────────
# JS Intl.NumberFormat rounds half-away-from-zero on the number's shortest
# decimal representation; Decimal(repr(x)) + ROUND_HALF_UP reproduces that,
# whereas Python's format() would use banker's rounding.

def _round_js(x, dp):
    q = Decimal(1).scaleb(-dp)
    return Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP)


def nf(x, dp=2):
    return "{:,}".format(_round_js(x, dp)) if dp == 0 else "{:,.{dp}f}".format(_round_js(x, dp), dp=dp)


def fm(x, dp=2):
    """Money, e.g. $39,717.00 — same as fm() on the site."""
    return "$" + nf(x, dp)


def fp(x, dp=1):
    """Percentage from a fraction, e.g. 0.175 -> 17.5% — same as fp() on the site."""
    return nf(x * 100, dp) + "%"


def fm0(x):
    """Whole-dollar money for prose/titles, e.g. $39,717."""
    return "$" + nf(x, 0)


if __name__ == "__main__":
    print(json.dumps(
        {k: (v if not isinstance(v, list) or not isinstance(v[0], tuple)
             else [[l if l != float("inf") else "Infinity", r] for l, r in v])
         for k, v in TAX_YEARS[CURRENT_YEAR].items()},
        indent=2,
    ))

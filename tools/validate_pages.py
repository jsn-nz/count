"""Validate generated pages against the engine.

Run:  python3 tools/validate_pages.py [seed]

Picks 5 random generated pages (mix of salary + hourly), recomputes every key
figure with tools/engine.py, and asserts the exact formatted figure appears in
the page HTML. Also checks canonical URL, title, robots, and that all JSON-LD
blocks parse. Exits non-zero on any mismatch.
"""

import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import Engine, REPO_ROOT, fm, fp, fm0  # noqa: E402
from generate import SALARIES, HOURLIES, SITE  # noqa: E402

seed = int(sys.argv[1]) if len(sys.argv) > 1 else random.randrange(10**6)
rng = random.Random(seed)
print("Validating with seed %d" % seed)

e = Engine()
picks = ([("salary", a) for a in rng.sample(SALARIES, 3)]
         + [("hourly", r) for r in rng.sample(HOURLIES, 2)])

failures = 0


def expect(page, html, label, needle):
    global failures
    if needle not in html:
        failures += 1
        print("  FAIL %s: %s not found (%r)" % (page, label, needle))


for kind, n in picks:
    path = REPO_ROOT / kind / str(n) / "index.html"
    page = "/%s/%d/" % (kind, n)
    html = path.read_text(encoding="utf-8")
    annual = n if kind == "salary" else e.hourly_to_annual(n)
    a = e.breakdown(annual)                     # PAYE + ACC only
    b = e.breakdown(annual, kiwisaver_pct=3.5)  # calculator default
    sl = e.breakdown(annual, kiwisaver_pct=3.5, with_student_loan=True)

    # Headline answers, both variants, all periods
    for r, tag in [(a, "no-KS"), (b, "KS3.5")]:
        for label, v in [("year", r["net"]), ("month", r["net"] / 12),
                         ("fortnight", r["net"] / 26), ("week", r["net"] / 52),
                         ("hourly", r["net"] / e.hours_per_year)]:
            expect(page, html, "%s net/%s" % (tag, label), fm(v))

    # Deduction table
    expect(page, html, "gross", fm(annual))
    for lo, hi, rate, taxed, tax in e.paye_slices(annual):
        expect(page, html, "PAYE slice @ %s" % fp(rate), fm(tax))
    expect(page, html, "total PAYE", fm(b["paye"]))
    expect(page, html, "ACC", fm(b["acc"]))
    expect(page, html, "KiwiSaver 3.5%", fm(b["ks"]))

    # Rates
    expect(page, html, "effective rate", fp(a["effective"]))
    expect(page, html, "marginal rate", fp(a["marginal"]))

    # KiwiSaver scenarios + student loan row
    for r_pct in [4, 6, 8, 10]:
        expect(page, html, "KS %d%% net" % r_pct,
               fm(e.breakdown(annual, kiwisaver_pct=r_pct)["net"]))
    expect(page, html, "M SL net", fm(sl["net"]))
    expect(page, html, "M SL weekly", fm(sl["net"] / 52))

    # Head / SEO
    expect(page, html, "canonical",
           '<link rel="canonical" href="%s%s">' % (SITE, page))
    expect(page, html, "robots", '<meta name="robots" content="index, follow">')
    m = re.search(r"<title>(.*?)</title>", html)
    if not m or len(m.group(1)) > 60:
        failures += 1
        print("  FAIL %s: title missing or >60 chars: %r" % (page, m and m.group(1)))
    if fm(b["net"]) not in re.search(r'<meta name="description" content="([^"]*)"', html).group(1):
        failures += 1
        print("  FAIL %s: meta description lacks computed take-home" % page)

    # JSON-LD parses and includes FAQPage + BreadcrumbList
    lds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    types = set()
    for block in lds:
        try:
            types.add(json.loads(block)["@type"])
        except Exception as ex:
            failures += 1
            print("  FAIL %s: bad JSON-LD: %s" % (page, ex))
    if not {"FAQPage", "BreadcrumbList"} <= types:
        failures += 1
        print("  FAIL %s: missing JSON-LD types, got %s" % (page, types))

    print("  OK %s (gross %s, take-home %s)" % (page, fm0(annual), fm(b["net"])))

if failures:
    print("\n%d validation failure(s)" % failures)
    sys.exit(1)
print("\nAll 5 pages match the engine.")

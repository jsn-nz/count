"""Golden + parity tests for tools/engine.py.

Run:  python3 tools/test_engine.py

Three layers:
  1. Golden tests — figures observed on the live count.co.nz calculator
     (tax code M, 3.5% KiwiSaver, no student loan).
  2. Boundary/edge tests — bracket edges, ACC cap, student-loan threshold,
     zero/negative/absurd inputs.
  3. JS parity — extracts the real calculator JavaScript from index.html,
     executes it with macOS JavaScriptCore (jsc), and asserts the Python
     engine matches it to the cent across a sweep of incomes.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import Engine, INDEX_HTML, fm, TAX_YEARS, CURRENT_YEAR  # noqa: E402

JSC = "/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc"

PASS = FAIL = 0


def check(label, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print("  FAIL %s %s" % (label, detail))


def approx(a, b, tol=0.005):
    return abs(a - b) <= tol


e = Engine()

# ── 1. Golden tests (from the live site; take-home rounded to the dollar) ────
print("Golden tests")
for gross, golden_net, golden_wk in [
    (50000, 39717, 764),
    (70000, 53105, 1021),
    (100000, 71873, None),
    (150000, 102748, None),
]:
    r = e.breakdown(gross, kiwisaver_pct=3.5)
    check("net(%d)" % gross, approx(r["net"], golden_net, tol=0.5),
          "engine=%.2f golden=%d" % (r["net"], golden_net))
    if golden_wk is not None:
        check("weekly(%d)" % gross, approx(r["net"] / 52, golden_wk, tol=0.5),
              "engine=%.2f golden=%d" % (r["net"] / 52, golden_wk))

check("PAYE-only(60000)", e.paye(60000) == 10220.50,
      "engine=%r expected=10220.50" % e.paye(60000))

# ── 2. Boundaries & edges ────────────────────────────────────────────────────
print("Boundary tests")
c = TAX_YEARS[CURRENT_YEAR]

# Exact PAYE at each bracket's upper edge, built from first principles
edge_expect = {}
tax = prev = 0.0
for limit, rate in c["brackets"]:
    if limit == float("inf"):
        break
    tax += (limit - prev) * rate
    edge_expect[limit] = tax
    prev = limit

for limit, expected in edge_expect.items():
    check("paye(%d)" % limit, approx(e.paye(limit), expected),
          "engine=%.4f expected=%.4f" % (e.paye(limit), expected))
    # $1 over the edge adds exactly the next bracket's marginal rate
    over = e.paye(limit + 1) - e.paye(limit)
    nxt = e.marginal_rate(limit + 1)
    check("paye(%d+1) marginal" % limit, approx(over, nxt),
          "delta=%.4f expected=%.4f" % (over, nxt))

# ACC cap: levy is flat above $156,641
cap = c["acc_cap"]
check("acc at cap", approx(e.acc(cap), cap * c["acc_rate"]))
check("acc above cap", e.acc(cap + 50000) == e.acc(cap),
      "%.2f vs %.2f" % (e.acc(cap + 50000), e.acc(cap)))
check("acc below cap", approx(e.acc(cap - 1), (cap - 1) * c["acc_rate"]))

# Student loan threshold: nothing at/below $24,128, 12c per $ above
t = c["sl_threshold"]
check("sl at threshold", e.student_loan(t) == 0.0)
check("sl below threshold", e.student_loan(t - 1) == 0.0)
check("sl $1000 over", approx(e.student_loan(t + 1000), 120.0))

# Zero / negative / absurd — engine must not blow up or go weird
check("paye(0)", e.paye(0) == 0.0)
check("acc(0)", e.acc(0) == 0.0)
check("paye(-5000)", e.paye(-5000) == 0.0, "got %r" % e.paye(-5000))
big = e.breakdown(10_000_000, kiwisaver_pct=3.5)
check("absurd income sane", 0 < big["net"] < big["annual"])
check("absurd marginal", big["marginal"] == 0.39)

# ── 3. Parity with the real calculator JS via jsc ────────────────────────────
print("JS parity (jsc)")
src = INDEX_HTML.read_text(encoding="utf-8")
m = re.search(r"(// ── Tax constants.*?)// ── Chart instance", src, re.S)
if not m:
    print("  FAIL could not extract calculator JS from index.html")
    FAIL += 1
else:
    sweep = [1, 100, 15600, 15601, 24128, 24129, 40000, 50000, 53500, 53501,
             60000, 70000, 78100, 78101, 100000, 123456.78, 150000, 156640,
             156641, 156642, 180000, 180001, 250000, 999999]
    js = m.group(1) + """
var out = [];
for (var i of %s) {
  state.income = i; state.period = "year";
  state.kiwisaver = true; state.kiwisaverRate = 3.5; state.studentLoan = false;
  var a = calculate();
  state.kiwisaver = false; state.studentLoan = true;
  var b = calculate();
  out.push([i, a.paye, a.acc, a.ks, a.net, b.sl, b.net, fm(a.net), fp((a.paye+a.acc)/a.annual)]);
}
print(JSON.stringify(out));
""" % json.dumps(sweep)
    res = subprocess.run([JSC, "-e", js], capture_output=True, text=True)
    if res.returncode != 0:
        print("  FAIL jsc error: %s" % (res.stderr or res.stdout))
        FAIL += 1
    else:
        for (i, paye, acc, ks, net, sl, net_sl, fmt_net, fmt_eff) in json.loads(res.stdout):
            ra = e.breakdown(i, kiwisaver_pct=3.5)
            rb = e.breakdown(i, kiwisaver_pct=None, with_student_loan=True)
            for label, js_v, py_v in [
                ("paye", paye, ra["paye"]), ("acc", acc, ra["acc"]),
                ("ks", ks, ra["ks"]), ("net", net, ra["net"]),
                ("sl", sl, rb["sl"]), ("net+sl", net_sl, rb["net"]),
            ]:
                check("%s(%s)" % (label, i), approx(js_v, py_v, tol=1e-6),
                      "js=%r py=%r" % (js_v, py_v))
            check("fm(%s)" % i, fm(ra["net"]) == fmt_net,
                  "js=%r py=%r" % (fmt_net, fm(ra["net"])))

print("\n%d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)

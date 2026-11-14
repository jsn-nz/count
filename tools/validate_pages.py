"""Validate generated pages.

Run:  python3 tools/validate_pages.py [seed]

1. Figures: picks random salary, hourly and pay-period pages, recomputes every
   key figure with tools/engine.py, and asserts the exact formatted figure
   appears in the page HTML.
2. Every page in the sitemap: canonical matches its path, title <= 60 chars,
   analytics + share image present, JSON-LD parses and contains no HTML
   entities or tags, and every internal link points at a file that exists.
Exits non-zero on any failure.
"""

import html as _html
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import Engine, REPO_ROOT, fm, fp, fm0  # noqa: E402
from generate import SALARIES, HOURLIES, PERIODS, SITE, GA_ID  # noqa: E402

seed = int(sys.argv[1]) if len(sys.argv) > 1 else random.randrange(10**6)
rng = random.Random(seed)
print("Validating with seed %d" % seed)

e = Engine()
picks = ([("salary", a) for a in rng.sample(SALARIES, 3)]
         + [("hourly", r) for r in rng.sample(HOURLIES, 2)]
         + [(k, rng.choice(PERIODS[k]["amounts"])) for k in PERIODS])

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
    per = PERIODS[kind]["n"] if kind in PERIODS else None
    annual = n if kind == "salary" else e.hourly_to_annual(n) if kind == "hourly" else n * per
    a = e.breakdown(annual)                     # PAYE + ACC only
    b = e.breakdown(annual, kiwisaver_pct=3.5)  # calculator default
    sl = e.breakdown(annual, kiwisaver_pct=3.5, with_student_loan=True)

    # Headline answers, both variants, all periods
    for r, tag in [(a, "no-KS"), (b, "KS3.5")]:
        for label, v in [("year", r["net"]), ("month", r["net"] / 12),
                         ("fortnight", r["net"] / 26), ("week", r["net"] / 52)]:
            expect(page, html, "%s net/%s" % (tag, label), fm(v))
        if not per:
            expect(page, html, "%s net/hourly" % tag, fm(r["net"] / e.hours_per_year))

    # Deduction table
    expect(page, html, "gross", fm(annual))
    if per:   # period pages show per-period and per-year columns
        for label, v in [("PAYE", b["paye"]), ("ACC", b["acc"]), ("KiwiSaver", b["ks"]), ("net", b["net"])]:
            expect(page, html, "%s per period" % label, fm(v / per))
    else:
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

    if fm(b["net"] / (per or 1)) not in re.search(r'<meta name="description" content="([^"]*)"', html).group(1):
        failures += 1
        print("  FAIL %s: meta description lacks computed take-home" % page)

    print("  OK %s (gross %s, take-home %s)" % (page, fm0(annual), fm(b["net"])))

# ── Site-wide checks on every sitemap URL ────────────────────────────────────
locs = re.findall(r"<loc>%s(/[^<]*)</loc>" % re.escape(SITE), (REPO_ROOT / "sitemap.xml").read_text())
checked = 0
for loc in locs:
    f = REPO_ROOT / loc.strip("/") / "index.html"
    if not f.exists():
        failures += 1
        print("  FAIL %s: in sitemap but no file" % loc)
        continue
    html = f.read_text(encoding="utf-8")
    checked += 1
    if loc == "/":
        need = [("canonical", '<link rel="canonical" href="%s/">' % SITE), ("analytics", GA_ID),
                ("og:image", "/images/og.png")]
    else:
        need = [("canonical", '<link rel="canonical" href="%s%s">' % (SITE, loc)),
                ("robots", '<meta name="robots" content="index, follow">'),
                ("analytics", GA_ID), ("og:image", "/images/og.png"),
                ("twitter card", "summary_large_image")]
    for label, needle in need:
        expect(loc, html, label, needle)
    m = re.search(r"<title>(.*?)</title>", html)
    if not m or (loc != "/" and len(_html.unescape(m.group(1))) > 60):
        failures += 1
        print("  FAIL %s: title missing or >60 chars: %r" % (loc, m and m.group(1)))
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            json.loads(block)
        except Exception as ex:
            failures += 1
            print("  FAIL %s: bad JSON-LD: %s" % (loc, ex))
        if loc != "/" and (re.search(r"&[a-z]+;|&#\d+;", block) or "<" in block):
            failures += 1
            print("  FAIL %s: HTML entity or tag inside JSON-LD" % loc)
    if loc != "/" and '"FAQPage"' not in html and loc.count("/") > 2:
        failures += 1
        print("  FAIL %s: no FAQPage JSON-LD" % loc)
    for href in set(re.findall(r'href="(/[^"#?]*)', html)):
        target = REPO_ROOT / href.strip("/")
        if not (target.is_file() or (target / "index.html").is_file()):
            failures += 1
            print("  FAIL %s: broken internal link %s" % (loc, href))
print("Checked %d sitemap pages (head tags, JSON-LD, internal links)." % checked)

if failures:
    print("\n%d validation failure(s)" % failures)
    sys.exit(1)
print("\nAll checks passed.")

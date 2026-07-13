"""Static page generator for count.co.nz programmatic salary/hourly pages.

Run:  python3 tools/generate.py

Emits:
  /salary/<amount>/index.html   121 pages ($40k-$150k by $1k, $160k-$250k by $10k)
  /hourly/<rate>/index.html      52 pages ($23-$70 by $1, plus 75/80/90/100)
  /salary/index.html, /hourly/index.html   hub pages
  /sitemap.xml                   regenerated with all URLs

All figures come from tools/engine.py, whose constants are parsed from the
calculator in index.html — see tools/test_engine.py for the parity proof.
Zero client-side JS on these pages except the same 2-line theme bootstrap the
homepage uses (reads the shared localStorage key so the theme matches on
click-through).
"""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import (  # noqa: E402
    Engine, TAX_YEARS, CURRENT_YEAR, REPO_ROOT, fm, fp, fm0, nf,
)

SITE = "https://count.co.nz"
YEAR = "2026–27"  # 2026–27 (en dash)
TODAY = date.today().isoformat()

e = Engine()
C = TAX_YEARS[CURRENT_YEAR]
HPY = e.hours_per_year  # 2080

SALARIES = list(range(40_000, 150_001, 1_000)) + list(range(160_000, 250_001, 10_000))
HOURLIES = list(range(23, 71)) + [75, 80, 90, 100]

PERCENTILES_FILE = REPO_ROOT / "data" / "income-percentiles.json"


def pick(variants, seed, salt):
    """Deterministic phrasing variant so no two pages read identically."""
    return variants[(int(seed) + salt) % len(variants)]


# ── Shared shell ─────────────────────────────────────────────────────────────

CSS = """
:root{--bg:#F4F4F4;--surface:#FFFFFF;--card:#ECECEC;--border:#DEDEDE;--accent:#2C5C3C;
--accent-mid:#245030;--accent-light:#E6F0EA;--accent-dim:#5A8C6A;--text:#111;--dim:#333;
--muted:#777;--ring:rgba(44,92,60,.12)}
[data-theme="dark"]{--bg:#111;--surface:#1A1A1A;--card:#222;--border:#303030;--accent:#4E8C62;
--accent-mid:#3D7250;--accent-light:#1A261D;--accent-dim:#4E8C62;--text:#F0F0F0;--dim:#C4C4C4;
--muted:#808080;--ring:rgba(78,140,98,.2)}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);background-image:radial-gradient(900px 480px at 50% -120px,var(--accent-light) 0%,transparent 70%);
background-repeat:no-repeat;color:var(--text);font-family:'Inter',system-ui,-apple-system,sans-serif;
font-size:15px;line-height:1.6;min-height:100vh}
main{max-width:760px;margin:0 auto;padding:1.5rem 1.25rem 3rem}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.crumbs{font-size:.8rem;color:var(--muted);margin-bottom:1.5rem}
.crumbs a{color:var(--muted)}.crumbs a:first-child{font-weight:800;color:var(--accent)}
h1{font-size:1.7rem;font-weight:800;letter-spacing:-.02em;line-height:1.25;margin-bottom:.35rem}
.sub{color:var(--muted);margin-bottom:1.5rem}
h2{font-size:1.05rem;font-weight:700;margin:2.2rem 0 .8rem}
.answer{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin:1.5rem 0}
.answer-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1.1rem 1.2rem}
.answer-card.primary{border-color:var(--accent);box-shadow:0 0 0 3px var(--ring)}
.answer-label{font-size:.7rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--accent-dim);margin-bottom:.6rem}
.answer-big{font-size:1.55rem;font-weight:800;color:var(--accent);font-variant-numeric:tabular-nums;line-height:1.1}
.answer-big span{font-size:.8rem;font-weight:600;color:var(--muted)}
.answer-rows{margin-top:.7rem;font-size:.85rem;color:var(--dim)}
.answer-rows div{display:flex;justify-content:space-between;padding:.15rem 0;font-variant-numeric:tabular-nums}
.answer-rows span:first-child{color:var(--muted)}
table{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--border);
border-radius:12px;overflow:hidden;font-size:.88rem;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:.55rem .9rem;border-bottom:1px solid var(--border)}
th{font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);background:var(--card)}
td:last-child,th:last-child,td.num,th.num{text-align:right}
tr:last-child td{border-bottom:none}
tr.total td{font-weight:700}
tr.takehome td{color:var(--accent);font-weight:800;background:var(--accent-light)}
.callout{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--accent);
border-radius:10px;padding:.9rem 1.1rem;margin:1rem 0;font-size:.9rem;color:var(--dim)}
.rates{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0}
.rate-chip{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:.7rem 1rem;flex:1;min-width:140px}
.rate-chip b{display:block;font-size:1.2rem;color:var(--accent);font-variant-numeric:tabular-nums}
.rate-chip span{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;font-weight:600}
.cta{display:inline-block;background:linear-gradient(135deg,var(--accent) 0%,var(--accent-mid) 100%);
color:#fff;font-weight:700;padding:.7rem 1.4rem;border-radius:10px;margin:.5rem 0}
.cta:hover{text-decoration:none;filter:brightness(1.08)}
.faq{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:.2rem 1.2rem;margin:1rem 0}
.faq details{border-bottom:1px solid var(--border);padding:.7rem 0}
.faq details:last-child{border-bottom:none}
.faq summary{font-weight:600;cursor:pointer;font-size:.92rem}
.faq p{font-size:.88rem;color:var(--dim);margin-top:.5rem}
.linkgrid{display:flex;flex-wrap:wrap;gap:.5rem;margin:1rem 0}
.linkgrid a{background:var(--surface);border:1px solid var(--border);border-radius:999px;
padding:.35rem .9rem;font-size:.85rem;font-weight:600;color:var(--dim)}
.linkgrid a:hover{border-color:var(--accent);color:var(--accent);text-decoration:none}
.fine{font-size:.78rem;color:var(--muted);margin-top:2rem}
.hub-band{margin-bottom:2rem}
.hub-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:.5rem}
.hub-grid a{background:var(--surface);border:1px solid var(--border);border-radius:10px;
padding:.5rem .85rem;font-size:.85rem;display:flex;justify-content:space-between;color:var(--dim);font-variant-numeric:tabular-nums}
.hub-grid a b{color:var(--text)}.hub-grid a span{color:var(--accent);font-weight:600}
.hub-grid a:hover{border-color:var(--accent);text-decoration:none}
footer{border-top:1px solid var(--border);margin-top:3rem;padding-top:1.2rem;display:flex;
justify-content:space-between;flex-wrap:wrap;gap:.8rem;font-size:.8rem;color:var(--muted)}
footer .brand{font-weight:800;color:var(--accent)}
footer nav{display:flex;gap:1rem;flex-wrap:wrap}
@media(max-width:600px){.answer{grid-template-columns:1fr}h1{font-size:1.4rem}}
""".strip()

# Same theme bootstrap the homepage runs (shared localStorage key), so the
# theme matches on click-through. No other JS on these pages.
THEME_JS = ('<script>document.documentElement.setAttribute("data-theme",'
            'localStorage.getItem("theme-alt")==="light"?"light":"dark");</script>')

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">')


def shell(*, title, description, canonical, crumbs, jsonld, body):
    crumb_html = " &rsaquo; ".join(
        '<a href="%s">%s</a>' % (href, label) if href else "<span>%s</span>" % label
        for label, href in crumbs
    )
    ld = "\n".join('<script type="application/ld+json">%s</script>'
                   % json.dumps(b, ensure_ascii=False) for b in jsonld)
    return """<!DOCTYPE html>
<html lang="en-NZ" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{theme_js}
<title>{title}</title>
<meta name="description" content="{description}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<link rel="icon" href="/images/favicon.ico" sizes="any">
{fonts}
{ld}
<style>
{css}
</style>
</head>
<body>
<main>
<nav class="crumbs">{crumb_html}</nav>
{body}
<footer>
  <div><span class="brand">Count.</span> &copy; 2023&ndash;2026 Count.co.nz &middot; Free NZ PAYE &amp; salary calculator</div>
  <nav>
    <a href="/">Calculator</a>
    <a href="/salary/">Salary after tax</a>
    <a href="/hourly/">Hourly to salary</a>
  </nav>
</footer>
</main>
</body>
</html>
""".format(theme_js=THEME_JS, title=title, description=description,
           canonical=canonical, fonts=FONTS, ld=ld, css=CSS,
           crumb_html=crumb_html, body=body)


def breadcrumb_ld(items):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": SITE + path}
            for i, (name, path) in enumerate(items)
        ],
    }


def faq_ld(faqs):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faqs
        ],
    }


# ── Shared content blocks ────────────────────────────────────────────────────

def answer_block(annual):
    """Headline take-home, two clearly-labelled ways."""
    a = e.breakdown(annual)                      # PAYE + ACC only
    b = e.breakdown(annual, kiwisaver_pct=3.5)   # calculator default state
    def card(r, label, cls):
        return """<div class="answer-card {cls}">
  <div class="answer-label">{label}</div>
  <div class="answer-big">{yr} <span>/ year</span></div>
  <div class="answer-rows">
    <div><span>Monthly</span><span>{mo}</span></div>
    <div><span>Fortnightly</span><span>{fn}</span></div>
    <div><span>Weekly</span><span>{wk}</span></div>
    <div><span>Hourly (40 hrs/wk)</span><span>{hr}</span></div>
  </div>
</div>""".format(cls=cls, label=label, yr=fm(r["net"]), mo=fm(r["net"] / 12),
                 fn=fm(r["net"] / 26), wk=fm(r["net"] / 52), hr=fm(r["net"] / HPY))
    return '<div class="answer">%s\n%s</div>' % (
        card(b, "With 3.5% KiwiSaver (calculator default)", "primary"),
        card(a, "PAYE + ACC only (no KiwiSaver)", ""),
    )


def deduction_table(annual):
    b = e.breakdown(annual, kiwisaver_pct=3.5)
    rows = ['<tr><td>Gross income</td><td class="num">%s</td></tr>' % fm(annual)]
    for lo, hi, rate, taxed, tax in e.paye_slices(annual):
        band = ("PAYE on income over %s @ %s" % (fm0(lo), fp(rate)) if hi == float("inf")
                else "PAYE on %s &ndash; %s @ %s" % (fm0(lo if lo == 0 else lo + 1), fm0(hi), fp(rate)))
        rows.append('<tr><td>%s</td><td class="num">&minus;%s</td></tr>' % (band, fm(tax)))
    rows.append('<tr class="total"><td>Total PAYE</td><td class="num">&minus;%s</td></tr>' % fm(b["paye"]))
    acc_note = " (capped at %s)" % fm0(C["acc_cap"]) if annual > C["acc_cap"] else ""
    rows.append('<tr><td>ACC earners&rsquo; levy %s%s</td><td class="num">&minus;%s</td></tr>'
                % (fp(C["acc_rate"], 2), acc_note, fm(b["acc"])))
    rows.append('<tr><td>KiwiSaver (3.5%%)</td><td class="num">&minus;%s</td></tr>' % fm(b["ks"]))
    rows.append('<tr class="takehome"><td>Take-home pay</td><td class="num">%s</td></tr>' % fm(b["net"]))
    return ('<table><thead><tr><th>Deduction (per year)</th><th class="num">Amount</th></tr></thead>'
            "<tbody>%s</tbody></table>" % "".join(rows))


def rates_block(annual, seed):
    b = e.breakdown(annual)
    chips = """<div class="rates">
  <div class="rate-chip"><b>{eff}</b><span>Effective rate (PAYE + ACC)</span></div>
  <div class="rate-chip"><b>{marg}</b><span>Marginal rate</span></div>
  <div class="rate-chip"><b>{keep}</b><span>Kept of every gross $ (before KiwiSaver)</span></div>
</div>""".format(eff=fp(b["effective"]), marg=fp(b["marginal"]),
                 keep=fp(b["net"] / annual))
    nb = e.next_bracket(annual)
    if nb is None:
        callout = ("You&rsquo;re in the top tax bracket &mdash; every extra dollar you earn is "
                   "taxed at 39%% (plus the ACC levy below %s)." % fm0(C["acc_cap"]))
    elif nb[0] == annual:
        callout = ("You&rsquo;re exactly at the top of the %s bracket: your next dollar is taxed at "
                   "%s. Only income above %s is taxed at the higher rate &mdash; the rest is untouched."
                   % (fp(e.marginal_rate(annual)), fp(nb[1]), fm0(nb[0])))
    else:
        gap = nb[0] - annual
        callout = pick([
            "You&rsquo;re {gap} below the next tax bracket: income above {limit} is taxed at "
            "{rate}. Crossing it only affects the dollars above the line, not your whole salary.",
            "Earn another {gap} and you cross into the {rate} bracket, which starts at {limit} "
            "&mdash; but only the income above that threshold is taxed at the higher rate, "
            "so a pay rise is always worth taking.",
        ], seed, 3).format(gap=fm0(gap), limit=fm0(nb[0]), rate=fp(nb[1]))
    return chips + '\n<div class="callout">%s</div>' % callout


def kiwisaver_table(annual):
    rows = []
    for r in C["kiwisaver_rates"]:
        br = e.breakdown(annual, kiwisaver_pct=r)
        star = " (default)" if r == C["kiwisaver_default"] else ""
        rows.append('<tr><td>%s%% KiwiSaver%s</td><td class="num">%s</td>'
                    '<td class="num">%s</td><td class="num">%s</td></tr>'
                    % (nf(r, 1 if r % 1 else 0), star, fm(br["ks"]), fm(br["net"]), fm(br["net"] / 52)))
    sl = e.breakdown(annual, kiwisaver_pct=3.5, with_student_loan=True)
    rows.append('<tr><td>3.5%% KiwiSaver + student loan (tax code M&nbsp;SL)</td>'
                '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td></tr>'
                % (fm(sl["ks"] + sl["sl"]), fm(sl["net"]), fm(sl["net"] / 52)))
    return ('<table><thead><tr><th>Scenario</th><th class="num">Deducted / yr</th>'
            '<th class="num">Take-home / yr</th><th class="num">Take-home / wk</th></tr></thead>'
            "<tbody>%s</tbody></table>" % "".join(rows))


def percentile_block(annual):
    if not PERCENTILES_FILE.exists():
        return ""
    try:
        data = json.loads(PERCENTILES_FILE.read_text(encoding="utf-8"))
        pts = sorted((float(v), float(k)) for k, v in data["percentiles"].items())
    except Exception:
        return ""
    if not pts:
        return ""
    if annual <= pts[0][0]:
        pct = pts[0][1]
    elif annual >= pts[-1][0]:
        pct = pts[-1][1]
    else:
        pct = next(p1 + (p2 - p1) * (annual - v1) / (v2 - v1)
                   for (v1, p1), (v2, p2) in zip(pts, pts[1:])
                   if v1 <= annual <= v2)
    return ("<h2>How does it compare?</h2>\n<div class=\"callout\">A %s income is higher than "
            "roughly %d%% of individual incomes in New Zealand (%s, Stats NZ).</div>"
            % (fm0(annual), round(pct), data.get("source_year", "latest available")))


def faq_block(faqs):
    items = "".join("<details><summary>%s</summary><p>%s</p></details>" % (q, a)
                    for q, a in faqs)
    return '<div class="faq">%s</div>' % items


def links_block(pairs):
    return '<div class="linkgrid">%s</div>' % "".join(
        '<a href="%s">%s</a>' % (href, label) for label, href in pairs)


def cta(annual):
    return ('<p><a class="cta" href="/?i=%d">Open %s in the calculator &rarr;</a></p>'
            % (int(annual) if annual == int(annual) else annual, fm0(annual)))


def fine_print(extra=""):
    return ('<p class="fine">Figures use NZ %s PAYE rates: tax code M, ACC earners&rsquo; levy of %s '
            "(capped at %s), no independent earner tax credit. KiwiSaver figures are employee "
            "contributions only. Hourly conversions assume 40 hours/week, 52 weeks/year. %s"
            'Rates sourced from <a href="https://www.ird.govt.nz" rel="noopener">IRD</a>. '
            "This is general information, not financial advice.</p>"
            % (YEAR, fp(C["acc_rate"], 2), fm0(C["acc_cap"]), extra))


# ── FAQ generation (computed, condition-varied phrasing) ─────────────────────

def salary_faqs(annual, seed):
    a = e.breakdown(annual)
    b = e.breakdown(annual, kiwisaver_pct=3.5)
    g = fm0(annual)
    faqs = []

    q = pick(["How much tax do I pay on %s a year in NZ?" % g,
              "How much PAYE comes out of a %s salary in New Zealand?" % g,
              "What are the total deductions on %s in NZ?" % g], seed, 0)
    faqs.append((q, "For %s: PAYE income tax is %s and the ACC earners&rsquo; levy is %s &mdash; %s "
                 "in total, an effective rate of %s. Add 3.5%% KiwiSaver (%s) and total deductions "
                 "are %s a year." % (YEAR, fm(a["paye"]), fm(a["acc"]), fm(a["paye"] + a["acc"]),
                                     fp(a["effective"]), fm(b["ks"]), fm(annual - b["net"]))))

    if pick([0, 1], seed, 1):
        faqs.append(("What is %s a month after tax in NZ?" % g,
                     "%s a month with 3.5%% KiwiSaver, or %s with no KiwiSaver (PAYE and ACC only)."
                     % (fm(b["net"] / 12), fm(a["net"] / 12))))
    else:
        faqs.append(("What is %s a year per week after tax?" % g,
                     "%s a week with 3.5%% KiwiSaver, or %s a week with no KiwiSaver "
                     "(PAYE and ACC only)." % (fm(b["net"] / 52), fm(a["net"] / 52))))

    if annual > C["sl_threshold"]:
        sl = e.student_loan(annual)
        faqs.append((pick(["How much student loan do I repay on %s?" % g,
                           "What are student loan repayments on a %s salary?" % g], seed, 2),
                     "Repayments are 12% of income above the $" + nf(C["sl_threshold"], 0) +
                     " annual threshold: %s a year (%s a week), deducted through the M&nbsp;SL tax code."
                     % (fm(sl), fm(sl / 52))))

    if 24_000 <= annual <= 70_000:
        faqs.append(("Can I get the independent earner tax credit (IETC) on %s?" % g,
                     "Possibly &mdash; the IETC is worth up to $520 a year for people earning between "
                     "$24,000 and $70,000 who don&rsquo;t receive Working for Families, a main benefit "
                     "or NZ&nbsp;Super. The figures on this page (and the Count. calculator) exclude "
                     "the IETC, so treat it as a possible bonus on top."))
    elif annual > 180_000:
        faqs.append(("Why is my marginal rate 39%% on %s?" % g,
                     "Income above $180,000 falls in NZ&rsquo;s top tax bracket at 39%%. Only the %s "
                     "above the threshold is taxed at 39%% &mdash; the rest is taxed at the lower "
                     "bracket rates, which is why the effective rate is %s, not 39%%."
                     % (fm0(annual - 180_000), fp(a["effective"]))))
    elif annual > C["acc_cap"]:
        faqs.append(("Does the ACC levy apply to all of %s?" % g,
                     "No &mdash; the 1.75%% ACC earners&rsquo; levy only applies to the first %s of "
                     "income, so it&rsquo;s capped at %s a year regardless of how much more you earn."
                     % (fm0(C["acc_cap"]), fm(e.acc(annual)))))
    else:
        nb = e.next_bracket(annual)
        faqs.append(("Which tax bracket is %s in?" % g,
                     "The top slice of a %s salary is taxed at %s. NZ tax is progressive: each "
                     "bracket rate only applies to the income inside that bracket, so your overall "
                     "PAYE works out to %s of gross." % (g, fp(a["marginal"]), fp(a["paye"] / annual))
                     + ("" if nb is None or nb[0] == annual else
                        " The next bracket (%s) starts at %s." % (fp(nb[1]), fm0(nb[0])))))

    faqs.append((pick(["What hourly rate is %s a year?" % g,
                       "%s a year is how much an hour in NZ?" % g], seed, 4),
                 "At 40 hours a week, %s a year is %s an hour before tax. After PAYE and ACC "
                 "you keep about %s an hour (%s with 3.5%% KiwiSaver)."
                 % (g, fm(annual / HPY), fm(a["net"] / HPY), fm(b["net"] / HPY))))
    return faqs


def hourly_faqs(rate, seed):
    annual = e.hourly_to_annual(rate)
    a = e.breakdown(annual)
    b = e.breakdown(annual, kiwisaver_pct=3.5)
    r = "$" + nf(rate, 0)
    faqs = []

    faqs.append((pick(["%s an hour is how much a year in NZ?" % r,
                       "What salary is %s an hour in New Zealand?" % r], seed, 0),
                 "%s an hour is %s a year gross at 40 hours a week, 52 weeks a year. After PAYE "
                 "and ACC that&rsquo;s %s a year take-home, or %s with 3.5%% KiwiSaver."
                 % (r, fm0(annual), fm(a["net"]), fm(b["net"]))))

    faqs.append(("How much is %s an hour weekly after tax?" % r,
                 "A 40-hour week at %s grosses %s. Take-home is %s a week after PAYE and ACC, "
                 "or %s a week with 3.5%% KiwiSaver." % (r, fm(rate * 40), fm(a["net"] / 52), fm(b["net"] / 52))))

    mw = C["min_wage"]
    if rate < mw:
        faqs.append(("Is %s an hour legal in NZ?" % r,
                     "%s an hour is below the adult minimum wage of $%s (%s). Most employees aged 16+ "
                     "must be paid at least the adult minimum wage; starting-out and training minimum "
                     "wages ($%s) are lower but only apply in limited cases."
                     % (r, nf(mw), YEAR, nf(mw * 0.8))))
    else:
        faqs.append((pick(["Is %s an hour above minimum wage in NZ?" % r,
                           "How does %s an hour compare to the NZ minimum wage?" % r], seed, 2),
                     "Yes &mdash; the adult minimum wage is $%s an hour (%s), so %s is %s above it, "
                     "about %s more per 40-hour week before tax."
                     % (nf(mw), YEAR, r, fm(rate - mw), fm0((rate - mw) * 40))))

    if annual > C["sl_threshold"]:
        sl = e.student_loan(annual)
        faqs.append(("What about student loan repayments at %s an hour?" % r,
                     "Full-time at %s an hour you&rsquo;d earn %s a year, which is over the %s "
                     "repayment threshold. On tax code M&nbsp;SL you&rsquo;d repay 12%% of the excess: "
                     "%s a year (%s a week)." % (r, fm0(annual), fm0(C["sl_threshold"]), fm(sl), fm(sl / 52))))

    faqs.append(("What is %s an hour as a monthly salary?" % r,
                 "Gross %s a month. After tax: %s a month (PAYE + ACC only) or %s a month with "
                 "3.5%% KiwiSaver." % (fm(annual / 12), fm(a["net"] / 12), fm(b["net"] / 12))))
    return faqs


# ── Comparison links ─────────────────────────────────────────────────────────

def nearest(value, options):
    return min(options, key=lambda o: abs(o - value))


def salary_links(a):
    pairs = []
    for delta in (-10_000, -5_000, -1_000, 1_000, 5_000, 10_000):
        other = a + delta
        if other in SALARIES and other != a:
            label = "%s%s" % ("&minus;" if delta < 0 else "+", fm0(abs(delta)))
            pairs.append(("%s &middot; %s" % (label, fm0(other)), "/salary/%d/" % other))
    hr = nearest(a / HPY, HOURLIES)
    pairs.append(("&asymp; $%d/hour" % hr, "/hourly/%d/" % hr))
    # de-dup preserving order
    seen, out = set(), []
    for label, href in pairs:
        if href not in seen:
            seen.add(href)
            out.append((label, href))
    return out


def hourly_links(r):
    pairs = []
    for delta in (-5, -1, 1, 5):
        other = r + delta
        if other in HOURLIES and other != r:
            pairs.append(("%s$%d &middot; $%d/hr" % ("&minus;" if delta < 0 else "+", abs(delta), other),
                          "/hourly/%d/" % other))
    sal = nearest(e.hourly_to_annual(r), SALARIES)
    pairs.append(("&asymp; %s salary" % fm0(sal), "/salary/%d/" % sal))
    seen, out = set(), []
    for label, href in pairs:
        if href not in seen:
            seen.add(href)
            out.append((label, href))
    return out


# ── Pages ────────────────────────────────────────────────────────────────────

def salary_page(a):
    seed = a // 1000
    br = e.breakdown(a, kiwisaver_pct=3.5)
    path = "/salary/%d/" % a
    faqs = salary_faqs(a, seed)
    title = "%s After Tax NZ (%s) — Take-Home Pay" % (fm0(a), YEAR)
    desc = ("%s after tax in New Zealand (%s): %s a year take-home (%s/week) with 3.5%% KiwiSaver, "
            "after PAYE and ACC. Full breakdown, KiwiSaver and student loan scenarios."
            % (fm0(a), YEAR, fm(br["net"]), fm(br["net"] / 52)))
    intro = pick([
        "Here&rsquo;s exactly where a %s salary goes in the %s tax year &mdash; every figure below "
        "matches the Count. PAYE calculator (tax code M).",
        "A full %s take-home breakdown for a %s salary in New Zealand, using the same engine as "
        "the Count. PAYE calculator (tax code M).",
    ], seed, 5)
    intro = intro % ((fm0(a), YEAR) if pick([0, 1], seed, 5) == 0 else (YEAR, fm0(a)))

    body = """<h1>{g} After Tax in New Zealand ({yr})</h1>
<p class="sub">{intro}</p>
{answer}
{cta}
<h2>Where the money goes</h2>
{table}
<h2>Effective vs marginal rate</h2>
{rates}
<h2>KiwiSaver &amp; student loan scenarios</h2>
{ks}
<h2>Hourly equivalent</h2>
<div class="callout">{g} a year is <b>{grosshr}</b> an hour before tax at 40 hours/week
(52 weeks). After PAYE and ACC you keep about <b>{nethr}</b> an hour.</div>
{pct}
<h2>FAQs</h2>
{faq}
<h2>Compare nearby incomes</h2>
{links}
{fine}""".format(
        g=fm0(a), yr=YEAR, intro=intro, answer=answer_block(a), cta=cta(a),
        table=deduction_table(a), rates=rates_block(a, seed), ks=kiwisaver_table(a),
        grosshr=fm(a / HPY), nethr=fm(e.breakdown(a)["net"] / HPY),
        pct=percentile_block(a), faq=faq_block(faqs), links=links_block(salary_links(a)),
        fine=fine_print())

    crumbs = [("Count.", "/"), ("Salary after tax", "/salary/"), (fm0(a), None)]
    ld_crumbs = [("Home", "/"), ("Salary after tax", "/salary/"), (fm0(a) + " after tax", path)]
    return shell(title=title, description=desc, canonical=SITE + path,
                 crumbs=crumbs, jsonld=[faq_ld(faqs), breadcrumb_ld(ld_crumbs)], body=body)


def hourly_page(r):
    annual = e.hourly_to_annual(r)
    br = e.breakdown(annual, kiwisaver_pct=3.5)
    a_only = e.breakdown(annual)
    path = "/hourly/%d/" % r
    faqs = hourly_faqs(r, r)
    rl = "$" + nf(r, 0)
    title = "%s an Hour is How Much a Year in NZ? (%s)" % (rl, YEAR)
    desc = ("%s an hour in New Zealand is %s a year gross (40 hrs/week). Take-home for %s: %s "
            "a year with 3.5%% KiwiSaver after PAYE and ACC. Full breakdown inside."
            % (rl, fm0(annual), YEAR, fm(br["net"])))
    mw_note = ""
    if r < C["min_wage"]:
        mw_note = ('<div class="callout"><b>Note:</b> %s an hour is below the %s adult minimum wage '
                   "of $%s an hour.</div>" % (rl, YEAR, nf(C["min_wage"])))

    body = """<h1>{rl} an Hour is How Much a Year in NZ?</h1>
<p class="sub">{rl}/hour at 40 hours a week, 52 weeks a year is <b>{gross}</b> before tax.
Here&rsquo;s what you actually take home in {yr} (tax code M) &mdash; same engine as the
Count. PAYE calculator.</p>
{mw}
{answer}
{cta}
<h2>Where the money goes (on {gross}/year)</h2>
{table}
<h2>Effective vs marginal rate</h2>
{rates}
<h2>KiwiSaver &amp; student loan scenarios</h2>
{ks}
<h2>Quick conversions</h2>
<div class="callout">{rl}/hour &rarr; <b>{d}</b> a day (8 hrs) &middot; <b>{w}</b> a week &middot;
<b>{f}</b> a fortnight &middot; <b>{m}</b> a month &middot; <b>{gross}</b> a year &mdash; all before tax.</div>
{pct}
<h2>FAQs</h2>
{faq}
<h2>Compare nearby rates</h2>
{links}
{fine}""".format(
        rl=rl, gross=fm0(annual), yr=YEAR, mw=mw_note, answer=answer_block(annual),
        cta='<p><a class="cta" href="/?i=%d">Open %s/hr in the calculator &rarr;</a></p>' % (r, rl),
        table=deduction_table(annual), rates=rates_block(annual, r), ks=kiwisaver_table(annual),
        d=fm(r * 8), w=fm(r * 40), f=fm(r * 80), m=fm(annual / 12),
        pct=percentile_block(annual), faq=faq_block(faqs), links=links_block(hourly_links(r)),
        fine=fine_print())

    crumbs = [("Count.", "/"), ("Hourly to salary", "/hourly/"), (rl + "/hr", None)]
    ld_crumbs = [("Home", "/"), ("Hourly to salary", "/hourly/"), (rl + " an hour", path)]
    return shell(title=title, description=desc, canonical=SITE + path,
                 crumbs=crumbs, jsonld=[faq_ld(faqs), breadcrumb_ld(ld_crumbs)], body=body)


# ── Hub pages ────────────────────────────────────────────────────────────────

def hub_grid(items):
    return '<div class="hub-grid">%s</div>' % "".join(
        '<a href="%s"><b>%s</b><span>%s/yr</span></a>' % (href, label, net)
        for label, net, href in items)


def salary_hub():
    bands = [("$40,000 – $60,000", range(40_000, 60_001, 1_000)),
             ("$61,000 – $80,000", range(61_000, 80_001, 1_000)),
             ("$81,000 – $100,000", range(81_000, 100_001, 1_000)),
             ("$101,000 – $125,000", range(101_000, 125_001, 1_000)),
             ("$126,000 – $150,000", range(126_000, 150_001, 1_000)),
             ("$160,000 – $250,000", range(160_000, 250_001, 10_000))]
    sections = []
    for label, rng in bands:
        items = [(fm0(a), fm0(e.breakdown(a, kiwisaver_pct=3.5)["net"]), "/salary/%d/" % a)
                 for a in rng if a in SALARIES]
        sections.append('<div class="hub-band"><h2>%s</h2>%s</div>' % (label, hub_grid(items)))
    title = "Salary After Tax NZ — Take-Home Pay Tables (%s)" % YEAR
    desc = ("Take-home pay for every salary from $40,000 to $250,000 in New Zealand, %s tax year. "
            "PAYE, ACC, KiwiSaver and student loan included — pick your salary for the full breakdown." % YEAR)
    body = """<h1>Salary After Tax in New Zealand ({yr})</h1>
<p class="sub">Pick a salary to see its full take-home breakdown &mdash; PAYE by bracket, ACC,
KiwiSaver scenarios and student loan repayments. Take-home shown with 3.5% KiwiSaver
(the calculator default). Paid by the hour? See <a href="/hourly/">hourly rates</a>,
or use the <a href="/">calculator</a> for any amount.</p>
{sections}
{fine}""".format(yr=YEAR, sections="".join(sections), fine=fine_print())
    crumbs = [("Count.", "/"), ("Salary after tax", None)]
    return shell(title=title, description=desc, canonical=SITE + "/salary/",
                 crumbs=crumbs, jsonld=[breadcrumb_ld([("Home", "/"), ("Salary after tax", "/salary/")])],
                 body=body)


def hourly_hub():
    bands = [("$23 – $30 an hour", range(23, 31)),
             ("$31 – $40 an hour", range(31, 41)),
             ("$41 – $50 an hour", range(41, 51)),
             ("$51 – $70 an hour", range(51, 71)),
             ("$75+ an hour", [75, 80, 90, 100])]
    sections = []
    for label, rng in bands:
        items = [("$%d/hr &rarr; %s" % (r, fm0(e.hourly_to_annual(r))),
                  fm0(e.breakdown(e.hourly_to_annual(r), kiwisaver_pct=3.5)["net"]),
                  "/hourly/%d/" % r)
                 for r in rng if r in HOURLIES]
        sections.append('<div class="hub-band"><h2>%s</h2>%s</div>' % (label, hub_grid(items)))
    title = "Hourly Rate to Salary NZ — After-Tax Tables (%s)" % YEAR
    desc = ("What $23–$100 an hour is as a yearly salary in New Zealand, and the take-home pay "
            "after PAYE, ACC and KiwiSaver for the %s tax year." % YEAR)
    body = """<h1>Hourly Rate to Yearly Salary in NZ ({yr})</h1>
<p class="sub">Each rate assumes 40 hours/week, 52 weeks/year. The gross annual salary is shown on
the link; the green figure is yearly take-home with 3.5% KiwiSaver (the calculator default).
On a salary instead? See <a href="/salary/">salary after tax</a>, or use the
<a href="/">calculator</a> for your exact hours.</p>
{sections}
{fine}""".format(yr=YEAR, sections="".join(sections), fine=fine_print())
    crumbs = [("Count.", "/"), ("Hourly to salary", None)]
    return shell(title=title, description=desc, canonical=SITE + "/hourly/",
                 crumbs=crumbs, jsonld=[breadcrumb_ld([("Home", "/"), ("Hourly to salary", "/hourly/")])],
                 body=body)


# ── Sitemap ──────────────────────────────────────────────────────────────────

def sitemap(urls):
    entries = ["""  <url>
    <loc>https://count.co.nz/</loc>
    <lastmod>2026-06-13</lastmod>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
  </url>"""]
    for path, priority in urls:
        entries.append("""  <url>
    <loc>%s%s</loc>
    <lastmod>%s</lastmod>
    <changefreq>monthly</changefreq>
    <priority>%s</priority>
  </url>""" % (SITE, path, TODAY, priority))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(entries) + "\n</urlset>\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    urls = [("/salary/", "0.8"), ("/hourly/", "0.8")]

    for a in SALARIES:
        out = REPO_ROOT / "salary" / str(a) / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(salary_page(a), encoding="utf-8")
        urls.append(("/salary/%d/" % a, "0.6"))

    for r in HOURLIES:
        out = REPO_ROOT / "hourly" / str(r) / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(hourly_page(r), encoding="utf-8")
        urls.append(("/hourly/%d/" % r, "0.6"))

    (REPO_ROOT / "salary" / "index.html").write_text(salary_hub(), encoding="utf-8")
    (REPO_ROOT / "hourly" / "index.html").write_text(hourly_hub(), encoding="utf-8")
    (REPO_ROOT / "sitemap.xml").write_text(sitemap(urls), encoding="utf-8")

    print("Generated %d salary + %d hourly pages, 2 hubs, sitemap with %d URLs."
          % (len(SALARIES), len(HOURLIES), len(urls) + 1))
    if not PERCENTILES_FILE.exists():
        print("(Percentile block skipped: %s not present.)" % PERCENTILES_FILE.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()

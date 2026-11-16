"""Static page generator for count.co.nz.

Run:  python3 tools/generate.py

Emits (all figures from tools/engine.py, whose constants are parsed from the
calculator in index.html; see tools/test_engine.py for the parity proof):
  /salary/<amount>/       annual salaries
  /hourly/<rate>/         hourly rates
  /weekly/<amount>/, /fortnightly/<amount>/, /monthly/<amount>/   pay-period amounts
  hub pages for each of the above
  topic pages + /tax-rates/ archive (see tools/topics.py)
  /sitemap.xml            lastmod only moves when a page's content changes
                          (hashes kept in tools/lastmod.json)

Salary/hourly/period pages carry no JS beyond the theme bootstrap and the
analytics tag; topic pages add a small inline calculator.
"""

import hashlib
import html as _html
import json
import re
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

SALARIES = (list(range(20_000, 150_001, 1_000)) + list(range(155_000, 250_001, 5_000))
            + [275_000, 300_000])
HOURLIES = list(range(23, 71)) + [75, 80, 90, 100]

# Pay-period pages: gross amount per period -> annualised with the multiplier.
PERIODS = {
    "weekly":      {"n": 52, "noun": "week", "adj": "Weekly", "a": "a week",
                    "amounts": list(range(500, 2_501, 50)) + list(range(2_600, 4_001, 100))},
    "fortnightly": {"n": 26, "noun": "fortnight", "adj": "Fortnightly", "a": "a fortnight",
                    "amounts": list(range(1_000, 5_001, 100)) + list(range(5_200, 8_001, 200))},
    "monthly":     {"n": 12, "noun": "month", "adj": "Monthly", "a": "a month",
                    "amounts": list(range(2_000, 10_001, 250)) + list(range(10_500, 20_001, 500))},
}

GA_ID = "G-077CHWJ9XD"   # same property as index.html
# 1200x630, built from tools/og.html. Bump v when the image changes so link previews refresh.
OG_IMAGE = SITE + "/images/og.png?v=2"
LASTMOD_FILE = REPO_ROOT / "tools" / "lastmod.json"

PERCENTILES_FILE = REPO_ROOT / "data" / "income-percentiles.json"   # built from IRD band counts


def pick(variants, seed, salt):
    """Deterministic phrasing variant so no two pages read identically."""
    return variants[(int(seed) + salt) % len(variants)]


# ── Shared shell ─────────────────────────────────────────────────────────────

CSS = """
:root{--bg:#F3F4F5;--surface:#FFFFFF;--card:#E9ECEE;--border:#D6DADD;--accent:#2F6B53;
--accent-mid:#2E5E4A;--accent-light:#E6EFEA;--accent-dim:#5C8A75;--text:#14181A;--dim:#333A3D;
--muted:#6C7478;--ring:rgba(47,107,83,.14)}
[data-theme="dark"]{--bg:#1B1E21;--surface:#24282C;--card:#2D3237;--border:#3B4148;--accent:#6BA88A;
--accent-mid:#2E5E4A;--accent-light:#22332B;--accent-dim:#6BA88A;--text:#F2F3F4;--dim:#CDD1D5;
--muted:#949BA3;--ring:rgba(107,168,138,.22)}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,-apple-system,sans-serif;
font-size:15px;line-height:1.6;min-height:100vh}
main{max-width:760px;margin:0 auto;padding:1.5rem 1.25rem 3rem}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.crumbs{font-size:.8rem;color:var(--muted);margin-bottom:1.5rem}
.crumbs a{color:var(--muted)}.crumbs a:first-child{font-weight:800;color:var(--accent)}
h1{font-size:1.7rem;font-weight:800;letter-spacing:-.02em;line-height:1.25;margin-bottom:.35rem}
.sub{color:var(--muted);margin-bottom:1.5rem}
h2{font-size:1.05rem;font-weight:700;margin:2.2rem 0 .8rem}
.answer{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin:1.5rem 0}
.answer-card{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:1.1rem 1.2rem}
.answer-card.primary{border-color:var(--accent);box-shadow:0 0 0 3px var(--ring)}
.answer-label{font-size:.7rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--accent-dim);margin-bottom:.6rem}
.answer-big{font-size:1.55rem;font-weight:800;color:var(--accent);font-variant-numeric:tabular-nums;line-height:1.1}
.answer-big span{font-size:.8rem;font-weight:600;color:var(--muted)}
.answer-rows{margin-top:.7rem;font-size:.85rem;color:var(--dim)}
.answer-rows div{display:flex;justify-content:space-between;padding:.15rem 0;font-variant-numeric:tabular-nums}
.answer-rows span:first-child{color:var(--muted)}
table{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--border);
border-radius:6px;overflow:hidden;font-size:.88rem;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:.55rem .9rem;border-bottom:1px solid var(--border)}
th{font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);background:var(--card)}
td:last-child,th:last-child,td.num,th.num{text-align:right}
tr:last-child td{border-bottom:none}
tr.total td{font-weight:700}
tr.takehome td{color:var(--accent);font-weight:800;background:var(--accent-light)}
.callout{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--accent);
border-radius:6px;padding:.9rem 1.1rem;margin:1rem 0;font-size:.9rem;color:var(--dim)}
.rates{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0}
.rate-chip{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:.7rem 1rem;flex:1;min-width:140px}
.rate-chip b{display:block;font-size:1.2rem;color:var(--accent);font-variant-numeric:tabular-nums}
.rate-chip span{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;font-weight:600}
.cta{display:inline-block;background:var(--accent-mid);
color:#fff;font-weight:700;padding:.7rem 1.4rem;border-radius:6px;margin:.5rem 0}
.cta:hover{text-decoration:none;filter:brightness(1.08)}
.faq{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:.2rem 1.2rem;margin:1rem 0}
.faq details{border-bottom:1px solid var(--border);padding:.7rem 0}
.faq details:last-child{border-bottom:none}
.faq summary{font-weight:600;cursor:pointer;font-size:.92rem}
.faq p{font-size:.88rem;color:var(--dim);margin-top:.5rem}
.linkgrid{display:flex;flex-wrap:wrap;gap:.5rem;margin:1rem 0}
.linkgrid a{background:var(--surface);border:1px solid var(--border);border-radius:6px;
padding:.35rem .9rem;font-size:.85rem;font-weight:600;color:var(--dim)}
.linkgrid a:hover{border-color:var(--accent);color:var(--accent);text-decoration:none}
.fine{font-size:.78rem;color:var(--muted);margin-top:2rem}
.hub-band{margin-bottom:2rem}
.hub-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:.5rem}
.hub-grid a{background:var(--surface);border:1px solid var(--border);border-radius:6px;
padding:.5rem .85rem;font-size:.85rem;display:flex;justify-content:space-between;color:var(--dim);font-variant-numeric:tabular-nums}
.hub-grid a b{color:var(--text)}.hub-grid a span{color:var(--accent);font-weight:600}
.hub-grid a:hover{border-color:var(--accent);text-decoration:none}
footer{border-top:1px solid var(--border);margin-top:3rem;padding-top:1.2rem;display:flex;
justify-content:space-between;flex-wrap:wrap;gap:.8rem;font-size:.8rem;color:var(--muted)}
footer .brand{font-weight:800;color:var(--accent)}
footer nav{display:flex;gap:1rem;flex-wrap:wrap}
main p{margin:.7rem 0}main ul.plain{margin:.7rem 0 .7rem 1.2rem;color:var(--dim);font-size:.92rem}
main ul.plain li{margin:.3rem 0}
.tablewrap{overflow-x:auto}
.calc{background:var(--surface);border:1px solid var(--accent);box-shadow:0 0 0 3px var(--ring);
border-radius:6px;padding:1.1rem 1.2rem;margin:1.5rem 0}
.calc-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:.9rem}
.calc label{display:block;font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:.3rem}
.calc input[type=number],.calc select{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--border);
border-radius:4px;padding:.55rem .7rem;font:inherit;font-variant-numeric:tabular-nums}
.calc input:focus,.calc select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--ring)}
.calc .check{display:flex;align-items:center;gap:.45rem;font-size:.88rem;color:var(--dim);text-transform:none;letter-spacing:0;font-weight:500;margin-top:1.45rem}
.calc-out{margin-top:1rem;border-top:1px solid var(--border);padding-top:.8rem;font-size:.92rem}
.calc-out div{display:flex;justify-content:space-between;gap:1rem;padding:.25rem 0;font-variant-numeric:tabular-nums}
.calc-out div span:first-child{color:var(--muted)}
.calc-out div.big{font-size:1.15rem;font-weight:800;color:var(--accent)}
.calc-out div.big span:first-child{color:var(--accent)}
.calc-note{font-size:.8rem;color:var(--muted);margin-top:.6rem}
footer{flex-direction:column}
@media(max-width:600px){.answer{grid-template-columns:1fr}h1{font-size:1.4rem}}
""".strip()

# Same theme bootstrap the homepage runs (shared localStorage key), so the
# theme matches on click-through. No other JS on these pages.
THEME_JS = ('<script>document.documentElement.setAttribute("data-theme",'
            'localStorage.getItem("theme-alt")==="light"?"light":"dark");</script>')

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">')


GA = ('<script async src="https://www.googletagmanager.com/gtag/js?id=%s"></script>\n'
      "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
      "gtag('js',new Date());gtag('config','%s');</script>" % (GA_ID, GA_ID))

# Analytics events shared by every generated page (same names as index.html):
#   open_calculator  click on the green "Open ... in the calculator" button
#   related_click    click on any internal link; to_type is the section it leads to
# page_type is the first path segment (salary, hourly, weekly, pay-rise, ...).
EVENTS_JS = ("<script>(function(){var t=location.pathname.split('/')[1]||'home';"
             "window.cEv=function(n,p){p=p||{};p.page_type=t;if(window.gtag)gtag('event',n,p)};"
             "document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a[href]');"
             "if(!a)return;var h=a.getAttribute('href');"
             "if(a.classList.contains('cta'))cEv('open_calculator');"
             "else if(h.charAt(0)==='/')cEv('related_click',{to_type:h.split('/')[1]||'home'})})})();</script>")

FOOTER_LINKS = [
    ("Calculator", "/"), ("Salary after tax", "/salary/"), ("Hourly to salary", "/hourly/"),
    ("Weekly pay", "/weekly/"), ("Fortnightly pay", "/fortnightly/"), ("Monthly pay", "/monthly/"),
    ("Tax rates", "/tax-rates/"), ("Secondary tax", "/secondary-tax/"),
    ("Student loan", "/student-loan/"), ("KiwiSaver", "/kiwisaver/"),
    ("Minimum wage", "/minimum-wage/"), ("Pay rise", "/pay-rise/"),
    ("Bonus &amp; redundancy tax", "/bonus-tax/"), ("Contractor tax", "/contractor-tax/"),
    ("ACC levy", "/acc-levy/"), ("NZ vs Australia", "/nz-vs-australia/"),
]


def plain(text):
    """HTML fragment -> plain text for JSON-LD (search engines don't decode entities there)."""
    text = _html.unescape(re.sub(r"<[^>]+>", "", text))
    return text.replace("\u00a0", " ")


def shell(*, title, description, canonical, crumbs, jsonld, body, script=""):
    crumb_html = " &rsaquo; ".join(
        '<a href="%s">%s</a>' % (href, label) if href else "<span>%s</span>" % label
        for label, href in crumbs
    )
    ld = "\n".join('<script type="application/ld+json">%s</script>'
                   % json.dumps(b, ensure_ascii=False) for b in jsonld)
    footer = "\n".join('    <a href="%s">%s</a>' % (href, label) for label, href in FOOTER_LINKS)
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
<meta property="og:site_name" content="Count.">
<meta property="og:locale" content="en_NZ">
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{og}">
<link rel="icon" href="/images/favicon.ico" sizes="any">
{ga}
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
{footer}
  </nav>
</footer>
</main>
{events}
{script}
</body>
</html>
""".format(theme_js=THEME_JS, title=title, description=description,
           canonical=canonical, fonts=FONTS, ld=ld, css=CSS, ga=GA, og=OG_IMAGE,
           crumb_html=crumb_html, body=body, footer=footer, script=script, events=EVENTS_JS)


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
            {"@type": "Question", "name": plain(q),
             "acceptedAnswer": {"@type": "Answer", "text": plain(a)}}
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
        callout = ("You&rsquo;re in the top tax bracket, so every extra dollar you earn is "
                   "taxed at 39%% (plus the ACC levy below %s)." % fm0(C["acc_cap"]))
    elif nb[0] == annual:
        callout = ("You&rsquo;re exactly at the top of the %s bracket: your next dollar is taxed at "
                   "%s. Only income above %s is taxed at the higher rate; the rest is untouched."
                   % (fp(e.marginal_rate(annual)), fp(nb[1]), fm0(nb[0])))
    else:
        gap = nb[0] - annual
        callout = pick([
            "You&rsquo;re {gap} below the next tax bracket: income above {limit} is taxed at "
            "{rate}. Crossing it only affects the dollars above the line, not your whole salary.",
            "Earn another {gap} and you cross into the {rate} bracket, which starts at {limit}, "
            "but only the income above that threshold is taxed at the higher rate, "
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


def _load_percentiles():
    if not PERCENTILES_FILE.exists():
        return None
    data = json.loads(PERCENTILES_FILE.read_text(encoding="utf-8"))
    data["cumulative"] = [(float(v), float(p)) for v, p in data["cumulative"]]
    return data


PCT = _load_percentiles()


def percentile_of(annual):
    """% of wage and salary earners at or below this income, or None if out of range."""
    if not PCT:
        return None
    pts = PCT["cumulative"]
    if annual < pts[0][0] or annual > pts[-1][0]:
        return None
    prev_v, prev_p = 0.0, 0.0
    for v, p in pts:
        if annual <= v:
            return prev_p + (p - prev_p) * (annual - prev_v) / (v - prev_v)
        prev_v, prev_p = v, p
    return None


def percentile_block(annual):
    pct = percentile_of(annual)
    if pct is None:
        return ""
    below = int(pct)            # floor: never overstate
    if below >= 99:
        line = "more than 99% of"
    else:
        line = "about %d%% of" % below
    top = 100 - below
    return ("<h2>How does it compare?</h2>\n<div class=\"callout\">Wage or salary income of %s a year is "
            "higher than %s New Zealand wage and salary earners, roughly the top %d%%. "
            "The median earner received about %s.</div>\n<p class=\"fine\" style=\"margin-top:.4rem\">"
            "Source: <a href=\"%s\" rel=\"noopener\">Inland Revenue wage and salary distributions</a>, "
            "%s (%s people). That count includes part-time and part-year workers, so full-time "
            "salaries rank lower against full-time workers alone.</p>"
            % (fm0(annual), line, max(top, 1), fm0(PCT_MEDIAN), PCT["source_url"],
               PCT["source_year"], nf(PCT["population"], 0)))


def _median():
    if not PCT:
        return 0
    prev_v, prev_p = 0.0, 0.0
    for v, p in PCT["cumulative"]:
        if p >= 50:
            return round((prev_v + (v - prev_v) * (50 - prev_p) / (p - prev_p)) / 100) * 100
        prev_v, prev_p = v, p
    return 0


PCT_MEDIAN = _median()


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
    faqs.append((q, "For %s: PAYE income tax is %s and the ACC earners&rsquo; levy is %s, %s "
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
                     "Possibly. The IETC is worth up to $520 a year for people earning between "
                     "$24,000 and $70,000 who don&rsquo;t receive Working for Families, a main benefit "
                     "or NZ&nbsp;Super. The figures on this page (and the Count. calculator) exclude "
                     "the IETC, so treat it as a possible bonus on top."))
    elif annual > 180_000:
        faqs.append(("Why is my marginal rate 39%% on %s?" % g,
                     "Income above $180,000 falls in NZ&rsquo;s top tax bracket at 39%%. Only the %s "
                     "above the threshold is taxed at 39%%; the rest is taxed at the lower "
                     "bracket rates, which is why the effective rate is %s, not 39%%."
                     % (fm0(annual - 180_000), fp(a["effective"]))))
    elif annual > C["acc_cap"]:
        faqs.append(("Does the ACC levy apply to all of %s?" % g,
                     "No. The 1.75%% ACC earners&rsquo; levy only applies to the first %s of "
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
                     "Yes. The adult minimum wage is $%s an hour (%s), so %s is %s above it, "
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


def _dedup(pairs):
    seen, out = set(), []
    for label, href in pairs:
        if href not in seen:
            seen.add(href)
            out.append((label, href))
    return out


def salary_links(a):
    pairs = []
    for delta in (-10_000, -5_000, -1_000, 1_000, 5_000, 10_000):
        other = a + delta
        if other in SALARIES and other != a:
            label = "%s%s" % ("&minus;" if delta < 0 else "+", fm0(abs(delta)))
            pairs.append(("%s &middot; %s" % (label, fm0(other)), "/salary/%d/" % other))
    i = SALARIES.index(a)
    for j in (i - 1, i + 1):          # sparse ranges: always link the list neighbours
        if 0 <= j < len(SALARIES):
            pairs.append((fm0(SALARIES[j]), "/salary/%d/" % SALARIES[j]))
    hr = nearest(a / HPY, HOURLIES)
    pairs.append(("&asymp; $%d/hour" % hr, "/hourly/%d/" % hr))
    wk = nearest(a / 52, PERIODS["weekly"]["amounts"])
    pairs.append(("&asymp; %s/week" % fm0(wk), "/weekly/%d/" % wk))
    mo = nearest(a / 12, PERIODS["monthly"]["amounts"])
    pairs.append(("&asymp; %s/month" % fm0(mo), "/monthly/%d/" % mo))
    pairs.append(("Pay rise calculator", "/pay-rise/"))
    return _dedup(pairs)


def hourly_links(r):
    pairs = []
    for delta in (-5, -1, 1, 5):
        other = r + delta
        if other in HOURLIES and other != r:
            pairs.append(("%s$%d &middot; $%d/hr" % ("&minus;" if delta < 0 else "+", abs(delta), other),
                          "/hourly/%d/" % other))
    sal = nearest(e.hourly_to_annual(r), SALARIES)
    pairs.append(("&asymp; %s salary" % fm0(sal), "/salary/%d/" % sal))
    wk = nearest(r * 40, PERIODS["weekly"]["amounts"])
    pairs.append(("&asymp; %s/week" % fm0(wk), "/weekly/%d/" % wk))
    pairs.append(("Minimum wage after tax", "/minimum-wage/"))
    return _dedup(pairs)


# ── Pages ────────────────────────────────────────────────────────────────────

def salary_page(a):
    seed = a // 1000
    br = e.breakdown(a, kiwisaver_pct=3.5)
    path = "/salary/%d/" % a
    faqs = salary_faqs(a, seed)
    title = "%s After Tax NZ (%s): %s/wk | Count." % (fm0(a), YEAR, fm0(br["net"] / 52))
    desc = ("%s after tax in New Zealand (%s): %s a year take-home (%s/week) with 3.5%% KiwiSaver, "
            "after PAYE and ACC. Full breakdown, KiwiSaver and student loan scenarios."
            % (fm0(a), YEAR, fm(br["net"]), fm(br["net"] / 52)))
    intro = pick([
        "Here&rsquo;s exactly where a %s salary goes in the %s tax year. Every figure below "
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
<div class="tablewrap">{ks}</div>
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
    title = "%s an Hour = %s a Year NZ: %s/wk After Tax" % (rl, fm0(annual), fm0(br["net"] / 52))
    desc = ("%s an hour in New Zealand is %s a year gross (40 hrs/week). Take-home for %s: %s "
            "a year with 3.5%% KiwiSaver after PAYE and ACC. Full breakdown inside."
            % (rl, fm0(annual), YEAR, fm(br["net"])))
    mw_note = ""
    if r < C["min_wage"]:
        mw_note = ('<div class="callout"><b>Note:</b> %s an hour is below the %s adult minimum wage '
                   "of $%s an hour.</div>" % (rl, YEAR, nf(C["min_wage"])))

    body = """<h1>{rl} an Hour is How Much a Year in NZ?</h1>
<p class="sub">{rl}/hour at 40 hours a week, 52 weeks a year is <b>{gross}</b> before tax.
Here&rsquo;s what you actually take home in {yr} (tax code M), using the same engine as the
Count. PAYE calculator.</p>
{mw}
{answer}
{cta}
<h2>Where the money goes (on {gross}/year)</h2>
{table}
<h2>Effective vs marginal rate</h2>
{rates}
<h2>KiwiSaver &amp; student loan scenarios</h2>
<div class="tablewrap">{ks}</div>
<h2>Quick conversions</h2>
<div class="callout">{rl}/hour &rarr; <b>{d}</b> a day (8 hrs) &middot; <b>{w}</b> a week &middot;
<b>{f}</b> a fortnight &middot; <b>{m}</b> a month &middot; <b>{gross}</b> a year, all before tax.</div>
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
    bands = [("$20,000 – $39,000", range(20_000, 40_000, 1_000)),
             ("$40,000 – $60,000", range(40_000, 60_001, 1_000)),
             ("$61,000 – $80,000", range(61_000, 80_001, 1_000)),
             ("$81,000 – $100,000", range(81_000, 100_001, 1_000)),
             ("$101,000 – $125,000", range(101_000, 125_001, 1_000)),
             ("$126,000 – $150,000", range(126_000, 150_001, 1_000)),
             ("$155,000 – $300,000", [a for a in SALARIES if a > 150_000])]
    sections = []
    for label, rng in bands:
        items = [(fm0(a), fm0(e.breakdown(a, kiwisaver_pct=3.5)["net"]), "/salary/%d/" % a)
                 for a in rng if a in SALARIES]
        sections.append('<div class="hub-band"><h2>%s</h2>%s</div>' % (label, hub_grid(items)))
    title = "Salary After Tax NZ (%s): Take-Home Tables | Count." % YEAR
    desc = ("Take-home pay for every salary from $20,000 to $300,000 in New Zealand, %s tax year. "
            "PAYE, ACC, KiwiSaver and student loan included. Pick your salary for the full breakdown." % YEAR)
    body = """<h1>Salary After Tax in New Zealand ({yr})</h1>
<p class="sub">Pick a salary to see its full take-home breakdown: PAYE by bracket, ACC,
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
    title = "Hourly Rate to Salary NZ (%s), After Tax | Count." % YEAR
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


# ── Pay-period pages (/weekly/, /fortnightly/, /monthly/) ───────────────────

def period_page(kind, amt):
    P = PERIODS[kind]
    n, noun, per = P["n"], P["noun"], P["a"]
    per_t = "a " + noun.title()          # "a Week" for titles/headings
    annual = amt * n
    a = e.breakdown(annual)
    b = e.breakdown(annual, kiwisaver_pct=3.5)
    g = fm0(amt)
    path = "/%s/%d/" % (kind, amt)
    seed = amt // (50 if kind == "weekly" else 100 if kind == "fortnightly" else 250)

    def card(r, label, cls):
        others = [("Weekly", 52), ("Fortnightly", 26), ("Monthly", 12)]
        rows = "".join("<div><span>%s</span><span>%s</span></div>" % (lab, fm(r["net"] / k))
                       for lab, k in others if k != n)
        return ('<div class="answer-card %s"><div class="answer-label">%s</div>'
                '<div class="answer-big">%s <span>/ %s</span></div><div class="answer-rows">%s'
                "<div><span>Yearly</span><span>%s</span></div></div></div>"
                % (cls, label, fm(r["net"] / n), noun, rows, fm(r["net"])))
    answer = '<div class="answer">%s\n%s</div>' % (
        card(b, "With 3.5% KiwiSaver (calculator default)", "primary"),
        card(a, "PAYE + ACC only (no KiwiSaver)", ""))

    def row(label, v, cls="", neg=True):
        sign = "&minus;" if neg else ""
        return ('<tr%s><td>%s</td><td class="num">%s%s</td><td class="num">%s%s</td></tr>'
                % (' class="%s"' % cls if cls else "", label, sign, fm(v / n), sign, fm(v)))
    table = ('<table><thead><tr><th>Deduction</th><th class="num">Per %s</th><th class="num">Per year</th>'
             "</tr></thead><tbody>%s</tbody></table>" % (noun, "".join([
                 row("Gross pay", annual, neg=False),
                 row("PAYE income tax", b["paye"]),
                 row("ACC earners&rsquo; levy %s" % fp(C["acc_rate"], 2), b["acc"]),
                 row("KiwiSaver (3.5%)", b["ks"]),
                 row("Take-home pay", b["net"], "takehome", neg=False)])))

    faqs = []
    faqs.append((pick(["How much tax do I pay on %s %s in NZ?" % (g, per),
                       "How much PAYE is deducted from %s %s?" % (g, per)], seed, 0),
                 "On %s %s (%s a year) in %s, PAYE is %s and the ACC earners&rsquo; levy is %s per %s "
                 "(%s in total), an effective rate of %s. With 3.5%% KiwiSaver (%s) you take home %s %s."
                 % (g, per, fm0(annual), YEAR, fm(a["paye"] / n), fm(a["acc"] / n), noun,
                    fm((a["paye"] + a["acc"]) / n), fp(a["effective"]), fm(b["ks"] / n), fm(b["net"] / n), per)))
    faqs.append(("What is %s %s as a yearly salary?" % (g, per),
                 "%s %s is %s a year before tax (%d pay periods). After PAYE and ACC that is %s a year, "
                 "or %s with 3.5%% KiwiSaver." % (g, per, fm0(annual), n, fm(a["net"]), fm(b["net"]))))
    if annual > C["sl_threshold"]:
        sl = e.student_loan(annual)
        faqs.append(("How much student loan comes out of %s %s?" % (g, per),
                     "Repayments are 12%% of everything above %s %s (the %s yearly threshold): "
                     "%s per %s, deducted on tax code M&nbsp;SL."
                     % (fm(C["sl_threshold"] / n), per, fm0(C["sl_threshold"]), fm(sl / n), noun)))
    if kind == "weekly":
        faqs.append(("What hourly rate is %s a week?" % g,
                     "Over a 40-hour week, %s is %s an hour before tax, and about %s an hour after "
                     "PAYE and ACC." % (g, fm(amt / 40), fm(a["net"] / 52 / 40))))
    else:
        faqs.append(("What is %s %s per week?" % (g, per),
                     "%s a week before tax, and %s a week after PAYE and ACC (%s with 3.5%% KiwiSaver)."
                     % (fm(annual / 52), fm(a["net"] / 52), fm(b["net"] / 52))))

    amounts = P["amounts"]
    i = amounts.index(amt)
    pairs = [("%s %s" % (fm0(amounts[j]), per), "/%s/%d/" % (kind, amounts[j]))
             for j in (i - 2, i - 1, i + 1, i + 2) if 0 <= j < len(amounts)]
    sal = nearest(annual, SALARIES)
    pairs.append(("&asymp; %s salary" % fm0(sal), "/salary/%d/" % sal))
    hr = nearest(annual / HPY, HOURLIES)
    pairs.append(("&asymp; $%d/hour" % hr, "/hourly/%d/" % hr))
    for other in PERIODS:
        if other != kind:
            o = nearest(annual / PERIODS[other]["n"], PERIODS[other]["amounts"])
            pairs.append(("&asymp; %s %s" % (fm0(o), PERIODS[other]["a"]), "/%s/%d/" % (other, o)))

    title = "%s %s After Tax NZ (%s) | Count." % (g, per_t, YEAR)
    desc = ("%s %s after tax in New Zealand (%s): %s %s take-home with 3.5%% KiwiSaver, or %s without, "
            "after PAYE and ACC. Equivalent to a %s salary." % (
                g, per, YEAR, fm(b["net"] / n), per, fm(a["net"] / n), fm0(annual)))
    sl_line = ""
    if annual > C["sl_threshold"]:
        slb = e.breakdown(annual, kiwisaver_pct=3.5, with_student_loan=True)
        sl_line = ('<div class="callout">With a student loan (tax code M&nbsp;SL) a further <b>%s</b> per %s '
                   "is deducted, leaving <b>%s</b> %s with 3.5%% KiwiSaver.</div>"
                   % (fm(slb["sl"] / n), noun, fm(slb["net"] / n), per))
    body = """<h1>{g} {per_t} After Tax in New Zealand ({yr})</h1>
<p class="sub">{g} {per} before tax is <b>{gross}</b> a year. Here&rsquo;s what reaches your bank
account each {noun} in {yr} on tax code M, using the same engine as the Count. PAYE calculator.</p>
{answer}
{cta}
<h2>Where the money goes</h2>
{table}
{sl}
<h2>Effective vs marginal rate</h2>
{rates}
<h2>KiwiSaver &amp; student loan scenarios (on {gross}/year)</h2>
<div class="tablewrap">{ks}</div>
{pct}
<h2>FAQs</h2>
{faq}
<h2>Compare nearby amounts</h2>
{links}
{fine}""".format(
        g=g, per=per, per_t=per_t, yr=YEAR, gross=fm0(annual), noun=noun, answer=answer,
        cta=cta(annual), table=table, sl=sl_line, rates=rates_block(annual, seed),
        ks=kiwisaver_table(annual), pct=percentile_block(annual), faq=faq_block(faqs),
        links=links_block(_dedup(pairs)),
        fine=fine_print("Per-period figures are the annual amounts divided evenly; a real payslip "
                        "can differ by a few cents because payroll rounds each pay. "))
    crumbs = [("Count.", "/"), ("%s pay after tax" % P["adj"], "/%s/" % kind), (g, None)]
    ld_crumbs = [("Home", "/"), ("%s pay after tax" % P["adj"], "/%s/" % kind),
                 ("%s %s after tax" % (g, per), path)]
    return shell(title=title, description=desc, canonical=SITE + path, crumbs=crumbs,
                 jsonld=[faq_ld(faqs), breadcrumb_ld(ld_crumbs)], body=body)


def period_hub(kind):
    P = PERIODS[kind]
    n, per = P["n"], P["a"]
    items = "".join(
        '<a href="/%s/%d/"><b>%s</b><span>%s</span></a>'
        % (kind, amt, fm0(amt), fm0(e.breakdown(amt * n, kiwisaver_pct=3.5)["net"] / n))
        for amt in P["amounts"])
    lo, hi = fm0(P["amounts"][0]), fm0(P["amounts"][-1])
    title = "%s Pay After Tax NZ (%s) | Count." % (P["adj"], YEAR)
    desc = ("What %s to %s %s is after tax in New Zealand for %s. Take-home pay after PAYE, ACC "
            "and KiwiSaver for every amount, with a full breakdown." % (lo, hi, per, YEAR))
    others = " &middot; ".join('<a href="/%s/">%s pay</a>' % (k, PERIODS[k]["adj"])
                               for k in PERIODS if k != kind)
    body = """<h1>{adj} Pay After Tax in New Zealand ({yr})</h1>
<p class="sub">Pick your gross pay {per} to see what you take home. The green figure is take-home
{per} with 3.5% KiwiSaver (the calculator default). See also {others}, <a href="/salary/">annual
salaries</a> and <a href="/hourly/">hourly rates</a>, or use the <a href="/">calculator</a> for any amount.</p>
<div class="hub-grid">{items}</div>
{fine}""".format(adj=P["adj"], yr=YEAR, per=per, others=others, items=items, fine=fine_print())
    name = "%s pay after tax" % P["adj"]
    return shell(title=title, description=desc, canonical=SITE + "/%s/" % kind,
                 crumbs=[("Count.", "/"), (name, None)],
                 jsonld=[breadcrumb_ld([("Home", "/"), (name, "/%s/" % kind)])], body=body)


# ── Output + sitemap (lastmod only moves when content changes) ───────────────

_PAGES = []   # (path, priority, html)


def emit(path, html, priority="0.6"):
    """Write a page at a site path like /salary/70000/ and register it for the sitemap."""
    out = REPO_ROOT / path.strip("/") / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    _PAGES.append((path, priority, html))


def write_sitemap():
    old = json.loads(LASTMOD_FILE.read_text()) if LASTMOD_FILE.exists() else {}
    new = {}
    home = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
    entries = []
    for path, priority, html in [("/", "1.0", home)] + _PAGES:
        h = hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]
        prev = old.get(path)
        lastmod = prev["lastmod"] if prev and prev["hash"] == h else TODAY
        new[path] = {"hash": h, "lastmod": lastmod}
        entries.append("  <url>\n    <loc>%s%s</loc>\n    <lastmod>%s</lastmod>\n"
                       "    <priority>%s</priority>\n  </url>" % (SITE, path, lastmod, priority))
    LASTMOD_FILE.write_text(json.dumps(new, indent=0, sort_keys=True) + "\n")
    (REPO_ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries) + "\n</urlset>\n", encoding="utf-8")
    changed = sorted(p for p in new if new[p]["lastmod"] == TODAY)
    (REPO_ROOT / "tools" / "changed-urls.txt").write_text(
        "".join(SITE + p + "\n" for p in changed))
    return len(entries), len(changed)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    emit("/salary/", salary_hub(), "0.8")
    emit("/hourly/", hourly_hub(), "0.8")
    for a in SALARIES:
        emit("/salary/%d/" % a, salary_page(a))
    for r in HOURLIES:
        emit("/hourly/%d/" % r, hourly_page(r))
    for kind, P in PERIODS.items():
        emit("/%s/" % kind, period_hub(kind), "0.8")
        for amt in P["amounts"]:
            emit("/%s/%d/" % (kind, amt), period_page(kind, amt), "0.5")

    import topics
    n_topics = topics.build(sys.modules[__name__])

    total, changed = write_sitemap()
    print("Generated %d salary, %d hourly, %d period pages, %d topic/tax-rate pages; "
          "sitemap has %d URLs (%d changed today)."
          % (len(SALARIES), len(HOURLIES), sum(len(P["amounts"]) for P in PERIODS.values()),
             n_topics, total, changed))
    if not PCT:
        print("(Percentile block skipped: %s not present.)" % PERCENTILES_FILE.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()

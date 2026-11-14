"""Topic pages and the /tax-rates/ archive for count.co.nz.

Called from generate.py as topics.build(g), where g is the generate module
(passed in rather than imported, because generate runs as __main__).

Every NZ figure comes from tools/engine.py. Facts that are not in the engine
are noted with their source next to where they are defined, so the April
update is one pass through this file:
  - SECONDARY_CODES      IRD secondary tax codes (thresholds follow the brackets)
  - SCHEDULAR            IRD form IR330C (January 2024 edition), page 3
  - MIN_WAGE_HISTORY     MBIE minimum wage rates
  - KiwiSaver settings   Budget 2025 changes (in kiwisaver())
  - AU_*                 ATO resident rates 2026-27, LITO, Medicare levy
"""

import json

from engine import Engine, TAX_YEARS, CURRENT_YEAR, fm, fp, fm0, nf

SECONDARY_CODES = ["SB", "S", "SH", "ST", "SA"]   # one per bracket, lowest first

# (activity number, short description, standard rate %, no-notification rate %)
SCHEDULAR = [
    (1, "ACC personal service rehabilitation payments (attendant care, home help, childcare)", 10.5, "45"),
    (2, "Agricultural contracts for maintenance, development or other work on farming land", 15, "45"),
    (3, "Agricultural, horticultural or viticultural labour contracts (fruit, orchards, vegetables, vineyards)", 15, "45"),
    (4, "Apprentice jockeys or drivers", 15, "45"),
    (5, "Cleaning offices, businesses or other premises (not residential), plant, vehicles or furniture", 20, "45"),
    (6, "Commissions to insurance agents, sub-agents and salespeople", 20, "45"),
    (7, "Company directors&rsquo; fees", 33, "45"),
    (8, "Labour-only contracts in the building industry", 20, "45"),
    (9, "Demonstrating goods or appliances", 25, "45"),
    (10, "Entertainers (NZ resident): lecturers, presenters, sports participants, performers", 20, "45"),
    (11, "Examiners&rsquo; fees", 33, "45"),
    (12, "Fishing boat work for profit-share (labour only)", 20, "45"),
    (13, "Forestry or bush work, flax planting or cutting", 15, "45"),
    (14, "Freelance contributions to newspapers, journals, radio, television or stage", 25, "45"),
    (15, "Gardening, grass or hedge cutting, weed or vermin destruction (for a business)", 20, "45"),
    (16, "Honoraria", 33, "45"),
    (17, "Modelling", 20, "45"),
    (18, "Non-resident entertainers and professional sportspeople visiting NZ", 20, "N/A"),
    (19, "Payments by a labour hire business under a labour hire arrangement", 20, "45"),
    (20, "Caretaking or guarding, mail contracting, milk delivery, refuse removal, school transport", 15, "45"),
    (21, "Sales of eels, greenstone, sphagnum moss, whitebait, wild deer, pigs or goats (not retail)", 25, "45"),
    (22, "Public office holders&rsquo; fees", 33, "45"),
    (23, "Shearing or droving", 15, "45"),
    (24, "Television, video or film production work (NZ residents)", 20, "45"),
    (25, "Voluntary schedular payments", 20, "45"),
    (26, "Non-resident contractor (not a company), no other activity applies", 15, "45"),
    (27, "Non-resident contractor (a company), no other activity applies", 15, "20"),
]

MIN_WAGE_HISTORY = [("1 April 2022", 21.20), ("1 April 2023", 22.70), ("1 April 2024", 23.15),
                    ("1 April 2025", 23.50)]   # current year is appended from the engine

# Australia, resident individuals, 2026-27 income year (1 July 2026 - 30 June 2027).
AU_BRACKETS = [(18200, 0.0), (45000, 0.15), (135000, 0.30), (190000, 0.37), (float("inf"), 0.45)]
AU_MEDICARE = 0.02
AU_MEDICARE_LOW, AU_MEDICARE_HIGH = 28011, 35014   # singles: nil below, 10% shade-in between
AU_LITO = 700            # low income tax offset: full to $37,500, then tapers to nil at $66,667
AU_SUPER = 0.12          # employer super guarantee, paid on top of salary


def au_breakdown(x):
    tax, prev = 0.0, 0.0
    for limit, rate in AU_BRACKETS:
        if x <= prev:
            break
        tax += (min(x, limit) - prev) * rate
        prev = limit
    if x <= 37500:
        lito = AU_LITO
    elif x <= 45000:
        lito = AU_LITO - (x - 37500) * 0.05
    elif x <= 66667:
        lito = 325 - (x - 45000) * 0.015
    else:
        lito = 0
    tax = max(0.0, tax - max(0.0, lito))
    if x <= AU_MEDICARE_LOW:
        med = 0.0
    elif x <= AU_MEDICARE_HIGH:
        med = (x - AU_MEDICARE_LOW) * 0.10
    else:
        med = x * AU_MEDICARE
    return {"tax": tax, "medicare": med, "net": x - tax - med}


# ── Shared page furniture ────────────────────────────────────────────────────

TOPICS = [
    ("/tax-rates/", "NZ tax rates"),
    ("/secondary-tax/", "Secondary tax"),
    ("/student-loan/", "Student loan repayments"),
    ("/kiwisaver/", "KiwiSaver contributions"),
    ("/minimum-wage/", "Minimum wage after tax"),
    ("/pay-rise/", "Pay rise calculator"),
    ("/bonus-tax/", "Bonus &amp; redundancy tax"),
    ("/contractor-tax/", "Contractor tax"),
    ("/acc-levy/", "ACC earners&rsquo; levy"),
    ("/nz-vs-australia/", "NZ vs Australia"),
]


def inp(id_, label, value="", step="1", placeholder=""):
    return ('<div><label for="%s">%s</label><input type="number" id="%s" value="%s" min="0" step="%s"'
            ' inputmode="decimal" placeholder="%s"></div>' % (id_, label, id_, value, step, placeholder))


def chk(id_, label, checked=False):
    return ('<div><label class="check"><input type="checkbox" id="%s"%s> %s</label></div>'
            % (id_, " checked" if checked else "", label))


def sel(id_, label, options, selected=None):
    opts = "".join('<option value="%s"%s>%s</option>' % (v, " selected" if v == selected else "", t)
                   for v, t in options)
    return '<div><label for="%s">%s</label><select id="%s">%s</select></div>' % (id_, label, id_, opts)


def calc(fields, note=""):
    return ('<div class="calc"><div class="calc-grid">%s</div><div class="calc-out" id="out"></div>%s</div>'
            % ("".join(fields), '<p class="calc-note">%s</p>' % note if note else ""))


def table(head, rows, last_class=""):
    th = "".join('<th%s>%s</th>' % (' class="num"' if i else "", h) for i, h in enumerate(head))
    body = ""
    for n, r in enumerate(rows):
        cls = ' class="%s"' % last_class if last_class and n == len(rows) - 1 else ""
        body += "<tr%s>%s</tr>" % (cls, "".join(
            '<td%s>%s</td>' % (' class="num"' if i else "", c) for i, c in enumerate(r)))
    return ('<div class="tablewrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
            % (th, body))


def ks_options(C):
    return [("0", "No KiwiSaver")] + [(str(r), "%s%%" % nf(r, 1 if r % 1 else 0)) for r in C["kiwisaver_rates"]]


def js_base(C):
    """Constants + helpers shared by every inline calculator (mirrors index.html)."""
    br = ",".join("[%s,%s]" % ("Infinity" if l == float("inf") else int(l), r) for l, r in C["brackets"])
    return (
        "const BR=[" + br + "],ACC_RATE=" + repr(C["acc_rate"]) + ",ACC_CAP=" + str(int(C["acc_cap"]))
        + ",SL_T=" + str(int(C["sl_threshold"])) + ",SL_R=" + repr(C["sl_rate"])
        + ",MW=" + repr(C["min_wage"]) + ";\n"
        "function paye(x){let t=0,p=0;for(const[l,r]of BR){if(x<=p)break;t+=(Math.min(x,l)-p)*r;p=l}return t}\n"
        "function acc(x){return Math.min(x,ACC_CAP)*ACC_RATE}\n"
        "function marg(x){for(const[l,r]of BR)if(x<=l)return r;return BR[BR.length-1][1]}\n"
        "function sl(x){return x>SL_T?(x-SL_T)*SL_R:0}\n"
        "const $=id=>document.getElementById(id),num=id=>Math.max(0,parseFloat($(id).value)||0);\n"
        "const fm=v=>(v<0?'\\u2212':'')+'$'+Math.abs(v).toLocaleString('en-NZ',{minimumFractionDigits:2,maximumFractionDigits:2});\n"
        "const pc=v=>(v*100).toFixed(1)+'%';\n"
        "function out(rows){$('out').innerHTML=rows.map(r=>'<div'+(r[2]?' class=\"big\"':'')+'><span>'+r[0]+'</span><span>'+r[1]+'</span></div>').join('')}\n"
    )


# tool_used fires once per page view, the first time a visitor changes an input.
JS_TAIL = ("\nlet used=false;function touched(){if(!used){used=true;if(window.cEv)cEv('tool_used')}run()}"
           "\ndocument.querySelectorAll('.calc input,.calc select').forEach(el=>{"
           "el.addEventListener('input',touched);el.addEventListener('change',touched)});run();")


def page(g, path, *, title, desc, h1, sub, body, faqs, js="", crumb=None, parents=(), priority="0.7"):
    related = [(label, href) for href, label in TOPICS if href != path]
    related += [("Salary after tax", "/salary/"), ("Hourly to salary", "/hourly/"), ("PAYE calculator", "/")]
    html_body = """<h1>%s</h1>
<p class="sub">%s</p>
%s
<h2>FAQs</h2>
%s
<h2>More NZ pay tools</h2>
%s
<p class="fine">Figures use NZ %s rates and thresholds. This is general information, not financial or tax
advice &mdash; check <a href="https://www.ird.govt.nz" rel="noopener">ird.govt.nz</a> or a tax agent for
your own situation.</p>""" % (h1, sub, body, g.faq_block(faqs), g.links_block(related), g.YEAR)
    crumb = crumb or g.plain(h1)
    crumbs = [("Count.", "/")] + [(n, p) for n, p in parents] + [(crumb, None)]
    ld_crumbs = [("Home", "/")] + [(g.plain(n), p) for n, p in parents] + [(g.plain(crumb), path)]
    script = "<script>\n%s%s%s\n</script>" % (js_base(g.C), js, JS_TAIL) if js else ""
    g.emit(path, g.shell(title=title, description=desc, canonical=g.SITE + path, crumbs=crumbs,
                         jsonld=[g.faq_ld(faqs), g.breadcrumb_ld(ld_crumbs)], body=html_body,
                         script=script), priority)


def band_label(lo, hi):
    if hi == float("inf"):
        return "Over %s" % fm0(lo)
    return "%s &ndash; %s" % (fm0(lo + 1 if lo else 0), fm0(hi))


def bands(C):
    out, prev = [], 0
    for limit, rate in C["brackets"]:
        out.append((prev, limit, rate))
        prev = limit
    return out


# ── Secondary tax ────────────────────────────────────────────────────────────

def secondary(g):
    C, e = g.C, g.e
    rows = [(code, band_label(lo, hi), fp(rate), fp(rate + C["acc_rate"], 2))
            for code, (lo, hi, rate) in zip(SECONDARY_CODES, bands(C))]
    main, second = 60000, 15000
    total = main + second
    flat = e.marginal_rate(total) * second
    true = e.paye(total) - e.paye(main)
    codes_js = json.dumps(SECONDARY_CODES)
    js = """
const CODES=""" + codes_js + """;
function run(){
  const m=num('main'),s=num('second'),t=m+s,hasSL=$('sl').checked;
  let i=BR.findIndex(b=>t<=b[0]);if(i<0)i=BR.length-1;
  const rate=BR[i][1],withheld=s*rate,levy=acc(t)-acc(m),owed=paye(t)-paye(m),loan=hasSL?s*SL_R:0,diff=withheld-owed;
  out([['Total income (both jobs)',fm(t)],['Secondary tax code',CODES[i]+(hasSL?' SL':'')+' ('+pc(rate)+')'],
   ['PAYE withheld on second job',fm(withheld)],['ACC earners\\u2019 levy on second job',fm(levy)]]
   .concat(hasSL?[['Student loan (12% of every dollar)',fm(loan)]]:[])
   .concat([['Second job take-home / year',fm(s-withheld-levy-loan),1],['Second job take-home / week',fm((s-withheld-levy-loan)/52)],
   ['Income tax actually due on it',fm(owed)],
   [diff>0.5?'Over-withheld (refund at year end)':diff<-0.5?'Under-withheld (bill at year end)':'Withheld vs due','\\u2248 '+fm(Math.abs(diff))]]));
}"""
    body = """%s
<h2>Secondary tax codes for %s</h2>
<p>Your second job is taxed at a single flat rate, chosen by your <b>total</b> yearly income from all
sources (both jobs, plus any benefit or NZ Super). Your main job &mdash; the one that pays the most &mdash;
keeps tax code M.</p>
%s
<h2>Is secondary tax higher?</h2>
<p>No. There is no extra tax for having two jobs &mdash; your total income is taxed exactly as if one
employer paid it all. Your main job has already used up the lower tax brackets, so the second job is
taxed at the rate your top dollars fall into.</p>
<div class="callout">Example: %s main job + %s second job = %s. That falls in the %s band (%s), so the
second job has %s PAYE withheld. The tax actually due on that extra income is %s%s</div>
<p>The flat rate is only exact when all your second-job income sits inside one bracket. If your total
straddles a threshold you will be slightly over-taxed; if your income changes during the year it can go
either way. Inland Revenue squares this up automatically after 31 March. If you are consistently
over-taxed, you can apply for a <b>tailored tax code</b> so less is deducted each pay.</p>
<h2>Student loans and second jobs</h2>
<p>On a secondary code with SL (for example S&nbsp;SL), repayments are 12%% of <b>every</b> dollar from the
second job, because the %s threshold is used by your main job. If your total income is below the
threshold you can ask IRD for a special deduction rate.</p>""" % (
        calc([inp("main", "Main job (per year)", main, "1000"),
              inp("second", "Second job (per year)", second, "500"),
              chk("sl", "Student loan")],
             "Assumes both jobs run all year. Uses %s rates; ACC is charged on total income up to %s."
             % (g.YEAR, fm0(C["acc_cap"]))),
        g.YEAR,
        table(["Code", "Total yearly income", "PAYE rate", "With ACC levy"], rows),
        fm0(main), fm0(second), fm0(total), SECONDARY_CODES[[i for i, (l, _) in enumerate(C["brackets"]) if total <= l][0]],
        fp(e.marginal_rate(total)), fm(flat), fm(true),
        " &mdash; the same, because the whole second income sits in one bracket." if abs(flat - true) < 0.5
        else ", so about %s is refunded at year end." % fm(flat - true) if flat > true
        else ", so about %s is owed at year end." % fm(true - flat),
        fm0(C["sl_threshold"]))
    faqs = [
        ("What is the secondary tax rate in NZ?",
         "It depends on your total yearly income: %s. The %s ACC earners&rsquo; levy is added on top."
         % ("; ".join("%s is %s (%s)" % (c, fp(r), g.plain(band_label(lo, hi)))
                      for c, (lo, hi, r) in zip(SECONDARY_CODES, bands(C))), fp(C["acc_rate"], 2))),
        ("Which job should be my main job?",
         "The one that pays the most. It uses tax code M (or M&nbsp;SL with a student loan) and gets the "
         "lower tax brackets; every other job uses a secondary code."),
        ("Do I get secondary tax back?",
         "Only the part that was over-withheld. Inland Revenue works out your tax on total income after "
         "31 March and automatically refunds any excess or bills any shortfall."),
        ("What if my second job income changes during the year?",
         "Tell your employer a new tax code if your expected total income moves into a different band. "
         "Using a code that is too low means a tax bill at the end of the year."),
    ]
    page(g, "/secondary-tax/",
         title="Secondary Tax NZ %s: Codes &amp; Calculator | Count." % g.YEAR,
         desc="NZ secondary tax codes for %s (SB, S, SH, ST, SA) and a calculator showing what is "
              "withheld from a second job, what you actually owe, and whether to expect a refund." % g.YEAR,
         h1="Secondary Tax in NZ: Codes and Calculator (%s)" % g.YEAR,
         sub="Work out which secondary tax code applies to your second job, how much is deducted, and "
             "whether you are likely to get some back.",
         body=body, faqs=faqs, js=js, crumb="Secondary tax")


# ── Student loan ─────────────────────────────────────────────────────────────

def student_loan(g):
    C, e = g.C, g.e
    t = C["sl_threshold"]
    rows = []
    for a in (30000, 40000, 50000, 60000, 70000, 80000, 100000, 120000, 150000):
        s = e.student_loan(a)
        b = e.breakdown(a, kiwisaver_pct=3.5, with_student_loan=True)
        rows.append(('<a href="/salary/%d/">%s</a>' % (a, fm0(a)), fm(s), fm(s / 52), fm(b["net"] / 52)))
    js = """
function run(){
  const s=num('sal'),b=num('bal'),r=sl(s);
  const rows=[['Repayment per year',fm(r),1],['Per month',fm(r/12)],['Per fortnight',fm(r/26)],['Per week',fm(r/52)],
   ['Share of gross pay',s?pc(r/s):'0.0%']];
  if(b>0)rows.push(['Time to clear '+fm(b),r>0?(()=>{const m=Math.ceil(b/r*12);return (m>=12?Math.floor(m/12)+' yr ':'')+(m%12)+' mo'})():'No repayments at this income']);
  out(rows);
}"""
    body = """%s
<h2>How repayments work</h2>
<p>If you have a New Zealand student loan and use a tax code ending in SL, your employer deducts
<b>12 cents for every dollar you earn above %s a year</b> &mdash; that is %s a week or %s a fortnight
before tax. Nothing is deducted in a pay period where you earn less than the threshold.</p>
<p>Repayments come out of your pay alongside PAYE and go straight to Inland Revenue. While you live in
New Zealand the loan is interest-free, so every dollar repaid reduces the balance.</p>
<h2>Repayments by salary</h2>
%s
<p class="fine" style="margin-top:.5rem">Take-home column is tax code M&nbsp;SL with 3.5%% KiwiSaver.</p>
<h2>Second jobs and going overseas</h2>
<ul class="plain">
<li>A second job on an SL code repays 12%% of every dollar, with no threshold. See
<a href="/secondary-tax/">secondary tax</a>.</li>
<li>You can make extra repayments at any time through myIR or internet banking.</li>
<li>If you move overseas for six months or more the loan generally starts to attract interest and
repayments are set by your loan balance instead of your income. Check with IRD before you go.</li>
</ul>""" % (
        calc([inp("sal", "Salary (per year)", 70000, "1000"),
              inp("bal", "Loan balance (optional)", 30000, "1000")],
             "Time to clear assumes your salary stays the same, you stay in NZ (no interest) and make no "
             "extra repayments."),
        fm0(t), fm0(t / 52), fm0(t / 26),
        table(["Salary", "Repaid / year", "Repaid / week", "Take-home / week"], rows))
    ex = e.student_loan(70000)
    faqs = [
        ("What is the student loan repayment threshold in NZ for %s?" % g.YEAR,
         "%s a year (%s a week). You repay 12%% of income above that." % (fm0(t), fm0(t / 52))),
        ("How much student loan do I repay on $70,000?",
         "%s a year, which is %s a week: 12%% of the %s you earn above the %s threshold."
         % (fm(ex), fm(ex / 52), fm0(70000 - t), fm0(t))),
        ("Is there interest on NZ student loans?",
         "Not while you live in New Zealand. Borrowers based overseas are generally charged interest."),
        ("Do KiwiSaver contributions reduce my student loan repayments?",
         "No. Repayments are worked out on gross pay, before KiwiSaver is taken out."),
    ]
    page(g, "/student-loan/",
         title="Student Loan Repayment Calculator NZ %s | Count." % g.YEAR,
         desc="NZ student loan repayment calculator for %s: 12%% of income over %s. See repayments per "
              "week, fortnight and year for your salary, and how long your loan will take to clear."
              % (g.YEAR, fm0(t)),
         h1="Student Loan Repayment Calculator NZ (%s)" % g.YEAR,
         sub="See how much comes out of your pay for your student loan, and how long it will take to clear.",
         body=body, faqs=faqs, js=js, crumb="Student loan")


# ── KiwiSaver ────────────────────────────────────────────────────────────────

def kiwisaver(g):
    C, e = g.C, g.e
    rates = C["kiwisaver_rates"]
    lab = lambda r: "%s%%" % nf(r, 1 if r % 1 else 0)
    rows = []
    for a in (50000, 70000, 90000, 120000, 150000):
        rows.append(['<a href="/salary/%d/">%s</a>' % (a, fm0(a))]
                    + [fm(e.breakdown(a)["net"] / 52)]
                    + [fm(e.breakdown(a, kiwisaver_pct=r)["net"] / 52) for r in rates])
    js = """
const RATES=""" + json.dumps(rates) + """,EMP=""" + repr(C["kiwisaver_default"]) + """;
function run(){
  const s=num('sal'),base=s-paye(s)-acc(s)-($('sl').checked?sl(s):0);
  const rows=[['No KiwiSaver: take-home / week',fm(base/52)]];
  RATES.forEach(r=>{const c=s*r/100;rows.push([r+'%: you put in '+fm(c/52)+' / week',fm((base-c)/52)+' take-home',r===EMP])});
  rows.push(['Employer adds (before tax on contributions)',fm(s*EMP/100)+' / year']);
  out(rows);
}"""
    body = """%s
<h2>Weekly take-home at each KiwiSaver rate</h2>
%s
<p class="fine" style="margin-top:.5rem">Tax code M, no student loan. Your KiwiSaver contribution is taken from
gross pay and does not reduce your PAYE.</p>
<h2>KiwiSaver rules for %s</h2>
<ul class="plain">
<li><b>Minimum employee rate is %s</b> of gross pay from 1 April 2026 (up from 3%%), and is set to rise to 4%%
from 1 April 2028. You can choose %s instead.</li>
<li><b>Your employer must put in at least %s</b> as well. Employer contributions are taxed (ESCT) before
they reach your account, so slightly less than the headline amount arrives.</li>
<li>You can apply to Inland Revenue to stay at 3%% temporarily if the higher rate is unaffordable; your
employer may then match at 3%%.</li>
<li><b>Government contribution:</b> 25 cents for every dollar you contribute, up to $260.72 a year
(reached by contributing $1,042.86 between 1 July and 30 June). It is not paid if your income is over
$180,000.</li>
<li>After 12 months you can take a savings suspension of 3 months to 1 year.</li>
</ul>
<h2>Is a higher rate worth it?</h2>
<p>Going from %s to %s on a $70,000 salary costs you %s a week in take-home pay and adds %s a year to your
KiwiSaver. Employers only have to match the minimum, so the extra is your money alone &mdash; a good deal
if you would not otherwise save it, less so if you have high-interest debt to clear first.</p>""" % (
        calc([inp("sal", "Salary (per year)", 70000, "1000"), chk("sl", "Student loan")]),
        table(["Salary", "No KiwiSaver"] + [lab(r) for r in rates], rows),
        g.YEAR, lab(rates[0]), ", ".join(lab(r) for r in rates[1:-1]) + " or " + lab(rates[-1]),
        lab(C["kiwisaver_default"]), lab(rates[0]), lab(rates[2]),
        fm(70000 * (rates[2] - rates[0]) / 100 / 52), fm(70000 * (rates[2] - rates[0]) / 100))
    faqs = [
        ("What is the minimum KiwiSaver contribution in %s?" % g.YEAR,
         "%s of gross pay for employees, matched by at least %s from your employer."
         % (lab(rates[0]), lab(C["kiwisaver_default"]))),
        ("How much is 3.5% KiwiSaver on $70,000?",
         "%s a year, or %s a week, from your pay &mdash; plus the same again from your employer before tax."
         % (fm(70000 * 0.035), fm(70000 * 0.035 / 52))),
        ("Does KiwiSaver reduce my tax?",
         "No. PAYE and the ACC levy are calculated on your full gross pay; KiwiSaver comes out afterwards."),
        ("Can I change my KiwiSaver rate?",
         "Yes, at any time, by telling your employer or through myIR. The change applies from your next pay."),
    ]
    page(g, "/kiwisaver/",
         title="KiwiSaver Contribution Calculator NZ %s | Count." % g.YEAR,
         desc="Compare KiwiSaver contribution rates (%s) for %s: what each rate costs per week, what your "
              "employer adds, and your take-home pay at each." % (", ".join(lab(r) for r in rates), g.YEAR),
         h1="KiwiSaver Contribution Calculator NZ (%s)" % g.YEAR,
         sub="See what each KiwiSaver rate takes from your pay each week, and what you are left with.",
         body=body, faqs=faqs, js=js, crumb="KiwiSaver")


# ── Minimum wage ─────────────────────────────────────────────────────────────

def minimum_wage(g):
    C, e = g.C, g.e
    mw = C["min_wage"]
    rows = []
    for h in (10, 15, 20, 25, 30, 35, 37.5, 40, 45, 50):
        annual = mw * h * 52
        a = e.breakdown(annual)
        b = e.breakdown(annual, kiwisaver_pct=3.5)
        rows.append((nf(h, 1 if h % 1 else 0), fm(mw * h), fm0(annual), fm(a["net"] / 52), fm(b["net"] / 52)))
    full = e.breakdown(mw * 40 * 52)
    full_ks = e.breakdown(mw * 40 * 52, kiwisaver_pct=3.5)
    hist = [(d, "$%s" % nf(r)) for d, r in MIN_WAGE_HISTORY] + [("1 April 2026", "$%s" % nf(mw))]
    js = """
function run(){
  const r=num('rate'),h=num('hrs'),y=r*h*52,ks=$('ks').checked?y*0.035:0,loan=$('sl').checked?sl(y):0;
  const net=y-paye(y)-acc(y)-ks-loan;
  out([['Gross per week',fm(r*h)],['Gross per year',fm(y)],['Take-home per week',fm(net/52),1],
   ['Take-home per fortnight',fm(net/26)],['Take-home per year',fm(net)],['Take-home per hour worked',h?fm(net/52/h):fm(0)]]
   .concat(r&&r<MW?[['Note','Below the adult minimum wage of $'+MW.toFixed(2)]]:[]));
}"""
    body = """<div class="answer"><div class="answer-card primary"><div class="answer-label">Adult minimum wage</div>
<div class="answer-big">$%s <span>/ hour</span></div><div class="answer-rows">
<div><span>40-hour week, gross</span><span>%s</span></div><div><span>Per year, gross</span><span>%s</span></div>
<div><span>Starting-out / training</span><span>$%s / hour</span></div></div></div>
<div class="answer-card"><div class="answer-label">Full-time take-home</div>
<div class="answer-big">%s <span>/ week</span></div><div class="answer-rows">
<div><span>With 3.5%% KiwiSaver</span><span>%s / week</span></div>
<div><span>Per year (PAYE + ACC only)</span><span>%s</span></div>
<div><span>Per hour after tax</span><span>%s</span></div></div></div></div>
%s
<h2>Minimum wage after tax by hours worked</h2>
%s
<p class="fine" style="margin-top:.5rem">Tax code M, no student loan, working every week of the year.</p>
<h2>Who gets which rate</h2>
<ul class="plain">
<li><b>Adult ($%s):</b> most employees aged 16 and over.</li>
<li><b>Starting-out ($%s):</b> some 16 to 19 year olds in their first six months with an employer, or who are
doing industry training.</li>
<li><b>Training ($%s):</b> employees aged 20 or over doing at least 60 credits a year of recognised
industry training.</li>
</ul>
<p>The minimum wage applies to every hour worked, whether you are paid by the hour, by salary or by piece
rate. Casual workers paid 8%% holiday pay on top receive it in addition to the minimum.</p>
<h2>Recent minimum wage increases</h2>
%s""" % (
        nf(mw), fm(mw * 40), fm0(mw * 40 * 52), nf(mw * 0.8),
        fm(full["net"] / 52), fm(full_ks["net"] / 52), fm(full["net"]), fm(full["net"] / 2080),
        calc([inp("rate", "Hourly rate", nf(mw), "0.05"), inp("hrs", "Hours per week", 40, "0.5"),
              chk("ks", "KiwiSaver 3.5%", True), chk("sl", "Student loan")]),
        table(["Hours / week", "Gross / week", "Gross / year", "Take-home / week", "With 3.5% KiwiSaver"], rows),
        nf(mw), nf(mw * 0.8), nf(mw * 0.8),
        table(["From", "Adult minimum wage"], hist))
    faqs = [
        ("What is the minimum wage in NZ in 2026?",
         "$%s an hour for adults from 1 April 2026. The starting-out and training minimum wages are $%s "
         "an hour (80%% of the adult rate)." % (nf(mw), nf(mw * 0.8))),
        ("What is minimum wage after tax for a 40-hour week?",
         "%s gross becomes %s a week after PAYE and the ACC levy, or %s a week with 3.5%% KiwiSaver."
         % (fm(mw * 40), fm(full["net"] / 52), fm(full_ks["net"] / 52))),
        ("What is the minimum wage as a yearly salary?",
         "%s a year for 40 hours a week, 52 weeks a year &mdash; %s after PAYE and ACC."
         % (fm0(mw * 40 * 52), fm(full["net"]))),
        ("Can a salaried employee be paid below minimum wage?",
         "No. A salary must work out to at least the minimum wage for every hour actually worked in each "
         "pay period."),
    ]
    page(g, "/minimum-wage/",
         title="Minimum Wage NZ 2026 After Tax: $%s/hr | Count." % nf(mw),
         desc="The NZ adult minimum wage is $%s an hour from 1 April 2026. A 40-hour week is %s gross and "
              "%s after tax. Take-home table for 10 to 50 hours a week, plus a calculator."
              % (nf(mw), fm(mw * 40), fm(full["net"] / 52)),
         h1="NZ Minimum Wage After Tax (%s)" % g.YEAR,
         sub="What the minimum wage actually pays into your bank account, for any number of hours.",
         body=body, faqs=faqs, js=js, crumb="Minimum wage")


# ── Pay rise ─────────────────────────────────────────────────────────────────

def pay_rise(g):
    C, e = g.C, g.e
    rows = []
    for a in (45000, 50000, 60000, 75000, 80000, 100000, 150000, 180000):
        d = e.breakdown(a + 5000)["net"] - e.breakdown(a)["net"]
        rows.append(("%s &rarr; %s" % (fm0(a), fm0(a + 5000)), fm(d), fm(d / 52), fp(d / 5000)))
    js = """
function run(){
  const a=num('cur'),b=num('nw'),k=parseFloat($('ks').value)/100,hasSL=$('sl').checked;
  const net=x=>x-paye(x)-acc(x)-x*k-(hasSL?sl(x):0),d=net(b)-net(a),g=b-a;
  out([['Change in gross pay',fm(g)+(a?' ('+(g/a*100).toFixed(1)+'%)':'')],['Extra take-home / year',fm(d),1],
   ['Extra take-home / fortnight',fm(d/26)],['Extra take-home / week',fm(d/52)],
   ['Share of the rise you keep',g?pc(d/g):'0.0%'],['New take-home / year',fm(net(b))],
   ['Marginal tax rate after the rise',pc(marg(b))]]);
}"""
    body = """%s
<h2>What a $5,000 pay rise is worth</h2>
%s
<p class="fine" style="margin-top:.5rem">After PAYE and the ACC levy only. KiwiSaver and student loan
repayments take a further share of every extra dollar.</p>
<h2>A pay rise never leaves you worse off</h2>
<p>New Zealand tax is progressive: moving into a higher bracket only changes the rate on the dollars
<b>above</b> the threshold. The tax on everything you already earned stays the same, so more gross pay
always means more take-home pay.</p>
<p>What can change is how much of each extra dollar you keep. Between %s and %s you keep about %s cents
in the dollar after PAYE and ACC; above %s it drops to about %s cents. If you receive Working for Families
or other income-tested support, those payments can reduce as your income rises &mdash; that is separate
from PAYE and not included here.</p>
<h2>Asking for a rise? Know the number</h2>
<p>Employers talk in gross, bills are paid in net. Use the calculator to turn an offer into dollars per
week, or compare two salaries side by side on the <a href="/salary/">salary pages</a>.</p>""" % (
        calc([inp("cur", "Current salary", 70000, "1000"), inp("nw", "New salary", 75000, "1000"),
              sel("ks", "KiwiSaver", ks_options(C), "3.5"), chk("sl", "Student loan")]),
        table(["Pay rise", "Extra / year", "Extra / week", "You keep"], rows),
        fm0(C["brackets"][0][0]), fm0(C["brackets"][1][0]),
        nf((1 - C["brackets"][1][1] - C["acc_rate"]) * 100, 0),
        fm0(C["brackets"][2][0]), nf((1 - C["brackets"][3][1] - C["acc_rate"]) * 100, 0))
    d = e.breakdown(80000)["net"] - e.breakdown(75000)["net"]
    faqs = [
        ("How much of a pay rise do I keep after tax in NZ?",
         "After PAYE and the %s ACC levy you keep between about %s%% and %s%% of each extra dollar, depending "
         "on your bracket. KiwiSaver and student loan deductions reduce that further."
         % (fp(C["acc_rate"], 2), nf((1 - C["brackets"][-1][1]) * 100, 0),
            nf((1 - C["brackets"][0][1] - C["acc_rate"]) * 100, 0))),
        ("Will a pay rise push me into a higher tax bracket and cost me money?",
         "No. Only the income above the bracket threshold is taxed at the higher rate, so your take-home "
         "pay always goes up."),
        ("How much extra is a rise from $75,000 to $80,000?",
         "%s a year after PAYE and ACC, or %s a week." % (fm(d), fm(d / 52))),
        ("Does KiwiSaver come out of a pay rise?",
         "Yes. Your contribution is a percentage of gross pay, so it rises with your salary &mdash; as does "
         "your employer&rsquo;s contribution."),
    ]
    page(g, "/pay-rise/",
         title="Pay Rise Calculator NZ %s: Extra Take-Home | Count." % g.YEAR,
         desc="NZ pay rise calculator for %s. Enter your current and new salary to see the extra take-home "
              "pay per week and per year after PAYE, ACC, KiwiSaver and student loan." % g.YEAR,
         h1="Pay Rise Calculator NZ (%s)" % g.YEAR,
         sub="Enter your current and new salary to see how much of the rise actually reaches your bank account.",
         body=body, faqs=faqs, js=js, crumb="Pay rise")


# ── Bonus / lump sum / redundancy ────────────────────────────────────────────

def bonus(g):
    C, e = g.C, g.e
    rows = []
    for lo, hi, rate in bands(C):
        if hi <= C["acc_cap"]:
            with_acc = fp(rate + C["acc_rate"], 2)
        elif lo < C["acc_cap"]:   # the ACC cap falls inside this band
            with_acc = "%s (%s above %s)" % (fp(rate + C["acc_rate"], 2), fp(rate, 2), fm0(C["acc_cap"]))
        else:
            with_acc = fp(rate, 2)
        rows.append((band_label(lo, hi), fp(rate), with_acc))
    sal, lump = 80000, 5000
    rate = e.marginal_rate(sal + lump)
    js = """
function run(){
  const s=num('sal'),b=num('lump'),red=$('type').value==='red',k=red?0:parseFloat($('ks').value)/100,t=s+b;
  const rate=marg(t),tax=b*rate,levy=red?0:Math.max(0,Math.min(t,ACC_CAP)-Math.min(s,ACC_CAP))*ACC_RATE;
  const wt=SL_T/52,w=s/52,loan=$('sl').checked?(Math.max(0,w+b-wt)-Math.max(0,w-wt))*SL_R:0,ksv=b*k,due=paye(t)-paye(s),diff=tax-due;
  out([['Annualised income incl. lump sum',fm(t)],['Lump sum PAYE rate',pc(rate)],['PAYE withheld',fm(tax)],
   ['ACC earners\\u2019 levy',red?'Not charged on redundancy':fm(levy)]]
   .concat(ksv?[['KiwiSaver',fm(ksv)]]:[]).concat(loan?[['Student loan (12%)',fm(loan)]]:[])
   .concat([['You receive',fm(b-tax-levy-ksv-loan),1],['Income tax actually due on it',fm(due)],
   [diff>0.5?'Over-withheld (refund at year end)':diff<-0.5?'Under-withheld (bill at year end)':'Withheld vs due','\\u2248 '+fm(Math.abs(diff))]]));
}"""
    body = """%s
<h2>How lump sums are taxed</h2>
<p>Bonuses, back pay, cashed-up leave, retirement payments and redundancy are &ldquo;extra pays&rdquo;.
Instead of using the normal PAYE tables, your employer:</p>
<ul class="plain">
<li>takes your regular gross pay for the <b>last four weeks</b> and multiplies it by 13 to estimate a yearly
income (or the last month multiplied by 12 if you are paid monthly),</li>
<li>adds the lump sum, and</li>
<li>taxes the <b>whole lump sum at one flat rate</b> &mdash; the rate for the band that total falls in.</li>
</ul>
%s
<p>The ACC earners&rsquo; levy (%s) is added while your annualised income is under %s. This calculator uses
your salary as the annualised figure; if your last four weeks were unusually high or low, your employer&rsquo;s
number will differ.</p>
<div class="callout">Example: a %s bonus on an %s salary. The total of %s is in the %s band, so %s PAYE is
withheld, plus %s ACC.</div>
<h2>Redundancy payments</h2>
<p>Redundancy is taxed as a lump sum using the same flat-rate method, with two differences: <b>no ACC
earners&rsquo; levy</b> is charged and <b>no KiwiSaver</b> is deducted. Student loan repayments are
still deducted. Notice pay and unused annual leave paid out with it are ordinary taxable pay.</p>
<h2>Why a bonus feels over-taxed</h2>
<p>The flat rate treats the whole lump sum as your top slice of income, which is usually right. It
over-taxes you when the lump sum straddles a bracket threshold or your annualised pay overstates what you
really earn in the year. Inland Revenue recalculates after 31 March and refunds any excess automatically.</p>""" % (
        calc([inp("sal", "Salary (per year)", sal, "1000"), inp("lump", "Bonus or lump sum", lump, "500"),
              sel("type", "Type", [("bonus", "Bonus / back pay / leave"), ("red", "Redundancy")]),
              sel("ks", "KiwiSaver", ks_options(C), "3.5"), chk("sl", "Student loan")]),
        table(["Annualised income + lump sum", "PAYE rate", "With ACC levy"], rows),
        fp(C["acc_rate"], 2), fm0(C["acc_cap"]),
        fm0(lump), fm0(sal), fm0(sal + lump), g.plain(band_label(*[(lo, hi) for lo, hi, r in bands(C) if sal + lump <= hi][0])),
        fm(lump * rate), fm(lump * C["acc_rate"]))
    faqs = [
        ("How much tax do I pay on a bonus in NZ?",
         "A flat rate of %s, depending on your annualised income plus the bonus, with the %s ACC levy on top. "
         "On an $80,000 salary a $5,000 bonus is taxed at %s."
         % (", ".join(fp(r) for _, _, r in bands(C)), fp(C["acc_rate"], 2), fp(rate))),
        ("Is redundancy pay taxed in NZ?",
         "Yes. It is taxed as a lump sum at the flat extra-pay rate. There is no tax-free amount, but the "
         "ACC earners&rsquo; levy and KiwiSaver are not deducted from it."),
        ("Are bonuses taxed more than normal pay?",
         "No. Over the full year a bonus is taxed like any other income. The flat-rate method can withhold "
         "too much at the time, and the excess is refunded after the tax year ends."),
        ("Does KiwiSaver come out of my bonus?",
         "Usually yes, at your normal contribution rate, unless your employment agreement says the bonus "
         "is discretionary and excluded. It is not deducted from redundancy."),
    ]
    page(g, "/bonus-tax/",
         title="Bonus &amp; Redundancy Tax Calculator NZ %s | Count." % g.YEAR,
         desc="How bonuses, lump sums and redundancy pay are taxed in NZ for %s. Calculator shows the flat "
              "PAYE rate, ACC, KiwiSaver and student loan, and what you actually receive." % g.YEAR,
         h1="Bonus and Redundancy Tax Calculator NZ (%s)" % g.YEAR,
         sub="See how much of a bonus, back-pay or redundancy payment you will actually receive.",
         body=body, faqs=faqs, js=js, crumb="Bonus &amp; redundancy tax")


# ── Contractor / schedular payments ──────────────────────────────────────────

def contractor(g):
    C, e = g.C, g.e
    rows = [(str(n), d, "%s%%" % nf(r, 1 if r % 1 else 0), nn if nn == "N/A" else nn + "%")
            for n, d, r, nn in SCHEDULAR]
    js = """
function run(){
  const inc=num('inc'),exp=num('exp'),wt=num('wt')/100,profit=Math.max(0,inc-exp);
  const withheld=inc*wt,tax=paye(profit),levy=acc(profit),bal=tax-withheld;
  out([['Withheld during the year',fm(withheld)],['Profit (income less expenses)',fm(profit)],
   ['Income tax on profit',fm(tax)],[bal>=0?'Still to pay at year end':'Refund at year end',fm(Math.abs(bal)),1],
   ['Rate that would cover your tax',inc?pc(tax/inc):'0.0%'],
   ['ACC earners\\u2019 levy (invoiced by ACC, estimate)',fm(levy)],['Left after tax and earners\\u2019 levy',fm(profit-tax-levy)]]);
}"""
    body = """%s
<h2>How contractors are taxed</h2>
<p>Contractors do not have PAYE deducted. If your work is on Inland Revenue&rsquo;s list of
<b>schedular payments</b>, the business paying you withholds tax at a flat rate from each invoice (tax
code WT) and you square up in an IR3 return after 31 March. Everyone else pays their own tax, usually
through provisional tax.</p>
<ul class="plain">
<li>You tell each payer your rate on an <b>IR330C</b> form. You can use the standard rate for your
activity or choose your own, but not below <b>10%%</b> (15%% for non-residents and temporary visa holders)
unless IRD gives you a tailored rate.</li>
<li>If you do not give a payer an IR330C, they must withhold at the <b>no-notification rate of 45%%</b>.</li>
<li>Withholding applies to the gross payment, before your expenses, so a contractor with high costs can
choose a lower rate and one with few costs a higher rate.</li>
<li>ACC is not deducted. ACC invoices you directly for the earners&rsquo; levy plus a work levy that
depends on your industry.</li>
<li>You must register for GST once your turnover passes $60,000 in any 12 months.</li>
</ul>
<h2>Schedular payment tax rates</h2>
%s
<p class="fine" style="margin-top:.5rem">Source: Inland Revenue form IR330C (January 2024 edition).
Descriptions are abbreviated; schedule 4 of the Income Tax Act 2007 has the full wording.</p>
<h2>Picking a rate</h2>
<p>The right rate is roughly your year&rsquo;s income tax divided by your gross contract income. The
calculator shows it as &ldquo;rate that would cover your tax&rdquo;. Choosing a rate below that leaves a
bill at year end; if that bill is over $5,000 you will also have to pay provisional tax the following year.</p>""" % (
        calc([inp("inc", "Contract income (per year)", 90000, "1000"),
              inp("exp", "Business expenses", 10000, "500"),
              inp("wt", "Withholding rate %", 20, "0.5")],
             "Assumes this is your only income. Uses %s income tax rates; the ACC figure is the earners&rsquo; "
             "levy only (%s up to %s) and excludes the work levy." % (g.YEAR, fp(C["acc_rate"], 2), fm0(C["acc_cap"]))),
        table(["#", "Activity", "Standard rate", "No-notification"], rows))
    faqs = [
        ("What is the withholding tax rate for contractors in NZ?",
         "It depends on the activity: standard rates run from 10.5% to 33%, with 20% the most common "
         "(labour-only building work, labour hire, cleaning, entertainers). You may choose a different rate "
         "of 10% or more on your IR330C."),
        ("What happens if I do not fill in an IR330C?",
         "The payer must deduct tax at the 45% no-notification rate (20% for non-resident contractor companies)."),
        ("Do contractors pay ACC?",
         "Yes, but not through withholding. ACC sends an invoice each year for the earners&rsquo; levy, a work "
         "levy based on your industry, and a small working safer levy."),
        ("Do contractors get holiday pay or KiwiSaver from the payer?",
         "No. Contractors are not employees, so there is no paid leave or compulsory employer KiwiSaver. "
         "Your rate needs to cover those."),
    ]
    page(g, "/contractor-tax/",
         title="Contractor Tax NZ %s: Withholding Rates | Count." % g.YEAR,
         desc="NZ contractor withholding tax (schedular payments) for %s: every IR330C activity rate, the "
              "45%% no-notification rate, and a calculator for your year-end tax bill or refund." % g.YEAR,
         h1="Contractor Withholding Tax in NZ (%s)" % g.YEAR,
         sub="Schedular payment rates for every activity, and a calculator to check whether your withholding "
             "rate will cover your tax.",
         body=body, faqs=faqs, js=js, crumb="Contractor tax")


# ── ACC earners' levy ────────────────────────────────────────────────────────

def acc_levy(g):
    C, e = g.C, g.e
    hist = []
    for y in sorted(TAX_YEARS):
        c = TAX_YEARS[y]
        hist.append((y.replace("-", "&ndash;"), fp(c["acc_rate"], 2), fm0(c["acc_cap"]),
                     fm(c["acc_cap"] * c["acc_rate"])))
    rows = [('<a href="/salary/%d/">%s</a>' % (a, fm0(a)), fm(e.acc(a)), fm(e.acc(a) / 52))
            for a in (40000, 60000, 80000, 100000, 150000, 200000)]
    js = """
function run(){
  const s=num('sal'),l=acc(s);
  out([['ACC earners\\u2019 levy per year',fm(l),1],['Per month',fm(l/12)],['Per fortnight',fm(l/26)],['Per week',fm(l/52)],
   ['Income not levied (above the cap)',fm(Math.max(0,s-ACC_CAP))]]);
}"""
    body = """%s
<h2>What the earners&rsquo; levy is</h2>
<p>The ACC earners&rsquo; levy pays for injuries that happen outside work &mdash; at home, on the road or
playing sport. Everyone who earns income from work pays it. For employees it is built into PAYE, so it
does not usually appear as a separate line on a payslip.</p>
<p>For %s the levy is <b>%s of gross earnings, up to %s</b> a year. The most anyone pays is %s. The rate
includes GST. It is set to rise again from 1 April 2027.</p>
<h2>Levy by salary</h2>
%s
<h2>Rate and cap by year</h2>
%s
<h2>Other ACC levies</h2>
<ul class="plain">
<li><b>Work levy:</b> paid by employers and the self-employed, based on industry risk. Employees do not pay it.</li>
<li><b>Working safer levy:</b> a small flat levy paid alongside the work levy.</li>
<li><b>Motor vehicle levy:</b> collected through vehicle licensing (rego) and petrol.</li>
</ul>
<p>Self-employed people and contractors are invoiced by ACC directly &mdash; see
<a href="/contractor-tax/">contractor tax</a>.</p>""" % (
        calc([inp("sal", "Salary (per year)", 80000, "1000")]),
        g.YEAR, fp(C["acc_rate"], 2), fm0(C["acc_cap"]), fm(C["acc_cap"] * C["acc_rate"]),
        table(["Salary", "Levy / year", "Levy / week"], rows),
        table(["Tax year", "Rate (incl. GST)", "Earnings cap", "Maximum levy"], hist))
    faqs = [
        ("What is the ACC earners' levy rate for %s?" % g.YEAR,
         "%s of gross earnings (GST inclusive), charged on income up to %s." % (fp(C["acc_rate"], 2), fm0(C["acc_cap"]))),
        ("Is the ACC levy included in PAYE?",
         "Yes. The PAYE your employer deducts is income tax plus the ACC earners&rsquo; levy."),
        ("What is the maximum ACC earners' levy?",
         "%s for %s, which is %s of the %s cap." % (fm(C["acc_cap"] * C["acc_rate"]), g.YEAR,
                                                  fp(C["acc_rate"], 2), fm0(C["acc_cap"]))),
        ("Is ACC charged on redundancy pay?",
         "No. Redundancy payments and retiring allowances are not liable for the earners&rsquo; levy."),
    ]
    page(g, "/acc-levy/",
         title="ACC Earners&rsquo; Levy %s: %s Rate &amp; Calculator | Count." % (g.YEAR, fp(C["acc_rate"], 2)),
         desc="The ACC earners&rsquo; levy for %s is %s on income up to %s (maximum %s). Calculator, levy by "
              "salary, and rates for previous years." % (g.YEAR, fp(C["acc_rate"], 2), fm0(C["acc_cap"]),
                                                         fm(C["acc_cap"] * C["acc_rate"])),
         h1="ACC Earners&rsquo; Levy Calculator (%s)" % g.YEAR,
         sub="How much ACC comes out of your pay, what it covers, and how the rate has changed.",
         body=body, faqs=faqs, js=js, crumb="ACC levy")


# ── NZ vs Australia ──────────────────────────────────────────────────────────

def nz_vs_au(g):
    C, e = g.C, g.e
    rows = []
    for a in (60000, 80000, 100000, 120000, 150000, 200000):
        nz = e.breakdown(a)
        au = au_breakdown(a)
        rows.append(("%s" % nf(a, 0), "NZ" + fm0(nz["net"]), fp(1 - nz["net"] / a),
                     "A" + fm0(au["net"]), fp(1 - au["net"] / a)))
    au_br = ",".join("[%s,%s]" % ("Infinity" if l == float("inf") else int(l), r) for l, r in AU_BRACKETS)
    js = """
const AUBR=[""" + au_br + """];
function au(x){let t=0,p=0;for(const[l,r]of AUBR){if(x<=p)break;t+=(Math.min(x,l)-p)*r;p=l}
  const lito=x<=37500?700:x<=45000?700-(x-37500)*.05:x<=66667?325-(x-45000)*.015:0;t=Math.max(0,t-Math.max(0,lito));
  const med=x<=""" + str(AU_MEDICARE_LOW) + """?0:x<=""" + str(AU_MEDICARE_HIGH) + """?(x-""" + str(AU_MEDICARE_LOW) + """)*.1:x*""" + repr(AU_MEDICARE) + """;
  return{tax:t,med:med,net:x-t-med}}
const fa=v=>'A'+fm(v),fn=v=>'NZ'+fm(v);
function run(){
  const n=num('nz'),a=num('au'),fx=num('fx'),ks=$('ks').checked?n*0.035:0;
  const nzNet=n-paye(n)-acc(n)-ks,A=au(a);
  const rows=[['NZ: PAYE + ACC'+(ks?' + KiwiSaver':''),fn(n-nzNet)],['NZ take-home / year',fn(nzNet),1],['NZ take-home / week',fn(nzNet/52)],
   ['Australia: income tax + Medicare levy',fa(A.tax+A.med)],['Australia take-home / year',fa(A.net),1],['Australia take-home / week',fa(A.net/52)],
   ['Employer super on top (""" + nf(AU_SUPER * 100, 0) + """%)',fa(a*""" + repr(AU_SUPER) + """)]];
  if(fx>0){const conv=A.net*fx;rows.push(['Australia take-home in NZ dollars',fn(conv)]);
    rows.push([conv>=nzNet?'Australia ahead by':'New Zealand ahead by',fn(Math.abs(conv-nzNet))+' / year',1])}
  out(rows);
}"""
    body = """%s
<h2>Same salary, each in local dollars</h2>
%s
<p class="fine" style="margin-top:.5rem">NZ: %s PAYE and ACC, no KiwiSaver. Australia: 2026&ndash;27 resident
rates, low income tax offset and 2%% Medicare levy; no HELP debt or private-health surcharge. Each column
is in its own currency.</p>
<h2>How the two systems differ</h2>
<ul class="plain">
<li><b>Tax-free threshold:</b> Australia taxes nothing on the first A$18,200. New Zealand taxes from the
first dollar at 10.5%%.</li>
<li><b>Brackets:</b> Australia&rsquo;s rates are 15%%, 30%%, 37%% and 45%% (above A$190,000). New Zealand&rsquo;s
are 10.5%%, 17.5%%, 30%%, 33%% and 39%% (above NZ$180,000).</li>
<li><b>Levies:</b> Australia adds a 2%% Medicare levy on all taxable income. New Zealand adds the %s ACC
earners&rsquo; levy, capped at %s of earnings.</li>
<li><b>Retirement saving:</b> Australian employers pay %s%% superannuation <b>on top of</b> salary and nothing
comes out of your pay. In New Zealand, KiwiSaver takes 3.5%% from your pay and your employer adds 3.5%%.</li>
<li><b>Tax year:</b> Australia runs 1 July to 30 June and most people file a return. New Zealand runs
1 April to 31 March and most employees never file.</li>
</ul>
<h2>Moving across the Tasman</h2>
<p>New Zealand citizens can live and work in Australia on a Special Category Visa and are normally
treated as Australian tax residents once settled there, so the resident rates above apply. Pay is only
half the comparison: rent, groceries, transport and the exchange rate decide how far it goes.</p>
<p>If you have a New Zealand student loan, it generally starts to attract interest once you have been
overseas for six months, and repayments are set by your balance instead of your income.</p>""" % (
        calc([inp("nz", "NZ salary (NZ$ per year)", 90000, "1000"),
              inp("au", "Australian salary (A$ per year)", 100000, "1000"),
              inp("fx", "NZ$ per A$1 (optional)", "", "0.01", "e.g. today&rsquo;s rate"),
              chk("ks", "Deduct 3.5% KiwiSaver in NZ", True)],
             "Enter today&rsquo;s exchange rate to compare in NZ dollars; without it each country is shown in "
             "its own currency."),
        table(["Salary", "NZ take-home", "NZ tax", "Australia take-home", "Australia tax"], rows),
        g.YEAR, fp(C["acc_rate"], 2), fm0(C["acc_cap"]), nf(AU_SUPER * 100, 0))
    nz100, au100 = e.breakdown(100000), au_breakdown(100000)
    faqs = [
        ("Do you pay more tax in NZ or Australia?",
         "On the same number of dollars, income tax plus levies is %s of a NZ$100,000 salary in New Zealand "
         "and %s of an A$100,000 salary in Australia. Australia is lighter at low incomes because of its "
         "tax-free threshold, and heavier at the top, where its 45%% rate exceeds New Zealand&rsquo;s 39%%."
         % (fp(1 - nz100["net"] / 100000), fp(1 - au100["net"] / 100000))),
        ("What is $100,000 after tax in Australia compared with NZ?",
         "A$100,000 leaves A%s in Australia. NZ$100,000 leaves NZ%s in New Zealand before KiwiSaver."
         % (fm0(au100["net"]), fm0(nz100["net"]))),
        ("Is superannuation deducted from my pay in Australia?",
         "No. The %s%% super guarantee is paid by your employer on top of your salary. Check whether a quoted "
         "package is &ldquo;plus super&rdquo; or &ldquo;including super&rdquo;." % nf(AU_SUPER * 100, 0)),
        ("Do New Zealanders pay the Medicare levy in Australia?",
         "Yes, if they are Australian tax residents. New Zealand citizens living in Australia are generally "
         "eligible for Medicare and pay the 2% levy."),
    ]
    page(g, "/nz-vs-australia/",
         title="NZ vs Australia Take-Home Pay Calculator %s | Count." % g.YEAR,
         desc="Compare take-home pay in New Zealand and Australia for %s. NZ PAYE and ACC against Australian "
              "income tax and Medicare levy, with super and KiwiSaver explained." % g.YEAR,
         h1="NZ vs Australia: Take-Home Pay Compared (%s)" % g.YEAR,
         sub="Thinking about a move across the ditch? Compare what a salary in each country leaves you after tax.",
         body=body, faqs=faqs, js=js, crumb="NZ vs Australia")


# ── Tax rates archive ────────────────────────────────────────────────────────

def _yl(y):
    return y.replace("-", "\u2013")


def tax_year_page(g, y):
    c = TAX_YEARS[y]
    en = Engine(y)
    yl = _yl(y)
    start = int(y[:4])
    current = y == CURRENT_YEAR
    rows, cum = [], 0.0
    for lo, hi, rate in bands(c):
        if hi == float("inf"):
            rows.append((band_label(lo, hi), fp(rate, 2 if (rate * 1000) % 1 else 1), "&mdash;", "&mdash;"))
        else:
            t = (hi - lo) * rate
            cum += t
            rows.append((band_label(lo, hi), fp(rate, 2 if round(rate * 10000) % 10 else 1), fm(t), fm(cum)))
    ksd = c["kiwisaver_default"]
    ksl = "%s%%" % nf(ksd, 1 if ksd % 1 else 0)
    ded = [("ACC earners&rsquo; levy", "%s on earnings up to %s" % (fp(c["acc_rate"], 2), fm0(c["acc_cap"]))),
           ("KiwiSaver minimum (employee)", ksl),
           ("Student loan repayment", "%s of income over %s" % (fp(c["sl_rate"], 0), fm0(c["sl_threshold"]))),
           ("Adult minimum wage", "$%s an hour" % nf(c["min_wage"]))]
    th = []
    for a in (30000, 40000, 50000, 60000, 70000, 80000, 100000, 120000, 150000, 200000):
        b = en.breakdown(a)
        k = en.breakdown(a, kiwisaver_pct=ksd)
        label = '<a href="/salary/%d/">%s</a>' % (a, fm0(a)) if current else fm0(a)
        th.append((label, fm(b["paye"]), fm(b["acc"]), fm(b["net"]), fm(k["net"] / 52)))
    note = ""
    if len(c["brackets"]) > 5:
        note = ('<div class="callout"><b>Composite year.</b> The bracket thresholds moved on 31 July 2024, part-way '
                "through the tax year. For the full year Inland Revenue applies blended rates, which is why "
                "this table has extra bands with rates such as 12.82% and 21.64%.</div>")
    others = "".join('<a href="/tax-rates/%s/">%s</a>' % (o, _yl(o)) for o in sorted(TAX_YEARS, reverse=True) if o != y)
    body = """<h1>NZ Income Tax Rates {yl}</h1>
<p class="sub">Income tax brackets, ACC levy, KiwiSaver, student loan and minimum wage settings for the
tax year 1 April {s} to 31 March {e}{cur}.</p>
<h2>Income tax brackets</h2>
{note}
{brackets}
<p>Each rate applies only to the income inside its band. Someone earning $60,000 pays the lower rates on
the first part of their income and the higher rate only on the top slice.</p>
<h2>Other deductions and thresholds</h2>
{ded}
<h2>Tax and take-home pay by salary</h2>
{th}
<p class="fine" style="margin-top:.5rem">Tax code M. Weekly take-home includes {ksl} KiwiSaver, the minimum
for the year.</p>
{cta}
<h2>Other tax years</h2>
<div class="linkgrid">{others}<a href="/tax-rates/">All years</a></div>
<p class="fine">Bracket rates from Inland Revenue; ACC levy rates include GST. General information, not tax advice.</p>""".format(
        yl=yl, s=start, e=start + 1,
        cur=" &mdash; the current tax year" if current else "",
        note=note,
        brackets=table(["Taxable income", "Rate", "Tax on this band", "Cumulative tax"], rows),
        ded=table(["Setting", yl], ded),
        th=table(["Salary", "Income tax", "ACC levy", "Take-home / year", "Take-home / week"], th),
        ksl=ksl,
        cta='<p><a class="cta" href="/">Calculate your own take-home pay &rarr;</a></p>' if current else
            '<p><a class="cta" href="/tax-rates/%s/">See current %s rates &rarr;</a></p>' % (CURRENT_YEAR, _yl(CURRENT_YEAR)),
        others=others)
    top = c["brackets"][-2][0]
    faqs = [
        ("What are the NZ income tax rates for %s?" % yl,
         "; ".join("%s on %s" % (fp(r, 2 if round(r * 10000) % 10 else 1), g.plain(band_label(lo, hi)).lower()
                                 if hi == float("inf") else g.plain(band_label(lo, hi)))
                   for lo, hi, r in bands(c)) + "."),
        ("When does the %s tax year start and end?" % yl,
         "It runs from 1 April %d to 31 March %d." % (start, start + 1)),
        ("What is the top tax rate in New Zealand?",
         "39%%, on income over %s." % fm0(top)),
        ("What was the ACC earners' levy in %s?" % yl,
         "%s of earnings up to %s." % (fp(c["acc_rate"], 2), fm0(c["acc_cap"]))),
    ]
    path = "/tax-rates/%s/" % y
    html_body = body + "\n<h2>FAQs</h2>\n" + g.faq_block(faqs)
    g.emit(path, g.shell(
        title="NZ Tax Rates %s: Income Tax Brackets | Count." % yl,
        description="New Zealand income tax brackets for %s (1 April %d to 31 March %d), plus the ACC levy, "
                    "KiwiSaver minimum, student loan threshold, minimum wage and take-home pay by salary."
                    % (yl, start, start + 1),
        canonical=g.SITE + path,
        crumbs=[("Count.", "/"), ("Tax rates", "/tax-rates/"), (yl, None)],
        jsonld=[g.faq_ld(faqs), g.breadcrumb_ld([("Home", "/"), ("Tax rates", "/tax-rates/"), (yl, path)])],
        body=html_body), "0.7")


def tax_rates_hub(g):
    years = sorted(TAX_YEARS, reverse=True)
    C = g.C
    rows = []
    for y in years:
        c = TAX_YEARS[y]
        ksd = c["kiwisaver_default"]
        rows.append(('<a href="/tax-rates/%s/">%s</a>' % (y, _yl(y)),
                     "%s &ndash; %s" % (fp(c["brackets"][0][1]), fp(c["brackets"][-1][1], 0)),
                     "%s to %s" % (fp(c["acc_rate"], 2), fm0(c["acc_cap"])),
                     "%s%%" % nf(ksd, 1 if ksd % 1 else 0), fm0(c["sl_threshold"]), "$%s" % nf(c["min_wage"])))
    cur = [(band_label(lo, hi), fp(rate)) for lo, hi, rate in bands(C)]
    body = """<h2>Current rates: %s</h2>
%s
<p><a class="cta" href="/tax-rates/%s/">Full %s rates and take-home table &rarr;</a></p>
<h2>All tax years</h2>
%s
<h2>What changed recently</h2>
<ul class="plain">
<li><b>1 April 2026:</b> KiwiSaver minimum rose from 3%% to 3.5%% for employees and employers; ACC earners&rsquo;
levy rose to %s; adult minimum wage rose to $%s.</li>
<li><b>1 April 2025:</b> first full year of the new bracket thresholds ($15,600, $53,500, $78,100).</li>
<li><b>31 July 2024:</b> bracket thresholds were lifted part-way through the 2024&ndash;25 year, creating a
one-off composite year with blended rates.</li>
</ul>
<p>New Zealand&rsquo;s tax year runs from 1 April to 31 March. Rates are normally confirmed in the Budget
each May and ACC, KiwiSaver and minimum wage settings change on 1 April.</p>""" % (
        g.YEAR, table(["Taxable income", "Rate"], cur), CURRENT_YEAR, g.YEAR,
        table(["Tax year", "Income tax", "ACC levy", "KiwiSaver min", "Student loan threshold", "Minimum wage"], rows),
        fp(C["acc_rate"], 2), nf(C["min_wage"]))
    faqs = [
        ("What are the current income tax rates in NZ?",
         "For %s: %s." % (g.YEAR, "; ".join("%s on %s" % (fp(r), g.plain(band_label(lo, hi)))
                                            for lo, hi, r in bands(C)))),
        ("When do NZ tax rates change?",
         "Changes usually take effect on 1 April, the start of the tax year, though the 2024 threshold "
         "changes took effect on 31 July 2024."),
        ("Is there a tax-free threshold in New Zealand?",
         "No. Income is taxed from the first dollar, at 10.5%."),
    ]
    page(g, "/tax-rates/",
         title="NZ Tax Rates %s &amp; Previous Years | Count." % g.YEAR,
         desc="New Zealand income tax brackets for %s and earlier years, with ACC levy, KiwiSaver, student "
              "loan and minimum wage settings side by side." % g.YEAR,
         h1="NZ Income Tax Rates by Year",
         sub="Income tax brackets and payroll settings for the current and previous tax years.",
         body=body, faqs=faqs, crumb="Tax rates", priority="0.8")


def build(g):
    before = len(g._PAGES)
    tax_rates_hub(g)
    for y in sorted(TAX_YEARS, reverse=True):
        tax_year_page(g, y)
    for fn in (secondary, student_loan, kiwisaver, minimum_wage, pay_rise, bonus, contractor,
               acc_levy, nz_vs_au):
        fn(g)
    return len(g._PAGES) - before

# Count.co.nz — NZ PAYE & take-home pay calculator

Source for [count.co.nz](https://count.co.nz): a free New Zealand PAYE calculator plus a few hundred
static pages answering "what is $X after tax" for salaries, hourly rates and weekly, fortnightly and
monthly pay, and calculators for secondary tax, student loans, KiwiSaver, pay rises, bonuses,
contractors, the ACC levy and NZ vs Australia.

Hosted on GitHub Pages from `main`. No build step on the server: generated pages are committed.

## Current rates (2026–27 tax year)

| Income | Rate |
| --- | --- |
| $0 – $15,600 | 10.5% |
| $15,601 – $53,500 | 17.5% |
| $53,501 – $78,100 | 30% |
| $78,101 – $180,000 | 33% |
| Over $180,000 | 39% |

ACC earners' levy 1.75% (to $156,641) · KiwiSaver minimum 3.5% · student loan 12% over $24,128 ·
adult minimum wage $23.95. Previous years: [count.co.nz/tax-rates](https://count.co.nz/tax-rates/).

## Layout

| Path | What |
| --- | --- |
| `index.html` | The calculator (single file, vanilla JS + Chart.js). Its tax constants are the source of truth. |
| `tools/engine.py` | Python tax engine; parses the constants out of `index.html`. Past years are literals here. |
| `tools/generate.py` | Builds `/salary/`, `/hourly/`, `/weekly/`, `/fortnightly/`, `/monthly/` pages, hubs and `sitemap.xml`. |
| `tools/topics.py` | Topic calculators and the `/tax-rates/` archive. Non-engine facts and their sources are at the top. |
| `data/income-percentiles.json` | IRD wage and salary distribution (year to March 2026), for the "how does it compare" block. |
| `tools/og.html` | Source for the social share image `images/og.png`. |

## Working on it

```sh
python3 -m http.server 8090          # preview at http://127.0.0.1:8090
python3 tools/test_engine.py         # engine vs the calculator's real JavaScript
python3 tools/generate.py            # rebuild every generated page + sitemap
python3 tools/validate_pages.py      # figures, head tags, JSON-LD, internal links
python3 tools/indexnow.py            # after deploy: notify Bing of changed URLs
```

Each April: update the constants in `index.html` and its static copy, add the old year to
`TAX_YEARS` in `tools/engine.py`, review the facts at the top of `tools/topics.py`, refresh
`data/income-percentiles.json` when IRD publishes a new year, update `tools/og.html`, then regenerate.

## License

MIT — see [LICENSE](LICENSE). General information only, not tax advice; rates from
[Inland Revenue](https://www.ird.govt.nz), ACC and MBIE.

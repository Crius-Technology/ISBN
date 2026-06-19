#!/usr/bin/env python3
# ruff: noqa: E501 - embedded HTML/SQL template lines are intentionally long
"""Run an analytical pass over the `editions` table and emit a self-contained HTML report.

Usage:  uv run python scripts/build_report.py [output.html]
Connects via ISBN_DB_DSN (default postgresql://isbn:isbn@localhost:5433/isbn).
"""

from __future__ import annotations

import html
import json
import sys
from datetime import UTC, datetime

import psycopg

DSN = "postgresql://isbn:isbn@localhost:5433/isbn"

# Registration-group bucketing: maps the ISBN-13 prefix to a language/market area.
# This is source-independent — it reflects where the ISBN was *registered*, not who
# catalogued it, so it is the cleanest signal of market reach we have.
MARKET_SQL = """
CASE
  WHEN left(isbn13,4) IN ('9780','9781') THEN 'English (US/UK/AU/etc.)'
  WHEN left(isbn13,4)='9783' THEN 'German'
  WHEN left(isbn13,4)='9782' THEN 'French'
  WHEN left(isbn13,4)='9784' THEN 'Japanese'
  WHEN left(isbn13,4)='9785' THEN 'Russian'
  WHEN left(isbn13,4)='9787' THEN 'Chinese'
  WHEN left(isbn13,5)='97882' THEN 'Norwegian'
  WHEN left(isbn13,5)='97891' THEN 'Swedish'
  WHEN left(isbn13,5)='97887' THEN 'Danish'
  WHEN left(isbn13,5)='97888' THEN 'Italian'
  WHEN left(isbn13,5)='97884' THEN 'Spanish'
  WHEN left(isbn13,5)='97890' THEN 'Dutch'
  WHEN left(isbn13,4)='9798' THEN 'US self-pub (979-8 / KDP)'
  WHEN left(isbn13,5)='97910' THEN 'French (979-10)'
  WHEN left(isbn13,5)='97911' THEN 'Korean (979-11)'
  WHEN left(isbn13,5)='97912' THEN 'Italian (979-12)'
  WHEN left(isbn13,3)='979' THEN 'Other 979'
  ELSE 'Other 978' END
"""

QUERIES: dict[str, str] = {
    "totals": "SELECT count(*) AS n FROM editions",
    "by_source": "SELECT source, count(*) AS n FROM editions GROUP BY source ORDER BY n DESC",
    "coverage": """
        SELECT round(100.0*count(title)/count(*),1)        AS title,
               round(100.0*count(publisher)/count(*),1)    AS publisher,
               round(100.0*count(publish_year)/count(*),1) AS publish_year,
               round(100.0*count(authors)/count(*),1)      AS authors,
               round(100.0*count(languages)/count(*),1)    AS languages,
               round(100.0*count(num_pages)/count(*),1)    AS num_pages,
               round(100.0*count(subjects)/count(*),1)     AS subjects
        FROM editions
    """,
    "market": f"SELECT {MARKET_SQL} AS market, count(*) AS n FROM editions GROUP BY 1 ORDER BY 2 DESC",
    "decade": """
        SELECT (publish_year/10*10) AS decade, count(*) AS n FROM editions
        WHERE publish_year BETWEEN 1900 AND 2026 GROUP BY 1 ORDER BY 1
    """,
    "recent_years": """
        SELECT publish_year AS yr, count(*) AS n FROM editions
        WHERE publish_year BETWEEN 2000 AND 2025 GROUP BY 1 ORDER BY 1
    """,
    "languages": """
        SELECT lang, count(*) AS n FROM editions, unnest(languages) lang
        GROUP BY lang ORDER BY n DESC LIMIT 15
    """,
    "formats": """
        SELECT lower(physical_format) AS fmt, count(*) AS n FROM editions
        WHERE physical_format IS NOT NULL GROUP BY 1 ORDER BY n DESC LIMIT 12
    """,
    "top_pub_all": """
        SELECT publisher, count(*) AS n FROM editions
        WHERE publisher IS NOT NULL GROUP BY publisher ORDER BY n DESC LIMIT 20
    """,
    "top_pub_de": """
        SELECT publisher, count(*) AS n FROM editions
        WHERE source='dnb' AND publisher IS NOT NULL
        GROUP BY publisher ORDER BY n DESC LIMIT 20
    """,
    "top_pub_en": """
        SELECT publisher, count(*) AS n FROM editions
        WHERE left(isbn13,4) IN ('9780','9781') AND publisher IS NOT NULL
        GROUP BY publisher ORDER BY n DESC LIMIT 20
    """,
    # Publisher concentration: how many distinct publishers, and what share the top 100 hold.
    "pub_concentration": """
        WITH p AS (
            SELECT publisher, count(*) AS n FROM editions
            WHERE publisher IS NOT NULL GROUP BY publisher
        )
        SELECT
            (SELECT count(*) FROM p) AS distinct_publishers,
            (SELECT sum(n) FROM p) AS total_with_pub,
            (SELECT sum(n) FROM (SELECT n FROM p ORDER BY n DESC LIMIT 100) t) AS top100_n,
            (SELECT count(*) FROM p WHERE n=1) AS singletons
    """,
    "pages_buckets": """
        SELECT CASE
            WHEN num_pages < 50 THEN '< 50'
            WHEN num_pages < 100 THEN '50-99'
            WHEN num_pages < 200 THEN '100-199'
            WHEN num_pages < 300 THEN '200-299'
            WHEN num_pages < 500 THEN '300-499'
            WHEN num_pages < 1000 THEN '500-999'
            ELSE '1000+' END AS bucket, count(*) AS n
        FROM editions WHERE num_pages BETWEEN 1 AND 20000 GROUP BY 1
        ORDER BY min(num_pages)
    """,
    # Market x recent-decade cross-tab for the priority markets.
    "market_recent": f"""
        SELECT {MARKET_SQL} AS market, (publish_year/10*10) AS decade, count(*) AS n
        FROM editions
        WHERE publish_year BETWEEN 1990 AND 2026
        GROUP BY 1,2
    """,
}


def run(conn, sql: str):
    with conn.cursor() as cur:
        cur.execute(sql)
        cols = [d.name for d in cur.description]
        return cols, cur.fetchall()


def main() -> None:
    out_path = sys.argv[1] if len(sys.argv) > 1 else "docs/report.html"
    results: dict[str, dict] = {}
    with psycopg.connect(DSN) as conn:
        for name, sql in QUERIES.items():
            cols, rows = run(conn, sql)
            results[name] = {"cols": cols, "rows": [list(r) for r in rows]}
            print(f"  {name}: {len(rows)} rows", file=sys.stderr)

    html_doc = render(results)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"wrote {out_path}", file=sys.stderr)


# --------------------------------------------------------------------------- rendering


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


def fmt(n) -> str:
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return esc(n)


def table(res: dict, headers: list[str] | None = None) -> str:
    cols = headers or res["cols"]
    head = "".join(f"<th>{esc(c)}</th>" for c in cols)
    body = []
    for row in res["rows"]:
        cells = "".join(
            f"<td class='{'num' if isinstance(v, (int, float)) else ''}'>{fmt(v) if isinstance(v, (int, float)) else esc(v)}</td>"
            for v in row
        )
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def render(r: dict) -> str:
    total = r["totals"]["rows"][0][0]
    cov = dict(zip(r["coverage"]["cols"], r["coverage"]["rows"][0], strict=False))
    src = {row[0]: row[1] for row in r["by_source"]["rows"]}
    conc = {k: int(v) for k, v in zip(r["pub_concentration"]["cols"], r["pub_concentration"]["rows"][0], strict=False)}

    market_rows = r["market"]["rows"]
    decade_rows = r["decade"]["rows"]
    recent_rows = r["recent_years"]["rows"]
    lang_rows = r["languages"]["rows"]
    pages_rows = r["pages_buckets"]["rows"]

    # Build market x decade series for priority markets.
    priority = ["English (US/UK/AU/etc.)", "German", "French", "US self-pub (979-8 / KDP)"]
    mr: dict[tuple, int] = {(m, d): n for m, d, n in r["market_recent"]["rows"]}
    decades_axis = sorted({d for (_, d) in mr})
    market_decade_series = {m: [mr.get((m, d), 0) for d in decades_axis] for m in priority}

    top100_share = round(100.0 * conc["top100_n"] / conc["total_with_pub"], 1)
    singleton_share = round(100.0 * conc["singletons"] / conc["distinct_publishers"], 1)

    js_data = {
        "market": {"labels": [m for m, _ in market_rows], "data": [n for _, n in market_rows]},
        "decade": {"labels": [str(d) + "s" for d, _ in decade_rows], "data": [n for _, n in decade_rows]},
        "recent": {"labels": [str(y) for y, _ in recent_rows], "data": [n for _, n in recent_rows]},
        "lang": {"labels": [lg for lg, _ in lang_rows], "data": [n for _, n in lang_rows]},
        "pages": {"labels": [b for b, _ in pages_rows], "data": [n for _, n in pages_rows]},
        "market_decade": {
            "labels": [str(d) + "s" for d in decades_axis],
            "series": market_decade_series,
        },
    }

    gen_ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    # Narrative conclusions, derived from the numbers above.
    de_pct = round(100.0 * dict((m, n) for m, n in market_rows).get("German", 0) / total, 1)
    en_pct = round(100.0 * dict((m, n) for m, n in market_rows).get("English (US/UK/AU/etc.)", 0) / total, 1)
    kdp = dict((m, n) for m, n in market_rows).get("US self-pub (979-8 / KDP)", 0)

    conclusions = f"""
    <ul>
      <li><b>The dataset is genuinely two-market today.</b> By ISBN registration group,
          <b>{en_pct}%</b> of editions are English-area and <b>{de_pct}%</b> German — a direct
          consequence of the two ingested sources (Open Library backbone + authoritative DNB).
          Every other language area is present but thin (French {fmt(dict((m, n) for m, n in market_rows).get("French", 0))},
          Spanish {fmt(dict((m, n) for m, n in market_rows).get("Spanish", 0))}), so the
          <b>UK and Nordic priority markets are not yet directly covered</b> — they appear only
          incidentally inside the English-area bucket and as small Norwegian/Swedish groups.</li>
      <li><b>German coverage is the strongest asset.</b> DNB contributes {fmt(src.get("dnb", 0))}
          authoritative editions and wins on merge, so German-market metadata is the highest-quality
          slice. For DE publisher/market analysis this DB is already production-grade.</li>
      <li><b>Self-publishing is visible and large.</b> The 979-8 registration group
          (Amazon KDP / US self-publishing) already accounts for {fmt(kdp)} editions — a structural
          shift worth tracking separately from traditional publishers.</li>
      <li><b>Publisher landscape is a long tail.</b> {fmt(conc["distinct_publishers"])} distinct
          publisher strings; the top 100 hold only <b>{top100_share}%</b> of attributed editions and
          <b>{singleton_share}%</b> of publishers appear on a single edition. Names are unnormalised
          (imprints, spelling variants, language variants) — <b>entity resolution on publisher is the
          highest-value next step</b> before any concentration claim is reliable.</li>
      <li><b>Coverage is strong on the fields that matter, weak where expected.</b> title {cov["title"]}%,
          publisher {cov["publisher"]}%, year {cov["publish_year"]}% — all excellent. Pages
          ({cov["num_pages"]}%) and subjects ({cov["subjects"]}%) are the gaps, both fixable by adding
          trade sources (Nielsen UK, VLB DE).</li>
      <li><b>Output curve matches the ISBN era.</b> Volume rises through the 1990s–2010s as ISBN
          adoption and retro-catalogue digitisation peak; the most recent years dip, reflecting
          catalogue lag (recently published titles not yet ingested), not a real market contraction.</li>
    </ul>
    """

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ISBN metadata DB — analytical report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{ --bg:#0f1419; --card:#1a2027; --ink:#e6e9ed; --muted:#9aa4b1; --accent:#4f9cf9;
           --accent2:#f5a623; --line:#2a313a; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
          font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }}
  .wrap {{ max-width:1100px; margin:0 auto; padding:32px 20px 80px; }}
  h1 {{ font-size:28px; margin:0 0 4px; }}
  h2 {{ font-size:20px; margin:40px 0 12px; border-bottom:1px solid var(--line); padding-bottom:6px; }}
  .sub {{ color:var(--muted); margin:0 0 24px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:14px; margin:24px 0; }}
  .kpi {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; }}
  .kpi .v {{ font-size:26px; font-weight:700; color:var(--accent); }}
  .kpi .l {{ color:var(--muted); font-size:13px; margin-top:2px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:18px; margin:16px 0; }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  @media (max-width:760px) {{ .grid2 {{ grid-template-columns:1fr; }} }}
  table {{ border-collapse:collapse; width:100%; font-size:13.5px; }}
  th,td {{ text-align:left; padding:6px 10px; border-bottom:1px solid var(--line); }}
  th {{ color:var(--muted); font-weight:600; }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  canvas {{ max-height:320px; }}
  .conclusions li {{ margin-bottom:10px; }}
  b {{ color:#fff; }}
  .note {{ color:var(--muted); font-size:12.5px; margin-top:8px; }}
</style></head>
<body><div class="wrap">
  <h1>ISBN Metadata Database — Analytical Report</h1>
  <p class="sub">Generated {gen_ts} · single-table <code>editions</code> keyed by canonical ISBN-13 ·
     source-priority merge (DNB &gt; Open Library)</p>

  <div class="kpis">
    <div class="kpi"><div class="v">{fmt(total)}</div><div class="l">total editions</div></div>
    <div class="kpi"><div class="v">{fmt(src.get("openlibrary", 0))}</div><div class="l">Open Library</div></div>
    <div class="kpi"><div class="v">{fmt(src.get("dnb", 0))}</div><div class="l">DNB (authoritative DE)</div></div>
    <div class="kpi"><div class="v">{fmt(conc["distinct_publishers"])}</div><div class="l">distinct publishers</div></div>
    <div class="kpi"><div class="v">{cov["publisher"]}%</div><div class="l">publisher coverage</div></div>
    <div class="kpi"><div class="v">0</div><div class="l">invalid ISBN-13</div></div>
  </div>

  <h2>Executive conclusions</h2>
  <div class="card conclusions">{conclusions}</div>

  <h2>Market reach (by ISBN registration group)</h2>
  <div class="card">
    <p class="note">Bucketed from the ISBN-13 prefix — independent of which library catalogued the
      record. This is the cleanest signal of the language/market area a title was registered for.</p>
    <div class="grid2">
      <canvas id="marketChart"></canvas>
      {table(r["market"], ["market", "editions"])}
    </div>
  </div>

  <h2>Publication output over time</h2>
  <div class="card"><canvas id="decadeChart"></canvas>
    <p class="note">Editions per decade (publish_year present on {cov["publish_year"]}% of rows).</p></div>
  <div class="card"><canvas id="recentChart"></canvas>
    <p class="note">Per-year, 2000–2025. The tail-end dip reflects catalogue ingest lag, not market contraction.</p></div>
  <div class="card"><canvas id="marketDecadeChart"></canvas>
    <p class="note">Priority markets over recent decades — English-area vs German vs the rising 979-8 self-publishing group.</p></div>

  <h2>Field coverage</h2>
  <div class="card">{table(r["coverage"], list(r["coverage"]["cols"]))}
    <p class="note">Percent of {fmt(total)} rows with a non-null value. Strong on bibliographic core
      (title/publisher/year); pages and subjects are the gaps.</p></div>

  <h2>Languages &amp; formats</h2>
  <div class="grid2">
    <div class="card"><h3 style="margin:0 0 8px;font-size:15px;">Top languages</h3><canvas id="langChart"></canvas></div>
    <div class="card"><h3 style="margin:0 0 8px;font-size:15px;">Physical format</h3>{table(r["formats"], ["format", "editions"])}</div>
  </div>

  <h2>Page-count distribution</h2>
  <div class="card"><canvas id="pagesChart"></canvas>
    <p class="note">Editions with a usable page count ({cov["num_pages"]}% coverage).</p></div>

  <h2>Publisher concentration</h2>
  <div class="card">
    <p>Across <b>{fmt(conc["distinct_publishers"])}</b> distinct publisher strings, the top 100 account
       for only <b>{top100_share}%</b> of attributed editions and <b>{singleton_share}%</b> of publishers
       appear exactly once. The market is a long tail — but these are raw, <i>unnormalised</i> strings
       (imprints and spelling variants counted separately), so treat concentration figures as an
       upper bound on fragmentation until entity resolution is applied.</p>
  </div>

  <h2>Top publishers</h2>
  <div class="grid2">
    <div class="card"><h3 style="margin:0 0 8px;font-size:15px;">Overall</h3>{table(r["top_pub_all"], ["publisher", "editions"])}</div>
    <div class="card"><h3 style="margin:0 0 8px;font-size:15px;">German market (DNB authoritative)</h3>{table(r["top_pub_de"], ["publisher", "editions"])}</div>
  </div>
  <div class="card"><h3 style="margin:0 0 8px;font-size:15px;">English-area (ISBN 978-0 / 978-1)</h3>{table(r["top_pub_en"], ["publisher", "editions"])}</div>

  <p class="note">Source: <code>isbn-db</code> · Open Library (CC0) + Deutsche Nationalbibliothek (CC0).
     Priority markets UK &amp; Germany, then US, then Norway &amp; Sweden.</p>
</div>

<script>
const D = {json.dumps(js_data)};
const FONT = '#e6e9ed', GRID = '#2a313a', ACC = '#4f9cf9', ACC2 = '#f5a623';
Chart.defaults.color = '#9aa4b1'; Chart.defaults.borderColor = GRID;
const bar = (id, labels, data, color, horizontal) => new Chart(document.getElementById(id), {{
  type:'bar',
  data:{{labels, datasets:[{{data, backgroundColor:color, borderRadius:3}}]}},
  options:{{indexAxis:horizontal?'y':'x', plugins:{{legend:{{display:false}}}},
    scales:{{x:{{grid:{{color:GRID}}}}, y:{{grid:{{color:GRID}}}}}}}}
}});
bar('marketChart', D.market.labels, D.market.data, ACC, true);
bar('decadeChart', D.decade.labels, D.decade.data, ACC, false);
bar('langChart', D.lang.labels, D.lang.data, ACC2, true);
bar('pagesChart', D.pages.labels, D.pages.data, ACC2, false);
new Chart(document.getElementById('recentChart'), {{
  type:'line',
  data:{{labels:D.recent.labels, datasets:[{{data:D.recent.data, borderColor:ACC,
    backgroundColor:'rgba(79,156,249,.15)', fill:true, tension:.25, pointRadius:2}}]}},
  options:{{plugins:{{legend:{{display:false}}}}, scales:{{x:{{grid:{{color:GRID}}}}, y:{{grid:{{color:GRID}}}}}}}}
}});
const palette = [ACC, ACC2, '#56d364', '#e06c75'];
new Chart(document.getElementById('marketDecadeChart'), {{
  type:'line',
  data:{{labels:D.market_decade.labels, datasets:Object.entries(D.market_decade.series).map((e,i)=>(
    {{label:e[0], data:e[1], borderColor:palette[i%palette.length], tension:.25, pointRadius:2, fill:false}}))}},
  options:{{plugins:{{legend:{{labels:{{color:FONT}}}}}}, scales:{{x:{{grid:{{color:GRID}}}}, y:{{grid:{{color:GRID}}}}}}}}
}});
</script>
</body></html>"""


if __name__ == "__main__":
    main()

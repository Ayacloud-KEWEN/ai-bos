"""把汇总情报渲染成投行级、可打印为 PDF 的自包含 HTML 报告。"""
from datetime import date
from html import escape


def _fmt(v, cur=""):
    if v is None:
        return "—"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return escape(str(v))
    a = abs(v); sign = "-" if v < 0 else ""
    sym = {"USD": "$", "CNY": "¥", "HKD": "HK$", "EUR": "€", "GBP": "£"}.get(cur, "")
    if a >= 1e12: s = f"{a/1e12:.2f}T"
    elif a >= 1e9: s = f"{a/1e9:.2f}B"
    elif a >= 1e6: s = f"{a/1e6:.2f}M"
    elif a >= 1e3: s = f"{a/1e3:.1f}K"
    else: s = f"{a:.0f}"
    return f"{sign}{sym}{s}"


def _pct(v):
    return "—" if v is None else f"{v:+.1f}%" if isinstance(v, (int, float)) else escape(str(v))


def _ul(items, limit=8):
    items = [i for i in (items or []) if i][:limit]
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{escape(str(i))}</li>" for i in items) + "</ul>"


def _score_pill(label, val, invert=False):
    v = val or 0
    s = 100 - v if invert else v
    color = "#10b981" if s >= 67 else "#f59e0b" if s >= 34 else "#ef4444"
    return (f'<div class="pill"><div class="pill-v" style="color:{color}">{v}</div>'
            f'<div class="pill-l">{escape(label)}</div></div>')


def render_report(intel: dict) -> str:
    c = intel["company"]
    cur = (intel.get("financial") or {}).get("currency", "USD")
    today = date.today().isoformat()
    name = escape(c["name"])

    sections = []

    # 执行简报
    b = intel.get("briefing")
    if b:
        sections.append(f"""
        <section class="brief">
          <h2>Executive Briefing · 执行简报</h2>
          <p class="lead">{escape(b.get('summary') or '')}</p>
          <div class="two">
            <div><h4>What happened</h4><p>{escape(b.get('what_happened') or '')}</p></div>
            <div><h4>Why it matters</h4><p>{escape(b.get('why_it_matters') or '')}</p></div>
          </div>
          <div class="two">
            <div><h4>Recommended actions</h4>{_ul(b.get('recommended_actions'))}</div>
            <div><h4>Next actions</h4>{_ul(b.get('next_actions'))}</div>
          </div>
        </section>""")

    # 财务
    f = intel.get("financial")
    if f:
        sm = f["trend"]["summary"]
        sc = f["scores"]
        rows = ""
        for p in f["trend"]["periods"]:
            rows += (f"<tr><td>{escape(str(p.get('period')))}</td>"
                     f"<td>{_fmt(p.get('revenue'), cur)}</td>"
                     f"<td>{_fmt(p.get('gross_profit'), cur)}</td>"
                     f"<td>{_fmt(p.get('operating_profit'), cur)}</td>"
                     f"<td>{_fmt(p.get('net_profit'), cur)}</td>"
                     f"<td>{_pct(p.get('net_margin'))}</td>"
                     f"<td>{_pct(p.get('revenue_growth'))}</td></tr>")
        sections.append(f"""
        <section>
          <h2>Financial Intelligence · 财务情报</h2>
          <div class="pills">{_score_pill('Health', sc.get('financial_health'))}{_score_pill('Growth', sc.get('growth'))}{_score_pill('Profitability', sc.get('profitability'))}{_score_pill('Liquidity', sc.get('liquidity'))}{_score_pill('Risk', sc.get('risk'), invert=True)}</div>
          <p>Latest revenue <b>{_fmt(sm.get('latest_revenue'), cur)}</b> · YoY {_pct(sm.get('yoy_revenue_growth'))} · CAGR {_pct(sm.get('revenue_cagr'))} · Net margin {_pct(sm.get('latest_net_margin'))}</p>
          <table><thead><tr><th>Period</th><th>Revenue</th><th>Gross</th><th>Operating</th><th>Net</th><th>Net %</th><th>Growth</th></tr></thead><tbody>{rows or '<tr><td colspan=7>No period data</td></tr>'}</tbody></table>
          <div class="two"><div><h4>Key findings</h4>{_ul(f.get('key_findings'))}</div><div><h4>Risks</h4>{_ul(f.get('risks'))}</div></div>
        </section>""")

    # 竞争
    comp = intel.get("competitive")
    if comp:
        sw = comp["swot"]
        crows = "".join(
            f"<tr><td>{escape(str(x.get('name')))}</td><td>{escape(str(x.get('type','')))}</td>"
            f"<td>{escape(', '.join(x.get('strengths') or []))}</td><td>{'●'*int(x.get('threat_level',3))}</td></tr>"
            for x in (comp.get("competitors") or [])[:8]
        )
        sections.append(f"""
        <section>
          <h2>Competitive Intelligence · 竞争情报</h2>
          <p><b>Market position:</b> {escape(comp.get('market_position') or '')} (moat {comp.get('positioning_score')})</p>
          <div class="swot">
            <div class="s"><h4>Strengths</h4>{_ul(sw['strengths'],6)}</div>
            <div class="w"><h4>Weaknesses</h4>{_ul(sw['weaknesses'],6)}</div>
            <div class="o"><h4>Opportunities</h4>{_ul(sw['opportunities'],6)}</div>
            <div class="t"><h4>Threats</h4>{_ul(sw['threats'],6)}</div>
          </div>
          <h4>Competitive matrix</h4>
          <table><thead><tr><th>Competitor</th><th>Type</th><th>Strengths</th><th>Threat</th></tr></thead><tbody>{crows or '<tr><td colspan=4>—</td></tr>'}</tbody></table>
        </section>""")

    # 尽调
    dd = intel.get("due_diligence")
    if dd:
        cats = "".join(
            f"<tr><td>{escape(str(rc.get('label', rc.get('key'))))}</td>"
            f"<td><div class='bar'><div style='width:{int(rc.get('score',0))}%;background:{'#ef4444' if rc.get('score',0)>=67 else '#f59e0b' if rc.get('score',0)>=34 else '#10b981'}'></div></div> {rc.get('score')}</td>"
            f"<td>{escape(str(rc.get('summary') or ''))}</td></tr>"
            for rc in (dd.get("risk_categories") or [])
        )
        sections.append(f"""
        <section>
          <h2>Due Diligence · 尽职调查</h2>
          <p><b>Attractiveness:</b> {dd.get('overall_score')}/100 &nbsp; <b>Recommendation:</b> {escape(dd.get('recommendation') or '')}</p>
          <table><thead><tr><th>Risk</th><th>Level</th><th>Assessment</th></tr></thead><tbody>{cats}</tbody></table>
          <div class="two"><div><h4>Red flags</h4>{_ul(dd.get('red_flags')) or '<p class=muted>None identified.</p>'}</div><div><h4>Opportunities</h4>{_ul(dd.get('opportunities'))}</div></div>
        </section>""")

    # 战略
    st = intel.get("strategy")
    if st:
        opt_rows = "".join(
            f"<tr><td><b>{escape(str(o.get('title')))}</b><br><span class=muted>{escape(str(o.get('description') or ''))}</span></td>"
            f"<td>{'●'*int(o.get('impact',0))}</td><td>{'●'*int(o.get('feasibility',0))}</td>"
            f"<td>{'●'*int(o.get('risk',0))}</td><td>{escape(str(o.get('investment','')))}</td></tr>"
            for o in (st.get("strategic_options") or [])
        )
        recs = "<ol>" + "".join(
            f"<li><b>{escape(str(r.get('title')))}</b>"
            + (f" — {escape(str(r.get('expected_outcome')))}" if r.get('expected_outcome') else "") + "</li>"
            for r in (st.get("recommendations") or [])
        ) + "</ol>" if st.get("recommendations") else ""
        forces = "".join(
            f"<tr><td>{escape(str(p.get('force')))}</td>"
            f"<td><div class='bar'><div style='width:{int(p.get('level',0))}%;background:{'#ef4444' if p.get('level',0)>=67 else '#f59e0b' if p.get('level',0)>=34 else '#10b981'}'></div></div> {p.get('level')}</td>"
            f"<td>{escape(str(p.get('summary') or ''))}</td></tr>"
            for p in (st.get("porters_five_forces") or [])
        )
        sections.append(f"""
        <section>
          <h2>Strategy · 战略情报</h2>
          <p>{escape(st.get('executive_summary') or '')}</p>
          <h4>Strategic options (impact / feasibility / risk)</h4>
          <table><thead><tr><th>Option</th><th>Impact</th><th>Feasibility</th><th>Risk</th><th>Investment</th></tr></thead><tbody>{opt_rows or '<tr><td colspan=5>—</td></tr>'}</tbody></table>
          <div class="two"><div><h4>Prioritized recommendations</h4>{recs}</div><div><h4>Growth opportunities</h4>{_ul(st.get('growth_opportunities'))}</div></div>
          <h4>Porter's Five Forces</h4>
          <table><thead><tr><th>Force</th><th>Intensity</th><th>Assessment</th></tr></thead><tbody>{forces}</tbody></table>
        </section>""")

    # 销售
    sa = intel.get("sales")
    if sa:
        icp = "".join(f"<tr><td><b>{escape(str(x.get('segment')))}</b></td><td>{escape(str(x.get('description') or ''))}</td><td>{escape(str(x.get('why_fit') or ''))}</td></tr>" for x in (sa.get("icp") or []))
        personas = "".join(f"<li><b>{escape(str(p.get('role')))}</b>: 目标 {escape(', '.join(p.get('goals') or []))}; 痛点 {escape(', '.join(p.get('pain_points') or []))}</li>" for p in (sa.get("buyer_personas") or []))
        sections.append(f"""
        <section>
          <h2>Sales Intelligence · 销售情报</h2>
          <p>{escape(sa.get('executive_summary') or '')}</p>
          <h4>Ideal Customer Profiles</h4>
          <table><thead><tr><th>Segment</th><th>Description</th><th>Why fit</th></tr></thead><tbody>{icp or '<tr><td colspan=3>—</td></tr>'}</tbody></table>
          <h4>Buyer personas</h4><ul>{personas}</ul>
          <div class="two"><div><h4>Pain points</h4>{_ul(sa.get('pain_points'))}</div><div><h4>Buying triggers</h4>{_ul(sa.get('buying_triggers'))}</div></div>
          <h4>Sales opportunities</h4>{_ul(sa.get('sales_opportunities'))}
        </section>""")

    # 市场
    mk = intel.get("market")
    if mk:
        seg = "".join(f"<li><b>{escape(str(s.get('name')))}</b>: {escape(str(s.get('description') or ''))}</li>" for s in (mk.get("segments") or []))
        sections.append(f"""
        <section>
          <h2>Market Research · 市场情报</h2>
          <p>{escape(mk.get('executive_summary') or '')}</p>
          <table><tbody>
            <tr><th>TAM</th><td>{escape(str(mk.get('tam') or '—'))}</td></tr>
            <tr><th>SAM</th><td>{escape(str(mk.get('sam') or '—'))}</td></tr>
            <tr><th>SOM</th><td>{escape(str(mk.get('som') or '—'))}</td></tr>
            <tr><th>Growth</th><td>{escape(str(mk.get('market_growth') or '—'))}</td></tr>
          </tbody></table>
          <div class="two"><div><h4>Trends</h4>{_ul(mk.get('trends'))}</div><div><h4>Drivers</h4>{_ul(mk.get('drivers'))}</div></div>
          <div class="two"><div><h4>Barriers</h4>{_ul(mk.get('barriers'))}</div><div><h4>Segments</h4><ul>{seg}</ul></div></div>
        </section>""")

    body = "\n".join(sections) or "<p class=muted>No analysis available yet.</p>"

    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>{name} — Intelligence Report</title>
<style>
:root{{--ink:#1e293b;--mut:#64748b;--line:#e2e8f0;--brand:#4f46e5}}
*{{box-sizing:border-box}}
body{{font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;color:var(--ink);margin:0;background:#f1f5f9}}
.page{{max-width:860px;margin:0 auto;background:#fff;padding:48px 56px}}
.toolbar{{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line);padding:10px 56px;display:flex;justify-content:space-between;align-items:center}}
.toolbar button{{background:var(--brand);color:#fff;border:0;border-radius:8px;padding:8px 16px;font-size:14px;cursor:pointer}}
.cover{{border-bottom:3px solid var(--brand);padding-bottom:20px;margin-bottom:8px}}
.cover h1{{font-size:30px;margin:0 0 6px}}
.cover .meta{{color:var(--mut);font-size:14px}}
.cover .score{{float:right;text-align:center;background:#eef2ff;border-radius:12px;padding:10px 18px}}
.cover .score b{{font-size:30px;color:var(--brand);display:block}}
section{{margin:26px 0;page-break-inside:avoid}}
h2{{font-size:19px;border-left:4px solid var(--brand);padding-left:10px;margin:0 0 12px}}
h4{{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);margin:14px 0 6px}}
p{{font-size:14px;line-height:1.6;margin:6px 0}}
.lead{{font-size:16px;font-weight:600}}
ul{{margin:4px 0;padding-left:18px}}li{{font-size:13.5px;line-height:1.55;margin:3px 0}}
.two{{display:flex;gap:24px}}.two>div{{flex:1}}
.pills{{display:flex;gap:10px;margin:10px 0}}
.pill{{flex:1;text-align:center;border:1px solid var(--line);border-radius:10px;padding:10px}}
.pill-v{{font-size:24px;font-weight:800}}.pill-l{{font-size:11px;color:var(--mut)}}
table{{width:100%;border-collapse:collapse;font-size:12.5px;margin:8px 0}}
th,td{{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#f8fafc;font-size:11px;text-transform:uppercase;color:var(--mut)}}
.swot{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px}}
.swot>div{{border:1px solid var(--line);border-radius:10px;padding:6px 12px}}
.swot .s{{background:#ecfdf5}}.swot .w{{background:#fef2f2}}.swot .o{{background:#eff6ff}}.swot .t{{background:#fffbeb}}
.bar{{display:inline-block;width:80px;height:7px;background:#eee;border-radius:4px;overflow:hidden;vertical-align:middle}}.bar>div{{height:100%}}
.muted{{color:var(--mut)}}
footer{{margin-top:32px;border-top:1px solid var(--line);padding-top:12px;color:var(--mut);font-size:11px}}
@media print{{.toolbar{{display:none}}body{{background:#fff}}.page{{padding:0}}@page{{margin:18mm}}}}
</style></head>
<body>
<div class="toolbar"><span style="font-size:13px;color:var(--mut)">AI-BOS Intelligence Report</span>
<button onclick="window.print()">🖨 Print / Save as PDF</button></div>
<div class="page">
  <div class="cover">
    <div class="score"><span style="font-size:11px;color:var(--mut)">Intelligence</span><b>{c.get('intelligence_score')}</b></div>
    <h1>{name}</h1>
    <div class="meta">{escape(c.get('industry') or '')} · {escape(c.get('sector') or '')} · {escape(c.get('location') or '')} &nbsp;|&nbsp; {today}</div>
  </div>
  {body}
  <footer>Generated by AI-BOS · {today} · Confidential. Figures may be AI-extracted; verify against primary sources before decisions.</footer>
</div>
</body></html>"""

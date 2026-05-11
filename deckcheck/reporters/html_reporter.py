"""HTML reporter —— 互動式 finding browser，可篩選 severity / checker / deck。"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from ..model import Finding, aggregate_by_severity, aggregate_by_checker, aggregate_by_deck


def write(findings: list[Finding], out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    sev = aggregate_by_severity(findings)
    chk = aggregate_by_checker(findings)
    by_deck = aggregate_by_deck(findings)

    payload = json.dumps([f.to_dict() for f in findings], ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="zh-TW"><head><meta charset="UTF-8">
<title>Deckcheck Report · {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif;background:#f7f6f1;color:#1a1a1a;padding:2rem;line-height:1.5}}
.h{{font-family:Georgia,serif;font-size:32px;font-weight:700;margin-bottom:.4rem}}
.sub{{opacity:.6;font-size:13px;letter-spacing:.1em;text-transform:uppercase;margin-bottom:2rem}}
.summary{{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:2rem}}
.card{{padding:1.2rem;background:white;border-radius:8px;border-left:4px solid var(--c)}}
.card.blocker{{--c:#c0392b}}
.card.error{{--c:#e67e22}}
.card.warn{{--c:#f39c12}}
.card.info{{--c:#3498db}}
.n{{font-size:32px;font-weight:700;font-family:"Helvetica Neue"}}
.l{{font-size:11px;letter-spacing:.16em;text-transform:uppercase;opacity:.6;margin-top:.2rem}}
.controls{{display:flex;gap:.6rem;flex-wrap:wrap;margin-bottom:1rem}}
.controls input,.controls select{{padding:.4rem .8rem;border:1px solid #ccc;border-radius:4px;font-size:13px}}
.controls input{{flex:1;min-width:200px}}
table{{width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden}}
th,td{{padding:.6rem .8rem;text-align:left;border-bottom:1px solid #eee;font-size:13px;vertical-align:top}}
th{{background:#fafafa;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.08em;opacity:.7}}
tr:hover{{background:#fafafa}}
.sev{{display:inline-block;padding:2px 8px;border-radius:99px;font-size:10px;font-weight:700;letter-spacing:.05em}}
.sev.BLOCKER{{background:#fde0dc;color:#c0392b}}
.sev.ERROR{{background:#fdebd0;color:#a04000}}
.sev.WARN{{background:#fef5e7;color:#7d6608}}
.sev.INFO{{background:#d6eaf8;color:#1f618d}}
.code{{font-family:"SF Mono",Menlo,monospace;font-size:11px;background:#f4f4f4;padding:1px 6px;border-radius:3px}}
.deck{{font-family:"SF Mono",Menlo,monospace;font-size:11px;opacity:.7}}
footer{{margin-top:2rem;font-size:11px;opacity:.5;text-align:center}}
</style></head><body>
<div class="h">Deckcheck Report</div>
<div class="sub">Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · {len(findings)} findings · {len(by_deck)} decks</div>

<div class="summary">
  <div class="card blocker"><div class="n">{sev['BLOCKER']}</div><div class="l">BLOCKER</div></div>
  <div class="card error"><div class="n">{sev['ERROR']}</div><div class="l">ERROR</div></div>
  <div class="card warn"><div class="n">{sev['WARN']}</div><div class="l">WARN</div></div>
  <div class="card info"><div class="n">{sev['INFO']}</div><div class="l">INFO</div></div>
</div>

<div class="controls">
  <input type="search" id="q" placeholder="搜尋 deck / message / code...">
  <select id="sev">
    <option value="">全部嚴重度</option>
    <option value="BLOCKER">BLOCKER</option>
    <option value="ERROR">ERROR</option>
    <option value="WARN">WARN</option>
    <option value="INFO">INFO</option>
  </select>
  <select id="chk">
    <option value="">全部 checker</option>
{"".join(f'<option value="{c}">{c}</option>' for c in sorted(chk))}
  </select>
</div>

<table id="t">
  <thead><tr><th>Sev</th><th>Code</th><th>Deck</th><th>p</th><th>Message</th><th>Checker</th></tr></thead>
  <tbody></tbody>
</table>

<footer>Deckcheck v0.1 · 弄一下工作室</footer>

<script>
const data = {payload};
const tbody = document.querySelector('#t tbody');
const q = document.querySelector('#q');
const sev = document.querySelector('#sev');
const chk = document.querySelector('#chk');
function render(){{
  const ql = q.value.toLowerCase();
  const sl = sev.value, cl = chk.value;
  const rows = data.filter(f =>
    (!sl || f.severity === sl) &&
    (!cl || f.checker === cl) &&
    (!ql || (f.deck_id+f.message+f.code+(f.selector||'')).toLowerCase().includes(ql))
  ).sort((a,b)=>{{
    const r={{BLOCKER:4,ERROR:3,WARN:2,INFO:1}};
    return r[b.severity]-r[a.severity] || a.deck_id.localeCompare(b.deck_id) || (a.slide||0)-(b.slide||0);
  }}).slice(0, 1000);
  tbody.innerHTML = rows.map(f =>
    `<tr><td><span class="sev ${{f.severity}}">${{f.severity}}</span></td>` +
    `<td><span class="code">${{f.code}}</span></td>` +
    `<td><span class="deck">${{f.deck_id}}</span></td>` +
    `<td>${{f.slide ?? '—'}}</td>` +
    `<td>${{f.message}}</td>` +
    `<td><span class="code">${{f.checker}}</span></td></tr>`
  ).join('');
}}
[q, sev, chk].forEach(el => el.addEventListener('input', render));
render();
</script>
</body></html>
"""
    out.write_text(html, encoding="utf-8")
    print(f"  → HTML written: {out}")

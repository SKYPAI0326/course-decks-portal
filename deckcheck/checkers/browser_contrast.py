"""browser_contrast —— Playwright + WCAG 對比度。

主動觸發 Motion One 動畫（強制 opacity:1 + transform:none）後測對比，
避免動畫中段誤判。
"""
from __future__ import annotations
from pathlib import Path
from ..model import Finding, derive_deck_id


CONTRAST_SCRIPT = r"""
async (threshold) => {
  document.querySelectorAll('[data-anim], [data-animate]').forEach(el => {
    el.style.opacity = '1';
    el.style.transform = 'none';
  });
  await new Promise(r => setTimeout(r, 200));

  function parseColor(c){const m=c.match(/rgba?\(([^)]+)\)/);if(!m)return null;const p=m[1].split(',').map(s=>parseFloat(s.trim()));return{r:p[0],g:p[1],b:p[2],a:p.length===4?p[3]:1};}
  function blend(fg,bg){if(!fg||!bg)return fg;const a=fg.a;return{r:fg.r*a+bg.r*(1-a),g:fg.g*a+bg.g*(1-a),b:fg.b*a+bg.b*(1-a),a:1};}
  function rel(c){const n=v=>{v=v/255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);};return 0.2126*n(c.r)+0.7152*n(c.g)+0.0722*n(c.b);}
  function contrast(fg,bg){const L1=rel(fg),L2=rel(bg);return(Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);}
  function getBg(el){let c=el;while(c&&c!==document.body){const cs=getComputedStyle(c);const bg=parseColor(cs.backgroundColor);if(bg&&bg.a>0.5)return bg;c=c.parentElement;}return parseColor(getComputedStyle(document.body).backgroundColor)||{r:255,g:255,b:255,a:1};}
  function getFg(el){const cs=getComputedStyle(el);let fg=parseColor(cs.color);if(!fg)return null;let c=el,op=1;while(c&&c!==document.body){op*=parseFloat(getComputedStyle(c).opacity||'1');c=c.parentElement;}fg.a=(fg.a||1)*op;return fg;}

  const issues = [];
  document.querySelectorAll('.slide').forEach((slide, idx) => {
    slide.querySelectorAll('h1,h2,h3,h4,p,div,span,li,a,em,strong,td,th,blockquote').forEach(el => {
      const text = el.innerText ? el.innerText.trim() : '';
      if (!text || text.length < 2) return;
      const hasBlock = [...el.children].some(c => {const d=getComputedStyle(c).display;return d==='block'||d==='flex'||d==='grid';});
      if (hasBlock) return;
      const fg = getFg(el), bg = getBg(el);
      if (!fg || !bg) return;
      const blended = blend(fg, bg);
      const ratio = contrast(blended, bg);
      if (ratio < threshold) {
        issues.push({page:idx+1,ratio:Math.round(ratio*100)/100,text:text.slice(0,60),opacity_chain:Math.round(fg.a*100)/100,tag:el.tagName.toLowerCase(),cls:el.className||''});
      }
    });
  });
  return issues;
}
"""


async def _check_one(file: Path, threshold: float):
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()
        await page.goto(f"file://{file.resolve()}")
        await page.wait_for_load_state("networkidle", timeout=10000)
        await page.wait_for_timeout(800)
        result = await page.evaluate(CONTRAST_SCRIPT, threshold)
        await browser.close()
    return result


async def run(files: list[Path], *, decks_parent: Path, thresholds: dict) -> list[Finding]:
    th_blocker = thresholds.get("contrast_blocker", 2.0)
    th_error = thresholds.get("contrast_error", 4.5)
    th_warn = thresholds.get("contrast_warn", 7.0)

    findings: list[Finding] = []
    for file in files:
        repo, deck_id = derive_deck_id(file, decks_parent)
        try:
            issues = await _check_one(file, th_warn)  # 抓最寬閾值，再分級
        except Exception as e:
            findings.append(Finding(
                deck_id=deck_id, repo=repo, file=str(file), slide=None,
                checker="browser_contrast", severity="ERROR", code="RENDER_ERROR",
                message=f"Contrast check failed: {e}",
            ))
            continue

        for it in issues:
            ratio = it["ratio"]
            if ratio < th_blocker:
                sev, code = "BLOCKER", "CONTRAST_INVISIBLE"
            elif ratio < th_error:
                sev, code = "ERROR", "CONTRAST_LOW"
            else:
                sev, code = "WARN", "CONTRAST_BELOW_AAA"
            findings.append(Finding(
                deck_id=deck_id, repo=repo, file=str(file),
                slide=it["page"], checker="browser_contrast",
                severity=sev, code=code,
                message=f"contrast {ratio}:1 「{it['text'][:40]}」",
                selector=f"{it['tag']}.{it['cls'][:30]}".strip("."),
                actual=ratio,
                expected=f">={th_error} (WCAG AA)",
                evidence={"opacity_chain": it["opacity_chain"], "text": it["text"]},
            ))
    return findings

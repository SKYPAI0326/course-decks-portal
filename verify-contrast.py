#!/usr/bin/env python3
"""verify-contrast.py v2 — 主動觸發每頁 Motion One 動畫後再測對比"""
import asyncio, argparse, json, sys
from pathlib import Path

DECKS_PARENT = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/01-PROJECTS/課程簡報"

# Replaces inline opacity:0 / 0.15 by force-triggering all animations
TRIGGER_THEN_MEASURE = r"""
async (threshold) => {
  // Force all data-anim to opacity 1 and transform none (simulate "all animations completed")
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

async def check_file(path, viewport=(1920,1080), threshold=3.0):
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(viewport={'width':viewport[0],'height':viewport[1]})
        page = await ctx.new_page()
        await page.goto(f"file://{path.resolve()}")
        await page.wait_for_load_state('networkidle', timeout=10000)
        await page.wait_for_timeout(800)
        result = await page.evaluate(TRIGGER_THEN_MEASURE, threshold)
        await browser.close()
    return result

def collect_files(target):
    if target.is_file() and target.suffix == '.html': return [target]
    if target.is_dir():
        return sorted(p for p in target.rglob('*.html') if 'assets' not in p.parts and p.name not in ('index.html','_base.html'))
    return []

def collect_all():
    out = []
    for repo in sorted(DECKS_PARENT.iterdir()):
        if not repo.is_dir(): continue
        if not repo.name.endswith('-decks'): continue
        out.extend(collect_files(repo))
    return out

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target', nargs='?')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--json')
    ap.add_argument('--threshold', type=float, default=3.0)
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    files = collect_all() if args.all else collect_files(Path(args.target)) if args.target else []
    if not files: ap.print_help(); sys.exit(2)
    print(f"verify-contrast.py v2 (trigger-mode) · {len(files)} deck · threshold {args.threshold}")

    all_results, total, issue_files = [], 0, 0
    for f in files:
        try:
            issues = await check_file(f, threshold=args.threshold)
        except Exception as e:
            print(f"  ✗ {f.relative_to(DECKS_PARENT)}: {e}")
            continue
        rel = f.relative_to(DECKS_PARENT)
        if issues:
            issue_files += 1
            total += len(issues)
            print(f"\n  {rel}  ({len(issues)} low-contrast)")
            seen = {}
            for it in issues: seen.setdefault(it['page'],[]).append(it)
            for page, items in sorted(seen.items()):
                worst = min(items, key=lambda x:x['ratio'])
                print(f"    p{page:02d} · {len(items)}× · 最低 {worst['ratio']}:1 · 「{worst['text'][:40]}」")
        elif not args.quiet:
            print(f"  ✓ {rel}  clean")
        all_results.append({'file':str(f),'issues':issues})
    print(f"\n= 結果 = Decks: {len(files)}  Issue files: {issue_files}  Total: {total}")
    if args.json:
        Path(args.json).write_text(json.dumps(all_results, ensure_ascii=False, indent=2))
        print(f"  JSON: {args.json}")
    sys.exit(0 if not total else 1)

if __name__ == '__main__': asyncio.run(main())

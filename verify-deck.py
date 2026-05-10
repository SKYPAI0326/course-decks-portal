#!/usr/bin/env python3
"""
verify-deck.py — guizang-ppt-skill deck overflow 真實渲染驗證

用法：
  python3 verify-deck.py <file.html>            # 單份
  python3 verify-deck.py /path/to/repo/         # 整個 repo
  python3 verify-deck.py --all                  # 所有 deck repos
  python3 verify-deck.py --all --json out.json  # 機器可讀
  python3 verify-deck.py <file> --viewport 1920x1080
  python3 verify-deck.py <file> --shot dir/     # overflow 頁面截圖

原理：用 Playwright 開啟 deck，量測每個 .frame 的 scrollHeight vs clientHeight。
.frame {overflow:hidden} 會剪掉超出內容；diff > 5px 視為真實 overflow。

需要：pip install playwright; playwright install chromium

Exit 0 = 全綠｜Exit 1 = 至少 1 頁 overflow
"""
from __future__ import annotations
import argparse, json, sys, re
from pathlib import Path
from dataclasses import dataclass, field, asdict

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERR: playwright 未安裝。pip install playwright && playwright install chromium")
    sys.exit(2)

DECKS_PARENT = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/01-PROJECTS"
OVERFLOW_TOLERANCE_PX = 5     # < 5px 視為 rounding noise
WARN_TOLERANCE_PX = 50        # 5-50px = 邊界擦邊

@dataclass
class SlideResult:
    page: int
    title: str
    overflow_px: int
    content_h: int
    visible_h: int
    severity: str   # OK | TIGHT | OVERFLOW

@dataclass
class DeckResult:
    file: str
    total: int
    results: list[SlideResult] = field(default_factory=list)

JS_AUDIT = r"""
() => {
  const slides = Array.from(document.querySelectorAll('section.slide'));
  return slides.map((s, idx) => {
    const frame = s.querySelector('.frame') || s;
    const chrome = s.querySelector('.chrome, header.chrome');
    const foot = s.querySelector('.foot, footer.foot, footer');
    const slideRect = s.getBoundingClientRect();
    const frameRect = frame.getBoundingClientRect();
    // 內容實際高度（含被剪掉部分）
    const scrollH = frame.scrollHeight;
    const clientH = frame.clientHeight;
    // 從 chrome label 取頁碼，否則用 idx
    let title = '';
    if (chrome) {
      const labels = chrome.querySelectorAll('div');
      if (labels.length) title = (labels[0].textContent || '').trim().slice(0, 40);
    }
    return {
      idx: idx + 1,
      title,
      contentH: scrollH,
      visibleH: clientH,
      overflowPx: Math.max(0, scrollH - clientH),
      slideH: Math.round(slideRect.height),
    };
  });
}
"""

def collect_html_files(target: Path) -> list[Path]:
    if target.is_file() and target.suffix == '.html':
        return [target]
    if target.is_dir():
        out = []
        for p in target.rglob('*.html'):
            if 'assets' in p.parts: continue
            if p.name in ('index.html', '_base.html'): continue
            out.append(p)
        return sorted(out)
    return []

def collect_all_decks() -> list[Path]:
    out: list[Path] = []
    for repo in sorted(DECKS_PARENT.iterdir()):
        if not repo.is_dir(): continue
        if not repo.name.endswith('-decks'): continue
        if repo.name == 'course-decks-portal': continue
        out.extend(collect_html_files(repo))
    return out

def verify_deck(page, file_path: Path, shot_dir: Path | None) -> DeckResult:
    url = f'file://{file_path}'
    page.goto(url, wait_until='domcontentloaded', timeout=20_000)
    # 等字型載入（影響量測）
    try:
        page.wait_for_function("document.fonts && document.fonts.ready.then(()=>true)", timeout=8_000)
    except Exception:
        pass
    audits = page.evaluate(JS_AUDIT)
    result = DeckResult(file=str(file_path), total=len(audits))
    for a in audits:
        ov = int(a['overflowPx'])
        if ov >= WARN_TOLERANCE_PX:
            sev = 'OVERFLOW'
        elif ov >= OVERFLOW_TOLERANCE_PX:
            sev = 'TIGHT'
        else:
            sev = 'OK'
        result.results.append(SlideResult(
            page=int(a['idx']), title=a['title'],
            overflow_px=ov, content_h=int(a['contentH']),
            visible_h=int(a['visibleH']), severity=sev,
        ))
        # 截圖 OVERFLOW 頁
        if sev == 'OVERFLOW' and shot_dir:
            shot_dir.mkdir(parents=True, exist_ok=True)
            shot_name = f"{file_path.parent.name}__{file_path.stem}__p{a['idx']:02d}.png"
            try:
                page.evaluate(f"document.querySelectorAll('section.slide')[{a['idx']-1}].scrollIntoView()")
                page.wait_for_timeout(150)
                page.screenshot(path=str(shot_dir / shot_name), clip={
                    'x': 0, 'y': 0,
                    'width': page.viewport_size['width'],
                    'height': page.viewport_size['height'],
                })
            except Exception as e:
                print(f"    (screenshot failed for p{a['idx']}: {e})")
    return result

def print_deck(deck: DeckResult, *, quiet: bool):
    bad = [r for r in deck.results if r.severity in ('TIGHT', 'OVERFLOW')]
    if not bad:
        if not quiet:
            print(f"  ✓ {Path(deck.file).relative_to(DECKS_PARENT)}  ({deck.total} slides) clean")
        return
    rel = Path(deck.file).relative_to(DECKS_PARENT)
    print(f"\n  {rel}  ({deck.total} slides)")
    for r in bad:
        if quiet and r.severity == 'TIGHT':
            continue
        bar = {'OVERFLOW': '🛑', 'TIGHT': '·  '}[r.severity]
        print(f"    {bar} [{r.severity:8s}] page-{r.page:02d}  +{r.overflow_px}px overflow  "
              f"(content {r.content_h}px / visible {r.visible_h}px)  {r.title}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target', nargs='?')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--json', help='輸出 JSON 報表')
    ap.add_argument('--shot', help='OVERFLOW 頁截圖到指定目錄')
    ap.add_argument('--viewport', default='1920x1080', help='WxH')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    if args.all:
        files = collect_all_decks()
    elif args.target:
        files = collect_html_files(Path(args.target))
    else:
        ap.print_help(); sys.exit(2)

    w, h = (int(x) for x in args.viewport.lower().split('x'))
    shot_dir = Path(args.shot) if args.shot else None

    print(f"verify-deck.py · {len(files)} decks · viewport {w}×{h}"
          + (f" · shot→ {shot_dir}" if shot_dir else ""))

    decks: list[DeckResult] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width': w, 'height': h},
                                      device_scale_factor=1)
        page = context.new_page()
        for i, f in enumerate(files):
            try:
                d = verify_deck(page, f, shot_dir)
            except Exception as e:
                print(f"  ✗ {f}: {e}")
                continue
            decks.append(d)
            print_deck(d, quiet=args.quiet)
            if (i+1) % 10 == 0:
                print(f"  --- progress {i+1}/{len(files)} ---")
        browser.close()

    overflows = sum(1 for d in decks for r in d.results if r.severity == 'OVERFLOW')
    tights = sum(1 for d in decks for r in d.results if r.severity == 'TIGHT')
    bad_files = sum(1 for d in decks if any(r.severity == 'OVERFLOW' for r in d.results))

    print("\n= 驗證結果 =")
    print(f"  Decks:    {len(decks)}")
    print(f"  Slides:   {sum(d.total for d in decks)}")
    print(f"  OVERFLOW: {overflows}  (in {bad_files} files)")
    print(f"  TIGHT:    {tights}")

    if args.json:
        Path(args.json).write_text(json.dumps(
            [{'file': d.file, 'total': d.total,
              'results': [asdict(r) for r in d.results]}
             for d in decks if any(r.severity != 'OK' for r in d.results)],
            ensure_ascii=False, indent=2))
        print(f"  → JSON: {args.json}")

    sys.exit(1 if overflows else 0)

if __name__ == '__main__':
    main()

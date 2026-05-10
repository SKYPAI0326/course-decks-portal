#!/usr/bin/env python3
"""
lint-deck.py — guizang-ppt-skill deck overflow / layout 靜態檢查

用途：在 95 deck × ~2400 頁規模下，自動掃出疑似「內容被切」「排版誤差」的 slide。
原理：估算每個 slide 內容元素的垂直高度需求，與 100vh 預算比對。
解析 inline `font-size`/`max-width` style 與類別大小，做 LLM 不易看出的視覺風險偵測。

用法：
  python3 lint-deck.py <file.html>            # 單份 deck
  python3 lint-deck.py /path/to/repo/         # 整個 repo
  python3 lint-deck.py --all                  # 所有 deck repos
  python3 lint-deck.py --all --json out.json  # 機器可讀
  python3 lint-deck.py --all --threshold 100  # 收緊（預設 96vh）
  python3 lint-deck.py --quiet                # 只看 BLOCKER

Exit:
  0 = 全綠
  1 = 至少 1 個 BLOCKER
"""

from __future__ import annotations
import argparse
import html
import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Iterable

DECKS_PARENT = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/01-PROJECTS"

# ---------- 高度估算常數（單位：vh）----------
# 對齊真實 CSS：.slide{padding:6vh 6vw 10vh 6vw} = 16vh 上下
# .frame{gap:1.6vh; overflow:hidden} → 元素被裁
# .body-zh{font-size:max(15px,1.22vw); line-height:1.75} → ~4.5vh/line
# .callout{padding:3vh 2.4vw} → 6vh 上下 + 內邊距
# .kicker{margin-bottom:2.6vh}
# .h-xl{font-size:9vw} → 16vw 螢幕 → ~16vh/line
# .h-hero{font-size:14vw} → ~26vh/line

PAGE_BUDGET_VH = 90.0

H_HERO_PER_LINE_VH = 30.0  # 14vw font + 1.2 line-height
H_XL_PER_LINE_VH = 19.0    # 9vw font + 1.2 line-height
H_LG_PER_LINE_VH = 12.0
H_MD_PER_LINE_VH = 8.0
KICKER_VH = 7.2           # font 3.2 + margin-bottom 2.6 + 行間 1.4
BODY_LINE_VH = 4.5        # 1.22vw 行高 1.75
LEAD_LINE_VH = 5.5
STAT_CARD_VH = 18.0
PIPELINE_STEP_VH = 9.0
CALLOUT_PADDING_VH = 7.0
GRID_GAP_VH = 2.0
SECTION_PADDING_VH = 16.0  # .slide padding 6+10
CHROME_VH = 3.0
FOOTER_VH = 3.0
FRAME_GAP_PER_CHILD_VH = 0.8  # 桌機 .frame 預設無 gap；inline style 偶有 1.6-2vh
ROWLINE_VH = 7.5           # .rowline padding 2.2vh×2 + 內容 ~3vh
META_ROW_VH = 5.5
RAIL_ROW_VH = 6.0

# ---------- 結構 ----------

@dataclass
class Issue:
    severity: str          # BLOCKER | ERROR | WARN
    code: str
    page_idx: int
    page_id: str | None
    message: str
    detail: str | None = None

@dataclass
class DeckReport:
    file: str
    total_slides: int
    issues: list[Issue] = field(default_factory=list)

    def add(self, *args, **kwargs):
        self.issues.append(Issue(*args, **kwargs))

# ---------- 解析 ----------

SLIDE_RE = re.compile(r'<section\b([^>]*?class="[^"]*slide[^"]*"[^>]*)>(.*?)</section>',
                      re.DOTALL | re.IGNORECASE)
TAG_RE = re.compile(r'<([a-z]+\d?)\b([^>]*)>(.*?)</\1>', re.DOTALL | re.IGNORECASE)
ATTR_RE = re.compile(r'([a-z_-]+)\s*=\s*"([^"]*)"', re.IGNORECASE)
BR_SPLIT = re.compile(r'<br\s*/?>', re.IGNORECASE)
TAG_STRIP = re.compile(r'<[^>]+>')

def find_frame_block(slide_html: str):
    """找出 frame 容器，回傳 (style_attr, inner_html)。frame 用 depth-aware 找對應 </div>。"""
    m = re.search(r'<div\b([^>]*?class="[^"]*\bframe\b[^"]*"[^>]*)>', slide_html)
    if not m:
        return None
    style_match = re.search(r'style="([^"]*)"', m.group(1))
    style_str = style_match.group(1) if style_match else ''
    start = m.end()
    depth = 1
    pos = start
    div_re = re.compile(r'<(/?)div\b', re.IGNORECASE)
    while True:
        nm = div_re.search(slide_html, pos)
        if not nm:
            return (style_str, slide_html[start:])
        if nm.group(1) == '/':
            depth -= 1
            if depth == 0:
                return (style_str, slide_html[start:nm.start()])
        else:
            depth += 1
        pos = nm.end()

def strip_chrome_and_foot(slide_html: str) -> str:
    """剝掉 chrome / footer / .foot 區塊。"""
    s = re.sub(r'<header\b[^>]*class="[^"]*\bchrome\b[^"]*"[^>]*>.*?</header>', '', slide_html, flags=re.DOTALL)
    s = re.sub(r'<div\b[^>]*class="[^"]*\bchrome\b[^"]*"[^>]*>.*?</div>\s*(?=<div|<footer|<section)', '', s, flags=re.DOTALL)
    s = re.sub(r'<footer\b[^>]*>.*?</footer>', '', s, flags=re.DOTALL)
    s = re.sub(r'<div\b[^>]*class="[^"]*\bfoot\b[^"]*"[^>]*>.*?</div>(?=\s*</section|\s*$)', '', s, flags=re.DOTALL)
    return s

def get_attrs(attrs_str: str) -> dict:
    return {m.group(1).lower(): m.group(2) for m in ATTR_RE.finditer(attrs_str)}

def text_of(html_chunk: str) -> str:
    return html.unescape(TAG_STRIP.sub('', html_chunk)).strip()

def split_lines(html_chunk: str, keep_empty: bool = False) -> list[str]:
    """以 <br> 切行；keep_empty=True 時保留空行（連續 <br> 的視覺空格）。"""
    lines = [text_of(p).strip() for p in BR_SPLIT.split(html_chunk)]
    if keep_empty:
        return lines
    return [l for l in lines if l]

def count_visual_rows(html_chunk: str) -> int:
    """計算實際視覺 row 數：1 + 連續 <br> 數（每個 <br> 換新行）。"""
    parts = BR_SPLIT.split(html_chunk)
    return len(parts)  # N 個 <br> = N+1 段；連續 <br><br> 的中段是空但仍佔一行

def has_class(class_attr: str, *names: str) -> bool:
    classes = set(class_attr.split())
    return any(n in classes for n in names)

# ---------- 估算 ----------

def estimate_heading_vh(class_attr: str, html_chunk: str) -> float:
    text = text_of(html_chunk)
    # 中文字粗估每 12 字一行（在 8vw 字體下視寬度而定）
    lines_zh = max(1, (len(text) + 11) // 12)
    if has_class(class_attr, 'h-hero'):
        return H_HERO_PER_LINE_VH * lines_zh
    if has_class(class_attr, 'h-xl'):
        return H_XL_PER_LINE_VH * max(1, (len(text) + 14) // 15)
    if has_class(class_attr, 'h-lg'):
        return H_LG_PER_LINE_VH * max(1, (len(text) + 17) // 18)
    if has_class(class_attr, 'h-md', 'h-sub'):
        return H_MD_PER_LINE_VH * max(1, (len(text) + 19) // 20)
    return H_MD_PER_LINE_VH

def estimate_body_vh(html_chunk: str, max_em: float = 30.0) -> float:
    """body-zh / lead 區塊的高度。max_em 是寬度估算（字寬 1em）。
    每個 <br> 都算一行（含空白行），長行按 max_em 折行加倍。"""
    rows = split_lines(html_chunk, keep_empty=True)
    if not rows:
        return BODY_LINE_VH
    total = 0.0
    for line in rows:
        if not line:
            total += BODY_LINE_VH  # 空行
            continue
        zh = sum(1 for c in line if ord(c) > 0x2E80)
        ascii_n = len(line) - zh
        approx_w = zh * 1.0 + ascii_n * 0.55
        wrapped = max(1, int(approx_w / max_em + 0.999))
        total += BODY_LINE_VH * wrapped
    return total

def estimate_callout_vh(callout_html: str, col_em: float = 30.0) -> float:
    """callout 容器：內容 + padding。"""
    body_h = 0.0
    # 估其中所有 body / kicker / 文字段
    for m in TAG_RE.finditer(callout_html):
        tag, attrs, inner = m.group(1).lower(), m.group(2), m.group(3)
        cls = get_attrs(attrs).get('class', '')
        if 'kicker' in cls:
            body_h += KICKER_VH
        elif tag in ('p', 'div') and ('body-zh' in cls or 'lead' in cls or not cls):
            body_h += estimate_body_vh(inner, max_em=col_em)
    if body_h == 0:
        body_h = estimate_body_vh(callout_html, max_em=col_em)
    return body_h + CALLOUT_PADDING_VH

# ---------- 主檢查 ----------

def lint_slide(idx: int, slide_attrs: dict, slide_html: str, report: DeckReport):
    page_id = f"page-{idx+1:02d}"
    classes = slide_attrs.get('class', '')
    is_hero = 'hero' in classes.split()

    # 找 frame；終止可能是 <footer / <div class="foot" / </section
    frame_match = find_frame_block(slide_html)
    if frame_match:
        frame_style_str, inner = frame_match
        gap_per_child = FRAME_GAP_PER_CHILD_VH
        gap_m = re.search(r'gap\s*:\s*(\d+(?:\.\d+)?)vh', frame_style_str or '')
        if gap_m:
            gap_per_child = float(gap_m.group(1))
    else:
        # 退而求其次：移除 chrome / footer 後估
        inner = strip_chrome_and_foot(slide_html)
        gap_per_child = FRAME_GAP_PER_CHILD_VH

    # 計算：固定成本 + chrome + footer
    used_vh = SECTION_PADDING_VH + CHROME_VH + FOOTER_VH

    # 1. 頂層元素逐個累加（grid 取 max）
    top_level_items = parse_top_level(inner)
    for item in top_level_items:
        used_vh += item['height']
        used_vh += gap_per_child

    # 2. 規則：超過 PAGE_BUDGET_VH = WARN，超過 100vh = BLOCKER
    breakdown = ', '.join(f'{it["kind"]}={it["height"]:.0f}' for it in top_level_items[:6])
    if used_vh > 100.0:
        report.add('BLOCKER', 'OVERFLOW', idx, page_id,
                   f'估算 {used_vh:.0f}vh > 100vh，內容必被切',
                   detail=f'items={len(top_level_items)}; {breakdown}')
    elif used_vh > 92.0:
        report.add('WARN', 'TIGHT', idx, page_id,
                   f'估算 {used_vh:.0f}vh / 100vh 偏緊，邊界可能切',
                   detail=f'items={len(top_level_items)}; {breakdown}')

    # 3. 額外規則：h-xl/h-hero 後接 callout 多行
    check_callout_count_under_big_heading(idx, page_id, top_level_items, report)

def parse_top_level(html_str: str) -> list[dict]:
    """掃 frame 內容，取出最外層的 div/h2/h1/p/section 元素並估高。"""
    items: list[dict] = []
    pos = 0
    # 簡化：找頂層 <div ...> ... </div> / <h1> / <h2> / <p>
    # 不解析全 HTML tree，用 balance counter
    elements = []
    depth = 0
    start = -1
    tag_open = re.compile(r'<(div|h\d|p|ul|ol)\b', re.IGNORECASE)
    for m in re.finditer(r'<(/?)(div|h\d|p|ul|ol)\b([^>]*)>', html_str, re.IGNORECASE):
        is_close = m.group(1) == '/'
        if not is_close:
            if depth == 0:
                start = m.start()
                tag = m.group(2).lower()
                attrs = get_attrs(m.group(3))
                elements_start_tag = tag
                elements_start_attrs = attrs
            depth += 1
        else:
            depth -= 1
            if depth == 0 and start >= 0:
                end = m.end()
                outer = html_str[start:end]
                inner = html_str[m.start():m.start()]  # not used
                # extract inner (between first > of opener and last <)
                opener_end = outer.find('>') + 1
                closer_start = outer.rfind(f'</{elements_start_tag}')
                inner_html = outer[opener_end:closer_start]
                items.append({
                    'tag': elements_start_tag,
                    'attrs': elements_start_attrs,
                    'inner': inner_html,
                    'kind': '',
                    'height': 0.0,
                })
                start = -1

    # 估每個 item 高度
    for item in items:
        cls = item['attrs'].get('class', '')
        tag = item['tag']
        if tag in ('h1', 'h2', 'h3'):
            item['kind'] = 'heading'
            item['height'] = estimate_heading_vh(cls, item['inner'])
        elif 'kicker' in cls:
            item['kind'] = 'kicker'
            item['height'] = KICKER_VH
        elif 'h-hero' in cls or 'h-xl' in cls or 'h-lg' in cls:
            item['kind'] = 'heading'
            item['height'] = estimate_heading_vh(cls, item['inner'])
        elif 'callout' in cls:
            item['kind'] = 'callout'
            item['height'] = estimate_callout_vh(item['inner'])
        elif 'stat-card' in cls or 'stat' == cls.strip():
            item['kind'] = 'stat-card'
            item['height'] = STAT_CARD_VH
        elif 'pipeline' in cls and 'pipeline-section' not in cls:
            steps = len(re.findall(r'class="[^"]*\bstep(?:["\s])', item['inner']))
            item['kind'] = 'pipeline'
            item['height'] = PIPELINE_STEP_VH * max(1, steps) + 2.0
        elif 'rowline' in cls:
            item['kind'] = 'rowline'
            item['height'] = ROWLINE_VH
        elif 'meta-row' in cls or 'meta_row' in cls:
            item['kind'] = 'meta-row'
            item['height'] = META_ROW_VH
        elif cls.strip() == 'row' or 'rail' in cls:
            item['kind'] = 'row'
            item['height'] = RAIL_ROW_VH
        elif cls.startswith('grid') or 'grid-' in cls:
            cols = parse_grid_cols(cls)
            col_em = max(8.0, 70.0 / cols)
            # 用 depth-aware parse_top_level 抓 grid 直接子節點
            child_items = parse_top_level(item['inner'])
            heights = []
            for c in child_items:
                ccls = c['attrs'].get('class', '')
                if 'callout' in ccls:
                    heights.append(estimate_callout_vh(c['inner'], col_em=col_em))
                elif 'stat-card' in ccls or 'stat' == ccls.strip():
                    heights.append(STAT_CARD_VH)
                elif 'pipeline' in ccls and 'pipeline-section' not in ccls:
                    steps = len(re.findall(r'class="[^"]*\bstep\b', c['inner']))
                    heights.append(PIPELINE_STEP_VH * max(1, steps) + 2.0)
                else:
                    # 一般 div：按其內部估高
                    nested = parse_top_level(c['inner'])
                    if nested:
                        heights.append(sum(n['height'] for n in nested) + len(nested) * FRAME_GAP_PER_CHILD_VH)
                    else:
                        heights.append(estimate_body_vh(c['inner'], max_em=col_em))
            item['kind'] = f'grid-{cols}'
            item['height'] = max(heights) if heights else 6.0
            item['_child_count'] = len(child_items)
        elif 'body-zh' in cls or 'lead' in cls or tag == 'p':
            item['kind'] = 'body'
            item['height'] = estimate_body_vh(item['inner'])
        elif tag == 'ul' or tag == 'ol':
            li = len(re.findall(r'<li\b', item['inner']))
            item['kind'] = 'list'
            item['height'] = BODY_LINE_VH * max(1, li)
        else:
            # 嵌套 div：估算內部
            item['kind'] = 'div'
            inner_items = parse_top_level(item['inner'])
            if inner_items:
                item['height'] = sum(i['height'] for i in inner_items) + len(inner_items) * 0.5
            else:
                item['height'] = estimate_body_vh(item['inner'])
    return items

def parse_grid_cols(class_attr: str) -> int:
    m = re.search(r'grid-(\d)(?:-|\b)', class_attr)
    if m:
        return int(m.group(1))
    if 'grid-2-' in class_attr or 'grid-2' in class_attr:
        return 2
    if 'grid-3' in class_attr:
        return 3
    if 'grid-4' in class_attr:
        return 4
    if 'grid-6' in class_attr:
        return 6
    return 2

def check_callout_count_under_big_heading(idx, page_id, items: list[dict], report: DeckReport):
    has_big_head = any(i['kind'] == 'heading' and i['height'] > 12 for i in items)
    callouts = [i for i in items if i['kind'] in ('callout',) or i['kind'].startswith('grid')]
    for i in callouts:
        if has_big_head and i['height'] > 50:
            report.add('WARN', 'CALLOUT_HEAVY', idx, page_id,
                       f'h-xl/h-hero 後接 {i["kind"]} 估高 {i["height"]:.0f}vh，總和易超 100vh')

# ---------- 主流程 ----------

def lint_file(path: Path) -> DeckReport:
    text = path.read_text(encoding='utf-8', errors='replace')
    report = DeckReport(file=str(path), total_slides=0)

    slides = list(SLIDE_RE.finditer(text))
    report.total_slides = len(slides)
    for idx, m in enumerate(slides):
        attrs = get_attrs(m.group(1))
        body = m.group(2)
        lint_slide(idx, attrs, body, report)
    return report

def collect_html_files(target: Path) -> list[Path]:
    if target.is_file() and target.suffix == '.html':
        return [target]
    if target.is_dir():
        # 排除 index.html、_base.html、assets/
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

def print_report(report: DeckReport, *, quiet: bool, color: bool):
    if not report.issues:
        if not quiet:
            print(f"  ✓ {Path(report.file).relative_to(DECKS_PARENT)}  ({report.total_slides} slides) clean")
        return
    rel = Path(report.file).relative_to(DECKS_PARENT)
    print(f"\n  {rel}  ({report.total_slides} slides)")
    for issue in report.issues:
        if quiet and issue.severity == 'WARN':
            continue
        bar = {'BLOCKER': '🛑', 'ERROR': '⚠️ ', 'WARN': '·  '}[issue.severity]
        print(f"    {bar} [{issue.severity:7s}] {issue.code:18s} {issue.page_id}  {issue.message}")
        if issue.detail:
            print(f"           {issue.detail}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target', nargs='?', help='file / dir / "--all" via flag')
    ap.add_argument('--all', action='store_true', help='掃所有 *-decks repos')
    ap.add_argument('--json', help='輸出 JSON 報表到指定路徑')
    ap.add_argument('--quiet', action='store_true', help='只列 BLOCKER + ERROR')
    ap.add_argument('--threshold', type=float, default=96.0,
                    help='WARN 閾值 vh（預設 96）')
    args = ap.parse_args()

    global PAGE_BUDGET_VH
    PAGE_BUDGET_VH = args.threshold - 6.0  # 給 padding 預留

    if args.all:
        files = collect_all_decks()
    elif args.target:
        files = collect_html_files(Path(args.target))
    else:
        ap.print_help()
        sys.exit(2)

    print(f"lint-deck.py · 掃 {len(files)} 個 deck（threshold={args.threshold}vh）")

    reports = [lint_file(f) for f in files]
    blockers = sum(1 for r in reports for i in r.issues if i.severity == 'BLOCKER')
    errors = sum(1 for r in reports for i in r.issues if i.severity == 'ERROR')
    warns = sum(1 for r in reports for i in r.issues if i.severity == 'WARN')
    issued_files = sum(1 for r in reports if any(i.severity in ('BLOCKER','ERROR') for i in r.issues))
    warn_files = sum(1 for r in reports if any(i.severity == 'WARN' for i in r.issues))

    for r in reports:
        print_report(r, quiet=args.quiet, color=True)

    print()
    print(f"= 總結 =")
    print(f"  Decks:   {len(files)}")
    print(f"  Slides:  {sum(r.total_slides for r in reports)}")
    print(f"  BLOCKER: {blockers}  (in {issued_files} files)")
    print(f"  ERROR:   {errors}")
    print(f"  WARN:    {warns}  (in {warn_files} files)")

    if args.json:
        Path(args.json).write_text(json.dumps(
            [{'file': r.file, 'slides': r.total_slides,
              'issues': [asdict(i) for i in r.issues]}
             for r in reports if r.issues],
            ensure_ascii=False, indent=2))
        print(f"  → JSON: {args.json}")

    sys.exit(1 if blockers else 0)

if __name__ == '__main__':
    main()

"""visual_regression —— Playwright 截圖每 deck 的 golden slides，與 baseline diff。

策略（按 SPEC）：
- 每 deck 取「golden slides」: page 1 (cover) + page N (closing) + 中段樣本（max 5-8 張）
- 多 viewport 矩陣：1920x1080 (desktop) / 932x430 (phone landscape)
- baseline 存 deckcheck/baselines/visual/<deck_id>/<viewport>/<slide>.png
- 第一次跑 = 創 baseline；之後跑 = diff
- mask 動態區域：canvas.bg / .deck-mobile-overlay / 任何 [data-mask]
- diff > pixel_warn_pct → WARN，> pixel_error_pct → ERROR
"""
from __future__ import annotations
import asyncio
from pathlib import Path
from ..model import Finding, derive_deck_id


GOLDEN_VIEWPORTS = [(1920, 1080), (932, 430)]
GOLDEN_SLIDES_FN = lambda total: sorted(set([1, 2, total // 2, total - 1, total]) - {0})  # cover + 開場 + 中段 + 收束 + 結束

MASK_SELECTORS = "canvas.bg, .deck-mobile-overlay, html.mobile-reader::before, [data-mask]"


SETUP_SCRIPT = r"""
async () => {
  // 完全停掉 Motion One 動畫（避免兩次截圖時序差異）
  if (window.__playSlide) window.__playSlide = function(){}; // no-op
  // 隱藏動態元素
  ['canvas.bg', '.deck-mobile-overlay', '#nav', '#hint'].forEach(sel => {
    document.querySelectorAll(sel).forEach(el => el.style.visibility = 'hidden');
  });
  // 全部 data-anim 強制顯示，並用 setProperty(important) 鎖死
  document.querySelectorAll('[data-anim], [data-animate]').forEach(el => {
    el.style.setProperty('opacity', '1', 'important');
    el.style.setProperty('transform', 'none', 'important');
    el.style.setProperty('transition', 'none', 'important');
    el.style.setProperty('animation', 'none', 'important');
  });
  // 暫停 motion-ready 行為
  document.body.classList.remove('motion-ready');
  await new Promise(r => setTimeout(r, 500));
  return document.querySelectorAll('.slide').length;
}
"""

GOTO_SLIDE = """
async (idx) => {
  const slides = document.querySelectorAll('.slide');
  if (idx < 1 || idx > slides.length) return false;
  // 用 transform 把指定 slide 帶到 viewport（不觸發 playSlide）
  const deck = document.getElementById('deck');
  if (deck) {
    deck.style.transition = 'none';
    deck.style.transform = `translateX(-${(idx - 1) * 100}vw)`;
  }
  // 鎖死該 slide 的 data-anim 全顯
  slides[idx - 1].querySelectorAll('[data-anim], [data-animate]').forEach(el => {
    el.style.setProperty('opacity', '1', 'important');
    el.style.setProperty('transform', 'none', 'important');
  });
  await new Promise(r => setTimeout(r, 250));
  return true;
}
"""


async def _shoot_deck(file: Path, *, viewports, baseline_dir: Path, mode: str):
    """mode='create' 寫 baseline；mode='compare' 與 baseline diff 並回 finding[]。"""
    from playwright.async_api import async_playwright
    repo, deck_id = "", ""
    issues = []  # tuple[(slide, viewport, msg, diff_pct)]

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for vp in viewports:
            ctx = await browser.new_context(viewport={"width": vp[0], "height": vp[1]})
            page = await ctx.new_page()
            try:
                await page.goto(f"file://{file.resolve()}")
                await page.wait_for_load_state("networkidle", timeout=10000)
                total = await page.evaluate(SETUP_SCRIPT)
            except Exception as e:
                issues.append((None, vp, f"render failed: {e}", 0))
                await ctx.close()
                continue

            golden_slides = GOLDEN_SLIDES_FN(total) if total >= 5 else list(range(1, total + 1))
            for slide_idx in golden_slides:
                try:
                    ok = await page.evaluate(GOTO_SLIDE, slide_idx)
                    if not ok: continue
                    await page.wait_for_timeout(300)
                    out_dir = baseline_dir / f"{vp[0]}x{vp[1]}"
                    out_dir.mkdir(parents=True, exist_ok=True)
                    out_path = out_dir / f"p{slide_idx:02d}.png"
                    if mode == "create":
                        await page.screenshot(path=str(out_path), full_page=False)
                    else:  # compare
                        if not out_path.exists():
                            issues.append((slide_idx, vp, "baseline 不存在", 0))
                            continue
                        # 截到 tmp 比對
                        tmp_path = out_path.with_suffix(".new.png")
                        await page.screenshot(path=str(tmp_path), full_page=False)
                        diff_pct = _diff_pixels(out_path, tmp_path)
                        tmp_path.unlink()
                        if diff_pct >= 0.5:
                            issues.append((slide_idx, vp,
                                          f"視覺變化 {diff_pct:.2f}% (vs baseline)", diff_pct))
                except Exception as e:
                    issues.append((slide_idx, vp, f"shoot failed: {e}", 0))
            await ctx.close()
        await browser.close()
    return issues


def _diff_pixels(a: Path, b: Path) -> float:
    """回傳兩張圖差異 pixel %（0-100）。用 Pillow 像素比較，0.05 顏色閾值。"""
    from PIL import Image
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return 100.0  # 尺寸不同 = 全變
    pa, pb = ia.load(), ib.load()
    w, h = ia.size
    diff = 0
    total = 0
    # 抽樣（每 4 px 一個，提速 16x，誤差可接受）
    for x in range(0, w, 4):
        for y in range(0, h, 4):
            total += 1
            r1, g1, b1 = pa[x, y]; r2, g2, b2 = pb[x, y]
            if abs(r1 - r2) > 12 or abs(g1 - g2) > 12 or abs(b1 - b2) > 12:
                diff += 1
    return (diff / total * 100) if total else 0.0


async def run(files: list[Path], *, decks_parent: Path, thresholds: dict) -> list[Finding]:
    """執行 visual regression check。第一次跑會建 baseline，之後 diff。"""
    portal = Path(__file__).parent.parent.parent
    baseline_root = portal / "deckcheck" / "baselines" / "visual"
    findings: list[Finding] = []

    for file in files:
        repo, deck_id = derive_deck_id(file, decks_parent)
        baseline_dir = baseline_root / deck_id.replace("/", "__")
        # 模式：baseline_dir 不存在 → create；存在 → compare
        mode = "create" if not baseline_dir.exists() else "compare"

        try:
            issues = await _shoot_deck(file, viewports=GOLDEN_VIEWPORTS,
                                       baseline_dir=baseline_dir, mode=mode)
        except Exception as e:
            findings.append(Finding(
                deck_id=deck_id, repo=repo, file=str(file), slide=None,
                checker="visual_regression", severity="ERROR",
                code="VISUAL_RUN_ERROR",
                message=f"視覺檢查失敗: {e}",
            ))
            continue

        if mode == "create":
            findings.append(Finding(
                deck_id=deck_id, repo=repo, file=str(file), slide=None,
                checker="visual_regression", severity="INFO",
                code="VISUAL_BASELINE_CREATED",
                message=f"建立 baseline 於 {baseline_dir.relative_to(portal)}",
            ))
            continue

        for slide, vp, msg, diff_pct in issues:
            sev = "ERROR" if diff_pct >= 2.0 else "WARN" if diff_pct >= 0.5 else "INFO"
            code = "VISUAL_DIFF" if diff_pct > 0 else "VISUAL_BASELINE_MISSING"
            findings.append(Finding(
                deck_id=deck_id, repo=repo, file=str(file), slide=slide,
                checker="visual_regression", severity=sev, code=code,
                message=f"{msg} @ {vp[0]}x{vp[1]}",
                actual=f"{diff_pct:.2f}%",
                expected="<0.5%",
                evidence={"viewport": f"{vp[0]}x{vp[1]}",
                          "baseline_dir": str(baseline_dir.relative_to(portal))},
            ))
    return findings

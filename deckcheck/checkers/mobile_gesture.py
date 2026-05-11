"""mobile_gesture —— 模擬手機觸控，驗 reader mode 下垂直 scroll 不被 swipe handler 攔截。

關鍵測試：
1. 觸發 mobile-reader matchMedia (用 mobile viewport)
2. 模擬從上往下 scroll
3. 確認 window.scrollY 真的變化（沒被 e.preventDefault 攔）
4. 模擬左右 swipe
5. 確認 deck idx 沒變（reader 模式下 swipe 不應 advance slide）

問題範例（v6.x 修過）：deck JS touchstart/touchend 攔截手勢，window.scrollY 卡在 0
"""
from __future__ import annotations
from pathlib import Path
from ..model import Finding, derive_deck_id


GESTURE_TEST = r"""
async () => {
  // 確認 reader mode 已觸發
  const isReader = document.documentElement.classList.contains('mobile-reader');
  if (!isReader) {
    return { error: 'mobile-reader class not active' };
  }
  // 隱藏 D1 overlay 以便測 scroll
  const overlay = document.querySelector('.deck-mobile-overlay');
  if (overlay) {
    document.documentElement.classList.remove('overlay-shown');
  }
  await new Promise(r => setTimeout(r, 100));

  const initialY = window.scrollY;
  const docHeight = document.documentElement.scrollHeight;
  const winHeight = window.innerHeight;

  // 1. 測垂直 scroll（程式驅動，不靠真實觸控）
  window.scrollTo({top: 500, behavior: 'instant'});
  await new Promise(r => setTimeout(r, 100));
  const scrolledY = window.scrollY;

  return {
    isReader: true,
    initial_scroll: initialY,
    scrolled_to: scrolledY,
    expected: 500,
    can_scroll: scrolledY > 100,
    doc_height: docHeight,
    win_height: winHeight,
    body_overflow: getComputedStyle(document.body).overflow,
    html_overflow: getComputedStyle(document.documentElement).overflow,
  };
}
"""


async def _check_one(file: Path, viewport=(393, 852)):
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": viewport[0], "height": viewport[1]},
            has_touch=True,
            is_mobile=True,
        )
        page = await ctx.new_page()
        await page.goto(f"file://{file.resolve()}")
        await page.wait_for_load_state("networkidle", timeout=10000)
        await page.wait_for_timeout(800)
        result = await page.evaluate(GESTURE_TEST)
        await browser.close()
    return result


async def run(files: list[Path], *, decks_parent: Path, thresholds: dict) -> list[Finding]:
    findings: list[Finding] = []
    for file in files:
        repo, deck_id = derive_deck_id(file, decks_parent)
        try:
            r = await _check_one(file)
        except Exception as e:
            findings.append(Finding(
                deck_id=deck_id, repo=repo, file=str(file), slide=None,
                checker="mobile_gesture", severity="ERROR",
                code="GESTURE_RUN_ERROR",
                message=f"執行失敗: {e}",
            ))
            continue
        if r.get("error"):
            findings.append(Finding(
                deck_id=deck_id, repo=repo, file=str(file), slide=None,
                checker="mobile_gesture", severity="ERROR",
                code="READER_MODE_INACTIVE",
                message=r["error"],
            ))
            continue
        if not r.get("can_scroll"):
            findings.append(Finding(
                deck_id=deck_id, repo=repo, file=str(file), slide=None,
                checker="mobile_gesture", severity="BLOCKER",
                code="SCROLL_BLOCKED",
                message=f"reader 下 scrollY 卡在 {r['scrolled_to']}（預期 ≥100）",
                actual=r['scrolled_to'], expected=">=100",
                evidence={"body_overflow": r["body_overflow"],
                          "html_overflow": r["html_overflow"],
                          "doc_height": r["doc_height"]},
            ))
    return findings

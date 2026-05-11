"""raf_drain —— instrument requestAnimationFrame，偵測 reader mode 是否仍在跑 WebGL/Motion loop。

關鍵測試：
1. 觸發 mobile-reader（手機 viewport）
2. monkey-patch requestAnimationFrame 計數
3. 等 5 秒
4. 計算 RAF 呼叫次數，> 60 → WARN（reader 應該停掉 GPU loop 省電）

v7.1 已加 RAF guard，這個 checker 確認還在生效。
"""
from __future__ import annotations
from pathlib import Path
from ..model import Finding, derive_deck_id


RAF_PROBE = r"""
async () => {
  const isReader = document.documentElement.classList.contains('mobile-reader');
  if (!isReader) return { error: 'mobile-reader not active' };

  let count = 0;
  const orig = window.requestAnimationFrame;
  // 計數 wrapper
  window.requestAnimationFrame = function(cb){
    count++;
    return orig.call(window, cb);
  };
  await new Promise(r => setTimeout(r, 3000));
  // 復原
  window.requestAnimationFrame = orig;
  return { isReader: true, raf_count_3s: count };
}
"""


async def _check_one(file: Path, viewport=(393, 852)):
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": viewport[0], "height": viewport[1]},
            has_touch=True, is_mobile=True,
        )
        page = await ctx.new_page()
        await page.goto(f"file://{file.resolve()}")
        await page.wait_for_load_state("networkidle", timeout=10000)
        await page.wait_for_timeout(500)
        result = await page.evaluate(RAF_PROBE)
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
                checker="raf_drain", severity="ERROR",
                code="RAF_RUN_ERROR",
                message=f"執行失敗: {e}",
            ))
            continue
        if r.get("error"):
            continue  # 不是 reader 就跳過
        cnt = r.get("raf_count_3s", 0)
        # threshold: 3 秒內 ≤ 30 = OK, 30-60 = WARN, > 60 = ERROR
        if cnt > 60:
            sev, code = "ERROR", "RAF_DRAIN_HIGH"
        elif cnt > 30:
            sev, code = "WARN", "RAF_DRAIN_MEDIUM"
        else:
            continue  # OK
        findings.append(Finding(
            deck_id=deck_id, repo=repo, file=str(file), slide=None,
            checker="raf_drain", severity=sev, code=code,
            message=f"reader mode 3 秒內 RAF 呼叫 {cnt} 次（預期 ≤30）",
            actual=cnt, expected="<=30",
        ))
    return findings

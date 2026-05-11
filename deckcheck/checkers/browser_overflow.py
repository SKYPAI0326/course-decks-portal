"""browser_overflow —— 封裝 verify-deck.py，Playwright 量 frame.scrollHeight - clientHeight。

> 50px = BLOCKER (OVERFLOW)
> 5-50px = WARN (TIGHT)
跨多 viewport 由 thresholds["viewports"] 控制。
"""
from __future__ import annotations
import asyncio
from pathlib import Path
from ..model import Finding, derive_deck_id


SCAN_SCRIPT = """
() => {
  const slides = document.querySelectorAll('.slide');
  const out = [];
  slides.forEach((s, i) => {
    const frame = s.querySelector('.frame') || s;
    const titleEl = s.querySelector('.h-hero, .h-xl, .h1-zh, .display-zh, .display, h1, h2, h3');
    const title = titleEl ? (titleEl.innerText || '').trim().slice(0, 60) : '';
    const ch = frame.scrollHeight, vh = frame.clientHeight;
    out.push({page: i+1, content_h: ch, visible_h: vh, overflow_px: ch - vh, title});
  });
  return out;
}
"""


async def _check_one_viewport(file: Path, viewport: tuple[int, int]):
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = await ctx.new_page()
        await page.goto(f"file://{file.resolve()}")
        await page.wait_for_load_state("networkidle", timeout=10000)
        await page.wait_for_timeout(800)
        result = await page.evaluate(SCAN_SCRIPT)
        await browser.close()
    return result


async def run(files: list[Path], *, decks_parent: Path, thresholds: dict) -> list[Finding]:
    blocker_px = thresholds.get("overflow_px_blocker", 50)
    tight_px = thresholds.get("overflow_px_tight", 5)
    viewports = thresholds.get("viewports", [(1920, 1080)])

    findings: list[Finding] = []
    for file in files:
        repo, deck_id = derive_deck_id(file, decks_parent)
        for vp in viewports:
            try:
                slides = await _check_one_viewport(file, vp)
            except Exception as e:
                findings.append(Finding(
                    deck_id=deck_id, repo=repo, file=str(file), slide=None,
                    checker="browser_overflow", severity="ERROR",
                    code="RENDER_ERROR",
                    message=f"Playwright render failed @ {vp[0]}x{vp[1]}: {e}",
                ))
                continue
            for s in slides:
                ov = s["overflow_px"]
                if ov >= blocker_px:
                    findings.append(Finding(
                        deck_id=deck_id, repo=repo, file=str(file),
                        slide=s["page"], checker="browser_overflow",
                        severity="BLOCKER", code="OVERFLOW",
                        message=f"+{ov}px @ {vp[0]}x{vp[1]} ({s['title']})",
                        actual=ov, expected=f"<{blocker_px}",
                        evidence={"viewport": f"{vp[0]}x{vp[1]}",
                                  "content_h": s["content_h"],
                                  "visible_h": s["visible_h"]},
                    ))
                elif ov >= tight_px:
                    findings.append(Finding(
                        deck_id=deck_id, repo=repo, file=str(file),
                        slide=s["page"], checker="browser_overflow",
                        severity="WARN", code="TIGHT",
                        message=f"+{ov}px @ {vp[0]}x{vp[1]} ({s['title']})",
                        actual=ov, expected=f"<{tight_px}",
                        evidence={"viewport": f"{vp[0]}x{vp[1]}"},
                    ))
    return findings

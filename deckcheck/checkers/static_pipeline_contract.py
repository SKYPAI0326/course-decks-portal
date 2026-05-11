"""static_pipeline_contract —— 檢查每個 deck 的關鍵 CSS/JS 契約是否齊全。

涵蓋我們過去 8 小時迭代建立的所有規範：
- mobile-reader v7.1 sentinel
- D1 mobile-overlay v1
- pipeline JS 含自閱模式分支（不再卡 0.15）
- chrome-link mobile 統一 CSS
- h-hero margin-bottom 主標題呼吸規則
- .grid-2 CSS 定義（修補 systemic missing）
"""
from __future__ import annotations
from pathlib import Path
from ..model import Finding, derive_deck_id


# (token, severity, code, hint)
CONTRACTS = [
    ("/* mobile-reader-mode v7", "ERROR", "MISSING_READER_MODE",
     "缺 v7+ mobile-reader CSS 區塊（Codex 0e6bc391/d4a34d90 採納）"),
    ("/* mobile-overlay v1", "ERROR", "MISSING_D1_OVERLAY",
     "缺 D1 mobile overlay（Codex 5ac1020f 採納）"),
    ("var strict = new URL(location.href).searchParams.get('pipeline')", "ERROR",
     "MISSING_PIPELINE_SELFREAD",
     "pipeline JS 缺自閱模式分支，會卡 opacity:0.15"),
    ("/* 主標題下方呼吸 — 補 skill 結構缺口", "WARN", "MISSING_TITLE_MARGIN",
     "缺 h-hero adjacent sibling margin 補強"),
    ("/* chrome-link mobile 位置統一", "WARN", "MISSING_CHROME_RULE",
     "缺手機 reader 下 chrome-link 位置統一規則"),
]

# Conditional contract: 只在 deck 實際使用該 class 時才檢
CONDITIONAL_CONTRACTS = [
    # (use_token, def_token, severity, code, hint)
    ('class="grid-2"', ".grid-2{display:grid", "WARN", "MISSING_GRID_2",
     "deck 用了 .grid-2 class 但缺 CSS 定義（曾系統性 missing）"),
    ('class="grid-2 ', ".grid-2{display:grid", "WARN", "MISSING_GRID_2",
     "deck 用了 .grid-2 class 但缺 CSS 定義"),
]


def run(files: list[Path], *, decks_parent: Path, thresholds: dict) -> list[Finding]:
    findings: list[Finding] = []
    for file in files:
        repo, deck_id = derive_deck_id(file, decks_parent)
        try:
            text = file.read_text(encoding="utf-8")
        except Exception as e:
            findings.append(Finding(
                deck_id=deck_id, repo=repo, file=str(file), slide=None,
                checker="static_pipeline_contract", severity="ERROR",
                code="READ_ERROR", message=f"無法讀檔：{e}",
            ))
            continue

        for token, sev, code, hint in CONTRACTS:
            if token not in text:
                findings.append(Finding(
                    deck_id=deck_id, repo=repo, file=str(file), slide=None,
                    checker="static_pipeline_contract", severity=sev, code=code,
                    message=hint,
                    expected=f"contains: {token[:40]}...",
                    evidence={"missing_token": token},
                ))
        # 條件契約：只在 deck 實際用該 class 時才報
        reported_codes = set()
        for use_tok, def_tok, sev, code, hint in CONDITIONAL_CONTRACTS:
            if code in reported_codes: continue
            if use_tok in text and def_tok not in text:
                findings.append(Finding(
                    deck_id=deck_id, repo=repo, file=str(file), slide=None,
                    checker="static_pipeline_contract", severity=sev, code=code,
                    message=hint,
                    expected=f"contains: {def_tok}", evidence={"missing_token": def_tok},
                ))
                reported_codes.add(code)
    return findings

"""static_tokens —— 跨 deck canonical token drift audit。

從 canonical/tokens.json 抓 baseline，每個 deck 的對應 selector 規則跟 baseline 比，
報「token 熱點」聚合（哪些 selector 在多少 deck 漂移）。

不用全 CSS parser（太重）— 用 regex 抓 `.selector{...}` 第一條，
比對單個 property（font-size / line-height / padding）的 numeric 偏離百分比。

Phase 1：只報、不 patch。
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from ..model import Finding, derive_deck_id


def _load_canonical() -> dict:
    here = Path(__file__).parent.parent / "canonical" / "tokens.json"
    return json.loads(here.read_text(encoding="utf-8"))


def _parse_numeric(value: str) -> tuple[float, str] | None:
    """從 '10vw' / '1.22vw' / '12px' / '.92' 抽出 (number, unit)。
    複雜的 max(...) / clamp(...) 取第一個數值當主要對比，回傳 None 跳過 numeric diff。"""
    s = value.strip()
    # 簡單值
    m = re.match(r"^(-?\d*\.?\d+)([a-z%]+)?$", s)
    if m:
        return float(m.group(1)), m.group(2) or ""
    return None  # 複雜值不做 numeric diff


def _extract_property(css_text: str, selector: str, prop: str) -> str | None:
    """從 CSS text 抓 `.selector { ... prop: value ... }` 第一條。
    用 regex 簡化處理；忽略 @media query 內的 override（只抓全域定義）。"""
    # 搜尋 selector 的 block。允許前面有空白或開頭。
    # 範圍：從 `.selector{` 到第一個 `}`
    pattern = rf"(?<![\w-]){re.escape(selector)}\s*\{{([^}}]*)\}}"
    matches = list(re.finditer(pattern, css_text))
    if not matches:
        return None
    # 取第一個（通常是全域定義；@media 內的會在後面）
    block = matches[0].group(1)
    # 尋找 prop
    pattern2 = rf"(?<![\w-]){re.escape(prop)}\s*:\s*([^;]+);?"
    m = re.search(pattern2, block)
    if m:
        return m.group(1).strip()
    return None


def run(files: list[Path], *, decks_parent: Path, thresholds: dict) -> list[Finding]:
    canonical = _load_canonical()["selectors"]
    warn_pct = thresholds.get("token_deviation_warn_pct", 3)
    error_pct = thresholds.get("token_deviation_error_pct", 8)

    findings: list[Finding] = []
    for file in files:
        repo, deck_id = derive_deck_id(file, decks_parent)
        try:
            text = file.read_text(encoding="utf-8")
        except Exception:
            continue

        for selector, props in canonical.items():
            for prop, expected_val in props.items():
                actual = _extract_property(text, selector, prop)
                if actual is None:
                    # 缺定義 — 對 .h-hero / .h-xl / .lead 這類核心 selector 是 ERROR
                    if selector in (".h-hero", ".h-xl", ".lead", ".body-zh"):
                        findings.append(Finding(
                            deck_id=deck_id, repo=repo, file=str(file), slide=None,
                            checker="static_tokens", severity="WARN",
                            code="TOKEN_MISSING",
                            message=f"{selector} 缺 {prop} 定義（canonical: {expected_val}）",
                            selector=selector,
                            actual=None, expected=expected_val,
                        ))
                    continue

                if actual == expected_val:
                    continue  # exact match

                # numeric diff
                exp_num = _parse_numeric(expected_val)
                act_num = _parse_numeric(actual)
                if exp_num and act_num and exp_num[1] == act_num[1]:
                    pct = abs(act_num[0] - exp_num[0]) / exp_num[0] * 100
                    if pct < warn_pct:
                        continue  # 容差內不報
                    sev = "ERROR" if pct >= error_pct else "WARN"
                    findings.append(Finding(
                        deck_id=deck_id, repo=repo, file=str(file), slide=None,
                        checker="static_tokens", severity=sev,
                        code="TOKEN_DEVIATION",
                        message=f"{selector} {prop}: {actual} (canonical {expected_val}, {pct:+.0f}%)",
                        selector=selector,
                        actual=actual, expected=expected_val,
                        evidence={"deviation_pct": round(pct, 1)},
                    ))
                else:
                    # 字串差異（不是 numeric 比較）— 只在主要 selector 報
                    if selector in (".h-hero", ".h-xl", ".kicker", ".lead", ".callout"):
                        findings.append(Finding(
                            deck_id=deck_id, repo=repo, file=str(file), slide=None,
                            checker="static_tokens", severity="WARN",
                            code="TOKEN_DIFF",
                            message=f"{selector} {prop}: {actual} ≠ canonical {expected_val}",
                            selector=selector,
                            actual=actual, expected=expected_val,
                        ))
    return findings

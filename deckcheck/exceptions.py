"""Exceptions filter —— 載入 deckcheck.yml allowed_findings，過濾 finding。

對 match 的 finding：
  - severity 從 BLOCKER/ERROR/WARN 全部降為 INFO（並標記 _allowed: True）
  - 報表仍能看到（透明度），但不算「真正問題」

用 PyYAML（系統有就用，沒有 fallback 到簡單 parser）。
"""
from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from .model import Finding


def _load_yaml(path: Path) -> dict:
    """嘗試 PyYAML，失敗 fallback 到極簡 parser（只支援本案使用的子集）。"""
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except ImportError:
        pass

    # Fallback: 極簡 yaml parser (不通用，只解 deckcheck.yml 結構)
    out = {"allowed_findings": []}
    cur: dict | None = None
    cur_list_key = None
    in_list = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"): continue
        # 檢查是不是新 list item（"  - key: val"）
        if line.startswith("  - "):
            if cur is not None:
                out["allowed_findings"].append(cur)
            cur = {}
            cur_list_key = None
            line = "    " + line[4:]  # 把 "- " 變等同 4 空格繼續
        if line.startswith("    ") and ":" in line:
            stripped = line[4:].lstrip()
            if "[" in stripped and "]" in stripped:
                k, v = stripped.split(":", 1)
                v = v.strip().strip("[]")
                items = [x.strip().strip('"').strip("'") for x in v.split(",") if x.strip()]
                if cur is not None: cur[k.strip()] = items
            elif ":" in stripped:
                k, v = stripped.split(":", 1)
                if cur is not None:
                    cur[k.strip()] = v.strip().strip('"').strip("'")
        elif line.startswith("allowed_findings:"):
            in_list = True
    if cur is not None:
        out["allowed_findings"].append(cur)
    return out


def _matches_pattern(deck_id: str, pattern: str) -> bool:
    """支援 'dm70h-decks/*' / 'gen-ai-140h-decks/m01' 等。"""
    if pattern == deck_id: return True
    if pattern.endswith("/*"):
        prefix = pattern[:-2]
        return deck_id.startswith(prefix + "/")
    return False


def _matches_rule(finding: Finding, rule: dict) -> bool:
    # 1. deck pattern
    deck_pat = rule.get("deck_pattern") or rule.get("deck")
    if deck_pat and not _matches_pattern(finding.deck_id, deck_pat):
        return False
    # 2. code
    if "code" in rule and rule["code"] != finding.code:
        return False
    # 3. selector / selector_in
    if "selector" in rule and finding.selector != rule["selector"]:
        return False
    if "selector_in" in rule:
        sels = rule["selector_in"] if isinstance(rule["selector_in"], list) else [rule["selector_in"]]
        if finding.selector not in sels:
            return False
    # 4. property（從 message 抽 prop name；e.g. ".h-xl font-size: 5.4vw" → "font-size"）
    if "property" in rule:
        msg = finding.message or ""
        # message 格式: ".selector property: value (canonical x, y%)"
        m = re.match(r"\S+\s+([\w-]+)\s*:", msg)
        if not m or m.group(1) != rule["property"]:
            return False
    # 5. actual_value / actual_in
    actual_str = str(finding.actual) if finding.actual is not None else ""
    if "actual_value" in rule and actual_str != rule["actual_value"]:
        return False
    if "actual_in" in rule:
        vals = rule["actual_in"] if isinstance(rule["actual_in"], list) else [rule["actual_in"]]
        if actual_str not in vals:
            return False
    # 6. expires（過期則不再 allow）
    expires = rule.get("expires")
    if expires:
        try:
            exp_str = str(expires)
            # date object 或 ISO string 都接受
            exp = datetime.fromisoformat(exp_str)
            if datetime.now() > exp:
                return False  # 過期 → 不再 allow，重新計入
        except Exception:
            pass
    return True


def apply_exceptions(findings: list[Finding], config_path: Path | None = None,
                     *, quiet: bool = False) -> tuple[list[Finding], int]:
    """掃 findings，把 match 的降為 INFO 並標 _allowed/reason。回傳 (findings, allowed_count)。"""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "deckcheck.yml"
    if not config_path.exists():
        return findings, 0
    try:
        cfg = _load_yaml(config_path)
    except Exception as e:
        if not quiet:
            print(f"  [warn] config 解析失敗: {e}")
        return findings, 0

    rules = cfg.get("allowed_findings", []) or []
    if not rules:
        return findings, 0

    allowed_count = 0
    out: list[Finding] = []
    for f in findings:
        matched_rule = None
        for rule in rules:
            if _matches_rule(f, rule):
                matched_rule = rule
                break
        if matched_rule:
            allowed_count += 1
            f.evidence = {**f.evidence, "_allowed": True,
                          "_reason": str(matched_rule.get("reason", "")),
                          "_expires": str(matched_rule.get("expires", ""))}
            f.severity = "INFO"  # 降級
            f.code = f.code + "_ALLOWED"
        out.append(f)

    if not quiet and allowed_count:
        print(f"  [exceptions] {allowed_count} findings 降為 INFO（match deckcheck.yml）")
    return out, allowed_count

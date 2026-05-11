"""static_lint —— 用 subprocess 跑既有 lint-deck.py 取 JSON（避免 from __future__ + dataclass 動態載入問題）。

把每頁元素估算 vh 加總 > 100 標 BLOCKER、>92 標 WARN。純靜態、秒級。
本框架降為 INFO/WARN（啟發式偽陽性高，當參考用）。
"""
from __future__ import annotations
import json
import subprocess
import tempfile
import sys
from pathlib import Path
from ..model import Finding, derive_deck_id


def run(files: list[Path], *, decks_parent: Path, thresholds: dict) -> list[Finding]:
    portal_root = Path(__file__).parent.parent.parent
    lint_script = portal_root / "lint-deck.py"

    findings: list[Finding] = []
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        # 一次跑全部 files
        cmd = [sys.executable, str(lint_script)] + [str(f) for f in files] + ["--quiet", "--json", str(tmp_path)]
        # lint-deck.py 接 single target，逐 file 跑
        for f in files:
            try:
                r = subprocess.run(
                    [sys.executable, str(lint_script), str(f), "--quiet", "--json", str(tmp_path)],
                    capture_output=True, text=True, timeout=30
                )
            except Exception as e:
                repo, deck_id = derive_deck_id(f, decks_parent)
                findings.append(Finding(
                    deck_id=deck_id, repo=repo, file=str(f), slide=None,
                    checker="static_lint", severity="WARN", code="LINT_FAIL",
                    message=f"subprocess error: {e}",
                ))
                continue

            if not tmp_path.exists() or tmp_path.stat().st_size == 0:
                continue
            try:
                data = json.loads(tmp_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            tmp_path.write_text("")  # 清空準備下一份

            repo, deck_id = derive_deck_id(f, decks_parent)
            # data 是 list of {file, slides, issues: [{severity, code, page_idx, page_id, message, detail}]}
            for entry in data:
                for issue in entry.get("issues", []):
                    raw_sev = issue.get("severity", "WARN")
                    # 啟發式偽陽性高，整體降一級
                    sev = {"BLOCKER": "WARN", "ERROR": "WARN", "WARN": "INFO"}.get(raw_sev, "INFO")
                    findings.append(Finding(
                        deck_id=deck_id, repo=repo, file=str(f),
                        slide=(issue.get("page_idx") or 0) + 1,
                        checker="static_lint",
                        severity=sev,
                        code=f"LINT_{issue.get('code', 'UNKNOWN')}",
                        message=issue.get("message", ""),
                        evidence={"detail": issue.get("detail") or "", "raw_severity": raw_sev},
                    ))
    finally:
        try: tmp_path.unlink()
        except Exception: pass

    return findings

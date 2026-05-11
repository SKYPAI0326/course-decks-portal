"""JSON reporter —— 機器可讀完整 dump。"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from ..model import Finding, aggregate_by_severity, aggregate_by_checker, aggregate_by_deck


def write(findings: list[Finding], out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total": len(findings),
            "by_severity": aggregate_by_severity(findings),
            "by_checker": aggregate_by_checker(findings),
            "by_deck_count": len(aggregate_by_deck(findings)),
        },
        "findings": [f.to_dict() for f in findings],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  → JSON written: {out}")

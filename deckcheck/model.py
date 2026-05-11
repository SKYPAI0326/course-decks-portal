"""Finding / Severity / Evidence schema —— 所有 checker 統一輸出格式。"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any
from pathlib import Path


class Severity(str, Enum):
    BLOCKER = "BLOCKER"   # 內容不可見 / 連結 404 / deck 無法載入
    ERROR   = "ERROR"     # 明顯違規但不阻斷上課
    WARN    = "WARN"      # 風險或漂移
    INFO    = "INFO"      # 統計 / 建議

    def rank(self) -> int:
        return {"BLOCKER": 4, "ERROR": 3, "WARN": 2, "INFO": 1}[self.value]


@dataclass
class Finding:
    deck_id: str               # 自動 derive: f"{repo}/{filename_stem}"
    repo: str                  # ai-workshop-decks / gen-ai-140h-decks 等
    file: str                  # absolute path
    slide: int | None          # 1-indexed; None 表整 deck-level
    checker: str               # browser_overflow / static_tokens 等
    severity: str              # 用 Severity.value
    code: str                  # OVERFLOW / CONTRAST_LOW / TOKEN_DEVIATION 等
    message: str               # 人類可讀
    selector: str | None = None
    actual: Any = None
    expected: Any = None
    evidence: dict = field(default_factory=dict)
    autofix: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def derive_deck_id(file_path: Path, decks_parent: Path) -> tuple[str, str]:
    """從 file path 推 (repo, deck_id)。
    例：~/.../課程簡報/dm70h-decks/m1-consumer-psychology.html
        → ('dm70h-decks', 'dm70h-decks/m1-consumer-psychology')
    """
    rel = file_path.resolve().relative_to(decks_parent.resolve())
    parts = rel.parts
    repo = parts[0]
    stem = file_path.stem
    return repo, f"{repo}/{stem}"


def aggregate_by_severity(findings: list[Finding]) -> dict[str, int]:
    out = {"BLOCKER": 0, "ERROR": 0, "WARN": 0, "INFO": 0}
    for f in findings:
        out[f.severity] = out.get(f.severity, 0) + 1
    return out


def aggregate_by_checker(findings: list[Finding]) -> dict[str, int]:
    out: dict[str, int] = {}
    for f in findings:
        out[f.checker] = out.get(f.checker, 0) + 1
    return out


def aggregate_by_deck(findings: list[Finding]) -> dict[str, list[Finding]]:
    out: dict[str, list[Finding]] = {}
    for f in findings:
        out.setdefault(f.deck_id, []).append(f)
    return out

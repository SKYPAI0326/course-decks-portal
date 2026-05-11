"""配置：threshold / profile / repo discovery。"""
from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass

# 預設位置，可用 DECKCHECK_DECKS_PARENT 環境變數覆蓋（CI / 不同環境）
_DEFAULT_PARENT = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/01-PROJECTS/課程簡報"
DECKS_PARENT = Path(os.environ.get("DECKCHECK_DECKS_PARENT", str(_DEFAULT_PARENT)))

# 不在 audit 範圍的 repo（接洽 / 入口頁等）
EXCLUDED_REPOS = {"course-decks-portal"}  # portal 自己不掃；catalog 由 user 決定獨立規則

# Profile → 啟用哪些 checker
PROFILES = {
    "fast":   ["static_lint", "static_pipeline_contract", "static_tokens"],
    "normal": ["static_lint", "static_pipeline_contract", "static_tokens",
               "browser_overflow", "browser_contrast"],
    "full":   ["static_lint", "static_pipeline_contract", "static_tokens",
               "browser_overflow", "browser_contrast",
               "visual_regression", "mobile_gesture", "raf_drain"],
    "visual": ["visual_regression"],
    "mobile": ["mobile_gesture", "raf_drain"],
}

# 預設 threshold
THRESHOLDS = {
    "overflow_px_blocker": 50,    # frame.scrollHeight - clientHeight > 50px
    "overflow_px_tight": 5,       # 5-50px = TIGHT (WARN)
    # Contrast 對「電子雜誌 × e-ink」設計偽陽性極多（callout opacity .92 + body opacity .82 等）
    # 預設只抓「真的看不見」< 2.0；想嚴格用 --threshold 自訂
    "contrast_blocker": 2.0,      # WCAG contrast < 2.0 = BLOCKER
    "contrast_error": 2.0,        # 同 blocker（不額外報 ERROR 級）
    "contrast_warn": 2.0,         # 同（不報 WARN）
    "token_deviation_warn_pct": 3,
    "token_deviation_error_pct": 8,
    "viewports": [
        (1920, 1080),   # 投影預設（Full HD）
        (1470, 800),    # MacBook 14" Safari 含 chrome 實際 viewport
        (1280, 720),    # Stress: 較舊筆電 / Safari 開側邊欄
    ],
}


def discover_deck_files(parent: Path = None, *, only_repos: list[str] = None) -> list[Path]:
    """掃所有 *-decks repo 的 deck HTML 檔（排除 catalog/portal/index.html/_base/assets）。
    路徑不存在（CI 等情境）→ return [] 不 crash。"""
    parent = parent or DECKS_PARENT
    if not parent.exists() or not parent.is_dir():
        return []
    out: list[Path] = []
    for repo in sorted(parent.iterdir()):
        if not repo.is_dir(): continue
        if not repo.name.endswith("-decks"): continue
        if repo.name in EXCLUDED_REPOS: continue
        if only_repos and repo.name not in only_repos: continue
        for p in sorted(repo.rglob("*.html")):
            if "assets" in p.parts: continue
            if p.name in ("index.html", "_base.html"): continue
            out.append(p)
    return out


def discover_changed_files(parent: Path = None) -> list[Path]:
    """從 git status 找 changed *-decks/*.html。"""
    import subprocess
    parent = parent or DECKS_PARENT
    out: list[Path] = []
    for repo in sorted(parent.iterdir()):
        if not repo.is_dir() or not repo.name.endswith("-decks"): continue
        if repo.name in EXCLUDED_REPOS: continue
        try:
            r = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                              capture_output=True, text=True, timeout=5)
            for line in r.stdout.splitlines():
                if not line.strip(): continue
                fname = line[3:].strip()
                if fname.endswith(".html") and fname not in ("index.html", "_base.html"):
                    p = repo / fname
                    if p.exists() and "assets" not in p.parts:
                        out.append(p)
        except Exception:
            pass
    return out

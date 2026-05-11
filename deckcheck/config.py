"""配置：threshold / profile / repo discovery。"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass

DECKS_PARENT = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/01-PROJECTS/課程簡報"

# 不在 audit 範圍的 repo（接洽 / 入口頁等）
EXCLUDED_REPOS = {"course-decks-portal"}  # portal 自己不掃；catalog 由 user 決定獨立規則

# Profile → 啟用哪些 checker
PROFILES = {
    "fast":   ["static_lint", "static_pipeline_contract", "static_tokens"],
    "normal": ["static_lint", "static_pipeline_contract", "static_tokens",
               "browser_overflow", "browser_contrast"],
    "full":   ["static_lint", "static_pipeline_contract", "static_tokens",
               "browser_overflow", "browser_contrast"],
    "visual": [],  # MVP 留白，Phase 2 加 visual_regression
}

# 預設 threshold
THRESHOLDS = {
    "overflow_px_blocker": 50,    # frame.scrollHeight - clientHeight > 50px
    "overflow_px_tight": 5,       # 5-50px = TIGHT (WARN)
    "contrast_blocker": 2.0,      # WCAG contrast < 2.0 = BLOCKER (真的看不見)
    "contrast_error": 4.5,        # < 4.5 (WCAG AA body) = ERROR
    "contrast_warn": 7.0,         # < 7.0 (WCAG AAA) = WARN
    "token_deviation_warn_pct": 3,
    "token_deviation_error_pct": 8,
    "viewports": [
        (1920, 1080),  # 投影預設
    ],
}


def discover_deck_files(parent: Path = None, *, only_repos: list[str] = None) -> list[Path]:
    """掃所有 *-decks repo 的 deck HTML 檔（排除 catalog/portal/index.html/_base/assets）。"""
    parent = parent or DECKS_PARENT
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

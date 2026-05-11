"""Checker orchestration —— 跑 profile 內所有 checker、收齊 Finding[]。"""
from __future__ import annotations
import asyncio
import importlib
from pathlib import Path
from .model import Finding
from .config import PROFILES, THRESHOLDS, DECKS_PARENT


CHECKER_REGISTRY = {
    "static_lint":              "deckcheck.checkers.static_lint",
    "static_pipeline_contract": "deckcheck.checkers.static_pipeline_contract",
    "static_tokens":            "deckcheck.checkers.static_tokens",
    "browser_overflow":         "deckcheck.checkers.browser_overflow",
    "browser_contrast":         "deckcheck.checkers.browser_contrast",
    "visual_regression":        "deckcheck.checkers.visual_regression",
    "mobile_gesture":           "deckcheck.checkers.mobile_gesture",
    "raf_drain":                "deckcheck.checkers.raf_drain",
}


async def run_profile(
    profile: str,
    files: list[Path],
    *,
    decks_parent: Path = None,
    thresholds: dict = None,
    quiet: bool = False,
) -> list[Finding]:
    """跑指定 profile 的所有 checker over files，回傳 Finding[]。"""
    decks_parent = decks_parent or DECKS_PARENT
    thresholds = thresholds or THRESHOLDS
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}. Available: {list(PROFILES)}")

    enabled = PROFILES[profile]
    if not quiet:
        print(f"[runner] profile={profile} · {len(files)} files · checkers: {enabled}")

    all_findings: list[Finding] = []
    for checker_name in enabled:
        if checker_name not in CHECKER_REGISTRY:
            if not quiet:
                print(f"  [skip] unknown checker {checker_name}")
            continue
        try:
            mod = importlib.import_module(CHECKER_REGISTRY[checker_name])
        except ImportError as e:
            if not quiet:
                print(f"  [skip] {checker_name}: {e}")
            continue
        run = getattr(mod, "run", None)
        if run is None:
            if not quiet:
                print(f"  [skip] {checker_name}: no run() function")
            continue
        try:
            if asyncio.iscoroutinefunction(run):
                findings = await run(files, decks_parent=decks_parent, thresholds=thresholds)
            else:
                findings = run(files, decks_parent=decks_parent, thresholds=thresholds)
        except Exception as e:
            if not quiet:
                print(f"  [error] {checker_name}: {e}")
            continue
        all_findings.extend(findings or [])
        if not quiet:
            print(f"  [✓] {checker_name}: {len(findings or [])} findings")

    return all_findings

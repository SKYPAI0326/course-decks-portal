#!/usr/bin/env python3
"""B 步驟工具 —— 統計 95 deck 各 selector/property 的實際值分布，找眾數。

跑法：
  python3 deckcheck/scripts/extract_actual_tokens.py

輸出：分布表 + 建議的新 canonical/tokens.json（不會自動覆蓋，需人工 review）
"""
from __future__ import annotations
import re
import sys
import json
from pathlib import Path
from collections import Counter

PORTAL = Path(__file__).parent.parent.parent
DECKS = PORTAL.parent  # 課程簡報/

sys.path.insert(0, str(PORTAL))
from deckcheck.checkers.static_tokens import _extract_property
from deckcheck.config import discover_deck_files


def collect_distribution() -> dict:
    canonical_path = PORTAL / "deckcheck" / "canonical" / "tokens.json"
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))["selectors"]

    files = discover_deck_files(DECKS)
    print(f"掃 {len(files)} deck files\n")

    dist: dict[str, dict[str, Counter]] = {}
    for selector, props in canonical.items():
        dist[selector] = {prop: Counter() for prop in props}

    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for selector, props in canonical.items():
            for prop in props:
                actual = _extract_property(text, selector, prop)
                if actual:
                    dist[selector][prop][actual.strip()] += 1
                else:
                    dist[selector][prop]["__missing__"] += 1
    return dist, canonical


def print_distribution(dist: dict, canonical: dict):
    print(f"{'='*88}")
    print(f"{'Selector / Property':40s} {'Canonical':18s} {'Actual mode':18s} {'Count':>6s}")
    print(f"{'='*88}")
    suggestions: dict[str, dict[str, str]] = {}
    for selector, props in dist.items():
        for prop, counter in props.items():
            if not counter:
                continue
            top = counter.most_common(3)
            mode_val, mode_cnt = top[0]
            total = sum(counter.values())
            mode_pct = mode_cnt / total * 100
            canonical_val = canonical.get(selector, {}).get(prop, "—")
            mark = "  " if mode_val == canonical_val else "→ "
            print(f"{mark}{selector + ' ' + prop:38s} {canonical_val:18s} {mode_val:18s} {mode_cnt:>3d}/{total:<3d} ({mode_pct:.0f}%)")
            if len(top) > 1:
                for v, c in top[1:]:
                    print(f"  {'':38s} {'':18s} {v:18s} {c:>3d}/{total:<3d}")
            # 建議規則：若眾數 ≥60% 且非 canonical，建議更新
            if mode_pct >= 60 and mode_val != canonical_val and mode_val != "__missing__":
                suggestions.setdefault(selector, {})[prop] = mode_val
    print(f"{'='*88}\n")
    return suggestions


def main():
    dist, canonical = collect_distribution()
    suggestions = print_distribution(dist, canonical)

    print(f"\n=== 建議更新（眾數 ≥60% 且偏離 canonical）===")
    if not suggestions:
        print("  無 — 所有 selector 的眾數都是 canonical 值（或眾數 <60%）")
        return
    for sel, props in suggestions.items():
        for prop, val in props.items():
            old = canonical.get(sel, {}).get(prop, "—")
            print(f"  {sel} {prop}: {old} → {val}")

    # 寫建議到 /tmp 不直接覆蓋
    suggested_canonical = json.loads((PORTAL / "deckcheck" / "canonical" / "tokens.json").read_text(encoding="utf-8"))
    for sel, props in suggestions.items():
        for prop, val in props.items():
            suggested_canonical["selectors"].setdefault(sel, {})[prop] = val
    suggested_canonical.setdefault("_meta", {})["fork_note"] = "B 步驟更新：眾數 ≥60% 且偏離原 skill 即升為新 canonical"
    Path("/tmp/tokens-suggested.json").write_text(
        json.dumps(suggested_canonical, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n  完整建議寫入：/tmp/tokens-suggested.json")


if __name__ == "__main__":
    main()

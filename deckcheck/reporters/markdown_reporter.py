"""Markdown reporter —— 跨 deck summary table + per-deck 細項。"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from ..model import Finding, Severity, aggregate_by_severity, aggregate_by_checker, aggregate_by_deck


SEV_EMOJI = {"BLOCKER": "🛑", "ERROR": "⚠️ ", "WARN": "·  ", "INFO": "ℹ️ "}


def write(findings: list[Finding], out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# Deckcheck Report")
    lines.append(f"")
    lines.append(f"> Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"")

    sev = aggregate_by_severity(findings)
    chk = aggregate_by_checker(findings)
    by_deck = aggregate_by_deck(findings)

    # Summary
    lines.append(f"## Summary")
    lines.append(f"")
    lines.append(f"- **Total findings**: {len(findings)}")
    lines.append(f"- **Decks scanned**: {len(by_deck)}")
    lines.append(f"- **By severity**: 🛑 BLOCKER `{sev['BLOCKER']}` · ⚠️ ERROR `{sev['ERROR']}` · · WARN `{sev['WARN']}` · ℹ️ INFO `{sev['INFO']}`")
    lines.append(f"")

    if chk:
        lines.append(f"### By checker")
        lines.append(f"| Checker | Count |")
        lines.append(f"|---|---:|")
        for c, n in sorted(chk.items(), key=lambda x: -x[1]):
            lines.append(f"| `{c}` | {n} |")
        lines.append(f"")

    # Worst decks
    if by_deck:
        lines.append(f"## Decks ranked by issue count")
        lines.append(f"")
        lines.append(f"| Deck | BLOCKER | ERROR | WARN | INFO | Total |")
        lines.append(f"|---|---:|---:|---:|---:|---:|")
        for d, fs in sorted(by_deck.items(), key=lambda x: -len(x[1])):
            sc = aggregate_by_severity(fs)
            lines.append(f"| `{d}` | {sc['BLOCKER']} | {sc['ERROR']} | {sc['WARN']} | {sc['INFO']} | {len(fs)} |")
        lines.append(f"")

    # Per-deck details (only decks with BLOCKER or ERROR)
    bad = {d: fs for d, fs in by_deck.items()
           if any(Severity(f.severity).rank() >= 3 for f in fs)}
    if bad:
        lines.append(f"## BLOCKER + ERROR details")
        lines.append(f"")
        for d, fs in sorted(bad.items()):
            lines.append(f"### `{d}`")
            lines.append(f"")
            for f in sorted(fs, key=lambda x: (-Severity(x.severity).rank(), x.slide or 0)):
                if Severity(f.severity).rank() < 3: continue
                slide_s = f"p{f.slide:02d}" if f.slide else "—"
                emoji = SEV_EMOJI[f.severity]
                lines.append(f"- {emoji} **{f.severity}** · `{f.code}` · {slide_s} · {f.message}")
                if f.actual is not None or f.expected is not None:
                    lines.append(f"   - actual: `{f.actual}` · expected: `{f.expected}`")
            lines.append(f"")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  → Markdown written: {out}")

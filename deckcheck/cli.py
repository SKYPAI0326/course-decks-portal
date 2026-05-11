"""check-deck.py 主入口 —— 接 CLI 參數、調 runner、輸出 reporter。"""
from __future__ import annotations
import argparse
import asyncio
import sys
from pathlib import Path
from .config import PROFILES, DECKS_PARENT, THRESHOLDS, discover_deck_files, discover_changed_files
from .runner import run_profile
from .model import Severity, aggregate_by_severity, aggregate_by_checker, aggregate_by_deck


def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="check-deck",
        description="統一檢查框架 for 弄一下工作室講師簡報集（95 deck × 2,389 slides）")
    ap.add_argument("target", nargs="?", help="單檔/單 dir；不給就用 --all 或 --changed")
    ap.add_argument("--profile", choices=list(PROFILES), default="fast",
                    help="fast(static only) / normal / full / visual (預設 fast)")
    ap.add_argument("--all", action="store_true", help="掃所有 *-decks")
    ap.add_argument("--changed", action="store_true", help="只掃 git status 顯示的 changed files")
    ap.add_argument("--repo", action="append", help="只掃指定 repo（可重複），如 --repo gtm-decks")
    ap.add_argument("--reporter", action="append", default=None,
                    help="輸出格式：json / markdown / html / stdout (預設 stdout) 可重複")
    ap.add_argument("--out", default="reports", help="report 輸出目錄（預設 reports/）")
    ap.add_argument("--threshold", action="append", default=[],
                    help="覆蓋 threshold，如 --threshold contrast_blocker=2.5")
    ap.add_argument("--quiet", action="store_true", help="只報 BLOCKER + ERROR")
    ap.add_argument("--fail-on", default="BLOCKER",
                    choices=["BLOCKER", "ERROR", "WARN", "INFO", "none"],
                    help="exit 1 條件（預設 BLOCKER）")
    return ap.parse_args(argv)


async def amain():
    args = parse_args()

    # 解析 thresholds 覆蓋
    th = dict(THRESHOLDS)
    for kv in args.threshold:
        if "=" not in kv: continue
        k, v = kv.split("=", 1)
        try: th[k] = float(v)
        except ValueError: th[k] = v

    # 收集 files
    if args.changed:
        files = discover_changed_files(DECKS_PARENT)
    elif args.all:
        files = discover_deck_files(DECKS_PARENT, only_repos=args.repo)
    elif args.target:
        target = Path(args.target).resolve()
        if target.is_file():
            files = [target]
        else:
            files = [p for p in target.rglob("*.html")
                    if "assets" not in p.parts and p.name not in ("index.html", "_base.html")]
    else:
        print("[error] 須指定 target 或 --all 或 --changed", file=sys.stderr)
        sys.exit(2)

    if not files:
        print("[runner] 沒有 deck 可掃")
        sys.exit(0)

    # 跑 profile
    findings = await run_profile(args.profile, files,
                                 decks_parent=DECKS_PARENT,
                                 thresholds=th,
                                 quiet=args.quiet)

    # 套用 deckcheck.yml allowed_findings
    from .exceptions import apply_exceptions
    findings, allowed_n = apply_exceptions(findings, quiet=args.quiet)

    # 預設 stdout reporter
    reporters = args.reporter or ["stdout"]
    out_dir = Path(args.out)
    if any(r != "stdout" for r in reporters):
        out_dir.mkdir(parents=True, exist_ok=True)
    for r in reporters:
        if r == "stdout":
            _print_stdout(findings, args.quiet)
        elif r == "json":
            from .reporters.json_reporter import write
            write(findings, out_dir / "deckcheck.json")
        elif r == "markdown":
            from .reporters.markdown_reporter import write
            write(findings, out_dir / "deckcheck.md")
        elif r == "html":
            from .reporters.html_reporter import write
            write(findings, out_dir / "deckcheck.html")

    # exit code
    if args.fail_on != "none":
        threshold = Severity[args.fail_on].rank()
        bad = sum(1 for f in findings if Severity(f.severity).rank() >= threshold)
        sys.exit(1 if bad else 0)
    sys.exit(0)


def _print_stdout(findings: list, quiet: bool):
    sev = aggregate_by_severity(findings)
    chk = aggregate_by_checker(findings)
    by_deck = aggregate_by_deck(findings)

    print(f"\n= Deckcheck 結果 =")
    print(f"  Decks scanned:     {len(by_deck) if by_deck else 0}")
    print(f"  Total findings:    {len(findings)}")
    print(f"  BLOCKER: {sev['BLOCKER']:4d}  ERROR: {sev['ERROR']:4d}  WARN: {sev['WARN']:4d}  INFO: {sev['INFO']:4d}")
    if chk:
        print(f"\n  By checker:")
        for c, n in sorted(chk.items(), key=lambda x: -x[1]):
            print(f"    {c:32s} {n:4d}")
    if not quiet and by_deck:
        print(f"\n  By deck (top 10):")
        ranked = sorted(by_deck.items(), key=lambda x: -len(x[1]))[:10]
        for deck, fs in ranked:
            sev_count = aggregate_by_severity(fs)
            print(f"    {deck:50s} B{sev_count['BLOCKER']:2d} E{sev_count['ERROR']:2d} W{sev_count['WARN']:3d}")
    elif by_deck:
        bad_decks = {d: fs for d, fs in by_deck.items() if any(Severity(f.severity).rank() >= 3 for f in fs)}
        if bad_decks:
            print(f"\n  Bad decks (B+E only):")
            for d, fs in sorted(bad_decks.items(), key=lambda x: -len(x[1])):
                sc = aggregate_by_severity(fs)
                print(f"    {d:50s} B{sc['BLOCKER']:2d} E{sc['ERROR']:2d}")


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()

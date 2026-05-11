#!/usr/bin/env python3
"""check-deck.py · thin wrapper for deckcheck CLI

用法：
  python3 check-deck.py --all                      # 所有 deck，fast profile（純靜態）
  python3 check-deck.py --all --profile normal     # + browser checks
  python3 check-deck.py --all --profile full       # 全部 checker
  python3 check-deck.py --changed                  # 只看 git status 改動
  python3 check-deck.py path/to/deck.html          # 單檔
  python3 check-deck.py --all --reporter html --reporter json --out reports/
  python3 check-deck.py --all --quiet              # 只看 BLOCKER + ERROR
  python3 check-deck.py --all --threshold contrast_blocker=2.5

Profiles:
  fast   - static lint + pipeline contract + token drift（秒級）
  normal - + Playwright overflow + contrast（分鐘級）
  full   - = normal（MVP；Phase 2 加 visual / mobile gesture / RAF drain）
  visual - 視覺 regression（Phase 2 留白）

Exit codes:
  0 - 全綠或 fail-on 條件未滿足
  1 - 有 fail-on 級的 finding（預設 BLOCKER）
  2 - CLI 用法錯誤
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from deckcheck.cli import main

if __name__ == "__main__":
    main()

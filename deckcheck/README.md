# Deckcheck v0.1 (MVP)

> 統一檢查框架 for 弄一下工作室講師簡報集（95 deck × 2,389 slides）  
> 採納：Codex consult `3f4115a3` 設計 · MVP 完成日 2026-05-11  
> SPEC：[`SPEC-deckcheck.md`](../SPEC-deckcheck.md)

## 用法

```bash
cd 課程簡報/course-decks-portal

# 全站 fast profile（純靜態，秒級）
python3 check-deck.py --all --profile fast

# 全站 normal profile（含 browser overflow + contrast，分鐘級）
python3 check-deck.py --all --profile normal

# 出 3 種報表到 reports/
python3 check-deck.py --all --profile fast \
  --reporter markdown --reporter html --reporter json --out reports

# 只看 BLOCKER + ERROR
python3 check-deck.py --all --profile fast --quiet

# 單檔
python3 check-deck.py ../simple-ai-decks/index.html

# git 改動的 deck 才掃
python3 check-deck.py --changed --profile normal

# 指定 repo
python3 check-deck.py --all --repo gtm-decks --repo dm70h-decks

# 自訂 threshold
python3 check-deck.py --all --threshold contrast_blocker=2.5
```

## 5 個 checker

| Checker | 類型 | 速度 | 找什麼 |
|---|---|---|---|
| `static_lint` | 靜態啟發式 | 秒 | vh 加總估算 overflow（偽陽性高，降為 INFO） |
| `static_pipeline_contract` | 靜態 grep | 秒 | mobile-reader / D1 overlay / pipeline JS 等契約缺失 |
| `static_tokens` | 靜態 + canonical diff | 秒 | 跨 deck token 漂移（vs `canonical/tokens.json`） |
| `browser_overflow` | Playwright | 分鐘 | 真實 frame.scrollHeight 量測 |
| `browser_contrast` | Playwright + WCAG | 分鐘 | 文字對比度（主動觸發 Motion 後測） |

## Profiles

- `fast` — 3 個 static checker
- `normal` — fast + 2 browser checker
- `full` — 同 normal（Phase 2 加 visual / mobile gesture / RAF drain）
- `visual` — 留白（Phase 2）

## Severity

- `BLOCKER` — 內容不可見 / 連結 404 / deck 無法載入（exit 1）
- `ERROR` — 明顯違規但不阻斷上課
- `WARN` — 風險或漂移
- `INFO` — 統計 / 建議

## 跨 deck 一致性 Audit

`canonical/tokens.json` 從 `~/.claude/skills/guizang-ppt-skill/assets/template.html` 抽出，
記錄 14 個核心 selector 的官方 token 值。

**第一次跑全站（MVP 完成）發現**：
- 0 BLOCKER（全站無致命問題）
- 94 TOKEN_DEVIATION ERROR — 主要是 `.h-hero / .h-xl / .lead / .kicker` 在不同 deck 偏離 canonical
  - 證實 Codex 早預測的「跨 deck 規範漂移」是真實存在的長尾問題
  - 範例：`ai-workshop-decks/s3` `.h-hero font-size: 8.6vw (canonical 10vw, +14%)`

下一步可選：
1. 把所有 deck 同步到 canonical（risk: 影響投影視覺）
2. 更新 canonical 反映「實際使用值」
3. 為某 deck/selector 加 `allowed_findings` 例外（含 expires）

## 報表位置

執行後在 `reports/` 內：
- `deckcheck.html` — 互動式 finding browser（搜尋 + 篩選）
- `deckcheck.md` — 跨 deck summary table + per-deck 細項
- `deckcheck.json` — 機器可讀完整 dump

## 與舊工具關係

舊 3 個獨立工具仍能用（backward compat）：
- `lint-deck.py` — 已被 `static_lint` checker 封裝
- `verify-deck.py` — 已被 `browser_overflow` checker 封裝
- `verify-contrast.py` — 已被 `browser_contrast` checker 封裝

未來會逐步 deprecate，但 MVP 階段保留。

## Phase 2（已完成 a / b / c）

✅ **2a · Visual regression**：`visual_regression` checker — Playwright 截 5 個 golden slide × 2 viewport，存 baseline 後續 diff（pixel diff > 0.5% WARN, > 2% ERROR）。第一次跑自動建 baseline。
- 觸發：`--profile visual` 或 `--profile full`
- baseline 位置：`deckcheck/baselines/visual/<deck_id>__<filename>/<viewport>/p<NN>.png`

✅ **2b · Mobile checkers**：
- `mobile_gesture` — 393×852 模擬手機 viewport，驗 `mobile-reader` 觸發 + scroll 不被攔
- `raf_drain` — instrument requestAnimationFrame，3 秒內 > 60 = ERROR (GPU 浪費)
- 觸發：`--profile mobile` 或 `--profile full`

✅ **2c · GitHub Actions workflow**：`.github/workflows/deckcheck.yml`
- push/PR 自動跑 fast profile（artifact 30 天）
- workflow_dispatch 可手動跑 normal/full/visual/mobile

### Phase 2 待做

- WebGL fallback checker（Safari 14- 偵測）
- token autofix（自動把 deviation 推回 canonical）
- cross-repo inventory dashboard
- 整合 visual diff gallery（HTML report 嵌入 baseline vs current 並列圖）

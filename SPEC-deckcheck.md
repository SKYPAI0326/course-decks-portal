# Deckcheck SPEC — 講師簡報集統一檢查框架

> 來源：Codex consult `3f4115a3` (2026-05-10) · verdict accepted  
> 狀態：**設計藍圖** — MVP 待實作  
> 範圍：16 GitHub repo · 95 deck · 2,389 slides · 排除 course-catalog-2026

## 為什麼需要

過去 8 小時 8+ 輪迭代發現 5 種反覆 bug pattern：
1. Layout overflow（slide > 100vh 被切）
2. 低對比（opacity 累乘到看不見、cascade 卡 0.15）
3. 跨 deck 規範漂移（同 class 不同 deck 不同數值）
4. Motion One 動畫狀態（pipeline strict / cascade inactive）
5. 手機/響應式失效

每次都「user 截圖 → 我修一個 → 過陣子又冒新的」，需要根本性檢查機制取代逐 case 補釘。

## 現有工具（要被收斂）

| 工具 | 覆蓋 |
|---|---|
| `lint-deck.py` | 純 Python 靜態 lint，估算 vh 加總（30-50% 偽陽性） |
| `verify-deck.py` | Playwright 量 OVERFLOW |
| `verify-contrast.py` | Playwright + WCAG ratio + 主動觸發 Motion One |

3 工具獨立、輸出格式不同、threshold 各設、無法 CI 統一。

---

## 採納設計（Codex 完整原文）

以下是我會採用的設計：把現在三個碎片工具收斂成「單一 CLI + checker plugin + 統一 finding schema + baseline/manifest」；不要一開始追求全自動修復，先建立可信的檢查證據鏈，否則 95 deck 會被 false positive 淹沒。

**核心判斷**

最重要的不是再多寫幾支 checker，而是先統一四件事：

1. 每個 deck 的身份：repo、course、deck id、template version、sentinel version。
2. 每個 finding 的格式：位置、證據、嚴重度、threshold、是否可 autofix。
3. 每個 checker 的執行層級：fast / normal / full / visual。
4. 每次檢查的 baseline：這次是「比 canonical 偏離」還是「比上次 commit 退步」。

---

**A. 總體架構**

建議做成一個 `deckcheck/` Python package，而不是繼續堆獨立 script。

```txt
course-decks-portal/
  deckcheck/
    __init__.py
    cli.py                    # check-deck entry point
    config.py                 # threshold / repo / deck discovery
    manifest.py               # deck inventory parser
    model.py                  # Finding / Evidence / Severity schema
    runner.py                 # checker orchestration
    reporters/
      json.py
      markdown.py
      html.py
      junit.py                # optional for CI annotations
    checkers/
      static_meta.py
      static_assets.py
      static_legacy_classes.py
      static_tokens.py
      static_pipeline_contract.py
      browser_overflow.py
      browser_contrast.py
      browser_motion_state.py
      browser_mobile_reader.py
      browser_links.py
      visual_regression.py
    canonical/
      tokens.json
      selectors.json
      sentinel.json
      legacy-classes.json
    baselines/
      visual/
      findings/
  check-deck.py               # thin wrapper: python -m deckcheck.cli
  deckcheck.yml               # project thresholds + deck roots
```

Module relationship:

```txt
check-deck.py
  -> loads deckcheck.yml
  -> discovers DeckManifest[]
  -> selects Checker[] by profile: fast | normal | full | visual
  -> each checker emits Finding[]
  -> runner normalizes severity + thresholds
  -> reporters write:
       reports/deckcheck.json
       reports/deckcheck.md
       reports/deckcheck.html
       reports/junit.xml
```

建議 entry point：

```bash
python3 check-deck.py --profile fast --changed
python3 check-deck.py --profile normal --deck path/to/deck.html
python3 check-deck.py --profile full --all
python3 check-deck.py --profile visual --baseline main
```

---

**Finding Schema**

所有 checker 都輸出同一種 finding。這是整套系統的地基。

```json
{
  "deck_id": "n8n-m03-intro",
  "repo": "course-n8n",
  "slide": 12,
  "checker": "browser_contrast",
  "severity": "ERROR",
  "code": "CONTRAST_TEXT_LOW",
  "message": "Text contrast ratio 2.1 below 4.5",
  "selector": ".slide.active .muted",
  "actual": 2.1,
  "expected": ">=4.5",
  "evidence": {
    "screenshot": "reports/evidence/n8n-m03/slide-12.png",
    "css": "opacity: .15; color: #888; background: #fff"
  },
  "autofix": false
}
```

Severity 建議：

- `BLOCKER`：內容不可見、被切掉、連結 404、deck 無法載入。
- `ERROR`：明顯違規但不一定阻斷上課，例如低對比、metadata 缺。
- `WARN`：有風險或規範漂移，例如 token 偏離 5%。
- `INFO`：統計、建議、非阻斷。

---

**Threshold 管理**

用三層覆寫，避免一刀切：

```yaml
profiles:
  fast:
    include: [static_*]
  normal:
    include: [static_*, browser_overflow, browser_contrast, browser_motion_state]
  full:
    include: [static_*, browser_*]
  visual:
    include: [visual_regression]

thresholds:
  global:
    overflow_px_blocker: 50
    contrast_body: 4.5
    contrast_large: 3.0
    token_deviation_warn_pct: 3
    token_deviation_error_pct: 8
  by_template_version:
    guizang-v4:
      overflow_px_blocker: 30
  by_deck:
    n8n-m03-intro:
      allowed_findings:
        - code: TOKEN_DEVIATION
          selector: ".h-hero"
          expires: "2026-06-01"
```

重點：允許 exception，但每個 exception 必須有 `expires`，不然會變永久債。

---

**B. Check Matrix**

| 檢查項 | 方法 | 嚴重度 | 預設 threshold | 修復 |
|---|---:|---:|---:|---|
| Layout overflow | Playwright 量 `scrollHeight - clientHeight`，逐 slide | BLOCKER | `>50px`，新模板可降到 `>30px` | 手動為主 |
| Hidden clipping | Playwright 找 bbox 超出 viewport 且父層 `overflow:hidden` | BLOCKER | 任一主要文字被裁切 | 手動 |
| Contrast | Playwright computed style + WCAG ratio，含 opacity chain | ERROR/BLOCKER | body `<4.5`，large `<3.0`，ratio `<2` BLOCKER | 半自動 |
| Motion One opacity state | Playwright 觸發 slide active / reader / pipeline 狀態後量 opacity | BLOCKER | active slide 文字 opacity `<0.85` | 手動 |
| Cascade inactive leakage | Playwright 切 slide 後檢查 visible text 不應為 `0` 或 `.15` | ERROR | active text opacity `<0.85` | 手動 |
| Mobile reader CSS contract | 靜態 grep + CSS parser | ERROR | 必須有 reader mode selectors、`#deck` scroll override | 半自動 |
| Mobile reader JS contract | 靜態 AST / grep pipeline flags | ERROR | `readerMode`、strict/self-read 分支存在 | 手動 |
| Mobile viewport overflow | Playwright iPhone SE / 390px / 430px | BLOCKER | horizontal scroll `>8px` 或 content clipped | 手動 |
| Chrome-link href | 靜態抽 href + HTTP/local file check | ERROR | 404/empty href；external timeout WARN | 可自動報 |
| SEO metadata | HTML parser | WARN/ERROR | title、description、og:title、og:image 缺 | 可自動補骨架 |
| Image exists | HTML parser + filesystem / URL check | ERROR | missing asset | 手動 |
| Image alt | HTML parser | WARN | meaningful img alt 空；decorative 可 `alt="" data-decorative` | 半自動 |
| Legacy classes | 靜態 selector scan | WARN/ERROR | 命中 `compact-landscape`、`dense-7` 等 | 可自動替換部分 |
| Sentinel version | HTML parser / comment marker | ERROR | 與 canonical `sentinel.json` 不一致 | 可自動 patch |
| Template token drift | CSS parser + canonical token diff | WARN/ERROR | numeric diff `>3% WARN`, `>8% ERROR` | 半自動 |
| Utility class divergence | CSS parser group by selector/property | WARN | 同 selector 跨 deck 超過 2 種值 | 手動或批次 patch |
| Font fallback chain | CSS parser + Playwright font check | WARN | 缺 CJK fallback 或 webfont failed | 半自動 |
| WebGL fallback | 靜態 JS scan + Playwright disable WebGL | WARN/ERROR | canvas blank 且無 fallback ERROR | 手動 |
| RAF/GPU drain reader mode | Playwright monkey patch `requestAnimationFrame` count | WARN | reader mode 10s 內 RAF `>60` | 手動 |
| Touch/native scroll conflict | Playwright mobile gesture test | WARN/ERROR | swipe 阻斷 vertical scroll | 手動 |
| Visual diff | Playwright screenshot + pixelmatch | WARN/ERROR | changed pixels `>0.5% WARN`, `>2% ERROR` | 手動 |

---

**C. 跨 Deck 一致性 Audit**

我會把這件事單獨當成一個子系統：`static_tokens.py` + `canonical/tokens.json`。

Canonical 來源不要人工手抄，建議從 guizang-ppt-skill template 抽一次，再 commit 成版本化 JSON：

```json
{
  "template": "guizang-v4",
  "version": "2026-05-10",
  "tokens": {
    ".h-hero": {
      "font-size": "clamp(3rem, 10vw, 8rem)",
      "line-height": "0.95"
    },
    ".callout": {
      "padding": "1.2rem",
      "border-left": "4px solid var(--ink)"
    },
    ".rowline": {
      "display": "grid",
      "gap": "0.8rem"
    }
  }
}
```

掃描做法：

1. 用 CSS parser，不用 regex。Python 可用 `tinycss2` + `cssselect2`；若要處理 inline style，也一起 parse。
2. 每個 deck 產出 `DeckStyleFingerprint`：
   - selector
   - property
   - value
   - normalized numeric value
   - source line
   - template/sentinel version
3. 跟 canonical diff：
   - exact diff：字串不同。
   - numeric diff：`10vw` vs `11vw` 算 `+10%`。
   - semantic diff：`clamp(3rem,10vw,8rem)` vs `clamp(3rem,11vw,8rem)` 只標中間 preferred value 偏離。
4. 報表按「token 熱點」聚合，而不是只按 deck：
   - `.h-hero font-size`：95 decks 中 78 canonical、12 為 `11vw`、5 為 `9vw`。
   - 列出 repo/deck/line/deviation。
5. Patch 策略：
   - Phase 1：只報，不 patch。
   - Phase 2：對 exact canonical class 可 `--fix-token .h-hero font-size`。
   - 不自動 patch 複雜 layout class，尤其是 deck 曾局部調過的頁面。

偏離報表示例：

```txt
TOKEN_DEVIATION ERROR .h-hero font-size
canonical: clamp(3rem, 10vw, 8rem)
course-n8n/m03.html: clamp(3rem, 11vw, 8rem)  +10%
course-make/m07.html: clamp(3rem, 9vw, 8rem)   -10%
recommendation: review manually or run --fix-token .h-hero font-size
```

關鍵原則：一致性 audit 應該先抓「共用 selector 的設計漂移」，不要一開始追逐所有 CSS 差異。所有 inline one-off CSS 都掃，但只對 canonical selectors 發 blocker/error。

---

**D. 視覺 Regression 策略**

不要對 2,389 slides 全量截圖當日常檢查，成本太高。分三種 baseline。

1. Golden slide baseline  
   每個 deck 類型選代表頁：cover / agenda / quote / pipeline / table / dense content / closing。每 deck 約 5-8 張。

2. Changed slide baseline  
   pre-push 只截 git diff 影響的 deck，若能從 HTML diff 推出 slide index，就只截那些 slide 前後各一頁。

3. Weekly full baseline  
   每週全量跑 95 deck，產 HTML gallery，人工看 top diff。

必測 viewport：

```txt
desktop: 1440x900 DPR 1
projector: 1920x1080 DPR 1
mobile-small: 375x667 DPR 2
mobile-modern: 390x844 DPR 3
tablet: 768x1024 DPR 2
```

DPR 不需要每次全跑。日常 `desktop + mobile-small`；weekly 再跑完整矩陣。

Baseline 存放建議：

- 一人公司、本地優先：先放 repo 外共用目錄，例如 `~/.cache/deckcheck/baselines/`，避免 Git 膨脹。
- 對真正穩定的 golden slides：可檢入 Git LFS 或獨立 `deck-baselines` repo。
- PR/GitHub Actions 若啟用：artifact 上傳 diff gallery，不把所有 PNG commit 回主 repo。

Visual diff threshold：

```yaml
visual:
  changed_pixel_warn_pct: 0.5
  changed_pixel_error_pct: 2.0
  ignore_regions:
    - selector: "canvas.webgl-bg"
    - selector: ".clock,.timestamp"
  per_slide_type:
    cover:
      error_pct: 1.0
    dense:
      error_pct: 3.0
```

WebGL / animated background 要 mask 掉，否則 visual diff 會不可用。

---

**E. CI / Git Hook 整合**

你是一人公司，所以我會設計成「本地 hooks 為主，GitHub Actions 作為保險，不作為日常阻塞」。

Pre-commit：秒級，只跑 changed files。

```bash
python3 check-deck.py --profile fast --changed
```

包含：

- HTML parse 是否成功
- SEO metadata
- image path exists
- legacy class
- sentinel version
- mobile reader CSS/JS contract
- token drift 靜態掃描
- chrome-link 空值或本地不存在

不跑 Playwright，不打外部 URL。

Pre-push：分鐘級，跑 changed deck 的 browser checks。

```bash
python3 check-deck.py --profile normal --changed --report html,json
```

包含：

- overflow desktop
- contrast
- Motion One active/reader/pipeline states
- mobile viewport smoke test
- local href check
- selected screenshots

Weekly cron：重檢查。

```bash
python3 check-deck.py --profile full --all
python3 check-deck.py --profile visual --sample golden
```

產出：

- `reports/deckcheck-weekly.html`
- `reports/token-drift.html`
- `reports/visual-gallery.html`
- `reports/trend.json`

GitHub Actions：建議「有跨 repo 共用模板改動」或「要發佈課程前」才啟用。用 matrix 跑 repo/deck group，輸出 artifact。不建議一開始讓 GH Actions 阻擋所有 commit，因為 Playwright + fonts + canvas 在 CI 上 false positive 會偏多。

---

**MVP vs Phase 2**

MVP 先做這 6 個，最能止血：

1. `check-deck.py` 統一 entry point。
2. 統一 `Finding` JSON schema。
3. 把現有 `verify-deck.py`、`lint-deck.py`、`verify-contrast.py` 包成 checker。
4. 新增 `static_pipeline_contract`：reader mode / strict / self-read contract。
5. 新增 `static_tokens`：canonical selector drift audit。
6. HTML + Markdown report，支援 `--changed`。

Phase 2：

1. visual regression gallery。
2. mobile gesture / touch conflict checker。
3. RAF/GPU drain checker。
4. WebGL fallback checker。
5. token autofix。
6. cross-repo inventory dashboard。
7. GitHub Actions artifact 報表。

不要 MVP 就做 visual diff 全量。它很有價值，但 baseline 管理會拖慢整個檢查框架落地。

---

**可行性風險**

最大風險是 false positive，不是漏報。控制方式：

- 所有 checker 都要有 `profile`，不要每次都跑 full。
- 所有 exception 必須有 `expires`。
- 靜態 lint 只當 WARN，除非是明確契約缺失。
- Playwright 證據要附 screenshot / selector / computed style，否則 finding 不可行動。
- token drift 先只檢 canonical selectors，不掃全 CSS。
- visual diff 必須支援 mask 動態區域，否則會失控。
- 外部 URL 檢查不要放 pre-commit，只放 pre-push 或 weekly。
- mobile 100vh 問題要用真實 viewport 行為驗證，單靠 CSS grep 不可靠。

**我的建議路線**

先實作 MVP，目標不是一次抓完所有 bug，而是讓每次檢查都輸出同一份報表、同一套 severity、同一個 deck inventory。等這層穩了，再加 visual regression 和 weekly full audit。這樣 95 deck 的問題會從「截圖救火」變成「有趨勢、有分級、有證據、有例外到期日」的工程流程。


---

## 實作優先順序（MVP）

按 Codex 建議分兩階段。

### MVP（先做）
1. `check-deck.py` 統一 entry point + `deckcheck/` package 骨架
2. 統一 `Finding` JSON schema（model.py）
3. 把現有 3 個 verify 包成 checker（不重寫，封裝呼叫）
4. **新增 `static_pipeline_contract`** — 檢 reader / strict / self-read 契約
5. **新增 `static_tokens`** — canonical drift audit（最痛點）
6. HTML + Markdown reporter，支援 `--changed`

### Phase 2（之後）
7. visual regression gallery
8. mobile gesture / touch conflict checker
9. RAF/GPU drain checker
10. WebGL fallback checker
11. token autofix
12. cross-repo inventory dashboard
13. GitHub Actions artifact 報表

---

## 此 SPEC 與既有規範的關係

- **`README.md`** — portal 對外文檔（live URL、deck 清單、設計基準）
- **`SPEC-deckcheck.md`** — 本檔，內部開發藍圖
- **`lint-deck.py` / `verify-deck.py` / `verify-contrast.py`** — MVP 階段保留並繼續用，MVP 完成後 deprecate

## Codex 諮詢紀錄

| Call ID | 議題 | Verdict |
|---|---|---|
| `0e6bc391` | mobile-reader 架構初次設計 | accepted |
| `d4a34d90` | mobile-reader v6 全盤審計 | accepted |
| `891fe83a` | simple-ai revert 後的 review | accepted |
| `5ac1020f` | 手機支援是否有不可解障礙 | accepted（D1 採納） |
| `3f4115a3` | **Deckcheck 統一框架設計（本 SPEC 來源）** | **accepted** |

---

## 變更紀錄

| 日期 | 版本 | 變更 |
|---|---|---|
| 2026-05-10 | v1.0 | 初版（採納 Codex 3f4115a3 完整設計） |

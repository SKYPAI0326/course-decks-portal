# 弄一下工作室 · 講師簡報集總入口

> 所有課程的橫向翻頁網頁簡報集合 · 跨課程一致設計基準 · **單一 repo 統一管理**

線上：https://skypai0326.github.io/course-decks-portal/

---

## 結構

2026-05-16 起，原本散在 17 個獨立 GitHub repo 的課程簡報，全部合併進**本 repo**，
依課程分子資料夾管理。`index.html` 是總入口頁，連結各課程子資料夾。

```
course-decks-portal/
├── index.html              ← 總入口頁
├── {course}-decks/         ← 17 個課程簡報子資料夾，各含 index.html + deck HTML + assets
└── deckcheck/ · *.py       ← 排版檢查工具
```

舊的 17 個獨立 `*-decks` repo 已設為 archived（唯讀封存）。
對外提案型錄 `course-catalog-2026` 維持獨立 repo：https://skypai0326.github.io/course-catalog-2026/

---

## 課程清單（17 課程 · 95 deck · 2389 頁 · 434.5 hr）

| 課程資料夾 | 課程 | 時數 | Deck | 頁數 | 主題色 |
|---|---|---:|---:|---:|---|
| [gen-ai-140h-decks](gen-ai-140h-decks/) | **生成式 AI 職訓 140hr（旗艦）** | **140hr** | **20** | **697** | 牛皮紙 |
| [dm70h-decks](dm70h-decks/) | 數位行銷人才培訓 | 70hr | 10 | 328 | 牛皮紙 |
| [gen-ai-36h-decks](gen-ai-36h-decks/) | 生成式 AI 工作應用班 | 36hr | 7 | 184 | 靛藍瓷 |
| [ipas-ai-beginner-decks](ipas-ai-beginner-decks/) | iPAS AI 應用規劃師初級研習 | 30hr | 5 | 132 | 牛皮紙 |
| [ntub-seo-ga4-decks](ntub-seo-ga4-decks/) | NTUB · 數位行銷實務 SEO × GA4 | 30hr | 10 | 200 | 靛藍瓷 |
| [ntub-gtm-adtech-decks](ntub-gtm-adtech-decks/) | NTUB · GTM × 廣告科技 | 30hr | 10 | 202 | 靛藍瓷 |
| [gtm-decks](gtm-decks/) | GTM 實務演練 | 21hr | 7 | 156 | 靛藍瓷 |
| [ai-workshop-decks](ai-workshop-decks/) | AI 實務全攻略 | 18hr | 6 | 134 | 靛藍瓷 |
| [gemini-ai-decks](gemini-ai-decks/) | Gemini 零代碼 AI 實戰 | 15hr | 5 | 112 | 靛藍瓷 |
| [line-stickers-decks](line-stickers-decks/) | AI 自製 LINE 貼圖 | 12hr | 2 | 66 | 牛皮紙 |
| [n8n-decks](n8n-decks/) | n8n 自動化實戰 | 9.5hr | 1 | 36 | 森林墨 |
| [gen-image-decks](gen-image-decks/) | 商業用圖片生成 | 8hr | 1 | 32 | 牛皮紙 |
| [office-ai-decks](office-ai-decks/) | 辦公室 AI 工具實務 | 6hr | 1 | 28 | 牛皮紙 |
| [office-ai-cases-decks](office-ai-cases-decks/) | 辦公室 AI 工具案例應用 | 6hr | 6 | — | 墨水經典 |
| [prompt-basic-decks](prompt-basic-decks/) | 從「問 AI」到「交辦 AI」 | 6hr | 1 | 32 | 靛藍瓷 |
| [simple-ai-decks](simple-ai-decks/) | 創業 AI 實戰 | 3hr | 1 | 22 | 森林墨 |
| [ccs-foundations-decks](ccs-foundations-decks/) | CCS GenAI Foundations 認證 | 自學 | 1 | 28 | 靛藍瓷 |

---

## 設計基準（所有 deck 共用）

- 樣板：guizang-ppt-skill
- 主題色：5 套預設（墨水經典 / 靛藍瓷 / 森林墨 / 牛皮紙 / 沙丘）
- 字型：Noto Serif SC + Noto Sans SC + Playfair Display + IBM Plex Mono
- 改良：em 中文螢光筆 / mobile-fix B+C / chrome-link（含 ★ starred 變體）/ Duration meta-row / Contact email
- 動效：cascade / hero / quote / directional / pipeline 五種 recipe
- WebGL 雙背景 + Motion One

---

## 排版檢查機制（兩段式）

跨 95 deck × 2,389 頁規模下，靠人眼很難抓出「內容被切」「callout 太擠」這類問題。
檢查工具會自動掃描本 repo 內所有 `*-decks/` 子資料夾。

### Stage A · 靜態啟發式 lint（秒級）

```bash
python3 lint-deck.py /path/to/deck.html        # 單份
python3 lint-deck.py /path/to/{course}-decks/  # 整個課程資料夾
python3 lint-deck.py --all                     # 所有 -decks 子資料夾
python3 lint-deck.py --all --quiet --json out.json
```

- 無需依賴，純 Python
- 估算每頁元素垂直高度，>100vh 標 BLOCKER、>92vh 標 WARN
- 偽陽性率約 30-50%（estimator 有限），用於「快速濾大塊」

### Stage B · Headless 渲染驗證（分鐘級·準確）

```bash
pip install playwright && playwright install chromium
python3 verify-deck.py /path/to/deck.html
python3 verify-deck.py --all --quiet --json overflow.json
python3 verify-deck.py --all --shot ./shots/   # OVERFLOW 頁自動截圖
```

- 用 Playwright 在 1920×1080 渲染每頁
- 量測 `.frame.scrollHeight - .frame.clientHeight`
- ≥50px = OVERFLOW（內容真的被切），5-50px = TIGHT，<5px = OK

### 統一檢查框架 deckcheck

```bash
python3 check-deck.py --all --profile fast     # 靜態（秒級）
python3 check-deck.py --all --profile normal   # + browser overflow/contrast
```

詳見 `SPEC-deckcheck.md`。

### 推薦工作流

1. 寫完／修完 deck → `lint-deck.py <file>` 看是否有 BLOCKER
2. 整批生產後 → `verify-deck.py --all --quiet` 抓真正 overflow 的頁
3. 修頁 → 重跑 verify 確認 0 OVERFLOW

---

**聯繫**：sky8697@gmail.com

弄一下工作室 · 2026

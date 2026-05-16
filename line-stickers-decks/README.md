# AI 自製 LINE 貼圖 · 12hr 兩階段講師簡報集

> **弄一下工作室**｜全免費工具 · 自用導向 · 從 0 到上架的 12 小時養成
> 2 份 deck · 14 單元 · 66 頁橫向翻頁網頁簡報

這是「AI 自製 LINE 貼圖：從 0 到上架的 12 小時養成」課程的**講師講課用**簡報集。
兩階段連續課程，把「我也想做一套自己的 LINE 貼圖」從幻想變成可上架的成品。

視覺基調採 **電子雜誌 × 電子墨水（牛皮紙主題）**，衬線標題、無圖片、純文字結構。鄰居教手作的溫度，不是設計師講座的距離。

---

## 線上瀏覽

GitHub Pages 部署網址：

> https://skypai0326.github.io/line-stickers-decks/

直接開即用，無需 clone。

---

## 課程地圖

| Part | 內容 | 時數 | 單元 | 頁數 | 主線角色 | 檔案 |
|---|---|---:|---:|---:|---|---|
| Part 1 | 入門班 — 一個下午做出 8 張靜態貼圖並送審 | 4 | 6 CH + PRAC1 | 28 | 橘貓上班族 | [part1.html](part1.html) |
| Part 2 | 進階班 — 一整天升級到 24 張動態 + 訊息貼圖 | 8 | 8 CH + PRAC2 | 38 | 粉紅水母 | [part2.html](part2.html) |
| **合計** | | **12** | **14 + 2** | **66** | | |

### Part 1 內容
- CH1-1 開場 + LINE 規格 + 工具地圖
- CH1-2 角色設定 + AI 角色一致性 3 手法
- CH1-3 8 張表情產出實戰
- CH1-4 透明背景 + 規格符合
- CH1-5 Creators Market 上架實作
- CH1-6 退件 SOP + 第一階段收尾
- PRAC1 課後作業

### Part 2 內容
- CH2-1 動態貼圖原理 + APNG 規格
- CH2-2 AI 產關鍵幀技巧
- CH2-3 APNG 組裝實戰
- CH2-4 訊息貼圖含可換字
- CH2-5 24 張套組設計策略
- CH2-6 角色一致性進階
- CH2-7 多風格延伸
- CH2-8 進階上架 + 結訓
- PRAC2 課後作業

---

## 設計原則（嚴格遵守）

### 自用導向
- 不教變現 / 不講行銷 / 不討論「賣得動嗎」
- 全免費工具（Gemini / ChatGPT / Pixian / Photopea / APNG Assembler / EZGIF / Creators Market）
- 退件當常態（每份 deck 都明確告訴學員「被退是過程不是失敗」+ SOP）

### 用語規範（術語對照表）

| 禁用 | 替代 |
|---|---|
| Prompt engineering | **把話講清楚 / 寫指令** |
| Style transfer | **換風格** |
| Reference image / cref | **參考圖** |
| Frame / KeyFrame | **幀 / 關鍵動作畫面** |
| Tweening | **中間補幾張** |
| Alpha channel | **透明背景** |
| Anti-aliasing | **邊緣不要鋸齒** |
| Hallucination | **AI 畫錯 / AI 亂腦補** |
| LLM / 多模態模型 | **AI（會看圖會畫圖的那種）** |

### 禁用詞（自用課全禁）

神圖、爆款、秒過審、必紅、流量、轉換、變現、月入、被動收入、IP 經營、賦能、生態系、AI 革命

### 主線角色

- **Part 1 全程**：橘貓上班族（圓滾滾橘色虎斑貓、戴白領巾、扁平卡通風格）
- **Part 2 後半**：粉紅水母（透明粉色小水母、漸變水彩風 — 為了示範「不是只有卡通能做」）

---

## 操作方式

| 動作 | 鍵 |
|---|---|
| 翻頁 | `←` `→` / 滾輪 / 觸控滑動 / 底部圓點 |
| 索引總覽 | `Esc`（看縮圖跳頁，再按 `Esc` 退出）|
| Pipeline 互動翻頁 | `→` 逐步點亮 step（三層去背救援、APNG 組裝、24 張選題等流程頁）|
| 講義對應連結 | 每頁右上角「講義 · CHX-X ↗」開新分頁跳到主課程網站對應 .html（需密碼）|
| 全螢幕投影 | 瀏覽器全螢幕快捷鍵（Mac Safari `Ctrl+Cmd+F` / Chrome `F11`）|

**手機開**：豎屏會自動顯示「請橫向觀看」提示；旋轉橫屏即可瀏覽。

---

## 技術規格

- **單檔 HTML** · 不依賴後端，離線可跑
- **WebGL 背景** · Hero 頁的雙 shader（暗色色散 + 亮色流動）
- **Motion One 動效** · cascade / hero / quote / directional / pipeline 五種 recipe
- **Lucide 圖示** · 線性圖標 CDN
- **Google Fonts** · Noto Serif SC + Noto Sans SC + Playfair Display + IBM Plex Mono
- **手機響應式** · 豎屏提示 overlay + 字型補強

### 主題色（🍂 牛皮紙 Kraft Paper）

```css
--ink: #2a1e13;       /* 深棕墨水色 */
--paper: #eedfc7;     /* 暖米牛皮紙 */
```

源課程主色 `#b5703a` 陶土橘，牛皮紙在 5 套 guizang-ppt-skill 預設裡最貼近暖橘調 + 手作感。

---

## 製作背景

製作於 2026 年 5 月，使用 Claude Code 並行 2 個 agent 完成（Part 1 + Part 2 同時派產）。
基底樣板沿用 [dm70h-decks](https://github.com/SKYPAI0326/dm70h-decks) / [prompt-basic-decks](https://github.com/SKYPAI0326/prompt-basic-decks) / [ntub-seo-ga4-decks](https://github.com/SKYPAI0326/ntub-seo-ga4-decks) 已驗收的設計（含 em 中文友善螢光筆、mobile-fix 響應式、portrait 提示、chrome-link 講義連結）。

源課程網頁：弄一下工作室「AI 自製 LINE 貼圖：從 0 到上架的 12 小時養成」（私有教學 repo · `courses/line-stickers/`）

---

## 授權

簡報內容為弄一下工作室教學設計成果，視覺樣板基於 guizang-ppt-skill。
教學使用、研究參考歡迎引用，商業翻製請先聯繫。

**聯繫**：sky8697@gmail.com

---

**弄一下工作室** · LINE Stickers Lecturer Decks · 2026

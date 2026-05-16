# 數位行銷人才培訓 70hr · 講師簡報集

> **弄一下工作室**｜10 個模組 · 52 個單元 · 328 頁橫向翻頁網頁簡報
> Vol.01 · 2026

這是「弄一下工作室」70 小時數位行銷課程的**講師講課用**簡報集。每一份對應一個模組、可獨立打開即用，從消費者心理學起步，一路走到 AI、SEO、GA4、GTM、廣告、Email，最後收束在整合實戰專案。

視覺基調採 **電子雜誌 × 電子墨水（牛皮紙主題）**，衬線大標題、無圖片、純文字結構，在大螢幕投影也能保持閱讀層次。

---

## 線上瀏覽

GitHub Pages 部署後可直接打開（無需 clone）：

> 部署網址：https://skypai0326.github.io/dm70h-decks/

也可以直接連到任一份 deck，例如：
- M1 消費者心理學：`./m1-consumer-psychology.html`
- M5 SEO 2.0：`./m5-seo-2.html`
- M10 整合實戰：`./m10-capstone-project.html`

---

## 課程地圖

| # | 模組 | 時數 | 單元 | 頁數 | 檔案 |
|---|---|---:|---:|---:|---|
| M1 | 消費者心理學：行銷的作業系統 | 6 | 4 | 32 | [m1-consumer-psychology.html](m1-consumer-psychology.html) |
| M2 | 生成式 AI 完整體系 | 12 | 12 | 50 | [m2-genai-foundation.html](m2-genai-foundation.html) |
| M3 | 市場洞察與策略定位 | 6 | 4 | 30 | [m3-market-insight.html](m3-market-insight.html) |
| M4 | 社群行銷：注意力爭奪戰 | 7 | 5 | 32 | [m4-social-marketing.html](m4-social-marketing.html) |
| M5 | SEO 2.0：AI 時代的搜尋策略 | 10 | 6 | 42 | [m5-seo-2.html](m5-seo-2.html) |
| M6 | GA4 數據分析與決策 | 8 | 5 | 36 | [m6-ga4-analytics.html](m6-ga4-analytics.html) |
| M7 | GTM：數據追蹤工程 | 5 | 4 | 26 | [m7-gtm-tracking.html](m7-gtm-tracking.html) |
| M8 | 數位廣告與流量心理學 | 5 | 4 | 26 | [m8-digital-ads.html](m8-digital-ads.html) |
| M9 | Email 行銷與第一方數據 | 4 | 4 | 22 | [m9-email-marketing.html](m9-email-marketing.html) |
| M10 | 整合實戰專案 | 7 | 4 | 32 | [m10-capstone-project.html](m10-capstone-project.html) |
| **合計** | | **70** | **52** | **328** | |

---

## 操作方式

| 動作 | 鍵 |
|---|---|
| 翻頁 | `←` `→` / 滾輪 / 觸控滑動 / 底部圓點 |
| 索引總覽 | `Esc`（看縮圖跳頁，再按 `Esc` 退出）|
| Pipeline 互動翻頁 | `→` 逐步點亮 step（GTM 七步、JTBD 五問等流程頁）|
| 全螢幕投影 | 瀏覽器全螢幕快捷鍵（Mac Safari `Ctrl+Cmd+F` / Chrome `F11`）|

---

## 技術規格

- **單檔 HTML** · 不依賴後端，離線可跑
- **WebGL 背景** · Hero 頁的雙 shader（暗色色散 + 亮色流動），翻頁時主題插值
- **Motion One 動效** · 內嵌入場動畫（cascade / hero / quote / directional / pipeline 五種 recipe），本地 `assets/motion.min.js` + CDN 雙保險
- **Lucide 圖示** · 線性圖標 CDN
- **Google Fonts** · Noto Serif SC + Noto Sans SC + Playfair Display + IBM Plex Mono
- **無框架依賴** · 純 HTML / CSS / 原生 JS

### 主題色（🍂 Kraft Paper）

```css
--ink: #2a1e13;       /* 深棕墨水色 */
--paper: #eedfc7;     /* 暖米牛皮紙 */
```

---

## 設計原則

每份 deck 都遵守同一套規範：

1. **主題節奏**：每頁 `light` / `dark` / `hero light` / `hero dark` 之一，禁止連續 ≥3 同主題
2. **字型分工**：衬線標題（Noto Serif SC）+ Sans 正文（Noto Sans SC）+ Mono 元數據（IBM Plex Mono）
3. **強調**：用 `<em>` 包字觸發螢光筆色塊樣式（中文不歪斜，英文 Playfair italic 保留）
4. **無 emoji**：用 `→` `★` `●` 或 Lucide 圖示
5. **無圖片**：純文字結構（stat-card / callout / pipeline / rowline / grid）
6. **每幕「概念 → 案例 → 練習」三段式**
7. **末頁連結地圖**：標出本模組概念在後續模組哪裡會回來

---

## 製作背景

製作於 2026 年 5 月，使用 Claude Code 並行多個 agent 完成（M1 為 pilot、人工驗收後 M2-M10 並行批產）。
基底樣板來自 [guizang-ppt-skill](https://github.com/guizang/magazine-web-ppt) 的「電子雜誌 × 電子墨水」風格，加上中文友善的 em 螢光筆改良。

源課程網頁：弄一下工作室「數位行銷人才培訓 70hr」（私有教學 repo）

---

## 授權

簡報內容為弄一下工作室教學設計成果，視覺樣板基於 guizang-ppt-skill。
教學使用、研究參考歡迎引用，商業翻製請先聯繫。

---

**弄一下工作室** · Digital Marketing 70hr Lecturer Decks · Vol.01 · 2026

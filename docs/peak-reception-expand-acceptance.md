# PEAK 評價概況擴充驗收（Steam／媒體彙整）

2026-10-22，沿用 `work/peak-real-data/knowledge.sqlite3` 與 `http://127.0.0.1:8767/`。本輪追加 **1** 個待審修訂（`peak-reception` → revision **265**），條目仍為 **244**，修訂 **264 → 265**；來源／快照 **222 → 224**。沒有批准發布，沒有合併 PR。

## 做了什麼

`peak-reception`（評價概況）由單一 PC Gamer 專評，擴成可核對的多來源概況：

- **Steam 使用者評價**：經 [Steambase 彙整頁](https://steambase.io/games/3527290/reviews) 短摘錄保存。觀測於 2026-10-22：Player Score **94／100**、約 **380,967** 則、標籤 **Very Positive**。**未直接 HTTP 抓取 Steam 商店**（既有 Subscriber Agreement 自動化限制仍在）。
- **媒體彙整**：Wikipedia Reception 短摘錄（CC BY-SA）：Metacritic **82／100**（generally favourable）、OpenCritic **100% recommend**，並記下 Steam Awards 2025 **Better With Friends**。
- **既有 PC Gamer**（Elie Gould，2025-06-26，86 分）快照與引文保留。

## 流程邊界

1. A：`register-file-source` → `intake-file`／`bundle` 產出兩份 `ssr.collection.v1`。
2. B：候選 DB 先驗證 → `ingest-collection --apply` → `import-drafts` → 再追加原庫。
3. C：查詢頁／API 直接讀原 DB。重送來源與草稿皆 `unchanged`。

私有來源檔、摘錄、交接包、備份與候選庫留在 `work/peak-reception-expand-20261022/`。

## 驗證

- PASS：integrity／foreign keys；revision 265 = 草稿；revision 261 歷史保留；昏迷／團長／徽章 head 不變。
- PASS：API `?entry=peak-reception` 顯示 revision 265；搜尋「Very Positive」可命中。
- 最終 DB SHA-256：`b5bcaeb21d68fcf0bd4535ee4d3a0ae11915eaa5e5d9e58b513c7a6a8c6f2b5f`。

驗收連結：[評價概況](http://127.0.0.1:8767/?entry=peak-reception)。請按「重新讀取 DB」後核對 Steam／Metacritic／PC Gamer 欄位與來源明細。

# PEAK 官方更新史（peak-updates-v1）驗收

2026-10-22，沿用 `work/peak-real-data/knowledge.sqlite3` 與既有查詢入口。本輪新增計畫 **`peak-updates-v1`（10 目標）**，條目 **244 → 254**，修訂 **265 → 275**，來源／快照 **224 → 233**；全部新修訂為 **`pending_review`**。沒有批准、發布或 home sync。

## 做法

1. A：9 份官方短摘錄 `approved_local_file`（搜尋索引觀測；**未**直接 HTTP 抓 Steam）→ `intake-file`／`bundle`。
2. B：`register-game-plan` → `ingest-collection --apply` → `import-drafts`。
3. 既有 `peak-death-timer-thorns-official-20261022` 快照复用為 `peak-update-dillydally`。
4. 既有 `peak-official-update`（2.6.b，rev **83**）**未改**。

## 新條目（pending_review）

| entry_id | 版本／名稱 | announced_at |
|----------|------------|--------------|
| peak-update-2-6-a | 2.6.a | 2026-10-02 |
| peak-update-2-5-a | 2.5.a | 2026-09-28 |
| peak-update-2-4-c | 2.4.c | 2026-09-14 |
| peak-update-2-4-a | 2.04.a THE KILN IS BACK | 2026-09-02 |
| peak-update-2-4-b | HOTFIX 2.4.b | 2026-09-02 |
| peak-update-2-03-a | 2.03.a | 2026-08-27 |
| peak-update-final-ascent | THE FINAL ASCENT／2.0.a | 2026-08-11 |
| peak-update-2-01-a | 2.01.a | 2026-08-13 |
| peak-update-2-02-a | 2.02.a | 2026-08-18 |
| peak-update-dillydally | DILLYDALLY（荊棘死亡計時） | 見缺口（正文無日期行） |

## 刻意留下的缺口

- **非整份** Steam 公告史／全部 hotfix。
- `peak-update-2-03-a` 的 `original_url` 暫指公告列表頁（detail GID 未解析）。
- `peak-update-dillydally`：`announced_at`／`version` 欄位為 gaps（既有快照正文只有 Thorns 一句）。
- Wiki／SteamPeaks／UpdateMonitor **未**用作 update 類證據。

## 原文差異（2.6.b）

既有快照為**短摘錄**，與目前搜尋索引可見的較完整句子不同；**未覆寫**舊快照。詳見本輪回報。

## 查詢

- CLI：`entry --entry-id peak-update-final-ascent` 等
- 頁面：`http://127.0.0.1:8767/?entry=peak-update-2-6-a`（若服務已綁同一 data-dir）

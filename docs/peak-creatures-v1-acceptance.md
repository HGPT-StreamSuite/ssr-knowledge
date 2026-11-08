# PEAK 生物／威脅首批（peak-creatures-v1）驗收

2026-10-22，沿用 `work/peak-real-data/knowledge.sqlite3`。新增計畫 **`peak-creatures-v1`（8 目標）**，條目 **254 → 262**，修訂 **275 → 283**，來源／快照 **233 → 241**；全部新修訂 **`pending_review`**。未批准／未發布。

## 做法

Wiki 短摘錄 `approved_local_file`（`source_type=wiki`）→ A `intake-file`／`bundle` → B `ingest-collection --apply` → `import-drafts`。先 candidate 再 live。

## 新條目

| entry_id | 名稱 | 備註 |
|----------|------|------|
| peak-creature-zombie | 殭屍 | Roots |
| peak-creature-spider | 蜘蛛 | Roots |
| peak-creature-beetle | 甲蟲 | Roots |
| peak-creature-antlion | 蟻獅 | Mesa；`counterplay` 缺口 |
| peak-creature-condor | 禿鷹 | Caldera |
| peak-creature-bee | 蜜蜂群 | Beehive 頁；與 peak-beehive 分開 |
| peak-creature-scorpion | 蠍子（威脅） | 與 peak-scorpion 道具分開；`counterplay` 缺口 |
| peak-creature-frog | 青蛙（威脅） | 與 peak-frog 道具分開 |

`peak-scoutmaster` 仍為 **rev 263**，未改。本批**不**跨計畫關聯。

## 刻意未收（已於 v2 補完者除外）

見後續 [peak-creatures-v2-acceptance.md](peak-creatures-v2-acceptance.md)：Tick／Jellyfish／Urchin／Flytrap／Big Ghost。Crow 仍因 Wiki 404 未建。

## 查詢

`http://127.0.0.1:8767/?entry=peak-creature-zombie`（請重新讀取 DB）。

# PEAK 後半行程與逐項徽章保存驗收

2026-10-21，依 collector 的 [peak-late-game-v1](https://github.com/HGPT-StreamSuite/ssr-collector-peak/blob/codex/collector-acceptance/plans/peak-late-game-v1.json) 在既有 `work/peak-real-data/knowledge.sqlite3` 保存 39 個新待審修訂，沿用 `http://127.0.0.1:8767/` 直接查同一 DB。

## 寫入結果

- 條目 **71 → 109**；修訂 **83 → 122**。新增 38 筆，修正 1 筆。
- 新增 13 道具、5 區域、3 機制、12 個別徽章與 5 攻略；反重力繩索炮移除未能一致核對的繩長斷言，保留原取得、操作、限制、計畫及關聯。
- 共 70 個來源／快照、435 個已存欄位、104 條目前關聯，9 個既有必填欄位缺漏未變。繩長來源分歧存於條目的來源明細。
- 原有 83 個修訂的完整資料列逐筆保留；70 個未修改舊條目維持原 current revision。所有 109 筆為 `pending_review`。

21 份本批 Wiki 索引摘錄先由 A 獨立 collector 產生標準檔案，再由 B `ingest-collection` 保存來源、`import-drafts` 交易保存整理知識。寫入前以 SQLite backup API 備份，候選副本通過相同流程後才寫入原庫。重送本輪 39 筆皆為 `unchanged`，沒有增加修訂。

## 可重現的驗證

既有 uv 環境、Python 3.13.3，collector 52 項及 knowledge 140 項測試通過。沒有新增套件或變更服務啟動方式。資料驗證針對原庫，而非合成隔離 DB：

1. 新 SQLite 唯讀連線檢查 integrity／foreign keys、原有修訂及 heads、所有 109 個 payload、435 個欄位引用、104 條目前關聯及 9 個缺欄。欄位及關聯引文均存在於各自指定的來源快照。
2. 每個條目以新 `uv run --no-sync python -m ssr_knowledge catalog --data-dir ... entry --entry-id ...` 程序讀回，109 個 payload、revision 與狀態均和 DB 一致。
3. 同一 8767 服務的 API 與安裝版 Google Chrome headless 頁面逐筆核對全部 109 筆的值、revision、引文／snapshot ID、缺欄和關聯目標；另操作六頁分頁、七個分類、搜尋、雙向跳轉、重新讀取與四份計畫進度。
4. 檢視城塞、個別徽章、紅色蘑菇莓及山頂救援攻略的實際頁面截圖，欄位與來源明細正常排列，來源與授權保持收合。

最終唯讀核對前後原 DB SHA-256 均為 `1a2bcd6335880f9e437b4e8517b0914df6dc20066650f41e9485e6a3f3d0fff8`。私有驗證報告、來源檔、草稿、備份及畫面保存在 checkout 外。

本機 8767 仍使用先前已載入的 d25240c 程序，直接讀到新保存的 109 筆；家裡缺漏顯示修正已在 checkout 與測試中，但本輪沒有重啟服務套用。封存程式另以新程序讀回備份驗證，不把該結果當作本機服務版本已更新。

## 使用者查詢入口

- `http://127.0.0.1:8767/?category=item&entry=peak-red-shroomberry`：五色之一的取得、使用、效果與徽章關聯。
- `http://127.0.0.1:8767/?category=location&entry=peak-citadel`：城塞位置、危險、配對及關聯。
- `http://127.0.0.1:8767/?category=achievement&entry=peak-badge-medieval-history`：個別徽章的條件、操作與獎勵。
- `http://127.0.0.1:8767/?category=guide&entry=peak-guide-peak-rescue`：山頂救援步驟及限制。

全庫可查 42 道具、10 標準區域、11 機制、8 狀態、18 攻略；成就分類為 12 個個別徽章加 1 個概覽。四份計畫的目標已有修訂不代表全遊戲完成：目前只整理 12／64 個別徽章，其他道具、生物、隱藏區域與 9 個既有缺欄仍待補。

## 家裡原 DB 的合併交接

[前一批家裡驗收](home-merge-acceptance.md)為 244 條目／665 修訂。上一批 37 筆加本輪 39 筆共 76 個不同條目的變更，須接續合併到原 DB。使用者指定提供交接文字，由使用者自己貼給家裡原 Codex 聊天；本輪不跨聊天發送任務。

私有包須包含原始 41 筆與本輪前 71 筆基線、兩批 37／39 筆差異、全部 109 筆目前內容、四份計畫、70 個來源交接檔及完整 DB 參考快照。完整快照用於對照；接收端從家裡原 DB 建立備份與候選，以保存 CLI 合併，不拿本機小庫替換原庫。

接收端先沿用已知 `peak-weight` → `peak-carried-weight`、`peak-shore` → `peak-location-shore`、`peak-unconscious` → `peak-unconsciousness`，再按實際英文名／遊戲 key 核對新道具和 12 個徽章是否已有 ID。保留官方名稱、`badge_details`、`item_details`、既有欄位與歷史；重新編排引用索引時同步驗證所有欄位及關聯。不可變計畫有 ID 對應差異時新建衍生版本，不能覆改舊計畫或將原關聯留在錯誤計畫。

完成候選驗證後，用相同合併草稿寫入家裡原 DB，重新逐筆讀 DB、8765 API 與 Chrome 頁面；保留合併前後計數、所有舊修訂、未修改 heads、關聯與重送不重複的證據。家裡已有較多官方條目，因此不預定合併後條目數。資料包交付與家裡實際入庫分開記錄；待審、使用者驗收與批准發布亦分開。

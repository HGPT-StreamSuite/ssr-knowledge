# PEAK 昏迷計時續查與全庫完整性驗收

2026-10-22，沿用 `work/peak-real-data/knowledge.sqlite3` 與 `http://127.0.0.1:8767/`。本輪追加 **3 個待審修訂**，條目仍為 **244**，修訂 **261 → 264**；沒有替換 DB、重啟查詢服務或批准發布。

## 昏迷秒數的查證結果

`peak-unconscious.quantities` 保留原缺口。未取得可確認現行原版基準秒數的官方數值、版本對應程式流程或可重現計時實測。

- [HangingOn 模組說明](https://thunderstore.io/c/peak/p/JJplayz/HangingOn/)提到一般情況約一分鐘；其 [2.1.0 公開程式頁](https://thunderstore.io/c/peak/p/JJplayz/HangingOn/source/)可見模組設定說明，不能據此當成現行原版計時驗證。Carry Regeneration 的新增計時程式同樣不能證明原版固定秒數。
- 搜尋得到的 30–60 秒攻略說法和約 10 秒玩家留言，缺乏可核對的版本、條件與計時過程，沒有寫入數值欄位。殭屍的倒數也不當成童軍昏迷倒數。
- [官方 2025-09-24 更新](https://steamcommunity.com/games/3527290/announcements/detail/520850995978175753)明確指出：因荊棘昏迷不會使死亡倒數加快。本輪保存其搜尋索引中的 18 字英文短摘錄，補入 `peak-unconscious.rule`，形成 **revision 262**。沒有把這項條件規則當成秒數缺口已完成。

## 完整性覆核發現與修正

除了檢查結構、雜湊及精確引文，也覆核所有條目的摘要及欄位中疑似缺漏的文字。發現上一批部分欄位已補齊，但舊摘要未跟進：

- **revision 263 / `peak-scoutmaster`**：移除「召喚物品名稱未明」的過時摘要；依已保存的團長與團長號角快照，補實追逐／抓取行為、號角召喚與 Tenderfoot 例外，保留一般追逐的既有應對。清除同一條目內重複的別名。
- **revision 264 / `peak-badges`**：摘要改為已保存欄位支持的 Steam 成就同步說明，不再顯示「Steam 對應未核對」。

33 個數字字面差異已逐項覆核：23 個為英文數字／序數、3 個日期、2 個 `x1.5` 格式、四分之一秒換算、1 小時換算、15 加 10 秒、列舉四項及千位分隔各 1 個。滑翔翼摘要的 100 公尺由同條目已存的徽章關聯引文支持。3 個疑似缺漏詞其實是「尚未結束的中毒」及「尚未開啟／使用的物件」條件，並非未填答案。另查出的團長「完整行為仍待詳細來源」已由 revision 263 補實。

## 實際 DB 與保存邊界

- **244 條目、264 修訂、984 個已填欄位、1 個明列缺口**。
- **222 份來源／快照／交接收件紀錄**；目前欄位共 **1,604 段精確引文**。
- **145 條目前關聯**；保留歷史後共有 153 列關聯、536 列引用。
- 64 個逐項徽章、123 個道具、11 個區域、19 篇攻略；六份不可變計畫均符合公開計畫檔，全部 244 個目標已有修訂。
- 原 261 個修訂及其他既有資料表的每列資料均保留；241 個未修改條目的 head 不變。所有目前條目仍是 `pending_review`。

先以 SQLite backup API 備份並驗證候選，再由保存端追加原庫。新官方短摘錄經 A `intake-file`／`bundle` 輸出 `ssr.collection.v1`，B `ingest-collection --apply` 保存快照，再以 `import-drafts` 建立修訂。兩個內容修正直接引用既存快照，由 B 另批匯入。C 從原 DB 讀取。來源包及三個草稿重送均為 `unchanged`，沒有重複修訂。

原文、來源設定、草稿、交接檔、兩次一致性備份、候選 DB 及逐筆結果留在私有 `work/peak-unconscious-audit-20261022/`；Git 僅保存本驗收紀錄。家裡端未操作。

## 驗證結果與入口

Windows、Python 3.13.3、既有 uv 環境及安裝版 Google Chrome。私有工作目錄內實際執行：

```powershell
$env:PYTHONPATH='C:\github\ssr-knowledge'
# 以下於 ssr-knowledge checkout 執行。
$auditDir='C:\Users\ASUS\Documents\Codex\2026-10-21\new-chat\work\peak-unconscious-audit-20261022'
uv --cache-dir .uv-cache --offline run --no-sync python "$auditDir\audit.py"
uv --cache-dir .uv-cache --offline run --no-sync python "$auditDir\verify_cli.py"
node "$auditDir\verify_ui.cjs"
git diff --check
```

- PASS：SQLite integrity／foreign keys；全部 264 個歷史 payload 雜湊與契約、222 份來源原文／正文雜湊、收件對應、536 列引用及153列歷史關聯與 payload 一致。
- PASS：全部目前欄位都有合法型別、精確引文與固定來源，或明列缺口；名稱、別名及關聯目標無重複衝突或斷鏈。既存來源登記下沒有 stale 條目；此狀態不代表已重新查證每個網站的最新版本。
- PASS：244 個獨立 CLI 程序讀回完整 payload、revision 及待審狀態；244 個 API 與 Chrome 條目頁逐筆比對摘要、984 個欄位、缺口、引文／snapshot ID 和雙向關聯。
- PASS：13 頁分頁、13 個分類、搜尋、重新讀取、六份計畫進度、徽章與道具雙向導航；搜尋新文字「荊棘昏迷」可開啟 revision 262。
- PASS：實際檢視昏迷、團長和徽章概覽截圖，三個最新修訂呈現正確、來源明細預設收合，秒數缺口仍可見，無頁面錯誤。
- PASS：最終查詢前後 DB SHA-256 均為 `f17630a4a2307d8e83ec4d06ddf45671dcc7487f33a7c08651ff4a182f6f0456`。
- 本輪未修改執行程式，未重跑套件單元測試；上一輪 collector 52／52、knowledge 140／140 是 2026-10-21 的結果。本輪驗證的是實際 DB、保存交易與查詢頁，不以舊測試代替。

這次核對涵蓋目前建庫計畫的資料完整性與實際呈現，並不宣稱所有版本的遊戲內容都已收齊或完成遊戲實測。

可在原查詢頁直接驗收：[昏迷與死亡](http://127.0.0.1:8767/?entry=peak-unconscious)、[團長](http://127.0.0.1:8767/?entry=peak-scoutmaster)、[徽章系統](http://127.0.0.1:8767/?entry=peak-badges)。開啟後按「重新讀取 DB」，依序應顯示 revision 262、263、264；展開欄位來源可看到實際固定引文。內容批准與 PR 合併仍由使用者另行決定。

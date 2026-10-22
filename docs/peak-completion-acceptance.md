# PEAK 全徽章攻略與道具續批驗收

2026-10-22 續查已追加 3 個修訂，目前為 244 條目／264 修訂；秒數缺口仍保留。最新全庫核對與畫面驗收見 [昏迷計時與完整性驗收](peak-timer-integrity-acceptance.md)。以下保留 2026-10-21 本批結果。

2026-10-21，依 [徽章與補給規劃](https://github.com/HGPT-StreamSuite/ssr-collector-peak/blob/codex/collector-acceptance/docs/peak-completion-plan.md)，把本批資料追加到既有 `work/peak-real-data/knowledge.sqlite3`。查詢入口沿用 `http://127.0.0.1:8767/`，沒有替換 DB 或重啟服務。

## 實際保存結果

- 條目 **109 → 244**；修訂 **122 → 261**。新增 135 個條目，補充 4 個舊條目，合計 139 個新待審修訂。
- 新增 52 個徽章攻略、81 個道具、納迪爾區域與四護符通關攻略。現在有 **64 個逐項徽章、123 個道具、11 個區域、19 篇攻略**；成就分類另有 1 個制度概覽。
- 全庫 **984 個已存欄位、145 條目前關聯、221 份來源／快照**。六份計畫目標均已有修訂：13、29、29、38、87、48。
- 原 122 個修訂的完整資料列、全部舊來源／快照／引用／關聯／計畫／收件紀錄均保留。105 個未修改舊條目維持原 current revision，4 個更新條目保留原 plan_id、未改欄位與關聯。
- 所有 244 個目前條目仍是 `pending_review`。本輪沒有批准或發布。

道具數的核對分母是本次來源分類中的 133 個項目。六種棋子和四種莓蕉皮分別合併共用行為、保留別名；兩個別名頁沿用既有 ID，共映射到 123 個條目。食物數值按具名表列與欄名核對；歷史／停用道具清楚標示。這不是全遊戲、所有版本或所有生物機制的完成宣告。

## 九個欄位缺口的結果

**補上 8 個，剩 1 個。**

- `peak-scoutmaster.counterplay`：普通追逐解除、岩釘停留策略及號角召喚的例外。
- `peak-badges.condition`、`steam_equivalence`：遊戲行動解鎖、外觀獎勵及 Steam 成就同步。
- `peak-crash.interpretation_limits`：分開玩家的飛機失事與團長日記的船難。
- `peak-reception.reviewer`、`reviewed_at`、`score`、`reasons`：PC Gamer 原評測的作者、日期、86 分與理由；評價立場同步改為這篇原評測支持的內容。
- `peak-unconscious.quantities` 仍缺固定死亡倒數的基準秒數。已知狀態與背負會改變倒數，但沒有可靠原版數值，不能用模組設定、推算或重述既有規則清除此缺口。原欄位與缺口原樣保留。

## 三個獨立環節與驗證

150 份 Wiki 索引摘錄和 1 份 PC Gamer 評測短摘錄先存為私有檔案。A `intake-file`／`bundle` 產生 151 份 `ssr.collection.v1`；B `ingest-collection` 保存固定快照，再以 87、48、4 筆三批 `import-drafts` 保存整理知識；C 直接查原 DB。來源與授權在畫面預設收合，不把採集評語放進遊戲正文。

寫入前用 SQLite backup API 建立一致性備份與候選副本。候選通過後才追加原庫；一度因重新產生來源設定時的審查時間不同而拒收，逐份比較確認只有 `policy.reviewed_at` 不同後沿用已驗證的固定設定，沒有更改任何允許／禁止值，也未放寬接收驗證。

1. 獨立 SQLite 唯讀核對全部 244 個 payload、984 個欄位引文、145 條目前關聯、六份計畫覆蓋及剩餘缺口；integrity／foreign keys 通過。
2. 全部 244 個條目各啟新 CLI 程序讀回；完整 payload、revision 和狀態與 DB 相同。
3. 安裝版 Google Chrome headless 逐筆核對 244 份 API 與實際頁面：值、revision、缺口、來源引文／snapshot ID、雙向關聯均一致。另操作全部 13 頁分頁、13 個分類、搜尋、雙向跳轉、重新讀取和六份計畫進度。
4. 實際檢視航空學徽章、四護符通關、第零條規則、童軍的堅韌及評價頁截圖；正文與收合來源正常呈現。
5. 重送全部 151 份來源包與 139 個草稿均為 unchanged；entries、revisions、sources、snapshots、receipts、citations、relations 計數不增加。

唯讀核對前後 DB SHA-256 均為 `4ab6e8299e07cf98feab0baa9def437582f525ba086be8c21929f62712be7e4a`。資料、來源、輸入、備份和逐筆報告留在 checkout 外；Git 只保存規劃與本驗收紀錄。

既有 uv 環境執行兩邊測試，collector **52/52**、knowledge **140/140** 通過。Python 保存／查詢實作與本機服務程序未變，本批增加資料與不可變計畫。

## 查詢入口

- [逐項徽章](http://127.0.0.1:8767/?category=achievement)：64 個徽章及 1 個概覽。
- [道具](http://127.0.0.1:8767/?category=item)：123 個已存條目。
- [第零條規則徽章](http://127.0.0.1:8767/?category=achievement&entry=peak-badge-rule-zero)：條件、步驟、獎勵及所需道具。
- [四護符與納迪爾通關](http://127.0.0.1:8767/?category=guide&entry=peak-guide-nadir)：準備、行進與撤離。
- [昏迷](http://127.0.0.1:8767/?entry=peak-unconscious)：唯一尚未填入的規劃欄位。

家裡端依使用者本輪指示不處理，沒有新同步、傳送資料包或跨聊天操作。既有接收端紀錄保留，與本機結果分開。

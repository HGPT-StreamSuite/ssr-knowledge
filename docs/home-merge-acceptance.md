# 2026-10-21 家裡既有 DB 合併紀錄

這是已執行的私有資料合併摘要，不是原文、DB 或測試資料的公開替代品。實際驗收仍依 [直接 DB 查詢規格](persistence-and-query-acceptance.md)。

## 實際輸入與處理

- 接收 `PEAK-Home-Check-20261021-155018.zip` 與 `PEAK-Home-Transfer-20261021-153827.zip`，核對隨附 SHA-256 及各 manifest 檔案大小／雜湊。
- 檢查包的 PowerShell 內容與 `d25240c` 原始碼一致；只回傳有界的服務、repo、DB 路徑和查詢中繼資料。回傳目的主機與 Tailscale peer 身分相符，傳送命令成功；沒有對方開啟檔案的回條。
- 以 SQLite backup API 備份原 DB，核對備份完整性。接收包內的 41 條目 DB 僅唯讀參照，沒有整庫取代或複製其資料表。
- 使用既有 `register_file_source`、`ingest_collection`、`register_plan`、`Catalog.import_drafts` 的驗證流程。先在明確標示的本機備份副本核對，再寫入原本家裡 DB。沒有另外安裝環境或啟動新服務。
- 實際合併輸入是 21 個來源設定、21 個 `ssr.collection.v1` 文件包、2 個規劃檔及 41 個 current draft。接收 DB 中其餘 5 個歷史修訂保留在原始私有封包，沒有冒充此次寫入。

## 寫入結果

| 項目 | 寫入前 | 寫入後 |
| --- | ---: | ---: |
| 條目 | 228 | 244 |
| 修訂 | 624 | 665 |
| 固定來源快照 | 9 | 30 |
| 保存的關聯列 | 26 | 58 |

41 個新修訂全部為 `pending_review`：25 個補充既有條目，16 個新增條目。原有名稱、官方名稱證據、數值、摘要、表格列、來源與歷史修訂保留。新補充為社群來源，沒有提升為官方或玩家實測。

為避免同義重建，接收端將 `peak-weight`、`peak-shore`、`peak-unconscious` 分別對應到家裡既有的 `peak-carried-weight`、`peak-location-shore`、`peak-unconsciousness`；衍生規劃使用新的 `*-home-20261021-v1` 身分，未變更接收封包或既有不可變規劃。

本批有 148 個有證據欄位、16 個明列缺口、32 個新關聯。重複匯入同一批 41 個草稿全部回傳 `unchanged`，沒有新增重複修訂。沒有批准、發布或合併 PR。

## 驗證與限制

新程序以唯讀連線核對全部 41 個 current revision、148 個欄位、16 個缺口及關聯與逐欄 snapshot；逐筆呼叫現有 loopback API，核對同一 DB 路徑、revision 和保存值。原有歷史資料列逐列比對仍在。SQLite integrity check 與 foreign key check 正常。

中文、英文、別名、數值全文查詢實測包含 `解毒劑`、`Antidote`、`解毒藥`、`4.8`、`岩釘`。一般發布查詢仍不回傳待審資料。Chrome 實際頁面另核對，不以 API 200 代替瀏覽器驗證；詳細私有證據、備份、輸入路徑、revision 對照和結果均留在 Git checkout 外。

此資料包是 Wikipedia 段落與 20 份搜尋索引摘錄，並非取得完整 Wiki 詳細頁。缺少的完整頁、欄位、官方更新及先前徽章／Shroomberry 補充，不因本次合併宣稱完成。`peak-stamina` 保留的舊官方引用仍受既有來源政策失效標記影響，沒有放寬政策。

補充欄位存在時，原 Items 表格的分類空白不代表整個條目沒有資料；頁面將該原表中繼資料放進折疊來源明細，實際規劃缺口仍在主畫面的「明確缺漏」顯示。回歸測試使用合成來源與持久 SQLite，與真實資料核對分開記錄。

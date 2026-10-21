# 家裡原庫：37＋39 筆累積變更驗收

2026-10-21，本輪接收 `PEAK-Home-Transfer-20261021-181413.zip`，SHA-256 為 `520edfb8d2c5ebac5b36db1bfe46f542d44d694c80b8e9cd589668df5f559030`。ZIP 及 manifest 的 164 個檔案均核對通過。本文件只公開非轉載的執行摘要；原始包、參考 DB、來源文字、合併輸入、備份及逐筆報告保留於家裡 checkout 外。

## 原庫與候選

現場確認原庫為 244 條目／665 修訂，現有 8765 唯讀服務使用同一資料目錄。先用 SQLite backup API 建立一致性備份，從該備份建立候選；包內 109 條目／122 修訂的 DB 僅唯讀對照，未作為候選起點或覆蓋原庫。

依 `merge-index.json`、兩批原始基線與原庫 current payload 三方比較：

- 76 個不同條目中，55 個更新家裡既有條目、21 個新增。來源機的 68 個 local-new 沒有直接當作家裡新增數。
- 12 個徽章逐一以官方英文名及既有遊戲 key 核對，沿用原 ID。原有官方中英名稱、name 引用、badge_details、item_details、organization、舊表格及嚴格關聯保持相同；引用只追加，舊索引位置不變。
- 區域及兩個含冠詞的道具對應既有身分；保留先前 weight／shore／unconscious 對應。兩個既有 home 計畫逐項相同比對，沒有搬移其活躍條目；新增兩個有獨立 ID 的衍生 home 計畫。
- 8 個來源端更新按 changed_fields 合併，其餘欄位與基線比對；沒有未解決的三方寫入衝突。反重力繩索炮的兩種長度來源仍留引用，新用途不擅自選定長度，原取得、使用、限制與關聯保留。

候選全批驗證、獨立讀回及歷史核對通過後，再確認原庫 heads 未變，使用既有 register-file-source／ingest-collection／register-game-plan／import-drafts 驗證邊界追加到原庫。未複製參考 DB 的資料表。

## 原庫實際結果

| 項目 | 寫入前 | 寫入後 |
| --- | ---: | ---: |
| 條目 | 244 | 265 |
| 修訂 | 665 | 741 |
| 來源快照 | 30 | 79 |
| 保存的關聯列，含歷史 | 58 | 142 |

新增修訂 666–741 全為 pending_review；原本 665 個修訂與所有舊來源、引用、關聯、計畫及收件紀錄逐列保留，未修改條目的 head 不變。家裡全部 current record 重新計算為 435 個規劃欄位、9 個明列規劃缺口、129 條目前有效關聯；不是採用來源機的缺欄或關聯數。此計數不等於全遊戲已無其他語意缺口。

重送相同 76 筆草稿及全部 70 份來源包均 unchanged，不新增修訂或來源快照。Integrity check 與 foreign key check 通過。全部資料維持待審，未批准、發布或合併 PR。

## 實際驗收方法

- 候選與原庫各以獨立程序完整比對 76 個 payload、310 個本輪條目欄位及逐欄引用、缺口與雙向關聯；另啟動 76 個獨立 entry CLI 程序讀原庫，完整 payload／revision 相同。
- 原庫逐筆呼叫實際 8765 API，核對指定 DB 路徑與每筆 revision／欄位／來源。查詢前後原 DB SHA-256 相同。
- 使用本機 Chrome computer use，實際導覽 76 個條目頁。從各頁 article DOM 讀出所有內容（含收合來源明細），正規化空白後與由已核對 API 模型排版的完整條目文字逐頁比對，76／76 相同。比對包含官方名稱、數值、逐欄來源、快照 ID、缺口及關聯；這不是 76 張截圖或使用者人工批准。
- 另實際展開來源、從紅色蘑菇莓跳到進階真菌學並核對五色反向關聯；提交「蘑菇莓＋道具」得到五色 5 筆，徽章分類保持原有 64 筆，實際操作第 1／4 → 2／4 頁及重新讀取。
- 一般發布查詢仍沒有待審命中。中文、英文及別名搜尋以實際 DB 驗證；例如蘑菇莓、Shroomberry、進階真菌學、24 克拉、Airline Food、城塞、Peak Rescue。

此輪以收到的已保存來源為依據，未重新抓取網站、安裝依賴、建立新環境、修改網路或憑證。來源摘錄／頁面版本限制仍保留；部分索引來源的標題與歸屬 URL 不同，沒有猜改，仍待內容審核。全遊戲完整性、其餘徽章攻略，以及 9 個明列缺口仍未宣稱完成。

關聯：[#5](https://github.com/HGPT-StreamSuite/ssr-knowledge/issues/5)、[#3](https://github.com/HGPT-StreamSuite/ssr-knowledge/issues/3)、[draft PR #4](https://github.com/HGPT-StreamSuite/ssr-knowledge/pull/4)。程式驗證起點為 13b6e2d；本輪 repo 只追加執行摘要，保存／查詢 Python 未變更。

# 獨立蒐集端的檔案接收

新增三個 opt-in 命令；不變更既有離線、HTTP、研究、審核、發布與查詢流程。這是第一步分離，尚未全面遷移舊功能。查詢仍可與知識保存放在本 repo，不串接 ssr-chat 或其他 repo。

本頁說明文件接收步驟；保存端的完整責任是再整理並寫入待審修訂，然後從同一 DB 重新讀回給使用者驗收。可用補充內容不能只停在文件 snapshot 或查證待辦；具體命令、完成證據及支援缺口見 [保存與查詢驗收規格](persistence-and-query-acceptance.md)。

`sources.config_json` 是中央現行政策。來源的四種用途、核對時間與依據集中保存；條目引用 snapshot 與段落，不複製整份授權。snapshot 中的當時設定是歷史證據，正式使用仍檢查現行政策。

## 可操作的本機驗收

獨立 collector repo 的 `Start-Acceptance.cmd` 提供一鍵驗收：指定本 repo checkout、checkout 外的測試資料夾，以及可選的既有正式 DB。工具沿用本 repo 已存在的 `.venv`／uv，以獨立 CLI 程序傳檔，分別跑兩端測試；生產核心仍無跨 repo import、共用套件或聊天串接。

成功後 `http://127.0.0.1:8766/` 每次直接讀 SQLite，顯示來源計畫、合成輸入、兩版資料包、保存端測試 DB、拒收／去重／更新與同版測試證據。合成測試與正式 DB 唯讀待審預覽分區，正式 DB 不交給任何寫入 CLI；沒有審核或發布按鈕。真站取得至入庫尚未通過，本輪真實網站原文新增 0。

完整啟動、停止、重播和判讀方式見 [collector 親自驗收說明](https://github.com/HGPT-StreamSuite/ssr-collector-peak/blob/codex/collector-acceptance/docs/acceptance.md)。若缺既有環境、資料不存在或測試失敗就報錯，不安裝新環境，也不以示範資料取代正式 DB。

```powershell
# 在本 repo，沿用既有本機 uv/Python。以下全部使用獨立測試 archive。
uv --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\fixture-archive register-file-source --file C:\collector\fixtures\permitted-source.synthetic.json
uv --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\fixture-archive export-source-plan
uv --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\fixture-archive ingest-collection --file C:\private\handoff\ID.collection.json
# 預設 read-only、validated_only。核對後才明確指定 --apply 保存原文和正文。
uv --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\fixture-archive ingest-collection --file C:\private\handoff\ID.collection.json --apply
uv --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\fixture-archive snapshot --snapshot-id SNAPSHOT_ID --body
```

三個命令都要求明確 `--data-dir`。export-source-plan 只匯出來源設定，可重複指定 `--source-id`，不匯出知識條目、不寫 DB。這是 `ssr.source-plan.v1` 政策快照，不是新的授權。請以 UTF-8 保存 stdout 後交給獨立蒐集工具；兩端互不 import、沒有共用套件、不互相啟動。

`register-file-source` 需要明確 `approved_local_file` 來源設定、`approved-file:SOURCE_ID` 內部 URL、出處 HTTPS original_url、allow_fetch=false 與明確 allow_import。這是另一條取得路徑的中央登記，不得用來替原網站解除禁止。合成 fixture 的許可只適用於合成文本，不能代表任何真站。真實來源仍需核對權限依據，unknown 維持 unknown。

`ingest-collection` 只接受 `ssr.collection.v1`，producer 為可核對的 `名稱/主版.次版.修補版`（本 collector 為 `ssr-collector-peak/0.1.0`）。根欄位只可有 format、producer、source_ref、document、bundle_id；source_ref 只有 source_id 和 config_sha256。document 包含 url、captured_at、observed_at、raw_base64、raw_sha256、body、body_sha256、metadata。canonical JSON 為排序鍵、緊湊分隔符、UTF-8、不跳脫 Unicode、拒絕 NaN；bundle_id 計算時排除自身。

接收端要求來源已在中央登記，核對精確設定雜湊、網址、用途、原文／正文雜湊與時間，重新解析正文，拒絕包內權限、審核、發布欄位。原文上限 2 MB、正文上限 2,000,000 字元、JSON 檔上限 6 MB。檔案來源只接受 UTF-8 plain_text 或中央 selector 的 html；script/style/hidden 不進正文。來源文本永遠是資料，不執行命令、不呼叫 LLM。設定更新後需重新取得來源計畫。

預設開 read-only 連線，驗證不改 DB。加 --apply 才在一筆交易保存 snapshot、來源最新版本、event 和 collection_receipts；失敗不留下半份文件。相同資料包不重存，原文更新建立新 snapshot，較舊觀測不能倒退最新版本。**接收永遠不建立知識條目、不生成摘要、不核准、不發布。** 草稿與正式搜尋沿用既有明確邊界。

這一輪只驗證合成檔案。metadata 的取得方法、HTTP 狀態和時間是生產端觀測宣告；雜湊不是簽章、身分驗證或抓取證明。檔案包只能標示 operator_file／synthetic_fixture、http_requests=0，不假稱 Chrome 取得成功。captured_at 是暫存時間，observed_at 是本次觀測時間，不是網頁更新時間。

使用者目前選定的網站取得方式是 computer use／本機 Chrome；新蒐集端的檔案 intake 尚不是 Chrome 自動匯出器。HTTP 核心僅保留可選架構，本輪未抓真站。瀏覽器能讀不代表批次蒐集獲准；不得藉瀏覽器繞過明確限制。原 repo 的 HTTP 核心與研究工作仍保留，沒有宣稱本輪全面搬移。

正式資料庫、原文、來源計畫、handoff 包與私有驗收輸出保持 checkout 外。本 repo 新增的公開測試全部是合成資料，不含真實 PEAK 網頁正文。既有文件與資料不刪除，PR #4 不合併。


## 統一契約與前置規劃（2026-10-21）

目前必要／可選欄位、表格／時間／版本／去重與多頁限制，詳見 [ssr.collection.v1 接收契約](collection-contract-v1.md)。同一 format 可由自有與客製 collector 產生，各保留 producer 身份；中央許可與接收驗證不因此放寬。可選 capture_receipt 只核對 DOM 觀測與檔案的綁定，不冒稱 HTTP 200 或來源許可。未帶 receipt 的既有包仍相容。

前置遊戲分析與條目／欄位／關聯計畫以 [collector issue #1](https://github.com/HGPT-StreamSuite/ssr-collector-peak/issues/1) 及其遊戲規劃規格為唯一入口；網站分類不是 DB 分類。介紹、評價、官方更新公告及其日期／版本／作者／影響範圍按規劃保留，意見與官方事實分開。

驗收固定為：**輸入查詢條件 → 直接查指定資料庫 → 顯示實際查詢結果**。測試／報告／驗收頁本身實際執行此流程；真實資料查指定持久 DB，合成模式查明確標示且已實際保存的測試 DB。前端可使用固定版型，結果不得由靜態 JSON、硬編碼摘要、先前快照或其他 DB 代替。

真實完成須逐筆核對「寫入 pending 修訂 → 新程序／新連線讀 DB → API → 實際頁面」的 revision、欄位、來源及關聯。文件 snapshot 不等於知識修訂；找到未存、已存未顯示、來源未提供、取得失敗、驗證阻擋分開記錄。pending 保存不是批准／發布。A／B／C 可獨立執行，以檔案交接，不新增不可分離服務、跨 repo import／共用套件或聊天串接。

現況：公開合成範例已由兩個獨立 CLI 驗證、保存到明確測試 DB、去重、新程序讀回；新增真實知識修訂仍為 0。受限 Wiki 的實際完整擷取→知識保存鏈路未通過，不以合成範例標成完成。

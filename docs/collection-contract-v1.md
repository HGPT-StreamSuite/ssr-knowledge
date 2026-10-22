# 統一文件交接契約 ssr.collection.v1

本頁定義 A 到 B 的共同文件格式；B 還須整理並實際保存待審知識，C 再直接查同一 DB 驗收。完整執行順序與逐筆完成條件見 [保存與查詢驗收](persistence-and-query-acceptance.md)。文件接收成功不代表知識修訂已保存。

## 實際接收格式：必要欄位

瀏覽器觀測新增 `method=local_chrome_playwright`，與原有 `local_chrome_computer_use` 分列，避免把自動化驗證描述為人工點擊。`export_format=rendered_text_html` 表示明確選定段落的純文字 HTML；原 `rendered_dom_html` 表示選定文章 DOM。scope 記錄挑選範圍，HTTP 狀態仍保留 null，檔案雜湊／exact URL／中央許可檢查相同。

下表對應 本 repo 的 `collection_handoff.validate_bundle`；這是已實作的文件封裝，並非模型答案或知識修訂包。

| 層級 | 必要欄位與型別 | 實際語意／限制 |
| --- | --- | --- |
| 根物件 | `format`, `producer`, `source_ref`, `document`, `bundle_id` | 只能有這五個欄位；format=`ssr.collection.v1`；bundle_id 是其餘根欄位 canonical JSON 的 SHA-256。 |
| source_ref | `source_id`, `config_sha256` | 只能有這兩個欄位；外部來源識別與精確中央設定雜湊，不是 SQLite 數字 ID，也不授予權限。 |
| document | `url`, `captured_at`, `observed_at`, `raw_base64`, `raw_sha256`, `body`, `body_sha256`, `metadata` | 只能有這八個欄位；url 必須等於中央 acquisition URI，原站 HTTPS URL 由中央 `original_url` 及觀測 metadata 保留。 |
| metadata 共通 | `acquisition_kind`, `purpose`, `collector_called_llm` | purpose=`local_cache`，collector_called_llm=false；本機檔案 kind=`approved_local_file`。 |
| metadata 本機檔案 | `acquisition_method`, `body_format`, `http_requests` | method=`operator_file` 或 `synthetic_fixture`，format=`plain_text` 或 `html`，http_requests=0 指 collector 未發 HTTP，不代表瀏覽器沒有網路請求。 |

producer 是生產程式識別；同一 format 的不同生產程式不得冒稱相同實作。當前接收端接受 `名稱/主版.次版.修補版`（名稱為小寫英數與連字號），不把此字串當身分驗證或權限。

**raw／正文／表格**：JSON 使用 UTF-8（可讀 UTF-8 BOM）；raw_base64 保留原始檔 bytes，檔案 profile 的 bytes 必須能嚴格解成 UTF-8。plain_text 原樣作正文；html 由中央 selector 重解析，必須精確匹配一個元素，script／style／hidden 等不進正文。HTML 表格結構仍在 raw，body 是文字；目前沒有另行標準化的 typed tables／rows 契約。不能只交 AI 摘要或模型答案。

**時間／版本**：兩個根據觀測記錄的 ISO-8601 時間都需時區；observed_at 不得早於 captured_at，未來時間超過 60 秒拒收。沒有可靠網頁更新日期時保留 null，不用擷取時間冒充更新時間。來源版本為中央 `declared_version`；可選 metadata 如 source_updated_at／source_updated_basis 是觀測紀錄，不是接收端已驗證的遊戲版本。

**大小／ID／更新**：raw 40 bytes–2 MB；body 40–2,000,000 字元；JSON 至多 6 MB。canonical JSON 排序鍵、緊湊分隔符、UTF-8、不跳脫 Unicode、拒絕 NaN。固定來源 ID／URL 為來源身份；沒有額外 business document_id。snapshot 由接收端依來源 URL＋raw hash＋中央設定 hash 產生，不能由包內指定；bundle_id 識別完整觀測包。重匯同包 unchanged，新原文產生新版本，舊觀測不倒退 latest。

**可選 metadata**：原檔名、出處／觀測 URL、正文定位、來源更新依據、`capture_receipt`。新加的 capture_receipt 是 `ssr.browser-export.v1` DOM 觀測紀錄，僅供 operator_file＋html；核對 exact URL、raw hash、時區時間與未知 HTTP=null，不能充當來源許可／簽章。未提供此欄位的既有 v1 包仍可接收。collector 的 `tools/capture_browser_export.mjs` 在既有本機 computer-use runtime 接受選定 tab 與明確許可的 source plan；不自行導覽、不繞過限制、不開 knowledge 或 DB。CLI 以 `--capture-receipt FILE` 帶入。

包內不得包含權限授予、審核／發布指令、內部 entry／revision／snapshot ID、知識條目或模型答案。根／document 的額外欄位拒收；metadata 的 policy／uses／allow_fetch／allow_import／review／published_at 也被明確拒收。接收端重新計算雜湊與正文，但不能僅靠雜湊證明來源真的被抓取或語意沒有被生成；須另核對實際擷取證據。

**多頁**：目前一包一個文件，不接受 pages 陣列、next-page 抓取指令或自動分頁清單。不同頁面各自對應中央來源、獨立檔案／包；目標規劃負責頁面對應。結構化數值／欄位與攻略關聯在 B 整理為有來源的 pending 修訂，不能假稱 v1 文件包本身已建立它們。

**狀態**：A intake=`saved`／`unchanged`；B 預設=`validated_only`（不寫 DB），加 --apply 後=`saved`／`saved_historical`／`unchanged`。拒收回 error／exit 1；可選 HTTP acquisition 的 blocked_or_failed／exit 2 與本機檔案驗證分開。缺字／來源未提供與取得失敗不得用空 body 冒充成功（低於大小下限即拒收）。

接收端倉庫的 [合成包](../fixtures/collection-example.synthetic.json) 與[單獨中央合成設定](../fixtures/collection-example-source.synthetic.json) 是一份由真實 collector CLI 產生、由真實 knowledge CLI 驗證／保存／重開讀回的範例。設定檔只授權自製合成內容，沒有放入包內，不能作任何真站許可。

```powershell
# 在 knowledge checkout，明確使用 checkout 外的合成測試 DB：
uv --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\handoff-test register-file-source --file fixtures\collection-example-source.synthetic.json
uv --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\handoff-test ingest-collection --file fixtures\collection-example.synthetic.json
# 預期 validated_only；只有要保存合成文件時再明確加 --apply。
```

本輪真實 Wiki 採集限制已另記錄；上述範例與可選 adapter 不構成真站端到端通過，也沒有把新查得資料存成真實知識修訂。

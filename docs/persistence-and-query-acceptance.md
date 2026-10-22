# 從擷取檔案到待審保存與直接 DB 驗收

家裡端最新累積批次：37＋39 筆已經候選驗證後追加同一原庫，現為 265 條目／741 修訂；逐筆 DB／CLI／API／Chrome 與重送證據見 [76 筆合併驗收](home-merge-76-acceptance.md)。

2026-10-21 家裡端後續：已在原本 228 條目 DB 合併本批待審補充，現為 244 條目／665 修訂，見 [合併與直接讀回紀錄](home-merge-acceptance.md)。下方新機與舊機未搬入的描述為當時基線。

2026-10-21 實作更新：分類計畫、typed 欄位、逐欄證據及一般有向關聯已落地，見 [遊戲計畫契約及真實本機驗證](game-plan-contract-v1.md)。下方歷史基線不代表本輪新 DB 的現況；本輪新庫已有 12 個真實待審條目，舊主機 DB 未移轉。

本規格落實 [knowledge issue #5](https://github.com/HGPT-StreamSuite/ssr-knowledge/issues/5) 的保存與查詢責任。遊戲基本構成、自己的分類／條目／欄位／關聯及來源對應，統一依 [collector 規劃規格](https://github.com/HGPT-StreamSuite/ssr-collector-peak/blob/codex/collector-acceptance/docs/game-knowledge-planning.md) 與 [issue #1](https://github.com/HGPT-StreamSuite/ssr-collector-peak/issues/1)，不另訂一套遊戲分類。

**完成是：擷取檔案 → 保存原文 → 整理並寫入待審修訂 → 新程序讀回 → 輸入查詢條件、直接查同一 DB、顯示實際結果。** 找到的可用補充資料應走完這條路；查證紀錄、待辦、文件快照及測試通過均不能替代知識保存。

## 三個獨立環節

- **A 擷取程式**只負責取得內容、保留原文／觀測與輸出檔案；可獨立執行，不讀寫 knowledge DB、不呼叫保存或查詢服務。
- **B 保存程式**讀取 A 的檔案、驗證及保存文件，再依規劃整理條目、欄位和關聯並寫入指定 DB；保存為 `pending_review` 與人工批准／發布分開。
- **C 查詢程式**接收條件，每次直接讀指定 DB，顯示查到的內容；測試與報告畫面本身就是這項查詢功能，沒有另外手寫的內容結果。

B 與 C 可以位於同一 repo，但有各自的命令與讀寫責任；C 可在 B 停止後單獨運作。操作員可依序執行不同程式，不要求常駐服務綁定或跨 repo import。

## 共用檔案與保存的兩個步驟

標準與客製 collector 都使用 [ssr.collection.v1](collection-contract-v1.md)；接收端以相同規則處理不同 producer。該格式只承載來源文件，**不因本規格增加知識條目、審核或發布欄位**。

1. **文件接收**：中央來源另行登記，`ingest-collection` 預設 `validated_only`，明確 `--apply` 才保存 snapshot／receipt。接收端檢查來源設定、用途、時間、原文／正文雜湊及重解析。成功只表示文件已收納。
2. **整理與知識保存**：操作員或 agent 以保存的原文和規劃目標整理草稿，交給 B 的 `import-drafts` 驗證並寫入。這份草稿是保存端的整理輸入，根物件僅含 `entries` 陣列；不是要求每個 collector 另實作一種交接格式。必須實際取得寫入結果，不能把草稿檔存在磁碟就當成已入庫。

既有草稿至少包含 entry_id、game、category、名稱／別名、摘要、evidence_class、citations、editor、game_version、limitations；引用固定 snapshot、locator 與原文短引。已實作的結構化內容包括 item_details、badge_details、guide_details 與 links，實際限制仍由 `Catalog._validate_draft` 及對應驗證器判定。整理文字可以由人員／agent 編寫，但不可代替原文或憑空補齊證據。

`import-drafts` 新增內容回傳 entry_id、revision_id、state=saved、status=pending_review。相同內容回傳 unchanged 並保留原狀態；不得計為新增，也不能聲稱重複匯入把已批准內容降回待審。內容更新以新修訂保存，舊修訂保留。關聯的目標必須已存在；目前同批驗證不會自動先建立尚不存在的目標。

## 執行順序與逐筆讀回

執行前指定同一個 checkout 外的資料目錄，核對其既有 DB 身份與寫入前的 entry／revision。對既有正式資料先保留可恢復備份；合成測試使用另一個明確標示的持久測試 DB。來源、草稿與 DB 的私人檔案都不提交 Git。

以下命令在 knowledge checkout 使用既有 uv 環境執行。路徑與 ID 為占位值，須替換成此次實際檔案和命令回傳值；來源登記及使用依據應先完成。

```powershell
uv --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\selected-archive ingest-collection --file C:\private\handoff\DOCUMENT.collection.json
uv --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\selected-archive ingest-collection --file C:\private\handoff\DOCUMENT.collection.json --apply
uv --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\selected-archive import-drafts --file C:\private\organized-drafts.json
# 以下各自啟動新程序，從上述同一 DB 讀回：
uv --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\selected-archive entry --entry-id ENTRY_ID --revision REVISION_ID
uv --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\selected-archive relations --entry-id ENTRY_ID
uv --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\selected-archive search --text QUERY --preview
uv --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\selected-archive serve-review --port 8765
```

上述 `import-drafts` 本身會寫入，沒有 `--apply` 開關；文件驗證的 `--apply` 規則不能套用到草稿命令。每一步失敗就記錄該階段及原因，不繼續宣稱下游成功。新內容保持待審，不為了讓搜尋命中而執行 review-entry／publish-entry。

每筆驗收至少核對：

- 實際 DB 路徑、遊戲／版本、本批規劃目標、查詢條件與讀取時間。
- A 的 bundle_id 與 B 接收後的 snapshot_id、來源位置、原文／正文完整性。
- 寫入前／後 entry_id 與 revision_id、saved／unchanged 狀態；新修訂的 pending_review、review 與 published_at。
- 新程序讀回的欄位值／單位、引用、關聯方向及目標；與實際保存的 revision 一致。總筆數增加不能代替逐筆內容核對。
- API 與頁面查詢的相同條件、相同 DB、相同 revision 及內容。每筆的資料保存、程式核對、使用者親自驗收分開記錄，不代替使用者表示批准。

## 查詢與報告的資料來源

使用 [即時 DB 唯讀驗收](live-review.md) 的 `serve-review`。搜尋、分類、翻頁、開條目與重新讀取都建立新 SQLite 唯讀連線；`/api/review` 與頁面使用相同查詢模型。頁面可排版、翻譯欄位標籤或折疊來源明細，但不能加入 DB 未保存的補充內容、臨時生成的答案或另讀其他 DB。

驗收 pending 修訂使用明示的審查預覽；一般 `search` 仍只回傳符合用途與發布條件的資料。已保存但尚未發布而得到 no_data，應檢查 preview 與資料狀態；不能把空查詢當作內容驗收通過。

未指定／找不到驗收 DB 或讀取失敗時明確顯示缺失／錯誤，不建立替代正式 DB，不回退至合成資料、先前 JSON、靜態 report.html 或硬編碼摘要。歷史報告與測試 log 可保留為證據，但不承擔本次查詢答案。瀏覽器實際操作要另有證據，HTTP 200 不能代替畫面驗收。

## 未完成狀態與目前能力界線

進度分為已規劃、找到未擷取、已擷取未收納、文件已存但知識未存、知識已存未顯示、已讀回並查詢顯示；來源未提供、取得失敗／受限與驗證拒收另記原因。不得用同一個「完成」涵蓋這些階段。

本規格是工作流程與 DoD，並非宣稱現有程式已自動執行全部步驟：

- 尚無自動遊戲根分析／規劃器或完整的逐欄進度帳。
- 現有 draft 驗證仍限 PEAK:3527290；介紹、評價、角色／模式已納入，並以已登記的 game plan 驗證本批目標與欄位。其他遊戲或超出受支援分類仍需明確擴充。
- v1 文件包沒有 typed tables 或多頁陣列，也不自動產生草稿。
- 舊 links 保留 badge_hint 與 condition_mentions_item 的嚴格驗證；新的 knowledge_links 按遊戲計畫驗證一般有向關聯及逐項引用。來源未命名的攻略物品集合仍不得猜補。
- 當前本機真實持久 DB 已有 [244 個待審條目、261 個歷史修訂](peak-completion-acceptance.md)，全部逐筆經新 CLI、API 與 Chrome 查詢核對；原 122 個修訂保留，9 個欄位缺口剩 1 個。本輪依使用者指示不處理家裡；[既有家裡驗收](home-merge-76-acceptance.md)與本機結果分開，不能互相代替最新查詢結果。

本輪若找到且有權使用的補充資料，應完成 B 寫入及 C 讀回；只有缺少指定 DB、來源取得受限或驗證能力不足等真實阻塞才保留未完成，記錄最後完成階段及具體原因。**不因文件規格、合成測試或 issue 更新完成，就將真實資料驗收勾選完成。**

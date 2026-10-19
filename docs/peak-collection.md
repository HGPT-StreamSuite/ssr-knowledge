# PEAK 小批來源蒐集、保存與搜尋

本批以未合併 PR #2 的 `8f02b722b4a70f30fd98681ee6e91ae434d71dc2` 為起點，新增 `catalog` 工作流。新 PR 的 base 是 `codex/ssr-knowledge-workflows`；`main` 尚未有該離線流程。Related to #1、#3。沒有修改其他 repo、部署、合併或共享套件。

## 能力與資料邊界

- `collect`：操作人員先研究條款並填入來源 manifest，再執行程式化 robots 檢查、HTTP 擷取、正文擷取、版本快照保存與事件記錄。不追蹤頁面連結、不執行 JavaScript、不使用 cookies／認證、不跟隨任何轉址。
- `import-drafts`：只驗證與保存**已編輯的** JSON；不自動翻譯、不呼叫 LLM、不驗證摘要是否正確推導自原文。每則引用需有存在於 pinned 正文的短錨點，人工仍須檢查語意與來源可靠性。
- `review-entry`／`publish-entry`：對指定修訂留下 reviewer、note、時間與明確 attestation，再獨立發布。真實資料本批保持待審；合成測試才會模擬批准。
- `search`：只搜尋已發布、當前修訂及當前來源；`--preview` 明確顯示審查資料，可含待審或拒絕狀態。結果含來源與快照 ID；不回傳原始 HTML／完整正文／私人引用短句。

SQLite `knowledge.sqlite3` 將 raw HTML（BLOB）與正文、來源設定及政策、HTTP header（白名單）、抓取時間、SHA-256、條目修訂與審核事件保存於一處。`snapshot --body` 和 `entry` 是本機私人審查介面；`sources` 和 `events` 也包含私人 metadata。**不應將這些輸出直接轉貼到公開 PR**。DB 不是加密儲存，使用既有 Windows 帳戶檔案權限；不提供遠端存取或跨使用者隔離。

## 受限來源 manifest

`sources/peak.json` 只有 URL／selector／政策紀錄，沒有原文。`allow_fetch=false` 直接跳過網路；true 仍需每次通過 robots。`policy.reviewed_at` 必須含時區且距現在不超過 31 天；過期請重新檢查條款並記錄日期，不要機械式改日期。程式不會自動推定使用權。

每來源欄位固定為：

| 欄位 | 用途 |
|---|---|
| `source_id`, `url`, `title` | 穩定 ID、確切 HTTPS URL、操作人員標題；ID 不可改綁另一 URL |
| `source_type` | `official`、`wiki`、`third_party_analysis`、`player_test`；官方優先由審查者判定 |
| `language`, `declared_version` | 本批英文；頁面／遊戲版本有未知就記 unknown，不推定最新版 |
| `selector` | 一個 `main`／`article`／`div`／`section`／`body`，可加 `id` 或單一 class；必須恰好命中一個節點 |
| `interval_seconds` | 每 origin 至少 2 秒，來源清單預設 3 秒 |
| `policy` | `allow_fetch`、`reviewed_at`、`terms_url`、`notes`；人員審查記錄，不是授權證書 |

robots 合併相同 agent 群組，支援 Allow／Disallow／`*`／`$`、Crawl-delay、Request-rate，保守同時檢查 SSRKnowledge、GPTBot、ChatGPT-User，並拒絕 `ai-input=no`、`search=no` 或 `use=reference` 的全文用途。不透過更換 UA 規避限制。robots 404／410 視為未設規則；403／5xx／無法讀取則關閉蒐集。robots 與政策結果寫入 audit。

單頁最多 2 MB，robots 最多 512 KB，timeout 15 秒，沒有壓縮或非 HTML 內容支援。只對網路錯誤、429、500／502／503／504 最多嘗試 3 次；遵守 Retry-After 與已記錄的 origin cooldown。需要等超過 30 秒時回報 deferred，留待操作人員稍後重試；不立即重試、更換憑證或更換端點。cooldown 會跨程序保存。多個操作人員不應同時採集；此為小批單機工具。

## 草稿輸入與人工審核

輸入 `{"entries": [...]}`，每條固定欄位：

| 欄位 | 要求 |
|---|---|
| `entry_id`, `game` | 穩定 ID；`game` 固定 `PEAK:3527290` |
| `category` | `mechanic`、`item`、`status`、`guide`、`lore` |
| `name_en`, `name_zh`, `aliases` | 英文原名、繁中顯示名、1–30 個別名；中文譯名需標明是否編輯暫譯 |
| `summary_zh` | 編輯的繁中摘要，不複製長段正文 |
| `evidence_class` | 同來源類別；`official` 只能引用 official，`player_test` 只能引用標為實測的來源，不能把推論變成實測 |
| `editor`, `game_version`, `limitations` | 人／agent 編輯者、遊戲版本或 unknown、已知不足與衝突 |
| `citations` | 1–20 個 `{snapshot_id, locator, evidence_quote}`；quote 限 300 字元，必須在已保存正文中逐字存在 |

草稿可以綜合有依據的資料，但來源分類不是自動真實性保證。每個分類應區別官方設定、Wiki 彙整、第三方建議、玩家實測。故事／世界觀沒有核對來源就不建條目；不接受同人創作當設定。本批沒有執行遊戲，也不把任何資料標為本機玩家實測。

```powershell
# 先看私人草稿及原文；以下核准命令只能由實際完成審核的人使用。
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog entry --entry-id ENTRY_ID
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog snapshot --snapshot-id SNAPSHOT_ID --body
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog review-entry --entry-id ENTRY_ID --revision 1 --decision approve --reviewer YOUR_NAME --note '已核對引用及版本' --human-reviewed
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog publish-entry --entry-id ENTRY_ID --revision 1
```

`--human-reviewed` 是明確意圖 attestation，沒有身份認證；程式無法阻止有 DB／CLI 權限的使用者冒填 reviewer。Agent 不應對真實條目使用它。批准不是發布；兩步分開。拒絕只能對當前待審修訂，需修訂內容後重新送審。

## 重複、更新及搜尋語意

- 來源 URL 與 raw SHA／來源設定共同決定 immutable snapshot ID；相同內容不新增快照，新的 HTTP 取得事件仍保存。頁面 raw 更新產生新快照，舊快照仍可讀。
- 條目由 canonical JSON SHA-256 去重。同一輸入不新增修訂或重新取得核准；舊內容重匯不會把 head 回滾。改動會新增待審修訂，舊修訂可由 `entry --revision N` 讀回。
- 條目修訂、來源新快照或政策變更都可能使現有公開條目消失於正式查詢；採保守最新修訂策略，直到重做審核／發布。舊發布修訂仍保存在 DB，**不是**穩定版本公開快照服務；原有 JSON publish/query 仍提供獨立不可變版本。
- 名稱、別名、摘要全文一起使用 NFKC、casefold 與空白正規化，再以 SQLite `instr` 做 literal substring；支援一字／二字繁中詞、英文與全形文字，沒有 SQL／FTS 語法解讀。不做簡繁轉換、斷詞、相關性排序、拼字修正或向量檢索；按 entry ID 排序、最多 100 筆。小批 corpus 是線性掃描。
- 來源 raw／正文與條目 payload 讀回會驗證雜湊。來源中的指令只當文字保存，沒有 shell、eval、工具呼叫或 LLM 執行路徑。

## 本機驗證與結果界線

```powershell
uv --cache-dir .uv-cache --offline lock --check
uv --cache-dir .uv-cache --offline run python -m unittest discover -s tests -v
git diff --check
```

測試內 `Lunar Rope`／`月光繩`／`MOON ROPE`／`藍色落腳` 都是合成資料。測試涵蓋 source 政策與 robots 阻擋、失敗重試、403／轉址、持久限流、去重、來源更新過期、原文與條目完整性、中文／英文／別名／全文與 literal 搜尋、pending／rejected／approved 隔離，以及每個 CLI 呼叫都是新 Python 程序的批准／發布／讀回測試。這些結果不代表真實網站提供相同狀態或真實知識經過批准。

真實資料驗收應在最終 commit 再執行，將 `git rev-parse HEAD`、完整 CLI argv／exit code／輸出及檔案雜湊存到 **checkout 外** evidence 檔案。實際網址、阻擋原因與不轉載正文的結果摘要可放在 PR；DB／原文快取／草稿／完整私人輸出不放 Git。

可重跑入口：先 `catalog collect --manifest sources/peak.json`，再用 `catalog sources` 取得新 snapshot ID，對照正文編輯私人草稿 JSON，`import-drafts` 後分別用 `search --preview` 和正式 `search` 驗證。若所有真實條目仍待審，正式查詢回傳 `no_data` 才是正確結果。

本機遇到的 Steam、wiki.gg、BLAST、G2A、Polygon 限制在 manifest 記錄；未以其他來源鏡像規避。官方行銷頁與 Wiki 的區域數描述不同，本批不收區域總數或推定目前遊戲 build。所有中文別名為編輯暫譯，需人工確認。首批不是完整道具圖鑑或版本差異追蹤器。

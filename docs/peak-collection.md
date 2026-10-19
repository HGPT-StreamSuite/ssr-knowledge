# PEAK 小批來源蒐集、保存與搜尋

新增使用者提供文字的離線來源途徑與詳細道具資料，見 [PEAK Items 附件匯入](peak-items-upload.md)。HTTP來源與上傳來源的身分、權限及取得方式分開，不將上傳檔案說成直接爬取成功；既有審核及search=no隔離維持。

本批以未合併 PR #2 的 `8f02b722b4a70f30fd98681ee6e91ae434d71dc2` 為起點，新增 `catalog` 工作流。新 PR 的 base 是 `codex/ssr-knowledge-workflows`；`main` 尚未有該離線流程。Related to #1、#3。沒有修改其他 repo、部署、合併或共享套件。

## 能力與資料邊界

- `collect`：操作人員先研究條款並填入來源 manifest，再執行程式化 robots 檢查、HTTP 擷取、正文擷取、版本快照保存與事件記錄。不追蹤頁面連結、不執行 JavaScript、不使用 cookies／認證、不跟隨任何轉址。
- `import-drafts`：只驗證與保存**已編輯的** JSON；不自動翻譯、不呼叫 LLM、不驗證摘要是否正確推導自原文。每則引用需有存在於 pinned 正文的短錨點，人工仍須檢查語意與來源可靠性。
- `review-entry`／`publish-entry`：對指定修訂留下 reviewer、note、時間與明確 attestation，再獨立發布。真實資料本批保持待審；合成測試才會模擬批准。
- `search`：只搜尋已發布、當前修訂及當前來源；`--preview` 明確顯示審查資料，可含待審或拒絕狀態。結果含來源與快照 ID；不回傳原始 HTML／完整正文／私人引用短句。

SQLite `knowledge.sqlite3` 將 raw HTML（BLOB）與正文、來源設定及政策、HTTP header（白名單）、抓取時間、SHA-256、條目修訂與審核事件保存於一處。`snapshot --body` 和 `entry` 是本機私人審查介面；`sources` 和 `events` 也包含私人 metadata。**不應將這些輸出直接轉貼到公開 PR**。DB 不是加密儲存，使用既有 Windows 帳戶檔案權限；不提供遠端存取或跨使用者隔離。

## 受限來源 manifest

`sources/peak.json` 只有 URL／selector／政策紀錄，沒有原文。`allow_fetch=false` 直接跳過網路；true 仍需本機保存用途與本次用途均經審查為 allowed，再每次通過 robots。unknown 或 prohibited 都不擷取正文，原因仍分開記錄。`policy.reviewed_at` 必須含時區且距現在不超過 31 天；過期請重新檢查條款並記錄日期，不要機械式改日期。程式不會自動推定使用權。現在只有 Wikipedia 文字用途完成有限審查；Landfall 新政策發現與其他限制見 [coverage](peak-coverage.md)。

每來源欄位固定為：

| 欄位 | 用途 |
|---|---|
| `source_id`, `url`, `title` | 穩定 ID、確切 HTTPS request URL、操作人員標題；ID 不可改綁另一 URL。選填 `original_url` 須正規化為同一請求 URL，否則拒絕 |
| `source_type` | `official`、`wiki`、`third_party_analysis`、`player_test`；官方優先由審查者判定 |
| `language`, `declared_version` | 本批英文；頁面／遊戲版本有未知就記 unknown，不推定最新版 |
| `selector` | 一個 `main`／`article`／`div`／`section`／`body`，可加 `id` 或單一 class；必須恰好命中一個節點 |
| `interval_seconds` | 每 origin 至少 2 秒，來源清單預設 3 秒 |
| `policy` | `allow_fetch`、`reviewed_at`、`terms_url`、`notes`、`uses`；人員審查記錄，不是授權證書 |

`policy.uses` 必須分別包含 `local_cache`、`search_index`、`ai_input`、`ai_train`，各有 `{status: allowed|prohibited|unknown, basis: 審查依據}`。`collect --purpose local_cache|search_index|ai_input` 預設 local_cache；由於一定保存正文，local_cache 必須 allowed，本次指定用途也必須 allowed。沒有訓練流程。標成 ai_input 僅表示這次為該用途核對，不表示已呼叫模型或 LLM 已讀取。

robots 合併實際固定 `SSRKnowledge/0.1` UA 的最具體適用群組，支援 Allow／Disallow／`*`／`$`、Crawl-delay、Request-rate。GPTBot／ChatGPT-User 是不同身份，不能強加其群組；也不能換 UA／代理／端點繞過已觀察 403。Content-Signal 是另記的非標準用途訊號：search、ai-input、ai-train 的 yes/no 只對應各自用途；缺失、非 yes/no、互相矛盾標 unknown。明示 no 只限制對應用途（矛盾中有 no 也保守停止該用途）。`use=reference` 原樣存為 uninterpreted，不一刀切拒絕；`ai-train=no` 不誤封一般搜尋或本機保存，`ai-input=no` 仍拒絕 AI-input 採集。沒有把 robots Allow／search=yes 當作條款重用授權。早期相反的規則已更正。robots 404／410 視為未設規則；403／5xx／無法讀取則關閉蒐集。robots、適用群組、各用途訊號與政策結果寫入 audit。

robots HTTP 200 也先驗證內容：拒絕 HTML／XML challenge、Access Denied 等非結構化錯誤、壓縮回應、不支援的 charset、無效 UTF-8／ASCII 及非文字控制字元；這些情況不請求 target page。只支援 text/plain（省略 Content-Type 時按純文字處理）、UTF-8／ASCII 及 identity encoding。合法空白、空檔案或只有註解的 robots 仍視為無限制。後續 robots Disallow 只阻止新採集，不自動推定舊資料使用權撤回；明確 manifest `allow_fetch=false` 的既有隔離保護維持不變。

HTTPS 每次只解析 DNS 一次，整份答案若含非 public IP 就拒絕；TCP 只連到當次已驗證的 numeric IP，不再以 hostname 二次解析。HTTP Host、TLS SNI 及憑證名稱驗證仍用原 hostname，保留系統信任根、`CERT_REQUIRED` 與 `check_hostname=true`；沒有略過憑證錯誤的 fallback。單次 HTTP attempt 只嘗試一個已驗證 IP（雙棧優先 IPv4），外層重試仍受原上限限制。

此 transport 不支援 proxy：若 `urllib.request.getproxies()` 偵測到 HTTP／HTTPS／ALL proxy，會在 DNS／TCP 前 fail closed；明確停用自動 proxy handler，也拒絕 CONNECT tunnel，不會靜默繞過既有 proxy 設定。需要 proxy 的環境須另行設計可核對目的 IP 的 transport，不能關閉 TLS 驗證以繞過。

單頁最多 2 MB，robots 最多 512 KB，timeout 15 秒，沒有壓縮或非 HTML 內容支援。只對網路錯誤、429、500／502／503／504 最多嘗試 3 次；遵守 Retry-After 與已記錄的 origin cooldown。需要等超過 30 秒時回報 deferred，留待操作人員稍後重試；不立即重試、更換憑證或更換端點。cooldown 會跨程序保存。多個操作人員不應同時採集；此為小批單機工具。

## 草稿輸入與人工審核

輸入 `{"entries": [...]}`，每條固定欄位：

| 欄位 | 要求 |
|---|---|
| `entry_id`, `game` | 穩定 ID；`game` 固定 `PEAK:3527290` |
| `category` | `mechanic`、`item`、`status`、`guide`、`lore`、`location`、`creature`、`achievement`、`update`、`support` |
| `name_en`, `name_zh`, `aliases` | 英文原名、繁中顯示名、1–30 個別名；中文譯名需標明是否編輯暫譯 |
| `summary_zh` | 編輯的繁中摘要，不複製長段正文 |
| `evidence_class` | 同來源類別；`official` 只能引用 official，`player_test` 只能引用標為實測的來源，不能把推論變成實測 |
| `editor`, `game_version`, `limitations` | 人／agent 編輯者、遊戲版本或 unknown、已知不足與衝突 |
| `citations` | 1–20 個 `{snapshot_id, locator, evidence_quote}`；quote 限 300 字元，必須在已保存正文中逐字存在 |
| `taxonomy`（選填） | `{mapping_version: "peak-v1", source_path: [原站分類／章節], subtype: 子類別}`；保留來源結構，不把 Wiki 分類視為自有 schema。對映是編輯步驟，未自動分類 |

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
- 名稱／別名另外以NFKC、casefold及忽略空白作整個標籤匹配，`--names-only` 僅查此路徑並明示歧義。一般全文仍使用正規化後的literal substring；支援一字／二字繁中詞、英文與全形，不解讀SQL／FTS語法。精確名稱先列出，其餘按ID；不做簡繁轉換、斷詞、拼字修正或語意搜尋，最多顯示100筆。小批corpus線性掃描，詳見[雙語名稱與證據狀態](peak-bilingual-names.md)。
- 來源 raw／正文與條目 payload 讀回會驗證雜湊。來源中的指令只當文字保存，沒有 shell、eval、工具呼叫或 LLM 執行路徑。

正式搜尋還須遵守已觀察的用途限制：即使 `collect --purpose local_cache` 合法保存、manifest 的 search_index 為 allowed，引用快照的 robots 明示 `search=no` 仍排除整則條目。多來源摘要只要任一引用受限就整則隱藏，不自動裁切來源或洩漏受限片段。批准／發布是知識審核，不覆蓋來源用途。私人 `--preview`／`entry` 仍保留內容及原審核狀態供核對。

robots 的 search 缺失、非 yes/no 或其他用途的 no 不視為搜尋禁止；search 的 yes/no 衝突仍記 unknown，但含明示 no 時保守排除搜尋。舊快照缺少結構化 assessment 時，離線重解讀已保存 robots；不新抓頁。也檢查來源最近一次有效 robots 觀察，因相同 HTML／設定去重可能不新增快照，不能丟掉新觀察到的 search=no。單純後續 robots 路徑 Disallow 與搜尋用途 no 分開，前者不自動撤回舊資料使用權。條款未知仍依既有 manifest gate 處理，與 robots 未知不是同一狀態。

## 來源追溯與手動更新

`snapshot`／`sources`／`entry` 回傳 `provenance`：原始 URL、實際請求 URL、canonical URL 及依據、正文 selector、取得時間、來源更新時間及依據、宣告版本、頁面 revision（未知明示）、快照當時與目前用途狀態。引用另保留 locator／pinned snapshot。頁面 canonical link 只當 metadata，不跟隨或改綁來源；未取得時使用正規化請求 URL 並標明 page canonical unknown。來源修改時間可取頁面 modified metadata 或 HTTP Last-Modified，但不把 HTTP Date 當更新時間，不推定遊戲 build。舊快照沒有資訊的欄位讀回為 unknown／null，不補造歷史資料。

```powershell
# 只保存條款審查，不發出網路請求。
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog register-sources --manifest sources/peak.json
# 重解讀已保存 robots；標示觀察時間，不宣稱目前存取或條款授權。
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog source-status --source-id peak-wikigg-items --purpose ai_input
# 手動重取當前允許來源，再比較不可變快照（預設只有 metadata/hash）。
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog collect --manifest sources/peak.json --source-id wikipedia-peak --purpose ai_input
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog snapshot-diff --before OLD_ID --after NEW_ID
```

`snapshot-diff --body` 另回傳最多 200 行／50,000 字元的**私人正文差異**。比較本身不建立條目、不改動審核；人工／agent 核對後編輯新 JSON，重新匯入為新待審修訂。舊審核與發布紀錄不覆蓋、不自動沿用。來源頁 HTML 外框改變、正文不變也分開回報。沒有排程／背景監控、LLM 串接或自動驗證事實功能；來源 URL 存在不代表模型已讀取。未來使用正文前仍須核對當時用途與限制。

## 本機驗證與結果界線

```powershell
uv --cache-dir .uv-cache --offline lock --check
uv --cache-dir .uv-cache --offline run python -m unittest discover -s tests -v
git diff --check
```

測試內 `Lunar Rope`／`月光繩`／`MOON ROPE`／`藍色落腳` 都是合成資料。測試涵蓋 source 政策與 robots 阻擋、失敗重試、403／轉址、持久限流、去重、來源更新過期、原文與條目完整性、中文／英文／別名／全文與 literal 搜尋、pending／rejected／approved 隔離，以及每個 CLI 呼叫都是新 Python 程序的批准／發布／讀回測試。這些結果不代表真實網站提供相同狀態或真實知識經過批准。

HTTP 200 robots challenge／編碼錯誤的回歸測試逐項斷言 target requests=0，另驗空 robots 可正常取頁。DNS rebinding 測試以 public→private 改答的 synthetic resolver 加上記錄 numeric endpoint／HTTP wire bytes 的 synthetic socket，證明每次 get 只做一次 DNS lookup、TCP 只連已驗證 public IP、原 hostname 仍用於 Host／SNI；下一次解析變私網時不新增 socket。另涵蓋 IPv6、混合 public/private 答案、proxy、憑證驗證失敗及轉址。這些是 mock transport 回歸，不宣稱對真實網站實施 DNS 攻擊或錯誤憑證測試。

真實資料驗收應在最終 commit 再執行，將 `git rev-parse HEAD`、完整 CLI argv／exit code／輸出及檔案雜湊存到 **checkout 外** evidence 檔案。實際網址、阻擋原因與不轉載正文的結果摘要可放在 PR；DB／原文快取／草稿／完整私人輸出不放 Git。

可重跑入口：先確認 [coverage 與用途](peak-coverage.md)，只選當前允許來源，再以 `catalog collect --manifest sources/peak.json --source-id wikipedia-peak` 採集。用 `catalog sources` 取得新 snapshot ID，對照正文編輯私人草稿 JSON，`import-drafts` 後分別用 `search --preview` 和正式 `search` 驗證。若所有真實條目仍待審，正式查詢回傳 `no_data` 才是正確結果。即使已發布，來源的 search_index 用途未經審查為 allowed 也不出現在正式搜尋；預覽保留狀態供審查。

本機遇到的 Steam、wiki.gg、BLAST、G2A、Polygon 限制在 manifest 記錄；未以其他來源鏡像規避。官方行銷頁與 Wiki 的區域數描述不同，本批不收區域總數或推定目前遊戲 build。所有中文別名為編輯暫譯，需人工確認。首批不是完整道具圖鑑或版本差異追蹤器。

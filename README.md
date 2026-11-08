# ssr-knowledge

獨立執行的本機知識準備工具，只使用此 repo 與 Python 標準函式庫。沒有跨 repo 匯入、共用套件、服務或模型依賴。

## 可複用採集 Playbook

他遊戲若要採用同一套「規劃 → 擷取檔案 → 保存待審 → 直接查 DB」方案，先讀 **[可複用遊戲知識採集 Playbook](docs/reusable-game-collection-playbook.md)**（含 Mermaid 架構／序列／取得決策／進度狀態與落地檢查清單）。契約細節仍以本頁下方規格為準。

執行順序與責任以 [保存與查詢驗收規格](docs/persistence-and-query-acceptance.md) 為準：先依遊戲分析決定要存什麼，擷取程式交檔案，保存端整理並真正寫入待審修訂，再直接查同一 DB 驗收。文件 snapshot、查證紀錄與待辦不算知識保存完成。

## 即時 DB 驗收入口

已實作 [遊戲建庫計畫與分類欄位](docs/game-plan-contract-v1.md)，保存端驗證不可變計畫、逐欄證據與關聯，查詢頁直接讀指定 DB。PEAK 本機批次規模與缺口以實際 DB 及最新 acceptance 為準（例如 [peak-completion-acceptance.md](docs/peak-completion-acceptance.md)、[peak-timer-integrity-acceptance.md](docs/peak-timer-integrity-acceptance.md)、[peak-reception-expand-acceptance.md](docs/peak-reception-expand-acceptance.md)）；勿只信本段歷史摘要。規劃範圍含徽章、道具、區域與攻略等；查詢入口維持 `http://127.0.0.1:8767/`。

使用 `catalog --data-dir PATH serve-review` 啟動 `http://127.0.0.1:8765/`。每次搜尋、翻頁與開條目都重新唯讀查詢實際 SQLite，顯示 DB 路徑及讀取時間；有中英文／別名搜尋、分類、來源與徽章關聯。資料庫失敗時直接報錯，不改用示範或上次資料。啟停、狀態與驗收步驟見 [即時唯讀驗收](docs/live-review.md)。舊 HTML 匯出僅保留作快照。

詳細來源可用 [有界批次採集](docs/research-batches.md) 保存逐條進度、失敗分類、有限重試及英文待審擷取；[PEAK 詳頁可行性結果](docs/peak-detail-feasibility.md) 分開記錄合成流程測試、真實存取阻擋與人工索引候選。目前沒有通過全庫原站採集的可行性驗證。

## PEAK 首批本機 catalog

新增 opt-in `catalog` CLI：從經操作人員檢查的**確切 HTTPS URL 清單**低速蒐集，將原始 HTML、選定正文、來源政策、時間、HTTP metadata 及內容雜湊保存在 checkout 外的 SQLite。只處理 PEAK（Steam app `3527290`）；League of Legends 與 Satisfactory 尚未開始。

蒐集不生成或批准知識。繁中摘要、英文原名、中文別名、分類與引用錨點由人員或 agent 編輯 JSON 後匯入，**全部預設 `pending_review`**。正式搜尋只讀已經明確審核及發布的當前修訂；待審、拒絕、來源變動後過期的條目只能在明確指定 `--preview` 的審查預覽出現。原有檔案工作流與 catalog 是各自獨立的儲存格式，沒有自動互相發布。

道具名稱以目前官方遊戲資源為優先：121件已核對PEAK2.6.b同key中英字串，11件維持暫譯／待查，目標zh-TW。官方名稱優先顯示、舊暫譯保留標記別名，`search --names-only`明示同ID命中與歧義。宣傳詞和歷史社群模組不冒充官方遊戲字串。唯讀擷取另需專案本機的可選extraction依賴群組，見[官方遊戲資源名稱](docs/peak-official-game-names.md)及[雙語檢索](docs/peak-bilingual-names.md)。

```powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:SSR_KNOWLEDGE_DATA_DIR = 'C:\Users\User\Documents\SSRKnowledgeData'
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog stats
# 先檢查 coverage、用途與 reviewed_at；目前只有 Wikipedia 文字完成有限用途審查。
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog register-sources --manifest sources/peak.json
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog source-status --source-id peak-wikigg-items --purpose ai_input
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog collect --manifest sources/peak.json --source-id wikipedia-peak --purpose ai_input
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog sources
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog import-drafts --file C:\private\peak-drafts.json
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog search --text '背包' --preview
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog search --text 'Backpack'
```

資料目錄也可由 `catalog --data-dir PATH` 指定；預設為 `%LOCALAPPDATA%\SSRKnowledge\data`，任何 Git checkout 內的路徑都會被拒絕。執行前檢查至少 50 MiB 可用空間。不安裝額外 SQLite extension、向量資料庫或模型。詳細資料格式、審核命令、來源追溯及 `snapshot-diff` 手動更新見 [PEAK 蒐集與驗收](docs/peak-collection.md)；已收／待收／待整理／受限與 Wiki 對映見 [coverage](docs/peak-coverage.md)。URL 不等於 LLM 已讀取；用途未知不自動視為許可或禁止。

現有資料的用途整理、獨立遊戲徽章、道具關聯與精簡 DB 驗收頁，見 [內容整理與徽章](docs/peak-organization.md)。`catalog relations` 可讀回穩定 ID 關聯，`catalog render-review` 從 SQLite 產生私有可讀頁；不會核准或發布資料。

## 原有離線工作流

使用者提供的 PEAK Items 文字也可透過 `catalog import-text-source` 保存原始bytes與來源／授權，再以 `parse-peak-items` 重現列數與數值解析。此途徑沒有HTTP請求，不代表直接爬取成功。本輪附件實際132個唯一道具（頁首宣稱134，差2待查），128新增／4更新，全部待審；詳見 [道具附件匯入與缺欄](docs/peak-items-upload.md)。

1. **預建知識**：從本機 JSON source bundle 產生待審 candidate。
2. **缺口補充**：將離線 gap 與已整理來源記錄保存為研究包，再由研究包建立待審 candidate；不自行上網研究。
3. **固定工具準備**：驗證、保存及讀回不可變版本 adapter manifest；`network_enabled=false`，仍不連線 HTTP API／MCP。catalog 蒐集器是獨立明確呼叫的功能，不會更動這些 manifest。

需求為 Python 3.11+；預設 catalog 使用標準函式庫。已鎖定的可選 `extraction` 群組供官方遊戲資源唯讀擷取使用。

```powershell
uv --cache-dir .uv-cache --offline lock --check
uv --cache-dir .uv-cache --offline run python -m unittest discover -s tests -v
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge prebuild --source fixtures/prebuild-source.json --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge research --gaps fixtures/gap-export.json --records fixtures/gap-records.json --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge supplement --research-id RESEARCH_ID --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge tools --save --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge tools --version v1.0.0 --state-dir .local-state
```

檔案 candidate 也必須明確審核後才能發布；舊 `query` 只讀指定版本 JSON 並重新驗證 records SHA-256。

```powershell
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge review --candidate-id CANDIDATE_ID --decision approve --reviewer human --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge publish --candidate-id CANDIDATE_ID --version v0.1.0 --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge query --version v0.1.0 --kind game_item --text '星砂' --state-dir .local-state
```

`fixtures/` 與測試內的 Lunar Rope／月光繩均為合成資料，不能作為真實 PEAK 知識。真實 cache、DB、草稿與私人驗收紀錄不提交 Git。人工審核 attestation 是本機操作邊界，沒有登入或身分驗證機制；本工具不會自行替使用者核准真實知識。

## 獨立本機驗收頁

共通必過門檻是「使用者預設瀏覽器實際開啟並正常操作」。目前此門檻受阻，**網頁驗收為 BLOCKED／未通過**；程式、檔案或模擬 DOM 檢查通過不能替代。

直接開啟 [本機驗收工作台](web/acceptance/dist/index.html)，可輸入合成 JSON、檢視 8 份契約與實際結構驗證結果。這是無服務的靜態頁面，資料僅在記憶體；不呼叫 Python、CLI 或 SQLite，不執行入庫、審核或發布。

[獨立驗收標準](docs/independent-acceptance.md) 列明輸入、輸出、錯誤、隔離及證據要求；[開啟方式與驗證紀錄](docs/acceptance-web.md) 明列已測與未測範圍。既有 localhost HTTP 權限阻擋仍有效，不啟動服務或改埠重試。契約結構通過不代表知識工作流已完成。

另有固定 [原生驗收 handler／CLI](docs/acceptance-native.md)：`python -B -m ssr_knowledge acceptance-native`，只從 stdin 接受固定操作的有界合成 JSON，實際呼叫本 repo 的 Store/Catalog，不接受路徑、指令、端點或 ACL。網頁到此 handler 的傳輸層尚未接通，不能把 CLI 結果當成預設瀏覽器驗收通過。

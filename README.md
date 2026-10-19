# ssr-knowledge

獨立執行的本機知識準備工具，只使用此 repo 與 Python 標準函式庫。沒有跨 repo 匯入、共用套件、服務或模型依賴。

## PEAK 首批本機 catalog

新增 opt-in `catalog` CLI：從經操作人員檢查的**確切 HTTPS URL 清單**低速蒐集，將原始 HTML、選定正文、來源政策、時間、HTTP metadata 及內容雜湊保存在 checkout 外的 SQLite。只處理 PEAK（Steam app `3527290`）；League of Legends 與 Satisfactory 尚未開始。

蒐集不生成或批准知識。繁中摘要、英文原名、中文別名、分類與引用錨點由人員或 agent 編輯 JSON 後匯入，**全部預設 `pending_review`**。正式搜尋只讀已經明確審核及發布的當前修訂；待審、拒絕、來源變動後過期的條目只能在明確指定 `--preview` 的審查預覽出現。原有檔案工作流與 catalog 是各自獨立的儲存格式，沒有自動互相發布。

道具名稱以目前官方遊戲內為優先；132件目前繁中仍是待核對暫譯，目標zh-TW。結構化名稱來源／語系與`search --names-only`明示別名命中及歧義，宣傳詞和歷史社群模組不冒充官方UI名稱。見[雙語名稱與檢索](docs/peak-bilingual-names.md)。

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

## 原有離線工作流

使用者提供的 PEAK Items 文字也可透過 `catalog import-text-source` 保存原始bytes與來源／授權，再以 `parse-peak-items` 重現列數與數值解析。此途徑沒有HTTP請求，不代表直接爬取成功。本輪附件實際132個唯一道具（頁首宣稱134，差2待查），128新增／4更新，全部待審；詳見 [道具附件匯入與缺欄](docs/peak-items-upload.md)。

1. **預建知識**：從本機 JSON source bundle 產生待審 candidate。
2. **缺口補充**：將離線 gap 與已整理來源記錄保存為研究包，再由研究包建立待審 candidate；不自行上網研究。
3. **固定工具準備**：驗證、保存及讀回不可變版本 adapter manifest；`network_enabled=false`，仍不連線 HTTP API／MCP。catalog 蒐集器是獨立明確呼叫的功能，不會更動這些 manifest。

需求為 Python 3.11+；現有 `uv.lock` 無第三方依賴。

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

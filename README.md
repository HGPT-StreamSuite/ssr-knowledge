# ssr-knowledge

`ssr-knowledge` 是獨立執行的本機知識準備工作流，只用本 repo 檔案和 Python 標準函式庫。正式問答不需要此 repo 運行；不假設共用資料庫，也不匯入其他 repo。

## 本機工作流

1. **預建知識**：讀取本機 JSON source bundle，整理為待審 candidate。是否每批預建都必須人工審核仍待決；本機預設先要求人工核准才發布。
2. **缺口補充**：將離線匯出的 gap 和人工整理的來源材料另存為研究包，再由研究包建立待審 candidate。缺口補充必須人工審核後才能發布。
3. **固定工具準備**：驗證並可選擇保存／讀回不可變版本 manifest，記錄 adapter kind、介面版本、參數與輸出；不執行或連接工具。

人物／遊戲資料方向已定為自有知識格式及人工整理的 Wiki／網路材料；本機 prebuild 接收已整理的 JSON bundle。現有素材是虛構 fixture，不執行網路抓取或自動研究。若未來啟用網路 provider，須先決定允許來源端點、授權／引用方式及更新頻率。

研究包、候選與已發布版本分開保存。發布建立不可變版本 JSON 和 records SHA-256；讀取指定版本時會重驗摘要。跨 repo bundle 交付與自動匯入明確延後，不是本批功能缺口。

## 本機執行

需求為 Python 3.11+；只用標準函式庫。`uv.lock` 記錄空依賴集合。

```powershell
uv --cache-dir .uv-cache --offline lock
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge prebuild --source fixtures/prebuild-source.json --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge tools
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge tools --save --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge tools --version v1.0.0 --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m unittest discover -s tests -v
```

CLI 會回報 candidate ID；需明確審核後才可發布：

```powershell
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge review --candidate-id CANDIDATE_ID --decision approve --reviewer human --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge publish --candidate-id CANDIDATE_ID --version v0.1.0 --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge query --version v0.1.0 --kind game_item --text "星砂"
```

缺口研究只匯入提供的 offline gap 和來源材料，不會上網搜尋：

```powershell
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge research --gaps fixtures/gap-export.json --records fixtures/gap-records.json --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge supplement --research-id RESEARCH_ID --state-dir .local-state
```

## 契約與狀態界線

- `contracts/` 是本 repo 自己的 JSON Schema；測試使用標準函式庫驗證本地 fixture 與使用者提供的文件。query response 只含 `status`、`materials`、`sources`。
- `tools --save` 將 manifest 寫入 `tool-configs/`；`tools --version v1.0.0` 讀回指定版本。manifest 強制 `network_enabled=false`，provider 保持 undecided，不儲存憑證或連線。
- 本機功能已完成：prebuild、離線缺口研究包、candidate 審核與發布、摘要重驗、固定工具 manifest 保存／讀回。
- Fixture only：範例素材為虛構內容；研究證據由人工離線提供；HTTP API／MCP 僅作未連線 manifest 範本。
- 真實來源 provider 尚未接線；人物／遊戲來源方向已決定，實際端點與授權政策待需要連網時決定。
- 跨 repo 交換／整合與 STT 明確延後，不是本批驗收條件。沒有網路研究、平台連線、模型呼叫、部署或遠端持久化。

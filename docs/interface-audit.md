# 系統性接口整理與未接通邊界

機器可讀清單：[interfaces/manifest.json](../interfaces/manifest.json)。固定 native 請求/回應 schema 位於同目錄，不混入原有8份領域契約；[原生操作](acceptance-native.md) 有確切語意。`tools/build_interface_inventory.py --check` 直接比對實際 argparse CLI、固定操作與完整原生 runtime source hashes，避免只靠名稱/HEAD假定版本相同。

## 職責與流程

此 repo 獨立完成來源文件保存、知識整理/待審、人工審核/發布、明確版本或catalog查詢；不負責聊天生成、平台身份判定、外部reader的完整Record或真實LLM。JSON離線儲存與SQLite catalog為不同持久格式，不能自動互相發布。

固定native模組分工：`acceptance_native`限定協定/隔離與分派；`contracts`驗證格式子集；`workflows`建立候選/研究；`store`處理JSON不可變版本和digest；`catalog`處理SQLite快照/引用/修訂/用途政策。可替換分派或頁面傳輸，但不得繞過上述驗證器、來源綁定或來源政策。native handler只用新建合成state，沒有可指定正式DB的參數。

入口與出口：legacy CLI的實際command/catalog action清單由機器清單列出；離線candidate/research/published對應現有schema；catalog search回`scope/query/status/matches/...`，不是通用Record。native stdout回自有版本化envelope；exit0代表請求已處理，data仍可是schema_invalid/no_data/rejected；exit1是拒收/錯誤，非法CLI選項exit2且stderr不是JSON。字數/bytes/深度/節點/record上限及非法選項見native規格。

本輪最小相容修補：舊非catalog CLI遇ContractError/ValueError/OSError時，從traceback改成與catalog一致的stdout JSON `status=error,error=...`，保留exit1；argparse仍exit2。正常輸出及舊參數不變，新增真實CLI錯誤測試。CLI來源hash改變後不沿用舊native收據，重新取得同版輸入/輸出再更新runtime綁定。

合成收據在 `interfaces/receipts/`，由本輪真正CLI輸入/輸出擷取，綁定原始stdin hash及runtime所有Python、領域schema和固定來源fixture的hash；不是手寫成功JSON。臨時state的before/after、原文hash/引用、revision、stale、用途與清理狀態均保留。它們只證明明示虛構內容的本機流程，不證明真站事實、來源新鮮度或預設瀏覽器。

## 上游：collector → knowledge

`ssr-collector-peak`提供`ssr.collection.v1`單文件，根欄位為format/producer/source_ref/document/bundle_id。source_ref的source_id/config_sha256必須精確對中央現行設定；document含原文bytes、正文、各自hash及captured_at/observed_at。時間需時區，observed不得早於captured；未知來源更新時間不以擷取時間替代。bundle/producer/hash不是身分驗證或權限。

原文接收不建立知識修訂。`import-drafts`仍須核對snapshot、逐字引文與欄位/關聯；saved pending不是審核/發布。重送不加修訂，更新不繼承批准，舊觀測不倒退latest。來源設定/用途不由包內授予。完整已實作規格見 [collection-contract-v1.md](collection-contract-v1.md)，不新增另一種強制上游格式。

## 現有下游：knowledge → ssr-chat

唯讀觀察 `ssr_chat/catalog_knowledge.py`：consumer用`catalog search --text=NAME --names-only --limit 2`，要求scope=published、query原樣、names_only=true、status=ok/no_data、truncated=false且最多一筆；match須published、stale=false、match_type=exact_name，包含entry/sources/revision_id/payload_sha256。

consumer另要求每個source的`provenance.snapshot_usage.ai_input.status`及`current_usage.ai_input.status`都為allowed。**本輪合成收據的ai_input是unknown；即使search_index允許、已發布且查得結果，仍不能當作LLM輸入許可。** native catalog_check的formal query預設names_only=false，只是驗收輸出，不能直接冒充此consumer的names-only回應。原有catalog CLI已提供該獨立選項，未修改consumer或放寬政策。

此為來源程式唯讀核對，不是本輪跨repo或真實模型驗收；外部repo HEAD未在本repo任務中宣稱固定。

## 待總控決策：catalog → hgpt-game-store / hgpt-ssr-game-search

唯讀觀察component契約1.0.1：reader/store的完整Record要求schema_version、record_id、source_id、source_event_id、revision、event_time、received_at、scope、actor_account_id、text、record_kind、quality_flags、source_refs、access_scope。SourceRef另要求source_id/record_id/revision/locator/transformation_version；scope六維domain/platform/channel_id/game_id/session_id/content_version；來源AccessScope有read_scopes/write_scopes，不能由呼叫者自授。

本repo的離線Record是record_id/kind/topic/summary/tags/source，catalog entry則是遊戲分類/名稱/摘要/game_version/引用與snapshot。它們都不是上述完整Record。catalog的global revision_id、source snapshot hash、declared game_version及created/published時間，不等於外部每筆Record的revision、source_event_id、可靠event_time或content_version。用途四分法也不能自動轉成來源ACL selector。

| 提供者 → 消費者 | 確切差異 | 相容建議／狀態 |
|---|---|---|
| ssr-knowledge catalog → hgpt-game-store/search | 缺外部schema_version、source_event_id、event/received時間、完整scope、actor、record_kind/quality_flags/source_refs/access_scope；summary_zh不是完整Record envelope | 由總控定義明確版本化bridge與來源控制ACL/scope、身份、時間及版本依據；缺資料應拒收，不填猜測值。本repo沒有冒稱已匯出。 |
| importer/store Evidence → reader完整Record | Evidence是檢索投影，缺Record的schema_version、record_kind、access_scope；另多layer/source_kind/match_reasons/rank | 請提供者交付真正完整Record或明確受控的Record export；不得把Evidence改名、補寬鬆ACL或混用cache掩蓋缺欄。交總控協調，未改任何他repo。 |
| 本repo no_data → component no_match等狀態 | 狀態字彙與版本不是同一協定 | bridge顯式映射並保留來源status/reason；不得把現有CLI全域改成外部schema。 |

## 已驗、未驗與阻塞

最小CLI錯誤出口修補改變runtime後，已重新取得22個原生CLI矩陣與3份收據，再同版執行142項安全Python案例：134 pass、8選配skip、0 fail/error；20項受限操作排除。13個native/CLI及5個interface/receipt案例包含在134 pass。舊版128 pass及原收據分開保留，不混用指紋。頁面真正native傳輸未接通；預設瀏覽器共通門檻BLOCKED。既有connect/WinError10013、file URL、Registry/CIM及不確定拒絕保留，不以其他工具、埠、路徑或HTTP替代。

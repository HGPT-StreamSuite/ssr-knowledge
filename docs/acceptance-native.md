# 固定原生驗收入口（不是已接通的網頁）

`python -B -m ssr_knowledge acceptance-native` 從 stdin 讀一個 UTF-8 JSON 請求，回傳真實原生結果；stdout 是 JSON，合法處理 exit 0，拒收/原生錯誤 exit 1。沒有任意路徑/指令/環境選項，也沒有 HTTP server。

固定請求根欄位只有 `format`、`operation`、`input`。format 為 `ssr.knowledge.acceptance.request.v1`；上限 65,536 bytes、深度 32、5,000 節點，拒絕非有限 JSON 常數及未知欄位。不得傳入 Python/DB/檔案路徑、外部端點、來源政策、ACL 或審核者。

| operation | input | 真實呼叫與輸出 |
|---|---|---|
| validate | 固定8契約之一的 schema 名稱、value | Python `contracts.validate`；回傳 schema_valid/schema_invalid 及原生錯誤，不寫 state。結構通過不是入庫或發布。 |
| prebuild_preview | source | `prepare_prebuild`→`LocalKnowledgeStore`保存→讀回；只接受1–10筆 fixture- ID、虛構來源、fixture:// locator，結果保持 pending_review。 |
| gap_supplement_preview | gaps、records | 原生研究包→候選保存/讀回；核對 gap ID、purpose/kind、引用來源及內容；不自動研究或補造來源。 |
| catalog_check | 固定 scenario、query（1–200字） | 新建合成 SQLite，真正保存快照/草稿、重送、查詢及新唯讀連線讀回。scenario 只有 pending、published、policy_denied、source_changed、bad_citation。 |

catalog 的來源、原文、版本與政策全為內建的自寫虛構 fixture，不接受呼叫端來源/政策變更。`published`等測例只在當次可拋棄 DB 建立明示的「合成模擬審核」事件，不代表使用者批准真實內容。`policy_denied`使用固定負向政策情境，驗證已發布內容不再進正式搜尋；`source_changed`驗證 stale；`bad_citation`驗證原文不存在的引文拒收且沒有知識 rows。

每次有 state 的請求都建立全新臨時目錄，結束後只清除此請求新建的 state。輸出保留 before/after counts、artifact 相對名稱/bytes/SHA-256、真正候選/引用/版本/政策結果及 temporary_state_removed；不洩漏完整機器環境或 production DB 路徑。query_only 是原生新連線的 PRAGMA 實際讀值。

範例（固定 repo 合成檔案，不是 handler 的檔案選項）：

```powershell
Get-Content -Raw fixtures/acceptance-native.synthetic.json | python -B -X utf8 -m ssr_knowledge acceptance-native
```

`status=ok`只代表 handler 已執行並回傳觀察；`data.formal.status=no_data`、`data.state=rejected`等仍是原生拒絕/無資料，不得說已核准或搜尋成功。每個請求獨立，重送不共享 state；單次 catalog 內也實際測試 duplicate import。

**接線程度：CLI → 固定 handler → 原生 Store/Catalog；網頁 → handler 尚未接通。** HTML 只顯示同一固定請求，不假裝執行它。被拒的 server/loopback/file URL/Registry/CIM 不因新增入口而重試；後續需總控在有權限的既有整合面協調傳輸層。共同的預設瀏覽器實際操作門檻仍為 BLOCKED。

本輪CLI錯誤出口修補後，實際執行13個 native/CLI測例及5個interface/receipt測例，全部通過。當前安全 Python 集合共142項：134 pass、8 UnityPy選配 skip、0 fail/error；另20項因既有 HTTP/server 或不確定操作被排除，未重試。父測試程序觀察到的 socket/DNS/bind 操作為0。完整同版隔離輸入、輸出、exit code、原生 before/after、artifact hashes及來源指紋保存於 checkout 外。首輪舊CLI指紋的128 pass證據與收據另保留，未混用。

另外實際以 stdin 呼叫 CLI 22個情境，22項預期結果全部符合：含4操作、用途禁止、來源更新stale、引文拒收、空值/非法/越界、禁止DB/Python/endpoint/ACL選項及錯誤後恢復。負向情境的「通過」指正確拒收，不代表內容被允許。實際原始 JSON 回應另存證據，不用預製 fixture 輸出代替。

JavaScript本輪17個程式案例亦通過；以上都不是預設瀏覽器實測。網頁 → handler 傳輸仍未接通，共通門檻維持 BLOCKED。真實來源的內容真偽、新鮮度、正式DB或真實人工批准均未驗證。

可機器讀取的請求/回應schema、CLI/library入口與出口清單、runtime指紋及3份本輪真實合成CLI收據位於 [interfaces](../interfaces/manifest.json)。重建清單用 `python -B -X utf8 tools/build_interface_inventory.py`，唯讀核對加 `--check`。收據不是產生器捏造的輸出；runtime變更會使收據契約測試失敗，應保留舊證據並取得新同版收據。跨repo欄位差異見 [接口稽核](interface-audit.md)。

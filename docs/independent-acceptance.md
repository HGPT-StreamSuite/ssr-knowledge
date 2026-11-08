# ssr-knowledge 獨立驗收標準

本頁約束本 repo 的成果，不涵蓋 collector 取得成功、聊天回覆、跨 repo 整合或正式服務部署。

## 所有 repo 共通門檻：預設瀏覽器可實際開啟並正常操作

**本 repo 網頁驗收狀態：BLOCKED／未通過。** 此共通門檻不得降低或標為不適用；程式存在、HTTP 成功、檔案連結存在、後端或模擬 DOM 測試通過都不能替代。

| ID | 每個 repo 相同的必要門檻 | 本 repo 實際結果 |
|---|---|---|
| G01 | 確認使用者的預設瀏覽器，使用該瀏覽器開啟交付入口 | 未確認。唯讀查詢 HTTPS UserChoice ProgId 遭 `Requested registry access is not allowed`；未改預設應用或重試。先前 Chrome 選擇並非預設瀏覽器已核實的證據。 |
| G02 | 實際看見頁面及所需控制項，記錄開啟位置和畫面證據 | BLOCKED。先前 CUA 建立 Chrome 分頁開啟本入口 `file://` URL 遭協定政策拒絕；沒有實際畫面或可用 HTTP URL。 |
| G03 | 在預設瀏覽器實際操作適用的正向輸入→執行→實際輸出 | 未驗證。8 契約的正向合成例只有程式結果，無瀏覽器操作證據。 |
| G04 | 在同一瀏覽器實際操作錯誤、重複提交、取消／返回等適用流程，確認可正常恢復 | 未驗證。記憶體事件模型只能輔助檢查，不能計為此門檻通過。 |
| G05 | 保存與同版原始檔案對應的實際瀏覽器操作記錄與結果 | 未達成。已有 branch/HEAD/dirty/hash、命令、程式輸出與拒絕原因，但沒有真實瀏覽器操作記錄。 |

只有所有適用共通門檻及本 repo 功能測例均有真實瀏覽器證據時，才能宣告網頁驗收通過。受阻、不適用、模擬或未測都不得算成通過。不安裝或更換瀏覽器、不改預設應用／安全設定／權限，不重試既有拒絕，也不透過其他工具、路徑、埠或執行器繞過。

## 工作版本與既有證據

- 工作 checkout：工作區 `repos/ssr-knowledge`；remote 為 `HGPT-StreamSuite/ssr-knowledge`。
- 本輪基準：`codex/peak-local-collection`，HEAD `bd2f415d29eacd489d349e88c191148ba80712f1`。頁面修改是此 HEAD 上尚未提交的工作檔。
- 開始前已有 README 修改及 10 份未追蹤的 acceptance/playbook 文件；不得覆蓋。每次驗收須記錄實際 HEAD、branch、dirty 與逐檔 SHA-256，不能只引用這段基準。
- 2026-11-05 既有 140 個案例記帳：122 個斷言通過、10 個 HTTP 權限阻擋、8 個 UnityPy 選配略過。122 包含前輪沿用的 8 項斷言；該前輪包裝另有 exit 1 與 6 次自設唯讀保護攔截，未宣稱整體通過。
- HTTP `socket.connect` 至 `127.0.0.1` 臨時測試埠曾遭 WinError 10013；CIM 程序清單及舊 checkout Git 查詢亦曾遭拒。這些操作不在本頁測試中重試。

## 1. 本 repo 功能測例與可操作範圍

入口為 `web/acceptance/dist/index.html`，以檔案直接開啟，不需 server、安裝、帳號或連線。

瀏覽器版驗證器讀取本 repo 的 8 份 `contracts/*.schema.json` 產生的副本，對齊 `ssr_knowledge/contracts.py` 的 `type`、`enum`、`required`、`properties`、`additionalProperties`、`items` 子集。**它不是完整 JSON Schema 實作，也不呼叫 Python、CLI 或 SQLite。** 不驗證記錄 digest、版本語意、來源許可、引文真實性或發布資格。candidate/published 的 records 僅依各自 schema 檢查；不隱含套用 record schema。

僅輸入合成 JSON。資料留在頁面記憶體，不使用網路、localStorage、cookie、檔案上傳或自動匯出。關閉／重新整理會清空自訂輸入。頁面不載入私人 DB、日誌、憑證或完整機器環境。

| ID | 輸入／動作 | 預期輸出與成功判定 |
|---|---|---|
| W01 | 直接開啟入口 | 載入 CSS、8 契約與範例；顯示靜態／未接通服務。沒有 server、外部資源請求或合成結果冒充 DB 查詢。 |
| W02 | 選契約、載入合成範例、執行 | 實際解析與驗證；輸出 `schema_valid`、使用的 schema 與空 errors。提醒只證明結構，不代表入庫、批准或發布。 |
| W03 | 缺少必填欄位／錯誤型別／額外欄位／非法 enum | `schema_invalid`，列出確切 JSON 路徑；錯誤集合與 Python 子集驗證器一致。 |
| W04 | 空字串／破損 JSON／未知契約 | `input_error`，不保留上一輪成功結果；不得顯示通過。 |
| W05 | 同一輸入再次提交 | 重新計算，結構結果相同；不增寫資料、不累加知識條目。待執行時重複提交只保留同一工作。 |
| W06 | 按「取消待執行」或 Escape | 僅取消尚未開始的排程，顯示 `cancelled` 且無驗證結果；保留輸入。不聲稱可中斷同步解析中的 JavaScript。 |
| W07 | 結果後「返回編輯」／切換契約／修改輸入 | 返回輸入焦點；編輯或換契約即使舊結果失效，保留/更新輸入依按鈕文義，不冒用舊結果。 |
| W08 | 清除輸入後重送 | 清空結果；下一次提交回報空輸入。 |
| W09 | 含 HTML/script 的字串、`__proto__` 欄位 | 只作文字；不執行、不污染物件原型；額外欄位照契約拒收。 |
| W10 | 超過 256,000 UTF-8 bytes、深度超過 64、節點超過 10,000 | 有界拒收為 `input_error`；不開始 schema 遞迴。數字非有限或超出 JS 安全整數範圍亦明確拒收。 |
| W11 | 桌面及窄視窗、鍵盤 Tab/Enter/Ctrl+Enter/Escape | 有可見焦點、關聯 label、狀態 live region、可捲動輸出；窄視窗切單欄。實際瀏覽器操作與程式測試分開記錄。 |
| W12 | 查閱標準／證據 | 可讀本頁及 `acceptance-web.md`，展示經整理的歷史基線與限制，明示未重新執行；不把歷史摘要當成當次驗收結果。 |

**W01–W12 的預設瀏覽器實測結果全部為未驗證／受阻。** 下列程式通過結果不改變這個狀態。W02 的 `schema_valid` 只是單筆 JSON 結構結果，不是網頁驗收通過。

瀏覽器輸入採嚴格 JSON（不接受 NaN/Infinity）。Python JSON 的寬鬆數字處理及任意精度整數可能不同；上述輸入界線是頁面明示的額外限制，不宣稱兩種 parser 完全等價。目前 8 份契約沒有 integer/number 欄位；若日後加入，必須先補齊 Python 整數/浮點 token 與 JavaScript Number 的差異驗收，不能直接宣稱相容。

## 2. 本 repo 原有工作流的獨立標準

固定原生入口與請求欄位見 [acceptance-native.md](acceptance-native.md)。CLI/handler 可在全新合成 state 執行原生功能；頁面傳輸尚未接通，G01–G05 不變。本輪必測：正確/空值/非法/越界請求、禁止 path/command/endpoint/ACL、pending 發布拒絕、重送不增修訂、精確引文、source_changed stale、固定用途政策拒絕、新唯讀連線讀回、錯誤後全新請求恢復與臨時 state 清理。

以下沿用 [保存與查詢規格](persistence-and-query-acceptance.md)、[檔案交接](collection-handoff.md)、[即時唯讀查詢](live-review.md)。靜態頁不提供這些操作。

| 範圍 | 輸入與隔離 | 成功與邊界判定 |
|---|---|---|
| 離線知識準備 | fixtures 合成 source/gap/research；新建專用 state | 產生 pending candidate；未批准不可發布；指定版本查詢驗 digest；重版本/拒絕/竄改須拒收。 |
| 來源與文件保存 | 合成 source plan/collection；checkout 外的新 SQLite | 核對政策、時間、原文/正文 hash；預設唯讀驗證；apply 原子保存；重送不新增，舊觀測不倒退，失敗不留半份。 |
| 待審知識 | 合成草稿及已存在 snapshot/plan | 精確引用、typed fields/缺欄與關聯驗證；新修訂 pending；重送 unchanged；批准與發布只針對明確修訂，不能繼承。 |
| 查詢 | 同一合成 DB，以新程序讀回 | CLI 查得相同 revision/欄位/引文/關聯；正式搜尋排除 pending/rejected/stale/用途禁止資料；只讀不得建替代庫。 |
| API／頁面 | 同一合成 DB、loopback 臨時測試服務 | 實際 JSON/HTML 與 DB 一致；Host/Origin/HTTP 方法控制；失檔/錯庫明確錯誤。此項因既有權限拒絕保持 BLOCKED，不在本輪重試。 |

真實資料的完成仍須逐筆「保存 pending 修訂 → 新程序讀回 → API → 使用者實際頁面」證據；測試通過、schema_valid 或找到 snapshot 都不能替代。

## 3. 已實際驗證結果：限程式檢查

- 本輪CLI錯誤出口修補後的當前原生安全集合：142項實際執行，134 pass、8選配skip、0 fail/error；20項既有HTTP/server或不確定操作排除未重試。13個固定native/CLI測例及5個interface/receipt測例包含在134 pass；舊CLI指紋的證據分開保留。
- 本輪真正stdin CLI矩陣22項符合預期，完整請求、回應、exit code、before/after與artifact hash另存。同一原生功能的負向拒收不是資料被允許；此集合仍不算瀏覽器通過。
- 17 個不同 JavaScript 案例通過：12 個結構／狀態案例及最終 5 個記憶體事件案例。
- 4 個 Python 檢查通過：契約與 fixture bytes、合成例、Python/JavaScript 錯誤集合及本機相對連結。
- 靜態資料包同步檢查、Git whitespace 檢查通過。這些只證明程式及檔案範圍。
- 原生工作流歷史結果另按固定版本保留；不是本次預設瀏覽器操作，也不承擔共通門檻。

## 4. 不適用項目與理由：不計通過

| 項目 | 不適用理由 | 如何處理 |
|---|---|---|
| 靜態入口的 HTTP health endpoint、常駐服務啟停 | 此入口是沒有後端的檔案頁，不提供 HTTP endpoint 或常駐程序 | 不適用；不能因此免除 G01–G05 的預設瀏覽器門檻。既有服務操作仍受權限限制。 |
| 取消已開始的長時間串流工作 | 本頁沒有串流或背景工作；結構解析為有界同步操作 | 不適用；只提供並測試取消「尚未開始」的排程，真實瀏覽器操作仍未測。 |
| 目前 8 契約的 integer/number 欄位相容性 | 這 8 份契約沒有此型別欄位 | 不適用於目前欄位；若新增，產生器要求另做相容性工作，不能沿用通過狀態。 |

原文擷取、catalog 入庫、批准／發布與真實 DB 查詢是本 repo 的原有職責，**在本靜態頁未接通，而不是不適用或已通過**。相關真實功能與 API 仍依第 2 節要求，不能用結構範例替代。

## 5. 證據與安全程式檢查方式

本頁新增的程式測試：

```powershell
# 在本 checkout，使用既有 Python / Node，不安裝依賴。
python -B -X utf8 -m unittest discover -s tests -p test_acceptance_web.py -v
node --test tools/test_acceptance_web.cjs
python -B -X utf8 tools/build_acceptance_web.py --check
git --no-optional-locks diff --check
```

證據須保存：命令、cwd、Python/Node 版本、基準 HEAD/branch/dirty、實際 stdout/stderr/exit code、所有相關來源與產物 SHA-256。合成輸入在 fixture/test source 保存；瀏覽器驗證另記實際 URL、動作、看到的結果與截圖（若可取得）。不重跑已完成且來源未改的測試，不安裝缺少的選配依賴。

## 6. 未測／阻塞與明確限制

- 靜態頁是獨立契約檢視/驗證工具；尚無可寫入 catalog 的瀏覽器後端，也沒有批准／發布按鈕。
- 既有 localhost HTTP、CIM 與舊 checkout 權限拒絕維持原狀，不換埠、換路徑或另用執行器重試。
- 本輪瀏覽器工具拒絕 `file://` 協定；靜態檔案已完成，實際開啟、桌面/窄視窗與瀏覽器操作未驗證，不用 HTTP 或其他瀏覽器表面繞過。
- HTTPS UserChoice 預設瀏覽器關聯的唯讀 Registry 查詢亦被拒，未重試；預設瀏覽器身分未知。沒有新增實際瀏覽器證據，網頁整體驗收維持 BLOCKED。
- UnityPy 選配測試、真實 DB、原站新鮮度、內容真偽、正式服務及跨 repo 整合均不能由本頁證明。
- 最新頁面測試與瀏覽器狀態見 [本機頁面說明](acceptance-web.md)；沒有實際瀏覽器證據時必須標為未驗證。

# 獨立本機驗收頁

## 共通門檻與整體結果

**網頁驗收：BLOCKED／未通過。** 所有 repo 的共通門檻相同：必須在使用者的預設瀏覽器實際看見頁面，操作適用的輸入、實際輸出與錯誤／恢復流程，保存同版操作證據。檔案存在、HTTP 成功、程式或記憶體 DOM 測試均不能替代。

預設瀏覽器身分未知：唯讀查詢 `HKCU\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice` 的 `ProgId` 遭 `Requested registry access is not allowed`，已停止且未重試。先前 CUA Chrome 分頁被拒並不證明 Chrome 是使用者預設瀏覽器。

## 本 repo 功能與本機入口

入口：[web/acceptance/dist/index.html](../web/acceptance/dist/index.html)。這是本機靜態檔案，不是已啟動的 localhost 服務。

預期開啟方式為使用者預設瀏覽器開啟此 HTML；這個方式尚未成功實測，不能宣稱可用。同目錄的 `data.js`、`contract.js`、`app.js`、`styles.css` 必須一併保留。關閉分頁即停止，不需背景程序或停止指令。**不要以啟動 HTTP server、改埠、更換瀏覽器／執行器或改預設應用重試既有拒絕。**

頁面提供 8 種 JSON 契約的瀏覽器版結構驗證、合成範例、錯誤路徑與輸出 JSON、取消待執行、返回編輯、完整驗收標準及整理過的證據摘要。瀏覽器端直接驗證，不以預製成功輸出替代。此處不連接 Python/CLI/SQLite，也不提供原文擷取、入庫、批准或發布操作。

所有範例都是既有 synthetic fixture 或從它們產生的結構範例；published sample 的 status 僅示範包格式，不代表本頁實際發布了資料。貼上的自訂資料不會送出、存到 localStorage 或寫檔。請只輸入合成資料。

完整可驗證標準與界線見 [independent-acceptance.md](independent-acceptance.md)。原資料流程的完成定義仍見 [persistence-and-query-acceptance.md](persistence-and-query-acceptance.md)，不因增加此頁而更動。

## 來源更新

`data.js` 由以下唯本地產生器更新；它讀取 8 契約、5 合成 fixtures、契約驗證器 hash 及本機 Git branch/HEAD，不讀 DB、設定或私人日誌：

```powershell
python -B -X utf8 tools/build_acceptance_web.py
python -B -X utf8 tools/build_acceptance_web.py --check
```

變更契約後應重建並重跑 Python/JavaScript 一致性檢查。目前 schema 沒有 integer/number 欄位；產生器遇到新增數字型別將拒絕，要求先補 Python 與 JavaScript 數字語意的驗收。

## 已實際驗證結果：程式與檔案範圍

靜態頁與下列程式檢查已完成；預設瀏覽器共通門檻及所有頁面功能測例的真實瀏覽器操作尚未通過。

- JavaScript：12 項驗證器／狀態測試通過；最終 5 項記憶體事件測試通過（載入範例、錯誤、重複提交、取消、返回、清除、快捷鍵、切換契約與清空還原表單）。合計 17 個不同案例；修改後僅重跑受影響事件測試。記憶體事件測試不等於真實瀏覽器。
- Python：4 項檢查通過，包括實際契約/fixture bytes、8 組正向範例、Python/JavaScript 錯誤集合比對與本機連結存在性。修改後僅重跑受影響的一致性與連結檢查，均通過。
- `tools/build_acceptance_web.py --check` 通過，8 契約/5 source fixtures/HEAD/branch 與資料包相符。`git diff --check` 通過。
- 使用既有 Python 3.13.11、Node 24.13.0；未安裝依賴，未啟動服務、未讀寫正式 DB。
- 同版原始命令、stdout/stderr、SHA-256 及差異狀態保存在 checkout 外的本機驗收紀錄。頁面只保留去識別化摘要，不讀私人日誌或機器環境。

## 不適用與理由：不計通過

此靜態入口沒有 HTTP health endpoint／常駐服務，沒有可中斷的串流工作；目前 8 份契約沒有 integer/number 欄位。這些項目按 [標準](independent-acceptance.md) 標為不適用，不算通過，也不免除預設瀏覽器門檻。

catalog 入庫、人工批准／發布與真實 DB 查詢屬本 repo 原有功能，但此頁未接通；狀態是未接通／未驗證，不是不適用。

## 未測／阻塞

瀏覽器阻塞的精確動作：透過 CUA 建立 Chrome 分頁，開啟本入口的 `file://` URL。工具回報 URL policy 不允許此協定，只接受 HTTP/HTTPS；動作被拒，沒有改用其他瀏覽器表面、HTTP server、改埠或其他執行器繞過。使用者可自行從檔案總管嘗試開啟，但本工具尚未觀察到實際頁面。

因此，桌面／窄視窗實際排版、真實鍵盤與螢幕閱讀器、瀏覽器 CSP 實際效果、使用者親自操作，以及 browser end-to-end 仍為 **NOT VERIFIED**。檔案與其相對連結已由程式確認存在，不代表瀏覽器已成功載入。

本次只更新共通門檻及狀態表述，沒有重試被拒的開啟或連線，沒有新的瀏覽器畫面／操作證據。G01–G05 與 W01–W12 全部保持未達成／未驗證，整體網頁驗收為 BLOCKED。

既有基線：140 項中122項斷言通過、10項 HTTP 權限阻擋、8項 UnityPy 選配略過；其中8項沿用前輪斷言，原包裝另有 exit 1 限制。這不是本頁最新測試結果。

既有阻塞：localhost HTTP `WinError 10013`、CIM 程序清單與舊 checkout Git 查詢先前被拒，維持原限制。沒有啟動服務、沒有本機 HTTP URL 可宣稱已連通。正式 DB、live、原站資料與跨 repo 整合未測。

## 本輪最終自動功能驗收：原生接線與結果

新增固定 [native handler/CLI](acceptance-native.md)，實際呼叫 `contracts.validate`、`prepare_prebuild`、缺口研究/補充、`LocalKnowledgeStore` 與 `Catalog`；只接受有界合成JSON，不接受任意指令、路徑、檔案、DB、端點或ACL。全新臨時state用完只清理自己新建的資料，回應保留真實before/after及artifact hashes。

- CLI錯誤出口修補後的當前安全Python集合：142項實際執行，134 pass、8選配skip、0 fail/error；20項HTTP/server/先前不確定的操作排除未重試。新增13項native/CLI測例與5項interface/receipt測例包含在134 pass中；舊版證據分開保留。
- stdin CLI矩陣：22項真實請求／回應情境全部符合預期，包含應拒收的負向案例；完整JSON與exit codes另存同版證據。
- JavaScript：本輪17項程式案例通過，仍屬驗證器及記憶體事件測試。
- 所有資料都是明示虛構來源，沒有原站取得、LLM、正式DB或真實人工審核。原文引用與政策/版本狀態由真正Catalog計算，非歷史回應重放。

**接線程度：CLI → handler → 原生函式已實測；頁面 → handler 尚未接通。** 網頁只顯示相同固定請求格式並連結說明，沒有把CLI輸出冒充網頁操作結果。本批沒有啟動server或爭用總控協調的瀏覽器；預設瀏覽器仍為BLOCKED／未通過。

# 即時 SQLite 唯讀驗收

主要入口是 `http://127.0.0.1:8765/`。搜尋、分類、翻頁、開啟條目及重新讀取時，每次都建立新的 SQLite `mode=ro` 連線，以單次讀取交易取得一致內容；沒有匯出 corpus、前端快取、示範資料或備援 DB。

## 啟動與停止

在既有專案 Python／uv 環境執行，明確指定 checkout 外的現有資料目錄：

```powershell
cd C:\path\to\ssr-knowledge
uv --cache-dir .uv-cache --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\peak-data serve-review --port 8765
```

開啟上方唯一主入口；在啟動終端按 **Ctrl+C** 停止。`--no-sync` 沿用既有環境，不安裝或移除套件。亦可明確設定 `SSR_KNOWLEDGE_DATA_DIR`；兩者皆未指定時拒絕啟動，不採用 catalog 的預設資料目錄。port 被占用會直接報錯，不靜默換入口。沒有改防火牆或區網綁定選項。

頁首顯示完整 DB 路徑、此次讀取時間、DB 最近條目紀錄及實際分類數量。條目紀錄時間不等於原網站或遊戲資料更新時間，來源日期在條目來源明細分開顯示。開錯空 DB 會顯示零條目提示；缺檔、格式錯誤或讀取失敗回傳 HTTP 503，醒目顯示路徑及原因，不建立檔案、不顯示上次結果。

## 可驗收功能

- 中英文、舊譯／別名及內容搜尋，沿用既有 NFKC／casefold 與名稱整體匹配規則，精確名稱優先，亦列出全文匹配。沒有語意或模糊搜尋。
- 全部／道具／遊戲徽章／其他分類，每頁預設 20 筆。計數由目前 DB 取得；舊泛稱道具及制度概念也保留，並非只顯示先前匯出頁的詳細表子集。
- 條目頁顯示有內容的用途、取得、限制、烹煮、官方徽章文字、雙向關聯及實際來源。缺漏短列；原文／原數值可展開。烹煮摘要保留「烹煮效果」語境，不偽裝成一般使用效果。
- 名稱證據、內容審核與來源狀態分開：例如「Wiki Items：已保存附件」、「詳細頁：未讀取（HTTP 403）」／「詳細頁：尚未補連結」、「內容：待使用者驗收」。來源有記錄不代表單品頁已讀，也不代表內容獲批准。
- 真實 0、來源 n/a、未提供與未解析狀態從 DB 原欄位取得，不互相填補；原始本文、hash 和內部 ID 不放在主要可讀內容。
- 入口只讀，沒有匯入、批准或修改按鈕。POST／PUT／PATCH／DELETE 回傳 405，SQLite 同時使用 `mode=ro` 與 `query_only`。

`GET /api/review` 回傳與伺服器端 HTML 共用的查詢模型，供本機核對使用；不是另一個使用者入口。參數為 `q`、`kind`、`page`、`page_size`（1–100）、`entry`。未知／重複／無效參數回傳 400，不存在的條目回傳 404。

服務只綁 `127.0.0.1`。沒有 CORS、外部前端套件、遠端請求或存取紀錄；回應 `Cache-Control: no-store`。Host／Origin 檢查拒絕非同址請求，並拒絕跨站 fetch／iframe；允許使用者由一般連結或書籤開啟頂層頁面。CSP 禁止 script、外部資源及框架嵌入，來源文本以 HTML escape 顯示。

## 重現驗收

1. 搜尋既有英文名、官方中文及舊譯，確認精確結果連到同一條目；全文匹配可以有其他結果。
2. 篩選道具／徽章並翻頁，核對結果數與資料庫；點開關聯，再沿反向連結回來。
3. 開來源明細，核對原值 0、n/a、附件來源與詳細頁狀態各自正確。
4. 用**臨時合成 DB**寫入新修訂後，在同一服務重新查詢，名稱、結果與最近條目紀錄必須更新。移走該測試 DB 後重新查詢應顯示 503，還原後恢復；不在正式 DB 測寫入。
5. 真實資料只以讀取方式逐筆對照 SQLite → 查詢模型 → HTTP JSON／HTML，並核對驗收前後 DB 位元組相同。

自動化命令：

```powershell
uv --cache-dir .uv-cache --offline lock --check
uv --cache-dir .uv-cache --offline run --group extraction python -m unittest discover -s tests -v
git diff --check
```

合成測試驗證搜尋／分類／分頁、狀態、數值缺漏、關聯、更新可見、失檔／錯誤 DB、HTTP 唯讀、同址保護及來源文本惰性。實際 Chrome 畫面、表單導覽與截圖須另有真實證據；HTTP／HTML 測試不冒稱視覺驗收。私有 DB、完整 JSON／HTML、截圖及驗收資料不入 Git。

舊 `render-review` 仍可匯出當時快照，但不是即時驗收的主入口。這個工具也沒有執行遊戲實測或代替使用者批准知識。

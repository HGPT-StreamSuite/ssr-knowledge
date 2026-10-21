# 遊戲建庫計畫與待審知識欄位

`ssr.game-plan.v1` 是保存端接收的獨立規劃檔，與 A 輸出的 `ssr.collection.v1` 原文包分開。它不授予採集權限，也不生成知識或批准內容。PEAK 的第一份實際計畫在 collector 的 `plans/peak-core-v1.json`，依遊戲結構規劃 13 類、13 個本批目標和 8 種有方向的關聯。

## 固定步驟

1. 完成遊戲分析，交付計畫檔；B 執行 `register-game-plan --file PLAN` 存入指定 DB。
2. 來源許可仍由 B 的中央 registry 管理。A 獨立擷取並輸出 `ssr.collection.v1`，B 以 `ingest-collection --file BUNDLE --apply` 保存原文快照。這時仍沒有知識條目。
3. 編輯者從已保存原文整理草稿；B 執行 `import-drafts --file DRAFTS` 保存 `pending_review` 修訂。每個欄位必須有來源證據，否則標明缺漏。
4. 關閉寫入程序，以新程序的 `entry`、`relations`、`game-plan-status` 讀回；再啟動 `serve-review`，讓 API 與頁面直接讀同一 DB。

```powershell
uv run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\peak register-game-plan --file C:\handoff\peak-core-v1.json
uv run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\peak ingest-collection --file C:\handoff\source.collection.json --apply
uv run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\peak import-drafts --file C:\private\drafts.json
uv run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\peak game-plan-status
uv run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\peak serve-review --port 8767
```

## 規劃檔

根欄位只能是 `format`, `plan_id`, `game`, `analysis`, `categories`, `relation_types`, `targets`。目前 game 支援 `PEAK:3527290`。計畫以 canonical JSON SHA-256 保存在 `game_plans`；同 ID 同內容重送不變，內容變更須使用新的 plan_id。讀舊 DB 不建立此表。

- `analysis`：core_loop、structure、basis_url、basis_sections、version_policy、exclusions、questions。說明核心玩法、分類依據、版本界線、排除理由與驗收問題。
- `categories[]`：id、label、rationale、allowed_source_types、fields。網站章節只屬於來源定位；不能代替分類理由。官方更新的來源類型必須只為 official。
- `fields[]`：id、label、type、unit。type 為 string、strings、integer、number、boolean 或 date。date 使用 YYYY-MM-DD；整數不接受布林；數字須有限且絕對值不超過 10^12。unit 未適用為 null，不能用缺漏代替零值。
- `relation_types[]`：id、label、from_categories、to_categories。由本遊戲分析定義方向及適用類別。
- `targets[]`：entry_id、category、name、question、priority（1–3）、source_url、source_locator、gap_reason。來源 URL 是規劃線索，不是取得成功紀錄或許可。具體目標最多 100 個；擴充批次以新計畫版本保留歷史。

## 草稿擴充

沿用既有必填的條目、名稱、摘要、版本、限制、編輯者、evidence_class 與 pinned citations。另增：

```json
{
  "knowledge_details": {
    "plan_id": "peak-core-v1",
    "fields": {
      "max_players": {
        "value": 4,
        "evidence": [{"citation": 0, "quote": "exact saved source text"}]
      }
    },
    "gaps": {"difficulty": "This source does not supply difficulty details."}
  },
  "knowledge_links": [{
    "kind": "uses_mechanic",
    "target_entry_id": "peak-stamina",
    "citation": 0,
    "evidence_text": "exact saved source text"
  }]
}
```

這段只是形狀示意，不是可直接匯入的完整條目或真實引文。完整草稿的每個規劃欄位恰好在 fields 或 gaps 出現一次，至少有一個有證據的值；未知欄位、重複缺漏、錯誤型別、偽造引文、未註冊計畫及目標分類不符均拒收。每欄 1–4 個精確引文，單引文最多 300 字，必須出現在指定 snapshot 的正文，來源類型須符合類別。這只驗證可追溯性，不自動判定語意正確或遊戲實測完成。

關聯不接受自連、重複、缺失目標、錯誤方向或跨計畫連結。來源與目標可在同一批新增，先完整驗證，再以一個寫入交易保存；任一條目失敗整批回滾。修改目標時也檢查目前指向它的關聯。重送歷史 payload 不倒退 current revision。DB 中以 `planned:` 前綴區分規劃關聯與舊版嚴格的 Items／官方徽章關聯，不混用證據等級。

## 查詢與完成條件

`game-plan-status` 與 `/api/review` 的 plans 資料直接來自指定 DB，顯示每個目標的 current revision、待審狀態、已保存欄位數及缺漏。`knowledge_saved` 只代表已有對應計畫的知識修訂，不代表全部欄位完成、使用者已驗收或已發布。

`/?category=mode` 篩選知識類別；條目頁顯示保存值、單位、逐欄引用、缺漏、版本與限制。來源快照 ID、授權資訊及 incoming／outgoing 關聯可供核對。每次請求新建唯讀 SQLite 連線並在同一讀取交易內產生結果。沒有資料庫時報錯，沒有靜態答案備援。

## 2026-10-21 本機真實驗證

在本輪新建的持久 DB，A 用本機 Chrome／Playwright 保存獲准的 Wikipedia 介紹及玩法 7 段文字，排除圖片及第三方評論引文；B 獨立讀取原文包，再保存 12 個條目、13 個歷史修訂、26 個有證據欄位、20 個欄位缺漏及 5 條目前關聯。全部 12 條目保持 pending_review。這不是舊主機 228 條目 DB 的移轉或更新。

獨立 SQLite 讀取、新 CLI 程序及 HTTP API 已逐筆核對，唯讀查詢前後 DB SHA-256 相同。已在安裝版 Chrome 的獨立 headless 工作階段實際操作搜尋、分類、證據展開、關聯跳轉、重新讀取與缺漏清單，並檢視畫面截圖。這是程式／瀏覽器驗證，使用者內容驗收仍待進行。

官方更新是第 13 個尚未保存的目標：來源取得／用途限制未解除；其他已存條目仍有明列的欄位缺漏，單一 Wiki 資料不代表完整攻略或官方事實。原文、草稿、DB、瀏覽器觀測與逐筆驗證檔只留本機，不入 Git。

## 2026-10-21 攀登與生存續批

依 collector 的 [peak-survival-v1 計畫](https://github.com/HGPT-StreamSuite/ssr-collector-peak/blob/codex/collector-acceptance/docs/peak-survival-plan.md)，在原來同一個本機 DB 新增 29 筆（15 道具、4 機制、4 狀態、6 攻略），補強 4 筆既有條目。20 份 PEAK Wiki 搜尋索引摘錄經獨立 collector 輸出共同檔案，再由保存端收納來源及交易匯入知識；來源取得方式記為摘錄，未記為完整網頁。

目前 DB：41 條目、46 修訂、21 快照、148 個有證據欄位、16 個明列缺欄及 32 條目前關聯。原有 13 個歷史修訂全部保留，未修改的 8 個條目仍指向原 revision；41 筆維持 pending_review。新計畫 29／29 個目標有知識修訂，與原計畫 12／13 分開顯示。

全部條目已經獨立 SQLite、新 CLI 程序、同一 DB 的 HTTP API 及 Chrome 頁面逐筆核對：revision、欄位值、缺欄、來源引文／snapshot ID 與雙向關聯一致。另操作分頁、分類、搜尋與重新讀取，查詢前後 DB SHA-256 相同。畫面的欄位引用與關聯引用均預設收合，主要內容保留操作與數值。

驗收入口仍為 `http://127.0.0.1:8767/`。選「道具」應見 16 筆；選「攻略」應見 7 筆。開「使用解毒劑處理中毒」，點「解毒劑」再點回攻略，確認相同 DB 的內容與關聯。來源資料、私有交接包、草稿和備份都保留在 checkout 外。

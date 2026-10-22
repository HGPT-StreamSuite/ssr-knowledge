# 現有道具內容整理與遊戲徽章

SQLite 是資料本體，HTML 是從當前修訂產生的私有驗收輸出。此輪只整理已保存的 Items 附件與先前取得的官方 `Localized_Text`；沒有再抽取遊戲資源或擴大蒐集。

## 保存格式與邊界

道具可附 `organization`：`schema_version=1`、`method=agent_edited_pending_review`、原列 hash、五個 `topics` 的備註索引及精簡中文 `notes_zh`。五類為用途效果、取得、使用條件、烹煮及徽章提示，每段原備註須恰好分入一類。這是 agent 編輯整理，驗證器檢查索引與來源列，並不自動判定翻譯或分類正確。原始 `item_details`、原數值、原譯註記及舊修訂都保留。

遊戲徽章沿用 `achievement` 分類，附 `badge_details.kind=game_badge`。名稱與條件按同一官方 CSV 的 `NAME_`／`DESC_` 完整 suffix 配對，明確選取 English 與繁體中文欄。名稱引用既有名稱投影，條件額外直接核對該快照保存的原始 CSV；不下載新來源。其他語言的重複差異不改寫目標欄；目標欄有衝突就拒絕。`condition_status=game_ui_text` 表示官方顯示文字，未宣稱已實測隱藏解鎖邏輯。`steam_equivalence=unverified`，不保存玩家個人成就進度。

可選 `links` 以穩定 `target_entry_id` 引用既有條目，連同修訂存入 SQLite `entry_relations`，保存類型、引用索引、原備註索引及證據。`badge_hint` 必須逐字符合該道具的已引用備註及完整徽章名稱；「可用於」仍只是部分提示。`condition_mentions_item` 必須符合已保存官方條件及明確英文道具名稱。兩者可由 `relations` 私有查詢雙向讀回。歷史關聯保留，預設讀目前修訂；正式搜尋移除 `links`，不透過已發布道具洩漏相連待審或拒絕條目的 ID。

`detail_page` 將個別詳細頁 URL、核對狀態與實際 citations 分開。目前只有使用者明確提供的一個 URL；必要唯讀核對得到 403，保留 `user_provided_unverified`，沒有冒稱該頁已讀或引用其內容。其餘網址不由道具英文名稱拼接。來源文字與連結都只作資料，不執行來源命令。

## 本機使用

```powershell
$env:SSR_KNOWLEDGE_DATA_DIR = 'C:\private\peak-data'
$env:PYTHONIOENCODING = 'utf-8'
uv --cache-dir .uv-cache --offline run --group extraction python -m ssr_knowledge catalog badge-drafts --en-snapshot-id SAVED_EN --zh-snapshot-id SAVED_TW
# 將產生的定義草稿存入私有 JSON，再用既有 import-drafts；沒有自動批准。
uv --cache-dir .uv-cache --offline run --group extraction python -m ssr_knowledge catalog import-drafts --file C:\private\drafts.json
uv --cache-dir .uv-cache --offline run --group extraction python -m ssr_knowledge catalog relations --entry-id ENTRY_ID
uv --cache-dir .uv-cache --offline run --group extraction python -m ssr_knowledge catalog render-review --output C:\private\peak-review.html
```

`badge-drafts` 只投影已有快照，`render-review` 只讀目前 DB 內容並在 checkout 外寫 HTML；兩者均不呼叫 HTTP、模型或遊戲抽取。核心功能可在不使用 extraction 群組的情況下執行；範例沿用既有選用依賴以免 uv 移除它。

## 驗收頁與資料缺口

主卡只顯示有內容的用途效果、取得、限制、烹煮及相關徽章，缺漏合併成短清單。原文、原數值、來源及整理註記可展開；頁面不輸出 hash、內部 ID 或解析細節。官方中英名稱優先，舊譯仍搜尋同一 ID。卡片內部連結與名稱／別名／內容篩選留在本機，沒有外部前端依賴。

實際已保存樣本的統計摘要（完整輸入、翻譯、DB 與 HTML 均不入 Git）：

- 132 件道具的 252 段既有備註全部整理；新增外部用途事實 0。
- 四項原數值共 528 格：315 格來源 n/a、213 格數值，其中 21 格為真實 0；沒有數值空白或未解析格。n/a 未改成 0 或不適用，也未用不同作用範圍的備註填回原數值。
- 36 件原表完全沒有額外備註；49 件沒有獨立用途效果備註。取得、限制與烹煮也仍有缺口，精確缺漏由 DB 產生的頁末統計呈現。
- 121 件官方中英名稱及 11 件待查名稱保持原狀。
- 64 個官方遊戲徽章定義；12 筆 Items 部分提示，加上 13 筆官方條件的明確道具提及，存為 25 筆有方向的關聯（18 組道具—徽章配對）。
- DB 由 164 條目／426 修訂變為 228 條目／622 修訂；14 來源、7 快照維持不變。全數真實修訂仍待審，沒有批准或發布。

缺漏分類與原 parser 的粗分不同，不能把重新分類的欄位數當成新增知識。官方資源版本只支持此輪名稱與徽章顯示文字，不代表舊 Wiki 用途與效果已核對該版本。

驗證使用既有本機環境：

```powershell
uv --cache-dir .uv-cache --offline run --group extraction python -m unittest discover -s tests -v
```

新增合成測試涵蓋原 n/a／0 不變、備註完整索引、精確徽章條件與繁中欄、關聯證據及去重、目前／歷史關聯、重開讀回、正式搜尋不洩漏相連待審／拒絕 ID、簡潔且惰性的 HTML。真實資料另以同一最終 commit 的私有命令紀錄驗證中英別名搜尋、關聯與去重。未執行遊戲實測或真實審核；本輪沒有合併 PR、部署或刪除資料。

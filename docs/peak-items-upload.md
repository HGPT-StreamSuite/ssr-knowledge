# PEAK Items 使用者提供文字匯入

本輪使用使用者提供的完整頁面貼文，**不是程式直接爬取成功**。原來源為 https://peak.wiki.gg/wiki/Items；頁尾聲明 CC BY-SA 4.0 unless otherwise noted，最後編輯 2026-08-14 16:05，未註明時區／遊戲 build。引用／作者群歸屬保留 PEAK Wiki 頁面連結，改寫／翻譯保留同授權及例外待審說明。

原始附件 22,625 bytes、707 行（CRLF），SHA-256 `56d40ec5e7e492a2fe2ae1fde0299b0051ea26c93ef4b9a5262c2b4da3cb0279`。原始 bytes、Library 身分／版本、收件及匯入資訊、資料庫與翻譯 JSON 均只存本機 checkout 外；公開檔案不含全文或真實逐列 fixtures。

## 計數與實際資料

程式以複製表格的 `Icon / Name / Weight / Hunger / Bonus Stamina / Poison` 列結構辨識，排除每列重複的圖示名稱及斷行表頭。實際 **132 列、132 唯一名稱、0 重複列、0 衝突重名、0 未解析列**。頁首宣稱 134，差 **2 件待查**；不把宣稱當驗證、不猜缺少哪兩個，也不把差額寫成「兩個未解析列」。

132 件含 128 個新增條目及 4 個既有條目的新修訂（Backpack、Energy Drink、Piton、Rope Spool），全部 `pending_review`。舊泛稱 Anti-Rope 不與 Anti-Rope Spool／Anti-Rope Cannon 合併。整個 catalog 為 164 條目／173 修訂，當前 item 共 133（附件132＋保留的舊泛稱1）；不能用133聲稱頁面道具已收全。

| 原表欄位 | 明確數值 | 原表 n/a | 空白／未解析 |
|---|---:|---:|---:|
| Weight | 132 | 0 | 0 |
| Hunger | 50 | 82 | 0 |
| Bonus Stamina | 15 | 117 | 0 |
| Poison | 16 | 116 | 0 |

`n/a` 保存為 `{state: "source_na", value: null, raw: "n/a"}`，不推成0、沒有作用或語意上的不適用。數值0是獨立的 value=0，Unicode負號保留於 raw，解析值維持負數；不補造單位、百分比、持續時間或遊戲版本。

| 欄位／敘述 | 未記載／未被規則分出 | 有內容 |
|---|---:|---:|
| 地區 | 0 | 132 |
| 具體地點 | 119 | 13 |
| 額外說明 | 36 | 96 |
| 取得敘述 | 115 | 17 |
| 限制敘述（字面規則） | 113 | 19 |
| 烹煮相關敘述 | 82 | 50 |

具體地點及取得敘述兩者皆缺的有105件。取得／限制／烹煮分類為明示字詞規則，不能當完整語意判定；全部252段英文說明及逐句繁中翻譯仍保存。沒有被分入「限制」不表示原文完全沒有條件。36件沒有額外說明者仍保留原表數值／地區，不從名稱猜用途。

缺漏與可能矛盾以 issues／limitations 標示，例如數值欄0與隨機狀態敘述並存、烹煮提到中毒但欄位n/a、狀態數量未記、要求參閱未提供的單品頁。程式不自行改正來源；英文及原始表格仍可核對。

## 本機重現流程

沿用既有 Windows Python／uv，無新套件、服務、瀏覽器、模型或跨 repo 介面。

```powershell
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog --data-dir C:\private\data import-text-source --file C:\private\items.txt --receipt C:\private\receipt.json
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog --data-dir C:\private\data parse-peak-items --snapshot-id SNAPSHOT_ID
# 先對照實際解析輸出編輯翻譯／別名，不能把尚未編輯的英文當成自動完成的繁中知識。
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog --data-dir C:\private\data import-drafts --file C:\private\drafts-first-100.json
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog --data-dir C:\private\data import-drafts --file C:\private\drafts-last-32.json
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog --data-dir C:\private\data search --text '反向繩索捲' --preview
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog --data-dir C:\private\data search --text 'Anti-Rope Spool'
```

正式查詢在所有真實資料待審時應無資料。每次最多100個草稿，本批分100＋32；同樣輸入重匯不新增修訂。所有真實條目不由agent批准／發布。只有合成測試模擬審核。

### Receipt 與來源身分

receipt 必須有 `source_id, source_url, title, original_filename, library_file_id, library_version, page_updated, page_updated_timezone, license_statement, license_url, provided_by, reviewed_at, uses`。`uses` 分別記 local_cache／search_index／ai_input／ai_train 的 status／basis；本機保存必須已明確審查為 allowed。使用者提供檔案不代表任意下游用途自動授權。

上傳來源以 `library-file:<實際Library ID>` 為獨立來源身分，canonical／original URL 仍為原 Wiki URL；`requested_url=null`、acquisition_kind=user_provided_text、http_requests=0。不改寫原有 HTTP 來源政策。來源政策 `allow_fetch=false`、`allow_import=true`，收藏程式明確拒絕對此來源執行 HTTP；撤回 allow_import 仍會隔離正式結果。匯入時間與頁尾版本時間分開，時區未知不自行加UTC。

### 詳細道具資料

草稿可有 `item_details`，內含 schema/parser版本、英文名、原始列行號／邏輯列雜湊、四項統計的 state/value/raw、地區／地點、全部英文說明及取得／限制／烹煮分類、逐句 `notes_zh`、issues 與 translation_status。每個解析欄位都必須與 pinned 正文重解析的同名列完全一致；不能把 n/a 改0或替換來源數字後匯入。每段英文須有一段編輯後繁中翻譯。

程式只做確定性解析、欄位核對、去重與保存。繁中名稱、別名、252段說明由agent編輯字典、嚴格數值模板與逐句翻譯後組裝，標為翻譯待審；沒有程式呼叫LLM。搜尋另外涵蓋道具的中英文說明及地區／地點。故事、同人內容與未提供的單品頁不補寫。

## 驗收邊界

最終head的測試與本機私人 evidence 由 PR #4 對照：來源匯入／重匯、132列逐欄比對、128新增／4更新、所有歷史修訂保留、Unicode負數／n/a／0、中文／英文／別名／全文、獨立程序重開與待審隔離。原始附件、資料庫、完整道具清單／HTML預覽及逐句翻譯不公開push；公開測試只有合成資料。頁首差2與來源缺欄仍是未完成事項，不能宣稱目前版本全量完成。

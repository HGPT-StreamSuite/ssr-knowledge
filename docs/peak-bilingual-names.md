# PEAK 雙語名稱與檢索

以目前官方遊戲內名稱為優先，目標語系 **zh-TW**；zh-CN須另有來源，不用繁簡轉換推定正式名稱。Wiki英文名、agent暫譯、官方宣傳詞、歷史社群模組譯名分開記錄，知識審核仍由revision管理。

## 本批核實結果

132件英文名可對照已保存的Wiki表，不自動等同目前遊戲UI；132個繁中顯示名保留原暫譯，**遊戲UI已核實0件、待核對132件**。

[Steam繁中商店](https://store.steampowered.com/app/3527290/PEAK/?l=tchinese)列有繁中介面支援。只用四個短詞建立本機人工參考筆記，不保存整頁HTML或聲稱collector直接抓取成功。3筆宣傳別名候選用於2件道具；原324別名保留，新增2個文字後共326個。宣傳詞與道具的對應仍是編輯候選，**不是UI核實**。「反向繩索」泛稱不據此指定為Spool或Cannon；原泛稱與兩變體分開。

只讀標準Steam設定與PEAK目錄，找到本機版本2.6.b／build ID 25739797，無BepInEx目錄；沒有直接可讀的在地化文字表。主要資料為UnityFS封裝，依要求未抽取、安裝工具或啟動遊戲，不能補寫正式名稱。此版本字串也不代表Wiki條目已核對該版本。

## 名稱欄位

草稿可加 `names: {schema_version: 1, target_locale: "zh-TW", records: [...]}`。每筆有 `text, locale, role, status, citation, basis`；前兩筆對應name_en/name_zh，後續alias紀錄涵蓋aliases全部文字。同字可保留不同來源證據，不合併entry ID、不批准修訂。

| status | 含義與邊界 |
|---|---|
| source_name | 名稱存在於指定引用短句及正文；不代表官方UI |
| provisional_translation | 編輯暫譯；locale為目標語系，citation=null，記編輯依據 |
| provisional_alias | 編輯別名，未核實遊戲在地化 |
| official_marketing_alias | 官方文案詞，僅alias；來源、語系與marketing scope須符合 |
| community_mod_alias | 非官方歷史模組詞，僅alias；須有相符非官方來源、語系及community_mod scope |
| game_ui_verified | 須有相符官方來源、精確語系及明示game_ui scope的pinned文字；宣傳／社群來源不能只改status通過 |
| unverified_legacy | 舊資料保守顯示，不改歷史payload或推定中文語系／正式名稱 |

citation是當筆citations索引，詞必須在該引用短句及正文出現。程式只核對宣告、定位與文字一致性，無法替代對UI／檔案的語意及來源審核。真實資料沒有game_ui_verified；新修訂均pending_review，歷史保留。

## 查詢

```powershell
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog --data-dir C:\private\data search --text '  anti- rope   spool ' --names-only --preview
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge catalog --data-dir C:\private\data search --text '反 重 力 繩 捲' --names-only --preview
```

名稱／別名用NFKC、casefold與移除Unicode空白後**整個標籤相等**比對。大小寫、全形、空白差異可對到同ID；標點、詞序、拼字、括號限定詞、Spool/Cannon仍不同。不做模糊匹配、拼字修正、簡繁互轉或切分使用者整句問題。

--names-only僅查名稱；一般search保留名稱、摘要及道具說明的literal全文子字串，先列精確名稱，再按ID。全文不移除字間全部空白。結果含match_type/name_matches（語系／來源狀態）；name_resolution有unresolved/unique/ambiguous與全部**可見**精確ID。--limit 1不把歧義改成唯一；unique只表示對到一個可見實體，不代表名稱官方。

正式查詢仍只讀已發布、當前、未過期且來源允許搜尋者；search=no、混合引用、待審／拒絕隔離適用兩種模式。不可見資料不進name_resolution或計數。所有真實資料待審時，正式結果應no_data，--preview才有資料。

## 參考檔與歷史社群對照

`import-name-reference --file FILE --receipt RECEIPT`保存已取得的固定connector文字或有限人工網頁筆記，沒有HTTP入口。receipt欄位：source_id/source_url/title/locale/evidence_kind/acquisition_method/version/upstream_commit/upstream_blob_sha/raw_sha256/license_statement/license_url/reviewed_at/uses。四項用途分開；local_cache必須allowed。connector歸屬URL固定完整commit，重算Git blob SHA及SHA-256；web筆記不是Git blob或全頁快照，不捏造upstream SHA／HTTP request。此入口不接受game_ui scope。

[社群Item.txt固定版本](https://github.com/Vocaloid2048/PEAK-zh-tw-Translation/blob/8f13b3d0670c18848ee7eea5b36134927b14c580/BepInEx/config/zh-tw-voc/Text/Item.txt)是歷史參考，根[LICENSE](https://github.com/Vocaloid2048/PEAK-zh-tw-Translation/blob/8f13b3d0670c18848ee7eea5b36134927b14c580/LICENSE)為GPLv3；原檔、授權與版本只存本機，不安裝執行或push。模組1.0.18／對應遊戲2.3.a與本機2.6.b分開。

實際438行／421筆key=value／213個casefold key，**不是213道具**。英文全名僅前後trim/casefold精確對照：132件中115匹配、17未匹配；1組來源衝突也命中Scroll，保留所有候選不挑譯名。拼錯key不模糊合併；若另有正確拼字列，只以該列匹配。依最新官方遊戲內優先要求，115件僅產生私人歷史候選報告，**本輪真實DB社群別名導入0個**。

`match-community-names --snapshot-id MOD --items-snapshot-id ITEMS`可從保存快照重現比較，不改entry。回報未匹配、重複、衝突與來源行號，不自動替代官方欄位或發布。

## 驗收邊界

同一最終commit驗證132件名稱狀態／完整payload新程序讀回、中英／全部別名同ID、大小寫／空白／全形、泛稱與變體、同名歧義、scope不可升格、正式隔離、重匯去重及歷史修訂保留。只有合成資料模擬批准；真實資料全待審。原文、DB、完整譯名表、私人證據及132卡片比較預覽不push。HTML只做結構檢查，沒有瀏覽器截圖QA。

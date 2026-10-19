# PEAK 官方遊戲資源名稱

本批在使用者明確同意後，唯讀擷取已安裝PEAK **2.6.b／82be08a25，Steam build25739797** 的官方文字資產，以穩定遊戲key配對English及繁體中文。132件中**121件可精確配對，11件保持待查**；121件優先顯示官方資源名稱，舊暫譯保留標記別名，69件繁中顯示文字與原暫譯不同。這是資源字串核對，沒有啟動遊戲或觀察遊戲畫面，也沒有核實道具效果／數值適用此版本。

## 來源及受限讀取

來源鏈：已安裝PEAK的 `data.unity3d → resources.assets → TextAsset Localized_Text`。本次path_id為1426、物件offset29333424／size425932，文字本身425,905 bytes；path_id不是跨版本固定值，程式以唯一TextAsset名稱定位。

- 遊戲包SHA-256前後一致：`24833370fcd486bd9f296a3a6c8e29ed7123d1c2dbcbaa4111afb6c937c48c2b`。
- 文字SHA-256：`70bf123abbc25963ff5edaf04e33e2043a4b07718eacc90e00b0830a1a8e2a57`。
- 原CSV同時有English／繁體中文／简体中文，實測索引分別**1／11／10**；程式按唯一欄名找索引、驗證receipt／header，而非假設位置。其他語系不導入索引。
- 只用NAME_道具命名空間。同一key的不同語系在同一列；完全相同的重複列保留位置並去重，衝突key不選任一值。Scroll等非道具同名UI字串不參與。

可選工具是[UnityPy官方專案](https://github.com/K0lb3/UnityPy)，固定PyPI版本1.25.4，以uv放在既有專案.venv的extraction群組，沒有全域安裝或新增執行環境。一般catalog仍不需此可選套件。

不呼叫UnityPy對整個bundle載入的解壓路徑；自有read-only串流先讀有限索引，按需解壓至多4MiB單區塊、32MiB快取，單次讀取上限16MiB。只解析resources.assets metadata與指定TextAsset，不掃場景、不解析／匯出材質、網格、音效，也不複製整包。遇加密／未知旗標、非支援壓縮或格式即停止，沒有解密、金鑰、DRM繞過或 fallback。

另以8MiB小塊串流讀整包兩次做SHA核對；這是檔案I/O，不是複製或整包解壓。receipt分開記錄hash讀取量、索引壓縮量、實際解壓資料量及快取峰值。快取大小不是整個Python程序RAM峰值。擷取前確認本機可用RAM／磁碟，程式另要求至少50MiB可用磁碟。

## 重現

```powershell
uv --cache-dir .uv-cache sync --group extraction
uv --cache-dir .uv-cache --offline run --group extraction python -m ssr_knowledge catalog extract-game-names --game-dir E:\SteamLibrary\steamapps\common\PEAK --output-dir C:\private\fresh-extraction
uv --cache-dir .uv-cache --offline run --group extraction python -m ssr_knowledge catalog --data-dir C:\private\data import-game-text --file C:\private\fresh-extraction\localization.txt --receipt C:\private\fresh-extraction\receipt.json
uv --cache-dir .uv-cache --offline run --group extraction python -m ssr_knowledge catalog --data-dir C:\private\data pair-game-names --en-snapshot-id EN --zh-snapshot-id TW --items-snapshot-id ITEMS
```

輸出資料夾須在所有Git checkout外，使用新資料夾保留舊證據。只讀PEAK指定manifest的appid／build／installdir及version.txt，不讀登入資料。來源正文是分開的en／zh-TW名稱JSON投影，原文與receipt只存私人SQLite／資料夾；無HTTP或LLM途徑，不把Steam歸屬連結當實際抓取URL。新的觀測時間若字串／版本未變，重匯仍unchanged，事件保留新觀測時間。

## 顯示與引用

`name_en`保留原Wiki來源拼寫，以維持item_details及實體身分；官方英文原字樣另存有game_key的證據紀錄。121件name_zh為官方繁中，`names.preferred`指向有唯一game_ui_verified證據的en／zh-TW，`entry`／`search`回傳的`display_names`供優先顯示。這個status在本批意指官方遊戲資源文字，並非遊戲畫面測試或知識審核批准。

引用記錄版本、build、bundle／文字hash、原欄名／索引、資產名／path_id、key與CSV record。game_key、英文canonical對照及目標欄位必須與pinned投影一致；不能把简体欄、其他道具key或僅有官方宣傳的詞改標為此證據。

舊繁中暫譯保留為provisional_alias並註明歷史來源；原Wiki、3筆宣傳候選與歷史社群比對仍分開。未匹配的11件沒有preferred宣告，維持暫譯／待核對。不同實體同名查詢顯示ambiguous與所有可見ID，不任選或合併。全部真實修訂仍pending_review，正式查詢不洩漏名稱／ID；--preview才顯示待審資料。

## 11件待查

| 原英文名稱 | 未自動配對原因 |
|---|---|
| Blue Berrynana Peel | 只有通用NAME_BERRYNANA PEEL，沒有顏色變體的直接物品ID／key橋接 |
| Brown Berrynana Peel | 同上；不把通用名稱任意指定給此變體 |
| Pink Berrynana Peel | 同上；不合併顏色實體 |
| Yellow Berrynana Peel | 同上；保留原ID與暫譯 |
| Bugle Shroom (Poisonous) | 沒有含Poisonous限定詞的精確英文／NAME_ key；一般菇名不足以證明此變體 |
| Button Shroom (Poisonous) | 同上；未取得物品ID與狀態變體的直接證據 |
| Cluster Shroom (Poisonous) | 同上；不移除限定詞後硬配 |
| Cooked Bird | 沒有精確英文或NAME_COOKED BIRD，也沒有直接物品ID橋接 |
| Half-Coconut | 資源是NAME_COCONUT HALF／COCONUT HALF，詞序與標點不同，沒有直接物品ID橋接 |
| Scout's Honor | 資源英文為彎引號SCOUT’S HONOR、key為NAME_SCOUTSHONOR；不暗中做標點近似配對 |
| Scout's Tenacity | 沒有精確英文／構造NAME_ key，未取得直接物品ID證據 |

「未配對」不表示遊戲沒有該物品；本輪沒有為求數量而解析遊戲執行碼、猜譯名或下載其他資源。

## 驗證

完整測試使用 `uv --cache-dir .uv-cache --offline run --group extraction python -m unittest discover -s tests -v`。合成fixture驗證重排欄位／簡繁差字、限定詞、衝突與重複、官方優先、舊譯同ID、誤key／简体列拒絕、歧義與pending隔離、區塊快取／seek／加密停止。真實擷取、輸入、更新／重匯、全部名稱讀回／查詢、舊修訂保留與預覽結構由同一最終commit私人evidence記錄；不以舊head的79測試當本輪驗收。

公開PR只有程式、lockfile、合成fixtures及不轉載全文的結果摘要；官方文字／投影、資料庫、完整配對表、快取與預覽均不push。沒有合併、部署、遊戲啟動、真實知識批准或社群模組安裝。

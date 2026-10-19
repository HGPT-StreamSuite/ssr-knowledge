# 2026-10-19 PEAK 有限批次結果摘要

**最新附件批次**：使用者提供的 Items 貼文已辨識132唯一道具，頁首宣稱134、差2待查。128個新增條目、4個既有道具新修訂，全待審；整體164條目／173修訂，item133包含保留的舊泛稱Anti-Rope。詳細原始來源、欄位、翻譯與缺欄統計見 [附件批次結果](peak-items-upload.md)。以下36條目／5道具為前兩批歷史狀態，不能當成最新數量。

此檔只有不轉載正文的結果摘要；私人 DB、原文、草稿輸入及完整命令輸出保存在本機 checkout 外。最終 commit 與實跑紀錄由 PR 及私人 evidence 檔案對照。

## 首批來源結果（歷史）

| URL | 程式化結果與用途 |
|---|---|
| https://landfall.se/peak | HTTP 200；官方頁 HTML 與選定 main 正文保存成功 |
| https://en.wikipedia.org/wiki/Peak_(video_game) | HTTP 200；Wiki HTML 與 mw-content-text 正文保存成功，保留來源及授權脈絡 |
| https://peak.wiki.gg/wiki/Items | robots 200；舊本機 use=reference 一刀切及額外 AI UA 群組規則造成阻擋，未請求正文。這不是網站禁止所有本機搜尋；現已修正，條款與存取限制仍待確認 |
| https://store.steampowered.com/app/3527290/PEAK/ | manifest 政策停用，未請求正文；app ID 僅作識別 |
| https://steamcommunity.com/sharedfiles/filedetails/?id=3514106064 | manifest 政策停用，未請求正文 |
| https://blast.tv/gaming/news/all-items-in-peak-explained | 條款不允許本次保存用途，未請求正文 |
| https://www.g2a.com/news/features/10-essential-beginner-tips-to-survive-your-first-climb-in-peak/ | 條款不允許建立資料庫／catalog，未請求正文 |
| https://www.polygon.com/guides/608514/peak-game-tips-tricks-beginners-before-you-start | robots／條款限制自動採集及 AI 資料庫，未請求正文 |

替代玩家攻略站 gameplay.tips 的公開 robots 可讀；對應 2025 年份的 `post-sitemap6.xml` 兩次回應 HTTP 500，其他已查公開索引未發現 PEAK 頁面。沒有繞用來源鏡像或補造玩家實測。

## 首批待審條目與來源對照（11 則）

| 來源 | 條目 ID（草稿） | 分類 |
|---|---|---|
| landfall-peak | peak-map-rotation、peak-stamina | 機制 |
| landfall-peak | peak-team-route | 官方合作玩法建議 |
| landfall-peak | peak-energy-drink、peak-anti-rope | 道具存在性；未補寫缺少的效果數值 |
| landfall-peak | peak-castaway-scouts | 官方故事前提；無衍生劇情 |
| wikipedia-peak | peak-rope-spool、peak-piton、peak-backpack | Wiki 道具彙整 |
| wikipedia-peak | peak-poison、peak-hunger | Wiki 狀態彙整 |

首批 11 則全部為 **agent 閱讀實際快照後編輯**的繁中草稿，非蒐集程式自動翻譯或研究；全部保持 `pending_review`，沒有真實條目經 agent 核准或發布。中文名稱與別名為編輯暫譯，仍需人工核對。以下新批結果取代首批數量作為當前狀態。

## 用途修正後的新批與目前狀態

目前 36 則真實條目、41 個不可變修訂，全部 pending_review、review=null、published_at=null。其中 6 official 為初批保留稿，30 wiki 來自 English Wikipedia。新批由 agent 編輯繁中 JSON 後匯入：25 則新增、5 則既有 Wiki 稿新增引用／分類修訂；不是採集器自動翻譯、研究或分類。初批 11 個修訂完整保留，未覆蓋審核結果。

| 分類 | 當前條目數 | 不足 |
|---|---:|---|
| mechanic | 9 | 官方 2、Wiki 7；缺精確數值與本機實測 |
| item | 5 | 官方 2、Wiki 3；非完整道具表，部分只確認存在 |
| status | 5 | Wiki 飢餓、中毒、受傷、負重、極端溫度；缺療法／持續時間 |
| guide | 1 | 官方合作建議，不能代稱獨立玩家攻略 |
| lore | 1 | 初批官方故事前提，無同人／衍生故事 |
| location | 10 | Wiki 區域概念／變體，不由此推算目前版本完整區域數 |
| creature | 1 | Wiki Scoutmaster，不採約略觸發距離作已驗證數值 |
| achievement | 1 | Wiki badges 制度概念，非逐項勳章條件表 |
| update | 3 | Wiki 更新摘要，未核對官方 patch／遊戲 build |
| support | 0 | 格式已支援，官方 FAQ 用途未確認 |

登錄來源增為 10 筆 URL，只有 2 個來源曾保存正文：Landfall 初批 1 快照、Wikipedia 初批／本輪 2 快照。本輪僅重取 Wikipedia：robots／page HTTP 200，HTML 外框與初批不同，但正文 SHA 相同；用途設定不同也保留新快照。每條新稿保留 CC BY-SA 4.0 作者群來源、授權連結、改寫及暫譯告知。

新發現 Landfall Fan Creation Policy 的 AI 文本／產品及訓練限制後，事實參考 AI 整理的適用範圍標為待確認，暫停新增官方正文與稿件；隱私政策不再作重用授權依據。FAQ／press kit URL 只登錄供 coverage，web 曾讀取但採集器尚未保存，素材不下載。原 6 則官方稿保留待審，因目前政策變更標為 stale，不在正式查詢出現。

wiki.gg 正文仍 0 頁。修正後依固定 SSRKnowledge UA 重解讀保存的 robots：wildcard 允許該路徑，search=yes、ai-train=no；ai-input 缺失、use=reference 非標準，兩者保持未知。不同 UA 的 GPTBot 群組不強加於本 collector；沒有因此開始取頁，條款未知與先前觀察的 403 分開保留，不換 UA／代理／端點繞過。

新預覽可查 `團長`／`Scoutmaster`／`童軍領隊` → peak-scoutmaster；`迷霧森林`／`Gloom` → peak-location-gloom（英文也可能命中更新摘要）；`徽章`／`Badges` → peak-badges；`復活`／`Teammate Revival` → peak-teammate-revival；`Final Ascent`／`最終攀登` → peak-update-final-ascent-update。真實正式查詢仍全部 no_data。沒有語意搜尋、FTS、斷詞、簡繁互轉或擴大量級效能驗證。

來源讀回含 original／request／canonical URL、selector，引用含章節 locator／pinned snapshot；另記取得／來源更新時間（缺失為 null／unknown）、版本、raw／body hash 與當時／目前用途。snapshot-diff 比較 hash／設定／正文差異，不改條目或審核；後續匯入仍產生新待審修訂。URL 不是模型已讀取的證明。本次沒有排程／監控、跨 repo LLM 串接或自動驗證事實。

詳細已收／待收／待整理／受限及自有分類對映見 [peak-coverage.md](peak-coverage.md)。wiki.gg 全站分母未知，不能報完成率；食物／烹調、全道具／生物／勳章、難度／數值／版本與獨立玩家攻略仍有缺口。

## 道具覆蓋的實際缺口

**item 仍只有 5 筆**；第二批增加區域／機制等條目，沒有增加道具數，不能用總條目數表示道具覆蓋成果。

| 英文名／繁中暫譯 | 已保存到條目的資訊 | 尚未取得 |
|---|---|---|
| Anti-Rope／反向繩索 | 官方行銷頁確認名稱存在 | 具體用途、取得地點／條件、操作、限制 |
| Energy Drink／能量飲料 | 官方行銷頁確認名稱存在 | 效果、持續時間、取得地點／條件、操作、限制 |
| Backpack／背包 | Wiki 概述增加攜帶空間 | 容量數值、取得地點／條件、操作、限制 |
| Piton／攀岩釘 | Wiki 概述協助攀登 | 取得地點／條件、操作、效果／限制；與官方 climbing spikes 名稱對應待核對 |
| Rope Spool／繩圈 | Wiki 概述協助登高的道具 | 取得地點／條件、放置方式、繩長、使用限制 |

目前 3 筆只有定性用途、2 筆只有存在性；0 筆有獨立核對的逐道具取得資訊或完整使用條件／限制。文章提到世界／行李箱的一般物資取得，不代表這 5 件個別道具都已核對來源。所有 5 筆仍待審，未實測。

已保存的 2 個正文來源都不是完整道具目錄；尚沒有一份已讀、能逐項核對的 PEAK 道具目錄。wiki.gg Items／Equipment 僅為候選 URL，不保證完整；正文不可得與授權未知分開。既有 robots 明示 search=yes、ai-train=no，ai-input 缺失，不是 AI 輸入明示禁止。`terms_url` 目前指向 robots，並不表示完整 Terms of Service 已讀或其拒絕全部本機用途；確切授權版本／例外與平台條款仍欠缺。主站正常讀取的 403 是存取障礙，沒有換 UA／代理／端點／鏡像解決。

Landfall Fan Creation Policy 的 AI 文本條文針對使用 PEAK IP 的 fans／未授權創作者；未明確說明事實摘記、官方網頁參考或翻譯摘要。當前暫停是本機保守設定，不能當成網站已明示禁止事實知識整理；其適用範圍仍待確認。

若道具主要來源仍無法正常取得，最小協助方案是一份使用者**有權轉交**的道具資料表或站方允許的 HTML／文字／PDF 匯出，保留原始 URL、來源更新／取得日期及授權／限制註記。這不是要求繞過登入、付費或 403，也不把「提供檔案」當作自動授權所有 AI 用途。亦可由使用者另行授權聯絡站方澄清；本批沒有對外發信。後續優先補逐道具來源、用途、取得條件與限制，不再用不相關概述擴充取代道具覆蓋。

## 搜尋驗收輸入

真實資料預覽輸入包括 `背`、`背包`、`Backpack`、`bAcKpAcK`、`ＢＡＣＫＰＡＣＫ`、別名 `揹包`／`背袋`、`毒`／`Poison`／`毒素`，以及只出現在摘要的 `攀登島中央`。正式查詢在真實資料全部待審時應一律為 `no_data`；不得把這點報成正式知識已上線。

合成資料測試使用 `Lunar Rope`／`月光繩`／`MOON ROPE`／`藍色落腳`，才模擬人工批准與發布，並驗證拒絕哨兵、待審修訂及過期來源不進正式查詢。每次 CLI 呼叫開啟獨立 Python 程序，重新讀取同一 SQLite；公開測試命令為：

```powershell
uv --cache-dir .uv-cache --offline lock --check
uv --cache-dir .uv-cache --offline run python -m unittest discover -s tests -v
git diff --check
```

## 未達標與限制

- **獨立玩家攻略來源仍未取得**。官方合作玩法建議可供預覽，但不可代稱成獨立玩家攻略；issue #3 保持未結案。
- 未核對本機遊戲 build／道具數值；沒有啟動遊戲或進行玩家實測。官方行銷頁與 Wiki 的區域數資訊不同，本批不收該總數。
- live 網站實際 429／503 恢復未遇到；重試、更新／去重、過期隔離由明確合成 transport 測試涵蓋，與真實 HTTP 200／政策阻擋分開回報。
- 不含自動知識整理／LLM、全量圖鑑、跨 repo 交付、部署或正式知識批准；沒有新增套件、服務或隔離執行環境。

## 靜態審核後的採集修正

同一 PR 補上 robots HTTP 200 challenge／編碼的 fail-closed 驗證，以及 DNS 已驗證 public IP 與實際 TCP 連線的綁定。保留原 hostname 的 TLS SNI／憑證／HTTP Host 驗證；偵測到 HTTP／HTTPS／ALL proxy 時明確停止，不自動繞過或減弱 TLS。

對應回歸測試確認不合法 robots 的 target requests=0、合法空 robots 仍可用、DNS public→private 改答不連私網；後續 robots 禁止新抓取不作舊資料授權撤回判定，既有 `allow_fetch=false` 隔離測試保留。當時 11 則未變更證據保留為歷史；用途修正後的 36 條目／41 修訂另存同一最終 commit 的完整驗收，不拿前版測試替代。

新增回歸覆蓋 ai-train=no 不封普通搜尋、use=reference 不一刀切、ai-input=no 限制該用途、不同 UA 群組不混用、用途未知不取頁、缺失／矛盾訊號為 unknown，以及來源追溯／快照差異不改審核。每次 CLI 都是新程序、等待退出後再讀回；不是 OS 重開／斷電測試。完整命令／argv／exit／輸出／輸入雜湊只存私人 evidence，PR 列最終 head 與本機結果。遠端 CI 沒有結果就不宣稱通過。

另修正 local_cache 保存後進正式搜尋的缺口：已保存 robots 的 search=no 不會被 manifest search_index=allowed 或人工批准／發布覆蓋；多引用任一受限時整則隱藏。回歸從合成採集→匯入→批准／發布→正式搜尋／預覽及新程序讀回驗證，包含未知／缺失訊號仍可依獨立條款審查搜尋、其他 UA 不混用、舊 metadata 和相同正文去重後新觀察到的限制。這輪不重新採集真實網站，不新增真實知識，也不改真實審核狀態；前版實抓結果只標作歷史。

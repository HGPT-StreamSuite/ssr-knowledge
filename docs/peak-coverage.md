# PEAK coverage 與 Wiki 分類對映

盤點日期：2026-10-19（UTC）。這是已知來源的工作清單，**不是全網或 wiki.gg 的完整目錄**。沒有取得該站 sitemap／分類樹／總頁數，分母未知，不能計算完成百分比。僅處理 PEAK；不與其他 repo 串接。

## 已收、待收、待整理、受限

| 狀態 | 已核對 URL／範圍 | 已知內容與下一步 |
|---|---|---|
| 已收 | [Landfall PEAK](https://landfall.se/peak) | 初批 1 快照、6 則官方待審稿；本輪政策核對後暫停新增與重抓。舊資料保留，不視為已獲未來 AI 使用許可 |
| 已收／待整理 | [English Wikipedia PEAK](https://en.wikipedia.org/wiki/Peak_(video_game)) | 已保存文章；Gameplay、Development 可做有限的事實條目。CC BY-SA 4.0 文字須附來源作者群、授權與改寫告知；不收圖片、外引長文或把 Wiki 說成官方設定 |
| 待收／用途待確認 | [Landfall FAQ](https://landfall.se/faq) | Web 已讀到 PEAK FAQ、支援、設定及更新方向；採集器尚未保存。頁面含其他遊戲，未驗證 PEAK 子樹 selector；未因可瀏覽就開始複製正文 |
| 待收／用途待確認 | [PEAK Press Kit](https://landfall.se/peak-press-kit) | Web 已讀到作品基本資料；採集器未保存，圖片／雲端素材不下載 |
| 受限／待確認 | [wiki.gg Items](https://peak.wiki.gg/wiki/Items) | 只保留已讀 robots／搜尋發現的 URL 與標題；**正文 0 頁**。修正本機用途混淆後仍不自動取頁；條款不明與先前觀察的 403 各自保留 |
| 受限／待確認 | [wiki.gg Equipment](https://peak.wiki.gg/wiki/Equipment)、[How to play](https://peak.wiki.gg/wiki/How_to_play) | 只知道 hub URL；不推斷子頁清單／數量，不再經 API、鏡像、其他 UA 或端點盤點受限正文 |
| 受限 | [Steam PEAK](https://store.steampowered.com/app/3527290/PEAK/)、[Steam 玩家指南](https://steamcommunity.com/sharedfiles/filedetails/?id=3514106064) | 保留 app identity 與來源候選；Subscriber Agreement §4.C 的 automation 限制未解決。玩家指南另有移除／相容性標記，不能當成已驗證攻略 |
| 受限 | [BLAST 道具文](https://blast.tv/gaming/news/all-items-in-peak-explained)、[G2A 攻略](https://www.g2a.com/news/features/10-essential-beginner-tips-to-survive-your-first-climb-in-peak/)、[Polygon 攻略](https://www.polygon.com/guides/608514/peak-game-tips-tricks-beginners-before-you-start) | 初批已記條款／robots 限制；本輪沒有重試正文，也未用替代路徑取得同一內容 |
| 待發現 | 可授權的獨立玩家攻略／實測 | 目前 **0** 個已保存玩家攻略來源、**0** 個本機玩家實測。gameplay.tips 公開索引未找到 PEAK，部分索引 500；不能把官方建議或 Wiki 轉述標成玩家實測 |

這些標籤可以同時成立：正文已保存仍可能有用途待確認；待收代表尚未保存，不代表可以立即採集。來源 URL、政策與未取得正文的原因都保留，URL 本身不表示 LLM 已讀取。

## 用途核對與已更正的錯誤

本機早期將 `use=reference` 一律拒絕，且額外套用 GPTBot／ChatGPT-User 的群組，曾把結果說成網站禁止所有本機檢索。這個說法過廣，已修正程式與文件。實際固定 UA 是 `SSRKnowledge/0.1`；不換 UA、代理或端點以跨過已觀察的存取限制。

wiki.gg 已保存 robots 的適用 wildcard 群組為 `Allow: /`，其 Content-Signal 包含 `search=yes`、`ai-train=no`、`use=reference`；`ai-input` 缺失。新解讀分開紀錄：robots 的搜尋訊號為 yes、訓練為 no，本機保存與 AI 輸入未知；`use` 不作標準 yes/no 的推論。GPTBot 的禁止群組不是本 collector 的 UA 群組。**robots 路徑可取不等於條款允許本機保存或 AI 整理**；沒有因此開始抓取 Wiki 正文。

新增核對 [PEAK Fan Creation Policy](https://landfall.se/peak-fan-policy) 後，發現其限制以 PEAK IP 產生 AI 文本／產品與訓練。這份政策主要討論 fan creations；對事實參考整理是否適用仍未明確。紀錄 training 為明示受限、AI input 為範圍待確認，不把「禁止產生 AI 文本」直接改寫成「禁止所有 AI 輸入」。Landfall 新採集及新增官方 AI 草稿暫停。隱私政策不作重用授權證明；不刪除原有待審資料。

Wikipedia 的文字採 [Wikimedia Terms §7](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use) 及 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 的複製／改作依據，有限人工／agent 整理仍須附上作者群來源、授權連結與改寫告知。這是操作人員對文字授權的用途評估，不代表網站特別批准本工具或下游所有使用。訓練未評估、未執行。

## 自有分類與對映（peak-v1）

以下是資料格式的對映建議；除已讀文章的章節外，不宣稱它是 wiki.gg 已驗證分類樹。每則條目可加 `taxonomy`，保留 `mapping_version`、`source_path`（原站分類／章節路徑）和 `subtype`。對映與繁中摘要是編輯步驟，採集器不會自行分類或翻譯。

| 來源主題／章節 | 自有 category | 建議 subtype | 尚缺什麼 |
|---|---|---|---|
| Gameplay：體力、攜帶、復活、合作、難度 | mechanic | stamina / inventory / revival / coop / difficulty | 目前版本數值、例外情況與遊戲內驗證 |
| Items / Equipment；食物、消耗品、攀登工具 | item | food / consumable / traversal / equipment | 完整道具名單、數值、取得／使用／互動；Wiki hub 正文受限 |
| Gameplay：狀態影響 | status | hunger / injury / poison / weight / temperature | 治療、持續時間、疊加與精確數值 |
| Gameplay：Biomes / Locations | location | biome / landmark | 僅收文章能核對的名稱／概略變體，不報完整區域數或全地圖 |
| Gameplay：Enemies / Creatures | creature | enemy / wildlife | 完整生物表、行為與觸發條件，未實測 |
| Gameplay：Badges / Achievements | achievement | badge | 只可建立制度概念；個別勳章與解鎖條件未取得 |
| Development：內容更新 | update | content_update | 記文章所述日期與未知遊戲 build，不冒稱目前版本 |
| How to play / 攻略 | guide | strategy | 必須分開 official、third_party_analysis、player_test；未有獨立玩家攻略正文 |
| FAQ：設定、連線、支援 | support | accessibility / multiplayer / troubleshooting | Landfall 用途待確認；不執行來源中的 OS／安裝／安全設定指令 |
| 世界觀／角色／故事 | lore | premise / character / narrative | 只保留有可核對事實的位置；不收同人，不由遊戲名稱或語氣補造設定 |

尚無可靠完整目錄的主題至少包括：食物／烹調、各道具、環境危害、全生物、個別勳章、難度明細、版本歷史、操作／故障處理與故事設定。已有概念條目不代表該主題完整。

## 可執行下一步

1. 在既有授權與 robots 範圍內手動重跑 Wikipedia 精確 URL，保留舊快照，做 hash／正文差異；依實際文章擴充待審事實條目。
2. 用 `snapshot-diff` 核對來源版本，將受影響知識編輯為新待審修訂；不自動沿用任何核准／發布結果。
3. wiki.gg／Landfall 用途待確認期間保留來源記錄和缺口。取得明確適用條件後才討論其正文採集；既有 403 不能靠改 UA／代理／端點解決。
4. 維持獨立玩家攻略為未完成條件；找到可正常存取且條件允許的真實來源後，另做有限批次。不承諾全網收全。

本輪沒有排程、雲端環境、跨 repo LLM 串接或向量 DB。網頁正文中的命令／連結僅為資料，不能影響程式或執行環境。

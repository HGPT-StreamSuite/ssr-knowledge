# 2026-10-19 PEAK 首批結果摘要

此檔只有不轉載正文的結果摘要；私人 DB、原文、草稿輸入及完整命令輸出保存在本機 checkout 外。最終 commit 與實跑紀錄由 PR 及私人 evidence 檔案對照。

## 來源結果

| URL | 程式化結果與用途 |
|---|---|
| https://landfall.se/peak | HTTP 200；官方頁 HTML 與選定 main 正文保存成功 |
| https://en.wikipedia.org/wiki/Peak_(video_game) | HTTP 200；Wiki HTML 與 mw-content-text 正文保存成功，保留來源及授權脈絡 |
| https://peak.wiki.gg/wiki/Items | robots 200；content signal／AI 規則不允許此全文用途，未請求目標正文 |
| https://store.steampowered.com/app/3527290/PEAK/ | manifest 政策停用，未請求正文；app ID 僅作識別 |
| https://steamcommunity.com/sharedfiles/filedetails/?id=3514106064 | manifest 政策停用，未請求正文 |
| https://blast.tv/gaming/news/all-items-in-peak-explained | 條款不允許本次保存用途，未請求正文 |
| https://www.g2a.com/news/features/10-essential-beginner-tips-to-survive-your-first-climb-in-peak/ | 條款不允許建立資料庫／catalog，未請求正文 |
| https://www.polygon.com/guides/608514/peak-game-tips-tricks-beginners-before-you-start | robots／條款限制自動採集及 AI 資料庫，未請求正文 |

替代玩家攻略站 gameplay.tips 的公開 robots 可讀；對應 2025 年份的 `post-sitemap6.xml` 兩次回應 HTTP 500，其他已查公開索引未發現 PEAK 頁面。沒有繞用來源鏡像或補造玩家實測。

## 待審條目與來源對照

| 來源 | 條目 ID（草稿） | 分類 |
|---|---|---|
| landfall-peak | peak-map-rotation、peak-stamina | 機制 |
| landfall-peak | peak-team-route | 官方合作玩法建議 |
| landfall-peak | peak-energy-drink、peak-anti-rope | 道具存在性；未補寫缺少的效果數值 |
| landfall-peak | peak-castaway-scouts | 官方故事前提；無衍生劇情 |
| wikipedia-peak | peak-rope-spool、peak-piton、peak-backpack | Wiki 道具彙整 |
| wikipedia-peak | peak-poison、peak-hunger | Wiki 狀態彙整 |

11 則全部為 **agent 閱讀實際快照後編輯**的繁中草稿，非蒐集程式自動翻譯或研究；全部保持 `pending_review`，沒有真實條目經 agent 核准或發布。中文名稱與別名為編輯暫譯，仍需人工核對。

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

# PEAK 詳細來源第一批可行性

2026-10-20，本機既有 Python／uv 環境。只處理 **24 KARAT BADGE（24 克拉徽章）**與 **Ancient Idol（古代偶像）**；結果不是整庫採集完成報告。

| 來源 | 實際取得方式與結果 |
| --- | --- |
| [PEAK robots](https://peak.wiki.gg/robots.txt) | 固定 SSRKnowledge transport，HTTP 200；只取得政策文件。 |
| [Badges](https://peak.wiki.gg/wiki/Badges) | web open 403；本機直接批次在用途審查階段停止，未再請求正文。 |
| [Ancient Idol](https://peak.wiki.gg/wiki/Ancient_Idol) | web open 403；同上，未重複嘗試或繞過。 |
| [Wiki.gg 條款](https://wiki.gg/termsofservice) | web open 403；未取得可完整核對的條款。 |
| 上述兩個 Wiki 頁的搜尋索引 | 操作者選取、附 query／捕捉時間的短摘錄；不是完整頁面或程式自動實抓。 |
| [Items](https://peak.wiki.gg/wiki/Items) 與遊戲 Localized_Text | 沿用已保存的使用者附件與官方本機文字；本次沒有重新抓網頁或擷取遊戲資源。 |

兩條本機自動任務結果皆為 `manual_required / terms_unreviewed`，正文 HTTP 次數為 0、沒有自動新增知識。重開完整 CLI 再執行時，已阻擋任務維持原狀、不重發請求。這與另行觀察到的 web open 403 分開記錄。robots 的 reference 訊號不作全面 KB 禁令；API/export 路徑的實際禁抓規則與未完成條款核對見 [批次文件](research-batches.md)。

## 實際保存與讀回

- 原有 228 個 entity 保留，只新增兩筆人工整理的 pending 修訂：徽章 623、偶像 624。沒有批准或發布真實知識。
- 原有 7 份來源快照與 raw hash 保留；新增 2 份明確標示為索引摘錄的快照。合計 18 個來源登記、9 份快照、624 個修訂；兩個直接來源登記尚無正文快照。
- 相同摘錄與草稿重複匯入均為 unchanged，不新增修訂。兩筆原有官方名稱、徽章官方顯示條件、道具原數值及原始表格備註均保持原值。
- 官方顯示文字與 Wiki 攻略分開。可核對的取得位置、Kiln 用法、持握效果、重量／烹調限制逐段附來源。索引中的 Citadel、背包線索明列取得方式與片段限制；未把被截斷的解鎖敘述補成事實。
- 獲得對象、具體獎勵、完整 Tomb 取物路線仍是缺口。來源不足不填成「沒有」，也不以整理筆數宣稱覆蓋完整。

## 驗證範圍

同一程式版本的 120 項本機測試包含完整既有回歸與新增合成採集測試。正常 fixture 可自動完成採集→解析→英文欄位→pending DB→預覽；更新不繼承批准，來源變體分列。403／401／429／redirect／challenge／timeout、robots／條款、來源 ID 衝突、解析不足、Retry-After、任務恢復與有界批次另有合成證據。**這些不是實站成功證據。**

真實驗收另對照 DB→HTTP JSON／HTML、名稱／舊別名／全文查詢、來源與缺欄。來源頁籤把本機遊戲資源位置與 Steam 歸屬網址分開，Items 關聯保留實際備註方法。私有完整輸入、DB、快照、指令輸出與頁面證據不在此 repo。

盤點結果：5 個已有明確詳細連結候選、63 個尚無額外攻略的官方條件徽章、37 個只有名稱／泛稱提示的道具候選。這是待處理清單，不是遊戲資料總數或完整性評分。其餘詳細道具的取得、限制等缺欄另存私有盤點；在原站可行性成立前不自動擴批。

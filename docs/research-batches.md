# 有界詳細來源採集

`catalog research-batch` 重用既有 collector，不另架服務或安裝套件。它是逐條來源任務，不是無界爬蟲。先完成少量真實來源的可行性驗證，再決定下一份明列 URL 的批次。

```powershell
uv --cache-dir .uv-cache --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\peak-data discover-details
uv --cache-dir .uv-cache --offline run --no-sync python -m ssr_knowledge catalog --data-dir C:\private\peak-data research-batch --plan C:\private\plan.json --max-jobs 2
```

計畫格式為 `{ "manifest": <既有來源 manifest>, "tasks": [{ "entry_id": "...", "source_id": "...", "adapter": "wiki_item" }] }`。manifest 沿用四種用途獨立審查、固定身分、exact HTTPS URL 與 selector 規則；一次最多 20 個來源。adapter 只有 `wiki_item` 和 `wiki_badge`。CLI 不提供 proxy、替換身分、登入或 challenge 繞過選項。

`discover-details` 只讀取現存明確的 `detail_page`，或已保存 Wiki HTML 中與現有英文名完全相同的連結；不猜 slug、不讀搜尋摘要、不請求網路。異站、查詢字串及 Wiki 特殊 namespace 連結不列入自動跟進候選。新發現連結必須先列入用途已審查的 manifest 才能採集。附件文字沒有 HTML 連結時不虛構詳細頁來源。

## 自動與人工邊界

自動流程為：已審查計畫 → robots／條款檢查 → 受限 HTTP → selector 本文擷取 → 目標範圍解析 → 字面英文欄位正規化 → 新 pending 修訂 → 獨立預覽查詢。英文原句、來源版本、時間、引用與缺漏一起保存；原有官方名稱、官方顯示條件與人工整理文字各自保留。程式沒有翻譯、推斷解鎖條件、遊戲實測或批准知識。

目前詳細頁規則只擷取有明確字面線索的取得、持握效果、熔岩投擲、限制、背包用法、獲得對象及獎勵段落。item 需要頁面 title 符合目標；badge 必須唯一匹配目標表格列，不從其他徽章借用條件。超過 300 字的段落、碎片、不同版型可能進人工處理。這是第一批 adapter；不能以兩條測試推定其餘 PEAK 版型均受支援。

「實質擷取」要求至少兩個欄位、兩段不同原文，合計至少 100 字元；名稱及 `Can be used for …` 等泛稱提示不算。此門檻只排除明顯空殼，不證明語義正確、攻略完整或來源沒有互相矛盾。覆蓋統計分別顯示成功實抓、已擷取欄位、缺欄、待翻譯、待人工審核。不同來源保留為分開候選；同欄位的不同說法標示尚未調和，不自動選邊。

`guide_details` 是另一種**人工整理**的繁體中文補充，逐段有 Wiki／第三方／玩家實測類別與 pinned 短引文；未找到的地點、前置、步驟、獲得對象、獎勵或限制必須列缺口。不能把這種補充或搜尋索引摘錄當作上述自動採集成功。官方徽章顯示文字維持獨立欄位與本機資源驗證。

## 例外與恢復

- 15 秒 HTTP timeout；每階段最多三次瞬時錯誤重試，指數退避，遵守數字與 HTTP 日期形式的 Retry-After。超過 30 秒的等待寫入 cooldown，結束此次請求，不阻塞長睡眠。
- robots、條款未確認／禁止、HTTP 403、401、redirect、200 challenge／密碼表單、429、網路失敗與解析不足分開標示。403 不立即重試；不替換 UA、proxy、鏡像或 endpoint 來繞過限制。404／410 也只代表該 URL 未取得，不是遊戲沒有資料。
- `research_jobs`／`research_attempts` 與 origin throttle 存在私有 SQLite。每次最多處理 1–10 條；其餘保持 queued。retry_wait 到期才可再試，最多三輪後轉人工；執行中任務有 300 秒 lease，程序中止後可恢復。
- completed 任務預設略過；`--refresh` 才重讀成功任務。人工阻擋預設略過；只有完成新的存取／用途確認後才考慮 `--retry-blocked`。此旗標不解除 collector 的條款或 robots 檢查。
- 不完整本文保存在私有 `quarantine/`，不改 latest snapshot 或條目。HTTP 失敗不保存空本文冒充新版本。有效更新保留舊 snapshot 與 immutable 修訂、輸出 diff，新的知識仍是 pending；相同內容不增加修訂。
- 若來源成功保存但候選驗證失敗，來源與錯誤留存、任務轉人工，既有條目不變。已發布版本不把批准狀態傳給新修訂。

目前真實 Wiki 詳頁的 web open 回報 403；現有直接採集用途審查仍未完成。兩者是不同阻塞。搜尋索引摘錄只能提供待核對線索；未取得實質原站本文前，不宣布全庫自動擴展可行。權限、robots 或網站限制不能用使用者想要資料作為放行依據。

2026-10-20 重新讀取 `https://peak.wiki.gg/robots.txt` 成功 HTTP 200：一般 `/wiki/Badges`、`/wiki/Ancient_Idol` 對固定 `SSRKnowledge` 身分的路徑規則允許；`search=yes`、`ai-train=no`、`use=reference` 分開保存。沒有 `ai-input` 或 local-cache 訊號表示訊號未表態，不是禁止；`use=reference` 也不作全面 KB 禁令。既有附件頁尾提供 CC-BY-SA 4.0 授權文字；它與自動存取政策分開。未完成的是 `https://wiki.gg/termsofservice` 的完整條款核對（本次 web open 403），所以直接採集來源保留既有 unknown 用途審查，並非宣稱條款已禁止快取。

同份當日 robots 明列 `/api.php`、`/rest.php`、`/wiki/Special:` 禁抓，因此沒有請求 API／Special:Export 作為替代。Wiki.gg 官方支援索引有 MediaWiki API 與 export 功能說明，但功能存在不代表本批來源允許這個採集器使用；未發現已核准的 PEAK 公開 dump 路線。

`catalog import-web-excerpt --file … --receipt …` 可保存**操作者選取**的至多 200 字詞 UTF-8 索引摘錄，附實際 query、失敗 HTTP 狀態、捕捉時間、索引日期標籤及用途審查。資料以獨立 acquisition kind 保存，`full_page_acquired=false`，不假裝網站 HTML 或原頁更新時間；本機匯入本身不發 HTTP。該快取依據僅涵蓋這份有歸屬的短摘錄，不解除直接採集的用途或存取限制。此路徑與附件一樣屬人工來源取得，不能通過自動 `research_extracts` 驗證，也不算自動採集成功。

## 驗收與資料保存

合成測試覆蓋成功採集到 pending、程序重開、dedupe／更新 diff、審核不繼承、來源變體分列、精確連結發現、名稱／提示不足、其他徽章誤歸、條款零請求、403／401／429／redirect／challenge／timeout、Retry-After、恢復 lease 與重試上限。合成結果不是實站成功證據。

實站每個批次另存計畫、程式 commit、實際 URL、成功／失敗分類、HTTP 次數、保存結果與搜尋結果。私有 corpus、DB、quarantine、計畫中的本機路徑與實測完整輸出不推到 Git。真實條目保持 pending；正式搜尋不得顯示它們。

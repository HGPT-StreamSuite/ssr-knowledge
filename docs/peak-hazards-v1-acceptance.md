# PEAK 環境危害首批（peak-hazards-v1）驗收

2026-10-22，沿用 `work/peak-real-data/knowledge.sqlite3`。新增計畫 **`peak-hazards-v1`（10 目標）**，條目 **268 → 278**，修訂 **296 → 306**，來源 **253 → 263**；全部新修訂 **`pending_review`**。未批准／未發布／未 home sync。

Live sha256：`b8c1915198dee1a7487de169e65eb135ca8c004288cee099ef933b6d9bc9cd74`（導入前 `b05413d1…`）。

## 新條目

| entry_id | 名稱 | 來源 |
|----------|------|------|
| peak-fog | 霧（時限） | [Hazards](https://peak.wiki.gg/wiki/Hazards) Fog |
| peak-sleepy-gloom | 昏沉陰鬱 | Hazards Sleepy Gloom |
| peak-lost-souls | 失落魂靈（時限） | Hazards The Lost Souls |
| peak-bridge | 橋樑崩塌 | Hazards Bridge |
| peak-lava-tube | 熔岩管 | Hazards Lava Tube（有別於 `peak-lava`） |
| peak-wind | 風（Roots） | Hazards Wind |
| peak-rain | 雨（Tropics） | Hazards Rain |
| peak-deep-water | 深水（Roots） | Hazards Deep Water |
| peak-mushroom-spore-cloud | 蘑菇孢子雲 | Hazards Mushroom Spore Clouds |
| peak-spike-trap | 尖刺陷阱 | Hazards Spike Traps（有別於 `peak-arrow-trap`） |

## 刻意留下的 quantities 缺口

短摘錄表列無數值者不臆造：

- `peak-bridge`：未給具體負載人數
- `peak-wind`：未給陣風週期／體力倍率
- `peak-rain`：未給額外體力倍率／時長
- `peak-deep-water`：未給每秒孢子量
- `peak-mushroom-spore-cloud`：未給精確孢子速率

## 刻意未收

- 已有 mechanic：`peak-blizzard`、`peak-lava`、`peak-arrow-trap`、`peak-belltower`
- 已收 creature 危害列（水母／蟻獅／捕蠅草等）不重複建條
- Citadel 其餘機械陷阱、Capybara NPC 延後
- 不碰 `peak-unconscious` 昏迷秒數

## 流程

A `approved_local_file` 短摘錄 → intake／bundle → B ingest `--apply` → import-drafts；candidate 先行再套 live。

## 查詢

`http://127.0.0.1:8767/?entry=peak-fog`（請重新讀取 DB）。

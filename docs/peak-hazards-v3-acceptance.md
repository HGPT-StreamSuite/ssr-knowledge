# PEAK 環境危害延後批（peak-hazards-v3）＋水豚（peak-creatures-v4）驗收

2026-10-22，沿用 `work/peak-real-data/knowledge.sqlite3`。

- **`peak-hazards-v3`（10 目標）**＋**`peak-creatures-v4`（1 目標）**
- 條目 **288 → 299**，修訂 **316 → 327**，來源 **273 → 284**
- 全部新修訂 **`pending_review`**；未批准／未發布／未 home sync

Live sha256：`c5b433b64b4e6eb4a5a5252bb01ffced719870b49b1c4983d3641b2d47375c38`（導入前 `1b074120…`）。

## hazards-v3 新條目

| entry_id | 名稱 | 區域 |
|----------|------|------|
| peak-ice-rocks | 冰岩 | Alpine |
| peak-icicles | 冰柱 | Alpine |
| peak-flash-bulbs | 閃光球 | Alpine |
| peak-geysers | 間歇泉 | Alpine |
| peak-rusty-piton | 鏽蝕岩釘 | Alpine |
| peak-poison-ivy | 毒藤 | Tropics |
| peak-thorny-giant-ivy | 帶刺巨型常春藤 | Tropics |
| peak-cactus-hazard | 仙人掌（危害） | Mesa（與道具 `peak-cactus` 分開） |
| peak-tumbleweed | 滾草 | Mesa |
| peak-tornado | 龍捲風 | Mesa |

## creatures-v4

| entry_id | 名稱 |
|----------|------|
| peak-creature-capybara | 水豚（友善 NPC） |

## 本批 quantities 缺口

表列無數值：`icicles`、`flash-bulbs`、`thorny-giant-ivy`、`cactus-hazard`、`tumbleweed`、`tornado`。

## 仍可延後（Hazards 表尚有、非生物重複）

- Tropics：Spore Bomb（explosive／poisonous）、Monstera（附壁蝨機率，威脅面見 tick）
- Mesa：Dynamite／Exploding Luggages／Pickaxe（危害面；道具已有 dynamite）
- Caldera／Kiln：Eruptions、Hot Rocks
- Fire Hazards（泛稱營火熱源）

## 流程

A `approved_local_file` → intake／bundle → B ingest `--apply` → import-drafts；candidate → live。

## 查詢

`http://127.0.0.1:8767/?entry=peak-creature-capybara`（請重新讀取 DB）。

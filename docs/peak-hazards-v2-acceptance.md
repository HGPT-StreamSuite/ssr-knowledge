# PEAK 環境危害補完（peak-hazards-v2）驗收

2026-10-22，沿用 `work/peak-real-data/knowledge.sqlite3`。新增計畫 **`peak-hazards-v2`（10 目標）**，條目 **278 → 288**，修訂 **306 → 316**，來源 **263 → 273**；全部新修訂 **`pending_review`**。未批准／未發布／未 home sync。

Live sha256：`1b074120156ae7abc6901609be73ce8ae9005481dbf435db205946b5cc069f13`（導入前 `b8c19151…`）。

## 新條目

| entry_id | 名稱 | 來源 |
|----------|------|------|
| peak-petrifying-stones | 石化石 | Hazards Petrifying Stones |
| peak-giant-saw | 巨型鋸 | Hazards Giant Saw |
| peak-swinging-mace | 擺盪釘錘 | Hazards Swinging Maces |
| peak-horizontal-spike-roller | 水平尖刺滾軸 | Hazards Horizontal Spike Rollers |
| peak-vertical-spike-roller | 垂直尖刺滾軸 | Hazards Vertical Spike Rollers |
| peak-luggage-trap | 行李陷阱 | Hazards Luggage Trap |
| peak-crucible-of-lava | 熔岩坩堝 | Hazards Crucible of Lava |
| peak-gloom-water | 陰鬱水域 | Hazards Gloom Water |
| peak-wrought-iron-fence | 鍛鐵圍欄 | Hazards Wrought-Iron Fences |
| peak-blazing-sun | 烈日（Mesa） | Hazards Blazing Sun |

## 刻意留下的 quantities 缺口

- `peak-giant-saw`：僅標 Injury
- `peak-luggage-trap`：僅標 Drowsy
- `peak-crucible-of-lava`：僅標 Heat
- `peak-gloom-water`：僅標 Slowness（未釘選 Gloom 頁百分比）

## 刻意未收

- hazards-v1 十則與既有 blizzard／lava／arrow-trap／spike-trap
- 已收 creature／道具列不重複
- Alpine 其餘環境列（冰岩／冰柱／閃光球／間歇泉等）、Capybara NPC 延後
- 不碰 `peak-unconscious` 秒數

## 流程

A `approved_local_file` 短摘錄 → intake／bundle → B ingest `--apply` → import-drafts；candidate 先行再套 live。

## 查詢

`http://127.0.0.1:8767/?entry=peak-swinging-mace`（請重新讀取 DB）。

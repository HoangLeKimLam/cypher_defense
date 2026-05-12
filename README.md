# Cypher Defense

> Tower Defense × Pathfinding — IT003.Q21.TTNT  
> Hoàng Lê Kim Lâm · MSSV 25520974

Bảo vệ **Server** khỏi các làn sóng Malware và Boss nguy hiểm bằng cách xây dựng hệ thống tháp phòng thủ. Mỗi level mang đến kẻ địch mới với cơ chế độc đáo buộc người chơi phải điều chỉnh chiến thuật liên tục.

---

## Mục lục

- [Cài đặt & chạy game](#cài-đặt--chạy-game)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Lối chơi](#lối-chơi)
- [Hệ thống Tháp (Tower)](#hệ-thống-tháp-tower)
- [Hệ thống Malware](#hệ-thống-malware)
- [Hệ thống Boss](#hệ-thống-boss)
- [Cơ chế đặc biệt](#cơ-chế-đặc-biệt)
- [Tiến trình Level](#tiến-trình-level)
- [Thuật toán & CTDL](#thuật-toán--ctdl)

---

## Cài đặt & chạy game

```bash
pip install pygame
python main.py
```

**Yêu cầu:** Python 3.10+, pygame 2.0+

---

## Cấu trúc dự án

```
cypher_defense/
├── core/                    # CTDL & thuật toán tự cài đặt (không dùng stdlib)
│   ├── data_structures.py   # LinkedList, Stack, Queue, MinHeap, MaxHeap
│   ├── graph.py             # Celltype, GridGraph
│   └── pathfinding.py       # astar(), bfs(), find_nearest_tower()
├── entities/
│   ├── malware.py           # Malware base + 13 subclass
│   ├── boss.py              # Boss base + 5 subclass
│   ├── tower.py             # Tower base + 9 subclass
│   ├── projectile.py        # BaseProjectile, Projectile, MalwareProjectile
│   ├── bomb.py              # Bomb, BossBomb (nổ thường + atomic)
│   ├── fire_mark.py         # FireMark — hiệu ứng lửa DoT
│   ├── server.py            # Server — mục tiêu bảo vệ
│   ├── wall.py              # Wall — tường tạm thời
│   └── shock_effect.py      # ShockEffect — hiệu ứng điện
├── systems/
│   ├── spatial_hash.py      # SpatialHash — truy vấn range query O(1) avg
│   ├── upgrade_tree.py      # N-ary upgrade tree
│   ├── shock_spread.py      # shock_spread() — BFS lan điện qua tháp
│   └── audio.py             # AudioManager singleton
├── ui/
│   ├── sprites.py           # SpriteCache singleton
│   ├── upgrade_menu.py      # UpgradeMenu UI
│   └── right_panel.py       # RightPanel HUD
├── data/levels/             # level1.json → level5.json
├── settings.py              # Hằng số toàn cục
├── game.py                  # Game loop chính
├── main.py                  # GameManager — state machine & menus
└── progress.json            # Tiến trình lưu tự động
```

---

## Lối chơi

| Hành động | Phím / Chuột |
|---|---|
| Đặt tháp | Click vào ô tường (WALL) |
| Chọn tháp để nâng cấp | Click vào tháp đã đặt |
| Hoàn tác đặt tháp | `Ctrl + Z` |
| Tạm dừng | `ESC` |
| Bật/tắt nhạc | `M` |

**Mục tiêu:** Ngăn Malware và Boss chạm vào Server (HP 1000). Qua tất cả wave trong level → Level Complete. Server bị phá → Game Over.

**Tiền:** Nhận thưởng khi tiêu diệt kẻ địch. Dùng để xây tháp và nâng cấp.

**Điểm:** Tích lũy theo HP server còn lại mỗi khi qua level. Lưu vào bảng xếp hạng.

---

## Hệ thống Tháp (Tower)

Tháp đặt trên **ô WALL**. Mỗi tháp có HP riêng — bị phá hủy khi HP về 0, đường đi malware tự tính lại.

### Tháp cơ bản (mở khóa từ Level 1)

| Tháp | Cost | HP | Damage | Fire Rate | Range | Đặc điểm |
|---|---|---|---|---|---|---|
| **BasicNode** | 50 | 200 | 30 | 1.0/s | 5 ô | Tháp chuẩn, không hiệu ứng |
| **IceWall** | 75 | 150 | 20 | 0.8/s | 5 ô | Slow malware 30%, kéo dài 2s |

### Tháp nâng cao (mở khóa theo level)

| Tháp | Mở ở | Cost | HP | Damage | Fire Rate | Range | Đặc điểm |
|---|---|---|---|---|---|---|---|
| **SpeedNode** | Lv 2 | 70 | 150 | 10 | 5.0/s | 6 ô | Liên thanh, DPS cao |
| **SpreadNode** | Lv 2 | 100 | 150 | 30 | 1.0/s | 10 ô | Slow lan ra bán kính 3 ô khi trúng |
| **RadarNode** | Lv 3 | 100 | 70 | 15 | 1.5/s | 10 ô | Tầm xa, đa dụng |
| **FireNode** | Lv 3 | 80 | 170 | 70 | 1.0/s | 6 ô | Tạo vết lửa 3s gây 5 dmg/s (DoT) |
| **PoisonNode** | Lv 4 | 120 | 80 | 3 | 1.0/s | 10 ô | Damage trong vùng AoE liên tục |
| **FreezeNode** | Lv 4 | 95 | 150 | 30 | — | 5 ô | Đóng băng hoàn toàn (slow 100%), 5s |
| **SniperNode** | Lv 5 | 90 | 170 | 100 | 0.25/s | 8 ô | Sát thương đơn cực cao, bắn chậm |

### Cây nâng cấp (N-ary Tree)

```
BasicNode
  ├── DamageUp → FireNode / SniperNode
  └── SpeedUp  → SpeedNode

IceWall
  ├── SlowUp   → FreezeNode
  └── RangeUp  → SpreadNode

RadarNode
  └── RangeUp  → PoisonNode
```

Nâng cấp tốn tiền và yêu cầu node cha đã mở khóa. Hiển thị trực quan qua **RightPanel HUD**.

---

## Hệ thống Malware

Malware spawn từ cổng Portal, di chuyển đến Server theo đường đã tính. Khi tháp bị phá hoặc đường thay đổi, toàn bộ malware tính lại path.

### Phân loại theo hành vi

#### Nhóm tấn công Server (A* pathfinding)

| Malware | HP | Speed | Reward | Đặc điểm |
|---|---|---|---|---|
| **Trojan** | 200 | 2.0 ô/s | 20 | Cơ bản, đi thẳng đến server |
| **Worm** | 150 | 4.0 ô/s | 15 | Nhanh, sprite tự xoay theo hướng |
| **WormPoison** | — | — | — | Kế thừa Worm, tấn công server gây độc (trừ HP theo thời gian) |
| **TrojanRanged** | — | — | — | Bắn projectile tầm xa (3 ô), không cần chạm mục tiêu |

#### Nhóm săn Tháp (BFS pathfinding)

| Malware | HP | Speed | Reward | Đặc điểm |
|---|---|---|---|---|
| **Spyware** | 200 | 1.5 ô/s | 20 | BFS đến tháp gần nhất, melee attack |
| **Ransomware** | 350 | 1.0 ô/s | 35 | Damage tháp cao (50/đòn), chậm |
| **LightSpy** | 250 | 1.5 ô/s | 20 | Tấn công tháp → kích hoạt **Shock Spread** lan điện sang tháp liền kề |
| **SlowSpy** | — | — | — | Tấn công tháp làm giảm fire_rate tháp |

#### Nhóm tầm xa

| Malware | Đặc điểm |
|---|---|
| **Spyware_Ranged** | Bắn MalwareProjectile đến Tower hoặc Server thay vì melee |
| **LightSpy_Ranged** | Phiên bản tầm xa của LightSpy — projectile gây shock khi trúng |
| **SlowSpy_Ranged** | Bắn projectile áp slow effect lên tháp khi trúng |

#### Nhóm cơ chế đặc biệt

| Malware | Đặc điểm |
|---|---|
| **VaultWare** | 50% thu hút đạn từ tháp về phía mình, tháp mất target |
| **RiposteWare** | 50% phản đòn — đạn tháp bắn trúng sẽ bay ngược lại tháp nguồn |

---

## Hệ thống Boss

Boss xuất hiện ở wave cuối mỗi level. Có HP cao, sát thương lớn, và cơ chế riêng biệt không có ở malware thường.
### RiposteBoss *(Level 1)*

> HP: 800 · Speed: 1.4 ô/s · Reward: 400

- **Riposte 50%:** Mỗi đạn tháp bắn trúng có 50% bị phản ngược lại tháp nguồn với damage = `attack_damage + projectile.damage`.
- 50% còn lại nhận damage bình thường.
- Di chuyển A* thẳng đến server, tấn công liên tục khi chạm.
- Phiên bản lớn hơn (scale 1.5×) của RiposteWare.
### FireWorm *(Level 2)*

> HP: 1000 · Speed: 1.2 ô/s · Reward: 100

- **AoE Tower Burn:** Mỗi 2 giây quét tất cả tháp trong bán kính 3 ô, gây 15 dmg + hiệu ứng đốt 5 dmg/s trong 3 giây.
- **Server Attack:** Khi chạm server, tấn công liên tục 30 dmg/đòn.
- Di chuyển bằng A* đến server.

### FlyingDemon *(Level 4)*

> HP: 1000 · Speed: 1.5 ô/s · Reward: 150

- **Bomb Drop:** Mỗi 8 giây thả 1 bomb ngẫu nhiên tại vị trí đứng:
  - **75%** Bomb thường — nổ sau 5–8s ngẫu nhiên, gây 150 dmg server + stun tháp 4s
  - **25%** Atomic bomb — nổ sau 5–8s, gây **10000 dmg** (thua game ngay lập tức)
- Cảnh báo: bomb nằm trên bản đồ sau khi drop, đếm ngược nổ ngẫu nhiên.

### Shadow *(Level 5)*

> HP: 1200 · Speed: 1.5 ô/s · Reward: 500

- **Roll Invincibility:** Mỗi 5 giây vào trạng thái Roll kéo dài 3 giây:
  - Tốc độ tăng **×3**, hoàn toàn **miễn sát thương** từ đạn tháp
  - Damage và attack speed tăng khi tấn công server trong Roll
- Animation 4 phase: Walk → Roll_Pre → Roll_Mid (loop) → Roll_End
- Khi Shadow xuất hiện, toàn bộ malware còn sống trở nên tàng hình.



### Final Boss *(Level 5)*

> HP: 5000 · Speed: 0.7 ô/s · Reward: 1000

- **Di chuyển col++:** Không dùng A* — đi thẳng từ (hàng 12, cột 0) sang phải từng cột.
- **Phá hủy 3×3:** Gặp ô không phải PATH/SERVER → animation Destroy_1 + Destroy_2 → xóa ô 3×3 xung quanh + **spawn RiposteWare** tại các ô bị phá.
- **Reflect 25%:** Đạn bắn trúng có 25% bay thẳng vào Server thay vì trúng Boss.
- **Bomb:** Thả bomb mỗi 15 giây (cùng cơ chế FlyingDemon, kể cả atomic).
- Nguy hiểm nhất vì liên tục biến đổi bản đồ và tạo thêm kẻ địch mới.

---

## Cơ chế đặc biệt

### Shock Spread (BFS qua lưới tháp)

Khi **LightSpy** hoặc **LightSpy_Ranged** tấn công một tháp:

1. `shock_spread()` chạy BFS từ tháp bị tấn công.
2. Duyệt qua các ô TOWER liền kề (4 hướng) — dùng **CustomQueue** tự cài đặt.



> Chiến thuật phòng thủ: Tránh đặt tháp thành chuỗi dài liên tục — LightSpy có thể vô hiệu hóa toàn bộ hàng tháp chỉ bằng một đòn.

### FireMark (DoT — Damage over Time)

FireNode khi bắn trúng malware → tạo **FireMark** tại ô đó:
- Tồn tại 3 giây, gây 5 dmg/s cho mọi malware đi qua.
- Có animation 18 frame, hiển thị qua Y-Sort pipeline.

### Bomb & Atomic Bomb

- **Bomb thường:** Nổ sau 5–8s ngẫu nhiên, stun tháp trong bán kính 4s.
- **Atomic Bomb:** Nổ gây 10000 dmg server — thực tế kết thúc game ngay lập tức. Có màu sắc khác biệt để cảnh báo.
- Người chơi có thể nhìn thấy bomb nằm trên bản đồ trước khi nổ.

### Tường tạm thời (Wall)

- Đặt tường tạm thời trên ô PATH để chặn đường malware.
- Tường tồn tại **10 giây**, sau đó tự biến mất và path được tính lại.
- Cooldown 10 giây giữa các lần đặt.
- Khi tường xuất hiện, toàn bộ malware đang sống tính lại đường đi qua A*.

### Y-Sort Rendering (Pseudo-3D)

Tất cả đối tượng được sắp xếp theo tọa độ Y trước khi vẽ — đối tượng ở hàng dưới đè lên hàng trên, tạo cảm giác chiều sâu. Mỗi sprite có bóng ellipse dưới chân.

### Riposte (Phản đạn)

Cả **RiposteWare** (malware) và **RiposteBoss** đều dùng cơ chế phản đạn:
- RiposteWare: 50% phản về tháp nguồn.
- RiposteBoss: 50% phản về tháp nguồn.
- Final Boss: 25% phản thẳng vào Server.

---



## Thuật toán & CTDL

> Tất cả CTDL trong `core/` được tự cài đặt — không dùng `heapq`, `collections.deque`, hay bất kỳ thư viện chuẩn tương đương.

| CTDL / Thuật toán | File | Ứng dụng |
|---|---|---|
| **CustomLinkedList** | `core/data_structures.py` | Lưu path di chuyển của malware/boss |
| **CustomStack** | `core/data_structures.py` | Undo stack khi đặt tháp (Ctrl+Z) |
| **CustomQueue** | `core/data_structures.py` | BFS pathfinding, shock_spread, riposte queue |
| **CustomMinHeap** | `core/data_structures.py` | A* open set — luôn lấy node chi phí thấp nhất |
| **CustomMaxHeap** | `core/data_structures.py` | Tower targeting — ưu tiên malware gần server nhất |
| **A\*** | `core/pathfinding.py` | Trojan, Worm, WormPoison, Boss di chuyển đến server |
| **BFS** | `core/pathfinding.py` | Spyware tìm đường đến tháp gần nhất |
| **BFS** | `systems/shock_spread.py` | Lan điện qua chuỗi tháp liên kết |
| **SpatialHash** | `systems/spatial_hash.py` | Tháp truy vấn malware trong range — O(1) avg |
| **N-ary Tree** | `systems/upgrade_tree.py` | Cây nâng cấp tháp phân cấp |
| **Binary Search** | `main.py` | Chèn điểm vào leaderboard — upper-bound O(log n) |

---

## Thông tin dự án

| | |
|---|---|
| Môn học | IT003.Q21.TTNT — Cấu trúc Dữ liệu & Giải thuật |
| Sinh viên | Hoàng Lê Kim Lâm — 25520974 |
| Engine | Python 3 + Pygame |
| GitHub | https://github.com/HoangLeKimLam/cypher_defense |

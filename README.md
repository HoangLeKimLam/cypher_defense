# Cypher Defense

Game tower defense 2D xây dựng bằng Python + Pygame cho môn **IT003.Q21.TTNT — Cấu trúc Dữ liệu và Giải thuật**, UIT.

> Người chơi vào vai Admin của Data Center trường UIT, bảo vệ Server trung tâm khỏi các đợt Malware do Rogue AI điều phối trên bản đồ mê cung 25×25.

---

## Chạy nhanh

```bash
pip install -r requirements.txt
python main.py
```

---

## Điểm đặc biệt — DSA tự cài đặt

Toàn bộ cấu trúc dữ liệu và giải thuật được **tự cài đặt từ đầu** trong `core/`, không dùng `heapq`, `collections.deque` hay bất kỳ module DSA nào của Python:

| Cấu trúc / Giải thuật | File | Dùng ở đâu trong game |
|---|---|---|
| `CustomLinkedList` | `core/data_structures.py` | `Malware.path` — lưu đường đi từng ô |
| `CustomStack` | `core/data_structures.py` | `Game.undo_stack` — Ctrl+Z hoàn tác |
| `CustomQueue` | `core/data_structures.py` | BFS frontier, hàng đợi spawn wave |
| `CustomMinHeap` | `core/data_structures.py` | A* open set, Tower nhắm kẻ gần Server nhất |
| `CustomMaxHeap` | `core/data_structures.py` | IceWall nhắm kẻ nhiều máu nhất |
| `GridGraph` | `core/graph.py` | Bản đồ lưới trung tâm |
| `A*` | `core/pathfinding.py` | Trojan, Worm tìm đường đến Server |
| `BFS` | `core/pathfinding.py` | Spyware/Ransomware tìm Tower gần nhất |
| `SpatialHash` | `systems/spatial_hash.py` | Tower dò Malware trong tầm bắn O(1) |

---

## Cấu trúc thư mục

```
cypher_defense/
│
├── core/                        ← Tầng DSA — tự cài đặt, không dùng stdlib
│   ├── data_structures.py       # Node, LinkedList, Stack, Queue, MinHeap, MaxHeap
│   ├── graph.py                 # Celltype constants + GridGraph
│   └── pathfinding.py           # heuristic, astar(), bfs(), find_nearest_tower()
│
├── entities/                    ← Các đối tượng game
│   ├── malware.py               # Malware + Trojan/Worm/Spyware/Ransomware/TrojanRanged
│   ├── tower.py                 # Tower + BasicNode/IceWall/RadarNode (có HP system)
│   └── projectile.py            # BaseProjectile → Projectile + MalwareProjectile
│
├── systems/                     ← Hệ thống hỗ trợ
│   └── spatial_hash.py          # SpatialHash — tra cứu Malware trong tầm bắn
│
├── ui/
│   └── sprites.py               # SpriteCache — load & quản lý toàn bộ sprite PNG
│
├── data/
│   ├── levels/
│   │   ├── level1.json          # Bản đồ 25×25, wave config, spawn weights
│   │   └── level2.json
│   └── sprites/                 # PNG assets (malware, tower, map tiles, portal)
│
├── main.py                      ← Entry point
├── game.py                      # Vòng lặp game chính (60 FPS), Y-Sort render
├── settings.py                  # Toàn bộ hằng số: màu, stats, FPS, animation
└── requirements.txt
```

---

## Cài đặt và chạy

**Yêu cầu:** Python 3.10+

```bash
# 1. Clone repo
git clone https://github.com/HoangLeKimLam/cypher_defense.git
cd cypher_defense

# 2. Cài thư viện
pip install -r requirements.txt

# 3. Chạy game
python main.py
```

---

## Cách chơi

| Phím / Thao tác | Tác dụng |
|---|---|
| Click ô xám (WALL) | Đặt Tower tại vị trí đó |
| Phím `1` | Chọn BasicNode ($50) — damage 25, range 3 ô |
| Phím `2` | Chọn IceWall ($75) — làm chậm Malware 50% trong 2 giây |
| Phím `3` | Chọn RadarNode ($100) — range 5 ô, phát hiện Malware |
| `Ctrl+Z` | Hoàn tác đặt Tower vừa xây, hoàn trả tiền |
| `ESC` | Thoát game |

---

## Các loại Malware

| Loại | Sprite | Chiến lược | Đặc điểm |
|---|---|---|---|
| **Trojan** | Mushroom (7 animation states) | A* đến Server | HP cao, tốc độ trung bình |
| **Worm** | Plant3 (6 action × 4 hướng) | A* đến Server | Nhanh nhất, HP thấp |
| **Spyware** | FloatingEye | BFS → phá Tower | Ưu tiên Tower thay vì Server |
| **Ransomware** | FoulGouger | BFS → phá Tower | Mạnh hơn Spyware, HP cao nhất |
| **TrojanRanged** | Enemy3 (5 animation states) | A* + tấn công từ xa | Bắn projectile, dừng cách Server 3 ô |

---

## Tính năng tuần 2

- **Đồ họa Sprite hoàn chỉnh** — map tiles PNG, pseudo-3D wall (TALL_FACTOR=1.5), tất cả entities có sprite
- **Animation state machine** — Trojan 7 trạng thái, Worm 6 action × 4 hướng, TrojanRanged 5 trạng thái
- **Y-Sort render pipeline 2.5D** — sort entity theo tọa độ Y, bóng ellipse alpha
- **Cổng Portal động** — random.choices() theo spawn weight, đếm ngược 10s trước mỗi wave
- **Tower có HP và bị phá** — BasicNode=100, IceWall=80, RadarNode=60; khi bị phá recalc path toàn bộ Malware
- **Projectile hierarchy** — BaseProjectile → Projectile (homing, tower) + MalwareProjectile (thẳng, ranged)
- **Death animation** — Malware chỉ bị xóa sau khi animation chết phát xong

---

## Asset credits

Sprite assets tải từ [itch.io Game Assets](https://itch.io/game-assets).

---

## Thông tin môn học

| | |
|---|---|
| Sinh viên | Hoàng Lê Kim Lâm |
| MSSV | 25520974 |
| Môn học | IT003.Q21.TTNT — Cấu trúc Dữ liệu và Giải thuật |
| Trường | Đại học Công nghệ Thông tin — ĐHQG TP.HCM (UIT) |

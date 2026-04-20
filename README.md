# Cypher Defense

Game tower defense 2D xây dựng bằng Python + Pygame cho môn **IT003.Q21.TTNT — Cấu trúc Dữ liệu và Giải thuật**, UIT.

> Người chơi là sysadmin Data Center, bảo vệ Server trung tâm khỏi các đợt Malware do Rogue AI điều phối.

---



> Chạy `python main.py` để thử ngay (xem hướng dẫn bên dưới).

---

## Điểm đặc biệt

Toàn bộ cấu trúc dữ liệu và giải thuật được **tự cài đặt từ đầu** trong `core/`, không dùng `heapq`, `collections.deque` hay bất kỳ module DSA nào của Python:

| Cấu trúc dữ liệu | Dùng ở đâu |
|---|---|
| `CustomLinkedList` | `Malware.path` — lưu đường đi từng ô |
| `CustomStack` | `Game.undo_stack` — Ctrl+Z hoàn tác |
| `CustomQueue` | BFS frontier, WaveSpawner |
| `CustomMinHeap` | A* open set, Tower nhắm kẻ gần Server nhất |
| `CustomMaxHeap` | IceWall nhắm kẻ nhiều máu nhất |
| `GridGraph` | Bản đồ lưới trung tâm |
| `A*` | Trojan, Worm tìm đường đến Server |
| `BFS` | Spyware tìm Tower gần nhất |
| `SpatialHash` | Tower dò Malware trong tầm bắn O(1) |

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
│   ├── malware.py               # Malware + Trojan / Worm / Spyware / Ransomware
│   ├── tower.py                 # Tower + BasicNode / IceWall / RadarNode
│   └── projectile.py            # Đạn bay từ Tower đến Malware
│
├── systems/                     ← Hệ thống hỗ trợ
│   └── spatial_hash.py          # SpatialHash — tra cứu Malware trong tầm bắn
│
├── data/
│   └── levels/
│       └── level1.json          # Bản đồ 15×15, cấu hình wave, start_money
│
├── main.py                      ← Entry point — chạy file này
├── game.py                      # Vòng lặp game chính (60 FPS)
├── settings.py                  # Toàn bộ hằng số: màu sắc, stats, FPS...
└── requirements.txt
```

---

## Cài đặt và chạy

### Yêu cầu

- Python 3.10 trở lên
- pip

### Bước 1 — Clone repo

```bash
git clone https://github.com/HoangLeKimLam/cypher_defense.git
cd cypher_defense
```

### Bước 2 — Cài thư viện

```bash
pip install -r requirements.txt
```

### Bước 3 — Chạy game

```bash
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

### Màu sắc trên bản đồ

| Màu | Ý nghĩa |
|---|---|
| Xám đậm | WALL — đặt Tower vào đây |
| Nâu | PATH — Malware đi qua đây |
| Xanh lá | SERVER — bảo vệ mục tiêu này |
| Cam | SPAWN — Malware sinh ra ở đây |
| Đỏ | Trojan |
| Cam nhạt | Worm |
| Tím | Spyware |
| Đỏ thẫm | Ransomware |

---

## Thông tin môn học

| | |
|---|---|
| Sinh viên | Hoàng Lê Kim Lâm |
| MSSV | 25520974 |
| Môn học | IT003.Q21.TTNT — Cấu trúc Dữ liệu và Giải thuật |
| Trường | Đại học Công nghệ Thông tin — ĐHQG TP.HCM (UIT) |

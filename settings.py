# settings.py
# Tất cả hằng số toàn cục của game — không có class, không có logic.
# Mọi file khác đều import từ đây bằng: import settings  hoặc  from settings import ...

# ---------------------------------------------------------------------------
# Màn hình
# ---------------------------------------------------------------------------
# CELL_SIZE: mỗi ô lưới chiếm bao nhiêu pixel.
# Khi vẽ ô (row, col) → pixel_x = col * CELL_SIZE, pixel_y = row * CELL_SIZE
CELL_SIZE = 48

# FPS: số frame mỗi giây. game.py dùng clock.tick(FPS) để giới hạn tốc độ.
FPS = 60

# GRID_ROWS, GRID_COLS: kích thước lưới. Phải khớp với level JSON.
# game.py đọc từ JSON, nhưng giá trị mặc định đặt ở đây để tham khảo.
GRID_ROWS = 15
GRID_COLS = 15

# Kích thước cửa sổ pixel = số ô × kích thước ô.
# Cộng thêm HUD_HEIGHT ở dưới cùng để hiển thị tiền, HP server, wave.
HUD_HEIGHT = 60
SCREEN_WIDTH  = GRID_COLS * CELL_SIZE          # 15 × 48 = 720
SCREEN_HEIGHT = GRID_ROWS * CELL_SIZE + HUD_HEIGHT  # 15 × 48 + 60 = 780

# ---------------------------------------------------------------------------
# Màu sắc — tuple (R, G, B), mỗi giá trị 0–255
# ---------------------------------------------------------------------------
COLOR_BG          = (10,  10,  10)   # nền đen
COLOR_WALL        = (45,  45,  55)   # tường xám đậm
COLOR_PATH        = (120, 110, 90)   # đường đi nâu nhạt
COLOR_SERVER      = (0,   220, 100)  # server xanh lá sáng
COLOR_SPAWN       = (220, 130, 0)    # điểm spawn cam
COLOR_TOWER_BASIC = (60,  130, 220)  # BasicNode xanh dương
COLOR_TOWER_ICE   = (140, 220, 255)  # IceWall xanh nhạt
COLOR_TOWER_RADAR = (180, 100, 255)  # RadarNode tím
COLOR_MALWARE_TROJAN    = (220, 50,  50)   # Trojan đỏ
COLOR_MALWARE_WORM      = (255, 140, 0)    # Worm cam
COLOR_MALWARE_SPYWARE   = (160, 60,  200)  # Spyware tím
COLOR_MALWARE_RANSOMWARE= (180, 20,  20)   # Ransomware đỏ thẫm
COLOR_PROJECTILE  = (255, 255, 100)  # đạn vàng
COLOR_HUD_BG      = (20,  20,  30)   # nền HUD
COLOR_HUD_TEXT    = (220, 220, 220)  # chữ HUD trắng nhạt
COLOR_GRID_LINE   = (30,  30,  40)   # viền ô lưới

# ---------------------------------------------------------------------------
# Tham số Tower
# ---------------------------------------------------------------------------
# Mỗi tower có cost (tiền xây), range (bán kính tấn công tính bằng ô),
# damage (sát thương mỗi phát), fire_rate (phát/giây).

TOWER_BASIC_COST      = 50
TOWER_BASIC_RANGE     = 3     # ô
TOWER_BASIC_DAMAGE    = 25
TOWER_BASIC_FIRE_RATE = 1.0   # phát/giây

TOWER_ICE_COST        = 75
TOWER_ICE_RANGE       = 2
TOWER_ICE_DAMAGE      = 10
TOWER_ICE_FIRE_RATE   = 0.8
TOWER_ICE_SLOW_FACTOR = 0.5   # nhân tốc độ malware khi bị đóng băng
TOWER_ICE_SLOW_DURATION = 2.0 # giây

TOWER_RADAR_COST      = 100
TOWER_RADAR_RANGE     = 5     # range lớn hơn vì chỉ phát hiện, không bắn thẳng
TOWER_RADAR_DAMAGE    = 15
TOWER_RADAR_FIRE_RATE = 1.5

# ---------------------------------------------------------------------------
# Tham số Malware
# ---------------------------------------------------------------------------
MALWARE_TROJAN_HP     = 100
MALWARE_TROJAN_SPEED  = 2.0   # ô/giây
MALWARE_TROJAN_REWARD = 15    # tiền nhận khi tiêu diệt

MALWARE_WORM_HP       = 60
MALWARE_WORM_SPEED    = 3.5
MALWARE_WORM_REWARD   = 10

MALWARE_SPYWARE_HP    = 80
MALWARE_SPYWARE_SPEED = 1.5
MALWARE_SPYWARE_REWARD= 20

MALWARE_RANSOMWARE_HP    = 150
MALWARE_RANSOMWARE_SPEED = 1.0
MALWARE_RANSOMWARE_REWARD= 30

# ---------------------------------------------------------------------------
# Tham số Server & Game
# ---------------------------------------------------------------------------
SERVER_MAX_HP   = 100000   # HP server ban đầu
PROJECTILE_SPEED = 6.0  # ô/giây (dùng khi vẽ animation đạn)

# ---------------------------------------------------------------------------
# SpatialHash
# ---------------------------------------------------------------------------
# SPATIAL_BUCKET_COUNT: số bucket trong hash table.
# Nên là lũy thừa của 2 để phép & nhanh hơn phép %.
SPATIAL_BUCKET_COUNT = 64

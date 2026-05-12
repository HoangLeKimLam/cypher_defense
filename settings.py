# settings.py
# Tất cả hằng số toàn cục của game — không có class, không có logic.
# Mọi file khác đều import từ đây bằng: import settings  hoặc  from settings import ...
import os

# ---------------------------------------------------------------------------
# Âm thanh (Audio)
# ---------------------------------------------------------------------------
AUDIO_ENABLED = True
VOLUME_MUSIC  = 0.3
VOLUME_SFX    = 0.7
AUDIO_PATH    = "data/audio"

# ---------------------------------------------------------------------------
# Màn hình
# ---------------------------------------------------------------------------
# CELL_SIZE: mỗi ô lưới chiếm bao nhiêu pixel.
# Khi vẽ ô (row, col) → pixel_x = col * CELL_SIZE, pixel_y = row * CELL_SIZE
CELL_SIZE = 60
TALL_FACTOR=1.6
# FPS: số frame mỗi giây. game.py dùng clock.tick(FPS) để giới hạn tốc độ.
FPS = 90

# GRID_ROWS, GRID_COLS: kích thước lưới. Phải khớp với level JSON.
# game.py đọc từ JSON, nhưng giá trị mặc định đặt ở đây để tham khảo.
GRID_ROWS = 25
GRID_COLS = 25

# Kích thước cửa sổ pixel = số ô × kích thước ô.
# Cộng thêm HUD_HEIGHT ở dưới cùng để hiển thị tiền, HP server, wave.
HUD_HEIGHT = 60
SCREEN_WIDTH  = 1920  # Fullscreen width - larger than map for camera panning
SCREEN_HEIGHT = 1080  # Fullscreen height (includes HUD at bottom)

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
COLOR_MALWARE_LIGHTSPY  = (100, 200, 255)  # LightSpy xanh dương (lightning)
COLOR_MALWARE_RANSOMWARE= (180, 20,  20)   # Ransomware đỏ thẫm
COLOR_MALWARE_RIPOSTEWARE= (200, 100, 200)  # RiposteWare tím (phản đạn)
COLOR_PROJECTILE  = (255, 255, 100)  # đạn vàng
COLOR_HUD_BG      = (20,  20,  30)   # nền HUD
COLOR_HUD_TEXT    = (220, 220, 220)  # chữ HUD trắng nhạt
COLOR_GRID_LINE   = (30,  30,  40)   # viền ô lưới
COLOR_HP_FULL     = (50,  220, 80)   # HP bar xanh lá (đầy)
COLOR_HP_EMPTY    = (60,  20,  20)   # HP bar nền đỏ sẫm (rỗng)

# ---------------------------------------------------------------------------
# Tham số Tower
# ---------------------------------------------------------------------------
# Mỗi tower có cost (tiền xây), range (bán kính tấn công tính bằng ô),
# damage (sát thương mỗi phát), fire_rate (phát/giây).

TOWER_BASIC_COST      = 50
TOWER_BASIC_RANGE     = 5     # ô
TOWER_BASIC_DAMAGE    = 30
TOWER_BASIC_FIRE_RATE = 1.0   # phát/giây

TOWER_ICE_COST        = 75
TOWER_ICE_RANGE       = 5
TOWER_ICE_DAMAGE      = 20
TOWER_ICE_FIRE_RATE   = 0.8
TOWER_ICE_SLOW_FACTOR = 0.7   # nhân tốc độ malware khi bị đóng băng
TOWER_ICE_SLOW_DURATION = 2.0 # giây

TOWER_RADAR_COST      = 100
TOWER_RADAR_RANGE     = 5     # range lớn hơn vì chỉ phát hiện, không bắn thẳng
TOWER_RADAR_DAMAGE    = 15
TOWER_RADAR_FIRE_RATE = 1.5

TOWER_FIRE_COST       = 80
TOWER_FIRE_RANGE      = 6
TOWER_FIRE_DAMAGE     = 70
TOWER_FIRE_FIRE_RATE  = 1.0
TOWER_FIRE_DURATION   = 3.0   # Thời gian vết lửa tồn tại (giây)
FIRE_DAMAGE_PER_SEC   = 5     # Sát thương/giây từ vết lửa

TOWER_POISON_COST     = 120
TOWER_POISON_RANGE    = 10     # Giữ y RadarNode
TOWER_POISON_DAMAGE   = 3    # Sát thương mỗi lần check (nằm trong vùng = dính dame)
TOWER_POISON_FIRE_RATE= 1.0   # Check 1 lần/giây
TOWER_POISON_HP       = 80

TOWER_SPREAD_COST     = 100
TOWER_SPREAD_RANGE    = 10
TOWER_SPREAD_DAMAGE   = 30
TOWER_SPREAD_FIRE_RATE= 1.0
TOWER_SPREAD_SLOW_FACTOR = 0.7
TOWER_SPREAD_SLOW_DURATION = 2.0
TOWER_SPREAD_SLOW_RANGE = 3   # Bán kính lan slow

TOWER_SPEED_COST      = 70
TOWER_SPEED_RANGE     = 6
TOWER_SPEED_DAMAGE    = 10
TOWER_SPEED_FIRE_RATE = 5 

TOWER_SNIPER_COST     = 90
TOWER_SNIPER_RANGE    = 8
TOWER_SNIPER_DAMAGE   = 100
TOWER_SNIPER_FIRE_RATE= 0.25   # Chậm nhưng sát thương cao

TOWER_FREEZE_COST     = 95
TOWER_FREEZE_DAMAGE   = 30
TOWER_FREEZE_SLOW_DURATION = 5.0   # Đóng băng (slow_factor=0.0)

# ---------------------------------------------------------------------------
# Tham số Malware
# ---------------------------------------------------------------------------
MALWARE_TROJAN_HP     = 200
MALWARE_TROJAN_SPEED  = 2.0   # ô/giây
MALWARE_TROJAN_REWARD = 20    # tiền nhận khi tiêu diệt

MALWARE_WORM_HP       = 150
MALWARE_WORM_SPEED    = 4
MALWARE_WORM_REWARD   = 15

MALWARE_SPYWARE_HP    = 200
MALWARE_SPYWARE_SPEED = 1.5
MALWARE_SPYWARE_REWARD= 20

MALWARE_LIGHTSPY_HP    = 250
MALWARE_LIGHTSPY_SPEED = 1.5
MALWARE_LIGHTSPY_REWARD= 20

MALWARE_RANSOMWARE_HP    = 350
MALWARE_RANSOMWARE_SPEED = 1.0
MALWARE_RANSOMWARE_REWARD= 35
MALWARE_TROJAN_ATTACK_DAMAGE    = 10    # server dame/đòn
MALWARE_TROJAN_ATTACK_SPEED     = 1
MALWARE_WORM_ATTACK_DAMAGE      = 10
MALWARE_WORM_ATTACK_SPEED       = 2
MALWARE_SPYWARE_ATTACK_DAMAGE   = 15   # mạnh vs tháp
MALWARE_SPYWARE_ATTACK_SPEED    = 1.0
MALWARE_LIGHTSPY_ATTACK_DAMAGE  = 12   # cao hơn Spyware (shock spread)
MALWARE_LIGHTSPY_ATTACK_SPEED   = 1.5
MALWARE_RANSOMWARE_ATTACK_DAMAGE= 50
MALWARE_RANSOMWARE_ATTACK_SPEED = 0.25
# ---------------------------------------------------------------------------
# Tham số Server & Game
# ---------------------------------------------------------------------------
SERVER_MAX_HP   = 1000   # HP server ban đầu
# ---------------------------------------------------------------------------
# Tham số Tower
# ---------------------------------------------------------------------------
PROJECTILE_SPEED = 6.0  # ô/giây (dùng khi vẽ animation đạn)
TOWER_BASIC_HP = 200
TOWER_ICE_HP = 150
TOWER_RADAR_HP = 70
TOWER_FIRE_HP = 170
TOWER_SPEED_HP = 150
TOWER_SNIPER_HP = 170
TOWER_SPREAD_HP = 150
TOWER_FREEZE_HP = 150

# ---------------------------------------------------------------------------
# Tham số Bomb
# ---------------------------------------------------------------------------
BOMB_HP = 150
BOMB_TIMER = 5  # Thời gian phát nổ tự động (giây)
BOMB_DAMAGE_TO_SERVER = 100  # Sát thương server khi bomb nổ
BOMB_STUN_DURATION = 5  # Thời gian choáng tháp (giây)

# ---------------------------------------------------------------------------
# Tham số Wall (Tường)
# ---------------------------------------------------------------------------
WALL_DURATION = 10.0  # Thời gian tồn tại tường (giây)
WALL_COOLDOWN = 10.0   # Cooldown giữa các lần đặt tường (giây)

# ---------------------------------------------------------------------------
# Tham số Boss
# ---------------------------------------------------------------------------
# FireWorm - Boss Level 1
FIREWORM_HP = 1000
FIREWORM_SPEED = 1.2
FIREWORM_ATTACK_DAMAGE_TOWER = 15
FIREWORM_ATTACK_DAMAGE_SERVER = 30
FIREWORM_ATTACK_SPEED = 0.8  # Tấn công server mỗi 1.25 giây
FIREWORM_ATTACK_RANGE = 3  # Phạm vi quét tháp (ô)
FIREWORM_DURATION_ATTACK_TOWER = 2.0  # Mỗi 2 giây quét một lần tháp
FIREWORM_FIRE_SPREAD_RANGE = 2  # Phạm vi lan cháy sang tường (ô)
FIREWORM_BURN_DAMAGE_PER_SEC = 5  # Sát thương đốt mỗi giây
FIREWORM_BURN_DURATION = 3.0  # Thời gian hiệu ứng đốt (giây)
FIREWORM_REWARD = 100  # Tiền nhận khi tiêu diệt

# FlyingDemon - Boss Level 2
FLYINGDEMON_HP = 1000
FLYINGDEMON_SPEED = 1.5
FLYINGDEMON_ATTACK_DAMAGE_SERVER = 100
FLYINGDEMON_ATTACK_SPEED = 0.5  # Tấn công server mỗi 2 giây
FLYINGDEMON_REWARD = 150
# Bomb-related
FLYINGDEMON_BOMB_DURATION = 8.0  # Mỗi 4 giây drop 1 bomb
FLYINGDEMON_BOMB_NORMAL_DAMAGE = 150  # Sát thương bomb bình thường
FLYINGDEMON_BOMB_ATOMIC_DAMAGE = 10000  # Sát thương atomic bomb (thua game)
FLYINGDEMON_BOMB_ATOMIC_CHANCE = 0.2  # 25% chance drop atomic bomb
FLYINGDEMON_BOMB_EXPLODE_MIN = 5.0  # Min thời gian nổ (s)
FLYINGDEMON_BOMB_EXPLODE_MAX = 8.0  # Max thời gian nổ (s)
FLYINGDEMON_BOMB_STUN_DURATION = 4.0  # Thời gian stun tháp

# ==================== WAVE COOLDOWN ====================
PRE_WAVE_DURATION = 10.0
# ---------------------------------------------------------------------------
# SpatialHash
# ---------------------------------------------------------------------------
# SPATIAL_BUCKET_COUNT: số bucket trong hash table.
# Nên là lũy thừa của 2 để phép & nhanh hơn phép %.
SPATIAL_BUCKET_COUNT = 64

# ---------------------------------------------------------------------------
# UI / Animation
# ---------------------------------------------------------------------------
ANIM_FPS        = 8    # malware walk animation frames per second
PORTAL_ANIM_FPS = 10   # portal swirl speed (frames/sec)
SERVER_ANIM_FPS = 2    # server pulse speed (slow)

# Map tileset — neo_zero_tiles_and_buildings_01.png (10×10 grid, 32px tiles)
# Điều chỉnh MAP_WALL_TILE / MAP_PATH_TILE (row, col) nếu tile trông không đúng
MAP_TILE_SIZE  = 32
MAP_WALL_TILE  = (0, 0)   # (row, col) tile dùng cho tường
MAP_PATH_TILE  = (0, 5)   # (row, col) tile dùng cho đường đi

# Malware sprite lớn hơn cell để tạo hiệu ứng depth overlap
SPRITE_SCALE   = 1.35     # 1.0 = vừa cell, 1.35 = 35% lớn hơn (malware)
TOWER_SCALE    = 3     # tower sprite size multiplier (lớn hơn malware để trông oai hơn)
TALL_FACTOR    = 1.5     # wall height multiplier for pseudo-3D look

# ---------------------------------------------------------------------------
# Dynamic Resolution Helper
# ---------------------------------------------------------------------------
def calculate_resolution_and_cell_size():
    """
    Tính toán SCREEN_WIDTH, SCREEN_HEIGHT, CELL_SIZE dựa trên resolution thực tế.
    
    Returns:
        tuple: (screen_width, screen_height, cell_size)
    
    Logic:
    - CELL_SIZE = min(
        screen_width / GRID_COLS,
        (screen_height - HUD_HEIGHT) / GRID_ROWS
      )
    - Đảm bảo map vừa khít màn hình mà không bị cắt
    """
    import pygame
    
    # Lấy resolution thực tế (fullscreen native)
    pygame.init()
    info = pygame.display.Info()
    screen_width = info.current_w
    screen_height = info.current_h
    
    # Tính CELL_SIZE để grid vừa khít
    max_cell_width = screen_width / GRID_COLS
    max_cell_height = (screen_height - HUD_HEIGHT) / GRID_ROWS
    cell_size = int(min(max_cell_width, max_cell_height))
   
    # Đảm bảo minimum 100px/cell, maximum 200px/cell
    #cell_size = max(60, min(200, cell_size))
    
    return screen_width, screen_height, 1.5*cell_size

# ===== INITIALIZE: Tính toán resolution ngay lập tức khi import settings =====
# Điều này đảm bảo SCREEN_WIDTH, SCREEN_HEIGHT, CELL_SIZE được set đúng TRƯỚC
# khi bất kỳ code nào khác access chúng (main.py, entities, etc.)
_w, _h, _cs = calculate_resolution_and_cell_size()
SCREEN_WIDTH = _w
SCREEN_HEIGHT = _h
CELL_SIZE = _cs

print(f"[SETTINGS] Auto-detected resolution: {SCREEN_WIDTH}×{SCREEN_HEIGHT}, CELL_SIZE: {CELL_SIZE}px")

# ---------------------------------------------------------------------------
# Tower / Upgrade unlock level
# ---------------------------------------------------------------------------
# Mỗi key (tên class tower hoặc node_id upgrade) chỉ được dùng từ màn đó trở đi.
UNLOCK_LEVEL: dict[str, int] = {
    # Màn 1 — BasicNode + IceWall và tầng 1 của chúng
    "BasicNode":              1,
    "IceWall":                1,
    "basic_damage_up_1":      1,
    "basic_speed_up_1":       1,
    "ice_range_up_1":         1,
    "ice_slow_duration_up_1": 1,
    # Màn 2 — SpeedNode, SpreadNode
    "SpeedNode":              2,
    "speed_upgrade":          2,
    "SpreadNode":             2,
    "spread_upgrade":         2,
    # Màn 3 — RadarNode, FireNode
    "RadarNode":              3,
    "radar_range_up_1":       3,
    "FireNode":               3,
    "fire_upgrade":           3,
    # Màn 4 — PoisonNode, FreezeNode
    "PoisonNode":             4,
    "poison_upgrade":         4,
    "FreezeNode":             4,
    "freeze_upgrade":         4,
    # Màn 5 — SniperNode
    "SniperNode":             5,
    "sniper_upgrade":         5,
}

SOUNDS = {
    "music_game":  "background.ogg",
    "explosion":   "explosion.wav",
    "firenode":    "firenode.wav",
    "freezenode":  "freezenode.wav",
    "spreadnode":  "spreadnode.wav",
    "warning":     "warning.wav",
}

def is_tower_unlocked(key: str, current_level: int) -> bool:
    """Trả về True nếu tower/node đã được mở khóa ở level hiện tại."""
    return UNLOCK_LEVEL.get(key, 1) <= current_level

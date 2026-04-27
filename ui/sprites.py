"""
ui/sprites.py — Load sprite từ file ảnh thực, fallback procedural nếu thiếu.
"""
import pygame
import os
import math
import settings

_cache: dict = {}
BASE = "data/sprites"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init() -> None:
    """Pre-load toàn bộ sprites. Gọi sau pygame.init()."""
    cs       = settings.CELL_SIZE
    spr_size = int(cs * settings.SPRITE_SCALE)  # malware size
    twr_size = int(cs * settings.TOWER_SCALE)   # tower/server/portal — to và oai hơn
    blt_size = max(10, cs // 4)

    # --- Map tiles ---
    _load_map_tiles(cs)

    # --- Tower ---
    _cache["tower_basic"] = _img(f"{BASE}/tower/BasicNode/Sniper Tower.png",   twr_size, twr_size)
    _cache["tower_ice"]   = _img(f"{BASE}/tower/IceWall/Base Spirit Tower.png", twr_size, twr_size)
    _cache["tower_radar"] = _img(f"{BASE}/tower/RadarNode/Posion Tower.png",    twr_size, twr_size)

    # --- Projectile ---
    _cache["proj_basic"] = _img(f"{BASE}/tower/BasicNode/Regular Bullet.png", blt_size, blt_size)
    _cache["proj_ice"]   = _img(f"{BASE}/tower/IceWall/Magic Bullet.png",     blt_size, blt_size)
    _cache["proj_radar"] = _proc_proj(5, (200, 100, 255), (240, 180, 255))

    # --- Portal spawn ---
    _cache["spawn"] = _sheet(f"{BASE}/portal/Portal_100x100px.png",
                              100, 100, max_frames=14, target=(twr_size, twr_size))

    # --- Server (4 frame pulse) ---
    base_srv = _img(f"{BASE}/server/Mage Tower.png", twr_size, twr_size)
    _cache["server"] = [_pulse_tint(base_srv, i) for i in range(4)]

    # --- Trojan (Mushroom sprite sheets, 80×64 mỗi frame) ---
    trojan_size = int(spr_size * 1.8)  # Trojan bigger than basic malware
    trojan_t = (trojan_size, trojan_size)
    _trojan_actions = {
        "Run": 8,
        "Idle": 7,
        "Attack": 10,
        "Hit": 5,
        "Die": 15,
        "Stun": 18,
        "AttackWithStun": 24,
    }
    for action, frame_count in _trojan_actions.items():
        path = f"{BASE}/malware/Trojan/Mushroom-{action}.png"
        frames = _sheet(path, 80, 64, max_frames=frame_count, target=trojan_t)
        _cache[f"trojan_{action}"] = frames

    # Fallback sprite
    _cache["trojan"] = _cache.get("trojan_Run", [pygame.Surface((trojan_size, trojan_size))])

    # --- Malware khác (64×16 → 4 frame 16×16) ---
    for key, fname in [("spyware",    "Spyware/FloatingEye.png"),
                       ("ransomware", "Ransomware/FoulGouger.png")]:
        _cache[key] = _sheet(f"{BASE}/malware/{fname}",
                              16, 16, target=(spr_size, spr_size))

    # --- Worm / Plant3 (64×64 mỗi frame, 4 hướng: up/down/left/right) ---
    worm_size = int(spr_size * 1.8)  # Worm bigger than other malware
    worm_t = (worm_size, worm_size)
    _worm_action_frames = {"Walk": 6, "Run": 8, "Attack": 7, "Idle": 4, "Death": 10, "Hurt": 5}
    _worm_directions = ["up", "down", "left", "right"]

    for action, n in _worm_action_frames.items():
        path = f"{BASE}/malware/Worm/Plant3/{action}/Plant3_{action}_full.png"
        # Load sheet (64×64 mỗi frame, 8 cột × 4 dòng)
        all_frames = _sheet(path, 64, 64, max_frames=n*4, target=worm_t)

        # Chia thành 4 hướng
        for dir_idx, direction in enumerate(_worm_directions):
            start = dir_idx * n
            end = start + n
            _cache[f"worm_{action}_{direction}"] = all_frames[start:end] if len(all_frames) >= end else all_frames

        # Fallback
        _cache[f"worm_{action}"] = _cache.get(f"worm_{action}_right", all_frames[:n])

    _cache["worm"] = _cache.get("worm_Run_right", [pygame.Surface((spr_size, spr_size))])

    # --- TrojanRanged (Enemy3, 1 hướng right, multiple actions) ---
    # Mỗi frame là 64x64px
    trojan_ranged_size = int(spr_size * 1.5)  # Bigger than normal malware
    tr_size = (trojan_ranged_size, trojan_ranged_size)
    _trojan_ranged_actions = {
        "Fly": 8,               # 512x64 → 8 frames of 64x64
        "AttackSmashStart": 12, # 768x64 → 12 frames of 64x64
        "AttackSmashLoop": 3,   # 192x64 → 3 frames of 64x64
        "Hit": 4,               # 256x64 → 4 frames of 64x64
        "Death": 13,            # 1088x64 → ~13 frames of 64x64
    }

    for action, frame_count in _trojan_ranged_actions.items():
        path = f"{BASE}/malware/TrojanRanged/Enemy3-{action}.png"
        frames = _sheet(path, 64, 64, max_frames=frame_count, target=tr_size)
        _cache[f"trojan_ranged_{action}"] = frames

    # Fallback sprite
    _cache["trojan_ranged"] = _cache.get("trojan_ranged_Fly", [pygame.Surface((trojan_ranged_size, trojan_ranged_size))])


def get(name: str):
    """Lấy sprite đã load từ cache theo tên key.

    Args:
        name (str): Tên sprite key (vd. "trojan_Run", "tower_basic", "proj_ice").

    Returns:
        pygame.Surface | list[pygame.Surface] | None:
            Surface đơn (tower, projectile), list frame (animated sprite),
            hoặc None nếu key không tồn tại trong cache.
    """
    return _cache.get(name)


def action_frame_count(key: str) -> int:
    """Trả về số frame của một sprite key trong cache.

    Args:
        key (str): Tên sprite key cần kiểm tra.

    Returns:
        int: Số frame nếu key tồn tại và là list. 4 nếu không tìm thấy (fallback mặc định).
    """
    frames = _cache.get(key)
    return len(frames) if frames else 4


# ---------------------------------------------------------------------------
# Helpers: image loading
# ---------------------------------------------------------------------------

def _img(path: str, w: int, h: int) -> pygame.Surface:
    """Load và scale một ảnh đơn từ file. Trả về placeholder màu magenta nếu lỗi.

    Args:
        path (str): Đường dẫn file ảnh (PNG/JPG).
        w (int): Chiều rộng đích sau khi scale (pixel).
        h (int): Chiều cao đích sau khi scale (pixel).

    Returns:
        pygame.Surface: Surface đã scale đúng kích thước (w × h).
            Surface magenta bán trong suốt (200, 0, 200, 160) nếu file không tìm thấy.
    """
    try:
        return pygame.transform.scale(
            pygame.image.load(path).convert_alpha(), (w, h)
        )
    except Exception:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((200, 0, 200, 160))
        return s


def _sheet(path: str, fw: int, fh: int,
           max_frames: int = 999,
           target: tuple = None) -> list:
    """Slice spritesheet thành danh sách frame Surface, tùy chọn scale.

    Đọc ảnh spritesheet và cắt thành các frame theo kích thước fw × fh.
    Frame đi từ trái sang phải, trên xuống dưới.

    Args:
        path (str): Đường dẫn file spritesheet.
        fw (int): Chiều rộng mỗi frame trong sheet (pixel).
        fh (int): Chiều cao mỗi frame trong sheet (pixel).
        max_frames (int): Số frame tối đa cần lấy. Mặc định 999 (lấy tất cả).
        target (tuple | None): (w, h) kích thước đích sau khi scale.
            None = giữ nguyên kích thước gốc fw × fh.

    Returns:
        list[pygame.Surface]: Danh sách frame Surface đã scale (nếu có target).
            List chứa 1 placeholder magenta nếu file không tìm thấy.
    """
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except Exception:
        dummy = pygame.Surface(target or (fw, fh), pygame.SRCALPHA)
        dummy.fill((200, 0, 200, 160))
        return [dummy]

    cols   = max(1, sheet.get_width()  // fw)
    rows   = max(1, sheet.get_height() // fh)
    count  = min(cols * rows, max_frames)
    frames = []
    for i in range(count):
        col  = i % cols
        row  = i // cols
        sub  = sheet.subsurface(pygame.Rect(col * fw, row * fh, fw, fh))
        if target:
            sub = pygame.transform.scale(sub, target)
        frames.append(sub)
    return frames or [pygame.Surface(target or (fw, fh), pygame.SRCALPHA)]


def _pulse_tint(base: pygame.Surface, frame: int) -> pygame.Surface:
    """Tạo hiệu ứng glow pulse nhẹ cho server sprite theo frame number.

    Args:
        base (pygame.Surface): Surface gốc của server sprite.
        frame (int): Chỉ số frame (0-3) — xác định cường độ glow theo sin.

    Returns:
        pygame.Surface: Bản sao của base với lớp tint cyan nhạt đè lên.
            Cường độ tint dao động theo sin(frame × π/2).
    """
    s     = base.copy()
    pulse = int(abs(math.sin(frame * math.pi / 2)) * 35)
    tint  = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    tint.fill((0, pulse, pulse // 2, 0))
    s.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return s


# ---------------------------------------------------------------------------
# Map tiles
# ---------------------------------------------------------------------------
PATH_FILES = ["Screenshot 2026-04-22 014150.png", "Screenshot 2026-04-22 014317.png"] 
WALL_FILES = ["Screenshot 2026-04-22 014353.png","Screenshot 2026-04-22 014438.png", "Screenshot 2026-04-22 014510.png"]
def _load_map_tiles(cs: int) -> None:
    """Load tile ảnh cho PATH và WALL từ thư mục data/sprites/Map/.

    Xử lý ảnh PATH (2 biến thể, overlay tối nhẹ) và WALL (3 biến thể,
    tạo hiệu ứng pseudo-3D bằng cách kéo dài thân tường theo TALL_FACTOR).
    Kết quả lưu vào _cache["path"] và _cache["wall"].

    Args:
        cs (int): Kích thước ô lưới (pixel) — settings.CELL_SIZE.

    Side effects:
        - Lưu list Surface vào _cache["path"] và _cache["wall"].
        - Nếu load thất bại → lưu list Surface trống làm fallback.

    Note:
        Gọi bởi init() sau pygame.display.set_mode() để convert_alpha() hoạt động.
        TALL_FACTOR (settings) xác định chiều cao thân tường so với cs.
    """
    try:
        # --- 1. XỬ LÝ PATH (2 ảnh, trọng số ngang nhau 50-50) ---
        path_variants = []
        for f_name in PATH_FILES:
            full_path = os.path.join(BASE, "Map", f_name)
            img = pygame.image.load(full_path).convert_alpha()
            img = pygame.transform.scale(img, (cs, cs))
            
            dark = pygame.Surface((cs, cs))
            dark.fill((20, 18, 28))
            dark.set_alpha(80)
            img.blit(dark, (0, 0))
            
            path_variants.append(img)
        wall_variants = []
        for f_name in WALL_FILES:
            if f_name == "Screenshot 2026-04-22 014510.png": 
                r=130
                g=10
                b=10
                b_r=150
                b_g=15
                b_b=15
            else:
                r=15
                g=15
                b=25
                b_r=30
                b_g=35
                b_b=50
                
            full_walls = os.path.join(BASE, "Map", f_name)
            
            w_img = pygame.image.load(full_walls).convert_alpha()
            w_img = pygame.transform.scale(w_img, (cs, cs))
        
            tall_h = int(cs * settings.TALL_FACTOR)
            body_h = tall_h - cs
            tall_wall = pygame.Surface((cs, tall_h), pygame.SRCALPHA)
        
            # --- CÁCH MỚI: DÙNG TEXTURE CỦA ẢNH GỐC LÀM THÂN TƯỜNG ---
            
            # Bước 1: Cắt lấy 2 pixel ở vị trí dưới cùng của ảnh nóc (Ảnh gốc)
            bottom_slice = pygame.Rect(0, cs - 20, cs, 20)
            wall_texture = w_img.subsurface(bottom_slice).copy()
            
            # Bước 2: Kéo giãn phần đã cắt xuống bằng chiều cao của thân tường
            wall_body = pygame.transform.scale(wall_texture, (cs, body_h))
            
            # Bước 3: Tạo một lớp màng tối (Overlay) trong suốt
            dark_overlay = pygame.Surface((cs, body_h), pygame.SRCALPHA)
            dark_overlay.fill((r, g, b, 180)) # Đặt Alpha khoảng 180-220 để thấy vân gạch bên dưới
            
            # Bước 4: Phủ lớp màng tối lên thân tường và vẽ viền
            wall_body.blit(dark_overlay, (0, 0))
            pygame.draw.rect(wall_body, (b_r, b_g, b_b, 200), [0, 0, cs, body_h], 1) # Viền khối
        
            # Bước 5: Lắp ghép thân và nóc vào khuôn tổng
            tall_wall.blit(wall_body, (0, cs)) # Thân dưới
            tall_wall.blit(w_img, (0, 0))
            
           
            wall_variants.append(tall_wall)

        # Lưu danh sách vào cache
        _cache["wall"] = wall_variants
        _cache["path"] = path_variants

    except Exception as e:
        print(f"Error loading sprite images: {e}")
        # Fallback nếu lỗi file
        _cache["wall"] = [pygame.Surface((cs, cs))] # Tạo mặt phẳng trống tạm thời
        _cache["path"] = [pygame.Surface((cs, cs))]
def _wall_proc(cs: int) -> pygame.Surface:
    """Tạo procedural wall tile màu xanh đậm làm fallback khi thiếu ảnh.

    Args:
        cs (int): Kích thước ô lưới (pixel).

    Returns:
        pygame.Surface: Surface cs × cs với pattern đường kẻ và vòng tròn trung tâm.
    """
    s   = pygame.Surface((cs, cs))
    mid = cs // 2
    s.fill((12, 52, 62))
    pygame.draw.rect(s, (18, 68, 80), (2, 2, cs-4, cs-4))
    c1, c2 = (0, 155, 175), (0, 200, 220)
    for dx, dy in [(0,-1),(0,1),(-1,0),(1,0)]:
        pygame.draw.line(s, c1, (mid+dx*4, mid+dy*4),
                         (mid+dx*(mid-3), mid+dy*(mid-3)), 1)
    for cx, cy in [(4,4),(cs-5,4),(4,cs-5),(cs-5,cs-5)]:
        pygame.draw.circle(s, c2, (cx, cy), 2)
    pygame.draw.circle(s, (0,120,140), (mid, mid), 5)
    pygame.draw.circle(s, c2,          (mid, mid), 3)
    pygame.draw.rect(s, (28, 95, 110), (0, 0, cs, cs), 1)
    return s


def _path_proc(cs: int) -> pygame.Surface:
    """Tạo procedural path tile màu tím đậm với grid lines làm fallback.

    Args:
        cs (int): Kích thước ô lưới (pixel).

    Returns:
        pygame.Surface: Surface cs × cs với lưới kẻ mờ trên nền tím đậm.
    """
    s    = pygame.Surface((cs, cs))
    grid = (44, 39, 56)
    s.fill((32, 28, 42))
    step = max(8, cs // 5)
    for i in range(0, cs+1, step):
        pygame.draw.line(s, grid, (i, 0), (i, cs), 1)
        pygame.draw.line(s, grid, (0, i), (cs, i), 1)
    return s


# ---------------------------------------------------------------------------
# Procedural projectile fallback
# ---------------------------------------------------------------------------

def _proc_proj(radius: int, inner: tuple, outer: tuple) -> pygame.Surface:
    """Tạo procedural projectile sprite hình tròn glow làm fallback.

    Args:
        radius (int): Bán kính lõi đạn (pixel).
        inner (tuple): Màu RGB lõi trong (vd. (200, 100, 255)).
        outer (tuple): Màu RGBA vòng ngoài glow (vd. (240, 180, 255)).

    Returns:
        pygame.Surface: Surface vuông (radius*3) × (radius*3) với SRCALPHA,
            vẽ vòng ngoài mờ và lõi sáng ở trung tâm.
    """
    size = radius * 3
    s    = pygame.Surface((size, size), pygame.SRCALPHA)
    mid  = size // 2
    pygame.draw.circle(s, (*outer, 80), (mid, mid), radius)
    pygame.draw.circle(s, inner,        (mid, mid), max(1, radius-2))
    return s

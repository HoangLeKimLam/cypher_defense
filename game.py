# game.py
# Lớp Game — trái tim của toàn bộ chương trình.
# Kết nối tất cả hệ thống: GridGraph, Malware, Tower, Projectile, SpatialHash.
# main.py chỉ làm một việc: tạo Game() và gọi game.run().

import json
import random
import time
import pygame

import settings
import ui.sprites as sprites
from core.graph import GridGraph, Celltype
from core.data_structures import CustomStack, CustomQueue
from entities.malware import Malware, Trojan, Worm, WormPoison, Spyware, SlowSpy, LightSpy, LightSpy_Ranged, Ransomware, VaultWare, RiposteWare, TrojanRanged, Spyware_Ranged, SlowSpy_Ranged
from entities.tower import Tower, BasicNode, IceWall, RadarNode, SpeedNode, FireNode, SniperNode, FreezeNode, SpreadNode, PoisonNode
from entities.projectile import Projectile, MalwareProjectile
from entities.server import Server
from entities.bomb import Bomb
from entities.wall import Wall
from entities.fire_mark import FireMark
from entities.shock_effect import ShockEffect
from entities.boss import Boss, FireWorm, FlyingDemon, RiposteBoss, Shadow, Final
from systems.spatial_hash import SpatialHash
from systems.upgrade_tree import create_basic_upgrade_tree, create_ice_upgrade_tree, create_radar_upgrade_tree
from ui.upgrade_menu import UpgradeMenu
from ui.right_panel import RightPanel
from systems.audio import audio_manager


# Ánh xạ chuỗi từ JSON → class Malware tương ứng
MALWARE_FACTORY = {
    "trojan":     Trojan,
    "trojan_ranged": TrojanRanged,
    "worm":       Worm,
    "worm_poison": WormPoison,
    "spyware":    Spyware,
    "spyware_ranged": Spyware_Ranged,
    "slowspy":    SlowSpy,
    "slowspy_ranged": SlowSpy_Ranged,
    "lightspy":   LightSpy,
    "lightspy_ranged": LightSpy_Ranged,
    "ransomware": Ransomware,
    "vaultware":  VaultWare,
    "riposteware": RiposteWare,
}

# Ánh xạ chuỗi từ JSON → class Boss tương ứng
BOSS_FACTORY = {
    "fireworm": FireWorm,
    "flyingdemon": FlyingDemon,
    "riposteboss": RiposteBoss,
    "shadow": Shadow,
    "final": Final,
}

# Ánh xạ phím số → class Tower (1=BasicNode, 2=IceWall, 3=RadarNode)
TOWER_FACTORY = {
    pygame.K_1: BasicNode,
    pygame.K_2: IceWall,
    pygame.K_3: RadarNode,
}


class Game:
    """Lớp điều phối toàn bộ vòng đời game — khởi tạo, cập nhật, và vẽ.

    Là điểm kết nối duy nhất giữa tất cả hệ thống: GridGraph, Malware, Tower,
    Projectile, SpatialHash. main.py chỉ cần: Game().run().

    Attributes:
        screen (pygame.Surface): Cửa sổ game kích thước SCREEN_WIDTH × SCREEN_HEIGHT.
        clock (pygame.time.Clock): Đồng hồ giới hạn FPS và cung cấp dt.
        running (bool): False → thoát vòng lặp run().
        game_over (bool): True → server bị phá, dừng update(), hiện "GAME OVER".
        victory (bool): True → hết tất cả wave, dừng update(), hiện "YOU WIN!".
        selected_tower (class): Loại tower đang chọn (BasicNode/IceWall/RadarNode).
        config (dict): Dữ liệu JSON của level hiện tại.
        graph (GridGraph): Bản đồ lưới — CellType, pathfinding, spawn weights.
        spatial_hash (SpatialHash): Tra cứu malware trong tầm bắn.
        server (Server): Mục tiêu chính — có HP, animation, vẽ được.
        malwares (list[Malware]): Tất cả malware đang sống trên map.
        towers (list[Tower]): Tất cả tower đã xây.
        projectiles (list[Projectile]): Tất cả đạn đang bay.
        undo_stack (CustomStack): Lịch sử xây tower để Ctrl+Z. Mỗi entry:
            {"pos": (row,col), "tower": Tower, "cost": int}.
        money (int): Tiền hiện tại của người chơi.
        wave_index (int): Chỉ số wave đang chạy (0-based, tính từ config["waves"]).
        spawn_queue (CustomQueue): Tên malware cần spawn trong wave hiện tại.
        spawn_timer (float): Đếm ngược (giây) đến lần spawn tiếp theo.
        spawn_interval (float): Khoảng cách giữa hai lần spawn (giây), từ JSON.
        font (pygame.font.Font): Font monospace 18px cho HUD.
        font_big (pygame.font.Font): Font monospace 36px cho màn hình kết thúc.

    Usage::

        game = Game()
        game.run()   # vòng lặp chính — block cho đến khi thoát
    """

    def __init__(self, level: int = 1, screen=None, managed=False):
        """Khởi tạo Game instance với screen được truyền từ GameManager.

        Args:
            level (int): Level number to load (default 1)
            screen: pygame.Surface được tạo từ GameManager (required)
            managed (bool): True nếu được quản lý bởi GameManager (không xử lý ESC)

        Side effects:
            - Gọi sprites.init() để load sprites nếu chưa initialized
            - Gọi self.load_level(level) để nạp bản đồ
        """
        if screen is None:
            pygame.init()
            
            # Resolution đã được auto-detected trong settings.py
            # Tạo window với size được calculate động
            print(f"[GAME] Creating window: {settings.SCREEN_WIDTH}×{settings.SCREEN_HEIGHT}")
            
            self.screen = pygame.display.set_mode(
                (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
            )
            pygame.display.set_caption("Cypher Defense - Press ESC to exit")
        else:
            self.screen = screen

        self.managed = managed  # True nếu được quản lý bởi GameManager
        sprites.init()   # phải sau set_mode() để convert_alpha() hoạt động
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_over = False
        self.victory = False

        self.selected_tower = BasicNode
        self.wall_placement_mode = False
        self.wall_cooldown_timer = 0.0

        # Camera system for scrolling map
        self.camera_x = 0.0  # Pixel offset of camera (left edge)
        self.camera_y = 0.0  # Pixel offset of camera (top edge)
        self.camera_speed = 300.0  # Pixels per second (WASD panning)

        # Animation timers (visual only)
        self._portal_timer = 0.0
        self._portal_frame = 0

        self.load_level(level)
        pass

    def load_level(self, level_num: int):
        """Đọc file JSON và khởi tạo toàn bộ trạng thái game cho level đó.

        Args:
            level_num (int): Số level cần load (1–5). File tương ứng:
                data/levels/level{level_num}.json.

        Side effects:
            - Đọc và parse JSON vào self.config.
            - Tạo GridGraph từ config["grid"], config["rows"], config["cols"].
            - Khởi tạo SpatialHash với kích thước map thực tế từ JSON.
            - Reset tất cả danh sách: malwares, towers, projectiles, undo_stack.
            - Đặt lại money và server_hp theo config và settings.
            - Gọi _start_wave(0) để bắt đầu wave đầu tiên ngay.
            - Tạo font cho HUD.

        Note:
            Truyền grid_rows/cols từ JSON vào SpatialHash thay vì settings
            để hỗ trợ map nhiều kích thước khác nhau giữa các level.
        """
        self.current_level = level_num
        path = f"data/levels/level{level_num}.json"
        with open(path, "r") as f:
            self.config = json.load(f)

        rows = self.config["rows"]
        cols = self.config["cols"]
        self.graph = GridGraph(rows, cols)
        self.graph.load_from_list(self.config["grid"], self.config)
        self.weights_and_cells = self.graph.get_spawn_weight()
        self.spatial_hash = SpatialHash(rows, cols, bucket_cell_size=2)
        self.malwares = []
        self.bosses = []
        self.towers = []
        self.projectiles = []
        self.portal = []
        self.bombs = []
        self.walls = []
        self.fire_marks = []
        self.shock_effects = []
        self.burning_cells = {}
        self.undo_stack = CustomStack() # Giữ nguyên cho các mục đích khác nếu có
        self.stack_tower = CustomStack() # Stack chính cho cơ chế Undo tháp
        self.undo_timer = 0.0

        # Upgrade system
        self.upgrade_trees = {}  # Map tower_class → UpgradeTree
        self.upgrade_menus = {}  # Map tower → UpgradeMenu
        self.active_upgrade_menu = None  # Tower hiện có menu mở
        self._init_upgrade_trees()
        self.right_panel = RightPanel(self.upgrade_trees)
        self.right_panel.set_level(level_num)
        self._pre_wave=True
        self._pre_wave_timer=settings.PRE_WAVE_DURATION
        self.money = self.config["start_money"]
        self.server = Server(pos=self.graph.server_pos)

        self.wave_index = 0
        self.spawn_queue = CustomQueue()
        self.spawn_timer = 0.0
        self.spawn_interval = self.config["waves"][0]["interval_seconds"]
        self.bomb_count = self.config["waves"][0].get("bomb_count", 0)
        self.bomb_spawn_queue = self.bomb_count  # số bomb chưa rơi
        self.bomb_spawn_timers = []  # list thời gian spawn từng bomb
        self._init_bomb_timers()
        self._start_wave(self.wave_index)
        self.global_timer        = 0.0
        self.invisible_duration  = 0.0
        self._stealth_notif_timer = 0.0
        self._bomb_notif_timer    = 0.0
        self._init_stealth_timers()
        self.font = pygame.font.SysFont("courier new", 18)
        self.font_big = pygame.font.SysFont("courier new", 36)
        pass

    def _init_upgrade_trees(self):
        """Khởi tạo upgrade trees cho các loại tower."""
        basic_tree = create_basic_upgrade_tree()
        ice_tree = create_ice_upgrade_tree()
        radar_tree = create_radar_upgrade_tree()

        # BasicNode tree cho: BasicNode, FireNode, SniperNode, SpeedNode
        self.upgrade_trees["BasicNode"] = basic_tree


        # IceWall tree cho: IceWall, FreezeNode, SpreadNode
        self.upgrade_trees["IceWall"] = ice_tree

        # RadarNode tree cho: RadarNode, PoisonNode
        self.upgrade_trees["RadarNode"] = radar_tree
  

    def _start_wave(self, wave_index: int):
        """Nạp dữ liệu wave vào spawn_queue, thiết lập portal, và đặt lại spawn timer.

        Args:
            wave_index (int): Chỉ số wave trong self.config["waves"] (0-based).

        Side effects:
            - Đặt self.victory = True và return nếu wave_index >= số lượng wave.
            - Nạp danh sách tên malware vào self.spawn_queue.
            - Cập nhật self.spawn_interval từ wave_data["interval_seconds"].
            - Reset self.spawn_timer về 0.0 để spawn ngay lập tức khi wave bắt đầu.
            - Chọn ngẫu nhiên num_portals ô từ SPAWN cells làm portal mới.
            - Chuyển portal cũ từ SPAWN về PATH trước khi set portal mới.

        Note:
            Portal random giúp tránh cho phép xây tháp chặn spawn point cố định.
            Số lượng portal theo wave_data["portal_count"], mặc định từ config.

        Usage:
            Gọi tự động trong load_level() và khi wave cũ kết thúc
            (_check_wave_complete() phát hiện spawn_queue rỗng và malwares rỗng).
        """
        waves = self.config["waves"]
        if wave_index >= len(waves):
            self.victory = True
            return

        wave_data = waves[wave_index]
        num_portals = wave_data["portals"]
        weights = [w for w, _ in self.weights_and_cells]
        cells   = [c for _, c in self.weights_and_cells]
        for x,y in self.portal:
            self.graph.set_cell(x,y,Celltype.PATH)
        self.portal  = random.choices(cells, weights=weights, k=num_portals)
        for x,y in self.portal:
            self.graph.set_cell(x,y,Celltype.SPAWN)
        self.spawn_queue = CustomQueue()
        for enemy in wave_data["enemies"]:
            self.spawn_queue.enqueue(enemy)
        self.spawn_interval = wave_data["interval_seconds"]
        self.spawn_timer = 0.0
        self.bomb_count = wave_data.get("bomb_count", 0)
        self.bomb_spawn_queue = self.bomb_count
        self._init_bomb_timers()
        pass

    def _init_bomb_timers(self):
        """Khởi tạo thời gian spawn ngẫu nhiên cho tất cả bomb trong wave.

        Mỗi bomb rơi tại một thời gian ngẫu nhiên trong khoảng [0, max_wave_duration].
        max_wave_duration = số lượng enemy × spawn_interval.
        """
        wave_duration = len(self.spawn_queue) * self.spawn_interval
        self.bomb_spawn_timers = []
        for _ in range(self.bomb_count):
            # Thời gian ngẫu nhiên từ 0 đến wave_duration
            spawn_time = random.uniform(0, wave_duration)
            self.bomb_spawn_timers.append(spawn_time)
        self.bomb_spawn_timers.sort()  # sắp xếp tăng dần
        self.bomb_spawn_index = 0
        self.wave_timer = 0.0

    def _init_stealth_timers(self):
        """Tính ngẫu nhiên thời điểm bắt đầu mỗi đợt tàng hình.

        Cửa sổ hợp lệ: [đầu wave 2, cuối wave 4 - 15s - stealth_duration].
        """
        waves = self.config.get("waves", [])
        stealth_count    = self.config.get("stealth_waves", 0)
        stealth_duration = float(self.config.get("stealth_duration", 0.0))
        self._stealth_duration_cfg = stealth_duration
        self.stealth_timers = []
        self.stealth_index  = 0

        if stealth_count <= 0 or len(waves) < 4 or stealth_duration <= 0:
            return

        # Tính thời gian tích lũy của từng wave (4 wave đầu)
        wave_dur = [len(w["enemies"]) * float(w["interval_seconds"]) for w in waves[:4]]

        start_t = wave_dur[0]                          # đầu wave 2
        end_t   = sum(wave_dur) - stealth_duration  # cửa sổ kết thúc

        if end_t <= start_t:
            return

        times = sorted(random.uniform(start_t, end_t) for _ in range(stealth_count))
        self.stealth_timers = times

    def _update_stealth(self, dt: float):
        """Kích hoạt đợt tàng hình và đếm ngược invisible_duration."""
        if self.stealth_index < len(self.stealth_timers):
            if self.global_timer >= self.stealth_timers[self.stealth_index]:
                self.stealth_index += 1
                self.invisible_duration = self._stealth_duration_cfg
                self._stealth_notif_timer = 3.0   # hiện thông báo 3 giây
                audio_manager.play_sound("warning") # Cảnh báo tàng hình
                for m in self.malwares:
                    m.invisible = self.invisible_duration

        if self.invisible_duration > 0:
            self.invisible_duration -= dt
            if self.invisible_duration < 0:
                self.invisible_duration = 0.0

        if hasattr(self, '_stealth_notif_timer') and self._stealth_notif_timer > 0:
            self._stealth_notif_timer -= dt

    # ------------------------------------------------------------------
    # VÒNG LẶP CHÍNH
    # ------------------------------------------------------------------

    def run(self):
        """Vòng lặp game chính — chạy cho đến khi self.running = False.

        Side effects:
            - Gọi clock.tick(FPS) để giới hạn frame rate và lấy dt.
            - Gọi handle_events(), update(dt), draw() mỗi frame.
            - Khi self.running = False, gọi pygame.quit() để dọn dẹp.

        Note:
            dt = clock.tick(FPS) / 1000.0 chuyển milliseconds → giây.
            Mọi chuyển động dùng "tốc độ × dt" → frame rate không ảnh hưởng
            đến tốc độ game thực tế (frame-rate independent movement).
            update() bị bỏ qua khi game_over hoặc victory — chỉ vẽ màn hình kết thúc.
        """
        while self.running:
            dt = self.clock.tick(settings.FPS) / 1000.0
            self.handle_events()

            if not self.game_over and not self.victory:
                self.update(dt)

            self.draw()
        pygame.quit()
        pass

    # ------------------------------------------------------------------
    # XỬ LÝ INPUT
    # ------------------------------------------------------------------

    def handle_events(self, events=None):
        """Xử lý tất cả sự kiện từ bàn phím và chuột trong frame hiện tại.

        Args:
            events: Danh sách events (nếu None, sẽ gọi pygame.event.get() tự động)

        Side effects:
            - Gọi self.undo() khi nhấn Ctrl+Z.
            - Cập nhật self.selected_tower khi nhấn phím 1/2/3.
            - Gọi self.place_tower(row, col) khi click chuột trái vào vùng lưới.
            - Toggle UpgradeMenu khi click vào tower đã xây.
            - Xử lý click upgrade button khi menu hiển thị (gọi _apply_upgrade()).

        Note:
            Click chuột chỉ được xử lý khi my < GRID_ROWS * CELL_SIZE
            (trong vùng lưới, không phải thanh HUD phía dưới).
            Tọa độ ô: row = my // CELL_SIZE, col = mx // CELL_SIZE.
            Ưu tiên kiểm tra: upgrade menu button → tower click → place tower.
        """
        if events is None:
            events = pygame.event.get()

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in TOWER_FACTORY:
                    self.selected_tower = TOWER_FACTORY[event.key]
                    self.wall_placement_mode = False
                    key_to_class = {pygame.K_1: "BasicNode", pygame.K_2: "IceWall", pygame.K_3: "RadarNode"}
                    self.right_panel.set_tower_type(key_to_class[event.key])

                elif event.key == pygame.K_4:
                    self.wall_placement_mode = not self.wall_placement_mode
                    self.right_panel.set_tower_type("Wall")
                
                elif event.key == pygame.K_ESCAPE:
                    # ESC để thoát fullscreen hoặc quit game
                    self.running = False
                
                elif event.key == pygame.K_z:
                    # Kiểm tra tổ hợp Ctrl + Z
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.undo()

            elif event.type == pygame.MOUSEMOTION:
                self.right_panel.handle_event(event)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                # Block clicks in the right panel area
                if mx >= self.right_panel.panel_x:
                    self.right_panel.handle_event(event)
                    continue

                # Trước tiên kiểm tra xem click có trúng upgrade menu không
                if self.active_upgrade_menu:
                    upgrade_node = self.active_upgrade_menu.get_clicked_upgrade((mx, my))
                    if upgrade_node:
                        if upgrade_node == "DEMOLISH":
                            # Click vào nút phá tháp
                            self._demolish_tower(self.active_upgrade_menu.tower)
                        else:
                            # Kiểm tra lock trước khi upgrade
                            success = False
                            if settings.is_tower_unlocked(upgrade_node.node_id, self.current_level):
                                success, self.money, msg = self.active_upgrade_menu.try_upgrade(upgrade_node, self.money)
                            if success:
                                # Áp dụng upgrade
                                self._apply_upgrade(self.active_upgrade_menu.tower, upgrade_node)
                        # Close menu sau khi click
                        self.active_upgrade_menu.hide()
                        self.active_upgrade_menu = None
                        return

                # Chỉ xử lý click trong vùng lưới (không phải HUD) — HUD ở dưới cùng
                hud_start_y = settings.SCREEN_HEIGHT - settings.HUD_HEIGHT
                if my < hud_start_y:
                    # Convert screen coords → world coords với camera offset
                    world_x = mx + self.camera_x
                    world_y = my + self.camera_y
                    row = int(world_y // settings.CELL_SIZE)
                    col = int(world_x // settings.CELL_SIZE)

                    # Kiểm tra xem click có trúng tower không
                    tower = self._get_tower_at((row, col))
                    if tower and tower in self.upgrade_menus:
                        # Toggle upgrade menu cho tower
                        if self.active_upgrade_menu == self.upgrade_menus[tower]:
                            self.active_upgrade_menu.hide()
                            self.active_upgrade_menu = None
                        else:
                            # Close menu cũ nếu có
                            if self.active_upgrade_menu:
                                self.active_upgrade_menu.hide()
                            # Show menu mới
                            self.active_upgrade_menu = self.upgrade_menus[tower]
                            self.active_upgrade_menu.show()
                    else:
                        # Click vào ô rỗng → close menu và place tower/wall
                        if self.active_upgrade_menu:
                            self.active_upgrade_menu.hide()
                            self.active_upgrade_menu = None

                        if self.wall_placement_mode:
                            self.place_wall(row, col)
                        else:
                            self.place_tower(row, col)
        pass

    def _update_camera(self, dt: float):
        """Update camera position based on WASD key presses.

        W: pan up (camera_y decreases)
        S: pan down (camera_y increases)
        A: pan left (camera_x decreases)
        D: pan right (camera_x increases)

        Camera is clamped to map boundaries.
        Playable area is SCREEN_HEIGHT - HUD_HEIGHT (HUD is fixed at bottom).
        """
        keys = pygame.key.get_pressed()
        
        # Map dimensions in pixels
        map_width = self.graph.col * settings.CELL_SIZE
        map_height = self.graph.row * settings.CELL_SIZE
        
        # Playable screen area (excluding HUD at bottom)
        playable_height = settings.SCREEN_HEIGHT - settings.HUD_HEIGHT
        
        # Max camera position (cannot pan past map edges)
        max_x = max(0, map_width - settings.SCREEN_WIDTH)
        max_y = max(0, map_height - playable_height)

        movement = self.camera_speed * dt

        if keys[pygame.K_w]:
            self.camera_y = max(0, self.camera_y - movement)
        if keys[pygame.K_s]:
            self.camera_y = min(max_y, self.camera_y + movement)
        if keys[pygame.K_a]:
            self.camera_x = max(0, self.camera_x - movement)
        if keys[pygame.K_d]:
            self.camera_x = min(max_x, self.camera_x + movement)

    def _world_to_screen(self, world_x: float, world_y: float) -> tuple:
        """Convert world coordinates to screen coordinates using camera offset.

        Args:
            world_x, world_y: World pixel coordinates

        Returns:
            Tuple of (screen_x, screen_y)
        """
        return (world_x - self.camera_x, world_y - self.camera_y)

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(self, dt: float):
        """Cập nhật toàn bộ trạng thái game mỗi frame theo thứ tự cố định.

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Spawn malware mới theo wave timer.
            - Di chuyển tất cả malware, cập nhật SpatialHash, xử lý server damage.
            - Tower chọn mục tiêu và bắn Projectile mới.
            - Di chuyển đạn, gây damage, xóa đạn đã kết thúc.
            - Kiểm tra chuyển wave nếu wave hiện tại đã xong.

        Note:
            Thứ tự quan trọng: spawner → malwares → towers → projectiles → wave check.
            Spawner trước malwares để malware mới được di chuyển ngay trong frame spawn.
            Towers sau malwares để query SpatialHash với vị trí đã cập nhật.
        """
        # Update camera position based on WASD keys
        self._update_camera(dt)

        if self._pre_wave:
            self._pre_wave_timer -= dt
            if self._pre_wave_timer <= 0:
                self._pre_wave = False
            return
    # KHÔNG gọi WaveSpawner.tick()
    # KHÔNG spawn malware
         # vẫn vẽ map, tháp, HUD

        # Tích lũy global timer và xử lý stealth
        self.global_timer += dt
        self._update_stealth(dt)

        # Xử lý đếm ngược 3 giây cho cơ chế Undo
        if self.undo_timer > 0:
            self.undo_timer -= dt
            if self.undo_timer <= 0:
                self.undo_timer = 0
                self.stack_tower = CustomStack() # Hết 3s thì reset stack về rỗng

        self._update_spawner(dt)
        self._update_bombs(dt)
        self._update_malwares(dt)
        self._update_bosses(dt)
        self._update_radar_detection()
        self._update_towers(dt)
        self._update_walls(dt)
        self._update_burning_cells(dt)
        self._update_projectiles(dt)
        self._update_shock_effects(dt)
        self._check_wave_complete()
        self._update_animations(dt)
        pass

    def _update_burning_cells(self, dt: float):
        """Cập nhật thời gian cháy của các ô tường (tạm thời không cho đặt tháp)."""
        if not hasattr(self, 'burning_cells'): return
        keys_to_remove = []
        for pos, duration in self.burning_cells.items():
            self.burning_cells[pos] = duration - dt
            if self.burning_cells[pos] <= 0:
                keys_to_remove.append(pos)
        for pos in keys_to_remove:
            del self.burning_cells[pos]

    def _update_animations(self, dt: float):
        """Cập nhật animation timer cho portal và server.

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Cập nhật portal animation frame (_portal_timer, _portal_frame).
            - Gọi self.server.update(dt) để cập nhật server animation.
        """
        self._portal_timer += dt
        if self._portal_timer >= 1.0 / settings.PORTAL_ANIM_FPS:
            self._portal_timer = 0.0
            self._portal_frame = (self._portal_frame + 1) % 14

        self.server.update(dt)
    def _update_spawner ( self, dt: float):
        
        """Xử lý logic spawn malware theo wave timer.

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Giảm self.spawn_timer mỗi frame.
            - Khi timer <= 0: reset timer, lấy tên malware đầu tiên từ spawn_queue,
              chọn vị trí spawn ngẫu nhiên có trọng số, gọi spawn_malware().

        Note:
            Dùng CustomQueue.dequeue() để spawn theo thứ tự trong JSON (FIFO).
            get_spawn_weight() trả về danh sách (weight, cell) — random.choices()
            chọn ngẫu nhiên có trọng số: malware khó spawn gần server hơn.
        """
        if self.spawn_queue.is_empty():
            return

        self.spawn_timer -= dt
        if self.spawn_timer > 0:
            return

        # Đến lúc spawn
        self.spawn_timer = self.spawn_interval

        malware_type = self.spawn_queue.dequeue()

        # Chọn vị trí spawn ngẫu nhiên có trọng số
        if not self.portal:
            return
        random.seed(None)
        chosen  = random.choices(self.portal, k=1)[0]

        self.spawn_malware(malware_type, chosen)
        pass

    def _update_bombs(self, dt: float) -> None:
        """Xử lý spawn và cập nhật bomb mỗi frame.

        Args:
            dt: Thời gian frame (giây).

        Side effects:
            - Spawn bomb tại thời gian ngẫu nhiên (từ _init_bomb_timers).
            - Cập nhật timer explosion cho từng bomb.
            - Khi bomb phát nổ: stun tất cả towers + damage server.
            - Xóa bomb đã chết.
        """
        # Cập nhật wave timer để track khi nào spawn bomb
        self.wave_timer += dt

        # Spawn bomb nếu đến thời gian
        if self.bomb_spawn_index < len(self.bomb_spawn_timers):
            random.seed(None)
            if self.wave_timer >= self.bomb_spawn_timers[self.bomb_spawn_index]:
                # Chọn vị trí ngẫu nhiên trên PATH cell (không WALL, không SERVER)
                available_cells = [(r, c) for r in range(self.graph.row)
                                        for c in range(self.graph.col)
                                        if self.graph.get_cell(r, c) == Celltype.PATH]
                if available_cells:
                   
                    
                    pos = random.choice(available_cells)
                  
                bomb = Bomb(pos)
                self.bombs.append(bomb)
                audio_manager.play_sound("warning") # Cảnh báo bom rơi
                self.bomb_spawn_index += 1
                self._bomb_notif_timer = 3.0

        # Cập nhật tất cả bomb
        dead_bombs = []

        for bomb in self.bombs:
            bomb.update(dt)

            if bomb.is_dead():
                # Bomb bị tower giết trước khi nổ
                dead_bombs.append(bomb)
            elif bomb.is_exploded():
                # Explosion animation: 11 frames @ 8 fps = 1.375 giây
                # Trigger damage/stun KHI ANIMATION HOÀN THÀNH (not immediately)
                if bomb.anim_timer <= 0.05: # Phát âm thanh khi vừa bắt đầu nổ
                     audio_manager.play_sound("explosion")

                if bomb.anim_timer >= 1.4:
                    # Animation nổ đã chạy xong → trigger effect + remove
                    explosion_data = bomb.get_explosion_data()
                    for tower in self.towers:
                        tower.apply_stun(explosion_data["stun_duration"])
                    self.server.take_damage(explosion_data["server_damage"])
                    dead_bombs.append(bomb)

        # Xóa bomb chết
        for bomb in dead_bombs:
            self.bombs.remove(bomb)

        if self._bomb_notif_timer > 0:
            self._bomb_notif_timer -= dt

    def _update_malwares(self, dt: float):
        """Di chuyển tất cả malware và xử lý kết quả (chết hoặc đến server).

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Gọi malware.update(dt) để di chuyển từng malware.
            - Gọi spatial_hash.update_position() nếu malware đã di chuyển.
            - Gọi self.server.take_damage() khi malware đến server; đặt game_over nếu server HP <= 0.
            - Cộng self.money += malware.reward khi malware chết.
            - Xóa malware đã chết hoặc đến server khỏi self.malwares và spatial_hash.
            - Collect projectiles từ ranged malware (SlowSpy_Ranged, Spyware_Ranged, TrojanRanged).

        Note:
            old_pos phải được lưu TRƯỚC malware.update(dt) để update_position()
            biết bucket cũ của malware.
            Kiểm tra has_reached_server() TRƯỚC is_dead() — malware bị giết đúng lúc
            chạm server vẫn trừ HP server.
        """
        dead = []
        for malware in self.malwares:
            old_pos = malware.pos
            malware.update(dt)
            if malware.pos != old_pos:
                self.spatial_hash.update_position(malware, old_pos)

            # Collect projectiles từ ranged malware (nếu có)
            if hasattr(malware, 'get_projectiles'):
                for proj in malware.get_projectiles():
                    self.projectiles.append(proj)

            # Xử lý damage từ malware (server hoặc tower)
            hit=malware.get_pending_hit()
            if hit:
                if hit["type"]=="server":
                    self.server.take_damage(hit["dmg"])
                    # Xử lý poison nếu malware có khả năng tiêm độc (ví dụ: WormPoison)
                    if "poison" in hit and hit["poison"] > 0:
                        self.server.get_poison(hit["poison"])
                elif hit["type"]=="tower":
                    tower=self._get_tower_at(hit["cell"])
                    if tower:
                        tower.take_damage(hit["dmg"])
                        # Xử lý slow nếu malware có khả năng làm chậm (ví dụ: Slowware)
                        if "slow" in hit and hit["slow"]:
                            factor, duration = hit["slow"]
                            tower.apply_slow(factor, duration)
                        if tower.is_destroyed():
                            self._on_tower_destroyed(tower)

                    # Xử lý shock spread nếu có affected_cells (ví dụ: LightSpy)
                    if "affected_cells" in hit and hit["affected_cells"]:
                        for cell in hit["affected_cells"]:
                            affected_tower = self._get_tower_at(cell)
                            if affected_tower and affected_tower != tower:
                                affected_tower.take_damage(hit["dmg"])
                                # Tạo shock effect tại tháp bị tấn công
                                shock = ShockEffect(pos=cell, duration=2)
                                self.shock_effects.append(shock)
                                # 15% cơ hội bị dính choáng từ shock spread
                                if random.random() < 0.15:
                                    affected_tower.apply_stun(settings.BOMB_STUN_DURATION)
                                if affected_tower.is_destroyed():
                                    self._on_tower_destroyed(affected_tower)
                malware.clear_pending_hit()

            if malware.has_reached_server():
                if self.server.is_destroyed():
                    self.game_over = True
            if malware.is_dead():
                # Add reward when dies (not when animation finishes)
                if not malware._reward_given:
                    self.money += malware.reward
                    malware._reward_given = True
                # Only remove after death animation is done
                if malware.is_death_animation_done():
                    dead.append(malware)
        for m in dead:
            self.malwares.remove(m)
            self.spatial_hash.remove(m)
        pass

    def _update_bosses(self, dt: float):
        """Cập nhật tất cả boss: di chuyển, tấn công, kiểm tra chết.

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Cập nhật vị trí boss dựa trên movement.
            - Xử lý tấn công AoE lên tháp (nếu có).
            - Xử lý tấn công server (nếu có).
            - Xóa boss đã chết khỏi self.bosses.
        """
        dead = []
        for boss in self.bosses:
            old_pos = boss.pos
            boss.update(dt)
            if boss.pos != old_pos:
                self.spatial_hash.update_position(boss, old_pos)
            
            # Xử lý tấn công tháp (AoE)
            if isinstance(boss,FireWorm):
                tower_attacks = boss.get_tower_attacks()
                for attack in tower_attacks:
                    # Tìm tất cả tháp trong phạm vi
                    attack_range = attack.get("range", 3)
                    attack_damage = attack.get("damage", 10)
                    affected_cells = attack.get("fire_spread_range", 0)

                    # Query all towers in range
                    for tower in self.towers:
                        dist = max(abs(tower.pos[0] - boss.pos[0]), abs(tower.pos[1] - boss.pos[1]))
                        if dist <= attack_range:
                            # Tháp bị tấn công
                            tower.take_damage(attack_damage)
                            if tower.is_destroyed():
                                self._on_tower_destroyed(tower)

                            # Lan cháy sang tường gần đó (dùng BFS trên Grid)
                            if affected_cells > 0:
                                burn_duration = attack.get("burn_duration", 0)
                                if burn_duration > 0:
                                    from core.data_structures import CustomQueue
                                    from core.graph import Celltype
                                    
                                    queue = CustomQueue()
                                    queue.enqueue((tower.pos, 0)) # (pos, dist)
                                    visited = {tower.pos}
                                    
                                    while not queue.is_empty():
                                        curr_pos, curr_dist = queue.dequeue()
                                        
                                        # Nếu là tường, áp dụng đốt cháy (khóa đặt tháp)
                                        if self.graph.get_cell(*curr_pos) == Celltype.WALL:
                                            if curr_pos not in self.burning_cells:
                                                self.burning_cells[curr_pos] = 0.0
                                            self.burning_cells[curr_pos] = max(self.burning_cells[curr_pos], burn_duration)
                                        
                                        if curr_dist < affected_cells:
                                            directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
                                            for dr, dc in directions:
                                                nr, nc = curr_pos[0] + dr, curr_pos[1] + dc
                                                if 0 <= nr < self.graph.row and 0 <= nc < self.graph.col:
                                                    if (nr, nc) not in visited:
                                                        visited.add((nr, nc))
                                                        queue.enqueue(((nr, nc), curr_dist + 1))
            elif isinstance(boss, (FlyingDemon, Final)):
                dead_bombs = []
                for bomb in boss.get_bombs():
                    if bomb.is_dead():
                        dead_bombs.append(bomb)
                    elif bomb.is_exploded():
                        if bomb.anim_timer >= 1.4:
                            explosion_data = bomb.get_explosion_data()
                            for tower in self.towers:
                                tower.apply_stun(explosion_data["stun_duration"])
                            self.server.take_damage(explosion_data["server_damage"])
                            if self.server.is_destroyed():
                                self.game_over = True
                            dead_bombs.append(bomb)
                for bomb in dead_bombs:
                    boss.remove_bomb(bomb)

            # Final Boss: clear destroyed cells và spawn RiposteWare
            if hasattr(boss, 'drain_spawn_queue'):
                cells = boss.drain_spawn_queue()
                if cells:
                    self._handle_boss_destruction(cells)

            # Thu projectile phản đạn từ RiposteBoss / Final
            if hasattr(boss, 'get_projectiles'):
                for proj in boss.get_projectiles():
                    self.projectiles.append(proj)

            # Xử lý tấn công server
            server_attack = boss.get_server_attack()
            if server_attack:
                damage = server_attack.get("damage", 10)
                self.server.take_damage(damage)
                if self.server.is_destroyed():
                    self.game_over = True

            # Kiểm tra boss đã chết
            if boss.is_dead():
                self.money += boss.reward
                dead.append(boss)

        # Xóa boss chết
        for boss in dead:
            self.spatial_hash.remove(boss)
            self.bosses.remove(boss)
        pass

    def _get_tower_at(self, cell):
        """Tìm tower đang chiếm ô lưới chỉ định.

        Args:
            cell (tuple[int,int]): Tọa độ ô cần tìm (row, col).

        Returns:
            Tower | None: Đối tượng Tower tại ô đó, hoặc None nếu không có.
        """
        for tower in self.towers:
            if tower.pos == cell:
                return tower
        return None

    def _on_tower_destroyed(self, tower):
        """Xử lý khi một tower bị phá hủy.

        Chuyển ô tower về PATH, xóa khỏi danh sách, tính lại đường đi
        cho tất cả malware đang sống.

        Args:
            tower (Tower): Tower vừa bị phá hủy.

        Side effects:
            - Cập nhật graph cell từ TOWER → PATH.
            - Xóa tower khỏi self.towers.
            - Gọi _calculate_path() cho tất cả malware.
        """
        self.graph.set_cell(*tower.pos, Celltype.PATH)
        self.towers.remove(tower)
        if tower in self.upgrade_menus:
            del self.upgrade_menus[tower]
        if self.active_upgrade_menu and self.active_upgrade_menu.tower == tower:
            self.active_upgrade_menu = None
        for m in self.malwares:
            m._calculate_path()
            if hasattr(m, 'attack_pos'):
                m.state = "moving"
        for t in self.towers:
            if t.is_destroyed(): continue
            t.path=t._path_can_shoot()
    def _update_radar_detection(self):
        """Cập nhật is_radar_range cho tất cả malware dựa trên RadarNode.

        Duyệt qua tất cả RadarNode (và PoisonNode — kế thừa RadarNode).
        Gom malware trong tầm vào set, rồi flag is_radar_range cho từng malware.
        Phải gọi SAU _update_malwares() và TRƯỚC _update_towers().
        """
        radar_detected = set()
        for tower in self.towers:
            if isinstance(tower, RadarNode):
                candidates = self.spatial_hash.query_range(tower.pos, tower.range)
                for m in candidates:
                    if isinstance(m, Boss): continue
                    radar_detected.add(m)
        for m in self.malwares:
            m.is_radar_range = m in radar_detected

    def _update_towers(self, dt: float):
        """Cho từng tower query SpatialHash, thêm Bomb, chọn mục tiêu, bắn Projectile.

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Gọi spatial_hash.query_range() để lấy candidates trong tầm bắn.
            - Thêm Bomb trong tầm bắn vào candidates.
            - Gọi tower.update(dt, candidates) — trả về Projectile hoặc None.
            - Append Projectile vào self.projectiles nếu không None.

        Note:
            SpatialHash lọc candidates trong O(1) trung bình → chỉ xây Heap
            từ số ít malware gần tower. Nếu dùng toàn bộ self.malwares → Heap
            tốn kém không cần thiết.

            Bomb được thêm vào candidates để tower có thể bắn (ưu tiên cao hơn malware).
        """
        import math
        for tower in self.towers:
            # Query malware từ spatial hash
            candidates = self.spatial_hash.query_range(tower.pos, tower.range)

            # Tower thường không thể target malware tàng hình ngoài tầm radar
            # RadarNode (và PoisonNode kế thừa) có thể target tất cả
            if not isinstance(tower, RadarNode):
                candidates = [m for m in candidates
                              if (isinstance(m, Boss)) or not(m.invisible > 0 and not m.is_radar_range)]

            # Thêm Bomb vào candidates nếu nằm trong tầm bắn
            for bomb in self.bombs:
                dist = math.sqrt((bomb.pos[0] - tower.pos[0])**2 + (bomb.pos[1] - tower.pos[1])**2)
                if dist <= tower.range:
                    candidates.append(bomb)

            for boss in self.bosses:
                if isinstance(boss, (FlyingDemon, Final)):
                    for bomb in boss.get_bombs():
                        dist = math.sqrt((bomb.pos[0] - tower.pos[0])**2 + (bomb.pos[1] - tower.pos[1])**2)
                        if dist <= tower.range:
                            candidates.append(bomb)

            projectile = tower.update(dt, candidates)
            if projectile is not None:
                self.projectiles.append(projectile)

    def _update_walls(self, dt: float) -> None:
        """Cập nhật tường - xóa tường hết hạn, khôi phục cell, quản lý cooldown.

        Args:
            dt: Thời gian frame (giây).

        Side effects:
            - Cập nhật timer duration cho từng wall.
            - Khi wall hết hạn: khôi phục cell, bắt đầu cooldown.
            - Tính lại đường đi cho tất cả malware.
            - Xóa wall đã hết hạn.
            - Giảm cooldown timer mỗi frame.
        """
        # Cập nhật cooldown timer
        if self.wall_cooldown_timer > 0:
            self.wall_cooldown_timer -= dt

        dead_walls = []
        for wall in self.walls:
            wall.update(dt)
            if wall.is_dead():
                # Khôi phục cell về giá trị ban đầu
                self.graph.set_cell(wall.pos[0], wall.pos[1], wall.original_cell)
                # Tính lại đường đi cho tất cả malware
                for malware in self.malwares:
                    malware._calculate_path()
                    if hasattr(malware, 'attack_pos'):
                        malware.state = "moving"
                dead_walls.append(wall)

        # Xóa wall chết
        for wall in dead_walls:
            self.walls.remove(wall)

    def _update_projectiles(self, dt: float):
        """Di chuyển đạn và xóa những đạn đã kết thúc vòng đời.

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Gọi proj.update(dt) để di chuyển từng đạn.
            - Gọi proj.apply_hit(game) khi proj.has_hit() để xử lý damage.
            - Lọc self.projectiles, giữ lại chỉ những đạn chưa has_hit().
        """
        for proj in self.projectiles:
            proj.update(dt)
            if proj.has_hit():
                proj.apply_hit(self)

                # Tạo vết lửa khi FireNode bắn trúng
                if proj.tower_type == "fire":
                    hit_pos = proj.target.pos if hasattr(proj, 'target') and proj.target else proj.goal_pos
                    fire_mark = FireMark(
                        pos=hit_pos,
                        damage_per_sec=settings.FIRE_DAMAGE_PER_SEC,
                        duration=settings.TOWER_FIRE_DURATION
                    )
                    self.fire_marks.append(fire_mark)

                # Lan slow khi SpreadNode bắn trúng
                if proj.tower_type == "ice":
                    if hasattr(proj.target, 'apply_slow'):  # Check if target has the apply_slow method
                        proj.target.apply_slow(proj.slow_factor, proj.slow_duration)
                if proj.tower_type == "spread":
                    hit_pos = proj.target.pos
                    import math
                    for malware in self.malwares:
                        dist = math.sqrt((malware.pos[0] - hit_pos[0])**2 + (malware.pos[1] - hit_pos[1])**2)
                        if dist <= proj.spread_range and not malware.is_dead():
                            malware.apply_slow(proj.slow_factor, proj.slow_duration)
                # Apply slow effect for slowspy_ranged projectiles
                if isinstance(proj, MalwareProjectile) :
                    if proj.malware_type == "slowspy_ranged":
                        if proj.goal_type == "tower":
                            tower = self._get_tower_at(proj.goal_pos)
                            if tower:
                                # SlowSpy_Ranged applies 50% slow for 2 seconds
                                tower.apply_slow(0.5, 2.0)
                    if proj.malware_type == "lightspy_ranged":
                        if proj.goal_type == "tower":
                            tower = self._get_tower_at(proj.goal_pos)
                            if proj.affected_cells:
                                for cell in proj.affected_cells:
                                    affected_tower = self._get_tower_at(cell)
                                    if affected_tower and affected_tower != tower:
                                        affected_tower.take_damage(proj.damage)
                                    # Tạo shock effect tại tháp bị tấn công
                                        shock = ShockEffect(pos=cell, duration=2)
                                        self.shock_effects.append(shock)
                                    # 25% cơ hội bị dính choáng từ shock spread
                                        if random.random() < 0.15:
                                            affected_tower.apply_stun(settings.BOMB_STUN_DURATION)
                                        if affected_tower.is_destroyed():
                                            self._on_tower_destroyed(affected_tower)

        self.projectiles = [p for p in self.projectiles if not p.has_hit()]

        # Cập nhật fire marks
        for mark in self.fire_marks:
            mark.update(dt)
            # Tìm quái đứng trên vết lửa
            for malware in self.malwares:
                if mark.affects_enemy(malware):
                    damage = mark.damage_per_sec * dt
                    malware.take_damage(damage)

        # Xóa vết lửa hết hạn
        self.fire_marks = [m for m in self.fire_marks if m.is_alive()]
        pass

    def _update_shock_effects(self, dt: float):
        """Cập nhật các hiệu ứng shock từ LightSpy attacks.

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Cập nhật animation frame cho mỗi shock effect.
            - Xóa shock effects đã hết thời gian (is_alive() = False).
        """
        for shock in self.shock_effects:
            shock.update(dt)
        self.shock_effects = [s for s in self.shock_effects if s.is_alive()]
        pass

    def _check_wave_complete(self):
        """Kiểm tra xem wave hiện tại đã xong chưa để chuyển sang wave tiếp.

        Side effects:
            - Tăng self.wave_index và gọi _start_wave(wave_index) nếu wave xong.
            - _start_wave() sẽ đặt self.victory = True nếu hết tất cả wave.

        Note:
            Wave xong khi: spawn_queue rỗng (không còn malware cần spawn)
            VÀ self.malwares rỗng (tất cả malware đã chết hoặc đến server)
            VÀ self.bosses rỗng (tất cả boss đã chết).
            Cả ba điều kiện phải thỏa đồng thời.
        """
        if self.spawn_queue.is_empty() and len(self.malwares) == 0 and len(self.bosses) == 0:
            self.wave_index += 1
            self._start_wave(self.wave_index)
        pass

    # ------------------------------------------------------------------
    # HÀNH ĐỘNG NGƯỜI CHƠI
    # ------------------------------------------------------------------

    def place_tower(self, row: int, col: int):
        """Đặt tower tại ô (row, col) nếu hợp lệ và đủ tiền.

        Args:
            row (int): Hàng ô lưới được click.
            col (int): Cột ô lưới được click.

        Side effects:
            - Trừ self.money theo cost của tower.
            - Đổi ô (row, col) từ WALL → TOWER trong GridGraph.
            - Thêm tower vào self.towers.
            - Lưu action vào self.undo_stack để Ctrl+Z có thể hoàn tác.
            - Gọi _calculate_path() cho tất cả Spyware/Ransomware đang sống
              vì lưới vừa thay đổi (tower mới có thể là target gần hơn).

        Note:
            Kiểm tra is_tower_placeable(): ô phải là WALL và không quá gần server
            (trong server_radius Chebyshev). Trojan/Worm không cần tính lại path
            vì chúng đi trên PATH, không qua WALL.
        """
        if not self.graph.is_tower_placeable(row, col):
            return
        if getattr(self, 'burning_cells', None) and (row, col) in self.burning_cells:
            return  # Ô đang bị cháy, không thể đặt tháp
        if self.walls:
            if (row,col) in [w.pos for w in self.walls]:
                return
        TowerClass = self.selected_tower
        if not settings.is_tower_unlocked(TowerClass.__name__, self.current_level):
            return
        temp = TowerClass((row, col), self.graph)
        if self.money < temp.cost:
            return
        self.money -= temp.cost
        tower = temp
        self.graph.set_cell(row, col, Celltype.TOWER)
        self.towers.append(tower)
        # Đẩy vào stack_tower để có thể Undo
        self.stack_tower.push({"pos": (row, col), "tower": tower, "cost": temp.cost})
        self.undo_timer = 3.0 # Đặt timer là 3 giây
        for m in self.malwares:
            if hasattr(m, 'attack_pos'):
                m._calculate_path()
                if m.attack_pos:
                    m.state = "moving"

        # Tạo upgrade menu cho tower
        tower_class_name = tower.__class__.__name__
        if tower_class_name in self.upgrade_trees:
            menu = UpgradeMenu(tower, self.upgrade_trees[tower_class_name])
            self.upgrade_menus[tower] = menu

    def place_wall(self, row: int, col: int):
        """Đặt tường tạm thời tại ô (row, col) nếu hợp lệ và cooldown hết.

        Args:
            row (int): Hàng ô lưới được click.
            col (int): Cột ô lưới được click.

        Side effects:
            - Đổi ô (row, col) từ PATH → WALL (celltype 0).
            - Lưu original_cell (PATH).
            - Thêm wall vào self.walls.
            - Tính lại đường đi cho tất cả malwares (vì PATH đã chuyển thành WALL).
            - Bắt đầu cooldown timer để ngăn đặt tường liên tục.

        Note:
            Tường chỉ có thể đặt trên ô PATH khi cooldown = 0.
            Sau WALL_DURATION, tường biến mất và bắt đầu cooldown.
            Tường không tốn tiền (là cơ chế bảo vệ tạm thời).
        """
        # Kiểm tra cooldown
        if self.wall_cooldown_timer > 0:
            return

        cell = self.graph.get_cell(row, col)
        # Chỉ đặt tường trên ô PATH
        if cell != Celltype.PATH:
            return

        # Tạo wall object
        wall = Wall((row, col), cell)
        self.walls.append(wall)

        # Đổi celltype thành WALL (0)
        self.graph.set_cell(row, col, Celltype.WALL)

        # Bắt đầu cooldown ngay lập tức (khóa đặt tường lại)
        self.wall_cooldown_timer = settings.WALL_DURATION + settings.WALL_COOLDOWN

        # Tính lại đường đi cho tất cả malwares vì PATH đã đổi thành WALL
        for malware in self.malwares:
            malware._calculate_path()
            if hasattr(malware, 'attack_pos'):
                
                malware.state = "moving"

    def _apply_upgrade(self, tower, upgrade_node):
        """Áp dụng upgrade cho tower.

        Args:
            tower: Tower object cần upgrade
            upgrade_node: SkillNode chứa thông tin upgrade

        Side effects:
            - Nếu stat_buff: cập nhật stats tower (damage, fire_rate, etc.)
            - Nếu tower_upgrade: thay thế tower bằng tower class mới, giữ nguyên vị trí

        Note:
            fire_rate được xử lý đặc biệt: cập nhật cả tower.fire_rate VÀ tower.original_fire_rate
            để đảm bảo slow/stun effect reset đúng khi hết (dùng original_fire_rate).
            Các stat khác chỉ dùng setattr cộng thêm giá trị.
        """
        if not settings.is_tower_unlocked(upgrade_node.node_id, self.current_level):
            return

        if upgrade_node.upgrade_type == "stat_buff" and upgrade_node.stat_buff:
            # Áp dụng stat buff
            for stat, value in upgrade_node.stat_buff.items():
                if hasattr(tower, stat):
                    if stat == "fire_rate":
                        # Tăng fire_rate
                        tower.fire_rate += value
                        tower.original_fire_rate = tower.fire_rate
                    elif stat == "damage":
                        tower.damage += value
                    else:
                        setattr(tower, stat, getattr(tower, stat) + value)
            self.right_panel.invalidate()

        elif upgrade_node.upgrade_type == "tower_upgrade":
            # Nâng cấp tower sang class mới
            tower_class_name = upgrade_node.tower_class
            # Map tên class → class object
            tower_classes = {
                "BasicNode": BasicNode,
                "IceWall": IceWall,
                "RadarNode": RadarNode,
                "SpeedNode": SpeedNode,
                "FireNode": FireNode,
                "SniperNode": SniperNode,
                "FreezeNode": FreezeNode,
                "SpreadNode": SpreadNode,
                "PoisonNode": PoisonNode,
            }

            if tower_class_name in tower_classes:
                NewTowerClass = tower_classes[tower_class_name]
                old_pos = tower.pos
                try:
                    tower_idx = self.towers.index(tower)
                except ValueError:
                    return

                # Tạo tower mới tại vị trí cũ
                new_tower = NewTowerClass(old_pos, self.graph)
                self.towers[tower_idx] = new_tower

                # Cập nhật upgrade menu
                if tower in self.upgrade_menus:
                    del self.upgrade_menus[tower]
                new_tower_class_name = new_tower.__class__.__name__

                menu = UpgradeMenu(new_tower, self.upgrade_trees.get(new_tower_class_name, None))
                self.upgrade_menus[new_tower] = menu
                self.right_panel.invalidate()

                # Nâng cấp tháp khiến stack_tower bị reset ngay lập tức
                self.stack_tower = CustomStack()
                self.undo_timer = 0

    def _demolish_tower(self, tower):
        """Phá tháp và hoàn lại 50% chi phí xây dựng.

        Args:
            tower: Tower object cần phá

        Side effects:
            - Tính toán refund = 50% của tower.cost
            - Thêm refund vào self.money
            - Đổi ô tower từ TOWER → WALL trong GridGraph
            - Xóa tower khỏi self.towers
            - Xóa tower khỏi self.upgrade_menus
            - Tính lại path cho tất cả tower-seeking enemies (trong case chúng đang tấn công tower này)

        Note:
            Khi tower bị phá, tất cả Spyware/Ransomware đang tấn công nó cần recalculate path
            vì target tower không còn tồn tại. Họ sẽ tìm tower gần nhất khác hoặc quay về
            A* đi tới Server.
        """
        if not tower:
            return
            
        # Phát âm thanh demolish đặc trưng
        tower_type = tower.__class__.__name__
        if tower_type == "FireNode":
            audio_manager.play_sound("firenode")
        elif tower_type == "FreezeNode":
            audio_manager.play_sound("freezenode")
        elif tower_type == "SpreadNode":
            audio_manager.play_sound("spreadnode")

        refund = tower.cost // 2
        # Tính toán tiền hoàn lại (50% cost)
        self.money += refund

        # Đổi ô từ TOWER → PATH
        row, col = tower.pos
        self.graph.set_cell(row, col, Celltype.PATH)

        # Xóa tower khỏi danh sách
        if tower in self.towers:
            self.towers.remove(tower)

        # Xóa khỏi upgrade menus
        if tower in self.upgrade_menus:
            del self.upgrade_menus[tower]

        # Phá tháp làm rỗng stack_tower ngay lập tức
        self.stack_tower = CustomStack()
        self.undo_timer = 0

        # Recalculate path cho tower-seeking enemies
        for malware in self.malwares:
            malware._calculate_path()
            if hasattr(malware, 'attack_pos'):
                
                malware.state = "moving"
        if tower.hp>tower.max_hp//2:
            self.money+=refund
            import math
            range_tower=tower.range//(2)
            path_can_shoot=tower.path.keys()
           
            candidates = self.spatial_hash.query_range(tower.pos, tower.range)
            if isinstance(tower, FireNode):
                for malware in candidates:
                    
                    dist = math.sqrt((malware.pos[0] - tower.pos[0])**2 + (malware.pos[1] - tower.pos[1])**2)
                    if dist <= range_tower and not malware.is_dead():
                        malware.take_damage(tower.damage*0.5) 
                for cell in path_can_shoot :
                    if int(math.sqrt((cell[0] - tower.pos[0])**2 + (cell[1] - tower.pos[1])**2))<=range_tower:
                        fire_mark = FireMark(
                        pos=cell,
                        damage_per_sec=tower.damage*0.1,
                        duration=settings.TOWER_FIRE_DURATION*0.75
                    )
                        self.fire_marks.append(fire_mark)       
            if isinstance(tower, SpreadNode) or isinstance(tower, FreezeNode):
                    for malware in candidates:
                        dist = math.sqrt((malware.pos[0] - tower.pos[0])**2 + (malware.pos[1] - tower.pos[1])**2)
                        if dist <= range_tower and not malware.is_dead():
                            malware.take_damage(tower.damage*0.5)
                            malware.apply_slow(tower.slow_factor, tower.slow_duration)
        for t in self.towers:
            if t.is_destroyed(): continue
            t.path=t._path_can_shoot()
    def _handle_boss_destruction(self, cells: list):
        """Xử lý ô bị Final Boss phá: xóa tower nếu có, set PATH, spawn RiposteWare.

        Args:
            cells: List (row, col) từ Final.drain_spawn_queue()
        """
        from core.graph import Celltype
        path_changed = False
        for (r, c) in cells:
            tower = self._get_tower_at((r, c))
            if tower:
                if tower in self.upgrade_menus:
                    del self.upgrade_menus[tower]
                if self.active_upgrade_menu and self.active_upgrade_menu.tower == tower:
                    self.active_upgrade_menu = None
                if tower in self.towers:
                    self.towers.remove(tower)
            self.graph.set_cell(r, c, Celltype.PATH)
            path_changed = True
            # Spawn RiposteWare tại ô vừa bị phá
            rw = MALWARE_FACTORY["riposteware"]((r, c), self.graph)
            rw._calculate_path()
            rw.invisible = self.invisible_duration
            self.malwares.append(rw)
            self.spatial_hash.insert(rw)
        if path_changed:
            for m in self.malwares:
                m._calculate_path()
                if hasattr(m, 'attack_pos'):
                    m.state = "moving"
            for t in self.towers:
                if t.is_destroyed(): continue
                t.path=t._path_can_shoot()

    def undo(self):
        """Thực hiện hoàn tác việc đặt tháp cuối cùng."""
        if self.stack_tower.is_empty():
            return

        action = self.stack_tower.pop()
        if not action:
            return

        row, col = action["pos"]
        tower = action["tower"]
        cost = action["cost"]

        # Hoàn trả tiền
        self.money += cost

        # Xóa tháp khỏi danh sách towers và menus
        if tower in self.towers:
            self.towers.remove(tower)
        if tower in self.upgrade_menus:
            del self.upgrade_menus[tower]

        # Khôi phục lại ô lưới thành tường (WALL = 0)
        from core.graph import Celltype
        self.graph.set_cell(row, col, Celltype.WALL)

        # Tính toán lại đường đi cho quái và tầm bắn
        for m in self.malwares:
            m._calculate_path()
            if hasattr(m, 'attack_pos'):
                m.state = "moving"
        for t in self.towers:
            if t.is_destroyed(): continue
            t.path = t._path_can_shoot()

       
    def spawn_malware(self, malware_type: str, pos: tuple):
        """Tạo Malware theo loại và thêm vào game.

        Args:
            malware_type (str): Tên loại malware — "trojan", "worm", "spyware",
                hoặc "ransomware". Phải là key trong MALWARE_FACTORY.
            pos (tuple): Vị trí (row, col) ô lưới để spawn. Phải là ô PATH
                (get_spawn_weight() chỉ trả về ô PATH — luôn hợp lệ).

        Side effects:
            - Tạo instance Malware tương ứng tại pos với graph hiện tại.
            - Thêm malware vào self.malwares.
            - Đăng ký malware vào self.spatial_hash để tower có thể query.

        Note:
            Bỏ qua silently nếu malware_type không hợp lệ (không có trong MALWARE_FACTORY hoặc BOSS_FACTORY).
            Malware.__init__() tự tính path từ pos → server_pos (hoặc tower gần nhất)
            ngay khi khởi tạo.
            Boss.__init__() cũng tính path tương tự.
        """
        # Kiểm tra xem có phải boss không
        if malware_type in BOSS_FACTORY:
            BossClass = BOSS_FACTORY[malware_type]
            boss = BossClass(pos, self.graph)
            
            # Kỹ năng đặc biệt: Shadow/Final khiến mọi quái tàng hình vĩnh viễn
            if isinstance(boss, (Shadow, Final)):
                self.invisible_duration = 10**9
                self._stealth_notif_timer = 5.0
                for m in self.malwares:
                    m.invisible = self.invisible_duration

            self.bosses.append(boss)
            self.spatial_hash.insert(boss)  # Boss cũng cần để tower bắn được
            return

        # Ngược lại spawn malware
        MalwareClass = MALWARE_FACTORY.get(malware_type)
        if MalwareClass is None:
            return

        malware = MalwareClass(pos, self.graph)
        malware.invisible = self.invisible_duration  # kế thừa thời gian tàng hình còn lại
        self.malwares.append(malware)
        self.spatial_hash.insert(malware)
        pass

    # ------------------------------------------------------------------
    # VẼ
    # ------------------------------------------------------------------

    def draw(self):
        """Vẽ toàn bộ màn hình mỗi frame theo thứ tự layer từ dưới lên trên.

        Side effects:
            - Xóa frame trước bằng screen.fill(COLOR_BG).
            - Vẽ các layer theo thứ tự: grid → towers → malwares → projectiles → HUD → game_over.
            - Gọi pygame.display.flip() để hiển thị frame đã vẽ lên màn hình.

        Note:
            Thứ tự vẽ quan trọng — layer sau đè lên layer trước:
            grid (thấp nhất) → towers → malwares → projectiles → HUD (cao nhất).
            Pygame dùng double buffering — vẽ vào buffer ẩn, flip() swap lên màn hình
            để tránh nhấp nháy (flickering).
        """
        self.screen.fill(settings.COLOR_BG)
        self._draw_grid()

        self._draw_projectiles()
        self.right_panel.draw(self.screen)
        self._draw_hud()
        self._draw_countdown()
        self._draw_game_over()
        self._draw_tower_range()
        self._draw_upgrade_menus()
        self._draw_stealth_notif()
        self._draw_bomb_notif()
        pygame.display.flip()
        pass

    def _draw_tower_range(self):
        """Vẽ vòng tròn range của tower khi upgrade menu đang mở.
        
        Hiển thị bán kính tấn công của tower dưới dạng vòng tròn bán trong suốt.
        Giúp người chơi hình dung được tầm hoạt động của tower.
        """
        if self.active_upgrade_menu:
            tower = self.active_upgrade_menu.tower
            row, col = tower.pos

            # World coordinates
            world_x = col * settings.CELL_SIZE + settings.CELL_SIZE // 2
            world_y = row * settings.CELL_SIZE + settings.CELL_SIZE // 2

            # Convert to screen coordinates using camera
            center_x, center_y = self._world_to_screen(world_x, world_y)

            # Bán kính = range × CELL_SIZE
            radius = tower.range * settings.CELL_SIZE

            # Vẽ vòng tròn bán trong suốt (xanh dương)
            circle_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(circle_surf, (100, 150, 255, 80), (radius, radius), radius)
            pygame.draw.circle(circle_surf, (100, 150, 255, 150), (radius, radius), radius, 2)

            # Blit vòng tròn lên màn hình
            self.screen.blit(circle_surf, (center_x - radius, center_y - radius))

    def _draw_upgrade_menus(self):
        """Vẽ upgrade menus cho towers."""
        if self.active_upgrade_menu:
            self.active_upgrade_menu.draw(self.screen, self.money, self.camera_x, self.camera_y, self.current_level)
    def _draw_grid(self):
        """Hệ thống kết xuất (Render) Y-Sorting thống nhất cho Tường, Quái, Tháp
        
        Tất cả rendering đều áp dụng camera offset để hỗ trợ panning.
        """
        import random
        import pygame
        cs = settings.CELL_SIZE
        wall_surfs   = sprites.get("wall")
        path_surfs   = sprites.get("path")
        _tile_rng = random.Random(42)

        # 1. VẼ MẶT ĐẤT TRƯỚC (Layer nền dưới cùng) — với camera offset
        for row in range(self.graph.row):
            for col in range(self.graph.col):
                path_surf = _tile_rng.choices(path_surfs, k=1)[0]
                # Tọa độ thế giới, rồi áp dụng camera offset
                world_x = col * cs
                world_y = row * cs
                screen_x, screen_y = self._world_to_screen(world_x, world_y)
                
                # Chỉ vẽ nếu ô nằm trong viewport
                if -cs < screen_x < settings.SCREEN_WIDTH and -cs < screen_y < settings.SCREEN_HEIGHT:
                    self.screen.blit(path_surf, (screen_x, screen_y))

        # 2. KHỞI TẠO DANH SÁCH LAYER (Y-Sorting)
        render_list = []

        # 3. GOM TƯỜNG (Duyệt ma trận)
        _tile_rng = random.Random(42)
        for row in range(self.graph.row):
            for col in range(self.graph.col):
                wall_surf = _tile_rng.choices(wall_surfs, weights=[60,  36, 4], k=1)[0]
                cell = self.graph.get_cell(row, col)

                if cell == 0:
                    tall_factor = getattr(settings, 'TALL_FACTOR', 1.7)
                    tall_h = int(cs * tall_factor)

                    wall_3d = pygame.transform.scale(wall_surf, (cs, tall_h))

                    # Vẽ lớp đồ cháy nếu ô đang cháy
                    if getattr(self, 'burning_cells', None) and (row, col) in self.burning_cells:
                        fire_overlay = pygame.Surface((cs, tall_h), pygame.SRCALPHA)
                        fire_overlay.fill((255, 80, 0, 120))  # Màu cam đỏ bán trong suốt
                        wall_3d.blit(fire_overlay, (0, 0))

                    render_list.append({
                        'surf': wall_3d,
                        'pos': (col * cs, row * cs - (tall_h - cs)),
                        'sort_y': (row + 1) * cs,
                        'type': 'wall'
                    })

        # 4. GOM QUÁI VẬT (Malware) — bỏ qua nếu đang tàng hình ngoài radar
        for malware in self.malwares:
            if malware.invisible > 0 and not malware.is_radar_range:
                continue
            data = malware.get_render_data(cs)
            if data:
                render_list.append(data)

        # 4a. GOM BOSS
        for boss in self.bosses:
            data = boss.get_render_data(cs)
            if data:
                render_list.append(data)
            # Render bomb của FlyingDemon / Final
            if hasattr(boss, 'get_bombs'):
                for bomb in boss.get_bombs():
                    bdata = bomb.get_render_data(cs)
                    if bdata:
                        render_list.append(bdata)

        # 4b. GOM BOMB — animated idle/explode, Y-Sort aligned
        for bomb in self.bombs:
            data = bomb.get_render_data(cs)
            if data:
                render_list.append(data)

        # 5. GOM THÁP — bottom-center aligned, cùng hệ Y-sort với tường và quái
        for tower in self.towers:
            data = tower.get_render_data(cs)
            if data:
                render_list.append(data)

        # 5b. GOM SERVER — animated, Y-Sort aligned
        server_data = self.server.get_render_data(cs)
        if server_data:
            render_list.append(server_data)

        # 5c. GOM PORTAL — animated, một frame chung cho tất cả spawn points
        portal_frames = sprites.get("spawn")
        if portal_frames and self.portal:
            p_surf = portal_frames[self._portal_frame % len(portal_frames)]
            sw, sh = p_surf.get_size()
            for p_row, p_col in self.portal:
                if self._pre_wave: continue
                render_list.append({
                    'surf': p_surf,
                    'pos': (p_col * cs + (cs - sw) // 2, p_row * cs + cs - sh),
                    'sort_y': (p_row + 1) * cs,
                    'type': 'portal'
                })

        # 6. SẮP XẾP THEO TRỤC Y (Vũ khí bí mật của 3D)
        # Cái nào sort_y nhỏ (ở trên) vẽ trước, sort_y lớn (ở dưới) vẽ đè lên sau
        render_list.sort(key=lambda obj: obj['sort_y'])

        # 7. VẼ LÊN MÀN HÌNH — áp dụng camera offset cho mỗi object
        for item in render_list:
            # Tất cả items đều có 'pos': (world_x, world_y) trong pixel coordinates
            world_x, world_y = item['pos']
            screen_x, screen_y = self._world_to_screen(world_x, world_y)
            
            # Bỏ qua nếu nằm ngoài viewport (với margin)
            if screen_x < -200 or screen_x > settings.SCREEN_WIDTH + 200 or \
               screen_y < -200 or screen_y > settings.SCREEN_HEIGHT + 200:
                continue
            
            # Vẽ bóng đổ chung cho cả Quái và Tường
            shadow = pygame.Surface((cs, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 80), [0, 0, cs, 10])
            # Vẽ bóng ngay sát chân đối tượng (at sort_y level)
            _, shadow_screen_y = self._world_to_screen(0, item['sort_y'] - 5)
            self.screen.blit(shadow, (screen_x, shadow_screen_y))

            # Vẽ Surface tổng hợp
            self.screen.blit(item['surf'], (screen_x, screen_y))

            # Vẽ attack effect (FlyingDemon hào quang)
            if item.get('attack_effect'):
                fx = item['attack_effect']
                fx_world_x, fx_world_y = fx['pos']
                fx_screen_x, fx_screen_y = self._world_to_screen(fx_world_x, fx_world_y)
                self.screen.blit(fx['surf'], (fx_screen_x, fx_screen_y), special_flags=pygame.BLEND_RGBA_ADD)
                self.screen.blit(fx['surf'], (fx_screen_x, fx_screen_y), special_flags=pygame.BLEND_RGBA_ADD)

            # Vẽ warning circle + countdown cho bomb
            if item.get('type') == 'bomb':
                if item.get('warning'):
                    warning = item['warning']
                    # Chuyển warning pos sang screen coords
                    warn_world_x, warn_world_y = warning['pos']
                    warn_screen_x, warn_screen_y = self._world_to_screen(warn_world_x, warn_world_y)
                    
                    # Filled glow circle (phát sáng đỏ không nháy)
                    glow_radius = warning['radius']
                    glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
                    glow_color = (255, 80, 80, 180)  # Bright red glow
                    pygame.draw.circle(glow_surf, glow_color, (glow_radius, glow_radius), glow_radius)
                    self.screen.blit(glow_surf, (warn_screen_x - glow_radius, warn_screen_y - glow_radius))

                # Vẽ countdown text trên bomb
                if item.get('countdown'):
                    countdown_txt = self.font_big.render(item['countdown'], True, (255, 50, 50))  # Red text
                    txt_w, txt_h = countdown_txt.get_size()
                    txt_pos = (screen_x + item['surf'].get_width() // 2 - txt_w // 2,
                              screen_y - txt_h)
                    self.screen.blit(countdown_txt, txt_pos)

        # 8. VẼ HIỆU ỨNG TẤN CÔNG SPYWARE LÊN THÁP (sau Y-sort) — áp dụng camera offset
        attack_frames = sprites.get("spyware_attack")
        if attack_frames and len(attack_frames) > 0:
            # Kiểm tra từng spyware xem nó có đang tấn công tower nào không
            for malware in self.malwares:
                # Chỉ vẽ effect khi spyware đang tấn công tower
                has_state = hasattr(malware, 'state') and malware.state == "attacking_tower"
                has_target = hasattr(malware, '_attack_target_cell') and malware._attack_target_cell
                has_timer = hasattr(malware, 'attack_timer')

                if has_state and has_target and has_timer:
                    # Tính frame dựa trên attack_timer
                    frame_idx = int((malware.attack_timer / (1 / malware.attack_speed)) * len(attack_frames)) % len(attack_frames)
                    attack_frame = attack_frames[frame_idx]

                    # Vẽ effect tại tower cell (ô chứa tower đang bị tấn công) — với camera offset
                    tower_row, tower_col = malware._attack_target_cell
                    world_fx = tower_col * cs + cs // 2
                    world_fy = tower_row * cs + cs // 2
                    screen_fx, screen_fy = self._world_to_screen(world_fx, world_fy)
                    fw, fh = attack_frame.get_size()
                    self.screen.blit(attack_frame, (int(screen_fx) - fw // 2, int(screen_fy) - fh // 2))

        # 9. VẼ HIỆU ỨNG SLOW LÊN THÁP — áp dụng camera offset
        for tower in self.towers:
            if tower.slow_effect_stage:
                effect_frames = sprites.get(f"tower_slow_{tower.slow_effect_stage}")
                if effect_frames and isinstance(effect_frames, list) and len(effect_frames) > 0:
                    # Animate frames at 8 fps
                    timer_frames = int(tower.slow_effect_timer * 8)
                    if tower.slow_effect_stage == "active":
                        frame_idx = min(timer_frames, len(effect_frames) - 1)
                    else:
                        frame_idx = timer_frames % len(effect_frames)
                    effect_sprite = effect_frames[frame_idx]
                    tower_row, tower_col = tower.pos
                    world_fx = tower_col * cs + cs // 2
                    world_fy = tower_row * cs +  int(cs * 0.4)  # Lower below tower feet
                    screen_fx, screen_fy = self._world_to_screen(world_fx, world_fy)
                    fw, fh = effect_sprite.get_size()
                    self.screen.blit(effect_sprite, (int(screen_fx) - fw // 2, int(screen_fy) - fh // 2))

        # 9b. VẼ HIỆU ỨNG SLOW LÊN QUÁI VẬT (Malware) — áp dụng camera offset
        for malware in self.malwares:
            if hasattr(malware, 'slow_timer') and malware.slow_timer > 0:
                # Hiển thị slow effect quanh quái vật khi đang bị slow
                effect_frames = sprites.get("tower_slow_active")
                if effect_frames and isinstance(effect_frames, list) and len(effect_frames) > 0:
                    # Animate frames at 8 fps
                    timer_frames = int(malware.slow_timer * 8)
                    frame_idx = timer_frames % len(effect_frames)
                    effect_sprite = effect_frames[frame_idx]
                    # Vẽ effect quanh vị trí malware (tại cell của nó) — với camera offset
                    malware_row, malware_col = malware.pos
                    world_fx = malware_col * cs + cs // 2
                    world_fy = malware_row * cs + cs // 2
                    screen_fx, screen_fy = self._world_to_screen(world_fx, world_fy)
                    fw, fh = effect_sprite.get_size()
                    self.screen.blit(effect_sprite, (int(screen_fx) - fw // 2, int(screen_fy) - fh // 2))

        # 10. VẼ VẾT LỬA (Fire marks) — áp dụng camera offset
        fire_frames = sprites.get("fire_mark")
        if fire_frames and isinstance(fire_frames, list) and len(fire_frames) > 0:
            for mark in self.fire_marks:
                # Calculate animation frame based on progress
                progress = mark.elapsed_time / mark.duration
                if progress < 0.45:  # Appearing phase (frames 7-11)
                    frame_in_phase = int(progress / 0.45 * 5)  # 0-4
                    frame_idx = 7 + frame_in_phase
                else:  # Disappearing phase (frames 12-17)
                    frame_in_phase = int((progress - 0.45) / 0.55 * 6)  # 0-5
                    frame_idx = 12 + frame_in_phase

                frame_idx = min(frame_idx, len(fire_frames) - 1)
                fire_sprite = fire_frames[frame_idx]
                mark_row, mark_col = mark.pos
                world_fx = mark_col * cs + cs // 2
                world_fy = mark_row * cs 
                screen_fx, screen_fy = self._world_to_screen(world_fx, world_fy)
                fw, fh = fire_sprite.get_size()
                self.screen.blit(fire_sprite, (int(screen_fx) - fw // 2, int(screen_fy) - fh // 2))

        # 11. VẼ HIỆU ỨNG SHOCK TỪ LIGHTSPY — áp dụng camera offset
        shock_frames = sprites.get("shock_effect")
        if shock_frames and isinstance(shock_frames, list) and len(shock_frames) > 0:
            for shock in self.shock_effects:
                # shock.animation_frame là giá trị 8-14 từ ping-pong sequence
                # Cần map từ animation_frame sang index trong danh sách frame
                frame_idx = max(0, min(shock.animation_frame, len(shock_frames) - 1))
                shock_sprite = shock_frames[frame_idx]
                shock_row, shock_col = shock.pos
                world_fx = shock_col * cs
                world_fy = shock_row * cs
                screen_fx, screen_fy = self._world_to_screen(world_fx, world_fy)
                fw, fh = shock_sprite.get_size()
                self.screen.blit(shock_sprite, (int(screen_fx) - fw // 2, int(screen_fy) - fh // 1.5))

        # 12. VẼ HIỆU ỨNG STUN CỦA THÁP (12 FPS, chạy 1 lần nhanh) — áp dụng camera offset
        stun_frames = sprites.get("tower_stun")
        if stun_frames and isinstance(stun_frames, list) and len(stun_frames) > 0:
            stun_animation_fps = 12
            frame_duration = 1.0 / stun_animation_fps

            for tower in self.towers:
                if tower.stunned_timer > 0:
                    # Lấy elapsed time khi stun bắt đầu
                    elapsed = getattr(tower, '_stun_elapsed_time', 0.0)

                    # Tính frame dựa trên elapsed time (12 FPS)
                    frame_idx = int(elapsed / frame_duration)
                    frame_idx = min(frame_idx, len(stun_frames) - 1)

                    stun_sprite = stun_frames[frame_idx]
                    tower_row, tower_col = tower.pos
                    world_fx = tower_col * cs + cs // 2
                    world_fy = tower_row * cs
                    screen_fx, screen_fy = self._world_to_screen(world_fx, world_fy)
                    fw, fh = stun_sprite.get_size()
                    self.screen.blit(stun_sprite, (int(screen_fx) - fw // 2, int(screen_fy) - fh // 2))

    def _get_cell_color(self, cell_type: int) -> tuple:
        """Trả về màu RGB cho từng loại ô lưới.

        Args:
            cell_type (int): Giá trị CellType (Celltype.WALL, PATH, SERVER, SPAWN, TOWER).

        Returns:
            tuple: Màu RGB (r, g, b) tương ứng từ settings.
                WALL → COLOR_WALL, PATH → COLOR_PATH, SERVER → COLOR_SERVER,
                SPAWN → COLOR_SPAWN, TOWER → COLOR_WALL (tower vẽ riêng bằng Tower.draw()),
                Không nhận dạng được → COLOR_BG.
        """
        if cell_type == Celltype.WALL:
            return settings.COLOR_WALL
        elif cell_type == Celltype.PATH:
            return settings.COLOR_PATH
        elif cell_type == Celltype.SERVER:
            return settings.COLOR_SERVER
        elif cell_type == Celltype.SPAWN:
            return settings.COLOR_SPAWN
        elif cell_type == Celltype.TOWER:
            return settings.COLOR_WALL
        else:
            return settings.COLOR_BG
        pass



    def _draw_projectiles(self):
        """Vẽ tất cả đạn đang bay lên màn hình — với camera offset.

        Side effects:
            - Gọi proj.draw(screen, camera_offset_x, camera_offset_y) cho từng projectile.

        Note:
            Gọi sau _draw_grid() để đạn hiển thị trên đầu tất cả objects.
        """
        for proj in self.projectiles:
            # Truyền camera offset để projectile có thể vẽ đúng vị trí
            proj.draw(self.screen, self.camera_x, self.camera_y)
        pass

    def _draw_hud(self):
        """Vẽ thanh thông tin HUD ở dưới cùng màn hình.

        Side effects:
            - Vẽ nền HUD màu COLOR_HUD_BG từ y=SCREEN_HEIGHT-HUD_HEIGHT đến SCREEN_HEIGHT.
            - Hiển thị: tiền hiện tại, HP server, số wave hiện tại/tổng.
            - Hiển thị hướng dẫn phím (1=Basic, 2=Ice, 3=Radar, Ctrl+Z=Undo).
            - Hiển thị tên tower đang chọn bằng màu nổi bật.

        Note:
            HUD nằm trong vùng y = SCREEN_HEIGHT - HUD_HEIGHT → SCREEN_HEIGHT (fixed at bottom).
            Không bị ảnh hưởng bởi camera panning.
        """
        cs    = settings.CELL_SIZE
        hud_y = settings.SCREEN_HEIGHT - settings.HUD_HEIGHT
        W     = settings.SCREEN_WIDTH

        # Nền HUD có đường viền trên
        pygame.draw.rect(self.screen, (14, 14, 22), (0, hud_y, W, settings.HUD_HEIGHT))
        pygame.draw.line(self.screen, (0, 180, 200), (0, hud_y), (W, hud_y), 2)

        # --- Hàng trên: Money | Server HP | Wave ---
        top_y = hud_y + 8

        # Money icon (vàng)
        pygame.draw.circle(self.screen, (255, 210, 40), (18, top_y + 7), 7)
        pygame.draw.circle(self.screen, (200, 160, 0),  (18, top_y + 7), 7, 1)
        money_c = (255, 230, 80) if self.money >= 50 else (200, 80, 80)
        money_s = self.font.render(f"${self.money}", True, money_c)
        self.screen.blit(money_s, (30, top_y))

        # Server HP bar
        hp_x   = 140
        bar_w  = 160
        hp_rat = max(0.0, self.server.hp / self.server.max_hp)
        hp_col = (50, 220, 80) if hp_rat > 0.5 else (220, 180, 40) if hp_rat > 0.2 else (220, 50, 50)
        pygame.draw.rect(self.screen, (60, 20, 20),  (hp_x, top_y + 2, bar_w, 10))
        pygame.draw.rect(self.screen, hp_col,         (hp_x, top_y + 2, int(bar_w * hp_rat), 10))
        pygame.draw.rect(self.screen, (100, 100, 120),(hp_x, top_y + 2, bar_w, 10), 1)
        hp_s = self.font.render(f"SRV {self.server.hp}", True, settings.COLOR_HUD_TEXT)
        self.screen.blit(hp_s, (hp_x + bar_w + 6, top_y))

        # Wave
        total_waves = len(self.config["waves"])
        wave_c = (255, 180, 50)
        wave_s = self.font.render(f"WAVE {min(self.wave_index + 1, total_waves)}/{total_waves}", True, wave_c)
        self.screen.blit(wave_s, (W - wave_s.get_width() - 10, top_y))

        # --- Hàng dưới: Hint + selected tower ---
        bot_y = hud_y + 30
        hint  = self.font.render("[1] Basic  [2] Ice  [3] Radar  [4] Wall  ", True, (80, 80, 100))
        self.screen.blit(hint, (10, bot_y))

        if self.wall_placement_mode:
            # Wall placement mode
            if self.wall_cooldown_timer > 0:
                sel_col = (200, 100, 100)  # Red - cooldown active
                sel_s = self.font.render(f"▶ WALL (COOLDOWN {self.wall_cooldown_timer:.1f}s)", True, sel_col)
            else:
                sel_col = (100, 255, 150)  # Green - ready
                sel_s = self.font.render("▶ WALL (READY)", True, sel_col)
        else:
            # Tower placement mode
            name_map = {BasicNode: "BasicNode", IceWall: "IceWall", RadarNode: "RadarNode"}
            cost_map = {BasicNode: settings.TOWER_BASIC_COST,
                        IceWall:   settings.TOWER_ICE_COST,
                        RadarNode: settings.TOWER_RADAR_COST}
            sel_name = name_map.get(self.selected_tower, "?")
            sel_cost = cost_map.get(self.selected_tower, 0)
            enough   = self.money >= sel_cost
            sel_col  = (80, 200, 255) if enough else (180, 80, 80)
            sel_s    = self.font.render(f"▶ {sel_name} (${sel_cost})", True, sel_col)
        self.screen.blit(sel_s, (W - sel_s.get_width() - 10, bot_y))

    def _draw_countdown(self):
        """Vẽ countdown và thông báo Level ở giữa màn hình khi chờ wave."""
        if not self._pre_wave:
            return

        W = settings.SCREEN_WIDTH
        H = settings.SCREEN_HEIGHT
        countdown = max(0, int(self._pre_wave_timer) + 1)
        
        # 1. Vẽ thông báo Level
        level_txt = f"LEVEL {self.current_level}"
        level_surf = self.font_big.render(level_txt, True, (0, 255, 200)) # Cyan/Neon color
        wave_txt = f"WAVE IN {countdown}s"
        wave_surf = self.font.render(wave_txt, True, (255, 200, 0)) # Yellow

        # Tính toán vị trí tâm
        panel_w = max(level_surf.get_width(), wave_surf.get_width()) + 60
        panel_h = level_surf.get_height() + wave_surf.get_height() + 40
        px = (W - panel_w) // 2
        py = (H - panel_h) // 2

        # Vẽ panel nền mờ
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((0, 10, 20, 180)) # Dark blue transparent
        pygame.draw.rect(panel, (0, 200, 255), (0, 0, panel_w, panel_h), 2) # Border
        # Corner accents
        for ox, oy, dx, dy in [(0,0,1,1),(panel_w,0,-1,1),(0,panel_h,1,-1),(panel_w,panel_h,-1,-1)]:
            pygame.draw.line(panel, (0, 255, 255), (ox, oy), (ox+dx*15, oy), 2)
            pygame.draw.line(panel, (0, 255, 255), (ox, oy), (ox, oy+dy*15), 2)
        
        self.screen.blit(panel, (px, py))

        # Shadow and Text Level
        level_x = W // 2 - level_surf.get_width() // 2
        level_y = py + 15
        shadow_l = self.font_big.render(level_txt, True, (0, 0, 0))
        self.screen.blit(shadow_l, (level_x + 2, level_y + 2))
        self.screen.blit(level_surf, (level_x, level_y))

        # Shadow and Text Wave Countdown
        wave_x = W // 2 - wave_surf.get_width() // 2
        wave_y = level_y + level_surf.get_height() + 5
        shadow_w = self.font.render(wave_txt, True, (0, 0, 0))
        self.screen.blit(shadow_w, (wave_x + 1, wave_y + 1))
        self.screen.blit(wave_surf, (wave_x, wave_y))

    def _draw_game_over(self):
        """Vẽ màn hình kết thúc (Game Over/Victory) với phong cách chuyên nghiệp."""
        if self.game_over:
            title = "SYSTEM COMPROMISED"
            status = "CRITICAL BREACH DETECTED"
            color = (255, 40, 40)  # Neon Red
            glow = (150, 0, 0)
        elif self.victory:
            title = "THREAT NEUTRALIZED"
            status = "ALL MALWARE PURGED"
            color = (0, 255, 200)  # Cyan/Green
            glow = (0, 100, 80)
        else:
            return

        W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT

        # 1. Full-screen overlay with scanlines
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 5, 10, 200)) # Very dark blue tint
        # Add subtle scanlines
        for y in range(0, H, 4):
            pygame.draw.line(overlay, (0, 0, 0, 40), (0, y), (W, y))
        self.screen.blit(overlay, (0, 0))

        # 2. Main Panel
        pw, ph = 600, 200
        px, py = (W - pw) // 2, (H - ph) // 2

        # Panel Background with glow border
        panel_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel_surf.fill((10, 15, 25, 230))
        pygame.draw.rect(panel_surf, color, (0, 0, pw, ph), 2)
        
        # Glow effect
        glow_surf = pygame.Surface((pw + 20, ph + 20), pygame.SRCALPHA)
        for i in range(10):
            alpha = int(50 * (1 - i/10))
            pygame.draw.rect(glow_surf, (*color, alpha), (10-i, 10-i, pw+i*2, ph+i*2), 1)
        self.screen.blit(glow_surf, (px - 10, py - 10))
        self.screen.blit(panel_surf, (px, py))

        # 3. Decorative Elements (Corners)
        cl = 30 # Corner length
        for x, y, dx, dy in [(px, py, 1, 1), (px+pw, py, -1, 1), (px, py+ph, 1, -1), (px+pw, py+ph, -1, -1)]:
            pygame.draw.line(self.screen, color, (x, y), (x + dx*cl, y), 4)
            pygame.draw.line(self.screen, color, (x, y), (x, y + dy*cl), 4)

        # 4. Text Rendering
        # Title
        title_surf = self.font_big.render(title, True, color)
        # Add outer glow to title
        title_glow = self.font_big.render(title, True, glow)
        self.screen.blit(title_glow, ((W - title_surf.get_width()) // 2 + 2, py + 40 + 2))
        self.screen.blit(title_surf, ((W - title_surf.get_width()) // 2, py + 40))

        # Status
        status_surf = self.font.render(status, True, (200, 200, 255))
        self.screen.blit(status_surf, ((W - status_surf.get_width()) // 2, py + 100))

        # Instruction
        hint = "[ ESC ] TO TERMINATE SESSION"
        hint_surf = self.font.render(hint, True, (100, 100, 130))
        self.screen.blit(hint_surf, ((W - hint_surf.get_width()) // 2, py + 150))
        pass

    def _draw_stealth_notif(self):
        """Vẽ thông báo tàng hình trong 2 giây đầu khi đợt tàng hình kích hoạt."""
        if self._stealth_notif_timer <= 0:
            return

        W = settings.SCREEN_WIDTH
        secs = int(self.invisible_duration) + 1

        # Fade in 0.3s đầu, fade out 0.5s cuối
        t = self._stealth_notif_timer
        if t > 2.7:
            alpha = int((3.0 - t) / 0.3 * 255)
        elif t < 0.5:
            alpha = int(t / 0.5 * 255)
        else:
            alpha = 255
        alpha = max(0, min(255, alpha))

        line1 = "! STEALTH ACTIVATED !"
        line2 = f"Enemies invisible for ~{secs}s"

        pw, ph = 560, 110
        px = (W - pw) // 2
        py = 130

        # Panel
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((10, 0, 25, min(210, alpha)))
        pygame.draw.rect(panel, (180, 60, 240, alpha), (0, 0, pw, ph), 2)
        # Corner accents
        for ox, oy, dx, dy in [(0,0,1,1),(pw,0,-1,1),(0,ph,1,-1),(pw,ph,-1,-1)]:
            pygame.draw.line(panel, (180, 60, 240, alpha), (ox, oy), (ox+dx*16, oy), 2)
            pygame.draw.line(panel, (180, 60, 240, alpha), (ox, oy), (ox, oy+dy*16), 2)
        self.screen.blit(panel, (px, py))

        # Text dòng 1 — dùng font_big (36px)
        s1 = self.font_big.render(line1, True, (230, 110, 255))
        s1.set_alpha(alpha)
        self.screen.blit(s1, (px + (pw - s1.get_width()) // 2, py + 12))

        # Text dòng 2 — font thường 18px
        s2 = self.font.render(line2, True, (190, 150, 230))
        s2.set_alpha(alpha)
        self.screen.blit(s2, (px + (pw - s2.get_width()) // 2, py + 68))

    def _draw_bomb_notif(self):
        """Vẽ thông báo bomb xuất hiện trong 3 giây."""
        if self._bomb_notif_timer <= 0:
            return

        W = settings.SCREEN_WIDTH
        t = self._bomb_notif_timer
        if t > 2.7:
            alpha = int((3.0 - t) / 0.3 * 255)
        elif t < 0.5:
            alpha = int(t / 0.5 * 255)
        else:
            alpha = 255
        alpha = max(0, min(255, alpha))

        pw, ph = 560, 110
        px = (W - pw) // 2
        py = 260  # bên dưới stealth notif nếu cùng lúc

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((25, 10, 0, min(210, alpha)))
        pygame.draw.rect(panel, (240, 140, 30, alpha), (0, 0, pw, ph), 2)
        for ox, oy, dx, dy in [(0,0,1,1),(pw,0,-1,1),(0,ph,1,-1),(pw,ph,-1,-1)]:
            pygame.draw.line(panel, (240, 140, 30, alpha), (ox, oy), (ox+dx*16, oy), 2)
            pygame.draw.line(panel, (240, 140, 30, alpha), (ox, oy), (ox, oy+dy*16), 2)
        self.screen.blit(panel, (px, py))

        s1 = self.font_big.render("! BOMB INCOMING !", True, (255, 160, 40))
        s1.set_alpha(alpha)
        self.screen.blit(s1, (px + (pw - s1.get_width()) // 2, py + 12))

        s2 = self.font.render("A bomb has been dropped on the map", True, (220, 160, 80))
        s2.set_alpha(alpha)
        self.screen.blit(s2, (px + (pw - s2.get_width()) // 2, py + 68))

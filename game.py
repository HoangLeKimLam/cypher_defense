# game.py
# Lớp Game — trái tim của toàn bộ chương trình.
# Kết nối tất cả hệ thống: GridGraph, Malware, Tower, Projectile, SpatialHash.
# main.py chỉ làm một việc: tạo Game() và gọi game.run().

import json
import random
import pygame

import settings
import ui.sprites as sprites
from core.graph import GridGraph, Celltype
from core.data_structures import CustomStack
from entities.malware import Malware, Trojan, Worm, Spyware, Ransomware, TrojanRanged
from entities.tower import Tower, BasicNode, IceWall, RadarNode
from entities.projectile import Projectile
from systems.spatial_hash import SpatialHash


# Ánh xạ chuỗi từ JSON → class Malware tương ứng
MALWARE_FACTORY = {
    "trojan":     Trojan,
    "trojan_ranged": TrojanRanged,
    "worm":       Worm,
    "spyware":    Spyware,
    "ransomware": Ransomware,
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
        game_over (bool): True → server HP về 0, dừng update(), hiện "GAME OVER".
        victory (bool): True → hết tất cả wave, dừng update(), hiện "YOU WIN!".
        selected_tower (class): Loại tower đang chọn (BasicNode/IceWall/RadarNode).
        config (dict): Dữ liệu JSON của level hiện tại.
        graph (GridGraph): Bản đồ lưới — CellType, pathfinding, spawn weights.
        spatial_hash (SpatialHash): Tra cứu malware trong tầm bắn.
        malwares (list[Malware]): Tất cả malware đang sống trên map.
        towers (list[Tower]): Tất cả tower đã xây.
        projectiles (list[Projectile]): Tất cả đạn đang bay.
        undo_stack (CustomStack): Lịch sử xây tower để Ctrl+Z. Mỗi entry:
            {"pos": (row,col), "tower": Tower, "cost": int}.
        money (int): Tiền hiện tại của người chơi.
        server_hp (int): Máu server — mỗi malware đến server trừ 1, về 0 → game_over.
        wave_index (int): Chỉ số wave đang chạy (0-based, tính từ config["waves"]).
        spawn_queue (list[str]): Tên malware cần spawn trong wave hiện tại.
        spawn_timer (float): Đếm ngược (giây) đến lần spawn tiếp theo.
        spawn_interval (float): Khoảng cách giữa hai lần spawn (giây), từ JSON.
        font (pygame.font.Font): Font monospace 18px cho HUD.
        font_big (pygame.font.Font): Font monospace 36px cho màn hình kết thúc.

    Usage::

        game = Game()
        game.run()   # vòng lặp chính — block cho đến khi thoát
    """

    def __init__(self):
        """Khởi tạo pygame, tạo cửa sổ, và load level 1.

        Side effects:
            - Gọi pygame.init() để khởi tạo toàn bộ module pygame.
            - Tạo cửa sổ SCREEN_WIDTH × SCREEN_HEIGHT với tiêu đề "Cypher Defense".
            - Gọi self.load_level(1) để nạp bản đồ và khởi tạo tất cả trạng thái game.

        Note:
            Không viết logic game trực tiếp ở đây — tất cả nằm trong load_level().
            __init__ chỉ setup pygame và gọi load_level.
        """
        pygame.init()

        self.screen = pygame.display.set_mode(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        )
        sprites.init()   # phải sau set_mode() để convert_alpha() hoạt động

        pygame.display.set_caption("Cypher Defense")
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_over = False
        self.victory = False

        self.selected_tower = BasicNode

        # Animation timers (visual only)
        self._portal_timer = 0.0
        self._portal_frame = 0
        self._server_timer = 0.0
        self._server_frame = 0

        self.load_level(1)
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
        self.towers = []
        self.projectiles = []
        self.portal=[]
        self.undo_stack = CustomStack()
        self._pre_wave=True
        self._pre_wave_timer=settings.PRE_WAVE_DURATION
        self.money = self.config["start_money"]
        self.server_hp = settings.SERVER_MAX_HP

        self.wave_index = 0
        self.spawn_queue = []
        self.spawn_timer = 0.0
        self.spawn_interval = self.config["waves"][0]["interval_seconds"]
        self._start_wave(self.wave_index)
        self.font = pygame.font.SysFont("courier new", 18)
        self.font_big = pygame.font.SysFont("courier new", 36)
        pass

    def _start_wave(self, wave_index: int):
        """Nạp dữ liệu wave vào spawn_queue và đặt lại spawn timer.

        Args:
            wave_index (int): Chỉ số wave trong self.config["waves"] (0-based).

        Side effects:
            - Đặt self.victory = True và return nếu wave_index >= số lượng wave.
            - Nạp danh sách tên malware vào self.spawn_queue.
            - Cập nhật self.spawn_interval từ wave_data["interval_seconds"].
            - Reset self.spawn_timer về 0.0 để spawn ngay lập tức khi wave bắt đầu.

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
        self.spawn_queue = list(wave_data["enemies"])
        self.spawn_interval = wave_data["interval_seconds"]
        self.spawn_timer = 0.0
        pass

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

    def handle_events(self):
        """Xử lý tất cả sự kiện từ bàn phím và chuột trong frame hiện tại.

        Side effects:
            - Đặt self.running = False khi nhấn ESC hoặc đóng cửa sổ.
            - Gọi self.undo() khi nhấn Ctrl+Z.
            - Cập nhật self.selected_tower khi nhấn phím 1/2/3.
            - Gọi self.place_tower(row, col) khi click chuột trái vào vùng lưới.

        Note:
            Click chuột chỉ được xử lý khi my < GRID_ROWS * CELL_SIZE
            (trong vùng lưới, không phải thanh HUD phía dưới).
            Tọa độ ô: row = my // CELL_SIZE, col = mx // CELL_SIZE.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

                elif event.key == pygame.K_z and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    self.undo()

                elif event.key in TOWER_FACTORY:
                    self.selected_tower = TOWER_FACTORY[event.key]

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = pygame.mouse.get_pos()
                mx, my = pygame.mouse.get_pos()
                # Chỉ xử lý click trong vùng lưới (không phải HUD)
                if my < settings.GRID_ROWS * settings.CELL_SIZE:
                    row = my // settings.CELL_SIZE
                    col = mx // settings.CELL_SIZE
                    self.place_tower(row, col)
        pass

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
        if self._pre_wave:
            self._pre_wave_timer -= dt
            if self._pre_wave_timer <= 0:
                self._pre_wave = False
            return
    # KHÔNG gọi WaveSpawner.tick()
    # KHÔNG spawn malware
         # vẫn vẽ map, tháp, HUD
        
        self._update_spawner(dt)
        self._update_malwares(dt)
        self._update_towers(dt)
        self._update_projectiles(dt)
        self._check_wave_complete()
        self._update_animations(dt)
        pass

    def _update_animations(self, dt: float):
        """Cập nhật animation timer cho portal và server (visual only)."""
        self._portal_timer += dt
        if self._portal_timer >= 1.0 / settings.PORTAL_ANIM_FPS:
            self._portal_timer = 0.0
            self._portal_frame = (self._portal_frame + 1) % 14

        self._server_timer += dt
        if self._server_timer >= 1.0 / settings.SERVER_ANIM_FPS:
            self._server_timer = 0.0
            self._server_frame = (self._server_frame + 1) % 4
    def _update_spawner ( self, dt: float):
        
        """Xử lý logic spawn malware theo wave timer.

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Giảm self.spawn_timer mỗi frame.
            - Khi timer <= 0: reset timer, lấy tên malware đầu tiên từ spawn_queue,
              chọn vị trí spawn ngẫu nhiên có trọng số, gọi spawn_malware().

        Note:
            Dùng pop(0) thay vì pop() để spawn theo thứ tự trong JSON (FIFO).
            get_spawn_weight() trả về danh sách (weight, cell) — random.choices()
            chọn ngẫu nhiên có trọng số: malware khó spawn gần server hơn.
        """
        if not self.spawn_queue:
            return

        self.spawn_timer -= dt
        if self.spawn_timer > 0:
            return

        # Đến lúc spawn
        self.spawn_timer = self.spawn_interval

        malware_type = self.spawn_queue.pop(0)

        # Chọn vị trí spawn ngẫu nhiên có trọng số
        if not self.portal:
            return
        random.seed(None)
        chosen  = random.choices(self.portal, k=1)[0]

        self.spawn_malware(malware_type, chosen)
        pass

    def _update_malwares(self, dt: float):
        """Di chuyển tất cả malware và xử lý kết quả (chết hoặc đến server).

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Gọi malware.update(dt) để di chuyển từng malware.
            - Gọi spatial_hash.update_position() nếu malware đã di chuyển.
            - Trừ self.server_hp khi malware đến server; đặt game_over nếu về 0.
            - Cộng self.money += malware.reward khi malware chết.
            - Xóa malware đã chết hoặc đến server khỏi self.malwares và spatial_hash.
            - Collect projectiles từ ranged malware.

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
                    self.server_hp -= hit["dmg"]
                elif hit["type"]=="tower":
                    tower=self._get_tower_at(hit["cell"])
                    if tower:
                        tower.take_damage(hit["dmg"])
                        if tower.is_destroyed():
                            self._on_tower_destroyed(tower)
                malware.clear_pending_hit()

            if malware.has_reached_server():
                if self.server_hp <= 0:
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
        for m in self.malwares:
            m._calculate_path()
            if hasattr(m, 'attack_pos'):
                m.state = "moving"
    def _update_towers(self, dt: float):
        """Cho từng tower query SpatialHash, chọn mục tiêu, bắn Projectile.

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Gọi spatial_hash.query_range() để lấy candidates trong tầm bắn.
            - Gọi tower.update(dt, candidates) — trả về Projectile hoặc None.
            - Append Projectile vào self.projectiles nếu không None.

        Note:
            SpatialHash lọc candidates trong O(1) trung bình → chỉ xây Heap
            từ số ít malware gần tower. Nếu dùng toàn bộ self.malwares → Heap
            tốn kém không cần thiết.
        """
        for tower in self.towers:
            candidates = self.spatial_hash.query_range(tower.pos, tower.range)
            projectile = tower.update(dt, candidates)
            if projectile is not None:
                self.projectiles.append(projectile)
        pass

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

        self.projectiles = [p for p in self.projectiles if not p.has_hit()]
        pass

    def _check_wave_complete(self):
        """Kiểm tra xem wave hiện tại đã xong chưa để chuyển sang wave tiếp.

        Side effects:
            - Tăng self.wave_index và gọi _start_wave(wave_index) nếu wave xong.
            - _start_wave() sẽ đặt self.victory = True nếu hết tất cả wave.

        Note:
            Wave xong khi: spawn_queue rỗng (không còn malware cần spawn)
            VÀ self.malwares rỗng (tất cả malware đã chết hoặc đến server).
            Cả hai điều kiện phải thỏa đồng thời.
        """
        if len(self.spawn_queue) == 0 and len(self.malwares) == 0:
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
        TowerClass = self.selected_tower
        temp = TowerClass((row, col), self.graph)
        if self.money < temp.cost:
            return
        self.money -= temp.cost
        tower = temp
        self.graph.set_cell(row, col, Celltype.TOWER)
        self.towers.append(tower)
        self.undo_stack.push({"pos": (row, col), "tower": tower, "cost": temp.cost})
        for m in self.malwares:
            if hasattr(m, 'attack_pos'):
                m._calculate_path()
        pass

    def undo(self):
        """Hoàn tác hành động xây tower gần nhất (Ctrl+Z).

        Side effects:
            - Pop action từ undo_stack; return ngay nếu stack rỗng.
            - Đổi ô (row, col) từ TOWER → WALL trong GridGraph.
            - Xóa tower khỏi self.towers.
            - Hoàn trả tiền: self.money += cost.
            - Gọi _calculate_path() cho Spyware/Ransomware vì target tower vừa bị xóa.

        Note:
            Đây là ứng dụng trực tiếp của DSA Stack (CustomStack.pop()).
            Chỉ hoàn tác tower xây bởi người chơi trong session hiện tại —
            không hoàn tác được tower từ session trước hoặc di chuyển malware.
        """
        action = self.undo_stack.pop()
        if action is None:
            return
        row, col = action["pos"]
        tower = action["tower"]
        cost = action["cost"]
        self.graph.set_cell(row, col, Celltype.WALL)
        if tower in self.towers:
            self.towers.remove(tower)
        self.money += cost
        for m in self.malwares:
            if hasattr(m, 'attack_pos'):
                m._calculate_path()
        pass

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
            Bỏ qua silently nếu malware_type không hợp lệ (không có trong MALWARE_FACTORY).
            Malware.__init__() tự tính path từ pos → server_pos (hoặc tower gần nhất)
            ngay khi khởi tạo.
        """
        MalwareClass = MALWARE_FACTORY.get(malware_type)
        if MalwareClass is None:
            return

        malware = MalwareClass(pos, self.graph)
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
        self._draw_hud()
        self._draw_countdown()
        self._draw_game_over()
        pygame.display.flip()
        pass
    def _draw_grid(self):
        """Hệ thống kết xuất (Render) Y-Sorting thống nhất cho Tường, Quái, Tháp"""
        import random
        import pygame
        cs = settings.CELL_SIZE
        wall_surfs   = sprites.get("wall")
        path_surfs   = sprites.get("path")
        
        # 1. VẼ MẶT ĐẤT TRƯỚC (Layer nền dưới cùng)
        random.seed(42)
        for row in range(self.graph.row):
            for col in range(self.graph.col):
                path_surf = random.choices(path_surfs, k=1)[0]
                # Lưu ý: Luôn vẽ sàn, kể cả ở ô có tường để khi quái đi sau tường không bị lọt nền đen
                self.screen.blit(path_surf, (col * cs, row * cs))

        # 2. KHỞI TẠO DANH SÁCH LAYER (Y-Sorting)
        render_list = []

        # 3. GOM TƯỜNG (Duyệt ma trận)
        random.seed(42)
        for row in range(self.graph.row):
            for col in range(self.graph.col):
                wall_surf = random.choices(wall_surfs, weights=[60,  36, 4], k=1)[0]
                cell = self.graph.get_cell(row, col)
                
                if cell == 0:
                    # TẠO TƯỜNG GRADIENT: Ở đây tôi giả định bạn đã có hàm tạo 3D.
                    # Nếu bạn dùng code tạo gradient trước đó, hãy truyền wall_surf vào hàm đó.
                    # Dưới đây là code tạm tính toán vị trí Y.
                    tall_factor = getattr(settings, 'TALL_FACTOR', 1.7)
                    tall_h = int(cs * tall_factor)
                    
                    # Chỗ này thay bằng: wall_3d = self.create_gradient_wall(wall_surf, ...)
                    wall_3d = pygame.transform.scale(wall_surf, (cs, tall_h)) 

                    render_list.append({
                        'surf': wall_3d,
                        'pos': (col * cs, row * cs - (tall_h - cs)),
                        'sort_y': (row + 1) * cs, # Neo đáy tường
                        'type': 'wall'
                    })

        # 4. GOM QUÁI VẬT (Malware)
        for malware in self.malwares:
            data = malware.get_render_data(cs)
            if data:
                render_list.append(data)

        # 5. GOM THÁP — bottom-center aligned, cùng hệ Y-sort với tường và quái
        for tower in self.towers:
            data = tower.get_render_data(cs)
            if data:
                render_list.append(data)

        # 5b. GOM SERVER — animated, bottom-center aligned
        srv_row, srv_col = self.graph.server_pos
        server_frames = sprites.get("server")
        if server_frames:
            srv_surf = server_frames[self._server_frame % len(server_frames)]
            sw, sh = srv_surf.get_size()
            render_list.append({
                'surf': srv_surf,
                'pos': (srv_col * cs + (cs - sw) // 2, srv_row * cs + cs - sh),
                'sort_y': (srv_row + 1) * cs - 1,  # Render behind malware at same position
                'type': 'server'
            })

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

        # 7. VẼ LÊN MÀN HÌNH
        for item in render_list:
            # Vẽ bóng đổ chung cho cả Quái và Tường
            shadow = pygame.Surface((cs, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 80), [0, 0, cs, 10])
            # Vẽ bóng ngay sát chân đối tượng
            self.screen.blit(shadow, (item['pos'][0], item['sort_y'] - 5))
            
            # Vẽ Surface tổng hợp
            self.screen.blit(item['surf'], item['pos'])

 
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
        """Vẽ tất cả đạn đang bay lên màn hình.

        Side effects:
            - Gọi proj.draw(screen) cho từng projectile trong self.projectiles.

        Note:
            Gọi sau _draw_malwares() để đạn hiển thị trên đầu malware.
        """
        for proj in self.projectiles:
            proj.draw(self.screen)
        pass

    def _draw_hud(self):
        """Vẽ thanh thông tin HUD ở dưới cùng màn hình.

        Side effects:
            - Vẽ nền HUD màu COLOR_HUD_BG từ y=GRID_ROWS*CELL_SIZE đến SCREEN_HEIGHT.
            - Hiển thị: tiền hiện tại, HP server, số wave hiện tại/tổng.
            - Hiển thị hướng dẫn phím (1=Basic, 2=Ice, 3=Radar, Ctrl+Z=Undo).
            - Hiển thị tên tower đang chọn bằng màu nổi bật.

        Note:
            HUD nằm trong vùng y = GRID_ROWS*CELL_SIZE → SCREEN_HEIGHT.
            handle_events() không xử lý click chuột trong vùng này.
        """
        cs    = settings.CELL_SIZE
        hud_y = settings.GRID_ROWS * cs
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
        hp_rat = max(0.0, self.server_hp / settings.SERVER_MAX_HP)
        hp_col = (50, 220, 80) if hp_rat > 0.5 else (220, 180, 40) if hp_rat > 0.2 else (220, 50, 50)
        pygame.draw.rect(self.screen, (60, 20, 20),  (hp_x, top_y + 2, bar_w, 10))
        pygame.draw.rect(self.screen, hp_col,         (hp_x, top_y + 2, int(bar_w * hp_rat), 10))
        pygame.draw.rect(self.screen, (100, 100, 120),(hp_x, top_y + 2, bar_w, 10), 1)
        hp_s = self.font.render(f"SRV {self.server_hp}", True, settings.COLOR_HUD_TEXT)
        self.screen.blit(hp_s, (hp_x + bar_w + 6, top_y))

        # Wave
        total_waves = len(self.config["waves"])
        wave_c = (255, 180, 50)
        wave_s = self.font.render(f"WAVE {min(self.wave_index + 1, total_waves)}/{total_waves}", True, wave_c)
        self.screen.blit(wave_s, (W - wave_s.get_width() - 10, top_y))

        # --- Hàng dưới: Hint + selected tower ---
        bot_y = hud_y + 30
        hint  = self.font.render("[1] Basic  [2] Ice  [3] Radar  [Ctrl+Z] Undo", True, (80, 80, 100))
        self.screen.blit(hint, (10, bot_y))

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
        """Vẽ countdown ở giữa màn hình khi chờ wave."""
        if not self._pre_wave:
            return

        W = settings.SCREEN_WIDTH
        H = settings.SCREEN_HEIGHT
        countdown = max(0, int(self._pre_wave_timer) + 1)

        # Vẽ text lớn ở giữa màn hình
        countdown_s = self.font_big.render(f"WAVE IN {countdown}s", True, (255, 200, 0))
        mid_x = W // 2 - countdown_s.get_width() // 2
        mid_y = H // 2 - countdown_s.get_height() // 2

        # Shadow effect (vẽ đen phía dưới-phải)
        shadow = self.font_big.render(f"WAVE IN {countdown}s", True, (0, 0, 0))
        self.screen.blit(shadow, (mid_x + 3, mid_y + 3))

        # Text chính
        self.screen.blit(countdown_s, (mid_x, mid_y))

    def _draw_game_over(self):
        """Vẽ màn hình kết thúc nếu game_over hoặc victory.

        Side effects:
            - Return ngay nếu game vẫn đang chạy (không game_over và không victory).
            - Vẽ overlay đen bán trong suốt (alpha=150) phủ toàn màn hình.
            - Vẽ chữ "GAME OVER" (đỏ) hoặc "YOU WIN!" (xanh lá) ở giữa màn hình.
            - Vẽ hướng dẫn "Press ESC to quit" phía dưới chữ kết thúc.

        Note:
            Dùng pygame.SRCALPHA để tạo Surface với kênh alpha, cho phép overlay
            bán trong suốt mà không ảnh hưởng đến các layer bên dưới đã vẽ.
        """
        if self.game_over:
            text      = "// SYSTEM BREACHED //"
            sub_text  = "SERVER COMPROMISED"
            color     = (220, 50, 50)
            sub_color = (180, 30, 30)
        elif self.victory:
            text      = "// THREAT ELIMINATED //"
            sub_text  = "ALL WAVES REPELLED"
            color     = (50, 220, 100)
            sub_color = (30, 180, 80)
        else:
            return

        W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT

        # Overlay
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Panel box
        pw, ph = 480, 140
        px, py = (W - pw) // 2, (H - ph) // 2
        pygame.draw.rect(self.screen, (18, 18, 28), (px, py, pw, ph))
        pygame.draw.rect(self.screen, color,         (px, py, pw, ph), 2)
        # Corner accents
        for ox, oy, dx, dy in [(px,py,1,1),(px+pw,py,-1,1),(px,py+ph,1,-1),(px+pw,py+ph,-1,-1)]:
            pygame.draw.line(self.screen, color, (ox, oy), (ox+dx*12, oy),       2)
            pygame.draw.line(self.screen, color, (ox, oy), (ox,       oy+dy*12), 2)

        # Main text
        surf = self.font_big.render(text, True, color)
        self.screen.blit(surf, ((W - surf.get_width()) // 2, py + 20))

        # Sub text
        sub  = self.font.render(sub_text, True, sub_color)
        self.screen.blit(sub, ((W - sub.get_width()) // 2, py + 68))

        # Hint
        hint = self.font.render("Press ESC to quit", True, (100, 100, 120))
        self.screen.blit(hint, ((W - hint.get_width()) // 2, py + 98))
        pass

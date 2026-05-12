# entities/tower.py
# Định nghĩa tất cả loại Tower trong game.
# Tower ngồi trên ô WALL, bắn Malware đang đi trên PATH kề cạnh.

import random

import settings
import ui.sprites as sprites
from core.graph import GridGraph
from core.data_structures import CustomMinHeap, CustomMaxHeap, CustomQueue
from entities.malware import VaultWare

class Tower:
    """Lớp cơ sở cho tất cả Tower trong game.

    Tower ngồi trên ô WALL, bắn Malware đang đi trên PATH kề xung quanh.
    Subclass ghi đè stats và chiến lược bắn để tạo Tower có đặc tính riêng.

    Attributes:
        pos (tuple): Vị trí ô lưới (row, col) — luôn là ô WALL.
        graph (GridGraph): Tham chiếu GridGraph để kiểm tra vị trí.
        hp (int): Máu hiện tại của tower. Về 0 → tower bị phá hủy.
        max_hp (int): Máu tối đa — dùng tính tỉ lệ thanh máu khi vẽ.
        range (int): Bán kính tấn công (đơn vị: ô lưới).
        damage (int): Sát thương mỗi phát bắn.
        fire_rate (float): Số phát bắn mỗi giây.
        fire_timer (float): Bộ đếm thời gian tích lũy dt — khi >= 1/fire_rate thì bắn.
        cost (int): Tiền cần để xây tower này.
        color (tuple): Màu RGB hiển thị trên lưới.
        targeting (str): Chiến lược chọn mục tiêu — "min_dist" hoặc "max_hp".
        tower_type (str): Loại tower ("basic", "ice", "radar") — dùng cho sprite.
        path (dict): Tập hợp ô PATH có thể bị bắn (BFS từ pos).
        slow_timer (float): Bộ đếm thời gian tính bằng giây.
        stunned_timer (float): Bộ đếm thời gian tính bằng giây.
        prev_slow_timer (float): Lưu giá trị slow_timer của frame trước để theo dõi transitions.
        slow_effect_stage (str): "start", "active", "ending" — giai đoạn của hiệu ứng slow.
        slow_effect_timer (float): Bộ đếm thời gian cho hiệu ứng slow animation.
        prev_slow_effect_timer (float): Lưu giá trị slow_effect_timer của frame trước để theo dõi transitions.

    Usage:
        Không khởi tạo trực tiếp — dùng subclass BasicNode/IceWall/RadarNode.
        game.py tạo Tower khi người chơi click ô WALL::

            tower = BasicNode((row, col), graph)
            projectile = tower.update(dt, candidates)
    """

    def __init__(self, pos: tuple, graph: GridGraph, targeting="min_dist"):
        """Khởi tạo Tower tại vị trí pos với giá trị mặc định.

        Subclass ghi đè range, damage, fire_rate, cost, color, tower_type sau khi
        gọi super().__init__() để thiết lập stats riêng.

        Args:
            pos (tuple): (row, col) vị trí ô lưới — phải là ô WALL.
            graph (GridGraph): Bản đồ lưới, dùng để BFS tìm ô PATH có thể bắn.
            targeting (str): Chiến lược chọn mục tiêu mặc định: "min_dist"
                (nhắm kẻ gần server nhất). Subclass có thể truyền "max_hp".

        Side effects:
            - Gọi self._path_can_shoot() để tính sẵn tập hợp ô PATH trong tầm bắn.
        """
        self.pos = pos
        self.hp = settings.TOWER_BASIC_HP
        self.max_hp = self.hp
        self.graph = graph
        self.range = 3
        self.damage = 20
        self.fire_rate = 1.0
        self.original_fire_rate = self.fire_rate
        self.fire_timer = 0.0
        self.cost = 50
        self.color = settings.COLOR_TOWER_BASIC
        self.targeting = targeting
        self.tower_type = "basic"   # overridden by subclass
        self.path = self._path_can_shoot()
        self.slow_timer = 0.0
        self.stunned_timer = 0.0
        self.burn_timer = 0.0
        self.burn_damage_per_sec = 0.0
        self.prev_slow_timer = 0.0  # Track previous slow state for transitions
        self.slow_effect_stage = None  # "start", "active", or "ending"
        self.slow_effect_timer = 0.0  # Timer for effect animation
        

    def update(self, dt: float, candidates: list):
        """Cập nhật cooldown và bắn nếu đến lượt.

        Args:
            dt (float): Thời gian frame tính bằng giây.
            candidates (list): Danh sách Malware trong tầm bắn (từ SpatialHash).
                Nếu danh sách rỗng → không bắn.

        Returns:
            Projectile: Đạn vừa bắn ra nếu đến lượt và có mục tiêu.
            None: Nếu chưa đến cooldown hoặc không có mục tiêu hợp lệ.

        Side effects:
            - Tích lũy self.fire_timer mỗi frame.
            - Reset self.fire_timer về 0 mỗi lần bắn để fire_rate luôn chính xác.
        """
        if self.stunned_timer > 0:
            if not hasattr(self, '_stun_elapsed_time'):
                self._stun_elapsed_time = 0.0
            self._stun_elapsed_time += dt
            self.stunned_timer -= dt
            if self.stunned_timer <= 0:
                self.stunned_timer = 0
            else: return None  # Nếu đang bị stun, không làm gì cả
                
        # Process burn effect
        if getattr(self, 'burn_timer', 0) > 0:
            self.take_damage(self.burn_damage_per_sec * dt)
            self.burn_timer -= dt
            if self.burn_timer <= 0:
                self.burn_timer = 0.0
                self.burn_damage_per_sec = 0.0

        # Track if we had slow before this frame
        was_slow = self.prev_slow_timer > 0

        # Decrement slow timer
        self.slow_timer -= dt
        if self.slow_timer <= 0:
            self.slow_timer = 0
            self.fire_rate = self.original_fire_rate

        # Check slow state AFTER decrement
        is_slow = self.slow_timer > 0

        # Update effect timer
        if self.slow_effect_stage:
            self.slow_effect_timer += dt

        # State transitions
        if not was_slow and is_slow:
            # Transition: 0 → slow: START effect (only on initial slow)
            self.slow_effect_stage = "start"
            self.slow_effect_timer = 0.0
        elif self.slow_effect_stage == "start":
            # Transition from start → active when timer threshold reached
            if self.slow_effect_timer >= 9 / 8.0:
                self.slow_effect_stage = "active"
        elif self.slow_effect_stage == "active":
            # Stay in active while slow is active, transition to ending when it ends
            if not is_slow:
                self.slow_effect_stage = "ending"
                self.slow_effect_timer = 0.0
        elif self.slow_effect_stage == "ending":
            # Ending animation running
            if self.slow_effect_timer >= 18 / 8.0:
                self.slow_effect_stage = None

        self.prev_slow_timer = self.slow_timer
        self.fire_timer += dt
        cooldown = 1.0 / self.fire_rate
        if self.fire_timer >= cooldown:
            self.fire_timer = 0.0
            target = self._find_target(candidates)
            if target is not None:
                return self.shoot(target)
        return None

    def apply_burn(self, damage_per_sec: float, duration: float):
        """Áp dụng hiệu ứng đốt cháy (DOT) lên tower.

        Args:
            damage_per_sec (float): Sát thương phải chịu mỗi giây.
            duration (float): Thời gian kéo dài của hiệu ứng.
        """
        self.burn_damage_per_sec = damage_per_sec
        # Không cộng dồn, chỉ lấy thời gian lớn nhất nếu đang bị đốt
        self.burn_timer = max(getattr(self, 'burn_timer', 0), duration)

    def apply_slow(self, factor: float, duration: float):
        """Áp dụng hiệu ứng slow lên tower

        Args:
            factor (float): Hệ số nhân tốc độ khi bị slow (0.5 = còn 50%).
            duration (float): Thời gian hiệu ứng slow tính bằng giây.

        Side effects:
            - Cộng dồn hiệu ứng slow nếu bị tấn công nhiều lần.
            - Khi self.slow_timer > 0 → tower bị slow, fire_rate giảm theo factor.
            - Khi self.slow_timer <= 0 → tower hết slow, fire_rate trở lại bình thường.
        """
        self.slow_timer += duration
        self.fire_rate = self.original_fire_rate * factor
    def apply_stun(self, duration: float):
        """Áp dụng hiệu ứng stun lên tower

        Args:
            duration (float): Thời gian hiệu ứng stun tính bằng giây.

        Side effects:
            - Cộng dồn hiệu ứng stun nếu bị tấn công nhiều lần.
            - Khi self.stunned_timer > 0 → tower bị stun
            - Khi self.stunned_timer <= 0 → tower hết stun
        """
        if self.stunned_timer <= 0:
            self._stun_elapsed_time = 0.0
        self.stunned_timer += duration
    def _path_can_shoot(self) -> dict:
        """Tính tập hợp tất cả ô PATH có thể bị tower này bắn (BFS từ pos).

        Dùng BFS lan ra từ các ô láng giềng của tower để tìm mọi ô PATH
        kết nối. Tower chỉ bắn malware đang đứng trên một trong các ô này.

        Returns:
            dict: {(row, col): True} — tập hợp ô PATH trong phạm vi bắn.
                Dùng dict thay set để tra cứu O(1) trong _find_target().

        Side effects:
            - Kết quả lưu vào self.path khi __init__ gọi phương thức này.
        """
        store = CustomQueue()
        res = {}
        for neibour in self.graph.get_neighbors(*self.pos):
            store.enqueue(neibour)
            res[neibour] = True
        while not store.is_empty():
            current = store.dequeue()
            for neibour in self.graph.get_neighbors(*current):
                if not res.get(neibour, False):
                    store.enqueue(neibour)
                    res[neibour] = True
        return res

    def take_damage(self, damage: int) -> None:
        """Trừ máu tower khi bị malware tấn công.

        Args:
            damage (int): Lượng sát thương cần trừ (>= 0).

        Side effects:
            - Giảm self.hp. Gọi is_destroyed() để kiểm tra sau khi take_damage().
        """
        self.hp -= damage

    def is_destroyed(self) -> bool:
        """Kiểm tra tower đã bị phá hủy chưa.

        Returns:
            bool: True nếu self.hp <= 0, False nếu còn sống.
        """
        return self.hp <= 0
    def _find_target(self, candidates: list):
        """Chọn mục tiêu tối ưu từ danh sách candidates bằng Heap (DSA).

        Chiến lược ưu tiên (theo thứ tự):
            1. VaultWare (cao nhất - trừ khi không dính attraction 50/50)
            2. Bomb (sau khi check xong VaultWare)
            3. Malware khác theo targeting strategy (min_dist hoặc max_hp)

        Args:
            candidates (list): Danh sách Malware + Bomb từ spatial hash.

        Returns:
            VaultWare | Bomb | Malware: Mục tiêu được chọn, hoặc None nếu không có.

        Note:
            Dùng Heap thay sort() để thể hiện ứng dụng DSA heap trong game thực tế.
        """
        from entities.bomb import Bomb

        filler_cadidates = []
        vaultware_target = None
        bomb_target = None

        # Một lần loop: check VaultWare, Bomb, lọc malware khác
        for candidate in candidates:
            # Ưu tiên 1: VaultWare (nếu đứng trong path)
            if isinstance(candidate, VaultWare) and candidate.pos in self.path:
                if random.random() < 0.75 and vaultware_target is None:  # 75% phát hiện
                    vaultware_target = candidate

            # Ưu tiên 2: Bomb (nếu chưa nổ)
            elif isinstance(candidate, Bomb) and not candidate.is_exploded() and bomb_target is None:
                bomb_target = candidate

            # Ưu tiên 3: Malware khác (lọc để xây heap)
            elif candidate.pos in self.path and not isinstance(candidate, Bomb):
                filler_cadidates.append(candidate)

        # Return theo thứ tự ưu tiên
        if vaultware_target is not None:
            return vaultware_target
        if bomb_target is not None:
            return bomb_target

        # Heap cho malware còn lại
        if self.targeting == "min_dist":
            heap = CustomMinHeap()
            for candidate in filler_cadidates:
                if not candidate.is_dead():
                    dist = abs(candidate.pos[0] - self.graph.server_pos[0]) + abs(candidate.pos[1] - self.graph.server_pos[1])
                    heap.push((dist, candidate))
            result = heap.pop()
            return result[1] if result else None
        else:
            heap = CustomMaxHeap()
            for candidate in filler_cadidates:
                if not candidate.is_dead():
                    heap.push((candidate.hp, candidate))
            result = heap.pop()
            return result[1] if result else None

    def shoot(self, target):
        """Bắn vào mục tiêu — tạo và trả về Projectile.

        Args:
            target (Malware): Đối tượng Malware đang bị nhắm bắn.

        Returns:
            Projectile: Đạn mới tạo ra, bay từ pos của tower đến target.

        Note:
            Import Projectile bên trong hàm để tránh circular import
            (projectile.py import settings, không import tower.py).
            Projectile chứa tham chiếu đến target — Projectile.update()
            kiểm tra target.is_dead() trước khi gây damage.
        """
        from entities.projectile import Projectile
        return Projectile(
            source_pos=self.pos,
            target=target,
            damage=self.damage,
            speed=settings.PROJECTILE_SPEED,
            tower_type=self.tower_type,
            source_tower=self,
        )

    def draw(self, screen, cell_size: int):
        """Vẽ Tower lên màn hình — sprite hoặc fallback hình tròn.

        Dùng sprite từ cache (key: "tower_{tower_type}") nếu có.
        Nếu không tìm được sprite → vẽ hình tròn màu self.color làm fallback.

        Args:
            screen (pygame.Surface): Bề mặt màn hình game, do game.py truyền vào.
            cell_size (int): Kích thước pixel mỗi ô lưới (settings.CELL_SIZE).

        Note:
            Quy đổi tọa độ: pixel_x = col * cell_size, pixel_y = row * cell_size.
            Phương thức này ít dùng trực tiếp — game._draw_grid() dùng
            get_render_data() thay thế để hỗ trợ Y-sorting.
        """
        import pygame
        px = self.pos[1] * cell_size
        py = self.pos[0] * cell_size
        key = f"tower_{self.tower_type}"
        surf = sprites.get(key)
        if surf:
            screen.blit(surf, (px, py))
        else:
            mid = cell_size // 2
            pygame.draw.circle(screen, self.color, (px + mid, py + mid), cell_size // 4)

    def get_render_data(self, cell_size: int):
      """Trả về dict render-data để Y-sort trong _draw_grid(), bottom-center aligned + HP bar.

      Tạo Surface tổng hợp (sprite + HP bar nếu bị damage), tính vị trí vẽ
      bottom-center aligned theo hệ Y-sorting của game._draw_grid().

      Args:
          cell_size (int): Kích thước pixel mỗi ô lưới (settings.CELL_SIZE).

      Returns:
          dict: {"surf": Surface, "pos": (x,y), "sort_y": int, "type": "tower"}
              dùng để xếp vào render_list và sort theo sort_y trước khi vẽ.
              None nếu sprite không tìm được trong cache.
      """
      import pygame
      cs = cell_size
      row, col = self.pos
      px = col * cs
      py = row * cs
      key = f"tower_{self.tower_type}"
      surf = sprites.get(key)
      if surf is None:
          return None
      sw, sh = surf.get_size()
      import settings as _s
      tall_h    = int(cs * getattr(_s, 'TALL_FACTOR', 1.6))
      foot_push = tall_h - cs

      # Tạo surface tổng hợp: cao thêm 10px để chứa HP bar phía trên
      final_surf = pygame.Surface((sw, sh + 10), pygame.SRCALPHA)
      final_surf.blit(surf, (0, 10))

      # Vẽ HP bar nếu tower bị damage
      if self.hp < self.max_hp:
          bar_w = max(cs - 4, sw - 4)
          hp_r  = max(0.0, self.hp / self.max_hp)
          bx    = (sw - bar_w) // 2
          by    = 2
          hp_col = (50, 210, 70) if hp_r > 0.5 else (220, 180, 40) if hp_r > 0.25 else (220, 50, 50)
          pygame.draw.rect(final_surf, (60, 10, 10), (bx, by, bar_w, 3))
          pygame.draw.rect(final_surf, hp_col,       (bx, by, int(bar_w * hp_r), 3))

      draw_x = px + (cs - sw) // 2
      draw_y = py + cs - sh + foot_push - 10
      return {
          'surf': final_surf,
          'pos': (draw_x, draw_y),
          'sort_y': (row + 1) * cs,
          'type': 'tower'
      }


# ---------------------------------------------------------------------------
# Subclasses
# ---------------------------------------------------------------------------

class BasicNode(Tower):
    """Tower cơ bản — single target, damage trung bình, giá rẻ nhất.

    Chiến lược: nhắm kẻ gần Server nhất (targeting = "min_dist").
    Thích hợp khi người chơi mới bắt đầu, chưa đủ tiền mua tower xịn hơn.

    Attributes:
        Kế thừa từ Tower. Stats lấy từ settings:
        TOWER_BASIC_RANGE, TOWER_BASIC_DAMAGE, TOWER_BASIC_FIRE_RATE,
        TOWER_BASIC_COST, TOWER_BASIC_HP.

    Usage:
        Tạo khi người chơi nhấn phím [1] rồi click ô WALL::

            tower = BasicNode((row, col), graph)
    """

    def __init__(self, pos: tuple, graph: GridGraph, targeting="min_dist"):
        """Khởi tạo BasicNode: gọi super().__init__, ghi đè stats BasicNode.

        Args:
            pos (tuple): (row, col) vị trí ô WALL.
            graph (GridGraph): Bản đồ lưới.
            targeting (str): Chiến lược chọn mục tiêu. Mặc định "min_dist".
        """
        super().__init__(pos, graph)
        self.range      = settings.TOWER_BASIC_RANGE
        self.damage     = settings.TOWER_BASIC_DAMAGE
        self.fire_rate  = settings.TOWER_BASIC_FIRE_RATE
        self.original_fire_rate = self.fire_rate
        self.cost       = settings.TOWER_BASIC_COST
        self.color      = settings.COLOR_TOWER_BASIC
        self.targeting  = targeting
        self.hp         = settings.TOWER_BASIC_HP
        self.max_hp     = self.hp
        self.tower_type = "basic"


class IceWall(Tower):
    """Tower làm chậm — damage thấp nhưng áp dụng slow effect lên mục tiêu.

    Sau khi bắn: gọi target.apply_slow(factor, duration) để giảm tốc độ Malware
    trong slow_duration giây. Kết hợp với BasicNode để tiêu diệt kẻ cứng nhất.

    Attributes:
        slow_factor (float): Hệ số nhân tốc độ khi bị đóng băng (0.5 = còn 50%).
        slow_duration (float): Thời gian hiệu ứng slow tính bằng giây.
        Kế thừa từ Tower. Stats lấy từ settings: TOWER_ICE_*.

    Usage:
        Tạo khi người chơi nhấn phím [2] rồi click ô WALL::

            tower = IceWall((row, col), graph)
    """

    def __init__(self, pos: tuple, graph: GridGraph, targeting="min_dist"):
        """Khởi tạo IceWall: gọi super().__init__, ghi đè stats IceWall.

        Args:
            pos (tuple): (row, col) vị trí ô WALL.
            graph (GridGraph): Bản đồ lưới.
            targeting (str): Chiến lược chọn mục tiêu. Mặc định "min_dist".
        """
        super().__init__(pos, graph)
        self.range         = settings.TOWER_ICE_RANGE
        self.damage        = settings.TOWER_ICE_DAMAGE
        self.fire_rate     = settings.TOWER_ICE_FIRE_RATE
        self.original_fire_rate = self.fire_rate
        self.cost          = settings.TOWER_ICE_COST
        self.color         = settings.COLOR_TOWER_ICE
        self.targeting     = targeting
        self.slow_factor   = settings.TOWER_ICE_SLOW_FACTOR
        self.slow_duration = settings.TOWER_ICE_SLOW_DURATION
        self.hp            = settings.TOWER_ICE_HP
        self.max_hp        = self.hp
        self.tower_type    = "ice"

    def shoot(self, target):
        """Bắn và áp dụng slow effect lên mục tiêu trước khi tạo đạn.

        Args:
            target (Malware): Đối tượng Malware đang bị nhắm bắn.

        Returns:
            Projectile: Đạn mới tạo ra (kế thừa từ Tower.shoot()).

        Side effects:
            - Gọi target.apply_slow(slow_factor, slow_duration) ngay lập tức.
              Hiệu ứng làm chậm áp dụng trước khi đạn bay tới.

        Note:
            apply_slow() TRƯỚC super().shoot() — slow áp dụng ngay khi bắn,
            không chờ đạn chạm target (thiết kế game Week 2).
        """
        from entities.projectile import Projectile
        proj = Projectile(
            source_pos=self.pos,
            target=target,
            damage=self.damage,
            speed=settings.PROJECTILE_SPEED,
            tower_type="ice",
            slow_factor=self.slow_factor,
            slow_duration=self.slow_duration,
            source_tower=self
        )
        return proj


class RadarNode(Tower):
    """Tower chỉ dò map — range lớn nhất, KHÔNG bắn đạn.

    Vai trò trong game: đặt ở vị trí chiến lược để SpatialHash.query_range()
    có thể "nhìn thấy" malware từ xa hơn, hỗ trợ các tower khác nhắm mục tiêu.
    shoot() bị override để luôn trả về None → game.py không tạo Projectile.

    Attributes:
        Kế thừa từ Tower. Stats lấy từ settings: TOWER_RADAR_RANGE,
        TOWER_RADAR_COST, TOWER_RADAR_HP. Không có damage/fire_rate riêng.

    Usage:
        Tạo khi người chơi nhấn phím [3] rồi click ô WALL::

            tower = RadarNode((row, col), graph)
    """

    def __init__(self, pos: tuple, graph: GridGraph, targeting="min_dist"):
        """Khởi tạo RadarNode: gọi super().__init__, ghi đè stats RadarNode.

        Args:
            pos (tuple): (row, col) vị trí ô WALL.
            graph (GridGraph): Bản đồ lưới.
            targeting (str): Chiến lược chọn mục tiêu. Mặc định "min_dist".
        """
        super().__init__(pos, graph)
        self.range      = settings.TOWER_RADAR_RANGE
        self.cost       = settings.TOWER_RADAR_COST
        self.color      = settings.COLOR_TOWER_RADAR
        self.hp         = settings.TOWER_RADAR_HP
        self.max_hp     = self.hp
        self.targeting  = targeting
        self.tower_type = "radar"
        self.tick_timer = 0.0 # Thêm bộ đếm cho cơ chế tự tiêu hao HP

    def shoot(self, target):
        """Override để vô hiệu hóa bắn — luôn trả về None.

        Args:
            target (Malware): Mục tiêu (không dùng — RadarNode không bắn).

        Returns:
            None: Luôn trả về None để game.py bỏ qua, không tạo Projectile.

        Note:
            game.py kiểm tra "if projectile is not None" trước khi append →
            RadarNode chỉ dò map, không bắn đạn.
        """
        return None

    def update(self, dt: float, candidates: list):
        """Cập nhật RadarNode: xử lý slow/stun/burn rồi tự trừ 5 HP mỗi giây.

        Args:
            dt (float): Thời gian frame tính bằng giây.
            candidates (list): Danh sách Malware trong tầm (không dùng — RadarNode không bắn).

        Returns:
            None: RadarNode không bắn projectile.

        Side effects:
            - Gọi super().update() để xử lý slow, stun, burn.
            - Tích lũy tick_timer; trừ 5 HP khi tick_timer >= 1.0 giây.
        """
        super().update(dt, candidates)
        self.tick_timer += dt
        if self.tick_timer >= 1.0:
            self.tick_timer = 0.0
            self.take_damage(5) # Tháp tự trừ máu chính mình 5HP mỗi giây
        return None

class SpeedNode(BasicNode):
    """Tower tăng tốc — bắn liên thanh với tốc độ cao nhất.

    Kế thừa từ BasicNode nhưng với fire_rate nhanh gấp 5 lần. Dùng để tiêu diệt
    nhanh những mục tiêu yếu hoặc đám quái.

    Attributes:
        Kế thừa từ BasicNode. Nâng cấp fire_rate (5.0 phát/giây), damage thấp hơn BasicNode.

    Usage:
        Tạo khi người chơi nâng cấp tháp BasicNode (từ nhánh Tăng Tốc Đánh I) lên SpeedNode trong UpgradeTree:

            tower = SpeedNode((row, col), graph)
    """

    def __init__(self, pos: tuple, graph: GridGraph, targeting="min_dist"):
        """Khởi tạo SpeedNode: gọi super().__init__, ghi đè stats SpeedNode.

        Args:
            pos (tuple): (row, col) vị trí ô WALL.
            graph (GridGraph): Bản đồ lưới.
            targeting (str): Chiến lược chọn mục tiêu. Mặc định "min_dist".
        """
        super().__init__(pos, graph, targeting)
        self.range      = settings.TOWER_SPEED_RANGE
        self.damage     = settings.TOWER_SPEED_DAMAGE
        self.fire_rate  = settings.TOWER_SPEED_FIRE_RATE
        self.original_fire_rate = self.fire_rate
        self.cost       = settings.TOWER_SPEED_COST
        self.hp         = settings.TOWER_SPEED_HP
        self.max_hp     = self.hp
        self.tower_type = "speed"
class FireNode(BasicNode):
    """Tower lửa — bắn tạo ô lửa lại vị trí quái đang đứng tồn tại trong vài giây, gây sát thương lâu dài, hiệu ứng đốt các quái đi qua.

    Attributes:
        Kế thừa từ BasicNode. Thêm skill bắn ra "vết lửa" tồn tại vài giây tại vị trí quái trúng đạn, gây sát thương theo thời gian lên quái đứng trên đó và quái đi qua. Stats vết lửa lấy từ settings: FIRE_DAMAGE, TOWER_FIRE_DURATION.

    Usage:
        Tạo khi người chơi nâng cấp tháp BasicNode ( từ nhánh nâng cấp damage) lên FireNode trong UpgradeTree:

            tower = FireNode((row, col), graph)
    """

    def __init__(self, pos: tuple, graph: GridGraph, targeting="min_dist"):
        """Khởi tạo FireNode: gọi super().__init__, ghi đè stats FireNode.

        Args:
            pos (tuple): (row, col) vị trí ô WALL.
            graph (GridGraph): Bản đồ lưới.
            targeting (str): Chiến lược chọn mục tiêu. Mặc định "min_dist".
        """
        super().__init__(pos, graph, targeting)
        self.range      = settings.TOWER_FIRE_RANGE
        self.damage     = settings.TOWER_FIRE_DAMAGE
        self.fire_rate  = settings.TOWER_FIRE_FIRE_RATE
        self.original_fire_rate = self.fire_rate
        self.cost       = settings.TOWER_FIRE_COST
        self.hp         = settings.TOWER_FIRE_HP
        self.max_hp     = self.hp
        self.fire_duration = settings.TOWER_FIRE_DURATION
        self.fire_damage = settings.FIRE_DAMAGE_PER_SEC
        self.tower_type = "fire"

    def shoot(self, target):
        """Override BasicNode.shoot() để bắn ra lửa.

        Args:
            target (Malware): Mục tiêu được bắn.

        Returns:
            Projectile: Đạn lửa bay từ tower đến target.
        """
        from entities.projectile import Projectile

        proj = Projectile(
            source_pos=self.pos,
            target=target,
            damage=self.damage,
            speed=settings.PROJECTILE_SPEED,
            tower_type="fire",
            source_tower=self
        )
        return proj
class SniperNode(BasicNode):
    """Tower xạ thủ — bắn sát thương cao nhưng đơn mục tiêu, tốc độ chậm.

    Kế thừa từ BasicNode nhưng với damage cao gấp đôi (40 vs 25) và fire_rate chậm
    (0.5 vs 1.0). Tầm bắn lớn hơn để dễ bảo vệ.

    Attributes:
        Kế thừa từ BasicNode. Nâng cấp damage (40), giảm fire_rate (0.5), tăng tầm bắn (4).

    Usage:
        Tạo khi người chơi nâng cấp tháp BasicNode (từ nhánh Tăng Damage I) lên SniperNode trong UpgradeTree:

            tower = SniperNode((row, col), graph)
    """

    def __init__(self, pos: tuple, graph: GridGraph, targeting="min_dist"):
        """Khởi tạo SniperNode: gọi super().__init__, ghi đè stats SniperNode.

        Args:
            pos (tuple): (row, col) vị trí ô WALL.
            graph (GridGraph): Bản đồ lưới.
            targeting (str): Chiến lược chọn mục tiêu. Mặc định "min_dist".
        """
        super().__init__(pos, graph, targeting)
        self.range      = settings.TOWER_SNIPER_RANGE
        self.damage     = settings.TOWER_SNIPER_DAMAGE
        self.fire_rate  = settings.TOWER_SNIPER_FIRE_RATE
        self.original_fire_rate = self.fire_rate
        self.cost       = settings.TOWER_SNIPER_COST
        self.hp         = settings.TOWER_SNIPER_HP
        self.max_hp     = self.hp
        self.tower_type = "sniper"
class FreezeNode(IceWall):
    """Tower đóng băng mạnh — quái đứng yên tại chỗ trong vài giây.

    Attributes:
        Kế thừa từ IceWall. Nhưng thay vì làm chậm thì đóng băng

    Usage:
        Tạo khi người chơi nâng cấp tháp IceWall ( từ nhánh nâng cấp slow) lên FreezeNode trong UpgradeTree:

            tower = FreezeNode((row, col), graph)
    """

    def __init__(self, pos: tuple, graph: GridGraph, targeting="min_dist"):
        """Khởi tạo FreezeNode: gọi super().__init__, ghi đè stats FreezeNode.

        Args:
            pos (tuple): (row, col) vị trí ô WALL.
            graph (GridGraph): Bản đồ lưới.
            targeting (str): Chiến lược chọn mục tiêu. Mặc định "min_dist".
        """
        super().__init__(pos, graph, targeting)
        self.slow_factor   = 0.0000001   # Freeze hoàn toàn → tốc độ còn 0%
        self.slow_duration = settings.TOWER_FREEZE_SLOW_DURATION
        self.damage        = settings.TOWER_FREEZE_DAMAGE
        self.cost          = settings.TOWER_FREEZE_COST
        self.hp            = settings.TOWER_FREEZE_HP
        self.max_hp        = self.hp
        self.tower_type    = "freeze"
class SpreadNode(IceWall):
    """Tower làm chậm lây lan — khi bắn trúng, không chỉ slow mục tiêu mà còn lan sang các quái trong 1 phạm vi nhất định.

    Attributes:
        Kế thừa từ IceWall. Nhưng thêm hiệu ứng lan sang các quái kề nhau trong 1 phạm vi.

    Usage:  
        Tạo khi người chơi nâng cấp tháp IceWall ( từ nhánh nâng cấp range) lên SpreadNode trong UpgradeTree:

            tower = SpreadNode((row, col), graph)
    """
    def __init__(self, pos: tuple, graph: GridGraph, targeting="min_dist"):
        """Khởi tạo SpreadNode: gọi super().__init__, ghi đè stats SpreadNode.

        Args:
            pos (tuple): (row, col) vị trí ô WALL.
            graph (GridGraph): Bản đồ lưới.
            targeting (str): Chiến lược chọn mục tiêu. Mặc định "min_dist".
        """
        super().__init__(pos, graph, targeting)
        self.range         = settings.TOWER_SPREAD_RANGE
        self.slow_factor   = settings.TOWER_SPREAD_SLOW_FACTOR
        self.slow_duration = settings.TOWER_SPREAD_SLOW_DURATION
        self.damage        = settings.TOWER_SPREAD_DAMAGE
        self.spread_range    = settings.TOWER_SPREAD_SLOW_RANGE
        self.cost          = settings.TOWER_SPREAD_COST
        self.hp            = settings.TOWER_SPREAD_HP
        self.max_hp        = self.hp
        self.tower_type    = "spread"

    def shoot(self, target):
        """Bắn + slow mục tiêu, projectile đánh dấu tower_type="spread" để game.py xử lý lan slow.

        Cơ chế:
            1. Slow mục tiêu bị bắn trúng ngay lập tức
            2. Tạo projectile với tower_type="spread"
            3. Game.py khi projectile hit: tìm tất cả malware trong spread_range xung quanh vị trí hit → slow tất cả

        Args:
            target (Malware): Mục tiêu bị bắn trúng.

        Returns:
            Projectile: Đạn với tower_type="spread" để game.py xử lý lan slow.
        """
        

        

        # Tạo projectile với tower_type="spread" và các attribute lan slow
        from entities.projectile import Projectile
        proj = Projectile(
            source_pos=self.pos,
            target=target,
            damage=self.damage,
            speed=settings.PROJECTILE_SPEED,
            tower_type="spread",
            spread_range=self.spread_range,
            slow_factor=self.slow_factor,
            slow_duration=self.slow_duration,
            source_tower=self
        )
        return proj


class PoisonNode(RadarNode):
    """Tower độc — không bắn đạn, gây damage liên tục cho tất cả quái trong phạm vi quét.

    Attributes:
        Kế thừa từ RadarNode. Override update() để gây damage thay vì bắn projectile.

    Usage:
        Tạo khi người chơi nâng cấp tháp RadarNode lên PoisonNode trong UpgradeTree:

            tower = PoisonNode((row, col), graph)
    """
    def __init__(self, pos: tuple, graph: GridGraph, targeting="min_dist"):
        """Khởi tạo PoisonNode: gọi super().__init__, ghi đè stats PoisonNode.

        Args:
            pos (tuple): (row, col) vị trí ô WALL.
            graph (GridGraph): Bản đồ lưới.
            targeting (str): Chiến lược chọn mục tiêu. Mặc định "min_dist".
        """
        super().__init__(pos, graph, targeting)
        self.damage        = settings.TOWER_POISON_DAMAGE
        self.fire_rate     = settings.TOWER_POISON_FIRE_RATE
        self.original_fire_rate = self.fire_rate
        self.cost          = settings.TOWER_POISON_COST
        self.hp            = settings.TOWER_POISON_HP
        self.max_hp        = self.hp
        self.tower_type    = "poison"

    def update(self, dt: float, candidates: list):
        """Cập nhật cooldown và gây damage cho tất cả malware trong phạm vi.

        Args:
            dt (float): Thời gian frame tính bằng giây.
            candidates (list): Danh sách Malware trong tầm quét (từ SpatialHash).

        Returns:
            None: PoisonNode không bắn projectile.

        Side effects:
            - Gây damage cho tất cả malware trong candidates mỗi lần cooldown reset.
            - Xử lý stun timer và slow timer (sau slow hết, khôi phục fire_rate).

        Note:
            Khác với Tower.update() — PoisonNode không tìm mục tiêu đơn lẻ, không gọi shoot(),
            và gây damage cho TẤT CẢ malware trong candidates thay vì chỉ 1 mục tiêu.
            game.py xử lý PoisonNode khác các tower khác vì return value là None.
        """
        super().update(dt, candidates)
        if self.stunned_timer > 0:
            return None
        # Nếu fire_timer vừa được reset về 0 trong Tower.update (nghĩa là đạt cooldown)
        if self.fire_timer == 0.0:
            for malware in candidates:
                if not malware.is_dead():
                    malware.take_damage(self.damage)
        return None

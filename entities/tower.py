# entities/tower.py
# Định nghĩa tất cả loại Tower trong game.
# Tower ngồi trên ô WALL, bắn Malware đang đi trên PATH kề cạnh.

import settings
import ui.sprites as sprites
from core.graph import GridGraph
from core.data_structures import CustomMinHeap, CustomMaxHeap, CustomQueue


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
        self.fire_timer = 0.0
        self.cost = 50
        self.color = settings.COLOR_TOWER_BASIC
        self.targeting = targeting
        self.tower_type = "basic"   # overridden by subclass
        self.path = self._path_can_shoot()

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
        self.fire_timer += dt
        cooldown = 1.0 / self.fire_rate
        if self.fire_timer >= cooldown:
            self.fire_timer = 0.0
            target = self._find_target(candidates)
            if target is not None:
                return self.shoot(target)
        return None
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

        Lọc trước: chỉ giữ malware đang đứng trên ô PATH mà tower có thể bắn
        (tham chiếu self.path tính bởi _path_can_shoot()).

        Chiến lược theo self.targeting:
            "min_dist" → CustomMinHeap → nhắm kẻ GẦN SERVER NHẤT
                (ưu tiên tiêu diệt kẻ sắp phá server).
            "max_hp" → CustomMaxHeap → nhắm kẻ CÒN NHIỀU MÁU NHẤT
                (tập trung hỏa lực vào kẻ cứng nhất).

        Args:
            candidates (list): Danh sách Malware từ SpatialHash.query_range().

        Returns:
            Malware: Mục tiêu được chọn, hoặc None nếu không có malware hợp lệ.

        Note:
            Dùng Heap thay sort() để thể hiện ứng dụng DSA heap trong game thực tế
            (yêu cầu môn học IT003).
        """
        filler_cadidates = []
        for candidate in candidates:
            if candidate.pos in self.path:
                filler_cadidates.append(candidate)
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
        target.apply_slow(self.slow_factor, self.slow_duration)
        return super().shoot(target)


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

# entities/tower.py
# Định nghĩa tất cả loại Tower trong game.
# Tower ngồi trên ô WALL, bắn Malware đang đi trên PATH kề cạnh.

import settings
from core.graph import GridGraph
from core.data_structures import CustomMinHeap, CustomMaxHeap


class Tower:
    """
    Lớp cơ sở cho tất cả Tower.

    Mỗi Tower có:
      - pos         : vị trí ô lưới (row, col) — luôn là ô WALL
      - graph       : tham chiếu GridGraph (để kiểm tra vị trí)
      - range       : bán kính tấn công (đơn vị: ô lưới)
      - damage      : sát thương mỗi phát bắn
      - fire_rate   : số phát bắn mỗi giây
      - fire_timer  : bộ đếm thời gian tích lũy dt — khi >= 1/fire_rate thì bắn
      - cost        : tiền cần để xây
      - color       : màu hiển thị trên lưới
      - targeting   : chiến lược chọn mục tiêu — "min_hp_dist" hoặc "max_hp"

    Quan hệ với phần còn lại:
      - game.py tạo Tower khi người chơi click ô WALL
      - game.py gọi tower.update(dt, candidates) mỗi frame
        với candidates = danh sách Malware trong tầm (từ SpatialHash)
      - tower.update() trả về Projectile hoặc None
      - game.py thêm Projectile vào self.projectiles nếu không None
    """

    def __init__(self, pos: tuple, graph: GridGraph,targeting="min_dist"):
      self.pos = pos
      self.graph = graph
      self.range = 3
      self.damage = 20
      self.fire_rate = 1.0
      self.fire_timer = 0.0
      self.cost = 50
      self.color = settings.COLOR_TOWER_BASIC
      self.targeting = targeting
      
      """
        Khởi tạo Tower tại vị trí pos.

        Việc cần làm:
          1. self.pos        = pos
          2. self.graph      = graph
          3. self.range      = 3          (mặc định, subclass ghi đè)
          4. self.damage     = 20
          5. self.fire_rate  = 1.0        (phát/giây)
          6. self.fire_timer = 0.0        (bắt đầu từ 0 — tháp chưa sẵn sàng bắn)
          7. self.cost       = 50
          8. self.color      = settings.COLOR_TOWER_BASIC
          9. self.targeting  = "min_dist" (mặc định: nhắm kẻ gần server nhất)
        """
      pass

    def update(self, dt: float, candidates: list):
      self.fire_timer += dt
      cooldown = 1.0 / self.fire_rate
      if self.fire_timer >= cooldown:
        self.fire_timer =0.0
        target = self._find_target(candidates)
        if target is not None:
          return self.shoot(target)
      return None
      """
        Cập nhật cooldown và bắn nếu đến lượt.

        dt          : thời gian frame (giây)
        candidates  : list[Malware] — các malware trong tầm bắn (từ SpatialHash)
                      Nếu danh sách rỗng → không bắn.

        Việc cần làm:
          1. self.fire_timer += dt
          2. cooldown = 1.0 / self.fire_rate
          3. if self.fire_timer >= cooldown:
               self.fire_timer = 0.0      ← reset, không tích lũy
               target = self._find_target(candidates)
               if target is not None:
                   return self.shoot(target)
          4. return None   ← chưa đến lúc bắn hoặc không có target

        Ảnh hưởng:
          - Nếu trả về Projectile → game.py thêm vào self.projectiles.
          - fire_timer reset về 0 mỗi lần bắn để fire_rate luôn chính xác.
        """
      pass

    def _find_target(self, candidates: list):
      if self.targeting=="min_dist":
        heap=CustomMinHeap()
        for candidate in candidates:
          if not candidate.is_dead():
            dist = abs(candidate.pos[0] - self.graph.server_pos[0]) + abs(candidate.pos[1] - self.graph.server_pos[1])
            heap.push((dist, candidate))
        result = heap.pop()
        return result[1] if result else None
      else:
        heap=CustomMaxHeap()
        for candidate in candidates:
          if not candidate.is_dead():
            heap.push((candidate.hp, candidate))
        result = heap.pop()
        return result[1] if result else None
        """
        Chọn mục tiêu tối ưu từ danh sách candidates bằng Heap.

        Chiến lược theo self.targeting:
          "min_dist" → CustomMinHeap → nhắm kẻ GẦN SERVER NHẤT
                       (ưu tiên tiêu diệt kẻ sắp phá server)
          "max_hp"   → CustomMaxHeap → nhắm kẻ CÒN NHIỀU MÁU NHẤT
                       (tập trung hỏa lực vào kẻ cứng nhất)

        Cách làm với "min_dist":
          1. Tạo heap = CustomMinHeap()
          2. server = self.graph.server_pos
          3. for m in candidates (nếu not m.is_dead() ):
               dist = |m.pos[0] - server[0]| + |m.pos[1] - server[1]|   ← Manhattan
               heap.push((dist, m))
          4. result = heap.pop()
          5. return result[1] if result else None

        Cách làm với "max_hp":
          1. Tạo heap = CustomMaxHeap()
          2. for m in candidates: heap.push((m.hp, m))
          3. result = heap.pop()
          4. return result[1] if result else None

        Tại sao dùng Heap thay vì sort()?
          Đây là yêu cầu DSA của môn học — heap cho O(n log n) nhưng quan trọng hơn
          là thể hiện ứng dụng heap trong game thực tế.
        """
        pass

    def shoot(self, target):
      from entities.projectile import Projectile
      return Projectile(
          source_pos = self.pos,
          target     = target,
          damage     = self.damage,
          speed      = settings.PROJECTILE_SPEED
      )
      """
        Bắn vào mục tiêu — tạo Projectile và trả về.

        target : đối tượng Malware đang bị nhắm

        Việc cần làm:
          from entities.projectile import Projectile
          return Projectile(
              source_pos = self.pos,
              target     = target,
              damage     = self.damage,
              speed      = settings.PROJECTILE_SPEED
          )

        Lưu ý: import Projectile bên trong hàm (tránh circular import).
        Projectile chứa tham chiếu đến target — khi target chết thì Projectile
        cần kiểm tra trước khi xử lý damage (xem Projectile.update()).
        """
      pass

    def draw(self, screen, cell_size: int):
      import pygame
      px = self.pos[1] * cell_size + cell_size // 2
      py = self.pos[0] * cell_size + cell_size // 2
      pygame.draw.circle(screen, self.color, (px, py), cell_size // 4)
      
      """
        Vẽ Tower lên màn hình.

        Tower đã được tô màu qua lưới (game._draw_grid() vẽ ô TOWER bằng color).
        Phương thức này vẽ THÊM:
          a) Vòng tròn nhỏ ở trung tâm ô để phân biệt loại tower
          b) (Tùy chọn) Vòng tròn bán kính tấn công mờ khi hover chuột

        Việc cần làm (phần a):
          import pygame
          px = self.pos[1] * cell_size + cell_size // 2
          py = self.pos[0] * cell_size + cell_size // 2
          pygame.draw.circle(screen, self.color, (px, py), cell_size // 4)

        Phần b (nâng cao, làm sau):
          pygame.draw.circle(screen, (*self.color, 40),
                             (px, py), self.range * cell_size, 1)
          (cần Surface với alpha để vẽ vòng tròn trong suốt)
      """
      pass


# ---------------------------------------------------------------------------
# Subclasses
# ---------------------------------------------------------------------------

class BasicNode(Tower):
    """
    Tower cơ bản — single target, damage trung bình, giá rẻ.

    Chiến lược: nhắm kẻ gần Server nhất (self.targeting = "min_dist").
    Dùng khi: người chơi mới bắt đầu, chưa đủ tiền mua tower xịn.
    """

    def __init__(self, pos: tuple, graph: GridGraph, targeting="min_dist"):
      super().__init__(pos, graph)
      self.range     = settings.TOWER_BASIC_RANGE
      self.damage    = settings.TOWER_BASIC_DAMAGE
      self.fire_rate = settings.TOWER_BASIC_FIRE_RATE
      self.cost      = settings.TOWER_BASIC_COST
      self.color     = settings.COLOR_TOWER_BASIC
      self.targeting = targeting
      
      """
        Khởi tạo BasicNode.

        Việc cần làm:
          1. super().__init__(pos, graph)
          2. self.range     = settings.TOWER_BASIC_RANGE
          3. self.damage    = settings.TOWER_BASIC_DAMAGE
          4. self.fire_rate = settings.TOWER_BASIC_FIRE_RATE
          5. self.cost      = settings.TOWER_BASIC_COST
          6. self.color     = settings.COLOR_TOWER_BASIC
          7. self.targeting = "min_dist"
        """
      pass


class IceWall(Tower):
    """
    Tower làm chậm — damage thấp nhưng áp dụng slow effect lên mục tiêu.

    Sau khi bắn: gọi target.apply_slow(factor, duration) để giảm tốc độ Malware.
    Chiến lược: nhắm kẻ nhiều máu nhất (self.targeting = "max_hp")
                vì muốn làm chậm kẻ cứng nhất để BasicNode tiêu diệt.
    """

    def __init__(self, pos: tuple, graph: GridGraph,targeting="min_dist"):
        super().__init__(pos, graph)
        self.range      = settings.TOWER_ICE_RANGE
        self.damage     = settings.TOWER_ICE_DAMAGE
        self.fire_rate  = settings.TOWER_ICE_FIRE_RATE
        self.cost       = settings.TOWER_ICE_COST
        self.color      = settings.COLOR_TOWER_ICE
        self.targeting  = targeting
        self.slow_factor   = settings.TOWER_ICE_SLOW_FACTOR
        self.slow_duration = settings.TOWER_ICE_SLOW_DURATION
        
        """
        Khởi tạo IceWall.

        Việc cần làm:
          1. super().__init__(pos, graph)
          2. self.range      = settings.TOWER_ICE_RANGE
          3. self.damage     = settings.TOWER_ICE_DAMAGE
          4. self.fire_rate  = settings.TOWER_ICE_FIRE_RATE
          5. self.cost       = settings.TOWER_ICE_COST
          6. self.color      = settings.COLOR_TOWER_ICE
          7. self.targeting  = "max_hp"
          8. self.slow_factor   = settings.TOWER_ICE_SLOW_FACTOR
          9. self.slow_duration = settings.TOWER_ICE_SLOW_DURATION
        """
        pass

    def shoot(self, target):
      target.apply_slow(self.slow_factor, self.slow_duration) 
      return super().shoot(target)
      """
        Bắn và áp dụng slow effect lên mục tiêu.

        Việc cần làm:
          1. Gọi target.apply_slow(self.slow_factor, self.slow_duration)
          2. Tạo và trả về Projectile giống Tower.shoot(target)
             (gọi super().shoot(target) hoặc copy logic từ Tower.shoot)

        Lưu ý: apply_slow() TRƯỚC khi tạo projectile — hiệu ứng áp dụng ngay lập tức
        trong Week 2. Animation đạn chỉ là hình thức.
        """
      pass


class RadarNode(Tower):
    """
    Tower chỉ DÒ MAP — range lớn nhất, KHÔNG bắn đạn.

    Vai trò trong game:
      - Đặt ở vị trí chiến lược để "nhìn thấy" malware từ xa.
      - Không gây damage, nhưng shoot() trả về None → game.py bỏ qua.

    Tại sao không bắn?
      shoot() bị override để luôn trả về None.
      Tower.update() vẫn gọi shoot() bình thường, nhưng nhận None
      → game.py kiểm tra "if projectile is not None" → bỏ qua.

      Luồng: Tower.update() → shoot(target) → None
                                               ↑
                                   RadarNode.shoot() luôn return None
    """

    def __init__(self, pos: tuple, graph: GridGraph,targeting="min_dist"):
      super().__init__(pos, graph)
      self.range     = settings.TOWER_RADAR_RANGE
      self.cost      = settings.TOWER_RADAR_COST
      self.color     = settings.COLOR_TOWER_RADAR
      self.targeting = targeting
      """
        Khởi tạo RadarNode.

        Việc cần làm:
          1. super().__init__(pos, graph)
          2. self.range     = settings.TOWER_RADAR_RANGE
          3. self.cost      = settings.TOWER_RADAR_COST
          4. self.color     = settings.COLOR_TOWER_RADAR
          5. self.targeting = "min_dist"

        Lưu ý: không cần self.damage và self.fire_rate vì không bắn.
                Set self.damage = 0 nếu muốn tránh AttributeError.
        """
      pass

    def shoot(self, target):
      return None
      """
        Override để vô hiệu hóa bắn — luôn trả về None.

        Việc cần làm: return None

        Tại sao return None?
          game.py dùng: projectile = tower.update(dt, candidates)
                        if projectile is not None:
                            self.projectiles.append(projectile)
          None → không append → không có đạn → RadarNode chỉ dò, không bắn.
        """
      pass

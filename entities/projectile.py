# entities/projectile.py
# Đạn được bắn ra từ Tower, bay đến Malware và gây damage khi chạm.
# Projectile hoạt động trong không gian PIXEL (không phải ô lưới)
# để animation trông mượt mà.

import math
import settings


class Projectile:
    """Đạn bắn từ Tower, bay theo đường thẳng đến Malware và gây damage khi chạm.

    Hoạt động trong không gian pixel (float) thay vì ô lưới để animation mượt mà.
    Mỗi frame, game.py gọi update(dt) để di chuyển đạn; khi has_hit() trả True
    thì game.py lọc đạn ra khỏi danh sách self.projectiles.

    Attributes:
        target (Malware): Tham chiếu malware đang bị nhắm. Có thể chết trước khi đạn đến.
        damage (int): Sát thương sẽ gây khi chạm mục tiêu.
        speed (float): Tốc độ đạn tính bằng pixel/giây (= speed_ô * CELL_SIZE).
        x (float): Tọa độ pixel X hiện tại của đạn.
        y (float): Tọa độ pixel Y hiện tại của đạn.
        color (tuple): Màu RGB đạn, lấy từ settings.COLOR_PROJECTILE.
        radius (int): Bán kính vẽ đạn tính bằng pixel, mặc định 4.
        _hit (bool): True khi đạn đã chạm mục tiêu hoặc mục tiêu đã chết.

    Usage:
        Không tạo trực tiếp — Tower.shoot() tạo và trả về, game.py quản lý vòng đời::

            # Tower.shoot() trả về:
            Projectile(source_pos=self.pos, target=target,
                       damage=self.damage, speed=settings.PROJECTILE_SPEED)

            # game.py mỗi frame:
            for proj in self.projectiles:
                proj.update(dt)
            self.projectiles = [p for p in self.projectiles if not p.has_hit()]
    """

    def __init__(self, source_pos: tuple, target, damage: int, speed: float):
        """Khởi tạo Projectile tại vị trí pixel tâm Tower, nhắm về phía target.

        Args:
            source_pos (tuple): Vị trí (row, col) ô lưới của Tower bắn ra.
                Được đổi sang tọa độ pixel tâm ô:
                x = col * CELL_SIZE + CELL_SIZE//2,
                y = row * CELL_SIZE + CELL_SIZE//2.
            target (Malware): Đối tượng Malware đang bị nhắm bắn.
            damage (int): Sát thương gây ra khi chạm.
            speed (float): Tốc độ đạn tính bằng ô/giây. Nội bộ nhân CELL_SIZE
                để ra pixel/giây cho phép tính di chuyển pixel-level.

        Note:
            Đạn bay theo kiểu "homing" — tính lại hướng đến target mỗi frame trong
            update(), vì malware di chuyển trong khi đạn bay.
        """
        self.target = target
        self.damage = damage
        self.speed = speed * settings.CELL_SIZE
        self._hit = False

        self.x = source_pos[1] * settings.CELL_SIZE + settings.CELL_SIZE // 2
        self.y = source_pos[0] * settings.CELL_SIZE + settings.CELL_SIZE // 2

        self.color = settings.COLOR_PROJECTILE
        self.radius = 4
        pass

    def update(self, dt: float):
        """Di chuyển đạn về phía target mỗi frame theo vector đơn vị (homing).

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Cập nhật self.x, self.y theo hướng đến vị trí pixel hiện tại của target.
            - Đặt self._hit = True và gọi target.take_damage(self.damage) khi đến nơi.
            - Đặt self._hit = True ngay lập tức nếu target đã chết, tránh đạn bay vô ích.

        Note:
            Normalize vector (dx/dist, dy/dist) đảm bảo tốc độ không đổi bất kể
            target ở xa hay gần. Điều kiện chạm: dist < speed*dt, tức là trong
            frame này đạn sẽ vượt qua target — xử lý damage ngay và đánh dấu _hit.
        """
        if self.target.is_dead():
            self._hit = True
            return
        tx = self.target.pos[1] * settings.CELL_SIZE + settings.CELL_SIZE // 2
        ty = self.target.pos[0] * settings.CELL_SIZE + settings.CELL_SIZE // 2
        dx = tx - self.x
        dy = ty - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist <= 0 or dist < self.speed * dt:
            self.target.take_damage(self.damage)
            self._hit = True
            return
        self.x += dx / dist * self.speed * dt
        self.y += dy / dist * self.speed * dt
        pass

    def has_hit(self) -> bool:
        """Kiểm tra đạn đã kết thúc vòng đời chưa.

        Returns:
            bool: True nếu đạn đã chạm mục tiêu hoặc mục tiêu đã chết.
                False nếu đạn vẫn đang bay về phía target.

        Usage:
            game.py lọc danh sách đạn sau mỗi frame::

                self.projectiles = [p for p in self.projectiles if not p.has_hit()]
        """
        return self._hit
        pass

    def draw(self, screen):
        """Vẽ đạn lên màn hình dưới dạng hình tròn nhỏ tại vị trí pixel hiện tại.

        Args:
            screen (pygame.Surface): Bề mặt pygame để vẽ lên.

        Side effects:
            - Vẽ hình tròn bán kính self.radius tại tọa độ (int(self.x), int(self.y)).

        Note:
            self.x và self.y là float — phải ép kiểu int() khi truyền vào pygame.draw.circle.
            Gọi sau _draw_malwares() trong game.draw() để đạn hiển thị trên đầu malware.
        """
        import pygame
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        pass

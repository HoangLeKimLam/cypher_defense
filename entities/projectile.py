# entities/projectile.py
# Đạn: BaseProjectile (cơ sở chung), Projectile (Tower), MalwareProjectile (Ranged Malware)
# Hoạt động trong không gian PIXEL (không phải ô lưới) để animation trông mượt mà.

import math
import settings
import ui.sprites as sprites


class BaseProjectile:
    """Lớp cơ sở cho tất cả projectiles.

    Chứa logic chung: vị trí pixel, tốc độ, rendering, hit detection.
    Subclass ghi đè update(dt) để định nghĩa cách di chuyển.

    Attributes:
        x (float): Tọa độ pixel X hiện tại của đạn.
        y (float): Tọa độ pixel Y hiện tại của đạn.
        damage (int): Sát thương gây ra.
        speed (float): Tốc độ đạn tính bằng pixel/giây.
        _hit (bool): True khi đạn đã kết thúc vòng đời.
        color (tuple): Màu RGB đạn.
        radius (int): Bán kính vẽ đạn.
        tower_type (str): Loại tower/malware bắn ra (dùng cho sprite).
    """

    def __init__(self, source_pos: tuple, damage: int, speed: float, tower_type: str = "basic",
                 spread_range: float = None, slow_factor: float = None, slow_duration: float = None):
        """Khởi tạo BaseProjectile.

        Args:
            source_pos (tuple): Vị trí (row, col) ô lưới.
            damage (int): Sát thương.
            speed (float): Tốc độ tính bằng ô/giây (nhân CELL_SIZE → pixel/giây).
            tower_type (str): Loại (basic, ice, radar, worm, etc.).
            spread_range (float): Bán kính lan slow (cho SpreadNode projectile).
            slow_factor (float): Hệ số slow khi lan (cho SpreadNode projectile).
            slow_duration (float): Thời gian slow khi lan (cho SpreadNode projectile).
        """
        self.damage = damage
        self.speed = speed * settings.CELL_SIZE
        self._hit = False
        self.tower_type = tower_type
        self.spread_range = spread_range
        self.slow_factor = slow_factor
        self.slow_duration = slow_duration

        # Chuyển từ ô lưới sang pixel (tâm ô)
        self.x = source_pos[1] * settings.CELL_SIZE + settings.CELL_SIZE // 2
        self.y = source_pos[0] * settings.CELL_SIZE + settings.CELL_SIZE // 2

        self.color = settings.COLOR_PROJECTILE
        self.radius = 4

    def update(self, dt: float):
        """Cập nhật vị trí đạn. Override trong subclass."""
        raise NotImplementedError("Subclass must implement update()")

    def has_hit(self) -> bool:
        """Kiểm tra đạn kết thúc vòng đời."""
        return self._hit

    def apply_hit(self, game):
        """Hook called by game.py when projectile hits. Override in subclass for custom behavior."""
        pass

    def draw(self, screen, camera_x=0, camera_y=0):
        """Vẽ đạn lên màn hình với camera offset.
        
        Args:
            screen: pygame.Surface để vẽ
            camera_x: offset camera theo trục X
            camera_y: offset camera theo trục Y
        """
        import pygame

        # Tính screen coordinates (world coords - camera offset)
        screen_x = self.x - camera_x
        screen_y = self.y - camera_y

        # Custom drawing cho trojan_ranged projectile
        if self.tower_type == "trojan_ranged":
            self._draw_trojan_ranged_projectile(screen, screen_x, screen_y)
            return

        # Custom drawing cho spyware_ranged projectile (red tone)
        if self.tower_type == "spyware_ranged":
            self._draw_spyware_ranged_projectile(screen, screen_x, screen_y)
            return

        # Custom drawing cho slowspy_ranged projectile (blue tone)
        if self.tower_type == "slowspy_ranged":
            self._draw_slowspy_ranged_projectile(screen, screen_x, screen_y)
            return

        # Custom drawing cho lightspy_ranged projectile (bright yellow, near white)
        if self.tower_type == "lightspy_ranged":
            self._draw_lightspy_ranged_projectile(screen, screen_x, screen_y)
            return

        # Custom drawing cho fire projectile (flame ball)
        if self.tower_type == "fire":
            self._draw_fire_projectile(screen, screen_x, screen_y)
            return

        # Custom drawing cho speed projectile (lightning bolt)
        if self.tower_type == "speed":
            self._draw_speed_projectile(screen, screen_x, screen_y)
            return

        # Custom drawing cho sniper projectile (piercing shot)
        if self.tower_type == "sniper":
            self._draw_sniper_projectile(screen, screen_x, screen_y)
            return

        # Custom drawing cho freeze projectile (ice shard)
        if self.tower_type == "freeze":
            self._draw_freeze_projectile(screen, screen_x, screen_y)
            return

        # Custom drawing cho spread projectile (toxic gas)
        if self.tower_type == "spread":
            self._draw_spread_projectile(screen, screen_x, screen_y)
            return

        # Custom drawing cho poison projectile (venom orb)
        if self.tower_type == "poison":
            self._draw_poison_projectile(screen, screen_x, screen_y)
            return

        # Custom drawing cho riposteware projectile (riposte/reflected)
        if self.tower_type == "riposteware":
            self._draw_riposteware_projectile(screen, screen_x, screen_y)
            return

        # Default: sprite hoặc circle
        key = f"proj_{self.tower_type}"
        surf = sprites.get(key)
        if surf:
            w, h = surf.get_size()
            screen.blit(surf, (int(screen_x) - w // 2, int(screen_y) - h // 2))
        else:
            pygame.draw.circle(screen, self.color, (int(screen_x), int(screen_y)), self.radius)

    def _draw_trojan_ranged_projectile(self, screen, screen_x, screen_y):
        """Vẽ projectile trojan_ranged: hình tròn gradient với trail (màu tím)."""
        import pygame
        import math

        x, y = int(screen_x), int(screen_y)

        # Vẽ glow effect (hào quang tím)
        glow_radius = 12
        glow_color = (180, 80, 200, 40)
        pygame.draw.circle(screen, glow_color, (x, y), glow_radius, 3)

        # Vẽ trail (đuôi tím)
        for i in range(5):
            alpha = int(120 * (1 - i / 5))
            trail_col = (200, 100, 230, alpha)
            pygame.draw.circle(screen, trail_col, (x - (i+1)*3, y), 3)

        # Vẽ core (lõi chính) tím - spherical shading
        core_color = (200, 80, 220)
        pygame.draw.circle(screen, core_color, (x, y), 8)

        # Vẽ inner glow (sáng bên trong)
        pygame.draw.circle(screen, (220, 150, 255), (x-2, y-2), 5)

        # Vẽ bright center (tâm sáng)
        pygame.draw.circle(screen, (240, 200, 255), (x, y), 3)

        # Vẽ outline mạnh (viền tím đậm)
        pygame.draw.circle(screen, (150, 30, 180), (x, y), 8, 2)

    def _draw_spyware_ranged_projectile(self, screen, screen_x, screen_y):
        """Vẽ projectile spyware_ranged: hình tròn gradient với trail (màu đỏ)."""
        import pygame

        x, y = int(screen_x), int(screen_y)

        # Vẽ glow effect (hào quang đỏ)
        glow_radius = 12
        pygame.draw.circle(screen, (200, 80, 80), (x, y), glow_radius, 3)

        # Vẽ trail (đuôi đỏ)
        for i in range(5):
            trail_col = (220, 100, 100)
            pygame.draw.circle(screen, trail_col, (x - (i+1)*3, y), 3)

        # Vẽ core (lõi chính) đỏ
        pygame.draw.circle(screen, (220, 80, 80), (x, y), 8)

        # Vẽ inner glow (sáng bên trong)
        pygame.draw.circle(screen, (240, 150, 150), (x-2, y-2), 5)

        # Vẽ bright center (tâm sáng)
        pygame.draw.circle(screen, (255, 200, 200), (x, y), 3)

        # Vẽ outline mạnh (viền đỏ đậm)
        pygame.draw.circle(screen, (180, 30, 30), (x, y), 8, 2)

    def _draw_slowspy_ranged_projectile(self, screen, screen_x, screen_y):
        """Vẽ projectile slowspy_ranged: hình tròn gradient với trail (màu xanh dương)."""
        import pygame

        x, y = int(screen_x), int(screen_y)

        # Vẽ glow effect (hào quang xanh dương)
        glow_radius = 12
        pygame.draw.circle(screen, (80, 120, 200), (x, y), glow_radius, 3)

        # Vẽ trail (đuôi xanh dương)
        for i in range(5):
            trail_col = (100, 150, 220)
            pygame.draw.circle(screen, trail_col, (x - (i+1)*3, y), 3)

        # Vẽ core (lõi chính) xanh dương
        pygame.draw.circle(screen, (100, 150, 220), (x, y), 8)

        # Vẽ inner glow (sáng bên trong)
        pygame.draw.circle(screen, (150, 180, 240), (x-2, y-2), 5)

        # Vẽ bright center (tâm sáng)
        pygame.draw.circle(screen, (200, 220, 255), (x, y), 3)

        # Vẽ outline mạnh (viền xanh dương đậm)
        pygame.draw.circle(screen, (30, 80, 180), (x, y), 8, 2)

    def _draw_lightspy_ranged_projectile(self, screen, screen_x, screen_y):
        """Vẽ projectile lightspy_ranged: hình tròn sáng vàng (gần trắng) với trail sáng."""
        import pygame

        x, y = int(screen_x), int(screen_y)

        # Vẽ glow effect (hào quang vàng sáng)
        glow_radius = 13
        pygame.draw.circle(screen, (255, 255, 150), (x, y), glow_radius, 3)

        # Vẽ trail (đuôi vàng sáng)
        for i in range(5):
            trail_col = (255, 255, 180)
            pygame.draw.circle(screen, trail_col, (x - (i+1)*3, y), 4)

        # Vẽ core (lõi chính) vàng sáng
        pygame.draw.circle(screen, (255, 250, 180), (x, y), 9)

        # Vẽ inner glow (sáng bên trong)
        pygame.draw.circle(screen, (255, 255, 220), (x-2, y-2), 6)

        # Vẽ bright center (tâm sáng, gần trắng)
        pygame.draw.circle(screen, (255, 255, 255), (x, y), 4)

        # Vẽ outline mạnh (viền vàng đậm)
        pygame.draw.circle(screen, (200, 200, 100), (x, y), 9, 2)

    def _draw_fire_projectile(self, screen, screen_x, screen_y):
        """Vẽ projectile fire: quả cầu lửa với trail lửa."""
        import pygame

        x, y = int(screen_x), int(screen_y)

        # Vẽ trail (đuôi lửa cam)
        for i in range(6):
            alpha = int(150 * (1 - i / 6))
            trail_col = (255, 150 - i * 15, 0)
            pygame.draw.circle(screen, trail_col, (x - (i+1)*2, y), 4)

        # Vẽ glow effect (hào quang cam/vàng)
        glow_radius = 14
        pygame.draw.circle(screen, (255, 150, 0), (x, y), glow_radius, 3)

        # Vẽ core chính (quả cầu lửa cam)
        pygame.draw.circle(screen, (255, 120, 0), (x, y), 10)

        # Vẽ inner glow (sáng vàng bên trong)
        pygame.draw.circle(screen, (255, 200, 100), (x-2, y-2), 6)

        # Vẽ bright center (tâm sáng vàng)
        pygame.draw.circle(screen, (255, 240, 150), (x, y), 3)

        # Vẽ outline mạnh (viền cam đậm)
        pygame.draw.circle(screen, (200, 80, 0), (x, y), 10, 2)

    def _draw_speed_projectile(self, screen, screen_x, screen_y):
        """Vẽ projectile speed: tia sét vàng với trail điện."""
        import pygame

        x, y = int(screen_x), int(screen_y)

        # Vẽ trail điện (đuôi vàng cam)
        for i in range(5):
            trail_col = (255, 200 - i * 20, 50)
            pygame.draw.circle(screen, trail_col, (x - (i+1)*3, y), 3)

        # Vẽ glow effect (hào quang sét)
        pygame.draw.circle(screen, (255, 220, 0), (x, y), 11, 2)

        # Vẽ core chính (lõi sét vàng)
        pygame.draw.circle(screen, (255, 200, 0), (x, y), 8)

        # Vẽ inner glow (sáng vàng)
        pygame.draw.circle(screen, (255, 240, 100), (x-2, y-2), 5)

        # Vẽ bright center (tâm sáng)
        pygame.draw.circle(screen, (255, 255, 200), (x, y), 3)

    def _draw_sniper_projectile(self, screen, screen_x, screen_y):
        """Vẽ projectile sniper: mũi tên đỏ sắc với trail máu."""
        import pygame

        x, y = int(screen_x), int(screen_y)

        # Vẽ trail máu (đuôi đỏ đậm)
        for i in range(6):
            trail_col = (200 - i * 20, 30, 30)
            pygame.draw.circle(screen, trail_col, (x - (i+1)*2, y), 3)

        # Vẽ glow effect (hào quang đỏ)
        pygame.draw.circle(screen, (220, 50, 50), (x, y), 10, 2)

        # Vẽ core chính (lõi đỏ sắc)
        pygame.draw.circle(screen, (200, 50, 50), (x, y), 7)

        # Vẽ inner glow (sáng đỏ)
        pygame.draw.circle(screen, (240, 100, 100), (x-2, y-2), 4)

        # Vẽ bright center
        pygame.draw.circle(screen, (255, 150, 150), (x, y), 2)

    def _draw_freeze_projectile(self, screen, screen_x, screen_y):
        """Vẽ projectile freeze: mảnh sông lạnh với trail băng."""
        import pygame

        x, y = int(screen_x), int(screen_y)

        # Vẽ trail băng (đuôi xanh lạnh)
        for i in range(5):
            trail_col = (100 + i * 20, 200, 255)
            pygame.draw.circle(screen, trail_col, (x - (i+1)*3, y), 3)

        # Vẽ glow effect (hào quang xanh lạnh)
        pygame.draw.circle(screen, (100, 200, 255), (x, y), 10, 2)

        # Vẽ core chính (lõi sông xanh)
        pygame.draw.circle(screen, (120, 200, 255), (x, y), 7)

        # Vẽ inner glow (sáng trắng xanh)
        pygame.draw.circle(screen, (180, 230, 255), (x-2, y-2), 4)

        # Vẽ bright center
        pygame.draw.circle(screen, (200, 240, 255), (x, y), 2)

    def _draw_spread_projectile(self, screen, screen_x, screen_y):
        """Vẽ projectile spread: khí độc tím với trail giãn nở."""
        import pygame

        x, y = int(screen_x), int(screen_y)

        # Vẽ trail độc (đuôi tím)
        for i in range(5):
            trail_col = (150 + i * 10, 100, 200)
            trail_rad = 4 - i * 0.5
            pygame.draw.circle(screen, trail_col, (x - (i+1)*3, y), max(2, int(trail_rad)))

        # Vẽ glow effect (hào quang tím)
        pygame.draw.circle(screen, (180, 100, 220), (x, y), 11, 2)

        # Vẽ core chính (lõi tím độc)
        pygame.draw.circle(screen, (170, 90, 210), (x, y), 8)

        # Vẽ inner glow (sáng tím)
        pygame.draw.circle(screen, (200, 140, 240), (x-2, y-2), 5)

        # Vẽ bright center
        pygame.draw.circle(screen, (220, 180, 255), (x, y), 3)

    def _draw_poison_projectile(self, screen, screen_x, screen_y):
        """Vẽ projectile poison: quả cầu nọc độc với trail độc tố."""
        import pygame

        x, y = int(screen_x), int(screen_y)

        # Vẽ trail độc (đuôi xanh lá)
        for i in range(5):
            trail_col = (100 + i * 20, 200, 80)
            pygame.draw.circle(screen, trail_col, (x - (i+1)*3, y), 3)

        # Vẽ glow effect (hào quang độc xanh)
        pygame.draw.circle(screen, (120, 200, 100), (x, y), 10, 2)

        # Vẽ core chính (lõi độc xanh)
        pygame.draw.circle(screen, (100, 200, 80), (x, y), 8)

        # Vẽ inner glow (sáng xanh)
        pygame.draw.circle(screen, (150, 240, 150), (x-2, y-2), 5)

        # Vẽ bright center
        pygame.draw.circle(screen, (180, 255, 180), (x, y), 3)

    def _draw_riposteware_projectile(self, screen, screen_x, screen_y):
        """Vẽ projectile riposte: quả cầu xanh lá (phản đạn) với glow sáng."""
        import pygame

        x, y = int(screen_x), int(screen_y)

        # Vẽ trail xanh lá (đuôi phản đạn)
        for i in range(6):
            trail_col = (80 + i * 20, 255 - i * 10, 100)
            pygame.draw.circle(screen, trail_col, (x - (i+1)*2, y), 3)

        # Vẽ glow effect (hào quang xanh lá sáng)
        pygame.draw.circle(screen, (100, 255, 120), (x, y), 11, 2)

        # Vẽ core chính (lõi xanh lá)
        pygame.draw.circle(screen, (80, 240, 100), (x, y), 8)

        # Vẽ inner glow (sáng trắng xanh)
        pygame.draw.circle(screen, (150, 255, 170), (x-2, y-2), 5)

        # Vẽ bright center (tâm sáng)
        pygame.draw.circle(screen, (200, 255, 220), (x, y), 3)


class Projectile(BaseProjectile):
    """Đạn bắn từ Tower, bay theo đường thẳng đến Malware và gây damage khi chạm.

    Hoạt động trong không gian pixel (float) thay vì ô lưới để animation mượt mà.
    Mỗi frame, game.py gọi update(dt) để di chuyển đạn; khi has_hit() trả True
    thì game.py lọc đạn ra khỏi danh sách self.projectiles.

    Attributes:
        target (Malware): Tham chiếu malware đang bị nhắm. Có thể chết trước khi đạn đến.

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

    def __init__(self, source_pos: tuple, target, damage: int, speed: float, tower_type: str = "basic",
                 spread_range: float = None, slow_factor: float = None, slow_duration: float = None, source_tower=None):
        """Khởi tạo Projectile tại vị trí pixel tâm Tower, nhắm về phía target.

        Args:
            source_pos (tuple): Vị trí (row, col) ô lưới của Tower bắn ra.
            target (Malware): Đối tượng Malware đang bị nhắm bắn.
            damage (int): Sát thương gây ra khi chạm.
            speed (float): Tốc độ đạn tính bằng ô/giây.
            tower_type (str): Loại tower (basic, ice, radar).
            spread_range (float): Bán kính lan slow (cho SpreadNode projectile).
            slow_factor (float): Hệ số slow khi lan (cho SpreadNode projectile).
            slow_duration (float): Thời gian slow khi lan (cho SpreadNode projectile).
            source_tower: Tham chiếu Tower bắn ra đạn này (để phục vụ riposte, etc).

        Note:
            Đạn bay theo kiểu "homing" — tính lại hướng đến target mỗi frame,
            vì malware di chuyển trong khi đạn bay.
        """
        super().__init__(source_pos, damage, speed, tower_type, spread_range, slow_factor, slow_duration)
        self.target = target
        self.source_tower = source_tower

    def update(self, dt: float):
        """Di chuyển đạn về phía target mỗi frame theo vector đơn vị (homing).

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Cập nhật self.x, self.y theo hướng đến vị trí pixel hiện tại của target.
            - Đặt self._hit = True khi đạn chạm target.
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
            # Gọi hook on_hit_by_projectile thay vì take_damage trực tiếp
            # Cho phép malware như RiposteWare xử lý riposte
            if hasattr(self.target, 'on_hit_by_projectile'):
                self.target.on_hit_by_projectile(self)
            else:
                self.target.take_damage(self.damage)
            self._hit = True
            return

        self.x += dx / dist * self.speed * dt
        self.y += dy / dist * self.speed * dt


class MalwareProjectile(BaseProjectile):
    """Đạn bắn từ Ranged Malware, bay thẳng đến goal position.

    Khác với Tower Projectile (homing), MalwareProjectile bay thẳng đến
    một vị trí cố định (goal_pos) mà không theo dõi mục tiêu di chuyển.

    Attributes:
        goal_pos (tuple): Vị trí (row, col) ô lưới đích (server hoặc tower).
        goal_type (str): Loại mục tiêu: "server" hoặc "tower".
        malware_type (str): Loại malware bắn ra (worm, spyware, etc.).

    Usage:
        Tạo khi ranged malware ready to attack:
            proj = MalwareProjectile(source_pos=malware.pos, goal_pos=malware.goal,
                                     goal_type="server", damage=..., speed=...,
                                     malware_type="worm")
            self.projectiles.append(proj)

        game.py cần xử lý hit result từ get_hit_info():
            if proj.has_hit():
                hit_info = proj.get_hit_info()
                # Apply damage đến server hoặc tower tại goal_pos
    """

    def __init__(self, source_pos: tuple, goal_pos: tuple, goal_type: str,
                 damage: int, speed: float, malware_type: str = "worm", affected_cells: list = None):
        """Khởi tạo MalwareProjectile.

        Args:
            source_pos (tuple): Vị trí (row, col) malware bắn ra.
            goal_pos (tuple): Vị trí (row, col) mục tiêu (server hoặc tower).
            goal_type (str): "server" hoặc "tower".
            damage (int): Sát thương.
            speed (float): Tốc độ tính bằng ô/giây.
            malware_type (str): Loại malware (worm, spyware, etc.).
            affected_cells (list): Danh sách ô bị ảnh hưởng (shock spread cho LightSpy_Ranged).
        """
        super().__init__(source_pos, damage, speed, malware_type)
        self.goal_pos = goal_pos
        self.goal_type = goal_type
        self.malware_type = malware_type
        self.affected_cells = affected_cells if affected_cells else []

    def update(self, dt: float):
        """Di chuyển đạn thẳng về phía goal_pos.

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Cập nhật self.x, self.y hướng đến goal_pos (cố định).
            - Đặt self._hit = True khi đạn đến goal_pos.
        """
        # Chuyển goal_pos (row, col) thành pixel (tâm ô)
        goal_x = self.goal_pos[1] * settings.CELL_SIZE + settings.CELL_SIZE // 2
        goal_y = self.goal_pos[0] * settings.CELL_SIZE + settings.CELL_SIZE // 2

        dx = goal_x - self.x
        dy = goal_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        # Kiểm tra nếu đạn đã đến goal
        if dist <= 0 or dist < self.speed * dt:
            self._hit = True
            return

        # Di chuyển đạn về phía goal
        self.x += dx / dist * self.speed * dt
        self.y += dy / dist * self.speed * dt

    def apply_hit(self, game):
        """Áp dụng damage từ projectile đến server hoặc tower.

        Args:
            game (Game): Game object để truy cập server, towers, etc.

        Side effects:
            - Nếu goal_type == "server": Gọi game.server.take_damage(), đặt game.game_over = True nếu server bị phá.
            - Nếu goal_type == "tower": Gọi tower.take_damage(), gọi game._on_tower_destroyed() nếu tower bị phá.

        Note:
            Ranged malware tự gọi apply_hit() từ game.py sau khi projectile kết thúc (_hit=True).
        """
        if self.goal_type == "server":
            game.server.take_damage(self.damage)
            if game.server.is_destroyed():
                game.game_over = True
        elif self.goal_type == "tower":
            tower = game._get_tower_at(self.goal_pos)
            if tower:
                tower.take_damage(self.damage)
                if tower.is_destroyed():
                    game._on_tower_destroyed(tower)

    def get_hit_info(self) -> dict:
        """Trả về thông tin hit để game.py xử lý damage.

        Returns:
            dict: {"goal_pos": (row,col), "goal_type": "server"/"tower", "dmg": damage, "affected_cells": [...]}
        """
        hit = {
            "goal_pos": self.goal_pos,
            "goal_type": self.goal_type,
            "dmg": self.damage
        }
        if self.affected_cells:
            hit["affected_cells"] = self.affected_cells
        return hit

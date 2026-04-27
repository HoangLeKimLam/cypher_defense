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

    def __init__(self, source_pos: tuple, damage: int, speed: float, tower_type: str = "basic"):
        """Khởi tạo BaseProjectile.

        Args:
            source_pos (tuple): Vị trí (row, col) ô lưới.
            damage (int): Sát thương.
            speed (float): Tốc độ tính bằng ô/giây (nhân CELL_SIZE → pixel/giây).
            tower_type (str): Loại (basic, ice, radar, worm, etc.).
        """
        self.damage = damage
        self.speed = speed * settings.CELL_SIZE
        self._hit = False
        self.tower_type = tower_type

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

    def draw(self, screen):
        """Vẽ đạn lên màn hình."""
        import pygame

        # Custom drawing cho trojan_ranged projectile
        if self.tower_type == "trojan_ranged":
            self._draw_trojan_ranged_projectile(screen)
            return

        # Default: sprite hoặc circle
        key = f"proj_{self.tower_type}"
        surf = sprites.get(key)
        if surf:
            w, h = surf.get_size()
            screen.blit(surf, (int(self.x) - w // 2, int(self.y) - h // 2))
        else:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

    def _draw_trojan_ranged_projectile(self, screen):
        """Vẽ projectile trojan_ranged: hình tròn gradient với trail (màu tím)."""
        import pygame
        import math

        x, y = int(self.x), int(self.y)

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

    def __init__(self, source_pos: tuple, target, damage: int, speed: float, tower_type: str = "basic"):
        """Khởi tạo Projectile tại vị trí pixel tâm Tower, nhắm về phía target.

        Args:
            source_pos (tuple): Vị trí (row, col) ô lưới của Tower bắn ra.
            target (Malware): Đối tượng Malware đang bị nhắm bắn.
            damage (int): Sát thương gây ra khi chạm.
            speed (float): Tốc độ đạn tính bằng ô/giây.
            tower_type (str): Loại tower (basic, ice, radar).

        Note:
            Đạn bay theo kiểu "homing" — tính lại hướng đến target mỗi frame,
            vì malware di chuyển trong khi đạn bay.
        """
        super().__init__(source_pos, damage, speed, tower_type)
        self.target = target

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
                 damage: int, speed: float, malware_type: str = "worm"):
        """Khởi tạo MalwareProjectile.

        Args:
            source_pos (tuple): Vị trí (row, col) malware bắn ra.
            goal_pos (tuple): Vị trí (row, col) mục tiêu (server hoặc tower).
            goal_type (str): "server" hoặc "tower".
            damage (int): Sát thương.
            speed (float): Tốc độ tính bằng ô/giây.
            malware_type (str): Loại malware (worm, spyware, etc.).
        """
        super().__init__(source_pos, damage, speed, malware_type)
        self.goal_pos = goal_pos
        self.goal_type = goal_type
        self.malware_type = malware_type

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
            game (Game): Game object để truy cập server_hp, towers, etc.

        Side effects:
            - Trừ game.server_hp nếu goal_type == "server"
            - Gây damage tower nếu goal_type == "tower"
            - Đặt game.game_over = True nếu server_hp <= 0
        """
        if self.goal_type == "server":
            game.server_hp -= self.damage
            if game.server_hp <= 0:
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
            dict: {"goal_pos": (row,col), "goal_type": "server"/"tower", "dmg": damage}
        """
        return {
            "goal_pos": self.goal_pos,
            "goal_type": self.goal_type,
            "dmg": self.damage
        }

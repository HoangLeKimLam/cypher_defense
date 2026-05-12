# entities/boss.py
# Lớp Boss — các enemy mạnh mẽ với kỹ năng đặc biệt

import math
import settings
import ui.sprites as sprites
from core.graph import GridGraph
from core.data_structures import CustomLinkedList, CustomQueue

class Boss:
    """Lớp Boss — enemy mạnh với cơ chế tấn công đặc biệt.

    Không kế thừa từ Malware nhưng có cơ chế tương tự (di chuyển, tấn công).
    Boss có máu cao, sát thương cao, và kỹ năng AoE/lan tỏa.

    Attributes:
        hp (int): Máu hiện tại
        max_hp (int): Máu tối đa
        pos (tuple): Vị trí hiện tại (row, col)
        graph (GridGraph): Bản đồ lưới
        path (list): Đường đi đến server
        speed (float): Tốc độ di chuyển (ô/giây)
        original_speed (float): Tốc độ gốc (trước khi slow)
        slow_timer (float): Thời gian bị slow
        slow_factor (float): Hệ số giảm tốc (0.0-1.0)
    """

    def __init__(self, pos: tuple, graph: GridGraph):
        """Khởi tạo Boss tại vị trí spawn.

        Args:
            pos (tuple): (row, col) vị trí spawn
            graph (GridGraph): Bản đồ lưới
        """
        self.hp = settings.SERVER_MAX_HP  # Mặc định, subclass override
        self.max_hp = self.hp
        self.pos = pos
        self.graph = graph
        self.path = CustomLinkedList()  # Đường đi sẽ được tính sau
        self.speed = 1.0
        self.original_speed = self.speed
        self.slow_timer = 0.0
        self.slow_factor = 1.0
        self.reward = 0

    def is_dead(self) -> bool:
        """Kiểm tra Boss đã chết hay chưa."""
        return self.hp <= 0

    def take_damage(self, damage: float):
        """Nhận sát thương."""
        self.hp = max(0, self.hp - damage)

    def apply_slow(self, factor: float, duration: float):
        """Áp dụng hiệu ứng slow."""
        self.slow_factor = factor
        self.slow_timer = duration

    def update(self, dt: float):
        """Cập nhật Boss mỗi frame (override trong subclass)."""
        if self.slow_timer > 0:
            self.slow_timer -= dt
            if self.slow_timer <= 0:
                self.slow_timer = 0
                self.slow_factor = 1.0

    def draw(self, screen, cell_size: int):
        """Vẽ Boss lên màn hình (override trong subclass)."""
        pass


class FireWorm(Boss):
    """Boss Level 2 - Quái lửa tấn công AoE với hiệu ứng đốt.

    Tấn công toàn bộ tháp trong phạm vị cứ mỗi duration_attack_tower giây.
    Gây hiệu ứng thiêu đốt và lan cháy sang tường gần đó.

    Attributes:
        attack_damage_tower (int): Sát thương khi tấn công tháp
        attack_damage_server (int): Sát thương khi tấn công server
        attack_speed (float): Tốc độ tấn công server (phát/giây)
        attack_range (int): Phạm vị quét tháp (ô)
        duration_attack_tower (float): Khoảng thời gian quét tháp (giây)
        fire_spread_range (int): Phạm vị lan cháy (ô)
        move_progress (float): Tiến độ di chuyển (0.0-1.0) đến ô tiếp theo
        attack_timer (float): Đếm ngược tấn công
        tower_attack_timer (float): Đếm ngược tấn công tháp
        attacking_server (bool): Đang tấn công server
    """

    def __init__(self, pos: tuple, graph: GridGraph):
        """Khởi tạo FireWorm.

        Args:
            pos (tuple): (row, col) vị trí spawn
            graph (GridGraph): Bản đồ lưới
        """
        super().__init__(pos, graph)
        self.hp = settings.FIREWORM_HP
        self.max_hp = self.hp
        self.speed = settings.FIREWORM_SPEED
        self.original_speed = self.speed
        self.attack_damage_tower = settings.FIREWORM_ATTACK_DAMAGE_TOWER
        self.attack_damage_server = settings.FIREWORM_ATTACK_DAMAGE_SERVER
        self.attack_speed = settings.FIREWORM_ATTACK_SPEED
        self.attack_range = settings.FIREWORM_ATTACK_RANGE
        self.duration_attack_tower = settings.FIREWORM_DURATION_ATTACK_TOWER
        self.fire_spread_range = settings.FIREWORM_FIRE_SPREAD_RANGE
        self.reward = settings.FIREWORM_REWARD

        # Timers
        self.move_progress = 0.0
        self.attack_timer = 0.0
        self.tower_attack_timer = 0.0
        self.attacking_server = False
        self._attack_display_timer = 0.0  # Giữ animation Attack sau khi fire
        self.sprite_key = "fireworm"
        self._anim_frame = 0
        self._anim_timer = 0.0
        self._anim_frames = 16

        # Animation state
        self.state = "moving"  # "moving", "attacking_tower", "attacking_server", "dead"

        # Tính đường đi ban đầu
        self.calculate_path()

    def calculate_path(self):
        """Tính đường đi đến server bằng A*."""
        from core.pathfinding import astar
        self.path = astar(self.graph, self.pos, self.graph.server_pos)

    def update(self, dt: float):
        """Cập nhật FireWorm: di chuyển, tấn công tháp, tấn công server.

        Args:
            dt (float): Thời gian frame (giây)
        """
        # Cập nhật slow effect
        super().update(dt)

        if self.is_dead():
            self.state = "dead"
            self.sprite_key = "fireworm_Die"
            # Cập nhật animation
            self._anim_timer += dt
            if self._anim_timer >= 1.0 / settings.ANIM_FPS:
                self._anim_timer = 0.0
                self._anim_frame = (self._anim_frame + 1) % 8
            return
        if self.slow_factor <0.01: return
        # Kiểm tra đã đến server
        if self.pos == self.graph.server_pos:
            self.attacking_server = True
        else:
            # Di chuyển
            current_speed = self.speed * self.slow_factor
            self.move_progress += current_speed * dt

            # Di chuyển sang ô tiếp theo khi progress >= 1.0
            if self.move_progress >= 1.0:
                self.move_progress -= 1.0
                if self.path:
                    self.pos = self.path.pop_head()
                elif self.pos != self.graph.server_pos:
                    # Path hết, tính lại
                    self.calculate_path()

        # Cập nhật bộ đếm tấn công tháp
        self.tower_attack_timer += dt

        # Cập nhật bộ đếm tấn công server
        if self.attacking_server:
            self.attack_timer += dt

        # Cập nhật animation state dựa trên action
        self._update_animation(dt)

    def _update_animation(self, dt: float):
        """Cập nhật sprite và frame theo state hiện tại của FireWorm.

        Args:
            dt (float): Thời gian frame (giây)
        """
        self._anim_timer += dt
        frame_duration = 1.0 / settings.ANIM_FPS

        if self._anim_timer >= frame_duration:
            self._anim_timer = 0.0
            self._anim_frame = (self._anim_frame + 1) % self._anim_frames

        if self._attack_display_timer > 0:
            self._attack_display_timer -= dt

        # Cập nhật sprite_key dựa trên action
        if self._attack_display_timer > 0:
            self.state = "attacking_tower"
            new_key = "fireworm_Attack"
        elif self.attacking_server and self.attack_timer >= 1.0 / self.attack_speed:
            self.state = "attacking_server"
            new_key = "fireworm_Attack"
        else:
            self.state = "moving"
            new_key = "fireworm_Walk"

        if new_key != self.sprite_key:
            self.sprite_key = new_key
            self._anim_frame = 0
            frames = sprites._cache.get(new_key)
            self._anim_frames = len(frames) if frames else 16

    def get_tower_attacks(self) -> list:
        """Trả về danh sách tháp cần tấn công trong phạm vị.

        Được gọi từ game.py để lấy tháp cần hit.

        Returns:
            list: Danh sách {pos: (row,col), damage: int, affected_cells: list}
                  hoặc [] nếu chưa đến lúc tấn công
        """
        if self.tower_attack_timer >= self.duration_attack_tower:
            self.tower_attack_timer = 0.0
            self._attack_display_timer = 16 / settings.ANIM_FPS  # 1 chu kỳ attack animation
            return [{
                "source": self,
                "range": self.attack_range,
                "damage": self.attack_damage_tower,
                "fire_spread_range": self.fire_spread_range,
                "burn_damage": settings.FIREWORM_BURN_DAMAGE_PER_SEC,
                "burn_duration": settings.FIREWORM_BURN_DURATION
            }]
        return []

    def get_server_attack(self) -> dict:
        """Trả về info tấn công server (nếu đang tấn công).

        Returns:
            dict: {"damage": ...} hoặc None
        """
        if self.attacking_server and self.attack_timer >= 1.0 / self.attack_speed:
            self.attack_timer = 0.0
            return {"damage": self.attack_damage_server}
        return None

    def is_alive(self) -> bool:
        """Kiểm tra Boss còn sống."""
        return self.hp > 0

    def has_reached_server(self) -> bool:
        """Kiểm tra đã chạm server."""
        return self.pos == self.graph.server_pos

    def get_render_data(self, cell_size: int):
        """Tạo Surface tổng hợp (Boss + HP bar) cho Y-Sort rendering.

        Args:
            cell_size (int): Kích thước pixel mỗi ô lưới.

        Returns:
            dict: {"surf": Surface, "pos": (x,y), "sort_y": int, "type": "boss"}
        """
        import pygame

        cs = cell_size
        px = self.pos[1] * cs
        py = self.pos[0] * cs

        frames = sprites._cache.get(self.sprite_key) if hasattr(self, 'sprite_key') else None
        if not frames:
            frames = sprites._cache.get("fireworm")

        if frames:
            base_surf = frames[self._anim_frame % len(frames)]
            sw, sh = base_surf.get_size()

            # Tạo Surface tổng hợp với chỗ cho HP bar
            final_surf = pygame.Surface((sw, sh + 10), pygame.SRCALPHA)
            final_surf.blit(base_surf, (0, 10))

            # HP bar
            bar_w = max(cs - 4, sw - 4)
            hp_r = max(0.0, self.hp / self.max_hp)
            bx = (sw - bar_w) // 2
            by = 2
            hp_col = (50, 210, 70) if hp_r > 0.5 else (220, 180, 40) if hp_r > 0.25 else (220, 50, 50)
            pygame.draw.rect(final_surf, (60, 10, 10), (bx, by, bar_w, 3))
            pygame.draw.rect(final_surf, hp_col, (bx, by, int(bar_w * hp_r), 3))

            draw_x = px + (cs - sw) // 2
            draw_y = py + cs - sh - 10

            return {
                'surf': final_surf,
                'pos': (draw_x, draw_y),
                'sort_y': py + cs,
                'type': 'boss'
            }
        else:
            # Fallback
            mid = cs // 2
            fallback = pygame.Surface((cs, cs + 10), pygame.SRCALPHA)
            pygame.draw.circle(fallback, (0, 255, 0), (mid, mid + 10), cs // 3)
            return {
                'surf': fallback,
                'pos': (px, py - 10),
                'sort_y': py + cs,
                'type': 'boss'
            }


class FlyingDemon(Boss):
    """Boss Level 3 - Quái bay thả Bomb ngẫu nhiên + tấn công server.

    Cơ chế chính:
    - Thả bomb ngẫu nhiên mỗi bomb_duration giây:
      - 75% Bomb bình thường (-300 HP, nổ 4-7s random)
      - 25% Atomic bomb (-10000 HP, nổ 4-7s random, thua game nếu nổ)
    - Tấn công server khi chạm (giống FireWorm)

    Attributes:
        attack_damage_server (int): Sát thương khi tấn công server
        attack_speed (float): Tốc độ tấn công server (phát/giây)
        bomb_duration (float): Khoảng thời gian drop bomb (giây)
        move_progress (float): Tiến độ di chuyển (0.0-1.0)
        attack_timer (float): Đếm ngược tấn công server
        bomb_timer (float): Đếm ngược drop bomb
        attacking_server (bool): Đang tấn công server
        dropped_bombs (list): Danh sách bomb được drop (BossBomb)
    """

    def __init__(self, pos: tuple, graph):
        """Khởi tạo FlyingDemon.

        Args:
            pos (tuple): (row, col) vị trí spawn
            graph (GridGraph): Bản đồ lưới
        """
        super().__init__(pos, graph)
        self.hp = settings.FLYINGDEMON_HP
        self.max_hp = self.hp
        self.speed = settings.FLYINGDEMON_SPEED
        self.original_speed = self.speed

        # Attack server
        self.attack_damage_server = settings.FLYINGDEMON_ATTACK_DAMAGE_SERVER
        self.attack_speed = settings.FLYINGDEMON_ATTACK_SPEED
        self.reward = settings.FLYINGDEMON_REWARD

        # Bomb mechanics
        self.bomb_duration = settings.FLYINGDEMON_BOMB_DURATION
        self.bomb_timer = 0.0
        self.dropped_bombs = []

        # Drop effect (chồng lên boss khi drop bomb)
        self.effect_timer = 0.0  # Timer cho effect
        self.effect_duration = 1.5  # 1.5s hiệu ứng

        # Timers
        self.move_progress = 0.0
        self.attack_timer = 0.0
        self.attacking_server = False
        self._attack_display_timer = 0.0  # Giữ animation Attack sau khi fire
        self.sprite_key = "flyingdemon"
        self._anim_frame = 0
        self._anim_timer = 0.0
        self._anim_frames = 10

        # Animation state
        self.state = "moving"  # "moving", "attacking_server", "dead"

        # Tính đường đi ban đầu
        self.calculate_path()

    def calculate_path(self):
        """Tính đường đi đến server bằng A*."""
        from core.pathfinding import astar
        self.path = astar(self.graph, self.pos, self.graph.server_pos)

    def _drop_bomb(self) :
        """Drop bomb ngẫu nhiên (75% normal, 25% atomic) tại vị trí hiện tại.

        Trigger drop effect animation trên boss.

        Returns:
            BossBomb: Bomb vừa drop
        """
        import random
        from entities.bomb import BossBomb

        # Trigger drop effect (0.6s)
        self.effect_timer = self.effect_duration

        # Quyết định loại bomb: 25% atomic, 75% normal
        is_atomic = random.random() < settings.FLYINGDEMON_BOMB_ATOMIC_CHANCE
        bomb_type = "atomic" if is_atomic else "normal"

        # Thời gian nổ random từ 4-7s
        explode_time = random.uniform(
            settings.FLYINGDEMON_BOMB_EXPLODE_MIN,
            settings.FLYINGDEMON_BOMB_EXPLODE_MAX
        )

        # Damage tùy theo loại bomb
        if is_atomic:
            damage = settings.FLYINGDEMON_BOMB_ATOMIC_DAMAGE
        else:
            damage = settings.FLYINGDEMON_BOMB_NORMAL_DAMAGE

        bomb = BossBomb(
            pos=self.pos,
            bomb_type=bomb_type,
            damage=damage,
            stun_duration=settings.FLYINGDEMON_BOMB_STUN_DURATION,
            explode_time=explode_time
        )
        self.dropped_bombs.append(bomb)
        return bomb

    def update(self, dt: float):
        """Cập nhật FlyingDemon: di chuyển, thả bomb, tấn công server.

        Args:
            dt (float): Thời gian frame (giây)
        """
        # Cập nhật slow effect
        super().update(dt)

        # Cập nhật effect timer

        if self.is_dead():
            self.state = "dead"
            self.sprite_key = "flyingdemon_Die"
            self._anim_timer += dt
            if self._anim_timer >= 1.0 / settings.ANIM_FPS:
                self._anim_timer = 0.0
                self._anim_frame = (self._anim_frame + 1) % 12
            return

        if self.slow_factor < 0.01:
            return
        if self.effect_timer > 0:
            self.effect_timer -= dt

        # Cập nhật bomb timer và drop bomb khi đến lúc
        self.bomb_timer += dt
        if self.bomb_timer >= self.bomb_duration:
            self.bomb_timer = 0.0
            self._drop_bomb()

        # Cập nhật bomb đã drop
        for bomb in self.dropped_bombs:
            bomb.update(dt)

        # Kiểm tra đã đến server
        if self.pos == self.graph.server_pos:
            self.attacking_server = True
        else:
            # Di chuyển
            current_speed = self.speed * self.slow_factor
            self.move_progress += current_speed * dt

            # Di chuyển sang ô tiếp theo khi progress >= 1.0
            if self.move_progress >= 1.0:
                self.move_progress -= 1.0
                if self.path:
                    self.pos = self.path.pop_head()
                elif self.pos != self.graph.server_pos:
                    # Path hết, tính lại
                    self.calculate_path()

        # Cập nhật bộ đếm tấn công server
        if self.attacking_server:
            self.attack_timer += dt

        # Cập nhật animation state
        self._update_animation(dt)

    def _update_animation(self, dt: float):
        """Cập nhật sprite và frame theo state của FlyingDemon.

        Args:
            dt (float): Thời gian frame (giây)
        """
        self._anim_timer += dt
        frame_duration = 1.0 / settings.ANIM_FPS

        if self._anim_timer >= frame_duration:
            self._anim_timer = 0.0
            self._anim_frame = (self._anim_frame + 1) % self._anim_frames

        if self._attack_display_timer > 0:
            self._attack_display_timer -= dt

        # Cập nhật sprite_key dựa trên action
        if self._attack_display_timer > 0:
            self.state = "attacking_server"
            new_key = "flyingdemon_Attack"
        else:
            self.state = "moving"
            new_key = "flyingdemon_Flying"

        if new_key != self.sprite_key:
            self.sprite_key = new_key
            self._anim_frame = 0
            frames = sprites._cache.get(new_key)
            self._anim_frames = len(frames) if frames else 8

    def get_server_attack(self) -> dict:
        """Trả về info tấn công server (nếu đang tấn công).

        Returns:
            dict: {"damage": ...} hoặc None
        """
        if self.attacking_server and self.attack_timer >= 1.0 / self.attack_speed:
            self.attack_timer = 0.0
            attack_frames = sprites._cache.get("flyingdemon_Attack")
            n = len(attack_frames) if attack_frames else 8
            self._attack_display_timer = n / settings.ANIM_FPS
            return {"damage": self.attack_damage_server}
        return None

    def is_alive(self) -> bool:
        """Kiểm tra Boss còn sống."""
        return self.hp > 0

    def has_reached_server(self) -> bool:
        """Kiểm tra đã chạm server."""
        return self.pos == self.graph.server_pos

    def get_bombs(self) -> list:
        """Trả về danh sách bomb hiện tại.

        Returns:
            list: Danh sách BossBomb
        """
        return self.dropped_bombs

    def remove_bomb(self, bomb):
        """Xóa bomb khỏi danh sách khi đã remove khỏi game.

        Args:
            bomb (BossBomb): Bomb cần xóa
        """
        if bomb in self.dropped_bombs:
            self.dropped_bombs.remove(bomb)

    def get_render_data(self, cell_size: int):  # noqa: F811
        """Tạo Surface tổng hợp (Boss + HP bar + attack effect) cho Y-Sort rendering.

        Args:
            cell_size (int): Kích thước pixel mỗi ô lưới.

        Returns:
            dict: {"surf": Surface, "pos": (x,y), "sort_y": int, "type": "boss", "attack_effect": {...}}
        """
        import pygame

        cs = cell_size
        px = self.pos[1] * cs
        py = self.pos[0] * cs

        frames = sprites._cache.get(self.sprite_key) if hasattr(self, 'sprite_key') else None
        if not frames:
            frames = sprites._cache.get("flyingdemon")

        if frames:
            base_surf = frames[self._anim_frame % len(frames)]
            sw, sh = base_surf.get_size()

            # Tạo Surface tổng hợp với chỗ cho HP bar
            final_surf = pygame.Surface((sw, sh + 10), pygame.SRCALPHA)
            final_surf.blit(base_surf, (0, 10))

            # HP bar
            bar_w = max(cs - 4, sw - 4)
            hp_r = max(0.0, self.hp / self.max_hp)
            bx = (sw - bar_w) // 2
            by = 2
            hp_col = (50, 210, 70) if hp_r > 0.5 else (220, 180, 40) if hp_r > 0.25 else (220, 50, 50)
            pygame.draw.rect(final_surf, (60, 10, 10), (bx, by, bar_w, 3))
            pygame.draw.rect(final_surf, hp_col, (bx, by, int(bar_w * hp_r), 3))

            draw_x = px + (cs - sw) // 2
            draw_y = py + cs - sh - 10

            result = {
                'surf': final_surf,
                'pos': (draw_x, draw_y),
                'sort_y': py + cs,
                'type': 'boss'
            }

            # Thêm attack effect data nếu còn effect_timer
            if self.effect_timer > 0:
                effect_frames = sprites._cache.get("flyingdemon_attack_effect")
                if effect_frames:
                    # Tính progress của effect (0.0 -> 1.0)
                    effect_progress = 1.0 - (self.effect_timer / self.effect_duration)
                    effect_frame_idx = int(effect_progress * len(effect_frames))
                    effect_frame_idx = min(effect_frame_idx, len(effect_frames) - 1)
                    effect_surf = effect_frames[effect_frame_idx]

                    result['attack_effect'] = {
                        'surf': effect_surf,
                        'pos': (draw_x + (sw - effect_surf.get_width()) // 2, 
                                draw_y + (sh - effect_surf.get_height()) // 2),
                        'alpha': int(255 * (1.0 - effect_progress))  # Fade out
                    }

            return result
        else:
            # Fallback
            mid = cs // 2
            fallback = pygame.Surface((cs, cs + 10), pygame.SRCALPHA)
            pygame.draw.circle(fallback, (100, 50, 200), (mid, mid + 10), cs // 3)
            return {
                'surf': fallback,
                'pos': (px, py - 10),
                'sort_y': py + cs,
                'type': 'boss'
            }


class Shadow(Boss):
    """Boss Level 4 - Kẻ tàng hình với cơ chế lăn bất tử.

    Khi xuất hiện: tất cả malware trên map trở nên tàng hình vĩnh viễn.
    Cơ chế Roll: mỗi 5 giây, vào trạng thái lăn 3 giây:
        - Tốc độ di chuyển tăng (x3), bất tử với đạn tháp
        - Hiệu ứng đốt/chậm vẫn dính
        - Damage và attack speed tăng khi ở server

    Attributes:
        roll_cooldown_timer (float): Đếm ngược đến lần Roll tiếp theo (giây).
        roll_timer (float): Đếm ngược thời gian Roll còn lại (giây).
        is_rolling (bool): True khi đang ở trạng thái Roll.
        roll_phase (str): Giai đoạn Roll hiện tại: "pre", "mid", hoặc "end".
        move_progress (float): Tiến độ di chuyển (0.0–1.0) đến ô tiếp theo.
        attacking_server (bool): True khi đã chạm ô server_pos.
        server_attack_timer (float): Đếm ngược giữa các đòn tấn công server.
        _sprite_key (str): Key sprite hiện tại trong cache.
        _anim_frame (int): Frame animation hiện tại.
        _anim_timer (float): Đếm thời gian đến frame kế tiếp.
        _anim_frames (int): Tổng số frame animation hiện tại.
        state (str): Trạng thái hiện tại: "moving", "rolling", "attacking_server", "dead".

    Animation: Walk(14f) → Roll[Pre(3f)→Mid(4f loop)→End(7f)] → Attack(10f) / Die(33f)
    """

    ROLL_COOLDOWN = 5.0
    ROLL_DURATION = 3.0
    ROLL_SPEED_MULT = 3.0
    ROLL_DMG_MULT = 2.5
    ROLL_RATE_MULT = 3.0

    def __init__(self, pos: tuple, graph: GridGraph):
        """Khởi tạo Shadow Boss tại vị trí spawn.

        Args:
            pos (tuple): (row, col) vị trí spawn trên lưới.
            graph (GridGraph): Bản đồ lưới.

        Side effects:
            - Gọi calculate_path() để tính A* đến server ngay khi spawn.
            - Đặt tất cả timer và state về giá trị ban đầu.
        """
        super().__init__(pos, graph)
        self.hp = 1200
        self.max_hp = self.hp
        self.speed = 1.5
        self.original_speed = self.speed
        self.attack_damage = 35
        self.attack_speed = 0.6
        self.reward = 500

        self.roll_cooldown_timer = self.ROLL_COOLDOWN
        self.roll_timer = 0.0
        self.is_rolling = False
        self.roll_phase = "pre"

        self.move_progress = 0.0
        self.attacking_server = False
        self.server_attack_timer = 0.0

        self._sprite_key = "shadow_Walk"
        self._anim_frame = 0
        self._anim_timer = 0.0
        self._anim_frames = 14
        self.state = "moving"

        self.calculate_path()

    def calculate_path(self):
        """Tính đường đi A* từ vị trí hiện tại đến server.

        Side effects:
            - Ghi đè self.path bằng kết quả A*.
        """
        from core.pathfinding import astar
        self.path = astar(self.graph, self.pos, self.graph.server_pos)

    def take_damage(self, damage: float):
        """Nhận sát thương — bất tử khi đang Roll.

        Args:
            damage (float): Sát thương nhận vào.

        Side effects:
            - Nếu is_rolling = True: bỏ qua hoàn toàn, không trừ HP.
            - Ngược lại: trừ HP tối thiểu 0.
        """
        if self.is_rolling:
            return
        self.hp = max(0, self.hp - damage)

    def update(self, dt: float):
        """Cập nhật Shadow Boss mỗi frame: slow, roll, di chuyển, tấn công server.

        Args:
            dt (float): Thời gian frame (giây).

        Side effects:
            - Gọi _update_roll() để quản lý chu kỳ Roll.
            - Gọi _move() để di chuyển trên lưới.
            - Tích lũy server_attack_timer khi đang tấn công server.
            - Cập nhật animation qua _update_animation().
        """
        super().update(dt)
        if self.is_dead():
            self.state = "dead"
            self._anim_simple("shadow_Die", 33, dt)
            return
        if self.slow_factor < 0.01:
            return    
        self._update_roll(dt)
        self._move(dt)
        if self.attacking_server:
            self.server_attack_timer += dt
        self._update_animation(dt)

    def _move(self, dt: float):
        """Di chuyển Shadow theo path; tốc độ nhân ROLL_SPEED_MULT khi đang Roll.

        Args:
            dt (float): Thời gian frame (giây).

        Side effects:
            - Cập nhật move_progress và self.pos khi progress >= 1.0.
            - Đặt attacking_server = True khi chạm server_pos.
            - Gọi calculate_path() nếu path cạn.
        """
        if self.pos == self.graph.server_pos:
            self.attacking_server = True
            return
        spd = self.speed * self.slow_factor
        if self.is_rolling:
            spd *= self.ROLL_SPEED_MULT
        self.move_progress += spd * dt
        if self.move_progress >= 1.0:
            self.move_progress -= 1.0
            nxt = self.path.pop_head()
            if nxt:
                self.pos = nxt
            else:
                self.calculate_path()

    def _update_roll(self, dt: float):
        """Quản lý chu kỳ Roll: đếm cooldown → kích hoạt Roll → đếm hết Roll.

        Args:
            dt (float): Thời gian frame (giây).

        Side effects:
            - Khi cooldown hết: đặt is_rolling=True, roll_phase="pre", reset timers.
            - Khi roll hết thời gian: chuyển roll_phase sang "end".
            - _update_animation() xử lý việc kết thúc phase "end" (is_rolling=False).
        """
        if self.is_rolling:
            self.roll_timer -= dt
            if self.roll_timer <= 0 and self.roll_phase != "end":
                self.roll_phase = "end"
                self._anim_frame = 0
        else:
            self.roll_cooldown_timer -= dt
            if self.roll_cooldown_timer <= 0:
                self.is_rolling = True
                self.roll_timer = self.ROLL_DURATION
                self.roll_phase = "pre"
                self._anim_frame = 0
                self.roll_cooldown_timer = self.ROLL_COOLDOWN

    def _update_animation(self, dt: float):
        """Cập nhật sprite key và frame animation theo state hiện tại.

        Args:
            dt (float): Thời gian frame (giây).

        Side effects:
            - Tăng _anim_frame theo ANIM_FPS.
            - Cập nhật _sprite_key và loop frame tương ứng state.
            - Khi roll_phase "end" kết thúc (>= 7 frames): đặt is_rolling = False.
        """
        self._anim_timer += dt
        if self._anim_timer >= 1.0 / settings.ANIM_FPS:
            self._anim_timer -= 1.0 / settings.ANIM_FPS
            self._anim_frame += 1

        if self.is_rolling:
            self.state = "rolling"
            if self.roll_phase == "pre":
                self._sprite_key = "shadow_Roll_Pre"
                if self._anim_frame >= 3:
                    self.roll_phase = "mid"
                    self._anim_frame = 0
            elif self.roll_phase == "mid":
                self._sprite_key = "shadow_Roll_Mid"
                self._anim_frame %= 4
            elif self.roll_phase == "end":
                self._sprite_key = "shadow_Roll_End"
                if self._anim_frame >= 7:
                    self.is_rolling = False
                    self.roll_phase = "pre"
                    self._anim_frame = 0
        elif self.attacking_server:
            self._sprite_key = "shadow_Attack"
            self.state = "attacking_server"
            self._anim_frame %= 10
        else:
            self._sprite_key = "shadow_Walk"
            self.state = "moving"
            self._anim_frame %= 14

    def _anim_simple(self, key: str, total: int, dt: float):
        """Chạy animation đơn giản một chiều (không loop) theo ANIM_FPS.

        Args:
            key (str): Sprite key trong cache.
            total (int): Tổng số frame; dừng ở frame total-1.
            dt (float): Thời gian frame (giây).

        Side effects:
            - Đặt _sprite_key = key.
            - Tăng _anim_frame tối đa đến total-1 (không wrap).
        """
        self._sprite_key = key
        self._anim_timer += dt
        if self._anim_timer >= 1.0 / settings.ANIM_FPS:
            self._anim_timer -= 1.0 / settings.ANIM_FPS
            self._anim_frame = min(self._anim_frame + 1, total - 1)

    def get_server_attack(self) -> dict:
        """Trả về info tấn công server nếu đến lúc (tốc độ và damage tăng khi Roll).

        Khi đang Roll: attack_speed × ROLL_RATE_MULT, damage × ROLL_DMG_MULT.

        Returns:
            dict: {"damage": float} khi đến lúc tấn công.
            None: chưa đến lúc hoặc không ở server.

        Side effects:
            - Reset server_attack_timer về 0 khi tấn công.
        """
        if not self.attacking_server:
            return None
        rate = self.attack_speed * (self.ROLL_RATE_MULT if self.is_rolling else 1.0)
        dmg = self.attack_damage * (self.ROLL_DMG_MULT if self.is_rolling else 1.0)
        if self.server_attack_timer >= 1.0 / rate:
            self.server_attack_timer = 0.0
            return {"damage": dmg}
        return None

    def has_reached_server(self) -> bool:
        """Kiểm tra Shadow đã chạm ô server_pos.

        Returns:
            bool: True nếu self.pos == graph.server_pos.
        """
        return self.pos == self.graph.server_pos

    def get_render_data(self, cell_size: int):
        """Tạo Surface tổng hợp (Boss + HP bar) cho Y-Sort rendering.

        Args:
            cell_size (int): Kích thước pixel mỗi ô lưới.

        Returns:
            dict: {"surf": Surface, "pos": (x,y), "sort_y": int, "type": "boss"}.
        """
        import pygame

        cs = cell_size
        px, py = self.pos[1] * cs, self.pos[0] * cs
        frames = sprites._cache.get(self._sprite_key) or sprites._cache.get("shadow_Walk")

        if frames:
            base = frames[self._anim_frame % len(frames)]
            sw, sh = base.get_size()
            surf = pygame.Surface((sw, sh + 10), pygame.SRCALPHA)
            surf.blit(base, (0, 10))


            bar_w = max(cs - 4, sw - 4)
            hp_r = max(0.0, self.hp / self.max_hp)
            bx = (sw - bar_w) // 2
            col = (50, 210, 70) if hp_r > 0.5 else (220, 180, 40) if hp_r > 0.25 else (220, 50, 50)
            pygame.draw.rect(surf, (60, 10, 10), (bx, 2, bar_w, 3))
            pygame.draw.rect(surf, col, (bx, 2, int(bar_w * hp_r), 3))

            return {'surf': surf, 'pos': (px + (cs - sw) // 2, py + cs - sh - 10),
                    'sort_y': py + cs, 'type': 'boss'}

        fallback = pygame.Surface((cs, cs + 10), pygame.SRCALPHA)
        pygame.draw.circle(fallback, (50, 50, 80), (cs // 2, cs // 2 + 10), cs // 3)
        return {'surf': fallback, 'pos': (px, py - 10), 'sort_y': py + cs, 'type': 'boss'}


class RiposteBoss(Boss):
    """Bosslv1: phiên bản của RiposteWare — cùng cơ chế phản đạn, to hơn, mạnh hơn.

    Kế thừa cơ chế riposte: 50% phản đạn projectile trở lại Tower.
    Sát thương phản đạn = attack_damage + projectile.damage.
    Khác RiposteWare (malware): đi A* thẳng đến Server, không hunt Tower.

    Attributes:
        _riposte_chance (float): Xác suất phản đạn (mặc định 0.5).
        _projectile_queue (CustomQueue): Queue lưu projectile phản đạn chờ game.py thu.
        server_attack_timer (float): Đếm thời gian tấn công server.
        server_attack_speed (float): Số đòn/giây khi ở server.
    """

    def __init__(self, pos: tuple, graph: GridGraph):
        """Khởi tạo RiposteBoss với cơ chế phản đạn và A* đến server.

        Args:
            pos (tuple): (row, col) vị trí spawn trên lưới.
            graph (GridGraph): Bản đồ lưới.

        Side effects:
            - Đặt tất cả chỉ số chiến đấu và timers về giá trị ban đầu.
            - Gọi calculate_path() để tính A* đến server ngay khi spawn.
        """
        super().__init__(pos, graph)
        self.hp = 800
        self.max_hp = self.hp
        self.speed = 1.4
        self.original_speed = self.speed
        self.attack_damage = 50
        self.reward = 400
        self._riposte_chance = 0.5

        self.server_attack_timer = 0.0
        self.server_attack_speed = 0.5  # đòn/giây khi ở server
        self.attacking_server = False

        self._projectile_queue = CustomQueue()

        # Animation (dùng sprite riposteware)
        self._sprite_key = "riposteware_Run"
        self._anim_frame = 0
        self._anim_timer = 0.0
        self._anim_frames = 8
        self.state = "moving"

        self.calculate_path()

    def calculate_path(self):
        """A* thẳng đến server."""
        from core.pathfinding import astar
        self.path = astar(self.graph, self.pos, self.graph.server_pos)

    def update(self, dt: float):
        """Cập nhật RiposteBoss mỗi frame: slow, di chuyển A*, tấn công server, animation.

        Args:
            dt (float): Thời gian frame (giây).

        Side effects:
            - Di chuyển theo path đến server, tính lại nếu path cạn.
            - Đặt attacking_server = True khi chạm server_pos.
            - Tích lũy server_attack_timer; cập nhật animation frame.
        """
        super().update(dt)  # cập nhật slow timer

        if self.is_dead():
            self.state = "dead"
            self._sprite_key = "riposteware_Run"
            self._anim_timer += dt
            if self._anim_timer >= 1.0 / settings.ANIM_FPS:
                self._anim_timer = 0.0
                self._anim_frame = (self._anim_frame + 1) % self._anim_frames
            return

        if self.slow_factor < 0.01:
            return

        if self.pos == self.graph.server_pos:
            self.attacking_server = True
            self.state = "attacking_server"
            self._sprite_key = "riposteware_Attack"
        else:
            current_speed = self.speed * self.slow_factor
            self.move_progress = getattr(self, 'move_progress', 0.0) + current_speed * dt
            if self.move_progress >= 1.0:
                self.move_progress -= 1.0
                next_cell = self.path.pop_head()
                if next_cell:
                    self.pos = next_cell
                else:
                    self.calculate_path()
            self.state = "moving"
            self._sprite_key = "riposteware_Run"

        if self.attacking_server:
            self.server_attack_timer += dt

        self._anim_timer += dt
        if self._anim_timer >= 1.0 / settings.ANIM_FPS:
            self._anim_timer = 0.0
            self._anim_frame = (self._anim_frame + 1) % self._anim_frames

    def on_hit_by_projectile(self, projectile):
        """Xử lý khi bị bắn — 50% phản đạn về Tower nguồn, nhận damage nếu không phản.

        Args:
            projectile: Đạn bắn vào (phải có thuộc tính damage và source_tower).

        Side effects:
            - Nếu phản thành công: tạo MalwareProjectile vào _projectile_queue, không trừ HP.
            - Nếu không phản: gọi take_damage(projectile.damage).
        """
        import random
        from entities.projectile import MalwareProjectile

        if random.random() < self._riposte_chance and projectile.source_tower:
            riposte_damage = self.attack_damage + projectile.damage
            riposte_proj = MalwareProjectile(
                source_pos=self.pos,
                goal_pos=projectile.source_tower.pos,
                goal_type="tower",
                damage=riposte_damage,
                speed=settings.PROJECTILE_SPEED,
                malware_type="riposteware"
            )
            self._projectile_queue.enqueue(riposte_proj)
        else:
            self.take_damage(projectile.damage)

    def get_projectiles(self) -> list:
        """Drain toàn bộ MalwareProjectile phản đạn ra list để game.py xử lý.

        Returns:
            list[MalwareProjectile]: Danh sách projectile đang chờ trong queue.
                Trả về [] nếu không có projectile mới.

        Side effects:
            - Làm rỗng _projectile_queue sau khi drain.
        """
        projectiles = []
        while not self._projectile_queue.is_empty():
            projectiles.append(self._projectile_queue.dequeue())
        return projectiles

    def get_server_attack(self) -> dict:
        """Trả về info tấn công server nếu đến lúc theo server_attack_speed.

        Returns:
            dict: {"damage": int} khi đến lúc tấn công.
            None: chưa đến lúc hoặc không ở server.

        Side effects:
            - Reset server_attack_timer về 0 khi tấn công.
        """
        if self.attacking_server and self.server_attack_timer >= 1.0 / self.server_attack_speed:
            self.server_attack_timer = 0.0
            return {"damage": self.attack_damage}
        return None

    def has_reached_server(self) -> bool:
        """Kiểm tra RiposteBoss đã chạm ô server_pos.

        Returns:
            bool: True nếu self.pos == graph.server_pos.
        """
        return self.pos == self.graph.server_pos

    def get_render_data(self, cell_size: int):
        """Tạo Surface tổng hợp (Boss scale 1.5× + HP bar) cho Y-Sort rendering.

        Args:
            cell_size (int): Kích thước pixel mỗi ô lưới.

        Returns:
            dict: {"surf": Surface, "pos": (x,y), "sort_y": int, "type": "boss"}.
        """
        import pygame

        cs = cell_size
        px = self.pos[1] * cs
        py = self.pos[0] * cs

        frames = sprites._cache.get(self._sprite_key) or sprites._cache.get("riposteware_Run")

        if frames:
            base_surf = frames[self._anim_frame % len(frames)]
            sw, sh = base_surf.get_size()
            # Scale up 1.5× so boss looks bigger than normal RiposteWare
            boss_w = int(sw * 1.5)
            boss_h = int(sh * 1.5)
            base_surf = pygame.transform.scale(base_surf, (boss_w, boss_h))
            sw, sh = boss_w, boss_h

            final_surf = pygame.Surface((sw, sh + 10), pygame.SRCALPHA)
            final_surf.blit(base_surf, (0, 10))

            bar_w = max(cs - 4, sw - 4)
            hp_r = max(0.0, self.hp / self.max_hp)
            bx = (sw - bar_w) // 2
            hp_col = (50, 210, 70) if hp_r > 0.5 else (220, 180, 40) if hp_r > 0.25 else (220, 50, 50)
            pygame.draw.rect(final_surf, (60, 10, 10), (bx, 2, bar_w, 3))
            pygame.draw.rect(final_surf, hp_col, (bx, 2, int(bar_w * hp_r), 3))

            draw_x = px + (cs - sw) // 2
            draw_y = py + cs - sh - 10
            return {'surf': final_surf, 'pos': (draw_x, draw_y), 'sort_y': py + cs, 'type': 'boss'}

        mid = cs // 2
        fallback = pygame.Surface((cs, cs + 10), pygame.SRCALPHA)
        pygame.draw.circle(fallback, (200, 100, 200), (mid, mid + 10), cs // 3)
        return {'surf': fallback, 'pos': (px, py - 10), 'sort_y': py + cs, 'type': 'boss'}


class Final(Boss):
    """Boss Level 5 — Final Boss. Đi thẳng col++ từ (12,0), phá 3×3 ô cản trở,
    spawn RiposteWare tại mỗi ô bị phá, phản đạn 25% thẳng vào server,
    thả bomb giống FlyingDemon.

    Movement: col++ mỗi bước, không dùng A*/BFS.
    Destroy: nếu next cell không phải PATH/SERVER → play Destroy_1(10f)→Destroy_2(10f)
             → queue 3×3 cells cho game.py xử lý (clear + spawn RiposteWare).
    Reflection: 25% khi bị bắn → MalwareProjectile bay thẳng vào server.
    Bombs: 75% normal / 25% atomic, purple glow 0.6s sau khi thả.
    """

    FIXED_ROW = 12

    def __init__(self, pos: tuple, graph: GridGraph):
        """Khởi tạo Final Boss tại hàng cố định FIXED_ROW, cột 0.

        Args:
            pos (tuple): (row, col) bị bỏ qua — Final luôn spawn tại (FIXED_ROW, 0).
            graph (GridGraph): Bản đồ lưới.

        Side effects:
            - Ghi đè self.pos thành (FIXED_ROW, 0) bất kể pos truyền vào.
            - Khởi tạo spawn_queue, bomb mechanics, projectile queue, animation state.
        """
        super().__init__(pos, graph)
        self.pos = (self.FIXED_ROW, 0)
        self.hp = 5000
        self.max_hp = self.hp
        self.speed = 0.7
        self.original_speed = self.speed
        self.attack_damage = 75
        self.attack_speed = 0.4
        self.reward = 1000
        self._riposte_chance = 0.25

        self.move_progress = 0.0
        self.attacking_server = False
        self.server_attack_timer = 0.0

        # Destruction state
        self._destroy_phase = 0   # 1 = Destroy_1 anim, 2 = Destroy_2 anim
        self._destroy_frame = 0
        self.spawn_queue = []     # (row, col) cells game.py must clear + spawn RiposteWare

        # Projectile reflection queue
        self._projectile_queue = CustomQueue()

        # Bomb (identical to FlyingDemon)
        self.bomb_duration = 15
        self.bomb_timer = 0.0
        self.dropped_bombs = []
        self.effect_timer = 0.0
        self.effect_duration = 1.5

        # Animation
        self._sprite_key = "final_Walk"
        self._anim_frame = 0
        self._anim_timer = 0.0
        self.state = "moving"

    def update(self, dt: float):
        """Cập nhật Final Boss mỗi frame: di chuyển col++, phá tường, tấn công server.

        Args:
            dt (float): Thời gian frame (giây).

        Side effects:
            - Tick bomb_timer; gọi _drop_bomb() khi đến hạn.
            - Nếu state == "destroying": gọi _update_destroy(), block movement.
            - Di chuyển sang cột tiếp theo; nếu gặp ô không phải PATH → "destroying".
            - Đặt attacking_server = True khi chạm SERVER hoặc vượt qua cột cuối.
        """
        super().update(dt)

        if self.is_dead():
            self.state = "dead"
            self._sprite_key = "final_Die"
            self._advance_anim(dt, 10, loop=False)
            return

        if self.slow_factor < 0.01:
            return

        # Bombs tick every frame regardless of state
        if self.effect_timer > 0:
            self.effect_timer -= dt
        self.bomb_timer += dt
        if self.bomb_timer >= self.bomb_duration:
            self.bomb_timer = 0.0
            self._drop_bomb()
        for bomb in self.dropped_bombs:
            bomb.update(dt)

        # Destroy animation blocks movement
        if self.state == "destroying":
            self._update_destroy(dt)
            return

        # Attacking server
        if self.attacking_server:
            self.server_attack_timer += dt
            self._sprite_key = "final_Attack"
            self._advance_anim(dt, 7, loop=True)
            return

        row, col = self.pos
        next_col = col + 1

        if next_col >= self.graph.col:
            self.attacking_server = True
            return

        from core.graph import Celltype
        next_cell = self.graph.get_cell(row, next_col)

        if next_cell == Celltype.SERVER:
            self.pos = (row, next_col)
            self.attacking_server = True
            return

        if next_cell != Celltype.PATH:
            # Obstacle: enter destroy animation
            self.state = "destroying"
            self._destroy_phase = 1
            self._destroy_frame = 0
            self._anim_frame = 0
            self._anim_timer = 0.0
            return

        # Move forward one cell
        self.move_progress += self.speed * self.slow_factor * dt
        if self.move_progress >= 1.0:
            self.move_progress -= 1.0
            self.pos = (row, next_col)

        self._sprite_key = "final_Walk"
        self._advance_anim(dt, 8, loop=True)

    def _update_destroy(self, dt: float):
        """Chạy animation phá hủy 2 phase; thực thi phá hủy cuối phase 2.

        Args:
            dt (float): Thời gian frame (giây).

        Side effects:
            - Phase 1 (Destroy_1, 10f): chơi xong → chuyển sang phase 2.
            - Phase 2 (Destroy_2, 10f): chơi xong → gọi _execute_destroy(),
              đặt state = "moving", reset destroy counters.
        """
        self._anim_timer += dt
        if self._anim_timer >= 1.0 / settings.ANIM_FPS:
            self._anim_timer -= 1.0 / settings.ANIM_FPS
            self._destroy_frame += 1

        if self._destroy_phase == 1:
            self._sprite_key = "final_Destroy_1"
            self._anim_frame = min(self._destroy_frame, 9)
            if self._destroy_frame >= 10:
                self._destroy_phase = 2
                self._destroy_frame = 0

        elif self._destroy_phase == 2:
            self._sprite_key = "final_Destroy_2"
            self._anim_frame = min(self._destroy_frame, 9)
            if self._destroy_frame >= 10:
                self._execute_destroy()
                self.state = "moving"
                self._destroy_phase = 0
                self._destroy_frame = 0
                self._anim_frame = 0

    def _execute_destroy(self):
        """Queue ô hàng ±1, cột +1..+3 (non-PATH/SERVER/SPAWN) để game.py phá và spawn.

        Side effects:
            - Append các (row, col) hợp lệ vào spawn_queue.
            - game.py drain spawn_queue mỗi frame: clear cell + spawn RiposteWare.
        """
        from core.graph import Celltype
        row, col = self.pos
        for dr in (-1, 0, 1):
            for dc in (1, 2, 3):
                r, c = row + dr, col + dc
                if 0 <= r < self.graph.row and 0 <= c < self.graph.col:
                    cell = self.graph.get_cell(r, c)
                    if cell not in (Celltype.PATH, Celltype.SERVER, Celltype.SPAWN):
                        self.spawn_queue.append((r, c))

    def drain_spawn_queue(self) -> list:
        """Trả về và xóa danh sách ô cần phá; game.py gọi mỗi frame.

        Returns:
            list[tuple]: Danh sách (row, col) ô cần clear + spawn RiposteWare.
                Trả về [] nếu không có ô mới.

        Side effects:
            - Làm rỗng self.spawn_queue sau khi drain.
        """
        result = list(self.spawn_queue)
        self.spawn_queue = []
        return result

    def _drop_bomb(self):
        """Thả bomb tại vị trí hiện tại (75% normal, 25% atomic) giống FlyingDemon.

        Returns:
            BossBomb: Bomb vừa tạo và thêm vào dropped_bombs.

        Side effects:
            - Đặt effect_timer = effect_duration (hiệu ứng glow 1.5s).
            - Append bomb mới vào self.dropped_bombs.
        """
        import random
        from entities.bomb import BossBomb
        self.effect_timer = self.effect_duration
        is_atomic = random.random() < settings.FLYINGDEMON_BOMB_ATOMIC_CHANCE
        bomb_type = "atomic" if is_atomic else "normal"
        explode_time = random.uniform(
            settings.FLYINGDEMON_BOMB_EXPLODE_MIN,
            settings.FLYINGDEMON_BOMB_EXPLODE_MAX
        )
        damage = (settings.FLYINGDEMON_BOMB_ATOMIC_DAMAGE if is_atomic
                  else settings.FLYINGDEMON_BOMB_NORMAL_DAMAGE)
        bomb = BossBomb(
            pos=self.pos,
            bomb_type=bomb_type,
            damage=damage,
            stun_duration=settings.FLYINGDEMON_BOMB_STUN_DURATION,
            explode_time=explode_time
        )
        self.dropped_bombs.append(bomb)
        return bomb

    def get_bombs(self) -> list:
        """Trả về danh sách bomb đang hoạt động.

        Returns:
            list[BossBomb]: Danh sách BossBomb chưa nổ hoặc đang nổ.
        """
        return self.dropped_bombs

    def remove_bomb(self, bomb):
        """Xóa bomb khỏi danh sách khi game.py đã xử lý xong.

        Args:
            bomb (BossBomb): Bomb cần xóa.

        Side effects:
            - Xóa bomb khỏi self.dropped_bombs nếu tồn tại.
        """
        if bomb in self.dropped_bombs:
            self.dropped_bombs.remove(bomb)

    def on_hit_by_projectile(self, projectile):
        """Xử lý khi bị bắn — 25% phản đạn thẳng vào server, nhận damage nếu không phản.

        Args:
            projectile: Đạn bắn vào (phải có thuộc tính damage).

        Side effects:
            - Nếu phản: tạo MalwareProjectile bay thẳng vào server, enqueue vào _projectile_queue.
            - Nếu không phản: gọi take_damage(projectile.damage).
        """
        import random
        from entities.projectile import MalwareProjectile
        if random.random() < self._riposte_chance:
            riposte = MalwareProjectile(
                source_pos=self.pos,
                goal_pos=self.graph.server_pos,
                goal_type="server",
                damage=self.attack_damage + projectile.damage,
                speed=settings.PROJECTILE_SPEED,
                malware_type="riposteware"
            )
            self._projectile_queue.enqueue(riposte)
        else:
            self.take_damage(projectile.damage)

    def get_projectiles(self) -> list:
        """Drain toàn bộ MalwareProjectile phản đạn ra list để game.py xử lý.

        Returns:
            list[MalwareProjectile]: Danh sách projectile đang chờ trong queue.
                Trả về [] nếu không có projectile mới.

        Side effects:
            - Làm rỗng _projectile_queue sau khi drain.
        """
        result = []
        while not self._projectile_queue.is_empty():
            result.append(self._projectile_queue.dequeue())
        return result

    def get_server_attack(self) -> dict:
        """Trả về info tấn công server nếu đến lúc theo attack_speed.

        Returns:
            dict: {"damage": int} khi đến lúc tấn công.
            None: chưa đến lúc hoặc không ở server.

        Side effects:
            - Reset server_attack_timer về 0 khi tấn công.
        """
        if self.attacking_server and self.server_attack_timer >= 1.0 / self.attack_speed:
            self.server_attack_timer = 0.0
            return {"damage": self.attack_damage}
        return None

    def has_reached_server(self) -> bool:
        """Kiểm tra Final Boss đang tấn công server.

        Returns:
            bool: True khi attacking_server = True (chạm SERVER hoặc vượt cột cuối).
        """
        return self.attacking_server

    def _advance_anim(self, dt: float, total: int, loop: bool = True):
        """Tăng frame animation theo ANIM_FPS, hỗ trợ loop hoặc dừng ở frame cuối.

        Args:
            dt (float): Thời gian frame (giây).
            total (int): Tổng số frame của animation hiện tại.
            loop (bool): True = vòng lại từ đầu; False = dừng ở frame total-1.

        Side effects:
            - Tích lũy _anim_timer; tăng _anim_frame khi đủ 1/ANIM_FPS.
        """
        self._anim_timer += dt
        if self._anim_timer >= 1.0 / settings.ANIM_FPS:
            self._anim_timer -= 1.0 / settings.ANIM_FPS
            if loop:
                self._anim_frame = (self._anim_frame + 1) % total
            else:
                self._anim_frame = min(self._anim_frame + 1, total - 1)

    def get_render_data(self, cell_size: int):
        """Tạo Surface tổng hợp (Boss + HP bar + purple glow khi thả bomb) cho Y-Sort.

        Args:
            cell_size (int): Kích thước pixel mỗi ô lưới.

        Returns:
            dict: {"surf": Surface, "pos": (x,y), "sort_y": int, "type": "boss"}.
                Thêm key "attack_effect" nếu effect_timer > 0.
        """
        import pygame
        cs = cell_size
        px, py = self.pos[1] * cs, self.pos[0] * cs
        frames = sprites._cache.get(self._sprite_key) or sprites._cache.get("final_Walk")
        if frames:
            base = frames[self._anim_frame % len(frames)]
            sw, sh = base.get_size()
            surf = pygame.Surface((sw, sh + 10), pygame.SRCALPHA)
            surf.blit(base, (0, 10))
            bar_w = max(cs - 4, sw - 4)
            hp_r = max(0.0, self.hp / self.max_hp)
            bx = (sw - bar_w) // 2
            col_c = ((50, 210, 70) if hp_r > 0.5
                     else (220, 180, 40) if hp_r > 0.25
                     else (220, 50, 50))
            pygame.draw.rect(surf, (60, 10, 10), (bx, 2, bar_w, 3))
            pygame.draw.rect(surf, col_c, (bx, 2, int(bar_w * hp_r), 3))

            draw_x = px + (cs - sw) // 2
            draw_y = py + cs - sh - 10
            result = {
                'surf': surf,
                'pos': (draw_x, draw_y),
                'sort_y': py + cs,
                'type': 'boss'
            }

            if self.effect_timer > 0:
                effect_frames = sprites._cache.get("flyingdemon_attack_effect")
                if effect_frames:
                    effect_progress = 1.0 - (self.effect_timer / self.effect_duration)
                    effect_frame_idx = min(int(effect_progress * len(effect_frames)), len(effect_frames) - 1)
                    effect_surf = effect_frames[effect_frame_idx]
                    result['attack_effect'] = {
                        'surf': effect_surf,
                        'pos': (draw_x + (sw - effect_surf.get_width()) // 2,
                                draw_y + (sh - effect_surf.get_height()) // 2),
                        'alpha': 255
                    }
            return result
        fallback = pygame.Surface((cs, cs + 10), pygame.SRCALPHA)
        pygame.draw.circle(fallback, (150, 0, 50), (cs // 2, cs // 2 + 10), cs // 3)
        return {'surf': fallback, 'pos': (px, py - 10), 'sort_y': py + cs, 'type': 'boss'}

"""Server — mục tiêu chính của game."""

import pygame
import settings
import ui.sprites as sprites


class Server:
    """Mục tiêu chính mà Malware cố gắng đến và tấn công.

    Server nằm tại vị trí cố định trong lưới (server_pos), có máu riêng.
    Mỗi Malware tới server trừ 1 HP. Khi HP về 0 → GAME OVER.

    Attributes:
        pos (tuple[int,int]): Tọa độ ô lưới (row, col) trên map.
        hp (int): Máu server hiện tại.
        max_hp (int): Máu tối đa (từ settings.SERVER_MAX_HP).
        _anim_frame (int): Frame animation hiện tại (0-3).
        _anim_timer (float): Đếm thời gian (giây) đến frame kế tiếp.

    Usage::

        server = Server(pos=(12, 12))
        server.take_damage(1)
        if server.is_destroyed():
            print("Game Over!")
        render_data = server.get_render_data(cell_size=48)
    """

    def __init__(self, pos: tuple[int, int]):
        """Khởi tạo Server tại vị trí pos.

        Args:
            pos (tuple[int,int]): Tọa độ ô lưới (row, col).

        Side effects:
            - Đặt self.hp = settings.SERVER_MAX_HP.
            - Đặt self._anim_frame = 0, self._anim_timer = 0.0.
            - Đặt self.poison_timer = 0.0, self.poison_end_time = 0.0.
        """
        self.pos = pos
        self.hp = settings.SERVER_MAX_HP
        self.max_hp = settings.SERVER_MAX_HP
        self._anim_frame = 0
        self._anim_timer = 0.0
        self.poison_timer = 0.0
        self.poison_end_time = 0.0

    def take_damage(self, amount: int):
        """Trừ máu server khi Malware tấn công.

        Args:
            amount (int): Lượng sát thương cần trừ (≥ 0).

        Side effects:
            - Giảm self.hp (không đặt lower bound, có thể âm).
        """
        self.hp -= amount

    def is_destroyed(self) -> bool:
        """Kiểm tra server đã bị phá hủy (HP ≤ 0) chưa.

        Returns:
            bool: True nếu self.hp ≤ 0, False nếu còn sống.
        """
        return self.hp <= 0

    def get_poison(self, poison_duration: float):
        """Áp dụng độc lên server (cộng dồn).

        Args:
            poison_duration (float): Thời gian độc tác động thêm (giây).

        Side effects:
            - Cộng thêm poison_duration vào self.poison_end_time.
            - Poison sẽ gây sát thương mỗi 1.5 giây cho đến khi hết thời gian.
        """
        self.poison_end_time += poison_duration

    def update(self, dt: float):
        """Cập nhật animation server và xử lý độc mỗi frame.

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Tích lũy dt vào self._anim_timer, chuyển frame kế tiếp khi đủ khoảng cách.
            - Xử lý độc: tích lũy thời gian, gây sát thương mỗi 1.5 giây.
        """
        # Animation
        self._anim_timer += dt
        if self._anim_timer >= 1.0 / settings.SERVER_ANIM_FPS:
            self._anim_timer = 0.0
            self._anim_frame = (self._anim_frame + 1) % 4

        # Poison damage (mỗi 1.5 giây trừ 1 máu)
        if self.poison_end_time > 0:
            self.poison_timer += dt
            if self.poison_timer >= 1.5:
                self.poison_timer -= 1.5
                self.poison_end_time -= 1.5
                self.take_damage(5)
                if self.is_destroyed():
                    self.poison_end_time = 0
                    self.hp=1  # Đặt lại HP để tránh âm quá sâu, độc không thể kết liễu server
                if self.poison_end_time <= 0:
                    self.poison_end_time = 0

    def get_render_data(self, cell_size: int) -> dict:
        """Tạo render data cho Server (sprite animation) cho Y-Sort.

        Args:
            cell_size (int): Kích thước ô lưới (pixel) — thường 48.

        Returns:
            dict: {
                'surf': pygame.Surface,  # sprite hiện tại.
                'pos': (pixel_x, pixel_y),  # vị trí để blit (bottom-center aligned).
                'sort_y': float,  # tọa độ Y để Y-Sort.
            }

        Note:
            Server lấy sprite từ cache key "server" (4 frame animation).
            Nếu không có sprite, fallback vẽ hình tròn xanh.
            HP hiển thị riêng trong HUD, không vẽ trên sprite.
        """
        row, col = self.pos

        # Lấy sprite server từ cache
        server_frames = sprites.get("server")
        if server_frames:
            srv_surf = server_frames[self._anim_frame % len(server_frames)]
            sw, sh = srv_surf.get_size()
        else:
            # Fallback: vẽ hình tròn xanh
            srv_surf = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)
            pygame.draw.circle(
                srv_surf,
                settings.COLOR_SERVER,
                (cell_size // 2, cell_size // 2),
                cell_size // 3,
            )
            sw, sh = cell_size, cell_size

        # Bottom-center aligned positioning
        pixel_x = col * cell_size + (cell_size - sw) // 2
        pixel_y = row * cell_size + cell_size - sh

        return {
            "surf": srv_surf,
            "pos": (pixel_x, pixel_y),
            "sort_y": (row + 1) * cell_size - 1,
        }

    def draw(self, screen: pygame.Surface, cell_size: int):
        """Vẽ server lên màn hình (fallback nếu không dùng Y-Sort).

        Args:
            screen (pygame.Surface): Surface cửa sổ game.
            cell_size (int): Kích thước ô lưới (pixel).

        Side effects:
            - Vẽ sprite server và HP bar lên screen.

        Note:
            Phương thức này là fallback — bình thường game.py dùng get_render_data()
            để đảm bảo Y-Sort đúng.
        """
        render_data = self.get_render_data(cell_size)
        screen.blit(render_data["surf"], render_data["pos"])

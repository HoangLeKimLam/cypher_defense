# entities/fire_mark.py
# Vết lửa từ FireNode - tồn tại 1 ô, quái bước vào nhận damage/giây

import settings


class FireMark:
    """Vết lửa trên 1 ô lưới - quái đi qua ô này sẽ nhận damage/giây.

    Attributes:
        pos (tuple): Vị trí ô lưới (row, col)
        damage_per_sec (int): Sát thương mỗi giây
        duration (float): Thời gian tồn tại (giây)
        elapsed_time (float): Thời gian đã trôi qua
        is_active (bool): Vết lửa còn hoạt động hay không
        animation_frame (int): Frame hiện tại (0-17 từ spritesheet)
    """

    def __init__(self, pos: tuple, damage_per_sec: int, duration: float):
        """Khởi tạo FireMark tại vị trí quái trúng đạn.

        Args:
            pos (tuple): (row, col) vị trí ô lưới
            damage_per_sec (int): Sát thương/giây từ lửa
            duration (float): Thời gian vết lửa tồn tại
        """
        self.pos = pos
        self.damage_per_sec = damage_per_sec
        self.duration = duration
        self.elapsed_time = 0.0
        self.is_active = True
        self.animation_frame = 0  # Bắt đầu từ frame 7 (appearing)

    def update(self, dt: float):
        """Cập nhật timer và animation frame của vết lửa.

        Args:
            dt (float): Thời gian frame (giây)
        """
        self.elapsed_time += dt

        # Tính toán frame animation:
        # Frame 7-11: xuất hiện (5 frames)
        # Frame 12-17: biến mất (6 frames)
        # Tổng: 11 frames (0.5 + 0.75 giây @ 8 fps)

        progress = self.elapsed_time / self.duration  # 0.0 → 1.0

        if progress < 0.45:  # 45% thời gian: xuất hiện (frame 7-11)
            frame_in_phase = int(progress / 0.45 * 5)  # 0-4
            self.animation_frame = 7 + frame_in_phase
        else:  # 55% thời gian: biến mất (frame 12-17)
            frame_in_phase = int((progress - 0.45) / 0.55 * 6)  # 0-5
            self.animation_frame = 12 + frame_in_phase

        if self.elapsed_time >= self.duration:
            self.is_active = False

    def is_alive(self) -> bool:
        """Kiểm tra vết lửa còn hoạt động hay không.

        Returns:
            bool: True nếu vết lửa chưa hết thời gian tồn tại.
        """
        return self.is_active

    def affects_enemy(self, malware) -> bool:
        """Kiểm tra quái có đứng trên ô lửa không.

        Args:
            malware (Malware): Đối tượng Malware cần kiểm tra

        Returns:
            bool: True nếu quái đứng tại vị trí vết lửa
        """
        return malware.pos == self.pos

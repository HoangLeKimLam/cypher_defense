# entities/shock_effect.py
# Hiệu ứng shock từ LightSpy - xuất hiện trên tháp bị tấn công

import settings


class ShockEffect:
    """Hiệu ứng shock từ LightSpy - tháp bị lan truyền nhận hiệu ứng tương tác.

    Attributes:
        pos (tuple): Vị trí ô lưới của tháp bị tấn công
        duration (float): Thời gian hiệu ứng tồn tại (giây)
        elapsed_time (float): Thời gian đã trôi qua
        is_active (bool): Hiệu ứng còn hoạt động hay không
        animation_frame (int): Frame hiện tại (8-14, ping-pong animation)
    """

    def __init__(self, pos: tuple, duration: float = 0.5):
        """Khởi tạo ShockEffect tại vị trí tháp bị LightSpy tấn công.

        Args:
            pos (tuple): (row, col) vị trí ô lưới
            duration (float): Thời gian hiệu ứng tồn tại (mặc định 0.5 giây)
        """
        self.pos = pos
        self.duration = duration
        self.elapsed_time = 0.0
        self.is_active = True
        self.animation_frame = 8  # Bắt đầu từ frame 8
        self._frame_sequence = list(range(8, 15)) + list(range(13, 7, -1))  # 8-14 rồi 14-8

    def update(self, dt: float):
        """Cập nhật animation frame của hiệu ứng shock.

        Args:
            dt (float): Thời gian frame (giây)

        Side effects:
            - Cập nhật animation_frame theo frame_sequence
            - Đặt is_active = False khi hết duration
        """
        self.elapsed_time += dt

        # Tính frame dựa trên thời gian
        progress = self.elapsed_time / self.duration  # 0.0 → 1.0
        if progress < 1.0:
            frame_idx = int(progress * len(self._frame_sequence)) % len(self._frame_sequence)
            self.animation_frame = self._frame_sequence[frame_idx]
        else:
            self.is_active = False

        if self.elapsed_time >= self.duration:
            self.is_active = False

    def is_alive(self) -> bool:
        """Kiểm tra hiệu ứng còn hoạt động hay không.

        Returns:
            bool: True nếu hiệu ứng chưa hết thời gian tồn tại.
        """
        return self.is_active

import settings


class Wall:
    """Tường được đặt bởi người chơi, tồn tại 30s sau đó biến mất.

    Khi đặt: cell thay đổi WALL → lưu lại cell cũ.
    Khi mất: cell trở lại giá trị cũ (thường là PATH), enemy tính lại đường đi.
    """
    def __init__(self, pos: tuple[int, int], original_cell: int):
        """Khởi tạo Wall tại vị trí pos.

        Args:
            pos: (row, col) vị trí đặt tường trên lưới.
            original_cell: Giá trị cell ban đầu (thường Celltype.PATH).
        """
        self.pos = pos
        self.original_cell = original_cell
        self.duration = settings.WALL_DURATION
        self.wall_dead = False

    def update(self, dt: float) -> None:
        """Cập nhật timer tồn tại tường mỗi frame.

        Args:
            dt: Thời gian frame (giây).
        """
        if not self.wall_dead:
            self.duration -= dt
            if self.duration <= 0:
                self.wall_dead = True
                self.duration = 0

    def is_dead(self) -> bool:
        """Trả về True nếu tường đã hết thời gian tồn tại.

        Returns:
            bool: True nếu wall_dead = True (duration <= 0).
        """
        return self.wall_dead

import settings


class Bomb:
    """Bom rơi ngẫu nhiên trên ô PATH trong wave — phát nổ sau timer_explode giây.

    Tower có thể bắn hạ bomb trước khi nổ. Khi nổ: stun toàn bộ tower và
    trừ HP server. Nếu bị tiêu diệt bởi tower: vẫn trigger animation nổ
    nhưng KHÔNG gây stun/damage.

    Attributes:
        pos (tuple[int,int]): Vị trí (row, col) trên lưới PATH.
        hp (int): Máu bomb — về 0 khi bị tower bắn.
        timer_explode (float): Đếm ngược (giây) đến khi tự nổ.
        bomb_damage_to_server (int): Sát thương gây ra cho Server khi nổ.
        bomb_stun_duration (float): Thời gian stun tất cả tower (giây).
        exploded (bool): True khi bomb đã phát nổ (tự hết giờ hoặc bị tiêu diệt).
        bomb_dead (bool): True khi bomb đã bị xóa khỏi game.
        anim_timer (float): Thời gian đã trôi qua trong animation hiện tại.
        warning_timer (float): Timer hiệu ứng cảnh báo (~1 giây).

    Usage::

        bomb = Bomb(pos=(5, 10))
        bomb.update(dt)
        if bomb.is_exploded() and bomb.anim_timer >= 1.4:
            data = bomb.get_explosion_data()
    """
    def __init__(self, pos: tuple[int, int]):
        """Khởi tạo Bomb tại vị trí pos với các thông số từ settings.

        Args:
            pos (tuple[int,int]): Vị trí (row, col) ô PATH trên lưới.
        """
        self.pos = pos
        self.hp = settings.BOMB_HP
        self.timer_explode = settings.BOMB_TIMER
        self.bomb_damage_to_server = settings.BOMB_DAMAGE_TO_SERVER
        self.bomb_stun_duration = settings.BOMB_STUN_DURATION
        self.exploded = False
        self.bomb_dead = False
        self.anim_timer = 0.0  # Thời gian animation hiện tại
        self.anim_fps = 8  # Frame per second cho animation
        self.warning_timer = 1.0  # Hiệu ứng cảnh báo khoảng 1 giây
    def update(self, dt: float):
        """Cập nhật trạng thái của Bomb mỗi frame.

        Args:
            dt (float): Thời gian frame tính bằng giây.

        Side effects:
            - Giảm self.timer_explode theo dt.
            - Khi self.timer_explode ≤ 0, đặt self.exploded = True để đánh dấu đã phát nổ.
            - Cập nhật animation timer.
            - Giảm warning_timer.
        """
        # Giảm warning timer (cảnh báo trong ~1 giây đầu)
        if self.warning_timer > 0:
            self.warning_timer -= dt

        if not self.exploded and not self.bomb_dead:
            self.timer_explode -= dt
            if self.timer_explode <= 0:
                self.exploded = True
                self.timer_explode = 0
                self.anim_timer = 0.0  # Reset animation timer when explosion starts
            else:
                # Cập nhật animation timer cho idle animation
                self.anim_timer += dt
        elif self.exploded and not self.bomb_dead:
            # Cập nhật animation timer cho explosion animation
            self.anim_timer += dt    
    def is_dead(self) -> bool:
        """Kiểm tra bomb đã bị xóa khỏi game (bị tower tiêu diệt hoặc animation nổ xong).

        Returns:
            bool: True nếu self.bomb_dead == True.

        Note:
            Sau khi bom nổ (is_exploded() == True), game.py chỉ xóa nó khỏi danh sách
            sau khi animation chạy xong (anim_timer >= 1.4), lúc đó gọi hàm này
            để kiểm tra trước khi remove.
        """
        return self.bomb_dead

    def is_exploded(self) -> bool:
        """Kiểm tra bomb đã phát nổ chưa (hết timer hoặc bị tower tiêu diệt).

        Returns:
            bool: True nếu self.exploded == True.

        Note:
            Không đồng nghĩa với is_dead() — bomb vẫn cần phát xong animation nổ
            trước khi is_dead() trả True. Giữa is_exploded()==True và is_dead()==True
            khoảng 1.4 giây animation.
        """
        return self.exploded
    def take_damage(self, amount: int):
        """Trừ HP của Bomb khi bị tấn công.

        Args:
            amount (int): Lượng sát thương cần trừ (≥ 0).

        Side effects:
            - Giảm self.hp (không đặt lower bound, có thể âm).
            - Nếu HP <= 0, đặt bomb_dead = True và trigger explosion.
        """
        if not self.bomb_dead:
            self.hp -= amount
            if self.hp <= 0:
                self.bomb_dead = True
                # Trigger explosion khi bomb bị hủy bởi tower
                if not self.exploded:
                    self.exploded = True
                    self.anim_timer = 0.0

    def get_explosion_data(self) -> dict:
        """Trả về dữ liệu khi bomb nổ: sát thương server + stun towers.

        Returns:
            dict với keys: "server_damage", "stun_duration"
        """
        return {
            "server_damage": self.bomb_damage_to_server,
            "stun_duration": self.bomb_stun_duration
        }

    def get_render_data(self, cell_size: int):
        """Trả về dữ liệu vẽ bomb cho Y-sorting trong game.py.

        Args:
            cell_size (int): Kích thước ô lưới (pixel).

        Returns:
            dict với keys: 'surf', 'pos', 'sort_y', 'type', 'warning' cho Y-sorting layer.
        """
        import ui.sprites as sprites

        # Chọn sprite dựa trên trạng thái
        if self.exploded:
            sprite_key = "bomb_explode"
            frame_count = 11  # 11 frames cho explode
        else:
            sprite_key = "bomb_idle"
            frame_count = 3   # 3 frames cho idle

        frames = sprites.get(sprite_key)
        if not frames:
            return None

        # Tính frame hiện tại dựa trên animation timer
        frame_idx = int(self.anim_timer * self.anim_fps)

        if self.exploded:
            # Explosion: play once, hold last frame
            frame_idx = min(frame_idx, frame_count - 1)
        else:
            # Idle: loop
            frame_idx = frame_idx % frame_count

        surf = frames[frame_idx] if isinstance(frames, list) else frames

        # Vị trí vẽ: center-aligned trong cell
        x = self.pos[1] * cell_size + cell_size // 2
        y = self.pos[0] * cell_size + cell_size // 2
        w, h = surf.get_size()

        # Tính alpha cho pulsing warning effect (0-255)
        warning_alpha = 0
        if self.warning_timer > 0:
            # Pulsing effect: 4 lần blink trong 1 giây, red brighter
            pulse = (1.0 - self.warning_timer) * 4.0  # 0 đến 4
            pulse_frac = pulse % 1.0  # 0 đến 1
            warning_alpha = int(255 * pulse_frac)  # 0 đến 255 (brighter)

        # Countdown display (chỉ show khi timer > 0)
        countdown_text = None
        if not self.exploded and self.timer_explode > 0:
            countdown_text = f"{int(self.timer_explode) + 1}"  # Round up for display

        return {
            'surf': surf,
            'pos': (int(x) - w // 2, int(y) - h // 2),
            'sort_y': 999999,  # Bomb luôn ưu tiên từ lúc spawn
            'type': 'bomb',
            'countdown': countdown_text,  # Thêm countdown
            'warning': {
                'pos': (int(x), int(y)),
                'radius': cell_size,
                'alpha': warning_alpha
            } if self.warning_timer > 0 else None
        }


class BossBomb(Bomb):
    """Bom của Boss — có damage tùy chỉnh và loại bomb (normal hoặc atomic).

    Dùng cho FlyingDemon: bomb bình thường (-300 HP) hoặc atomic bomb (-10000 HP).
    Thời gian nổ được random từ min_explode đến max_explode.

    Attributes:
        bomb_type (str): "normal" hoặc "atomic" — ảnh hưởng damage
        is_atomic (bool): True nếu là atomic bomb (gây -10000 HP)
    """

    def __init__(self, pos: tuple[int, int], bomb_type: str = "normal",
                 damage: int = 300, stun_duration: float = 5.0,
                 explode_time: float = 5.0):
        """Khởi tạo BossBomb.

        Args:
            pos (tuple[int,int]): Vị trí (row, col)
            bomb_type (str): "normal" hoặc "atomic"
            damage (int): Sát thương gây cho server
            stun_duration (float): Thời gian stun tháp
            explode_time (float): Thời gian nổ (giây)
        """
        super().__init__(pos)
        self.bomb_type = bomb_type
        self.is_atomic = (bomb_type == "atomic")
        self.bomb_damage_to_server = damage
        self.bomb_stun_duration = stun_duration
        self.timer_explode = explode_time
        self.hp = settings.BOMB_HP  # Vẫn có thể bị tower tiêu diệt
        
        
# main.py
# GameManager — quản lí trạng thái game, level progression, save/load

import pygame
import json
import os
from game import Game
import settings
from systems.audio import audio_manager
from ui.right_panel import TOWER_META


class GameManager:
    """Quản lí trạng thái game: menu, level progression, save/load.

    GameManager nhận input từ người chơi (click, key) và quản lí state transitions.
    Game instance xử lí việc render và game logic cho mỗi level.

    Attributes:
        state (str): Trạng thái ("START", "PLAYING", "LEVEL_COMPLETE", "GAME_OVER", "VICTORY")
        current_level (int): Level hiện tại (1-indexed)
        completed_levels (set): Tập hợp các level đã hoàn thành
        game (Game | None): Instance Game hiện tại (None khi ở menu)
        save_file (str): Đường dẫn file lưu tiến độ
    """

    def __init__(self):
        """Khởi tạo GameManager và tải tiến độ đã lưu."""
        pygame.init()
        self.screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        pygame.display.set_caption("Cypher Defense")
        self.clock = pygame.time.Clock()
        self.font_title = pygame.font.SysFont("arial", 56, bold=True)
        self.font_normal = pygame.font.SysFont("arial", 28, bold=True)
        self.font_small = pygame.font.SysFont("arial", 20)

        # Load menu background
        self.menu_bg = self._load_menu_background()

        # State machine
        self.state = "START"  # "START", "PLAYING", "LEVEL_COMPLETE", "GAME_OVER", "VICTORY"
        self.current_level = 1
        self.completed_levels = set()
        self.game = None
        self.save_file = "progress.json"
        self.menu_cooldown = 0.0  # Prevent rapid clicks
        self.codex_selected = "BasicNode"

        # Leaderboard — sorted ascending by score; display reversed
        self.leaderboard: list = []
        self.session_number = 0
        self.session_entry: dict | None = None  # current run's live entry

        # Notification banner (menu messages)
        self._notif_msg = ""
        self._notif_timer = 0.0

        # Load saved progress
        self._load_progress()

        self.running = True

    def _load_menu_background(self):
        """Tải background ảnh cho menu từ data/sprites/Menu."""
        try:
            bg_path = "data/sprites/Menu/ChatGPT Image 00_02_37 8 thg 5, 2026.png"
            if os.path.exists(bg_path):
                bg = pygame.image.load(bg_path)
                # Scale to screen size
                bg = pygame.transform.scale(bg, (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
                return bg
        except Exception as e:
            print(f"Failed to load menu background: {e}")
        return None

    def _load_progress(self):
        """Tải tiến độ từ file lưu (nếu tồn tại)."""
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, 'r') as f:
                    data = json.load(f)
                    self.completed_levels = set(data.get("completed_levels", []))
                    self.current_level    = data.get("current_level", 1)
                    self.leaderboard      = data.get("leaderboard", [])
                    self.session_number   = data.get("session_number", 0)
            except:
                pass

    def _save_progress(self):
        """Lưu tiến độ vào file."""
        data = {
            "completed_levels": list(self.completed_levels),
            "current_level":    self.current_level,
            "leaderboard":      self.leaderboard,
            "session_number":   self.session_number,
        }
        with open(self.save_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _ub_insert(self, entry: dict):
        """Upper-bound insert vào self.leaderboard (tăng dần theo score)."""
        lo, hi = 0, len(self.leaderboard)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.leaderboard[mid]["score"] <= entry["score"]:
                lo = mid + 1
            else:
                hi = mid
        self.leaderboard.insert(lo, entry)

    def _get_max_levels(self):
        """Đếm số level có sẵn từ data/levels/."""
        levels = 0
        for i in range(1, 100):
            if os.path.exists(f"data/levels/level{i}.json"):
                levels = i
            else:
                break
        return levels

    def handle_events(self):
        """Xử lí sự kiện: GameManager xử lý ESC/QUIT, Game xử lý những events khác."""
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.state == "PLAYING":
                    # ESC khi chơi → quay lại menu
                    self.state = "START"
                    self.game = None
                else:
                    # ESC ở menu → thoát game
                    self.running = False

        # Pass all events to Game when in PLAYING state
        if self.state == "PLAYING" and self.game:
            self.game.handle_events(events)

    def update(self, dt: float):
        """Cập nhật trạng thái game."""
        self.menu_cooldown -= dt
        if self.menu_cooldown < 0:
            self.menu_cooldown = 0
        if self._notif_timer > 0:
            self._notif_timer -= dt

        if self.state == "START":
            self._handle_start_menu()
        elif self.state == "PLAYING":
            self.game.update(dt)
            # Kiểm tra kết quả
            if self.game.game_over:
                self.state = "GAME_OVER"
            elif self.game.victory:
                self.completed_levels.add(self.current_level)
                # Cộng HP server còn lại vào điểm của run hiện tại
                if self.session_entry is not None:
                    hp = int(getattr(getattr(self.game, 'server', None), 'hp', 0))
                    self.leaderboard.remove(self.session_entry)
                    self.session_entry["score"] += hp
                    self.session_entry["levels"] += 1
                    self._ub_insert(self.session_entry)
                self._save_progress()
                self.state = "LEVEL_COMPLETE"
        elif self.state == "LEVEL_COMPLETE":
            self._handle_level_complete()
        elif self.state == "GAME_OVER":
            self._handle_game_over()
        elif self.state == "VICTORY":
            self._handle_victory()
        elif self.state == "CONFIRM_NEW_GAME":
            self._handle_confirm_new_game()
        elif self.state == "TOWER_INFO":
            self._handle_tower_info()
        elif self.state == "LEADERBOARD":
            self._handle_leaderboard()

    def draw(self):
        """Vẽ màn hình dựa trên state."""
        if self.state == "PLAYING":
            # Game.draw() handles all rendering
            self.game.draw()
        else:
            # GameManager draws menus
            # Draw background
            if self.menu_bg:
                self.screen.blit(self.menu_bg, (0, 0))
            else:
                self.screen.fill(settings.COLOR_BG)

            if self.state == "START":
                self._draw_start_menu()
            elif self.state == "LEVEL_COMPLETE":
                self._draw_level_complete()
            elif self.state == "GAME_OVER":
                self._draw_game_over()
            elif self.state == "VICTORY":
                self._draw_victory()
            elif self.state == "CONFIRM_NEW_GAME":
                self._draw_start_menu()
                self._draw_confirm_new_game()
            elif self.state == "TOWER_INFO":
                self._draw_tower_info()
            elif self.state == "LEADERBOARD":
                self._draw_leaderboard()
            pygame.display.flip()

    def _handle_start_menu(self):
        """Xử lí input menu chính."""
        if self.menu_cooldown > 0:
            return

        if pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            button_width = 300
            button_height = 60
            button_y = 350  # FIXED: Match _draw_start_menu()

                # New Game button
            new_game_rect = pygame.Rect(settings.SCREEN_WIDTH // 2 - button_width // 2, button_y, button_width, button_height)
            if new_game_rect.collidepoint(mx, my):
                self.state = "CONFIRM_NEW_GAME"
                self.menu_cooldown = 0.3

            # Continue button — always increment button_y to match _draw_start_menu
            button_y += button_height + 20
            continue_rect = pygame.Rect(settings.SCREEN_WIDTH // 2 - button_width // 2, button_y, button_width, button_height)
            if continue_rect.collidepoint(mx, my):
                if len(self.completed_levels) < 2:
                    self._notif_msg = "No save data available!"
                    self._notif_timer = 2.0
                    self.menu_cooldown = 0.3
                else:
                    self.current_level = max(self.completed_levels) + 1
                    if self.current_level > self._get_max_levels():
                        self.state = "VICTORY"
                    else:
                        self._start_level()
                    self.menu_cooldown = 0.2

            # Codex button
            button_y += button_height + 20
            codex_rect = pygame.Rect(settings.SCREEN_WIDTH // 2 - button_width // 2, button_y, button_width, button_height)
            if codex_rect.collidepoint(mx, my):
                self.state = "TOWER_INFO"
                self.menu_cooldown = 0.2

            # Leaderboard button
            button_y += button_height + 20
            lb_rect = pygame.Rect(settings.SCREEN_WIDTH // 2 - button_width // 2, button_y, button_width, button_height)
            if lb_rect.collidepoint(mx, my):
                self.state = "LEADERBOARD"
                self.menu_cooldown = 0.2

            # Quit button
            button_y += button_height + 20
            quit_rect = pygame.Rect(settings.SCREEN_WIDTH // 2 - button_width // 2, button_y, button_width, button_height)
            if quit_rect.collidepoint(mx, my):
                self.running = False
                self.menu_cooldown = 0.2

    def _handle_level_complete(self):
        """Xử lí input level hoàn thành khớp với UI mới."""
        if self.menu_cooldown > 0:
            return

        if pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
            bw, bh = 200, 50
            py = (H - 350) // 2
            
            # Next button (Proceed)
            next_rect = pygame.Rect(W // 2 - bw - 20, py + 220, bw, bh)
            if next_rect.collidepoint(mx, my):
                max_levels = self._get_max_levels()
                if self.current_level >= max_levels:
                    self.state = "VICTORY"
                else:
                    self.current_level += 1
                    self._start_level()
                self.menu_cooldown = 0.2

            # Menu button (Exit to Hub)
            menu_rect = pygame.Rect(W // 2 + 20, py + 220, bw, bh)
            if menu_rect.collidepoint(mx, my):
                self.state = "START"
                self.game = None
                self.menu_cooldown = 0.2

    def _handle_game_over(self):
        """Xử lí input game over khớp với UI mới."""
        if self.menu_cooldown > 0:
            return

        if pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
            bw, bh = 200, 50
            py = (H - 350) // 2
            
            # Retry button (Reboot)
            retry_rect = pygame.Rect(W // 2 - bw - 20, py + 220, bw, bh)
            if retry_rect.collidepoint(mx, my):
                self._start_level()
                self.menu_cooldown = 0.2

            # Menu button (Hub)
            menu_rect = pygame.Rect(W // 2 + 20, py + 220, bw, bh)
            if menu_rect.collidepoint(mx, my):
                self.state = "START"
                self.game = None
                self.menu_cooldown = 0.2

    def _handle_victory(self):
        """Xử lí input victory khớp với UI mới."""
        if self.menu_cooldown > 0:
            return

        if pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
            bw, bh = 300, 60
            py = (H - 400) // 2
            
            menu_rect = pygame.Rect(W // 2 - bw // 2, py + 280, bw, bh)
            if menu_rect.collidepoint(mx, my):
                self.state = "START"
                self.game = None
                self.menu_cooldown = 0.2

    def _handle_confirm_new_game(self):
        """Xử lí input hộp xác nhận New Game."""
        if self.menu_cooldown > 0:
            return
        if pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
            bw, bh = 160, 50
            box_w, box_h = 460, 200
            bx = (W - box_w) // 2
            by = (H - box_h) // 2
            yes_rect  = pygame.Rect(bx + 40,           by + 120, bw, bh)
            no_rect   = pygame.Rect(bx + box_w - 40 - bw, by + 120, bw, bh)
            if yes_rect.collidepoint(mx, my):
                self.current_level = 1
                self.completed_levels = {0}
                # Create a new leaderboard entry for this run
                self.session_number += 1
                self.session_entry = {"run": self.session_number, "score": 0, "levels": 0}
                self._ub_insert(self.session_entry)
                self._save_progress()
                self._start_level()
                self.menu_cooldown = 0.3
            elif no_rect.collidepoint(mx, my):
                self.state = "START"
                self.menu_cooldown = 0.2

    def _draw_confirm_new_game(self):
        """Vẽ hộp xác nhận trước khi reset New Game."""
        W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        box_w, box_h = 460, 200
        bx = (W - box_w) // 2
        by = (H - box_h) // 2

        # Dim overlay
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        # Panel
        pygame.draw.rect(self.screen, (12, 16, 28), (bx, by, box_w, box_h))
        pygame.draw.rect(self.screen, (0, 200, 80), (bx, by, box_w, box_h), 2)

        # Title
        title = self.font_normal.render("START NEW GAME?", True, (0, 230, 100))
        self.screen.blit(title, (bx + box_w // 2 - title.get_width() // 2, by + 28))

        # Warning
        warn = self.font_small.render("All current progress will be erased.", True, (210, 160, 60))
        self.screen.blit(warn, (bx + box_w // 2 - warn.get_width() // 2, by + 72))

        # Buttons
        bw, bh = 160, 50
        yes_rect = pygame.Rect(bx + 40,                by + 120, bw, bh)
        no_rect  = pygame.Rect(bx + box_w - 40 - bw,  by + 120, bw, bh)

        pygame.draw.rect(self.screen, (20, 50, 30), yes_rect)
        pygame.draw.rect(self.screen, (0, 210, 90), yes_rect, 2)
        yt = self.font_normal.render("CONFIRM", True, (255, 255, 255))
        self.screen.blit(yt, (yes_rect.centerx - yt.get_width() // 2, yes_rect.centery - yt.get_height() // 2))

        pygame.draw.rect(self.screen, (40, 20, 20), no_rect)
        pygame.draw.rect(self.screen, (220, 60, 60), no_rect, 2)
        nt = self.font_normal.render("CANCEL", True, (255, 255, 255))
        self.screen.blit(nt, (no_rect.centerx - nt.get_width() // 2, no_rect.centery - nt.get_height() // 2))

    def _start_level(self):
        """Bắt đầu level hiện tại."""
        try:
            self.game = Game(level=self.current_level, screen=self.screen, managed=True)
            self.state = "PLAYING"
            audio_manager.play_music("music_game")
        except Exception as e:
            print(f"Error loading level {self.current_level}: {e}")
            self.state = "START"

    def _draw_start_menu(self):
        """Vẽ menu chính chuyên nghiệp (kết hợp với ảnh nền)."""
        W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        
        # 1. Overlay để làm tối ảnh nền và thêm Scanlines
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 10, 20, 100)) # Làm tối ảnh nền một chút
        for y in range(0, H, 4):
            pygame.draw.line(overlay, (0, 0, 0, 60), (0, y), (W, y))
        self.screen.blit(overlay, (0, 0))

       

        # 3. Buttons
        button_y = 350
        button_height = 60
        button_width = 300

        # Helper for styled buttons
        def draw_neon_button(rect, text, base_color, text_color=(255, 255, 255)):
            pygame.draw.rect(self.screen, (15, 20, 30), rect)
            pygame.draw.rect(self.screen, base_color, rect, 2)
            # Corner accents
            cl = 10
            for x, y, dx, dy in [(rect.left, rect.top, 1, 1), (rect.right, rect.top, -1, 1), 
                                 (rect.left, rect.bottom, 1, -1), (rect.right, rect.bottom, -1, -1)]:
                pygame.draw.line(self.screen, base_color, (x, y), (x + dx*cl, y), 3)
                pygame.draw.line(self.screen, base_color, (x, y), (x, y + dy*cl), 3)
            
            txt_surf = self.font_normal.render(text, True, text_color)
            self.screen.blit(txt_surf, (rect.centerx - txt_surf.get_width() // 2, rect.centery - txt_surf.get_height() // 2))

        # New Game button
        new_game_rect = pygame.Rect(W // 2 - button_width // 2, button_y, button_width, button_height)
        draw_neon_button(new_game_rect, "INITIALIZE NEW SESSION", (0, 255, 100))

        # Continue button
        button_y += button_height + 20
        continue_rect = pygame.Rect(W // 2 - button_width // 2, button_y, button_width, button_height)
        if len(self.completed_levels) >= 2:

            draw_neon_button(continue_rect, "RESUME OPERATION", (0, 180, 255))
        else:
            # Locked state
            pygame.draw.rect(self.screen, (20, 25, 30), continue_rect)
            pygame.draw.rect(self.screen, (60, 60, 70), continue_rect, 1)
            c_text = self.font_normal.render("NO SAVED DATA", True, (80, 80, 90))
            self.screen.blit(c_text, (continue_rect.centerx - c_text.get_width() // 2, continue_rect.centery - c_text.get_height() // 2))

        # Codex button
        button_y += button_height + 20
        codex_rect = pygame.Rect(W // 2 - button_width // 2, button_y, button_width, button_height)
        draw_neon_button(codex_rect, "TOWER CODEX", (180, 120, 255))

        # Leaderboard button
        button_y += button_height + 20
        lb_rect = pygame.Rect(W // 2 - button_width // 2, button_y, button_width, button_height)
        draw_neon_button(lb_rect, "HIGH SCORES", (255, 200, 60))

        # Quit button
        button_y += button_height + 20
        quit_rect = pygame.Rect(W // 2 - button_width // 2, button_y, button_width, button_height)
        draw_neon_button(quit_rect, "TERMINATE SESSION", (255, 50, 50))

        # Notification banner
        if self._notif_timer > 0 and self._notif_msg:
            notif_surf = self.font_normal.render(self._notif_msg, True, (255, 80, 80))
            nx = W // 2 - notif_surf.get_width() // 2
            ny = quit_rect.bottom + 20
            pygame.draw.rect(self.screen, (30, 10, 10), pygame.Rect(nx - 12, ny - 6, notif_surf.get_width() + 24, notif_surf.get_height() + 12))
            pygame.draw.rect(self.screen, (180, 40, 40), pygame.Rect(nx - 12, ny - 6, notif_surf.get_width() + 24, notif_surf.get_height() + 12), 1)
            self.screen.blit(notif_surf, (nx, ny))

    # ── Tower order for Codex ────────────────────────────────────────────────
    _CODEX_ORDER = [
        "BasicNode", "IceWall", "SpeedNode", "SpreadNode",
        "RadarNode", "FireNode", "PoisonNode", "FreezeNode",
        "SniperNode", "Wall",
    ]

    def _handle_tower_info(self):
        """Xử lí click trong màn hình Tower Codex."""
        if self.menu_cooldown > 0:
            return
        if not pygame.mouse.get_pressed()[0]:
            return
        mx, my = pygame.mouse.get_pos()
        W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT

        # Back button (top-left)
        if pygame.Rect(30, 24, 130, 44).collidepoint(mx, my):
            self.state = "START"
            self.menu_cooldown = 0.2
            return

        # Left list rows
        list_x, list_y = 40, 100
        row_h = 64
        for i, key in enumerate(self._CODEX_ORDER):
            row_rect = pygame.Rect(list_x, list_y + i * row_h, 280, row_h - 4)
            if row_rect.collidepoint(mx, my):
                self.codex_selected = key
                self.menu_cooldown = 0.15
                return

    def _draw_tower_info(self):
        """Vẽ màn hình Tower Codex."""
        from ui.sprites import get as _sget
        W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        screen = self.screen

        # Background
        if self.menu_bg:
            screen.blit(self.menu_bg, (0, 0))
        else:
            screen.fill(settings.COLOR_BG)
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 8, 18, 210))
        screen.blit(ov, (0, 0))

        # Back button
        back_rect = pygame.Rect(30, 24, 130, 44)
        pygame.draw.rect(screen, (20, 28, 44), back_rect)
        pygame.draw.rect(screen, (100, 140, 220), back_rect, 2)
        bt = self.font_small.render("< BACK", True, (180, 200, 255))
        screen.blit(bt, (back_rect.centerx - bt.get_width() // 2,
                         back_rect.centery - bt.get_height() // 2))

        # Title
        title = self.font_title.render("TOWER CODEX", True, (180, 120, 255))
        screen.blit(title, (W // 2 - title.get_width() // 2, 22))

        # ── Left list ─────────────────────────────────────────────────────
        list_x, list_y, row_h = 40, 100, 64
        for i, key in enumerate(self._CODEX_ORDER):
            meta = TOWER_META.get(key, {})
            accent = meta.get("accent", (100, 150, 220))
            is_sel = (key == self.codex_selected)
            ry = list_y + i * row_h
            row_rect = pygame.Rect(list_x, ry, 280, row_h - 4)

            bg_col = (*accent, 50) if is_sel else (14, 18, 30, 200)
            border_col = accent if is_sel else (50, 60, 90)
            s = pygame.Surface((280, row_h - 4), pygame.SRCALPHA)
            s.fill(bg_col)
            screen.blit(s, (list_x, ry))
            pygame.draw.rect(screen, border_col, row_rect, 2 if is_sel else 1)

            # Icon
            raw = _sget(meta.get("sprite")) if meta.get("sprite") else None
            icon = None
            if isinstance(raw, pygame.Surface):
                icon = pygame.transform.smoothscale(raw, (40, 40))
            elif isinstance(raw, list) and raw:
                icon = pygame.transform.smoothscale(raw[0], (40, 40))
            if icon:
                screen.blit(icon, (list_x + 8, ry + (row_h - 4 - 40) // 2))

            # Name + unlock level
            lv = settings.UNLOCK_LEVEL.get(key, 1)
            name_col = accent if is_sel else (200, 210, 230)
            ns = self.font_small.render(meta.get("label", key), True, name_col)
            screen.blit(ns, (list_x + 56, ry + 8))
            lv_col = (255, 200, 60) if lv > 1 else (80, 200, 120)
            lv_txt = f"Unlocks: LV {lv}" if key != "Wall" else "Always available"
            ls = self.font_small.render(lv_txt, True, lv_col)
            screen.blit(ls, (list_x + 56, ry + 30))

        # ── Right detail panel ────────────────────────────────────────────
        meta = TOWER_META.get(self.codex_selected, {})
        accent = meta.get("accent", (100, 150, 220))
        px, py_d, pw, ph = 360, 90, W - 390, H - 110
        pygame.draw.rect(screen, (10, 14, 24), (px, py_d, pw, ph))
        pygame.draw.rect(screen, accent, (px, py_d, pw, ph), 2)

        cx = px + pw // 2
        dy = py_d + 20

        # Sprite
        raw = _sget(meta.get("sprite")) if meta.get("sprite") else None
        img = None
        if isinstance(raw, pygame.Surface):
            img = pygame.transform.smoothscale(raw, (110, 110))
        elif isinstance(raw, list) and raw:
            img = pygame.transform.smoothscale(raw[0], (110, 110))
        if img:
            screen.blit(img, (px + 20, dy))

        # Name + cost + unlock level
        tx = px + 148
        name_s = self.font_title.render(meta.get("label", self.codex_selected), True, accent)
        screen.blit(name_s, (tx, dy))
        dy2 = dy + name_s.get_height() + 6

        lv = settings.UNLOCK_LEVEL.get(self.codex_selected, 1)
        lv_txt = f"Unlocks at: Level {lv}" if self.codex_selected != "Wall" else "Always available"
        lv_s = self.font_normal.render(lv_txt, True, (255, 200, 60) if lv > 1 else (80, 210, 120))
        screen.blit(lv_s, (tx, dy2))
        dy2 += lv_s.get_height() + 4

        cost_s = self.font_normal.render(f"Cost: $ {meta.get('cost', 0)}", True, (210, 185, 55))
        screen.blit(cost_s, (tx, dy2))

        # Description (wrapped)
        desc_y = py_d + 195
        pygame.draw.line(screen, (*accent, 80), (px + 16, desc_y - 12), (px + pw - 16, desc_y - 12))
        self._codex_blit_wrapped(screen, meta.get("desc", ""), (195, 200, 220), px + 16, desc_y, pw - 32)

        # Stats grid
        stats_y = desc_y + 96
        pygame.draw.line(screen, (*accent, 80), (px + 16, stats_y - 10), (px + pw - 16, stats_y - 10))
        stat_hdr = self.font_small.render("STATS", True, accent)
        screen.blit(stat_hdr, (px + 16, stats_y - 8))
        stats_y += 16
        stats = meta.get("stats", [])
        col_w = (pw - 32) // 3
        for i, (label, value) in enumerate(stats):
            col = i % 3
            row = i // 3
            sx = px + 16 + col * col_w
            sy = stats_y + row * 26
            lbl_s = self.font_small.render(label, True, (120, 138, 168))
            val_s = self.font_small.render(str(value), True, (240, 242, 255))
            screen.blit(lbl_s, (sx, sy))
            screen.blit(val_s, (sx + 80, sy))

    def _codex_blit_wrapped(self, surf, text, color, x, y, max_w):
        """Word-wrap text onto surf using font_small."""
        words = text.split()
        line = ""
        for word in words:
            test = line + word + " "
            if self.font_small.size(test)[0] > max_w and line:
                s = self.font_small.render(line.rstrip(), True, color)
                surf.blit(s, (x, y))
                y += s.get_height() + 3
                line = word + " "
            else:
                line = test
        if line.strip():
            surf.blit(self.font_small.render(line.rstrip(), True, color), (x, y))

    def _handle_leaderboard(self):
        """Xử lí click trong màn hình bảng xếp hạng."""
        if self.menu_cooldown > 0:
            return
        if not pygame.mouse.get_pressed()[0]:
            return
        mx, my = pygame.mouse.get_pos()
        W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT

        # Back button
        if pygame.Rect(30, 24, 130, 44).collidepoint(mx, my):
            self.state = "START"
            self.menu_cooldown = 0.2
            return

        # Clear button
        pw, ph = 700, 560
        px = (W - pw) // 2
        py = (H - ph) // 2
        clear_rect = pygame.Rect(px + pw - 180, py + ph - 60, 160, 44)
        if clear_rect.collidepoint(mx, my):
            self.leaderboard.clear()
            self.session_number = 0
            self.session_entry  = None
            self._save_progress()
            self.menu_cooldown = 0.3

    def _draw_leaderboard(self):
        """Vẽ màn hình bảng xếp hạng (hiển thị giảm dần)."""
        W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        screen = self.screen

        if self.menu_bg:
            screen.blit(self.menu_bg, (0, 0))
        else:
            screen.fill(settings.COLOR_BG)
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 8, 18, 215))
        screen.blit(ov, (0, 0))

        # Back button
        back_rect = pygame.Rect(30, 24, 130, 44)
        pygame.draw.rect(screen, (20, 28, 44), back_rect)
        pygame.draw.rect(screen, (100, 140, 220), back_rect, 2)
        bt = self.font_small.render("< BACK", True, (180, 200, 255))
        screen.blit(bt, (back_rect.centerx - bt.get_width() // 2,
                         back_rect.centery - bt.get_height() // 2))

        # Title
        title = self.font_title.render("HIGH SCORES", True, (255, 200, 60))
        screen.blit(title, (W // 2 - title.get_width() // 2, 18))

        # Panel
        pw, ph = 700, 560
        px = (W - pw) // 2
        py = (H - ph) // 2
        pygame.draw.rect(screen, (10, 14, 26), (px, py, pw, ph))
        pygame.draw.rect(screen, (255, 200, 60), (px, py, pw, ph), 2)

        # Header row
        hy = py + 18
        cols = [px + 30, px + 130, px + 350, px + 530]
        for text, cx in zip(["RANK", "RUN #", "SCORE", "LEVELS"], cols):
            s = self.font_small.render(text, True, (255, 200, 60))
            screen.blit(s, (cx, hy))
        pygame.draw.line(screen, (255, 200, 60, 120),
                         (px + 16, hy + 28), (px + pw - 16, hy + 28), 1)

        # Entries — reversed (highest score first)
        entries = list(reversed(self.leaderboard))
        row_h = 36
        max_rows = min(len(entries), 12)
        for i in range(max_rows):
            e   = entries[i]
            ry  = hy + 36 + i * row_h
            # Highlight current session
            is_cur = (self.session_entry is not None and
                      e.get("run") == self.session_entry.get("run"))
            if is_cur:
                hl = pygame.Surface((pw - 4, row_h - 4), pygame.SRCALPHA)
                hl.fill((255, 200, 60, 30))
                screen.blit(hl, (px + 2, ry))
            tc = (255, 230, 120) if is_cur else (210, 216, 232)
            rank_s  = self.font_small.render(f"#{i + 1}", True, tc)
            run_s   = self.font_small.render(f"Run {e.get('run', '?')}", True, tc)
            score_s = self.font_small.render(str(e.get("score", 0)), True, tc)
            lvl_s   = self.font_small.render(str(e.get("levels", 0)), True, tc)
            for s, cx in zip([rank_s, run_s, score_s, lvl_s], cols):
                screen.blit(s, (cx, ry + 4))

        if not self.leaderboard:
            empty = self.font_normal.render("No runs recorded yet.", True, (100, 110, 140))
            screen.blit(empty, (W // 2 - empty.get_width() // 2, py + ph // 2 - 14))

        # Clear button
        clear_rect = pygame.Rect(px + pw - 180, py + ph - 60, 160, 44)
        pygame.draw.rect(screen, (40, 16, 16), clear_rect)
        pygame.draw.rect(screen, (200, 50, 50), clear_rect, 2)
        ct = self.font_small.render("CLEAR ALL", True, (255, 255, 255))
        screen.blit(ct, (clear_rect.centerx - ct.get_width() // 2,
                         clear_rect.centery - ct.get_height() // 2))

    def _draw_level_complete(self):
        """Vẽ màn hình hoàn thành level chuyên nghiệp."""
        W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        
        # Overlay
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 10, 20, 200))
        self.screen.blit(overlay, (0, 0))

        # Panel
        pw, ph = 600, 350
        px, py = (W - pw) // 2, (H - ph) // 2
        
        # Glow border
        color = (0, 255, 150)
        pygame.draw.rect(self.screen, (15, 20, 30), (px, py, pw, ph))
        pygame.draw.rect(self.screen, color, (px, py, pw, ph), 2)
        
        # Title
        txt = f"LEVEL {self.current_level} SECURED"
        t_surf = self.font_title.render(txt, True, color)
        self.screen.blit(t_surf, (W // 2 - t_surf.get_width() // 2, py + 40))

        # Subtitle
        max_levels = self._get_max_levels()
        if self.current_level >= max_levels:
            sub = "ALL THREATS NEUTRALIZED"
            sub_col = (255, 200, 0)
        else:
            sub = f"NEXT OBJECTIVE: LEVEL {self.current_level + 1}"
            sub_col = (0, 180, 255)
        
        s_surf = self.font_normal.render(sub, True, sub_col)
        self.screen.blit(s_surf, (W // 2 - s_surf.get_width() // 2, py + 120))

        # Buttons
        bw, bh = 200, 50
        
        # Next Button
        next_rect = pygame.Rect(W // 2 - bw - 20, py + 220, bw, bh)
        pygame.draw.rect(self.screen, (20, 40, 30), next_rect)
        pygame.draw.rect(self.screen, color, next_rect, 2)
        nt = self.font_normal.render("PROCEED", True, (255, 255, 255))
        self.screen.blit(nt, (next_rect.centerx - nt.get_width() // 2, next_rect.centery - nt.get_height() // 2))

        # Menu Button
        menu_rect = pygame.Rect(W // 2 + 20, py + 220, bw, bh)
        pygame.draw.rect(self.screen, (20, 30, 40), menu_rect)
        pygame.draw.rect(self.screen, (0, 150, 255), menu_rect, 2)
        mt = self.font_normal.render("EXIT TO HUB", True, (255, 255, 255))
        self.screen.blit(mt, (menu_rect.centerx - mt.get_width() // 2, menu_rect.centery - mt.get_height() // 2))

    def _draw_game_over(self):
        """Vẽ màn hình game over chuyên nghiệp."""
        W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        
        # Overlay
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((20, 0, 0, 180)) # Reddish tint
        self.screen.blit(overlay, (0, 0))

        # Panel
        pw, ph = 600, 350
        px, py = (W - pw) // 2, (H - ph) // 2
        color = (255, 40, 40)
        
        pygame.draw.rect(self.screen, (20, 10, 10), (px, py, pw, ph))
        pygame.draw.rect(self.screen, color, (px, py, pw, ph), 2)
        
        # Title
        t_surf = self.font_title.render("SYSTEM FAILURE", True, color)
        self.screen.blit(t_surf, (W // 2 - t_surf.get_width() // 2, py + 40))

        # Status
        s_surf = self.font_normal.render("CRITICAL DATA LOSS DETECTED", True, (255, 150, 150))
        self.screen.blit(s_surf, (W // 2 - s_surf.get_width() // 2, py + 120))

        # Buttons
        bw, bh = 200, 50
        retry_rect = pygame.Rect(W // 2 - bw - 20, py + 220, bw, bh)
        pygame.draw.rect(self.screen, (40, 20, 20), retry_rect)
        pygame.draw.rect(self.screen, (0, 255, 100), retry_rect, 2)
        rt = self.font_normal.render("REBOOT", True, (255, 255, 255))
        self.screen.blit(rt, (retry_rect.centerx - rt.get_width() // 2, retry_rect.centery - rt.get_height() // 2))

        menu_rect = pygame.Rect(W // 2 + 20, py + 220, bw, bh)
        pygame.draw.rect(self.screen, (20, 20, 30), menu_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), menu_rect, 1)
        mt = self.font_normal.render("HUB", True, (255, 255, 255))
        self.screen.blit(mt, (menu_rect.centerx - mt.get_width() // 2, menu_rect.centery - mt.get_height() // 2))

    def _draw_victory(self):
        """Vẽ màn hình thắng toàn bộ game chuyên nghiệp."""
        W, H = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
        
        # Overlay (Keep BG visible)
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 20, 40, 150)) # Transparent blue tint
        for y in range(0, H, 2):
            pygame.draw.line(overlay, (0, 40, 80, 50), (0, y), (W, y))
        self.screen.blit(overlay, (0, 0))

        # Panel
        pw, ph = 700, 400
        px, py = (W - pw) // 2, (H - ph) // 2
        color = (0, 255, 255)
        
        pygame.draw.rect(self.screen, (5, 10, 20, 240), (px, py, pw, ph))
        pygame.draw.rect(self.screen, color, (px, py, pw, ph), 4)
        
        # Title
        t_surf = self.font_title.render("GRAND VICTORY", True, color)
        self.screen.blit(t_surf, (W // 2 - t_surf.get_width() // 2, py + 60))

        # Subtitle
        s_surf = self.font_normal.render("GLOBAL SECURITY RESTORED", True, (150, 255, 255))
        self.screen.blit(s_surf, (W // 2 - s_surf.get_width() // 2, py + 140))
        
        msg = self.font_normal.render("All malicious nodes have been purged from the network.", True, (100, 150, 200))
        self.screen.blit(msg, (W // 2 - msg.get_width() // 2, py + 200))

        # Menu Button
        bw, bh = 300, 60
        menu_rect = pygame.Rect(W // 2 - bw // 2, py + 280, bw, bh)
        pygame.draw.rect(self.screen, (0, 40, 80), menu_rect)
        pygame.draw.rect(self.screen, color, menu_rect, 2)
        mt = self.font_normal.render("RETURN TO MAIN HUB", True, (255, 255, 255))
        self.screen.blit(mt, (menu_rect.centerx - mt.get_width() // 2, menu_rect.centery - mt.get_height() // 2))

    def run(self):
        """Chạy game loop chính."""
        while self.running:
            dt = self.clock.tick(settings.FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()


def main():
    """Khởi động Cypher Defense với GameManager."""
    manager = GameManager()
    manager.run()


if __name__ == "__main__":
    main()

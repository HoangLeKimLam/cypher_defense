"""ui/right_panel.py — Right-side info panel: tower graphic, stats, upgrade tree."""

from __future__ import annotations
from collections import deque
import pygame
import settings

# ── Static tower metadata ──────────────────────────────────────────────────
_S = settings

TOWER_META: dict = {
    "BasicNode": {
        "label": "Basic Node",
        "sprite": "tower_basic",
        "cost": _S.TOWER_BASIC_COST,
        "accent": (100, 160, 255),
        "desc": "All-purpose tower with balanced attack stats.",
        "stats": [
            ("HP",     _S.TOWER_BASIC_HP),
            ("Damage", _S.TOWER_BASIC_DAMAGE),
            ("Atk/s",  _S.TOWER_BASIC_FIRE_RATE),
            ("Range",  _S.TOWER_BASIC_RANGE),
        ],
    },
    "IceWall": {
        "label": "Ice Wall",
        "sprite": "tower_ice",
        "cost": _S.TOWER_ICE_COST,
        "accent": (90, 210, 255),
        "desc": "Slows enemies. Essential support tower.",
        "stats": [
            ("HP",       _S.TOWER_ICE_HP),
            ("Damage",   _S.TOWER_ICE_DAMAGE),
            ("Atk/s",    _S.TOWER_ICE_FIRE_RATE),
            ("Range",    _S.TOWER_ICE_RANGE),
            ("Slow",     f"{int((1 - _S.TOWER_ICE_SLOW_FACTOR) * 100)}%"),
            ("Slow dur", f"{_S.TOWER_ICE_SLOW_DURATION}s"),
        ],
    },
    "RadarNode": {
        "label": "Radar Node",
        "sprite": "tower_radar",
        "cost": _S.TOWER_RADAR_COST,
        "accent": (80, 230, 150),
        "desc": "Reveals invisible malware. No attack.",
        "stats": [
            ("HP",     _S.TOWER_RADAR_HP),
            ("Range",  _S.TOWER_RADAR_RANGE),
        ],
    },
    "FireNode": {
        "label": "Fire Node",
        "sprite": "tower_fire",
        "cost": _S.TOWER_FIRE_COST,
        "accent": (255, 110, 40),
        "desc": "Leaves burning marks. High DPS over time. On demolish: triggers a fire explosion in the area.",
        "stats": [
            ("HP",       _S.TOWER_FIRE_HP),
            ("Damage",   _S.TOWER_FIRE_DAMAGE),
            ("Atk/s",    _S.TOWER_FIRE_FIRE_RATE),
            ("Range",    _S.TOWER_FIRE_RANGE),
            ("Burn/s",   _S.FIRE_DAMAGE_PER_SEC),
            ("Burn dur", f"{_S.TOWER_FIRE_DURATION}s"),
        ],
    },
    "SniperNode": {
        "label": "Sniper Node",
        "sprite": "tower_sniper",
        "cost": _S.TOWER_SNIPER_COST,
        "accent": (220, 200, 70),
        "desc": "Extreme range and damage. Very slow fire rate.",
        "stats": [
            ("HP",     _S.TOWER_SNIPER_HP),
            ("Damage", _S.TOWER_SNIPER_DAMAGE),
            ("Atk/s",  _S.TOWER_SNIPER_FIRE_RATE),
            ("Range",  _S.TOWER_SNIPER_RANGE),
        ],
    },
    "SpeedNode": {
        "label": "Speed Node",
        "sprite": "tower_speed",
        "cost": _S.TOWER_SPEED_COST,
        "accent": (230, 160, 50),
        "desc": "Rapid-fire. Shreds weak and fast enemies.",
        "stats": [
            ("HP",     _S.TOWER_SPEED_HP),
            ("Damage", _S.TOWER_SPEED_DAMAGE),
            ("Atk/s",  _S.TOWER_SPEED_FIRE_RATE),
            ("Range",  _S.TOWER_SPEED_RANGE),
        ],
    },
    "FreezeNode": {
        "label": "Freeze Node",
        "sprite": "tower_freeze",
        "cost": _S.TOWER_FREEZE_COST,
        "accent": (160, 210, 255),
        "desc": "Completely stops enemies in their tracks. On demolish: freezes all nearby enemies in a short radius.",
        "stats": [
            ("HP",       _S.TOWER_FREEZE_HP),
            ("Damage",   _S.TOWER_FREEZE_DAMAGE),
            ("Range",    _S.TOWER_ICE_RANGE),
            ("Freeze",   f"{_S.TOWER_FREEZE_SLOW_DURATION}s"),
        ],
    },
    "SpreadNode": {
        "label": "Spread Node",
        "sprite": "tower_spread",
        "cost": _S.TOWER_SPREAD_COST,
        "accent": (180, 110, 230),
        "desc": "AoE slow. Hits and slows multiple enemies. On demolish: instantly slows all enemies in the blast area.",
        "stats": [
            ("HP",      _S.TOWER_SPREAD_HP),
            ("Damage",  _S.TOWER_SPREAD_DAMAGE),
            ("Atk/s",   _S.TOWER_SPREAD_FIRE_RATE),
            ("Range",   _S.TOWER_SPREAD_RANGE),
            ("Slow",    f"{int((1 - _S.TOWER_SPREAD_SLOW_FACTOR) * 100)}%"),
            ("AoE rad", _S.TOWER_SPREAD_SLOW_RANGE),
        ],
    },
    "PoisonNode": {
        "label": "Poison Node",
        "sprite": "tower_poison",
        "cost": _S.TOWER_POISON_COST,
        "accent": (130, 220, 80),
        "desc": "Poisons all enemies in range continuously.",
        "stats": [
            ("HP",     _S.TOWER_POISON_HP),
            ("Dmg/s",  _S.TOWER_POISON_DAMAGE),
            ("Atk/s",  _S.TOWER_POISON_FIRE_RATE),
            ("Range",  _S.TOWER_POISON_RANGE),
        ],
    },
    "Wall": {
        "label": "Firewall",
        "sprite": None,
        "cost": 0,
        "accent": (160, 140, 100),
        "desc": "Temporary barrier. Blocks paths for 10s then collapses.",
        "stats": [],
    },
}

# Base tree root for each tower class
TOWER_TREE_MAP: dict[str, str | None] = {
    "BasicNode":  "BasicNode",
    "FireNode":   "BasicNode",
    "SniperNode": "BasicNode",
    "SpeedNode":  "BasicNode",
    "IceWall":    "IceWall",
    "FreezeNode": "IceWall",
    "SpreadNode": "IceWall",
    "RadarNode":  "RadarNode",
    "PoisonNode": "RadarNode",
    "Wall":       None,
}


# Maps stat_buff dict keys → the label used in TOWER_META stats lists
STAT_KEY_LABEL: dict[str, str] = {
    "damage":        "Damage",
    "fire_rate":     "Atk/s",
    "range":         "Range",
    "slow_duration": "Slow dur",
    "slow_factor":   "Slow",
    "hp":            "HP",
}


class RightPanel:
    """Panel HUD bên phải — hiển thị sprite, stats, và upgrade tree của tower được chọn.

    Người chơi nhấn phím 1-4 để chọn loại tower; click vào node trong cây
    để xem trước stats của tower nâng cấp đó.

    Attributes:
        upgrade_trees (dict): Map tree_key → UpgradeTree (BasicNode/IceWall/RadarNode).
        selected_type (str): Tên class tower đang được chọn (vd. "BasicNode").
        preview_type (str | None): Tên class tower đang được preview qua node click.
        preview_node (SkillNode | None): Node upgrade đang được preview.
        node_rects (dict[str, pygame.Rect]): Map node_id → Rect để hit-test click.
        hovered_node (str | None): node_id đang được hover, None nếu không hover.
        current_level (int): Level game hiện tại — dùng để kiểm tra tower unlock.
        panel_x (int): Tọa độ pixel x bắt đầu của panel.
        panel_y (int): Tọa độ pixel y bắt đầu của panel.
        panel_w (int): Chiều rộng panel (pixel).
        panel_h (int): Chiều cao panel (pixel).

    Usage::

        panel = RightPanel(upgrade_trees)
        panel.set_tower_type("BasicNode")
        panel.draw(screen)
        panel.handle_event(event)
    """

    # ── Layout ──────────────────────────────────────────────────────────────
    PAD        = 14
    NODE_W     = 86
    NODE_H     = 80
    NODE_GAP   = 10
    LEVEL_GAP  = 30

    # ── Palette ─────────────────────────────────────────────────────────────
    BG         = (11, 13, 21)
    CARD_BG    = (20, 24, 38)
    DIVIDER    = (38, 48, 68)
    TEXT       = (210, 216, 232)
    LABEL      = (120, 138, 168)
    CONN       = (50, 68, 100)

    def __init__(self, upgrade_trees: dict):
        """Khởi tạo RightPanel với upgrade trees và giá trị mặc định.

        Args:
            upgrade_trees (dict): Map tree_key → UpgradeTree do game.py tạo khi load level.

        Side effects:
            - Gọi _init_dims() để tính kích thước panel từ settings.
            - Fonts được lazy-init lần đầu khi draw() được gọi.
        """
        self.upgrade_trees  = upgrade_trees
        self.selected_type  = "BasicNode"
        self.preview_type: str | None = None
        self.preview_node = None   # SkillNode currently previewed (may be stat_buff)
        self.node_rects: dict[str, pygame.Rect] = {}
        self.hovered_node: str | None = None
        self.current_level  = 1
        self._dirty = True
        self._surf: pygame.Surface | None = None
        self._init_dims()
        self._fonts_ready = False

    # ── Dimensions ──────────────────────────────────────────────────────────

    def _init_dims(self):
        """Tính tọa độ và kích thước panel dựa trên settings.

        Side effects:
            - Đặt panel_x, panel_y, panel_w, panel_h từ GRID_COLS, CELL_SIZE, SCREEN_WIDTH/HEIGHT.
        """
        cs = settings.CELL_SIZE
        self.panel_x = int(settings.GRID_COLS * cs)
        self.panel_y = 0
        self.panel_w = settings.SCREEN_WIDTH  - self.panel_x
        self.panel_h = settings.SCREEN_HEIGHT

    def _init_fonts(self):
        """Khởi tạo fonts lần đầu (lazy init). Không làm gì nếu đã khởi tạo.

        Side effects:
            - Tạo f_title, f_section, f_body, f_desc, f_small, f_node từ pygame.font.SysFont.
            - Fallback về Font(None, 16) nếu "courier new" không tìm thấy.
            - Đặt _fonts_ready = True sau khi hoàn tất.
        """
        if self._fonts_ready:
            return
        try:
            self.f_title  = pygame.font.SysFont("courier new", 19, bold=True)
            self.f_section= pygame.font.SysFont("courier new", 12, bold=True)
            self.f_body   = pygame.font.SysFont("courier new", 12)
            self.f_desc   = pygame.font.SysFont("courier new", 14)
            self.f_small  = pygame.font.SysFont("courier new", 11)
            self.f_node   = pygame.font.SysFont("courier new", 11, bold=True)
        except Exception:
            f = pygame.font.Font(None, 16)
            self.f_title = self.f_section = self.f_body = self.f_desc = self.f_small = self.f_node = f
        self._fonts_ready = True

    # ── Public API ───────────────────────────────────────────────────────────

    def set_tower_type(self, tower_class_name: str):
        """Đặt loại tower đang được chọn và reset preview nếu type thay đổi.

        Args:
            tower_class_name (str): Tên class tower (vd. "BasicNode", "IceWall").

        Side effects:
            - Cập nhật selected_type, xóa preview_type/preview_node.
            - Đặt _dirty = True để panel re-render.
        """
        if self.selected_type != tower_class_name:
            self.selected_type = tower_class_name
            self.preview_type  = None
            self.preview_node  = None
            self._dirty = True

    def set_level(self, level: int):
        """Cập nhật level game hiện tại để kiểm tra trạng thái unlock tower.

        Args:
            level (int): Level game hiện tại.

        Side effects:
            - Cập nhật current_level; đặt _dirty = True nếu level thay đổi.
        """
        if self.current_level != level:
            self.current_level = level
            self._dirty = True

    def invalidate(self):
        """Force re-render next frame (call after upgrades that change unlock state)."""
        self._dirty = True

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Xử lý sự kiện chuột; trả về True nếu event được panel tiêu thụ.

        Args:
            event (pygame.event.Event): Sự kiện pygame (MOUSEMOTION hoặc MOUSEBUTTONDOWN).

        Returns:
            bool: True nếu con trỏ nằm trong panel và event đã được xử lý.
                False nếu con trỏ ngoài panel hoặc event không liên quan.

        Side effects:
            - MOUSEMOTION: cập nhật hovered_node; đặt _dirty nếu hover thay đổi.
            - MOUSEBUTTONDOWN (left): gọi _on_node_click() nếu click trúng node.
        """
        if not hasattr(event, 'pos'):
            return False
        mx, my = event.pos
        if mx < self.panel_x:
            return False
        lx, ly = mx - self.panel_x, my - self.panel_y

        if event.type == pygame.MOUSEMOTION:
            old = self.hovered_node
            self.hovered_node = None
            for nid, rect in self.node_rects.items():
                if rect.collidepoint(lx, ly):
                    self.hovered_node = nid
                    break
            if self.hovered_node != old:
                self._dirty = True
            return self.hovered_node is not None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for nid, rect in self.node_rects.items():
                if rect.collidepoint(lx, ly):
                    self._on_node_click(nid)
                    return True
        return False

    def draw(self, screen: pygame.Surface):
        """Vẽ panel lên màn hình; re-render cache nếu _dirty = True.

        Args:
            screen (pygame.Surface): Màn hình game do game.py truyền vào.

        Side effects:
            - Gọi _render() và lưu vào _surf khi _dirty.
            - Blit _surf vào (panel_x, panel_y) trên screen.
        """
        self._init_fonts()
        if self._dirty or self._surf is None:
            self._surf = self._render()
            self._dirty = False
        screen.blit(self._surf, (self.panel_x, self.panel_y))

    # ── Rendering ────────────────────────────────────────────────────────────

    def _render(self) -> pygame.Surface:
        """Vẽ toàn bộ nội dung panel vào Surface mới và trả về.

        Returns:
            pygame.Surface: Surface kích thước panel_w × panel_h đã vẽ đầy đủ.

        Side effects:
            - Gọi các hàm _draw_* theo thứ tự từ trên xuống.
        """
        surf = pygame.Surface((self.panel_w, self.panel_h))
        surf.fill(self.BG)

        # Left border
        pygame.draw.line(surf, self.DIVIDER, (1, 0), (1, self.panel_h), 2)

        p = self.PAD
        y = p
        y = self._draw_instruction(surf, y)
        y = self._draw_sep(surf, y + 4)
        y = self._draw_header(surf, y + 8)
        y = self._draw_sep(surf, y + 10)
        y = self._draw_stats(surf, y + 10)
        y = self._draw_sep(surf, y + 10)
        self._draw_tree(surf, y + 12)

        return surf

    def _draw_instruction(self, surf: pygame.Surface, y: int) -> int:
        """Vẽ dòng hướng dẫn phím tắt ở đầu panel.

        Args:
            surf (pygame.Surface): Surface đang render.
            y (int): Tọa độ y bắt đầu vẽ.

        Returns:
            int: Tọa độ y sau khi vẽ xong section này.
        """
        p = self.PAD
        title_s = self.f_section.render("HUD INSTRUCTIONS", True, (170, 185, 220))
        surf.blit(title_s, (p, y))
        y += title_s.get_height() + 5

        hints = [
            ("[1] Basic Node", (100, 160, 255)),
            ("[2] Ice Wall",   (90,  210, 255)),
            ("[3] Radar Node", (80,  230, 150)),
            ("[4] Firewall",   (160, 140, 100)),
        ]
        col_w = (self.panel_w - 2 * p) // 2
        for i, (text, color) in enumerate(hints):
            col = i % 2
            row = i // 2
            sx = p + col * col_w
            sy = y + row * 16
            s = self.f_small.render(text, True, color)
            surf.blit(s, (sx, sy))

        rows = (len(hints) + 1) // 2
        return y + rows * 16

    # ── Header (sprite + name + cost + desc) ────────────────────────────────

    def _draw_header(self, surf: pygame.Surface, y: int) -> int:
        """Vẽ card header: sprite tower, tên, cost/lock badge, và description.

        Args:
            surf (pygame.Surface): Surface đang render.
            y (int): Tọa độ y bắt đầu vẽ card.

        Returns:
            int: Tọa độ y phía dưới card (card.bottom).
        """
        display = self.preview_type or self.selected_type
        meta    = TOWER_META.get(display, TOWER_META["BasicNode"])
        accent  = meta["accent"]
        p, pw   = self.PAD, self.panel_w

        SPRITE_SZ = 82
        CARD_H    = SPRITE_SZ + 24
        card = pygame.Rect(p, y, pw - 2 * p, CARD_H)

        # Card background + accent border
        pygame.draw.rect(surf, self.CARD_BG, card, border_radius=8)
        pygame.draw.rect(surf, accent,       card, width=1, border_radius=8)

        # Sprite
        sx, sy = card.x + 10, card.y + (CARD_H - SPRITE_SZ) // 2
        self._blit_sprite(surf, meta.get("sprite"), sx, sy, SPRITE_SZ, accent)

        # Check lock state for the selected (not preview) tower
        tower_locked = not settings.is_tower_unlocked(self.selected_type, self.current_level)
        lock_lvl     = settings.UNLOCK_LEVEL.get(self.selected_type, 1)

        # Text block
        tx = sx + SPRITE_SZ + 14
        tw = card.right - tx - 8

        name_color = (130, 130, 140) if tower_locked else (240, 242, 255)
        name_s = self.f_title.render(meta["label"], True, name_color)
        surf.blit(name_s, (tx, card.top + 9))

        if tower_locked:
            lock_s = self.f_section.render(f"LOCKED — LV {lock_lvl}", True, (210, 80, 80))
            surf.blit(lock_s, (tx, card.top + 31))
        else:
            cost_s = self.f_small.render(f"$ {meta['cost']}", True, (210, 185, 55))
            surf.blit(cost_s, (tx, card.top + 31))

        # Accent bar under label
        bar_y = card.top + 29
        bar_color = (160, 60, 60) if tower_locked else accent
        pygame.draw.line(surf, (*bar_color, 120), (tx, bar_y), (tx + tw, bar_y))

        self._blit_wrapped(surf, meta.get("desc", ""), self.f_desc,
                           self.LABEL, tx, card.top + 48, tw)

        # Lock overlay on sprite
        if tower_locked:
            overlay = pygame.Surface((SPRITE_SZ, SPRITE_SZ), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            surf.blit(overlay, (sx, sy))
            lock_icon = self.f_title.render("🔒", True, (220, 80, 80))
            surf.blit(lock_icon, (sx + SPRITE_SZ // 2 - lock_icon.get_width() // 2,
                                   sy + SPRITE_SZ // 2 - lock_icon.get_height() // 2))

        # "PREVIEW" badge
        if self.preview_type and self.preview_type != self.selected_type and not tower_locked:
            badge = self.f_small.render("▶ PREVIEW", True, (210, 175, 50))
            surf.blit(badge, (card.right - badge.get_width() - 8, card.top + 7))

        return card.bottom

    def _blit_sprite(self, surf, key, x, y, sz, accent):
        """Vẽ sprite tower (hoặc fallback hình tròn) với glow backdrop.

        Args:
            surf (pygame.Surface): Surface đang render.
            key (str | None): Sprite key trong cache (vd. "tower_basic").
            x (int): Tọa độ x vẽ sprite.
            y (int): Tọa độ y vẽ sprite.
            sz (int): Kích thước sprite (sz × sz pixel).
            accent (tuple): Màu RGB accent của tower — dùng cho glow backdrop.
        """
        from ui.sprites import get as _sget
        raw = _sget(key) if key else None
        img = None
        if isinstance(raw, pygame.Surface):
            img = pygame.transform.smoothscale(raw, (sz, sz))
        elif isinstance(raw, list) and raw:
            img = pygame.transform.smoothscale(raw[0], (sz, sz))

        # Glow backdrop
        glow = pygame.Surface((sz + 10, sz + 10), pygame.SRCALPHA)
        glow.fill((*accent, 25))
        pygame.draw.rect(glow, (*accent, 60), (0, 0, sz + 10, sz + 10), width=1, border_radius=7)
        surf.blit(glow, (x - 5, y - 5))

        if img:
            surf.blit(img, (x, y))
        else:
            pygame.draw.rect(surf, (28, 32, 50), (x, y, sz, sz), border_radius=6)
            pygame.draw.circle(surf, accent, (x + sz // 2, y + sz // 2), sz // 3, 2)

    # ── Stats grid ───────────────────────────────────────────────────────────

    def _draw_stats(self, surf: pygame.Surface, y: int) -> int:
        """Vẽ bảng stats của tower (hoặc tower đang preview).

        Nếu preview_node là stat_buff, hiển thị giá trị gốc + delta (highlight xanh).

        Args:
            surf (pygame.Surface): Surface đang render.
            y (int): Tọa độ y bắt đầu section stats.

        Returns:
            int: Tọa độ y phía dưới sau khi vẽ xong tất cả dòng stats.
        """
        display = self.preview_type or self.selected_type
        meta    = TOWER_META.get(display, TOWER_META["BasicNode"])
        accent  = meta["accent"]
        p, pw   = self.PAD, self.panel_w

        # Build stat rows, merging any stat_buff preview deltas
        base_stats: list[tuple] = list(meta.get("stats", []))
        buff_labels: set[str] = set()
        if self.preview_node and self.preview_node.upgrade_type == "stat_buff" and self.preview_node.stat_buff:
            for stat_key, delta in self.preview_node.stat_buff.items():
                label = STAT_KEY_LABEL.get(stat_key, stat_key)
                buff_labels.add(label)
                found = False
                for i, (lbl, val) in enumerate(base_stats):
                    if lbl == label:
                        try:
                            base_stats[i] = (lbl, f"{val} +{delta}")
                        except Exception:
                            base_stats[i] = (lbl, f"{val} +{delta}")
                        found = True
                        break
                if not found:
                    base_stats.append((label, f"+{delta}"))

        hdr = self.f_section.render("STATS", True, accent)
        surf.blit(hdr, (p, y))
        y += hdr.get_height() + 8

        if not base_stats:
            s = self.f_small.render("No stats available.", True, self.LABEL)
            surf.blit(s, (p, y))
            return y + s.get_height()

        col_w  = (pw - 2 * p) // 2
        row_h  = 21
        LABEL_W = 74

        for i, (label, value) in enumerate(base_stats):
            col = i % 2
            row = i // 2
            sx  = p + col * col_w
            sy  = y + row * row_h

            is_buffed = label in buff_labels
            val_color = (120, 230, 140) if is_buffed else (240, 242, 255)

            lbl = self.f_small.render(label, True, self.LABEL)
            val = self.f_section.render(str(value), True, val_color)
            surf.blit(lbl, (sx, sy + 1))
            surf.blit(val, (sx + LABEL_W, sy))

        rows = (len(base_stats) + 1) // 2
        return y + rows * row_h

    # ── Upgrade tree ─────────────────────────────────────────────────────────

    def _draw_tree(self, surf: pygame.Surface, y: int):
        """Vẽ toàn bộ upgrade tree của tower đang chọn: header, connectors, nodes.

        Args:
            surf (pygame.Surface): Surface đang render.
            y (int): Tọa độ y bắt đầu section upgrade tree.

        Side effects:
            - Xóa và tái tạo node_rects cho hit-testing click/hover.
            - Gọi _layout(), _draw_connections(), _draw_node() theo thứ tự.
        """
        self.node_rects.clear()

        tree_key = TOWER_TREE_MAP.get(self.selected_type)
        accent   = TOWER_META.get(self.selected_type, {}).get("accent", (100, 150, 220))
        p        = self.PAD

        hdr = self.f_section.render("UPGRADE TREE", True, accent)
        surf.blit(hdr, (p, y))
        y += hdr.get_height() + 12

        if not tree_key:
            s = self.f_small.render("No upgrade tree for this tower.", True, self.LABEL)
            surf.blit(s, (p, y))
            return

        tree = self.upgrade_trees.get(tree_key)
        if not tree:
            return

        positions = self._layout(tree.root, y)

        # Draw connectors first (behind nodes)
        self._draw_connections(surf, tree.root, positions)

        # Draw nodes
        for nid, (nx, ny) in positions.items():
            node = tree.get_node(nid)
            if node:
                self._draw_node(surf, node, nx, ny, accent)

    def _layout(self, root, start_y: int) -> dict[str, tuple[int, int]]:
        """BFS level layout: phân bổ đều các node của mỗi level theo chiều ngang panel.

        Args:
            root (SkillNode): Node gốc của UpgradeTree.
            start_y (int): Tọa độ y bắt đầu vẽ level đầu tiên.

        Returns:
            dict[str, tuple[int, int]]: Map node_id → (x, y) pixel tọa độ góc trên-trái node.
        """
        levels: list[list] = []
        q = deque([(root, 0)])
        while q:
            node, depth = q.popleft()
            while len(levels) <= depth:
                levels.append([])
            levels[depth].append(node)
            for child in node.children:
                q.append((child, depth + 1))

        positions: dict[str, tuple[int, int]] = {}
        pw = self.panel_w
        level_y = start_y

        for nodes in levels:
            count   = len(nodes)
            total_w = count * self.NODE_W + (count - 1) * self.NODE_GAP
            start_x = (pw - total_w) // 2
            for i, node in enumerate(nodes):
                nx = start_x + i * (self.NODE_W + self.NODE_GAP)
                positions[node.node_id] = (nx, level_y)
            level_y += self.NODE_H + self.LEVEL_GAP

        return positions

    def _draw_connections(self, surf, node, positions: dict):
        """Vẽ đường nối hình chữ L từ node cha đến từng node con (đệ quy).

        Args:
            surf (pygame.Surface): Surface đang render.
            node (SkillNode): Node hiện tại (xuất phát điểm của đường nối).
            positions (dict[str, tuple[int, int]]): Map node_id → (x, y) từ _layout().

        Side effects:
            - Vẽ 3 đoạn thẳng màu CONN cho mỗi cặp cha-con: xuống → ngang → lên.
        """
        if node.node_id not in positions:
            return
        px, py = positions[node.node_id]
        bottom  = (px + self.NODE_W // 2, py + self.NODE_H)
        for child in node.children:
            if child.node_id in positions:
                cx, cy = positions[child.node_id]
                top    = (cx + self.NODE_W // 2, cy)
                mid_y  = (bottom[1] + top[1]) // 2
                pygame.draw.line(surf, self.CONN, bottom, (bottom[0], mid_y), 2)
                pygame.draw.line(surf, self.CONN, (bottom[0], mid_y), (top[0], mid_y), 2)
                pygame.draw.line(surf, self.CONN, (top[0], mid_y), top, 2)
            self._draw_connections(surf, child, positions)

    def _draw_node(self, surf, node, nx: int, ny: int, accent: tuple):
        """Vẽ một node trong upgrade tree với icon, tên, cost/badge, và trạng thái màu sắc.

        Args:
            surf (pygame.Surface): Surface đang render.
            node (SkillNode): Node cần vẽ.
            nx (int): Tọa độ x góc trên-trái của node box.
            ny (int): Tọa độ y góc trên-trái của node box.
            accent (tuple): Màu RGB accent của tower gốc — không dùng trực tiếp ở đây
                nhưng truyền từ _draw_tree để nhất quán với phong cách màu.

        Side effects:
            - Thêm node.node_id → Rect vào self.node_rects để hit-test click/hover.
        """
        rect = pygame.Rect(nx, ny, self.NODE_W, self.NODE_H)
        self.node_rects[node.node_id] = rect

        is_base         = node.upgrade_type == "base"
        is_unlocked     = node.is_unlocked
        is_preview      = (self.preview_type == node.tower_class and node.tower_class)
        is_hovered      = (self.hovered_node == node.node_id)
        node_lock_key   = node.node_id if not is_base else (node.tower_class or node.node_id)
        is_level_locked = not settings.is_tower_unlocked(node_lock_key, self.current_level)
        lock_lvl        = settings.UNLOCK_LEVEL.get(node_lock_key, 1)

        if is_level_locked:
            fill, border, tc = (38, 10, 10), (140, 40, 40),  (180, 70, 70)
        elif is_preview:
            fill, border, tc = (42, 38, 8),  (215, 175, 55), (255, 215, 80)
        elif is_unlocked:
            fill, border, tc = (12, 38, 18), (55, 175, 85),  (100, 210, 120)
        elif is_hovered:
            fill, border, tc = (28, 33, 52), (130, 155, 215),(195, 208, 255)
        else:
            fill, border, tc = (18, 20, 33), (50, 60, 88),   (130, 142, 165)

        pygame.draw.rect(surf, fill,   rect, border_radius=7)
        pygame.draw.rect(surf, border, rect, width=1, border_radius=7)

        cx     = rect.centerx
        ICON_SZ = 24
        icon_y  = rect.top + 6

        # Icon — top-center
        if node.tower_class and node.tower_class in TOWER_META:
            icon_key = TOWER_META[node.tower_class].get("sprite")
            if icon_key:
                from ui.sprites import get as _sget
                raw  = _sget(icon_key)
                icon = None
                if isinstance(raw, pygame.Surface):
                    icon = pygame.transform.smoothscale(raw, (ICON_SZ, ICON_SZ))
                elif isinstance(raw, list) and raw:
                    icon = pygame.transform.smoothscale(raw[0], (ICON_SZ, ICON_SZ))
                if icon:
                    surf.blit(icon, (cx - ICON_SZ // 2, icon_y))

        # Unlock checkmark — top-right corner of node
        if is_unlocked and not is_base:
            ck = self.f_small.render("✓", True, (55, 195, 90))
            surf.blit(ck, (rect.right - ck.get_width() - 3, rect.top + 3))

        # Name — centered below icon
        name = node.name
        if len(name) > 10:
            name = name[:9] + "…"
        name_s = self.f_node.render(name, True, tc)
        name_y = icon_y + ICON_SZ + 4
        surf.blit(name_s, (cx - name_s.get_width() // 2, name_y))

        # Cost / badge / buff delta — centered at bottom
        bottom_y = name_y + name_s.get_height() + 4

        if is_level_locked:
            lk_s = self.f_small.render(f"LV{lock_lvl}+", True, (180, 70, 70))
            surf.blit(lk_s, (cx - lk_s.get_width() // 2, bottom_y))
        elif is_base:
            label  = "OWNED" if is_unlocked else "BASE"
            color  = (55, 175, 85) if is_unlocked else (80, 95, 120)
            badge  = self.f_small.render(label, True, color)
            surf.blit(badge, (cx - badge.get_width() // 2, bottom_y))
        elif node.upgrade_type == "stat_buff" and node.stat_buff:
            parts   = [f"+{v} {STAT_KEY_LABEL.get(k, k)[:3]}" for k, v in node.stat_buff.items()]
            delta_c = (130, 210, 130) if is_unlocked else (160, 175, 45)
            cost_c  = (175, 155, 45) if not is_unlocked else (65, 125, 75)
            delta_s = self.f_small.render(" ".join(parts), True, delta_c)
            cost_s  = self.f_small.render(f"${node.cost}", True, cost_c)
            surf.blit(delta_s, (cx - delta_s.get_width() // 2, bottom_y))
            surf.blit(cost_s,  (cx - cost_s.get_width() // 2, bottom_y + 12))
        elif node.cost > 0:
            cost_c = (175, 155, 45) if not is_unlocked else (65, 125, 75)
            cost_s = self.f_small.render(f"${node.cost}", True, cost_c)
            surf.blit(cost_s, (cx - cost_s.get_width() // 2, bottom_y))

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _draw_sep(self, surf: pygame.Surface, y: int) -> int:
        """Vẽ đường kẻ ngang phân cách giữa các section.

        Args:
            surf (pygame.Surface): Surface đang render.
            y (int): Tọa độ y của đường kẻ.

        Returns:
            int: Cùng giá trị y (caller dùng để tính offset tiếp theo).
        """
        p = self.PAD
        pygame.draw.line(surf, self.DIVIDER, (p, y), (self.panel_w - p, y))
        return y

    def _blit_wrapped(self, surf, text: str, font, color, x, y, max_w: int):
        """Vẽ văn bản tự động xuống dòng khi vượt quá max_w pixel.

        Args:
            surf (pygame.Surface): Surface đang render.
            text (str): Chuỗi văn bản cần vẽ.
            font (pygame.font.Font): Font dùng để render.
            color (tuple): Màu RGB chữ.
            x (int): Tọa độ x bắt đầu mỗi dòng.
            y (int): Tọa độ y dòng đầu tiên.
            max_w (int): Chiều rộng tối đa (pixel) trước khi xuống dòng.
        """
        words = text.split()
        line  = ""
        for word in words:
            test = line + word + " "
            if font.size(test)[0] > max_w and line:
                s = font.render(line.rstrip(), True, color)
                surf.blit(s, (x, y))
                y   += s.get_height() + 2
                line = word + " "
            else:
                line = test
        if line.strip():
            surf.blit(font.render(line.rstrip(), True, color), (x, y))

    # ── Node click ───────────────────────────────────────────────────────────

    def _on_node_click(self, node_id: str):
        """Xử lý click vào node: toggle preview hoặc xóa preview nếu click lại node đó.

        Args:
            node_id (str): ID của node vừa được click.

        Side effects:
            - Nếu node đang preview được click lại: xóa preview_type và preview_node.
            - Nếu click node khác: đặt preview_node = node, preview_type = node.tower_class.
            - Không làm gì nếu node bị khóa theo level (level-locked).
            - Đặt _dirty = True để panel re-render.
        """
        tree_key = TOWER_TREE_MAP.get(self.selected_type)
        if not tree_key:
            return
        tree = self.upgrade_trees.get(tree_key)
        if not tree:
            return
        node = tree.get_node(node_id)
        if not node:
            return

        # Block click on level-locked nodes
        node_lock_key = node.node_id if node.upgrade_type != "base" else (node.tower_class or node.node_id)
        if not settings.is_tower_unlocked(node_lock_key, self.current_level):
            return

        # Toggle preview
        if self.preview_node is not None and self.preview_node.node_id == node_id:
            self.preview_type = None
            self.preview_node = None
        else:
            self.preview_node = node
            self.preview_type = node.tower_class if node.tower_class else None
        self._dirty = True

"""
ui/upgrade_menu.py — Hiển thị menu nâng cấp khi click vào tower.
"""
import pygame
import settings


class UpgradeMenu:
    """Menu nâng cấp tower, hiển thị node hiện tại và các nâng cấp sẵn có.

    Attributes:
        tower: Tower object đang được upgrade
        upgrade_tree: UpgradeTree chứa cây nâng cấp
        current_node_id: ID của node hiện tại trong cây
        available_upgrades: Danh sách SkillNode có thể nâng cấp
        is_visible: Menu đang hiển thị hay không
    """

    def __init__(self, tower, upgrade_tree):
        """Khởi tạo UpgradeMenu.

        Args:
            tower: Tower object cần nâng cấp
            upgrade_tree: UpgradeTree chứa cây nâng cấp
        """
        self.tower = tower
        self.upgrade_tree = upgrade_tree

        # Map tower class → upgrade tree root node ID
        tower_class_name = tower.__class__.__name__
        root_node_map = {
            "BasicNode": "basic_root",
            "FireNode": "basic_root",
            "SniperNode": "basic_root",
            "SpeedNode": "basic_root",
            "IceWall": "ice_root",
            "FreezeNode": "ice_root",
            "SpreadNode": "ice_root",
            "RadarNode": "radar_root",
            "PoisonNode": "radar_root",
        }
        self.current_node_id = root_node_map.get(tower_class_name, "basic_root")

        self.available_upgrades = []
        self.is_visible = False
        self.rect = None
        self.upgrade_buttons = []  # List của (upgrade_node, button_rect)
        self.font_title = None
        self.font_normal = None
        self._init_fonts()
        self._update_upgrades()

    def _init_fonts(self):
        """Khởi tạo fonts cho menu."""
        try:
            self.font_title = pygame.font.Font(None, 20)
            self.font_normal = pygame.font.Font(None, 16)
        except:
            self.font_title = pygame.font.Font(None, 20)
            self.font_normal = pygame.font.Font(None, 16)

    def _update_upgrades(self):
        """Cập nhật danh sách nâng cấp có sẵn từ node hiện tại."""
        if self.upgrade_tree:
            self.available_upgrades = self.upgrade_tree.get_available_upgrades(self.current_node_id)

    def show(self):
        """Hiển thị menu upgrade."""
        self.is_visible = True

    def hide(self):
        """Ẩn menu upgrade."""
        self.is_visible = False

    def get_clicked_upgrade(self, pos: tuple):
        """Kiểm tra xem click có trúng nút nâng cấp nào không.

        Args:
            pos: (x, y) vị trí click

        Returns:
            SkillNode của nâng cấp được click, hoặc "DEMOLISH" nếu click nút phá, hoặc None
        """
        if not self.is_visible:
            return None

        x, y = pos
        
        # Kiểm tra demolish button
        if hasattr(self, 'demolish_button_rect') and self.demolish_button_rect:
            if self.demolish_button_rect.collidepoint(x, y):
                return "DEMOLISH"
        
        # Kiểm tra upgrade buttons
        for upgrade_node, button_rect in self.upgrade_buttons:
            if button_rect.collidepoint(x, y):
                return upgrade_node
        return None

    def try_upgrade(self, upgrade_node, money: int) -> tuple[bool, int, str]:
        """Thử nâng cấp tower.

        Args:
            upgrade_node (SkillNode): SkillNode muốn nâng cấp.
            money (int): Tiền hiện tại của player.

        Returns:
            tuple[bool, int, str]:
                - bool: True nếu nâng cấp thành công, False nếu thất bại.
                - int: Số tiền còn lại sau nâng cấp (đã trừ cost nếu thành công).
                - str: Thông báo kết quả (thành công hoặc lý do thất bại).
        """
        if not upgrade_node.can_be_unlocked(money):
            return False, money, "Không đủ tiền hoặc chưa mở khóa node cha"

        # Mở khóa node
        upgrade_node.unlock()
        new_money = money - upgrade_node.cost

        # Cập nhật current node
        self.current_node_id = upgrade_node.node_id
        self._update_upgrades()

        return True, new_money, f"Nâng cấp thành công: {upgrade_node.name}"

    def get_demolish_refund(self) -> int:
        """Tính toán tiền hoàn lại khi phá tháp (50% cost).

        Returns:
            int: 50% của tower.cost (làm tròn xuống)
        """
        return self.tower.cost // 2

    def draw(self, screen, player_money: int = 0, camera_x: float = 0, camera_y: float = 0, current_level: int = 1):
        """Vẽ menu upgrade trên màn hình.

        Args:
            screen: pygame surface để vẽ
            player_money: Số tiền hiện tại của player để kiểm tra nâng cấp khả dụng
            camera_x: Camera horizontal offset (world → screen conversion)
            camera_y: Camera vertical offset (world → screen conversion)
        """
        if not self.is_visible:
            return

        # Tính toán vị trí menu — chuyển world coords sang screen coords
        tower_x = self.tower.pos[1] * settings.CELL_SIZE + settings.CELL_SIZE // 2 - camera_x
        tower_y = self.tower.pos[0] * settings.CELL_SIZE + settings.CELL_SIZE // 2 - camera_y
        menu_w = 200
        num_upgrades = len(self.available_upgrades)
        menu_h = 30 + num_upgrades * 35 + 40
        menu_x = int(tower_x - menu_w // 2)
        menu_y = int(min(tower_y, settings.SCREEN_HEIGHT - menu_h))

        # Chiều rộng & cao của menu (thêm chỗ cho nút demolish)

        # Nền menu (đen mờ)
        menu_rect = pygame.Rect(menu_x, menu_y, menu_w, menu_h)
        pygame.draw.rect(screen, (30, 30, 30), menu_rect)
        pygame.draw.rect(screen, (100, 100, 100), menu_rect, 2)

        # Tiêu đề (node hiện tại)
        if self.upgrade_tree:
            current_node = self.upgrade_tree.get_node(self.current_node_id)
            title_text = self.font_title.render(f"Node: {current_node.name}", True, (200, 200, 200))
        else:
            current_node = self.tower.__class__.__name__
            title_text = self.font_title.render(f"Node: {current_node}", True, (200, 200, 200))
        screen.blit(title_text, (menu_x + 10, menu_y + 8))

        # Vẽ các nút nâng cấp
        self.upgrade_buttons = []
        for i, upgrade_node in enumerate(self.available_upgrades):
            button_y = menu_y + 30 + i * 35
            button_rect = pygame.Rect(menu_x + 10, button_y, menu_w - 20, 30)

            # Xanh chỉ khi đủ điều kiện: đủ tiền + parent unlock + không bị level-lock
            level_ok  = settings.is_tower_unlocked(upgrade_node.node_id, current_level)
            can_unlock = level_ok and upgrade_node.can_be_unlocked(player_money)
            button_color = (100, 200, 100) if can_unlock else (80, 80, 80)

            pygame.draw.rect(screen, button_color, button_rect)
            pygame.draw.rect(screen, (200, 200, 200), button_rect, 1)

            # Text: tên + cost
            text = f"{upgrade_node.name} (Cost: {upgrade_node.cost})"
            text_surf = self.font_normal.render(text, True, (255, 255, 255))
            text_x = button_rect.x + 5
            text_y = button_rect.y + 7
            screen.blit(text_surf, (text_x, text_y))

            self.upgrade_buttons.append((upgrade_node, button_rect))

        # Vẽ nút Demolish (đỏ, ở dưới cùng)
        demolish_y = menu_y + 30 + num_upgrades * 35 + 5
        demolish_rect = pygame.Rect(menu_x + 10, demolish_y, menu_w - 20, 30)
        demolish_refund = self.get_demolish_refund()
        
        pygame.draw.rect(screen, (200, 50, 50), demolish_rect)  # Màu đỏ
        pygame.draw.rect(screen, (255, 100, 100), demolish_rect, 2)
        
        demolish_text = f"Demolish (Refund: {demolish_refund})"
        demolish_surf = self.font_normal.render(demolish_text, True, (255, 255, 255))
        demolish_x = demolish_rect.x + 5
        demolish_y_text = demolish_rect.y + 7
        screen.blit(demolish_surf, (demolish_x, demolish_y_text))
        
        self.demolish_button_rect = demolish_rect

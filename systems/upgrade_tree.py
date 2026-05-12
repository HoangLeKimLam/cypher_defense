class SkillNode:
    """Một node trong cây nâng cấp tower — đại diện cho một lựa chọn upgrade.

    Mỗi node có thể là:
    - "base": Node gốc (đã unlock sẵn, cost=0).
    - "stat_buff": Tăng chỉ số tower (damage, fire_rate, range, slow_duration).
    - "tower_upgrade": Thay thế tower bằng class mới (BasicNode → FireNode).

    Attributes:
        node_id (str): ID duy nhất của node trong cây.
        name (str): Tên hiển thị trong UpgradeMenu.
        cost (int): Tiền cần để mở khóa node này.
        upgrade_type (str): "base", "stat_buff", hoặc "tower_upgrade".
        tower_class (str | None): Tên class tower khi upgrade_type == "tower_upgrade".
        stat_buff (dict | None): {stat_name: delta} khi upgrade_type == "stat_buff".
        is_unlocked (bool): True nếu đã được mua. Mặc định False.
        parent (SkillNode | None): Node cha trong cây. None nếu là root.
        children (list[SkillNode]): Danh sách node con có thể mở sau node này.

    Usage::

        root = SkillNode("basic_root", "BasicNode", cost=0, upgrade_type="base",
                         tower_class="BasicNode")
        root.is_unlocked = True
        child = SkillNode("fire_upgrade", "→ FireNode", cost=120,
                          upgrade_type="tower_upgrade", tower_class="FireNode")
        root.add(child)
    """
    def __init__(self, node_id: str, name: str, cost: int, upgrade_type: str, tower_class: str = None, stat_buff: dict = None):
        """Khởi tạo SkillNode với metadata upgrade.

        Args:
            node_id (str): ID duy nhất trong UpgradeTree.
            name (str): Tên hiển thị trong UpgradeMenu.
            cost (int): Tiền người chơi phải trả để mở khóa.
            upgrade_type (str): "base", "stat_buff", hoặc "tower_upgrade".
            tower_class (str | None): Tên class tower đích (cho tower_upgrade).
            stat_buff (dict | None): Map stat → delta (cho stat_buff).
        """
        self.node_id = node_id
        self.name = name
        self.cost = cost
        self.tower_class = tower_class
        self.upgrade_type = upgrade_type
        self.stat_buff = stat_buff
        self.is_unlocked = False  # Mặc định node chưa được mở khóa
        self.parent = None
        self.children = []  # Danh sách các node con (nâng cấp tiếp theo)
    def add(self, child_node: "SkillNode") -> None:
        """Gắn child_node làm con của node này và đặt parent tương ứng.

        Args:
            child_node (SkillNode): Node con cần thêm vào cây.

        Side effects:
            - Append child_node vào self.children.
            - Đặt child_node.parent = self.
        """
        self.children.append(child_node)
        child_node.parent = self

    def can_be_unlocked(self, money: int) -> bool:
        """Kiểm tra xem node này có thể được mở khóa hay không dựa trên trạng thái của player.

        Args:
            money (int): Số tiền hiện tại của player.

        Returns:
            bool: True nếu node cha đã unlock AND player đủ tiền, False ngược lại.

        Note:
            - Nếu là root node (parent=None), không cần kiểm tra parent.
            - Cost = 0 (root) luôn có thể unlock.
        """
        if self.parent and not self.parent.is_unlocked:
            return False  # Node cha chưa được mở khóa
        if money < self.cost:
            return False  # Player không đủ tiền
        return True

    def unlock(self) -> None:
        """Mở khóa node này (người chơi đã trả tiền).

        Side effects:
            - Đặt self.is_unlocked = True.

        Note:
            Không tự trừ tiền — gọi UpgradeTree.try_unlock() hoặc
            UpgradeMenu.try_upgrade() để trừ tiền và gọi unlock() an toàn.
        """
        self.is_unlocked = True
class UpgradeTree:
    """Cây nâng cấp tower — quản lý toàn bộ SkillNode theo cấu trúc cây.

    Mỗi tower loại (BasicNode, IceWall, RadarNode) có một UpgradeTree riêng.
    game.py tạo các tree khi load level và lưu vào self.upgrade_trees.

    Attributes:
        root (SkillNode): Node gốc của cây (luôn is_unlocked=True, cost=0).
        nodes (dict[str, SkillNode]): Map node_id → SkillNode để tra cứu O(1).

    Usage::

        tree = create_basic_upgrade_tree()
        menu = UpgradeMenu(tower, tree)
        success, new_money = tree.try_unlock("fire_upgrade", current_money)
    """
    def __init__(self, root: SkillNode):
        """Khởi tạo UpgradeTree từ root node và đánh chỉ số toàn bộ cây.

        Args:
            root (SkillNode): Node gốc của cây nâng cấp (cost=0, đã unlock).

        Side effects:
            - Gọi _index_nodes(root) để xây dựng self.nodes dict ngay khi khởi tạo.
        """
        self.root = root
        self.nodes = {}  # Map node_id → SkillNode
        self._index_nodes(root)

    def _index_nodes(self, node: SkillNode) -> None:
        """Đánh chỉ số tất cả nodes để dễ tìm kiếm bằng node_id.

        Args:
            node (SkillNode): Node hiện tại để index.

        Side effects:
            - Thêm node vào self.nodes[node.node_id].
            - Đệ quy gọi trên tất cả children.

        Note:
            Gọi từ __init__() một lần duy nhất. Tạo DFS traversal toàn bộ cây.
        """
        self.nodes[node.node_id] = node
        for child in node.children:
            self._index_nodes(child)

    def get_node(self, node_id: str) -> SkillNode | None:
        """Lấy node theo ID duy nhất.

        Args:
            node_id (str): ID của node cần lấy.

        Returns:
            SkillNode | None: Node nếu tồn tại, None ngược lại.
        """
        return self.nodes.get(node_id)

    def get_available_upgrades(self, current_node_id: str) -> list:
        """Lấy danh sách upgrade có thể làm được từ node hiện tại.

        Args:
            current_node_id (str): ID của node hiện tại (thường là tower class).

        Returns:
            list[SkillNode]: Danh sách các node con (upgrades khả dụng).
                Trả về [] nếu node không tồn tại hoặc node này là leaf.

        Note:
            UpgradeMenu sử dụng hàm này để hiển thị danh sách nút upgrade.
        """
        node = self.get_node(current_node_id)
        if not node:
            return []
        return [child for child in node.children]

    def try_unlock(self, node_id: str, money: int) -> tuple[bool, int]:
        """Thử mở khóa node nếu điều kiện được thỏa mãn.

        Args:
            node_id (str): ID của node cần mở khóa.
            money (int): Số tiền hiện tại của player.

        Returns:
            tuple[bool, int]:
                - bool: True nếu mở khóa thành công, False nếu thất bại.
                - int: Số tiền còn lại (trừ cost nếu thành công, giữ nguyên nếu thất bại).

        Side effects:
            - Gọi node.unlock() nếu điều kiện thỏa mãn (node tồn tại, parent unlock, đủ tiền).

        Note:
            Gọi từ UpgradeMenu.try_upgrade() sau khi player click nút upgrade.
        """
        node = self.get_node(node_id)
        if not node:
            return False, money
        if not node.can_be_unlocked(money):
            return False, money
        node.unlock()
        return True, money - node.cost


def create_basic_upgrade_tree():
    """Tạo và trả về UpgradeTree đầy đủ cho BasicNode.

    Cấu trúc cây:
        BasicNode (root)
        ├── Damage I → SniperNode, FireNode
        └── Speed I  → SpeedNode

    Returns:
        UpgradeTree: Cây nâng cấp với root đã unlock, sẵn sàng dùng cho UpgradeMenu.
    """
    # Root: BasicNode (đã unlock)
    basic_root = SkillNode(
        node_id="basic_root",
        name="BasicNode",
        cost=0,
        upgrade_type="base",
        tower_class="BasicNode"
    )
    basic_root.is_unlocked = True

    # Level 1: 2 nhánh
    # Nhánh 1: Tăng damage
    damage_up_1 = SkillNode(
        node_id="basic_damage_up_1",
        name="Damage I",
        cost=80,
        upgrade_type="stat_buff",
        tower_class="BasicNode",
        stat_buff={"damage": 20}
    )

    # Nhánh 2: Tăng tốc đánh
    speed_up_1 = SkillNode(
        node_id="basic_speed_up_1",
        name="Speed I",
        cost=80,
        upgrade_type="stat_buff",
        tower_class="BasicNode",
        stat_buff={"fire_rate": 2}
    )

    basic_root.add(damage_up_1)
    basic_root.add(speed_up_1)

    # Level 2: Nhánh từ damage_up_1
    sniper_node = SkillNode(
        node_id="sniper_upgrade",
        name="SniperNode",
        cost=100,
        upgrade_type="tower_upgrade",
        tower_class="SniperNode"
    )

    fire_node = SkillNode(
        node_id="fire_upgrade",
        name="FireNode",
        cost=100,
        upgrade_type="tower_upgrade",
        tower_class="FireNode"
    )

    damage_up_1.add(sniper_node)
    damage_up_1.add(fire_node)

    # Level 2: Nhánh từ speed_up_1
    speed_node = SkillNode(
        node_id="speed_upgrade",
        name="SpeedNode",
        cost=100,
        upgrade_type="tower_upgrade",
        tower_class="SpeedNode"
    )

    speed_up_1.add(speed_node)

    return UpgradeTree(basic_root)


def create_ice_upgrade_tree():
    """Tạo và trả về UpgradeTree đầy đủ cho IceWall.

    Cấu trúc cây:
        IceWall (root)
        ├── Range I       → SpreadNode
        └── Slow I        → FreezeNode

    Returns:
        UpgradeTree: Cây nâng cấp với root đã unlock, sẵn sàng dùng cho UpgradeMenu.
    """
    # Root: IceWall (đã unlock)
    ice_root = SkillNode(
        node_id="ice_root",
        name="IceWall",
        cost=0,
        upgrade_type="base",
        tower_class="IceWall"
    )
    ice_root.is_unlocked = True

    # Level 1: 2 nhánh
    # Nhánh 1: Tăng tầm đánh
    range_up_1 = SkillNode(
        node_id="ice_range_up_1",
        name="Range I",
        cost=85,
        upgrade_type="stat_buff",
        tower_class="IceWall",
        stat_buff={"range": 3}
    )

    # Nhánh 2: Tăng thời gian làm chậm
    slow_duration_up_1 = SkillNode(
        node_id="ice_slow_duration_up_1",
        name="Slow I",
        cost=85,
        upgrade_type="stat_buff",
        tower_class="IceWall",
        stat_buff={"slow_duration": 2.0}
    )

    ice_root.add(range_up_1)
    ice_root.add(slow_duration_up_1)

    # Level 2: Nhánh từ range_up_1
    spread_node = SkillNode(
        node_id="spread_upgrade",
        name="SpreadNode",
        cost=110,
        upgrade_type="tower_upgrade",
        tower_class="SpreadNode"
    )

    range_up_1.add(spread_node)

    # Level 2: Nhánh từ slow_duration_up_1
    freeze_node = SkillNode(
        node_id="freeze_upgrade",
        name="FreezeNode",
        cost=110,
        upgrade_type="tower_upgrade",
        tower_class="FreezeNode"
    )

    slow_duration_up_1.add(freeze_node)

    return UpgradeTree(ice_root)


def create_radar_upgrade_tree():
    """Tạo và trả về UpgradeTree đầy đủ cho RadarNode.

    Cấu trúc cây:
        RadarNode (root)
        └── Range I → PoisonNode

    Returns:
        UpgradeTree: Cây nâng cấp với root đã unlock, sẵn sàng dùng cho UpgradeMenu.
    """
    # Root: RadarNode (đã unlock)
    radar_root = SkillNode(
        node_id="radar_root",
        name="RadarNode",
        cost=0,
        upgrade_type="base",
        tower_class="RadarNode"
    )
    radar_root.is_unlocked = True

    # Level 1: 1 nhánh
    # Nhánh 1: Tăng tầm
    range_up_1 = SkillNode(
        node_id="radar_range_up_1",
        name="Range I",
        cost=90,
        upgrade_type="stat_buff",
        tower_class="RadarNode",
        stat_buff={"range": 3}
    )

    radar_root.add(range_up_1)

    # Level 2: Nhánh từ range_up_1
    poison_node = SkillNode(
        node_id="poison_upgrade",
        name="PoisonNode",
        cost=110,
        upgrade_type="tower_upgrade",
        tower_class="PoisonNode"
    )

    range_up_1.add(poison_node)

    return UpgradeTree(radar_root)

from core.data_structures import CustomQueue


class Celltype:
    """Hằng số kiểu ô trong lưới map — dùng thống nhất giữa graph, pathfinding và game.

    Attributes:
        WALL (int): 0 — ô tường, không thể đi qua, tower đặt ở đây.
        PATH (int): 1 — ô đường đi, malware di chuyển trên đây.
        TOWER (int): 2 — ô tường có tower, không walkable.
        SERVER (int): 3 — ô server, malware đi đến đây gây damage.
        SPAWN (int): 4 — ô điểm spawn, walkable (malware xuất hiện ở đây).

    Usage:
        from core.graph import GridGraph, Celltype
        graph.set_cell(row, col, Celltype.TOWER)
        if graph.get_cell(row, col) == Celltype.PATH:
            ...
    """
    WALL = 0
    PATH = 1
    TOWER = 2
    SERVER = 3
    SPAWN = 4


class GridGraph:
    """Lưới ô vuông biểu diễn map game — lõi dữ liệu dùng cho pathfinding và rendering.

    Mỗi ô có kiểu Celltype (WALL/PATH/TOWER/SERVER/SPAWN). GridGraph cung cấp
    các method để kiểm tra, thay đổi ô và tính toán spawn weights.

    Attributes:
        row (int): Số hàng của lưới.
        col (int): Số cột của lưới.
        grid (list[list[int]]): Ma trận 2D lưu Celltype của từng ô.
        spawn_pos (list[tuple]): Danh sách vị trí (row, col) của các ô SPAWN.
        server_pos (tuple | None): Vị trí (row, col) của ô SERVER.
        PLATEAU_THRESHOLD (float): Ngưỡng khoảng cách để tính spawn weight (từ JSON).
        server_radius (int): Bán kính Chebyshev quanh server không cho đặt tower (từ JSON).

    Usage:
        game.py tạo GridGraph và load từ JSON::

            graph = GridGraph(rows, cols)
            graph.load_from_list(config["grid"], config)
            path = astar(graph, spawn_pos, graph.server_pos)
    """

    def __init__(self, row: int, col: int):
        """Khởi tạo GridGraph với toàn bộ ô là WALL.

        Args:
            row (int): Số hàng của lưới.
            col (int): Số cột của lưới.
        """
        self.PLATEAU_THRESHOLD = 0.7
        self.server_radius = 5
        self.row = row
        self.col = col
        self.grid = [[Celltype.WALL for _ in range(col)] for _ in range(row)]
        self.spawn_pos = []
        self.server_pos = None

    def in_bounds(self, x: int, y: int) -> bool:
        """Kiểm tra tọa độ (x, y) có nằm trong phạm vi lưới hay không.

        Args:
            x (int): Hàng cần kiểm tra.
            y (int): Cột cần kiểm tra.

        Returns:
            bool: True nếu 0 <= x < row và 0 <= y < col.
        """
        return 0 <= x < self.row and 0 <= y < self.col

    def is_walkable(self, x: int, y: int) -> bool:
        """Kiểm tra malware có thể đi qua ô (x, y) không.

        Các ô walkable: PATH, SERVER, SPAWN. WALL và TOWER không walkable.

        Args:
            x (int): Hàng cần kiểm tra.
            y (int): Cột cần kiểm tra.

        Returns:
            bool: True nếu ô trong phạm vi và là PATH/SERVER/SPAWN.
        """
        return self.in_bounds(x, y) and (
            self.grid[x][y] == Celltype.PATH or
            self.grid[x][y] == Celltype.SERVER or
            self.grid[x][y] == Celltype.SPAWN
        )

    def set_cell(self, x: int, y: int, celltype: int) -> None:
        """Đặt kiểu ô tại (x, y) và cập nhật spawn_pos/server_pos nếu cần.

        Args:
            x (int): Hàng của ô cần thay đổi.
            y (int): Cột của ô cần thay đổi.
            celltype (int): Kiểu ô mới (hằng số Celltype).

        Side effects:
            - Cập nhật self.grid[x][y].
            - Append (x, y) vào self.spawn_pos nếu celltype == SPAWN.
            - Đặt self.server_pos = (x, y) nếu celltype == SERVER.
        """
        if self.in_bounds(x, y):
            self.grid[x][y] = celltype
            if celltype == Celltype.SPAWN:
                self.spawn_pos.append((x, y))
            elif celltype == Celltype.SERVER:
                self.server_pos = (x, y)

    def get_cell(self, x: int, y: int):
        """Lấy kiểu ô tại tọa độ (x, y).

        Args:
            x (int): Hàng của ô cần lấy.
            y (int): Cột của ô cần lấy.

        Returns:
            int: Giá trị Celltype của ô (0-4).
            None: Nếu (x, y) ngoài phạm vi lưới.
        """
        if self.in_bounds(x, y):
            return self.grid[x][y]
        return None

    def get_neighbors(self, x: int, y: int) -> list:
        """Lấy danh sách các ô lân cận walkable của ô tại (x, y).

        Kiểm tra 4 hướng: phải, xuống, trái, lên. Chỉ trả về ô walkable
        (PATH/SERVER/SPAWN) — WALL và TOWER bị loại.

        Args:
            x (int): Hàng của ô hiện tại.
            y (int): Cột của ô hiện tại.

        Returns:
            list[tuple]: Danh sách (nx, ny) của các ô lân cận có thể đi qua.
        """
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        neighbors = []
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if self.is_walkable(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

    def is_tower_placeable(self, x: int, y: int) -> bool:
        """Kiểm tra có thể đặt tower tại (x, y) không.

        Điều kiện: ô phải là WALL VÀ không nằm trong vùng bảo vệ server
        (Chebyshev distance <= server_radius).

        Args:
            x (int): Hàng của ô cần kiểm tra.
            y (int): Cột của ô cần kiểm tra.

        Returns:
            bool: True nếu có thể đặt tower, False nếu không hợp lệ.
        """
        if not self.in_bounds(x, y):
            return False
        if self.grid[x][y] != Celltype.WALL:
            return False
        if self.server_pos:
            sx, sy = self.server_pos
            if abs(sx - x) <= self.server_radius and abs(sy - y) <= self.server_radius:
                return False
        return True

    def load_from_list(self, grid_list: list, level_config: dict) -> None:
        """Load bản đồ từ danh sách 2D (đọc từ JSON) và cấu hình level.

        Args:
            grid_list (list[list[int]]): Ma trận 2D giá trị Celltype từ JSON.
                Giá trị: 0=WALL, 1=PATH, 3=SERVER, 4=SPAWN.
            level_config (dict): Dict cấu hình level — đọc plateau_threshold
                và server_radius từ đây.

        Side effects:
            - Cập nhật PLATEAU_THRESHOLD và server_radius từ level_config.
            - Gọi set_cell() cho từng ô để cập nhật grid, spawn_pos, server_pos.
        """
        self.PLATEAU_THRESHOLD = level_config.get('plateau_threshold', 0.7)
        self.server_radius = level_config.get('server_radius', 5)
        for i in range(min(self.row, len(grid_list))):
            for j in range(min(self.col, len(grid_list[i]))):
                celltype = grid_list[i][j]
                self.set_cell(i, j, celltype)

    def get_all_path_cells(self) -> list:
        """Lấy danh sách tất cả ô walkable kết nối đến server bằng BFS.

        Dùng BFS từ server_pos để tìm tất cả ô PATH/SERVER/SPAWN có thể
        đến được từ server. Dùng để tính spawn weights.

        Returns:
            list[tuple]: Danh sách (row, col) của tất cả ô walkable kết nối.
        """
        visited = {}
        store = CustomQueue()
        store.enqueue(self.server_pos)
        visited[self.server_pos] = True
        while not store.is_empty():
            current = store.dequeue()
            for neibour in self.get_neighbors(*current):
                if not visited.get(neibour, False):
                    store.enqueue(neibour)
                    visited[neibour] = True
        return list(visited.keys())

    def get_spawn_weight(self) -> list:
        """Tính trọng số spawn cho từng ô PATH dựa trên khoảng cách đến server.

        Ô càng xa server → trọng số càng cao → dễ được chọn làm spawn hơn.
        Ô vượt ngưỡng PLATEAU_THRESHOLD × max_dist → trọng số = 1.0 (tối đa).
        Ô gần server hơn → trọng số = dist / max_dist (giảm dần).

        Returns:
            list[tuple]: Danh sách (weight, (row, col)) cho từng ô PATH.
                game.py dùng với random.choices(cells, weights=weights) để
                chọn vị trí spawn ngẫu nhiên có trọng số.

        Note:
            Công thức spawn weight từ CLAUDE.md:
                dist >= plateau_threshold × max_dist → weight = 1.0
                dist <  plateau_threshold × max_dist → weight = dist / max_dist
        """
        max_distance = 0
        list_path_cells = self.get_all_path_cells()
        list_spawn_weights = []

        def manhattan_distance(a, b):
            """Tính khoảng cách Manhattan giữa hai ô lưới.

            Args:
                a (tuple[int,int]): Tọa độ ô thứ nhất (row, col).
                b (tuple[int,int]): Tọa độ ô thứ hai (row, col).

            Returns:
                int: Tổng chênh lệch hàng và cột.
            """
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        for path in list_path_cells:
            dist = manhattan_distance(path, self.server_pos)
            if dist > max_distance:
                max_distance = dist
        for path in list_path_cells:
            dist = manhattan_distance(path, self.server_pos)
            if dist >= self.PLATEAU_THRESHOLD * max_distance:
                list_spawn_weights.append((1, path))
            else:
                list_spawn_weights.append((dist / max_distance if max_distance else 0, path))
        return list_spawn_weights
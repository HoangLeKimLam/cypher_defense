class Celltype:
    WALL = 0
    PATH=1
    TOWER =2
    SERVER=3
    SPAWN=4
class GridGraph:
    """
    Lưới ô vuông biểu diễn map game, mỗi ô có thể là tường, đường đi, tháp, server hoặc điểm spawn.
    """    
    def __init__(self, row, col):
        self.PLATEAU_THRESHOLD = 0.7
        self.server_radius = 5
        self.row = row
        self.col = col
        self.grid = [[Celltype.WALL for _ in range(col)] for _ in range(row)]
        self.spawn_pos= []
        self.server_pos= None
    def in_bounds(self, x, y):
        """Kiểm tra xem tọa độ (x, y) có nằm trong phạm vi lưới hay không."""
        return 0 <= x < self.row and 0 <= y < self.col
    def is_walkable(self, x, y):
        """Kiểm tra xem ô tại (x, y) có phải là đường đi hoặc server hay không, tức là malware có thể đi qua."""
        return self.in_bounds(x, y) and (self.grid[x][y] == Celltype.PATH or self.grid[x][y] == Celltype.SERVER)
    def set_cell(self, x, y, celltype):
        """Đặt loại ô tại tọa độ (x, y) và cập nhật thông tin spawn/server nếu cần thiết."""
        if self.in_bounds(x, y):
            self.grid[x][y] = celltype
            if celltype == Celltype.SPAWN:
                self.spawn_pos.append((x, y))
            elif celltype == Celltype.SERVER:
                self.server_pos = (x, y)
    def get_cell(self, x, y):
        """Lấy loại ô tại tọa độ (x, y). Trả về None nếu ngoài phạm vi."""
        if self.in_bounds(x, y):
            return self.grid[x][y]
        return None
    def get_neighbors(self, x, y):
        """Lấy danh sách các ô lân cận có thể đi qua của ô tại (x, y)."""
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        neighbors = []
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if self.is_walkable(nx, ny):
                neighbors.append((nx, ny))
        return neighbors
    def is_tower_placeable(self, x, y):
        """Kiểm tra xem có thể đặt tháp tại (x, y) hay không.
        Ô phải là tường và không được nằm trong phạm vi tùy chỉnh quanh server.
        """
        if not self.in_bounds(x, y):
            return False
        if self.grid[x][y] != Celltype.WALL:
            return False
        # Tháp không được đặt xung quanh server phạm vị tùy chỉnh theo yêu cầu
        if self.server_pos:
            sx, sy = self.server_pos
            if abs(sx - x) <= self.server_radius and abs(sy - y) <= self.server_radius:
                return False
        
        return True
    def load_from_list (self, grid_list,level_config):
        """Load bản đồ"""
        self.PLATEAU_THRESHOLD = level_config.get('plateau_threshold', 0.7)
        self.server_radius = level_config.get('server_radius', 5)
        for i in range(min(self.row, len(grid_list))):
            for j in range(min(self.col, len(grid_list[i]))):
                celltype = grid_list[i][j]
                self.set_cell(i, j, celltype)
    def get_all_path_cells(self):
        """Lấy danh sách tất cả các ô là đường đi trên bản đồ."""
        path_cells = []
        for i in range(self.row):
            for j in range(self.col):
                if self.grid[i][j] == Celltype.PATH:
                    path_cells.append((i, j))
        return path_cells
    def get_spawn_weight(self):
        """Cài đặt trọng số spawn phục vụ mục đích xác suất cổng spawn sinh ra dựa trên khoảng cách đến server.
        Ô càng xa server càng có trọng số spawn cao, nhưng chỉ những ô nằm trong phần trên của khoảng cách tối đa mới được tính trọng số spawn.
        """
        max_distance = 0
        list_path_cells = self.get_all_path_cells()
        list_spawn_weights = []
        def manhattan_distance(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])
        for path in list_path_cells:
            dist= manhattan_distance(path, self.server_pos)
            if dist > max_distance:
                max_distance = dist
        for path in list_path_cells:
            dist= manhattan_distance(path, self.server_pos)
            if dist>=self.PLATEAU_THRESHOLD * max_distance:
                list_spawn_weights.append((1, path))
            else:
                list_spawn_weights.append((dist/max_distance if max_distance else 0, path))
        return list_spawn_weights
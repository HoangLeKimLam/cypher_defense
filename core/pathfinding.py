
# core/pathfinding.py
# A* và BFS — trả về CustomLinkedList chứa path
from core.graph import GridGraph, Celltype
from core.data_structures import CustomLinkedList, CustomQueue, CustomMinHeap


def heuristic(r1: int, c1: int, r2: int, c2: int) -> int:
    """Tính Manhattan distance — ước tính chi phí còn lại trong A*.

    Args:
        r1 (int): Hàng vị trí hiện tại.
        c1 (int): Cột vị trí hiện tại.
        r2 (int): Hàng vị trí đích.
        c2 (int): Cột vị trí đích.

    Returns:
        int: Khoảng cách Manhattan |r1-r2| + |c1-c2|.

    Note:
        Dùng Manhattan distance vì malware chỉ đi 4 hướng (không chéo).
        Heuristic này admissible (không ước tính quá) → A* luôn tìm đường ngắn nhất.
    """
    return abs(r1 - r2) + abs(c1 - c2)


def reconstruct_path(came_from: dict,
                     start: tuple,
                     goal: tuple) -> CustomLinkedList:
    """Truy vết ngược từ goal về start và trả về CustomLinkedList theo thứ tự xuôi.

    Args:
        came_from (dict): {(r,c): (r_prev, c_prev)} — bản đồ truy vết từ A*/BFS.
        start (tuple): Vị trí bắt đầu (row, col).
        goal (tuple): Vị trí đích (row, col).

    Returns:
        CustomLinkedList: Path từ START đến GOAL theo thứ tự đi, bao gồm cả start.

    Note:
        Dùng append_head() để xây path theo thứ tự xuôi khi truy vết ngược.
        Cả A* lẫn BFS đều gọi hàm này sau khi tìm xong đường.
    """
    path = CustomLinkedList()
    cur = goal
    while cur != start:
        path.append_head(cur)
        cur = came_from[cur]
    path.append_head(start)
    return path


def astar(graph: GridGraph,
          start: tuple,
          goal: tuple) -> CustomLinkedList:
    """Tìm đường ngắn nhất từ start đến goal dùng thuật toán A*.

    Dùng CustomMinHeap làm priority queue với f = g + h.
    Heuristic: Manhattan distance đến goal.

    Args:
        graph (GridGraph): Bản đồ lưới đang dùng trong game.
        start (tuple): Vị trí (row, col) spawn malware.
        goal (tuple): Vị trí (row, col) đích (thường là server_pos).

    Returns:
        CustomLinkedList: Path từ start đến goal theo thứ tự đi.
            CustomLinkedList rỗng nếu không tìm được đường.

    Usage:
        Trojan/Worm gọi khi spawn và khi bản đồ thay đổi::

            malware.path = astar(graph, spawn_pos, graph.server_pos)
    """
    store = CustomMinHeap()
    g = {start: 0}
    h = heuristic(*start, *goal)
    f = g[start] + h
    store.push((f, start))
    came_from = {}

    while not store.is_empty():
        f, current = store.pop()
        if current == goal:
            return reconstruct_path(came_from, start, goal)
        for neighbor in graph.get_neighbors(*current):
            g_score = g[current] + 1
            if neighbor not in g or g_score < g.get(neighbor, float('inf')):
                came_from[neighbor] = current
                h = heuristic(*neighbor, *goal)
                f = g_score + h
                g[neighbor] = g_score
                store.push((f, neighbor))
    return CustomLinkedList()   # không tìm được đường


def bfs(graph: GridGraph,
        start: tuple,
        goal: tuple) -> CustomLinkedList:
    """Tìm đường ngắn nhất từ start đến goal dùng BFS (không có heuristic).

    Dùng CustomQueue thay CustomMinHeap — mỗi bước đi có chi phí bằng nhau
    nên BFS đảm bảo tìm đường ngắn nhất mà không cần heuristic.

    Args:
        graph (GridGraph): Bản đồ lưới đang dùng trong game.
        start (tuple): Vị trí (row, col) bắt đầu.
        goal (tuple): Vị trí (row, col) đích (thường là ô PATH kề tower).

    Returns:
        CustomLinkedList: Path từ start đến goal theo thứ tự đi.
            CustomLinkedList rỗng nếu không tìm được đường.

    Usage:
        Spyware/Ransomware gọi với goal = ô PATH kề tower gần nhất::

            malware.path = bfs(graph, malware.pos, attack_pos)
    """
    store = CustomQueue()
    store.enqueue(start)
    came_from = {}
    visited = set()
    visited.add(start)
    while not store.is_empty():
        current = store.dequeue()
        if current == goal:
            return reconstruct_path(came_from, start, goal)
        for neighbor in graph.get_neighbors(*current):
            if neighbor not in visited:
                visited.add(neighbor)
                came_from[neighbor] = current
                store.enqueue(neighbor)
    return CustomLinkedList()   # không tìm được đường


def find_nearest_tower(graph: GridGraph,
                       start: tuple) -> tuple:
    """Dùng BFS tìm ô PATH kề tower gần nhất từ vị trí start.

    BFS lan rộng từ start trên các ô walkable. Khi tìm thấy ô có ít nhất
    một ô láng giềng là TOWER → trả về ô PATH đó (không phải ô TOWER).
    Spyware/Ransomware dùng ô này làm goal của BFS path.

    Args:
        graph (GridGraph): Bản đồ lưới đang dùng trong game.
        start (tuple): Vị trí (row, col) hiện tại của Spyware/Ransomware.

    Returns:
        tuple: Vị trí (row, col) ô PATH kề tower gần nhất.
            None nếu không có tower nào trên map.

    Note:
        Trả về ô PATH kề tower (không phải ô TOWER) vì malware không thể
        đứng trên TOWER — chỉ đứng kề để tấn công.
    """
    store = CustomQueue()
    store.enqueue(start)
    visited = set()
    visited.add(start)
    while not store.is_empty():
        current = store.dequeue()
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        for dx, dy in directions:
            nx, ny = current[0] + dx, current[1] + dy
            if graph.get_cell(nx, ny) == Celltype.TOWER:
                return current
        for neighbor in graph.get_neighbors(*current):
            if neighbor not in visited:
                visited.add(neighbor)
                store.enqueue(neighbor)
    return None   # không tìm được tháp nào

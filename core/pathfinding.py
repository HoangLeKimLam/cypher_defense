
# core/pathfinding.py
# A* và BFS — trả về CustomLinkedList chứa path
from core.graph import GridGraph, Celltype
from core.data_structures import CustomLinkedList, CustomQueue, CustomMinHeap


def heuristic(r1: int, c1: int, r2: int, c2: int) -> int:
    """
    Tính Manhattan distance — ước tính khoảng cách còn lại.
    Input : r1,c1 = vị trí hiện tại, r2,c2 = vị trí đích
    Output: int — khoảng cách Manhattan
    """
    return abs(r1 - r2) + abs(c1 - c2)
  



def reconstruct_path(came_from: dict,
                     start: tuple,
                     goal: tuple) -> CustomLinkedList:
    """
    Truy vết ngược từ goal về start, trả về LinkedList xuôi.
    Input : came_from = {(r,c): (r_prev, c_prev), ...}
            start, goal = tuple (r,c)
    Output: CustomLinkedList — path từ START đến GOAL (theo thứ tự đi)
    Dùng khi: cả A* lẫn BFS gọi sau khi tìm xong
    """
    path= CustomLinkedList()
    cur= goal
    while cur != start:
        path.append_head(cur)
        cur= came_from[cur]
    path.append_head(start)
    return path
    

def astar(graph: GridGraph,
          start: tuple,
          goal: tuple) -> CustomLinkedList:
    
    """
    Tìm đường ngắn nhất từ start đến goal dùng A*.
    Input : graph — GridGraph đang dùng trong game
            start — tuple (r,c) vị trí spawn quái
            goal  — tuple (r,c) vị trí Server
    Output: CustomLinkedList chứa các (r,c) từ start→goal
            hoặc CustomLinkedList rỗng nếu không tìm được đường

    Dùng khi:
      - Lúc spawn Malware loại TROJAN/WORM:
            malware.path = astar(grid, spawn_pos, server_pos)
      - Lúc người chơi đặt Partition (tường tạm) → gọi lại cho tất cả quái sống
    

    
    """
    store= CustomMinHeap()
    g= {start: 0}
    h= heuristic(*start, *goal)
    f= g[start]+h
    store.push((f, start))
    came_from={}

    while not store.is_empty():
        f, current= store.pop()
        if current == goal:
            return reconstruct_path(came_from, start, goal)
        for neighbor in graph.get_neighbors(*current):
            g_score= g[current]+1
            if neighbor not in g or g_score < g.get(neighbor, float('inf')):
                came_from[neighbor]= current
                h= heuristic(*neighbor, *goal)
                f= g_score+h
                g[neighbor]= g_score
                store.push((f, neighbor))
    return CustomLinkedList()   # không tìm được đường
        
  



def bfs(graph: GridGraph,
        start: tuple,
        goal: tuple) -> CustomLinkedList:
    
    """
    Tìm đường ngắn nhất dùng BFS (không có heuristic).
    Input/Output: giống astar()

    Dùng khi:
      - Malware loại SPYWARE/RANSOMWARE tìm THÁP gần nhất
        (goal lúc này là vị trí tháp gần nhất, không phải Server)
      - Có thể dùng BFS thay astar() để tìm tháp trong tầm

    Cấu trúc dùng: CustomQueue (thay MinHeap)

    
    """
    store= CustomQueue()
    store.enqueue(start)
    came_from={}
    visited= set()
    visited.add(start)
    while not store.is_empty():
        current=store.dequeue()
        if current==goal:
            return reconstruct_path(came_from, start, goal)
        for neighbor in graph.get_neighbors(*current):
            if neighbor not in visited:
                visited.add(neighbor)
                came_from[neighbor]= current
                store.enqueue(neighbor)
    return CustomLinkedList()   # không tìm được đường
    


def find_nearest_tower(graph: GridGraph,
                       start: tuple,
  ) -> tuple:
    
    """
    Dùng BFS tìm tháp GẦN NHẤT từ vị trí start.
    Input : graph — GridGraph
            start — vị trí hiện tại của Spyware/Ransomware (tuple (r,c))
    Output: tuple (r,c) của tháp gần nhất, hoặc None nếu không có tháp

    Dùng khi: Spyware/Ransomware mỗi khi cần chọn mục tiêu tấn công

    
    """

    store= CustomQueue()
    store.enqueue(start)
    visited= set()
    visited.add(start)
    while not store.is_empty():
        current=store.dequeue()
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

    
   

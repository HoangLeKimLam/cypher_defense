from core.graph import GridGraph, Celltype
from core.data_structures import CustomQueue


def shock_spread(self , graph: GridGraph, pos: tuple[int, int]) -> list[tuple[int, int]]:
        """Tính toán các ô bị ảnh hưởng bởi hiệu ứng shock khi một Malware bị tiêu diệt.

        Args:
            self (LightSpy): Đối tượng LightSpy gọi hàm này (dùng self.graph nội bộ).
            graph (GridGraph): Đồ thị lưới của bản đồ, dùng để xác định ô kề nhau.
            pos (tuple[int, int]): Tọa độ ô lưới nơi Tower bị điện giật (row, col).

        Returns:
            list[tuple[int, int]]: Danh sách tọa độ các ô bị ảnh hưởng bởi shock.
        """
        affected_cells = set()  # Dùng set để tránh trùng lặp
        affected_cells.add(pos)
        queue = CustomQueue()
        queue.enqueue(pos)
        while not queue.is_empty():
            current = queue.dequeue()
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            if self.graph.get_cell(*current) == Celltype.TOWER:
                for dr, dc in directions:
                    neighbor = (current[0] + dr, current[1] + dc)
                    if self.graph.in_bounds(*neighbor) and neighbor not in affected_cells:
                        affected_cells.add(neighbor)
                        queue.enqueue(neighbor)
            else:
                for dr, dc in directions:
                    neighbor = (current[0] + dr, current[1] + dc)
                    if self.graph.in_bounds(*neighbor) and neighbor not in affected_cells and self.graph.get_cell(*neighbor) == Celltype.TOWER:
                        affected_cells.add(neighbor)
                        queue.enqueue(neighbor)
        return list(affected_cells)       
                
        
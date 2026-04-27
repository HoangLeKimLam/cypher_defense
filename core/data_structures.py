class Node:
    """Đại diện cho một node trong linked list.

    Attributes:
        value: Dữ liệu lưu trong node (thường là tuple như (row, col)).
        next (Node | None): Con trỏ tới node tiếp theo (None nếu là node cuối).

    Usage:
        Không dùng trực tiếp — CustomLinkedList quản lý Node nội bộ::

            linked = CustomLinkedList()
            linked.append_tail((3, 5))
    """
    def __init__(self, value):
        """Khởi tạo Node với giá trị cho trước.

        Args:
            value: Dữ liệu cần lưu (thường là tuple (row, col) cho pathfinding).
        """
        self.value = value
        self.next = None


class CustomLinkedList:
    """Linked List tự cài đặt (singly linked list) — dùng để lưu path trong game.

    Dùng làm hàng đợi path cho Malware: reconstruct_path() thêm vào tail,
    Malware.update() pop từ head từng ô một theo thứ tự đi.

    Attributes:
        head (Node | None): Node đầu danh sách.
        tail (Node | None): Node cuối danh sách.
        size (int): Số phần tử hiện tại.

    Usage:
        astar() và bfs() trả về CustomLinkedList chứa path từ start đến goal::

            path = astar(graph, spawn_pos, server_pos)
            next_cell = path.pop_head()  # lấy ô tiếp theo để đi
    """

    def __init__(self):
        """Khởi tạo LinkedList rỗng."""
        self.head = None
        self.tail = None
        self.size = 0

    def append_head(self, value: tuple) -> None:
        """Thêm phần tử vào đầu danh sách.

        Args:
            value (tuple): Dữ liệu cần thêm (thường là (row, col)).

        Note:
            Độ phức tạp O(1). reconstruct_path() dùng append_head() để xây path
            theo thứ tự xuôi (truy vết ngược từ goal → start).
        """
        new_node = Node(value)
        new_node.next = self.head

        if self.head is None:
            self.tail = new_node

        self.head = new_node
        self.size += 1

    def append_tail(self, value: tuple) -> None:
        """Thêm phần tử vào cuối danh sách.

        Args:
            value (tuple): Dữ liệu cần thêm (thường là (row, col)).

        Note:
            Độ phức tạp O(1) nhờ con trỏ tail.
        """
        new_node = Node(value)

        if self.head is None:
            self.head = new_node
            self.tail = new_node
        else:
            self.tail.next = new_node
            self.tail = new_node

        self.size += 1

    def pop_head(self):
        """Lấy và xóa phần tử đầu danh sách.

        Returns:
            tuple: Giá trị của node đầu (thường là (row, col)) nếu tồn tại.
            None: Nếu danh sách rỗng.

        Note:
            Độ phức tạp O(1). Malware.update() gọi mỗi bước di chuyển.
        """
        if self.head is None:
            return None

        value = self.head.value
        self.head = self.head.next
        self.size -= 1

        if self.head is None:
            self.tail = None

        return value

    def is_empty(self) -> bool:
        """Kiểm tra danh sách có rỗng không.

        Returns:
            bool: True nếu size == 0, False nếu còn phần tử.
        """
        return self.size == 0

    def __len__(self) -> int:
        """Trả về số phần tử trong danh sách.

        Returns:
            int: Giá trị self.size.
        """
        return self.size


class CustomStack:
    """Stack (LIFO) tự cài đặt — dùng để lưu lịch sử xây tower (Ctrl+Z).

    Nguyên lý: push vào cuối list, pop từ cuối list → O(1) cả hai chiều.
    game.py dùng để lưu mỗi action xây tower; Ctrl+Z gọi pop() để hoàn tác.

    Attributes:
        data (list): Danh sách nội bộ lưu các phần tử.

    Usage:
        game.py lưu action xây tower và hoàn tác::

            undo_stack = CustomStack()
            undo_stack.push({"pos": (row, col), "tower": tower, "cost": cost})
            action = undo_stack.pop()  # Ctrl+Z
    """

    def __init__(self):
        """Khởi tạo Stack rỗng."""
        self.data = []

    def push(self, value) -> None:
        """Thêm phần tử vào đỉnh stack.

        Args:
            value: Dữ liệu cần push (bất kỳ kiểu nào).

        Note:
            Độ phức tạp O(1) — append vào cuối list Python.
        """
        self.data.append(value)

    def pop(self):
        """Lấy và xóa phần tử ở đỉnh stack.

        Returns:
            Phần tử ở đỉnh (LIFO) nếu stack còn phần tử.
            None nếu stack rỗng.

        Note:
            Độ phức tạp O(1).
        """
        if len(self.data) == 0:
            return None
        return self.data.pop()

    def peek(self):
        """Xem phần tử đỉnh stack nhưng không xóa.

        Returns:
            Phần tử ở đỉnh nếu stack còn phần tử.
            None nếu stack rỗng.
        """
        if len(self.data) == 0:
            return None
        return self.data[-1]

    def is_empty(self) -> bool:
        """Kiểm tra stack có rỗng không.

        Returns:
            bool: True nếu không có phần tử nào, False nếu còn phần tử.
        """
        return len(self.data) == 0

    def __len__(self) -> int:
        """Trả về số phần tử trong stack.

        Returns:
            int: Số lượng phần tử hiện tại.
        """
        return len(self.data)


class CustomQueue:
    """Queue (FIFO) tối ưu bằng kỹ thuật lazy slicing — dùng cho BFS và spawn queue.

    Không dùng pop(0) (O(n)). Thay vào đó dùng pointer _front để track vị trí đầu.
    Khi _front > len/2 thì slice lại list để thu hồi bộ nhớ (amortized O(1)).

    Attributes:
        _data (list): Danh sách nội bộ lưu các phần tử.
        _front (int): Chỉ số phần tử đầu hàng đợi trong _data.

    Usage:
        BFS trong pathfinding.py và SpatialHash::

            queue = CustomQueue()
            queue.enqueue((3, 5))
            cell = queue.dequeue()
    """

    def __init__(self):
        """Khởi tạo Queue rỗng."""
        self._data = []
        self._front = 0

    def enqueue(self, value) -> None:
        """Thêm phần tử vào cuối queue.

        Args:
            value: Dữ liệu cần thêm (bất kỳ kiểu nào).

        Note:
            Độ phức tạp O(1) — append vào cuối list Python.
        """
        self._data.append(value)

    def dequeue(self):
        """Lấy và xóa phần tử đầu queue.

        Returns:
            Phần tử đầu hàng đợi (FIFO) nếu còn phần tử.
            None nếu queue rỗng.

        Note:
            Amortized O(1) — dùng _front pointer thay vì pop(0).
            Khi _front > len(_data)//2, slice lại list để thu hồi bộ nhớ.
        """
        if self.is_empty():
            return None

        value = self._data[self._front]
        self._front += 1

        # Tối ưu bộ nhớ: thu hồi khi _front đã qua nửa list
        if self._front > len(self._data) // 2:
            self._data = self._data[self._front:]
            self._front = 0

        return value

    def is_empty(self) -> bool:
        """Kiểm tra queue có rỗng không.

        Returns:
            bool: True nếu không có phần tử nào, False nếu còn phần tử.
        """
        return self._front >= len(self._data)

    def peek(self):
        """Xem phần tử đầu queue nhưng không xóa.

        Returns:
            Phần tử đầu hàng đợi nếu còn phần tử.
            None nếu queue rỗng.
        """
        if self.is_empty():
            return None
        return self._data[self._front]

    def __len__(self) -> int:
        """Trả về số phần tử trong queue.

        Returns:
            int: Số lượng phần tử hiện tại (chưa dequeue).
        """
        return len(self._data) - self._front


class CustomMinHeap:
    """Min Heap (Priority Queue) tự cài đặt — dùng cho A* và Tower targeting.

    Lưu dưới dạng array-based binary heap: parent[i] <= children[i].
    Phần tử lưu dạng tuple (priority, data) — so sánh theo priority.

    Attributes:
        _data (list): Danh sách nội bộ lưu các tuple (priority, data).

    Usage:
        A* dùng để chọn ô có f-score nhỏ nhất, Tower dùng để chọn target
        có khoảng cách đến server nhỏ nhất::

            heap = CustomMinHeap()
            heap.push((f_score, (row, col)))
            priority, cell = heap.pop()
    """

    def __init__(self):
        """Khởi tạo MinHeap rỗng."""
        self._data = []

    def _parent(self, i: int) -> int:
        """Trả về chỉ số node cha của node tại i."""
        return (i - 1) // 2

    def _left(self, i: int) -> int:
        """Trả về chỉ số node con trái của node tại i."""
        return 2 * i + 1

    def _right(self, i: int) -> int:
        """Trả về chỉ số node con phải của node tại i."""
        return 2 * i + 2

    def _swap(self, i: int, j: int) -> None:
        """Hoán đổi hai phần tử tại chỉ số i và j trong _data."""
        self._data[i], self._data[j] = self._data[j], self._data[i]

    def _bubble_up(self, i: int) -> None:
        """Đẩy phần tử tại i lên đúng vị trí trong heap (sau push).

        Args:
            i (int): Chỉ số phần tử vừa thêm vào.
        """
        while i > 0:
            parent = self._parent(i)
            if self._data[i][0] < self._data[parent][0]:
                self._swap(i, parent)
                i = parent
            else:
                break

    def _bubble_down(self, i: int) -> None:
        """Đẩy phần tử tại i xuống đúng vị trí trong heap (sau pop).

        Args:
            i (int): Chỉ số phần tử cần sắp xếp xuống (thường là 0).
        """
        n = len(self._data)
        while True:
            left = self._left(i)
            right = self._right(i)
            smallest = i

            if left < n and self._data[left][0] < self._data[smallest][0]:
                smallest = left

            if right < n and self._data[right][0] < self._data[smallest][0]:
                smallest = right

            if smallest == i:
                break

            self._swap(i, smallest)
            i = smallest

    def push(self, value: tuple) -> None:
        """Thêm phần tử vào heap và duy trì tính chất heap.

        Args:
            value (tuple): (priority, data) — so sánh theo priority[0].

        Note:
            Độ phức tạp O(log n).
        """
        self._data.append(value)
        self._bubble_up(len(self._data) - 1)

    def pop(self):
        """Lấy và xóa phần tử có priority nhỏ nhất.

        Returns:
            tuple: (priority, data) của phần tử nhỏ nhất.
            None: Nếu heap rỗng.

        Note:
            Độ phức tạp O(log n).
        """
        if len(self._data) == 0:
            return None

        self._swap(0, len(self._data) - 1)
        min_value = self._data.pop()
        self._bubble_down(0)

        return min_value

    def peek(self):
        """Xem phần tử có priority nhỏ nhất nhưng không xóa.

        Returns:
            tuple: (priority, data) của phần tử đỉnh heap.
            None: Nếu heap rỗng.
        """
        if len(self._data) == 0:
            return None
        return self._data[0]

    def is_empty(self) -> bool:
        """Kiểm tra heap có rỗng không.

        Returns:
            bool: True nếu không có phần tử nào.
        """
        return len(self._data) == 0

    def __len__(self) -> int:
        """Trả về số phần tử trong heap.

        Returns:
            int: Số lượng phần tử hiện tại.
        """
        return len(self._data)


class CustomMaxHeap:
    """Max Heap xây dựng dựa trên CustomMinHeap — dùng cho Tower targeting "max_hp".

    Ý tưởng: đảo dấu priority (x → -x) khi push/pop, dùng lại toàn bộ
    logic sắp xếp của MinHeap.

    Attributes:
        _heap (CustomMinHeap): MinHeap nội bộ lưu các tuple (-priority, data).

    Usage:
        Tower với targeting="max_hp" dùng để chọn malware có HP nhiều nhất::

            heap = CustomMaxHeap()
            heap.push((malware.hp, malware))
            priority, target = heap.pop()
    """

    def __init__(self):
        """Khởi tạo MaxHeap rỗng (bọc MinHeap nội bộ)."""
        self._heap = CustomMinHeap()

    def push(self, value: tuple) -> None:
        """Thêm phần tử vào heap với priority đảo dấu.

        Args:
            value (tuple): (priority, data) — priority sẽ được lưu âm trong MinHeap.
        """
        self._heap.push((-value[0], value[1]))

    def pop(self):
        """Lấy và xóa phần tử có priority lớn nhất.

        Returns:
            tuple: (priority, data) với priority dương (đã đảo lại dấu).
            None: Nếu heap rỗng.
        """
        result = self._heap.pop()
        return (-result[0], result[1]) if result else None

    def peek(self):
        """Xem phần tử có priority lớn nhất nhưng không xóa.

        Returns:
            tuple: (priority, data) với priority dương.
            None: Nếu heap rỗng.
        """
        result = self._heap.peek()
        return (-result[0], result[1]) if result else None

    def is_empty(self) -> bool:
        """Kiểm tra heap có rỗng không.

        Returns:
            bool: True nếu không có phần tử nào.
        """
        return self._heap.is_empty()

    def __len__(self) -> int:
        """Trả về số phần tử trong heap.

        Returns:
            int: Số lượng phần tử hiện tại.
        """
        return len(self._heap)
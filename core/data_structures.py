class Node:
    """
    Đại diện cho một node trong linked list.

    Attributes:
        value: Dữ liệu lưu trong node (thường là tuple như (row, col))
        next : Con trỏ tới node tiếp theo (None nếu là node cuối)
    """
    def __init__(self, value):
        self.value = value
        self.next = None


class CustomLinkedList:
    """
    Linked List tự cài đặt (singly linked list).

    Attributes:
        head: Node đầu danh sách
        tail: Node cuối danh sách
        size: Số phần tử hiện tại

    Methods:
        append_head(value): thêm vào đầu
        append_tail(value): thêm vào cuối
        pop_head(): lấy và xóa phần tử đầu
        is_empty(): kiểm tra rỗng
        __len__(): trả về size
    """

    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0

    def append_head(self, value: tuple):
        """
        Thêm phần tử vào đầu danh sách.

        Input:
            value (tuple): dữ liệu cần thêm

        Output:
            None

        Time complexity:
            O(1)
        """
        new_node = Node(value)
        new_node.next = self.head

        if self.head is None:
            self.tail = new_node

        self.head = new_node
        self.size += 1

    def append_tail(self, value: tuple):
        """
        Thêm phần tử vào cuối danh sách.

        Input:
            value (tuple)

        Output:
            None

        Time complexity:
            O(1)
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
        """
        Lấy và xóa phần tử đầu danh sách.

        Input:
            None

        Output:
            value (tuple) nếu tồn tại, None nếu rỗng

        Time complexity:
            O(1)
        """
        if self.head is None:
            return None

        value = self.head.value
        self.head = self.head.next
        self.size -= 1

        if self.head is None:
            self.tail = None

        return value

    def is_empty(self):
        """
        Kiểm tra danh sách có rỗng không.

        Output:
            bool
        """
        return self.size == 0

    def __len__(self):
        """
        Trả về số phần tử trong danh sách.
        """
        return self.size


class CustomStack:
    """
    Stack (LIFO) 
    Nguyên lý:
        push vào cuối list
        pop từ cuối list

    Methods:
        push(value)
        pop()
        peek()
        is_empty()
        __len__()
    """

    def __init__(self):
        self.data = []

    def push(self, value):
        """
        Thêm phần tử vào stack.

        Input:
            value: bất kỳ

        Output:
            None
        """
        self.data.append(value)

    def pop(self):
        """
        Lấy và xóa phần tử top.

        Output:
            value hoặc None nếu rỗng

        Time:
            O(1)
        """
        if len(self.data) == 0:
            return None
        return self.data.pop()

    def peek(self):
        """
        Xem phần tử top nhưng không xóa.

        Output:
            value hoặc None
        """
        if len(self.data) == 0:
            return None
        return self.data[-1]

    def is_empty(self):
        """
        Kiểm tra stack rỗng.
        """
        return len(self.data) == 0

    def __len__(self):
        return len(self.data)


class CustomQueue:
    """
    Queue (FIFO) tối ưu bằng kỹ thuật lazy slicing.
    Ý tưởng:
        - Không pop đầu list (O(n))
        - Dùng pointer _front để track vị trí
        - Khi _front quá lớn thì slice lại list

    Methods:
        enqueue(value)
        dequeue()
        peek()
        is_empty()
        __len__()
    """

    def __init__(self):
        self._data = []
        self._front = 0

    def enqueue(self, value):
        """
        Thêm phần tử vào cuối queue.

        Input:
            value

        Output:
            None
        """
        self._data.append(value)

    def dequeue(self):
        """
        Lấy và xóa phần tử đầu queue.

        Output:
            value hoặc None nếu rỗng

        Amortized time:
            O(1)
        """
        if self.is_empty():
            return None

        value = self._data[self._front]
        self._front += 1

        # Tối ưu bộ nhớ
        if self._front > len(self._data) // 2:
            self._data = self._data[self._front:]
            self._front = 0

        return value

    def is_empty(self):
        return self._front >= len(self._data)

    def peek(self):
        """
        Xem phần tử đầu queue.
        """
        if self.is_empty():
            return None
        return self._data[self._front]

    def __len__(self):
        return len(self._data) - self._front


class CustomMinHeap:
    """
    Min Heap (Priority Queue).

    Lưu dưới dạng list:
        parent < children

    Value lưu dạng tuple:
        (priority, data)

    Methods:
        push(value)
        pop()
        peek()
        is_empty()
    """

    def __init__(self):
        self._data = []

    def _parent(self, i):
        return (i - 1) // 2

    def _left(self, i):
        return 2 * i + 1

    def _right(self, i):
        return 2 * i + 2

    def _swap(self, i, j):
        self._data[i], self._data[j] = self._data[j], self._data[i]

    def _bubble_up(self, i):
        while i > 0:
            parent = self._parent(i)
            if self._data[i][0] < self._data[parent][0]:
                self._swap(i, parent)
                i = parent
            else:
                break

    def _bubble_down(self, i):
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

    def push(self, value: tuple):
        """
        Thêm phần tử vào heap.
        Input:
            value (priority, data)

        Output:
            None
        """
        self._data.append(value)
        self._bubble_up(len(self._data) - 1)

    def pop(self):
        """
        Lấy phần tử nhỏ nhất.
        Output:
            tuple hoặc None
        """
        if len(self._data) == 0:
            return None

        self._swap(0, len(self._data) - 1)
        min_value = self._data.pop()
        self._bubble_down(0)

        return min_value

    def peek(self):
        """
        Xem phần tử nhỏ nhất.
        """
        if len(self._data) == 0:
            return None
        return self._data[0]

    def is_empty(self):
        return len(self._data) == 0

    def __len__(self):
        return len(self._data)


class CustomMaxHeap:
    """
    Max Heap xây dựng dựa trên MinHeap.

    Ý tưởng:
        - Đảo dấu priority (x → -x)
        - Dùng lại toàn bộ logic của MinHeap

    Methods:
        push(value)
        pop()
        peek()
    """

    def __init__(self):
        self._heap = CustomMinHeap()

    def push(self, value: tuple):
        """
        Input:
            value (priority, data)
        """
        self._heap.push((-value[0], value[1]))

    def pop(self):
        """
        Output:
            (priority, data) hoặc None
        """
        result = self._heap.pop()
        return (-result[0], result[1]) if result else None

    def peek(self):
        result = self._heap.peek()
        return (-result[0], result[1]) if result else None

    def is_empty(self):
        return self._heap.is_empty()

    def __len__(self):
        return len(self._heap)
# systems/spatial_hash.py
# CustomSpatialHash — tìm kiếm Malware trong tầm bắn của Tower.
#
# VẤN ĐỀ: Nếu dùng vòng lặp đơn giản, mỗi Tower phải kiểm tra TẤT CẢ Malware
#          → O(towers × malwares) mỗi frame → chậm khi có nhiều entity.
#
# GIẢI PHÁP: Chia lưới thành các "bucket" (vùng ô). Mỗi bucket là 1 key trong dict.
#            Tower chỉ hỏi các bucket gần nó → gần O(1) trung bình.
#
# CẤU TRÚC:
#   - Lõi: Python dict{}  — key=(brow, bcol), value=list[entity]
#   - "Custom" ở đây nghĩa là: các method insert/remove/update_position/query_range
#     được thiết kế riêng cho bài toán spatial lookup trong game, không có sẵn
#     trong dict thuần. Dict chỉ là phương tiện lưu trữ — logic là của class này.


import settings


class SpatialHash:
    """Spatial hash map dùng Python dict làm lõi lưu trữ.

    Chia lưới thành các "bucket" (vùng ô vuông bucket_cell × bucket_cell).
    Mỗi bucket là một key (brow, bcol) trong dict. Khi Tower hỏi "ai trong tầm?",
    chỉ cần kiểm tra vài bucket quanh Tower thay vì toàn bộ malware.

    Attributes:
        _bucket_cell (int): Số ô lưới mỗi chiều của 1 bucket. Mặc định 2 → vùng 2×2 ô.
        _bucket_rows (int): Số bucket theo chiều dọc = grid_rows // bucket_cell.
        _bucket_cols (int): Số bucket theo chiều ngang = grid_cols // bucket_cell.
        _buckets (dict): {(brow, bcol): list[entity]} — chỉ chứa bucket có ít nhất 1 entity.

    Usage:
        game.py khởi tạo một lần khi load level, sau đó cập nhật mỗi frame::

            spatial_hash = SpatialHash(grid_rows=15, grid_cols=15, bucket_cell_size=2)

            # Khi malware spawn:
            spatial_hash.insert(malware)

            # Mỗi frame, sau malware.update(dt):
            spatial_hash.update_position(malware, old_pos)

            # Tower hỏi danh sách trong tầm:
            candidates = spatial_hash.query_range(tower.pos, tower.range)

            # Khi malware chết hoặc đến server:
            spatial_hash.remove(malware)

    Note:
        Dict dùng tuple (brow, bcol) làm key — không có collision giả tạo như hash
        dựa trên modulo. Hai bucket ở góc đối nhau luôn có key khác nhau.
    """

    def __init__(self, grid_rows: int, grid_cols: int, bucket_cell_size: int = 2):
        """Khởi tạo SpatialHash với dict rỗng.

        Args:
            grid_rows (int): Số hàng thực tế của map — đọc từ config["rows"] trong JSON.
                Không dùng settings.GRID_ROWS vì các level có kích thước khác nhau.
            grid_cols (int): Số cột thực tế của map — đọc từ config["cols"] trong JSON.
            bucket_cell_size (int): Số ô lưới mỗi chiều của 1 bucket. Mặc định 2.
                Bucket nhỏ → nhiều bucket hơn, query chính xác hơn nhưng tốn bộ nhớ hơn.
                Bucket lớn → ít bucket, query nhanh hơn nhưng lọc nhiều false-positive hơn.

        Note:
            Truyền grid_rows/cols từ JSON thay vì settings để hỗ trợ map nhiều kích thước.
            Nếu dùng settings cứng → _bucket_rows/_bucket_cols sai → query_range() clamp
            sai biên → bỏ sót malware ở rìa map.

        Example::

            # map 15×15, bucket_cell=2 → _bucket_rows=7, _bucket_cols=7
            SpatialHash(15, 15, 2)

            # map 20×30, bucket_cell=2 → _bucket_rows=10, _bucket_cols=15
            SpatialHash(20, 30, 2)
        """
        self._bucket_cell = bucket_cell_size
        self._bucket_rows = max(1, grid_rows // bucket_cell_size)
        self._bucket_cols = max(1, grid_cols // bucket_cell_size)
        self._buckets = {}
        pass

    # ------------------------------------------------------------------
    # HÀM NỘI BỘ
    # ------------------------------------------------------------------

    def _hash(self, row: int, col: int) -> tuple:
        """Ánh xạ tọa độ ô lưới (row, col) → key bucket (brow, bcol).

        Đây là "hàm hash" của class — quyết định entity ở ô nào thuộc bucket nào.

        Args:
            row (int): Hàng ô lưới.
            col (int): Cột ô lưới.

        Returns:
            tuple: (brow, bcol) — key dict cho bucket chứa ô (row, col).

        Example::

            # bucket_cell_size = 2
            _hash(0, 0) → (0, 0)   # ô (0,0)(0,1)(1,0)(1,1) cùng 1 bucket
            _hash(0, 1) → (0, 0)   # 1//2 = 0
            _hash(2, 0) → (1, 0)   # 2//2 = 1, sang bucket mới
            _hash(3, 7) → (1, 3)   # 3//2=1, 7//2=3

        Note:
            Dùng tuple thay vì integer tránh collision giả tạo — hai bucket ở
            góc đối nhau sẽ không bao giờ chung key.
        """
        brow, bcol = row // self._bucket_cell, col // self._bucket_cell
        return (brow, bcol)
        pass

    # ------------------------------------------------------------------
    # CÁC METHOD GAME-SPECIFIC (đây là phần "Custom")
    # ------------------------------------------------------------------

    def insert(self, entity) -> None:
        """Thêm entity vào bucket tương ứng với vị trí hiện tại của nó.

        Args:
            entity: Object có thuộc tính .pos = (row, col). Trong game là Malware.

        Side effects:
            - Tạo bucket mới trong _buckets nếu chưa tồn tại.
            - Append entity vào list của bucket tương ứng.

        Usage:
            game.py gọi khi malware mới được spawn::

                spatial_hash.insert(malware)

        Example::

            # malware.pos = (3, 5), bucket_cell=2
            # key = (3//2, 5//2) = (1, 2)
            # _buckets[(1,2)] = [malware]  ← bucket mới được tạo
        """
        x, y = entity.pos
        bucket = self._hash(x, y)
        if bucket not in self._buckets:
            self._buckets[bucket] = []
        self._buckets[bucket].append(entity)
        pass

    def remove(self, entity) -> None:
        """Xóa entity khỏi bucket của nó.

        Args:
            entity: Object có thuộc tính .pos = (row, col). Vị trí phải là vị trí
                HIỆN TẠI của entity (không phải vị trí cũ).

        Side effects:
            - Xóa entity khỏi list của bucket tương ứng với entity.pos.
            - Xóa luôn key khỏi dict nếu bucket trở nên rỗng (giữ dict gọn).

        Usage:
            game.py gọi khi malware chết hoặc đến server::

                spatial_hash.remove(malware)

        Note:
            list.remove() xóa theo tham chiếu object, không theo giá trị.
            Nếu entity không tồn tại trong bucket, không gây lỗi (kiểm tra trước).
        """
        x, y = entity.pos
        bucket = self._hash(x, y)
        if bucket in self._buckets:
            malwares = self._buckets[bucket]
            if entity in malwares:
                malwares.remove(entity)
            if not malwares:
                del self._buckets[bucket]
        pass

    def update_position(self, entity, old_pos: tuple) -> None:
        """Cập nhật vị trí entity trong dict khi entity di chuyển sang ô mới.

        Method đặc thù của game — entity DI CHUYỂN nên bucket key có thể thay đổi
        mỗi frame. Nếu entity vẫn trong cùng bucket → không làm gì (tối ưu hóa).

        Args:
            entity: Object có .pos = (row, col) ĐÃ CẬP NHẬT (vị trí mới sau update).
            old_pos (tuple): Vị trí (row, col) CŨ — trước khi malware.update(dt) chạy.
                game.py phải lưu old_pos = malware.pos TRƯỚC khi gọi malware.update().

        Side effects:
            - Xóa entity khỏi bucket cũ (tính từ old_pos).
            - Thêm entity vào bucket mới (tính từ entity.pos hiện tại).
            - Xóa bucket cũ khỏi dict nếu trở nên rỗng.

        Usage:
            game.py trong _update_malwares()::

                old_pos = malware.pos
                malware.update(dt)
                if malware.pos != old_pos:
                    spatial_hash.update_position(malware, old_pos)

        Example::

            # Malware (2,4)→(2,5), bucket_cell=2
            # old_key = (1,2), new_key = (1,2) → CÙNG BUCKET → không làm gì

            # Malware (2,5)→(2,6), bucket_cell=2
            # old_key = (1,2), new_key = (1,3) → KHÁC → chuyển bucket
        """
        old_bucket = self._hash(old_pos[0], old_pos[1])
        new_bucket = self._hash(entity.pos[0], entity.pos[1])

        if old_bucket == new_bucket:
            return

        # Xóa trực tiếp từ old_bucket — KHÔNG dùng self.remove() vì nó dùng entity.pos mới
        if old_bucket in self._buckets:
            lst = self._buckets[old_bucket]
            if entity in lst:
                lst.remove(entity)
            if not lst:
                del self._buckets[old_bucket]

        # Thêm vào bucket mới
        self._buckets.setdefault(new_bucket, []).append(entity)
        pass

    def query_range(self, center_pos: tuple, radius: int) -> list:
        """Trả về tất cả entity trong bán kính radius ô quanh center_pos.

        Đây là method cốt lõi của spatial hash — lý do class này tồn tại.
        Thay vì duyệt toàn bộ entity, chỉ kiểm tra các bucket trong vùng bao quanh.

        Args:
            center_pos (tuple): Vị trí (row, col) ô lưới của Tower đang hỏi.
            radius (int): Bán kính tấn công của Tower (đơn vị ô lưới, Manhattan distance).

        Returns:
            list: Tất cả entity trong tầm (Manhattan distance <= radius).
                Có thể rỗng nếu không có entity nào gần Tower.

        Note:
            3 bước xử lý:
            1. Xác định hình chữ nhật bucket bao quanh vòng tròn bán kính radius.
            2. Duyệt từng bucket trong hình chữ nhật đó (bỏ qua bucket rỗng).
            3. Lọc bằng Manhattan distance thực tế — bucket hình chữ nhật có thể
               bao gồm góc nằm ngoài vòng tròn thực.

            Tại sao không cần seen set?
            Dict dùng (brow, bcol) làm key → mỗi bucket là list RIÊNG BIỆT → không trùng.

        Example::

            # Tower tại (6,6), radius=3, bucket_cell=2
            # min_brow=(6-3)//2=1, max_brow=(6+3)//2+1=5
            # min_bcol=1, max_bcol=5  → duyệt 16 bucket
            candidates = spatial_hash.query_range((6, 6), 3)
        """
        cr = center_pos[0]
        cc = center_pos[1]
        res = []
        min_br = max(0, (cr - radius) // self._bucket_cell)
        min_bc = max(0, (cc - radius) // self._bucket_cell)
        max_br = min(self._bucket_rows, (cr + radius) // self._bucket_cell + 1)
        max_bc = min(self._bucket_cols, (cc + radius) // self._bucket_cell + 1)
        for brow in range(min_br, max_br):
            for bcol in range(min_bc, max_bc):
                bucket_key = (brow, bcol)
                if bucket_key in self._buckets:
                    bucket = self._buckets[bucket_key]
                    for entity in bucket:
                        x, y = entity.pos
                        dist = abs(x - center_pos[0]) + abs(y - center_pos[1])
                        if dist <= radius:
                            res.append(entity)
        return res
        pass

    def clear(self) -> None:
        """Xóa toàn bộ entity — reset dict về rỗng.

        Side effects:
            - self._buckets trở thành dict rỗng {}.

        Usage:
            game.py gọi khi chuyển level hoặc restart game::

                spatial_hash.clear()
        """
        self._buckets = {}
        pass

    # ------------------------------------------------------------------
    # HELPER METHODS — hỗ trợ debug và quan sát trạng thái
    # ------------------------------------------------------------------

    def bucket_count(self) -> int:
        """Trả về số bucket đang có ít nhất 1 entity.

        Returns:
            int: Số lượng key trong _buckets (= số bucket không rỗng).

        Usage:
            Dùng khi debug để quan sát mức độ phân tán của spatial hash::

                print(spatial_hash.bucket_count())
                # Nếu bằng tổng malware → mỗi malware 1 bucket riêng → bucket quá nhỏ
        """
        return len(self._buckets)
        pass

    def entities_in_bucket(self, row: int, col: int) -> list:
        """Trả về list entity trong bucket chứa ô (row, col).

        Args:
            row (int): Hàng ô lưới (không phải hàng bucket).
            col (int): Cột ô lưới (không phải cột bucket).

        Returns:
            list: Danh sách entity trong bucket tương ứng.
                Trả về [] nếu bucket không tồn tại (không raise KeyError).

        Usage:
            Dùng khi debug để kiểm tra một ô lưới cụ thể đang có entity nào::

                entities = spatial_hash.entities_in_bucket(3, 5)
        """
        key = self._hash(row, col)
        return self._buckets.get(key, [])
        pass

"""
Thuật toán nén Huffman Coding.

Ý tưởng chính:
    Byte nào xuất hiện nhiều → gán mã ngắn (ít bit).
    Byte nào xuất hiện ít   → gán mã dài (nhiều bit).
    → Tổng số bit sau khi mã hóa sẽ ít hơn bản gốc → file nhỏ hơn.

Quy trình nén:
    1. count_frequency  — Đếm mỗi byte xuất hiện bao nhiêu lần.
    2. build_tree       — Xây cây Huffman từ bảng tần suất (dùng Min Heap).
    3. build_codes      — Duyệt cây để tạo bảng mã bit cho mỗi byte.
    4. encode_data      — Thay mỗi byte bằng mã bit → ghép lại → chuyển thành bytes.

Quy trình giải nén:
    1. Đọc bảng tần suất từ file nén.
    2. Xây lại cây Huffman (giống bước 2 ở trên).
    3. decode_data — Đọc từng bit, đi theo cây, đến lá thì lấy byte gốc.

Chương trình dùng byte (0..255) thay vì ký tự, nên nén được cả file nhị phân.
"""

import heapq
import json

from .file_format import HUFFMAN_ID, HEADER_SIZE, pack_header, unpack_header


# ============================================================
# CÂY HUFFMAN
# ============================================================

class HuffmanNode:
    """
    Một nút trong cây Huffman.

    Có 2 loại nút:
        - Nút lá:  chứa 1 byte cụ thể (ví dụ: byte 65 = ký tự 'A').
        - Nút cha: không chứa byte, chỉ nối 2 nút con (trái và phải).

    Thuộc tính:
        byte_value : giá trị byte (0-255), None nếu là nút cha.
        frequency  : số lần xuất hiện (hoặc tổng tần suất 2 con).
        left       : nút con trái (đi theo bit 0).
        right      : nút con phải (đi theo bit 1).
    """

    def __init__(self, byte_value=None, frequency=0, left=None, right=None):
        self.byte_value = byte_value
        self.frequency = frequency
        self.left = left
        self.right = right

    def is_leaf(self):
        """Nút lá = không có con trái lẫn con phải = chứa 1 byte thật."""
        return self.left is None and self.right is None

    def __lt__(self, other):
        """So sánh theo tần suất, để heapq luôn lấy nút nhỏ nhất trước."""
        return self.frequency < other.frequency


# ============================================================
# BỘ NÉN HUFFMAN
# ============================================================

class HuffmanCompressor:
    """
    Lớp thực hiện nén và giải nén dữ liệu bằng thuật toán Huffman.

    Cách dùng:
        compressor = HuffmanCompressor()
        compressed, stats = compressor.compress_data(data)    # Nén
        original = compressor.decompress_data(compressed)     # Giải nén

    Độ phức tạp (n = số byte đầu vào, k = số loại byte riêng biệt, k ≤ 256):
        - Đếm tần suất:  O(n)
        - Xây cây:        O(k log k)   → vì k ≤ 256, gần như hằng số
        - Tạo bảng mã:    O(k)
        - Mã hóa/giải mã: O(n)
        → Tổng:            O(n)         → tuyến tính theo kích thước file
    """

    MAX_CODEBOOK_SIZE = 8192  # Giới hạn kích thước bảng tần suất (bytes)
    algorithm_name = "huffman"
    algorithm_id = HUFFMAN_ID

    # ========================================================
    # BƯỚC 1: ĐẾM TẦN SUẤT — O(n)
    # ========================================================

    def count_frequency(self, data):
        """
        Đếm mỗi byte xuất hiện bao nhiêu lần.

        Ví dụ:
            data = b"AAAB"
            → {65: 3, 66: 1}   (A=65 xuất hiện 3 lần, B=66 xuất hiện 1 lần)
        """
        frequency = {}
        for byte_value in data:
            if byte_value not in frequency:
                frequency[byte_value] = 0
            frequency[byte_value] += 1
        return frequency

    # ========================================================
    # BƯỚC 2: XÂY CÂY HUFFMAN — O(k log k)
    # ========================================================

    def build_tree(self, frequency):
        """
        Xây cây Huffman từ bảng tần suất.

        Thuật toán (dùng Min Heap):
            1. Tạo 1 nút lá cho mỗi byte, bỏ vào heap.
            2. Lấy 2 nút có tần suất NHỎ NHẤT ra.
            3. Gộp thành 1 nút cha (tần suất = tổng 2 con).
            4. Đẩy nút cha lại vào heap.
            5. Lặp bước 2-4 cho đến khi heap chỉ còn 1 nút → đó là gốc cây.

        Ví dụ: {A:3, B:1, C:1}
            Heap ban đầu: [B(1), C(1), A(3)]
            Lần 1: gộp B(1)+C(1) → nút cha(2), heap = [cha(2), A(3)]
            Lần 2: gộp cha(2)+A(3) → gốc(5)
        """
        if not frequency:
            return None

        # Tạo nút lá cho mỗi byte và đưa vào min heap
        heap = []
        for byte_value, count in frequency.items():
            leaf = HuffmanNode(byte_value=byte_value, frequency=count)
            heapq.heappush(heap, leaf)

        # Trường hợp đặc biệt: chỉ có 1 loại byte
        # → Tạo 1 nút cha giả để byte đó có mã là "0"
        if len(heap) == 1:
            leaf = heapq.heappop(heap)
            root = HuffmanNode(frequency=leaf.frequency, left=leaf)
            return root

        # Gộp 2 nút nhỏ nhất cho đến khi chỉ còn 1 nút (gốc cây)
        while len(heap) > 1:
            left = heapq.heappop(heap)     # Nút nhỏ nhất
            right = heapq.heappop(heap)    # Nút nhỏ nhì
            parent = HuffmanNode(
                frequency=left.frequency + right.frequency,
                left=left,
                right=right,
            )
            heapq.heappush(heap, parent)

        root = heap[0]
        return root

    # ========================================================
    # BƯỚC 3: TẠO BẢNG MÃ BIT — O(k)
    # ========================================================

    def build_codes(self, root):
        """
        Duyệt cây Huffman để tạo bảng mã cho mỗi byte.

        Quy tắc: đi trái = thêm "0", đi phải = thêm "1".
        Khi đến nút lá → đường đi từ gốc chính là mã của byte đó.

        Ví dụ cây:
                gốc
               /    \\
             (2)     A(3)
            /   \\
          B(1)  C(1)

        → Bảng mã: {A: "1", B: "00", C: "01"}
          (A xuất hiện nhiều → mã ngắn nhất)
        """
        codes = {}
        if root is not None:
            self._traverse_tree(root, "", codes)
        return codes

    def _traverse_tree(self, node, current_code, codes):
        """Duyệt cây đệ quy: đến lá thì lưu mã, chưa đến lá thì đi tiếp."""
        if node.is_leaf():
            codes[node.byte_value] = current_code
            return

        # Đi trái → thêm "0"
        if node.left is not None:
            self._traverse_tree(node.left, current_code + "0", codes)

        # Đi phải → thêm "1"
        if node.right is not None:
            self._traverse_tree(node.right, current_code + "1", codes)

    # ========================================================
    # BƯỚC 4: MÃ HÓA (NÉN) — O(n)
    # ========================================================

    def encode_data(self, data, codes):
        """
        Thay mỗi byte bằng mã Huffman, rồi chuyển chuỗi bit thành bytes.

        Ví dụ:
            data = b"AAAB", codes = {65:"1", 66:"00"}
            → chuỗi bit: "1" + "1" + "1" + "00" = "11100"
            → thêm 3 bit đệm (padding): "11100" + "000" = "11100000"
            → chuyển thành 1 byte: 0b11100000 = 224

        Trả về: (bytes đã nén, số bit đệm đã thêm)
        """
        # Ghép mã Huffman của từng byte thành 1 chuỗi bit dài
        code_list = []
        for byte_value in data:
            huffman_code = codes[byte_value]
            code_list.append(huffman_code)
        bit_string = "".join(code_list)

        # Thêm bit 0 vào cuối cho đủ chia hết cho 8
        # Vì 1 byte = 8 bit, nên chuỗi bit phải có độ dài chia hết cho 8
        remainder = len(bit_string) % 8
        padding = 0
        if remainder != 0:
            padding = 8 - remainder
        bit_string += "0" * padding

        # Cắt chuỗi bit thành từng nhóm 8 bit → chuyển mỗi nhóm thành 1 byte
        compressed_bytes = bytearray()
        for position in range(0, len(bit_string), 8):
            eight_bits = bit_string[position:position + 8]
            byte_value = int(eight_bits, 2)   # "11100000" → 224
            compressed_bytes.append(byte_value)

        return bytes(compressed_bytes), padding

    # ========================================================
    # GIẢI MÃ (GIẢI NÉN) — O(n)
    # ========================================================

    def decode_data(self, payload, root, original_size, padding):
        """
        Đọc từng bit, đi theo cây Huffman, đến lá thì lấy byte gốc.

        Ví dụ:
            payload chứa byte 224 = "11100000", padding = 3
            → bỏ 3 bit cuối: "11100"
            → đọc bit "1" → đi phải → đến lá A → lấy A, quay về gốc
            → đọc bit "1" → đi phải → đến lá A → lấy A, quay về gốc
            → đọc bit "1" → đi phải → đến lá A → lấy A, quay về gốc
            → đọc bit "0" → đi trái
            → đọc bit "0" → đi trái → đến lá B → lấy B
            → Kết quả: b"AAAB"
        """
        # Chuyển mỗi byte thành chuỗi 8 bit (ví dụ: 224 → "11100000")
        bit_groups = []
        for byte_value in payload:
            eight_bits = format(byte_value, "08b")
            bit_groups.append(eight_bits)
        bit_string = "".join(bit_groups)

        # Bỏ các bit đệm ở cuối (vì chúng không phải dữ liệu thật)
        if padding > 0:
            bit_string = bit_string[:len(bit_string) - padding]

        # Duyệt từng bit theo cây Huffman
        restored_bytes = bytearray()
        current_node = root
        for bit in bit_string:
            # Bit "0" → đi trái, bit "1" → đi phải
            if bit == "0":
                current_node = current_node.left
            else:
                current_node = current_node.right

            if current_node is None:
                raise ValueError("Đường đi trong cây Huffman không hợp lệ.")

            # Đến nút lá → lấy byte gốc, quay lại gốc cây để đọc byte tiếp
            if current_node.is_leaf():
                if len(restored_bytes) >= original_size:
                    raise ValueError("Dữ liệu nén có byte thừa.")
                restored_bytes.append(current_node.byte_value)
                current_node = root

        # Kiểm tra: phải quay đúng về gốc và đủ số byte
        if current_node is not root or len(restored_bytes) != original_size:
            raise ValueError("Dữ liệu nén bị thiếu hoặc kết thúc giữa một mã Huffman.")
        return bytes(restored_bytes)

    # ============================================================
    # CÁC HÀM HỖ TRỢ ĐỌC/GHI FILE
    # (Không phải phần thuật toán chính — đọc sau nếu cần)
    # ============================================================

    def calculate_statistics(self, original_size, compressed_size):
        """Tính tỷ lệ nén. Số dương = file nhỏ đi, số âm = file lớn hơn."""
        compression_ratio = 0.0
        if original_size > 0:
            saved_size = original_size - compressed_size
            compression_ratio = saved_size / original_size * 100

        return {
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": round(compression_ratio, 2),
            "algorithm": self.algorithm_name,
        }

    def serialize_codebook(self, frequency):
        """Chuyển bảng tần suất thành JSON bytes để lưu vào file nén."""
        json_text = json.dumps(frequency, separators=(",", ":"))
        codebook_bytes = json_text.encode("utf-8")
        return codebook_bytes

    def deserialize_codebook(self, data):
        """Đọc JSON bytes từ file nén → khôi phục bảng tần suất."""
        try:
            json_text = data.decode("utf-8")
            raw = json.loads(json_text, object_pairs_hook=self._check_duplicate_keys)

            if not isinstance(raw, dict):
                raise ValueError("Bảng tần suất phải là dictionary.")
            if len(raw) > 256:
                raise ValueError("Chỉ có tối đa 256 giá trị byte (0-255).")

            frequency = {}
            for key, count in raw.items():
                byte_value = int(key)
                if str(byte_value) != key:
                    raise ValueError("Khóa phải là số nguyên.")
                if byte_value < 0 or byte_value > 255:
                    raise ValueError("Giá trị byte phải từ 0 đến 255.")
                if type(count) is not int:
                    raise ValueError("Tần suất phải là số nguyên.")
                if count <= 0 or count > 4294967295:
                    raise ValueError("Tần suất nằm ngoài phạm vi cho phép.")
                frequency[byte_value] = count
            return frequency
        except (ValueError, TypeError, RecursionError) as exc:
            raise ValueError("Codebook Huffman không hợp lệ.") from exc

    def _check_duplicate_keys(self, pairs):
        """Phát hiện khóa trùng trong JSON (JSON mặc định sẽ âm thầm ghi đè)."""
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Bảng tần suất có khóa trùng.")
            result[key] = value
        return result

    # ============================================================
    # API CHÍNH: NÉN VÀ GIẢI NÉN
    # ============================================================

    def compress_data(self, input_bytes):
        """
        Nén dữ liệu. Trả về (file_nén_bytes, thống_kê).

        File nén gồm 3 phần nối nhau:
            [Header 12 byte] + [Bảng tần suất JSON] + [Dữ liệu đã mã hóa]
        """
        # Chạy 4 bước thuật toán Huffman
        frequency = self.count_frequency(input_bytes)
        root = self.build_tree(frequency)
        codes = self.build_codes(root)
        payload, padding = self.encode_data(input_bytes, codes)

        # Đóng gói: header + bảng tần suất + dữ liệu nén
        codebook = self.serialize_codebook(frequency)
        header = pack_header(self.algorithm_id, len(input_bytes), len(codebook), padding)
        compressed = header + codebook + payload
        stats = self.calculate_statistics(len(input_bytes), len(compressed))
        return compressed, stats

    def decompress_data(self, input_bytes):
        """
        Giải nén file .bin do ShrinkIT tạo. Trả về dữ liệu gốc (bytes).

        Quy trình:
            1. Đọc header → biết kích thước gốc, kích thước bảng tần suất, padding.
            2. Đọc bảng tần suất → xây lại cây Huffman.
            3. Đọc dữ liệu nén → duyệt cây theo từng bit → lấy byte gốc.
            4. Kiểm tra kết quả có khớp bảng tần suất không.
        """
        # Tách và kiểm tra các phần của file nén
        frequency, payload, original_size, padding = self._read_compressed_file(input_bytes)
        if original_size == 0:
            return b""

        # Xây lại cây và giải mã
        root = self.build_tree(frequency)
        codes = self.build_codes(root)
        self._validate_payload(payload, codes, frequency, padding)
        restored = self.decode_data(payload, root, original_size, padding)

        # Kiểm tra: tần suất byte sau giải nén phải khớp với bảng tần suất gốc
        restored_frequency = self.count_frequency(restored)
        if restored_frequency != frequency:
            raise ValueError("Tần suất dữ liệu giải nén không khớp codebook.")
        return restored

    def _read_compressed_file(self, input_bytes):
        """Tách file nén thành: bảng tần suất, payload, kích thước gốc, padding."""
        header = unpack_header(input_bytes)
        if header["algorithm_id"] != self.algorithm_id:
            raise ValueError("File không dùng thuật toán Huffman.")

        size = header["original_size"]
        codebook_size = header["codebook_size"]
        padding = header["padding_bits"]

        if padding > 7 or not 2 <= codebook_size <= self.MAX_CODEBOOK_SIZE:
            raise ValueError("Padding hoặc kích thước codebook không hợp lệ.")

        end = HEADER_SIZE + codebook_size
        if end > len(input_bytes):
            raise ValueError("File nén bị thiếu codebook.")

        frequency = self.deserialize_codebook(input_bytes[HEADER_SIZE:end])
        if sum(frequency.values()) != size:
            raise ValueError("Bảng tần suất không khớp kích thước gốc.")

        payload = input_bytes[end:]
        if size == 0:
            if frequency or padding or payload:
                raise ValueError("File rỗng có dữ liệu thừa.")

        return frequency, payload, size, padding

    def _validate_payload(self, payload, codes, frequency, padding):
        """Kiểm tra độ dài dữ liệu nén và các bit đệm trước khi giải mã."""
        # Tính tổng số bit dữ liệu thật phải có
        expected_bits = 0
        for byte_value, count in frequency.items():
            expected_bits += count * len(codes[byte_value])

        actual_bits = len(payload) * 8 - padding
        if actual_bits != expected_bits:
            raise ValueError("Độ dài dữ liệu nén không khớp bảng tần suất.")

        # Các bit đệm cuối phải là 0
        if padding > 0:
            last_byte_bits = format(payload[-1], "08b")
            if last_byte_bits[-padding:] != "0" * padding:
                raise ValueError("Các bit padding phải bằng 0.")

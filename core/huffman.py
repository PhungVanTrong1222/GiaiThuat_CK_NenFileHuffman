"""Huffman: đếm tần suất -> xây cây -> tạo mã -> nén và giải nén.

Chương trình dùng byte (0..255) thay cho ký tự để xử lý cả văn bản và file nhị phân.
Chuỗi '0'/'1' giúp theo dõi thuật toán, nhưng tốn RAM hơn cách đóng gói bit trực tiếp.
"""

import heapq
import json

from .base_compressor import BaseCompressor, HEADER_SIZE, pack_header, unpack_header


class HuffmanNode:
    """Nút lá chứa một byte; nút cha chứa tổng tần suất của các nút con."""
    def __init__(self, byte_val=None, freq=0, left=None, right=None):
        self.byte_val = byte_val
        self.freq = freq
        self.left = left
        self.right = right

    def is_leaf(self):
        # Nút lá không có con trái và con phải.
        return self.left is None and self.right is None

    def __lt__(self, other):
        # heapq dùng phép so sánh này để lấy nút có tần suất nhỏ nhất.
        return self.freq < other.freq


class HuffmanCompressor(BaseCompressor):
    MAX_CODEBOOK_SIZE = 8192

    @property
    def algorithm_name(self):
        return "huffman"

    def _count_frequency(self, data):
        """Bước 1: đếm số lần mỗi byte xuất hiện."""
        frequency = {}
        for byte_value in data:
            if byte_value not in frequency:
                frequency[byte_value] = 0
            frequency[byte_value] += 1
        return frequency

    def _build_tree(self, frequency):
        """Bước 2: liên tục ghép hai cây có tần suất nhỏ nhất."""
        if not frequency:
            return None
        # Giữ thứ tự trong bảng tần suất để đọc được file của phiên bản cũ.
        heap = []
        for byte_value, count in frequency.items():
            leaf = HuffmanNode(byte_val=byte_value, freq=count)
            heapq.heappush(heap, leaf)

        if len(heap) == 1:
            # Chỉ một loại byte: thêm gốc để byte đó có mã '0'.
            leaf = heapq.heappop(heap)
            root = HuffmanNode(freq=leaf.freq, left=leaf)
            return root

        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            parent = HuffmanNode(
                freq=left.freq + right.freq,
                left=left,
                right=right,
            )
            heapq.heappush(heap, parent)
        root = heap[0]
        return root

    def _build_codes(self, root):
        """Bước 3: đi trái thêm '0', đi phải thêm '1'; đến lá thì lưu mã."""
        codes = {}
        if root is not None:
            self._traverse_tree(root, "", codes)
        return codes

    def _traverse_tree(self, node, current_code, codes):
        """Duyệt đệ quy: current_code là đường đi từ gốc đến nút đang xét."""
        if node.is_leaf():
            codes[node.byte_val] = current_code
            return

        if node.left is not None:
            left_code = current_code + "0"
            self._traverse_tree(node.left, left_code, codes)

        if node.right is not None:
            right_code = current_code + "1"
            self._traverse_tree(node.right, right_code, codes)

    def _encode(self, data, codes):
        """Bước 4: thay mỗi byte bằng mã Huffman, rồi chia thành nhóm 8 bit."""
        code_list = []
        for byte_value in data:
            huffman_code = codes[byte_value]
            code_list.append(huffman_code)

        # join ghép các mã trong danh sách thành một chuỗi.
        bit_string = "".join(code_list)

        # Ví dụ '10110' cần thêm 3 số 0 để thành '10110000'.
        remainder = len(bit_string) % 8
        padding = 0
        if remainder != 0:
            padding = 8 - remainder
        bit_string += "0" * padding

        compressed_bytes = bytearray()
        for position in range(0, len(bit_string), 8):
            eight_bits = bit_string[position:position + 8]
            byte_value = int(eight_bits, 2)
            compressed_bytes.append(byte_value)
        return bytes(compressed_bytes), padding

    def _decode(self, payload, root, original_size, padding):
        """Giải nén: đọc từng bit, đến nút lá thì lấy byte và quay lại gốc."""
        # '08b' chuyển một byte thành đúng 8 ký tự, kể cả các số 0 ở đầu.
        bit_groups = []
        for byte_value in payload:
            eight_bits = format(byte_value, "08b")
            bit_groups.append(eight_bits)
        bit_string = "".join(bit_groups)
        if padding > 0:
            number_of_data_bits = len(bit_string) - padding
            bit_string = bit_string[:number_of_data_bits]

        restored_bytes = bytearray()
        current_node = root
        for bit in bit_string:
            if bit == "0":
                current_node = current_node.left
            else:
                current_node = current_node.right

            if current_node is None:
                raise ValueError("Đường đi trong cây Huffman không hợp lệ.")
            if current_node.is_leaf():
                if len(restored_bytes) >= original_size:
                    raise ValueError("Dữ liệu nén có byte thừa.")
                restored_bytes.append(current_node.byte_val)
                current_node = root

        if current_node is not root or len(restored_bytes) != original_size:
            raise ValueError("Dữ liệu nén bị thiếu hoặc kết thúc giữa một mã Huffman.")
        return bytes(restored_bytes)

    # Các hàm bên dưới hỗ trợ lưu/đọc file và kiểm tra lỗi.
    # Khi học thuật toán, đọc _count_frequency đến _decode trước.

    def _serialize_codebook(self, frequency):
        """Đổi bảng tần suất sang JSON rồi sang bytes để lưu trong file."""
        json_text = json.dumps(frequency, separators=(",", ":"))
        codebook_bytes = json_text.encode("utf-8")
        return codebook_bytes

    def _check_duplicate_keys(self, pairs):
        """JSON gọi hàm này với các cặp (khóa, giá trị) đọc được."""
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Bảng tần suất có khóa trùng.")
            result[key] = value
        return result

    def _deserialize_codebook(self, data):
        """Đọc bảng tần suất từ file; từ chối dữ liệu không hợp lệ."""
        try:
            json_text = data.decode("utf-8")
            # Hook giúp phát hiện khóa trùng thay vì âm thầm ghi đè giá trị.
            raw = json.loads(json_text, object_pairs_hook=self._check_duplicate_keys)
            if not isinstance(raw, dict):
                raise ValueError("Bảng tần suất phải là dictionary.")
            if len(raw) > 256:
                raise ValueError("Chỉ có tối đa 256 giá trị byte.")

            frequency = {}
            for key, count in raw.items():
                byte_value = int(key)
                if str(byte_value) != key:
                    raise ValueError("Khóa byte phải viết đúng dạng số nguyên.")
                if byte_value < 0 or byte_value > 255:
                    raise ValueError("Giá trị byte phải từ 0 đến 255.")
                # type thay cho isinstance để không chấp nhận True/False là số.
                if type(count) is not int:
                    raise ValueError("Tần suất phải là số nguyên.")
                if count <= 0 or count > 4294967295:
                    raise ValueError("Tần suất nằm ngoài phạm vi lưu trữ 4 byte.")
                frequency[byte_value] = count
            return frequency
        except (ValueError, TypeError, RecursionError) as exc:
            raise ValueError("Codebook Huffman không hợp lệ.") from exc

    def compress_data(self, input_bytes):
        """Thực hiện lần lượt các bước Huffman và lưu thông tin để giải nén."""
        frequency = self._count_frequency(input_bytes)
        root = self._build_tree(frequency)
        codes = self._build_codes(root)
        payload, padding = self._encode(input_bytes, codes)

        # File = header + bảng tần suất + dữ liệu nén.
        codebook = self._serialize_codebook(frequency)
        header = pack_header(self.algorithm_id, len(input_bytes), len(codebook), padding)
        compressed = header + codebook + payload
        stats = self._build_stats(len(input_bytes), len(compressed))
        return compressed, stats

    def _read_compressed_file(self, input_bytes):
        """Đọc và kiểm tra định dạng file; không thực hiện thuật toán giải mã."""
        header = unpack_header(input_bytes)
        self._validate_header(header)
        size = header["original_size"]
        book_size = header["codebook_size"]
        padding = header["padding_bits"]
        if padding > 7 or not 2 <= book_size <= self.MAX_CODEBOOK_SIZE:
            raise ValueError("Padding hoặc kích thước codebook không hợp lệ.")
        end = HEADER_SIZE + book_size
        if end > len(input_bytes):
            raise ValueError("File nén bị thiếu codebook.")
        frequency = self._deserialize_codebook(input_bytes[HEADER_SIZE:end])
        if sum(frequency.values()) != size:
            raise ValueError("Bảng tần suất không khớp kích thước gốc.")
        payload = input_bytes[end:]
        if size == 0:
            if frequency or padding or payload:
                raise ValueError("File rỗng có dữ liệu thừa.")
        return frequency, payload, size, padding

    def _validate_payload(self, payload, codes, frequency, padding):
        """Kiểm tra độ dài và padding trước khi duyệt cây."""
        expected_bits = 0
        for byte_value, count in frequency.items():
            expected_bits += count * len(codes[byte_value])
        actual_bits = len(payload) * 8 - padding
        if actual_bits != expected_bits:
            raise ValueError("Độ dài dữ liệu nén không khớp bảng tần suất.")
        if padding > 0:
            last_byte_bits = format(payload[-1], "08b")
            if last_byte_bits[-padding:] != "0" * padding:
                raise ValueError("Các bit padding phải bằng 0.")

    def decompress_data(self, input_bytes):
        """Đọc bảng tần suất, xây lại cây và giải mã dữ liệu."""
        frequency, payload, original_size, padding = self._read_compressed_file(input_bytes)
        if original_size == 0:
            return b""

        root = self._build_tree(frequency)
        codes = self._build_codes(root)
        self._validate_payload(payload, codes, frequency, padding)
        restored = self._decode(payload, root, original_size, padding)
        restored_frequency = self._count_frequency(restored)
        if restored_frequency != frequency:
            raise ValueError("Tần suất dữ liệu giải nén không khớp codebook.")
        return restored

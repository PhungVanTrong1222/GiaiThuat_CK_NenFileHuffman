"""Huffman: đếm tần suất -> xây cây -> tạo mã -> nén và giải nén.

Chương trình dùng byte (0..255) thay cho ký tự để xử lý cả văn bản và file nhị phân.
Chuỗi '0'/'1' giúp theo dõi thuật toán, nhưng tốn RAM hơn cách đóng gói bit trực tiếp.
"""

import heapq
import json
from collections import Counter

from .base_compressor import BaseCompressor, HEADER_SIZE, pack_header, unpack_header


class HuffmanNode:
    """Nút lá chứa một byte; nút cha chứa tổng tần suất của các nút con."""
    def __init__(self, byte_val=None, freq=0, left=None, right=None):
        self.byte_val = byte_val
        self.freq = freq
        self.left = left
        self.right = right

    def is_leaf(self):
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
        if len(frequency) == 1:
            # Chỉ một loại byte: thêm gốc để byte đó có mã '0'.
            byte_value, count = next(iter(frequency.items()))
            leaf = HuffmanNode(byte_val=byte_value, freq=count)
            return HuffmanNode(freq=count, left=leaf)
        # Giữ thứ tự trong bảng tần suất để đọc được file của phiên bản cũ.
        heap = []
        for byte_value, count in frequency.items():
            leaf = HuffmanNode(byte_val=byte_value, freq=count)
            heapq.heappush(heap, leaf)
        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            parent = HuffmanNode(
                freq=left.freq + right.freq,
                left=left,
                right=right,
            )
            heapq.heappush(heap, parent)
        return heap[0]

    def _build_codes(self, root):
        """Bước 3: đi trái thêm '0', đi phải thêm '1'; đến lá thì lưu mã."""
        codes = {}

        def traverse(node, current_code):
            if node.is_leaf():
                codes[node.byte_val] = current_code
            else:
                if node.left:
                    traverse(node.left, current_code + "0")
                if node.right:
                    traverse(node.right, current_code + "1")

        if root:
            traverse(root, "")
        return codes

    def _encode(self, data, codes):
        """Bước 4: thay mỗi byte bằng mã Huffman, rồi chia thành nhóm 8 bit."""
        bit_string = "".join(codes[byte_value] for byte_value in data)

        # Ví dụ '10110' cần thêm 3 số 0 để thành '10110000'.
        padding = (8 - len(bit_string) % 8) % 8
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
        bit_string = "".join(format(byte_value, "08b") for byte_value in payload)
        if padding > 0:
            bit_string = bit_string[:-padding]

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

    def _serialize_codebook(self, frequency):
        return json.dumps(frequency, separators=(",", ":")).encode("utf-8")

    def _deserialize_codebook(self, data):
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Bảng tần suất có khóa trùng.")
                result[key] = value
            return result

        try:
            raw = json.loads(data.decode("utf-8"), object_pairs_hook=unique_pairs)
            if not isinstance(raw, dict) or len(raw) > 256:
                raise ValueError("Bảng tần suất phải là object tối đa 256 phần tử.")
            frequency = {}
            for key, count in raw.items():
                value = int(key)
                if (str(value) != key or not 0 <= value <= 255
                        or type(count) is not int or not 0 < count <= 0xFFFFFFFF):
                    raise ValueError("Byte hoặc tần suất không hợp lệ.")
                frequency[value] = count
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
        if Counter(restored) != frequency:
            raise ValueError("Tần suất dữ liệu giải nén không khớp codebook.")
        return restored

"""Nén Huffman: đếm byte, xây cây bằng min heap và đóng gói bit.

Với n byte và mã dài tối đa L, xử lý bit tốn O(nL) thời gian.
Bộ nhớ gồm dữ liệu vào/ra và cây tối đa 256 lá; không tạo chuỗi bit cho cả file.
"""

import heapq
import json
from collections import Counter

from .base_compressor import BaseCompressor, HEADER_SIZE, pack_header, unpack_header


class HuffmanNode:
    def __init__(self, byte_val=None, freq=0, left=None, right=None):
        self.byte_val = byte_val
        self.freq = freq
        self.left = left
        self.right = right

    def is_leaf(self):
        return self.left is None and self.right is None

    def __lt__(self, other):
        return self.freq < other.freq


class HuffmanCompressor(BaseCompressor):
    MAX_CODEBOOK_SIZE = 8192

    @property
    def algorithm_name(self):
        return "huffman"

    def _count_frequency(self, data):
        return dict(Counter(data))

    def _build_tree(self, frequency):
        if not frequency:
            return None
        if len(frequency) == 1:
            value, count = next(iter(frequency.items()))
            return HuffmanNode(freq=count, left=HuffmanNode(value, count))
        # Giữ thứ tự trong bảng tần suất để đọc được file của phiên bản cũ.
        heap = []
        for value, count in frequency.items():
            heapq.heappush(heap, HuffmanNode(value, count))
        while len(heap) > 1:
            left, right = heapq.heappop(heap), heapq.heappop(heap)
            heapq.heappush(heap, HuffmanNode(freq=left.freq + right.freq,
                                           left=left, right=right))
        return heap[0]

    def _build_codes(self, root):
        codes = {}

        def visit(node, bits):
            if node.is_leaf():
                codes[node.byte_val] = bits or "0"
            else:
                if node.left:
                    visit(node.left, bits + "0")
                if node.right:
                    visit(node.right, bits + "1")

        if root:
            visit(root, "")
        return codes

    def _encode(self, data, codes):
        packed = {value: (int(bits, 2), len(bits)) for value, bits in codes.items()}
        output = bytearray()
        buffer = bit_count = 0
        for value in data:
            code, length = packed[value]
            buffer = (buffer << length) | code
            bit_count += length
            while bit_count >= 8:
                bit_count -= 8
                output.append((buffer >> bit_count) & 255)
            buffer &= (1 << bit_count) - 1
        padding = (-bit_count) % 8
        if bit_count:
            output.append(buffer << padding)
        return bytes(output), padding

    def _decode(self, payload, root, original_size, padding):
        output = bytearray()
        node = root
        for index, value in enumerate(payload):
            stop = padding if index == len(payload) - 1 else 0
            for shift in range(7, stop - 1, -1):
                node = node.right if (value >> shift) & 1 else node.left
                if node is None:
                    raise ValueError("Đường đi trong cây Huffman không hợp lệ.")
                if node.is_leaf():
                    if len(output) >= original_size:
                        raise ValueError("Dữ liệu nén có byte thừa.")
                    output.append(node.byte_val)
                    node = root
        if node is not root or len(output) != original_size:
            raise ValueError("Dữ liệu nén bị thiếu hoặc kết thúc giữa một mã Huffman.")
        return bytes(output)

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
        frequency = self._count_frequency(input_bytes)
        codes = self._build_codes(self._build_tree(frequency))
        payload, padding = self._encode(input_bytes, codes)
        codebook = self._serialize_codebook(frequency)
        header = pack_header(self.algorithm_id, len(input_bytes), len(codebook), padding)
        compressed = header + codebook + payload
        return compressed, self._build_stats(len(input_bytes), len(compressed))

    def decompress_data(self, input_bytes):
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
        payload = memoryview(input_bytes)[end:]
        if size == 0:
            if frequency or padding or payload:
                raise ValueError("File rỗng có dữ liệu thừa.")
            return b""
        root = self._build_tree(frequency)
        codes = self._build_codes(root)
        expected_bits = sum(count * len(codes[value]) for value, count in frequency.items())
        if len(payload) * 8 - padding != expected_bits:
            raise ValueError("Độ dài dữ liệu nén không khớp bảng tần suất.")
        if padding and payload[-1] & ((1 << padding) - 1):
            raise ValueError("Các bit padding phải bằng 0.")
        restored = self._decode(payload, root, size, padding)
        if Counter(restored) != frequency:
            raise ValueError("Tần suất dữ liệu giải nén không khớp codebook.")
        return restored

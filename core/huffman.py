"""
ShrinkIT - Huffman Coding Compressor
=====================================
Thuật toán nén Huffman Coding sử dụng cấu trúc dữ liệu:
    - Min Heap (Priority Queue) để xây dựng cây Huffman
    - Binary Tree để tạo bảng mã bit tối ưu

Độ phức tạp:
    - Thời gian:
        + Đếm tần suất:  O(n)           n = số bytes input
        + Xây dựng cây:  O(k log k)     k = số ký tự distinct
        + Tạo bảng mã:   O(k)
        + Encode:         O(n × L)       L = chiều dài mã trung bình
        + Decode:         O(n × L)
        → Tổng:           O(n log k)     (vì k ≤ 256 nên log k ≤ 8, gần như O(n))
    
    - Không gian:
        + Bảng tần suất:  O(k)           k ≤ 256
        + Cây Huffman:    O(k)
        + Bảng mã bit:   O(k × L)
        + Output buffer:  O(n)
        → Tổng:           O(n)

Best case:  Dữ liệu có phân bố tần suất lệch mạnh → tỷ lệ nén cao (~60-70%)
Worst case: Dữ liệu có phân bố đồng đều (256 ký tự, tần suất bằng nhau)
            → mỗi ký tự cần ~8 bits → file nén có thể LỚN HƠN file gốc (do thêm header + codebook)
"""

import heapq
import json
from collections import Counter
from .base_compressor import BaseCompressor, pack_header, unpack_header, HEADER_SIZE


# Huffman Tree Node
class HuffmanNode:
    """
    Node trong cây Huffman.
    
    Attributes:
        byte_val: Giá trị byte (None nếu là node nội bộ)
        freq:     Tần suất xuất hiện
        left:     Con trái (bit 0)
        right:    Con phải (bit 1)
    """
    
    def __init__(self, byte_val=None, freq=0, left=None, right=None):
        self.byte_val = byte_val
        self.freq = freq
        self.left = left
        self.right = right
    
    def is_leaf(self) -> bool:
        """Kiểm tra có phải node lá (chứa ký tự) hay không."""
        return self.left is None and self.right is None
    
    # Cần định nghĩa __lt__ để heapq so sánh được khi 2 node cùng tần suất
    def __lt__(self, other):
        return self.freq < other.freq


# Huffman Compressor
class HuffmanCompressor(BaseCompressor):
    """
    Thuật toán nén Huffman Coding.
    
    Quy trình nén:
        1. Đếm tần suất từng byte trong dữ liệu
        2. Xây dựng cây Huffman từ bảng tần suất (dùng Min Heap)
        3. Tạo bảng mã bit cho từng byte (duyệt cây)
        4. Encode dữ liệu: thay mỗi byte bằng mã bit tương ứng
        5. Đóng gói: header + codebook (bảng tần suất) + dữ liệu nén
    
    Quy trình giải nén:
        1. Đọc header → lấy thông tin codebook size, padding bits
        2. Đọc codebook → khôi phục bảng tần suất
        3. Xây lại cây Huffman từ bảng tần suất
        4. Decode: duyệt cây theo từng bit để khôi phục dữ liệu gốc
    """
    
    @property
    def algorithm_name(self) -> str:
        return "huffman"
    
    # Bước 1: Đếm tần suất — O(n)
    def _count_frequency(self, data: bytes) -> dict:
        """
        Đếm tần suất xuất hiện của từng byte.
        
        Args:
            data: Dữ liệu gốc
        
        Returns:
            dict: {byte_value: frequency}
        """
        return dict(Counter(data))
    
    # Bước 2: Xây dựng cây Huffman — O(k log k)
    def _build_tree(self, frequency: dict) -> HuffmanNode:
        """
        Xây dựng cây Huffman từ bảng tần suất bằng Min Heap.
        
        Thuật toán:
            1. Tạo node lá cho mỗi ký tự, đưa vào min heap
            2. Lặp: lấy 2 node có tần suất nhỏ nhất, gộp thành node cha
            3. Tiếp tục cho đến khi chỉ còn 1 node (gốc cây)
        
        Args:
            frequency: Bảng tần suất {byte_value: count}
        
        Returns:
            HuffmanNode: Gốc cây Huffman
        """
        if not frequency:
            return None
        
        # Trường hợp đặc biệt: chỉ có 1 loại ký tự
        if len(frequency) == 1:
            byte_val, freq = next(iter(frequency.items()))
            leaf = HuffmanNode(byte_val=byte_val, freq=freq)
            # Tạo node cha để đảm bảo mã bit có ít nhất 1 bit
            return HuffmanNode(freq=freq, left=leaf)
        
        # Tạo min heap từ các node lá
        heap = []
        for byte_val, freq in frequency.items():
            node = HuffmanNode(byte_val=byte_val, freq=freq)
            heapq.heappush(heap, node)
        
        # Gộp 2 node nhỏ nhất cho đến khi còn 1 node
        while len(heap) > 1:
            left = heapq.heappop(heap)    # Node có tần suất nhỏ nhất
            right = heapq.heappop(heap)   # Node có tần suất nhỏ nhì
            
            # Tạo node cha với tần suất = tổng 2 con
            parent = HuffmanNode(
                freq=left.freq + right.freq,
                left=left,
                right=right
            )
            heapq.heappush(heap, parent)
        
        return heap[0]  # Gốc cây
    
    # Bước 3: Tạo bảng mã bit — O(k)
    def _build_codes(self, root: HuffmanNode) -> dict:
        """
        Duyệt cây Huffman để tạo bảng mã bit cho từng ký tự.
        
        Quy tắc: đi trái = thêm "0", đi phải = thêm "1".
        Ký tự ở node lá → mã bit = đường đi từ gốc đến lá.
        
        Args:
            root: Gốc cây Huffman
        
        Returns:
            dict: {byte_value: "bit_string"}  (ví dụ: {65: "010", 66: "11"})
        """
        if root is None:
            return {}
        
        codes = {}
        
        def _traverse(node, current_code):
            if node.is_leaf():
                # Đảm bảo mã bit không rỗng (trường hợp 1 ký tự)
                codes[node.byte_val] = current_code if current_code else "0"
                return
            
            if node.left:
                _traverse(node.left, current_code + "0")
            if node.right:
                _traverse(node.right, current_code + "1")
        
        _traverse(root, "")
        return codes
    
    # Bước 4: Encode dữ liệu — O(n × L)
    def _encode(self, data: bytes, codes: dict) -> tuple:
        """
        Mã hóa dữ liệu bằng bảng mã Huffman.
        
        Args:
            data:  Dữ liệu gốc (bytes)
            codes: Bảng mã bit {byte_value: "bit_string"}
        
        Returns:
            tuple: (encoded_bytes, padding_bits)
                - encoded_bytes: Dữ liệu đã nén (bytes)
                - padding_bits: Số bit padding thêm vào byte cuối (0-7)
        """
        # Ghép tất cả mã bit thành chuỗi dài
        bit_string = "".join(codes[byte] for byte in data)
        
        # Tính số bit padding cần thêm để chia hết cho 8
        padding_bits = (8 - len(bit_string) % 8) % 8
        bit_string += "0" * padding_bits
        
        # Chuyển chuỗi bit thành bytes
        encoded_bytes = bytearray()
        for i in range(0, len(bit_string), 8):
            byte = int(bit_string[i:i+8], 2)
            encoded_bytes.append(byte)
        
        return bytes(encoded_bytes), padding_bits
    
    # Bước 5 (giải nén): Decode dữ liệu — O(n × L)
    def _decode(self, encoded_bytes: bytes, root: HuffmanNode, 
                original_size: int, padding_bits: int) -> bytes:
        """
        Giải mã dữ liệu bằng cách duyệt cây Huffman.
        
        Thuật toán:
            1. Chuyển bytes thành chuỗi bit (bỏ padding)
            2. Duyệt từng bit: 0 → đi trái, 1 → đi phải
            3. Khi đến node lá → lấy ký tự, quay lại gốc cây
            4. Dừng khi đã giải mã đủ original_size bytes
        
        Args:
            encoded_bytes: Dữ liệu đã nén
            root:          Gốc cây Huffman
            original_size: Kích thước file gốc
            padding_bits:  Số bit padding ở byte cuối
        
        Returns:
            bytes: Dữ liệu gốc
        """
        # Chuyển bytes thành chuỗi bit
        bit_string = ""
        for byte in encoded_bytes:
            bit_string += format(byte, '08b')
        
        # Bỏ padding bits ở cuối
        if padding_bits > 0:
            bit_string = bit_string[:-padding_bits]
        
        # Duyệt cây để decode
        decoded = bytearray()
        current_node = root
        
        for bit in bit_string:
            if bit == '0':
                current_node = current_node.left
            else:
                current_node = current_node.right

            if current_node is None:
                raise ValueError("Dữ liệu Huffman bị hỏng: đường đi trong cây không hợp lệ.")
            
            if current_node.is_leaf():
                decoded.append(current_node.byte_val)
                current_node = root
                
                # Dừng sớm nếu đã đủ kích thước gốc
                if len(decoded) >= original_size:
                    break
        
        if len(decoded) != original_size:
            raise ValueError(
                "Dữ liệu Huffman bị thiếu hoặc bị hỏng: "
                f"khôi phục được {len(decoded)}/{original_size} bytes."
            )

        return bytes(decoded)
    
    # Serialization: Codebook ↔ JSON
    def _serialize_codebook(self, frequency: dict) -> bytes:
        """
        Serialize bảng tần suất thành JSON bytes.
        Lưu bảng tần suất (thay vì cây) vì nhỏ gọn hơn và dễ xây lại cây.
        
        Chuyển key từ int sang string vì JSON không hỗ trợ key kiểu int.
        """
        str_freq = {str(k): v for k, v in frequency.items()}
        return json.dumps(str_freq, separators=(',', ':')).encode('utf-8')
    
    def _deserialize_codebook(self, codebook_bytes: bytes) -> dict:
        """Deserialize JSON bytes thành bảng tần suất {int: int}."""
        str_freq = json.loads(codebook_bytes.decode('utf-8'))
        return {int(k): v for k, v in str_freq.items()}
    
    # Public API: compress_data
    def compress_data(self, input_bytes: bytes) -> tuple:
        """
        Nén dữ liệu bằng thuật toán Huffman Coding.
        
        Args:
            input_bytes: Dữ liệu gốc cần nén
        
        Returns:
            tuple: (compressed_file_bytes, stats_dict)
        """
        if not input_bytes:
            # File rỗng: trả về header + codebook rỗng
            codebook_bytes = b"{}"
            header = pack_header(self.algorithm_id, 0, len(codebook_bytes), 0)
            compressed = header + codebook_bytes
            return compressed, self._build_stats(0, len(compressed))
        
        # 1. Đếm tần suất
        frequency = self._count_frequency(input_bytes)
        
        # 2. Xây dựng cây Huffman
        root = self._build_tree(frequency)
        
        # 3. Tạo bảng mã bit
        codes = self._build_codes(root)
        
        # 4. Encode dữ liệu
        encoded_bytes, padding_bits = self._encode(input_bytes, codes)
        
        # 5. Serialize codebook (bảng tần suất)
        codebook_bytes = self._serialize_codebook(frequency)
        
        # 6. Đóng gói: header + codebook + encoded data
        header = pack_header(
            algorithm_id=self.algorithm_id,
            original_size=len(input_bytes),
            codebook_size=len(codebook_bytes),
            padding_bits=padding_bits
        )
        
        compressed = header + codebook_bytes + encoded_bytes
        stats = self._build_stats(len(input_bytes), len(compressed))
        
        return compressed, stats
    
    # Public API: decompress_data
    def decompress_data(self, input_bytes: bytes) -> bytes:
        """
        Giải nén file .bin đã nén bằng Huffman.
        
        Args:
            input_bytes: File .bin hoàn chỉnh (header + codebook + data)
        
        Returns:
            bytes: Dữ liệu gốc
        """
        # 1. Đọc header
        header = unpack_header(input_bytes)
        self._validate_header(header)
        
        original_size = header["original_size"]
        codebook_size = header["codebook_size"]
        padding_bits = header["padding_bits"]
        
        # File gốc rỗng
        if original_size == 0:
            return b""
        
        # 2. Đọc codebook
        codebook_start = HEADER_SIZE
        codebook_end = codebook_start + codebook_size

        if padding_bits > 7:
            raise ValueError(f"Số bit padding không hợp lệ: {padding_bits}.")

        if codebook_end > len(input_bytes):
            raise ValueError("File nén bị thiếu dữ liệu codebook.")

        codebook_bytes = input_bytes[codebook_start:codebook_end]
        try:
            frequency = self._deserialize_codebook(codebook_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError("Codebook Huffman không hợp lệ.") from exc

        if (
            not frequency
            or any(not 0 <= byte_val <= 255 for byte_val in frequency)
            or any(not isinstance(count, int) or count <= 0 for count in frequency.values())
            or sum(frequency.values()) != original_size
        ):
            raise ValueError("Bảng tần suất Huffman không khớp với header.")
        
        # 3. Xây lại cây Huffman từ bảng tần suất
        root = self._build_tree(frequency)
        
        # 4. Đọc dữ liệu nén
        encoded_bytes = input_bytes[codebook_end:]
        
        # 5. Decode
        return self._decode(encoded_bytes, root, original_size, padding_bits)

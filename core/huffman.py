"""Huffman: đếm tần suất -> xây cây -> tạo mã -> nén và giải nén.

Chương trình dùng byte (0..255) thay cho ký tự để xử lý cả văn bản và file nhị phân.
Chuỗi '0'/'1' giúp theo dõi thuật toán, nhưng tốn RAM hơn cách đóng gói bit trực tiếp.
"""

import heapq
import json

from .file_format import HUFFMAN_ID, HEADER_SIZE, pack_header, unpack_header


class HuffmanNode:
    """Nút lá chứa một byte; nút cha chứa tổng tần suất của các nút con."""
    def __init__(self, byte_value=None, frequency=0, left=None, right=None):
        """Tạo một nút của cây Huffman.

        byte_value là giá trị byte ở nút lá; nút cha dùng None.
        frequency là số lần xuất hiện; left và right là hai nút con.
        Python tự gọi hàm này khi viết HuffmanNode(...)."""
        self.byte_value = byte_value
        self.frequency = frequency
        self.left = left
        self.right = right

    def is_leaf(self):
        """Trả về True nếu nút không có con trái và con phải.

        Nút lá chứa byte cần xuất ra khi giải nén."""
        # Nút lá không có con trái và con phải.
        return self.left is None and self.right is None

    def __lt__(self, other):
        """So sánh tần suất của nút hiện tại với nút other.

        Trả về True khi nút hiện tại có tần suất nhỏ hơn.
        heapq dùng phép so sánh này để chọn hai nút nhỏ nhất."""
        # heapq dùng phép so sánh này để lấy nút có tần suất nhỏ nhất.
        return self.frequency < other.frequency


class HuffmanCompressor:
    MAX_CODEBOOK_SIZE = 8192

    algorithm_name = "huffman"
    algorithm_id = HUFFMAN_ID

    def calculate_statistics(self, original_size, compressed_size):
        """Tính kết quả thống kê từ kích thước gốc và kích thước nén (byte).

        Trả về dictionary gồm hai kích thước, phần trăm giảm và tên thuật toán.
        File rỗng dùng tỷ lệ 0 để tránh chia cho 0; tỷ lệ âm là file nén lớn hơn."""
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

    def count_frequency(self, data):
        """Đếm số lần xuất hiện của mỗi byte trong data.

        Đầu vào: dữ liệu bytes. Đầu ra: dictionary {giá trị byte: số lần}.
        Ví dụ b'AAAB' cho kết quả {65: 3, 66: 1}."""
        frequency = {}
        for byte_value in data:
            if byte_value not in frequency:
                frequency[byte_value] = 0
            frequency[byte_value] += 1
        return frequency

    def build_tree(self, frequency):
        """Xây cây Huffman từ bảng tần suất và trả về nút gốc.

        Đưa các nút lá vào min heap, lấy hai nút nhỏ nhất ghép thành nút cha,
        rồi đưa nút cha lại vào heap. Lặp đến khi chỉ còn một cây.
        Bảng rỗng trả về None; một loại byte được đặt bên trái gốc để có mã 0."""
        if not frequency:
            return None
        # Giữ thứ tự trong bảng tần suất để đọc được file của phiên bản cũ.
        heap = []
        for byte_value, count in frequency.items():
            leaf = HuffmanNode(byte_value=byte_value, frequency=count)
            heapq.heappush(heap, leaf)

        if len(heap) == 1:
            # Chỉ một loại byte: thêm gốc để byte đó có mã '0'.
            leaf = heapq.heappop(heap)
            root = HuffmanNode(frequency=leaf.frequency, left=leaf)
            return root

        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            parent = HuffmanNode(
                frequency=left.frequency + right.frequency,
                left=left,
                right=right,
            )
            heapq.heappush(heap, parent)
        root = heap[0]
        return root

    def build_codes(self, root):
        """Tạo dictionary {giá trị byte: chuỗi mã Huffman} từ nút gốc.

        Gọi traverse_tree để duyệt cây và điền bảng mã.
        Cây rỗng trả về dictionary rỗng."""
        codes = {}
        if root is not None:
            self.traverse_tree(root, "", codes)
        return codes

    def traverse_tree(self, node, current_code, codes):
        """Duyệt cây đệ quy và ghi mã của các nút lá vào dictionary codes.

        node là nút đang xét; current_code là chuỗi đường đi từ gốc.
        Đi trái nối 0, đi phải nối 1. Đến lá thì lưu mã và quay lui.
        Hàm sửa trực tiếp codes được truyền vào, không trả về bảng mới."""
        if node.is_leaf():
            codes[node.byte_value] = current_code
            return

        if node.left is not None:
            left_code = current_code + "0"
            self.traverse_tree(node.left, left_code, codes)

        if node.right is not None:
            right_code = current_code + "1"
            self.traverse_tree(node.right, right_code, codes)

    def encode_data(self, data, codes):
        """Đổi dữ liệu gốc thành các byte nén dựa trên bảng codes.

        Ghép mã Huffman của từng byte, thêm số 0 cho đủ nhóm 8 bit,
        rồi đổi từng nhóm sang một byte bằng int(nhóm_bit, 2).
        Trả về (dữ liệu nén bytes, số bit đệm từ 0 đến 7), chưa có header."""
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

    def decode_data(self, payload, root, original_size, padding):
        """Khôi phục bytes gốc từ payload bằng cách duyệt cây root.

        payload chỉ chứa dữ liệu nén, không gồm header và bảng tần suất.
        Đổi từng byte thành 8 bit, bỏ padding bit cuối rồi duyệt cây.
        Gặp lá thì lấy byte và quay lại gốc. original_size là số byte cần có.
        Trả về dữ liệu gốc; báo ValueError nếu đường đi hoặc số byte sai."""
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
                restored_bytes.append(current_node.byte_value)
                current_node = root

        if current_node is not root or len(restored_bytes) != original_size:
            raise ValueError("Dữ liệu nén bị thiếu hoặc kết thúc giữa một mã Huffman.")
        return bytes(restored_bytes)

    # Các hàm bên dưới hỗ trợ lưu/đọc file và kiểm tra lỗi.
    # Khi học thuật toán, đọc count_frequency đến decode_data trước.

    def serialize_codebook(self, frequency):
        """Chuyển dictionary tần suất thành JSON dạng bytes để lưu file.

        Khóa số nguyên được JSON ghi thành chuỗi. Không thêm khoảng trắng
        để bảng chiếm ít dung lượng. Hàm không tự ghi file xuống ổ đĩa."""
        json_text = json.dumps(frequency, separators=(",", ":"))
        codebook_bytes = json_text.encode("utf-8")
        return codebook_bytes

    def check_duplicate_keys(self, pairs):
        """Tạo dictionary từ danh sách cặp khóa, giá trị do json.loads đưa vào.

        Báo ValueError nếu một khóa xuất hiện hai lần; nếu hợp lệ thì trả dictionary.
        Được dùng làm object_pairs_hook để JSON không bỏ qua khóa trùng."""
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Bảng tần suất có khóa trùng.")
            result[key] = value
        return result

    def deserialize_codebook(self, data):
        """Đọc bytes JSON và trả về bảng tần suất với khóa byte dạng số nguyên.

        Kiểm tra kiểu dictionary, tối đa 256 byte, khóa không trùng,
        giá trị byte 0..255 và tần suất nguyên dương nằm trong giới hạn.
        Báo ValueError khi codebook sai định dạng hoặc không hợp lệ."""
        try:
            json_text = data.decode("utf-8")
            # Hook giúp phát hiện khóa trùng thay vì âm thầm ghi đè giá trị.
            raw = json.loads(json_text, object_pairs_hook=self.check_duplicate_keys)
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
        """Thực hiện toàn bộ quá trình nén một dữ liệu bytes.

        Đếm tần suất -> xây cây -> tạo mã -> mã hóa -> ghép header và codebook.
        Trả về (bytes của file nén hoàn chỉnh, dictionary thống kê).
        API hoặc chương trình chạy thử chịu trách nhiệm nhận/lưu file."""
        frequency = self.count_frequency(input_bytes)
        root = self.build_tree(frequency)
        codes = self.build_codes(root)
        payload, padding = self.encode_data(input_bytes, codes)

        # File = header + bảng tần suất + dữ liệu nén.
        codebook = self.serialize_codebook(frequency)
        header = pack_header(self.algorithm_id, len(input_bytes), len(codebook), padding)
        compressed = header + codebook + payload
        stats = self.calculate_statistics(len(input_bytes), len(compressed))
        return compressed, stats

    def read_compressed_file(self, input_bytes):
        """Tách các thành phần và kiểm tra cấu trúc file nén input_bytes.

        Kiểm tra header, mã thuật toán, codebook, tổng tần suất và file rỗng.
        Trả về (bảng tần suất, payload, kích thước gốc, số bit đệm).
        Chưa giải mã payload; báo ValueError khi cấu trúc không hợp lệ."""
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

    def validate_payload(self, payload, codes, frequency, padding):
        """Kiểm tra độ dài bit và các bit đệm của payload trước khi giải mã.

        Dùng codes và frequency để tính số bit dữ liệu phải có.
        Các bit đệm cuối phải bằng 0. Không trả dữ liệu; báo ValueError nếu sai."""
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
        """Giải nén bytes của một file Huffman hoàn chỉnh thành bytes gốc.

        Đọc các thành phần, dựng lại cây từ tần suất, kiểm tra và giải mã payload.
        So sánh tần suất sau giải nén với codebook; báo ValueError nếu không khớp.
        Kiểm tra này không thay thế checksum, nên chưa phát hiện mọi cách sửa file."""
        frequency, payload, original_size, padding = self.read_compressed_file(input_bytes)
        if original_size == 0:
            return b""

        root = self.build_tree(frequency)
        codes = self.build_codes(root)
        self.validate_payload(payload, codes, frequency, padding)
        restored = self.decode_data(payload, root, original_size, padding)
        restored_frequency = self.count_frequency(restored)
        if restored_frequency != frequency:
            raise ValueError("Tần suất dữ liệu giải nén không khớp codebook.")
        return restored

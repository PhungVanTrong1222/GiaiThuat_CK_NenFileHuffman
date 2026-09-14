"""Kiểm thử Huffman trên file rỗng, văn bản và dữ liệu nhị phân.

Nén rồi giải nén phải giữ nguyên dữ liệu; file lỗi phải bị từ chối."""

import os
import unittest

from core import auto_decompress, get_compressor, list_algorithms


class HuffmanRoundTripTests(unittest.TestCase):
    def setUp(self):
        """Tạo đối tượng Huffman mới trước mỗi test; unittest tự gọi hàm này."""
        self.compressor = get_compressor()

    def assert_round_trip(self, data: bytes) -> None:
        """Nén rồi giải nén data (bytes), kiểm tra nội dung và thống kê.

        Không trả dữ liệu; assert báo test thất bại khi kết quả không khớp."""
        compressed, stats = self.compressor.compress_data(data)
        restored = auto_decompress(compressed)

        self.assertEqual(restored, data)
        self.assertEqual(stats["original_size"], len(data))
        self.assertEqual(stats["compressed_size"], len(compressed))
        self.assertEqual(stats["algorithm"], "huffman")

    def test_supported_algorithms(self):
        """Kiểm tra danh sách thuật toán chỉ gồm Huffman."""
        self.assertEqual(list_algorithms(), ["huffman"])

    def test_empty_file(self):
        """Kiểm tra nén và khôi phục file rỗng."""
        self.assert_round_trip(b"")

    def test_single_byte(self):
        """Kiểm tra file chỉ có một byte X."""
        self.assert_round_trip(b"X")

    def test_repeated_bytes(self):
        """Kiểm tra một loại byte lặp 10.000 lần."""
        self.assert_round_trip(b"A" * 10_000)

    def test_vietnamese_utf8(self):
        """Kiểm tra văn bản tiếng Việt UTF-8 được khôi phục nguyên vẹn."""
        self.assert_round_trip(
            "Thuật toán Huffman nén dữ liệu không mất mát.".encode("utf-8")
        )

    def test_all_byte_values(self):
        """Kiểm tra đủ 256 giá trị byte."""
        self.assert_round_trip(bytes(range(256)) * 4)

    def test_random_binary_data(self):
        """Kiểm tra nén rồi giải nén 4.096 byte ngẫu nhiên."""
        self.assert_round_trip(os.urandom(4096))

    def test_rejects_unknown_algorithm(self):
        """Kiểm tra tên thuật toán không hỗ trợ gây ValueError."""
        with self.assertRaises(ValueError):
            get_compressor("unknown")

    def test_rejects_invalid_magic_bytes(self):
        """Kiểm tra file không có dấu nhận diện ShrinkIT bị từ chối."""
        with self.assertRaises(ValueError):
            auto_decompress(b"not-a-shrinkit-file")

    def test_rejects_truncated_data(self):
        """Bỏ byte cuối file nén và kiểm tra giải nén báo lỗi."""
        compressed, _ = self.compressor.compress_data(b"abcde " * 100)

        with self.assertRaises(ValueError):
            auto_decompress(compressed[:-1])


if __name__ == "__main__":
    unittest.main()

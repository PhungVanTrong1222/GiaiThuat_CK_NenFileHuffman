import os
import unittest

from core import auto_decompress, get_compressor, list_algorithms


class HuffmanRoundTripTests(unittest.TestCase):
    def setUp(self):
        self.compressor = get_compressor()

    def assert_round_trip(self, data: bytes) -> None:
        compressed, stats = self.compressor.compress_data(data)
        restored = auto_decompress(compressed)

        self.assertEqual(restored, data)
        self.assertEqual(stats["original_size"], len(data))
        self.assertEqual(stats["compressed_size"], len(compressed))
        self.assertEqual(stats["algorithm"], "huffman")

    def test_supported_algorithms(self):
        self.assertEqual(list_algorithms(), ["huffman"])

    def test_empty_file(self):
        self.assert_round_trip(b"")

    def test_single_byte(self):
        self.assert_round_trip(b"X")

    def test_repeated_bytes(self):
        self.assert_round_trip(b"A" * 10_000)

    def test_vietnamese_utf8(self):
        self.assert_round_trip(
            "Thuật toán Huffman nén dữ liệu không mất mát.".encode("utf-8")
        )

    def test_all_byte_values(self):
        self.assert_round_trip(bytes(range(256)) * 4)

    def test_random_binary_data(self):
        self.assert_round_trip(os.urandom(4096))

    def test_rejects_unknown_algorithm(self):
        with self.assertRaises(ValueError):
            get_compressor("unknown")

    def test_rejects_invalid_magic_bytes(self):
        with self.assertRaises(ValueError):
            auto_decompress(b"not-a-shrinkit-file")

    def test_rejects_truncated_data(self):
        compressed, _ = self.compressor.compress_data(b"abcde " * 100)

        with self.assertRaises(ValueError):
            auto_decompress(compressed[:-1])


if __name__ == "__main__":
    unittest.main()

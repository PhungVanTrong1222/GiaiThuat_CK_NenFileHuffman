"""Kiểm thử file nén hỏng, tương thích file cũ và giới hạn API.

Dùng unittest và TestClient, không cần bật server thật."""

import asyncio
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from api.main import app
from core import get_compressor, auto_decompress
from core.file_format import pack_header


class ValidationTests(unittest.TestCase):
    def test_reads_legacy_file(self):
        """Kiểm tra đọc mẫu file cũ và tạo lại đúng các byte của mẫu đó."""
        data = bytes.fromhex(
            "534b010000000b00000026017b223937223a352c223938223a322c22313134223a32"
            "2c223939223a312c22313030223a317d7c8af8"
        )
        self.assertEqual(auto_decompress(data), b"abracadabra")
        self.assertEqual(get_compressor().compress_data(b"abracadabra")[0], data)

    def test_invalid_codebooks(self):
        """Thử bảng tần suất sai kiểu, trùng khóa, sai giá trị và JSON lồng quá sâu.

        Mỗi mẫu phải gây ValueError; subTest cho biết mẫu nào thất bại."""
        for book in (b"[]", b"null", b"1", b'{"65":true}', b'{"65":1.0}',
                     b'{"65":-1}', b'{"256":1}', b'{"065":1}',
                     b'{"65":1,"65":1}', b'{"65":[]}', b"\xff",
                     b'{"65":' + b"[" * 1500 + b"]" * 1500 + b"}"):
            with self.subTest(book=book[:60]):
                data = pack_header(1, 1, len(book), 7) + book + b"\x00"
                with self.assertRaises(ValueError):
                    auto_decompress(data)

    def test_empty_file_is_validated(self):
        """Kiểm tra file khai báo rỗng vẫn phải có codebook và padding hợp lệ."""
        valid, _ = get_compressor().compress_data(b"")
        for data in (valid[:-1], valid + b"\x00",
                     pack_header(1, 0, 2, 8) + b"{}",
                     pack_header(1, 0, 2, 1) + b"{}",
                     pack_header(1, 0, 7, 0) + b'{"0":1}'):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    auto_decompress(data)

    def test_padding_truncation_and_trailing_bytes(self):
        """Kiểm tra thiếu byte, thừa byte và bit đệm khác 0 đều bị phát hiện."""
        valid, _ = get_compressor().compress_data(b"A" * 9)
        for data in (valid[:-1], valid + b"\x00", valid[:-1] + b"\x01"):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    auto_decompress(data)

    def test_detects_wrong_decoded_frequencies(self):
        """Kiểm tra payload có tần suất khác codebook bị từ chối."""
        book = b'{"65":2,"66":2}'
        with self.assertRaises(ValueError):
            auto_decompress(pack_header(1, 4, len(book), 4) + book + b"\x00")

    def test_bit_boundaries(self):
        """Thử nhiều độ dài quanh mốc 8 bit và kiểm tra khôi phục đúng."""
        for size in range(1, 34):
            for data in (b"A" * size, bytes(range(size)), b"abac" * size):
                compressed, _ = get_compressor().compress_data(data)
                self.assertEqual(auto_decompress(compressed), data)


class ApiValidationTests(unittest.TestCase):
    def setUp(self):
        """Mở TestClient trước mỗi test và đăng ký đóng sau test kể cả khi có lỗi."""
        self.context = TestClient(app)
        self.client = self.context.__enter__()
        self.addCleanup(self.context.__exit__, None, None, None)

    def post(self, endpoint, data):
        """Gửi data dưới dạng file test.bin đến endpoint và trả phản hồi HTTP."""
        uploaded_file = ("test.bin", data)
        form_files = {"file": uploaded_file}
        response = self.client.post(endpoint, files=form_files)
        return response

    def test_upload_limits_and_expanded_file(self):
        """Kiểm tra giới hạn upload, giải nén và file nén lớn hơn bản gốc.

        patch tạm giảm giới hạn để test nhẹ; hết with thì cấu hình tự trở lại."""
        with patch("api.main.MAX_FILE_SIZE", 256):
            self.assertEqual(self.post("/api/compress", b"a" * 257).status_code, 413)
            raw = bytes(range(256))
            compressed = self.post("/api/compress", raw)
            self.assertEqual(compressed.status_code, 200)
            self.assertGreater(len(compressed.content), len(raw))
            restored = self.post("/api/decompress", compressed.content)
            self.assertEqual(restored.status_code, 200)
            self.assertEqual(restored.content, raw)
            oversized, _ = get_compressor().compress_data(b"a" * 257)
            self.assertEqual(self.post("/api/decompress", oversized).status_code, 413)
        with patch("api.main.MAX_COMPRESSED_SIZE", 10):
            self.assertEqual(self.post("/api/decompress", b"x" * 11).status_code, 413)

    def test_malformed_codebook_returns_400(self):
        """Kiểm tra codebook sai kiểu trả HTTP 400 thay vì lỗi 500."""
        self.assertEqual(self.post("/api/decompress",
            pack_header(1, 1, 2, 7) + b"[]" + b"\x00").status_code, 400)

    def test_missing_file(self):
        """Kiểm tra yêu cầu không có file trả HTTP 422."""
        self.assertEqual(self.client.post("/api/compress").status_code, 422)

    def test_codec_runs_outside_event_loop(self):
        """Thay tạm hàm nén để xác nhận thuật toán chạy ngoài event loop của API."""
        original = get_compressor().compress_data
        worker_threads = []

        def checked(data):
            """Ghi nhận thread, kiểm tra không có event loop chạy ở đây,
            sau đó gọi hàm nén gốc với data và trả kết quả."""
            worker_threads.append(threading.get_ident())
            with self.assertRaises(RuntimeError):
                asyncio.get_running_loop()
            return original(data)

        with patch("core.huffman.HuffmanCompressor.compress_data", side_effect=checked):
            self.assertEqual(self.post("/api/compress", b"abc").status_code, 200)
        self.assertEqual(len(worker_threads), 1)

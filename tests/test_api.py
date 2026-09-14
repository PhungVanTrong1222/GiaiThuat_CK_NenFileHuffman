import unittest

from fastapi.testclient import TestClient

from api.main import app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "algorithms": ["huffman"]},
        )

    def test_compress_and_decompress(self):
        original = "Dữ liệu kiểm thử Huffman\n".encode("utf-8") * 100

        compressed = self.client.post(
            "/api/compress",
            files={"file": ("dulieu.txt", original, "text/plain")},
        )

        self.assertEqual(compressed.status_code, 200)
        self.assertEqual(compressed.headers["x-original-size"], str(len(original)))
        self.assertEqual(compressed.headers["x-compression-algorithm"], "huffman")
        self.assertIn(
            'filename="dulieu.txt.huff"',
            compressed.headers["content-disposition"],
        )

        restored = self.client.post(
            "/api/decompress",
            files={
                "file": (
                    "dulieu.txt.huff",
                    compressed.content,
                    "application/octet-stream",
                )
            },
        )

        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.content, original)
        self.assertIn(
            'filename="dulieu.txt"',
            restored.headers["content-disposition"],
        )

    def test_empty_file(self):
        compressed = self.client.post(
            "/api/compress",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        restored = self.client.post(
            "/api/decompress",
            files={
                "file": (
                    "empty.txt.huff",
                    compressed.content,
                    "application/octet-stream",
                )
            },
        )

        self.assertEqual(compressed.status_code, 200)
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.content, b"")

    def test_rejects_invalid_compressed_file(self):
        response = self.client.post(
            "/api/decompress",
            files={
                "file": (
                    "invalid.huff",
                    b"invalid-data",
                    "application/octet-stream",
                )
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("format ShrinkIT", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()

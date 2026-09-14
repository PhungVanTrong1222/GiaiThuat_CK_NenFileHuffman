"""Chạy: python -m core.benchmark để đo thời gian và kiểm tra kết quả Huffman."""

import time

from core import get_compressor


def generate_test_data() -> dict:
    """Tạo dữ liệu văn bản, lặp byte, CSV, log và đủ 256 giá trị byte.

    Trả dictionary {tên bộ dữ liệu: bytes}; các dữ liệu được tạo trong RAM,
    không tải từ mạng và không ghi file."""
    datasets = {}

    # 1. Text tiếng Anh (tần suất ký tự lệch → Huffman tốt)
    english_text = (
        "The quick brown fox jumps over the lazy dog. " * 500 +
        "Algorithm analysis and design is a fundamental course. " * 300 +
        "Data compression reduces storage costs significantly. " * 200
    )
    datasets["Text tiếng Anh"] = english_text.encode('utf-8')

    # 2. Dữ liệu lặp nhiều
    repetitive_data = b"A" * 10000 + b"B" * 8000 + b"C" * 5000 + b"A" * 7000
    datasets["Dữ liệu lặp"] = repetitive_data

    # 3. File CSV giả lập
    csv_lines = ["id,name,email,status,created_at"]
    for i in range(1000):
        csv_lines.append(f"{i},user_{i},user_{i}@example.com,active,2025-01-{(i%28)+1:02d}")
    csv_data = "\n".join(csv_lines)
    datasets["File CSV"] = csv_data.encode('utf-8')

    # 4. File log giả lập
    log_lines = []
    for i in range(500):
        log_lines.append(f"[2025-09-12 10:{i%60:02d}:{i%60:02d}] INFO  - Request processed successfully, status=200, duration={i*2}ms")
        log_lines.append(f"[2025-09-12 10:{i%60:02d}:{i%60:02d}] DEBUG - Database query executed in {i}ms")
    log_data = "\n".join(log_lines)
    datasets["File Log"] = log_data.encode('utf-8')

    # 5. Dữ liệu hỗn hợp (mix byte values)
    mixed_data = bytes(range(256)) * 100
    datasets["Dữ liệu hỗn hợp"] = mixed_data

    return datasets


def format_size(size_bytes: int) -> str:
    """Đổi số byte thành chuỗi dung lượng dễ đọc.

    Trả chuỗi B, KB hoặc MB; các mức trong hàm dùng hệ số 1024."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def run_benchmark():
    """Đo thời gian nén, giải nén và in thống kê cho từng bộ dữ liệu.

    Không nhận tham số, không trả kết quả. Dùng perf_counter để đo thời gian.
    Báo ValueError nếu dữ liệu giải nén khác dữ liệu gốc."""
    datasets = generate_test_data()
    compressor = get_compressor()

    for dataset_name, original_data in datasets.items():
        start_time = time.perf_counter()
        compressed_data, statistics = compressor.compress_data(original_data)
        compression_time = time.perf_counter() - start_time

        start_time = time.perf_counter()
        restored_data = compressor.decompress_data(compressed_data)
        decompression_time = time.perf_counter() - start_time

        print()
        print("Dữ liệu:", dataset_name)
        print("Dung lượng gốc:", format_size(len(original_data)))
        print("Dung lượng nén:", format_size(len(compressed_data)))
        print("Phần trăm giảm dung lượng:", statistics["compression_ratio"])
        print("Thời gian nén (giây):", round(compression_time, 4))
        print("Thời gian giải nén (giây):", round(decompression_time, 4))

        if restored_data != original_data:
            raise ValueError("Kết quả giải nén không khớp: " + dataset_name)
        print("Kết quả: khớp dữ liệu gốc")


def run_edge_case_tests():
    """Chạy thử file rỗng, byte lặp, byte 0, dữ liệu nhị phân và tiếng Việt.

    In tên trường hợp đạt; báo ValueError ngay nếu nén rồi giải nén không khớp.
    Không nhận tham số và không trả dữ liệu."""
    test_cases = {
        "File rỗng": b"",
        "Một byte": b"X",
        "Một byte lặp": b"A" * 1000,
        "Hai byte xen kẽ": b"AB" * 500,
        "Đủ 256 giá trị byte": bytes(range(256)),
        "Byte bằng 0": b"\x00" * 500,
        "Tiếng Việt": "Xin chào thế giới!".encode("utf-8"),
    }
    compressor = get_compressor()
    for test_name, original_data in test_cases.items():
        compressed_data, statistics = compressor.compress_data(original_data)
        restored_data = compressor.decompress_data(compressed_data)
        if restored_data != original_data:
            raise ValueError("Kiểm tra thất bại: " + test_name)
        print("Đạt:", test_name)


if __name__ == "__main__":
    run_benchmark()
    run_edge_case_tests()

"""
ShrinkIT - Benchmark Script
==============================
Đánh giá hiệu suất thuật toán Huffman trên nhiều loại dữ liệu.

Cách chạy:
    cd DETAICUOIKI
    python -m core.benchmark

Kết quả:
    - Bảng so sánh: kích thước gốc, kích thước nén, tỷ lệ nén, thời gian
    - Kiểm tra tính đúng đắn: nén → giải nén → so sánh với file gốc
"""

import time
import os
import sys

# Thêm thư mục cha vào path để import core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import get_compressor, list_algorithms


def generate_test_data() -> dict:
    """
    Tạo các bộ dữ liệu test đa dạng để benchmark.
    
    Returns:
        dict: {tên_test: bytes_data}
    """
    datasets = {}
    
    # 1. Text tiếng Anh (tần suất ký tự lệch → Huffman tốt)
    english_text = (
        "The quick brown fox jumps over the lazy dog. " * 500 +
        "Algorithm analysis and design is a fundamental course. " * 300 +
        "Data compression reduces storage costs significantly. " * 200
    )
    datasets["Text tiếng Anh (~50KB)"] = english_text.encode('utf-8')
    
    # 2. Dữ liệu lặp nhiều
    repetitive_data = b"A" * 10000 + b"B" * 8000 + b"C" * 5000 + b"A" * 7000
    datasets["Dữ liệu lặp (~30KB)"] = repetitive_data
    
    # 3. File CSV giả lập
    csv_lines = []
    for i in range(1000):
        csv_lines.append(f"id,name,email,status,created_at")
        csv_lines.append(f"{i},user_{i},user_{i}@example.com,active,2025-01-{(i%28)+1:02d}")
    csv_data = "\n".join(csv_lines)
    datasets["File CSV (~80KB)"] = csv_data.encode('utf-8')
    
    # 4. File log giả lập
    log_lines = []
    for i in range(500):
        log_lines.append(f"[2025-09-12 10:{i%60:02d}:{i%60:02d}] INFO  - Request processed successfully, status=200, duration={i*2}ms")
        log_lines.append(f"[2025-09-12 10:{i%60:02d}:{i%60:02d}] DEBUG - Database query executed in {i}ms")
    log_data = "\n".join(log_lines)
    datasets["File Log (~65KB)"] = log_data.encode('utf-8')
    
    # 5. Dữ liệu hỗn hợp (mix byte values)
    mixed_data = bytes(range(256)) * 100
    datasets["Dữ liệu hỗn hợp (~25KB)"] = mixed_data
    
    return datasets


def format_size(size_bytes: int) -> str:
    """Format kích thước bytes thành chuỗi dễ đọc."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def run_benchmark():
    """Chạy benchmark và in kết quả."""
    
    print("=" * 90)
    print("  ShrinkIT - BENCHMARK THUẬT TOÁN HUFFMAN")
    print("=" * 90)
    
    algorithms = list_algorithms()
    datasets = generate_test_data()
    
    for dataset_name, data in datasets.items():
        print(f"\n{'─' * 90}")
        print(f"  📁 Dataset: {dataset_name}")
        print(f"  📏 Kích thước gốc: {format_size(len(data))}")
        print(f"{'─' * 90}")
        
        # Header bảng
        print(f"  {'Thuật toán':<12} │ {'Kích thước nén':>14} │ {'Tỷ lệ nén':>10} │ "
              f"{'T/g nén':>10} │ {'T/g giải nén':>12} │ {'Đúng đắn':>8}")
        print(f"  {'─' * 12}─┼─{'─' * 14}─┼─{'─' * 10}─┼─"
              f"{'─' * 10}─┼─{'─' * 12}─┼─{'─' * 8}")
        
        for algo_name in algorithms:
            compressor = get_compressor(algo_name)
            
            # Đo thời gian nén
            start = time.perf_counter()
            compressed, stats = compressor.compress_data(data)
            compress_time = time.perf_counter() - start
            
            # Đo thời gian giải nén
            start = time.perf_counter()
            decompressed = compressor.decompress_data(compressed)
            decompress_time = time.perf_counter() - start
            
            # Kiểm tra tính đúng đắn
            is_correct = decompressed == data
            correct_str = "✅ OK" if is_correct else "❌ FAIL"
            
            # Tỷ lệ nén
            ratio = stats["compression_ratio"]
            ratio_str = f"{ratio:+.1f}%" if ratio >= 0 else f"{ratio:.1f}%"
            
            # In kết quả
            print(f"  {algo_name.upper():<12} │ {format_size(len(compressed)):>14} │ "
                  f"{ratio_str:>10} │ {compress_time*1000:>8.1f}ms │ "
                  f"{decompress_time*1000:>10.1f}ms │ {correct_str:>8}")
    
    # Tổng kết
    print(f"\n{'=' * 90}")
    print("PHÂN TÍCH & NHẬN XÉT")
    print(f"{'=' * 90}")
    print("""
  • Huffman phù hợp với dữ liệu văn bản có phân bố tần suất byte không đều.
  • File nhỏ hoặc dữ liệu có phân bố gần đồng đều có thể lớn hơn bản gốc
    do chi phí lưu header và bảng tần suất.
  • Tất cả kết quả phải được xác nhận bằng phép thử giải nén khớp 100%.
    """)


def run_edge_case_tests():
    """Test các trường hợp biên (edge cases)."""
    
    print(f"\n{'=' * 90}")
    print("KIỂM TRA EDGE CASES")
    print(f"{'=' * 90}")
    
    test_cases = {
        "File rỗng": b"",
        "1 byte": b"X",
        "1 ký tự lặp 1000 lần": b"A" * 1000,
        "2 ký tự xen kẽ": b"AB" * 500,
        "Tất cả 256 byte values": bytes(range(256)),
        "Chỉ null bytes": b"\x00" * 500,
        "Text UTF-8 tiếng Việt": "Xin chào thế giới! Đây là bài test tiếng Việt có dấu.".encode('utf-8'),
    }
    
    algorithms = list_algorithms()
    all_passed = True
    
    for test_name, data in test_cases.items():
        results = []
        for algo_name in algorithms:
            compressor = get_compressor(algo_name)
            try:
                compressed, stats = compressor.compress_data(data)
                decompressed = compressor.decompress_data(compressed)
                passed = decompressed == data
                results.append((algo_name, passed))
                if not passed:
                    all_passed = False
            except Exception as e:
                results.append((algo_name, False))
                all_passed = False
        
        status = " | ".join(
            f"{name.upper()}: {'✓' if ok else '✗'}" for name, ok in results
        )
        print(f"  {test_name:<30} → {status}")
    
    print(f"\n  {'TẤT CẢ TESTS PASSED!' if all_passed else 'CÓ TEST THẤT BẠI!'}")


if __name__ == "__main__":
    run_benchmark()
    run_edge_case_tests()

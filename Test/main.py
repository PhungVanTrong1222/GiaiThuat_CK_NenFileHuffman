"""Chạy thử Huffman với file thật: python Test/main.py [đường_dẫn_file].

Mặc định đọc data/sample.txt, ghi output.huff và restored.txt trong data/,
rồi so sánh với dữ liệu gốc. Chỉ chạy trực tiếp, không chạy khi import."""

import argparse
import os
import sys

SCRIPT_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
# Cho phép chạy file từ thư mục khác mà vẫn import được core.
sys.path.insert(0, PROJECT_DIR)

from core import get_compressor

DEFAULT_INPUT = os.path.join(PROJECT_DIR, "data", "sample.txt")
COMPRESSED_FILE = os.path.join(PROJECT_DIR, "data", "output.huff")
DECOMPRESSED_FILE = os.path.join(PROJECT_DIR, "data", "restored.txt")

def main():
    """Đọc đường dẫn từ dòng lệnh và chạy thử nén, giải nén trên một file.

    Không truyền đường dẫn thì dùng data/sample.txt. Ghi kết quả vào
    output.huff và restored.txt trong data/, thay thế file kết quả nếu đã có.
    In dung lượng, tỷ lệ nén và kết quả so sánh; không trả dữ liệu."""
    parser = argparse.ArgumentParser(description="Kiểm tra nén và giải nén Huffman.")
    parser.add_argument(
        "input_file",
        nargs="?",
        default=DEFAULT_INPUT,
        help="File cần kiểm tra; mặc định là data/sample.txt.",
    )
    args = parser.parse_args()
    input_file = os.path.abspath(args.input_file)

    # ============================
    # 1. Đọc file gốc
    # ============================
    with open(input_file, "rb") as file:
        original_data = file.read()

    print(f"File gốc: {input_file}")
    print(f"Kích thước gốc: {len(original_data):,} bytes ({len(original_data)/1024:.1f} KB)")
    print()

    # ============================
    # 2. Nén file
    # ============================
    compressor = get_compressor("huffman")
    compressed_data, stats = compressor.compress_data(original_data)

    # Lưu file nén
    with open(COMPRESSED_FILE, "wb") as file:
        file.write(compressed_data)

    print(f"Nén xong → {COMPRESSED_FILE}")
    print(f"Kích thước nén: {stats['compressed_size']:,} bytes ({stats['compressed_size']/1024:.1f} KB)")
    print(f"Tỷ lệ nén: {stats['compression_ratio']}%")
    print()

    # ============================
    # 3. Giải nén file
    # ============================
    with open(COMPRESSED_FILE, "rb") as file:
        compressed_from_file = file.read()

    restored_data = compressor.decompress_data(compressed_from_file)

    # Lưu file giải nén
    with open(DECOMPRESSED_FILE, "wb") as file:
        file.write(restored_data)

    print(f"Giải nén xong → {DECOMPRESSED_FILE}")
    print(f"Kích thước phục hồi: {len(restored_data):,} bytes")
    print()

    # ============================
    # 4. Kiểm tra tính đúng đắn
    # ============================
    if original_data == restored_data:
        print("Kết quả: KHỚP 100% — Nén/giải nén thành công!")
    else:
        print("Kết quả: KHÔNG KHỚP — Có lỗi!")


if __name__ == "__main__":
    main()

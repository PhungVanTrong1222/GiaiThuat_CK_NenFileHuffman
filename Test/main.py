import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import get_compressor

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT = os.path.join(PROJECT_DIR, "data", "sample.txt")
COMPRESSED_FILE = os.path.join(PROJECT_DIR, "data", "output.bin")
DECOMPRESSED_FILE = os.path.join(PROJECT_DIR, "data", "restored.txt")

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
with open(input_file, "rb") as f:
    original_data = f.read()

print(f"File gốc: {input_file}")
print(f"Kích thước gốc: {len(original_data):,} bytes ({len(original_data)/1024:.1f} KB)")
print()

# ============================
# 2. Nén file
# ============================
huff = get_compressor("huffman")
compressed_data, stats = huff.compress_data(original_data)

# Lưu file nén
with open(COMPRESSED_FILE, "wb") as f:
    f.write(compressed_data)

print(f"Nén xong → {COMPRESSED_FILE}")
print(f"Kích thước nén: {stats['compressed_size']:,} bytes ({stats['compressed_size']/1024:.1f} KB)")
print(f"Tỷ lệ nén: {stats['compression_ratio']}%")
print()

# ============================
# 3. Giải nén file
# ============================
with open(COMPRESSED_FILE, "rb") as f:
    compressed_from_file = f.read()

restored_data = huff.decompress_data(compressed_from_file)

# Lưu file giải nén
with open(DECOMPRESSED_FILE, "wb") as f:
    f.write(restored_data)

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

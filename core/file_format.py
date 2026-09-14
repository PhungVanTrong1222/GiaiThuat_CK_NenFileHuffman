"""Cấu trúc file: header 12 byte + bảng tần suất JSON + dữ liệu nén.

Header gồm:
- 2 byte nhận diện SK.
- 1 byte mã thuật toán (1 = Huffman).
- 4 byte kích thước gốc.
- 4 byte kích thước bảng tần suất.
- 1 byte số bit đệm.
Giữ nguyên cấu trúc này để đọc được file .huff và .bin đã tạo trước đây.
"""

import struct

MAGIC_BYTES = b"SK"
HUFFMAN_ID = 1
HEADER_SIZE = 12
# >: số lớn trước; 2s: 2 byte; B: số 1 byte; I: số 4 byte.
HEADER_FORMAT = ">2s B I I B"


def pack_header(algorithm_id, original_size, codebook_size, padding_bits):
    """Ghi các thông tin đầu file thành 12 byte."""
    header = struct.pack(
        HEADER_FORMAT,
        MAGIC_BYTES,
        algorithm_id,
        original_size,
        codebook_size,
        padding_bits,
    )
    return header


def unpack_header(data):
    """Đọc 12 byte đầu và trả về dictionary thông tin file."""
    if len(data) < HEADER_SIZE:
        raise ValueError("File quá nhỏ, cần ít nhất 12 byte header.")

    header_bytes = data[:HEADER_SIZE]
    fields = struct.unpack(HEADER_FORMAT, header_bytes)
    magic = fields[0]
    algorithm_id = fields[1]
    original_size = fields[2]
    codebook_size = fields[3]
    padding_bits = fields[4]

    if magic != MAGIC_BYTES:
        raise ValueError("File không phải format ShrinkIT.")

    algorithm_name = "unknown"
    if algorithm_id == HUFFMAN_ID:
        algorithm_name = "huffman"

    return {
        "magic": magic,
        "algorithm_id": algorithm_id,
        "algorithm_name": algorithm_name,
        "original_size": original_size,
        "codebook_size": codebook_size,
        "padding_bits": padding_bits,
    }

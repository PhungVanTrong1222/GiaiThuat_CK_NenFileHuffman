"""Cung cấp các hàm gọi Huffman cho API và chương trình chạy thử.

Cho phép from core import get_compressor, auto_decompress.
Thuật toán ở huffman.py; header file ở file_format.py."""

from .huffman import HuffmanCompressor


def get_compressor(algorithm="huffman"):
    """Nhận tên thuật toán và trả một đối tượng HuffmanCompressor mới.

    Bỏ khoảng trắng, chuyển tên về chữ thường; tên khác huffman gây ValueError."""
    algorithm = algorithm.lower().strip()
    if algorithm != "huffman":
        raise ValueError("Thuật toán không hỗ trợ: " + algorithm)
    compressor = HuffmanCompressor()
    return compressor


def auto_decompress(input_bytes):
    """Nhận bytes của file nén và trả bytes được khôi phục bởi Huffman.

    Tên hàm được giữ cho các nơi gọi; hiện dự án chỉ hỗ trợ Huffman.
    Lỗi kiểm tra file của Huffman được chuyển nguyên ra cho nơi gọi xử lý."""
    compressor = HuffmanCompressor()
    restored_data = compressor.decompress_data(input_bytes)
    return restored_data


def list_algorithms():
    """Trả danh sách tên thuật toán được hỗ trợ: hiện chỉ có huffman."""
    return ["huffman"]

"""Các hàm để API và chương trình chạy thử sử dụng Huffman."""

from .huffman import HuffmanCompressor


def get_compressor(algorithm="huffman"):
    """Tạo đối tượng nén; dự án chỉ hỗ trợ Huffman."""
    algorithm = algorithm.lower().strip()
    if algorithm != "huffman":
        raise ValueError("Thuật toán không hỗ trợ: " + algorithm)
    compressor = HuffmanCompressor()
    return compressor


def auto_decompress(input_bytes):
    """Huffman tự kiểm tra header trước khi giải nén."""
    compressor = HuffmanCompressor()
    restored_data = compressor.decompress_data(input_bytes)
    return restored_data


def list_algorithms():
    return ["huffman"]

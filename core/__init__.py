"""
ShrinkIT - Core Module
========================
Export HuffmanCompressor và cung cấp factory function để backend
sử dụng thống nhất một thuật toán nén duy nhất.

Cách sử dụng:
    from core import get_compressor
    
    compressor = get_compressor("huffman")
    compressed_bytes, stats = compressor.compress_data(file_bytes)
    original_bytes = compressor.decompress_data(compressed_bytes)
"""

from .huffman import HuffmanCompressor
from .base_compressor import BaseCompressor, unpack_header

# Giữ registry để backend có thể dùng cùng một giao diện ổn định.
_COMPRESSORS = {
    "huffman": HuffmanCompressor,
}


def get_compressor(algorithm: str = "huffman") -> BaseCompressor:
    """
    Factory function: trả về compressor phù hợp theo tên thuật toán.
    
    Args:
        algorithm: Tên thuật toán. Hiện chỉ hỗ trợ "huffman".
    
    Returns:
        BaseCompressor: Instance của compressor tương ứng
    
    Raises:
        ValueError: Nếu tên thuật toán không hợp lệ
    
    Ví dụ:
        >>> compressor = get_compressor("huffman")
        >>> compressed, stats = compressor.compress_data(b"Hello World")
        >>> original = compressor.decompress_data(compressed)
        >>> assert original == b"Hello World"
    """
    algorithm = algorithm.lower().strip()
    
    if algorithm not in _COMPRESSORS:
        available = ", ".join(_COMPRESSORS.keys())
        raise ValueError(
            f"Thuật toán '{algorithm}' không hỗ trợ. "
            f"Các thuật toán hợp lệ: {available}"
        )
    
    return _COMPRESSORS[algorithm]()


def auto_decompress(input_bytes: bytes) -> bytes:
    """
    Tự động nhận diện thuật toán từ header và giải nén.
    
    Đọc algorithm_id từ header file .bin → chọn đúng compressor → giải nén.
    Người dùng không cần biết file được nén bằng thuật toán nào.
    
    Args:
        input_bytes: File .bin đã nén
    
    Returns:
        bytes: Dữ liệu gốc
    """
    header = unpack_header(input_bytes)
    algo_name = header["algorithm_name"]
    
    if algo_name == "unknown":
        raise ValueError(f"Không nhận diện được thuật toán (ID: {header['algorithm_id']})")
    
    compressor = get_compressor(algo_name)
    return compressor.decompress_data(input_bytes)


def list_algorithms() -> list[str]:
    """Trả về danh sách thuật toán ShrinkIT đang hỗ trợ."""
    return list(_COMPRESSORS.keys())

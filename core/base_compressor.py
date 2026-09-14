"""
ShrinkIT - Base Compressor Module
==================================
Định nghĩa abstract class BaseCompressor và các hàm tiện ích
để đọc/ghi header 12 bytes cho file nén .huff.

File Format (.huff, tương thích file .bin cũ):
    [Magic bytes]    2 bytes  - b"SK" (ShrinkIT identifier)
    [Algorithm ID]   1 byte   - 0x01=Huffman
    [Original size]  4 bytes  - Kích thước file gốc (big-endian)
    [Codebook size]  4 bytes  - Kích thước codebook (big-endian)
    [Padding bits]   1 byte   - Số bit padding ở byte cuối
    [Codebook data]  variable - Bảng mã (JSON serialized)
    [Compressed data] variable - Dữ liệu đã nén
"""

import struct
from abc import ABC, abstractmethod

# Constants
MAGIC_BYTES = b"SK"                # Nhận diện file ShrinkIT
HEADER_SIZE = 12                   # Tổng kích thước header cố định
HEADER_FORMAT = ">2s B I I B"      # Format struct: 2s=magic, B=algo_id, I=orig_size, I=codebook_size, B=padding

# Mapping Algorithm ID
ALGORITHM_IDS = {
    "huffman": 0x01,
}

ALGORITHM_NAMES = {v: k for k, v in ALGORITHM_IDS.items()}


# Header Utilities
def pack_header(algorithm_id: int, original_size: int, codebook_size: int, padding_bits: int) -> bytes:
    """
    Đóng gói header 12 bytes cho file nén.
    
    Args:
        algorithm_id:  ID thuật toán (0x01=Huffman)
        original_size: Kích thước file gốc (bytes)
        codebook_size: Kích thước codebook (bytes)
        padding_bits:  Số bit padding thêm vào byte cuối (0-7)
    
    Returns:
        bytes: Header 12 bytes
    """
    return struct.pack(
        HEADER_FORMAT,
        MAGIC_BYTES,
        algorithm_id,
        original_size,
        codebook_size,
        padding_bits
    )


def unpack_header(data: bytes) -> dict:
    """
    Giải mã header 12 bytes từ file nén.
    
    Args:
        data: Dữ liệu file nén (ít nhất 12 bytes)
    
    Returns:
        dict: {magic, algorithm_id, algorithm_name, original_size, codebook_size, padding_bits}
    
    Raises:
        ValueError: Nếu file không phải format ShrinkIT
    """
    if len(data) < HEADER_SIZE:
        raise ValueError(f"File quá nhỏ ({len(data)} bytes), cần ít nhất {HEADER_SIZE} bytes header.")
    
    magic, algo_id, original_size, codebook_size, padding_bits = struct.unpack(
        HEADER_FORMAT, data[:HEADER_SIZE]
    )
    
    if magic != MAGIC_BYTES:
        raise ValueError(f"File không phải format ShrinkIT (magic bytes: {magic!r}, cần: {MAGIC_BYTES!r})")
    
    return {
        "magic": magic,
        "algorithm_id": algo_id,
        "algorithm_name": ALGORITHM_NAMES.get(algo_id, "unknown"),
        "original_size": original_size,
        "codebook_size": codebook_size,
        "padding_bits": padding_bits,
    }


# Abstract Base Class
class BaseCompressor(ABC):
    """
    Lớp trừu tượng cho tất cả thuật toán nén trong ShrinkIT.
    
    Mỗi thuật toán cần implement 2 phương thức:
        - compress_data(input_bytes) -> (compressed_bytes, stats_dict)
        - decompress_data(input_bytes) -> original_bytes
    
    Trong đó compressed_bytes đã bao gồm header + codebook + data,
    là file .bin hoàn chỉnh có thể tự giải nén mà không cần thông tin bên ngoài.
    """
    
    @property
    @abstractmethod
    def algorithm_name(self) -> str:
        """Tên thuật toán (hiện tại là 'huffman')."""
        pass
    
    @property
    def algorithm_id(self) -> int:
        """ID thuật toán theo file format."""
        return ALGORITHM_IDS[self.algorithm_name]
    
    @abstractmethod
    def compress_data(self, input_bytes: bytes) -> tuple:
        """
        Nén dữ liệu.
        
        Args:
            input_bytes: Dữ liệu gốc cần nén
        
        Returns:
            tuple: (compressed_bytes, stats_dict)
                - compressed_bytes: File .bin hoàn chỉnh (header + codebook + data)
                - stats_dict: {
                    "original_size": int,
                    "compressed_size": int,
                    "compression_ratio": float,  # tỷ lệ % đã nén được
                    "algorithm": str
                  }
        """
        pass
    
    @abstractmethod
    def decompress_data(self, input_bytes: bytes) -> bytes:
        """
        Giải nén dữ liệu.
        
        Args:
            input_bytes: File .bin đã nén (bao gồm header + codebook + data)
        
        Returns:
            bytes: Dữ liệu gốc
        
        Raises:
            ValueError: Nếu file không hợp lệ hoặc sai thuật toán
        """
        pass
    
    def _build_stats(self, original_size: int, compressed_size: int) -> dict:
        """Tạo dictionary thống kê kết quả nén."""
        if original_size == 0:
            ratio = 0.0
        else:
            ratio = (1 - compressed_size / original_size) * 100
        
        return {
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": round(ratio, 2),
            "algorithm": self.algorithm_name,
        }
    
    def _validate_header(self, header: dict) -> None:
        """Kiểm tra header có đúng thuật toán không."""
        if header["algorithm_id"] != self.algorithm_id:
            raise ValueError(
                f"File được nén bằng '{header['algorithm_name']}', "
                f"không thể giải nén bằng '{self.algorithm_name}'."
            )

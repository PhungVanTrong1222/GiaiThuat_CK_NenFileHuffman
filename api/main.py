"""API nhận file từ giao diện, gọi Huffman và trả file kết quả.

Đọc hai hàm compress_file và decompress_file trước để thấy luồng chính.
Các hàm phía trên hỗ trợ đọc file, kiểm tra dung lượng và tạo phản hồi HTTP.
"""

import re
import unicodedata
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import Response

from core import auto_decompress, get_compressor, list_algorithms
from core.file_format import HEADER_SIZE, unpack_header
from core.huffman import HuffmanCompressor


# Giới hạn dung lượng tính bằng byte: 1 MiB = 1024 * 1024 byte.
MAX_FILE_SIZE = 25 * 1024 * 1024
MAX_COMPRESSED_SIZE = MAX_FILE_SIZE + HuffmanCompressor.MAX_CODEBOOK_SIZE + HEADER_SIZE
MAX_CONCURRENT_TASKS = 2


# Giống hai chỗ làm việc: tác vụ thứ ba phải chờ một chỗ trống.
processing_slots = BoundedSemaphore(MAX_CONCURRENT_TASKS)


app = FastAPI(
    title="ShrinkIT API",
    description="API nén và giải nén file bằng thuật toán Huffman.",
    version="1.0.0",
)


def safe_filename(filename, default_name):
    """Tạo tên file phù hợp để đặt trong header tải xuống."""
    if not filename:
        filename = default_name

    filename = Path(filename).name
    # Chuyển tên về ASCII và thay ký tự đặc biệt bằng dấu gạch dưới.
    filename = unicodedata.normalize("NFKD", filename)
    filename_bytes = filename.encode("ascii", "ignore")
    filename = filename_bytes.decode("ascii")
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    filename = filename.strip("._")

    if not filename:
        return default_name
    return filename


def read_uploaded_file(file, size_limit):
    """Đọc nội dung file; trả lỗi HTTP 413 nếu vượt giới hạn."""
    try:
        # Đọc thêm 1 byte để biết file có vượt giới hạn hay không.
        file_data = file.file.read(size_limit + 1)
    finally:
        # File tạm phải được đóng cả khi đọc thất bại.
        file.file.close()

    if len(file_data) > size_limit:
        raise HTTPException(
            status_code=413,
            detail=f"File vượt quá giới hạn {size_limit:,} byte.",
        )
    return file_data


def validate_restored_size(compressed_data):
    """Kiểm tra kích thước gốc trong header trước khi cấp bộ nhớ giải nén."""
    header = unpack_header(compressed_data)
    if header["original_size"] > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Dung lượng giải nén vượt quá {MAX_FILE_SIZE:,} byte.",
        )


def restored_filename(uploaded_name):
    """Ví dụ: baocao.txt.huff -> baocao.txt."""
    filename = safe_filename(uploaded_name, "file.huff")
    if filename.lower().endswith(".huff"):
        return filename[:-5]
    # File cũ có thể dùng đuôi .bin và không lưu tên gốc trong header.
    return filename + ".restored"


def download_response(file_data, filename, stats=None):
    """Đặt dữ liệu vào body và tên file, thống kê vào HTTP headers."""
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    if stats is not None:
        headers["X-Original-Size"] = str(stats["original_size"])
        headers["X-Compressed-Size"] = str(stats["compressed_size"])
        headers["X-Compression-Ratio"] = str(stats["compression_ratio"])
        headers["X-Compression-Algorithm"] = stats["algorithm"]

    response = Response(
        content=file_data,
        media_type="application/octet-stream",  # Dữ liệu file nhị phân.
        headers=headers,
    )
    return response


@app.get("/health")
def health_check():
    """Cho giao diện biết server đang hoạt động."""
    return {"status": "ok", "algorithms": list_algorithms()}


@app.post("/api/compress")
def compress_file(file: UploadFile):
    """Nhận file -> đọc dữ liệu -> nén Huffman -> trả file .huff."""
    # FastAPI tự chạy hàm def trong thread, nên không cần async/await ở đây.
    # with tự trả chỗ xử lý khi kết thúc, kể cả khi có lỗi.
    with processing_slots:
        # 1. Đọc file người dùng gửi lên.
        original_data = read_uploaded_file(file, MAX_FILE_SIZE)

        # 2. Tạo đối tượng Huffman và nén dữ liệu.
        compressor = get_compressor("huffman")
        compressed_data, stats = compressor.compress_data(original_data)

    # 3. Đặt tên file và gửi kết quả về trình duyệt.
    original_name = safe_filename(file.filename, "file")
    filename = original_name + ".huff"
    response = download_response(compressed_data, filename, stats)
    return response


@app.post("/api/decompress")
def decompress_file(file: UploadFile):
    """Nhận file nén -> kiểm tra -> giải nén Huffman -> trả dữ liệu gốc."""
    with processing_slots:
        # 1. Đọc file nén.
        compressed_data = read_uploaded_file(file, MAX_COMPRESSED_SIZE)
        try:
            # 2. Kiểm tra dung lượng gốc rồi giải nén.
            validate_restored_size(compressed_data)
            restored_data = auto_decompress(compressed_data)
        except ValueError as error:
            # Phần lõi báo ValueError; API chuyển thành lỗi HTTP 400 cho giao diện.
            raise HTTPException(status_code=400, detail=str(error)) from error

    # 3. Đặt tên file khôi phục và gửi về trình duyệt.
    filename = restored_filename(file.filename)
    response = download_response(restored_data, filename)
    return response

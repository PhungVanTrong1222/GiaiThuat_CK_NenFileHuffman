"""API nhận file từ giao diện, gọi Huffman và trả file kết quả.

Đọc hai hàm compress_file và decompress_file trước để thấy luồng chính.
Các hàm phía trên hỗ trợ đọc file, kiểm tra dung lượng và tạo phản hồi HTTP.
"""

import re
import unicodedata
from contextlib import asynccontextmanager
from pathlib import Path

from anyio import CapacityLimiter
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from core import auto_decompress, get_compressor, list_algorithms
from core.base_compressor import HEADER_SIZE, unpack_header
from core.huffman import HuffmanCompressor


# Giới hạn dung lượng tính bằng byte: 1 MiB = 1024 * 1024 byte.
MAX_FILE_SIZE = 25 * 1024 * 1024
MAX_COMPRESSED_SIZE = MAX_FILE_SIZE + HuffmanCompressor.MAX_CODEBOOK_SIZE + HEADER_SIZE
MAX_CONCURRENT_TASKS = 2


@asynccontextmanager
async def lifespan(app):
    """FastAPI gọi hàm này khi server khởi động và dừng."""
    # Mỗi tác vụ giữ dữ liệu trong RAM, nên chỉ cho hai tác vụ chạy cùng lúc.
    app.state.codec_limiter = CapacityLimiter(MAX_CONCURRENT_TASKS)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="ShrinkIT API",
    description="API nén và giải nén file bằng thuật toán Huffman.",
    version="1.0.0",
)


def safe_filename(filename: str | None, default_name: str) -> str:
    """Tạo tên file phù hợp để đặt trong header tải xuống."""
    if not filename:
        filename = default_name

    filename = Path(filename).name
    # Chuyển tên về ASCII và thay ký tự đặc biệt bằng dấu gạch dưới.
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    filename = filename.strip("._")

    if not filename:
        return default_name
    return filename


async def read_uploaded_file(file: UploadFile, size_limit: int) -> bytes:
    """Đọc nội dung file; trả lỗi HTTP 413 nếu vượt giới hạn."""
    try:
        # Đọc thêm 1 byte để biết file có vượt giới hạn hay không.
        file_data = await file.read(size_limit + 1)
    finally:
        # File tạm phải được đóng cả khi đọc thất bại.
        await file.close()

    if len(file_data) > size_limit:
        raise HTTPException(
            status_code=413,
            detail=f"File vượt quá giới hạn {size_limit:,} byte.",
        )
    return file_data


def validate_restored_size(compressed_data: bytes) -> None:
    """Kiểm tra kích thước gốc trong header trước khi cấp bộ nhớ giải nén."""
    header = unpack_header(compressed_data)
    if header["original_size"] > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Dung lượng giải nén vượt quá {MAX_FILE_SIZE:,} byte.",
        )


def restored_filename(uploaded_name: str | None) -> str:
    """Ví dụ: baocao.txt.huff -> baocao.txt."""
    filename = safe_filename(uploaded_name, "file.huff")
    if filename.lower().endswith(".huff"):
        return filename[:-5]
    # File cũ có thể dùng đuôi .bin và không lưu tên gốc trong header.
    return filename + ".restored"


def download_response(file_data: bytes, filename: str, stats: dict | None = None) -> Response:
    """Đặt dữ liệu vào body và tên file, thống kê vào HTTP headers."""
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    if stats is not None:
        headers["X-Original-Size"] = str(stats["original_size"])
        headers["X-Compressed-Size"] = str(stats["compressed_size"])
        headers["X-Compression-Ratio"] = str(stats["compression_ratio"])
        headers["X-Compression-Algorithm"] = stats["algorithm"]

    return Response(
        content=file_data,
        media_type="application/octet-stream",  # Dữ liệu file nhị phân.
        headers=headers,
    )


@app.get("/health")
def health_check() -> dict:
    """Cho giao diện biết server đang hoạt động."""
    return {"status": "ok", "algorithms": list_algorithms()}


@app.post("/api/compress")
async def compress_file(file: UploadFile) -> Response:
    """Nhận file -> đọc dữ liệu -> nén Huffman -> trả file .huff."""
    # async with: chờ một vị trí trống; tự trả vị trí khi xong hoặc gặp lỗi.
    async with app.state.codec_limiter:
        original_data = await read_uploaded_file(file, MAX_FILE_SIZE)
        compressor = get_compressor("huffman")

        # Huffman chạy trong thread để không chạy trực tiếp trên event loop.
        # await chờ kết quả, đồng thời cho server tiếp tục xử lý công việc khác.
        compressed_data, stats = await run_in_threadpool(
            compressor.compress_data, original_data
        )

    filename = safe_filename(file.filename, "file") + ".huff"
    return download_response(compressed_data, filename, stats)


@app.post("/api/decompress")
async def decompress_file(file: UploadFile) -> Response:
    """Nhận file nén -> kiểm tra -> giải nén Huffman -> trả dữ liệu gốc."""
    async with app.state.codec_limiter:
        compressed_data = await read_uploaded_file(file, MAX_COMPRESSED_SIZE)
        try:
            validate_restored_size(compressed_data)
            restored_data = await run_in_threadpool(auto_decompress, compressed_data)
        except ValueError as error:
            # Phần lõi báo ValueError; API chuyển thành lỗi HTTP 400 cho giao diện.
            raise HTTPException(status_code=400, detail=str(error)) from error

    filename = restored_filename(file.filename)
    return download_response(restored_data, filename)

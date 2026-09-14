"""API nhận file từ giao diện, gọi Huffman và trả file kết quả.

Đọc hai hàm compress_file và decompress_file trước để thấy luồng chính.
Các hàm phía trên hỗ trợ đọc file, kiểm tra dung lượng và tạo phản hồi HTTP.
"""

import re
import unicodedata
from pathlib import Path
from threading import BoundedSemaphore

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles

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


# Chỉ phục vụ thư mục web, không công khai mã Python hay dữ liệu dự án.
WEB_DIRECTORY = Path(__file__).resolve().parent.parent / "web"
app.mount("/static", StaticFiles(directory=WEB_DIRECTORY), name="static")


@app.get("/", include_in_schema=False)
def home_page():
    """Trả trang HTML chính; trình duyệt tải CSS và JavaScript từ /static."""
    return FileResponse(WEB_DIRECTORY / "index.html")


@app.get("/api/config")
def application_config():
    """Cho giao diện biết giới hạn file hiện tại, tính bằng byte."""
    return {
        "max_file_size": MAX_FILE_SIZE,
        "max_compressed_size": MAX_COMPRESSED_SIZE,
    }


def safe_filename(filename, default_name):
    """Làm sạch tên file trước khi đưa vào header tải xuống.

    Nhận tên người dùng gửi lên và tên mặc định; trả tên ASCII đã bỏ
    hoặc thay ký tự đặc biệt. Dùng tên mặc định nếu kết quả rỗng."""
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
    """Đọc UploadFile và trả nội dung bytes trong giới hạn size_limit.

    Đọc tối đa giới hạn cộng 1 byte để phát hiện vượt mức, rồi đóng file tạm.
    Báo HTTP 413 nếu file quá lớn. Không ghi dữ liệu vào thư mục dự án."""
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
    """Kiểm tra kích thước gốc trong header của compressed_data.

    Không trả dữ liệu. Báo HTTP 413 nếu kích thước vượt MAX_FILE_SIZE;
    header không hợp lệ có thể gây ValueError từ unpack_header."""
    header = unpack_header(compressed_data)
    if header["original_size"] > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Dung lượng giải nén vượt quá {MAX_FILE_SIZE:,} byte.",
        )


def restored_filename(uploaded_name):
    """Tạo tên tải xuống từ tên file nén người dùng gửi.

    Bỏ đuôi .bin, ví dụ baocao.txt.bin thành baocao.txt.
    Nếu không có đuôi này thì thêm .restored vì header không lưu tên gốc."""
    filename = safe_filename(uploaded_name, "file.bin")
    if filename.lower().endswith(".bin"):
        return filename[:-4]
    # Tiếp tục nhận các file .huff đã tạo ở phiên bản trước.
    if filename.lower().endswith(".huff"):
        return filename[:-5]
    # Header không lưu tên gốc nên dùng tên dự phòng cho đuôi khác.
    return filename + ".restored"


def download_response(file_data, filename, stats=None):
    """Tạo phản hồi tải file từ file_data (bytes) và filename (tên đã làm sạch).

    Trả Response có body là dữ liệu nhị phân và header đặt tên tải xuống.
    Nếu có stats, thêm các header X-... để giao diện đọc số liệu nén."""
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
    """Xử lý GET /health để kiểm tra API đang hoạt động.

    Trả dictionary trạng thái và danh sách thuật toán; FastAPI đổi thành JSON."""
    return {"status": "ok", "algorithms": list_algorithms()}


@app.post("/api/compress")
def compress_file(file: UploadFile):
    """Xử lý POST /api/compress: nhận file upload và trả file .bin.

    Đọc file, gọi Huffman, đặt tên kết quả và gửi thống kê qua headers.
    File quá lớn trả HTTP 413; giới hạn số tác vụ giúp kiểm soát RAM."""
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
    filename = original_name + ".bin"
    response = download_response(compressed_data, filename, stats)
    return response


@app.post("/api/decompress")
def decompress_file(file: UploadFile):
    """Xử lý POST /api/decompress: nhận file nén và trả dữ liệu gốc.

    Đọc file, kiểm tra kích thước gốc rồi gọi Huffman giải nén.
    Trả Response tải file; lỗi định dạng trả 400, vượt dung lượng trả 413."""
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

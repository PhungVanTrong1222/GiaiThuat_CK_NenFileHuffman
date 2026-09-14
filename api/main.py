import re
import unicodedata
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from anyio import CapacityLimiter
from contextlib import asynccontextmanager

from core import auto_decompress, get_compressor, list_algorithms
from core.base_compressor import unpack_header


MAX_FILE_SIZE = 25 * 1024 * 1024
# File Huffman có thể lớn hơn bản gốc do bảng tần suất.
MAX_COMPRESSED_SIZE = MAX_FILE_SIZE + 8192 + 12


@asynccontextmanager
async def lifespan(app):
    app.state.codec_limiter = CapacityLimiter(2)
    yield

app = FastAPI(
    lifespan=lifespan,
    title="ShrinkIT API",
    description="API nén và giải nén file bằng thuật toán Huffman.",
    version="1.0.0",
)


def _safe_filename(filename: str | None, default: str) -> str:
    name = Path(filename or default).name
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", normalized).strip("._")
    return cleaned or default


async def _read_upload(file: UploadFile, limit: int) -> bytes:
    try:
        data = await file.read(limit + 1)
    finally:
        await file.close()
    if len(data) > limit:
        raise HTTPException(status_code=413, detail="File vượt quá giới hạn 25 MB.")
    return data


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "algorithms": list_algorithms()}


@app.post("/api/compress")
async def compress_file(
    file: Annotated[UploadFile, File(description="File cần nén")],
) -> Response:
    async with app.state.codec_limiter:
        data = await _read_upload(file, MAX_FILE_SIZE)
        compressed, stats = await run_in_threadpool(
            get_compressor("huffman").compress_data, data
        )
    filename = f"{_safe_filename(file.filename, 'file')}.huff"

    return Response(
        content=compressed,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Original-Size": str(stats["original_size"]),
            "X-Compressed-Size": str(stats["compressed_size"]),
            "X-Compression-Ratio": str(stats["compression_ratio"]),
            "X-Compression-Algorithm": stats["algorithm"],
        },
    )


@app.post("/api/decompress")
async def decompress_file(
    file: Annotated[UploadFile, File(description="File .huff cần giải nén")],
) -> Response:
    async with app.state.codec_limiter:
        data = await _read_upload(file, MAX_COMPRESSED_SIZE)
        try:
            header = unpack_header(data)
            if header["original_size"] > MAX_FILE_SIZE:
                raise HTTPException(413, "Dung lượng giải nén vượt quá 25 MB.")
            restored = await run_in_threadpool(auto_decompress, data)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    uploaded_name = _safe_filename(file.filename, "file.huff")
    filename = (
        uploaded_name[:-5]
        if uploaded_name.lower().endswith(".huff")
        else f"{uploaded_name}.restored"
    )

    return Response(
        content=restored,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

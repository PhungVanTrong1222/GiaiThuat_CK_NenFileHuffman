import re
import unicodedata
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response

from core import auto_decompress, get_compressor, list_algorithms


MAX_FILE_SIZE = 25 * 1024 * 1024

app = FastAPI(
    title="ShrinkIT API",
    description="API nén và giải nén file bằng thuật toán Huffman.",
    version="1.0.0",
)


def _safe_filename(filename: str | None, default: str) -> str:
    name = Path(filename or default).name
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", normalized).strip("._")
    return cleaned or default


async def _read_upload(file: UploadFile) -> bytes:
    data = await file.read(MAX_FILE_SIZE + 1)
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File vượt quá giới hạn 25 MB.")
    return data


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "algorithms": list_algorithms()}


@app.post("/api/compress")
async def compress_file(
    file: Annotated[UploadFile, File(description="File cần nén")],
) -> Response:
    data = await _read_upload(file)
    compressed, stats = get_compressor("huffman").compress_data(data)
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
    data = await _read_upload(file)
    try:
        restored = auto_decompress(data)
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

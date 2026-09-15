# ShrinkIT — Nén file bằng Huffman Coding

Đồ án cuối kỳ môn **Phân tích Thiết kế Giải thuật**.

ShrinkIT nén file văn bản (`.txt`, `.csv`, `.log`, `.json`) bằng thuật toán Huffman Coding
và khôi phục lại chính xác dữ liệu ban đầu (nén không mất mát).

---

## Cấu trúc dự án

```
ShrinkIT/
├── core/               # Thuật toán Huffman + định dạng file nén
│   ├── huffman.py      # Toàn bộ logic nén/giải nén
│   ├── file_format.py  # Đọc/ghi header 12 byte
│   ├── benchmark.py    # Đo hiệu suất trên nhiều loại dữ liệu
│   └── __init__.py     # Hàm khởi tạo compressor
│
├── api/                # Backend API (FastAPI)
│   └── main.py         # Nhận file, gọi Huffman, trả kết quả
│
├── web/                # Giao diện người dùng
│   ├── index.html      # Bố cục trang
│   ├── style.css       # Giao diện
│   └── script.js       # Gọi API, hiển thị kết quả
│
├── tests/              # 26 bài kiểm thử tự động
├── Test/               # Chạy thử nhanh với 1 file
├── data/               # File mẫu để test
├── doc/                # Tài liệu kế hoạch, phân công
└── requirements.txt    # Thư viện cần cài
```

---

## Cài đặt

Cần Python 3.10 trở lên. Từ thư mục gốc của dự án:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## Chạy ứng dụng web

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload
```

Mở trình duyệt tại **http://127.0.0.1:8000/**

> **Lưu ý:** Không mở trực tiếp file `index.html` bằng cách nhấp đúp —
> giao diện cần gọi API nên phải chạy qua server.

---

## Chạy kiểm thử

```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Chạy benchmark

```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m core.benchmark
```

## Thử nhanh với 1 file

```powershell
.\.venv\Scripts\python.exe Test/main.py
.\.venv\Scripts\python.exe Test/main.py "D:\duong-dan\file.txt"
```

---

## Thuật toán Huffman — Tóm tắt

**Ý tưởng:** Byte xuất hiện nhiều → gán mã ngắn. Byte xuất hiện ít → gán mã dài.
Kết quả: tổng số bit ít hơn → file nhỏ hơn.

### Quy trình nén (trong `core/huffman.py`)

| Bước | Hàm | Mô tả | Độ phức tạp |
|------|-----|-------|-------------|
| 1 | `count_frequency()` | Đếm mỗi byte xuất hiện bao nhiêu lần | O(n) |
| 2 | `build_tree()` | Xây cây Huffman bằng Min Heap | O(k log k) |
| 3 | `build_codes()` | Duyệt cây: trái = "0", phải = "1" | O(k) |
| 4 | `encode_data()` | Thay byte bằng mã bit → ghép → chuyển thành bytes | O(n) |

> n = số byte đầu vào, k = số loại byte riêng biệt (k ≤ 256)
> → Tổng: **O(n)** — tuyến tính theo kích thước file

### Quy trình giải nén

1. Đọc bảng tần suất từ file nén → xây lại cây Huffman.
2. `decode_data()` — Đọc từng bit, đi theo cây, đến lá thì lấy byte gốc.

### Ví dụ đơn giản

```
Dữ liệu: "AAAB" → A xuất hiện 3 lần, B xuất hiện 1 lần.

Cây Huffman:       Bảng mã:
      gốc            A → "1"  (ngắn vì xuất hiện nhiều)
     /    \           B → "00" (dài vì xuất hiện ít)
   (2)    A(3)
  /   \
B(1)  ...

Mã hóa: "1" + "1" + "1" + "00" = "11100"
Thêm padding: "11100" + "000" = "11100000" (1 byte)
```

---

## Định dạng file nén (`.bin`)

File nén gồm 3 phần nối nhau:

```
[Header 12 byte] + [Bảng tần suất JSON] + [Dữ liệu đã mã hóa]
```

Header 12 byte:

| Vị trí | Kích thước | Nội dung |
|--------|-----------|----------|
| 0-1 | 2 byte | `"SK"` — nhận diện file ShrinkIT |
| 2 | 1 byte | Mã thuật toán (1 = Huffman) |
| 3-6 | 4 byte | Kích thước file gốc |
| 7-10 | 4 byte | Kích thước bảng tần suất |
| 11 | 1 byte | Số bit đệm (0-7) |

---

## API

| Endpoint | Mô tả |
|----------|-------|
| `POST /api/compress` | Nhận file → trả file `.bin` đã nén |
| `POST /api/decompress` | Nhận file `.bin` → trả file gốc |
| `GET /health` | Kiểm tra API đang hoạt động |
| `GET /api/config` | Lấy giới hạn dung lượng |

Mở **http://127.0.0.1:8000/docs** để thử API trên Swagger UI.

**Giới hạn:** File tối đa 25 MB. API trả mã lỗi 400 (file hỏng),
413 (vượt giới hạn), 422 (thiếu file).

---

## Lưu ý quan trọng

- **Huffman chỉ hiệu quả với file chưa nén** (`.txt`, `.csv`, `.log`, `.json`, `.bmp`).
- File đã nén sẵn (`.pdf`, `.docx`, `.zip`, `.jpg`, `.mp4`) sẽ bị **lớn hơn** sau khi nén
  vì dữ liệu bên trong đã có entropy cao + phải thêm header và bảng tần suất.
- Đây là đặc điểm của thuật toán, không phải lỗi.

---

## Thành viên nhóm

| Vai trò | Nhiệm vụ |
|---------|----------|
| TV1 — Trưởng nhóm | Quản lý repo, điều phối, slide thuyết trình |
| TV2 — Thuật toán | Viết logic Huffman (`core/huffman.py`) |
| TV3 — Backend | Viết API FastAPI (`api/main.py`) |
| TV4 — Frontend | Giao diện web (`web/`) |
| TV5 — QA & Data | Kiểm thử, dữ liệu mẫu, triển khai |

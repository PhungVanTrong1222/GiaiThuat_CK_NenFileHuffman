# ShrinkIT

ShrinkIT là dự án cuối kỳ minh họa thuật toán nén dữ liệu không mất mát
bằng **Huffman Coding**. Phần lõi nhận dữ liệu dạng `bytes`, tạo file nén
có header riêng và khôi phục lại chính xác dữ liệu ban đầu.

## Cấu trúc hiện tại

```text
ShrinkIT/
├── core/               # Cài đặt thuật toán Huffman và định dạng file
├── api/                # API nén và giải nén
├── data/               # Dữ liệu mẫu
├── doc/                # Ý tưởng và kế hoạch dự án
├── Test/               # Chương trình thử thủ công với một file
└── tests/              # Kiểm thử tự động
```

## Chạy kiểm thử

Chuẩn bị môi trường (Python 3.13):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Các lệnh dưới dùng Python trong môi trường riêng, không cần kích hoạt PowerShell.

Từ thư mục gốc của dự án:

```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Chạy benchmark

```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m core.benchmark
```

## Chạy API

Cài các thư viện và khởi động server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload
```

Mở `http://127.0.0.1:8000/docs` để thử API trên Swagger UI.

- `POST /api/compress`: nhận file và trả về file `.huff`.
- `POST /api/decompress`: nhận file `.huff` và trả về file gốc.
- `GET /health`: kiểm tra trạng thái API.

File gốc và dữ liệu sau giải nén tối đa 25 MiB (26.214.400 byte).
File nén được thêm 8.204 byte cho header và codebook, vì nén có thể làm file lớn hơn.
API trả 400 với file hỏng, 413 khi vượt giới hạn và 422 khi thiếu file.
Giới hạn này kiểm tra nội dung file sau khi framework đọc multipart; khi triển khai
public cần giới hạn request body tại reverse proxy.

Mỗi worker xử lý tối đa hai tác vụ nén/giải nén cùng lúc trong thread.
Thread giúp tránh chạy thuật toán trực tiếp trên event loop; không làm Python
nén nhanh hơn bằng nhiều lõi CPU.

## Thử với một file

Không truyền tham số thì chương trình dùng `data/sample.txt`:

```powershell
.\.venv\Scripts\python.exe Test/main.py
.\.venv\Scripts\python.exe Test/main.py "D:\duong-dan\file.log"
```

Hai file sinh ra `data/output.huff` và `data/restored.txt` được bỏ qua bởi Git.
Các file `.bin` cũ vẫn đọc được vì định dạng bên trong không đổi.

File nén được kiểm tra header, codebook, số bit, padding và tần suất sau giải nén.
Chưa có checksum nên không phát hiện được mọi thay đổi giữ nguyên tần suất byte.

## Hướng phát triển tiếp theo

1. Xây dựng giao diện upload và tải file bằng Streamlit.
2. Bổ sung checksum để phát hiện file nén bị sửa đổi.
3. Đo thời gian và bộ nhớ với các file 1 MB, 5 MB và 25 MB.

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


## Đọc phần API

Trong `api/main.py`, bắt đầu từ `compress_file` và `decompress_file` ở cuối file.
Mỗi hàm tương ứng với một địa chỉ API và thực hiện lần lượt:

1. Nhận file do trình duyệt gửi lên bằng trường `file` trong form.
2. Gọi `read_uploaded_file` để đọc dữ liệu và kiểm tra giới hạn.
3. Gọi thuật toán Huffman để nén hoặc giải nén.
4. Gọi `download_response` để trả dữ liệu và tên file tải xuống.

API chỉ phụ trách nhận/trả file; thuật toán nằm trong thư mục `core/`.
`UploadFile` là file nhận từ người dùng, còn `Response` là phản hồi gửi về.
Body của phản hồi chứa dữ liệu nhị phân. Header `Content-Disposition` đặt tên
file tải xuống; các header `X-...` chứa số liệu để giao diện hiển thị.

`await` chờ một công việc hoàn thành. `run_in_threadpool` chạy Huffman
trong thread, giúp server không thực hiện thuật toán trực tiếp trên event loop.
`lifespan` chuẩn bị giới hạn số tác vụ khi server khởi động;
`async with` giữ một vị trí xử lý và tự trả lại vị trí đó khi kết thúc.

Muốn đổi giới hạn, sửa `MAX_FILE_SIZE` ở đầu file rồi khởi động lại API.
Thông báo dung lượng được tính từ cấu hình, không ghi cố định trong từng hàm.

## Đọc phần thuật toán

Trong `core/huffman.py`, đọc theo thứ tự:

1. `_count_frequency`: đếm số lần xuất hiện của từng byte.
2. `_build_tree`: lấy hai nút nhỏ nhất trong min heap và ghép thành nút cha.
3. `_build_codes`: duyệt cây, trái là 0 và phải là 1.
4. `_encode`: ghép các mã, thêm padding và đổi từng nhóm 8 bit thành byte.
5. `_decode`: khôi phục chuỗi bit, bỏ padding, duyệt cây để lấy lại dữ liệu.

Ví dụ với `AAAB`: A có mã 1, B có mã 0. Chuỗi mã là `1110`;
thêm 4 bit đệm thành `11100000`. Khi giải nén, bỏ 4 bit đệm rồi
duyệt cây theo `1110` để thu lại `AAAB`.

Các hàm đọc header và kiểm tra file được tách khỏi các bước thuật toán.
Cách cài đặt này ưu tiên dễ đọc: chuỗi bit của cả file được giữ trong RAM,
nên dùng nhiều bộ nhớ hơn phiên bản xử lý bit trực tiếp, đặc biệt với file lớn.

## Hướng phát triển tiếp theo

1. Xây dựng giao diện upload và tải file bằng Streamlit.
2. Bổ sung checksum để phát hiện file nén bị sửa đổi.
3. Đo thời gian và bộ nhớ với các file 1 MB, 5 MB và 25 MB.

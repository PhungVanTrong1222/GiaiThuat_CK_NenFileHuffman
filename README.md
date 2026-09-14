# ShrinkIT

ShrinkIT là dự án cuối kỳ minh họa thuật toán nén dữ liệu không mất mát
bằng **Huffman Coding**. Phần lõi nhận dữ liệu dạng `bytes`, tạo file nén
có header riêng và khôi phục lại chính xác dữ liệu ban đầu.

## Cấu trúc hiện tại

```text
ShrinkIT/
├── core/               # Cài đặt thuật toán Huffman và định dạng file
├── api/                # API nén và giải nén
├── web/                # Giao diện HTML, CSS và JavaScript
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

## Chạy giao diện web và API

Cài các thư viện và khởi động server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload
```

Mở `http://127.0.0.1:8000/` để dùng giao diện web. Chỉ cần chạy một server.
Không mở trực tiếp file HTML bằng cách nhấp đúp vì giao diện cần gọi API.
Mở `http://127.0.0.1:8000/docs` nếu muốn thử API riêng trên Swagger UI.

- `POST /api/compress`: nhận file và trả về file `.bin`.
- `POST /api/decompress`: nhận file `.bin` và trả về file gốc.
- `GET /health`: kiểm tra trạng thái API.
- `GET /api/config`: lấy giới hạn file để giao diện hiển thị và kiểm tra.

## Đọc phần giao diện

- `web/index.html`: bố cục trang, vùng chọn file, nút thao tác và vùng kết quả.
- `web/style.css`: màu sắc, kích thước, bố cục máy tính và điện thoại.
- `web/script.js`: nhận file, gọi API và hiển thị phản hồi.

Trong JavaScript, đọc `selectFile` → `submitFile` → `showResult`.
`FormData` chứa file gửi lên, `fetch` gọi API, `Blob` chứa file trả về.
`URL.createObjectURL` tạo đường dẫn tải xuống trong trình duyệt; khi đổi file,
`clearResult` thu hồi đường dẫn cũ để giải phóng bộ nhớ.

Nút Nén/Giải nén bị khóa trong lúc xử lý để tránh gửi nhầm dữ liệu.
Tổng thời gian chờ tính từ lúc gửi yêu cầu đến khi nhận hết file, bao gồm
truyền dữ liệu và chờ server, không phải chỉ thời gian chạy thuật toán.
Số phần trăm âm nghĩa là file nén lớn hơn bản gốc; file nhỏ hoặc đã nén có thể gặp.

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

Hai file sinh ra `data/output.bin` và `data/restored.txt` được bỏ qua bởi Git.
Các file `.huff` đã tạo trước đây vẫn đọc được vì định dạng bên trong không đổi.

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

Các endpoint dùng hàm `def` thông thường. FastAPI tự chạy chúng trong thread.
Vì vậy bên trong hàm có thể đọc file và gọi Huffman theo thứ tự, không dùng
`async/await`. Tham số `file: UploadFile` cho FastAPI biết cần nhận một file upload.

`processing_slots` giống hai chỗ làm việc, chỉ cho hai tác vụ xử lý đồng thời.
`with processing_slots` chờ một chỗ trống và tự trả chỗ khi xong hoặc gặp lỗi.
Đây là phần giới hạn sử dụng RAM, không thuộc thuật toán Huffman.

Muốn đổi giới hạn, sửa `MAX_FILE_SIZE` ở đầu file rồi khởi động lại API.
Thông báo dung lượng được tính từ cấu hình, không ghi cố định trong từng hàm.

## Đọc phần thuật toán

Phần lõi gồm hai file chính:

- `core/huffman.py`: lớp Huffman độc lập, thực hiện nén, giải nén và tính tỷ lệ nén.
- `core/file_format.py`: đọc/ghi header 12 byte của file nén.

Không dùng lớp cha hay lớp trừu tượng. `core/__init__.py` chỉ cung cấp các hàm
gọi Huffman cho API và chương trình chạy thử.

Trong `core/huffman.py`, đọc theo thứ tự:

1. `count_frequency`: đếm số lần xuất hiện của từng byte.
2. `build_tree`: lấy hai nút nhỏ nhất trong min heap và ghép thành nút cha.
3. `build_codes`: duyệt cây, trái là 0 và phải là 1.
4. `encode_data`: ghép các mã, thêm padding và đổi từng nhóm 8 bit thành byte.
5. `decode_data`: khôi phục chuỗi bit, bỏ padding, duyệt cây để lấy lại dữ liệu.

Ví dụ với `AAAB`: A có mã 1, B có mã 0. Chuỗi mã là `1110`;
thêm 4 bit đệm thành `11100000`. Khi giải nén, bỏ 4 bit đệm rồi
duyệt cây theo `1110` để thu lại `AAAB`.

Các hàm đọc header và kiểm tra file được tách khỏi các bước thuật toán.
Cách cài đặt này ưu tiên dễ đọc: chuỗi bit của cả file được giữ trong RAM,
nên dùng nhiều bộ nhớ hơn phiên bản xử lý bit trực tiếp, đặc biệt với file lớn.

## Hướng phát triển tiếp theo

1. Bổ sung số liệu thực nghiệm và phần minh họa cây Huffman.
2. Bổ sung checksum để phát hiện file nén bị sửa đổi.
3. Đo thời gian và bộ nhớ với các file 1 MB, 5 MB và 25 MB.

## Quy ước viết code

Tên hàm và biến viết đầy đủ, dùng dấu gạch dưới giữa các từ, ví dụ
`count_frequency`. Không thêm dấu gạch dưới ở đầu tên hàm thông thường.
`__init__` và `__lt__` giữ nguyên vì Python dùng chúng để khởi tạo và so sánh đối tượng.

Ưu tiên vòng lặp, biến trung gian và điều kiện rõ ràng. Chú thích giải thích
mục đích hoặc phần khó. Các tên `setUp`, `test_...` trong kiểm thử là quy ước
của unittest để chuẩn bị và tìm các bài kiểm tra.

Chương trình chạy thử có hàm `main()`; chỉ chạy khi mở trực tiếp bằng Python.
Import file để đọc hoặc kiểm thử không tự tạo hay ghi đè dữ liệu mẫu.

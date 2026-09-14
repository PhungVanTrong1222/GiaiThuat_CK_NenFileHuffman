# ShrinkIT

ShrinkIT là dự án cuối kỳ minh họa thuật toán nén dữ liệu không mất mát
bằng **Huffman Coding**. Phần lõi nhận dữ liệu dạng `bytes`, tạo file nén
có header riêng và khôi phục lại chính xác dữ liệu ban đầu.

## Cấu trúc hiện tại

```text
ShrinkIT/
├── core/               # Cài đặt thuật toán Huffman và định dạng file
├── data/               # Dữ liệu mẫu
├── doc/                # Ý tưởng và kế hoạch dự án
├── Test/               # Chương trình thử thủ công với một file
└── tests/              # Kiểm thử tự động
```

## Chạy kiểm thử

Từ thư mục gốc của dự án:

```powershell
$env:PYTHONIOENCODING="utf-8"
python -m unittest discover -s tests -v
```

## Chạy benchmark

```powershell
$env:PYTHONIOENCODING="utf-8"
python -m core.benchmark
```

## Thử với một file

Không truyền tham số thì chương trình dùng `data/sample.txt`:

```powershell
python Test/main.py
python Test/main.py "D:\duong-dan\file.log"
```

Hai file sinh ra `data/output.bin` và `data/restored.txt` được bỏ qua bởi Git.

## Hướng phát triển tiếp theo

1. Xây dựng API nén/giải nén bằng FastAPI.
2. Xây dựng giao diện upload và tải file bằng Streamlit.
3. Bổ sung checksum để phát hiện file nén bị sửa đổi.
4. Đo thời gian và bộ nhớ với các file 1 MB, 5 MB và 50 MB.

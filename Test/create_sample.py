"""Tạo văn bản mẫu để thử Huffman: python Test/create_sample.py.

Ghi hoặc ghi đè data/sample.txt; đường dẫn tính từ vị trí dự án."""

import os


def main():
    """Tạo thư mục data nếu thiếu và ghi văn bản mẫu vào data/sample.txt.

    File mẫu có sẵn sẽ bị ghi đè khi chạy hàm này. In đường dẫn và kích thước.
    Không nhận tham số và không trả dữ liệu."""
    script_path = os.path.abspath(__file__)
    script_directory = os.path.dirname(script_path)
    project_directory = os.path.dirname(script_directory)
    data_directory = os.path.join(project_directory, "data")
    os.makedirs(data_directory, exist_ok=True)
    sample_path = os.path.join(data_directory, "sample.txt")

    content = "Xin chao! Day la file test cho ShrinkIT.\n" * 1000
    content += "Huffman Coding la thuat toan nen du lieu khong mat mat.\n" * 500
    content += "Log entry: [2025-09-12 10:00:00] INFO - Request processed successfully.\n" * 300

    with open(sample_path, "w", encoding="utf-8") as sample_file:
        sample_file.write(content)

    size = os.path.getsize(sample_path)
    print(f"Da tao file: {sample_path} ({size:,} bytes)")


if __name__ == "__main__":
    main()

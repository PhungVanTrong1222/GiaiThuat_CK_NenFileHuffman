import os

os.makedirs("data", exist_ok=True)

content = "Xin chao! Day la file test cho ShrinkIT.\n" * 1000
content += "Huffman Coding la thuat toan nen du lieu khong mat mat.\n" * 500
content += "Log entry: [2025-09-12 10:00:00] INFO - Request processed successfully.\n" * 300

with open("data/sample.txt", "w", encoding="utf-8") as f:
    f.write(content)

size = os.path.getsize("data/sample.txt")
print(f"Da tao file: data/sample.txt ({size:,} bytes)")

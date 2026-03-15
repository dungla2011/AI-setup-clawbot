"""Simple RAG quality check — no interactive prompts."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding='utf-8')

from rag import retrieve

QUERIES = [
    ("Hàng tồn kho được kế toán theo phương pháp nào?", "staff"),
    ("Phương pháp tính giá xuất kho bình quân gia quyền", "staff"),
    ("Khấu hao tài sản cố định hữu hình", "staff"),
]

for q, role in QUERIES:
    print(f"\nQ: {q}")
    chunks = retrieve(q, user_role=role, top_k=3, min_score=0.0)
    for i, c in enumerate(chunks[:3], 1):
        preview = c['content'].replace('\n', ' ')[:200]
        print(f"  [{i}] score={c['score']:.4f}  trang={c['page_num']}")
        print(f"       {preview}")

print("\nDONE")

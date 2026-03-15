"""
test_rag.py — Kiểm tra pipeline RAG độc lập (không cần server).

Chạy:
    python test_rag.py
    python test_rag.py "câu hỏi của bạn"
"""

import sys
import os
import textwrap
from pathlib import Path

# Đảm bảo import từ đúng folder
sys.path.insert(0, str(Path(__file__).parent))

from database import get_db
from embeddings import embed, from_blob, cosine_similarity
from rag import retrieve, format_context

SEP = "─" * 70

# ── 1. Kiểm tra DB có chunk không ─────────────────────────────────────────────
def check_db():
    with get_db() as conn:
        c = conn.cursor()
        docs = c.execute("""
            SELECT d.original_filename, d.total_chunks, d.category_id,
                   cat.name as cat_name,
                   COUNT(ch.id) as actual_chunks,
                   SUM(CASE WHEN ch.embedding IS NOT NULL THEN 1 ELSE 0 END) as with_embed
            FROM documents d
            JOIN doc_categories cat ON d.category_id = cat.id
            LEFT JOIN doc_chunks ch ON ch.doc_id = d.id
            WHERE d.is_active = 1
            GROUP BY d.id
        """).fetchall()

    print(SEP)
    print("📚 TÀI LIỆU TRONG DB")
    print(SEP)
    if not docs:
        print("  ⚠️  Không có tài liệu nào! Upload trước.")
        sys.exit(1)
    for d in docs:
        print(f"  📄 {d['original_filename']}")
        print(f"     Category : {d['category_id']} ({d['cat_name']})")
        print(f"     Chunks DB: {d['total_chunks']}  |  Thực tế: {d['actual_chunks']}  |  Có embed: {d['with_embed']}")
        if d['actual_chunks'] == 0:
            print("     ❌ Không có chunk! Cần reprocess document.")
        elif d['with_embed'] < d['actual_chunks']:
            print(f"     ⚠️  Thiếu embedding: {d['actual_chunks'] - d['with_embed']} chunks không có vector.")
    return docs

# ── 2. Test embedding nhanh ────────────────────────────────────────────────────
def check_embedding():
    print()
    print(SEP)
    print("🔢 KIỂM TRA EMBEDDING MODEL")
    print(SEP)
    test_text = "hàng tồn kho kế toán phương pháp"
    vec = embed(test_text)
    print(f"  Input : '{test_text}'")
    print(f"  Vector: dim={len(vec)}, norm≈{sum(x*x for x in vec)**0.5:.4f}")
    print(f"  ✅ MiniLM embedding OK")
    return vec

# ── 3. Tìm Top-K chunks ────────────────────────────────────────────────────────
def test_retrieve(query: str, user_role: str = "staff", top_k: int = 5, min_score: float = 0.20):
    print()
    print(SEP)
    print(f"🔍 RETRIEVE: '{query}'")
    print(f"   Role={user_role}  top_k={top_k}  min_score={min_score}")
    print(SEP)

    chunks = retrieve(query, user_role=user_role, top_k=top_k, min_score=min_score)

    if not chunks:
        print(f"  ⚠️  Không tìm thấy chunk nào với score >= {min_score}")
        print("      Thử hạ min_score hoặc kiểm tra lại embedding.")
        # Debug: lấy top-3 bất kể score
        print()
        print("  🔎 Debug — top 3 chunk gần nhất (bất kể score):")
        debug_chunks = retrieve(query, user_role=user_role, top_k=3, min_score=0.0)
        for i, c in enumerate(debug_chunks, 1):
            print(f"    [{i}] score={c['score']:.4f} | {c['source_file']} trang {c['page_num']}")
            print(f"         {c['content'][:120].replace(chr(10),' ')}...")
        return []

    for i, c in enumerate(chunks, 1):
        print(f"\n  [{i}] score={c['score']:.4f} | {c['source_file']}, trang {c['page_num']}")
        preview = c['content'].replace('\n', ' ')[:300]
        for line in textwrap.wrap(preview, width=65):
            print(f"       {line}")

    return chunks

# ── 4. Gọi Claude với context ─────────────────────────────────────────────────
def test_with_claude(query: str, chunks: list):
    if not chunks:
        print("\n  ⚠️  Không có chunks để test Claude.")
        return

    print()
    print(SEP)
    print(f"🤖 GỌI CLAUDE VỚI RETRIEVED CONTEXT")
    print(SEP)

    try:
        import anthropic
        from dotenv import load_dotenv
        load_dotenv()
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        context = format_context(chunks)
        system = (
            "Bạn là trợ lý AI chuyên về tài liệu kế toán Việt Nam. "
            "Trả lời chính xác dựa trên tài liệu được cung cấp. "
            "Trích dẫn nguồn (tên file, số trang) khi trả lời.\n\n"
            + context
        )

        resp = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": query}]
        )
        answer = resp.content[0].text
        print(f"\n  Câu hỏi: {query}")
        print(f"\n  Trả lời:")
        for line in answer.split('\n'):
            print(f"    {line}")
        usage = resp.usage
        print(f"\n  Tokens: input={usage.input_tokens}, output={usage.output_tokens}")
    except Exception as e:
        print(f"  ❌ Lỗi Claude: {e}")

# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    queries = sys.argv[1:] if len(sys.argv) > 1 else [
        "Hàng tồn kho được kế toán theo phương pháp nào?",
        "Nguyên tắc ghi nhận doanh thu theo thông tư 200",
        "Khấu hao tài sản cố định hữu hình",
        "Phương pháp tính giá xuất kho",
    ]

    check_db()
    check_embedding()

    for q in queries:
        chunks = test_retrieve(q, user_role="staff", top_k=3, min_score=0.20)

    # Test Claude chỉ với câu hỏi đầu tiên (tốn token)
    print()
    ans = input(f"Gọi Claude với câu '{queries[0]}'? (y/N): ").strip().lower()
    if ans == 'y':
        chunks = retrieve(queries[0], user_role="staff", top_k=5, min_score=0.20)
        test_with_claude(queries[0], chunks)

    print()
    print(SEP)
    print("✅ Test xong")
    print(SEP)

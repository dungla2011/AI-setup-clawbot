"""
test-rag-diagnose.py
Kiểm tra nhanh toàn bộ pipeline RAG:
  1. Import sentence_transformers
  2. Load MiniLM model
  3. Embed 1 câu test
  4. Parse PDF (nếu truyền đường dẫn)
  5. Xem DB có chunks chưa
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

print("="*60)
print("STEP 1 — Import sentence_transformers")
try:
    from sentence_transformers import SentenceTransformer
    print("  ✅ Import OK")
except Exception as e:
    print(f"  ❌ Import FAILED: {e}")
    sys.exit(1)

print("\nSTEP 2 — Load MiniLM model (sẽ download nếu chưa có)")
MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
try:
    model = SentenceTransformer(MODEL)
    print(f"  ✅ Model loaded: {MODEL}")
    import os
    # Find cache
    for base in [os.path.expanduser("~/.cache/torch/sentence_transformers"),
                 os.path.expanduser("~/.cache/huggingface/hub")]:
        if os.path.exists(base):
            print(f"  📁 Cache: {base}")
            for item in os.listdir(base):
                print(f"     └─ {item}")
except Exception as e:
    print(f"  ❌ Load FAILED: {e}")
    sys.exit(1)

print("\nSTEP 3 — Embed test sentence")
try:
    vec = model.encode("Chính sách nghỉ phép năm 2026", normalize_embeddings=True)
    print(f"  ✅ Embedding OK — shape: {vec.shape}, dtype: {vec.dtype}")
except Exception as e:
    print(f"  ❌ Embed FAILED: {e}")
    sys.exit(1)

print("\nSTEP 4 — Parse PDF (nếu có file truyền vào)")
if len(sys.argv) > 1:
    from pathlib import Path
    pdf_path = Path(sys.argv[1])
    print(f"  📄 Testing: {pdf_path.name}")
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        print(f"  Pages: {len(reader.pages)}")
        for i, page in enumerate(reader.pages[:3]):
            text = page.extract_text() or ""
            print(f"  Page {i+1}: {len(text)} chars | preview: {text[:80].strip()!r}")
    except Exception as e:
        print(f"  ❌ PDF parse FAILED: {e}")
else:
    print("  (bỏ qua — truyền đường dẫn PDF để test: python test-rag-diagnose.py uploads/xxx.pdf)")

print("\nSTEP 5 — DB chunk count")
try:
    import sqlite3
    conn = sqlite3.connect("bot_data.db")
    rows = conn.execute("SELECT d.original_filename, d.total_chunks, d.is_active, COUNT(c.id) as actual_chunks FROM documents d LEFT JOIN doc_chunks c ON c.doc_id = d.id GROUP BY d.id").fetchall()
    if not rows:
        print("  (no documents in DB yet)")
    for r in rows:
        status = "✅" if r[3] > 0 else ("⚠️ 0 chunks" if r[2] else "❌ inactive")
        print(f"  {status} {r[0]} — recorded:{r[1]} actual:{r[3]}")
    conn.close()
except Exception as e:
    print(f"  ❌ DB check FAILED: {e}")

print("\n" + "="*60)
print("Xong!")

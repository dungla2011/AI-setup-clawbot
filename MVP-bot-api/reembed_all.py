"""
reembed_all.py — Xoá toàn bộ doc_chunks và embed lại tất cả tài liệu PDF.

Usage:
    python reembed_all.py
"""
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from database import get_db
from doc_processor import process_document, UPLOADS_DIR


def main():
    with get_db() as conn:
        docs = conn.execute(
            "SELECT id, filename, original_filename, category_id FROM documents ORDER BY created_at"
        ).fetchall()

    if not docs:
        print("Không có tài liệu nào trong DB.")
        return

    print(f"Tổng số tài liệu: {len(docs)}")
    print()

    ok = 0
    skip = 0
    errors = []

    for doc in docs:
        doc_id   = doc["id"]
        filename = doc["filename"]
        orig     = doc["original_filename"] or filename
        cat_id   = doc["category_id"]

        file_path = UPLOADS_DIR / filename
        if not file_path.exists():
            print(f"⚠️  [{orig}] File không tồn tại: {file_path} — bỏ qua")
            skip += 1
            continue

        print(f"🔄  [{orig}] Đang xoá chunks cũ...")
        with get_db() as conn:
            conn.execute("DELETE FROM doc_chunks WHERE doc_id = ?", (doc_id,))
            conn.commit()

        try:
            n = process_document(doc_id, file_path, cat_id)
            print(f"✅  [{orig}] → {n} chunks")
            ok += 1
        except Exception as e:
            print(f"❌  [{orig}] LỖI: {e}")
            errors.append((orig, str(e)))

    print()
    print("=" * 50)
    print(f"Hoàn tất: {ok} thành công, {skip} bỏ qua, {len(errors)} lỗi")
    if errors:
        for name, err in errors:
            print(f"  - {name}: {err}")


if __name__ == "__main__":
    main()

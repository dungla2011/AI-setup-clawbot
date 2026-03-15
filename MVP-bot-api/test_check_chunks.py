"""
test_check_chunks.py — Extract N trang PDF bằng pdfplumber, tách chunk,
lưu vào folder test_chunk/ để so sánh trực quan.

Hoàn toàn độc lập — không cần DB, không cần server.

Usage:
    python test_check_chunks.py [pdf_path] [max_pages]
    python test_check_chunks.py                                     # PDF mặc định, 10 trang
    python test_check_chunks.py taiLieuSample/abc.pdf 5            # PDF khác, 5 trang
"""
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from doc_processor import chunk_text, _clean_pdf_text

import pdfplumber

# ── Args ──────────────────────────────────────────────────────────────────────
DEFAULT_PDF = BASE / "taiLieuSample" / "Thong_Tu_200_2014_TT-BTC.pdf"
pdf_path  = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
MAX_PAGES = int(sys.argv[2]) if len(sys.argv) > 2 else 10

if not pdf_path.exists():
    print(f"Không tìm thấy PDF: {pdf_path}")
    sys.exit(1)

# ── Output folder ─────────────────────────────────────────────────────────────
OUT_DIR = BASE / "test_chunk"
OUT_DIR.mkdir(exist_ok=True)
# Xóa output cũ
for f in OUT_DIR.glob("*.txt"):
    f.unlink()

# ── Extract text từ PDF ───────────────────────────────────────────────────────
print(f"PDF      : {pdf_path.name}")
raw_pages = []
with pdfplumber.open(str(pdf_path)) as pdf:
    total = len(pdf.pages)
    check = min(MAX_PAGES, total)
    print(f"Trang    : {check}/{total}")
    for i in range(check):
        t = pdf.pages[i].extract_text(x_tolerance=2, y_tolerance=3) or ""
        t = _clean_pdf_text(t)
        if t:
            raw_pages.append((i + 1, t))   # (page_num, text)

# ── Lưu full text ─────────────────────────────────────────────────────────────
full_text = ""
for page_num, t in raw_pages:
    full_text += f"\n{'='*60}\n[ TRANG {page_num} ]\n{'='*60}\n{t}\n"

full_path = OUT_DIR / "full_text.txt"
full_path.write_text(full_text, encoding="utf-8")
print(f"Full text: {len(full_text):,} ký tự → {full_path.name}")

# ── Tách chunk ────────────────────────────────────────────────────────────────
all_chunks = []
for page_num, t in raw_pages:
    for ch in chunk_text(t, page_num):
        all_chunks.append(ch)

# Re-index chunk_index globally
for i, ch in enumerate(all_chunks):
    ch["chunk_index"] = i

print(f"Chunks   : {len(all_chunks)} chunks từ {len(raw_pages)} trang\n")

# ── Lưu từng chunk ra file ────────────────────────────────────────────────────
for ch in all_chunks:
    idx      = ch["chunk_index"]
    page_num = ch["page"]
    tokens   = ch["token_count"]
    text     = ch["text"]

    fname = OUT_DIR / f"chunk_{idx:04d}_p{page_num}.txt"
    header = (
        f"[Chunk {idx:04d}] | Trang {page_num} | ~{tokens} tokens\n"
        f"{'-'*50}\n"
    )
    fname.write_text(header + ch["text"], encoding="utf-8")

print(f"Đã lưu {len(all_chunks)} file vào: {OUT_DIR}/")
print()

# ── Kiểm tra nhanh: đầu/cuối mỗi chunk ──────────────────────────────────────
print(f"{'IDX':>4}  {'PAGE':>4}  {'TOKENS':>6}  BẮT ĐẦU → KẾT THÚC")
print("-" * 80)
for ch in all_chunks:
    s = ch["text"].replace('\n', ' ')
    start_preview = s[:40]
    end_preview   = s[-40:]
    print(f"{ch['chunk_index']:>4}  {ch['page']:>4}  {ch['token_count']:>6}  "
          f"{start_preview!r} … {end_preview!r}")

print()
print(f"✅ Xong. Mở folder: {OUT_DIR}")

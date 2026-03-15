"""
test_pdf_extract.py - Extract PDF to TXT using pdfplumber.
Output: same filename with _pdfplumber.txt extension
"""
import sys
from pathlib import Path

BASE = Path(__file__).parent
PDF = sys.argv[1] if len(sys.argv) > 1 else str(
    BASE / "taiLieuSample" / "Thong_Tu_200_2014_TT-BTC.pdf"
)

import pdfplumber

pdf_path = Path(PDF)
out_path = pdf_path.with_name(pdf_path.stem + "_pdfplumber.txt")

print(f"Extracting: {pdf_path.name}")

pages_text = []
with pdfplumber.open(str(pdf_path)) as pdf:
    total = len(pdf.pages)
    print(f"[pdfplumber] Tong so trang: {total}")
    for i, page in enumerate(pdf.pages, 1):
        text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
        pages_text.append(text)
        if i % 50 == 0 or i == total:
            print(f"  Da xu ly {i}/{total} trang...")

full_text = "\n\n".join(pages_text)
out_path.write_text(full_text, encoding="utf-8")

lines = full_text.splitlines()
print(f"Done: {out_path}")
print(f"Pages: {total} | Chars: {len(full_text):,} | Lines: {len(lines):,}")
print()
print("--- First 60 lines ---")
print("\n".join(lines[:60]))



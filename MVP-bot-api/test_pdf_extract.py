"""Quick test: compare pypdf vs pymupdf text extraction quality."""
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

PDF = str(BASE / "taiLieuSample" / "Thong_Tu_200_2014_TT-BTC.pdf")
PAGE = 5  # 0-indexed = page 6

print("=== pypdf ===")
try:
    from pypdf import PdfReader
    r = PdfReader(PDF)
    t = r.pages[PAGE].extract_text() or ""
    print(repr(t[:300]))
except Exception as e:
    print(f"ERROR: {e}")

print()
print("=== pymupdf (fitz) ===")
try:
    import fitz
    doc = fitz.open(PDF)
    t = doc[PAGE].get_text()
    doc.close()
    print(repr(t[:300]))
except ImportError:
    print("NOT installed — pip install pymupdf")
except Exception as e:
    print(f"ERROR: {e}")

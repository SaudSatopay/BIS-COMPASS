"""Quick PDF inspection — dump pages to a text file for inspection."""
import fitz
import sys
from pathlib import Path

PDF_PATH = Path("datasets/dataset.pdf")
OUT_PATH = Path("scripts/_pdf_peek.txt")

def main(start: int = 0, end: int = 5):
    doc = fitz.open(PDF_PATH)
    print(f"Total pages: {len(doc)}")
    print(f"Title: {doc.metadata.get('title')}")
    with OUT_PATH.open("w", encoding="utf-8") as f:
        f.write(f"Total pages: {len(doc)}\n")
        f.write(f"Metadata: {doc.metadata}\n")
        f.write("=" * 80 + "\n")
        for i in range(start, min(end, len(doc))):
            page = doc[i]
            text = page.get_text("text")
            f.write(f"\n--- PAGE {i + 1} ---\n")
            f.write(text)
            f.write("\n")
    doc.close()
    print(f"Wrote pages {start + 1}-{end} to {OUT_PATH}")

if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    main(start, end)

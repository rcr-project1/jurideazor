from pathlib import Path
import pandas as pd
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/joradp/pdf"
rows = []

for pdf in sorted(RAW.rglob("*.pdf")):
    lang = pdf.parts[-3]          # fr / ar
    year = int(pdf.parts[-2])
    try:
        doc = pymupdf.open(pdf)
        chars = sum(len(p.get_text().strip()) for p in doc)
        rows.append({"lang": lang, "year": year, "file": pdf.name,
                     "pages": doc.page_count, "chars": chars,
                     "kind": "text" if chars > 50 * doc.page_count else "scan"})
    except Exception as e:
        rows.append({"lang": lang, "year": year, "file": pdf.name,
                     "pages": 0, "chars": 0, "kind": f"ERROR: {type(e).__name__}"})

out = pd.DataFrame(rows)
out.to_csv(ROOT / "data/processed/pdf_report.csv", index=False)
print(out.to_string(index=False))
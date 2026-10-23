"""Organiser-only page index to verify exact booklet sections before extraction."""
import json
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sources = json.loads((ROOT / "corpus/sources.json").read_text(encoding="utf-8"))
index = {}
for source in sources:
    reader = PdfReader(ROOT / "corpus/pdfs" / source["filename"])
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({"pdf_page": i + 1, "text": text})
    index[source["ballot_id"]] = pages
    print(source["ballot_id"], "PDF pages:", len(pages))
    for page in pages[:56]:
        print(page["pdf_page"], page["text"][:160].replace("\n", " "))
(ROOT / "outputs/source_page_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

"""Page-preserving pypdf extraction and token-aware chunking."""
import hashlib
import json
import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_jsonl(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")


def extract_passages(root, ballot_ids=None):
    """Extract only explicitly selected, 1-based PDF pages; no inferred ranges."""
    root = Path(root)
    sources = json.loads((root / "corpus/sources.json").read_text(encoding="utf-8"))
    passages = []
    for source in sources:
        if source["status"] != "available":
            continue
        if ballot_ids is not None and source["ballot_id"] not in ballot_ids:
            continue
        path = root / "corpus/pdfs" / source["filename"]
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if source.get("source_sha256") and source_hash != source["source_sha256"]:
            raise ValueError(f"Quellendatei wurde verändert: {source['ballot_id']}")
        reader = PdfReader(path)
        source_passages = []
        for section in source["sections"]:
            for number in section["pdf_pages"]:
                page = reader.pages[number - 1]
                text = page.extract_text(extraction_mode="layout") or ""
                # Retain paragraph/page boundaries and do not repair numerical claims.
                text = text.replace("\u00ad", "")
                text = re.sub(r"[ \t]+", " ", text).strip()
                if not text:
                    raise ValueError(f"Kein Text: {source['ballot_id']}, PDF-Seite {number}. OCR prüfen.")
                passage_id = f"{source['ballot_id']}-PDF{number:03d}"
                source_passages.append({
                    "passage_id": passage_id,
                    "ballot_id": source["ballot_id"], "title": source["title"],
                    "ballot_date": source["ballot_date"],
                    "information_cutoff": source["information_cutoff"],
                    "source_url": source["source_url"], "source_sha256": source_hash,
                    "filename": source["filename"],
                    "extraction_review_status": source["extraction_review_status"],
                    "source_role": section["source_role"], "section": section["name"],
                    "pdf_page": number,
                    "printed_page": section.get("printed_page_offset", 0) + number,
                    "text": text,
                })
        corpus_text = re.sub(r"[^a-zäöüß0-9]", "", " ".join(p["text"] for p in source_passages).casefold())
        for marker in source.get("required_markers", []):
            normalized = re.sub(r"[^a-zäöüß0-9]", "", marker.casefold())
            if normalized not in corpus_text:
                raise ValueError(f"Unlesbare oder falsche Extraktion: {source['ballot_id']}, Prüfwort {marker!r} fehlt.")
        passages.extend(source_passages)
    ids = [p["passage_id"] for p in passages]
    if len(ids) != len(set(ids)):
        raise ValueError("Überlappende Seitenauswahl: Passage-IDs sind nicht eindeutig.")
    return passages


def make_chunks(passages, size=300, overlap=50):
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Es muss gelten: 0 <= Overlap < Chunkgrösse.")
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base", chunk_size=size, chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    config = {"size_tokens": size, "overlap_tokens": overlap, "encoding": "cl100k_base"}
    chunks = []
    for passage in passages:
        for i, text in enumerate(splitter.split_text(passage["text"])):
            record = {**passage, "text": text, "source_passage_ids": [passage["passage_id"]], "chunking": config}
            record["chunk_id"] = f"{passage['passage_id']}-{digest([config, text, i])[:12]}"
            chunks.append(record)
    return chunks

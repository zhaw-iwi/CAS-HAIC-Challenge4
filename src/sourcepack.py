"""Integrity checks for the pre-extracted teaching corpus; no PDF parsing or network."""
import hashlib
import json
from pathlib import Path


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def seal_pack(root):
    root = Path(root)
    sources = json.loads((root / "corpus/sources.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (root / "corpus/passages.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    expected_ids = {f"{s['ballot_id']}-PDF{p:03d}" for s in sources if s["status"] == "available"
                    for section in s["sections"] for p in section["pdf_pages"]}
    if {r["passage_id"] for r in rows} != expected_ids or len(rows) != len(expected_ids):
        raise ValueError("Extrahierte Seiten passen nicht zur Seitenauswahl.")
    for source in sources:
        if source["status"] != "available":
            continue
        actual = hashlib.sha256((root / "corpus/pdfs" / source["filename"]).read_bytes()).hexdigest()
        if actual != source["source_sha256"] or any(r["source_sha256"] != actual for r in rows if r["ballot_id"] == source["ballot_id"]):
            raise ValueError(f"Quellenhash passt nicht: {source['ballot_id']}")
    manifest = {"sources_sha256": fingerprint(sources), "passages_sha256": fingerprint(rows),
                "passage_count": len(rows), "extraction": "pypdf layout; whitespace normalised; soft hyphens removed",
                "review_status": "page_selection_checked; full_text_and_references_pending"}
    (root / "corpus/passages.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def load_pack(root):
    root = Path(root)
    try:
        sources = json.loads((root / "corpus/sources.json").read_text(encoding="utf-8"))
        manifest = json.loads((root / "corpus/passages.manifest.json").read_text(encoding="utf-8"))
        rows = [json.loads(line) for line in (root / "corpus/passages.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        valid = manifest["sources_sha256"] == fingerprint(sources) and manifest["passages_sha256"] == fingerprint(rows)
        for source in sources:
            if source["status"] == "available":
                actual = hashlib.sha256((root / "corpus/pdfs" / source["filename"]).read_bytes()).hexdigest()
                valid = valid and actual == source["source_sha256"]
        if not valid:
            raise ValueError("Prüfsumme stimmt nicht überein.")
    except (OSError, KeyError, ValueError) as exc:
        raise ValueError("Der vorbereitete Quellenbestand fehlt oder wurde verändert. Bitte die Lehrperson kontaktieren; "
                         "sie kann scripts/prepare_corpus.py ausführen.") from exc
    return rows

"""Run from challenge/: python scripts/prepare_corpus.py."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.corpus import extract_passages, write_jsonl
from src.sourcepack import seal_pack

if __name__ == "__main__":
    passages = extract_passages(ROOT)
    write_jsonl(ROOT / "corpus/passages.jsonl", passages)
    seal_pack(ROOT)
    print(f"{len(passages)} Quellenseiten mit pypdf extrahiert. Text und Seitenzuordnung prüfen.")

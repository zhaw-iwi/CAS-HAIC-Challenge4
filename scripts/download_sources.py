"""Organiser-only download of the four official pre-vote booklets. No model calls."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
VOTES = {"A2024": 665, "R2024": 666, "P2024": 667, "K2024": 668}


def main():
    path = ROOT / "corpus/sources.json"
    sources = json.loads(path.read_text(encoding="utf-8"))
    folder = ROOT / "corpus/pdfs"
    folder.mkdir(exist_ok=True)
    for source in sources:
        vote = VOTES[source["ballot_id"]]
        url = f"https://swissvotes.ch/vote/{vote}.00/brochure-de.pdf"
        destination = folder / source["filename"]
        if not destination.exists():
            request = Request(url, headers={"User-Agent": "CAS-HAIC teaching corpus preparation"})
            with urlopen(request, timeout=90) as response:
                data = response.read()
            if not data.startswith(b"%PDF-"):
                raise ValueError(f"Keine PDF-Datei erhalten: {source['ballot_id']}")
            destination.write_bytes(data)
            print(f"Downloaded {source['ballot_id']}: {len(data)} bytes", flush=True)
        else:
            print(f"Preserved existing {source['ballot_id']}", flush=True)
        source.update(source_url=url, discovery_url=f"https://swissvotes.ch/vote/{vote}.00",
                      swissvotes_id=vote,
                      source_sha256=hashlib.sha256(destination.read_bytes()).hexdigest())
        source.setdefault("retrieved_at_utc", datetime.now(timezone.utc).isoformat())
        # Availability means both file and a reviewed page selection exist.
        if not source["sections"]:
            source["status"] = "downloaded"
        path.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

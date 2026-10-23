"""Organiser's explicit page/role selection, checked against original booklet headings."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pages(start, end=None):
    return list(range(start, (end or start) + 1))


SUMMARY = "Amtliche Kurzfassung mit zugeschriebenen Positionen"
DETAIL = "Erläuterungen der Behörden"
COMMITTEE = "Argumente des Initiativkomitees"
AUTHORITY = "Argumente von Bundesrat und Parlament"
BALLOT = "Originaler Abstimmungstext"

SECTIONS = {
    "A2024": [("In Kürze", SUMMARY, pages(4, 5)), ("Im Detail", DETAIL, pages(8, 12)),
              ("Initiativkomitee", COMMITTEE, pages(14, 15)), ("Bundesrat und Parlament", AUTHORITY, pages(16, 17)),
              ("Abstimmungstext", BALLOT, pages(18))],
    "R2024": [("In Kürze", SUMMARY, pages(6, 7)), ("Im Detail", DETAIL, pages(20, 22) + pages(24)),
              ("Initiativkomitee", COMMITTEE, pages(26, 27)), ("Bundesrat und Parlament", AUTHORITY, pages(28, 29)),
              ("Abstimmungstext", BALLOT, pages(30, 31))],
    "P2024": [("In Kürze", SUMMARY, pages(4, 5)), ("Im Detail", DETAIL, pages(12, 15)),
              ("Initiativkomitee", COMMITTEE, pages(16, 17)), ("Bundesrat und Parlament", AUTHORITY, pages(18, 19)),
              ("Abstimmungstext", BALLOT, pages(20, 21))],
    "K2024": [("In Kürze", SUMMARY, pages(6, 7)), ("Im Detail", DETAIL, pages(22, 25)),
              ("Initiativkomitee", COMMITTEE, pages(26, 27)), ("Bundesrat und Parlament", AUTHORITY, pages(28, 29)),
              ("Abstimmungstext", BALLOT, pages(30, 31))],
}

MARKERS = {
    "A2024": ["Altersrente", "Ergänzungsleistungen"],
    "R2024": ["Rentenalter", "Lebenserwartung"],
    "P2024": ["Prämien", "Einkommen"],
    "K2024": ["Kostenbremse", "Löhne"],
}


if __name__ == "__main__":
    path = ROOT / "corpus/sources.json"
    sources = json.loads(path.read_text(encoding="utf-8"))
    for source in sources:
        bid = source["ballot_id"]
        source["sections"] = [{"name": name, "source_role": role, "pdf_pages": selected, "printed_page_offset": 0}
                              for name, role, selected in SECTIONS[bid]]
        source.update(status="available", page_selection_review_status="checked_against_booklet_headings",
                      extraction_review_status="pending_full_text_audit", required_markers=MARKERS[bid],
                      extraction_note="Original-PDF erhalten; Textextraktion bildet Grafiken und Tabellen nicht vollständig ab.")
        source["source_sha256"] = hashlib.sha256((ROOT / "corpus/pdfs" / source["filename"]).read_bytes()).hexdigest()
        if bid in ("A2024", "R2024"):
            source["selection_note"] = "Seiten ohne extrahierbaren Inhalt (z.B. reine Grafik oder Leerseite) ausgelassen; Original-PDF bleibt vollständig."
    path.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

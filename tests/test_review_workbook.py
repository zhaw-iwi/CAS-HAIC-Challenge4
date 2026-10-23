import json
import xml.etree.ElementTree as ET
import zipfile

from test_assignment import prepared
from src.assignment_ui import download_link

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_book(path):
    with zipfile.ZipFile(path) as archive:
        shared = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        strings = ["".join(item.itertext()) for item in shared]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        names = [sheet.attrib["name"] for sheet in workbook.find("s:sheets", NS)]
        result = {}
        for index, name in enumerate(names, 1):
            sheet = ET.fromstring(archive.read(f"xl/worksheets/sheet{index}.xml"))
            rows = []
            for row in sheet.findall("s:sheetData/s:row", NS):
                cells = {}
                for cell in row:
                    value = cell.find("s:v", NS)
                    if value is not None:
                        cells[cell.attrib["r"]] = strings[int(value.text)] if cell.get("t") == "s" else value.text
                    assert cell.find("s:f", NS) is None, "Untrusted text must never become an Excel formula"
                rows.append(cells)
            result[name] = (rows, sheet)
        return result


def test_workbook_joins_saved_answers_refs_sources_and_human_judgments(tmp_path):
    p = prepared(tmp_path)
    page = p.protocol()["passages"][0]
    chunk = {**page, "chunk_id": "TEST-CHUNK", "score": .9}
    p.store_answer("R0", "F01", "=UNTRUSTED()\nOriginale R0-Antwort", {"model": "Test-R0"}, [chunk])
    p.store_answer("V", "F01", "Erste V-Antwort", {"model": "Test-V", "document_uploaded": True, "service": "Claude", "conversation_mode": "one_chat_all_questions"})
    p.save_human_review("R0", "F01", {"correct": 1, "support": "belegt", "evidence_available": "ja",
        "has_claims": True, "reason": "Menschliche Begründung", "confirmed": True})
    auto = p.frozen_folder / "automatic_r0"
    auto.mkdir()
    (auto / "F01.json").write_text(json.dumps({"proposal": {"correctness_proposal": 0,
        "support": "unbelegt", "evidence_available": "teilweise", "missing_components": ["Test"],
        "reason": "Nur Klassifikation"}, "decisions": [{"name": "correctness", "choice": "incorrect", "confidence": .7}]}))
    before = (p.frozen_folder / "answers/R0/F01.json").read_bytes()
    workbook = p.export_workbook()
    book = read_book(workbook)
    assert set(book) == {"Hinweise", "Übersicht", "Prüftabelle", "Vorprüfung R0", "Quellenseiten", "R0-Chunks", "Kennzahlen", "Langtexte"}
    assert len(book["Übersicht"][0]) == 21
    assert len(book["Prüftabelle"][0]) == 41
    assert len(book["Quellenseiten"][0]) == 13
    overview = book["Übersicht"][0][1]
    assert overview["D2"] == "1" and "E2" not in overview  # V judgment pending, not zero.
    assert overview["G2"] == "ja"  # Human corrected the automatic suggestion.
    row = book["Prüftabelle"][0][1]
    assert row["D2"] == "Eigene Testfrage Nummer 1?"
    assert row["E2"] == "REFERENCE_SECRET_1"
    assert row["H2"].startswith("=UNTRUSTED()")  # Literal string, no formula.
    assert row["J2"] == "0" and row["K2"] == "1"
    assert row["N2"] == "Menschliche Begründung"
    assert book["Prüftabelle"][0][2]["H3"] == "Erste V-Antwort"
    assert book["R0-Chunks"][0][1]["F2"] == page["text"]
    assert book["Prüftabelle"][1].find("s:hyperlinks", NS) is not None
    assert book["Prüftabelle"][1].find("s:autoFilter", NS) is not None
    assert book["Prüftabelle"][1].find("s:sheetViews/s:sheetView/s:pane", NS) is not None
    assert (p.frozen_folder / "answers/R0/F01.json").read_bytes() == before
    with zipfile.ZipFile(p.export()) as archive:
        assert "Challenge_4_Prueftabelle.xlsx" in archive.namelist()
        assert any(name.endswith("/Challenge_4_Prueftabelle.xlsx") for name in archive.namelist())


def test_workbook_preserves_text_beyond_excel_cell_limit_and_failure_status(tmp_path):
    p = prepared(tmp_path)
    long_answer = "Volltext " * 9000
    p.store_answer("R0", "F01", long_answer, {"model": "Test"}, [])
    p.store_failure("V", "F01", "Tatsächlicher Testausfall")
    book = read_book(p.export_workbook())
    pieces = [next(value for cell, value in row.items() if cell.startswith("C")) for row in book["Langtexte"][0][1:]]
    assert "".join(pieces) == long_answer
    assert book["Übersicht"][0][1]["E2"] == "0"
    assert book["Prüftabelle"][0][2]["H3"] == "Tatsächlicher Testausfall"


def test_download_links_are_direct_local_files_and_escape_labels(tmp_path, monkeypatch):
    monkeypatch.setenv("JUPYTERHUB_SERVICE_PREFIX", "/")
    path = tmp_path / "outputs/Prüftabelle.xlsx"
    link = download_link(tmp_path, path, "Excel <Download>")
    assert '/files/outputs/Pr%C3%BCftabelle.xlsx?download=1' in link
    assert 'download="Prüftabelle.xlsx"' in link
    assert "&lt;Download&gt;" in link

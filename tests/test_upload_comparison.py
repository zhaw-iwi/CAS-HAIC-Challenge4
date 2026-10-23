import hashlib
import json

from pypdf import PdfReader
import pytest

from test_assignment import prepared
from src.assignment import dump, fulltext, prompt
from src.corpus import digest


def test_upload_pdf_contains_exact_original_dossier_pages_and_detects_changes(tmp_path):
    p = prepared(tmp_path)
    protocol = p.protocol()
    assert protocol["v_input_mode"] == "document_upload"
    upload = p.frozen_folder / protocol["upload_pdf"]["filename"]
    pages = sorted(protocol["passages"], key=lambda page: page["pdf_page"])
    original = PdfReader(p.root / "corpus/pdfs" / pages[0]["filename"])
    excerpt = PdfReader(upload)
    assert len(excerpt.pages) == 12
    assert [p["pdf_page"] for p in protocol["upload_pdf"]["pages"]] == [p["pdf_page"] for p in pages]
    # Compare page streams rather than extracting text again; images/layout are retained as well.
    for actual, selected in zip(excerpt.pages, pages):
        assert actual.get_contents().get_data() == original.pages[selected["pdf_page"]-1].get_contents().get_data()
    assert protocol["upload_pdf"]["sha256"] == hashlib.sha256(upload.read_bytes()).hexdigest()
    upload.write_bytes(upload.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="Upload-PDF"):
        p.protocol()


def test_upload_answer_records_service_mode_and_pdf_identity(tmp_path):
    p = prepared(tmp_path)
    metadata = {"model": "Angezeigtes Testmodell", "service": "Claude", "conversation_mode": "one_chat_all_questions", "document_uploaded": True}
    with pytest.raises(ValueError, match="Dienst"):
        p.store_answer("V", "F01", "Test", {"model": "Test", "fulltext_pasted": True})
    with pytest.raises(ValueError, match="Dienst"):
        p.store_answer("V", "F01", "Test", {**metadata, "service": "unknown"})
    p.store_answer("V", "F01", "Unveränderte erste Antwort", metadata)
    record = p.answers("V")["F01"]
    assert record["metadata"]["service"] == "Claude"
    assert record["metadata"]["conversation_mode"] == "one_chat_all_questions"
    assert record["uploaded_pdf_sha256"] == p.protocol()["upload_pdf"]["sha256"]
    assert "fulltext_sha256" not in record


def test_legacy_frozen_fulltext_protocol_keeps_its_meaning(tmp_path):
    p = prepared(tmp_path)
    # Construct an old-format fixture; production code never migrates a frozen protocol.
    protocol = p.protocol()
    protocol.pop("v_input_mode")
    protocol.pop("upload_pdf")
    dump(p.frozen_folder / "protocol.json", protocol)
    dump(p.frozen_folder / "integrity.json", {"protocol_sha256": digest(protocol), "references_sha256": digest(protocol["questions"])})
    before = (p.frozen_folder / "protocol.json").read_bytes()
    assert p.v_prompt("F01") == prompt(protocol["questions"][0], fulltext(protocol["passages"]))
    p.store_answer("V", "F01", "Alte Volltextantwort", {"model": "Test", "fulltext_pasted": True})
    assert "fulltext_sha256" in p.answers("V")["F01"]
    assert (p.frozen_folder / "protocol.json").read_bytes() == before

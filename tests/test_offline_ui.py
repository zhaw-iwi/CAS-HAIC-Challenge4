import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.notebook_ui import evidence_html, preview_configs, evidence_browser
from src.retrieval import OpenAIEmbeddings
from src.pipeline import OpenAIBackend, GateDecision
from src.sourcepack import load_pack, seal_pack


def test_offline_blocks_paid_clients_even_with_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("CHALLENGE_OFFLINE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder-not-a-real-key")
    def fail_if_called(**kwargs):
        pytest.fail("API client must not be called in offline mode")
    client = SimpleNamespace(embeddings=SimpleNamespace(create=fail_if_called),
                             responses=SimpleNamespace(parse=fail_if_called))
    with pytest.raises(RuntimeError, match="Offline-Modus"):
        OpenAIEmbeddings(client, "test", tmp_path / "cache").embed(["Test"])
    with pytest.raises(RuntimeError, match="Offline-Modus"):
        OpenAIBackend(client, tmp_path / "raw").parse("test", "Test", {}, GateDecision, 100)
    monkeypatch.delenv("CHALLENGE_OFFLINE")
    with pytest.raises(RuntimeError, match="Offline-Modus"):
        OpenAIEmbeddings(client, "test", tmp_path / "cache").embed(["Test"])


def test_full_text_cards_are_not_truncated_and_escape_source_html():
    text = "Anfang " + "wichtiger vollständiger Beleg " * 120 + "<script>untrusted()</script> ENDE"
    record = {"passage_id": "Q-P1", "chunk_id": "Q-P1-C1", "title": "Titel & Beispiel", "ballot_id": "Q",
        "ballot_date": "2024-03-03", "information_cutoff": "2024-03-02", "pdf_page": 18, "printed_page": 18,
        "source_role": "Abstimmungstext", "text": text, "source_url": "https://example.com/source.pdf"}
    html = evidence_html(record, 1, 2)
    assert "ENDE" in html and html.count("wichtiger vollständiger Beleg") == 120
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "Titel &amp; Beispiel" in html
    assert "#page=18" in html and "1 von 2" in html
    browser = evidence_browser([record])
    assert "ENDE" in browser.children[-1].value


@pytest.mark.parametrize("variable,value", [("chunk_size", 180), ("chunk_overlap", 100), ("top_k", 8), ("filter_ballot", True)])
def test_learner_controls_change_exactly_one_factor(variable, value):
    a, b = preview_configs(variable, value)
    assert [k for k in a if a[k] != b[k]] == [variable]
    with pytest.raises(ValueError):
        preview_configs("chunk_size", 300)
    with pytest.raises(ValueError):
        preview_configs("chunk_overlap", 300)


def test_notebook_is_offline_and_setup_cells_are_protected():
    root = Path(__file__).resolve().parents[1]
    notebook = json.loads((root / "Evidenzknacker.ipynb").read_text(encoding="utf-8"))
    code = "\n".join("".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code")
    assert "load_dotenv" not in code
    assert "OpenAI(" not in code
    assert "RUN_LIVE" not in code
    assert "CHALLENGE_OFFLINE" in code
    assert all(cell["metadata"].get("editable") is False for cell in notebook["cells"] if cell["cell_type"] == "code")


def test_exactly_four_source_packs_and_pdfs_have_correct_pages():
    root = Path(__file__).resolve().parents[1]
    rows = load_pack(root)
    sources = json.loads((root / "corpus/sources.json").read_text(encoding="utf-8"))
    assert len(rows) == 48
    expected = {"A2024", "R2024", "P2024", "K2024"}
    assert {r["ballot_id"] for r in rows} == expected
    assert {s["ballot_id"] for s in sources} == expected
    assert {p.name for p in (root / "corpus/pdfs").glob("*.pdf")} == {f"{bid}.pdf" for bid in expected}
    for source in sources:
        selected = {p for section in source["sections"] for p in section["pdf_pages"]}
        assert {r["pdf_page"] for r in rows if r["ballot_id"] == source["ballot_id"]} == selected


def test_source_pack_detects_changed_originals(tmp_path):
    import hashlib
    folder = tmp_path / "corpus"
    (folder / "pdfs").mkdir(parents=True)
    pdf = folder / "pdfs/test.pdf"
    pdf.write_bytes(b"original test fixture")
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    sources = [{"ballot_id": "Q", "filename": "test.pdf", "status": "available", "source_sha256": sha,
                "sections": [{"pdf_pages": [1]}]}]
    rows = [{"passage_id": "Q-PDF001", "ballot_id": "Q", "source_sha256": sha, "text": "Test"}]
    (folder / "sources.json").write_text(json.dumps(sources))
    (folder / "passages.jsonl").write_text(json.dumps(rows[0]) + "\n")
    seal_pack(tmp_path)
    assert load_pack(tmp_path) == rows
    pdf.write_bytes(b"changed test fixture")
    with pytest.raises(ValueError, match="Quellenbestand"):
        load_pack(tmp_path)


def test_learner_notes_and_one_change_are_saved_without_code_edits(tmp_path):
    from src.notebook_ui import OfflineLab
    root = Path(__file__).resolve().parents[1]
    lab = OfflineLab(root)
    lab.saved = {}
    lab.saved_path = tmp_path / "arbeitsblatt.json"
    lab.show_questions()
    lab.show_experiment_controls()
    lab.variable.value = "top_k"
    lab.value.value = 7
    lab.prediction.value = "Mehr Chunks könnten eine Einschränkung sichtbar machen."
    lab.observations.value = "Offline wurde noch keine Rangliste berechnet."
    lab.save_button.click()
    saved = json.loads(lab.saved_path.read_text(encoding="utf-8"))
    assert saved["mode"] == "offline" and saved["intervention"]["top_k"] == 7
    assert saved["prediction"] == lab.prediction.value
    assert [k for k in saved["baseline"] if saved["baseline"][k] != saved["intervention"][k]] == ["top_k"]

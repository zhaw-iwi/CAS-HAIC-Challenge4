import json
from pathlib import Path
from types import SimpleNamespace
import zipfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pytest

from src.assignment import (Assignment, DOSSIERS, TYPES, PreliminaryEvaluation, evaluate_rag_only,
                            fulltext, run_rag, validate_questions)

ROOT = Path(__file__).resolve().parents[1]


def prepared(tmp_path, freeze=True):
    p = Assignment(ROOT, "A2024", tmp_path)
    ids = [r["passage_id"] for r in p.state["passages"]]
    for i, q in enumerate(p.state["questions"], 1):
        q.update(question=f"Eigene Testfrage Nummer {i}?", reference_answer=f"REFERENCE_SECRET_{i}",
                 required_components=[f"Pflichtbestandteil {i}"],
                 reference_passage_ids=ids[:2] if 11 <= i <= 15 else (ids[:1] if i <= 15 else []),
                 missing_information="Im ganzen Dossier nicht vorhanden." if i > 15 else "", reviewed=True)
    p.state.update(text_reviewed=True, prediction="R0 könnte notwendige Belege übersehen.")
    p.state["config"].update(generation_model="test-model", evaluation_model="test-judge")
    if freeze:
        p.freeze()
    return p


def test_four_choices_and_empty_own_reference_template(tmp_path):
    assert set(DOSSIERS) == {"A2024", "R2024", "P2024", "K2024"}
    p = Assignment(ROOT, "A2024", tmp_path)
    assert len(p.state["questions"]) == 20
    assert all(not q["question"] and not q["reference_answer"] for q in p.state["questions"])
    assert [sum(q["type"] == t for q in p.state["questions"]) for t in TYPES] == [5, 5, 5, 5]
    with pytest.raises(ValueError):
        Assignment(ROOT, "H2016", tmp_path)
    with pytest.raises(ValueError):
        p.freeze()


def test_freeze_keeps_source_text_and_excludes_fulltext_and_references_from_upload_prompt(tmp_path):
    p = prepared(tmp_path)
    qid = "F01"
    exported = (p.frozen_folder / "v_prompts/F01.txt").read_text(encoding="utf-8")
    assert exported == p.v_prompt(qid)
    assert fulltext(p.protocol()["passages"]) not in exported
    assert "A2024_Dossier.pdf" in exported and "Upload-Seite 1:" in exported
    assert p.protocol()["instruction"] in exported
    assert "REFERENCE_SECRET" not in exported and "Pflichtbestandteil" not in exported
    assert {r["ballot_id"] for r in p.protocol()["passages"]} == {"A2024"}
    with pytest.raises(ValueError):
        p.save()
    refs = p.frozen_folder / "references.json"
    refs.write_text("[]")
    with pytest.raises(ValueError, match="verändert"):
        p.protocol()


def test_corrected_text_keeps_original_and_frozen_ui_renders_all_steps(tmp_path):
    from src.assignment_ui import ChallengeNotebook
    p = prepared(tmp_path, freeze=False)
    original = p.original[0]["text"]
    p.state["passages"][0]["text"] += "\nTestkorrektur der Extraktion."
    assert p.original[0]["text"] == original
    p.freeze()
    session = ChallengeNotebook(ROOT, tmp_path)
    session.show_dossier()
    session.show_references()
    session.show_protocol()
    session.show_runs()
    session.show_evaluation()
    session.show_results()
    assert session.project.frozen and len(session.refreshers) == 6


def test_reference_validation_rejects_duplicates_wrong_pages_and_missing_components(tmp_path):
    p = prepared(tmp_path, freeze=False)
    assert validate_questions(p.state["questions"], p.state["passages"]) == []
    p.state["questions"][1]["question"] = p.state["questions"][0]["question"]
    p.state["questions"][10]["reference_passage_ids"] = ["OTHER-PDF001"]
    p.state["questions"][19]["missing_information"] = ""
    errors = validate_questions(p.state["questions"], p.state["passages"])
    assert any("doppelte" in e for e in errors)
    assert any("unbekannte" in e for e in errors)
    assert any("fehlende Information" in e for e in errors)


def test_first_v_answer_is_immutable_and_requires_document_upload_confirmation(tmp_path):
    p = prepared(tmp_path)
    with pytest.raises(ValueError):
        p.store_answer("V", "F01", "Testantwort", {"model": "Test", "document_uploaded": False, "service": "Claude", "conversation_mode": "one_chat_all_questions"})
    p.store_answer("V", "F01", "Erste Testantwort", {"model": "Test", "document_uploaded": True, "service": "Claude", "conversation_mode": "one_chat_all_questions"})
    with pytest.raises(ValueError):
        p.store_answer("V", "F01", "Korrigierte Testantwort", {"model": "Test", "document_uploaded": True, "service": "Claude", "conversation_mode": "one_chat_all_questions"})
    assert p.answers("V")["F01"]["answer"] == "Erste Testantwort"


def test_scores_use_confirmed_human_judgments_with_fixed_denominators(tmp_path):
    p = prepared(tmp_path)
    for condition in ("R0", "V"):
        for i in range(1, 21):
            qid = f"F{i:02d}"
            if condition == "R0" and i == 20:
                p.store_failure("R0", qid, "Testfall: API-Ausfall nach tatsächlichem Versuch")
                continue
            p.store_answer(condition, qid, "Testantwort, kein Modellresultat", {"model": "Test", "document_uploaded": True, "service": "Claude", "conversation_mode": "one_chat_all_questions"}, [] if condition == "R0" else None)
            correct = int(condition == "V" or i <= 10 or i >= 16)
            p.save_human_review(condition, qid, {"correct": correct,
                "support": ("belegt" if correct else "unbelegt") if i <= 15 else "nicht anwendbar",
                "evidence_available": "ja" if i <= 15 else "nicht anwendbar",
                "has_claims": i <= 15, "reason": "Menschliche Testbegründung", "confirmed": True})
    rows, metrics = p.result_tables()
    lookup = {(m["condition"], m["metric"]): m for m in metrics}
    assert lookup[("R0", "korrekt insgesamt")]["numerator"] == 14
    assert lookup[("R0", "korrekt insgesamt")]["denominator"] == 20
    assert lookup[("R0", "beantwortbare Fragen korrekt")]["numerator"] == 10
    assert lookup[("R0", "richtige Begrenzungen")]["numerator"] == 4
    support = lookup[("R0", "vollständig belegt unter Antworten mit Sachbehauptungen")]
    assert (support["numerator"], support["denominator"]) == (10, 15)
    assert lookup[("V", "korrekt insgesamt")]["numerator"] == 20
    assert len(rows) == 40
    zip_path = p.export()
    with zipfile.ZipFile(zip_path) as archive:
        assert not any(Path(name).name.startswith(".env") for name in archive.namelist())
        assert "Kurzbericht_Vorlage.md" in archive.namelist()
        assert any(name.endswith("comparison.csv") for name in archive.namelist())


def test_pending_work_does_not_become_zero_accuracy(tmp_path):
    p = prepared(tmp_path)
    rows, metrics = p.result_tables()
    assert all(m["numerator"] is None for m in metrics if m["metric"] == "korrekt insgesamt")
    assert all(r["status"] == "missing" for r in rows)


def test_offline_blocks_both_new_model_paths(tmp_path, monkeypatch):
    p = prepared(tmp_path)
    monkeypatch.setenv("CHALLENGE_OFFLINE", "1")
    with pytest.raises(RuntimeError, match="Offline-Modus"):
        run_rag(p, None, None)
    with pytest.raises(RuntimeError, match="Offline-Modus"):
        evaluate_rag_only(p, None)


def test_rag_generation_has_no_reference_leak_or_pre_generation_gate(tmp_path, monkeypatch):
    p = prepared(tmp_path)
    monkeypatch.setenv("CHALLENGE_OFFLINE", "0")  # Fake local client only.
    calls = []
    class Embeddings:
        model = "text-embedding-3-small"
        def embed(self, texts):
            assert not any("REFERENCE_SECRET" in t for t in texts)
            return np.array([[1., 0.] for _ in texts], dtype="float32")
    def create(**request):
        calls.append(request)
        assert "REFERENCE_SECRET" not in request["input"]
        assert "Pflichtbestandteil" not in request["input"]
        return SimpleNamespace(status="completed", output_text="Lokales Test-Doppel", model="test-model",
                               model_dump=lambda **kwargs: {"status": "completed", "output_text": "Lokales Test-Doppel"})
    run_rag(p, Embeddings(), SimpleNamespace(responses=SimpleNamespace(create=create)))
    assert len(calls) == 20 and len(p.answers("R0")) == 20
    assert all({c["ballot_id"] for c in r["retrieved"]} == {"A2024"} for r in p.answers("R0").values())
    before = json.dumps(p.answers("R0"), sort_keys=True)
    class Judge:
        def __init__(self):
            self.calls = []
        def evaluate(self, model, instruction, state):
            self.calls.append(state)
            assert state["r0"]["condition"] == "R0" and "reference" in state
            return PreliminaryEvaluation(correctness_proposal=0, support="unbelegt", evidence_available="teilweise",
                missing_components=["Test"], evidence_ids=[], reason="Test-Doppel"), "local-test.json", []
    judge = Judge()
    evaluate_rag_only(p, judge)
    assert len(judge.calls) == 20
    assert not p.answers("V")
    assert before == json.dumps(p.answers("R0"), sort_keys=True)
    _, metrics = p.result_tables()
    assert all(m["numerator"] is None for m in metrics if m["metric"] == "korrekt insgesamt")

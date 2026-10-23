import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import live
from src.assignment import BASE_CONFIG


def test_live_config_is_opt_in_and_teacher_settings_win(tmp_path, monkeypatch):
    monkeypatch.delenv("CHALLENGE_OFFLINE", raising=False)
    monkeypatch.setenv("OPENAI_GENERATION_MODEL", "environment-test-model")
    assert not live.enabled()
    assert not live.configured_models(tmp_path)["generation_model"]
    monkeypatch.setenv("CHALLENGE_OFFLINE", "0")
    assert live.configured_models(tmp_path)["generation_model"] == "environment-test-model"
    (tmp_path / "instructor_config.json").write_text(json.dumps({"generation_model": "teacher-test-model"}))
    assert live.configured_models(tmp_path)["generation_model"] == "teacher-test-model"


def test_probe_checks_inputs_before_calls_or_files(tmp_path, monkeypatch):
    monkeypatch.setenv("CHALLENGE_OFFLINE", "1")
    with pytest.raises(RuntimeError, match="Offline-Modus"):
        live.run_probe(tmp_path, [], "Test", "Referenz", {}, None)
    monkeypatch.setenv("CHALLENGE_OFFLINE", "0")
    with pytest.raises(ValueError, match="Probe-Referenz"):
        live.run_probe(tmp_path, [], "Test", "", {}, None)
    with pytest.raises(ValueError, match="GENERATION_MODEL"):
        live.run_probe(tmp_path, [], "Test", "Referenz", BASE_CONFIG, None)
    assert not list(tmp_path.iterdir())


def test_probe_uses_three_services_and_preserves_separate_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("CHALLENGE_OFFLINE", "0")  # All clients below are local fakes.
    calls = []
    def embeddings(**request):
        calls.append("embeddings")
        return SimpleNamespace(data=[SimpleNamespace(index=i, embedding=[1., .5]) for i in range(len(request["input"]))],
                               usage=SimpleNamespace(model_dump=lambda: {"total_tokens": 3}))
    def response(**request):
        calls.append("responses")
        assert "PROBE_REFERENCE_SECRET" not in request["input"]
        return SimpleNamespace(status="completed", output_text="Test-Antwort [TEST-PDF001]",
                               model_dump=lambda **kwargs: {"status": "completed", "output_text": "Test-Antwort [TEST-PDF001]"})
    def decisions(**request):
        calls.append("decisions")
        assert "PROBE_REFERENCE_SECRET" in request["input"]
        selections = {"correctness": "incorrect", "support": "belegt", "evidence_available": "ja", "component_0": "missing_or_wrong"}
        return SimpleNamespace(model_dump=lambda **kwargs: {"model": request["model"], "usage": {"input_tokens": 100},
            "answers": [{"name": q["name"], "type": "choice", "choice": selections[q["name"]],
                         "confidence": .7, "probabilities": []} for q in request["questions"]]})
    api = SimpleNamespace(embeddings=SimpleNamespace(create=embeddings), responses=SimpleNamespace(create=response),
                          decisions=SimpleNamespace(create=decisions))
    page = {"passage_id": "TEST-PDF001", "title": "Test", "information_cutoff": "2024-01-01",
            "pdf_page": 1, "source_role": "Originaler Abstimmungstext", "ballot_id": "TEST", "text": "Kurzer Testbeleg."}
    config = {**BASE_CONFIG, "generation_model": "test-model"}
    result = live.run_probe(tmp_path, [page], "Eigene Frage", "PROBE_REFERENCE_SECRET", config, api)
    assert calls == ["embeddings", "embeddings", "responses", "decisions"]
    assert result["proposal"]["correctness_proposal"] == 0
    folder = Path(result["folder"])
    assert folder.parent == tmp_path / "outputs/live_probes"
    assert (folder / "generation.json").exists()
    assert (folder / "embedding_usage.json").exists()
    assert not (tmp_path / "outputs/meine_challenge").exists()


def test_live_ui_initialization_never_creates_api_client(tmp_path, monkeypatch):
    from src.assignment_ui import ChallengeNotebook
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("CHALLENGE_OFFLINE", "0")
    monkeypatch.setenv("OPENAI_GENERATION_MODEL", "test-model")
    def unexpected():
        pytest.fail("Rendering controls must not initialize the paid client")
    monkeypatch.setattr(live, "client", unexpected)
    session = ChallengeNotebook(root, tmp_path)
    session.show_protocol()
    assert session.project.state["config"]["generation_model"] == "test-model"
    assert session.project.state["config"]["evaluation_model"]
    assert not session.project.frozen

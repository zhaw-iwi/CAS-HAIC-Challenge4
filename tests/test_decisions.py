"""Verify the dedicated endpoint with the real SDK and local HTTP transport only."""
import json
from pathlib import Path
import sys

import httpx2 as httpx
import pytest
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.assignment import DecisionsEvaluator, EVALUATOR_INSTRUCTION


@pytest.mark.parametrize("mode", ["complete", "refusal", "missing", "duplicate", "invalid", "transport_error"])
def test_decisions_endpoint_preserves_classifications_and_failures(tmp_path, monkeypatch, mode):
    monkeypatch.setenv("CHALLENGE_OFFLINE", "0")  # Local MockTransport; no network.
    requests = []
    def handle(request):
        assert request.url.path == "/v1/decisions"
        body = json.loads(request.content)
        requests.append(body)
        assert body["model"] == "gpt-6-luna"
        assert set(body) == {"model", "input", "questions"}
        state = json.loads(body["input"])
        assert state["r0"]["condition"] == "R0"
        assert state["reference"]["reference_answer"] == "Geprüfte Referenz"
        if mode == "transport_error":
            raise httpx.ConnectError("Local test failure", request=request)
        selections = {"correctness": "incorrect", "support": "teilweise belegt",
                      "evidence_available": "teilweise", "component_0": "present",
                      "component_1": "missing_or_wrong", "component_2": "uncertain"}
        answers = [{"name": q["name"], "type": "choice", "choice": selections[q["name"]],
                    "confidence": .8, "probabilities": [
                        {"value": option["value"], "probability": .8 if option["value"] == selections[q["name"]]
                         else .2 / (len(q["choices"]) - 1)} for option in q["choices"]]}
                   for q in body["questions"]]
        if mode == "refusal":
            answers[0] = {"name": "correctness", "type": "refusal"}
        elif mode == "missing":
            answers.pop()
        elif mode == "duplicate":
            answers[-1] = answers[0]
        elif mode == "invalid":
            answers[0]["choice"] = "unexpected"
        return httpx.Response(200, json={"model": "gpt-6-luna", "answers": answers,
            "usage": {"input_tokens": 42, "output_tokens": 0, "total_tokens": 42,
                      "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
                      "output_tokens_details": {"reasoning_tokens": 0}}})

    client = OpenAI(api_key="test-placeholder", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    backend = DecisionsEvaluator(client, tmp_path)
    state = {"reference": {"reference_answer": "Geprüfte Referenz",
                           "required_components": ["Bestandteil A", "Bestandteil B", "Bestandteil C"]},
             "full_dossier": "Vollständiger Text", "r0": {"condition": "R0", "answer": "Test"}}
    if mode == "complete":
        proposal, raw_file, answers = backend.evaluate("gpt-6-luna", EVALUATOR_INSTRUCTION, state)
        assert proposal.correctness_proposal == 0
        assert proposal.missing_components == ["Bestandteil B"]
        assert proposal.evidence_ids == []  # No invented evidence IDs or generated explanation.
        assert answers[-1]["choice"] == "uncertain"
        assert answers[0]["confidence"] == .8
        log = json.loads(Path(raw_file).read_text(encoding="utf-8"))
        assert log["response"]["usage"]["input_tokens"] == 42
    else:
        with pytest.raises(Exception):
            backend.evaluate("gpt-6-luna", EVALUATOR_INSTRUCTION, state)
        log = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
        assert "error_type" in log if mode == "transport_error" else "response" in log
    assert len(requests) == 1
    assert log["endpoint"] == "/v1/decisions"
    assert "request" in log
    client.close()


def test_decisions_default_offline_guard_blocks_client(tmp_path, monkeypatch):
    monkeypatch.delenv("CHALLENGE_OFFLINE", raising=False)
    with pytest.raises(RuntimeError, match="Offline-Modus"):
        DecisionsEvaluator(None, tmp_path).evaluate("gpt-6-luna", "Test", {})
    assert not list(tmp_path.iterdir())

import json
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.corpus import extract_passages, make_chunks
from src.retrieval import VectorStore, OpenAIEmbeddings
from src.pipeline import (GateDecision, Answer, Claim, ExperimentConfig, OpenAIBackend,
                          assert_one_change, run_question, run_comparison)
from src.evaluation import summarize


def chunks():
    return [{"chunk_id": str(i), "ballot_id": bid, "information_cutoff": "2016-02-27",
             "text": "Beleg", "source_passage_ids": [f"P{i}"]}
            for i, bid in enumerate(["OTHER", "OTHER", "TARGET"])]


def config():
    return ExperimentConfig("embedding-test", "decision-test", "generation-test", top_k=1)


def question():
    return {"question_id": "Q1", "question": "Testfrage", "ballot_id": "TARGET",
            "information_cutoff": "2016-02-27", "reference_status": "draft",
            "required_facts": ["SECRET_REFERENCE"], "reference_passage_ids": ["P2"]}


class Embeddings:
    model = "embedding-test"
    usage = []

    def embed(self, texts):
        return np.array([[1., 0.] for _ in texts], dtype="float32")


class Backend:
    def __init__(self, actions):
        self.actions = iter(actions)
        self.states = []

    def parse(self, model, prompt, state, schema, max_output_tokens):
        self.states.append(state)
        if schema is GateDecision:
            return GateDecision(action=next(self.actions), relevant_chunk_ids=[p["chunk_id"] for p in state["passages"]],
                                missing_information=[], reason="Test-Doppel"), "test-only.json"
        ids = [p["chunk_id"] for p in state["passages"]]
        return Answer(explanation="Test-Doppel, kein Modellresultat", claims=[Claim(text="Test", kind="fact", chunk_ids=ids)],
                      uncertainty=[]), "test-only.json"


def test_faiss_filters_before_top_k_and_roundtrip(tmp_path):
    store = VectorStore(chunks(), [[1, 0], [.99, .01], [0, 1]])
    assert store.search([1, 0], 1)[0]["ballot_id"] == "OTHER"
    assert store.search([1, 0], 1, ballot_ids=["TARGET"])[0]["chunk_id"] == "2"
    assert store.search([1, 0], 1, ballot_ids=["MISSING"]) == []
    assert store.search([1, 0], 1, cutoff="2015-01-01") == []
    assert store.search([1, 0], 1, ballot_ids=["TARGET"], threshold=.5) == []
    store.save(tmp_path)
    metadata = json.loads((tmp_path / "metadata.json").read_text())
    loaded = VectorStore(metadata, np.load(tmp_path / "vectors.npy"))
    assert loaded.search([0, 1], 1)[0]["chunk_id"] == "2"


def test_real_pypdf_and_token_chunks():
    root = Path(__file__).resolve().parents[1]
    passages = extract_passages(root, ballot_ids={"A2024"})
    sources = json.loads((root / "corpus/sources.json").read_text(encoding="utf-8"))
    assert len(passages) == 12
    assert all(s["status"] == "available" for s in sources)
    assert {p["source_role"] for p in passages} >= {"Originaler Abstimmungstext", "Argumente des Initiativkomitees"}
    assert "Altersrente" in " ".join(p["text"] for p in passages)
    rows = make_chunks(passages, 100, 10)
    assert len(rows) > len(passages)
    assert all(c["source_passage_ids"] == [c["passage_id"]] for c in rows)
    assert len({c["chunk_id"] for c in rows}) == len(rows)
    assert make_chunks(passages, 100, 10) == rows
    assert make_chunks(passages, 110, 10)[0]["chunk_id"] != rows[0]["chunk_id"]
    with pytest.raises(ValueError):
        make_chunks(passages, 100, 100)


def test_gate_retrieves_once_then_qualifies_and_no_reference_leak():
    store = VectorStore(chunks(), [[1, 0], [.99, .01], [0, 1]])
    backend = Backend(["retrieve_more", "retrieve_more"])
    result = run_question(question(), store, Embeddings(), backend, config())
    assert len(result["gate_trace"]) == 2
    assert len(result["retrieved"]) == 2
    assert result["effective_decision"]["action"] == "qualify"
    assert "SECRET_REFERENCE" not in json.dumps(backend.states)
    assert "required_facts" not in json.dumps(backend.states)


def test_human_review_stops_generation():
    backend = Backend(["human_review"])
    result = run_question(question(), VectorStore(chunks(), [[1, 0]] * 3), Embeddings(), backend, config())
    assert result["answer"] is None
    assert len(backend.states) == 1


def test_comparison_rejects_multiple_changes_and_preserves_failures(tmp_path):
    baseline = config()
    with pytest.raises(ValueError):
        assert_one_change(baseline, replace(baseline, top_k=2, filter_ballot=True))
    passages = [{"passage_id": "TARGET-P1", "ballot_id": "TARGET", "information_cutoff": "2016-02-27", "text": "Testbeleg."}]
    class FailingBackend:
        def parse(self, *args):
            raise RuntimeError("Testfehler")
    with pytest.raises(RuntimeError):
        run_comparison(passages, [question()], Embeddings(), FailingBackend(), baseline,
                       replace(baseline, top_k=2), "Vorhersage", tmp_path, 1)
    runs = list(tmp_path.glob("*/runs.jsonl"))
    assert len(runs) == 1
    assert json.loads(runs[0].read_text())["status"] == "error"


def test_unknown_citations_and_unreviewed_recall():
    class BadCitation(Backend):
        def parse(self, model, prompt, state, schema, max_output_tokens):
            if schema is Answer:
                return Answer(explanation="Test", claims=[Claim(text="Test", kind="fact", chunk_ids=["invented"])], uncertainty=[]), "test.json"
            return super().parse(model, prompt, state, schema, max_output_tokens)
    record = run_question(question(), VectorStore(chunks(), [[1, 0]] * 3), Embeddings(), BadCitation(["answer"]), config())
    assert record["status"] == "invalid_citations"
    record.update(question_id="Q1", condition="A", repetition=1)
    table = summarize([record], [question()])
    assert table["reference_recall"].isna().all()


def test_openai_transport_records_request_and_raw_response(tmp_path, monkeypatch):
    # Real SDK request/response handling over a local fake HTTP transport, never the network.
    import httpx2 as httpx
    from openai import OpenAI
    monkeypatch.setenv("CHALLENGE_OFFLINE", "0")  # MockTransport only; no network calls.
    calls = []
    def handle(request):
        data = json.loads(request.content)
        calls.append(data)
        assert data["store"] is False
        assert data["text"]["format"]["type"] == "json_schema"
        payload = {"action": "human_review", "relevant_chunk_ids": [], "missing_information": ["Test"], "reason": "Test-Doppel"}
        return httpx.Response(200, json={"id": "resp_test", "object": "response", "created_at": 0,
            "model": "decision-test", "status": "completed", "error": None, "incomplete_details": None,
            "output": [{"id": "msg_test", "type": "message", "role": "assistant", "status": "completed",
                        "content": [{"type": "output_text", "text": json.dumps(payload), "annotations": []}]}],
            "usage": {"input_tokens": 2, "output_tokens": 2, "total_tokens": 4}})
    client = OpenAI(api_key="test-placeholder", http_client=httpx.Client(transport=httpx.MockTransport(handle)))
    decision, filename = OpenAIBackend(client, tmp_path).parse("decision-test", "Test", {}, GateDecision, 500)
    assert decision.action == "human_review"
    assert len(calls) == 1
    log = json.loads(Path(filename).read_text())
    assert log["response"]["usage"]["total_tokens"] == 4


def test_embedding_cache_avoids_duplicate_requests(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setenv("CHALLENGE_OFFLINE", "0")  # FakeAPI only; no network calls.
    calls = []
    class FakeAPI:
        def create(self, model, input):
            calls.append(input)
            return SimpleNamespace(data=[SimpleNamespace(index=i, embedding=[1., float(i)]) for i in range(len(input))],
                                   usage=SimpleNamespace(model_dump=lambda: {"total_tokens": len(input)}))
    embedder = OpenAIEmbeddings(SimpleNamespace(embeddings=FakeAPI()), "test", tmp_path)
    vectors = embedder.embed(["a", "b", "a"])
    assert calls == [["a", "b"]]
    np.testing.assert_array_equal(vectors[0], vectors[2])
    embedder.embed(["b", "a"])
    assert len(calls) == 1


def test_successful_ab_run_keeps_every_independent_repetition(tmp_path):
    passages = [{"passage_id": "TARGET-P1", "ballot_id": "TARGET", "information_cutoff": "2016-02-27", "text": "Testbeleg."}]
    baseline = config()
    q = {**question(), "reference_status": "reviewed", "reference_passage_ids": ["TARGET-P1"]}
    backend = Backend(["answer"] * 6)
    folder, records = run_comparison(passages, [q], Embeddings(), backend, baseline,
        replace(baseline, top_k=2), "Explizite Testvorhersage", tmp_path, repetitions=3)
    assert [(r["condition"], r["repetition"]) for r in records] == [
        ("A", 1), ("B", 1), ("A", 2), ("B", 2), ("A", 3), ("B", 3)]
    assert len(backend.states) == 12  # six fresh gate calls and six fresh generations
    assert len((folder / "runs.jsonl").read_text().splitlines()) == 6
    protocol = json.loads((folder / "protocol.json").read_text())
    assert protocol["prediction"] == "Explizite Testvorhersage"
    assert protocol["package_versions"]["faiss-cpu"]
    assert summarize(records, [q])["reference_recall"].tolist() == [1.] * 6

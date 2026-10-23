"""Explicit live connections and isolated one-question rehearsal."""
import json
import os
import uuid
from pathlib import Path

from src.assignment import (BASE_CONFIG, DecisionsEvaluator, EVALUATOR_INSTRUCTION,
                            dump, fulltext, now, prompt)
from src.corpus import make_chunks
from src.retrieval import OpenAIEmbeddings, VectorStore
from src.runtime import require_live_access


def enabled():
    return os.environ.get("CHALLENGE_OFFLINE", "1") == "0"


def configured_models(root):
    """No credential file reads: Compose supplies environment only in live mode."""
    config = dict(BASE_CONFIG)
    path = Path(root) / "instructor_config.json"
    overrides = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    fields = {"embedding_model": "OPENAI_EMBEDDING_MODEL",
              "generation_model": "OPENAI_GENERATION_MODEL",
              "evaluation_model": "OPENAI_DECISION_MODEL"}
    for key, environment in fields.items():
        value = overrides.get(key) or (os.environ.get(environment) if enabled() else None)
        if value:
            config[key] = value.strip()
    return config


def client():
    require_live_access()
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise ValueError("OPENAI_API_KEY fehlt. In .env neben compose.yaml eintragen und den Live-Container neu starten.")
    from openai import OpenAI
    # Every paid attempt remains visible; do not hide retries in the SDK.
    return OpenAI(max_retries=0, timeout=60.0)


def embedder(root, api, config):
    return OpenAIEmbeddings(api, config["embedding_model"], Path(root) / "cache/openai_embeddings")


def run_probe(root, passages, question, reference, config, api):
    """One fresh trial; never writes assignment preparations, frozen work or main answers."""
    require_live_access()
    if not question.strip() or not reference.strip():
        raise ValueError("Separate Probefrage und eigene geprüfte Probe-Referenz eintragen.")
    if not config.get("generation_model") or not config.get("evaluation_model"):
        raise ValueError("OPENAI_GENERATION_MODEL und OPENAI_DECISION_MODEL in .env festlegen und neu starten.")
    folder = Path(root) / "outputs/live_probes" / (now().replace(":", "-") + "-" + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True)
    dump(folder / "protocol.json", {"purpose": "Separate Funktionsprobe; kein Hauptvergleich",
        "config": config, "question": question, "reference": reference, "passages": passages})
    embeddings = embedder(root, api, config)
    try:
        chunks = make_chunks(passages, config["chunk_size"], config["chunk_overlap"])
        store = VectorStore(chunks, embeddings.embed([c["text"] for c in chunks]))
        store.save(folder / "index")
        retrieved = store.search(embeddings.embed([question])[0], k=config["top_k"])
        context = "\n\n".join(f"[{c['passage_id']}] | Chunk {c['chunk_id']} | {c['source_role']}\n{c['text']}" for c in retrieved)
        request = {"model": config["generation_model"], "input": prompt({"question_id": "PROBE", "question": question}, context),
                   "max_output_tokens": config["max_output_tokens"], "store": False}
        dump(folder / "generation.json", {"request": request, "retrieved": retrieved})
        response = api.responses.create(**request)
        dump(folder / "generation.json", {"request": request, "retrieved": retrieved,
                                           "response": response.model_dump(mode="json")})
        if response.status != "completed" or not response.output_text.strip():
            raise ValueError("Probe ohne vollständige Antwort. Rohdaten erhalten; Ausgabelimit/Modell vor Hauptlauf prüfen.")
        state = {"reference": {"question_id": "PROBE", "question": question, "reference_answer": reference,
                               "required_components": [reference], "type": "Separate Funktionsprobe"},
                 "full_dossier": fulltext(passages),
                 "r0": {"condition": "R0", "answer": response.output_text, "retrieved": retrieved}}
        proposal, raw, decisions = DecisionsEvaluator(api, folder / "raw_evaluation").evaluate(
            config["evaluation_model"], EVALUATOR_INSTRUCTION, state)
        result = {"answer": response.output_text, "proposal": proposal.model_dump(), "decisions": decisions,
                  "raw_file": raw, "folder": str(folder), "completed_at": now()}
        dump(folder / "result.json", result)
        return result
    except Exception as exc:
        dump(folder / "failure.json", {"error_type": type(exc).__name__, "failed_at": now()})
        raise
    finally:
        dump(folder / "embedding_usage.json", embeddings.usage)

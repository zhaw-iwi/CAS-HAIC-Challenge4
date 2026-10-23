"""Mechanical checks only: citation existence is not factual support."""
import pandas as pd


def summarize(records, questions):
    references = {q["question_id"]: q for q in questions}
    rows = []
    for record in records:
        question = references[record["question_id"]]
        retrieved = record.get("retrieved", [])
        # Draft or empty references must never become a misleading zero/one score.
        expected = set(question.get("reference_passage_ids", []))
        found = {pid for c in retrieved for pid in c["source_passage_ids"]}
        reviewed = question.get("reference_status") == "reviewed"
        rows.append({"question_id": record["question_id"], "condition": record["condition"],
            "repetition": record["repetition"], "status": record["status"],
            "retrieved_count": len(retrieved),
            "wrong_ballot_count": sum(c["ballot_id"] != question["ballot_id"] for c in retrieved),
            "post_cutoff_count": sum(c["information_cutoff"] > question["information_cutoff"] for c in retrieved),
            "reference_recall": len(expected & found) / len(expected) if expected and reviewed else None,
            "unknown_citations": len(record.get("unknown_citations", [])),
            "gate_action": record.get("effective_decision", {}).get("action"),
            "human_claim_support": None})
    return pd.DataFrame(rows)

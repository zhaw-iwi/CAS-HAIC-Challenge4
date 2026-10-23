"""Exact CPU cosine retrieval with metadata filtering before top-k."""
import json
from pathlib import Path

import faiss
import numpy as np

from src.corpus import digest
from src.runtime import require_live_access


class OpenAIEmbeddings:
    def __init__(self, client, model, cache_dir):
        self.client, self.model = client, model
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.usage = []

    def embed(self, texts):
        vectors = [None] * len(texts)
        pending = {}
        for i, text in enumerate(texts):
            key = digest({"model": self.model, "text": text})
            path = self.cache_dir / f"{key}.json"
            if path.exists():
                vectors[i] = json.loads(path.read_text())["vector"]
            else:
                pending.setdefault(key, {"text": text, "indices": []})["indices"].append(i)
        keys = list(pending)
        for start in range(0, len(keys), 64):
            require_live_access()
            batch = keys[start:start + 64]
            response = self.client.embeddings.create(model=self.model, input=[pending[k]["text"] for k in batch])
            self.usage.append(response.usage.model_dump())
            for item in response.data:
                key = batch[item.index]
                vector = item.embedding
                (self.cache_dir / f"{key}.json").write_text(json.dumps({"model": self.model, "vector": vector}))
                for i in pending[key]["indices"]:
                    vectors[i] = vector
        return np.asarray(vectors, dtype="float32")


class VectorStore:
    def __init__(self, chunks, vectors):
        self.chunks = list(chunks)
        self.vectors = np.array(vectors, dtype="float32", copy=True)
        if self.vectors.ndim != 2 or len(chunks) != len(vectors) or not len(chunks):
            raise ValueError("Chunks und Vektoren müssen vollständig und gleich lang sein.")
        if not np.isfinite(self.vectors).all() or (np.linalg.norm(self.vectors, axis=1) == 0).any():
            raise ValueError("Ungültige Embeddings.")
        if len({c["chunk_id"] for c in chunks}) != len(chunks):
            raise ValueError("Chunk-IDs müssen eindeutig sein.")
        faiss.normalize_L2(self.vectors)
        self.index = faiss.IndexFlatIP(self.vectors.shape[1])
        self.index.add(self.vectors)

    def search(self, query, k=5, ballot_ids=None, cutoff=None, threshold=None):
        if k < 1:
            raise ValueError("k muss positiv sein.")
        eligible = [i for i, c in enumerate(self.chunks)
                    if (ballot_ids is None or c["ballot_id"] in ballot_ids)
                    and (cutoff is None or c["information_cutoff"] <= cutoff)]
        if not eligible:
            return []
        query = np.array(query, dtype="float32", copy=True).reshape(1, -1)
        if query.shape[1] != self.vectors.shape[1] or not np.isfinite(query).all() or np.linalg.norm(query) == 0:
            raise ValueError("Frage-Embedding passt nicht zum Index.")
        faiss.normalize_L2(query)
        # Rebuilding a small exact index avoids post-top-k filtering errors.
        index = faiss.IndexFlatIP(self.vectors.shape[1])
        index.add(self.vectors[eligible])
        scores, ids = index.search(query, min(k, len(eligible)))
        return [{**self.chunks[eligible[i]], "score": float(score)}
                for score, i in zip(scores[0], ids[0])
                if i >= 0 and (threshold is None or score >= threshold)]

    def save(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(folder / "index.faiss"))
        np.save(folder / "vectors.npy", self.vectors)
        (folder / "metadata.json").write_text(json.dumps(self.chunks, ensure_ascii=False, indent=2), encoding="utf-8")
        (folder / "manifest.json").write_text(json.dumps({"count": len(self.chunks), "dimensions": self.vectors.shape[1],
            "metadata_sha256": digest(self.chunks), "metric": "cosine; L2-normalised IndexFlatIP"}, indent=2))

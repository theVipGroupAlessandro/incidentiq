"""Semantic search over the corpus, in memory (exact cosine search with numpy).

The model name is stored with the index, so vectors from different models are never mixed.
"""
import numpy as np

MODELS = {
    "bge-small": {
        "name": "BAAI/bge-small-en-v1.5",
        # BGE recommends this instruction in front of short search queries.
        "query_prefix": "Represent this sentence for searching relevant passages: ",
    },
    "minilm": {
        "name": "sentence-transformers/all-MiniLM-L6-v2",
        "query_prefix": "",
    },
}

_loaded_models = {}


def load_encoder(model_key):
    """Load a model once and return a function: list of texts -> normalized vectors."""
    if model_key not in _loaded_models:
        # Imported here because it is slow to import and the tests do not need it.
        from sentence_transformers import SentenceTransformer
        _loaded_models[model_key] = SentenceTransformer(MODELS[model_key]["name"])
    model = _loaded_models[model_key]
    return lambda texts: model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)


class SemanticIndex:
    """Document vectors for one model, plus exact top-k search."""

    def __init__(self, documents, encode, model_key, query_prefix=""):
        self.documents = documents
        self.encode = encode
        self.model_key = model_key
        self.query_prefix = query_prefix
        self.vectors = encode([doc["text"] for doc in documents])  # one row per document

    def search(self, query, top_k=5, where=None):
        """Return up to `top_k` (document, score) pairs, best first.

        Vectors are normalized, so the dot product is the cosine similarity.
        `where` is an optional filter: a function document -> True/False.
        """
        query_vector = self.encode([self.query_prefix + query])[0]
        scores = self.vectors @ query_vector
        results = []
        for i in np.argsort(-scores):
            if where is None or where(self.documents[i]):
                results.append((self.documents[i], float(scores[i])))
                if len(results) == top_k:
                    break
        return results


def build_index(documents, model_key, use_query_prefix=True):
    prefix = MODELS[model_key]["query_prefix"] if use_query_prefix else ""
    return SemanticIndex(documents, load_encoder(model_key), model_key, prefix)


def top_evidence(results, k=5):
    """Collapse document results to distinct evidence ids (an ADR has several sections), keeping the order."""
    evidence = []
    for doc, score in results:
        if doc["evidence_id"] not in [e for e, _ in evidence]:
            evidence.append((doc["evidence_id"], score))
    return evidence[:k]
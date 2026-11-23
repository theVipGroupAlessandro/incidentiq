import numpy as np

from app.embeddings import SemanticIndex, top_evidence

DOCS = [
    {"doc_id": "A", "evidence_id": "A", "kind": "incident", "text": "database pool exhausted"},
    {"doc_id": "B", "evidence_id": "B", "kind": "incident", "text": "card declined by bank"},
    {"doc_id": "C#x", "evidence_id": "C", "kind": "adr", "text": "database pool limits"},
    {"doc_id": "C#y", "evidence_id": "C", "kind": "adr", "text": "database pool alerts"},
]


def fake_encode(texts):
    """Tiny stand-in for a real model: bag of words over a fixed vocabulary, normalized."""
    vocabulary = ["database", "pool", "exhausted", "card", "declined", "bank", "limits", "alerts"]
    vectors = np.array([[text.split().count(word) for word in vocabulary] for text in texts], dtype=float)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.where(norms == 0, 1, norms)


def test_best_match_comes_first():
    index = SemanticIndex(DOCS, fake_encode, "fake")
    results = index.search("database pool exhausted", top_k=2)
    assert results[0][0]["doc_id"] == "A"
    assert results[0][1] >= results[1][1]


def test_top_k_and_filter():
    index = SemanticIndex(DOCS, fake_encode, "fake")
    results = index.search("database pool", top_k=3, where=lambda doc: doc["kind"] == "adr")
    assert [doc["doc_id"] for doc, _ in results] == ["C#x", "C#y"]


def test_index_remembers_its_model():
    assert SemanticIndex(DOCS, fake_encode, "fake").model_key == "fake"


def test_query_prefix_is_added_to_queries_only():
    seen = []
    def recording_encode(texts):
        seen.extend(texts)
        return fake_encode(texts)
    index = SemanticIndex(DOCS, recording_encode, "fake", query_prefix="Q: ")
    index.search("pool")
    assert "Q: pool" in seen and not any(text.startswith("Q: ") for text in seen[:len(DOCS)])


def test_top_evidence_merges_adr_sections():
    results = [(DOCS[2], 0.9), (DOCS[3], 0.8), (DOCS[0], 0.7)]
    assert top_evidence(results) == [("C", 0.9), ("A", 0.7)]
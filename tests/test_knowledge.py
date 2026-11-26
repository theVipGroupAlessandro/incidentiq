"""Step 4 tested on the real corpus with a tiny fake embedding model and a fake graph,
so it runs without models, Neo4j or PostgreSQL."""
import hashlib
import os

import numpy as np
import pytest

from app.corpus import load_corpus
from app.knowledge import MemoryKnowledge, PostgresKnowledge, query_text, retrieve_knowledge


def fake_encode(texts):
    """Bag of words hashed into 384 dimensions (the size the database expects), normalized: similar wording -> similar vectors."""
    vectors = np.zeros((len(texts), 384))
    for row, text in enumerate(texts):
        for word in text.lower().replace(":", " ").replace(".", " ").split():
            vectors[row, int(hashlib.md5(word.encode()).hexdigest(), 16) % 384] += 1
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.where(norms == 0, 1, norms)


class FakeGraph:
    """Same answers as the real topology for the services used below; accepted ADRs from the corpus."""
    DOWNSTREAM = {"gateway": {"inventory": 1, "order": 1, "notification": 2, "payment": 2},
                  "order": {"inventory": 1, "notification": 1, "payment": 1},
                  "payment": {"notification": 1, "order": 2, "inventory": 3}}

    def downstream(self, service):
        return self.DOWNSTREAM.get(service, {})

    def accepted_adrs(self, services=None):
        adrs = {d["evidence_id"]: d for d in load_corpus() if d["kind"] == "adr" and d["status"] == "accepted"}
        return sorted(e for e, d in adrs.items() if services is None or set(d["services"]) & set(services))


CAUSE = {"service": "payment", "text": "payment: Database connection pool exhausted (50/50 connections in use)"}


@pytest.fixture(scope="module")
def search():
    return MemoryKnowledge(load_corpus(), model_key="fake", encode=fake_encode)


def test_query_text_modes():
    assert query_text("Checkout fails", CAUSE, "question") == "Checkout fails"
    assert query_text("Checkout fails", CAUSE, "message") == CAUSE["text"]
    assert query_text("Checkout fails", CAUSE, "both") == "Checkout fails " + CAUSE["text"]
    assert query_text("Checkout fails", None, "message") == "Checkout fails"  # no cause: fall back to the question


def test_incidents_come_only_from_the_cause_service(search):
    result = retrieve_knowledge(search, FakeGraph(), "Checkout fails", service="gateway", cause=CAUSE, threshold=0.0)
    assert result.incident_services == ["payment"]
    assert all(doc["root_service"] == "payment" for doc, _ in result.incidents)
    assert result.incidents[0][0]["evidence_id"] in {"INC-001", "INC-013"}  # the two pool exhaustions on payment


def test_adrs_are_accepted_and_superseded_ones_never_appear(search):
    result = retrieve_knowledge(search, FakeGraph(), "How much memory should order get?", service="order",
                                threshold=0.0)
    ids = [doc["evidence_id"] for doc, _ in result.adrs]
    assert len(ids) == 2 and "ADR-003" not in ids


def test_without_a_cause_incidents_come_from_the_selected_service_and_its_callees(search):
    result = retrieve_knowledge(search, FakeGraph(), "Order reports timeouts calling payment", service="order",
                                threshold=0.0)
    assert result.incident_services == ["inventory", "notification", "order", "payment"]


def test_search_widens_and_flags_insufficient_evidence_when_nothing_is_similar(search):
    result = retrieve_knowledge(search, FakeGraph(), "Checkout fails", service="gateway", cause=CAUSE,
                                threshold=2.0)  # unreachable threshold
    assert result.widened and not result.sufficient
    assert set(result.incident_services) == {"gateway", "inventory", "order", "notification", "payment"}


@pytest.mark.skipif(not os.environ.get("INCIDENTIQ_DB_TESTS"), reason="needs PostgreSQL (set INCIDENTIQ_DB_TESTS=1)")
def test_postgres_backend_matches_the_memory_backend():
    from app.db import postgres_connection
    from app.index_embeddings import index_model
    with postgres_connection() as connection:
        index_model(connection, "test-fake", fake_encode)
        try:
            database = PostgresKnowledge(connection, model_key="test-fake", encode=fake_encode)
            memory = MemoryKnowledge(load_corpus(), model_key="test-fake", encode=fake_encode)
            for kind, kwargs in (("incident", {"root_services": ["payment"]}), ("adr", {"evidence_ids": ["ADR-001"]})):
                from_db = [doc["doc_id"] for doc, _ in database.search(CAUSE["text"], kind, 5, **kwargs)]
                from_memory = [doc["doc_id"] for doc, _ in memory.search(CAUSE["text"], kind, 5, **kwargs)]
                assert from_db == from_memory
        finally:
            connection.execute("DELETE FROM knowledge_embeddings WHERE model = 'test-fake'")
            connection.execute("DELETE FROM event_embeddings WHERE model = 'test-fake'")
            connection.commit()
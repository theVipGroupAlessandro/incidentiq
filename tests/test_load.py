import inspect

from app import load_postgres
from app.index_embeddings import to_pgvector


def test_vectors_use_the_pgvector_text_format():
    assert to_pgvector([0.5, -0.25, 1.0]) == "[0.5,-0.25,1]"


def test_evaluation_labels_are_never_loaded():
    # incident_id in the logs is ground truth for the evaluation, not data for the system.
    assert "incident_id" not in inspect.getsource(load_postgres.load_events)


def test_log_groups_are_keyed_on_their_first_log():
    class FakeCursor:
        def executemany(self, sql, rows):
            self.rows = rows
    cursor = FakeCursor()
    group = {"doc_id": "LOG-0001", "services": ["payment"], "fingerprint": "abc", "count": 3,
             "first_seen": "2026-11-09T10:30:00Z", "last_seen": "2026-11-09T10:40:00Z"}
    load_postgres.load_log_groups(cursor, [group], {"payment": "svc-id"}, {"LOG-0001": "event-id"})
    assert cursor.rows == [("event-id", "svc-id", "abc", 3, "2026-11-09T10:30:00Z", "2026-11-09T10:40:00Z")]
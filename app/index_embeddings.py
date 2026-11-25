"""Compute embeddings with each model and store them in PostgreSQL (repeatable indexing script).

Run from the project root (SSH tunnel open, data loaded):  python -m app.index_embeddings
Optional: --model bge-small  (default: every model in app.embeddings.MODELS)
Running it again replaces the vectors of that model: safe after changing data or model version.
"""
import argparse

from app.db import postgres_connection
from app.embeddings import MODELS, load_encoder


def to_pgvector(vector):
    """pgvector text format, e.g. '[0.1,0.2]': works with any driver, no extra package needed."""
    return "[" + ",".join(f"{value:.7g}" for value in vector) + "]"


def index_model(connection, model_key, encode):
    documents = connection.execute("SELECT doc_id, body FROM knowledge_documents ORDER BY doc_id").fetchall()
    groups = connection.execute(
        "SELECT e.id, s.name || ': ' || e.body FROM log_groups g "
        "JOIN telemetry_events e ON e.id = g.representative_event_id "
        "JOIN services s ON s.id = e.service_id ORDER BY e.log_id").fetchall()

    document_vectors = encode([body for _, body in documents]) if documents else []
    group_vectors = encode([text for _, text in groups]) if groups else []

    with connection.transaction(), connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO knowledge_embeddings (doc_id, model, embedding) VALUES (%s, %s, %s::vector) "
            "ON CONFLICT (doc_id, model) DO UPDATE SET embedding = EXCLUDED.embedding",
            [(doc_id, model_key, to_pgvector(vector)) for (doc_id, _), vector in zip(documents, document_vectors)])
        cursor.executemany(
            "INSERT INTO event_embeddings (event_id, model, embedding) VALUES (%s, %s, %s::vector) "
            "ON CONFLICT (event_id, model) DO UPDATE SET embedding = EXCLUDED.embedding",
            [(event_id, model_key, to_pgvector(vector)) for (event_id, _), vector in zip(groups, group_vectors)])
    return len(documents), len(groups)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=MODELS, help="index only this model")
    args = parser.parse_args()
    with postgres_connection() as connection:
        for model_key in [args.model] if args.model else list(MODELS):
            n_documents, n_groups = index_model(connection, model_key, load_encoder(model_key))
            print(f"{model_key:<10} {n_documents} knowledge documents, {n_groups} log groups indexed")


if __name__ == "__main__":
    main()
"""Load the synthetic data into PostgreSQL (run the migrations first).

Run from the project root (SSH tunnel open):  python -m app.load_postgres
Safe to run again: rows are matched on their stable ids (log_id, incident id, ADR id, doc_id),
so a replay updates them instead of creating duplicates.

Evaluation labels (incident_id in the logs, queries, scenarios) are NOT loaded: the system
must never see the answers it is evaluated on.
"""
import json

from app.corpus import FIXTURES, load_corpus, read_adrs
from app.db import postgres_connection
from app.logs import fingerprint, load_logs, log_documents, redact
from data.topology import SERVICES


def load_services(cursor, services=SERVICES):
    cursor.executemany("INSERT INTO services (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                       [(name,) for name in services])
    cursor.execute("SELECT name, id FROM services")
    return dict(cursor.fetchall())


def load_events(cursor, logs, service_ids):
    cursor.executemany(
        "INSERT INTO telemetry_events (log_id, ts, service_id, trace_id, span_id, severity, body, fingerprint) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (log_id) DO NOTHING",
        [(log["log_id"], log["timestamp"], service_ids[log["service"]], log["trace_id"], log["span_id"],
          log["severity"], redact(log["message"]), fingerprint(log["message"])) for log in logs])
    cursor.execute("SELECT log_id, id FROM telemetry_events")
    return dict(cursor.fetchall())


def load_log_groups(cursor, groups, service_ids, event_ids):
    cursor.executemany(
        "INSERT INTO log_groups (representative_event_id, service_id, fingerprint, event_count, first_seen, last_seen) "
        "VALUES (%s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (representative_event_id) DO UPDATE SET "
        "event_count = EXCLUDED.event_count, first_seen = EXCLUDED.first_seen, last_seen = EXCLUDED.last_seen",
        [(event_ids[group["doc_id"]], service_ids[group["services"][0]], group["fingerprint"],
          group["count"], group["first_seen"], group["last_seen"]) for group in groups])


def load_incidents(cursor, incidents, service_ids):
    cursor.executemany(
        "INSERT INTO incidents (id, title, incident_date, status, root_service_id, failure_type, "
        "affected_services, symptoms, cause, mitigation) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, status = EXCLUDED.status, "
        "symptoms = EXCLUDED.symptoms, cause = EXCLUDED.cause, mitigation = EXCLUDED.mitigation, "
        "affected_services = EXCLUDED.affected_services",
        [(i["id"], i["title"], i["date"], i["status"], service_ids[i["service"]], i["failure_type"],
          i["affected_services"], i["symptoms"], i["cause"], i["mitigation"]) for i in incidents])


def load_adrs(cursor, adrs):
    # Two passes: an ADR may supersede one that is inserted later in the list.
    cursor.executemany(
        "INSERT INTO adrs (id, title, status, adr_date, services) VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, status = EXCLUDED.status, "
        "adr_date = EXCLUDED.adr_date, services = EXCLUDED.services",
        [(m["id"], m["title"], m["status"], m["date"], m["services"]) for m, _ in adrs])
    cursor.executemany("UPDATE adrs SET supersedes = %s WHERE id = %s",
                       [(m["supersedes"], m["id"]) for m, _ in adrs])


def load_knowledge_documents(cursor, documents):
    cursor.executemany(
        "INSERT INTO knowledge_documents (doc_id, evidence_id, kind, services, root_service, status, body) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (doc_id) DO UPDATE SET services = EXCLUDED.services, status = EXCLUDED.status, "
        "body = EXCLUDED.body",
        [(d["doc_id"], d["evidence_id"], d["kind"], d["services"], d["root_service"], d["status"], d["text"])
         for d in documents])


def load_all(connection):
    logs = load_logs()
    incidents = json.loads((FIXTURES / "incidents.json").read_text(encoding="utf-8"))
    with connection.transaction(), connection.cursor() as cursor:
        service_ids = load_services(cursor)
        event_ids = load_events(cursor, logs, service_ids)
        load_log_groups(cursor, log_documents(logs), service_ids, event_ids)
        load_incidents(cursor, incidents, service_ids)
        load_adrs(cursor, read_adrs())
        load_knowledge_documents(cursor, load_corpus())


def counts(connection):
    tables = ["services", "telemetry_events", "log_groups", "incidents", "adrs", "knowledge_documents"]
    return {table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in tables}


def main():
    with postgres_connection() as connection:
        load_all(connection)
        for table, n in counts(connection).items():
            print(f"{table:<20} {n}")


if __name__ == "__main__":
    main()
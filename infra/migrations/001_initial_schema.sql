-- 001: initial schema for IncidentIQ.
-- Raw events and their embeddings live in separate tables (re-embedding with another model never
-- touches raw data). The service name is the key shared with Neo4j.

CREATE EXTENSION IF NOT EXISTS vector;

-- Services: one row per service; `name` matches the Neo4j Service node.
CREATE TABLE services (
    id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text UNIQUE NOT NULL
);

-- Telemetry: one row per raw log event.
CREATE TABLE telemetry_events (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    log_id      text UNIQUE NOT NULL,          -- stable evidence id, e.g. LOG-0577
    ts          timestamptz NOT NULL,
    service_id  uuid NOT NULL REFERENCES services(id),
    trace_id    text,
    span_id     text,
    severity    text NOT NULL,
    body        text NOT NULL,                 -- message, already redacted
    fingerprint text NOT NULL,                 -- hash of the normalized message, for deduplication
    attributes  jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX telemetry_events_service_ts_idx ON telemetry_events (service_id, ts DESC);
CREATE INDEX telemetry_events_fingerprint_idx ON telemetry_events (fingerprint);

-- Deduplicated log groups: same service + fingerprint + burst of activity.
-- Only groups are embedded; the representative event is the first one of the group.
CREATE TABLE log_groups (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    representative_event_id uuid UNIQUE NOT NULL REFERENCES telemetry_events(id) ON DELETE CASCADE,
    service_id              uuid NOT NULL REFERENCES services(id),
    fingerprint             text NOT NULL,
    event_count             integer NOT NULL CHECK (event_count > 0),
    first_seen              timestamptz NOT NULL,
    last_seen               timestamptz NOT NULL,
    CHECK (last_seen >= first_seen)
);
CREATE INDEX log_groups_service_time_idx ON log_groups (service_id, first_seen, last_seen);

CREATE TABLE event_embeddings (
    event_id  uuid NOT NULL REFERENCES telemetry_events(id) ON DELETE CASCADE,
    model     text NOT NULL,                   -- e.g. 'bge-small', 'minilm'
    embedding vector(384) NOT NULL,
    PRIMARY KEY (event_id, model)
);

-- Knowledge: incidents and ADRs, plus the searchable documents built from them
-- (one per incident, one per ADR section), mirroring app/corpus.py.
CREATE TABLE incidents (
    id                text PRIMARY KEY,        -- INC-001
    title             text NOT NULL,
    incident_date     date NOT NULL,
    status            text NOT NULL,
    root_service_id   uuid NOT NULL REFERENCES services(id),
    failure_type      text NOT NULL,
    affected_services text[] NOT NULL,
    symptoms          text NOT NULL,
    cause             text NOT NULL,
    mitigation        text NOT NULL
);

CREATE TABLE adrs (
    id         text PRIMARY KEY,               -- ADR-001
    title      text NOT NULL,
    status     text NOT NULL CHECK (status IN ('proposed', 'accepted', 'superseded', 'deprecated')),
    adr_date   date NOT NULL,
    services   text[] NOT NULL,
    supersedes text REFERENCES adrs(id)
);

CREATE TABLE knowledge_documents (
    doc_id       text PRIMARY KEY,             -- INC-001 or ADR-001#decision
    evidence_id  text NOT NULL,                -- what answers cite and the benchmark counts
    kind         text NOT NULL CHECK (kind IN ('incident', 'adr')),
    services     text[] NOT NULL,
    root_service text,                         -- incidents only
    status       text NOT NULL,
    body         text NOT NULL
);
CREATE INDEX knowledge_documents_evidence_idx ON knowledge_documents (evidence_id);

CREATE TABLE knowledge_embeddings (
    doc_id    text NOT NULL REFERENCES knowledge_documents(doc_id) ON DELETE CASCADE,
    model     text NOT NULL,
    embedding vector(384) NOT NULL,
    PRIMARY KEY (doc_id, model)
);

-- No HNSW index yet: on a few hundred rows exact search is fast and always returns k rows.
-- An approximate index can be added in a later migration if the data grows.
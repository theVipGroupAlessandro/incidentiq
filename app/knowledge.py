"""Step 4 of the investigation: retrieve past incidents and accepted ADRs for the current problem.

The graph decides WHERE to look, semantic search decides WHAT is similar:
  - incidents: only those that STARTED on the candidate service(s) (root_service), because a
    service that was merely affected saw timeouts, not the failure itself;
  - ADRs: only accepted ones that the graph links (AFFECTS) to the candidate service(s);
  - ranking: semantic similarity with the chosen embedding model (MiniLM by default),
    best 3 incidents + best 2 ADRs, so incidents cannot crowd out the rules;
  - a relevance threshold: if no incident reaches it, the evidence is flagged as insufficient.

Two interchangeable search backends: PostgresKnowledge (pgvector, the real system) and
MemoryKnowledge (in-memory index, for the benchmark and the tests).
"""
from dataclasses import dataclass, field

from app.embeddings import MODELS, SemanticIndex, load_encoder
from app.index_embeddings import to_pgvector

DEFAULT_MODEL = "minilm"
# Provisional thresholds from the vector-only benchmark (lowest best-score of an answerable query
# vs highest best-score of a no-evidence query). Scales differ per model: never share a threshold.
THRESHOLDS = {"minilm": 0.46, "bge-small": 0.65}


@dataclass
class KnowledgeResult:
    query_text: str
    incident_services: list
    incidents: list = field(default_factory=list)   # [(doc, score)], best first
    adrs: list = field(default_factory=list)        # [(doc, score)], best first
    widened: bool = False                            # True if the search had to look beyond the cause's service
    sufficient: bool = False                         # at least one incident above the threshold


def query_text(question, cause, mode):
    """Text that is searched: the engineer's question, the candidate cause's log message, or both."""
    message = cause["text"] if cause else None
    if mode == "question" or not message:
        return question
    if mode == "message":
        return message
    return f"{question} {message}"


class MemoryKnowledge:
    """Search the in-memory corpus (app.corpus) with an embedding model."""

    def __init__(self, documents, model_key=DEFAULT_MODEL, encode=None):
        prefix = MODELS[model_key]["query_prefix"] if model_key in MODELS else ""
        self.index = SemanticIndex(documents, encode or load_encoder(model_key), model_key, prefix)

    def search(self, text, kind, top_k, root_services=None, evidence_ids=None):
        def allowed(doc):
            return (doc["kind"] == kind
                    and (root_services is None or doc["root_service"] in root_services)
                    and (evidence_ids is None or doc["evidence_id"] in evidence_ids))
        return self.index.search(text, top_k=top_k, where=allowed)


class PostgresKnowledge:
    """Search knowledge_documents / knowledge_embeddings in PostgreSQL with pgvector (exact search)."""

    def __init__(self, connection, model_key=DEFAULT_MODEL, encode=None):
        self.connection = connection
        self.model_key = model_key
        self.encode = encode or load_encoder(model_key)
        self.prefix = MODELS[model_key]["query_prefix"] if model_key in MODELS else ""

    def search(self, text, kind, top_k, root_services=None, evidence_ids=None):
        vector = to_pgvector(self.encode([self.prefix + text])[0])
        rows = self.connection.execute(
            "SELECT d.doc_id, d.evidence_id, d.kind, d.services, d.root_service, d.status, d.body, "
            "       1 - (e.embedding <=> %(vector)s::vector) AS score "
            "FROM knowledge_documents d JOIN knowledge_embeddings e ON e.doc_id = d.doc_id "
            "WHERE e.model = %(model)s AND d.kind = %(kind)s "
            "  AND (%(roots)s::text[] IS NULL OR d.root_service = ANY(%(roots)s::text[])) "
            "  AND (%(ids)s::text[] IS NULL OR d.evidence_id = ANY(%(ids)s::text[])) "
            "ORDER BY e.embedding <=> %(vector)s::vector LIMIT %(k)s",
            {"vector": vector, "model": self.model_key, "kind": kind, "k": top_k,
             "roots": list(root_services) if root_services is not None else None,
             "ids": list(evidence_ids) if evidence_ids is not None else None}).fetchall()
        keys = ("doc_id", "evidence_id", "kind", "services", "root_service", "status", "text")
        return [(dict(zip(keys, row[:7])), float(row[7])) for row in rows]


def best_per_evidence(results, k):
    """Keep the best-scoring document of each evidence id (an ADR has several sections), best first."""
    best = {}
    for doc, score in results:
        best.setdefault(doc["evidence_id"], (doc, score))
    return list(best.values())[:k]


def retrieve_knowledge(search, graph, question, service=None, cause=None, query_mode="both",
                       threshold=THRESHOLDS[DEFAULT_MODEL], k_incidents=3, k_adrs=2):
    """Incidents and accepted ADRs for one investigation.

    search: MemoryKnowledge or PostgresKnowledge.
    graph:  object with downstream(service) -> {service: hops} and accepted_adrs(services) -> [ADR ids]
            (app.graph_neo4j.Neo4jGraph in the real system).
    service: the service the engineer selected (None = no graph filter for incidents).
    cause:   the candidate root cause from step 3 (a timeline entry), or None.
    """
    text = query_text(question, cause, query_mode)

    # Where incidents may have started: the cause's service if we have one; otherwise the selected
    # service and everything it calls (where a cause can be); otherwise anywhere.
    graph_services = {service, *graph.downstream(service)} if service else None
    incident_services = {cause["service"]} if cause else graph_services
    widened = False

    def find_incidents(services):
        return best_per_evidence(search.search(text, "incident", 20, root_services=services), k_incidents)

    incidents = find_incidents(incident_services)
    if cause and graph_services and not any(score >= threshold for _, score in incidents):
        # Nothing similar on the cause's service: look at the other candidate services before giving up.
        incident_services, widened = graph_services | {cause["service"]}, True
        incidents = find_incidents(incident_services)

    # Accepted ADRs linked by the graph to the services involved (all accepted ADRs if no service is known).
    adr_services = (graph_services or set()) | ({cause["service"]} if cause else set())
    adr_ids = graph.accepted_adrs(sorted(adr_services) if adr_services else None)
    adrs = best_per_evidence(search.search(text, "adr", 20, evidence_ids=adr_ids), k_adrs)

    return KnowledgeResult(
        query_text=text,
        incident_services=sorted(incident_services) if incident_services else [],
        incidents=incidents,
        adrs=adrs,
        widened=widened,
        sufficient=any(score >= threshold for _, score in incidents),
    )
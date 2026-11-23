from app.corpus import load_corpus, parse_frontmatter, split_sections


def test_corpus_has_20_incidents_and_3_sections_per_adr():
    corpus = load_corpus()
    assert sum(1 for doc in corpus if doc["kind"] == "incident") == 20
    assert sum(1 for doc in corpus if doc["kind"] == "adr") == 5 * 3


def test_doc_ids_are_unique():
    ids = [doc["doc_id"] for doc in load_corpus()]
    assert len(ids) == len(set(ids))


def test_adr_sections_keep_metadata():
    sections = [doc for doc in load_corpus() if doc["evidence_id"] == "ADR-005"]
    assert {doc["doc_id"] for doc in sections} == {
        "ADR-005#context", "ADR-005#decision", "ADR-005#consequences"}
    assert all(doc["status"] == "accepted" and "payment" in doc["services"] for doc in sections)


def test_superseded_adr_is_marked():
    statuses = {doc["status"] for doc in load_corpus() if doc["evidence_id"] == "ADR-003"}
    assert statuses == {"superseded"}


def test_frontmatter_parser():
    metadata, body = parse_frontmatter("---\nid: ADR-9\nservices: [a, b]\nsupersedes: null\n---\n## X\ntext\n")
    assert metadata == {"id": "ADR-9", "services": ["a", "b"], "supersedes": None}
    assert split_sections(body) == {"X": "text"}
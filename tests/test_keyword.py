from app.keyword import BM25Index, tokenize

DOCS = [
    {"doc_id": "A", "evidence_id": "A", "kind": "incident", "text": "Database connection pool exhausted on payment"},
    {"doc_id": "B", "evidence_id": "B", "kind": "incident", "text": "Card declined by the bank"},
    {"doc_id": "C", "evidence_id": "C", "kind": "adr", "text": "Connection pool limits for every service"},
]


def test_tokenize_lowercases_and_drops_stopwords():
    assert tokenize("The Pool is EXHAUSTED (50/50)") == ["pool", "exhausted", "50", "50"]


def test_document_with_query_words_ranks_first():
    results = BM25Index(DOCS).search("pool exhausted", top_k=3)
    assert results[0][0]["doc_id"] == "A"


def test_no_shared_words_means_zero_score():
    results = BM25Index(DOCS).search("kafka consumer lag", top_k=3)
    assert all(score == 0 for _, score in results)


def test_rare_words_count_more_than_common_ones():
    # "pool" appears in two documents, "bank" in one: a match on "bank" weighs more.
    index = BM25Index(DOCS)
    assert index.idf["bank"] > index.idf["pool"]


def test_filter_works_like_semantic_search():
    results = BM25Index(DOCS).search("pool", top_k=3, where=lambda doc: doc["kind"] == "adr")
    assert [doc["doc_id"] for doc, _ in results] == ["C"]
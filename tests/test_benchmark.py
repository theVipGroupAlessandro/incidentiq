from evaluation import benchmark


def test_recall_counts_found_relevant_evidence():
    assert benchmark.recall_at_k(["INC-001", "INC-005", "ADR-001"], ["INC-001", "INC-013", "ADR-001"]) == 2 / 3
    assert benchmark.recall_at_k(["INC-001"], []) is None  # no-evidence query: reported separately


def test_bootstrap_interval_contains_the_mean_and_is_reproducible():
    a, b = [1, 1, 0.5, 1, 0], [0.5, 1, 0.5, 0, 0]
    mean, low, high = benchmark.bootstrap_mean_diff_ci(a, b)
    assert low <= mean <= high
    assert benchmark.bootstrap_mean_diff_ci(a, b) == (mean, low, high)


def test_identical_methods_have_a_zero_difference():
    mean, low, high = benchmark.bootstrap_mean_diff_ci([1, 0.5, 0], [1, 0.5, 0])
    assert (mean, low, high) == (0.0, 0.0, 0.0)


def test_benchmark_runs_end_to_end_with_bm25_only():
    rows = benchmark.run(["bm25"])
    assert len(rows) == 30 * len(benchmark.MODES)
    summary = benchmark.summarize(rows)
    assert 0 <= summary[("bm25", "global")]["recall_at_5"] <= 1


def test_by_type_mode_returns_three_incidents_and_two_adrs():
    rows = benchmark.run(["bm25"])
    found = [row["found"].split() for row in rows if row["mode"] == "by_type"][0]
    assert [e.startswith("INC") for e in found] == [True, True, True, False, False]
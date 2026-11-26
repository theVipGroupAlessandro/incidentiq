"""Retrieval benchmark on the 30 labeled development queries (evaluation/queries.json).

Run from the project root:  python -m evaluation.benchmark
Options: --methods bm25 minilm   (default: all)
Outputs: evaluation/results/benchmark_per_query.csv and evaluation/results/benchmark_report.md

For every method and retrieval mode, each query is searched once (after one warm-up query, so the
first-call overhead is not counted) and scored with Recall@5 over distinct evidence ids.
Model loading time is not part of the latency. The held-out scenarios are never used here.
"""
import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np

from app.corpus import load_corpus
from app.embeddings import build_index, top_evidence
from app.keyword import BM25Index

QUERIES_FILE = Path(__file__).parent / "queries.json"
RESULTS_DIR = Path(__file__).parent / "results"
K = 5
SEED = 0

# name -> function that builds the index from the documents
METHODS = {
    "bm25": lambda documents: BM25Index(documents),
    "bge-small": lambda documents: build_index(documents, "bge-small", use_query_prefix=True),
    "bge-small-noprefix": lambda documents: build_index(documents, "bge-small", use_query_prefix=False),
    "minilm": lambda documents: build_index(documents, "minilm"),
}

# How the top-5 evidence list is built:
#   global  = best 5 distinct evidence ids overall
#   by_type = best 3 incidents + best 2 ADRs (tests whether incidents crowd out the rules)
MODES = ("global", "by_type")


def retrieve(index, query, mode):
    if mode == "global":
        return top_evidence(index.search(query, top_k=20), K)
    incidents = top_evidence(index.search(query, top_k=10, where=lambda d: d["kind"] == "incident"), 3)
    adrs = top_evidence(index.search(query, top_k=10, where=lambda d: d["kind"] == "adr"), 2)
    return incidents + adrs


def recall_at_k(found_ids, relevant_ids):
    """Share of the relevant evidence found in the top results; None when nothing is relevant."""
    if not relevant_ids:
        return None
    return len(set(found_ids) & set(relevant_ids)) / len(relevant_ids)


def evaluate(index, queries, method, mode):
    """One row per query: what was found, Recall@5, the best score and the latency in ms."""
    retrieve(index, queries[0]["question"], mode)  # warm-up, not measured
    rows = []
    for query in queries:
        start = time.perf_counter()
        results = retrieve(index, query["question"], mode)
        latency_ms = (time.perf_counter() - start) * 1000
        found = [evidence_id for evidence_id, _ in results]
        rows.append({
            "method": method, "mode": mode, "query_id": query["id"], "type": query["type"],
            "relevant": " ".join(query["relevant"]), "found": " ".join(found),
            "recall_at_5": recall_at_k(found, query["relevant"]),
            "top_score": round(max((score for _, score in results), default=0.0), 4),
            "latency_ms": round(latency_ms, 3),
        })
    return rows


def bootstrap_mean_diff_ci(a, b, n_resamples=10_000, seed=SEED, level=0.95):
    """Paired bootstrap: resample queries with replacement, return the CI of mean(a - b)."""
    differences = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(differences, size=(n_resamples, len(differences)), replace=True).mean(axis=1)
    tail = (1 - level) / 2 * 100
    return float(differences.mean()), float(np.percentile(samples, tail)), float(np.percentile(samples, 100 - tail))


def summarize(rows):
    """Mean Recall@5 (overall and by query type) and latency percentiles for each method/mode."""
    summary = {}
    for key in sorted({(row["method"], row["mode"]) for row in rows}):
        group = [row for row in rows if (row["method"], row["mode"]) == key]
        answerable = [row for row in group if row["recall_at_5"] is not None]
        latencies = [row["latency_ms"] for row in group]
        by_type = {}
        for query_type in sorted({row["type"] for row in answerable}):
            values = [row["recall_at_5"] for row in answerable if row["type"] == query_type]
            by_type[query_type] = sum(values) / len(values)
        summary[key] = {
            "recall_at_5": sum(row["recall_at_5"] for row in answerable) / len(answerable),
            "by_type": by_type,
            "p50_ms": float(np.percentile(latencies, 50)),
            "p95_ms": float(np.percentile(latencies, 95)),
            "answerable_top_score_min": min(row["top_score"] for row in answerable),
            "none_top_score_max": max((row["top_score"] for row in group if row["recall_at_5"] is None),
                                      default=None),
        }
    return summary


def paired_recalls(rows, key_a, key_b):
    """Recall@5 of two method/mode pairs on the same answerable queries, in the same order."""
    def by_query(key):
        return {row["query_id"]: row["recall_at_5"] for row in rows
                if (row["method"], row["mode"]) == key and row["recall_at_5"] is not None}
    a, b = by_query(key_a), by_query(key_b)
    shared = sorted(set(a) & set(b))
    return [a[q] for q in shared], [b[q] for q in shared]


def write_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(rows, summary, path):
    types = sorted({row["type"] for row in rows if row["recall_at_5"] is not None})
    lines = ["# Retrieval benchmark", "",
             f"{len({row['query_id'] for row in rows})} labeled development queries, Recall@{K} over distinct evidence ids.",
             "Latency: one search including query encoding, after a warm-up query; model loading excluded.", "",
             "| Method | Mode | Recall@5 | " + " | ".join(types) + " | p50 ms | p95 ms |",
             "|---|---|---|" + "---|" * len(types) + "---|---|"]
    for (method, mode), s in summary.items():
        lines.append(f"| {method} | {mode} | {s['recall_at_5']:.3f} | "
                     + " | ".join(f"{s['by_type'].get(t, float('nan')):.3f}" for t in types)
                     + f" | {s['p50_ms']:.2f} | {s['p95_ms']:.2f} |")

    best = max(summary, key=lambda key: summary[key]["recall_at_5"])
    lines += ["", f"## Paired comparison against the best ({best[0]}, {best[1]})", "",
              "Mean difference in Recall@5 (best minus other) with a 95% paired bootstrap interval "
              "(10,000 resamples of the queries). An interval that contains 0 means the difference is not conclusive "
              "on this sample.", "", "| Other | Difference | 95% CI |", "|---|---|---|"]
    for key in summary:
        if key != best:
            mean, low, high = bootstrap_mean_diff_ci(*paired_recalls(rows, best, key))
            lines.append(f"| {key[0]} ({key[1]}) | {mean:+.3f} | [{low:+.3f}, {high:+.3f}] |")

    lines += ["", "## Scores for choosing a relevance threshold", "",
              "Lowest best-score among answerable queries vs highest best-score among no-evidence queries. "
              "Scores are on different scales per method and must not be compared across methods.", "",
              "| Method | Mode | Min top score (answerable) | Max top score (no evidence) |", "|---|---|---|---|"]
    for (method, mode), s in summary.items():
        lines.append(f"| {method} | {mode} | {s['answerable_top_score_min']:.3f} | {s['none_top_score_max']:.3f} |")

    lines += ["", "## Misses (relevant evidence not in the top 5)", ""]
    for row in rows:
        if row["recall_at_5"] is not None and row["recall_at_5"] < 1 and (row["method"], row["mode"]) == best:
            missing = set(row["relevant"].split()) - set(row["found"].split())
            lines.append(f"- {row['query_id']} ({row['type']}): missing {', '.join(sorted(missing))}; found {row['found']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(methods, queries=None, documents=None, factories=METHODS):
    queries = queries or json.loads(QUERIES_FILE.read_text(encoding="utf-8"))
    documents = documents or load_corpus()
    rows = []
    for method in methods:
        index = factories[method](documents)  # model loading happens here, outside the timing
        for mode in MODES:
            rows += evaluate(index, queries, method, mode)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--methods", nargs="*", choices=METHODS, default=list(METHODS))
    args = parser.parse_args()
    rows = run(args.methods)
    summary = summarize(rows)
    write_csv(rows, RESULTS_DIR / "benchmark_per_query.csv")
    write_report(rows, summary, RESULTS_DIR / "benchmark_report.md")
    for (method, mode), s in summary.items():
        print(f"{method:<20} {mode:<8} Recall@5 {s['recall_at_5']:.3f}   p50 {s['p50_ms']:.2f} ms   p95 {s['p95_ms']:.2f} ms")
    print(f"\nDetails: {RESULTS_DIR / 'benchmark_report.md'}")


if __name__ == "__main__":
    main()
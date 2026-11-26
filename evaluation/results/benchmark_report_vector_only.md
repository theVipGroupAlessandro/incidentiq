Baseline without the graph (26/11/2026). Default embedding model chosen: **MiniLM**, by_type mode
(Recall@5 equivalent to BGE-small, CI touches 0; ~2.3x faster; better score separation for the threshold).
To be re-checked with the graph-aware retriever.

# Retrieval benchmark

30 labeled development queries, Recall@5 over distinct evidence ids.
Latency: one search including query encoding, after a warm-up query; model loading excluded.

| Method | Mode | Recall@5 | failure | rule | symptom | trigger | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|
| bge-small | by_type | 0.968 | 1.000 | 1.000 | 0.700 | 1.000 | 27.18 | 30.20 |
| bge-small | global | 0.798 | 0.750 | 1.000 | 0.617 | 0.929 | 13.70 | 18.44 |
| bge-small-noprefix | by_type | 0.950 | 0.969 | 1.000 | 0.700 | 1.000 | 21.10 | 25.88 |
| bge-small-noprefix | global | 0.763 | 0.688 | 1.000 | 0.617 | 0.929 | 10.58 | 14.46 |
| bm25 | by_type | 0.929 | 0.917 | 1.000 | 0.783 | 1.000 | 0.07 | 0.08 |
| bm25 | global | 0.910 | 0.854 | 1.000 | 0.933 | 1.000 | 0.04 | 0.05 |
| minilm | by_type | 0.950 | 0.969 | 1.000 | 0.700 | 1.000 | 11.77 | 14.98 |
| minilm | global | 0.838 | 0.760 | 1.000 | 0.767 | 1.000 | 5.90 | 6.80 |

## Paired comparison against the best (bge-small, by_type)

Mean difference in Recall@5 (best minus other) with a 95% paired bootstrap interval (10,000 resamples of the queries). An interval that contains 0 means the difference is not conclusive on this sample.

| Other | Difference | 95% CI |
|---|---|---|
| bge-small (global) | +0.170 | [+0.083, +0.259] |
| bge-small-noprefix (by_type) | +0.018 | [+0.000, +0.054] |
| bge-small-noprefix (global) | +0.205 | [+0.116, +0.298] |
| bm25 (by_type) | +0.039 | [-0.009, +0.101] |
| bm25 (global) | +0.058 | [-0.013, +0.131] |
| minilm (by_type) | +0.018 | [+0.000, +0.054] |
| minilm (global) | +0.130 | [+0.038, +0.225] |

## Scores for choosing a relevance threshold

Lowest best-score among answerable queries vs highest best-score among no-evidence queries. Scores are on different scales per method and must not be compared across methods.

| Method | Mode | Min top score (answerable) | Max top score (no evidence) |
|---|---|---|---|
| bge-small | by_type | 0.654 | 0.643 |
| bge-small | global | 0.654 | 0.643 |
| bge-small-noprefix | by_type | 0.644 | 0.644 |
| bge-small-noprefix | global | 0.644 | 0.644 |
| bm25 | by_type | 2.850 | 5.397 |
| bm25 | global | 2.850 | 5.397 |
| minilm | by_type | 0.470 | 0.444 |
| minilm | global | 0.470 | 0.444 |

## Misses (relevant evidence not in the top 5)

- Q17 (symptom): missing INC-004, INC-013; found INC-014 INC-002 INC-001 ADR-002 ADR-005
- Q18 (symptom): missing INC-010, INC-016; found INC-015 INC-019 INC-009 ADR-005 ADR-002

# Synthetic dataset

All data is synthetic and generated with a fixed seed (`SEED = 42` in `data/generate.py`).
Regenerate with: `python -m data.generate`

## Contents
| File | Content |
|---|---|
| `data/topology.py` | 5 services, 8 directed CALLS edges, one cycle (order -> notification -> order) |
| `data/fixtures/logs.jsonl` | 707 logs: 458 from historical incidents, 129 from held-out scenarios, 120 noise |
| `data/fixtures/incidents.json` | 20 resolved incidents with symptoms, cause, mitigation, affected services |
| `data/fixtures/adrs/` | 5 Markdown ADRs with frontmatter (id, status, services, supersedes) |

## Failure types
Database connection pool exhaustion, external API timeout, memory exhaustion, authentication failure.
Cascading failures are modelled with `spread` (how many hops upstream the failure propagates, 0-2).
Each historical failure type has 5 incidents with different causes.

## Held-out scenarios
SCN-01 to SCN-05 are kept for the final evaluation. Their logs carry no `incident_id`.
SCN-05 is an unknown-cause case: its failure type has no historical incident.

## Design decisions (not specified in the brief)
- Dependency edges and the cycle are chosen to exercise hop limits and cycle handling.
- Logs, incidents and ADRs are kept consistent: pool size 50 and 5 s wait (ADR-001),
  3 s external timeout and circuit breaker after 5 failures (ADR-002).
- ADR-003 is superseded by ADR-005 on purpose, to test that only accepted ADRs are used.
- Noise logs are isolated business errors; some resemble real failures (e.g. slow query) as distractors.

## Labelling criteria (evaluation/queries.json)
- failure queries: incidents with the same root service and the same failure type.
  Being only affected by a failure elsewhere does not count: affected services see symptoms
  (timeouts, 5xx), not the failure itself.
- symptom queries: incidents rooted in the called service that affected the reporting service.
  No ADR when the candidate incidents have different failure types.
- trigger queries: the incident with that specific cause.
- ADRs: the accepted ADR governing that failure type for that service. ADR-003 (superseded) never counts.
- none queries: nothing in the data is relevant; reported separately from Recall@5.
- Labels were cross-checked against an independent LLM review (22/30 identical at first pass);
  disagreements were resolved with the criteria above.
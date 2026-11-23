"""Failure episodes used to generate the logs.

HISTORICAL: past failures, already investigated (each becomes an incident record).
SCENARIOS: new failures to investigate. Held out for the final evaluation: their logs carry no incident ID.
`spread` = how many hops upstream the failure propagates (0 = only the root service).
"""

HISTORICAL = [
    {"id": "INC-001", "service": "payment", "failure": "db_pool_exhaustion", "start": "2026-05-04T10:12", "spread": 2},
    {"id": "INC-002", "service": "payment", "failure": "api_timeout", "start": "2026-05-13T15:40", "spread": 1},
    {"id": "INC-003", "service": "order", "failure": "memory_exhaustion", "start": "2026-05-22T08:05", "spread": 1},
    {"id": "INC-004", "service": "payment", "failure": "auth_failure", "start": "2026-05-30T21:18", "spread": 1},
    {"id": "INC-005", "service": "order", "failure": "db_pool_exhaustion", "start": "2026-06-08T12:30", "spread": 1},
    {"id": "INC-006", "service": "notification", "failure": "api_timeout", "start": "2026-06-17T09:47", "spread": 0},
    {"id": "INC-007", "service": "notification", "failure": "memory_exhaustion", "start": "2026-06-26T03:22", "spread": 0},
    {"id": "INC-008", "service": "gateway", "failure": "auth_failure", "start": "2026-07-05T18:02", "spread": 0},
    {"id": "INC-009", "service": "inventory", "failure": "db_pool_exhaustion", "start": "2026-07-14T11:15", "spread": 1},
    {"id": "INC-010", "service": "inventory", "failure": "api_timeout", "start": "2026-07-23T14:55", "spread": 2},
    {"id": "INC-011", "service": "gateway", "failure": "memory_exhaustion", "start": "2026-08-01T20:40", "spread": 0},
    {"id": "INC-012", "service": "notification", "failure": "auth_failure", "start": "2026-08-10T07:33", "spread": 0},
    {"id": "INC-013", "service": "payment", "failure": "db_pool_exhaustion", "start": "2026-08-19T13:08", "spread": 1},
    {"id": "INC-014", "service": "payment", "failure": "api_timeout", "start": "2026-08-28T16:25", "spread": 2},
    {"id": "INC-015", "service": "inventory", "failure": "memory_exhaustion", "start": "2026-09-06T02:50", "spread": 1},
    {"id": "INC-016", "service": "inventory", "failure": "auth_failure", "start": "2026-09-15T10:10", "spread": 1},
    {"id": "INC-017", "service": "order", "failure": "db_pool_exhaustion", "start": "2026-09-24T17:45", "spread": 2},
    {"id": "INC-018", "service": "notification", "failure": "api_timeout", "start": "2026-10-03T08:20", "spread": 1},
    {"id": "INC-019", "service": "order", "failure": "memory_exhaustion", "start": "2026-10-12T22:05", "spread": 2},
    {"id": "INC-020", "service": "order", "failure": "auth_failure", "start": "2026-10-21T12:00", "spread": 1},
]

SCENARIOS = [
    {"id": "SCN-01", "service": "payment", "failure": "db_pool_exhaustion", "start": "2026-11-09T10:30", "spread": 2},
    {"id": "SCN-02", "service": "inventory", "failure": "api_timeout", "start": "2026-11-10T14:10", "spread": 1},
    {"id": "SCN-03", "service": "order", "failure": "memory_exhaustion", "start": "2026-11-11T09:00", "spread": 1},
    {"id": "SCN-04", "service": "gateway", "failure": "auth_failure", "start": "2026-11-12T16:45", "spread": 0},
    {"id": "SCN-05", "service": "inventory", "failure": "unknown", "start": "2026-11-13T11:20", "spread": 1},
]
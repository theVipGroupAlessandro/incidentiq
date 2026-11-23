"""Synthetic log generator for IncidentIQ.

Run from the project root:  python -m data.generate
Output: data/fixtures/logs.jsonl (one JSON object per line) and data/fixtures/incidents.json.
"""
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.graph_local import upstream_callers
from data.catalog import DISTRACTORS, EXTERNAL, GATEWAY_SYMPTOM, ROOT_MESSAGES, SYMPTOM_MESSAGES
from data.episodes import HISTORICAL, SCENARIOS
from data.incidents import build_incidents
from data.topology import CALLS, SERVICES

SEED = 42
NOISE_LOGS = 120
NOISE_START = datetime(2026, 5, 1, tzinfo=timezone.utc)
NOISE_END = datetime(2026, 11, 15, tzinfo=timezone.utc)
OUTPUT_DIR = Path(__file__).parent / "fixtures"


def pick(rng, templates):
    """Choose a (severity, template) pair, respecting the weights."""
    weights = [weight for _, _, weight in templates]
    severity, template, _ = rng.choices(templates, weights=weights)[0]
    return severity, template


def fill(rng, template, service, callee=None):
    """Replace the {placeholders} with random but plausible values."""
    values = {
        "used": 50, "max": 50,        # pool size from ADR-001
        "db_wait_ms": 5000,           # max wait for a connection, ADR-001
        "api_timeout_ms": 3000,       # external API timeout, ADR-002
        "ms": rng.choice([3000, 5000, 10000, 30000]),
        "attempt": rng.randint(1, 3),
        "pct": rng.randint(85, 99),
        "failures": 5,                # circuit breaker threshold, ADR-002
        "external": EXTERNAL[service],
        "callee": callee,
        "file": f"stock_{rng.randint(1000, 9999)}.csv",
        "n": rng.randint(10, 500),
        "ip": f"10.0.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
        "code": f"SAVE{rng.randint(10, 99)}",
        "order": f"ORD-{rng.randint(10000, 99999)}",
        "sku": f"SKU-{rng.randint(1000, 9999)}",
        "email": f"user{rng.randint(1, 999)}@example.com",
    }
    return template.format(**values)

def make_log(rng, ts, service, severity, message, trace_id, incident_id):
    return {
        "timestamp": ts.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "service": service,
        "severity": severity,
        "message": message,
        "trace_id": trace_id,
        "span_id": f"{rng.getrandbits(64):016x}",
        "incident_id": incident_id,
    }


def episode_logs(rng, episode, incident_id):
    """Logs for one failure: the root cause first, then symptoms in the callers upstream."""
    start = datetime.fromisoformat(episode["start"]).replace(tzinfo=timezone.utc)
    duration = timedelta(minutes=rng.randint(10, 40))
    root = episode["service"]
    traces = [f"{rng.getrandbits(128):032x}" for _ in range(6)]  # requests shared by the episode's logs
    logs = []

    # Root cause: many repeated messages from the failing service. The first one opens the episode.
    for i in range(rng.randint(8, 20)):
        ts = start if i == 0 else start + duration * rng.random()
        severity, template = pick(rng, ROOT_MESSAGES[episode["failure"]])
        logs.append(make_log(rng, ts, root, severity, fill(rng, template, root),
                             rng.choice(traces), incident_id))

    # Symptoms: each affected caller complains about the service it calls, slightly later.
    affected = upstream_callers(root, SERVICES, CALLS, max_hops=episode["spread"])
    distance = {root: 0, **affected}
    for service, hops in affected.items():
        # The callee is the next service on the path back to the root.
        callee = next(b for a, b in CALLS if a == service and distance.get(b) == hops - 1)
        templates = [GATEWAY_SYMPTOM] if service == "gateway" else SYMPTOM_MESSAGES
        for _ in range(rng.randint(3, 8)):
            ts = start + timedelta(seconds=5 * hops) + duration * rng.random()
            severity, template = pick(rng, templates)
            logs.append(make_log(rng, ts, service, severity, fill(rng, template, service, callee),
                                 rng.choice(traces), incident_id))
    return logs


def noise_logs(rng):
    """Background errors spread over the whole period, not linked to any incident."""
    logs = []
    span = NOISE_END - NOISE_START
    for _ in range(NOISE_LOGS):
        service = rng.choice(SERVICES)
        ts = NOISE_START + span * rng.random()
        severity, template = pick(rng, DISTRACTORS[service])
        logs.append(make_log(rng, ts, service, severity, fill(rng, template, service),
                             f"{rng.getrandbits(128):032x}", None))
    return logs


def generate_logs(seed=SEED):
    rng = random.Random(seed)
    logs = []
    for episode in HISTORICAL:
        logs += episode_logs(rng, episode, incident_id=episode["id"])
    for episode in SCENARIOS:
        logs += episode_logs(rng, episode, incident_id=None)  # unknown at investigation time
    logs += noise_logs(rng)

    logs.sort(key=lambda log: log["timestamp"])
    for number, log in enumerate(logs, start=1):
        log["log_id"] = f"LOG-{number:04d}"
    return logs


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    logs = generate_logs()
    with open(OUTPUT_DIR / "logs.jsonl", "w", encoding="utf-8") as file:
        for log in logs:
            file.write(json.dumps(log) + "\n")
    print(f"Wrote {len(logs)} logs to {OUTPUT_DIR / 'logs.jsonl'}")

    incidents = build_incidents()
    with open(OUTPUT_DIR / "incidents.json", "w", encoding="utf-8") as file:
        json.dump(incidents, file, indent=2)
    print(f"Wrote {len(incidents)} incidents to {OUTPUT_DIR / 'incidents.json'}")

if __name__ == "__main__":
    main()
"""Log normalization, deduplication and log documents for semantic search.

Pipeline: keep ERROR and CRITICAL only -> redact sensitive-looking values -> compute a fingerprint
(the message without numbers and IDs) -> group logs with the same service and fingerprint that are
close in time -> one searchable document per group.
"""
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

LOGS_FILE = Path(__file__).parent.parent / "data" / "fixtures" / "logs.jsonl"
KEPT_SEVERITIES = {"ERROR", "CRITICAL"}
GROUP_GAP = timedelta(minutes=30)  # same message more than 30 minutes later = a new group

REDACTIONS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<email>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "<ip>"),
]
VARIABLE_PARTS = [
    (re.compile(r"\b[0-9a-f]{12,}\b"), "<id>"),   # hex ids
    (re.compile(r"\b[A-Z]+-\d+\b"), "<id>"),      # ORD-12345, SKU-1234
    (re.compile(r"\S+\.csv\b"), "<file>"),
    (re.compile(r"\d+"), "<n>"),                  # any remaining number
]


def load_logs(path=LOGS_FILE):
    with open(path, encoding="utf-8") as file:
        return [json.loads(line) for line in file]


def redact(message):
    """Hide values that look personal (emails, IP addresses)."""
    for pattern, replacement in REDACTIONS:
        message = pattern.sub(replacement, message)
    return message


def fingerprint(message):
    """Same fingerprint for messages that differ only in numbers, IDs or file names."""
    normalized = redact(message)
    for pattern, replacement in VARIABLE_PARTS:
        normalized = pattern.sub(replacement, normalized)
    return hashlib.sha1(normalized.lower().encode("utf-8")).hexdigest()[:12]


def _time(log):
    return datetime.fromisoformat(log["timestamp"].replace("Z", "+00:00"))


def group_logs(logs):
    """Deduplicate: one group per (service, fingerprint, burst of activity)."""
    kept = [log for log in logs if log["severity"] in KEPT_SEVERITIES]
    kept.sort(key=lambda log: (log["service"], fingerprint(log["message"]), log["timestamp"]))

    groups = []
    for log in kept:
        key = (log["service"], fingerprint(log["message"]))
        last = groups[-1] if groups else None
        if last and last["key"] == key and _time(log) - _time(last["logs"][-1]) <= GROUP_GAP:
            last["logs"].append(log)
        else:
            groups.append({"key": key, "logs": [log]})
    return groups


def log_documents(logs=None):
    """One searchable document per log group, in the same shape as the corpus documents."""
    documents = []
    for group in group_logs(load_logs() if logs is None else logs):
        first, members = group["logs"][0], group["logs"]
        documents.append({
            "doc_id": first["log_id"],
            "evidence_id": first["log_id"],
            "kind": "log",
            "services": [first["service"]],
            "root_service": None,
            "status": None,
            "severity": "CRITICAL" if any(m["severity"] == "CRITICAL" for m in members) else "ERROR",
            "text": f"{first['service']}: {redact(first['message'])}",
            "fingerprint": group["key"][1],
            "count": len(members),
            "first_seen": first["timestamp"],
            "last_seen": members[-1]["timestamp"],
            "log_ids": [m["log_id"] for m in members],
            "trace_ids": sorted({m["trace_id"] for m in members}),
        })
    documents.sort(key=lambda doc: doc["first_seen"])
    return documents


def in_window(start, end):
    """Filter for SemanticIndex.search: groups active between start and end (ISO strings)."""
    return lambda doc: doc["first_seen"] <= end and doc["last_seen"] >= start
"""Step 3 of the investigation: the log timeline and the candidate root cause.

Input: log groups (same shape as app.logs.log_documents) for the candidate services.
Output: the groups active in the time window, oldest first, each labelled as
  - "waiting": the service reports a problem with ANOTHER internal service it calls (a symptom), or
  - "own":     the service reports a problem of its own (a possible cause),
plus the candidate root cause: the earliest REPEATED "own" error (an isolated error, seen once,
is more likely background noise), ties broken by the larger count.

This is a rule, not a proof: the language model receives the whole timeline and decides.
"""
import re

# Words that, next to the name of another service, mean "I am waiting for / failing because of it".
WAITING_PATTERNS = [
    r"timeout calling {service}\b",
    r"\bfrom {service}\b",
    r"upstream {service}\b",
    r"circuit breaker opened for {service}\b",
    r"calling {service}\b",
]


def waiting_on(message, service, services):
    """The internal service this message is waiting on, or None if the error is the service's own."""
    text = message.lower()
    for other in services:
        if other == service:
            continue
        if any(re.search(pattern.format(service=re.escape(other)), text) for pattern in WAITING_PATTERNS):
            return other
    return None


def build_timeline(groups, services, start, end, all_services):
    """Groups of the given services active between start and end (ISO strings), oldest first, labelled."""
    selected = [g for g in groups
                if g["services"][0] in services and g["first_seen"] <= end and g["last_seen"] >= start]
    timeline = []
    for group in sorted(selected, key=lambda g: (g["first_seen"], -g["count"])):
        service = group["services"][0]
        waited = waiting_on(group["text"], service, all_services)
        timeline.append({**group, "service": service,
                         "kind": "waiting" if waited else "own", "waiting_on": waited})
    return timeline


def candidate_cause(timeline):
    """Earliest repeated 'own' error; isolated ones (count 1) only if nothing repeats. None if no 'own' error."""
    own = [entry for entry in timeline if entry["kind"] == "own"]
    if not own:
        return None
    return min(own, key=lambda entry: (entry["count"] < 2, entry["first_seen"], -entry["count"]))


def consistent_symptoms(timeline, cause, upstream_of_cause):
    """'waiting' entries that point at the cause's service or at a service upstream of it:
    the symptoms that the candidate cause would explain. `upstream_of_cause` comes from the graph."""
    if cause is None:
        return []
    chain = {cause["service"], *upstream_of_cause}
    return [entry for entry in timeline if entry["kind"] == "waiting" and entry["waiting_on"] in chain]
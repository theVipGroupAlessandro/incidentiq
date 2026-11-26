from app.timeline import build_timeline, candidate_cause, consistent_symptoms, waiting_on

SERVICES = ["gateway", "order", "payment", "inventory", "notification"]


def group(doc_id, service, message, first, last, count):
    return {"doc_id": doc_id, "services": [service], "text": f"{service}: {message}",
            "first_seen": first, "last_seen": last, "count": count}


CASCADE = [
    group("LOG-1", "payment", "Database connection pool exhausted (50/50 connections in use)",
          "2026-11-09T10:30:00Z", "2026-11-09T11:04:00Z", 11),
    group("LOG-2", "order", "Timeout calling payment after 5000 ms", "2026-11-09T10:39:00Z", "2026-11-09T10:48:00Z", 2),
    group("LOG-3", "gateway", "504 Gateway Timeout: upstream order did not respond",
          "2026-11-09T10:33:00Z", "2026-11-09T11:00:00Z", 7),
    group("LOG-4", "payment", "Card declined by issuer: insufficient funds (order ORD-1)",
          "2026-11-09T10:20:00Z", "2026-11-09T10:20:00Z", 1),
    group("LOG-5", "payment", "Database connection pool exhausted (50/50 connections in use)",
          "2026-05-04T10:12:00Z", "2026-05-04T10:40:00Z", 9),
]
WINDOW = ("2026-11-09T10:00:00Z", "2026-11-09T11:30:00Z")


def test_messages_about_another_service_are_symptoms():
    assert waiting_on("order: Timeout calling payment after 5000 ms", "order", SERVICES) == "payment"
    assert waiting_on("gateway: 504 Gateway Timeout: upstream order did not respond", "gateway", SERVICES) == "order"
    assert waiting_on("order: 502 Bad Gateway from payment", "order", SERVICES) == "payment"
    assert waiting_on("payment: Request to payment-provider.example.com timed out after 3000 ms",
                      "payment", SERVICES) is None


def test_timeline_keeps_the_window_and_is_ordered_by_time():
    timeline = build_timeline(CASCADE, SERVICES, *WINDOW, SERVICES)
    assert [entry["doc_id"] for entry in timeline] == ["LOG-4", "LOG-1", "LOG-3", "LOG-2"]  # LOG-5 is in May
    assert [entry["kind"] for entry in timeline] == ["own", "own", "waiting", "waiting"]


def test_candidate_is_the_earliest_repeated_own_error_not_isolated_noise():
    timeline = build_timeline(CASCADE, SERVICES, *WINDOW, SERVICES)
    assert candidate_cause(timeline)["doc_id"] == "LOG-1"  # LOG-4 is earlier but seen only once


def test_no_own_error_means_no_candidate():
    only_symptoms = [entry for entry in CASCADE if entry["doc_id"] in ("LOG-2", "LOG-3")]
    assert candidate_cause(build_timeline(only_symptoms, SERVICES, *WINDOW, SERVICES)) is None


def test_symptoms_consistent_with_the_cause_follow_the_call_chain():
    timeline = build_timeline(CASCADE, SERVICES, *WINDOW, SERVICES)
    cause = candidate_cause(timeline)
    explained = consistent_symptoms(timeline, cause, upstream_of_cause={"order": 1, "gateway": 2})
    assert {entry["doc_id"] for entry in explained} == {"LOG-2", "LOG-3"}
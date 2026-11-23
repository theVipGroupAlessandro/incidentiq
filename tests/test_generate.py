from data.catalog import ROOT_MESSAGES
from data.episodes import HISTORICAL, SCENARIOS
from data.generate import generate_logs
from data.topology import SERVICES


def test_same_seed_same_logs():
    assert generate_logs(seed=1) == generate_logs(seed=1)


def test_at_least_500_logs():
    assert len(generate_logs()) >= 500


def test_fields_are_valid():
    for log in generate_logs():
        assert log["service"] in SERVICES
        assert log["severity"] in {"WARN", "ERROR", "CRITICAL"}
        assert len(log["trace_id"]) == 32 and len(log["span_id"]) == 16


def test_log_ids_are_unique():
    ids = [log["log_id"] for log in generate_logs()]
    assert len(ids) == len(set(ids))


def test_every_historical_incident_has_logs():
    incident_ids = {log["incident_id"] for log in generate_logs()}
    assert {episode["id"] for episode in HISTORICAL} <= incident_ids


def test_scenario_logs_have_no_incident_id():
    scenario_ids = {episode["id"] for episode in SCENARIOS}
    assert not scenario_ids & {log["incident_id"] for log in generate_logs()}


def test_all_failure_types_are_covered():
    failures = {episode["failure"] for episode in HISTORICAL + SCENARIOS}
    assert failures == set(ROOT_MESSAGES)


def test_unknown_failure_has_no_historical_incident():
    assert "unknown" not in {episode["failure"] for episode in HISTORICAL}


def test_root_cause_is_logged_first():
    logs = generate_logs()
    for episode in HISTORICAL:
        episode_logs = [log for log in logs if log["incident_id"] == episode["id"]]
        first = min(episode_logs, key=lambda log: log["timestamp"])
        assert first["service"] == episode["service"]


def test_timeouts_match_the_adrs():
    for log in generate_logs():
        if "waiting for a database connection" in log["message"]:
            assert "after 5000 ms" in log["message"]  # ADR-001
        if log["message"].startswith("Request to") and "timed out" in log["message"]:
            assert "after 3000 ms" in log["message"]  # ADR-002


def test_circuit_breaker_matches_adr_002():
    for log in generate_logs():
        if "Circuit breaker opened" in log["message"]:
            assert "after 5 consecutive failures" in log["message"]
            def test_timeouts_match_the_adrs():
                for log in generate_logs():
                    if "waiting for a database connection" in log["message"]:
                        assert "after 5000 ms" in log["message"]  # ADR-001
                    if log["message"].startswith("Request to") and "timed out" in log["message"]:
                        assert "after 3000 ms" in log["message"]  # ADR-002


def test_circuit_breaker_matches_adr_002():
    for log in generate_logs():
        if "Circuit breaker opened" in log["message"]:
            assert "after 5 consecutive failures" in log["message"]
import json
from pathlib import Path

from app.graph_local import upstream_callers
from data.episodes import SCENARIOS
from data.incidents import build_incidents
from data.topology import CALLS, SERVICES
from data.generate import generate_logs

ROOT = Path(__file__).parent.parent
QUERIES = json.loads((ROOT / "evaluation" / "queries.json").read_text(encoding="utf-8"))
SCENARIO_LABELS = json.loads((ROOT / "evaluation" / "scenarios.json").read_text(encoding="utf-8"))
INCIDENT_IDS = {incident["id"] for incident in build_incidents()}
ADR_IDS = {path.name[:7] for path in (ROOT / "data" / "fixtures" / "adrs").glob("ADR-*.md")}
ACCEPTED_ADRS = ADR_IDS - {"ADR-003"}  # ADR-003 is superseded


def test_thirty_queries_with_unique_ids():
    ids = [query["id"] for query in QUERIES]
    assert len(ids) == 30 and len(set(ids)) == 30


def test_relevant_evidence_exists():
    for query in QUERIES:
        for evidence_id in query["relevant"]:
            assert evidence_id in INCIDENT_IDS | ACCEPTED_ADRS, (query["id"], evidence_id)


def test_some_queries_have_no_relevant_evidence():
    assert sum(1 for query in QUERIES if not query["relevant"]) >= 2


def test_query_services_are_known():
    for query in QUERIES:
        assert query["service"] is None or query["service"] in SERVICES


def test_scenario_labels_match_the_generated_episodes():
    episodes = {episode["id"]: episode for episode in SCENARIOS}
    assert [label["id"] for label in SCENARIO_LABELS] == list(episodes)
    for label in SCENARIO_LABELS:
        episode, expected = episodes[label["id"]], label["expected"]
        assert expected["root_service"] == episode["service"]
        assert expected["failure_type"] == episode["failure"]
        assert label["window"]["start"].startswith(episode["start"])
        callers = upstream_callers(episode["service"], SERVICES, CALLS, max_hops=episode["spread"])
        assert set(expected["affected_services"]) == {episode["service"], *callers}


def test_scenario_evidence_exists():
    for label in SCENARIO_LABELS:
        for evidence_id in label["expected"]["similar_incidents"] + label["expected"]["adrs"]:
            assert evidence_id in INCIDENT_IDS | ACCEPTED_ADRS


def test_questions_do_not_leak_the_answer():
    # The held-out questions must not name the failure type.
    words = ("pool", "connection", "timeout", "memory", "oom", "auth", "401", "certificate")
    for label in SCENARIO_LABELS:
        assert not any(word in label["question"].lower() for word in words), label["id"]

def test_root_log_message_appears_in_the_scenario_logs():
    
    logs = generate_logs()
    for label in SCENARIO_LABELS:
        start, end = label["window"]["start"], label["window"]["end"]
        root = label["expected"]["root_service"]
        messages = [log["message"] for log in logs
                    if log["service"] == root and start <= log["timestamp"] <= end]
        assert any(label["expected"]["root_log_message"] in message for message in messages), label["id"]
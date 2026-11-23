from pathlib import Path

from data.episodes import HISTORICAL
from data.incidents import build_incidents
from data.topology import SERVICES

ADR_DIR = Path(__file__).parent.parent / "data" / "fixtures" / "adrs"


def test_one_incident_per_historical_episode():
    assert [i["id"] for i in build_incidents()] == [e["id"] for e in HISTORICAL]


def test_affected_services_start_with_root_service():
    for incident in build_incidents():
        assert incident["affected_services"][0] == incident["service"]
        assert set(incident["affected_services"]) <= set(SERVICES)


def test_incidents_of_the_same_type_are_different():
    causes = [i["cause"] for i in build_incidents()]
    assert len(causes) == len(set(causes))


def test_required_fields_are_filled():
    for incident in build_incidents():
        for field in ("title", "date", "symptoms", "cause", "mitigation"):
            assert incident[field]


def test_five_adrs_with_id_status_and_services():
    files = sorted(ADR_DIR.glob("ADR-*.md"))
    assert len(files) == 5
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---")
        for field in ("id:", "status:", "services:"):
            assert field in text
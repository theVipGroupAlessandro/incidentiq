"""Neo4j code tested with a fake driver: it records the queries and returns prepared records.
The real database is checked by running `python -m app.graph_neo4j` (it compares Neo4j with Python)."""
import pytest

from app import graph_neo4j
from data.topology import CALLS, SERVICES


class FakeDriver:
    def __init__(self, records=None):
        self.calls = []
        self.records = records or []

    def execute_query(self, query, parameters_=None):
        self.calls.append((query, parameters_ or {}))
        if "count(s) AS n" in query:
            return [{"n": 1}], None, None
        return self.records, None, None


def test_seed_parameters_come_from_the_data_files():
    parameters = graph_neo4j.seed_parameters()
    assert parameters["services"] == SERVICES
    assert len(parameters["calls"]) == len(CALLS) == 8
    adrs = {adr["id"]: adr for adr in parameters["adrs"]}
    assert adrs["ADR-005"]["supersedes"] == "ADR-003"
    assert adrs["ADR-003"]["status"] == "superseded"


def test_seed_runs_constraints_then_every_seed_query_with_its_parameters():
    driver = FakeDriver()
    graph_neo4j.seed(driver)
    queries = [query for query, _ in driver.calls]
    assert queries[:2] == graph_neo4j.CONSTRAINTS
    assert len(queries) == len(graph_neo4j.CONSTRAINTS) + len(graph_neo4j.SEED_QUERIES)
    merge_calls = next(params for query, params in driver.calls if "MERGE (caller)-[:CALLS]" in query)
    assert merge_calls["calls"][0] == {"caller": "gateway", "callee": "order"}


def test_upstream_query_uses_the_hop_limit_and_returns_distances():
    driver = FakeDriver(records=[{"service": "order", "hops": 1}, {"service": "gateway", "hops": 2}])
    assert graph_neo4j.upstream_callers_neo4j(driver, "payment", max_hops=2) == {"order": 1, "gateway": 2}
    assert "[:CALLS*1..2]" in driver.calls[-1][0]


def test_hop_limit_must_be_a_small_integer():
    with pytest.raises(ValueError):
        graph_neo4j.upstream_callers_neo4j(FakeDriver(), "payment", max_hops="3; DROP")


def test_unknown_service_is_rejected():
    class EmptyDriver(FakeDriver):
        def execute_query(self, query, parameters_=None):
            return [{"n": 0}], None, None
    with pytest.raises(ValueError):
        graph_neo4j.downstream_callees_neo4j(EmptyDriver(), "shipping")
"""Service graph in Neo4j: seed it from the data files, and query callers and callees.

Run from the project root (SSH tunnel open):  python -m app.graph_neo4j
It seeds the graph, then prints the graph query output for every service and checks it
against the plain-Python version (app/graph_local.py). Exit code 1 if they disagree.

Graph model (from the decisionX Phase 1 Research Report):
    (:Service)-[:CALLS]->(:Service)
    (:ADR)-[:AFFECTS]->(:Service)
    (:ADR)-[:SUPERSEDES]->(:ADR)
"""
import sys

from app.corpus import read_adrs
from app.db import neo4j_driver
from app.graph_local import downstream_callees, upstream_callers
from data.topology import CALLS, SERVICES

CONSTRAINTS = [
    "CREATE CONSTRAINT service_name IF NOT EXISTS FOR (s:Service) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT adr_id IF NOT EXISTS FOR (a:ADR) REQUIRE a.id IS UNIQUE",
]

# The seed mirrors the data files exactly: nodes that are no longer in the files are removed,
# relationships are rebuilt, everything else is MERGEd (so running it twice changes nothing).
SEED_QUERIES = [
    ("MATCH (s:Service) WHERE NOT s.name IN $services DETACH DELETE s", "services"),
    ("MATCH (a:ADR) WHERE NOT a.id IN $adr_ids DETACH DELETE a", "adr_ids"),
    ("MATCH (:Service)-[r:CALLS]->(:Service) DELETE r", None),
    ("MATCH (:ADR)-[r:AFFECTS|SUPERSEDES]->() DELETE r", None),
    ("UNWIND $services AS name MERGE (:Service {name: name})", "services"),
    ("UNWIND $calls AS call "
     "MATCH (caller:Service {name: call.caller}) MATCH (callee:Service {name: call.callee}) "
     "MERGE (caller)-[:CALLS]->(callee)", "calls"),
    ("UNWIND $adrs AS adr "
     "MERGE (a:ADR {id: adr.id}) "
     "SET a.title = adr.title, a.status = adr.status, a.date = date(adr.date) "
     "WITH a, adr UNWIND adr.services AS service_name "
     "MATCH (s:Service {name: service_name}) MERGE (a)-[:AFFECTS]->(s)", "adrs"),
    ("UNWIND $adrs AS adr WITH adr WHERE adr.supersedes IS NOT NULL "
     "MATCH (new:ADR {id: adr.id}) MATCH (old:ADR {id: adr.supersedes}) "
     "MERGE (new)-[:SUPERSEDES]->(old)", "adrs"),
]


def seed_parameters(services=SERVICES, calls=CALLS, adrs=None):
    adr_metadata = [metadata for metadata, _ in (read_adrs() if adrs is None else adrs)]
    return {
        "services": list(services),
        "calls": [{"caller": caller, "callee": callee} for caller, callee in calls],
        "adrs": [{key: metadata[key] for key in ("id", "title", "status", "date", "services", "supersedes")}
                 for metadata in adr_metadata],
        "adr_ids": [metadata["id"] for metadata in adr_metadata],
    }


def seed(driver, parameters=None):
    parameters = parameters or seed_parameters()
    for query in CONSTRAINTS:
        driver.execute_query(query)
    for query, needs in SEED_QUERIES:
        driver.execute_query(query, parameters_={needs: parameters[needs]} if needs else {})


def _hops(max_hops):
    # Neo4j does not accept a parameter as path length, so the number goes into the text:
    # check it is a small positive integer first.
    if not isinstance(max_hops, int) or not 1 <= max_hops <= 10:
        raise ValueError(f"max_hops must be an integer between 1 and 10, got {max_hops!r}")
    return max_hops


def _service_exists(driver, service):
    records, _, _ = driver.execute_query(
        "MATCH (s:Service {name: $name}) RETURN count(s) AS n", parameters_={"name": service})
    if records[0]["n"] == 0:
        raise ValueError(f"Unknown service: {service!r}")


def upstream_callers_neo4j(driver, service, max_hops=3):
    """Who calls `service` within max_hops (who may be affected): {service: shortest distance}."""
    _service_exists(driver, service)
    records, _, _ = driver.execute_query(
        f"MATCH (target:Service {{name: $name}}) "
        f"MATCH path = (caller:Service)-[:CALLS*1..{_hops(max_hops)}]->(target) "
        f"WHERE caller <> target "
        f"RETURN caller.name AS service, min(length(path)) AS hops ORDER BY hops, service",
        parameters_={"name": service})
    return {record["service"]: record["hops"] for record in records}


def downstream_callees_neo4j(driver, service, max_hops=3):
    """What `service` calls within max_hops (where a cause may be): {service: shortest distance}."""
    _service_exists(driver, service)
    records, _, _ = driver.execute_query(
        f"MATCH (source:Service {{name: $name}}) "
        f"MATCH path = (source)-[:CALLS*1..{_hops(max_hops)}]->(callee:Service) "
        f"WHERE callee <> source "
        f"RETURN callee.name AS service, min(length(path)) AS hops ORDER BY hops, service",
        parameters_={"name": service})
    return {record["service"]: record["hops"] for record in records}


def accepted_adrs_neo4j(driver, service):
    """Accepted ADRs that govern `service` (superseded ones are left out)."""
    records, _, _ = driver.execute_query(
        "MATCH (a:ADR {status: 'accepted'})-[:AFFECTS]->(:Service {name: $name}) "
        "RETURN a.id AS id ORDER BY id",
        parameters_={"name": service})
    return [record["id"] for record in records]

def accepted_adrs_for_services_neo4j(driver, services=None):
    """Accepted ADRs linked (AFFECTS) to any of `services`; every accepted ADR when services is None."""
    records, _, _ = driver.execute_query(
        "MATCH (a:ADR {status: 'accepted'}) "
        "WHERE $services IS NULL OR EXISTS { MATCH (a)-[:AFFECTS]->(s:Service) WHERE s.name IN $services } "
        "RETURN a.id AS id ORDER BY id",
        parameters_={"services": services})
    return [record["id"] for record in records]


class Neo4jGraph:
    """The graph as the investigation uses it: who a service calls, and which accepted ADRs apply."""

    def __init__(self, driver, max_hops=3):
        self.driver, self.max_hops = driver, max_hops

    def upstream(self, service):
        return upstream_callers_neo4j(self.driver, service, self.max_hops)

    def downstream(self, service):
        return downstream_callees_neo4j(self.driver, service, self.max_hops)

    def accepted_adrs(self, services=None):
        return accepted_adrs_for_services_neo4j(self.driver, services)
    
def main():
    with neo4j_driver() as driver:
        seed(driver)
        print("Graph seeded: 5 services, 8 CALLS, ADRs with AFFECTS/SUPERSEDES.\n")
        mismatches = 0
        for service in SERVICES:
            up = upstream_callers_neo4j(driver, service)
            down = downstream_callees_neo4j(driver, service)
            ok = (up == upstream_callers(service, SERVICES, CALLS)
                  and down == downstream_callees(service, SERVICES, CALLS))
            mismatches += not ok
            print(f"[{'MATCH' if ok else 'DIFF '}] {service:<13} upstream {up}  downstream {down}  "
                  f"ADRs {accepted_adrs_neo4j(driver, service)}")
    print("\nNeo4j and Python agree." if not mismatches else f"\n{mismatches} service(s) disagree!")
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
"""Upstream caller lookup on the service graph, in plain Python (no Neo4j).

Used until Neo4j is available, and afterwards as the expected answer to verify the Cypher queries.
"""
from collections import deque


def upstream_callers(service, services, calls, max_hops=3):
    """Return the services that call `service`, directly or indirectly.

    Result: dict {service: distance}, sorted by distance, then by name.
    Distance 1 = direct caller, 2 = caller of a caller, and so on up to `max_hops`.
    The start service is never included, even if a cycle leads back to it.
    """
    if service not in services:
        raise ValueError(f"Unknown service: {service!r}")

    # For each service, the list of its callers (edges read in reverse).
    callers_of = {}
    for caller, callee in calls:
        callers_of.setdefault(callee, []).append(caller)

    # Breadth-first search: all services at distance 1 first, then distance 2, ...
    # Each service gets its SHORTEST distance; visited services are skipped (cycle handling).
    distances = {service: 0}
    queue = deque([service])
    while queue:
        current = queue.popleft()
        if distances[current] == max_hops:
            continue  # hop limit reached: do not expand further
        for caller in callers_of.get(current, []):
            if caller not in distances:
                distances[caller] = distances[current] + 1
                queue.append(caller)

    del distances[service]
    return dict(sorted(distances.items(), key=lambda item: (item[1], item[0])))
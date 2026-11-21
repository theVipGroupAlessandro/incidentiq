"""Ricerca dei chiamanti a monte sul grafo, in puro Python (senza Neo4j).

Serve finché Neo4j non è disponibile, e dopo come "risposta attesa" per verificare le query Cypher.
"""
from collections import deque


def upstream_callers(service, services, calls, max_hops=3):
    """Restituisce i servizi che chiamano `service`, direttamente o indirettamente.

    Risultato: dizionario {servizio: distanza}, ordinato per distanza e poi per nome.
    Distanza 1 = chiamante diretto, 2 = chiamante del chiamante, e così via fino a `max_hops`.
    Il servizio di partenza non compare mai, anche se un ciclo ci riporta a lui.
    """
    if service not in services:
        raise ValueError(f"Servizio sconosciuto: {service!r}")

    # Per ogni servizio, l'elenco di chi lo chiama (le frecce lette al contrario).
    callers_of = {}
    for caller, callee in calls:
        callers_of.setdefault(callee, []).append(caller)

    # Visita in ampiezza (BFS): prima tutti i servizi a distanza 1, poi a distanza 2, ...
    # così ogni servizio riceve la distanza MINIMA, e chi è già visitato non si rivisita (gestione dei cicli).
    distances = {service: 0}
    queue = deque([service])
    while queue:
        current = queue.popleft()
        if distances[current] == max_hops:
            continue  # limite di passi raggiunto: non si va oltre
        for caller in callers_of.get(current, []):
            if caller not in distances:
                distances[caller] = distances[current] + 1
                queue.append(caller)

    del distances[service]
    return dict(sorted(distances.items(), key=lambda item: (item[1], item[0])))
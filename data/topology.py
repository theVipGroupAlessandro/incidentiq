"""Topologia sintetica di IncidentIQ: i servizi e chi chiama chi."""

# I 5 servizi del negozio online di prova.
SERVICES = ["gateway", "order", "payment", "inventory", "notification"]

# Ogni coppia (A, B) significa: A chiama B (in Neo4j: (A)-[:CALLS]->(B)).
# Se B si guasta, A può risentirne: il guasto "risale" da B verso A.
CALLS = [
    ("gateway", "order"),            # il cliente crea un ordine
    ("gateway", "inventory"),        # il cliente controlla la disponibilità
    ("order", "payment"),            # l'ordine richiede il pagamento
    ("order", "inventory"),          # l'ordine prenota la merce
    ("order", "notification"),       # conferma d'ordine via email
    ("payment", "notification"),     # ricevuta di pagamento
    ("inventory", "notification"),   # avviso di scorte basse
    ("notification", "order"),       # legge i dettagli dell'ordine per l'email -> CICLO
]
"""Synthetic IncidentIQ topology: the services and who calls whom."""

# The 5 services of the sample online shop.
SERVICES = ["gateway", "order", "payment", "inventory", "notification"]

# Each pair (A, B) means: A calls B (in Neo4j: (A)-[:CALLS]->(B)).
# If B fails, A may be affected: failures propagate upstream, from B to A.
CALLS = [
    ("gateway", "order"),            # customer places an order
    ("gateway", "inventory"),        # customer checks availability
    ("order", "payment"),            # order requests payment
    ("order", "inventory"),          # order reserves stock
    ("order", "notification"),       # order confirmation email
    ("payment", "notification"),     # payment receipt
    ("inventory", "notification"),   # low-stock alert
    ("notification", "order"),       # reads order details for the email -> CYCLE
]
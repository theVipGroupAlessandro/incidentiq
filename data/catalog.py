"""Message templates for the synthetic logs."""

# External systems each service depends on (used in timeout and auth messages).
EXTERNAL = {
    "gateway": "auth-server.example.com",
    "order": "tax-api.example.com",
    "payment": "payment-provider.example.com",
    "inventory": "warehouse-api.example.com",
    "notification": "smtp.example.com",
}

# Root-cause messages: written by the service where the failure starts.
# (severity, template, weight) - higher weight = more frequent.
ROOT_MESSAGES = {
    "db_pool_exhaustion": [
        ("ERROR", "Database connection pool exhausted ({used}/{max} connections in use)", 3),
        ("ERROR", "Timed out waiting for a database connection after {db_wait_ms} ms", 2),
    ],
    "api_timeout": [
        ("ERROR", "Request to {external} timed out after {api_timeout_ms} ms", 3),
        ("WARN", "Retrying request to {external} (attempt {attempt}/3)", 1),
    ],
    "memory_exhaustion": [
        ("CRITICAL", "java.lang.OutOfMemoryError: Java heap space", 2),
        ("ERROR", "Container restarted: memory limit exceeded (OOMKilled)", 1),
        ("WARN", "GC pause of {ms} ms, heap usage at {pct}%", 1),
    ],
    "auth_failure": [
        ("ERROR", "Authentication to {external} failed: 401 Unauthorized (credentials expired)", 3),
        ("ERROR", "Access token refresh failed for {external}: invalid_client", 1),
    ],
    # No historical incident matches this one: used for the unknown-cause scenario.
    "unknown": [
        ("ERROR", "Checksum mismatch in stock snapshot {file}, record skipped", 3),
        ("ERROR", "Reconciliation job aborted: {n} records failed validation", 1),
    ],
}

# Symptom messages: written by a caller when the service it calls is failing.
SYMPTOM_MESSAGES = [
    ("ERROR", "Timeout calling {callee} after {ms} ms", 3),
    ("ERROR", "502 Bad Gateway from {callee}", 2),
    ("WARN", "Circuit breaker opened for {callee} after {failures} consecutive failures", 1),
]

# The gateway reports upstream problems to the customer with a 504.
GATEWAY_SYMPTOM = ("ERROR", "504 Gateway Timeout: upstream {callee} did not respond", 1)

# Background noise not linked to any incident. Some look similar to real failures on purpose.
DISTRACTORS = {
    "gateway": [
        ("WARN", "Rate limit exceeded for client {ip}, request rejected", 1),
        ("ERROR", "Malformed JSON in request body from client {ip}", 1),
    ],
    "order": [
        ("ERROR", "Invalid coupon code {code} rejected", 1),
        ("WARN", "Slow query on table orders took {ms} ms", 1),
    ],
    "payment": [
        ("ERROR", "Card declined by issuer: insufficient funds (order {order})", 2),
        ("WARN", "Duplicate payment request ignored for order {order}", 1),
    ],
    "inventory": [
        ("ERROR", "SKU {sku} not found", 2),
        ("WARN", "Cache miss rate at {pct}% for product catalog", 1),
    ],
    "notification": [
        ("WARN", "Email to {email} bounced: mailbox full", 2),
        ("ERROR", "Template order_confirmation missing field 'customer_name'", 1),
    ],
}
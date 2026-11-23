"""Incident records (post-mortems) for the historical episodes.

Each failure type has five (cause, mitigation) variants, used in order,
so the five incidents of the same type do not read the same.
"""
from app.graph_local import upstream_callers
from data.catalog import EXTERNAL
from data.episodes import HISTORICAL
from data.topology import CALLS, SERVICES

TITLES = {
    "db_pool_exhaustion": "{service} database connection pool exhausted",
    "api_timeout": "{service} timeouts calling {external}",
    "memory_exhaustion": "{service} out of memory",
    "auth_failure": "{service} authentication failures towards {external}",
}

ROOT_SYMPTOMS = {
    "db_pool_exhaustion": "{service} logged 'Database connection pool exhausted' and requests waited for a free connection.",
    "api_timeout": "{service} requests to {external} timed out and were retried.",
    "memory_exhaustion": "{service} threw OutOfMemoryError and its container was restarted repeatedly.",
    "auth_failure": "{service} received 401 Unauthorized responses from {external}.",
}

VARIANTS = {
    "db_pool_exhaustion": [
        ("A traffic spike from a marketing campaign used all 50 connections.",
         "Scaled out {service} and enabled queueing at the gateway."),
        ("A slow query held connections open for minutes.",
         "Killed the long-running query and added a missing index."),
        ("A connection leak introduced in the latest release: connections were not returned to the pool.",
         "Rolled back the release and fixed the leak."),
        ("A nightly batch job opened connections in parallel with live traffic.",
         "Moved the batch job to a separate connection pool."),
        ("A deployment doubled the worker threads, and each thread held a connection.",
         "Reverted the thread count and sized workers to the pool limit."),
    ],
    "api_timeout": [
        ("{external} was in an unannounced maintenance window.",
         "Waited for the provider to recover; added status-page monitoring."),
        ("High network latency between our data centre and {external}.",
         "Network team rerouted traffic; added latency alerts."),
        ("{external} rate-limited our requests after we exceeded our daily quota.",
         "Requested a higher quota and added quota usage alerts."),
        ("DNS resolution for {external} failed intermittently.",
         "Switched to a secondary DNS resolver and added DNS caching."),
        ("Regional outage at {external}.",
         "Failed over to the provider's secondary region."),
    ],
    "memory_exhaustion": [
        ("A memory leak in the in-process cache: entries were never evicted.",
         "Restarted the service and added a size limit to the cache."),
        ("A large export loaded the whole dataset into memory.",
         "Changed the export to stream data in chunks."),
        ("An internal queue grew without bounds while a dependency was slow.",
         "Bounded the queue and added back-pressure."),
        ("The heap limit was too small after a framework upgrade increased memory usage.",
         "Raised the heap and container memory limits."),
        ("Processing of large attachments kept full files in memory.",
         "Limited attachment size and processed files as streams."),
    ],
    "auth_failure": [
        ("API credentials for {external} expired and were not rotated.",
         "Rotated the credentials and added an expiry alert."),
        ("The client TLS certificate used to call {external} expired.",
         "Renewed the certificate and automated renewal."),
        ("The token signing key was rotated without updating {service}.",
         "Deployed the new key and documented the rotation procedure."),
        ("Clock drift on {service} hosts made tokens appear expired.",
         "Fixed NTP synchronisation on the hosts."),
        ("The client secret for {external} was revoked by mistake.",
         "Issued a new secret and restricted who can revoke secrets."),
    ],
}

CALLER_SYMPTOM = "{service} reported timeouts and 5xx errors calling {callee}."
GATEWAY_SYMPTOM = "Customers received 504 Gateway Timeout errors from the gateway."


def build_incidents():
    used = {failure: 0 for failure in VARIANTS}
    incidents = []
    for episode in HISTORICAL:
        service, failure = episode["service"], episode["failure"]
        names = {"service": service, "external": EXTERNAL[service]}

        cause, mitigation = VARIANTS[failure][used[failure]]
        used[failure] += 1

        affected = upstream_callers(service, SERVICES, CALLS, max_hops=episode["spread"])
        distance = {service: 0, **affected}
        symptoms = [ROOT_SYMPTOMS[failure].format(**names)]
        for caller, hops in affected.items():
            if caller == "gateway":
                symptoms.append(GATEWAY_SYMPTOM)
            else:
                callee = next(b for a, b in CALLS if a == caller and distance.get(b) == hops - 1)
                symptoms.append(CALLER_SYMPTOM.format(service=caller, callee=callee))

        incidents.append({
            "id": episode["id"],
            "title": TITLES[failure].format(**names).capitalize(),
            "date": episode["start"][:10],
            "status": "resolved",
            "service": service,
            "failure_type": failure,
            "affected_services": [service, *affected],
            "symptoms": " ".join(symptoms),
            "cause": cause.format(**names),
            "mitigation": mitigation.format(**names),
        })
    return incidents
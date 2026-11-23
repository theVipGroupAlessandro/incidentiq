from app.logs import fingerprint, group_logs, in_window, load_logs, log_documents, redact


def make_log(log_id, ts, service, message, severity="ERROR"):
    return {"log_id": log_id, "timestamp": ts, "service": service, "severity": severity,
            "message": message, "trace_id": "t" + log_id, "span_id": "s", "incident_id": None}


def test_fingerprint_ignores_numbers_and_ids():
    assert fingerprint("Timeout calling payment after 3000 ms") == fingerprint("Timeout calling payment after 30000 ms")
    assert fingerprint("SKU SKU-1234 not found") == fingerprint("SKU SKU-9876 not found")
    assert fingerprint("Timeout calling payment after 3000 ms") != fingerprint("Timeout calling order after 3000 ms")


def test_redact_hides_emails_and_ips():
    assert redact("Email to user12@example.com bounced") == "Email to <email> bounced"
    assert redact("Rate limit exceeded for client 10.0.3.7") == "Rate limit exceeded for client <ip>"


def test_repeated_messages_become_one_group():
    logs = [make_log("L1", "2026-11-09T10:00:00Z", "payment", "pool exhausted (50/50)"),
            make_log("L2", "2026-11-09T10:05:00Z", "payment", "pool exhausted (49/50)"),
            make_log("L3", "2026-11-09T10:06:00Z", "order", "pool exhausted (50/50)")]
    documents = log_documents(logs)
    assert len(documents) == 2
    payment = next(doc for doc in documents if doc["services"] == ["payment"])
    assert payment["count"] == 2 and payment["log_ids"] == ["L1", "L2"]


def test_same_message_much_later_is_a_new_group():
    logs = [make_log("L1", "2026-05-04T10:00:00Z", "payment", "pool exhausted"),
            make_log("L2", "2026-11-09T10:00:00Z", "payment", "pool exhausted")]
    assert len(group_logs(logs)) == 2


def test_warnings_are_not_indexed():
    logs = [make_log("L1", "2026-11-09T10:00:00Z", "order", "Slow query", severity="WARN")]
    assert log_documents(logs) == []


def test_time_window_filter():
    doc = {"first_seen": "2026-11-09T10:30:00Z", "last_seen": "2026-11-09T10:50:00Z"}
    assert in_window("2026-11-09T10:00:00Z", "2026-11-09T11:00:00Z")(doc)
    assert not in_window("2026-11-10T10:00:00Z", "2026-11-10T11:00:00Z")(doc)


def test_real_logs_shrink_after_deduplication():
    logs = load_logs()
    documents = log_documents(logs)
    errors = [log for log in logs if log["severity"] in {"ERROR", "CRITICAL"}]
    assert len(documents) < len(errors) / 2
    assert sum(doc["count"] for doc in documents) == len(errors)
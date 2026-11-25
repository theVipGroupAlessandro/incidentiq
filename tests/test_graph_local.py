import pytest

from app.graph_local import upstream_callers
from data.topology import CALLS, SERVICES


def callers(service, max_hops=3):
    return upstream_callers(service, SERVICES, CALLS, max_hops)


def test_payment_up_to_three_hops():
    assert callers("payment") == {"order": 1, "gateway": 2, "notification": 2, "inventory": 3}


def test_hop_limit():
    assert callers("payment", max_hops=2) == {"order": 1, "gateway": 2, "notification": 2}


def test_cycle_does_not_include_start_service():
    # order -> notification -> order is a cycle: order must not appear among its own callers
    assert "order" not in callers("order")


def test_gateway_has_no_callers():
    assert callers("gateway") == {}


def test_unknown_service_is_rejected():
    with pytest.raises(ValueError):
        callers("shipping")

        

def test_payment_downstream_is_notification_then_order():
    from app.graph_local import downstream_callees
    # payment calls notification; notification calls order; order calls inventory (and payment, the start).
    assert downstream_callees("payment", SERVICES, CALLS) == {"notification": 1, "order": 2, "inventory": 3}


def test_gateway_reaches_everything_downstream():
    from app.graph_local import downstream_callees
    assert set(downstream_callees("gateway", SERVICES, CALLS)) == {"order", "inventory", "payment", "notification"}
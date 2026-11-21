import pytest

from app.graph_local import upstream_callers
from data.topology import CALLS, SERVICES


def callers(service, max_hops=3):
    return upstream_callers(service, SERVICES, CALLS, max_hops)


def test_payment_fino_a_3_passi():
    assert callers("payment") == {"order": 1, "gateway": 2, "notification": 2, "inventory": 3}


def test_limite_di_passi():
    assert callers("payment", max_hops=2) == {"order": 1, "gateway": 2, "notification": 2}


def test_ciclo_non_include_il_servizio_di_partenza():
    # order -> notification -> order è un ciclo: order non deve comparire tra i propri chiamanti
    assert "order" not in callers("order")


def test_gateway_non_ha_chiamanti():
    assert callers("gateway") == {}


def test_servizio_sconosciuto():
    with pytest.raises(ValueError):
        callers("shipping")
""" TODO: Implement the tests. """

import pytest


@pytest.fixture
def reactor():
    from graphite_beacon.core import Reactor

    return Reactor()


def test_reactor():
    from graphite_beacon.core import Reactor

    r = Reactor()
    assert r
    assert r.reinit()


def test_alert(reactor):
    from graphite_beacon.alerts import BaseAlert, GraphiteAlert, URLAlert

    alert = BaseAlert.get(reactor, name='Test', query='*', rules=[{}])
    assert alert
    assert isinstance(alert, GraphiteAlert)

    alert = BaseAlert.get(reactor, name='Test', query='*', source='url', rules=[{}])
    assert isinstance(alert, URLAlert)


def test_invalid_handler(reactor):
    reactor.reinit(critical_handlers=['log', 'unknown'])
    assert len(reactor.handlers['critical']) == 1


def test_invalid_method():
    pass


def test_invalid_url():
    pass


def test_invalid_rule():
    pass


def test_load_error():
    pass


def test_alert_error():
    pass


def test_warning():
    pass


def test_critical():
    pass


def test_graphite_record():
    pass

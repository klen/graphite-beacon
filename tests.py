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


def test_convert():
    from graphite_beacon.utils import convert

    assert convert(789874, 'none') == 789874
    assert convert(45, 'percent') == "45%"
    assert convert(.25, 'percent') == "25%"

    assert convert(789, 'bytes') == 789
    assert convert(456789, 'bytes') == '456.8KB'
    assert convert(45678912, 'bytes') == '45.7MB'
    assert convert(4567891245, 'bytes') == '4.6GB'

    assert convert(789, 'short') == 789
    assert convert(456789, 'short') == '456.8K'
    assert convert(45678912, 'short') == '45.7Mil'
    assert convert(4567891245, 'short') == '4.6Bil'

    assert convert(789, 's') == "13.2m"
    assert convert(789456, 's') == "1.3w"
    assert convert(789456234, 's') == "25y"

    assert convert(79456234, 'ms') == "22.1h"
    assert convert(34, 'ms') == "34ms"


def test_parse_interval():
    from graphite_beacon.utils import parse_interval

    assert parse_interval('10') == 10000
    assert parse_interval('15s') == 15000
    assert parse_interval('5minute') == 300000
    assert parse_interval('5month') == 12960000000


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

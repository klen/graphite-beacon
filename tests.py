""" TODO: Implement the tests. """

import pytest
import mock


@pytest.fixture
def reactor():
    from graphite_beacon.core import Reactor

    return Reactor()


def test_reactor():
    from graphite_beacon.core import Reactor

    rr = Reactor()
    assert rr
    assert rr.reinit()

    rr = Reactor(include=['example-config.json'], alerts=[
        {'name': 'test', 'query': '*', 'rules': ["normal: == 0"]}])
    assert rr.options['interval'] == '20minute'
    assert len(rr.alerts) == 3


def test_alert(reactor):
    from graphite_beacon.alerts import BaseAlert, GraphiteAlert, URLAlert

    alert1 = BaseAlert.get(reactor, name='Test', query='*', rules=["normal: == 0"])
    assert alert1
    assert isinstance(alert1, GraphiteAlert)

    alert2 = BaseAlert.get(reactor, name='Test', query='*', source='url', rules=["normal: == 0"])
    assert isinstance(alert2, URLAlert)

    assert alert1 != alert2

    alert3 = BaseAlert.get(reactor, name='Test', query='*', interval='2m', rules=["normal: == 0"])
    assert alert3.interval == '2minute'

    assert alert1 == alert3
    assert set([alert1, alert3]) == set([alert1])

    alert = BaseAlert.get(reactor, name='Test', query='*', rules=["warning: >= 3MB"])
    assert alert.rules[0]['value'] == 3000000


def test_multimetrics(reactor):
    from graphite_beacon.alerts import BaseAlert

    alert = BaseAlert.get(
        reactor, name="Test", query="*", rules=["critical: > 100", "warning: > 50"])
    reactor.alerts = set([alert])

    with mock.patch.object(reactor, 'notify'):
        alert.check([(110, 'metric1'), (60, 'metric2'), (30, 'metric3')])
        assert reactor.notify.call_count == 2
        assert reactor.notify.call_args_list[0][0][0] == 'critical'
        assert reactor.notify.call_args_list[0][1]['target'] == 'metric1'
        assert reactor.notify.call_args_list[1][0][0] == 'warning'
        assert reactor.notify.call_args_list[1][1]['target'] == 'metric2'

    with mock.patch.object(reactor, 'notify'):
        alert.check([(60, 'metric1'), (60, 'metric2'), (30, 'metric3')])
        assert reactor.notify.call_count == 1
        assert reactor.notify.call_args_list[0][0][0] == 'warning'
        assert reactor.notify.call_args_list[0][1]['target'] == 'metric1'

    with mock.patch.object(reactor, 'notify'):
        alert.check([(60, 'metric1'), (30, 'metric2'), (105, 'metric3')])
        assert reactor.notify.call_count == 2
        assert reactor.notify.call_args_list[0][0][0] == 'normal'
        assert reactor.notify.call_args_list[0][1]['target'] == 'metric2'
        assert reactor.notify.call_args_list[1][0][0] == 'critical'
        assert reactor.notify.call_args_list[1][1]['target'] == 'metric3'

    with mock.patch.object(reactor, 'notify'):
        alert.check([(60, 'metric1'), (30, 'metric2'), (105, 'metric3')])
        assert reactor.notify.call_count == 0

    assert alert.state['metric1'] == 'warning'
    reactor.repeat()
    assert alert.state == {None: 'normal'}


def test_invalid_handler(reactor):
    reactor.reinit(critical_handlers=['log', 'unknown'])
    assert len(reactor.handlers['critical']) == 1


def test_convert():
    from graphite_beacon.utils import convert_to_format, convert_from_format

    assert convert_to_format(789874) == 789874
    assert convert_from_format(789874)
    assert convert_to_format(45, 'percent') == "45%"
    assert convert_from_format('45%') == 45

    assert convert_to_format(789, 'bytes') == 789
    assert convert_to_format(456789, 'bytes') == '456.8KB'
    assert convert_from_format('456.8KB') == 456800
    assert convert_to_format(45678912, 'bytes') == '45.7MB'
    assert convert_from_format('45.7MB') == 45700000
    assert convert_to_format(4567891245, 'bytes') == '4.6GB'
    assert convert_from_format('4.6GB') == 4600000000

    assert convert_to_format(789, 'short') == 789
    assert convert_to_format(456789, 'short') == '456.8K'
    assert convert_from_format('456.8K') == 456800
    assert convert_to_format(45678912, 'short') == '45.7Mil'
    assert convert_from_format('45.7Mil') == 45700000
    assert convert_to_format(4567891245, 'short') == '4.6Bil'
    assert convert_from_format('4.6Bil') == 4600000000

    assert convert_to_format(789, 's') == "13.2m"
    assert convert_from_format('13.2m') == 792
    assert convert_to_format(789456, 's') == "1.3w"
    assert convert_from_format('1.3w') == 786240
    assert convert_to_format(789456234, 's') == "25y"

    assert convert_to_format(79456234, 'ms') == "22.1h"
    assert convert_to_format(34, 'ms') == "34ms"


def test_parse_interval():
    from graphite_beacon.utils import parse_interval

    assert parse_interval('10') == 10000.0
    assert parse_interval('15s') == 15000.0
    assert parse_interval('5minute') == 300000.0
    assert parse_interval('6m') == 360000.0
    assert parse_interval('1.2day') == 103680000.0
    assert parse_interval('4d') == 345600000.0
    assert parse_interval('5month') == 12960000000.0


def test_interval_to_graphite():
    from graphite_beacon.utils import interval_to_graphite

    assert interval_to_graphite('10m') == '10minute'
    assert interval_to_graphite('875') == '875second'
    assert interval_to_graphite('2hour') == '2hour'


def test_parse_rule():
    from graphite_beacon.utils import parse_rule
    import operator as op

    with pytest.raises(ValueError):
        assert parse_rule('invalid')

    assert parse_rule('normal: == 0') == {'level': 'normal', 'op': op.eq, 'value': 0}

    from graphite_beacon.utils import RULE_RE
    rule = 'critical: < 30MB'
    match = RULE_RE.match(rule)
    level, cond, value = match.groups()
    assert level == 'critical'
    assert cond == '<'
    assert value == '30MB'

    assert parse_rule('critical: < 30MB') == {'level': 'critical', 'op': op.lt, 'value': 30000000}
    assert parse_rule('warning: >= 30MB') == {'level': 'warning', 'op': op.ge, 'value': 30000000}

""" TODO: Implement the tests. """

import logging
import pytest
import mock


@pytest.fixture
def reactor():
    from graphite_beacon.core import Reactor

    return Reactor(history_size='40m')


def test_reactor():
    from graphite_beacon.core import Reactor

    rr = Reactor()
    assert rr
    assert rr.reinit()

    rr = Reactor(include=['example-config.json'], alerts=[
        {'name': 'test', 'query': '*', 'rules': ["normal: == 0"]}])
    assert rr.options['interval'] == '20minute'
    assert len(rr.alerts) == 2


def test_convert_config_log_level():
    from graphite_beacon.core import _get_numeric_log_level

    assert logging.DEBUG == _get_numeric_log_level('debug')
    assert logging.DEBUG == _get_numeric_log_level('DEBUG')

    assert logging.INFO == _get_numeric_log_level('info')
    assert logging.INFO == _get_numeric_log_level('INFO')

    assert logging.WARN == _get_numeric_log_level('warn')
    assert logging.WARN == _get_numeric_log_level('WARN')

    assert logging.WARNING == _get_numeric_log_level('warning')
    assert logging.WARNING == _get_numeric_log_level('WARNING')

    assert logging.ERROR == _get_numeric_log_level('error')
    assert logging.ERROR == _get_numeric_log_level('ERROR')

    assert logging.CRITICAL == _get_numeric_log_level('critical')
    assert logging.CRITICAL == _get_numeric_log_level('CRITICAL')


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
    assert alert.rules[0]['value'] == 3145728


def test_multimetrics(reactor):
    from graphite_beacon.alerts import BaseAlert

    alert = BaseAlert.get(
        reactor, name="Test", query="*", rules=[
            "critical: > 100", "warning: > 50", "warning: < historical / 2"])
    reactor.alerts = set([alert])

    with mock.patch.object(reactor, 'notify'):
        alert.check([(110, 'metric1'), (60, 'metric2'), (30, 'metric3')])

        assert reactor.notify.call_count == 2

        # metric1 - critical
        assert reactor.notify.call_args_list[0][0][0] == 'critical'
        assert reactor.notify.call_args_list[0][1]['target'] == 'metric1'

        # metric2 - warning
        assert reactor.notify.call_args_list[1][0][0] == 'warning'
        assert reactor.notify.call_args_list[1][1]['target'] == 'metric2'

    assert list(alert.history['metric1']) == [110]

    with mock.patch.object(reactor, 'notify'):
        alert.check([(60, 'metric1'), (60, 'metric2'), (30, 'metric3')])
        assert reactor.notify.call_count == 1

        # metric1 - warning, metric2 didn't change
        assert reactor.notify.call_args_list[0][0][0] == 'warning'
        assert reactor.notify.call_args_list[0][1]['target'] == 'metric1'

    assert list(alert.history['metric1']) == [110, 60]

    with mock.patch.object(reactor, 'notify'):
        alert.check([(60, 'metric1'), (30, 'metric2'), (105, 'metric3')])
        assert reactor.notify.call_count == 2

        # metric2 - normal
        assert reactor.notify.call_args_list[0][0][0] == 'normal'
        assert reactor.notify.call_args_list[0][1]['target'] == 'metric2'

        # metric3 - critical
        assert reactor.notify.call_args_list[1][0][0] == 'critical'
        assert reactor.notify.call_args_list[1][1]['target'] == 'metric3'

    assert list(alert.history['metric1']) == [110, 60, 60]

    with mock.patch.object(reactor, 'notify'):
        alert.check([(60, 'metric1'), (30, 'metric2'), (105, 'metric3')])
        assert reactor.notify.call_count == 0

    with mock.patch.object(reactor, 'notify'):
        alert.check([(70, 'metric1'), (21, 'metric2'), (105, 'metric3')])
        assert reactor.notify.call_count == 1

        # metric2 - historical warning
        assert reactor.notify.call_args_list[0][0][0] == 'warning'
        assert reactor.notify.call_args_list[0][1]['target'] == 'metric2'

    assert list(alert.history['metric1']) == [60, 60, 60, 70]
    assert alert.state['metric1'] == 'warning'

    reactor.repeat()

    assert alert.state == {
        None: 'normal', 'metric1': 'normal', 'metric2': 'normal', 'metric3': 'normal',
        'waiting': 'normal', 'loading': 'normal'}


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
    assert convert_to_format(456789, 'bytes') == '446.1KB'
    assert convert_from_format('456.8KB') == 467763.2
    assert convert_to_format(45678912, 'bytes') == '43.6MB'
    assert convert_from_format('45.7MB') == 47919923.2
    assert convert_to_format(4567891245, 'bytes') == '4.3GB'
    assert convert_from_format('4.6GB') == 4939212390.4

    assert convert_from_format('456.8Kb') == 467763.2
    assert convert_from_format('456.8Kbps') == 456800

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
    from graphite_beacon.utils import parse_rule, DEFAULT_MOD
    import operator as op

    with pytest.raises(ValueError):
        assert parse_rule('invalid')

    assert parse_rule('normal: == 0') == {
        'level': 'normal', 'op': op.eq, 'value': 0, 'mod': DEFAULT_MOD, 'raw': 'normal: == 0'}
    assert parse_rule('critical: < 30MB') == {
        'level': 'critical', 'op': op.lt, 'value': 31457280, 'mod': DEFAULT_MOD,
        'raw': 'critical: < 30MB'}
    assert parse_rule('warning: >= 30MB') == {
        'level': 'warning', 'op': op.ge, 'value': 31457280, 'mod': DEFAULT_MOD,
        'raw': 'warning: >= 30MB'}
    assert parse_rule('warning: >= historical') == {
        'level': 'warning', 'op': op.ge, 'value': 'historical', 'mod': DEFAULT_MOD,
        'raw': 'warning: >= historical'}
    rule = parse_rule('warning: >= historical * 1.2')
    assert rule['mod']
    assert rule['mod'](5) == 6


def test_html_template(reactor):
    from graphite_beacon.handlers.smtp import SMTPHandler
    from graphite_beacon.alerts import BaseAlert

    target = 'node.com'
    galert = BaseAlert.get(reactor, name='Test', query='*', rules=["normal: == 0"])
    galert.history[target] += [1, 2, 3, 4, 5]

    reactor.options['smtp'] = {
        'to': 'user@com.com', 'graphite_url': 'http://graphite.myhost.com'}
    smtp = SMTPHandler(reactor)

    message = smtp.get_message(
        'critical', galert, 3000000, target=target, ntype='graphite', rule=galert.rules[0])
    assert message

    assert len(message._payload) == 2
    text, html = message._payload
    assert 'graphite.myhost.com' in html.as_string()

    ualert = BaseAlert.get(
        reactor, source='url', name='Test', query='http://google.com', rules=["critical: != 200"])
    message = smtp.get_message('critical', ualert, '3000000', target, 'url')
    assert message

    assert len(message._payload) == 2
    _, html = message._payload
    assert 'google.com' in html.as_string()

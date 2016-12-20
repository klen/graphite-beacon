import mock

from graphite_beacon import units
from graphite_beacon._compat import urlparse
from graphite_beacon.alerts import BaseAlert, GraphiteAlert, URLAlert
from graphite_beacon.core import Reactor
from graphite_beacon.units import SECOND

BASIC_ALERT_OPTS = {
    'name': 'GraphiteTest',
    'query': '*',
    'rules': ['normal: == 0'],
}

BASIC_GRAPHITE_ALERT_OPTS = BASIC_ALERT_OPTS

BASIC_URL_ALERT_OPTS = {
    'name': 'URLTest',
    'query': '*',
    'source': 'url',
    'rules': ['normal: == 0'],
}


def test_alert(reactor):
    alert1 = BaseAlert.get(reactor, **BASIC_GRAPHITE_ALERT_OPTS)
    assert alert1
    assert isinstance(alert1, GraphiteAlert)

    alert2 = BaseAlert.get(reactor, **BASIC_URL_ALERT_OPTS)
    assert isinstance(alert2, URLAlert)

    assert alert1 != alert2

    alert3 = BaseAlert.get(reactor, interval='2m', **BASIC_GRAPHITE_ALERT_OPTS)
    assert alert3.interval.as_tuple() == (2, units.MINUTE)

    assert alert1 == alert3
    assert set([alert1, alert3]) == set([alert1])

    alert = BaseAlert.get(reactor, name='Test', query='*', rules=["warning: >= 3MB"])
    assert alert.rules[0]['exprs'][0]['value'] == 3145728


def test_history_size(reactor):
    alert = BaseAlert.get(reactor, interval='1second', history_size='10second',
                          **BASIC_GRAPHITE_ALERT_OPTS)
    assert alert.history_size == 10

    alert = BaseAlert.get(reactor, interval='1minute', history_size='5hour',
                          **BASIC_GRAPHITE_ALERT_OPTS)
    assert alert.history_size == 60*5

    alert = BaseAlert.get(reactor, interval='5minute', history_size='1minute',
                          **BASIC_GRAPHITE_ALERT_OPTS)
    assert alert.history_size == 1


def test_time_window():
    # Time window set explicitly on the alert - should be preferred
    alert = BaseAlert.get(Reactor(), time_window='6second', interval='3second',
                          **BASIC_GRAPHITE_ALERT_OPTS)
    assert alert.time_window.as_tuple() == (6, SECOND)

    # Time window set explicitly at the root - should be preferred next
    reactor = Reactor(interval='10second', time_window='4second')
    alert = BaseAlert.get(reactor, interval='3second', **BASIC_GRAPHITE_ALERT_OPTS)
    assert alert.time_window.as_tuple() == (4, SECOND)

    # No time window set, but interval set directly on the alert
    reactor = Reactor(interval='10second')
    alert = BaseAlert.get(reactor, interval='1second', **BASIC_GRAPHITE_ALERT_OPTS)
    assert alert.time_window.as_tuple() == (1, SECOND)

    # Only time interval set at root
    reactor = Reactor(interval='10second')
    alert = BaseAlert.get(reactor, **BASIC_GRAPHITE_ALERT_OPTS)
    assert alert.time_window.as_tuple() == (10, SECOND)


def test_from_time(reactor):
    alert = BaseAlert.get(reactor, time_window='5minute',
                          **BASIC_GRAPHITE_ALERT_OPTS)

    url = urlparse.urlparse(alert.get_graph_url('*'))
    query = urlparse.parse_qs(url.query)
    assert query['from'] == ['-5min']
    assert query['until'] == ['-0s']


def test_from_time_with_until(reactor):
    alert = BaseAlert.get(reactor, time_window='5minute', until='1minute',
                          **BASIC_GRAPHITE_ALERT_OPTS)

    url = urlparse.urlparse(alert.get_graph_url('*'))
    query = urlparse.parse_qs(url.query)
    assert query['from'] == ['-6min']
    assert query['until'] == ['-1min']


def test_multimetrics(reactor):
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


def test_multiexpressions(reactor):
    alert = BaseAlert.get(
        reactor, name="Test", query="*", rules=["warning: > historical * 1.05 AND > 70"])
    reactor.alerts = set([alert])

    with mock.patch.object(reactor, 'notify'):
        alert.check([
            (50, 'metric1'), (65, 'metric1'), (85, 'metric1'), (65, 'metric1'),
            (68, 'metric1'), (75, 'metric1')])

        assert reactor.notify.call_count == 1

        # metric2 - warning
        assert reactor.notify.call_args_list[0][0][0] == 'warning'
        assert reactor.notify.call_args_list[0][1]['target'] == 'metric1'

    assert list(alert.history['metric1']) == [85, 65, 68, 75]

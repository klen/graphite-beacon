"""Implement alerts."""

import math
from collections import defaultdict, deque
from itertools import islice

from tornado import httpclient as hc
from tornado import escape, gen, ioloop, log

from . import _compat as _
from . import units
from .graphite import GraphiteRecord
from .units import MILLISECOND, TimeUnit
from .utils import HISTORICAL, LOGICAL_OPERATORS, convert_to_format, parse_rule

LOGGER = log.gen_log
METHODS = "average", "last_value", "sum", "minimum", "maximum"
LEVELS = {
    'critical': 0,
    'warning': 10,
    'normal': 20,
}


class sliceable_deque(deque):  # pylint: disable=invalid-name

    """Deque with slices support."""

    def __getitem__(self, index):
        """Support slices."""
        try:
            return deque.__getitem__(self, index)
        except TypeError:
            return type(self)(islice(self, index.start, index.stop, index.step))


class AlertFabric(type):

    """Register alert's classes and produce an alert by source."""

    alerts = {}

    def __new__(mcs, name, bases, params):
        """Register an Alert Class in self."""
        source = params.get('source')
        cls = super(AlertFabric, mcs).__new__(mcs, name, bases, params)
        if source:
            mcs.alerts[source] = cls
            LOGGER.info('Register Alert: %s', source)
        return cls

    def get(cls, reactor, source='graphite', **options):
        """Get Alert Class by source."""
        acls = cls.alerts[source]
        return acls(reactor, **options)


class BaseAlert(_.with_metaclass(AlertFabric)):

    """Abstract basic alert class."""

    source = None

    def __init__(self, reactor, **options):
        """Initialize alert."""
        self.reactor = reactor
        self.options = options
        self.client = hc.AsyncHTTPClient()

        try:
            self.configure(**options)
        except Exception as e:
            LOGGER.exception(e)
            raise ValueError("Invalid alert configuration: %s" % e)

        self.waiting = False
        self.state = {None: "normal", "waiting": "normal", "loading": "normal"}
        self.history = defaultdict(lambda: sliceable_deque([], self.history_size))

        LOGGER.info("Alert '%s': has inited", self)

    def __hash__(self):
        """Provide alert's hash."""
        return hash(self.name) ^ hash(self.source)

    def __eq__(self, other):
        """Check that other alert iis the same."""
        return hash(self) == hash(other)

    def __str__(self):
        """String representation."""
        return "%s (%s)" % (self.name, self.interval)

    def configure(self, name=None, rules=None, query=None, **options):
        """Configure the alert."""
        self.name = name
        if not name:
            raise AssertionError("Alert's name should be defined and not empty.")

        if not rules:
            raise AssertionError("%s: Alert's rules is invalid" % name)
        self.rules = [parse_rule(rule) for rule in rules]
        self.rules = list(sorted(self.rules, key=lambda r: LEVELS.get(r.get('level'), 99)))

        assert query, "%s: Alert's query is invalid" % self.name
        self.query = query

        interval_raw = options.get('interval', self.reactor.options['interval'])
        self.interval = TimeUnit.from_interval(interval_raw)

        time_window_raw = options.get(
            'time_window',
            self.reactor.options.get('time_window', interval_raw),
        )
        self.time_window = TimeUnit.from_interval(time_window_raw)

        until_raw = options.get('until', self.reactor.options['until'])
        self.until = TimeUnit.from_interval(until_raw)

        # Adjust the start time to cater for `until`
        self.from_time = self.time_window + self.until

        self._format = options.get('format', self.reactor.options['format'])
        self.request_timeout = options.get(
            'request_timeout', self.reactor.options['request_timeout'])
        self.connect_timeout = options.get(
            'connect_timeout', self.reactor.options['connect_timeout'])

        interval_ms = self.interval.convert_to(units.MILLISECOND)

        history_size_raw = options.get('history_size', self.reactor.options['history_size'])
        history_size_unit = TimeUnit.from_interval(history_size_raw)
        history_size_ms = history_size_unit.convert_to(MILLISECOND)
        self.history_size = int(math.ceil(history_size_ms / interval_ms))

        self.no_data = options.get('no_data', self.reactor.options['no_data'])
        self.loading_error = options.get('loading_error', self.reactor.options['loading_error'])

        if self.reactor.options.get('debug'):
            self.callback = ioloop.PeriodicCallback(self.load, 5000)
        else:
            self.callback = ioloop.PeriodicCallback(self.load, interval_ms)

    def convert(self, value):
        """Convert self value."""
        try:
            return convert_to_format(value, self._format)
        except (ValueError, TypeError):
            return value

    def reset(self):
        """Reset state to normal for all targets.

        It will repeat notification if a metric is still failed.
        """
        for target in self.state:
            self.state[target] = "normal"

    def start(self):
        """Start checking."""
        self.callback.start()
        self.load()

    def stop(self):
        """Stop checking."""
        self.callback.stop()

    def check(self, records):
        """Check current value."""
        for value, target in records:
            LOGGER.info("%s [%s]: %s", self.name, target, value)
            if value is None:
                self.notify(self.no_data, value, target)
                continue
            for rule in self.rules:
                if self.evaluate_rule(rule, value, target):
                    self.notify(rule['level'], value, target, rule=rule)
                    break
            else:
                self.notify('normal', value, target, rule=rule)

            self.history[target].append(value)

    def evaluate_rule(self, rule, value, target):
        """Calculate the value."""
        def evaluate(expr):
            if expr in LOGICAL_OPERATORS.values():
                return expr
            rvalue = self.get_value_for_expr(expr, target)
            if rvalue is None:
                return False  # ignore this result
            return expr['op'](value, rvalue)

        evaluated = [evaluate(expr) for expr in rule['exprs']]
        while len(evaluated) > 1:
            lhs, logical_op, rhs = (evaluated.pop(0) for _ in range(3))
            evaluated.insert(0, logical_op(lhs, rhs))

        return evaluated[0]

    def get_value_for_expr(self, expr, target):
        """I have no idea."""
        if expr in LOGICAL_OPERATORS.values():
            return None
        rvalue = expr['value']
        if rvalue == HISTORICAL:
            history = self.history[target]
            if len(history) < self.history_size:
                return None
            rvalue = sum(history) / float(len(history))

        rvalue = expr['mod'](rvalue)
        return rvalue

    def notify(self, level, value, target=None, ntype=None, rule=None):
        """Notify main reactor about event."""
        # Did we see the event before?
        if target in self.state and level == self.state[target]:
            return False

        # Do we see the event first time?
        if target not in self.state and level == 'normal' \
                and not self.reactor.options['send_initial']:
            return False

        self.state[target] = level
        return self.reactor.notify(level, self, value, target=target, ntype=ntype, rule=rule)

    def load(self):
        """Load from remote."""
        raise NotImplementedError()


class GraphiteAlert(BaseAlert):

    """Check graphite records."""

    source = 'graphite'

    def configure(self, **options):
        """Configure the alert."""
        super(GraphiteAlert, self).configure(**options)

        self.method = options.get('method', self.reactor.options['method'])
        self.default_nan_value = options.get(
            'default_nan_value', self.reactor.options['default_nan_value'])
        self.ignore_nan = options.get('ignore_nan', self.reactor.options['ignore_nan'])
        assert self.method in METHODS, "Method is invalid"

        self.auth_username = self.reactor.options.get('auth_username')
        self.auth_password = self.reactor.options.get('auth_password')
        self.validate_cert = self.reactor.options.get('validate_cert', True)

        self.url = self._graphite_url(
            self.query, graphite_url=self.reactor.options.get('graphite_url'), raw_data=True)
        LOGGER.debug('%s: url = %s', self.name, self.url)

    @gen.coroutine
    def load(self):
        """Load data from Graphite."""
        LOGGER.debug('%s: start checking: %s', self.name, self.query)
        if self.waiting:
            self.notify('warning', 'Process takes too much time', target='waiting', ntype='common')
        else:
            self.waiting = True
            try:
                response = yield self.client.fetch(self.url, auth_username=self.auth_username,
                                                   auth_password=self.auth_password,
                                                   request_timeout=self.request_timeout,
                                                   connect_timeout=self.connect_timeout,
                                                   validate_cert=self.validate_cert)
                records = (
                    GraphiteRecord(line, self.default_nan_value, self.ignore_nan)
                    for line in response.buffer)
                data = [
                    (None if record.empty else getattr(record, self.method), record.target)
                    for record in records]
                if len(data) == 0:
                    raise ValueError('No data')
                self.check(data)
                self.notify('normal', 'Metrics are loaded', target='loading', ntype='common')
            except Exception as e:
                self.notify(
                    self.loading_error, 'Loading error: %s' % e, target='loading', ntype='common')
            self.waiting = False

    def get_graph_url(self, target, graphite_url=None):
        """Get Graphite URL."""
        return self._graphite_url(target, graphite_url=graphite_url, raw_data=False)

    def _graphite_url(self, query, raw_data=False, graphite_url=None):
        """Build Graphite URL."""
        query = escape.url_escape(query)
        graphite_url = graphite_url or self.reactor.options.get('public_graphite_url')

        url = "{base}/render/?target={query}&from=-{from_time}&until=-{until}".format(
            base=graphite_url, query=query,
            from_time=self.from_time.as_graphite(),
            until=self.until.as_graphite(),
        )
        if raw_data:
            url = "{}&format=raw".format(url)
        return url


class URLAlert(BaseAlert):

    """Check URLs."""

    source = 'url'

    @staticmethod
    def get_data(response):
        """Value is response.status."""
        return response.code

    @gen.coroutine
    def load(self):
        """Load URL."""
        LOGGER.debug('%s: start checking: %s', self.name, self.query)
        if self.waiting:
            self.notify('warning', 'Process takes too much time', target='waiting', ntype='common')
        else:
            self.waiting = True
            try:
                response = yield self.client.fetch(
                    self.query, method=self.options.get('method', 'GET'),
                    request_timeout=self.request_timeout,
                    connect_timeout=self.connect_timeout,
                    validate_cert=self.options.get('validate_cert', True))
                self.check([(self.get_data(response), self.query)])
                self.notify('normal', 'Metrics are loaded', target='loading', ntype='common')

            except Exception as e:
                self.notify('critical', str(e), target='loading', ntype='common')

            self.waiting = False

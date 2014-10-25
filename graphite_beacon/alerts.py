import operator as op
from re import compile as re
from . import _compat as _

from tornado import ioloop, httpclient as hc, gen, log, escape

from .graphite import GraphiteRecord


OPERATORS = {'lt': op.lt, 'le': op.le, 'eq': op.eq, 'gt': op.gt, 'ge': op.ge}
LOGGER = log.gen_log
METHODS = "average", "last_value"
TIME_RE = re('(\d+)')
TIME_UNIT_SIZE = {
    "second": 1000,
    "minute": 60 * 1000,
    "hour": 60 * 60 * 1000,
    "day": 24 * 60 * 60 * 1000,
    "month": 30 * 24 * 60 * 60 * 1000,
    "year": 365.2425 * 24 * 60 * 60 * 1000
}


class AlertFabric(type):

    alerts = {}

    def __new__(mcs, name, bases, params):
        source = params.get('source')
        cls = super(AlertFabric, mcs).__new__(mcs, name, bases, params)
        if source:
            mcs.alerts[source] = cls
            LOGGER.info('Register Alert: %s' % source)
        return cls

    def get(cls, reactor, source='graphite', **options):
        acls = cls.alerts[source]
        return acls(reactor, **options)


class BaseAlert(_.with_metaclass(AlertFabric)):

    """ Abstract basic alert class. """

    source = None

    def __init__(self, reactor, **options):
        self.reactor = reactor
        self.options = options
        self.client = hc.AsyncHTTPClient()

        try:
            self.configure(**options)
        except Exception as e:
            raise ValueError("Invalid alert configuration: %s" % e)

        self.waiting = False
        self.level = 'normal'

        LOGGER.info("Alert '%s': has inited" % self)

    def configure(self, name=None, rules=None, query=None, **options):
        assert name, "Alert's name is invalid"
        self.name = name
        assert rules, "%s: Alert's rules is invalid" % name
        self.rules = rules
        assert query, "%s: Alert's query is invalid" % self.name
        self.query = query
        self.interval = options.get('interval', self.reactor.options['interval'])
        self.callback = ioloop.PeriodicCallback(self.load, self.parse_interval(self.interval))

    def __str__(self):
        return "%s (%s)" % (self.name, self.interval)

    @staticmethod
    def parse_interval(interval):
        _, count, unit = TIME_RE.split(interval)
        return int(count) * TIME_UNIT_SIZE[unit]

    def notify(self, level, value, comment=None):
        if self.level == level:
            return False
        self.level = level
        return self.reactor.notify(level, self, value, comment=comment)

    def start(self):
        self.callback.start()
        return self

    def stop(self):
        self.callback.stop()
        return self

    def check(self, value, comment=""):
        for rule in self.rules:
            op = OPERATORS[rule['operator']]
            if op(value, rule['value']):
                return self.notify(rule.get('level', 'warning'), value, comment)

        self.notify('normal', value, comment)

    def load(self):
        raise NotImplementedError()


class GraphiteAlert(BaseAlert):

    source = 'graphite'

    def configure(self, **options):
        super(GraphiteAlert, self).configure(**options)

        self.method = options.get('method', self.reactor.options['method'])
        assert self.method in METHODS, "Method is invalid"

        query = escape.url_escape(self.query)
        self.url = "%(base)s/render/?target=%(query)s&rawData=true&from=-%(interval)s" % {
            'base': self.reactor.options['graphite_url'], 'query': query,
            'interval': self.interval}

    @gen.coroutine
    def load(self):
        LOGGER.debug('%s: start checking: %s' % (self.name, self.url))
        if self.waiting:
            self.notify('warning', 'waiting for metrics')
        else:
            self.waiting = True
            try:
                response = yield self.client.fetch(
                    self.url,
                    auth_username=self.reactor.options.get('auth_username'),
                    auth_password=self.reactor.options.get('graphite_pass'),
                )
                for record in (GraphiteRecord(line) for line in response.buffer):
                    value = getattr(record, self.method)
                    self.check(value, comment=record.target)
            except Exception as e:
                self.notify('critical', e)
            self.waiting = False


class URLAlert(BaseAlert):

    source = 'url'

    @gen.coroutine
    def load(self):
        LOGGER.debug('%s: start checking: %s' % (self.name, self.query))
        if self.waiting:
            self.notify('warning', 'waiting for metrics')
        else:
            self.waiting = True
            try:
                response = yield self.client.fetch(
                    self.query, method=self.options.get('method', 'GET'),
                    auth_username=self.reactor.options.get('auth_username'),
                    auth_password=self.reactor.options.get('graphite_pass'),
                )
                self.check(response.code)
            except Exception as e:
                self.notify('critical', e)
            self.waiting = False

from tornado import ioloop, httpclient as hc, gen, log, escape

from . import _compat as _
from .graphite import GraphiteRecord
from .utils import convert_to_format, parse_interval, interval_to_graphite, parse_rule


LOGGER = log.gen_log
METHODS = "average", "last_value"
LEVELS = {
    'critical': 0,
    'warning': 10,
    'normal': 20,
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
        self.state = {None: "normal"}

        LOGGER.info("Alert '%s': has inited" % self)

    def __hash__(self):
        return hash(self.name) ^ hash(self.source)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __str__(self):
        return "%s (%s)" % (self.name, self.interval)

    def configure(self, name=None, rules=None, query=None, **options):
        assert name, "Alert's name is invalid"
        self.name = name
        assert rules, "%s: Alert's rules is invalid" % name
        self.rules = [parse_rule(rule) for rule in rules]
        self.rules = list(sorted(self.rules, key=lambda r: LEVELS.get(r.get('level'), 99)))
        assert query, "%s: Alert's query is invalid" % self.name
        self.query = query
        self.interval = interval_to_graphite(options.get('interval',
                                                         self.reactor.options['interval']))
        if self.reactor.options.get('debug'):
            self.callback = ioloop.PeriodicCallback(self.load, 5000)
        else:
            self.callback = ioloop.PeriodicCallback(self.load, parse_interval(self.interval))
        self._format = options.get('format', self.reactor.options['format'])

    def convert(self, value):
        return convert_to_format(value, self._format)

    def reset(self):
        self.state = {None: "normal"}

    def start(self):
        self.callback.start()
        return self

    def stop(self):
        self.callback.stop()
        return self

    def check(self, records):
        for value, target in records:
            LOGGER.debug("%s: %s", target, value)
            for rule in self.rules:
                if rule['op'](value, rule['value']):
                    self.notify(rule['level'], value, target)
                    break
            else:
                self.notify('normal', value, target)

    def notify(self, level, value, target=None, ntype=None):
        if level != self.state.get(target, 'normal'):
            self.state[target] = level
            return self.reactor.notify(level, self, value, target=target, ntype=ntype)

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
            self.notify('warning', 'Process takes too much time', 'waiting', 'common')
        else:
            self.waiting = True
            try:
                response = yield self.client.fetch(
                    self.url,
                    auth_username=self.reactor.options.get('auth_username'),
                    auth_password=self.reactor.options.get('auth_password'),
                )
                records = (GraphiteRecord(line) for line in response.buffer)
                self.check([(getattr(record, self.method), record.target) for record in records])
            except Exception as e:
                self.notify('critical', 'Loading error: %s' % e, target='loading', ntype='common')
            self.waiting = False

    def get_graph_url(self, target):
        query = escape.url_escape(target)
        return "%(base)s/render/?target=%(query)s&from=-%(interval)s" % {
            'base': self.reactor.options['graphite_url'], 'query': query,
            'interval': self.interval}


class URLAlert(BaseAlert):

    source = 'url'

    @gen.coroutine
    def load(self):
        LOGGER.debug('%s: start checking: %s' % (self.name, self.query))
        if self.waiting:
            self.reactor.notify('warning', 'Process takes too much time', ntype='common')
        else:
            self.waiting = True
            try:
                response = yield self.client.fetch(
                    self.query, method=self.options.get('method', 'GET'),
                )
                self.check([(response.code, self.query)])
            except Exception as e:
                self.notify('critical', 'Loading error: %s' % e, target='loading', ntype='common')
            self.waiting = False

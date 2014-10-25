import operator as op
import os
from re import compile as re

import json
from tornado import ioloop, log, httpclient as hc, gen

from .graphite import GraphiteRecord
from .handlers import registry


LOGGER = log.gen_log

METHODS = "average", "last_value"

LEVELS = 'critical', 'warning', 'normal', 'no data'

OPERATORS = {'lt': op.lt, 'le': op.le, 'eq': op.eq, 'gt': op.gt, 'ge': op.ge}

TIME_UNIT_SIZE = {
    "second": 1000,
    "minute": 60 * 1000,
    "hour": 60 * 60 * 1000,
    "day": 24 * 60 * 60 * 1000,
    "month": 30 * 24 * 60 * 60 * 1000,
    "year": 365.2425 * 24 * 60 * 60 * 1000
}

TIME_RE = re('(\d+)')


class Alert(object):

    def __init__(self, reactor, name=None, query=None, **options):
        self.reactor = reactor

        try:
            self.name = name
            assert self.name, "Alert's name is invalid"
            self.query = query
            assert self.query, "Alert's query is invalid"
            self.interval = options.get('interval', reactor.options['interval'])
            self.internal_sec = self.parse_interval(self.interval)
            self.method = options.get('method', reactor.options['method'])
            assert self.method in METHODS, "Method is invalid"
        except Exception as e:
            raise ValueError("Invalid configuration: %s" % e)

        self.rules = options.get('rules', [])

        self.url = "%(base)s/render/?target=%(query)s&rawData=true&from=-%(interval)s" % {
            'base': reactor.options['graphite_url'], 'query': query, 'interval': self.interval}
        self.client = hc.AsyncHTTPClient()

        LOGGER.info("%s: init" % self)

        if self.rules:
            # self.callback = ioloop.PeriodicCallback(self.check, self.parse_interval(interval))
            self.callback = ioloop.PeriodicCallback(self.load, 2000)
        else:
            LOGGER.warn("%s: No rules found, the alert has stopped")

        self.waiting = False
        self.level = 'normal'

    def __str__(self):
        return "%s (%s)" % (self.name, self.interval)

    @staticmethod
    def parse_interval(interval):
        _, count, unit = TIME_RE.split(interval)
        return int(count) * TIME_UNIT_SIZE[unit]

    @gen.coroutine
    def load(self):
        LOGGER.debug('%s: start checking' % self.name)
        if self.waiting:
            self.notify('warning', 'waiting for metrics')
        else:
            self.waiting = True
            try:
                response = yield self.client.fetch(self.url)
                for record in (GraphiteRecord(line) for line in response.buffer):
                    self.check(record)
            except Exception as e:
                self.notify('critical', e)
            self.waiting = False

    def check(self, record):
        value = getattr(record, self.method)
        LOGGER.debug('%s: %s: (%s) %s' % (self.name, record.target, self.method, value))
        for rule in self.rules:
            op = OPERATORS[rule['operator']]
            if op(value, rule['value']):
                return self.notify(rule.get('level', 'warning'), value, record)

        self.notify('normal', value, record)

    def notify(self, level, value, record=None):
        if self.level == level:
            return False
        self.level = level
        return self.reactor.notify(level, self, value, record=record)

    def start(self):
        self.callback.start()
        return self

    def stop(self):
        self.callback.stop()
        return self


class Reactor(object):

    """ Class description. """

    defaults = {
        'config': 'config.json',
        'graphite_url': 'http://localhost',
        'graphite_user': None,
        'graphite_password': None,
        'pidfile': None,
        'interval': '10minute',
        'logging': 'info',
        'method': 'average',
        'prefix': '[BEACON]',
        'critical_handlers': ['log', 'smtp'],
        'warning_handlers': ['log', 'smtp'],
        'normal_handlers': ['log', 'smtp'],
    }

    def __init__(self, **options):
        self.alerts = set()
        self.loop = ioloop.IOLoop.instance()
        self.options = dict(self.defaults)
        self.reinit(**options)
        LOGGER.setLevel(self.options.get('logging', 'info').upper())

    def reinit(self, *args, **options):
        LOGGER.info('Read configuration')

        self.options.update(options)

        config = self.options.get('config')
        if config:
            try:
                with open(config) as fconfig:
                    self.options.update(json.load(fconfig))
            except (IOError, ValueError):
                LOGGER.error('Invalid config file: %s' % config)

        registry.clean()

        self.handlers = {'warning': set(), 'critical': set(), 'normal': set()}
        self.reinit_handlers('warning')
        self.reinit_handlers('critical')
        self.reinit_handlers('normal')

        for alert in list(self.alerts):
            alert.stop()
            self.alerts.remove(alert)

        self.alerts = set(Alert(self, **opts).start() for opts in self.options.get('alerts', []))

        LOGGER.info('Loaded with options:')
        LOGGER.info(json.dumps(self.options, indent=2))
        return self

    def reinit_handlers(self, level='warning'):
        for name in self.options['%s_handlers' % level]:
            try:
                self.handlers[level].add(registry.get(self, name))
            except Exception as e:
                LOGGER.error('Handler "%s" did not init. Error: %s' % (name, e))

    def start(self, *args):
        if self.options.get('pidfile'):
            with open(self.options.get('pidfile'), 'w') as fpid:
                fpid.write(str(os.getpid()))
        LOGGER.info('Reactor starts')
        self.loop.start()

    def stop(self, *args):
        self.loop.stop()
        if self.options.get('pidfile'):
            os.unlink(self.options.get('pidfile'))
        LOGGER.info('Reactor has stopped')

    def notify(self, level, alert, value, record=None):
        for handler in self.handlers[level]:
            handler.notify(level, alert, value, record=record)

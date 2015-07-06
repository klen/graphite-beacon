from tornado import ioloop, httpclient as hc, gen, log, escape

from . import _compat as _
from .graphite import GraphiteRecord
from .utils import convert_to_format, parse_interval, parse_rule, HISTORICAL, HISTORICAL_TOD, interval_to_graphite
import math
import psycopg2
from collections import deque, defaultdict
from itertools import islice
from datetime import datetime

LOGGER = log.gen_log
METHODS = "average", "last_value", "sum"
LEVELS = {
    'critical': 0,
    'warning': 10,
    'normal': 20,
}


class sliceable_deque(deque):

    def __getitem__(self, index):
        try:
            return deque.__getitem__(self, index)
        except TypeError:
            return type(self)(islice(self, index.start, index.stop, index.step))


class AlertFabric(type):

    """ Register alert's classes and produce an alert by source. """

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

        self.history_TOD_value = {}
        self.recorded = False
        self.pastHour = datetime.now().time().hour
        self.historicValues = {}
        self.first = True

        try:
            self.configure(**options)
        except Exception as e:
            raise ValueError("Invalid alert configuration: %s" % e)

        self.waiting = False
        self.state = {None: "normal", "waiting": "normal", "loading": "normal"}
        self.history = defaultdict(lambda: sliceable_deque([], self.history_size))

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

        self.interval = interval_to_graphite(
            options.get('interval', self.reactor.options['interval']))
        interval = parse_interval(self.interval)

        self.time_window = interval_to_graphite(
            options.get('time_window', options.get('interval', self.reactor.options['interval'])))

        self._format = options.get('format', self.reactor.options['format'])
        self.request_timeout = options.get(
            'request_timeout', self.reactor.options['request_timeout'])

        self.history_size = options.get('history_size', self.reactor.options['history_size'])
        self.history_size = parse_interval(self.history_size)
        self.history_size = int(math.ceil(self.history_size / interval))

        self.history_TOD_size = options.get('history_TOD_size', '10d')
        self.history_TOD_size = int(parse_interval(self.history_TOD_size) / 86400000.0)

        if self.reactor.options.get('debug'):
            self.callback = ioloop.PeriodicCallback(self.load, 5000)
        else:
            self.callback = ioloop.PeriodicCallback(self.load, interval)

    def convert(self, value):
        return convert_to_format(value, self._format)

    def reset(self):
        """ Reset state to normal for all targets.

        It will repeat notification if a metric is still failed.

        """
        for target in self.state:
            self.state[target] = "normal"

    def start(self):
        self.callback.start()
        self.load()
        return self

    def stop(self):
        self.callback.stop()
        return self
    def check(self, records):
        work = False
        if datetime.now().time().hour == (self.pastHour+1)%24 and not self.recorded:
             work = True
             self.recorded = True
             self.pastHour = (self.pastHour+1)%24
             #DB call
        elif datetime.now().time().hour == self.pastHour and self.recorded:
            self.recorded = False
        for value, target in records:
            LOGGER.info("%s [%s]: %s", self.name, target, value)
            if value is None:
                self.notify('critical', value, target)
                continue
            if target not in self.historicValues:
                self.historicValues[target] = (value, 1)
            else:
                self.historicValues[target] = (self.historicValues[target][0]+value, self.historicValues[target][1]+1)
            if (self.first or work) and not value is None and target in self.historicValues:
                conn = psycopg2.connect(self.reactor.options.get('database'))
                cur  = conn.cursor()

                ### Pull new history_TOD data by averaging database data ###

                cur.execute("SELECT * FROM history where day >= date %s - integer  \' %s \' AND query LIKE %s;", (str(datetime.now().date()), self.history_TOD_size, target))
                lista = cur.fetchall()
                count = 0
                total = 0
                for item in lista:
                    count += 1
                    total += float(item[1])
                    if count > 0:
                        total /= count
                        self.history_TOD_value[target] = total
                    else:
                        LOGGER.error("No history data for %s" % target)
                conn.commit()
                cur.close()
                conn.close()

            for rule in self.rules:
                rvalue = self.get_value_for_rule(rule, target)
                if rvalue is None:
                    continue
                if rule['op'](value, rvalue):
                    self.notify(rule['level'], value, target, rule=rule)
                    break
            else:
                self.notify('normal', value, target, rule=rule)
            # INSERT DAILY STUFF HERE #

            if work and not value is None and target in self.historicValues:
                conn = psycopg2.connect(self.reactor.options.get('database'))
                cur  = conn.cursor()
                LOGGER.info("datebase call made");

                ### Insert Hourly Data into database ###

                cur.execute("INSERT INTO history (query, value, day, hour) VALUES (%s, %s, %s, %s);", (target, self.historicValues[target][0]/self.historicValues[target][1] , str(datetime.now().date()), str(datetime.now().time().hour)))

                ### If the start of a day, insert average of past day's data into database ###

                if datetime.now().time().hour == 0:
                    cur.execute("SELECT * FROM history WHERE day == date %s - integer \' 1 \'AND query LIKE %s;", (str(datetime.now().date()) ,target))
                    lista = cur.fetchall()
                    count = 0
                    total = 0
                    for item in lista:
                        count += 1
                        total += float(item[1])
                    if count > 0:
                        total /= count
                        cur.execute("INSERT INTO history (query, value, day, hour) VALUES (%s, %s, date %s - integer \' 1 \', %s);",  (target, total , str(datetime.now().date()), 24))

                ### Commit Changes. Database calls done ###

                conn.commit()
                cur.close()
                conn.close()
                del self.historicValues[target]
                #database call#
            self.history[target].append(value)

    def get_value_for_rule(self, rule, target):
        rvalue = rule['value']
        if rvalue == HISTORICAL:
            history = self.history[target]
            if len(history) < self.history_size:
                return None
            rvalue = sum(history) / len(history)
        if rvalue == HISTORICAL_TOD:
            try:
                rvalue = self.history_TOD_value[target]
            except KeyError:
                LOGGER.error("KeyError for %s, No Historical Data" % target)
                rvalue = 0
        rvalue = rule['mod'](rvalue)
        return rvalue

    def notify(self, level, value, target=None, ntype=None, rule=None):
        """ Notify main reactor about event. """

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
        raise NotImplementedError()


class GraphiteAlert(BaseAlert):

    source = 'graphite'

    def configure(self, **options):
        super(GraphiteAlert, self).configure(**options)

        self.method = options.get('method', self.reactor.options['method'])
        assert self.method in METHODS, "Method is invalid"

        self.auth_username = self.reactor.options.get('auth_username')
        self.auth_password = self.reactor.options.get('auth_password')

        query = escape.url_escape(self.query)
        self.url = "%(base)s/render/?target=%(query)s&rawData=true&from=-%(time_window)s" % {
            'base': self.reactor.options['graphite_url'], 'query': query,
            'time_window': self.time_window}
        LOGGER.debug('%s: url = %s' % (self.name, self.url))

    @gen.coroutine
    def load(self):
        LOGGER.debug('%s: start checking: %s' % (self.name, self.query))
        if self.waiting:
            LOGGER.debug('process takes too much time')
        #    self.notify('warning', 'Process takes too much time', target='waiting', ntype='common')
        else:
            self.waiting = True
            try:
                response = yield self.client.fetch(self.url, auth_username=self.auth_username,
                                                   auth_password=self.auth_password,
                                                   request_timeout=self.request_timeout)
                print response
                records = (GraphiteRecord(line.decode('utf-8')) for line in response.buffer)
                data = [(1 if record.empty else getattr(record, self.method), record.target) for record in records]
                print data
                if len(data) == 0:
                    raise ValueError('No data')
                self.check(data)
                self.notify('normal', 'Metrics are loaded', target='loading', ntype='common')
            except Exception as e:
                self.notify('critical', 'Loading error: %s' % e, target='loading', ntype='common')
            self.waiting = False

    def get_graph_url(self, target, graphite_url=None):
        query = escape.url_escape(target)
        return "%(base)s/render/?target=%(query)s&from=-%(time_window)s" % {
            'base': graphite_url or self.reactor.options['graphite_url'], 'query': query,
            'time_window': self.time_window}


class URLAlert(BaseAlert):

    source = 'url'

    @gen.coroutine
    def load(self):
        LOGGER.debug('%s: start checking: %s' % (self.name, self.query))
        if self.waiting:
            self.notify('warning', 'Process takes too much time', target='waiting', ntype='common')
        else:
            self.waiting = True
            try:
                response = yield self.client.fetch(self.query,
                                                   method=self.options.get('method', 'GET'),
                                                   request_timeout=self.request_timeout)
                self.check([(response.code, self.query)])
                self.notify('normal', 'Metrics are loaded', target='loading')

            except Exception as e:
                self.notify('critical', str(e), target='loading')

            self.waiting = False

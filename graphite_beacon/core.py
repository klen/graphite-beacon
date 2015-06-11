import os
from re import compile as re, M

import json
import logging
import psycopg2
from tornado import ioloop, log, web

from .alerts import BaseAlert
from .utils import parse_interval
from .handlers import registry


LOGGER = log.gen_log

COMMENT_RE = re('//\s+.*$', M)



class Reactor(object):
    class UpdateHandler(web.RequestHandler):
        #modify self.options
        #self.options.get('alerts')
        def initialize(self, react):
            self.reactor = react
        #change
        def put(self, arg):
            info = json.loads(self.request.body)
            for i in range(len(self.reactor.options.get('alerts'))):
                if self.reactor.options.get('alerts')[i].get('query').strip() == info.get('query').strip():
                    self.reactor.options.get('alerts')[i] = info
                    print "replaced"
                    break
            else:
                print "nothing happened"
            self.reactor.reinit()
            conn = psycopg2.connect(self.reactor.options.get('database'))
            cur  = conn.cursor()
           # try:
            cur.execute("UPDATE alerts SET name = %s, source = %s, format = %s, interval = %s, history_size = %s, rules = %s WHERE query = %s;", (info['name'], info['source'], info['format'], info['interval'], info['history_size'], ', '.join(info['rules']), info['query']))
            cur.execute("INSERT INTO alerts (query, name, source, format, interval, history_size, rules) SELECT %s, %s, %s, %s, %s, %s, %s WHERE NOT EXISTS (SELECT 1 FROM alerts WHERE query = %s);", (info['query'], info['name'], info['source'], info['format'], info['interval'], info['history_size'], ', '.join(info['rules']), info['query']))
            #except Exception as e:
            #    print e
            #    self.write(e)
            conn.commit()
            cur.close()
            conn.close()
            self.write("All good")
            
        #remove
        def delete(self, arg):
            for i in range(len(self.reactor.options.get('alerts'))):
                if self.reactor.options.get('alerts')[i].get('query') == arg:
                    break
            self.reactor.options.get('alerts').pop(i)
            self.reactor.reinit()
            conn = psycopg2.connect(self.reactor.options.get('database'))
            cur  = conn.cursor()
            try:
                cur.execute("DELETE FROM alerts WHERE query = %s;", (arg,))
            except Exception as e:
                print e
            #    self.write(e)
            conn.commit()
            cur.close()
            conn.close()
            self.write("All good")
        #add new
        def post(self, arg):
            info = json.loads(self.request.body)
            self.reactor.options.get('alerts').append(info)
            self.reactor.reinit()
            conn = psycopg2.connect(self.reactor.options.get('database'))
            cur  = conn.cursor()
            try:
                cur.execute("INSERT INTO alerts (name, query, source, format, interval, history_size, rules) VALUES (%s, %s, %s, %s, %s, %s, %s);", (info['name'], info['query'], info['source'], info['format'], info['interval'], info['history_size'], ', '.join(info['rules'])))
            except Exception as e:
                self.write(e)
            conn.commit()
            cur.close()
            conn.close()
            self.write("All good")
            
        def get(self, arg):
            if arg == "":
                self.write(json.dumps(self.reactor.options))
            else:
                for alert in self.reactor.options.get('alerts'):
                    if alert['query'] == arg:
                        self.write(json.dumps(alert))
                        break
                else:
                    self.write("Query not found")
    """ Class description. """

    defaults = {
        'auth_password': None,
        'auth_username': None,
        'config': 'config.json',
        'critical_handlers': ['log', 'smtp'],
        'debug': False,
        'format': 'short',
        'graphite_url': 'http://localhost',
        'history_size': '1day',
        'interval': '10minute',
        'logging': 'info',
        'method': 'average',
        'normal_handlers': ['log', 'smtp'],
        'pidfile': None,
        'prefix': '[BEACON]',
        'repeat_interval': '2hour',
        'request_timeout': 20.0,
        'send_initial': False,
        'warning_handlers': ['log', 'smtp'],
    }

    def __init__(self, **options):
        self.alerts = set()
        self.loop = ioloop.IOLoop.instance()
        self.options = dict(self.defaults)
        self.reinit(**options)
        conn = psycopg2.connect(self.options.get('database'))
        cur  = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS alerts (query text, name text, source text, format text, interval text, history_size text, rules text);")
        cur.execute("SELECT * FROM alerts;")
        alertList = cur.fetchall()
        if not 'alerts' in self.options:
            self.options['alerts'] = []
        for alert in alertList:
            for i in range(len(self.options.get('alerts'))):
                if alert[0] == self.options.get('alerts')[i].get('query'):
                    self.options.get('alerts').pop(i)
                    self.options.get('alerts').append(dict(query=alert[0], name=alert[1], source=alert[2], format=alert[3], interval=alert[4], history_size=alert[5],rules=alert[6]))
                    break
            else:
                self.options.get('alerts').append(dict(query=alert[0], name=alert[1], source=alert[2], format=alert[3], interval=alert[4], history_size=alert[5],rules=alert[6]))
        conn.commit()
        cur.close()
        conn.close()
        self.options['config'] = 0
        self.callback = ioloop.PeriodicCallback(
            self.repeat, parse_interval(self.options['repeat_interval']))

    def reinit(self, *args, **options):
        LOGGER.info('Read configuration')
        
        # Update this to make DB and config.json fusion more in the way that we want it
        self.options.update(options)
        print "reinit called"
        self.include_config(self.options.get('config'))
        for config in self.options.pop('include', []):
            self.include_config(config)

        LOGGER.setLevel(_get_numeric_log_level(self.options.get('logging', 'info')))
        registry.clean()

        self.handlers = {'warning': set(), 'critical': set(), 'normal': set()}
        self.reinit_handlers('warning')
        self.reinit_handlers('critical')
        self.reinit_handlers('normal')

        for alert in list(self.alerts):
            alert.stop()
            self.alerts.remove(alert)
        for alert in self.options.get('alerts'):
            if not isinstance(alert['rules'], list):
                alert['rules'] = alert['rules'].split(',')
        self.alerts = set(
            BaseAlert.get(self, **opts).start() for opts in self.options.get('alerts', []))

        LOGGER.debug('Loaded with options:')
        LOGGER.debug(json.dumps(self.options, indent=2))
        return self

    def include_config(self, config):
        LOGGER.info('Load configuration: %s' % config)
        if config:
            try:
                with open(config) as fconfig:
                    source = COMMENT_RE.sub("", fconfig.read())
                    config = json.loads(source)
                    self.options.update(config)
            except (IOError, ValueError):
                LOGGER.error('Invalid config file: %s' % config)

    def reinit_handlers(self, level='warning'):
        for name in self.options['%s_handlers' % level]:
            try:
                self.handlers[level].add(registry.get(self, name))
            except Exception as e:
                LOGGER.error('Handler "%s" did not init. Error: %s' % (name, e))

    def repeat(self):
        LOGGER.info('Reset alerts')
        for alert in self.alerts:
            alert.reset()

    def start(self, *args):
        if self.options.get('pidfile'):
            with open(self.options.get('pidfile'), 'w') as fpid:
                fpid.write(str(os.getpid()))
        application = web.Application(
            [
                (r'/(.*)', self.UpdateHandler, dict(react=self))
            ]
        )
        application.listen(3030)
        self.callback.start()
        LOGGER.info('Reactor starts')
        self.loop.start()

    def stop(self, *args):
        self.callback.stop()
        self.loop.stop()
        if self.options.get('pidfile'):
            os.unlink(self.options.get('pidfile'))
        LOGGER.info('Reactor has stopped')

    def notify(self, level, alert, value, target=None, ntype=None, rule=None):
        """ Provide the event to the handlers. """

        LOGGER.info('Notify %s:%s:%s:%s', level, alert, value, target or "")

        if ntype is None:
            ntype = alert.source

        for handler in self.handlers.get(level, []):
            handler.notify(level, alert, value, target=target, ntype=ntype, rule=rule)

_LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARN': logging.WARN,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}


def _get_numeric_log_level(level):
    """Convert a textual log level to the numeric constants expected by the
    :meth:`logging.Logger.setLevel` method.

    This is required for compatibility with Python 2.6 where there is no conversion
    performed by the ``setLevel`` method. In Python 2.7 textual names are converted
    to numeric constants automatically.

    :param basestring name: Textual log level name
    :return: Numeric log level constant
    :rtype: int
    """
    if not isinstance(level, int):
        try:
            return _LOG_LEVELS[str(level).upper()]
        except KeyError:
            raise ValueError("Unknown log level: %s" % level)
    return level

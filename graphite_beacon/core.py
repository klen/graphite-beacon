import os
from re import compile as re, M

import json
import logging
import socket
from time import time, sleep
from tornado import ioloop, log

from .alerts import BaseAlert
from .utils import parse_interval
from .handlers import registry

try:
    import yaml
except ImportError:
    yaml = None


LOGGER = log.gen_log

COMMENT_RE = re('//\s+.*$', M)


class Reactor(object):

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
        'stats_report_interval': '1minute',
        'logging': 'info',
        'method': 'average',
        'no_data': 'critical',
        'normal_handlers': ['log', 'smtp'],
        'pidfile': None,
        'prefix': '[BEACON]',
        'public_graphite_url': None,
        'repeat_interval': '2hour',
        'request_timeout': 20.0,
        'connect_timeout': 20.0,
        'send_initial': False,
        'until': '0second',
        'warning_handlers': ['log', 'smtp'],
        'default_nan_value': 0,
        'ignore_nan': False,
        'loading_error': 'critical',
        'alerts': []
    }

    default_stats = {
        'alerts_reset' : 0,
        'handlers_notified' : 0,
        'critical_handlers_notified' : 0,
        'warning_handlers_notified' : 0,
        'normal_handlers_notified' : 0,
    }


    def __init__(self, **options):
        self.alerts = set()
        self.loop = ioloop.IOLoop.instance()
        self.options = dict(self.defaults)
        self.stats = dict(self.default_stats)
        self.reinit(**options)
        self.callback = ioloop.PeriodicCallback(
            self.repeat, parse_interval(self.options['repeat_interval']))
        self.bumpstats = ioloop.PeriodicCallback(
            self.bump_stats, parse_interval(self.options['stats_report_interval']))

    def reinit(self, *args, **options):
        LOGGER.info('Read configuration')

        self.options.update(options)

        self.include_config(self.options.get('config'))
        for config in self.options.pop('include', []):
            self.include_config(config)

        if not self.options['public_graphite_url']:
            self.options['public_graphite_url'] = self.options['graphite_url']

        LOGGER.setLevel(_get_numeric_log_level(self.options.get('logging', 'info')))
        registry.clean()

        self.handlers = {'warning': set(), 'critical': set(), 'normal': set()}
        self.reinit_handlers('warning')
        self.reinit_handlers('critical')
        self.reinit_handlers('normal')

        for alert in list(self.alerts):
            alert.stop()
            self.alerts.remove(alert)

        self.alerts = set(
            BaseAlert.get(self, **opts).start() for opts in self.options.get('alerts'))

        LOGGER.debug('Loaded with options:')
        LOGGER.debug(json.dumps(self.options, indent=2))
        return self

    def include_config(self, config):
        LOGGER.info('Load configuration: %s' % config)
        if config:
            loader = yaml.load if yaml and config.endswith('.yml') else json.loads
            try:
                with open(config) as fconfig:
                    source = COMMENT_RE.sub("", fconfig.read())
                    config = loader(source)
                    self.options.get('alerts').extend(config.pop("alerts", []))
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
        self.stats['alerts_reset'] = 0

        for alert in self.alerts:
            alert.reset()
            self.stats['alerts_reset'] += 1

    def bump_stats(self):
        hostname = socket.gethostname()
        LOGGER.debug('Bump stats to carbon for host reactor' + hostname)
        for metric in self.stats:
            self.send_graphite_metric('beacon.'+hostname+'.'+metric, self.stats[metric])

    def start(self, *args):
        if self.options.get('pidfile'):
            with open(self.options.get('pidfile'), 'w') as fpid:
                fpid.write(str(os.getpid()))
        self.callback.start()
        LOGGER.info('Reactor starts')
        self.bumpstats.start()
        self.loop.start()

    def stop(self, *args):
        self.callback.stop()
        self.bumpstats.stop()
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
            self.stats[level+'_handlers_notified'] += 1
            self.stats['handlers_notified'] += 1

    def send_graphite_metric(self, name, value):
        if 'carbon_host' in self.options and 'carbon_port' in self.options:
            sock = socket.socket()
            sock.connect((self.options.get('carbon_host'), self.options.get('carbon_port')))
            sock.sendall('%s %s %i\n' % (name, value, time()))
            sock.close()
            return True
    
        return False

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


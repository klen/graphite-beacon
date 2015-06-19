import os
from re import compile as re, M

import json
import logging
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
        'graphite_username': None,
        'graphite_password': None,
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
        self.callback = ioloop.PeriodicCallback(
            self.repeat, parse_interval(self.options['repeat_interval']))

    def reinit(self, *args, **extra_options):
        LOGGER.info('Read configuration')

        options = dict(self.defaults)
        options.update(extra_options)

        self.include_config(options.get('config'))
        for config in options.pop('include', []):
            self.include_config(options, config)

        LOGGER.setLevel(_get_numeric_log_level(options.get('logging', 'info')))

        registry.clean()
        self.handlers = {'warning': set(), 'critical': set(), 'normal': set()}
        self.reinit_handlers(options, 'warning')
        self.reinit_handlers(options, 'critical')
        self.reinit_handlers(options, 'normal')

        for alert in list(self.alerts):
            alert.stop()
            self.alerts.remove(alert)

        self.options = options
        self.alerts = set(BaseAlert.get(self, **opts)
                          for opts in options.get('alerts', []))
        for alert in self.alerts:
            LOGGER.debug('Starting alert %s', alert)
            alert.start()

        LOGGER.debug('Loaded with options:')
        LOGGER.debug(json.dumps(self.options, indent=2))

        return self

    def include_config(self, options, config):
        LOGGER.info('Load configuration: %s' % config)
        if config:
            loader = yaml.load if yaml and config.endswith('.yml') else json.loads
            try:
                with open(config) as fconfig:
                    source = COMMENT_RE.sub("", fconfig.read())
                    config = loader(source)
                    self.options.update(config)
            except (IOError, ValueError):
                LOGGER.error('Invalid config file: %s' % config)

    def reinit_handlers(self, options, level='warning'):
        for name in options['%s_handlers' % level]:
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

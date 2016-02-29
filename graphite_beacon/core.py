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

    def __init__(self, **options):
        self.alerts = set()
        self.loop = ioloop.IOLoop.instance()
        self.options = dict(self.defaults)
        self.reinit(**options)
        self.callback = ioloop.PeriodicCallback(
            self.repeat, parse_interval(self.options['repeat_interval']))

    def reinit(self, *args, **options):
        LOGGER.info('Read configuration')

        self.options.update(options)

        self.include_config(self.options.get('config'))
        for config in self.options.pop('include', []):
            if os.path.isdir(config):
                for chunk in os.listdir(config):
                    LOGGER.info('Processing config chunk:', chunk)
                    self.include_config(os.path.abspath(os.path.join(config, chunk)))
            else:
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
            BaseAlert.get(self, **opts).start() for opts in self.options.get('alerts', [])
        )

        LOGGER.debug('Loaded with options:')
        LOGGER.debug(json.dumps(self.options, indent=2))
        return self

    def include_config(self, config):
        LOGGER.info('Load configuration: %s' % config)
        # Mandatory alarm record fields
        mandatory = ['name', 'query', 'rules', 'format', 'source']

        if config:
            if yaml and (config.endswith('.yml') or config.endswith('.yaml')):
                loader = yaml.load
                LOGGER.info('Loading YAML.')
            else:
                loader = json.loads
                LOGGER.info('Loading JSON.')

            try:
                with open(config) as fconfig:
                    source = COMMENT_RE.sub("", fconfig.read())
                    data = loader(source)
            except (IOError, ValueError), e:
                LOGGER.error('Invalid config file: %s' % config)
            else:
                alerts = self.options.get('alerts', [])
                if not alerts:
                    alert_names = [alert['name'] for alert in alerts]
                else:
                    alert_names = []

                candidates = data.pop("alerts", [])
                if not candidates:
                    LOGGER.error("Config file {} does not contain alerts section, skipping.".format(config))
                else:
                    for item in candidates:
                        field_check = True
                        for field in mandatory:
                            if field not in item.keys():
                                field_check = False
                                LOGGER.error("In config {}, alert is missing mandatory key {}, skipping"
                                             .format(config, field))
                        if field_check:
                            if item['name'] not in alert_names:
                                self.options.get('alerts').append(item)
                                self.options.update(data)

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

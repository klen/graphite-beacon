import sys
import os
from re import compile as re, M

import json
import logging

from tornado import ioloop, log
import yaml

from .alerts import BaseAlert
from .utils import parse_interval
from .handlers import registry


LOGGER = log.gen_log

COMMENT_RE = re(r'//\s+.*$', M)


class Reactor(object):

    """ Class description. """

    defaults = {
        'auth_password': None,
        'auth_username': None,
        'config': None,
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

    def started(self):
        """Check whether the reactor is running.

        :rtype: bool
        """
        return hasattr(self, 'callback') and self.callback.is_running()

    def reinit(self, *args, **options):  # pylint: disable=unused-argument
        LOGGER.info('Read configuration')

        self.options.update(options)

        config_valid = self.include_config(self.options.get('config'))
        for config in self.options.pop('include', []):
            config_valid = config_valid and self.include_config(config)

        # If we haven't started the ioloop yet and config is invalid then fail fast.
        if not self.started() and not config_valid:
            sys.exit(1)

        if not self.options['public_graphite_url']:
            self.options['public_graphite_url'] = self.options['graphite_url']

        LOGGER.setLevel(self.options.get('logging', 'info').upper())
        registry.clean()

        self.handlers = {'warning': set(), 'critical': set(), 'normal': set()}
        self.reinit_handlers('warning')
        self.reinit_handlers('critical')
        self.reinit_handlers('normal')

        for alert in list(self.alerts):
            alert.stop()
            self.alerts.remove(alert)

        self.alerts = set(
            BaseAlert.get(self, **opts).start() for opts in self.options.get('alerts'))  # pylint: disable=no-member

        LOGGER.debug('Loaded with options:')
        LOGGER.debug(json.dumps(self.options, indent=2))
        return self

    def include_config(self, config):
        LOGGER.info('Load configuration: %s' % config)
        if config:
            loader_name, loader = _get_loader(config)
            LOGGER.debug('Using loader: %s' % loader_name)
            if not loader:
                return False
            try:
                with open(config) as fconfig:
                    source = fconfig.read()
                    if loader_name == 'json':
                        source = COMMENT_RE.sub("", source)
                    config = loader(source)
                    self.options.get('alerts').extend(config.pop("alerts", []))
                    self.options.update(config)
            except (IOError, ValueError):
                LOGGER.error('Invalid config file: %s' % config)
                return False
        return True

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

    def start(self, *args):  # pylint: disable=unused-argument
        if self.options.get('pidfile'):
            with open(self.options.get('pidfile'), 'w') as fpid:
                fpid.write(str(os.getpid()))
        self.callback.start()
        LOGGER.info('Reactor starts')
        self.loop.start()

    def stop(self, *args):  # pylint: disable=unused-argument
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


def _get_loader(config):
    """Determine which config file type and loader to use based on a filename.

    :param config str: filename to config file
    :return: a tuple of the loader type and callable to load
    :rtype: (str, Callable)
    """
    if config.endswith('.yml') or config.endswith('.yaml'):
        if not yaml:
            LOGGER.error("pyyaml must be installed to use the YAML loader")
            # TODO: stop reactor if running
            return None, None
        return 'yaml', yaml.load
    else:
        return 'json', json.loads

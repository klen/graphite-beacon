import os
from re import compile as re, M

import json
from tornado import ioloop, log

from .alerts import BaseAlert
from .handlers import registry


LOGGER = log.gen_log

COMMENT_RE = re('//\s+.*$', M)


class Reactor(object):

    """ Class description. """

    defaults = {
        'config': 'config.json',
        'graphite_url': 'http://localhost',
        'auth_username': None,
        'auth_password': None,
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
                    source = COMMENT_RE.sub("", fconfig.read())
                    self.options.update(json.loads(source))
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

        self.alerts = set(
            BaseAlert.get(self, **opts).start() for opts in self.options.get('alerts', []))

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

    def notify(self, level, alert, value, comment=None):
        for handler in self.handlers[level]:
            handler.notify(level, alert, value, comment=comment)

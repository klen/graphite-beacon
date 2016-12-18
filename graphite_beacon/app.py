import os.path
import signal
import sys

from tornado import log
from tornado.options import define, options, print_help

from .core import Reactor


LOGGER = log.gen_log
DEFAULT_CONFIG_PATH = 'config.json'


define('config', default=None, help='Path to a configuration file (JSON/YAML)')
define('pidfile', default=Reactor.defaults['pidfile'], help='Set pid file')
define('graphite_url', default=Reactor.defaults['graphite_url'], help='Graphite URL')


def run():
    options.parse_command_line()

    options_dict = options.as_dict()

    if not options_dict.get('config', None):
        if os.path.isfile(DEFAULT_CONFIG_PATH):
            options_dict['config'] = DEFAULT_CONFIG_PATH
        else:
            LOGGER.error("Config file is required.")
            print_help()
            sys.exit(1)

    reactor = Reactor(**options_dict)

    signal.signal(signal.SIGTERM, reactor.stop)
    signal.signal(signal.SIGINT, reactor.stop)
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, reactor.reinit)

    reactor.start()

if __name__ == '__main__':
    run()

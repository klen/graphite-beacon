import signal

from tornado.options import define, options

from .core import Reactor


define('config', default=Reactor.defaults['config'], help='Path to an configuration file (YAML)')
define('pidfile', default=Reactor.defaults['pidfile'], help='Set pid file')
define('graphite_url', default=Reactor.defaults['graphite_url'], help='Graphite URL')


def run():
    options.parse_command_line()

    r = Reactor(**options.as_dict())

    signal.signal(signal.SIGTERM, r.stop)
    signal.signal(signal.SIGINT, r.stop)
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, r.reinit)

    r.start()

if __name__ == '__main__':
    run()

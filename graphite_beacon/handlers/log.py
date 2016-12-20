from graphite_beacon.handlers import LOGGER, AbstractHandler


class LogHandler(AbstractHandler):

    """Handle events to log output."""

    name = 'log'

    def init_handler(self):
        self.logger = LOGGER

    def notify(self, level, *args, **kwargs):
        message = self.get_short(level, *args, **kwargs)
        if level == 'normal':
            self.logger.info(message)
        elif level == 'warning':
            self.logger.warn(message)
        elif level == 'critical':
            self.logger.error(message)

from . import AbstractHandler, LOGGER


class LogHandler(AbstractHandler):

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

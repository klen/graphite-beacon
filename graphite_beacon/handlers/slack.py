import json
from tornado import gen, httpclient as hc

from . import AbstractHandler, LOGGER


class SlackHandler(AbstractHandler):

    name = 'slack'

    def init_handler(self):
        self.url = self.options.get('url')
        assert self.url, 'URL is not defined'
        self.client = hc.AsyncHTTPClient()

    @gen.coroutine
    def notify(self, level, alert, value, target=None, ntype=None, rule=None):
        LOGGER.debug("Handler (%s) %s", self.name, level)
        message = self.get_short(level, alert, value, target=target, ntype=ntype, rule=rule)
        payload = json.dumps({'text': message})
        yield self.client.fetch(self.url, method="POST", body=payload)



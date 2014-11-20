import urllib
from tornado import gen, httpclient as hc

from . import AbstractHandler, LOGGER


class HttpHandler(AbstractHandler):

    name = 'http'

    # Default options
    defaults = {
        'params': {},
        'method': 'GET',
    }

    def init_handler(self):
        self.url = self.options.get('url')
        assert self.url, 'URL is not defined'
        self.params = self.options['params']
        self.method = self.options['method']
        self.client = hc.AsyncHTTPClient()

    @gen.coroutine
    def notify(self, level, alert, value, target=None, ntype=None, rule=None):
        LOGGER.debug("Handler (%s) %s", self.name, level)

        message = self.get_short(level, alert, value, target=target, ntype=ntype, rule=rule)
        data = {'alert': alert.name, 'desc': message, 'level': level}
        if target:
            data['target'] = target
        if rule:
            data['rule'] = rule['raw']
        data.update(self.params)
        body = urllib.urlencode(data)
        yield self.client.fetch(self.url, method=self.method, body=body)

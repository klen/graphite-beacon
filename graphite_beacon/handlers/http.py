import urllib

from tornado import httpclient as hc
from tornado import gen

from graphite_beacon.handlers import LOGGER, AbstractHandler


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

        if alert.source == 'graphite':
            data['graph_url'] = alert.get_graph_url(target)
            data['value'] = value

        data.update(self.params)
        body = urllib.urlencode(data)
        yield self.client.fetch(self.url, method=self.method, body=body)

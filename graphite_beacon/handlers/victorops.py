import json

from tornado import httpclient as hc
from tornado import gen

from graphite_beacon.handlers import LOGGER, AbstractHandler

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


class VictorOpsHandler(AbstractHandler):

    name = 'victorops'

    def init_handler(self):
        self.url = self.options.get('endpoint')
        assert self.url, 'REST Endpoint is not defined'

        self.routing_key = self.options.get('routing_key', 'everyone')
        
        self.client = hc.AsyncHTTPClient()

    @gen.coroutine
    def notify(self, level, alert, value, target=None, ntype=None, rule=None):
        LOGGER.debug("Handler (%s) %s", self.name, level)
        url = self.url
        routing_key = self.routing_key
        if alert.override and self.name in alert.override:
            override = alert.override[self.name]
            url = override.get('url', url)
            routing_key = override.get('routing_key', routing_key)
            url = urljoin(url, routing_key)

        message = self.get_short(level, alert, value, target=target, ntype=ntype, rule=rule)
        data = {'entity_display_name': alert.name, 'state_message': message, 'message_type': level}
        if target:
            data['target'] = target
        if rule:
            data['rule'] = rule['raw']
        body = json.dumps(data)
        headers = {'Content-Type': 'application/json;'}
        yield self.client.fetch(url, method="POST", body=body, headers=headers)

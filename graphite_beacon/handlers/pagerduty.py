import json

from tornado import httpclient as hc
from tornado import gen

from graphite_beacon.handlers import LOGGER, AbstractHandler


class PagerdutyHandler(AbstractHandler):

    name = 'pagerduty'

    # Default options
    defaults = {
        'subdomain': None,
        'apitoken': None,
        'service_key': None
    }

    def init_handler(self):
        self.subdomain = self.options.get('subdomain')
        assert self.subdomain, 'subdomain is not defined'
        self.apitoken = self.options.get('apitoken')
        assert self.apitoken, 'apitoken is not defined'
        self.service_key = self.options.get('service_key')
        assert self.service_key, 'service_key is not defined'
        self.client = hc.AsyncHTTPClient()

    @gen.coroutine
    def notify(self, level, alert, value, target=None, ntype=None, rule=None):
        LOGGER.debug("Handler (%s) %s", self.name, level)
        message = self.get_short(level, alert, value, target=target, ntype=ntype, rule=rule)
        LOGGER.debug('message1:%s', message)
        if level == 'normal':
            event_type = 'resolve'
        else:
            event_type = 'trigger'

        headers = {
            "Content-type": "application/json",
        }

        client_url = None
        if target:
            client_url = alert.get_graph_url(target)
        incident_key = 'graphite connect error'
        if rule:
            incident_key = "alert={},rule={}".format(alert.name, rule['raw'])

        data = {
            "service_key": self.service_key,
            "event_type": event_type,
            "description": message,
            "details": message,
            "incident_key": incident_key,
            "client": 'graphite-beacon',
            "client_url": client_url
        }
        yield self.client.fetch(
            "https://events.pagerduty.com/generic/2010-04-15/create_event.json",
            body=json.dumps(data),
            headers=headers,
            method='POST'
        )

import json
from tornado import gen, httpclient as hc

from . import AbstractHandler, LOGGER


class PagerdutyHandler(AbstractHandler):

    name = 'pagerduty'

    # Default options
    defaults = {
        'subdomain':  None,
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
        LOGGER.debug('message1:{}'.format(message))
        if level == 'normal':
            event_type = 'resolve'
        else:
            event_type = 'trigger'

        headers = {
            "Content-type": "application/json",
        }

        data = {
            "service_key": self.service_key,
            "event_type": event_type,
            "description": message,
            "details": message,
            "incident_key":  rule['raw'] if rule is not None else 'graphite connect error',
            "client": 'graphite-beacon',
            "client_url": None
        }
        yield self.client.fetch(
            "https://events.pagerduty.com/generic/2010-04-15/create_event.json",
            body=json.dumps(data),
            headers=headers,
            method='POST'
        )

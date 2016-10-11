import json
import hashlib

from tornado import gen, httpclient as hc

from graphite_beacon.handlers import AbstractHandler, LOGGER


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
        LOGGER.debug('message1:%s', message)

	# Extract unique alert identifiers
        alert_name = message[message.find("<")+1:message.find(">")]
        alert_metric = message[message.find("(")+1:message.find(")")]
	
        # Generate hash 
	h = hashlib.md5()
	h.update(alert_name)
	h.update(alert_metric)

        # Use hash as incident key to support resolution
	incident_key = h.hexdigest()

        if level == 'critical':
            event_type = "trigger"
        elif level == 'warning':
            event_type = "trigger"
        elif level == 'normal':
            event_type = "resolve"
        else:
            return

        headers = {
            "Content-type": "application/json",
        }

        data  = {
            "incident_key": incident_key,
            "service_key": self.service_key,
            "description": message,
            "event_type": event_type,
            "description": message,
            "details": message,
            "client": 'graphite-beacon',
            "client_url": None
        }

        yield self.client.fetch(
            "https://events.pagerduty.com/generic/2010-04-15/create_event.json",
            body=json.dumps(data),
            headers=headers,
            method='POST'
	)


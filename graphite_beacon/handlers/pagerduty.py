import pygerduty
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

        pager = pygerduty.PagerDuty(self.subdomain, self.apitoken)
        LOGGER.debug('message:{}'.format(message))
        if level == 'normal':
            pager.resolve_incident(
                service_key=self.service_key,
                incident_key=rule,
                description=message,
                details=message,
            )
        else:
            pager.trigger_incident(
                service_key=self.service_key,
                incident_key=rule,
                description=message,
                details=message,
                client_url='graphite-beacon'
            )

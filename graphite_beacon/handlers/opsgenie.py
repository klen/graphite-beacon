import json
import urllib

from tornado import gen, httpclient

from graphite_beacon.handlers import AbstractHandler


class OpsgenieHandler(AbstractHandler):

    name = 'opsgenie'

    defaults = {
        'api_key': None
    }

    def init_handler(self):
        self.api_key = self.options.get('api_key')
        assert self.api_key, "Opsgenie API key not defined."
        self.client = httpclient.AsyncHTTPClient()

    @gen.coroutine
    def notify(self, level, alert, value, target=None, *args, **kwargs):

        message = self.get_short(level, alert, value, target, *args, **kwargs)
        description = "{url}/composer/?{params}".format(
            url=self.reactor.options['public_graphite_url'],
            params=urllib.urlencode({'target': alert.query}))
        alias = target + ':' + alert.name

        if level == 'critical':
            yield self.client.fetch(
                'https://api.opsgenie.com/v1/json/alert',
                method='POST',
                headers={'Content-Type': 'application/json'},
                body=json.dumps({'apiKey': self.api_key,
                                 'message': message,
                                 'alias': alias,
                                 'description': description}))
        elif level == 'normal':
            # Close issue
            yield self.client.fetch(
                'https://api.opsgenie.com/v1/json/alert/close',
                method='POST',
                headers={'Content-Type': 'application/json'},
                body=json.dumps({'apiKey': self.api_key, 'alias': alias}))
        # TODO: Maybe add option to create alert when level == 'warning'?

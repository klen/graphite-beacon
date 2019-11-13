import json

from tornado import httpclient as hc
from tornado import gen

from graphite_beacon.handlers import LOGGER, AbstractHandler
from graphite_beacon.template import TEMPLATES


class SlackHandler(AbstractHandler):

    name = 'slack'

    # Default options
    defaults = {
        'webhook': None,
        'channel': None,
        'username': 'graphite-beacon',
    }

    emoji = {
        'critical': ':exclamation:',
        'warning': ':warning:',
        'normal': ':white_check_mark:',
    }

    @staticmethod
    def _make_channel_name(channel):
        if channel and not channel.startswith(('#', '@')):
            channel = '#' + channel
        return channel

    def init_handler(self):
        self.webhook = self.options.get('webhook')
        assert self.webhook, 'Slack webhook is not defined.'

        self.channel = self._make_channel_name(self.options.get('channel'))
        self.username = self.options.get('username')
        self.client = hc.AsyncHTTPClient()

    def get_message(self, level, alert, value, target=None, ntype=None, rule=None):  # pylint: disable=unused-argument
        msg_type = 'slack' if ntype == 'graphite' else 'short'
        tmpl = TEMPLATES[ntype][msg_type]
        return tmpl.generate(
            level=level, reactor=self.reactor, alert=alert, value=value, target=target).strip()

    @gen.coroutine
    def notify(self, level, alert, *args, **kwargs):
        LOGGER.debug("Handler (%s) %s", self.name, level)

        channel = self.channel
        username = self.username
        if alert.override and self.name in alert.override:
            override = alert.override[self.name]
            channel = self._make_channel_name(override.get('channel', channel))
            username = override.get('username', username)

        message = self.get_message(level, alert, *args, **kwargs)
        data = dict()
        data['username'] = username
        data['text'] = message
        data['icon_emoji'] = self.emoji.get(level, ':warning:')
        if channel:
            data['channel'] = channel

        body = json.dumps(data)
        yield self.client.fetch(
            self.webhook,
            method='POST',
            headers={'Content-Type': 'application/json'},
            body=body
        )

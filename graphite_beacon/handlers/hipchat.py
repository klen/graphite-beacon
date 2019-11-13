import json

from tornado import httpclient as hc
from tornado import gen

from graphite_beacon.handlers import LOGGER, AbstractHandler


class HipChatHandler(AbstractHandler):

    name = 'hipchat'

    # Default options
    defaults = {
        'url': 'https://api.hipchat.com',
        'room': None,
        'key': None,
    }

    colors = {
        'critical': 'red',
        'warning': 'yellow',
        'normal': 'green',
    }

    def init_handler(self):
        self.room = self.options.get('room')
        self.key = self.options.get('key')
        assert self.room, 'Hipchat room is not defined.'
        assert self.key, 'Hipchat key is not defined.'
        self.client = hc.AsyncHTTPClient()

    @gen.coroutine
    def notify(self, level, alert, *args, **kwargs):
        LOGGER.debug("Handler (%s) %s", self.name, level)

        room = self.room
        if alert.override and self.name in alert.override:
            override = alert.override[self.name]
            room = override.get('room', room)

        data = {
            'message': self.get_short(level, alert, *args, **kwargs).decode('UTF-8'),
            'notify': True,
            'color': self.colors.get(level, 'gray'),
            'message_format': 'text',
        }

        yield self.client.fetch('{url}/v2/room/{room}/notification?auth_token={token}'.format(
            url=self.options.get('url'), room=room, token=self.key), headers={
                'Content-Type': 'application/json'}, method='POST', body=json.dumps(data))

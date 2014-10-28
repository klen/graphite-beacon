import urllib
from tornado import gen, httpclient as hc

from . import AbstractHandler


class HipChatHandler(AbstractHandler):

    name = 'hipchat'

    # Default options
    defaults = {
        'room': None,
        'key': None,
    }

    colors = {
        'critical': 'red',
        'warning': 'magenta',
        'normal': 'green',
    }

    def init_handler(self):
        self.room = self.options.get('room')
        self.key = self.options.get('key')
        assert self.room, 'Hipchat room is not defined.'
        assert self.key, 'Hipchat key is not defined.'
        self.client = hc.AsyncHTTPClient()

    @gen.coroutine
    def notify(self, level, *args, **kwargs):
        message = self.get_short(level, *args, **kwargs)
        data = {
            'room_id': self.room,
            'from': self.prefix,
            'message': message,
            'notify': 1,
            'color': self.colors.get(level, 'blue'),
            'message_format': 'text',
        }
        body = urllib.urlencode(data)
        yield self.client.fetch('https://api.hipchat.com/v1/rooms/message?auth_token=' + self.key,
                                method='POST', body=body)

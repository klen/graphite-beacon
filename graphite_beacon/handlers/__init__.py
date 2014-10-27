from tornado import log, template
import os.path as op

from .. import _compat as _

LOADER = template.Loader(op.join(op.dirname(op.abspath(__file__)), 'templates'), autoescape=None)
TEMPLATES = {
    'graphite': {
        'html': LOADER.load('graphite/message.html'),
        'text': LOADER.load('graphite/message.txt'),
        'short': LOADER.load('graphite/short.txt'),
    },
    'url': {
        'html': LOADER.load('url/message.html'),
        'text': LOADER.load('url/message.txt'),
        'short': LOADER.load('url/short.txt'),
    },
    'common': {
        'html': LOADER.load('common/message.html'),
        'text': LOADER.load('common/message.txt'),
        'short': LOADER.load('common/short.txt'),
    },
}

LOGGER = log.gen_log


class HandlerMeta(type):

    loaded = {}
    handlers = {}

    def __new__(mcs, name, bases, params):
        cls = super(HandlerMeta, mcs).__new__(mcs, name, bases, params)
        name = params.get('name')
        if name:
            mcs.handlers[name] = cls
            LOGGER.info("Register Handler: %s" % name)
        return cls

    @classmethod
    def clean(mcs):
        mcs.loaded = {}

    @classmethod
    def get(mcs, reactor, name):
        if name not in mcs.loaded:
            mcs.loaded[name] = mcs.handlers[name](reactor)
        return mcs.loaded[name]


class AbstractHandler(_.with_metaclass(HandlerMeta)):

    name = None

    def __init__(self, reactor):
        self.reactor = reactor
        self.prefix = self.reactor.options.get('prefix', '')
        self.init_handler()

    def get_short(self, level, alert, value, target=None, ntype=None):
        tmpl = TEMPLATES[ntype]['short']
        return tmpl.generate(
            level=level, reactor=self.reactor, alert=alert, value=value, target=target).strip()

    def init_handler(self):
        """ Init configuration here."""
        raise NotImplementedError()

    def notify(self, level, alert, value, target=None, ntype=None):
        raise NotImplementedError()

registry = HandlerMeta

from .log import LogHandler # noqa
from .smtp import SMTPHandler # noqa
from .hipchat import HipChatHandler # noqa

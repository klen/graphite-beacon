from tornado import log

from .. import _compat as _
from ..template import TEMPLATES

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
    defaults = {}

    def __init__(self, reactor):
        self.reactor = reactor
        self.options = dict(self.defaults)
        self.options.update(self.reactor.options.get(self.name, {}))
        self.init_handler()
        LOGGER.debug('Handler "%s" has inited: %s', self.name, self.options)

    def get_short(self, level, alert, value, target=None, ntype=None, rule=None):
        tmpl = TEMPLATES[ntype]['short']
        return tmpl.generate(
            level=level, reactor=self.reactor, alert=alert, value=value, target=target).strip()

    def init_handler(self):
        """ Init configuration here."""
        raise NotImplementedError()

    def notify(self, level, alert, value, target=None, ntype=None, rule=None):
        raise NotImplementedError()

registry = HandlerMeta

from .hipchat import HipChatHandler      # noqa
from .http import HttpHandler            # noqa
from .log import LogHandler              # noqa
from .pagerduty import PagerdutyHandler  # noqa
from .slack import SlackHandler          # noqa
from .smtp import SMTPHandler            # noqa
from .cli import CliHandler              # noqa
from .opsgenie import OpsgenieHandler    # noqa

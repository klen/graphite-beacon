from tornado import log, gen, concurrent, httpclient as hc
import urllib

from . import _compat as _
from smtplib import SMTP
from email.mime.text import MIMEText as text


class HandlerMeta(type):

    loaded = {}
    handlers = {}

    def __new__(mcs, name, bases, params):
        cls = super(HandlerMeta, mcs).__new__(mcs, name, bases, params)
        name = params.get('name')
        if name:
            mcs.handlers[name] = cls
            log.gen_log.info("Register Handler: %s" % name)
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

    templates = {
        'critical': "%(prefix)s %(level)s: %(alert)s failed. Current value: %(value)s",
        'warning': "%(prefix)s %(level)s: %(alert)s failed. Current value: %(value)s",
        'normal': "%(prefix)s %(alert)s is back to normal. Current value: %(value)s",
    }

    def __init__(self, reactor):
        self.reactor = reactor
        self.prefix = self.reactor.options.get('prefix', '')
        self.init_handler()

    def get_message(self, level, alert, value, comment=None):
        tmpl = self.templates.get(level)
        return tmpl % {
            'prefix': self.prefix, 'level': level.upper(), 'alert': alert.name, 'value': value}

    def init_handler(self):
        """ Init configuration here."""
        raise NotImplementedError()

    def notify(self, level, alert, value, comment=None):
        raise NotImplementedError()


class LogHandler(AbstractHandler):

    name = 'log'

    def init_handler(self):
        self.logger = log.gen_log

    def notify(self, level, *args, **kwargs):
        message = self.get_message(level, *args, **kwargs)
        if level == 'normal':
            self.logger.info(message)
        elif level == 'warning':
            self.logger.warn(message)
        elif level == 'critical':
            self.logger.error(message)


class SmtpHandler(AbstractHandler):

    name = 'smtp'

    def init_handler(self):
        self._from = self.reactor.options.get('smtp_from', 'beacon@graphite')
        self.host = self.reactor.options.get('smtp_host', 'smtp.gmail.com')
        self.password = self.reactor.options.get('smtp_password')
        self.port = self.reactor.options.get('smtp_port', 587)
        self.use_tls = self.reactor.options.get('smtp_use_tls', True)
        self.username = self.reactor.options.get('smtp_username')
        self.to = self.reactor.options.get('smtp_to')
        assert self.to, 'Recepients list is empty. SMTP disabled.'

    @gen.coroutine
    def notify(self, level, alert, value, comment):
        msg = text('%s %s value is %s' % (comment, alert.method, value))
        msg['Subject'] = self.get_message(level, alert, value)
        msg['From'] = self._from
        msg['To'] = ", ".join(self.to)
        smtp = SMTP()
        yield smtp_connect(smtp, self.host, self.port)

        if self.use_tls:
            yield smtp_starttls(smtp)

        if self.username and self.password:
            yield smtp_login(smtp, self.username, self.password)

        try:
            log.gen_log.debug(msg)
            smtp.sendmail(self._from, self.to, msg.as_string())
        finally:
            smtp.quit()


@concurrent.return_future
def smtp_connect(smtp, host, port, callback):
    callback(smtp.connect(host, port))


@concurrent.return_future
def smtp_starttls(smtp, callback):
    callback(smtp.starttls())


@concurrent.return_future
def smtp_login(smtp, username, password, callback):
    callback(smtp.login(username, password))


class HipChatHandler(AbstractHandler):

    name = 'hipchat'
    colors = {
        'critical': 'red',
        'warning': 'magenta',
        'normal': 'green',
    }

    def init_handler(self):
        self.room = self.reactor.options['hipchat_room']
        self.key = self.reactor.options['hipchat_key']
        self.client = hc.AsyncHTTPClient()

    @gen.coroutine
    def notify(self, level, alert, value, comment=None):
        message = self.get_message(level, alert, value)
        data = {
            'room_id': self.room,
            'from': self.prefix,
            'message': message,
            'notify': 1,
            'color': self.colors.get(level, 'blue'),
            'message_format': 'text',
        }
        body = urllib.urlencode(data)
        yield self.client.fetch(
            'https://api.hipchat.com/v1/rooms/message?auth_token=' + self.key,
            method='POST', body=body)

registry = HandlerMeta

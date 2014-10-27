from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from smtplib import SMTP
from tornado import log, gen, concurrent
import datetime as dt

from . import AbstractHandler, TEMPLATES


class SMTPHandler(AbstractHandler):

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
    def notify(self, *args, **kwargs):
        msg = self.get_message(*args, **kwargs)
        msg['Subject'] = self.get_short(*args, **kwargs)
        msg['From'] = self._from
        msg['To'] = ", ".join(self.to)

        smtp = SMTP()
        yield smtp_connect(smtp, self.host, self.port)

        if self.use_tls:
            yield smtp_starttls(smtp)

        if self.username and self.password:
            yield smtp_login(smtp, self.username, self.password)

        try:
            log.gen_log.debug("Send message to: %s" % ", ".join(self.to))
            smtp.sendmail(self._from, self.to, msg.as_string())
        finally:
            smtp.quit()

    def get_message(self, level, alert, value, target=None, ntype=None):
        html_tmpl = TEMPLATES[ntype]['html']
        txt_tmpl = TEMPLATES[ntype]['text']
        ctx = {'reactor': self.reactor, 'alert': alert, 'value': value, 'level': level,
               'target': target, 'dt': dt}
        msg = MIMEMultipart('alternative')
        plain = MIMEText(txt_tmpl.generate(**ctx), 'plain')
        html = MIMEText(html_tmpl.generate(**ctx), 'html')
        msg.attach(plain)
        msg.attach(html)
        return msg


@concurrent.return_future
def smtp_connect(smtp, host, port, callback):
    callback(smtp.connect(host, port))


@concurrent.return_future
def smtp_starttls(smtp, callback):
    callback(smtp.starttls())


@concurrent.return_future
def smtp_login(smtp, username, password, callback):
    callback(smtp.login(username, password))

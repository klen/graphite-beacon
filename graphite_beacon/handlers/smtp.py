import datetime as dt

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP
from tornado import gen, concurrent

from . import AbstractHandler, TEMPLATES, LOGGER


class SMTPHandler(AbstractHandler):

    name = 'smtp'

    # Default options
    defaults = {
        'host': 'localhost',
        'port': 25,
        'username': None,
        'password': None,
        'from': 'beacon@graphite',
        'to': None,
        'use_tls': False,
        'html': True,
    }

    def init_handler(self):
        """ Check self options. """
        assert self.options.get('host') and self.options.get('port'), "Invalid options"
        assert self.options.get('to'), 'Recepients list is empty. SMTP disabled.'
        if not isinstance(self.options['to'], (list, tuple)):
            self.options['to'] = [self.options['to']]

    @gen.coroutine
    def notify(self, *args, **kwargs):
        msg = self.get_message(*args, **kwargs)
        msg['Subject'] = self.get_short(*args, **kwargs)
        msg['From'] = self.options['from']
        msg['To'] = ", ".join(self.options['to'])

        smtp = SMTP()
        yield smtp_connect(smtp, self.options['host'], self.options['port'])

        if self.options['use_tls']:
            yield smtp_starttls(smtp)

        if self.options['username'] and self.options['password']:
            yield smtp_login(smtp, self.options['username'], self.options['password'])

        try:
            LOGGER.debug("Send message to: %s" % ", ".join(self.options['to']))
            smtp.sendmail(self.options['from'], self.options['to'], msg.as_string())
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

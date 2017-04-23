from graphite_beacon.alerts import BaseAlert
from graphite_beacon.handlers.smtp import SMTPHandler


def test_html_template(reactor):
    target = 'node.com'
    galert = BaseAlert.get(reactor, name='Test', query='*', rules=["normal: == 0"])
    galert.history[target] += [1, 2, 3, 4, 5]

    reactor.options['smtp'] = {
        'to': 'user@com.com', 'graphite_url': 'http://graphite.myhost.com'}
    smtp = SMTPHandler(reactor)

    message = smtp.get_message(
        'critical', galert, 3000000, target=target, ntype='graphite', rule=galert.rules[0])
    assert message.as_string()

    assert len(message._payload) == 2
    text, html = message._payload
    assert 'graphite.myhost.com' in html.as_string()

    ualert = BaseAlert.get(
        reactor, source='url', name='Test', query='http://google.com', rules=["critical: != 200"])
    message = smtp.get_message('critical', ualert, '3000000', target, 'url')
    assert message.as_string()

    assert len(message._payload) == 2
    _, html = message._payload
    assert 'google.com' in html.as_string()

    ealert = BaseAlert.get(reactor, name='Test', query='*', rules=["critical: > 5 AND < 10"])
    message = smtp.get_message(
        'critical', ealert, 8, target=target, ntype='graphite', rule=ealert.rules[0])
    assert message.as_string()

    assert len(message._payload) == 2

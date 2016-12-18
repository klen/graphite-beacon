from graphite_beacon.core import Reactor


def test_reactor():
    rr = Reactor()
    assert rr
    assert rr.reinit()

    rr = Reactor(include=['examples/example-config.json'], alerts=[
        {'name': 'test', 'query': '*', 'rules': ["normal: == 0"]}])
    assert rr.options['interval'] == '20minute'
    assert len(rr.alerts) == 3

    rr = Reactor(include=['examples/example-config.yml'], alerts=[
        {'name': 'test', 'query': '*', 'rules': ["normal: == 0"]}])
    assert rr.options['interval'] == '20minute'
    assert len(rr.alerts) == 3


def test_public_graphite_url():
    rr = Reactor(graphite_url='http://localhost', public_graphite_url=None)
    rr.reinit()
    assert rr.options.get("public_graphite_url") == 'http://localhost'

    rr.reinit(public_graphite_url="http://public")
    assert rr.options.get("public_graphite_url") == "http://public"


def test_invalid_handler(reactor):
    reactor.reinit(critical_handlers=['log', 'unknown'])
    assert len(reactor.handlers['critical']) == 1

import mock
import tornado.gen
from mock import ANY
from tornado import ioloop
from tornado.httpclient import HTTPRequest, HTTPResponse
from tornado.testing import AsyncTestCase, gen_test

from graphite_beacon.alerts import URLAlert
from graphite_beacon.core import Reactor
from graphite_beacon._compat import StringIO

from ..util import build_graphite_response

fetch_mock_url = lambda m: m.call_args_list[0][0][0]


class TestGraphite(AsyncTestCase):

    target_url = 'http://localhost/check'

    def get_new_ioloop(self):
        return ioloop.IOLoop.instance()

    @mock.patch('graphite_beacon.alerts.hc.AsyncHTTPClient.fetch')
    @mock.patch('graphite_beacon.handlers.smtp.SMTPHandler.notify')
    @gen_test
    def test_graphite(self, mock_smpt_notify, mock_fetch):
        self.reactor = Reactor(
            alerts=[
                {
                    'name': 'test',
                    'source': 'url',
                    'query': self.target_url,
                    'rules': ['warning: != 200']
                }
            ],
            smtp={
                'from': 'graphite@localhost',
                'to': ['alerts@localhost'],
            },
            interval='0.25second',
        )

        assert not self.reactor.is_running()

        alert = list(self.reactor.alerts)[0]
        assert len(self.reactor.alerts) == 1
        assert isinstance(alert, URLAlert)

        metric_data = [5, 7, 9]
        build_resp = lambda: HTTPResponse(HTTPRequest(self.target_url), 500,
                                          buffer=StringIO(''))

        mock_fetch.side_effect = iter(tornado.gen.maybe_future(build_resp())
                                      for _ in range(10))

        self.reactor.start(start_loop=False)
        yield tornado.gen.sleep(0.5)

        # There should be at least 1 immediate fetch + 1 instance of the PeriodicCallback
        assert mock_fetch.call_count >= 2
        assert fetch_mock_url(mock_fetch) == self.target_url

        assert alert.state[self.target_url] == 'warning'
        assert mock_smpt_notify.call_count == 1
        mock_smpt_notify.assert_called_once_with(
            'warning',
            alert,
            500.0,
            ntype='url',
            rule=ANY,
            target=self.target_url)

        self.reactor.stop(stop_loop=False)

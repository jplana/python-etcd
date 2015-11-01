import etcd
import unittest
import urllib3
import json
try:
    import mock
except ImportError:
    from unittest import mock


class TestClientApiBase(unittest.TestCase):

    def setUp(self):
        self.client = etcd.Client()

    def _prepare_response(self, s, d, cluster_id=None):
        if isinstance(d, dict):
            data = json.dumps(d).encode('utf-8')
        else:
            data = d.encode('utf-8')

        r = mock.create_autospec(urllib3.response.HTTPResponse)()
        r.status = s
        r.data = data
        r.getheader.return_value = cluster_id or "abcd1234"
        return r

    def _mock_api(self, status, d, cluster_id=None):
        resp = self._prepare_response(status, d, cluster_id=cluster_id)
        self.client.api_execute = mock.MagicMock(return_value=resp)

    def _mock_exception(self, exc, msg):
        self.client.api_execute = mock.Mock(side_effect=exc(msg))

import etcd
import unittest
import json
import urllib3

try:
    import mock
except ImportError:
    from unittest import mock

from etcd import EtcdException


class TestClientApiInterface(unittest.TestCase):

    def setUp(self):
        self.client = etcd.Client()

    def _prepare_response(self, s, d):
        if isinstance(d, dict):
            data = json.dumps(d).encode('utf-8')
        else:
            data = d.encode('utf-8')

        r = mock.create_autospec(urllib3.response.HTTPResponse)()
        r.status = s
        r.data = data
        return r

    def _mock_api(self, status, d):
        resp = self._prepare_response(status, d)
        self.client.api_execute = mock.create_autospec(
            self.client.api_execute, return_value=resp)

    def _mock_exception(self, exc, msg):
        self.client.api_execute = mock.Mock(side_effect=exc(msg))

    def test_machines(self):
        """ Can request machines """
        data = ['http://127.0.0.1:4001',
                'http://127.0.0.1:4002', 'http://127.0.0.1:4003']
        d = ','.join(data)
        self._mock_api(200, d)
        self.assertEquals(data, self.client.machines)

    def test_leader(self):
        """ Can request the leader """
        data = "http://127.0.0.1:4001"
        self._mock_api(200, data)
        self.assertEquals(self.client.leader, data)

    def test_set_plain(self):
        """ Can set a value """
        d = {u'action': u'set',
             u'expiration': u'2013-09-14T00:56:59.316195568+02:00',
             u'modifiedIndex': 183,
             u'key': u'/testkey',
             u'ttl': 19,
             u'value': u'test'}

        self._mock_api(200, d)
        res = self.client.write('/testkey', 'test')
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_newkey(self):
        """ Can set a new value """
        d = {u'action': u'set',
             u'expiration': u'2013-09-14T00:56:59.316195568+02:00',
             u'modifiedIndex': 183,
             u'key': u'/testkey',
             u'ttl': 19,
             u'value': u'test'}

        self._mock_api(201, d)
        d['newKey'] = True
        res = self.client.write('/testkey', 'test')
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_compare_and_swap(self):
        """ Can set compare-and-swap a value """
        d = {u'action': u'compareAndSwap',
             u'expiration': u'2013-09-14T00:56:59.316195568+02:00',
             u'modifiedIndex': 183,
             u'key': u'/testkey',
             'prevValue': 'test_old',
             u'ttl': 19,
             u'value': u'test'}

        self._mock_api(200, d)
        res = self.client.write('/testkey', 'test', prevValue='test_old')
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_compare_and_swap_failure(self):
        """ Exception will be raised if prevValue != value in test_set """
        self._mock_exception(ValueError, 'Test Failed : [ 1!=3 ]')
        self.assertRaises(
            ValueError,
            self.client.write,
            '/testKey',
            'test',
            prevValue='oldbog'
        )

    def test_delete(self):
        """ Can delete a value """
        d = {
            u'action': u'delete',
            u'key': u'/testkey',
        }
        self._mock_api(200, d)
        res = self.client.delete('/testKey')
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_read(self):
        """ Can get a value """
        d = {
            u'action': u'get',
            u'modifiedIndex': 190,
            u'key': u'/testkey',
            u'value': u'test'
        }
        self._mock_api(200, d)
        res = self.client.read('/testKey')
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_get_dir(self):
        """Can get values in dirs"""
        d = {
            u'action': u'get',
            u'modifiedIndex': 190,
            u'key': u'/testkey',
            u'dir': True,
            u'kvs': [
                {
                    u'key': u'/testDir/testKey',
                    u'modifiedIndex': 150,
                    u'value': 'test'
                },
                {
                    u'key': u'/testDir/testKey2',
                    u'modifiedIndex': 190,
                    u'value': 'test2'
                }
            ]
        }
        self._mock_api(200, d)
        res = self.client.read('/testDir', recursive=True)
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_not_in(self):
        """ Can check if key is not in client """
        self._mock_exception(KeyError, 'Key not Found : /testKey')
        self.assertTrue('/testey' not in self.client)

    def test_in(self):
        """ Can check if key is not in client """
        d = {
            u'action': u'get',
            u'modifiedIndex': 190,
            u'key': u'/testkey',
            u'value': u'test'
        }
        self._mock_api(200, d)
        self.assertTrue('/testey' in self.client)

    def test_watch(self):
        """ Can watch a key """
        d = {
            u'action': u'get',
            u'modifiedIndex': 190,
            u'key': u'/testkey',
            u'value': u'test'
        }
        self._mock_api(200, d)
        res = self.client.read('/testkey', wait=True)
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_watch_index(self):
        """ Can watch a key starting from the given Index """
        d = {
            u'action': u'get',
            u'modifiedIndex': 170,
            u'key': u'/testkey',
            u'value': u'testold'
        }
        self._mock_api(200, d)
        res = self.client.read('/testkey', wait=True, waitIndex=True)
        self.assertEquals(res, etcd.EtcdResult(**d))


class TestClientRequest(TestClientApiInterface):

    def setUp(self):
        self.client = etcd.Client()

    def _mock_api(self, status, d):
        resp = self._prepare_response(status, d)
        self.client.http.request_encode_body = mock.create_autospec(
            self.client.http.request_encode_body, return_value=resp
        )
        self.client.http.request = mock.create_autospec(
            self.client.http.request, return_value=resp
        )

    def _mock_error(self, error_code, msg, cause, method='PUT', fields=None):
        resp = self._prepare_response(
            500,
            {'errorCode': error_code, 'message': msg, 'cause': cause}
        )
        self.client.http.request_encode_body = mock.create_autospec(
            self.client.http.request_encode_body, return_value=resp
        )
        self.client.http.request = mock.create_autospec(
            self.client.http.request, return_value=resp
        )

    def test_compare_and_swap_failure(self):
        """ Exception will be raised if prevValue != value in test_set """
        self._mock_error(200, 'Test Failed',
                         '[ 1!=3 ]', fields={'prevValue': 'oldbog'})
        self.assertRaises(
            ValueError,
            self.client.write,
            '/testKey',
            'test',
            prevValue='oldbog'
        )

    def test_not_in(self):
        pass

    def test_in(self):
        pass

import etcd
import unittest

from .test_request import TestClientApiBase

try:
    import mock
except ImportError:
    from unittest import mock

class EtcdLeaderElectionTestCase(TestClientApiBase):
    def setUp(self):
        self.client = etcd.Client()

    def _mock_api(self, status, d):
        #We want to test at a lower level here.
        resp = self._prepare_response(status, d)
        self.client.http.request_encode_body = mock.create_autospec(
            self.client.http.request_encode_body, return_value=resp
        )
        self.client.http.request = mock.create_autospec(
            self.client.http.request, return_value=resp
        )


    def test_get_leader(self):
        """ Can fetch a leader value """
        self._mock_api(200, 'foo.example.com')
        self.assertEquals(self.client.election.get('/mysql'), 'foo.example.com')
        self._mock_api(200,'')
        self.assertRaises(etcd.EtcdException, self.client.election.get, '/mysql')

    def test_set_leader(self):
        """ Can set a leader value """
        self._mock_api(200, u'234')
        #set w/o a TTL or a name
        self.assertEquals(self.client.election.set('/mysql'), u'234')
        self.assertEquals(self.client.election.set(
            '/mysql',
            name='foo.example.com',
            ttl=60), u'234')
        self._mock_api(500, 'leader name required')
        self.assertRaises(etcd.EtcdException, self.client.election.set,'/mysql')

    def test_del_leader(self):
        """ Can remove a leader value """
        self._mock_api(200,'')
        self.assertTrue(self.client.election.delete('/mysql'))

import etcd
from . import test_simple
import time
import unittest

class TestElection(test_simple.EtcdIntegrationTest):
    def setUp(self):
        self.client = etcd.Client(port=6001)

    def test_set_get_delete(self):
        e = self.client.election
        res = e.set('/mysql', name='foo.example.com', ttl=30)
        self.assertTrue(res != '')
        res = e.get('/mysql')
        self.assertEquals(res, 'foo.example.com')
        self.assertTrue(e.delete('/mysql', name='foo.example.com'))


    def test_set_invalid_ttl(self):
        self.assertRaises(etcd.EtcdException, self.client.election.set, '/mysql', name='foo.example.com', ttl='ciao')

    @unittest.skip
    def test_get_non_existing(self):
        """This is actually expected to fail. See https://github.com/coreos/etcd/issues/446"""
        self.assertRaises(etcd.EtcdException, self.client.election.get, '/foobar')

    def test_delete_non_existing(self):
        self.assertRaises(etcd.EtcdException, self.client.election.delete, '/foobar')

    def test_get_delete_after_ttl_expired_raises(self):
        e = self.client.election
        e.set('/mysql', name='foo', ttl=1)
        time.sleep(2)
        self.assertRaises(etcd.EtcdException, e.get, '/mysql')
        self.assertRaises(etcd.EtcdException, e.delete, '/mysql', name='foo')

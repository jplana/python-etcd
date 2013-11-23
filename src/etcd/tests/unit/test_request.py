import etcd
import unittest
import json
import mox
import urllib3

from etcd import EtcdException

class TestClientV2ApiInterface(mox.MoxTestBase):

    def setUp(self):
        mox.MoxTestBase.setUp(self)
        self.client = etcd.Client()
        self.mox.StubOutWithMock(self.client, 'api_execute')


    def _prepare_response(self, status, d):
        r = self.mox.CreateMock(urllib3.response.HTTPResponse)
        r.status = status
        if isinstance(d, dict):
            r.data = json.dumps(d)
        else:
            r.data = d
        return r


    def _mock_write(self, status, d):
        resp = self._prepare_response(status, d)
        self.client.api_execute(mox.IsA(str),self.client._MPUT,
                                mox.IsA(dict)).AndReturn(resp)

    def _mock_get(self, status, d):
        resp = self._prepare_response(status, d)
        self.client.api_execute(
            mox.IsA(str),
            self.client._MGET,
            mox.Or(mox.IsA(dict), mox.IsA(None))
        ).AndReturn(resp)

    def _mock_get_plain(self, status, d):
        resp = self._prepare_response(status, d)
        self.client.api_execute(
            mox.IsA(str),
            self.client._MGET
        ).AndReturn(resp)

    def _mock_delete(self, status, d):
        resp = self._prepare_response(status, d)
        self.client.api_execute(
            mox.IsA(str),
            self.client._MDELETE
        ).AndReturn(resp)


    def _mock_exception(self, exc, msg):
        self.client.api_execute(
            mox.IgnoreArg(),
            mox.IgnoreArg(),
            mox.IgnoreArg()
#            params = mox.Or(mox.IsA(dict), mox.IsA(None))
        ).AndRaise(exc(msg))

    def test_machines(self):
        """ Can request machines """
        data = ['http://127.0.0.1:4001','http://127.0.0.1:4002','http://127.0.0.1:4003']
        d = ','.join(data)
        self._mock_get_plain(200,d)
        self.mox.ReplayAll()
        self.assertEquals(data, self.client.machines)

    def test_leader(self):
        """ Can request the leader """
        data = "http://127.0.0.1:4001"
        self._mock_get_plain(200, data)
        self.mox.ReplayAll()
        self.assertEquals(self.client.leader, data)

    #test writes
    def test_set_plain(self):
        d = {u'action': u'set',
             u'expiration': u'2013-09-14T00:56:59.316195568+02:00',
             u'modifiedIndex': 183,
             u'key': u'/testkey',
             u'ttl': 19,
             u'value': u'test'}

        self._mock_write(200, d)
        self.mox.ReplayAll()
        res = self.client.write('/testkey', 'test')
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_newkey(self):
        d = {u'action': u'set',
             u'expiration': u'2013-09-14T00:56:59.316195568+02:00',
             u'modifiedIndex': 183,
             u'key': u'/testkey',
             u'ttl': 19,
             u'value': u'test'}

        self._mock_write(201, d)
        self.mox.ReplayAll()
        d['newKey'] = True
        res = self.client.write('/testkey', 'test')
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_compare_and_swap(self):
        d = {u'action': u'compareAndSwap',
             u'expiration': u'2013-09-14T00:56:59.316195568+02:00',
             u'modifiedIndex': 183,
             u'key': u'/testkey',
             'prevValue': 'test_old',
             u'ttl': 19,
             u'value': u'test'}

        self._mock_write(200,d)
        self.mox.ReplayAll()
        res = self.client.write('/testkey', 'test', prevValue = 'test_old')
        self.assertEquals(res, etcd.EtcdResult(**d))
        self.mox.UnsetStubs()
        self.mox.VerifyAll()

    def test_compare_and_swap_existence(self):
        d = {
            u'action': u'compareAndSwap',
            u'expiration': u'2013-09-14T00:56:59.316195568+02:00',
            u'modifiedIndex': 183,
            u'key': u'/testkey',
            u'ttl': 19,
            u'value': u'test'
        }
        self._mock_write(200,d)
        self.mox.ReplayAll()
        res = self.client.write('/testkey', 'test', prevExists = True)
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_compare_and_swap_failure(self):
        """ Exception will be raised if prevValue != value in test_set """
        self._mock_exception(ValueError,'Test Failed : [ 1!=3 ]')
        self.mox.ReplayAll()
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
        self._mock_delete(200, d)
        self.mox.ReplayAll()
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
        self._mock_get(200,d)
        self.mox.ReplayAll()
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
        self._mock_get(200,d)
        self.mox.ReplayAll()
        res = self.client.read('/testDir', recursive = True)
        self.assertEquals(res, etcd.EtcdResult(**d))


class TestClientV2Request(TestClientV2ApiInterface):

    def setUp(self):
        mox.MoxTestBase.setUp(self)
        self.client = etcd.Client()
        self.mox.StubOutWithMock(self.client.http, 'request')
        self.mox.StubOutWithMock(self.client.http, 'request_encode_body')

    def _mock_write(self, status, d):
        resp = self._prepare_response(status, d)
        self.client.http.request_encode_body(
            self.client._MPUT, mox.IsA(str),
            encode_multipart=mox.IsA(bool),
            redirect=mox.IsA(bool),
            fields=mox.IsA(dict)
        ).AndReturn(resp)

    def _mock_get(self, status, data):
        resp = self._prepare_response(status, data)
        self.client.http.request(
            self.client._MGET, mox.IsA(str),
            redirect=mox.IsA(bool),
            fields=mox.Or(mox.IsA(dict),mox.IsA(None))
        ).AndReturn(resp)

    def _mock_get_plain(self, status, data):
        return self._mock_get(status, data)

    def _mock_error(self, error_code, msg, cause, method='PUT', fields=None):
        resp = self._prepare_response(
            500,
            {'errorCode': error_code,'message': msg, 'cause': cause}
        )
        kwds = {'redirect': mox.IsA(bool), 'fields': mox.IsA(type(fields))}
        if method == 'PUT':
            kwds['encode_multipart'] = mox.IsA(bool)
            self.client.http.request_encode_body(
                method,
                mox.IsA(str),
                **kwds
            ).AndReturn(resp)
        else:
            self.client.http.request(
                method,
                mox.IsA(str),
                **kwds
            ).AndReturn(resp)

    def _mock_delete(self, status, data):
        resp = self._prepare_response(status, data)
        self.client.http.request(
            self.client._MDELETE, mox.IsA(str),
            redirect=mox.IsA(bool),
            fields=mox.Or(mox.IsA(dict),mox.IsA(None))
        ).AndReturn(resp)


    def test_compare_and_swap_failure(self):
        """ Exception will be raised if prevValue != value in test_set """
        self._mock_error(200, 'Test Failed', '[ 1!=3 ]', fields={'prevValue': 'oldbog'})
        self.mox.ReplayAll()
        self.assertRaises(
            ValueError,
            self.client.write,
            '/testKey',
            'test',
            prevValue='oldbog'
        )

import etcd
import unittest
import json
import urllib3

try:
    import mock
except ImportError:
    from unittest import mock

from etcd import EtcdException


class TestClientApiBase(unittest.TestCase):

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

class TestClientApiInterface(TestClientApiBase):

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
             u'node': {
                 u'expiration': u'2013-09-14T00:56:59.316195568+02:00',
                 u'modifiedIndex': 183,
                 u'key': u'/testkey',
                 u'ttl': 19,
                 u'value': u'test'
             }
             }

        self._mock_api(200, d)
        res = self.client.write('/testkey', 'test')
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_newkey(self):
        """ Can set a new value """
        d = {
            u'action': u'set',
            u'node': {
                u'expiration': u'2013-09-14T00:56:59.316195568+02:00',
                u'modifiedIndex': 183,
                u'key': u'/testkey',
                u'ttl': 19,
                u'value': u'test'
            }
        }
        self._mock_api(201, d)
        res = self.client.write('/testkey', 'test')
        d['node']['newKey'] = True
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_not_found_response(self):
        """ Can handle server not found response """
        self._mock_api(404, 'Not found')
        self.assertRaises(etcd.EtcdException, self.client.read, '/somebadkey')

    def test_compare_and_swap(self):
        """ Can set compare-and-swap a value """
        d = {u'action': u'compareAndSwap',
             u'node': {
                 u'expiration': u'2013-09-14T00:56:59.316195568+02:00',
                 u'modifiedIndex': 183,
                 u'key': u'/testkey',
                 u'ttl': 19,
                 u'value': u'test'
             }
             }

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

    def test_set_append(self):
        """ Can append a new key """
        d = {
            u'action': u'create',
            u'node': {
                u'createdIndex': 190,
                u'modifiedIndex': 190,
                u'key': u'/testdir/190',
                u'value': u'test'
            }
        }
        self._mock_api(201, d)
        res = self.client.write('/testdir', 'test')
        self.assertEquals(res.createdIndex, 190)

    def test_set_dir_with_value(self):
        """ Creating a directory with a value raises an error. """
        self.assertRaises(etcd.EtcdException, self.client.write,
                          '/bar', 'testvalye', dir=True)

    def test_delete(self):
        """ Can delete a value """
        d = {
            u'action': u'delete',
            u'node': {
                u'key': u'/testkey',
                "modifiedIndex": 3,
                "createdIndex": 2
            }
        }
        self._mock_api(200, d)
        res = self.client.delete('/testKey')
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_read(self):
        """ Can get a value """
        d = {
            u'action': u'get',
            u'node': {
                u'modifiedIndex': 190,
                u'key': u'/testkey',
                u'value': u'test'
            }
        }
        self._mock_api(200, d)
        res = self.client.read('/testKey')
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_get_dir(self):
        """Can get values in dirs"""
        d = {
            u'action': u'get',
            u'node': {
                u'modifiedIndex': 190,
                u'key': u'/testkey',
                u'dir': True,
                u'nodes': [
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
            u'node': {
                u'modifiedIndex': 190,
                u'key': u'/testkey',
                u'value': u'test'
            }
        }
        self._mock_api(200, d)
        self.assertTrue('/testey' in self.client)

    def test_watch(self):
        """ Can watch a key """
        d = {
            u'action': u'get',
            u'node': {
                u'modifiedIndex': 190,
                u'key': u'/testkey',
                u'value': u'test'
            }
        }
        self._mock_api(200, d)
        res = self.client.read('/testkey', wait=True)
        self.assertEquals(res, etcd.EtcdResult(**d))

    def test_watch_index(self):
        """ Can watch a key starting from the given Index """
        d = {
            u'action': u'get',
            u'node': {
                u'modifiedIndex': 170,
                u'key': u'/testkey',
                u'value': u'testold'
            }
        }
        self._mock_api(200, d)
        res = self.client.read('/testkey', wait=True, waitIndex=True)
        self.assertEquals(res, etcd.EtcdResult(**d))


class EtcdLockTestCase(TestClientApiBase):
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


    def test_acquire_lock(self):
        """ Can get a lock. """
        key = u'/testkey'
        ttl = 1
        self._mock_api(200, '2')
        lock = self.client.get_lock(key, ttl=ttl)
        lock.acquire()
        self.assertEquals(lock._index, '2')

    def test_acquire_lock_invalid_ttl(self):
        """ Invalid TTL throws an error """
        key = u'/testkey'
        ttl = u'invalid'
        expected_index = u'invalid'
        self._mock_exception(etcd.EtcdException, u'invalid ttl: invalid')
        lock = self.client.get_lock(key, ttl=ttl)
        self.assertRaises(etcd.EtcdException, lock.acquire)

    def test_acquire_lock_with_context_manager(self):
        key = u'/testkey'
        ttl = 1
        self._mock_api(200, u'2')
        lock = self.client.get_lock(key, ttl=ttl)
        with lock:
            self.assertTrue(lock.is_locked())
        self._mock_api(200, u'')
        self.assertFalse(lock.is_locked())

    def test_is_locked(self):
        key = u'/testkey'
        ttl = 1
        self._mock_api(200, u'')
        lock = self.client.get_lock(key, ttl=ttl)
        self.assertFalse(lock.is_locked())
        self._mock_api(200, u'2')
        lock.acquire()
        self.assertTrue(lock.is_locked())


    def test_renew(self):
        key = '/testkey'
        ttl = 1
        self._mock_api(200, u'2')
        lock = self.client.get_lock(key, ttl=ttl)
        lock.acquire()
        self.assertTrue(lock.is_locked())
        self._mock_api(200, u'')
        lock.renew(2)
        self._mock_api(200, u'2')
        self.assertTrue(lock.is_locked())

    def test_renew_fails_if_expired(self):
        self._mock_api(200, u'4')
        lock = self.client.get_lock('/testlock', value='test', ttl=1).acquire()
        self._mock_api(500, 'renew lock error: cannot find: test')
        self.assertRaises(etcd.EtcdException, lock.renew, 10)

    def test_renew_fails_without_locking(self):
        key = u'/testkey'
        ttl = 1
        self._mock_exception(etcd.EtcdException,
                             u'Cannot renew lock that is not locked')
        lock = self.client.get_lock(key, ttl=ttl)
        self.assertRaises(etcd.EtcdException, lock.renew, 2)

    def test_release(self):
        key = u'/testkey'
        ttl = 1
        index = u'2'
        self._mock_api(200, index)
        lock = self.client.get_lock(key, ttl=ttl)
        lock.acquire()
        self.assertTrue(lock.is_locked())
        self._mock_api(200, '')
        lock.release()
        self.assertFalse(lock.is_locked())

    def test_release_fails_without_locking(self):
        key = u'/testkey'
        ttl = 1
        self._mock_exception(etcd.EtcdException,
                             u'Cannot release lock that is not locked')
        lock = self.client.get_lock(key, ttl=ttl)
        self.assertRaises(etcd.EtcdException, lock.release)

    def test_release_fails_if_expired(self):
        self._mock_api(200, u'4')
        lock = self.client.get_lock('/testlock', value='test', ttl=1).acquire()
        self._mock_api(500, 'release lock error: cannot find: test')
        self.assertRaises(etcd.EtcdException, lock.release)



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

    def test_path_without_trailing_slash(self):
        """ Exception will be raised if a path without a trailing slash is used """
        self.assertRaises(ValueError, self.client.api_execute,
                          'testpath/bar', self.client._MPUT)

    def test_api_method_not_supported(self):
        """ Exception will be raised if an unsupported HTTP method is used """
        self.assertRaises(etcd.EtcdException,
                          self.client.api_execute, '/testpath/bar', 'TRACE')

    def test_not_in(self):
        pass

    def test_in(self):
        pass

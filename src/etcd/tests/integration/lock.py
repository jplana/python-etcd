import etcd
from etcd.tests.integration import test_simple


class TestLocks(test_simple.EtcdIntegrationTest):
    def setUp(self):
        self.client = etcd.Client(port=6001)

    def test_acquire_lock(self):
        """ Can get a lock. """
        key = '/testkey'
        ttl = 1
        expected_index = '2'
        lock = self.client.get_lock(key, ttl=ttl)
        lock.acquire()
        self.assertEquals(lock._index, expected_index)
        lock.release()

    def test_acquire_lock_invalid_ttl(self):
        """ Invalid TTL throws an error """
        key = '/testkey'
        ttl = 'invalid'
        expected_index = 'invalid'
        lock = self.client.get_lock(key, ttl=ttl)
        self.assertRaises(etcd.EtcdException, lock.acquire)

    def test_acquire_lock_with_context_manager(self):
        key = '/testkey'
        ttl = 1
        lock = self.client.get_lock(key, ttl=ttl)
        with lock:
            self.assertTrue(lock.is_locked())
        self.assertFalse(lock.is_locked())

    def test_is_locked(self):
        key = '/testkey'
        ttl = 1
        lock = self.client.get_lock(key, ttl=ttl)
        self.assertFalse(lock.is_locked())
        lock.acquire()
        self.assertTrue(lock.is_locked())
        lock.release()

    def test_renew(self):
        key = '/testkey'
        ttl = 1
        lock = self.client.get_lock(key, ttl=ttl)
        lock.acquire()
        self.assertTrue(lock.is_locked())
        lock.renew(2)
        # TODO sleep(1)?
        self.assertTrue(lock.is_locked())
        lock.release()

    def test_renew_fails_without_locking(self):
        key = '/testkey'
        ttl = 1
        lock = self.client.get_lock(key, ttl=ttl)
        self.assertEquals(lock._index, None)
        self.assertRaises(etcd.EtcdException, lock.renew, 2)

    def test_release(self):
        key = '/testkey'
        ttl = 1
        index = '2'
        lock = self.client.get_lock(key, ttl=ttl)
        lock.acquire()
        self.assertTrue(lock.is_locked())
        lock.release()
        self.assertFalse(lock.is_locked())

    def test_release_fails_without_locking(self):
        key = '/testkey'
        ttl = 1
        lock = self.client.get_lock(key, ttl=ttl)
        self.assertEquals(lock._index, None)
        self.assertRaises(etcd.EtcdException, lock.release)

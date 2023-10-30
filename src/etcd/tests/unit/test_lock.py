import etcd

try:
    import mock
except ImportError:
    from unittest import mock
from etcd.tests.unit import TestClientApiBase


class TestClientLock(TestClientApiBase):
    def recursive_read(self):
        nodes = [
            {
                "key": "/_locks/test_lock/1",
                "value": "2qwwwq",
                "modifiedIndex": 33,
                "createdIndex": 33,
            },
            {
                "key": "/_locks/test_lock/34",
                "value": self.locker.uuid,
                "modifiedIndex": 34,
                "createdIndex": 34,
            },
        ]
        d = {
            "action": "get",
            "node": {
                "dir": True,
                "nodes": [{"key": "/_locks/test_lock", "dir": True, "nodes": nodes}],
            },
        }
        self._mock_api(200, d)

    def setUp(self):
        super(TestClientLock, self).setUp()
        self.locker = etcd.Lock(self.client, "test_lock")

    def test_initialization(self):
        """
        Verify the lock gets initialized correctly
        """
        self.assertEqual(self.locker.name, "test_lock")
        self.assertEqual(self.locker.path, "/_locks/test_lock")
        self.assertEqual(self.locker.is_taken, False)

    def test_acquire(self):
        """
        Acquiring a precedingly inexistent lock works.
        """
        l = etcd.Lock(self.client, "test_lock")
        l._find_lock = mock.MagicMock(spec=l._find_lock, return_value=False)
        l._acquired = mock.MagicMock(spec=l._acquired, return_value=True)
        # Mock the write
        d = {
            "action": "set",
            "node": {
                "modifiedIndex": 190,
                "key": "/_locks/test_lock/1",
                "value": l.uuid,
            },
        }
        self._mock_api(200, d)
        self.assertEqual(l.acquire(), True)
        self.assertEqual(l._sequence, "1")

    def test_is_acquired(self):
        """
        Test is_acquired
        """
        self.locker._sequence = "1"
        d = {
            "action": "get",
            "node": {
                "modifiedIndex": 190,
                "key": "/_locks/test_lock/1",
                "value": self.locker.uuid,
            },
        }
        self._mock_api(200, d)
        self.locker.is_taken = True
        self.assertEqual(self.locker.is_acquired, True)

    def test_is_not_acquired(self):
        """
        Test is_acquired failures
        """
        self.locker._sequence = "2"
        self.locker.is_taken = False
        self.assertEqual(self.locker.is_acquired, False)
        self.locker.is_taken = True
        self._mock_exception(etcd.EtcdKeyNotFound, self.locker.lock_key)
        self.assertEqual(self.locker.is_acquired, False)
        self.assertEqual(self.locker.is_taken, False)

    def test_acquired(self):
        """
        Test the acquiring primitives
        """
        self.locker._sequence = "4"
        retval = ("/_locks/test_lock/4", None)
        self.locker._get_locker = mock.MagicMock(return_value=retval)
        self.assertTrue(self.locker._acquired())
        self.assertTrue(self.locker.is_taken)
        retval = ("/_locks/test_lock/1", "/_locks/test_lock/4")
        self.locker._get_locker = mock.MagicMock(return_value=retval)
        self.assertFalse(self.locker._acquired(blocking=False))
        self.assertFalse(self.locker.is_taken)
        d = {
            "action": "delete",
            "node": {
                "modifiedIndex": 190,
                "key": "/_locks/test_lock/1",
                "value": self.locker.uuid,
            },
        }
        self._mock_api(200, d)
        returns = [
            ("/_locks/test_lock/1", "/_locks/test_lock/4"),
            ("/_locks/test_lock/4", None),
        ]

        def side_effect():
            return returns.pop()

        self.locker._get_locker = mock.MagicMock(side_effect=side_effect)
        self.assertTrue(self.locker._acquired())

    def test_acquired_no_timeout(self):
        self.locker._sequence = 4
        returns = [
            ("/_locks/test_lock/4", None),
            (
                "/_locks/test_lock/1",
                etcd.EtcdResult(node={"key": "/_locks/test_lock/4", "modifiedIndex": 1}),
            ),
        ]

        def side_effect():
            return returns.pop()

        d = {
            "action": "get",
            "node": {
                "modifiedIndex": 190,
                "key": "/_locks/test_lock/4",
                "value": self.locker.uuid,
            },
        }
        self._mock_api(200, d)

        self.locker._get_locker = mock.create_autospec(
            self.locker._get_locker, side_effect=side_effect
        )
        self.assertTrue(self.locker._acquired())

    def test_lock_key(self):
        """
        Test responses from the lock_key property
        """
        with self.assertRaises(ValueError):
            self.locker.lock_key
        self.locker._sequence = "5"
        self.assertEqual("/_locks/test_lock/5", self.locker.lock_key)

    def test_set_sequence(self):
        self.locker._set_sequence("/_locks/test_lock/10")
        self.assertEqual("10", self.locker._sequence)

    def test_find_lock(self):
        d = {
            "action": "get",
            "node": {
                "modifiedIndex": 190,
                "key": "/_locks/test_lock/1",
                "value": self.locker.uuid,
            },
        }
        self._mock_api(200, d)
        self.locker._sequence = "1"
        self.assertTrue(self.locker._find_lock())
        # Now let's pretend the lock is not there
        self._mock_exception(etcd.EtcdKeyNotFound, self.locker.lock_key)
        self.assertFalse(self.locker._find_lock())
        self.locker._sequence = None
        self.recursive_read()
        self.assertTrue(self.locker._find_lock())
        self.assertEqual(self.locker._sequence, "34")

    def test_get_locker(self):
        self.recursive_read()
        self.assertEqual(
            (
                "/_locks/test_lock/1",
                etcd.EtcdResult(
                    node={
                        "newKey": False,
                        "_children": [],
                        "createdIndex": 33,
                        "modifiedIndex": 33,
                        "value": "2qwwwq",
                        "expiration": None,
                        "key": "/_locks/test_lock/1",
                        "ttl": None,
                        "action": None,
                        "dir": False,
                    }
                ),
            ),
            self.locker._get_locker(),
        )
        with self.assertRaises(etcd.EtcdLockExpired):
            self.locker._sequence = "35"
            self.locker._get_locker()

    def test_release(self):
        d = {
            "action": "delete",
            "node": {
                "modifiedIndex": 190,
                "key": "/_locks/test_lock/1",
                "value": self.locker.uuid,
            },
        }
        self._mock_api(200, d)
        self.locker._sequence = 1
        self.locker.is_taken = True
        self.locker.release()
        self.assertFalse(self.locker.is_taken)

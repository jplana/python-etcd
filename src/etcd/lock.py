import contextlib

import etcd

class Lock(object):

    """
    Lock object using etcd's lock module.
    """

    def __init__(self, client, key, ttl=None, value=None):
        """
        Initialize a lock object.

        Args:
            client (Client):  etcd client to use for communication.

            key (string):  key to lock.

            ttl (int):  ttl (in seconds) for the lock to live.
                        0 or None to lock forever.

            value (mixed):  value to store on the lock.
        """
        self.client = client
        self.key = key
        self.ttl = ttl or 0
        self.value = value
        self._index = None

    def _api_execute(self, *args, **kwargs):
        """Proxy method for `self.client.api_execute`"""
        return self.client.api_execute(*args, **kwargs)

    def __enter__(self):
        self.acquire()

    def __exit__(self, type, value, traceback):
        self.release()

    @property
    def _path(self):
        return '/mod/v2/lock{}'.format(self.key)

    def acquire(self):
        """Acquire the lock from etcd. Blocks until lock is acquired."""
        params = {'ttl': self.ttl}
        if self.value is not None:
            params['value'] = self.value

        res = self._api_execute(self._path, self.client._MPOST, params=params)
        if res.status == 200:
            self._index = res.data

    def is_locked(self):
        """Check if lock is currently locked."""
        params = {'field': 'index'}
        res = self._api_execute(self._path, self.client._MGET, params=params)
        return res.data != ''

    def release(self):
        """Release this lock."""
        if not self._index:
            raise etcd.EtcdException('cannot release lock that has not been locked')
        params = {'index': self._index}
        res = self._api_execute(self._path, self.client._MDELETE, params=params)
        self._index = None

    def renew(self, new_ttl):
        """
        Renew the TTL on this lock.

        Args:
            new_ttl (int): new TTL to set.
        """
        if not self._index:
            raise etcd.EtcdException('cannot renew lock that has not been locked')
        params = {'ttl': new_ttl, 'index': self._index}
        res = self._api_execute(self._path, self.client._MPUT, params=params)

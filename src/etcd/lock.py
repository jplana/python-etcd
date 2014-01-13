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
        if not key.startswith('/'):
            key = '/' + key
        self.key = key
        self.ttl = ttl or 0
        self.value = value
        self._index = None

    def __enter__(self):
        self.acquire()

    def __exit__(self, type, value, traceback):
        self.release()

    @property
    def _path(self):
        return u'/mod/v2/lock{}'.format(self.key)

    def acquire(self, timeout=None):
        """Acquire the lock from etcd. Blocks until lock is acquired."""
        params = {u'ttl': self.ttl}
        if self.value is not None:
            params[u'value'] = self.value

        res = self.client.api_execute(
            self._path, self.client._MPOST, params=params, timeout=timeout)
        self._index = res.data.decode('utf-8')
        return self

    def get(self):
        """
        Get Information on the lock.
        This allows to operate on locks that have not been acquired directly.
        """
        res = self.client.api_execute(self._path, self.client._MGET)
        if res.data:
            self.value = res.data.decode('utf-8')
        else:
            raise etcd.EtcdException('Lock is non-existent (or expired)')
        self._get_index()
        return self

    def _get_index(self):
        res = self.client.api_execute(
            self._path,
            self.client._MGET,
            {u'field': u'index'})
        if not res.data:
            raise etcd.EtcdException('Lock is non-existent (or expired)')
        self._index = res.data.decode('utf-8')

    def is_locked(self):
        """Check if lock is currently locked."""
        params = {u'field': u'index'}
        res = self.client.api_execute(
            self._path, self.client._MGET, params=params)
        return bool(res.data)

    def release(self):
        """Release this lock."""
        if not self._index:
            raise etcd.EtcdException(
                u'Cannot release lock that has not been locked')
        params = {u'index': self._index}
        res = self.client.api_execute(
            self._path, self.client._MDELETE, params=params)
        self._index = None

    def renew(self, new_ttl, timeout=None):
        """
        Renew the TTL on this lock.

        Args:
            new_ttl (int): new TTL to set.
        """
        if not self._index:
            raise etcd.EtcdException(
                u'Cannot renew lock that has not been locked')
        params = {u'ttl': new_ttl, u'index': self._index}
        res = self.client.api_execute(
            self._path, self.client._MPUT, params=params)

import contextlib

import etcd

class Lock(object):
    def __init__(self, client, key, ttl=None, value=None):
        self.client = client
        self.key = key
        self.ttl = ttl or 0
        self.value = value
        self._index = None

    def api_execute(self, *args, **kwargs):
        return self.client.api_execute(*args, **kwargs)

    def __enter__(self):
        self.acquire()

    def __exit__(self, type, value, traceback):
        self.release()

    @property
    def _path(self):
        return '/mod/v2/lock{}'.format(self.key)

    def acquire(self):
        params = {'ttl': self.ttl}
        if self.value is not None:
            params['value'] = self.value

        res = self.client.api_execute(self._path, self.client._MPOST, params=params)
        if res.status == 200:
            self._index = res.data

    def is_locked(self):
        params = {'field': 'index'}
        res = self.api_execute(self._path, self.client._MGET, params=params)
        return res.data != ''

    def release(self):
        if not self._index:
            raise etcd.EtcdException('cannot release lock that is not locked')
        params = {'index': self._index}
        res = self.api_execute(self._path, self.client._MDELETE, params=params)
        self._index = None

    def renew(self, new_ttl):
        if not self._index:
            raise etcd.EtcdException('cannot renew lock that is not locked')
        params = {'ttl': new_ttl, 'index': self._index}
        res = self.api_execute(self._path, self.client._MPUT, params=params)

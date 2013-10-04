import collections
from client import Client


class EtcdResult(collections.namedtuple(
    'EtcdResult',
    [
        'action',
        'index',
        'key',
        'prevValue',
        'value',
        'expiration',
        'ttl',
        'newKey'])):

    def __new__(
            cls,
            action=None,
            index=None,
            key=None,
            prevValue=None,
            value=None,
            expiration=None,
            ttl=None,
            newKey=None):
        return super(EtcdResult, cls).__new__(
            cls,
            action,
            index,
            key,
            prevValue,
            value,
            expiration,
            ttl,
            newKey)


class EtcdException(Exception):
    """
    Generic Etcd Exception.
    """

    pass

# Attempt to enable urllib3's SNI support, if possible
# Blatantly copied from requests.
try:
    from urllib3.contrib import pyopenssl
    pyopenssl.inject_into_urllib3()
except ImportError:
    pass

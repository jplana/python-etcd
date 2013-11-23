import collections
from client import Client

class EtcdResult(collections.namedtuple(
        'EtcdResult',
        [
            'action',
            'key',
            'value',
            'expiration',
            'ttl',
            'modifiedIndex',
            'prevValue',
            'dir',
            'kvs'
        ]
)):
    def __new__(
            cls,
            action=None,
            key=None,
            value=None,
            expiration=None,
            ttl=None,
            modifiedIndex=None,
            prevValue=None,
            dir=False,
            kvs=None
    ):
        if dir and kvs:
            keys = []
            for result in kvs:
                keys.append(EtcdResult(**result))
            kvs = keys

        return super(EtcdResult, cls).__new__(
            cls,
            action,
            key,
            value,
            expiration,
            ttl,
            modifiedIndex,
            prevValue,
            dir,
            kvs
        )


class EtcdException(Exception):
    """
    Generic Etcd Exception.
    """

    pass


class EtcdError(object):
    # See https://github.com/coreos/etcd/blob/master/Documentation/errorcode.md
    error_exceptions = {
        100: KeyError,
        101: ValueError,
        102: KeyError,
        103: Exception,
        104: KeyError,
        105: KeyError,
        106: KeyError,
        200: ValueError,
        201: ValueError,
        202: ValueError,
        203: ValueError,
        300: Exception,
        301: Exception,
        400: Exception,
        401: EtcdException,
        500: EtcdException
    }

    @classmethod
    def handle(cls, errorCode=None, message=None, cause=None, **kwdargs):
        """ Decodes the error and throws the appropriate error message"""
        try:
            msg = "{} : {}".format(message, cause)
            exc = cls.error_exceptions[errorCode]
        except:
            msg = "Unable to decode server response"
            exc = EtcdException
        raise exc(msg)



# Attempt to enable urllib3's SNI support, if possible
# Blatantly copied from requests.
try:
    from urllib3.contrib import pyopenssl
    pyopenssl.inject_into_urllib3()
except ImportError:
    pass

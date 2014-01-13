import collections
from .client import Client
from .lock import Lock
from .election import LeaderElection


class EtcdResult(object):
    _node_props = {
        'key': None,
        'value': None,
        'expiration': None,
        'ttl': None,
        'modifiedIndex': None,
        'createdIndex': None,
        'newKey': False,
        'dir': False,
    }

    def __init__(self, action=None, node=None, **kwdargs):
        """
        Creates an EtcdResult object.

        Args:
            action (str): The action that resulted in key creation

            node (dict): The dictionary containing all node information.

        """
        self.action = action
        for (key, default) in self._node_props.items():
            if key in node:
                setattr(self, key, node[key])
            else:
                setattr(self, key, default)

        self._children = []
        if self.dir and 'nodes' in node:
            # We keep the data in raw format, converting them only when needed
            self._children = node['nodes']

    @property
    def children(self):
        if not self._children:
            yield self
            return
        for n in self._children:
            for child in EtcdResult(None, n).children:
                yield child
        return

    def __eq__(self, other):
        if not (type(self) is type(other)):
            return False
        for k in self._node_props.keys():
            try:
                a = getattr(self, k)
                b = getattr(other, k)
                if a != b:
                    return False
            except:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)


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

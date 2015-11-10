"""
.. module:: python-aioetcd
   :synopsis: An asynchronus python etcd client.

.. moduleauthor:: Jose Plana <jplana@gmail.com>


"""
import logging
#from http.client import HTTPException
from aiohttp.web_exceptions import HTTPException
import socket
import aiohttp
import json
import ssl
import aioetcd
import asyncio
import inspect

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


_log = logging.getLogger(__name__)


class Client(object):

    """
    Asynchronous client for etcd, the distributed log service using raft.
    """

    _MGET = 'GET'
    _MPUT = 'PUT'
    _MPOST = 'POST'
    _MDELETE = 'DELETE'
    _comparison_conditions = set(('prevValue', 'prevIndex', 'prevExist'))
    _read_options = set(('recursive', 'wait', 'waitIndex', 'sorted', 'quorum'))
    _del_conditions = set(('prevValue', 'prevIndex'))

    http = None

    def __init__(
            self,
            host='127.0.0.1',
            port=4001,
            version_prefix='/v2',
            read_timeout=60,
            allow_redirect=True,
            protocol='http',
            cert=None,
            ca_cert=None,
            allow_reconnect=False,
            use_proxies=False,
            expected_cluster_id=None,
            per_host_pool_size=10,
            loop=None,
    ):
        """
        Initialize the client.

        Args:
            host (mixed):
                           If a string, IP to connect to.
                           If a tuple ((host, port), (host, port), ...)

            port (int):  Port used to connect to etcd.

            version_prefix (str): Url or version prefix in etcd url (default=/v2).

            read_timeout (int):  max seconds to wait for a read.

            allow_redirect (bool): allow the client to connect to other nodes.

            protocol (str):  Protocol used to connect to etcd.

            cert (mixed):   If a string, the whole ssl client certificate;
                            if a tuple, the cert and key file names.

            ca_cert (str): The ca certificate. If pressent it will enable
                           validation.

            allow_reconnect (bool): allow the client to reconnect to another
                                    etcd server in the cluster in the case the
                                    default one does not respond.

            use_proxies (bool): we are using a list of proxies to which we connect,
                                 and don't want to connect to the original etcd cluster.

            expected_cluster_id (str): If a string, recorded as the expected
                                       UUID of the cluster (rather than
                                       learning it from the first request),
                                       reads will raise EtcdClusterIdChanged
                                       if they receive a response with a
                                       different cluster ID.
            per_host_pool_size (int): specifies maximum number of connections to pool
                                      by host. By default this will use up to 10
                                      connections.
        """
        _log.debug("New etcd client created for %s:%s%s",
                  host, port, version_prefix)
        self._protocol = protocol
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._client = aiohttp.ClientSession(loop=loop)

        def uri(protocol, host, port):
            return '%s://%s:%d' % (protocol, host, port)

        if not isinstance(host, tuple):
            self._machines_cache = []
            self._base_uri = uri(self._protocol, host, port)
        else:
            if not allow_reconnect:
                _log.error("List of hosts incompatible with allow_reconnect.")
                raise aioetcd.EtcdException("A list of hosts to connect to was given, but reconnection not allowed?")
            self._machines_cache = [uri(self._protocol, *conn) for conn in host]
            self._base_uri = self._machines_cache.pop(0)

        self.expected_cluster_id = expected_cluster_id
        self.version_prefix = version_prefix

        self._read_timeout = read_timeout
        self._allow_redirect = allow_redirect
        self._use_proxies = use_proxies
        self._allow_reconnect = allow_reconnect

        # SSL Client certificate support

        kw = {
          'maxsize': per_host_pool_size
        }

        if self._read_timeout > 0:
            kw['timeout'] = self._read_timeout

        if protocol == 'https':
            # If we don't allow TLSv1, clients using older version of OpenSSL
            # (<1.0) won't be able to connect.
            _log.debug("HTTPS enabled.")
            kw['ssl_version'] = ssl.PROTOCOL_TLSv1

        if cert:
            if isinstance(cert, tuple):
                # Key and cert are separate
                kw['cert_file'] = cert[0]
                kw['key_file'] = cert[1]
            else:
                # combined certificate
                kw['cert_file'] = cert

        if ca_cert:
            kw['ca_certs'] = ca_cert
            kw['cert_reqs'] = ssl.CERT_REQUIRED

        if self._allow_reconnect:
            # we need the set of servers in the cluster in order to try
            # reconnecting upon error. The cluster members will be
            # added to the hosts list you provided. If you are using
            # proxies, set all
            #
            # Beware though: if you input '127.0.0.1' as your host and
            # etcd advertises 'localhost', both will be in the
            # resulting list.

            # If we're connecting to the original cluster, we can
            # extend the list given to the client with what we get
            # from self.machines
            self._machines_available = self._use_proxies
            self._machines_cache = list(set(self._machines_cache))

            if self._base_uri in self._machines_cache:
                self._machines_cache.remove(self._base_uri)
            _log.debug("Machines cache initialised to %s",
                       self._machines_cache)
        else:
            self._machines_available = True

    def __del__(self):
        if self._client is not None:
            self._client.close()

    @asyncio.coroutine
    def _update_machines(self):
        self._machines_cache = yield from self.machines()
        self._machines_available = True

    @property
    def base_uri(self):
        """URI used by the client to connect to etcd."""
        return self._base_uri

    @property
    def host(self):
        """Node to connect to etcd."""
        return urlparse(self._base_uri).netloc.split(':')[0]

    @property
    def port(self):
        """Port to connect to etcd."""
        return int(urlparse(self._base_uri).netloc.split(':')[1])

    @property
    def protocol(self):
        """Protocol used to connect to etcd."""
        return self._protocol

    @property
    def read_timeout(self):
        """Max seconds to wait for a read."""
        return self._read_timeout

    @property
    def allow_redirect(self):
        """Allow the client to connect to other nodes."""
        return self._allow_redirect

    @asyncio.coroutine
    def machines(self):
        """
        Members of the cluster.

        Returns:
            list. str with all the nodes in the cluster.

        >>> print client.machines
        ['http://127.0.0.1:4001', 'http://127.0.0.1:4002']
        """
        # We can't use api_execute here, or it causes a logical loop
        try:
            uri = self._base_uri + self.version_prefix + '/machines'
            response = yield from self._client.request(
                self._MGET,
                uri,
                allow_redirects=self.allow_redirect,
            )

            response = yield from self._handle_server_response(response)
            response = yield from response.read()
            machines = [
                node.strip() for node in response.decode('utf-8').split(',')
            ]
            _log.debug("Retrieved list of machines: %s", machines)
            return machines
        except (HTTPException,
                socket.error) as e:
            # We can't get the list of machines, if one server is in the
            # machines cache, try on it
            _log.error("Failed to get list of machines from %s%s: %r",
                       self._base_uri, self.version_prefix, e)
            if self._machines_cache:
                self._base_uri = self._machines_cache.pop(0)
                _log.info("Retrying on %s", self._base_uri)
                # Call myself
                return (yield from self.machines())
            else:
                raise aioetcd.EtcdException("Could not get the list of servers, "
                                         "maybe you provided the wrong "
                                         "host(s) to connect to?")

    @asyncio.coroutine
    def members(self):
        """
        A more structured view of peers in the cluster.

        Note that while we have an internal DS called _members, accessing the public property will call etcd.
        """
        # Empty the members list
        self._members = {}
        try:
            response = yield from self.api_execute(self.version_prefix + '/members', self._MGET)
            data = yield from response.read()
            res = json.loads(data.decode('utf-8'))
            for member in res['members']:
                self._members[member['id']] = member
            return self._members
        except:
            raise aioetcd.EtcdException("Could not get the members list, maybe the cluster has gone away?")

    @asyncio.coroutine
    def leader(self):
        """
        Returns:
            dict. the leader of the cluster.

        >>> print (loop.run_until_complete(client.leader()))
        {"id":"ce2a822cea30bfca","name":"default","peerURLs":["http://localhost:2380","http://localhost:7001"],"clientURLs":["http://127.0.0.1:4001"]}
        """
        try:
            response = yield from self.api_execute(self.version_prefix + '/stats/leader', self._MGET)
            data = yield from response.read()
            leader = json.loads(data.decode('utf-8'))
            return (yield from self.members())[leader['leader']]
        except Exception as e:
            raise aioetcd.EtcdException("Cannot get leader data: %s" % e)

    def stats(self):
        """
        Returns:
            dict. the stats of the local server
        """
        return self._stats()

    def leader_stats(self):
        """
        Returns:
            dict. the stats of the leader
        """
        return self._stats('leader')

    def store_stats(self):
        """
        Returns:
           dict. the stats of the kv store
        """
        return self._stats('store')

    @asyncio.coroutine
    def _stats(self, what='self'):
        """ Internal method to access the stats endpoints"""
        data = yield from self.api_execute(self.version_prefix + '/stats/' + what, self._MGET)
        data = yield from data.read()
        data = data.decode('utf-8')
        try:
            return json.loads(data)
        except (TypeError,ValueError):
            raise aioetcd.EtcdException("Cannot parse json data in the response")

    @property
    def key_endpoint(self):
        """
        REST key endpoint.
        """
        return self.version_prefix + '/keys'

    @asyncio.coroutine
    def contains(self, key):
        """
        Check if a key is available in the cluster.

        >>> print 'key' in client
        True
        """
        try:
            yield from self.get(key)
            return True
        except aioetcd.EtcdKeyNotFound:
            return False

    def _sanitize_key(self, key):
        if not key.startswith('/'):
            key = "/{}".format(key)
        return key


    @asyncio.coroutine
    def write(self, key, value, ttl=None, dir=False, append=False, **kwdargs):
        """
        Writes the value for a key, possibly doing atomit Compare-and-Swap

        Args:
            key (str):  Key.

            value (object):  value to set

            ttl (int):  Time in seconds of expiration (optional).

            dir (bool): Set to true if we are writing a directory; default is false.

            append (bool): If true, it will post to append the new value to the dir, creating a sequential key. Defaults to false.

            Other parameters modifying the write method are accepted:


            prevValue (str): compare key to this value, and swap only if corresponding (optional).

            prevIndex (int): modify key only if actual modifiedIndex matches the provided one (optional).

            prevExist (bool): If false, only create key; if true, only update key.

        Returns:
            client.EtcdResult

        >>> print client.write('/key', 'newValue', ttl=60, prevExist=False).value
        'newValue'

        """
        _log.debug("Writing %s to key %s ttl=%s dir=%s append=%s",
                  value, key, ttl, dir, append)
        key = self._sanitize_key(key)
        params = {}
        if value is not None:
            params['value'] = value

        if ttl is not None:
            params['ttl'] = ttl

        if dir:
            if value:
                raise aioetcd.EtcdException(
                    'Cannot create a directory with a value')
            params['dir'] = "true"

        for (k, v) in kwdargs.items():
            if k in self._comparison_conditions:
                if type(v) == bool:
                    params[k] = v and "true" or "false"
                else:
                    params[k] = v

        method = append and self._MPOST or self._MPUT
        if '_endpoint' in kwdargs:
            path = kwdargs['_endpoint'] + key
        else:
            path = self.key_endpoint + key

        response = yield from self.api_execute(path, method, params=params)
        return (yield from self._result_from_response(response))

    def update(self, obj):
        """
        Updates the value for a key atomically. Typical usage would be:

        c = aioetcd.Client()
        o = yield from c.read("/somekey")
        o.value += 1
        yield from c.update(o)

        Args:
            obj (aioetcd.EtcdResult):  The object that needs updating.

        This method returns a coroutine.
        """
        _log.debug("Updating %s to %s.", obj.key, obj.value)
        kwdargs = {
            'dir': obj.dir,
            'ttl': obj.ttl,
            'prevExist': True
            }

        if not obj.dir:
            # prevIndex on a dir causes a 'not a file' error. d'oh!
            kwdargs['prevIndex'] = obj.modifiedIndex
        return self.write(obj.key, obj.value, **kwdargs)

    @asyncio.coroutine
    def read(self, key, **kwdargs):
        """
        Returns the value of the key 'key'.

        Args:
            key (str):  Key.

            Recognized kwd args

            recursive (bool): If you should fetch recursively a dir

            wait (bool): If we should wait and return next time the key is changed

            waitIndex (int): The index to fetch results from.

            sorted (bool): Sort the output keys (alphanumerically)

        Returns:
            client.EtcdResult (or an array of client.EtcdResult if a
            subtree is queried)

        Raises:
            KeyValue:  If the key doesn't exists.

        >>> print client.get('/key').value
        'value'

        """
        _log.debug("Issuing read for key %s with args %s", key, kwdargs)
        key = self._sanitize_key(key)

        params = {}
        for (k, v) in kwdargs.items():
            if k in self._read_options:
                if type(v) == bool:
                    params[k] = v and "true" or "false"
                elif v is not None:
                    params[k] = v

        response = yield from self.api_execute(
            self.key_endpoint + key, self._MGET, params=params)
        return (yield from self._result_from_response(response))

    @asyncio.coroutine
    def delete(self, key, recursive=None, dir=None, **kwdargs):
        """
        Removed a key from etcd.

        Args:

            key (str):  Key.

            recursive (bool): if we want to recursively delete a directory, set
                              it to true

            dir (bool): if we want to delete a directory, set it to true

            prevValue (str): compare key to this value, and swap only if
                             corresponding (optional).

            prevIndex (int): modify key only if actual modifiedIndex matches the
                             provided one (optional).

        Returns:
            client.EtcdResult

        Raises:
            KeyValue:  If the key doesn't exists.

        >>> print client.delete('/key').key
        '/key'

        """
        _log.debug("Deleting %s recursive=%s dir=%s extra args=%s",
                   key, recursive, dir, kwdargs)
        key = self._sanitize_key(key)

        kwds = {}
        if recursive is not None:
            kwds['recursive'] = recursive and "true" or "false"
        if dir is not None:
            kwds['dir'] = dir and "true" or "false"

        for k in self._del_conditions:
            if k in kwdargs:
                kwds[k] = kwdargs[k]
        _log.debug("Calculated params = %s", kwds)

        response = yield from self.api_execute(
            self.key_endpoint + key, self._MDELETE, params=kwds)
        return (yield from self._result_from_response(response))

    def pop(self, key, recursive=None, dir=None, **kwdargs):
        """
        Remove specified key from etcd and return the corresponding value.

        Args:

            key (str):  Key.

            recursive (bool): if we want to recursively delete a directory, set
                              it to true

            dir (bool): if we want to delete a directory, set it to true

            prevValue (str): compare key to this value, and swap only if
                             corresponding (optional).

            prevIndex (int): modify key only if actual modifiedIndex matches the
                             provided one (optional).

        Returns:
            A coroutine returning client.EtcdResult

        Raises:
            KeyValue:  If the key doesn't exists.

        >>> print client.pop('/key').value
        'value'

        """
        return self.delete(key=key, recursive=recursive, dir=dir, **kwdargs)._prev_node

    # Higher-level methods on top of the basic primitives
    def test_and_set(self, key, value, prev_value, ttl=None):
        """
        Atomic test & set operation.
        It will check if the value of 'key' is 'prev_value',
        if the the check is correct will change the value for 'key' to 'value'
        if the the check is false an exception will be raised.

        Args:
            key (str):  Key.
            value (object):  value to set
            prev_value (object):  previous value.
            ttl (int):  Time in seconds of expiration (optional).

        Returns:
            A coroutine returning client.EtcdResult

        Raises:
            ValueError: When the 'prev_value' is not the current value.

        >>> print client.test_and_set('/key', 'new', 'old', ttl=60).value
        'new'

        """
        return self.write(key, value, prevValue=prev_value, ttl=ttl)

    def set(self, key, value, ttl=None):
        """
        Compatibility: sets the value of the key 'key' to the value 'value'

        Args:
            key (str):  Key.
            value (object):  value to set
            ttl (int):  Time in seconds of expiration (optional).

        Returns:
            A coroutine returning client.EtcdResult

        Raises:
           aioetcd.EtcdException: when something weird goes wrong.

        """
        return self.write(key, value, ttl=ttl)

    def get(self, key):
        """
        Returns the value of the key 'key'.

        Args:
            key (str):  Key.

        Returns:
            A coroutine returning client.EtcdResult

        Raises:
            KeyError:  If the key doesn't exists.

        >>> print client.get('/key').value
        'value'

        """
        return self.read(key)

    def watch(self, key, index=None, recursive=None):
        """
        Blocks until a new event has been received, starting at index 'index'

        Args:
            key (str):  Key.

            index (int): Index to start from.

            timeout (int):  max seconds to wait for a read.

        Returns:
            A coroutine returning client.EtcdResult

        Raises:
            KeyValue:  If the key doesn't exists.

        >>> print client.watch('/key').value
        'value'

        """
        _log.debug("About to wait on key %s, index %s", key, index)
        if index:
            return self.read(key, wait=True, waitIndex=index, recursive=recursive)
        else:
            return self.read(key, wait=True, recursive=recursive)

    @asyncio.coroutine
    def eternal_watch(self, key, callback, index=None, recursive=None):
        """
        Generator that will yield changes from a key.
        Note that this method will block forever until an event is generated.

        Args:
            key (str):  Key to subcribe to.
            index (int):  Index from where the changes will be received.

        Yields:
            client.EtcdResult

        >>> for event in client.eternal_watch('/subcription_key'):
        ...     print event.value
        ...
        value1
        value2

        """
        local_index = index
        while True:
            response = yield from self.watch(key, index=local_index, recursive=recursive)
            local_index = response.modifiedIndex + 1
            res = callback(response)
            if isinstance(res, asyncio.Future) or inspect.isgenerator(res):
                yield from res

    def get_lock(self, *args, **kwargs):
        raise NotImplementedError('Lock primitives were removed from etcd 2.0')

    @property
    def election(self):
        raise NotImplementedError('Election primitives were removed from etcd 2.0')

    @asyncio.coroutine
    def _result_from_response(self, response):
        """ Creates an EtcdResult from json dictionary """
        try:
            data = yield from response.read()
            res = json.loads(data.decode('utf-8'))
            r = aioetcd.EtcdResult(**res)
            if response.status == 201:
                r.newKey = True
            r.parse_headers(response)
            return r
        except Exception as e:
            raise aioetcd.EtcdException(
                'Unable to decode server response: %s' % e)

    def _next_server(self):
        """ Selects the next server in the list, refreshes the server list. """
        _log.debug("Selection next machine in cache. Available machines: %s",
                   self._machines_cache)
        try:
            mach = self._machines_cache.pop()
        except IndexError:
            _log.error("Machines cache is empty, no machines to try.")
            raise aioetcd.EtcdConnectionFailed('No more machines in the cluster')
        else:
            _log.info("Selected new etcd server %s", mach)
            return mach

    @asyncio.coroutine
    def api_execute(self, path, method, params=None):
        """ Executes the query. """

        some_request_failed = False
        response = False

        if not path.startswith('/'):
            raise ValueError('Path does not start with /')

        if not self._machines_available:
            yield from self._update_machines()

        while not response:
            try:
                url = self._base_uri + path

                response = yield from self._client.request(
                    method,
                    url,
                    params=params,
                    allow_redirects=self.allow_redirect,
                    )

            # earlier versions don't wrap socket errors
            except (HTTPException,
                    socket.error) as e:
                _log.error("Request to server %s failed: %r",
                           self._base_uri, e)
                if self._allow_reconnect:
                    _log.info("Reconnection allowed, looking for another "
                              "server.")
                    # _next_server() raises EtcdException if there are no
                    # machines left to try, breaking out of the loop.
                    self._base_uri = self._next_server()
                    some_request_failed = True
                else:
                    _log.debug("Reconnection disabled, giving up.")
                    raise aioetcd.EtcdConnectionFailed(
                        "Connection to etcd failed due to %r" % e)
            except:
                _log.exception("Unexpected request failure, re-raising.")
                raise

            else:
                # Check the cluster ID hasn't changed under us.  We use
                # preload_content=False above so we can read the headers
                # before we wait for the content of a long poll.
                try:
                    cluster_id = response.headers["x-etcd-cluster-id"]
                except KeyError: # some messages don't have it
                    pass
                else:
                    id_changed = (self.expected_cluster_id
                                  and cluster_id is not None and
                                  cluster_id != self.expected_cluster_id)
                    # Update the ID so we only raise the exception once.
                    old_expected_cluster_id = self.expected_cluster_id
                    self.expected_cluster_id = cluster_id
                    if id_changed:
                        # Defensive: clear the pool so that we connect afresh next
                        # time.
                        raise aioetcd.EtcdClusterIdChanged(
                            'The UUID of the cluster changed from {} to '
                            '{}.'.format(old_expected_cluster_id, cluster_id))

        if some_request_failed:
            if not self._use_proxies:
                # The cluster may have changed since last invocation
                self._machines_cache = yield from self.machines()
            self._machines_cache.remove(self._base_uri)
        response = yield from self._handle_server_response(response)
        return response

    @asyncio.coroutine
    def _handle_server_response(self, response):
        """ Handles the server response """
        if response.status in [200, 201]:
            return response

        else:
            data = yield from response.read()
            resp = data.decode('utf-8')

            # throw the appropriate exception
            try:
                r = json.loads(resp)
            except (TypeError, ValueError):
                # Bad JSON, make a response locally.
                r = {"message": "Bad response",
                     "cause": str(resp)}
            aioetcd.EtcdError.handle(r)


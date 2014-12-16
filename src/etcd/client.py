"""
.. module:: python-etcd
   :synopsis: A python etcd client.

.. moduleauthor:: Jose Plana <jplana@gmail.com>


"""
import urllib3
import json
import ssl

import etcd


class Client(object):

    """
    Client for etcd, the distributed log service using raft.
    """

    _MGET = 'GET'
    _MPUT = 'PUT'
    _MPOST = 'POST'
    _MDELETE = 'DELETE'
    _comparison_conditions = set(('prevValue', 'prevIndex', 'prevExist'))
    _read_options = set(('recursive', 'wait', 'waitIndex', 'sorted', 'consistent'))
    _del_conditions = set(('prevValue', 'prevIndex'))
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
+
            protocol (str):  Protocol used to connect to etcd.

            cert (mixed):   If a string, the whole ssl client certificate;
                            if a tuple, the cert and key file names.

            ca_cert (str): The ca certificate. If pressent it will enable
                           validation.

            allow_reconnect (bool): allow the client to reconnect to another
                                    etcd server in the cluster in the case the
                                    default one does not respond.

        """
        self._machines_cache = []

        self._protocol = protocol

        def uri(protocol, host, port):
            return '%s://%s:%d' % (protocol, host, port)

        if not isinstance(host, tuple):
            self._host = host
            self._port = port
        else:
            self._host, self._port = host[0]
            self._machines_cache.extend(
                [uri(self._protocol, *conn) for conn in host])

        self._base_uri = uri(self._protocol, self._host, self._port)

        self.version_prefix = version_prefix

        self._read_timeout = read_timeout
        self._allow_redirect = allow_redirect
        self._allow_reconnect = allow_reconnect

        # SSL Client certificate support

        kw = {}

        if self._read_timeout > 0:
            kw['timeout'] = self._read_timeout

        if protocol == 'https':
            # If we don't allow TLSv1, clients using older version of OpenSSL
            # (<1.0) won't be able to connect.
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

        self.http = urllib3.PoolManager(num_pools=10, **kw)

        if self._allow_reconnect:
            # we need the set of servers in the cluster in order to try
            # reconnecting upon error.
            self._machines_cache = self.machines
            self._machines_cache.remove(self._base_uri)
        else:
            self._machines_cache = []

    @property
    def base_uri(self):
        """URI used by the client to connect to etcd."""
        return self._base_uri

    @property
    def host(self):
        """Node to connect  etcd."""
        return self._host

    @property
    def port(self):
        """Port to connect etcd."""
        return self._port

    @property
    def protocol(self):
        """Protocol used to connect etcd."""
        return self._protocol

    @property
    def read_timeout(self):
        """Max seconds to wait for a read."""
        return self._read_timeout

    @property
    def allow_redirect(self):
        """Allow the client to connect to other nodes."""
        return self._allow_redirect

    @property
    def machines(self):
        """
        Members of the cluster.

        Returns:
            list. str with all the nodes in the cluster.

        >>> print client.machines
        ['http://127.0.0.1:4001', 'http://127.0.0.1:4002']
        """
        return [
            node.strip() for node in self.api_execute(
                self.version_prefix + '/machines',
                self._MGET).data.decode('utf-8').split(',')
        ]

    @property
    def leader(self):
        """
        Returns:
            str. the leader of the cluster.

        >>> print client.leader
        'http://127.0.0.1:4001'
        """
        return self.api_execute(
            self.version_prefix + '/leader',
            self._MGET).data.decode('ascii')

    @property
    def key_endpoint(self):
        """
        REST key endpoint.
        """
        return self.version_prefix + '/keys'

    def __contains__(self, key):
        """
        Check if a key is available in the cluster.

        >>> print 'key' in client
        True
        """
        try:
            self.get(key)
            return True
        except KeyError:
            return False

    def _sanitize_key(self, key):
        if not key.startswith('/'):
            key = "/{}".format(key)
        return key


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
        key = self._sanitize_key(key)
        params = {}
        if value is not None:
            params['value'] = value

        if ttl:
            params['ttl'] = ttl

        if dir:
            if value:
                raise etcd.EtcdException(
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

        response = self.api_execute(path, method, params=params)
        return self._result_from_response(response)

    def update(self, obj):
        """
        Updates the value for a key atomically. Typical usage would be:

        c = etcd.Client()
        o = c.read("/somekey")
        o.value += 1
        c.update(o)

        Args:
            obj (etcd.EtcdResult):  The object that needs updating.

        """
        kwdargs = {
            'dir': obj.dir,
            'ttl': obj.ttl,
            'prevExist': True
            }

        if not obj.dir:
            # prevIndex on a dir causes a 'not a file' error. d'oh!
            kwdargs['prevIndex'] = obj.modifiedIndex

        return self.write(obj.key, obj.value, **kwdargs)



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

            timeout (int):  max seconds to wait for a read.

        Returns:
            client.EtcdResult (or an array of client.EtcdResult if a
            subtree is queried)

        Raises:
            KeyValue:  If the key doesn't exists.

            urllib3.exceptions.TimeoutError: If timeout is reached.

        >>> print client.get('/key').value
        'value'

        """
        key = self._sanitize_key(key)

        params = {}
        for (k, v) in kwdargs.items():
            if k in self._read_options:
                if type(v) == bool:
                    params[k] = v and "true" or "false"
                else:
                    params[k] = v

        timeout = kwdargs.get('timeout', None)

        response = self.api_execute(
            self.key_endpoint + key, self._MGET, params=params, timeout=timeout)
        return self._result_from_response(response)

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
        key = self._sanitize_key(key)

        kwds = {}
        if recursive is not None:
            kwds['recursive'] = recursive and "true" or "false"
        if dir is not None:
            kwds['dir'] = dir and "true" or "false"

        for k in self._del_conditions:
            if k in kwdargs:
                kwds[k] = kwdargs[k]

        response = self.api_execute(
            self.key_endpoint + key, self._MDELETE, params=kwds)
        return self._result_from_response(response)

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
            client.EtcdResult

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
            client.EtcdResult

        Raises:
           etcd.EtcdException: when something weird goes wrong.

        """
        return self.write(key, value, ttl=ttl)

    def get(self, key):
        """
        Returns the value of the key 'key'.

        Args:
            key (str):  Key.

        Returns:
            client.EtcdResult

        Raises:
            KeyError:  If the key doesn't exists.

        >>> print client.get('/key').value
        'value'

        """
        return self.read(key)

    def watch(self, key, index=None, timeout=None, recursive=None):
        """
        Blocks until a new event has been received, starting at index 'index'

        Args:
            key (str):  Key.

            index (int): Index to start from.

            timeout (int):  max seconds to wait for a read.

        Returns:
            client.EtcdResult

        Raises:
            KeyValue:  If the key doesn't exists.

            urllib3.exceptions.TimeoutError: If timeout is reached.

        >>> print client.watch('/key').value
        'value'

        """
        if index:
            return self.read(key, wait=True, waitIndex=index, timeout=timeout,
                             recursive=recursive)
        else:
            return self.read(key, wait=True, timeout=timeout,
                             recursive=recursive)

    def eternal_watch(self, key, index=None):
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
            response = self.watch(key, index=local_index, timeout=0)
            if local_index is not None:
                local_index += 1
            yield response

    def get_lock(self, *args, **kwargs):
        return etcd.Lock(self, *args, **kwargs)

    @property
    def election(self):
        return etcd.LeaderElection(self)

    def _result_from_response(self, response):
        """ Creates an EtcdResult from json dictionary """
        try:
            res = json.loads(response.data.decode('utf-8'))
            r = etcd.EtcdResult(**res)
            if response.status == 201:
                r.newKey = True
            r.parse_headers(response)
            return r
        except Exception as e:
            raise etcd.EtcdException(
                'Unable to decode server response: %s' % e)

    def _next_server(self):
        """ Selects the next server in the list, refreshes the server list. """
        try:
            return self._machines_cache.pop()
        except IndexError:
            raise etcd.EtcdException('No more machines in the cluster')

    def api_execute(self, path, method, params=None, timeout=None):
        """ Executes the query. """

        some_request_failed = False
        response = False

        if timeout is None:
            timeout = self.read_timeout

        if timeout == 0:
            timeout = None

        if not path.startswith('/'):
            raise ValueError('Path does not start with /')

        while not response:
            try:
                url = self._base_uri + path

                if (method == self._MGET) or (method == self._MDELETE):
                    response = self.http.request(
                        method,
                        url,
                        timeout=timeout,
                        fields=params,
                        redirect=self.allow_redirect)

                elif (method == self._MPUT) or (method == self._MPOST):
                    response = self.http.request_encode_body(
                        method,
                        url,
                        fields=params,
                        timeout=timeout,
                        encode_multipart=False,
                        redirect=self.allow_redirect)
                else:
                    raise etcd.EtcdException(
                        'HTTP method {} not supported'.format(method))

            except urllib3.exceptions.MaxRetryError:
                self._base_uri = self._next_server()
                some_request_failed = True

        if some_request_failed:
            self._machines_cache = self.machines
            self._machines_cache.remove(self._base_uri)
        return self._handle_server_response(response)

    def _handle_server_response(self, response):
        """ Handles the server response """
        if response.status in [200, 201]:
            return response

        else:
            resp = response.data.decode('utf-8')

            # throw the appropriate exception
            try:
                r = json.loads(resp)
            except ValueError:
                r = None
            if r:
                etcd.EtcdError.handle(**r)
            else:
                raise etcd.EtcdException(resp)

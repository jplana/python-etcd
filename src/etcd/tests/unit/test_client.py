import unittest
import etcd
import dns.name
import dns.rdtypes.IN.SRV
import dns.resolver
try:
    import mock
except ImportError:
    from unittest import mock


class TestClient(unittest.TestCase):

    def test_instantiate(self):
        """ client can be instantiated"""
        client = etcd.Client()
        assert client is not None

    def test_default_host(self):
        """ default host is 127.0.0.1"""
        client = etcd.Client()
        assert client.host == "127.0.0.1"

    def test_default_port(self):
        """ default port is 4001"""
        client = etcd.Client()
        assert client.port == 4001

    def test_default_prefix(self):
        client = etcd.Client()
        assert client.version_prefix == '/v2'

    def test_default_protocol(self):
        """ default protocol is http"""
        client = etcd.Client()
        assert client.protocol == 'http'

    def test_default_read_timeout(self):
        """ default read_timeout is 60"""
        client = etcd.Client()
        assert client.read_timeout == 60

    def test_default_allow_redirect(self):
        """ default allow_redirect is True"""
        client = etcd.Client()
        assert client.allow_redirect

    def test_default_username(self):
        """ default username is None"""
        client = etcd.Client()
        assert client.username is None

    def test_default_password(self):
        """ default username is None"""
        client = etcd.Client()
        assert client.password is None

    def test_set_host(self):
        """ can change host """
        client = etcd.Client(host='192.168.1.1')
        assert client.host == '192.168.1.1'

    def test_set_port(self):
        """ can change port """
        client = etcd.Client(port=4002)
        assert client.port == 4002

    def test_set_prefix(self):
        client = etcd.Client(version_prefix='/etcd')
        assert client.version_prefix == '/etcd'

    def test_set_protocol(self):
        """ can change protocol """
        client = etcd.Client(protocol='https')
        assert client.protocol == 'https'

    def test_set_read_timeout(self):
        """ can set read_timeout """
        client = etcd.Client(read_timeout=45)
        assert client.read_timeout == 45

    def test_set_allow_redirect(self):
        """ can change allow_redirect """
        client = etcd.Client(allow_redirect=False)
        assert not client.allow_redirect

    def test_default_base_uri(self):
        """ default uri is http://127.0.0.1:4001 """
        client = etcd.Client()
        assert client.base_uri == 'http://127.0.0.1:4001'

    def test_set_base_uri(self):
        """ can change base uri """
        client = etcd.Client(
            host='192.168.1.1',
            port=4003,
            protocol='https')
        assert client.base_uri == 'https://192.168.1.1:4003'

    def test_set_use_proxies(self):
        """ can set the use_proxies flag """
        client = etcd.Client(use_proxies = True)
        assert client._use_proxies

    def test_set_username_only(self):
        client = etcd.Client(username='username')
        assert client.username is None

    def test_set_password_only(self):
        client = etcd.Client(password='password')
        assert client.password is None

    def test_set_username_password(self):
        client = etcd.Client(username='username', password='password')
        assert client.username == 'username'
        assert client.password == 'password'

    def test_get_headers_with_auth(self):
        client = etcd.Client(username='username', password='password')
        assert client._get_headers() == {
            'authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='
        }

    def test_get_headers_without_auth(self):
        client = etcd.Client()
        assert client._get_headers() == {}

    def test_allow_reconnect(self):
        """ Fails if allow_reconnect is false and a list of hosts is given"""
        with self.assertRaises(etcd.EtcdException):
            etcd.Client(
                host=(('localhost', 4001), ('localhost', 4002)),
            )
        # This doesn't raise an exception
        client = etcd.Client(
            host=(('localhost', 4001), ('localhost', 4002)),
            allow_reconnect=True,
            use_proxies=True,
        )

    def test_discover(self):
        """Tests discovery."""
        answers = []
        for i in range(1,3):
            r = mock.create_autospec(dns.rdtypes.IN.SRV.SRV)
            r.port = 2379
            try:
                method = dns.name.from_unicode
            except AttributeError:
                method = dns.name.from_text
            r.target = method(u'etcd{}.example.com'.format(i))
            answers.append(r)
        dns.resolver.query = mock.create_autospec(dns.resolver.query, return_value=answers)
        self.machines = etcd.Client.machines
        etcd.Client.machines = mock.create_autospec(etcd.Client.machines, return_value=[u'https://etcd2.example.com:2379'])
        c = etcd.Client(srv_domain="example.com", allow_reconnect=True, protocol="https")
        etcd.Client.machines = self.machines
        self.assertEquals(c.host, u'etcd1.example.com')
        self.assertEquals(c.port, 2379)
        self.assertEquals(c._machines_cache,
                          [u'https://etcd2.example.com:2379'])

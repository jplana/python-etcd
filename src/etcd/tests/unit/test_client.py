import unittest
import etcd


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

    def test_default_protocol(self):
        """ default protocol is http"""
        client = etcd.Client()
        assert client.port == 'http'

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

    def test_set_host(self):
        """ can change host """
        client = etcd.Client(host='192.168.1.1')
        assert client.host == '192.168.1.1'

    def test_set_port(self):
        """ can change port """
        client = etcd.Client(port=4002)
        assert client.port == 4002

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

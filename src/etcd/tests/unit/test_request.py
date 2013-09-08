import etcd
import unittest
import mock

from etcd import EtcdException


class TestClientRequest(unittest.TestCase):

    def test_machines(self):
        """ Can request machines """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=
            "http://127.0.0.1:4002,"
            " http://127.0.0.1:4001,"
            " http://127.0.0.1:4003,"
            " http://127.0.0.1:4001"
        )

        assert client.machines == [
            'http://127.0.0.1:4002',
            'http://127.0.0.1:4001',
            'http://127.0.0.1:4003',
            'http://127.0.0.1:4001'
        ]

    def test_leader(self):
        """ Can request the leader """
        client = etcd.Client()
        client.api_execute = mock.Mock(return_value="http://127.0.0.1:7002")
        result = client.leader
        self.assertEquals('http://127.0.0.1:7002', result)

    def test_set(self):
        """ Can set a value """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=
            '{"action":"SET",'
            '"key":"/testkey",'
            '"value":"test",'
            '"newKey":true,'
            '"expiration":"2013-09-14T00:56:59.316195568+02:00",'
            '"ttl":19,"index":183}')

        result = client.set('/testkey', 'test', ttl=19)

        self.assertEquals(
            etcd.EtcdResult(
                **{u'action': u'SET',
                   u'expiration': u'2013-09-14T00:56:59.316195568+02:00',
                   u'index': 183,
                   u'key': u'/testkey',
                   u'newKey': True,
                   u'ttl': 19,
                   u'value': u'test'}), result)

    def test_test_and_set(self):
        """ Can test and set a value """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=
            '{"action":"SET",'
            '"key":"/testkey",'
            '"prevValue":"test",'
            '"value":"newvalue",'
            '"expiration":"2013-09-14T02:09:44.24390976+02:00",'
            '"ttl":49,"index":203}')

        result = client.test_and_set('/testkey', 'newvalue', 'test', ttl=19)
        self.assertEquals(
            etcd.EtcdResult(
                **{u'action': u'SET',
                   u'expiration': u'2013-09-14T02:09:44.24390976+02:00',
                   u'index': 203,
                   u'key': u'/testkey',
                   u'prevValue': u'test',
                   u'ttl': 49,
                   u'value': u'newvalue'}), result)

    def test_test_and_test_failure(self):
        """ Exception will be raised if prevValue != value in test_set """

        client = etcd.Client()
        client.api_execute = mock.Mock(
            side_effect=ValueError(
                'The given PrevValue is not equal'
                ' to the value of the key : TestAndSet: 1!=3'))
        try:
            result = client.test_and_set(
                '/testkey',
                'newvalue',
                'test', ttl=19)
        except ValueError, e:
            #from ipdb import set_trace; set_trace()
            self.assertEquals(
                'The given PrevValue is not equal'
                ' to the value of the key : TestAndSet: 1!=3', e.message)

    def test_delete(self):
        """ Can delete a value """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=
            '{"action":"DELETE",'
            '"key":"/testkey",'
            '"prevValue":"test",'
            '"expiration":"2013-09-14T01:06:35.5242587+02:00",'
            '"index":189}')

        result = client.delete('/testkey')
        self.assertEquals(etcd.EtcdResult(
            **{u'action': u'DELETE',
               u'expiration': u'2013-09-14T01:06:35.5242587+02:00',
               u'index': 189,
               u'key': u'/testkey',
               u'prevValue': u'test'}), result)

    def test_get(self):
        """ Can get a value """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=
            '{"action":"GET",'
            '"key":"/testkey",'
            '"value":"test",'
            '"index":190}')

        result = client.get('/testkey')
        self.assertEquals(etcd.EtcdResult(
            **{u'action': u'GET',
               u'index': 190,
               u'key': u'/testkey',
               u'value': u'test'}), result)

    def test_not_in(self):
        """ Can check if key is not in client """
        client = etcd.Client()
        client.get = mock.Mock(side_effect=KeyError())
        result = '/testkey' not in client
        self.assertEquals(True, result)

    def test_in(self):
        """ Can check if key is in client """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=
            '{"action":"GET",'
            '"key":"/testkey",'
            '"value":"test",'
            '"index":190}')
        result = '/testkey' in client

        self.assertEquals(True, result)

    def test_simple_watch(self):
        """ Can watch values """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=
            '{"action":"SET",'
            '"key":"/testkey",'
            '"value":"test",'
            '"newKey":true,'
            '"expiration":"2013-09-14T01:35:07.623681365+02:00",'
            '"ttl":19,'
            '"index":192}')
        result = client.watch('/testkey')
        self.assertEquals(
            etcd.EtcdResult(
                **{u'action': u'SET',
                   u'expiration': u'2013-09-14T01:35:07.623681365+02:00',
                   u'index': 192,
                   u'key': u'/testkey',
                   u'newKey': True,
                   u'ttl': 19,
                   u'value': u'test'}), result)

    def test_index_watch(self):
        """ Can watch values from index """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=
            '{"action":"SET",'
            '"key":"/testkey",'
            '"value":"test",'
            '"newKey":true,'
            '"expiration":"2013-09-14T01:35:07.623681365+02:00",'
            '"ttl":19,'
            '"index":180}')
        result = client.watch('/testkey', index=180)
        self.assertEquals(
            etcd.EtcdResult(
                **{u'action': u'SET',
                   u'expiration': u'2013-09-14T01:35:07.623681365+02:00',
                   u'index': 180,
                   u'key': u'/testkey',
                   u'newKey': True,
                   u'ttl': 19,
                   u'value': u'test'}), result)


class TestEventGenerator(object):
    def check_watch(self, result):
        assert etcd.EtcdResult(
            **{u'action': u'SET',
               u'expiration': u'2013-09-14T01:35:07.623681365+02:00',
               u'index': 180,
               u'key': u'/testkey',
               u'newKey': True,
               u'ttl': 19,
               u'value': u'test'}) == result

    def test_ethernal_watch(self):
        """ Can watch values from generator """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=
            '{"action":"SET",'
            '"key":"/testkey",'
            '"value":"test",'
            '"newKey":true,'
            '"expiration":"2013-09-14T01:35:07.623681365+02:00",'
            '"ttl":19,'
            '"index":180}')
        for result in range(1, 5):
            result = client.ethernal_watch('/testkey', index=180).next()
            yield self.check_watch, result


class FakeHTTPResponse(object):
    def __init__(self, status, data=''):
        self.status = status
        self.data = data


class TestClientApiExecutor(unittest.TestCase):

    def test_get(self):
        """ http get request """
        client = etcd.Client()
        response = FakeHTTPResponse(status=200, data='arbitrary json data')
        client.http.request = mock.Mock(return_value=response)
        result = client.api_execute('/v1/keys/testkey', client._MGET)
        self.assertEquals('arbitrary json data', result)

    def test_delete(self):
        """ http delete request """
        client = etcd.Client()
        response = FakeHTTPResponse(status=200, data='arbitrary json data')
        client.http.request = mock.Mock(return_value=response)
        result = client.api_execute('/v1/keys/testkey', client._MDELETE)
        self.assertEquals('arbitrary json data', result)

    def test_get_error(self):
        """ http get error request 101"""
        client = etcd.Client()
        response = FakeHTTPResponse(status=400,
                                    data='{"message": "message",'
                                    ' "cause": "cause",'
                                    ' "errorCode": 100}')
        client.http.request = mock.Mock(return_value=response)
        try:
            client.api_execute('v1/keys/testkey', client._MGET)
            assert False
        except KeyError, e:
            self.assertEquals(e.message, "message : cause")

    def test_post(self):
        """ http post request """
        client = etcd.Client()
        response = FakeHTTPResponse(status=200, data='arbitrary json data')
        client.http.request_encode_body = mock.Mock(return_value=response)
        result = client.api_execute('v1/keys/testkey', client._MPOST)
        self.assertEquals('arbitrary json data', result)

    def test_test_and_set_error(self):
        """ http post error request 101 """
        client = etcd.Client()
        response = FakeHTTPResponse(
            status=400,
            data='{"message": "message", "cause": "cause", "errorCode": 101}')
        client.http.request_encode_body = mock.Mock(return_value=response)
        payload = {'value': 'value', 'prevValue': 'oldValue', 'ttl': '60'}
        try:
            client.api_execute('v1/keys/testkey', client._MPOST, payload)
            self.fail()
        except ValueError, e:
            self.assertEquals('message : cause', e.message)

    def test_set_error(self):
        """ http post error request 102 """
        client = etcd.Client()
        response = FakeHTTPResponse(
            status=400,
            data='{"message": "message", "cause": "cause", "errorCode": 102}')
        client.http.request_encode_body = mock.Mock(return_value=response)
        payload = {'value': 'value', 'prevValue': 'oldValue', 'ttl': '60'}
        try:
            client.api_execute('v1/keys/testkey', client._MPOST, payload)
            self.fail()
        except KeyError, e:
            self.assertEquals('message : cause', e.message)

    def test_set_error(self):
        """ http post error request 102 """
        client = etcd.Client()
        response = FakeHTTPResponse(
            status=400,
            data='{"message": "message", "cause": "cause", "errorCode": 102}')
        client.http.request_encode_body = mock.Mock(return_value=response)
        payload = {'value': 'value', 'prevValue': 'oldValue', 'ttl': '60'}
        try:
            client.api_execute('v1/keys/testkey', client._MPOST, payload)
            self.fail()
        except KeyError, e:
            self.assertEquals('message : cause', e.message)

    def test_get_error_unknown(self):
        """ http get error request unknown """
        client = etcd.Client()
        response = FakeHTTPResponse(status=400,
                                    data='{"message": "message",'
                                    ' "cause": "cause",'
                                    ' "errorCode": 42}')
        client.http.request = mock.Mock(return_value=response)
        try:
            client.api_execute('v1/keys/testkey', client._MGET)
            assert False
        except EtcdException, e:
            self.assertEquals(e.message, "Unable to decode server response")

    def test_get_error_request_invalid(self):
        """ http get error request invalid """
        client = etcd.Client()
        response = FakeHTTPResponse(status=200,
                                    data='{){){)*garbage*')
        client.http.request = mock.Mock(return_value=response)
        try:
            client.get('/testkey')
            assert False
        except EtcdException, e:
            self.assertEquals(e.message, "Unable to decode server response")

    def test_get_error_invalid(self):
        """ http get error request invalid """
        client = etcd.Client()
        response = FakeHTTPResponse(status=400,
                                    data='{){){)*garbage*')
        client.http.request = mock.Mock(return_value=response)
        try:
            client.api_execute('v1/keys/testkey', client._MGET)
            assert False
        except EtcdException, e:
            self.assertEquals(e.message, "Unable to decode server response")

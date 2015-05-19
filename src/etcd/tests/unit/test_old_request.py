import etcd
import unittest
try:
    import mock
except ImportError:
    from unittest import mock

from etcd import EtcdException


class FakeHTTPResponse(object):

    def __init__(self, status, data='', headers=None):
        self.status = status
        self.data = data.encode('utf-8')
        self.headers = headers or {
            "x-etcd-cluster-id": "abdef12345",
        }

    def getheaders(self):
        return self.headers

    def getheader(self, header):
        return self.headers[header]


class TestClientRequest(unittest.TestCase):

    def test_set(self):
        """ Can set a value """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=FakeHTTPResponse(201,
                                          '{"action":"SET",'
                                          '"node": {'
                                          '"key":"/testkey",'
                                          '"value":"test",'
                                          '"newKey":true,'
                                          '"expiration":"2013-09-14T00:56:59.316195568+02:00",'
                                          '"ttl":19,"modifiedIndex":183}}')
        )

        result = client.set('/testkey', 'test', ttl=19)

        self.assertEquals(
            etcd.EtcdResult(
                **{u'action': u'SET',
                   'node': {
                       u'expiration': u'2013-09-14T00:56:59.316195568+02:00',
                       u'modifiedIndex': 183,
                       u'key': u'/testkey',
                       u'newKey': True,
                       u'ttl': 19,
                       u'value': u'test'}}), result)

    def test_test_and_set(self):
        """ Can test and set a value """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=FakeHTTPResponse(200,
                                          '{"action":"SET",'
                                          '"node": {'
                                          '"key":"/testkey",'
                                          '"prevValue":"test",'
                                          '"value":"newvalue",'
                                          '"expiration":"2013-09-14T02:09:44.24390976+02:00",'
                                          '"ttl":49,"modifiedIndex":203}}')
        )
        result = client.test_and_set('/testkey', 'newvalue', 'test', ttl=19)
        self.assertEquals(
            etcd.EtcdResult(
                **{u'action': u'SET',
                   u'node': {
                       u'expiration': u'2013-09-14T02:09:44.24390976+02:00',
                       u'modifiedIndex': 203,
                       u'key': u'/testkey',
                       u'prevValue': u'test',
                       u'ttl': 49,
                       u'value': u'newvalue'}
                   }), result)

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
        except ValueError as e:
            #from ipdb import set_trace; set_trace()
            self.assertEquals(
                'The given PrevValue is not equal'
                ' to the value of the key : TestAndSet: 1!=3', str(e))

    def test_delete(self):
        """ Can delete a value """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=FakeHTTPResponse(200,
                                          '{"action":"DELETE",'
                                          '"node": {'
                                          '"key":"/testkey",'
                                          '"prevValue":"test",'
                                          '"expiration":"2013-09-14T01:06:35.5242587+02:00",'
                                          '"modifiedIndex":189}}')
        )
        result = client.delete('/testkey')
        self.assertEquals(etcd.EtcdResult(
            **{u'action': u'DELETE',
               u'node': {
                   u'expiration': u'2013-09-14T01:06:35.5242587+02:00',
                   u'modifiedIndex': 189,
                   u'key': u'/testkey',
                   u'prevValue': u'test'}
               }), result)

    def test_get(self):
        """ Can get a value """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=FakeHTTPResponse(200,
                                          '{"action":"GET",'
                                          '"node": {'
                                          '"key":"/testkey",'
                                          '"value":"test",'
                                          '"modifiedIndex":190}}')
        )

        result = client.get('/testkey')
        self.assertEquals(etcd.EtcdResult(
            **{u'action': u'GET',
               u'node': {
                   u'modifiedIndex': 190,
                   u'key': u'/testkey',
                   u'value': u'test'}
               }), result)

    def test_get_multi(self):
        """Can get multiple values"""
        pass

    def test_get_subdirs(self):
        """ Can understand dirs in results """
        pass

    def test_not_in(self):
        """ Can check if key is not in client """
        client = etcd.Client()
        client.get = mock.Mock(side_effect=etcd.EtcdKeyNotFound())
        result = '/testkey' not in client
        self.assertEquals(True, result)

    def test_in(self):
        """ Can check if key is in client """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=FakeHTTPResponse(200,
                                          '{"action":"GET",'
                                          '"node": {'
                                          '"key":"/testkey",'
                                          '"value":"test",'
                                          '"modifiedIndex":190}}')
        )
        result = '/testkey' in client

        self.assertEquals(True, result)

    def test_simple_watch(self):
        """ Can watch values """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=FakeHTTPResponse(200,
                                          '{"action":"SET",'
                                          '"node": {'
                                          '"key":"/testkey",'
                                          '"value":"test",'
                                          '"newKey":true,'
                                          '"expiration":"2013-09-14T01:35:07.623681365+02:00",'
                                          '"ttl":19,'
                                          '"modifiedIndex":192}}')
        )
        result = client.watch('/testkey')
        self.assertEquals(
            etcd.EtcdResult(
                **{u'action': u'SET',
                   u'node': {
                       u'expiration': u'2013-09-14T01:35:07.623681365+02:00',
                       u'modifiedIndex': 192,
                       u'key': u'/testkey',
                       u'newKey': True,
                       u'ttl': 19,
                       u'value': u'test'}
                   }), result)

    def test_index_watch(self):
        """ Can watch values from index """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=FakeHTTPResponse(200,
                                          '{"action":"SET",'
                                          '"node": {'
                                          '"key":"/testkey",'
                                          '"value":"test",'
                                          '"newKey":true,'
                                          '"expiration":"2013-09-14T01:35:07.623681365+02:00",'
                                          '"ttl":19,'
                                          '"modifiedIndex":180}}')
        )
        result = client.watch('/testkey', index=180)
        self.assertEquals(
            etcd.EtcdResult(
                **{u'action': u'SET',
                   u'node': {
                       u'expiration': u'2013-09-14T01:35:07.623681365+02:00',
                       u'modifiedIndex': 180,
                       u'key': u'/testkey',
                       u'newKey': True,
                       u'ttl': 19,
                       u'value': u'test'}
                   }), result)


class TestEventGenerator(object):

    def check_watch(self, result):
        assert etcd.EtcdResult(
            **{u'action': u'SET',
               u'node': {
                   u'expiration': u'2013-09-14T01:35:07.623681365+02:00',
                   u'modifiedIndex': 180,
                   u'key': u'/testkey',
                   u'newKey': True,
                   u'ttl': 19,
                   u'value': u'test'}
               }) == result

    def test_eternal_watch(self):
        """ Can watch values from generator """
        client = etcd.Client()
        client.api_execute = mock.Mock(
            return_value=FakeHTTPResponse(200,
                                          '{"action":"SET",'
                                          '"node": {'
                                          '"key":"/testkey",'
                                          '"value":"test",'
                                          '"newKey":true,'
                                          '"expiration":"2013-09-14T01:35:07.623681365+02:00",'
                                          '"ttl":19,'
                                          '"modifiedIndex":180}}')
        )
        for result in range(1, 5):
            result = next(client.eternal_watch('/testkey', index=180))
            yield self.check_watch, result


class TestClientApiExecutor(unittest.TestCase):

    def test_get(self):
        """ http get request """
        client = etcd.Client()
        response = FakeHTTPResponse(status=200, data='arbitrary json data')
        client.http.request = mock.Mock(return_value=response)
        result = client.api_execute('/v1/keys/testkey', client._MGET)
        self.assertEquals('arbitrary json data'.encode('utf-8'), result.data)

    def test_delete(self):
        """ http delete request """
        client = etcd.Client()
        response = FakeHTTPResponse(status=200, data='arbitrary json data')
        client.http.request = mock.Mock(return_value=response)
        result = client.api_execute('/v1/keys/testkey', client._MDELETE)
        self.assertEquals('arbitrary json data'.encode('utf-8'), result.data)

    def test_get_error(self):
        """ http get error request 101"""
        client = etcd.Client()
        response = FakeHTTPResponse(status=400,
                                    data='{"message": "message",'
                                    ' "cause": "cause",'
                                    ' "errorCode": 100}')
        client.http.request = mock.Mock(return_value=response)
        try:
            client.api_execute('/v2/keys/testkey', client._MGET)
            assert False
        except etcd.EtcdKeyNotFound as e:
            self.assertEquals(str(e), 'message : cause')

    def test_put(self):
        """ http put request """
        client = etcd.Client()
        response = FakeHTTPResponse(status=200, data='arbitrary json data')
        client.http.request_encode_body = mock.Mock(return_value=response)
        result = client.api_execute('/v2/keys/testkey', client._MPUT)
        self.assertEquals('arbitrary json data'.encode('utf-8'), result.data)

    def test_test_and_set_error(self):
        """ http post error request 101 """
        client = etcd.Client()
        response = FakeHTTPResponse(
            status=400,
            data='{"message": "message", "cause": "cause", "errorCode": 101}')
        client.http.request_encode_body = mock.Mock(return_value=response)
        payload = {'value': 'value', 'prevValue': 'oldValue', 'ttl': '60'}
        try:
            client.api_execute('/v2/keys/testkey', client._MPUT, payload)
            self.fail()
        except ValueError as e:
            self.assertEquals('message : cause', str(e))

    def test_set_not_file_error(self):
        """ http post error request 102 """
        client = etcd.Client()
        response = FakeHTTPResponse(
            status=400,
            data='{"message": "message", "cause": "cause", "errorCode": 102}')
        client.http.request_encode_body = mock.Mock(return_value=response)
        payload = {'value': 'value', 'prevValue': 'oldValue', 'ttl': '60'}
        try:
            client.api_execute('/v2/keys/testkey', client._MPUT, payload)
            self.fail()
        except etcd.EtcdNotFile as e:
            self.assertEquals('message : cause', str(e))

    def test_get_error_unknown(self):
        """ http get error request unknown """
        client = etcd.Client()
        response = FakeHTTPResponse(status=400,
                                    data='{"message": "message",'
                                         ' "cause": "cause",'
                                         ' "errorCode": 42}')
        client.http.request = mock.Mock(return_value=response)
        try:
            client.api_execute('/v2/keys/testkey', client._MGET)
            self.fail()
        except etcd.EtcdException as e:
            self.assertEqual(str(e), "message : cause")

    def test_get_error_request_invalid(self):
        """ http get error request invalid """
        client = etcd.Client()
        response = FakeHTTPResponse(status=400,
                                    data='{)*garbage')
        client.http.request = mock.Mock(return_value=response)
        try:
            client.api_execute('/v2/keys/testkey', client._MGET)
            self.fail()
        except etcd.EtcdException as e:
            self.assertEqual(str(e),
                             "Bad response : {)*garbage")

    def test_get_error_invalid(self):
        """ http get error request invalid """
        client = etcd.Client()
        response = FakeHTTPResponse(status=400,
                                    data='{){){)*garbage*')
        client.http.request = mock.Mock(return_value=response)
        self.assertRaises(etcd.EtcdException, client.api_execute,
                          '/v2/keys/testkey', client._MGET)

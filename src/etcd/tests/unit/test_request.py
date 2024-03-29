import socket
import urllib3

import etcd
from etcd.tests.unit import TestClientApiBase

try:
    import mock
except ImportError:
    from unittest import mock


class TestClientApiInternals(TestClientApiBase):
    def test_read_default_timeout(self):
        """Read timeout set to the default"""
        d = {
            "action": "get",
            "node": {"modifiedIndex": 190, "key": "/testkey", "value": "test"},
        }
        self._mock_api(200, d)
        res = self.client.read("/testkey")
        self.assertEqual(self.client.api_execute.call_args[1]["timeout"], None)

    def test_read_custom_timeout(self):
        """Read timeout set to the supplied value"""
        d = {
            "action": "get",
            "node": {"modifiedIndex": 190, "key": "/testkey", "value": "test"},
        }
        self._mock_api(200, d)
        self.client.read("/testkey", timeout=15)
        self.assertEqual(self.client.api_execute.call_args[1]["timeout"], 15)

    def test_read_no_timeout(self):
        """Read timeout disabled"""
        d = {
            "action": "get",
            "node": {"modifiedIndex": 190, "key": "/testkey", "value": "test"},
        }
        self._mock_api(200, d)
        self.client.read("/testkey", timeout=0)
        self.assertEqual(self.client.api_execute.call_args[1]["timeout"], 0)

    def test_write_no_params(self):
        """Calling `write` without a value argument will omit the `value` from
        the API call params"""
        d = {
            "action": "set",
            "node": {
                "createdIndex": 17,
                "dir": True,
                "key": "/newdir",
                "modifiedIndex": 17,
            },
        }
        self._mock_api(200, d)
        self.client.write("/newdir", None, dir=True)
        self.assertEqual(
            self.client.api_execute.call_args,
            (("/v2/keys/newdir", "PUT"), dict(params={"dir": "true"})),
        )


class TestClientApiInterface(TestClientApiBase):
    """
    All tests defined in this class are executed also in TestClientRequest.

    If a test should be run only in this class, please override the method there.
    """

    def test_machines(self):
        """Can request machines"""
        data = [
            "http://127.0.0.1:4001",
            "http://127.0.0.1:4002",
            "http://127.0.0.1:4003",
        ]
        d = ",".join(data)
        self.client.http.request = mock.MagicMock(return_value=self._prepare_response(200, d))
        self.assertEqual(data, self.client.machines)

    @mock.patch("etcd.Client.machines", new_callable=mock.PropertyMock)
    def test_use_proxies(self, mocker):
        """Do not overwrite the machines cache when using proxies"""
        mocker.return_value = [
            "https://10.0.0.2:4001",
            "https://10.0.0.3:4001",
            "https://10.0.0.4:4001",
        ]
        c = etcd.Client(
            host=(("localhost", 4001), ("localproxy", 4001)),
            protocol="https",
            allow_reconnect=True,
            use_proxies=True,
        )

        self.assertEqual(c._machines_cache, ["https://localproxy:4001"])
        self.assertEqual(c._base_uri, "https://localhost:4001")
        self.assertNotIn(c.base_uri, c._machines_cache)

        c = etcd.Client(
            host=(("localhost", 4001), ("10.0.0.2", 4001)),
            protocol="https",
            allow_reconnect=True,
            use_proxies=False,
        )
        self.assertIn("https://10.0.0.3:4001", c._machines_cache)
        self.assertNotIn(c.base_uri, c._machines_cache)

    def test_members(self):
        """Can request machines"""
        data = {
            "members": [
                {
                    "id": "ce2a822cea30bfca",
                    "name": "default",
                    "peerURLs": ["http://localhost:2380", "http://localhost:7001"],
                    "clientURLs": ["http://127.0.0.1:4001"],
                }
            ]
        }
        self._mock_api(200, data)
        self.assertEqual(self.client.members["ce2a822cea30bfca"]["id"], "ce2a822cea30bfca")

    def test_self_stats(self):
        """Request for stats"""
        data = {
            "id": "eca0338f4ea31566",
            "leaderInfo": {
                "leader": "8a69d5f6b7814500",
                "startTime": "2014-10-24T13:15:51.186620747-07:00",
                "uptime": "10m59.322358947s",
            },
            "name": "node3",
            "recvAppendRequestCnt": 5944,
            "recvBandwidthRate": 570.6254930219969,
            "recvPkgRate": 9.00892789741075,
            "sendAppendRequestCnt": 0,
            "startTime": "2014-10-24T13:15:50.072007085-07:00",
            "state": "StateFollower",
        }
        self._mock_api(200, data)
        self.assertEqual(self.client.stats["name"], "node3")

    def test_leader_stats(self):
        """Request for leader stats"""
        data = {"leader": "924e2e83e93f2560", "followers": {}}
        self._mock_api(200, data)
        self.assertEqual(self.client.leader_stats["leader"], "924e2e83e93f2560")

    @mock.patch("etcd.Client.members", new_callable=mock.PropertyMock)
    def test_leader(self, mocker):
        """Can request the leader"""
        members = {"ce2a822cea30bfca": {"id": "ce2a822cea30bfca", "name": "default"}}
        mocker.return_value = members
        self._mock_api(200, {"leaderInfo": {"leader": "ce2a822cea30bfca", "followers": {}}})
        self.assertEqual(self.client.leader, members["ce2a822cea30bfca"])

    def test_set_plain(self):
        """Can set a value"""
        d = {
            "action": "set",
            "node": {
                "expiration": "2013-09-14T00:56:59.316195568+02:00",
                "modifiedIndex": 183,
                "key": "/testkey",
                "ttl": 19,
                "value": "test",
            },
        }

        self._mock_api(200, d)
        res = self.client.write("/testkey", "test")
        self.assertEqual(res, etcd.EtcdResult(**d))

    def test_update(self):
        """Can update a result."""
        d = {
            "action": "set",
            "node": {
                "expiration": "2013-09-14T00:56:59.316195568+02:00",
                "modifiedIndex": 6,
                "key": "/testkey",
                "ttl": 19,
                "value": "test",
            },
        }
        self._mock_api(200, d)
        res = self.client.get("/testkey")
        res.value = "ciao"
        d["node"]["value"] = "ciao"
        self._mock_api(200, d)
        newres = self.client.update(res)
        self.assertEqual(newres.value, "ciao")

    def test_newkey(self):
        """Can set a new value"""
        d = {
            "action": "set",
            "node": {
                "expiration": "2013-09-14T00:56:59.316195568+02:00",
                "modifiedIndex": 183,
                "key": "/testkey",
                "ttl": 19,
                "value": "test",
            },
        }
        self._mock_api(201, d)
        res = self.client.write("/testkey", "test")
        d["node"]["newKey"] = True
        self.assertEqual(res, etcd.EtcdResult(**d))

    def test_refresh(self):
        """Can refresh a new value"""
        d = {
            "action": "update",
            "node": {
                "expiration": "2016-05-31T08:27:54.660337Z",
                "modifiedIndex": 183,
                "key": "/testkey",
                "ttl": 600,
                "value": "test",
            },
        }

        self._mock_api(200, d)
        res = self.client.refresh("/testkey", ttl=600)
        self.assertEqual(res, etcd.EtcdResult(**d))

    def test_not_found_response(self):
        """Can handle server not found response"""
        self._mock_api(404, "Not found")
        self.assertRaises(etcd.EtcdException, self.client.read, "/somebadkey")

    def test_compare_and_swap(self):
        """Can set compare-and-swap a value"""
        d = {
            "action": "compareAndSwap",
            "node": {
                "expiration": "2013-09-14T00:56:59.316195568+02:00",
                "modifiedIndex": 183,
                "key": "/testkey",
                "ttl": 19,
                "value": "test",
            },
        }

        self._mock_api(200, d)
        res = self.client.write("/testkey", "test", prevValue="test_old")
        self.assertEqual(res, etcd.EtcdResult(**d))

    def test_compare_and_swap_failure(self):
        """Exception will be raised if prevValue != value in test_set"""
        self._mock_exception(ValueError, "Test Failed : [ 1!=3 ]")
        self.assertRaises(ValueError, self.client.write, "/testKey", "test", prevValue="oldbog")

    def test_set_append(self):
        """Can append a new key"""
        d = {
            "action": "create",
            "node": {
                "createdIndex": 190,
                "modifiedIndex": 190,
                "key": "/testdir/190",
                "value": "test",
            },
        }
        self._mock_api(201, d)
        res = self.client.write("/testdir", "test")
        self.assertEqual(res.createdIndex, 190)

    def test_set_dir_with_value(self):
        """Creating a directory with a value raises an error."""
        self.assertRaises(etcd.EtcdException, self.client.write, "/bar", "testvalye", dir=True)

    def test_delete(self):
        """Can delete a value"""
        d = {
            "action": "delete",
            "node": {"key": "/testkey", "modifiedIndex": 3, "createdIndex": 2},
        }
        self._mock_api(200, d)
        res = self.client.delete("/testKey")
        self.assertEqual(res, etcd.EtcdResult(**d))

    def test_pop(self):
        """Can pop a value"""
        d = {
            "action": "delete",
            "node": {"key": "/testkey", "modifiedIndex": 3, "createdIndex": 2},
            "prevNode": {
                "newKey": False,
                "createdIndex": None,
                "modifiedIndex": 190,
                "value": "test",
                "expiration": None,
                "key": "/testkey",
                "ttl": None,
                "dir": False,
            },
        }

        self._mock_api(200, d)
        res = self.client.pop(d["node"]["key"])
        self.assertEqual(
            {attr: getattr(res, attr) for attr in dir(res) if attr in etcd.EtcdResult._node_props},
            d["prevNode"],
        )
        self.assertEqual(res.value, d["prevNode"]["value"])

    def test_read(self):
        """Can get a value"""
        d = {
            "action": "get",
            "node": {"modifiedIndex": 190, "key": "/testkey", "value": "test"},
        }
        self._mock_api(200, d)
        res = self.client.read("/testKey")
        self.assertEqual(res, etcd.EtcdResult(**d))

    def test_get_dir(self):
        """Can get values in dirs"""
        d = {
            "action": "get",
            "node": {
                "modifiedIndex": 190,
                "key": "/testkey",
                "dir": True,
                "nodes": [
                    {"key": "/testDir/testKey", "modifiedIndex": 150, "value": "test"},
                    {
                        "key": "/testDir/testKey2",
                        "modifiedIndex": 190,
                        "value": "test2",
                    },
                ],
            },
        }
        self._mock_api(200, d)
        res = self.client.read("/testDir", recursive=True)
        self.assertEqual(res, etcd.EtcdResult(**d))

    def test_not_in(self):
        """Can check if key is not in client"""
        self._mock_exception(etcd.EtcdKeyNotFound, "Key not Found : /testKey")
        self.assertTrue("/testey" not in self.client)

    def test_in(self):
        """Can check if key is not in client"""
        d = {
            "action": "get",
            "node": {"modifiedIndex": 190, "key": "/testkey", "value": "test"},
        }
        self._mock_api(200, d)
        self.assertTrue("/testey" in self.client)

    def test_watch(self):
        """Can watch a key"""
        d = {
            "action": "get",
            "node": {"modifiedIndex": 190, "key": "/testkey", "value": "test"},
        }
        self._mock_api(200, d)
        res = self.client.read("/testkey", wait=True)
        self.assertEqual(res, etcd.EtcdResult(**d))

    def test_watch_index(self):
        """Can watch a key starting from the given Index"""
        d = {
            "action": "get",
            "node": {"modifiedIndex": 170, "key": "/testkey", "value": "testold"},
        }
        self._mock_api(200, d)
        res = self.client.read("/testkey", wait=True, waitIndex=True)
        self.assertEqual(res, etcd.EtcdResult(**d))


class TestClientRequest(TestClientApiInterface):
    def setUp(self):
        self.client = etcd.Client(expected_cluster_id="abcdef1234")

    def _mock_api(self, status, d, cluster_id=None):
        resp = self._prepare_response(status, d)
        resp.getheader.return_value = cluster_id or "abcdef1234"
        self.client.http.request_encode_body = mock.MagicMock(return_value=resp)
        self.client.http.request = mock.MagicMock(return_value=resp)

    def _mock_error(self, error_code, msg, cause, method="PUT", fields=None, cluster_id=None):
        resp = self._prepare_response(
            500, {"errorCode": error_code, "message": msg, "cause": cause}
        )
        resp.getheader.return_value = cluster_id or "abcdef1234"
        self.client.http.request_encode_body = mock.create_autospec(
            self.client.http.request_encode_body, return_value=resp
        )
        self.client.http.request = mock.create_autospec(self.client.http.request, return_value=resp)

    def test_compare_and_swap_failure(self):
        """Exception will be raised if prevValue != value in test_set"""
        self._mock_error(200, "Test Failed", "[ 1!=3 ]", fields={"prevValue": "oldbog"})
        self.assertRaises(ValueError, self.client.write, "/testKey", "test", prevValue="oldbog")

    def test_watch_timeout(self):
        """Exception will be raised if prevValue != value in test_set"""
        self.client.http.request = mock.create_autospec(
            self.client.http.request,
            side_effect=urllib3.exceptions.ReadTimeoutError(
                self.client.http, "foo", "Read timed out"
            ),
        )
        self.assertRaises(
            etcd.EtcdWatchTimedOut,
            self.client.watch,
            "/testKey",
        )

    def test_path_without_trailing_slash(self):
        """Exception will be raised if a path without a trailing slash is used"""
        self.assertRaises(ValueError, self.client.api_execute, "testpath/bar", self.client._MPUT)

    def test_api_method_not_supported(self):
        """Exception will be raised if an unsupported HTTP method is used"""
        self.assertRaises(etcd.EtcdException, self.client.api_execute, "/testpath/bar", "TRACE")

    def test_read_cluster_id_changed(self):
        """Read timeout set to the default"""
        d = {
            "action": "set",
            "node": {
                "expiration": "2013-09-14T00:56:59.316195568+02:00",
                "modifiedIndex": 6,
                "key": "/testkey",
                "ttl": 19,
                "value": "test",
            },
        }
        self._mock_api(200, d, cluster_id="notabcd1234")
        self.assertRaises(etcd.EtcdClusterIdChanged, self.client.read, "/testkey")
        self.client.read("/testkey")

    def test_read_connection_error(self):
        self.client.http.request = mock.create_autospec(
            self.client.http.request, side_effect=socket.error()
        )
        self.assertRaises(etcd.EtcdConnectionFailed, self.client.read, "/something")
        # Direct GET request
        self.assertRaises(etcd.EtcdConnectionFailed, self.client.api_execute, "/a", "GET")

    def test_not_in(self):
        pass

    def test_in(self):
        pass

    def test_update_fails(self):
        """Non-atomic updates fail"""
        d = {
            "action": "set",
            "node": {
                "expiration": "2013-09-14T00:56:59.316195568+02:00",
                "modifiedIndex": 6,
                "key": "/testkey",
                "ttl": 19,
                "value": "test",
            },
        }
        res = etcd.EtcdResult(**d)

        error = {
            "errorCode": 101,
            "message": "Compare failed",
            "cause": "[ != bar] [7 != 6]",
            "index": 6,
        }
        self._mock_api(412, error)
        res.value = "bar"
        self.assertRaises(ValueError, self.client.update, res)

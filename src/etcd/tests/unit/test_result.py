import etcd
import unittest
import json
import urllib3

try:
    import mock
except ImportError:
    from unittest import mock

class TestEtcdResult(unittest.TestCase):

    def test_get_subtree_1_level(self):
        """
        Test get_subtree() for a read with tree 1 level deep.
        """
        response = {"node": {
            'key': "/test",
            'value': "hello",
            'expiration': None,
            'ttl': None,
            'modifiedIndex': 5,
            'createdIndex': 1,
            'newKey': False,
            'dir': False,
        }}
        result = etcd.EtcdResult(**response)
        self.assertEqual(result.key, response["node"]["key"])
        self.assertEqual(result.value, response["node"]["value"])

        # Get subtree returns itself, whether or not leaves_only
        subtree = list(result.get_subtree(leaves_only=True))
        self.assertListEqual([result], subtree)
        subtree = list(result.get_subtree(leaves_only=False))
        self.assertListEqual([result], subtree)

    def test_get_subtree_2_level(self):
        """
        Test get_subtree() for a read with tree 2 levels deep.
        """
        leaf0 = {
            'key': "/test/leaf0",
            'value': "hello1",
            'expiration': None,
            'ttl': None,
            'modifiedIndex': 5,
            'createdIndex': 1,
            'newKey': False,
            'dir': False,
        }
        leaf1 = {
            'key': "/test/leaf1",
            'value': "hello2",
            'expiration': None,
            'ttl': None,
            'modifiedIndex': 6,
            'createdIndex': 2,
            'newKey': False,
            'dir': False,
        }
        testnode = {"node": {
            'key': "/test/",
            'expiration': None,
            'ttl': None,
            'modifiedIndex': 6,
            'createdIndex': 2,
            'newKey': False,
            'dir': True,
            'nodes': [leaf0, leaf1]
        }}
        result = etcd.EtcdResult(**testnode)
        self.assertEqual(result.key, "/test/")
        self.assertTrue(result.dir)

        # Get subtree returns just two leaves for leaves only.
        subtree = list(result.get_subtree(leaves_only=True))
        self.assertEqual(subtree[0].key, "/test/leaf0")
        self.assertEqual(subtree[1].key, "/test/leaf1")
        self.assertEqual(len(subtree), 2)

        # Get subtree returns leaves and directory.
        subtree = list(result.get_subtree(leaves_only=False))
        self.assertEqual(subtree[0].key, "/test/")
        self.assertEqual(subtree[1].key, "/test/leaf0")
        self.assertEqual(subtree[2].key, "/test/leaf1")
        self.assertEqual(len(subtree), 3)

    def test_get_subtree_3_level(self):
        """
        Test get_subtree() for a read with tree 3 levels deep.
        """
        leaf0 = {
            'key': "/test/mid0/leaf0",
            'value': "hello1",
        }
        leaf1 = {
            'key': "/test/mid0/leaf1",
            'value': "hello2",
        }
        leaf2 = {
            'key': "/test/mid1/leaf2",
            'value': "hello1",
        }
        leaf3 = {
            'key': "/test/mid1/leaf3",
            'value': "hello2",
        }
        mid0 = {
            'key': "/test/mid0/",
            'dir': True,
            'nodes': [leaf0, leaf1]
        }
        mid1 = {
            'key': "/test/mid1/",
            'dir': True,
            'nodes': [leaf2, leaf3]
        }
        testnode = {"node": {
            'key': "/test/",
            'dir': True,
            'nodes': [mid0, mid1]
        }}
        result = etcd.EtcdResult(**testnode)
        self.assertEqual(result.key, "/test/")
        self.assertTrue(result.dir)

        # Get subtree returns just two leaves for leaves only.
        subtree = list(result.get_subtree(leaves_only=True))
        self.assertEqual(subtree[0].key, "/test/mid0/leaf0")
        self.assertEqual(subtree[1].key, "/test/mid0/leaf1")
        self.assertEqual(subtree[2].key, "/test/mid1/leaf2")
        self.assertEqual(subtree[3].key, "/test/mid1/leaf3")
        self.assertEqual(len(subtree), 4)

        # Get subtree returns leaves and directory.
        subtree = list(result.get_subtree(leaves_only=False))
        self.assertEqual(subtree[0].key, "/test/")
        self.assertEqual(subtree[1].key, "/test/mid0/")
        self.assertEqual(subtree[2].key, "/test/mid0/leaf0")
        self.assertEqual(subtree[3].key, "/test/mid0/leaf1")
        self.assertEqual(subtree[4].key, "/test/mid1/")
        self.assertEqual(subtree[5].key, "/test/mid1/leaf2")
        self.assertEqual(subtree[6].key, "/test/mid1/leaf3")
        self.assertEqual(len(subtree), 7)

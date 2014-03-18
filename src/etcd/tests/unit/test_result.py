import unittest

from etcd import EtcdResult


class TestEtcdResult(unittest.TestCase):
    def test_no_children(self):
        " No children returned "
        single = {
            u'action': u'get',
            u'node': {
                u'createdIndex': 190,
                u'key': u'/testkey',
                u'modifiedIndex': 190,
                u'value': u'test'
            }
        }
        result = EtcdResult(**single)
        self.assertEqual(list(result.children), [])

    def test_children(self):
        " Children returned "
        children = [{
            u'createdIndex': 191,
            u'key': u'/testkey/testChildOne',
            u'modifiedIndex': 191,
            u'value': u'test'
        }, {
            u'createdIndex': 192,
            u'modifiedIndex': 192,
            u'key': u'/testkey/testChildTwo',
            u'value': u'test'
        }]
        parent = {
            u'action': u'get',
            u'node': {
                u'createdIndex': 190,
                u'dir': u'true',
                u'key': u'/testkey',
                u'modifiedIndex': 190,
                u'nodes': children,
            }
        }
        result = EtcdResult(**parent)
        child_results = [EtcdResult(None, child) for child in children]
        self.assertEqual(list(result.children), child_results)

    def test_grand_children(self):
        " Children and grand children returned "
        grand_children = [{
            u'createdIndex': 193,
            u'key': u'/testkey/testChildOne/testGrandChild',
            u'modifiedIndex': 193,
            u'value': u'test'
        }]
        children = [{
            u'createdIndex': 191,
            u'dir': u'true',
            u'key': u'/testkey/testChildOne',
            u'modifiedIndex': 191,
            u'nodes': grand_children,
        }, {
            u'createdIndex': 192,
            u'modifiedIndex': 192,
            u'key': u'/testkey/testChildTwo',
            u'value': u'test'
        }]
        parent = {
            u'action': u'get',
            u'node': {
                u'createdIndex': 190,
                u'dir': u'true',
                u'key': u'/testkey',
                u'modifiedIndex': 190,
                u'nodes': children,
            }
        }
        result = EtcdResult(**parent)
        child_results = [EtcdResult(None, child) for child in children]
        self.assertEqual(list(result.children), child_results)

        # may not be necessary, but still good to check 3 levels of recursion
        grand_child_result = EtcdResult(None, grand_children[0])
        self.assertEqual(list(child_results[0].children), [grand_child_result])
        self.assertEqual(list(child_results[1].children), [])

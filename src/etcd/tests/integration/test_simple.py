import os
import time
import logging
import unittest
import multiprocessing

import etcd
import helpers

from nose.tools import nottest

log = logging.getLogger()


class EtcdIntegrationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        program = cls._get_exe()

        cls.processHelper = helpers.EtcdProcessHelper(
            proc_name=program,
            port_range_start=6001,
            internal_port_range_start=8001)
        cls.processHelper.run(number=3)
        cls.client = etcd.Client(port=6001)

    @classmethod
    def tearDownClass(cls):
        cls.processHelper.stop()

    @classmethod
    def _is_exe(cls, fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    @classmethod
    def _get_exe(cls):
        PROGRAM = 'etcd'

        program_path = None

        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, PROGRAM)
            if cls._is_exe(exe_file):
                program_path = exe_file
                break

        if not program_path:
            raise Exception('etcd not in path!!')

        return program_path


class TestSimple(EtcdIntegrationTest):

    def test_machines(self):
        """ INTEGRATION: retrieve machines """
        self.assertEquals(self.client.machines, ['http://127.0.0.1:6001'])

    def test_leader(self):
        """ INTEGRATION: retrieve leader """
        self.assertEquals(self.client.leader, 'http://127.0.0.1:8001')

    def test_get_set_delete(self):
        """ INTEGRATION: set a new value """
        try:
            get_result = self.client.get('/test_set')
            assert False
        except KeyError, e:
            pass

        self.assertNotIn('/test_set', self.client)

        set_result = self.client.set('/test_set', 'test-key')
        self.assertEquals('SET', set_result.action)
        self.assertEquals('/test_set', set_result.key)
        self.assertEquals(True, set_result.newKey)
        self.assertEquals('test-key', set_result.value)

        self.assertIn('/test_set', self.client)

        get_result = self.client.get('/test_set')
        self.assertEquals('GET', get_result.action)
        self.assertEquals('/test_set', get_result.key)
        self.assertEquals('test-key', get_result.value)

        delete_result = self.client.delete('/test_set')
        self.assertEquals('DELETE', delete_result.action)
        self.assertEquals('/test_set', delete_result.key)
        self.assertEquals('test-key', delete_result.prevValue)

        self.assertNotIn('/test_set', self.client)

        try:
            get_result = self.client.get('/test_set')
            assert False
        except KeyError, e:
            pass


class TestErrors(EtcdIntegrationTest):

    def test_is_not_a_file(self):
        """ INTEGRATION: try to write  value to a directory """

        set_result = self.client.set('/directory/test-key', 'test-value')

        try:
            get_result = self.client.set('/directory', 'test-value')
            assert False
        except KeyError, e:
            pass

    def test_test_and_set(self):
        """ INTEGRATION: try test_and_set operation """

        set_result = self.client.set('/test-key', 'old-test-value')

        set_result = self.client.test_and_set(
            '/test-key',
            'test-value',
            'old-test-value')

        try:
            set_result = self.client.test_and_set(
                '/test-key',
                'new-value',
                'old-test-value')

            assert False
        except ValueError, e:
            pass


class TestWatch(EtcdIntegrationTest):

    def test_watch(self):
        """ INTEGRATION: Receive a watch event from other process """

        set_result = self.client.set('/test-key', 'test-value')

        queue = multiprocessing.Queue()

        def change_value(key, newValue):
            c = etcd.Client(port=6001)
            c.set(key, newValue)

        def watch_value(key, queue):
            c = etcd.Client(port=6001)
            queue.put(c.watch(key).value)

        changer = multiprocessing.Process(
            target=change_value, args=('/test-key', 'new-test-value',))

        watcher = multiprocessing.Process(
            target=watch_value, args=('/test-key', queue))

        watcher.start()
        time.sleep(1)

        changer.start()

        value = queue.get(timeout=2)
        watcher.join(timeout=5)
        changer.join(timeout=5)

        assert value == 'new-test-value'

    def test_watch_indexed(self):
        """ INTEGRATION: Receive a watch event from other process, indexed """

        set_result = self.client.set('/test-key', 'test-value')
        set_result = self.client.set('/test-key', 'test-value0')
        original_index = int(set_result.index)
        set_result = self.client.set('/test-key', 'test-value1')
        set_result = self.client.set('/test-key', 'test-value2')

        queue = multiprocessing.Queue()

        def change_value(key, newValue):
            c = etcd.Client(port=6001)
            c.set(key, newValue)
            c.get(key)

        def watch_value(key, index, queue):
            c = etcd.Client(port=6001)
            for i in range(0, 3):
                queue.put(c.watch(key, index=index+i).value)

        proc = multiprocessing.Process(
            target=change_value, args=('/test-key', 'test-value3',))

        watcher = multiprocessing.Process(
            target=watch_value, args=('/test-key', original_index, queue))

        watcher.start()
        time.sleep(0.5)

        proc.start()

        for i in range(0, 3):
            value = queue.get()
            log.debug("index: %d: %s" % (i, value))
            self.assertEquals('test-value%d' % i, value)

        watcher.join(timeout=5)
        proc.join(timeout=5)

    def test_watch_generator(self):
        """ INTEGRATION: Receive a watch event from other process (gen) """

        set_result = self.client.set('/test-key', 'test-value')

        queue = multiprocessing.Queue()

        def change_value(key):
            time.sleep(0.5)
            c = etcd.Client(port=6001)
            for i in range(0, 3):
                c.set(key, 'test-value%d' % i)
                c.get(key)

        def watch_value(key, queue):
            c = etcd.Client(port=6001)
            for i in range(0, 3):
                event = c.ethernal_watch(key).next().value
                queue.put(event)

        changer = multiprocessing.Process(
            target=change_value, args=('/test-key',))

        watcher = multiprocessing.Process(
            target=watch_value, args=('/test-key', queue))

        watcher.start()
        changer.start()

        values = ['test-value0', 'test-value1', 'test-value2']
        for i in range(0, 1):
            value = queue.get()
            log.debug("index: %d: %s" % (i, value))
            self.assertIn(value, values)

        watcher.join(timeout=5)
        changer.join(timeout=5)

    def test_watch_indexed_generator(self):
        """ INTEGRATION: Receive a watch event from other process, ixd, (2) """

        set_result = self.client.set('/test-key', 'test-value')
        set_result = self.client.set('/test-key', 'test-value0')
        original_index = int(set_result.index)
        set_result = self.client.set('/test-key', 'test-value1')
        set_result = self.client.set('/test-key', 'test-value2')

        queue = multiprocessing.Queue()

        def change_value(key, newValue):
            c = etcd.Client(port=6001)
            c.set(key, newValue)

        def watch_value(key, index, queue):
            c = etcd.Client(port=6001)
            iterevents = c.ethernal_watch(key, index=index)
            for i in range(0, 3):
                queue.put(iterevents.next().value)

        proc = multiprocessing.Process(
            target=change_value, args=('/test-key', 'test-value3',))

        watcher = multiprocessing.Process(
            target=watch_value, args=('/test-key', original_index, queue))

        watcher.start()
        time.sleep(0.5)
        proc.start()

        for i in range(0, 3):
            value = queue.get()
            log.debug("index: %d: %s" % (i, value))
            self.assertEquals('test-value%d' % i, value)

        watcher.join(timeout=5)
        proc.join(timeout=5)

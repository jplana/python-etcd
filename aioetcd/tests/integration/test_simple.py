import os
import time
import shutil
import logging
import unittest
import tempfile
import pytest

import aioetcd
from . import helpers

log = logging.getLogger()

class EtcdIntegrationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        program = cls._get_exe()
        cls.directory = tempfile.mkdtemp(prefix='python-aioetcd')
        cls.processHelper = helpers.EtcdProcessHelper(
            cls.directory,
            proc_name=program,
            port_range_start=6001,
            internal_port_range_start=8001)
        cls.processHelper.run(number=3)
        cls.client = aioetcd.Client(port=6001)

    @classmethod
    def tearDownClass(cls):
        cls.processHelper.stop()
        shutil.rmtree(cls.directory)

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
            raise Exception('aioetcd not in path!!')

        return program_path


class TestSimple(EtcdIntegrationTest):

    @pytest.mark.asyncio
    def test_machines(self):
        """ INTEGRATION: retrieve machines """
        self.assertEquals((yield from self.client.machines())[0], 'http://127.0.0.1:6001')

    @pytest.mark.asyncio
    def test_leader(self):
        """ INTEGRATION: retrieve leader """
        self.assertEquals((yield from self.client.leader())['clientURLs'], ['http://127.0.0.1:6001'])

    @pytest.mark.asyncio
    def test_get_set_delete(self):
        """ INTEGRATION: set a new value """
        import pdb;pdb.set_trace()
        try:
            get_result = yield from self.client.get('/test_set')
            assert False
        except aioetcd.EtcdKeyNotFound as e:
            pass

        self.assertFalse((yield from self.client.contains('/test_set')))

        set_result = yield from self.client.set('/test_set', 'test-key')
        self.assertEquals('set', set_result.action.lower())
        self.assertEquals('/test_set', set_result.key)
        self.assertEquals('test-key', set_result.value)

        self.assertTrue((yield from self.client.contains('/test_set')))

        get_result = yield from self.client.get('/test_set')
        self.assertEquals('get', get_result.action.lower())
        self.assertEquals('/test_set', get_result.key)
        self.assertEquals('test-key', get_result.value)

        delete_result = yield from self.client.delete('/test_set')
        self.assertEquals('delete', delete_result.action.lower())
        self.assertEquals('/test_set', delete_result.key)

        self.assertFalse((yield from self.client.contains('/test_set')))

        try:
            get_result = yield from self.client.get('/test_set')
            assert False
        except aioetcd.EtcdKeyNotFound as e:
            pass

    @pytest.mark.asyncio
    def test_update(self):
        """INTEGRATION: update a value"""
        yield from self.client.set('/foo', 3)
        c = yield from self.client.get('/foo')
        c.value = int(c.value) + 3
        yield from self.client.update(c)
        newres = yield from self.client.get('/foo')
        self.assertEquals(newres.value, u'6')
        try:
            yield from self.client.update(c)
            assert False
        except ValueError:
            pass

    @pytest.mark.asyncio
    def test_retrieve_subkeys(self):
        """ INTEGRATION: retrieve multiple subkeys """
        set_result = yield from self.client.write('/subtree/test_set', 'test-key1')
        set_result = yield from self.client.write('/subtree/test_set1', 'test-key2')
        set_result = yield from self.client.write('/subtree/test_set2', 'test-key3')
        get_result = yield from self.client.read('/subtree', recursive=True)
        result = [subkey.value for subkey in get_result.leaves]
        self.assertEquals(['test-key1', 'test-key2', 'test-key3'].sort(), result.sort())

    @pytest.mark.asyncio
    def test_directory_ttl_update(self):
        """ INTEGRATION: should be able to update a dir TTL """
        yield from self.client.write('/dir', None, dir=True, ttl=30)
        res = yield from self.client.write('/dir', None, dir=True, ttl=31, prevExist=True)
        self.assertEquals(res.ttl, 31)
        res = yield from self.client.get('/dir')
        res.ttl = 120
        new_res = yield from self.client.update(res)
        self.assertEquals(new_res.ttl, 120)



class TestErrors(EtcdIntegrationTest):

    @pytest.mark.asyncio
    def test_is_not_a_file(self):
        """ INTEGRATION: try to write  value to an existing directory """

        yield from self.client.set('/directory/test-key', 'test-value')
        try:
            yield from self.client.set('/directory', 'test-value')
            raise False
        except aioetcd.EtcdNotFile:
            pass

    @pytest.mark.asyncio
    def test_test_and_set(self):
        """ INTEGRATION: try test_and_set operation """

        set_result = yield from self.client.set('/test-key', 'old-test-value')

        set_result = yield from self.client.test_and_set(
            '/test-key',
            'test-value',
            'old-test-value')

        try:
            yield from self.client.test_and_set('/test-key', 'new-value', 'old-test-value')
        except ValueError:
            pass

    @pytest.mark.asyncio
    def test_creating_already_existing_directory(self):
        """ INTEGRATION: creating an already existing directory without
        `prevExist=True` should fail """
        yield from self.client.write('/mydir', None, dir=True)

        try:
            yield from self.client.write('/mydir', None, dir=True)
            assert False
        except aioetcd.EtcdNotFile:
            pass
        try:
            yield from self.client.write('/mydir', None, dir=True, prevExist=False)
            assert False
        except aioetcd.EtcdAlreadyExist:
            pass


class TestClusterFunctions(EtcdIntegrationTest):

    @classmethod
    def setUpClass(cls):
        program = cls._get_exe()
        cls.directory = tempfile.mkdtemp(prefix='python-aioetcd')

        cls.processHelper = helpers.EtcdProcessHelper(
            cls.directory,
            proc_name=program,
            port_range_start=6001,
            internal_port_range_start=8001,
            cluster=True)

    @pytest.mark.asyncio
    def test_reconnect(self):
        """ INTEGRATION: get key after the server we're connected fails. """
        self.processHelper.stop()
        self.processHelper.run(number=3)
        self.client = aioetcd.Client(port=6001, allow_reconnect=True)
        set_result = yield from self.client.set('/test_set', 'test-key1')
        get_result = yield from self.client.get('/test_set')

        self.assertEquals('test-key1', get_result.value)

        self.processHelper.kill_one(0)

        get_result = yield from self.client.get('/test_set')
        self.assertEquals('test-key1', get_result.value)

    @pytest.mark.asyncio
    def test_reconnect_with_several_hosts_passed(self):
        """ INTEGRATION: receive several hosts at connection setup. """
        self.processHelper.stop()
        self.processHelper.run(number=3)
        self.client = aioetcd.Client(
            host=(
                ('127.0.0.1', 6004),
                ('127.0.0.1', 6001)),
            allow_reconnect=True)
        set_result = yield from self.client.set('/test_set', 'test-key1')
        get_result = yield from self.client.get('/test_set')

        self.assertEquals('test-key1', get_result.value)

        self.processHelper.kill_one(0)

        get_result = self.client.get('/test_set')
        self.assertEquals('test-key1', get_result.value)

    @pytest.mark.asyncio
    def test_reconnect_not_allowed(self):
        """ INTEGRATION: fail on server kill if not allow_reconnect """
        self.processHelper.stop()
        self.processHelper.run(number=3)
        self.client = aioetcd.Client(port=6001, allow_reconnect=False)
        self.processHelper.kill_one(0)
        try:
            self.client.get('/test_set')
        except aioetcd.EtcdConnectionFailed:
            pass

    @pytest.mark.asyncio
    def test_reconnet_fails(self):
        """ INTEGRATION: fails to reconnect if no available machines """
        self.processHelper.stop()
        # Start with three instances (0, 1, 2)
        self.processHelper.run(number=3)
        # Connect to instance 0
        self.client = aioetcd.Client(port=6001, allow_reconnect=True)
        set_result = yield from self.client.set('/test_set', 'test-key1')

        get_result = yield from self.client.get('/test_set')
        self.assertEquals('test-key1', get_result.value)
        self.processHelper.kill_one(2)
        self.processHelper.kill_one(1)
        self.processHelper.kill_one(0)
        try:
            yield from self.client.get('/test_set')
        except aioetcd.EtcdException:
            pass


class TestWatch(EtcdIntegrationTest):

    @pytest.mark.asyncio
    def test_watch(self):
        """ INTEGRATION: Receive a watch event from other process """

        set_result = yield from self.client.set('/test-key', 'test-value')

        queue = asyncio.Queue()

        @asyncio.coroutine
        def change_value(key, newValue):
            c = aioetcd.Client(port=6001)
            c.set(key, newValue)

        @asyncio.coroutine
        def watch_value(key, queue):
            c = aioetcd.Client(port=6001)
            queue.put((yield from c.watch(key)).value)

        watcher = asyncio.async(watch_value('/test-key'))
        yield from asyncio.sleep(1)
        changer = asyncio.async(change_value('/test-key', 'new-test-value'))

        value = yield from asyncio.wait_for(queue.get(),timeout=2)
        yield from asyncio.wait_for(watcher,timeout=5)
        yield from asyncio.wait_for(changer,timeout=5)

        assert value == 'new-test-value'

    @pytest.mark.asyncio
    def test_watch_indexed(self):
        """ INTEGRATION: Receive a watch event from other process, indexed """

        set_result = yield from self.client.set('/test-key', 'test-value')
        set_result = yield from self.client.set('/test-key', 'test-value0')
        original_index = int(set_result.modifiedIndex)
        set_result = yield from self.client.set('/test-key', 'test-value1')
        set_result = yield from self.client.set('/test-key', 'test-value2')

        queue = asyncio.Queue()

        @asyncio.coroutine
        def change_value(key, newValue):
            c = aioetcd.Client(port=6001)
            yield from c.set(key, newValue)
            yield from c.get(key)

        @asyncio.coroutine
        def watch_value(key, index, queue):
            c = aioetcd.Client(port=6001)
            for i in range(0, 3):
                yield from queue.put(c.watch(key, index=index + i).value)


        watcher = asyncio.async(watch_value('/test-key', original_index, queue))
        yield from asyncio.sleep(0.5)
        proc = asyncio.async(change_value('/test-key', 'test-value3'))

        for i in range(0, 3):
            value = yield from queue.get()
            log.debug("index: %d: %s" % (i, value))
            self.assertEquals('test-value%d' % i, value)

        yield from asyncio.wait_for(watcher,timeout=5)
        yield from asyncio.wait_for(proc,timeout=5)

    @pytest.mark.asyncio
    def test_watch_generator(self):
        """ INTEGRATION: Receive a watch event from other process (gen) """

        set_result = yield from self.client.set('/test-key', 'test-value')

        queue = asyncio.Queue()

        @asyncio.coroutine
        def change_value(key):
            yield from asyncio.sleep(0.5)
            c = aioetcd.Client(port=6001)
            for i in range(0, 3):
                yield from c.set(key, 'test-value%d' % i)
                yield from c.get(key)

        @asyncio.coroutine
        def watch_value(key, queue):
            c = aioetcd.Client(port=6001)
            n = 0
            @asyncio.coroutine
            def qput(event):
                nonlocal n
                yield from queue.put(event.value)
                n += 1
                if n == 3:
                    raise StopIteration
                
            yield from c.eternal_watch(key, qput)
            assert n == 3, n


        watcher = asyncio.async(watch_value('/test-key', queue))
        changer = asyncio.async(change_value('/test-key'))

        values = ['test-value0', 'test-value1', 'test-value2']
        for i in range(0, 3):
            value = yield from queue.get()
            log.debug("index: %d: %s" % (i, value))
            self.assertTrue(value in values)

        yield from asyncio.wait_for(watcher,timeout=5)
        yield from asyncio.wait_for(changer,timeout=5)

    @pytest.mark.asyncio
    def test_watch_indexed_generator(self):
        """ INTEGRATION: Receive a watch event from other process, ixd, (2) """

        set_result = yield from self.client.set('/test-key', 'test-value')
        set_result = yield from self.client.set('/test-key', 'test-value0')
        original_index = int(set_result.modifiedIndex)
        set_result = yield from self.client.set('/test-key', 'test-value1')
        set_result = yield from self.client.set('/test-key', 'test-value2')

        queue = asyncio.Queue()

        @asyncio.coroutine
        def change_value(key, newValue):
            c = aioetcd.Client(port=6001)
            yield from c.set(key, newValue)

        @asyncio.coroutine
        def watch_value(key, index, queue):
            c = aioetcd.Client(port=6001)
            n = 0
            @asyncio.coroutine
            def qput(v):
                nonlocal n
                yield from queue.put(v.value)
                n += 1
                if n == 3:
                    raise StopIteration
            yield from c.eternal_watch(key, qput, index=index)
            assert n == 3, n

        watcher = asyncio.async(watch_value('/test-key', original_index, queue))
        time.sleep(0.5)
        proc = asyncio.async(change_value('/test-key', 'test-value3',))

        for i in range(0, 3):
            value = yield from queue.get()
            log.debug("index: %d: %s" % (i, value))
            self.assertEquals('test-value%d' % i, value)

        yield from asyncio.wait_for(watcher,timeout=5)
        yield from asyncio.wait_for(proc,timeout=5)


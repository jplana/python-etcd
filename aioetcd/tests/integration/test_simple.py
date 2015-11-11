import os
import time
import shutil
import logging
import unittest
import tempfile
import pytest

import asyncio
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
        cls.processHelper.run(number=1)

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

    @helpers.run_async
    def test_machines(loop, self):
        """ INTEGRATION: retrieve machines """
        client = aioetcd.Client(port=6001, loop=loop)
        self.assertEquals((yield from client.machines())[0], 'http://127.0.0.1:6001')

    @helpers.run_async
    def test_leader(loop, self):
        """ INTEGRATION: retrieve leader """
        client = aioetcd.Client(port=6001, loop=loop)
        self.assertEquals((yield from client.leader())['clientURLs'], ['http://127.0.0.1:6001'])

    @helpers.run_async
    def test_get_set_delete(loop, self):
        """ INTEGRATION: set a new value """
        client = aioetcd.Client(port=6001, loop=loop)
        try:
            get_result = yield from client.get('/test_set')
            assert False
        except aioetcd.EtcdKeyNotFound as e:
            pass

        self.assertFalse((yield from client.contains('/test_set')))

        set_result = yield from client.set('/test_set', 'test-key')
        self.assertEquals('set', set_result.action.lower())
        self.assertEquals('/test_set', set_result.key)
        self.assertEquals('test-key', set_result.value)

        self.assertTrue((yield from client.contains('/test_set')))

        get_result = yield from client.get('/test_set')
        self.assertEquals('get', get_result.action.lower())
        self.assertEquals('/test_set', get_result.key)
        self.assertEquals('test-key', get_result.value)

        delete_result = yield from client.delete('/test_set')
        self.assertEquals('delete', delete_result.action.lower())
        self.assertEquals('/test_set', delete_result.key)

        self.assertFalse((yield from client.contains('/test_set')))

        try:
            get_result = yield from client.get('/test_set')
            assert False
        except aioetcd.EtcdKeyNotFound as e:
            pass

    @helpers.run_async
    def test_update(loop, self):
        """INTEGRATION: update a value"""
        client = aioetcd.Client(port=6001, loop=loop)
        yield from client.set('/foo', 3)
        c = yield from client.get('/foo')
        c.value = int(c.value) + 3
        yield from client.update(c)
        newres = yield from client.get('/foo')
        self.assertEquals(newres.value, u'6')
        try:
            yield from client.update(c)
            assert False
        except ValueError:
            pass

    @helpers.run_async
    def test_retrieve_subkeys(loop, self):
        """ INTEGRATION: retrieve multiple subkeys """
        client = aioetcd.Client(port=6001, loop=loop)
        set_result = yield from client.write('/subtree/test_set', 'test-key1')
        set_result = yield from client.write('/subtree/test_set1', 'test-key2')
        set_result = yield from client.write('/subtree/test_set2', 'test-key3')
        get_result = yield from client.read('/subtree', recursive=True)
        result = [subkey.value for subkey in get_result.leaves]
        self.assertEquals(['test-key1', 'test-key2', 'test-key3'].sort(), result.sort())

    @helpers.run_async
    def test_directory_ttl_update(loop, self):
        """ INTEGRATION: should be able to update a dir TTL """
        client = aioetcd.Client(port=6001, loop=loop)
        yield from client.write('/dir', None, dir=True, ttl=30)
        res = yield from client.write('/dir', None, dir=True, ttl=31, prevExist=True)
        self.assertEquals(res.ttl, 31)
        res = yield from client.get('/dir')
        res.ttl = 120
        new_res = yield from client.update(res)
        self.assertEquals(new_res.ttl, 120)



class TestErrors(EtcdIntegrationTest):

    @helpers.run_async
    def test_is_not_a_file(loop, self):
        """ INTEGRATION: try to write  value to an existing directory """
        client = aioetcd.Client(port=6001, loop=loop)

        yield from client.set('/directory/test-key', 'test-value')
        try:
            yield from client.set('/directory', 'test-value')
            raise False
        except aioetcd.EtcdNotFile:
            pass

    @helpers.run_async
    def test_test_and_set(loop, self):
        """ INTEGRATION: try test_and_set operation """
        client = aioetcd.Client(port=6001, loop=loop)

        set_result = yield from client.set('/test-key', 'old-test-value')

        set_result = yield from client.test_and_set(
            '/test-key',
            'test-value',
            'old-test-value',
            )

        try:
            yield from client.test_and_set('/test-key', 'new-value', 'old-test-value')
        except ValueError:
            pass

    @helpers.run_async
    def test_creating_already_existing_directory(loop, self):
        """ INTEGRATION: creating an already existing directory without
        `prevExist=True` should fail """
        client = aioetcd.Client(port=6001, loop=loop)
        yield from client.write('/mydir', None, dir=True)

        try:
            yield from client.write('/mydir', None, dir=True)
            assert False
        except aioetcd.EtcdNotFile:
            pass
        try:
            yield from client.write('/mydir', None, dir=True, prevExist=False)
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

    @helpers.run_async
    def test_reconnect(loop, self):
        """ INTEGRATION: get key after the server we're connected fails. """
        self.processHelper.stop()
        self.processHelper.run(number=3)
        client = aioetcd.Client(port=6001, allow_reconnect=True, loop=loop)
        set_result = yield from client.set('/test_set', 'test-key1')
        get_result = yield from client.get('/test_set')

        self.assertEquals('test-key1', get_result.value)

        self.processHelper.kill_one(0)

        get_result = yield from client.get('/test_set')
        self.assertEquals('test-key1', get_result.value)

    @helpers.run_async
    def test_reconnect_with_several_hosts_passed(loop, self):
        """ INTEGRATION: receive several hosts at connection setup. """
        self.processHelper.stop()
        self.processHelper.run(number=3)
        client = aioetcd.Client(
            host=(
                ('127.0.0.1', 6004),
                ('127.0.0.1', 6001)),
            allow_reconnect=True, loop=loop)
        set_result = yield from client.set('/test_set', 'test-key1')
        get_result = yield from client.get('/test_set')

        self.assertEquals('test-key1', get_result.value)

        self.processHelper.kill_one(0)

        get_result = yield from client.get('/test_set')
        self.assertEquals('test-key1', get_result.value)

    @helpers.run_async
    def test_reconnect_not_allowed(loop, self):
        """ INTEGRATION: fail on server kill if not allow_reconnect """
        self.processHelper.stop()
        self.processHelper.run(number=3)
        client = aioetcd.Client(port=6001, allow_reconnect=False, loop=loop)
        self.processHelper.kill_one(0)
        try:
            yield from client.get('/test_set')
            assert False
        except aioetcd.EtcdConnectionFailed:
            pass

    @helpers.run_async
    def test_reconnet_fails(loop, self):
        """ INTEGRATION: fails to reconnect if no available machines """
        self.processHelper.stop()
        # Start with three instances (0, 1, 2)
        self.processHelper.run(number=3)
        # Connect to instance 0
        client = aioetcd.Client(port=6001, allow_reconnect=True, loop=loop)
        set_result = yield from client.set('/test_set', 'test-key1')

        get_result = yield from client.get('/test_set')
        self.assertEquals('test-key1', get_result.value)
        self.processHelper.kill_one(2)
        self.processHelper.kill_one(1)
        self.processHelper.kill_one(0)
        try:
            yield from client.get('/test_set')
        except aioetcd.EtcdException:
            pass


class TestWatch(EtcdIntegrationTest):

    @helpers.run_async
    def test_watch(loop, self):
        """ INTEGRATION: Receive a watch event from other process """

        client = aioetcd.Client(port=6001, allow_reconnect=True, loop=loop)
        set_result = yield from client.set('/test-key', 'test-value')

        queue = asyncio.Queue(loop=loop)

        @asyncio.coroutine
        def change_value(key, newValue):
            c = aioetcd.Client(port=6001, loop=loop)
            yield from c.set(key, newValue)

        @asyncio.coroutine
        def watch_value(key, queue):
            c = aioetcd.Client(port=6001, loop=loop)
            w = yield from c.watch(key)
            yield from queue.put(w.value)

        watcher = asyncio.async(watch_value('/test-key', queue), loop=loop)
        yield from asyncio.sleep(0.1, loop=loop)
        changer = asyncio.async(change_value('/test-key', 'new-test-value'), loop=loop)

        value = yield from asyncio.wait_for(queue.get(),timeout=2,loop=loop)
        yield from asyncio.wait_for(watcher,timeout=5,loop=loop)
        yield from asyncio.wait_for(changer,timeout=5,loop=loop)

        assert value == 'new-test-value'

    @helpers.run_async
    def test_watch_indexed(loop, self):
        """ INTEGRATION: Receive a watch event from other process, indexed """

        client = aioetcd.Client(port=6001, allow_reconnect=True, loop=loop)

        set_result = yield from client.set('/test-key', 'test-value')
        set_result = yield from client.set('/test-key', 'test-value0')
        original_index = int(set_result.modifiedIndex)
        set_result = yield from client.set('/test-key', 'test-value1')
        set_result = yield from client.set('/test-key', 'test-value2')

        queue = asyncio.Queue(loop=loop)

        @asyncio.coroutine
        def change_value(key, newValue):
            c = aioetcd.Client(port=6001, loop=loop)
            yield from c.set(key, newValue)
            yield from c.get(key)

        @asyncio.coroutine
        def watch_value(key, index, queue):
            c = aioetcd.Client(port=6001, loop=loop)
            for i in range(0, 3):
                yield from queue.put((yield from c.watch(key, index=index + i)).value)


        watcher = asyncio.async(watch_value('/test-key', original_index, queue), loop=loop)
        yield from asyncio.sleep(0.5, loop=loop)
        proc = asyncio.async(change_value('/test-key', 'test-value3'), loop=loop)

        for i in range(0, 3):
            value = yield from queue.get()
            log.debug("index: %d: %s" % (i, value))
            self.assertEquals('test-value%d' % i, value)

        yield from asyncio.wait_for(watcher,timeout=5,loop=loop)
        yield from asyncio.wait_for(proc,timeout=5,loop=loop)

    @helpers.run_async
    def test_watch_generator(loop, self):
        """ INTEGRATION: Receive a watch event from other process (gen) """

        client = aioetcd.Client(port=6001, allow_reconnect=True, loop=loop)
        set_result = yield from client.set('/test-key', 'test-value')

        queue = asyncio.Queue(loop=loop)

        @asyncio.coroutine
        def change_value(key):
            yield from asyncio.sleep(0.5, loop=loop)
            c = aioetcd.Client(port=6001, loop=loop)
            for i in range(0, 3):
                yield from c.set(key, 'test-value%d' % i)
                yield from c.get(key)

        @asyncio.coroutine
        def watch_value(key, queue):
            c = aioetcd.Client(port=6001, loop=loop)
            n = 0
            @asyncio.coroutine
            def qput(event):
                nonlocal n
                yield from queue.put(event.value)
                n += 1
                if n == 3:
                    raise aioetcd.StopWatching
                
            yield from c.eternal_watch(key, qput)
            assert n == 3, n


        watcher = asyncio.async(watch_value('/test-key', queue), loop=loop)
        changer = asyncio.async(change_value('/test-key'), loop=loop)

        values = ['test-value0', 'test-value1', 'test-value2']
        for i in range(0, 3):
            value = yield from queue.get()
            log.debug("index: %d: %s" % (i, value))
            self.assertTrue(value in values)

        yield from asyncio.wait_for(watcher,timeout=5,loop=loop)
        yield from asyncio.wait_for(changer,timeout=5,loop=loop)

    @helpers.run_async
    def test_watch_indexed_generator(loop, self):
        """ INTEGRATION: Receive a watch event from other process, ixd, (2) """

        client = aioetcd.Client(port=6001, allow_reconnect=True, loop=loop)

        set_result = yield from client.set('/test-key', 'test-value')
        set_result = yield from client.set('/test-key', 'test-value0')
        original_index = int(set_result.modifiedIndex)
        set_result = yield from client.set('/test-key', 'test-value1')
        set_result = yield from client.set('/test-key', 'test-value2')

        queue = asyncio.Queue(loop=loop)

        @asyncio.coroutine
        def change_value(key, newValue):
            c = aioetcd.Client(port=6001, loop=loop)
            yield from c.set(key, newValue)

        @asyncio.coroutine
        def watch_value(key, index, queue):
            c = aioetcd.Client(port=6001, loop=loop)
            n = 0
            @asyncio.coroutine
            def qput(v):
                nonlocal n
                yield from queue.put(v.value)
                n += 1
                if n == 3:
                    raise aioetcd.StopWatching
            yield from c.eternal_watch(key, qput, index=index)
            assert n == 3, n

        watcher = asyncio.async(watch_value('/test-key', original_index, queue), loop=loop)
        yield from asyncio.sleep(0.5, loop=loop)
        proc = asyncio.async(change_value('/test-key', 'test-value3',), loop=loop)

        for i in range(0, 3):
            value = yield from queue.get()
            log.debug("index: %d: %s" % (i, value))
            self.assertEquals('test-value%d' % i, value)

        yield from asyncio.wait_for(watcher,timeout=5,loop=loop)
        yield from asyncio.wait_for(proc,timeout=5,loop=loop)


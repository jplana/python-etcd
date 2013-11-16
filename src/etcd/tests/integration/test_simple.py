import os
import time
import shutil
import logging
import unittest
import multiprocessing
import tempfile
import urllib3

import etcd
import helpers

from nose.tools import nottest


log = logging.getLogger()


class EtcdIntegrationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        program = cls._get_exe()
        cls.directory = tempfile.mkdtemp(prefix='python-etcd')
        cls.processHelper = helpers.EtcdProcessHelper(
            cls.directory,
            proc_name=program,
            port_range_start=6001,
            internal_port_range_start=8001)
        cls.processHelper.run(number=3)
        cls.client = etcd.Client(port=6001)

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

        self.assertFalse('/test_set' in self.client)

        set_result = self.client.set('/test_set', 'test-key')
        self.assertEquals('SET', set_result.action)
        self.assertEquals('/test_set', set_result.key)
        self.assertEquals(True, set_result.newKey)
        self.assertEquals('test-key', set_result.value)

        self.assertTrue('/test_set' in self.client)

        get_result = self.client.get('/test_set')
        self.assertEquals('GET', get_result.action)
        self.assertEquals('/test_set', get_result.key)
        self.assertEquals('test-key', get_result.value)

        delete_result = self.client.delete('/test_set')
        self.assertEquals('DELETE', delete_result.action)
        self.assertEquals('/test_set', delete_result.key)
        self.assertEquals('test-key', delete_result.prevValue)

        self.assertFalse('/test_set' in self.client)

        try:
            get_result = self.client.get('/test_set')
            assert False
        except KeyError, e:
            pass

    def test_retrieve_subkeys(self):
        """ INTEGRATION: retrieve multiple subkeys """
        set_result = self.client.set('/subtree/test_set', 'test-key1')
        set_result = self.client.set('/subtree/test_set1', 'test-key2')
        set_result = self.client.set('/subtree/test_set2', 'test-key3')
        get_result = self.client.get('/subtree')
        result = [subkey.value for subkey in get_result]
        self.assertEquals(['test-key1', 'test-key2', 'test-key3'], result)


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

class TestClusterFunctions(EtcdIntegrationTest):
    @classmethod
    def setUpClass(cls):
        program = cls._get_exe()

        cls.processHelper = helpers.EtcdProcessHelper(
            proc_name=program,
            port_range_start=6001,
            internal_port_range_start=8001,
            cluster = True)
        cls.processHelper.run(number=3)

    def test_reconnect(self):
        """ INTEGRATION: retreive a key after the server we're connected to dies. """
        self.client = etcd.Client(port=6001, allow_reconnect = True)
        set_result = self.client.set('/test_set', 'test-key1')
        self.processHelper.kill_one()
        get_result = self.client.get('/test_set')
        self.assertEquals('test-key1', get_result.value)

    def test_reconnect_not_allowed(self):
        """ INTEGRATION: fail on server kill if not allow_reconnect """
        self.client = etcd.Client(port=6001, allow_reconnect = False)
        self.processHelper.kill_one()
        self.assertRaises(urllib3.exceptions.MaxRetryError, self.client.get,'/test_set')


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
            self.assertTrue(value in values)

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


class TestAuthenticatedAccess(EtcdIntegrationTest):

    @classmethod
    def setUpClass(cls):
        program = cls._get_exe()
        cls.directory = tempfile.mkdtemp(prefix='python-etcd')

        cls.ca_cert_path = os.path.join(cls.directory, 'ca.crt')
        ca_key_path = os.path.join(cls.directory, 'ca.key')

        cls.ca2_cert_path = os.path.join(cls.directory, 'ca2.crt')
        ca2_key_path = os.path.join(cls.directory, 'ca2.key')

        server_cert_path = os.path.join(cls.directory, 'server.crt')
        server_key_path = os.path.join(cls.directory, 'server.key')

        ca, ca_key = helpers.TestingCA.create_test_ca_certificate(
            cls.ca_cert_path, ca_key_path, 'TESTCA')

        ca2, ca2_key = helpers.TestingCA.create_test_ca_certificate(
            cls.ca2_cert_path, ca2_key_path, 'TESTCA2')

        helpers.TestingCA.create_test_certificate(
            ca, ca_key, server_cert_path, server_key_path, '127.0.0.1')

        cls.processHelper = helpers.EtcdProcessHelper(
            cls.directory,
            proc_name=program,
            port_range_start=6001,
            internal_port_range_start=8001)

        cls.processHelper.run(number=3,
                              proc_args=[
                                  '-clientCert=%s' % server_cert_path,
                                  '-clientKey=%s' % server_key_path
                              ])

    def test_get_set_unauthenticated(self):
        """ INTEGRATION: set/get a new value unauthenticated (http->https) """

        client = etcd.Client(port=6001)

        try:
            set_result = client.set('/test_set', 'test-key')
            self.fail()

        except etcd.EtcdException, e:
            self.assertEquals(e.message, "Unable to decode server response")

        try:
            get_result = client.get('/test_set')
            self.fail()

        except etcd.EtcdException, e:
            self.assertEquals(e.message, "Unable to decode server response")

    def test_get_set_unauthenticated_missing_ca(self):
        """ INTEGRATION: try unauthenticated w/out validation (https->https)"""

        client = etcd.Client(protocol='https', port=6001)
        set_result = client.set('/test_set', 'test-key')
        get_result = client.get('/test_set')

    def test_get_set_unauthenticated_with_ca(self):
        """ INTEGRATION: try unauthenticated w/out validation (https->https)"""

        client = etcd.Client(
            protocol='https', port=6001, ca_cert=self.ca2_cert_path)

        try:
            set_result = client.set('/test_set', 'test-key')
            assert False
        except urllib3.exceptions.SSLError, e:
            assert True

        try:
            get_result = client.get('/test_set')
        except urllib3.exceptions.SSLError, e:
            assert True

    def test_get_set_authenticated(self):
        """ INTEGRATION: set/get a new value authenticated """

        client = etcd.Client(
            port=6001, protocol='https', ca_cert=self.ca_cert_path)

        set_result = client.set('/test_set', 'test-key')
        get_result = client.get('/test_set')


class TestClientAuthenticatedAccess(EtcdIntegrationTest):

    @classmethod
    def setUpClass(cls):
        program = cls._get_exe()
        cls.directory = tempfile.mkdtemp(prefix='python-etcd')

        cls.ca_cert_path = os.path.join(cls.directory, 'ca.crt')
        ca_key_path = os.path.join(cls.directory, 'ca.key')

        server_cert_path = os.path.join(cls.directory, 'server.crt')
        server_key_path = os.path.join(cls.directory, 'server.key')

        cls.client_cert_path = os.path.join(cls.directory, 'client.crt')
        cls.client_key_path = os.path.join(cls.directory, 'client.key')

        cls.client_all_cert = os.path.join(cls.directory, 'client-all.crt')

        ca, ca_key = helpers.TestingCA.create_test_ca_certificate(
            cls.ca_cert_path, ca_key_path)

        helpers.TestingCA.create_test_certificate(
            ca, ca_key, server_cert_path, server_key_path, '127.0.0.1')

        helpers.TestingCA.create_test_certificate(
            ca,
            ca_key,
            cls.client_cert_path,
            cls.client_key_path)

        cls.processHelper = helpers.EtcdProcessHelper(
            cls.directory,
            proc_name=program,
            port_range_start=6001,
            internal_port_range_start=8001)

        with file(cls.client_all_cert, 'w') as f:
            f.write(file(cls.client_key_path).read())
            f.write(file(cls.client_cert_path).read())

        cls.processHelper.run(number=3,
                              proc_args=[
                                  '-clientCert=%s' % server_cert_path,
                                  '-clientKey=%s' % server_key_path,
                                  '-clientCAFile=%s' % cls.ca_cert_path
                              ])

    def test_get_set_unauthenticated(self):
        """ INTEGRATION: set/get a new value unauthenticated (http->https) """

        client = etcd.Client(port=6001)

        try:
            set_result = client.set('/test_set', 'test-key')
            self.fail()

        except etcd.EtcdException, e:
            self.assertEquals(e.message, "Unable to decode server response")

        try:
            get_result = client.get('/test_set')
            self.fail()

        except etcd.EtcdException, e:
            self.assertEquals(e.message, "Unable to decode server response")

    def test_get_set_authenticated(self):
        """ INTEGRATION: connecting to server with mutual auth """

        client = etcd.Client(
            port=6001,
            protocol='https',
            cert=self.client_all_cert,
            ca_cert=self.ca_cert_path
        )

        set_result = client.set('/test_set', 'test-key')
        self.assertEquals('SET', set_result.action)
        self.assertEquals('/test_set', set_result.key)
        self.assertEquals(True, set_result.newKey)
        self.assertEquals('test-key', set_result.value)

        get_result = client.get('/test_set')
        self.assertEquals('GET', get_result.action)
        self.assertEquals('/test_set', get_result.key)
        self.assertEquals('test-key', get_result.value)

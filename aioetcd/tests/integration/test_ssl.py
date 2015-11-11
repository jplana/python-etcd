import os
import time
import shutil
import logging
import unittest
import tempfile
import pytest
import ssl

import asyncio
import aioetcd
from . import helpers
from . import test_simple

log = logging.getLogger()

class TestEncryptedAccess(test_simple.EtcdIntegrationTest):

    @classmethod
    def setUpClass(cls):
        program = cls._get_exe()
        cls.directory = tempfile.mkdtemp(prefix='python-aioetcd')

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
            internal_port_range_start=8001,
            tls=True
        )

        cls.processHelper.run(number=3,
                              proc_args=[
                                  '-cert-file=%s' % server_cert_path,
                                  '-key-file=%s' % server_key_path
                              ])

    @helpers.run_async
    def test_get_set_unauthenticated(loop, self):
        """ INTEGRATION: set/get a new value unauthenticated (http->https) """

        client = aioetcd.Client(port=6001, loop=loop)

        # Since python 3 raises a MaxRetryError here, this gets caught in
        # different code blocks in python 2 and python 3, thus messages are
        # different. Python 3 does the right thing(TM), for the record
        try:
            yield from client.set('/test_set', 'test-key')
            raise False
        except aioetcd.EtcdException:
            pass

        try:
            yield from client.get('/test_set')
            assert False
        except aioetcd.EtcdException:
            pass

    @helpers.run_async
    def test_get_set_unauthenticated_missing_ca(loop, self):
        """ INTEGRATION: try unauthenticated w/out validation (https->https)"""
        # This doesn't work for now and will need further inspection
        client = aioetcd.Client(protocol='https', port=6001, ssl_verify=ssl.CERT_NONE, loop=loop)
        set_result = yield from client.set('/test_set', 'test-key')
        get_result = yield from client.get('/test_set')

    @helpers.run_async
    def test_get_set_unauthenticated_with_ca(loop, self):
        """ INTEGRATION: try unauthenticated with validation (https->https)"""
        client = aioetcd.Client(
            protocol='https', port=6001, ca_cert=self.ca2_cert_path, loop=loop)

        loop = asyncio.get_event_loop()
        try:
            yield from client.set('/test-set', 'test-key')
            assert False
        except aioetcd.EtcdConnectionFailed:
            pass
        try:
            yield from client.get('/test-set')
            assert False
        except aioetcd.EtcdConnectionFailed:
            pass

    @helpers.run_async
    def test_get_set_authenticated(loop, self):
        """ INTEGRATION: set/get a new value authenticated """

        client = aioetcd.Client(
            port=6001, protocol='https', ca_cert=self.ca_cert_path, loop=loop)

        set_result = yield from client.set('/test_set', 'test-key')
        get_result = yield from client.get('/test_set')


class TestClientAuthenticatedAccess(test_simple.EtcdIntegrationTest):

    @classmethod
    def setUpClass(cls):
        program = cls._get_exe()
        cls.directory = tempfile.mkdtemp(prefix='python-aioetcd')

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
            internal_port_range_start=8001,
            tls=True
        )

        with open(cls.client_all_cert, 'w') as f:
            with open(cls.client_key_path, 'r') as g:
                f.write(g.read())
            with open(cls.client_cert_path, 'r') as g:
                f.write(g.read())

        cls.processHelper.run(number=3,
                              proc_args=[
                                  '-cert-file=%s' % server_cert_path,
                                  '-key-file=%s' % server_key_path,
                                  '-ca-file=%s' % cls.ca_cert_path,
                              ])


    @helpers.run_async
    def test_get_set_unauthenticated(loop, self):
        """ INTEGRATION: set/get a new value unauthenticated (http->https) """

        client = aioetcd.Client(port=6001, loop=loop)

        # See above for the reason of this change
        try:
            yield from client.set('/test_set', 'test-key')
            assert False
        except aioetcd.EtcdException:
            pass
        try:
            yield from client.get('/test_set')
            assert False
        except aioetcd.EtcdException:
            pass

    @helpers.run_async
    def test_get_set_authenticated(loop, self):
        """ INTEGRATION: connecting to server with mutual auth """
        # This gives an unexplicable ssl error, as connecting to the same
        # Etcd cluster where this fails with the exact same code this
        # doesn't fail

        client = aioetcd.Client(
            port=6001,
            protocol='https',
            cert=self.client_all_cert,
            ca_cert=self.ca_cert_path,
            loop=loop,
            )

        set_result = yield from client.set('/test_set', 'test-key')
        self.assertEquals(u'set', set_result.action.lower())
        self.assertEquals(u'/test_set', set_result.key)
        self.assertEquals(u'test-key', set_result.value)
        get_result = yield from client.get('/test_set')
        self.assertEquals('get', get_result.action.lower())
        self.assertEquals('/test_set', get_result.key)
        self.assertEquals('test-key', get_result.value)


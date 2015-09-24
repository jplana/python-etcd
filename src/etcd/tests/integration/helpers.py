import shutil
import subprocess
import tempfile
import logging
import time
import hashlib
import uuid

from OpenSSL import crypto


class EtcdProcessHelper(object):

    def __init__(
            self,
            base_directory,
            proc_name='etcd',
            port_range_start=4001,
            internal_port_range_start=7001,
            cluster=False,
            tls=False
    ):

        self.base_directory = base_directory
        self.proc_name = proc_name
        self.port_range_start = port_range_start
        self.internal_port_range_start = internal_port_range_start
        self.processes = {}
        self.cluster = cluster
        self.schema = 'http://'
        if tls:
            self.schema = 'https://'

    def run(self, number=1, proc_args=[]):
        if number > 1:
            initial_cluster = ",".join([ "test-node-{}={}127.0.0.1:{}".format(slot, 'http://', self.internal_port_range_start + slot) for slot in range(0, number)])
            proc_args.extend([
                '-initial-cluster', initial_cluster,
                '-initial-cluster-state', 'new'
            ])
        else:
            proc_args.extend([
                '-initial-cluster', 'test-node-0=http://127.0.0.1:{}'.format(self.internal_port_range_start),
                '-initial-cluster-state', 'new'
            ])

        for i in range(0, number):
            self.add_one(i, proc_args)

    def stop(self):
        log = logging.getLogger()
        for key in [k for k in self.processes.keys()]:
            self.kill_one(key)

    def add_one(self, slot, proc_args=None):
        log = logging.getLogger()
        directory = tempfile.mkdtemp(
            dir=self.base_directory,
            prefix='python-etcd.%d-' % slot)

        log.debug('Created directory %s' % directory)
        client = '%s127.0.0.1:%d' % (self.schema, self.port_range_start + slot)
        peer = '%s127.0.0.1:%d' % ('http://', self.internal_port_range_start
                                   + slot)
        daemon_args = [
            self.proc_name,
            '-data-dir', directory,
            '-name', 'test-node-%d' % slot,
            '-initial-advertise-peer-urls', peer,
            '-listen-peer-urls', peer,
            '-advertise-client-urls', client,
            '-listen-client-urls', client
        ]

        if proc_args:
            daemon_args.extend(proc_args)

        daemon = subprocess.Popen(daemon_args)
        log.debug('Started %d' % daemon.pid)
        log.debug('Params: %s' % daemon_args)
        time.sleep(2)
        self.processes[slot] = (directory, daemon)

    def kill_one(self, slot):
        log = logging.getLogger()
        data_dir, process = self.processes.pop(slot)
        process.kill()
        time.sleep(2)
        log.debug('Killed etcd pid:%d', process.pid)
        shutil.rmtree(data_dir)
        log.debug('Removed directory %s' % data_dir)


class TestingCA(object):

    @classmethod
    def create_test_ca_certificate(cls, cert_path, key_path, cn=None):
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 4096)
        cert = crypto.X509()

        if not cn:
            serial = uuid.uuid4().int
        else:
            md5_hash = hashlib.md5()
            md5_hash.update(cn.encode('utf-8'))
            serial = int(md5_hash.hexdigest(), 36)
            cert.get_subject().CN = cn

        cert.get_subject().C = "ES"
        cert.get_subject().ST = "State"
        cert.get_subject().L = "City"
        cert.get_subject().O = "Organization"
        cert.get_subject().OU = "Organizational Unit"
        cert.set_serial_number(serial)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(315360000)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.add_extensions([
            crypto.X509Extension("basicConstraints".encode('ascii'), False,
                                 "CA:TRUE".encode('ascii')),
            crypto.X509Extension("keyUsage".encode('ascii'), False,
                                 "keyCertSign, cRLSign".encode('ascii')),
            crypto.X509Extension("subjectKeyIdentifier".encode('ascii'), False,
                                 "hash".encode('ascii'),
                                 subject=cert),
        ])

        cert.add_extensions([
            crypto.X509Extension(
                "authorityKeyIdentifier".encode('ascii'), False,
                "keyid:always".encode('ascii'), issuer=cert)
        ])

        cert.sign(k, 'sha1')

        with open(cert_path, 'w') as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
                    .decode('utf-8'))

        with open(key_path, 'w') as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k)
                    .decode('utf-8'))

        return cert, k

    @classmethod
    def create_test_certificate(cls, ca, ca_key, cert_path, key_path, cn=None):
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 4096)
        cert = crypto.X509()

        if not cn:
            serial = uuid.uuid4().int
        else:
            md5_hash = hashlib.md5()
            md5_hash.update(cn.encode('utf-8'))
            serial = int(md5_hash.hexdigest(), 36)
            cert.get_subject().CN = cn

        cert.get_subject().C = "ES"
        cert.get_subject().ST = "State"
        cert.get_subject().L = "City"
        cert.get_subject().O = "Organization"
        cert.get_subject().OU = "Organizational Unit"

        cert.add_extensions([
            crypto.X509Extension(
                "keyUsage".encode('ascii'),
                False,
                "nonRepudiation,digitalSignature,keyEncipherment".encode('ascii')),
            crypto.X509Extension(
                "extendedKeyUsage".encode('ascii'),
                False,
                "clientAuth,serverAuth".encode('ascii')),
            crypto.X509Extension(
                "subjectAltName".encode('ascii'),
                False,
                "IP: 127.0.0.1".encode('ascii')),
        ])

        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(315360000)
        cert.set_issuer(ca.get_subject())
        cert.set_pubkey(k)
        cert.set_serial_number(serial)

        cert.sign(ca_key, 'sha1')

        with open(cert_path, 'w') as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
                    .decode('utf-8'))

        with open(key_path, 'w') as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k)
                    .decode('utf-8'))

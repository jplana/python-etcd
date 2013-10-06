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
            cluster = False):

        self.base_directory = base_directory
        self.proc_name = proc_name
        self.port_range_start = port_range_start
        self.internal_port_range_start = internal_port_range_start
        self.processes = []
        self.cluster = cluster

    def run(self, number=1, proc_args=None):
        log = logging.getLogger()
        for i in range(0, number):
            directory = tempfile.mkdtemp(
                dir=self.base_directory,
                prefix='python-etcd.%d-' % i)
            log.debug('Created directory %s' % directory)
            daemon_args = [
                self.proc_name,
                '-d', directory,
                '-n', 'test-node-%d' % i,
                '-s', '127.0.0.1:%d' % (self.internal_port_range_start + i),
                '-c', '127.0.0.1:%d' % (self.port_range_start + i),
            ]

            if proc_args:
                daemon_args.extend(proc_args)

            if i and self.cluster:
                daemon_args.append('-C')
                daemon_args.append(
                    '127.0.0.1:%d' % self.internal_port_range_start)
            daemon_args

            daemon = subprocess.Popen(daemon_args)
            log.debug('Started %d' % daemon.pid)
            time.sleep(2)
            self.processes.append((directory, daemon))

    def stop(self):
        log = logging.getLogger()
        for directory, process in self.processes:
            process.kill()
            time.sleep(2)
            log.debug('Killed etcd pid:%d' % process.pid)
            shutil.rmtree(directory)
            log.debug('Removed directory %s' % directory)

    def kill_one(self):
        log = logging.getLogger()
        dir, process = self.processes.pop(0)
        process.kill()
        time.sleep(2)
        log.debug('Killed etcd pid:%d', process.pid)
        shutil.rmtree(dir)
        log.debug('Removed directory %s' % dir)


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
            md5_hash.update(cn)
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
            crypto.X509Extension("basicConstraints", False,
                                 "CA:TRUE"),
            crypto.X509Extension("keyUsage", False,
                                 "keyCertSign, cRLSign"),
            crypto.X509Extension("subjectKeyIdentifier", False, "hash",
                                 subject=cert),
        ])

        cert.add_extensions([
            crypto.X509Extension(
                "authorityKeyIdentifier", False,
                "keyid:always", issuer=cert)
        ])

        cert.sign(k, 'sha1')

        with file(cert_path, 'w') as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

        with file(key_path, 'w') as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

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
            md5_hash.update(cn)
            serial = int(md5_hash.hexdigest(), 36)
            cert.get_subject().CN = cn

        cert.get_subject().C = "ES"
        cert.get_subject().ST = "State"
        cert.get_subject().L = "City"
        cert.get_subject().O = "Organization"
        cert.get_subject().OU = "Organizational Unit"

        cert.add_extensions([
            crypto.X509Extension(
                "keyUsage",
                False,
                "nonRepudiation,digitalSignature,keyEncipherment"),
            crypto.X509Extension(
                "extendedKeyUsage",
                False,
                "clientAuth,serverAuth"),
        ])

        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(315360000)
        cert.set_issuer(ca.get_subject())
        cert.set_pubkey(k)
        cert.set_serial_number(serial)

        cert.sign(ca_key, 'sha1')

        with file(cert_path, 'w') as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

        with file(key_path, 'w') as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

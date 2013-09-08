import shutil
import subprocess
import tempfile
import logging
import time


class EtcdProcessHelper(object):
    def __init__(
            self,
            proc_name='etcd',
            port_range_start=4001,
            internal_port_range_start=7001):
        self.proc_name = proc_name
        self.port_range_start = port_range_start
        self.internal_port_range_start = internal_port_range_start
        self.processes = []

    def run(self, number=1):
        log = logging.getLogger()
        for i in range(0, number):
            directory = tempfile.mkdtemp(prefix='python-etcd.%d' % i)
            log.debug('Created directory %s' % directory)
            daemon_args = [
                self.proc_name,
                '-d', directory,
                '-n', 'test-node-%d' % i,
                '-s', '127.0.0.1:%d' % (self.internal_port_range_start + i),
                '-c', '127.0.0.1:%d' % (self.port_range_start + i),
            ]
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

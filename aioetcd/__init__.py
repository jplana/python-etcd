import logging
from etcd import *
from .client import Client
from .lock import Lock

_log = logging.getLogger(__name__)

class StopWatching(BaseException):
    pass

_EtcdResult = EtcdResult
class EtcdResult(_EtcdResult):
    def parse_headers(self, response):
        headers = response.headers
        self.etcd_index = int(headers.get('x-etcd-index', 1))
        self.raft_index = int(headers.get('x-raft-index', 1))


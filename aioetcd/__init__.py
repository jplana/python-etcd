import logging
from etcd import *
from .client import Client
from .lock import Lock

_log = logging.getLogger(__name__)


import etcd
import platform


class LeaderElection(object):

    """
    Leader Election class using the etcd module
    """

    def __init__(self, client):
        """
        Initialize a leader election object.

        Args:
            client (etcd.Client): etcd client to use for the connection
        """
        self.client = client

    def get_path(self, key):
        if not key.startswith('/'):
            key = '/' + key
        return '/mod/v2/leader{}'.format(key)

    def set(self, key, name=None, ttl=0, timeout=None):
        """
        Initialize a leader election object.

        Args:
            key (string): name of the leader key,

            ttl (int): ttl (in seconds) for the lock to live.

            name (string): the name to store as the leader name. Defaults to the
                           client's hostname

        """

        name = name or platform.node()
        params = {'ttl': ttl, 'name': name}
        path = self.get_path(key)

        res = self.client.api_execute(
            path, self.client._MPUT, params=params, timeout=timeout)
        return res.data.decode('utf-8')

    def get(self, key):
        """
        Get the name of a leader object.

        Args:
            key (string): name of the leader key,

        Raises:
            etcd.EtcdException

        """
        res = self.client.api_execute(self.get_path(key), self.client._MGET)
        if not res.data:
            raise etcd.EtcdException('Leader path {} not found'.format(key))
        return res.data.decode('utf-8')

    def delete(self, key, name=None):
        """
        Delete a leader object.

        Args:
            key (string): the leader key,

            name (string): name of the elected leader

        Raises:
            etcd.EtcdException

        """
        path = self.get_path(key)
        name = name or platform.node()
        res = self.client.api_execute(
            path, self.client._MDELETE, {'name': name})
        if (res.data.decode('utf-8') == ''):
            return True
        return False

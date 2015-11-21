import json

import logging

try:
    # Python 3
    from http.client import HTTPException
except ImportError:
    # Python 2
    from httplib import HTTPException
import socket
import urllib3

from .client import Client
import etcd

_log = logging.getLogger(__name__)


class AuthClient(Client):
    """
    Extended etcd client that supports authentication primitives added in 2.1.
    """

    def __init__(self, *args, **kwargs):
        super(AuthClient, self).__init__(*args, **kwargs)

    def create_user(self, username, password, roles=[], role_action='roles'):
        """
        Add a user.

        Args:
            username (str): Username to create.
            password (str): Password for username.
            roles (list): List of roles as strings.

        Returns:
            EtcdUser

        Raises:
            etcd.EtcdException: If user can't be created.
        """
        try:
            uri = self.version_prefix + '/auth/users/' + username
            params = {'user': username}
            if password:
                params['password'] = password
            if roles:
                params[role_action] = roles

            response = self.json_api_execute(uri, self._MPUT, params=params)
            res = json.loads(response.data.decode('utf-8'))
            return EtcdUser(self, res)
        except Exception as e:
            _log.error("Failed to create user in %s%s: %r",
                       self._base_uri, self.version_prefix, e)
            raise etcd.EtcdException("Could not create user")

    def get_user(self, username):
        """
        Look up a user.

        Args:
            username (str): Username to lookup.

        Returns:
            EtcdUser

        Raises:
            etcd.EtcdException: If user can't be found.
        """
        try:
            uri = self.version_prefix + '/auth/users/' + username
            response = self.api_execute(uri, self._MGET)
            res = json.loads(response.data.decode('utf-8'))
            return EtcdUser(self, res)
        except Exception as e:
            _log.error("Failed to fetch user in %s%s: %r",
                       self._base_uri, self.version_prefix, e)
            raise etcd.EtcdException("Could not fetch user")

    @property
    def usernames(self):
        """List user names."""
        try:
            uri = self.version_prefix + '/auth/users'
            response = self.api_execute(uri, self._MGET)
            res = json.loads(response.data.decode('utf-8'))
            return res['users']
        except Exception as e:
            _log.error("Failed to list users in %s%s: %r",
                       self._base_uri, self.version_prefix, e)
            raise etcd.EtcdException("Could not list users")

    @property
    def users(self):
        """List users in detail."""
        return [self.get_user(x) for x in self.usernames]

    def create_role(self, role_name):
        """
        Create a role.

        Args:
            role_name (str): Name of role

        Returns:
            EtcdRole
        """
        return self.modify_role(role_name)

    def get_role(self, role_name):
        """
        Look up a role.

        Args:
            role_name (str): Name of role.

        Returns:
            EtcdRole
        """
        try:
            uri = self.version_prefix + '/auth/roles/' + role_name
            response = self.api_execute(uri, self._MGET)
            res = json.loads(response.data.decode('utf-8'))
            return EtcdRole(self, res)
        except Exception as e:
            _log.error("Failed to fetch user in %s%s: %r",
                       self._base_uri, self.version_prefix, e)
            raise etcd.EtcdException("Could not fetch users")

    @property
    def role_names(self):
        """List role names."""
        try:
            uri = self.version_prefix + '/auth/roles'
            response = self.api_execute(uri, self._MGET)
            res = json.loads(response.data.decode('utf-8'))
            return res['roles']
        except Exception as e:
            _log.error("Failed to list roles in %s%s: %r",
                       self._base_uri, self.version_prefix, e)
            raise etcd.EtcdException("Could not list roles")

    @property
    def roles(self):
        """List roles in detail."""
        return [self.get_role(x) for x in self.role_names]

    def toggle_auth(self, auth_enabled=True):
        """
        Toggle authentication.

        Args:
            auth_enabled (bool): Should auth be enabled or disabled
        """
        try:
            uri = self.version_prefix + '/auth/enable'
            action = auth_enabled and self._MPUT or self._MDELETE

            self.api_execute(uri, action)
        except Exception as e:
            _log.error("Failed enable authentication in %s%s: %r",
                       self._base_uri, self.version_prefix, e)
            raise etcd.EtcdException("Could not toggle authentication")

    def modify_role(self, role_name, permissions=None, perm_key=None):
        """Modifies role."""
        try:
            uri = self.version_prefix + '/auth/roles/' + role_name
            params = {
                'role': role_name,
            }
            if permissions:
                params[perm_key] = {
                    'kv': {
                        'read': [k for k, v in permissions.items() if
                                 'R' in v.upper()],
                        'write': [k for k, v in permissions.items() if
                                  'W' in v.upper()]
                    }
                }
            response = self.json_api_execute(uri, self._MPUT, params=params)
            res = json.loads(response.data.decode('utf-8'))
            return EtcdRole(self, res)
        except Exception as e:
            _log.error("Failed to modify role in %s%s: %r",
                       self._base_uri, self.version_prefix, e)
            raise etcd.EtcdException("Could not modify role")

    def json_api_execute(self, path, method, params=None, timeout=None):
        """ Executes the query. """

        some_request_failed = False
        response = False

        if timeout is None:
            timeout = self.read_timeout

        if timeout == 0:
            timeout = None

        if not path.startswith('/'):
            raise ValueError('Path does not start with /')

        while not response:
            try:
                url = self._base_uri + path
                json_payload = json.dumps(params)
                headers = self._get_headers()
                headers['Content-Type'] = 'application/json'
                response = self.http.urlopen(method,
                                             url,
                                             body=json_payload,
                                             timeout=timeout,
                                             redirect=self.allow_redirect,
                                             headers=headers,
                                             preload_content=False)
            # urllib3 doesn't wrap all httplib exceptions and earlier versions
            # don't wrap socket errors either.
            except (urllib3.exceptions.HTTPError,
                    HTTPException,
                    socket.error) as e:
                _log.error("Request to server %s failed: %r",
                           self._base_uri, e)
                if self._allow_reconnect:
                    _log.info("Reconnection allowed, looking for another "
                              "server.")
                    # _next_server() raises EtcdException if there are no
                    # machines left to try, breaking out of the loop.
                    self._base_uri = self._next_server()
                    some_request_failed = True
                else:
                    _log.debug("Reconnection disabled, giving up.")
                    raise etcd.EtcdConnectionFailed(
                        "Connection to etcd failed due to %r" % e)
            except:
                _log.exception("Unexpected request failure, re-raising.")
                raise

            else:
                # Check the cluster ID hasn't changed under us.  We use
                # preload_content=False above so we can read the headers
                # before we wait for the content of a long poll.
                cluster_id = response.getheader("x-etcd-cluster-id")
                id_changed = (self.expected_cluster_id
                              and cluster_id is not None and
                              cluster_id != self.expected_cluster_id)
                # Update the ID so we only raise the exception once.
                old_expected_cluster_id = self.expected_cluster_id
                self.expected_cluster_id = cluster_id
                if id_changed:
                    # Defensive: clear the pool so that we connect afresh next
                    # time.
                    self.http.clear()
                    raise etcd.EtcdClusterIdChanged(
                        'The UUID of the cluster changed from {} to '
                        '{}.'.format(old_expected_cluster_id, cluster_id))
                try:
                    response = self._handle_server_response(response)
                except etcd.EtcdException as e:
                    # This may happen during etcd startup.
                    # It's a very short-lived condition, so retry just once.
                    if "during rolling upgrades" in e.payload['message'] \
                            and not some_request_failed:
                        response = False
                        some_request_failed = True
                        continue
                    raise

        if some_request_failed:
            if not self._use_proxies:
                # The cluster may have changed since last invocation
                self._machines_cache = self.machines
            self._machines_cache.remove(self._base_uri)
        return response


class EtcdUser(object):
    def __init__(self, auth_client, json_user):
        self.client = auth_client
        self.name = json_user.get('user')
        self._roles = json_user.get('roles') or []

    @property
    def password(self):
        """Empty property for password."""
        return None

    @password.setter
    def password(self, new_password):
        """Change user's password."""
        self.client.create_user(self.name, new_password)

    @property
    def roles(self):
        return tuple(self._roles)

    @roles.setter
    def roles(self, roles):
        existing_roles = set(self._roles)
        new_roles = set(roles)

        if existing_roles == new_roles:
            _log.debug('User %s already belongs to %s', self.name, self._roles)
            return

        to_revoke = existing_roles - new_roles
        to_grant = new_roles - existing_roles

        if to_revoke:
            self.client.create_user(self.name, None, roles=list(to_revoke),
                                    role_action='revoke')
        if to_grant:
            self.client.create_user(self.name, None, roles=list(to_grant),
                                    role_action='grant')
        self._roles = new_roles


class EtcdRole(object):
    def __init__(self, auth_client, role_json):
        self.client = auth_client
        self.name = role_json.get('role')
        self.permissions = RolePermissionsDict(self, role_json)


class RolePermissionsDict(dict):
    _PERMISSIONS = {'R', 'W'}

    def __init__(self, etcd_role, role_json, *args, **kwargs):
        super(RolePermissionsDict, self).__init__(*args, **kwargs)
        self.role = etcd_role
        permissions = role_json.get('permissions')
        if permissions and 'kv' in permissions:
            self.__add_permissions(permissions, 'read', 'R')
            self.__add_permissions(permissions, 'write', 'W')

    def __add_permissions(self, permissions, label, symbol):
        if label in permissions['kv'] and permissions['kv'][label]:
            for path in permissions['kv'][label]:
                existing_perms = dict.get(self, path)
                if existing_perms:
                    dict.__setitem__(self, path,
                                     existing_perms + symbol)
                else:
                    dict.__setitem__(self, path, symbol)

    def __setitem__(self, key, value):
        if not value:
            raise ValueError('Permissions may only be (R)ead or (W)ite')
        perms = set(x.upper() for x in value)
        if not perms <= RolePermissionsDict._PERMISSIONS:
            raise ValueError('Permissions may only be (R)ead or (W)ite')

        role_name = self.role.name
        perm_dict = {key: value}
        existing_value = dict.get(self, key)

        if existing_value:
            existing_perms = set(x.upper() for x in existing_value)
            if perms != existing_perms:
                to_grant = perms - existing_perms
                to_revoke = existing_perms - perms

                if to_revoke:
                    perm_dict = {key: ''.join(to_revoke)}
                    self.role.client.modify_role(role_name, perm_dict, 'revoke')
                if to_grant:
                    perm_dict = {key: ''.join(to_grant)}
                    self.role.client.modify_role(role_name, perm_dict, 'grant')
            else:
                _log.debug('Permission %s=%s already granted', key, value)
        else:
            self.role.client.modify_role(role_name, perm_dict, 'grant')

        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        self.role.client.modify_role(self.role.name, {key: 'RW'}, 'revoke')
        dict.__delitem__(self, key)

import unittest
import shutil
import tempfile

import time

import etcd
import etcd.auth
from etcd.tests.integration.test_simple import EtcdIntegrationTest
from etcd.tests.integration import helpers


class TestAuthentication(unittest.TestCase):
    def setUp(self):
        # Restart etcd for each test (since some tests will lock others out)
        program = EtcdIntegrationTest._get_exe()
        self.directory = tempfile.mkdtemp(prefix='python-etcd')
        self.processHelper = helpers.EtcdProcessHelper(
            self.directory,
            proc_name=program,
            port_range_start=6001,
            internal_port_range_start=8001)
        self.processHelper.run(number=1)
        self.client = etcd.auth.AuthClient(port=6001)

        # Wait for sync, to avoid:
        # "Not capable of accessing auth feature during rolling upgrades."
        time.sleep(0.5)

    def tearDown(self):
        self.processHelper.stop()
        shutil.rmtree(self.directory)

    def test_create_user(self):
        user = self.client.create_user('username', 'password')
        assert user.name == 'username'
        assert len(user.roles) == 0

    def test_create_user_with_role(self):
        user = self.client.create_user('username', 'password', roles=['root'])
        assert user.name == 'username'
        assert user.roles == ('root',)

    def test_create_user_add_role(self):
        user = self.client.create_user('username', 'password')
        self.client.create_role('role')

        # Empty to [root]
        user.roles = ['root']
        user = self.client.get_user('username')
        assert user.roles == ('root',)

        # [root] to [root,role]
        user.roles = ['root', 'role']
        user = self.client.get_user('username')
        assert user.roles == ('role', 'root')

        # [root,role] to [role]
        user.roles = ['role']
        user = self.client.get_user('username')
        assert user.roles == ('role',)

    def test_usernames_empty(self):
        assert len(self.client.usernames) == 0

    def test_usernames(self):
        self.client.create_user('username', 'password', roles=['root'])
        assert self.client.usernames == ['username']

    def test_users(self):
        self.client.create_user('username', 'password', roles=['root'])
        users = self.client.users
        assert len(users) == 1
        assert users[0].name == 'username'

    def test_get_user(self):
        self.client.create_user('username', 'password', roles=['root'])
        user = self.client.get_user('username')
        assert user.roles == ('root',)

    def test_get_user_not_found(self):
        self.assertRaises(etcd.EtcdException, self.client.get_user, 'username')

    def test_set_user_password(self):
        self.client.create_user('username', 'password', roles=['root'])
        user = self.client.get_user('username')
        assert not user.password
        user.password = 'new_password'
        assert not user.password

    def test_create_role(self):
        role = self.client.create_role('role')
        assert role.name == 'role'
        assert len(role.permissions) == 0

    def test_grant_role(self):
        role = self.client.create_role('role')

        # Read access to keys under /foo
        role.permissions['/foo/*'] = 'R'
        assert len(role.permissions) == 1
        assert role.permissions['/foo/*'] == 'R'

        # Write access to the key at /foo/bar
        role.permissions['/foo/bar'] = 'W'
        assert len(role.permissions) == 2

        # Full access to keys under /pub
        role.permissions['/pub/*'] = 'RW'
        assert len(role.permissions) == 3

        # Fresh fetch to bust cache:
        role = self.client.get_role('role')
        assert len(role.permissions) == 3

    def test_get_role(self):
        role = self.client.create_role('role')
        role.permissions['/foo/*'] = 'R'

        role = self.client.get_role('role')
        assert len(role.permissions) == 1

    def test_revoke_role(self):
        role = self.client.create_role('role')
        role.permissions['/foo/*'] = 'R'

        del role.permissions['/foo/*']

        role = self.client.get_role('role')
        assert len(role.permissions) == 0

    def test_modify_role_invalid(self):
        role = self.client.create_role('role')
        self.assertRaises(ValueError, role.permissions.__setitem__, '/foo/*',
                          '')

    def test_modify_role_permissions(self):
        role = self.client.create_role('role')
        role.permissions['/foo/*'] = 'R'

        # Replace R with W
        role.permissions['/foo/*'] = 'W'
        assert role.permissions['/foo/*'] == 'W'
        role = self.client.get_role('role')
        assert role.permissions['/foo/*'] == 'W'

        # Extend W to RW
        role.permissions['/foo/*'] = 'WR'
        role = self.client.get_role('role')
        assert role.permissions['/foo/*'] == 'RW'

        # NO-OP RW to RW
        role.permissions['/foo/*'] = 'RW'
        role = self.client.get_role('role')
        assert role.permissions['/foo/*'] == 'RW'

        # Reduce RW to W
        role.permissions['/foo/*'] = 'W'
        role = self.client.get_role('role')
        assert role.permissions['/foo/*'] == 'W'

    def test_role_names_empty(self):
        assert self.client.role_names == ['root']

    def test_role_names(self):
        self.client.create_role('role')
        assert self.client.role_names == ['role', 'root']

    def test_roles(self):
        self.client.create_role('role')
        assert len(self.client.roles) == 2

    def test_enable_auth(self):
        # Store a value, lock out guests
        self.client.write('/foo', 'bar')
        self.client.create_user('root', 'rootpassword')
        # Creating role before auth is enabled prevents default permissions
        self.client.create_role('guest')
        self.client.toggle_auth(True)

        # Now we can't access key:
        try:
            self.client.get('/foo')
            self.fail('Expected exception')
        except etcd.EtcdException as e:
            assert 'Insufficient credentials' in str(e)

        # But an authenticated client can:
        root_client = etcd.Client(port=6001,
                                  username='root',
                                  password='rootpassword')
        assert root_client.get('/foo').value == 'bar'

    def test_enable_auth_before_root_created(self):
        self.assertRaises(etcd.EtcdException, self.client.toggle_auth, True)

from .integration.test_simple import EtcdIntegrationTest
from ..auth import EtcdUser, Auth, EtcdRole
from ..client import Client
from ..common import EtcdKeyNotFound, EtcdInsufficientPermissions, EtcdException


class TestEtcdAuthBase(EtcdIntegrationTest):
    cl_size = 1

    def setUp(self):
        # Sets up the root user, toggles auth
        u = EtcdUser(self.client, 'root')
        u.password = 'testpass'
        u.write()
        self.client = Client(port=6001, username='root',
                                password='testpass')
        self.unclient = Client(port=6001)
        a = Auth(self.client)
        a.active = True

    def tearDown(self):
        u = EtcdUser(self.client, 'test_user')
        r = EtcdRole(self.client, 'test_role')
        try:
            u.delete()
        except:
            pass
        try:
            r.delete()
        except:
            pass
        a = Auth(self.client)
        a.active = False


class EtcdUserTest(TestEtcdAuthBase):
    def test_names(self):
        u = EtcdUser(self.client, 'test_user')
        self.assertEquals(u.names, ['root'])

    def test_read(self):
        u = EtcdUser(self.client, 'root')
        # Reading an existing user succeeds
        try:
            u.read()
        except Exception:
            self.fail("reading the root user raised an exception")

        # roles for said user are fetched
        self.assertEquals(u.roles, set(['root']))

        # The user is correctly rendered out
        self.assertEquals(u._to_net(), [{'user': 'root', 'password': None,
                                         'roles': ['root']}])

        # An inexistent user raises the appropriate exception
        u = EtcdUser(self.client, 'user.does.not.exist')
        self.assertRaises(EtcdKeyNotFound, u.read)

        # Reading with an unnticated client raises an exception
        u = EtcdUser(self.unclient, 'root')
        self.assertRaises(EtcdInsufficientPermissions, u.read)

        # Generic errors are caught
        c = Client(port=9999)
        u = EtcdUser(c, 'root')
        self.assertRaises(EtcdException, u.read)

    def test_write_and_delete(self):
        # Create an user
        u = EtcdUser(self.client, 'test_user')
        u.roles.add('guest')
        u.roles.add('root')
        # directly from my suitcase
        u.password = '123456'
        try:
            u.write()
        except:
            self.fail("creating a user doesn't work")
        # Password gets wiped
        self.assertEquals(u.password, None)
        u.read()
        # Verify we can log in as this user and access the (it has the
        # root role)
        cl = Client(port=6001, username='test_user',
                         password='123456')
        ul = EtcdUser(cl, 'root')
        try:
            ul.read()
        except EtcdInsufficientPermissions:
            self.fail("Reading with the new user is not possible")

        self.assertEquals(u.name, "test_user")
        self.assertEquals(u.roles, set(['guest', 'root']))
        # set roles as a list, it works!
        u.roles = ['guest', 'test_group']
        try:
            u.write()
        except:
            self.fail("updating a user you previously created fails")
        u.read()
        self.assertIn('test_group', u.roles)

        # Unrized access is properly handled
        ua = EtcdUser(self.unclient, 'test_user')
        self.assertRaises(EtcdInsufficientPermissions, ua.write)

        # now let's test deletion
        du = EtcdUser(self.client, 'user.does.not.exist')
        self.assertRaises(EtcdKeyNotFound, du.delete)

        # Delete test_user
        u.delete()
        self.assertRaises(EtcdKeyNotFound, u.read)
        # Permissions are properly handled
        self.assertRaises(EtcdInsufficientPermissions, ua.delete)


class EtcdRoleTest(TestEtcdAuthBase):
    def test_names(self):
        r = EtcdRole(self.client, 'guest')
        self.assertListEqual(r.names, [u'guest', u'root'])

    def test_read(self):
        r = EtcdRole(self.client, 'guest')
        try:
            r.read()
        except:
            self.fail('Reading an existing role failed')

        self.assertEquals(r.acls, {'*': 'RW'})
        # We can actually skip most other read tests as they are common
        # with EtcdUser

    def test_write_and_delete(self):
        r = EtcdRole(self.client, 'test_role')
        r.acls = {'*': 'R', '/test/*': 'RW'}
        try:
            r.write()
        except:
            self.fail("Writing a simple groups should not fail")

        r1 = EtcdRole(self.client, 'test_role')
        r1.read()
        self.assertEquals(r1.acls, r.acls)
        r.revoke('/test/*', 'W')
        r.write()
        r1.read()
        self.assertEquals(r1.acls, {'*': 'R', '/test/*': 'R'})
        r.grant('/pub/*', 'RW')
        r.write()
        r1.read()
        self.assertEquals(r1.acls['/pub/*'], 'RW')
        # All other exceptions are tested by the user tests
        r1.name = None
        self.assertRaises(EtcdException, r1.write)
        # ditto for delete
        try:
            r.delete()
        except:
            self.fail("A normal delete should not fail")
        self.assertRaises(EtcdKeyNotFound, r.read)

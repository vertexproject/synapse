import unittest

import synapse.httpapi as s_httpapi

class WootExc(Exception):pass

class Woot:
    def __init__(self, x, y=None):
        self.x = x
        self.y = y

    def getstuff(self):
        return self.x, self.y

    def dostuff(self, foo, bar=None):
        return (foo,bar)

    def raisestuff(self):
        raise WootExc('gronk!')

class HttpApiTest(unittest.TestCase):

    def test_httpapi_basics(self):

        api = s_httpapi.HttpApi()

        role = 'testrole'
        apikey = 'testkey'

        api.addRole(role)
        api.addApiKey(apikey,name='testname')
        api.addApiKeyRole(apikey,role)

        api.addApiObject('woot', 'synapse.tests.test_httpapi.Woot', 10, y=30)
        api.addApiPath('/woot/v1/dostuff', 'woot', 'dostuff' )
        api.addApiPath('/woot/v1/getstuff', 'woot', 'getstuff' )
        api.addApiPath('/woot/v1/raisestuff', 'woot', 'raisestuff' )

        ret = api.callApiPath(apikey, '/woot/v1/dostuff', 'haha', bar='hehe')

        self.assertIsNone( ret.get('err') )
        self.assertIsNotNone( ret.get('took') )
        self.assertEqual( ret.get('ret'), ('haha','hehe') )

        ret = api.callApiPath(apikey, '/woot/v1/raisestuff')
        self.assertIsNone( ret.get('ret') )
        self.assertEqual( ret.get('err'), 'WootExc')
        self.assertEqual( ret.get('msg'), 'gronk!')

        # 1 for ours and one for builtin root
        self.assertEqual( len(api.getRoles()), 2 )
        self.assertEqual( len(api.getApiKeys()), 2 )

        keyinfo = api.getApiKey(apikey)
        self.assertEqual( keyinfo.get('en'), True )
        self.assertEqual( keyinfo.get('name'), 'testname' )

        roleinfo = api.getRole(role)
        self.assertEqual(roleinfo.get('en'), True)

        api.addRoleAllow(role,'/role/test')
        api.addRoleAllow(role,'/role/glob*')

        api.addApiKeyAllow(apikey,'/key/test')
        api.addApiKeyAllow(apikey,'/key/glob*')

        self.assertIsNone( api.getApiKeyAllow(apikey,'/newp/newp') )
        self.assertIsNotNone( api.getApiKeyAllow(apikey,'/key/test') )
        self.assertIsNotNone( api.getApiKeyAllow(apikey,'/key/test') )
        self.assertIsNotNone( api.getApiKeyAllow(apikey,'/key/glob/visi') )
        self.assertIsNotNone( api.getApiKeyAllow(apikey,'/role/test') )
        self.assertIsNotNone( api.getApiKeyAllow(apikey,'/role/glob/visi') )

        self.assertEqual( len(api.rulecache), 4 )

        api.addApiKeyAllow(apikey,'/bump')
        self.assertEqual( len(api.rulecache), 0 )

        api.setApiKeyInfo(apikey,'en',False)
        self.assertIsNone( api.getApiKeyAllow(apikey,'/key/test') )

        api.setApiKeyInfo(apikey,'en',True)
        self.assertIsNotNone( api.getApiKeyAllow(apikey,'/key/test') )

        api.setRoleInfo(role,'en',False)
        self.assertIsNone( api.getApiKeyAllow(apikey,'/role/test') )

        api.setRoleInfo(role,'en',True)
        self.assertIsNotNone( api.getApiKeyAllow(apikey,'/role/test') )

        api.delApiKeyRole(apikey,role)
        self.assertIsNone( api.getApiKeyAllow(apikey,'/role/test') )

        api.delApiKey(apikey)
        self.assertIsNone( api.getApiKey(apikey) )

        api.fini()

    def test_httpapi_nosuch(self):

        api = s_httpapi.HttpApi()
        self.assertRaises( s_httpapi.NoSuchApiKey, api.addApiKeyAllow, 'newp', 'newp' )
        self.assertRaises( s_httpapi.NoSuchApiObj, api.addApiPath, 'newp', 'newp', 'newp')

    def test_httpapi_dups(self):
        api = s_httpapi.HttpApi()
        api.addRole('testrole')
        api.addApiKey('testkey')

        self.assertRaises( s_httpapi.DupRole, api.addRole, 'testrole' )
        self.assertRaises( s_httpapi.DupApiKey, api.addApiKey, 'testkey' )

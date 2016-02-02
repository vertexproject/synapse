from synapse.tests.common import *

from synapse.lib.moddef import *

class Foo:
    def bar(self):
        return 'bar'

def bazfunc():
    return 'baz'

class ModDefTest(SynTest):

    def test_moddef_ispy(self):
        self.assertTrue( isPyStdLib('os') )
        self.assertTrue( isPyStdLib('os.path') )
        self.assertFalse( isPyStdLib('synapse') )

    def test_moddef_get(self):
        moddef = getModDef('synapse')
        self.assertTrue( moddef[1].get('pkg') )
        self.assertIsNotNone( moddef[1].get('path') )

    def test_moddef_imps(self):
        moddef = getModDef('synapse.tests.test_moddef')
        modimps = set( getModDefImps(moddef) )

        self.assertIn( 'synapse.lib.moddef', modimps )

    def test_moddef_sitedeps(self):
        deps = getSiteDeps( getModDef('synapse.tests.test_moddef') )

        self.assertIsNotNone( deps.get('synapse') )

        self.assertIsNotNone( deps.get('synapse.tests') )
        self.assertIsNotNone( deps.get('synapse.tests.test_moddef') )

        self.assertIsNotNone( deps.get('synapse.lib') )
        self.assertIsNotNone( deps.get('synapse.lib.moddef') )

    def test_moddef_calldeps(self):
        foo = Foo()

        deps = getSiteDeps( getCallModDef(foo.bar ) )
        self.assertIsNotNone( deps.get('synapse.lib') )
        self.assertIsNotNone( deps.get('synapse.lib.moddef') )

        deps = getSiteDeps( getCallModDef(bazfunc) )
        self.assertIsNotNone( deps.get('synapse.lib') )
        self.assertIsNotNone( deps.get('synapse.lib.moddef') )

    def test_moddef_modsbypath(self):
        path = os.path.dirname(__file__)
        deps = getModsByPath(path)
        self.assertIsNone( deps.get('newp') )
        self.assertIsNotNone( deps.get('test_moddef') )

    def test_moddef_modsbypath_nodir(self):
        self.assertRaises( NoSuchDir, getModsByPath, 'newp/newp/newp' )

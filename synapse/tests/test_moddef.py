from synapse.tests.common import *

from synapse.lib.moddef import *

class Foo:
    def bar(self):
        return 'bar'

def bazfunc():
    return 'baz'

class ModDefTest(SynTest):

    def test_moddef_ispy(self):
        self.true(isPyStdLib('os'))
        self.true(isPyStdLib('os.path'))
        self.false(isPyStdLib('synapse'))

    def test_moddef_get(self):
        moddef = getModDef('synapse')
        self.true(moddef[1].get('pkg'))
        self.nn(moddef[1].get('path'))

    def test_moddef_imps(self):
        moddef = getModDef('synapse.tests.test_moddef')
        modimps = set(getModDefImps(moddef))

        self.isin('synapse.lib.moddef', modimps)

    def test_moddef_sitedeps(self):
        deps = getSiteDeps(getModDef('synapse.tests.test_moddef'))

        self.nn(deps.get('synapse'))

        self.nn(deps.get('synapse.tests'))
        self.nn(deps.get('synapse.tests.test_moddef'))

        self.nn(deps.get('synapse.lib'))
        self.nn(deps.get('synapse.lib.moddef'))

    def test_moddef_calldeps(self):
        foo = Foo()

        deps = getSiteDeps(getCallModDef(foo.bar))
        self.nn(deps.get('synapse.lib'))
        self.nn(deps.get('synapse.lib.moddef'))

        deps = getSiteDeps(getCallModDef(bazfunc))
        self.nn(deps.get('synapse.lib'))
        self.nn(deps.get('synapse.lib.moddef'))

    def test_moddef_modsbypath(self):
        path = os.path.dirname(__file__)
        deps = getModsByPath(path)
        self.none(deps.get('newp'))
        self.nn(deps.get('test_moddef'))

    def test_moddef_modsbypath_nodir(self):
        self.raises(NoSuchDir, getModsByPath, 'newp/newp/newp')

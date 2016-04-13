import synapse.cortex as s_cortex
import synapse.lib.plugins as s_plugins

from synapse.tests.common import *

class PlugTest(SynTest):

    def test_plugins_init(self):
        core = s_cortex.openurl('ram://')
        srccode = '''
def _syn_plug_init(bus):
    print('HI')

def _syn_plug_fini(bus):
    print('BYE')
        '''
        core.formTufoByProp('plugin', guid(), en=1, source=srccode)
        plug = s_plugins.Plugins(core)

        plug.fini()
        core.fini()

    #def test_plugins_set_en(self):
    #def test_plugins_set_source(self):

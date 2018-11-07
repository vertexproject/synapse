import unittest
raise unittest.SkipTest()
# FIXME broken because no configable

import synapse.tools.autodoc as s_autodoc

class TestAutoDoc(s_t_utils.SynTest):

    def test_tools_autodoc(self):

        with self.getTestDir() as path:

            save = os.path.join(path, 'model.rst')
            outp = self.getTestOutp()
            argv = ['--doc-model', '--savefile', save]
            self.eq(s_autodoc.main(argv, outp=outp), 0)

            with open(save, 'rb') as fd:
                rst = fd.read().decode()

            self.true('inet:ipv4:asn = <inet:asn> (default: -1)' in rst)
            self.true('Universal Props' in rst)

    def test_tools_autodoc_configable(self):
        with self.getTestDir() as path:

            save = os.path.join(path, 'configables.rst')
            outp = self.getTestOutp()
            argv = ['--configable-opts', '--savefile', save]
            self.eq(s_autodoc.main(argv, outp=outp), 0)

            with open(save, 'rb') as fd:
                rst = fd.read().decode()

            self.true('Synapse Configable Classes' in rst)
            # Some cell configs which are comming in from @staticmethod and initConfDefs()
            self.isin('synapse.lib.auth.Auth', rst)
            self.isin('synapse.cryotank.CryoCell', rst)
            self.true('axon:mapsize' in rst)
            self.true('The TCP port the Cell binds to (defaults to dynamic)' in rst)
            self.true('The TCP port the Neuron binds to' in rst)

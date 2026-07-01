import synapse.assets as s_assets

import synapse.tests.utils as s_t_utils

class AssetsTest(s_t_utils.SynTest):

    def test_assets_getstorm(self):
        text = s_assets.getStorm('migrations', 'test.storm')
        self.eq(text, 'test\n')

    def test_assets_getassetpath(self):
        fp = s_assets.getAssetPath('storm', 'migrations', 'test.storm')
        self.true(fp.startswith(s_assets.dirname))
        self.true(fp.endswith('test.storm'))

        with self.getLoggerStream('synapse.assets') as stream:
            with self.raises(ValueError) as cm:
                s_assets.getAssetPath('..', 'newp.storm')

        self.isin('Path escaping detected', cm.exception.args[0])

        with self.getLoggerStream('synapse.assets') as stream:
            with self.raises(ValueError) as cm:
                s_assets.getAssetPath('storm', 'newp.storm')

        self.isin('Asset does not exist', cm.exception.args[0])

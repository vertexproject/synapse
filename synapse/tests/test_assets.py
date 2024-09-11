import os
import synapse.assets as s_assets

import synapse.tests.utils as s_t_utils

class TestAssets(s_t_utils.SynTest):

    def test_assets_path(self):

        fp = s_assets.getAssetPath('storm', 'migrations', 'test.storm')
        self.true(os.path.isfile(fp))

        with self.raises(ValueError) as cm:
            s_assets.getAssetPath('../../../../../../../etc/passwd')
        self.isin('Path escaping', str(cm.exception))

        with self.raises(ValueError) as cm:
            s_assets.getAssetPath('newp', 'does', 'not', 'exit')
        self.isin('Asset does not exist', str(cm.exception))

    def test_assets_storm(self):

        text = s_assets.getStorm('migrations', 'test.storm')
        self.isinstance(text, str)
        self.gt(len(text), 0)

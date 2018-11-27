import synapse.glob as s_glob
import synapse.common as s_common

import synapse.tests.test_cortex as t_cortex
import synapse.tests.test_lib_snap as t_snap
import synapse.tests.test_lib_layer as t_layer

class RemoteLayerTestBase:
    def setUp(self):
        '''
        Spin up a separate dmon that's serving up a remote LMDB layer, and set up our test layer to point to tha, and
        set up our test layer to point to that.
        '''
        self.alt_write_layer = None
        self._dmonctx = self.getTestDmon(mirror='dmonlayer')
        self._layrdmon = s_glob.sync(self._dmonctx.__aenter__())
        telepath = self.getTestUrl(self._layrdmon, 'layer1')
        bootconf = {
            'type': 'layer-remote'
        }
        cellconf = {
            'remote:telepath': telepath
        }
        self._testdirctx = self.getTestConfDir('', boot=bootconf, conf=cellconf)
        self._testdir = self._testdirctx.__enter__()
        s_common.yamlsave(cellconf, self._testdir, 'cell.yaml')
        self.alt_write_layer = self._testdir

    def tearDown(self):
        self._testdirctx.__exit__(None, None, None)
        s_glob.sync(self._dmonctx.__aexit__(None, None, None))
        self.alt_write_layer = None

class RemoteLayerTest(RemoteLayerTestBase, t_layer.LayerTest):
    '''
    Note:  doesn't do anything right now, but if we ever do add layer unit tests, it will
    '''
    pass

class RemoteLayerSnapTest(RemoteLayerTestBase, t_snap.SnapTest):
    pass

class RemoteLayerCortexTest(RemoteLayerTestBase, t_cortex.CortexTest):
    pass

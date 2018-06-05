import synapse.axon as s_axon
import synapse.cells as s_cells
import synapse.cryotank as s_cryotank

from synapse.tests.common import *

class CellTest(SynTest):
    def test_getcells(self):
        data = s_cells.getCells()
        data = {k: v for k, v in data}
        self.isin('cortex', data)

    def test_deploy(self):
        with self.getTestDir() as dirn:
            s_cells.deploy('cortex', dirn, {'test': 1})
            d = s_common.yamlload(dirn, 'boot.yaml')
            self.eq(d, {'type': 'cortex', 'test': 1, })

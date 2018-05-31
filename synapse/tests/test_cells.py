import synapse.axon as s_axon
import synapse.cells as s_cells
import synapse.cryotank as s_cryotank

from synapse.tests.common import *

class CellTest(SynTest):
    def test_getcells(self):
        data = s_cells.getCells()
        data = {k: v for k, v in data}
        self.isin('cortex', data)

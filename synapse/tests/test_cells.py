import synapse.axon as s_axon
import synapse.cells as s_cells
import synapse.cryotank as s_cryotank

from synapse.tests.common import *

class CellTest(SynTest):

    def test_cell_cryo(self):
        with self.getTestDir() as dirn:
            with s_cells.cryo(dirn) as cryo:
                self.isinstance(cryo, s_cryotank.CryoCell)

    def test_cell_axon(self):
        with self.getTestDir() as dirn:
            with s_cells.axon(dirn) as axon:
                self.isinstance(axon, s_axon.AxonCell)

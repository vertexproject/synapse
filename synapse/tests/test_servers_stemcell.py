import os

import synapse.tests.utils as s_test

import synapse.axon as s_axon
import synapse.cortex as s_cortex
import synapse.common as s_common
import synapse.lib.jsonstor as s_jsonstor

import synapse.servers.stemcell as s_stemcell

class StemCellTest(s_test.SynTest):

    async def test_servers_stemcell(self):

        with self.getTestDir() as dirn:

            conf = {'cell:ctor': 'synapse.cells.axon'}
            s_common.yamlsave(conf, dirn, 'cell.yaml')
            cell = s_stemcell.getStemCell(dirn)
            self.true(cell is s_axon.Axon)

            conf = {'cell:ctor': 'synapse.cells.cortex'}
            s_common.yamlsave(conf, dirn, 'cell.yaml')
            cell = s_stemcell.getStemCell(dirn)
            self.true(cell is s_cortex.Cortex)

            conf = {'cell:ctor': 'synapse.cells.jsonstor'}
            s_common.yamlsave(conf, dirn, 'cell.yaml')
            cell = s_stemcell.getStemCell(dirn)
            self.true(cell is s_jsonstor.JsonStorCell)

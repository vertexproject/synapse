import os

import synapse.tests.utils as s_test

import synapse.axon as s_axon
import synapse.cortex as s_cortex
import synapse.common as s_common

import synapse.lib.aha as s_aha
import synapse.lib.cell as s_cell
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

            conf = {'cell:ctor': 'synapse.cells.aha'}
            s_common.yamlsave(conf, dirn, 'cell.yaml')
            cell = s_stemcell.getStemCell(dirn)
            self.true(cell is s_aha.AhaCell)

            conf = {'cell:ctor': 'synapse.lib.cell.Cell'}
            s_common.yamlsave(conf, dirn, 'cell.yaml')
            cell = s_stemcell.getStemCell(dirn)
            self.true(cell is s_cell.Cell)

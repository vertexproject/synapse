import os

import synapse.tests.utils as s_test

import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.cryotank as s_cryotank

import synapse.lib.aha as s_aha
import synapse.lib.cell as s_cell
import synapse.lib.jsonstor as s_jsonstor

import synapse.servers.stemcell as s_stemcell

class StemCellTest(s_test.SynTest):

    async def test_servers_stemcell(self):

        with self.getTestDir() as dirn:

            cellyaml = os.path.join(dirn, 'cell.yaml')

            conf = {'cell:ctor': 'synapse.cells.axon'}
            s_common.yamlsave(conf, cellyaml)
            cell = s_stemcell.getStemCell(dirn)
            self.true(cell is s_axon.Axon)

            conf = {'cell:ctor': 'synapse.cells.cortex'}
            s_common.yamlsave(conf, cellyaml)
            cell = s_stemcell.getStemCell(dirn)
            self.true(cell is s_cortex.Cortex)

            conf = {'cell:ctor': 'synapse.cells.jsonstor'}
            s_common.yamlsave(conf, cellyaml)
            cell = s_stemcell.getStemCell(dirn)
            self.true(cell is s_jsonstor.JsonStorCell)

            conf = {'cell:ctor': 'synapse.cells.aha'}
            s_common.yamlsave(conf, cellyaml)
            cell = s_stemcell.getStemCell(dirn)
            self.true(cell is s_aha.AhaCell)

            # Direct python class paths
            conf = {'cell:ctor': 'synapse.lib.cell.Cell'}
            s_common.yamlsave(conf, cellyaml)
            cell = s_stemcell.getStemCell(dirn)
            self.true(cell is s_cell.Cell)

            # Resolve a envar
            os.unlink(cellyaml)
            self.false(os.path.isfile(cellyaml))

            with self.setTstEnvars(SYN_STEM_CELL_CTOR='synapse.cells.cryotank'):
                cell = s_stemcell.getStemCell(dirn)
                self.true(cell is s_cryotank.CryoCell)

            # Sad paths
            with self.setTstEnvars(SYN_STEM_CELL_CTOR='synapse.lib.newp.Newp'):
                with self.raises(s_exc.NoSuchCtor):
                    cell = s_stemcell.getStemCell(dirn)

            with self.raises(s_exc.NoSuchFile):
                cell = s_stemcell.getStemCell(dirn)

            os.rmdir(dirn)
            with self.raises(s_exc.NoSuchDir):
                cell = s_stemcell.getStemCell(dirn)

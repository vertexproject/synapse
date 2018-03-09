import time
import synapse.cryotank as s_cryotank

import synapse.tests.common as s_tc

class CryoIndexTest(s_tc.SynTest):
    def test_cryotank_index(self):
        with self.getTestDir() as dirn, s_cryotank.CryoTank(dirn) as tank:
            idxr = tank.indexer
            data1 = {'foo': 1234, 'bar': 'stringval'}

            # Simple index add/remove
            self.eq([], idxr.getIndices())
            idxr.addIndex('first', 'int', 'foo')
            idxs = idxr.getIndices()
            self.eq(idxs[0]['propname'], 'first')
            idxr.delIndex('first')
            self.eq([], idxr.getIndices())

            tank.puts([data1])
            idxr.addIndex('first', 'int', 'foo')
            idxs = idxr.getIndices()
            self.eq(1, idxs[0]['nextoffset'])
            self.eq(1, idxs[0]['ngood'])
            import ipdb; ipdb.set_trace()
            retn = list(idxr.rowsByPropVal('first', retoffset=True, retraw=True, retnorm=True))
            print(retn)
            self.eq(1, len(retn))

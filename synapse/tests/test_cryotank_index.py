import time
import synapse.cryotank as s_cryotank
import synapse.cryotank_index as s_cryotank_index
import synapse.lib.msgpack as s_msgpack

import synapse.tests.common as s_tc

logger = s_cryotank_index.logger

class CryoIndexTest(s_tc.SynTest):
    def test_cryotank_index(self):
        with self.getTestDir() as dirn, s_cryotank.CryoTank(dirn) as tank:
            idxr = tank.indexer
            data1 = {'foo': 1234, 'bar': 'stringval'}
            data2 = {'foo': 2345, 'baz': 4567, 'bar': 'strinstrin'}
            data3 = {'foo': 388383, 'bar': ('strinstrin' * 20)}
            baddata = {'foo': 'bad'}

            # Simple index add/remove
            self.eq([], idxr.getIndices())
            idxr.addIndex('first', 'int', 'foo')
            self.raises(ValueError, idxr.addIndex, 'first', 'int', 'foo')
            idxs = idxr.getIndices()
            self.eq(idxs[0]['propname'], 'first')
            idxr.delIndex('first')
            self.raises(ValueError, idxr.delIndex, 'first')
            self.eq([], idxr.getIndices())

            self.genraises(ValueError, idxr.normValuByPropVal, 'notanindex')

            # Check simple 1 record, 1 index index and retrieval
            tank.puts([data1])
            time.sleep(1)
            idxr.addIndex('first', 'int', 'foo')
            idxs = idxr.getIndices()
            self.eq(1, idxs[0]['nextoffset'])
            self.eq(1, idxs[0]['ngood'])
            retn = list(idxr.normRecordsByPropVal('first'))
            self.eq(1, len(retn))
            t = retn[0]
            self.eq(2, len(t))
            self.eq(t[0], 0)
            self.eq(t[1], {'first': 1234})

            tank.puts([data2])
            time.sleep(0.1)
            idxs = idxr.getIndices()
            self.eq(2, idxs[0]['nextoffset'])
            self.eq(2, idxs[0]['ngood'])

            # exact query
            retn = list(idxr.rawRecordsByPropVal('first', valu=2345, exact=True))
            self.eq(1, len(retn))
            t = retn[0]
            self.eq(2, len(t))
            self.eq(t[0], 1)
            self.eq(s_msgpack.un(t[1]), data2)

            # second index
            idxr.addIndex('second', 'str', 'bar')
            time.sleep(0.1)

            # prefix search
            retn = list(idxr.normValuByPropVal('second', valu='strin'))
            self.eq(2, len(retn))

            # long value, exact
            tank.puts([data3])
            time.sleep(0.1)
            retn = list(idxr.rawRecordsByPropVal('second', valu='strinstrin' * 20, exact=True))
            self.eq(1, len(retn))
            self.eq(s_msgpack.un(retn[0][1]), data3)

            # long value with prefix
            retn = list(idxr.rawRecordsByPropVal('second', valu='str'))
            self.eq(3, len(retn))

            # Bad data
            tank.puts([baddata])
            time.sleep(0.1)
            idxs = idxr.getIndices()
            self.eq(4, idxs[0]['nextoffset'])
            self.eq(3, idxs[0]['ngood'])
            self.eq(1, idxs[0]['nnormfail'])

            idxr.delIndex('second')
            time.sleep(0.1)

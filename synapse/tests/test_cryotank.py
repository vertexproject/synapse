import time
import random

from unittest.mock import patch

import synapse.exc as s_exc
import synapse.lib.cell as s_cell
import synapse.cryotank as s_cryotank

import synapse.lib.msgpack as s_msgpack

import synapse.tests.common as s_test

logger = s_cryotank.logger

cryodata = (('foo', {'bar': 10}), ('baz', {'faz': 20}))

class CryoTest(s_test.SynTest):

    def test_cryo_cell(self):

        with self.getTestDmon(mirror='cryodmon') as dmon:

            with dmon._getTestProxy('cryo00') as prox:

                self.eq((), prox.list())

                self.true(prox.init('foo'))

                self.eq('foo', prox.list()[0][0])

                self.none(prox.last('foo'))
                self.true(prox.puts('foo', cryodata))

                self.true(prox.puts('foo', cryodata))

                items = list(prox.slice('foo', 1, 3))
                self.eq(items[0][1][0], 'baz')

                metrics = list(prox.metrics('foo', 0, 9999))
                self.len(2, metrics)
                self.eq(2, metrics[0][1]['count'])

                self.eq(3, prox.last('foo')[0])
                self.eq('baz', prox.last('foo')[1][0])

                # test offset storage and updating
                iden = 'asdf'

                self.none(prox.offset('foo', 'asdf'))

                items = list(prox.slice('foo', 0, 1000, iden='asdf'))
                self.eq(0, prox.offset('foo', 'asdf'))

                items = list(prox.slice('foo', 4, 1000, iden='asdf'))
                self.eq(4, prox.offset('foo', 'asdf'))

# FIXME remove before 0.1.0

class Newp:

    def newp_cryo_cell_indexing(self):

        conf = {'bind': '127.0.0.1', 'host': 'localhost', 'defvals': {'mapsize': s_test.TEST_MAP_SIZE}}
        with self.getTestDir() as dirn, s_cryotank.CryoCell(dirn, conf) as cell:

            addr = cell.getCellAddr()
            cuser = s_cell.CellUser(cell.genUserAuth('foo'))
            with cuser.open(addr, timeout=2) as sess:
                user = s_cryotank.CryoClient(sess)

                # Setting the _chunksize to 1 forces iteration on the client
                # side of puts, as well as the server-side.
                user._chunksize = 1
                user.puts('woot:woot', cryodata, timeout=2)

                # Test index operations
                self.raises(s_exc.RetnErr, user.getIndices, 'notpresent')
                self.eq((), user.getIndices('woot:woot'))
                self.raises(s_exc.BadOperArg, user.addIndex, 'woot:woot', 'prop1', 'str', [])
                user.addIndex('woot:woot', 'prop1', 'str', ['0'])
                user.delIndex('woot:woot', 'prop1')
                self.raises(s_exc.RetnErr, user.delIndex, 'woot:woot', 'noexist')
                user.addIndex('woot:woot', 'prop1', 'str', ['0'])
                user.pauseIndex('woot:woot', 'prop1')
                user.pauseIndex('woot:woot')
                user.resumeIndex('woot:woot')
                self.eq([(1, 'baz'), (0, 'foo')], list(user.queryNormValu('woot:woot', 'prop1')))
                self.eq([(1, 'baz')], list(user.queryNormValu('woot:woot', 'prop1', valu='b')))
                self.eq([], list(user.queryNormValu('woot:woot', 'prop1', valu='bz', timeout=10)))
                self.eq([(1, {'prop1': 'baz'})], (list(user.queryNormRecords('woot:woot', 'prop1', valu='b'))))
                self.eq([(1, s_msgpack.en(('baz', {'faz': 20})))],
                        list(user.queryRows('woot:woot', 'prop1', valu='b')))

                user.init('woot:boring', {'noindex': True})
                self.raises(s_exc.RetnErr, user.getIndices, 'woot:boring')

class CryoIndexTest(s_test.SynTest):

    def initWaiter(self, tank, operation):
        return tank.waiter(1, 'cryotank:indexer:noworkleft:' + operation)

    def wait(self, waiter):
        rv = waiter.wait(s_cryotank.CryoTankIndexer.MAX_WAIT_S)
        self.nn(rv)

    def newp_cryotank_index(self):

        with self.getTestDir() as dirn, s_cryotank.CryoTank(dirn, {'mapsize': s_test.TEST_MAP_SIZE}) as tank:

            idxr = tank.indexer

            data1 = {'foo': 1234, 'bar': 'stringval'}
            data2 = {'foo': 2345, 'baz': 4567, 'bar': 'strinstrin'}
            data3 = {'foo': 388383, 'bar': ('strinstrin' * 20)}
            data4 = {'foo2': 9999, 'baz': 4567}
            baddata = {'foo': 'bad'}

            # Simple index add/remove
            self.eq([], idxr.getIndices())
            idxr.addIndex('first', 'int', ['foo'])
            self.raises(DupIndx, idxr.addIndex, 'first', 'int', ['foo'])
            idxs = idxr.getIndices()
            self.eq(idxs[0]['propname'], 'first')
            idxr.delIndex('first')
            self.raises(NoSuchIndx, idxr.delIndex, 'first')
            self.eq([], idxr.getIndices())

            self.genraises(NoSuchIndx, idxr.queryNormValu, 'notanindex')

            # Check simple 1 record, 1 index index and retrieval
            waiter = self.initWaiter(tank, 'addIndex')
            tank.puts([data1])
            idxr.addIndex('first', 'int', ['foo'])
            self.wait(waiter)
            waiter = self.initWaiter(tank, 'getIndices')
            idxs = idxr.getIndices()
            self.wait(waiter)
            self.eq(1, idxs[0]['nextoffset'])
            self.eq(1, idxs[0]['ngood'])
            retn = list(idxr.queryNormRecords('first'))
            self.eq(1, len(retn))
            t = retn[0]
            self.eq(2, len(t))
            self.eq(t[0], 0)
            self.eq(t[1], {'first': 1234})

            waiter = self.initWaiter(tank, 'None')
            tank.puts([data2])
            self.wait(waiter)
            idxs = idxr.getIndices()
            self.eq(2, idxs[0]['nextoffset'])
            self.eq(2, idxs[0]['ngood'])

            # exact query
            retn = list(idxr.queryRows('first', valu=2345, exact=True))
            self.eq(1, len(retn))
            t = retn[0]
            self.eq(2, len(t))
            self.eq(t[0], 1)
            self.eq(s_msgpack.un(t[1]), data2)

            # second index
            waiter = self.initWaiter(tank, 'addIndex')
            idxr.addIndex('second', 'str', ['bar'])
            self.wait(waiter)

            # prefix search
            retn = list(idxr.queryNormValu('second', valu='strin'))
            self.eq(retn, [(0, 'stringval'), (1, 'strinstrin')])

            # long value, exact
            waiter = self.initWaiter(tank, 'None')
            tank.puts([data3])
            self.wait(waiter)
            retn = list(idxr.queryRows('second', valu='strinstrin' * 20, exact=True))
            self.eq(1, len(retn))
            self.eq(s_msgpack.un(retn[0][1]), data3)

            # long value with prefix
            retn = list(idxr.queryRows('second', valu='str'))
            self.eq(3, len(retn))

            # long value with long prefix
            self.genraises(s_exc.BadOperArg, idxr.queryNormRecords, 'second', valu='strinstrin' * 15)

            # Bad data
            waiter = self.initWaiter(tank, 'None')
            tank.puts([baddata])
            self.wait(waiter)
            idxs = idxr.getIndices()
            idx = next(i for i in idxs if i['propname'] == 'first')
            self.eq(4, idx['nextoffset'])
            self.eq(3, idx['ngood'])
            self.eq(1, idx['nnormfail'])

            waiter = self.initWaiter(tank, 'delIndex')
            idxr.delIndex('second')
            self.wait(waiter)

            # Multiple datapaths
            waiter = self.initWaiter(tank, 'delIndex')
            idxr.delIndex('first')
            self.wait(waiter)
            waiter = self.initWaiter(tank, 'addIndex')
            idxr.addIndex('first', 'int', ('foo', 'foo2'))
            self.wait(waiter)

            waiter = self.initWaiter(tank, 'None')
            tank.puts([data4])
            self.wait(waiter)
            retn = list(idxr.queryNormValu('first'))
            self.eq(retn, [(0, 1234), (1, 2345), (4, 9999), (2, 388383)])

            waiter = self.initWaiter(tank, 'pauseIndex')
            idxr.pauseIndex('first')
            self.wait(waiter)

            waiter = self.initWaiter(tank, 'resumeIndex')
            idxr.resumeIndex('first')
            self.wait(waiter)

            waiter = self.initWaiter(tank, 'getIndices')
            before_idxs = idxr.getIndices()
            before_idx = next(i for i in before_idxs if i['propname'] == 'first')
            self.wait(waiter)
            waiter = self.initWaiter(tank, 'None')
            tank.puts([data1, data2, data3, data4] * 1000)
            self.wait(waiter)
            after_idxs = idxr.getIndices()
            after_idx = next(i for i in after_idxs if i['propname'] == 'first')
            self.lt(before_idx['ngood'], after_idx['ngood'])

    def newp_cryotank_index_nest(self):
        with self.getTestDir() as dirn, s_cryotank.CryoTank(dirn, {'mapsize': s_test.TEST_MAP_SIZE}) as tank:
            idxr = tank.indexer
            item = {
                'hehe': {
                    'haha': {
                        'key': 'valu'
                    }
                }
            }
            waiter = self.initWaiter(tank, 'addIndex')
            idxr.addIndex('key', 'str:lwr', ['hehe/haha/key'])
            self.wait(waiter)
            waiter = self.initWaiter(tank, 'None')
            tank.puts([item])
            self.wait(waiter)
            idxs = idxr.getIndices()
            self.eq(idxs[0]['ngood'], 1)

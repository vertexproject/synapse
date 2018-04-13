import time
import random

import synapse.exc as s_exc
import synapse.lib.cell as s_cell
import synapse.cryotank as s_cryotank
import synapse.lib.msgpack as s_msgpack
from synapse.tests.common import *

logger = s_cryotank.logger

cryodata = (('foo', {'bar': 10}), ('baz', {'faz': 20}))

class CryoTest(SynTest):

    def test_cryo_tank(self):

        with self.getTestDir() as dirn:

            with s_cryotank.CryoTank(dirn) as tank:  # type: s_cryotank.CryoTank

                # Default configable option
                self.eq(tank.getConfOpt('mapsize'), s_const.tebibyte)

                info = tank.info()
                self.eq(0, info.get('indx'))
                self.eq(0, info.get('metrics'))

                self.nn(info.get('stat').get('entries'))

                tank.puts(cryodata)
                info = tank.info()
                self.eq(2, info.get('indx'))
                self.eq(1, info.get('metrics'))

                self.eq('baz', tank.last()[1][0])

                retn = tuple(tank.slice(0, 1))
                self.eq(retn, ((0, cryodata[0]),))

                retn = tuple(tank.rows(0, 1))  # coverage related
                self.len(1, retn)
                retn = tuple(tank.rows(0, 2))
                self.len(2, retn)
                data = retn[-1]
                self.eq(data, (1, b'\x92\xa3baz\x81\xa3faz\x14'))

                info = tank.info()
                self.eq(2, info.get('indx'))
                self.eq(1, info.get('metrics'))

                retn = tuple(tank.metrics(0, 1))[0]

                self.nn(retn[1].get('time'))
                self.eq(retn[1].get('size'), 22)
                self.eq(retn[1].get('count'), 2)

                # Slices and rows can start at offsets
                retn = tuple(tank.rows(1, 4))
                self.len(1, retn)
                retn = tuple(tank.slice(1, 4))
                self.len(1, retn)

                retn = tuple(tank.rows(4, 4))
                self.len(0, retn)
                retn = tuple(tank.slice(4, 4))
                self.len(0, retn)

                # Test empty puts
                tank.puts(tuple())
                info = tank.info()
                self.eq(2, info.get('indx'))
                self.eq(2, info.get('metrics'))

    def test_cryo_mapsize(self):
        self.skipTest('LMDB Failure modes need research')
        mapsize = s_const.mebibyte * 1
        v = s_const.kibibyte * b'''In that flickering pallor it had the effect of a large and clumsy black insect, an insect the size of an ironclad cruiser, crawling obliquely to the first line of trenches and firing shots out of portholes in its side. And on its carcass the bullets must have been battering with more than the passionate violence of hail on a roof of tin.'''

        with self.getTestDir() as dirn:
            with s_cryotank.CryoTank(dirn, {'mapsize': mapsize}) as tank:  # type: s_cryotank.CryoTank
                tank.puts([(0, {'key': v})])
                tank.puts([(1, {'key': v})])
                # Now we fail
                with self.getLoggerStream('synapse.cryotank') as stream:
                    self.none(tank.puts([(2, {'key': v})]))
                stream.seek(0)
                mesgs = stream.read()
                self.isin('Error appending items to the cryotank', mesgs)
                # We can still put a small item in though!
                self.eq(tank.puts([(2, {'key': 'tinyitem'})]))

    def test_cryo_cell(self):

        with self.getTestDir() as dirn:

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}

            with s_cryotank.CryoCell(dirn, conf) as cell:

                addr = cell.getCellAddr()
                cuser = s_cell.CellUser(cell.genUserAuth('foo'))
                with cuser.open(addr, timeout=2) as sess:
                    user = s_cryotank.CryoClient(sess)

                    # Setting the _chunksize to 1 forces iteration on the client
                    # side of puts, as well as the server-side.
                    user._chunksize = 1
                    user.puts('woot:woot', cryodata, timeout=2)

                    self.eq(user.last('woot:woot', timeout=2)[1][0], 'baz')

                    retn = user.list(timeout=3)
                    self.eq(retn[0][1]['indx'], 2)
                    self.eq(retn[0][0], 'woot:woot')

                    metr = list(user.metrics('woot:woot', 0, 100, timeout=2))

                    self.len(2, metr)
                    self.eq(metr[0][1]['count'], 1)

                    user.puts('woot:woot', cryodata, timeout=2)
                    retn = list(user.slice('woot:woot', 2, 2, timeout=3))
                    self.len(2, retn)
                    self.eq(2, retn[0][0])

                    retn = list(user.rows('woot:woot', 0, 2, timeout=3))
                    self.len(2, retn)
                    self.eq(retn[0], (0, s_msgpack.en(cryodata[0])))
                    self.eq(retn[1], (1, s_msgpack.en(cryodata[1])))

                    # Reset chunksize
                    user._chunksize = s_cryotank.CryoClient._chunksize
                    user.puts('woot:hehe', cryodata, timeout=5)
                    user.puts('woot:hehe', cryodata, timeout=5)
                    retn = list(user.slice('woot:hehe', 1, 2))
                    retn = [val for indx, val in retn[::-1]]
                    self.eq(tuple(retn), cryodata)

                    metr = list(user.metrics('woot:hehe', 0))
                    self.len(2, metr)

                    listd = dict(user.list(timeout=3))
                    self.isin('woot:hehe', listd)
                    self.eq(user.last('woot:hehe', timeout=3), (3, cryodata[1]))

                    # delete woot.hehe and then call apis on it
                    self.true(user.delete('woot:hehe'))
                    self.false(user.delete('woot:hehe'))
                    self.none(cell.tanks.get('woot:hehe'))
                    self.none(cell.names.get('woot:hehe'))

                    self.genraises(s_exc.RetnErr, user.slice, 'woot:hehe', 1, 2, timeout=3)
                    self.genraises(s_exc.RetnErr, user.rows, 'woot:hehe', 1, 2, timeout=3)

                    listd = dict(user.list(timeout=3))
                    self.notin('woot:hehe', listd)

                    self.none(user.last('woot:hehe', timeout=3))
                    self.genraises(s_exc.RetnErr, user.metrics, 'woot:hehe', 0, 100, timeout=3)

                    # Adding data re-adds the tank
                    user._chunksize = 1000
                    user.puts('woot:hehe', cryodata, timeout=5)
                    metr = list(user.metrics('woot:hehe', 0))
                    self.len(1, metr)

                    # We can initialize a new tank directly with a custom map size
                    self.true(user.init('weee:imthebest', {'mapsize': 5558675309}))
                    self.false(user.init('woot:hehe'))

                    # error when we specify an invalid config option
                    self.raises(s_exc.RetnErr, user.init, 'weee:danktank', {'newp': 'hehe'})

            # Turn it back on
            with s_cryotank.CryoCell(dirn, conf) as cell:

                addr = cell.getCellAddr()
                cuser = s_cell.CellUser(cell.genUserAuth('foo'))
                with cuser.open(addr, timeout=2) as sess:
                    user = s_cryotank.CryoClient(sess)
                    listd = dict(user.list(timeout=3))
                    self.len(3, listd)
                    self.isin('weee:imthebest', listd)
                    self.isin('woot:woot', listd)
                    self.isin('woot:hehe', listd)
                    self.istufo(user.last('woot:woot')[1])
                    self.istufo(user.last('woot:hehe')[1])
                    self.none(user.last('weee:imthebest'))

                    # Test empty puts
                    user.puts('woot:hehe', tuple())
                    listd = dict(user.list(timeout=3))
                    metr = list(user.metrics('woot:hehe', 0))
                    self.len(2, metr)
                    self.nn(user.last('woot:hehe'))

    def test_cryo_cell_daemon(self):

        with self.getTestDir() as dirn:
            celldir = os.path.join(dirn, 'cell')
            port = random.randint(10000, 50000)

            conf = {
                'cells': [
                    (celldir, {'ctor': 'synapse.cryotank.CryoCell',
                                'port': port,
                                'host': 'localhost',
                                'bind': '127.0.0.1',
                                }),
                ],
            }

        with s_daemon.Daemon() as dmon:
            dmon.loadDmonConf(conf)
            with genfile(celldir, 'cell.lock') as fd:
                self.true(checkLock(fd, 30))

            authfp = os.path.join(celldir, 'cell.auth')
            auth = s_msgpack.loadfile(authfp)

            addr = ('127.0.0.1', port)
            cuser = s_cell.CellUser(auth)
            with cuser.open(addr, timeout=2) as sess:
                user = s_cryotank.CryoClient(sess)
                retn = user.list(timeout=3)
                self.eq(retn, ())

                user.puts('woot:woot', cryodata, timeout=2)

                retn = user.list(timeout=3)
                self.eq(retn[0][1]['indx'], 2)
                self.eq(retn[0][0], 'woot:woot')

                self.eq(user.last('woot:woot', timeout=2)[1][0], 'baz')
                retn = user.list(timeout=3)
                self.eq(retn[0][1]['indx'], 2)
                self.eq(retn[0][0], 'woot:woot')

        # ensure dmon cell processes are fini'd
        for celldir, proc in dmon.cellprocs.items():
            self.false(proc.is_alive())

class CryoIndexTest(SynTest):
    def initWaiter(self, tank, count=1):
        return tank.waiter(count, 'cryotank:indexer:noworkleft')

    def wait(self, waiter):
        rv = waiter.wait(s_cryotank.CryoTankIndexer.MAX_WAIT_S)
        self.nn(rv)

    def test_cryotank_index(self):
        with self.getTestDir() as dirn, s_cryotank.CryoTank(dirn) as tank:
            idxr = tank.indexer

            waiter = self.initWaiter(tank)
            data1 = {'foo': 1234, 'bar': 'stringval'}
            data2 = {'foo': 2345, 'baz': 4567, 'bar': 'strinstrin'}
            data3 = {'foo': 388383, 'bar': ('strinstrin' * 20)}
            data4 = {'foo2': 9999, 'baz': 4567}
            baddata = {'foo': 'bad'}

            # Simple index add/remove
            self.eq([], idxr.getIndices())
            idxr.addIndex('first', 'int', 'foo')
            self.raises(DupIndx, idxr.addIndex, 'first', 'int', 'foo')
            idxs = idxr.getIndices()
            self.eq(idxs[0]['propname'], 'first')
            idxr.delIndex('first')
            self.raises(NoSuchIndx, idxr.delIndex, 'first')
            self.eq([], idxr.getIndices())

            self.genraises(NoSuchIndx, idxr.normValuByPropVal, 'notanindex')

            # Check simple 1 record, 1 index index and retrieval
            waiter = self.initWaiter(tank)
            tank.puts([data1])
            idxr.addIndex('first', 'int', 'foo')
            self.wait(waiter)
            idxs = idxr.getIndices()
            self.eq(1, idxs[0]['nextoffset'])
            self.eq(1, idxs[0]['ngood'])
            retn = list(idxr.normRecordsByPropVal('first'))
            self.eq(1, len(retn))
            t = retn[0]
            self.eq(2, len(t))
            self.eq(t[0], 0)
            self.eq(t[1], {'first': 1234})
            waiter = self.initWaiter(tank)
            self.wait(waiter)

            waiter = self.initWaiter(tank)
            tank.puts([data2])
            self.wait(waiter)
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

            waiter = self.initWaiter(tank)
            self.wait(waiter)

            # second index
            waiter = self.initWaiter(tank)
            idxr.addIndex('second', 'str', 'bar')
            self.wait(waiter)

            # prefix search
            retn = list(idxr.normValuByPropVal('second', valu='strin'))
            self.eq(retn, [(0, 'stringval'), (1, 'strinstrin')])

            # long value, exact
            waiter = self.initWaiter(tank)
            tank.puts([data3])
            self.wait(waiter)
            retn = list(idxr.rawRecordsByPropVal('second', valu='strinstrin' * 20, exact=True))
            self.eq(1, len(retn))
            self.eq(s_msgpack.un(retn[0][1]), data3)

            # long value with prefix
            retn = list(idxr.rawRecordsByPropVal('second', valu='str'))
            self.eq(3, len(retn))

            # long value with long prefix
            self.genraises(s_exc.BadOperArg, idxr.normRecordsByPropVal, 'second', valu='strinstrin' * 15)

            # Bad data
            waiter = self.initWaiter(tank)
            tank.puts([baddata])
            self.wait(waiter)
            idxs = idxr.getIndices()
            self.eq(4, idxs[0]['nextoffset'])
            self.eq(3, idxs[0]['ngood'])
            self.eq(1, idxs[0]['nnormfail'])

            waiter = self.initWaiter(tank)
            idxr.delIndex('second')
            self.wait(waiter)

            waiter = self.initWaiter(tank)
            self.wait(waiter)

            # Multiple datapaths
            idxr.delIndex('first')
            waiter = self.initWaiter(tank)
            self.wait(waiter)
            idxr.addIndex('first', 'int', 'foo', 'foo2')
            waiter = self.initWaiter(tank)
            self.wait(waiter)

            waiter = self.initWaiter(tank)
            tank.puts([data4])
            self.wait(waiter)
            retn = list(idxr.normValuByPropVal('first'))
            self.eq(retn, [(0, 1234), (1, 2345), (4, 9999), (2, 388383)])

            idxr.pauseIndex('first')
            waiter = self.initWaiter(tank)
            self.wait(waiter)

            idxr.resumeIndex('first')
            waiter = self.initWaiter(tank)
            self.wait(waiter)

            waiter = self.initWaiter(tank)
            before_idxs = idxr.getIndices()
            self.wait(waiter)
            waiter = self.initWaiter(tank)
            tank.puts([data1, data2, data3, data4] * 1000)
            self.wait(waiter)
            after_idxs = idxr.getIndices()
            self.lt(before_idxs[0]['ngood'], after_idxs[0]['ngood'])

    def test_cryotank_index_nest(self):
        with self.getTestDir() as dirn, s_cryotank.CryoTank(dirn) as tank:
            idxr = tank.indexer
            item = {
                'hehe': {
                    'haha': {
                        'key': 'valu'
                    }
                }
            }
            idxr.addIndex('key', 'str:lwr', 'hehe/haha/key')
            waiter = self.initWaiter(tank)
            self.wait(waiter)
            waiter = self.initWaiter(tank)
            tank.puts([item])
            self.wait(waiter)
            idxs = idxr.getIndices()
            self.eq(idxs[0]['ngood'], 1)

import random

import synapse.cryotank as s_cryotank

from synapse.tests.common import *

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
                    print('go boom')
                    self.none(tank.puts([(2, {'key': v})]))
                    print('no boom!')
                stream.seek(0)
                mesgs = stream.read()
                self.isin('Error appending items to the cryotank', mesgs)
                print('tiny item time!')
                # We can still put a small item in though!
                self.eq(tank.puts([(2, {'key': 'tinyitem'})]))

    def test_cryo_cell(self):

        with self.getTestDir() as dirn:

            initCellDir(dirn)
            root, auth = getCellAuth()

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}

            with s_cryotank.CryoCell(dirn, conf) as cell:

                addr = cell.getCellAddr()

                user = s_cryotank.CryoUser(auth, addr, timeout=2)

                # Setting the _chunksize to 1 forces iteration on the client
                # side of puts, as well as the server-side.
                user._chunksize = 1
                user.puts('woot:woot', cryodata, timeout=2)

                self.eq(user.last('woot:woot', timeout=2)[1][0], 'baz')

                retn = user.list()
                self.eq(retn[0][1]['indx'], 2)
                self.eq(retn[0][0], 'woot:woot')

                metr = user.metrics('woot:woot', 0, 100, timeout=2)

                self.len(2, metr)
                self.eq(metr[0][1]['count'], 1)

                user.puts('woot:woot', cryodata, timeout=2)
                retn = list(user.slice('woot:woot', 2, 2))
                self.len(2, retn)
                self.eq(2, retn[0][0])

                retn = list(user.rows('woot:woot', 0, 2))
                self.len(2, retn)
                self.eq(retn[0], (0, s_msgpack.en(cryodata[0])))
                self.eq(retn[1], (1, s_msgpack.en(cryodata[1])))

                # Reset chunksize
                user._chunksize = s_cryotank.CryoUser._chunksize
                user.puts('woot:hehe', cryodata, timeout=5)
                user.puts('woot:hehe', cryodata, timeout=5)
                retn = list(user.slice('woot:hehe', 1, 2))
                retn = [val for indx, val in retn[::-1]]
                self.eq(tuple(retn), cryodata)
                self.len(2, (user.metrics('woot:hehe', 0, 100)))
                listd = dict(user.list())
                self.isin('woot:hehe', listd)
                self.eq(user.last('woot:hehe'), (3, cryodata[1]))

                # delete woot.hehe and then call apis on it
                self.true(user.delete('woot:hehe'))
                self.false(user.delete('woot:hehe'))
                self.none(cell.tanks.get('woot:hehe'))
                self.none(cell.names.get('woot:hehe'))
                self.eq(list(user.slice('woot:hehe', 1, 2, timeout=3)), [])
                self.eq(list(user.rows('woot:hehe', 1, 2, timeout=3)), [])
                listd = dict(user.list(timeout=3))
                self.notin('woot:hehe', listd)
                self.none(user.metrics('woot:hehe', 0, 100, timeout=3))
                self.none(user.last('woot:hehe', timeout=3))

                # Adding data re-adds the tank
                user.puts('woot:hehe', cryodata, timeout=5)
                self.len(1, (user.metrics('woot:hehe', 0, 100)))

                # We can initialize a new tank directly with a custom map size
                self.true(user.init('weee:imthebest', {'mapsize': 5558675309}))
                self.false(user.init('woot:hehe'))
                with self.getLoggerStream('synapse.cryotank') as stream:
                    self.false(user.init('weee:danktank', {'newp': 'hehe'}))
                stream.seek(0)
                mesgs = stream.read()
                self.isin('Error making CryoTank', mesgs)

            # Turn it back on
            with s_cryotank.CryoCell(dirn, conf) as cell:

                addr = cell.getCellAddr()
                user = s_cryotank.CryoUser(auth, addr, timeout=2)
                listd = dict(user.list())
                self.len(3, listd)
                self.isin('weee:imthebest', listd)
                self.isin('woot:woot', listd)
                self.isin('woot:hehe', listd)
                self.istufo(user.last('woot:woot')[1])
                self.istufo(user.last('woot:hehe')[1])
                self.none(user.last('weee:imthebest'))

                # Test empty puts
                user.puts('woot:hehe', tuple())
                listd = dict(user.list())
                self.len(2, (user.metrics('woot:hehe', 0, 100)))
                self.nn(user.metrics('woot:hehe', 0, 100))
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
            user = s_cryotank.CryoUser(auth, addr, timeout=2)

            retn = user.list()
            self.eq(retn, ())

            user.puts('woot:woot', cryodata, timeout=2)

            retn = user.list()
            self.eq(retn[0][1]['indx'], 2)
            self.eq(retn[0][0], 'woot:woot')

            self.eq(user.last('woot:woot', timeout=2)[1][0], 'baz')
            retn = user.list()
            self.eq(retn[0][1]['indx'], 2)
            self.eq(retn[0][0], 'woot:woot')

        # ensure dmon cell processes are fini'd
        for celldir, proc in dmon.cellprocs.items():
            self.false(proc.is_alive())

    def test_cryo_cryouser_timeout(self):
        with self.getTestDir() as dirn:
            conf = {'bind': '127.0.0.1', 'host': 'localhost'}
            with s_cryotank.CryoCell(dirn, conf) as cell:
                addr = cell.getCellAddr()
                auth = cell.genUserAuth('visi@vertex.link')
                self.raises(CellUserErr, s_cryotank.CryoUser, auth, addr, timeout=-1)

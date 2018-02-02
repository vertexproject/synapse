import synapse.neuron as s_neuron
import synapse.cryotank as s_cryotank

from synapse.tests.common import *

cryodata = (('foo', {'bar': 10}), ('baz', {'faz': 20}))

class CryoTest(SynTest):

    def test_cryo_tank(self):

        with self.getTestDir() as dirn:

            with s_cryotank.CryoTank(dirn) as tank:

                info = tank.info()
                self.eq(0, info.get('indx'))
                self.eq(0, info.get('metrics'))

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

    def test_cryo_cell(self):

        with self.getTestDir() as dirn:

            conf = {'host': '127.0.0.1'}

            with s_cryotank.CryoCell(dirn, conf) as cell:

                port = cell.getCellPort()

                auth = cell.genUserAuth('visi@vertex.link')

                addr = ('127.0.0.1', port)

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

                # delete woot.hehe and hten call apis on it
                self.true(user.delete('woot:hehe'))
                self.false(user.delete('woot:hehe'))
                self.none(cell.tanks.get('woot:hehe'))
                self.none(cell.names.get('woot:hehe'))
                self.eq(list(user.slice('woot:hehe', 1, 2)), [])
                self.eq(list(user.rows('woot:hehe', 1, 2)), [])
                listd = dict(user.list())
                self.notin('woot:hehe', listd)
                self.none(user.metrics('woot:hehe', 0, 100))
                self.none(user.last('woot:hehe'))

                # Adding data re-adds the tank
                user.puts('woot:hehe', cryodata, timeout=5)
                self.len(1, (user.metrics('woot:hehe', 0, 100)))

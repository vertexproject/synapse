import threading

from synapse.tests.common import *

import synapse.lib.persist as s_persist

class PersistTest(SynTest):

    def test_persist_file(self):
        pers = s_persist.File()

        foo0 = ('asdf', {'hehe': 'haha'})
        foo1 = ('qwer', {'hehe': 'hoho'})

        off0, size0 = pers.add(foo0)

        self.eq(off0, 0)

        off1, size1 = pers.add(foo1)

        self.eq(off0 + size0, off1)

        pers.fini()

    def test_persist_dir(self):

        with self.getTestDir() as dirname:

            opts = {
                'filemax': 1024,
            }
            added_offsets = []

            pdir = s_persist.Dir(dirname, **opts)

            # trigger storage file alloc
            boff, sz = pdir.add(b'V' * 2000)
            added_offsets.append(boff + sz)
            boff, sz = pdir.add(b'I' * 2000)
            added_offsets.append(boff + sz)
            boff, sz = pdir.add(b'S' * 2000)
            added_offsets.append(boff + sz)

            # get all caught up and gen one real-time
            items = []

            ev0 = threading.Event()
            ev1 = threading.Event()

            def pumploop(offset):

                for i, (noff, item) in enumerate(pdir.items(offset), 1):

                    items.append((noff, item))

                    if i == 3:
                        ev0.set()

                    if i == 4:
                        ev1.set()

            thr = worker(pumploop, 0)

            ev0.wait(timeout=3)

            self.true(ev0.is_set())

            boff, sz = pdir.add(b'VISI')
            added_offsets.append(boff + sz)
            ev1.wait(timeout=3)

            self.true(ev1.is_set())

            pdir.fini()

            self.eq(items[3][1], b'VISI')
            self.eq(items[0][1], b'V' * 2000)

            thr.join(timeout=1)

            offset = items[-1][0]

            # Now, restart the pdir and continue populating the items list from the middle of a stream
            ev0.clear()
            ev1.clear()
            pdir = s_persist.Dir(dirname, **opts)

            boff, sz = pdir.add(b'1' * 1)
            added_offsets.append(boff + sz)
            boff, sz = pdir.add(b'2' * 2)
            added_offsets.append(boff + sz)
            boff, sz = pdir.add(b'3' * 3)
            added_offsets.append(boff + sz)

            thr = worker(pumploop, offset)

            ev0.wait(timeout=3)

            self.true(ev0.is_set())

            boff, sz = pdir.add(b'LULZ')
            added_offsets.append(boff + sz)

            ev1.wait(timeout=3)

            self.true(ev1.is_set())

            pdir.fini()

            self.len(8, items)
            received_offsets = [offset for offset, item in items]
            self.eq(received_offsets, added_offsets)

            thr.join(timeout=1)

    def test_persist_offset(self):

        with self.getTestDir() as dirname:

            poff = s_persist.Offset(dirname, 'test0.off')
            poff.set(200)

            self.eq(poff.get(), 200)

            poff.set(201)

            poff.fini()

            poff = s_persist.Offset(dirname, 'test0.off')
            self.eq(poff.get(), 201)

            poff.fini()

    def test_persist_pump(self):
        events = []
        iden = guid()
        wait = threading.Event()

        def pumpfunc(x):
            events.append(x)
            if len(events) >= 4:
                wait.set()

        with self.getTestDir() as dirname:

            pdir = s_persist.Dir(dirname)

            pdir.add(('foo', {}))
            pdir.add(('bar', {}))

            pdir.pump(iden, pumpfunc)

            pdir.add(('hehe', {}))
            pdir.add(('haha', {}))

            wait.wait(timeout=2)
            self.true(wait.is_set())

            pdir.fini()

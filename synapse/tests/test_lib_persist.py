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

            # Ensure that the getIdenOffset() / getOffsetIdens() apis work.
            iden = guid()
            poff = pdir.getIdenOffset(iden)
            self.isinstance(poff, s_persist.Offset)
            idens = pdir.getOffsetIdens()
            self.len(1, idens)
            self.isin(iden, idens)
            poff.fini()

            # Ensure the dirSize api works
            self.eq(pdir.dirSize(), 0)

            # trigger storage file alloc
            boff, sz = pdir.add(b'V' * 2000)
            added_offsets.append(boff + sz)
            boff, sz = pdir.add(b'I' * 2000)
            added_offsets.append(boff + sz)
            boff, sz = pdir.add(b'S' * 2000)
            added_offsets.append(boff + sz)

            # Account for msgpack encoding for bin types
            self.eq(pdir.dirSize(), 3 * (2000 + 3))

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

            # Capture the current pdir size
            esize = pdir.dirSize()
            self.gt(esize, 0)

            pdir.fini()

            self.eq(items[3][1], b'VISI')
            self.eq(items[0][1], b'V' * 2000)

            thr.join(timeout=1)

            offset = items[-1][0]

            # Now, restart the pdir and continue populating the items list from the middle of a stream
            ev0.clear()
            ev1.clear()
            pdir = s_persist.Dir(dirname, **opts)

            # Size is initialized on startup to the old valu
            self.eq(esize, pdir.dirSize())

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

    def test_persist_surrogates(self):
        with self.getTestDir() as dirname:

            opts = {
                'filemax': 1024,
            }

            pdir = s_persist.Dir(dirname, **opts)

            bads = '\u01cb\ufffd\ud842\ufffd\u0012'
            t0 = ('1234', {'key': bads})

            pdir.add(t0)

            items = []
            ev0 = threading.Event()

            def pumploop(offset):

                for i, (noff, item) in enumerate(pdir.items(offset), 1):

                    items.append(item)
                    ev0.set()

            thr = worker(pumploop, 0)
            ev0.wait(timeout=3)

            self.true(ev0.is_set())
            self.len(1, items)
            self.eq(items[0], t0)

            pdir.fini()
            thr.join(timeout=1)

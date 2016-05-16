import threading

from synapse.tests.common import *

import synapse.lib.persist as s_persist

class PersistTest(SynTest):

    def test_persist_file(self):
        pers = s_persist.File()

        foo0 = ('asdf',{'hehe':'haha'})
        foo1 = ('qwer',{'hehe':'hoho'})

        off0,size0 = pers.add(foo0)

        self.assertEqual( off0, 0 )

        off1,size1 = pers.add(foo1)

        self.assertEqual( off0 + size0, off1 )

        pers.fini()

    def test_persist_dir(self):

        with self.getTestDir() as dirname:

            opts = {
                'filemax':1024,
            }

            pdir = s_persist.Dir(dirname,**opts)

            # trigger storage file alloc
            pdir.add( b'V' * 2000 )
            pdir.add( b'I' * 2000 )
            pdir.add( b'S' * 2000 )

            # get all caught up and gen one real-time
            items = []

            ev0 = threading.Event()
            ev1 = threading.Event()

            def pumploop():

                for noff,item in pdir.items(0):

                    items.append( (noff,item) )

                    if len(items) == 3:
                        ev0.set()

                    if len(items) == 4:
                        ev1.set()

            thr = worker(pumploop)

            ev0.wait(timeout=3)

            self.assertTrue( ev0.is_set() )

            pdir.add(b'VISI')
            ev1.wait(timeout=3)

            self.assertTrue(ev1.is_set())

            pdir.fini()

            self.assertEqual( items[3][1], b'VISI' )
            self.assertEqual( items[0][1], b'V' * 2000 )

    def test_persist_offset(self):

        with self.getTestDir() as dirname:

            poff = s_persist.Offset(dirname,'test0.off')
            poff.set(200)

            self.assertEqual( poff.get(), 200 )

            poff.set(201)

            poff.fini()

            poff = s_persist.Offset(dirname,'test0.off')
            self.assertEqual( poff.get(), 201 )

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

            pdir.add( ('foo',{}) )
            pdir.add( ('bar',{}) )

            pdir.pump(iden,pumpfunc)

            pdir.add( ('hehe',{}) )
            pdir.add( ('haha',{}) )

            wait.wait(timeout=2)
            self.assertTrue( wait.is_set() )

            pdir.fini()

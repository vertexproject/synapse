import threading

import synapse.glob as s_glob
import synapse.lib.threads as s_threads

from synapse.tests.common import *

class GlobTest(SynTest):

    def test_glob_call(self):

        evnt = threading.Event()
        def woot():
            evnt.set()

        s_glob.pool.call(woot)
        self.true(evnt.wait(timeout=1))

    def test_glob_task(self):

        data = {}
        def onretn(retn):
            ok, valu = retn
            data['ok'] = ok
            data['valu'] = valu

        def woot():
            return 20

        def junk():
            raise Exception('woot')

        with s_glob.pool.task(woot) as task:
            task.onretn(onretn)

        self.true(task.waitfini(timeout=1))

        self.true(data['ok'])
        self.eq(20, data['valu'])

        with s_glob.pool.task(junk) as task:
            task.onretn(onretn)

        task.waitfini(timeout=1)
        self.false(data['ok'])

    def test_glob_insec(self):

        evnt = threading.Event()
        def woot():
            evnt.set()

        s_glob.sched.insec(0.01, woot)
        self.true(evnt.wait(timeout=1))

    def test_glob_persec(self):
        evnt = threading.Event()
        def woot():
            evnt.set()

        task = s_glob.sched.persec(100, woot)
        self.true(evnt.wait(timeout=1))

        task.fini()
        evnt.clear()

        self.false(evnt.wait(timeout=0.1))

    def test_glob_inpool(self):

        iden = s_threads.iden()

        retn = {}
        evnt = threading.Event()

        @s_glob.inpool
        def woot():
            retn['iden'] = s_threads.iden()
            evnt.set()

        woot()
        evnt.wait(timeout=1)
        self.ne(iden, retn.get('iden'))

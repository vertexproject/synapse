import threading

import synapse.glob as s_glob

import synapse.lib.threads as s_threads

import synapse.tests.utils as s_t_utils

class GlobTest(s_t_utils.SynTest):

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

    def test_glob_sync(self):

        async def afoo():
            return 42

        retn = s_glob.sync(afoo())
        self.eq(retn, 42)

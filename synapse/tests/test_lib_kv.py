import os

import synapse.lib.kv as s_kv

from synapse.tests.common import *

class KvTest(SynTest):

    def test_lib_kv_base(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')

            with s_kv.KvStor(path) as stor:
                klis = stor.getKvList('hehe')
                kdic = stor.getKvDict('haha')

                self.none(kdic.get('lol'))

                kdic.set('lol', (1, 2, 3))

                self.eq(kdic.get('lol'), (1, 2, 3))

                self.eq(0, len(klis))

                klis.append(10)
                klis.append(20)

                self.eq(2, len(klis))

            with s_kv.KvStor(path) as stor:
                klis = stor.getKvList('hehe')
                kdic = stor.getKvDict('haha')

                self.eq(2, len(klis))
                self.true(klis.remove(20))
                self.false(klis.remove(80))

                self.eq(kdic.get('lol'), (1, 2, 3))

                kdic.set('lol', (5, 6, 7))
                self.eq(kdic.get('lol'), (5, 6, 7))

            with s_kv.KvStor(path) as stor:

                klis = stor.getKvList('hehe')
                kdic = stor.getKvDict('haha')

                self.eq(1, len(klis))
                self.eq(tuple(klis), (10,))

                self.eq(kdic.get('lol'), (5, 6, 7))

    def test_lib_kv_alias(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')

            with s_kv.KvStor(path) as stor:
                iden = stor.genKvAlias('hehe')
                self.true(type(iden) is bytes)

            with s_kv.KvStor(path) as stor:
                self.eq(iden, stor.genKvAlias('hehe'))

    def test_lib_kv_look(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'test.lmdb')

            with s_kv.KvStor(path) as stor:
                look = stor.getKvLook('haha')

                self.none(look.get('lol'))

                look.set('lol', (1, 2, 3))

                self.eq(look.get('lol'), (1, 2, 3))

            with s_kv.KvStor(path) as stor:
                look = stor.getKvLook('haha')

                self.eq(look.get('lol'), (1, 2, 3))

                look.set('lol', (5, 6, 7))
                self.eq(look.get('lol'), (5, 6, 7))

            with s_kv.KvStor(path) as stor:

                look = stor.getKvLook('haha')

                self.eq(look.get('lol'), (5, 6, 7))

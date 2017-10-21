from synapse.tests.common import *

import synapse.lib.msgpack as s_msgpack

class MsgPackTest(SynTest):

    def test_msgpack_en(self):
        byts = s_msgpack.en(('hehe', 10))
        self.eq(byts, b'\x92\xa4hehe\n')

    def test_msgpack_un(self):
        item = s_msgpack.un(b'\x92\xa4hehe\n')
        self.eq(item, ('hehe', 10))

    def test_msgpack_unpk(self):
        byts = b'\x92\xa4hehe\n' * 3

        unpk = s_msgpack.Unpk()
        rets = unpk.feed(byts)

        self.eq(rets, [(7, ('hehe', 10))] * 3)

    def test_msgpack_byte(self):
        unpk = s_msgpack.Unpk()
        self.len(0, unpk.feed(b'\xa4'))
        self.len(0, unpk.feed(b'v'))
        self.len(0, unpk.feed(b'i'))
        self.len(0, unpk.feed(b's'))
        self.eq(unpk.feed(b'i')[0], (5, 'visi'))

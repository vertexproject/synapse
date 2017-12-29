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

    def test_msgpack_iterfd(self):
        t0 = ('5678', {'key': 1})
        t1 = ('1234', {'key': 'haha'})

        with self.getTestDir() as fdir:
            fd = genfile(fdir, 'test.mpk')
            for obj in (t0, t1):
                fd.write(s_msgpack.en(obj))
            fd.close()

            fd = genfile(fdir, 'test.mpk')
            gen = s_msgpack.iterfd(fd)

            items = [obj for obj in gen]
            self.len(2, items)
            self.sorteq(items, [t0, t1])

            fd.close()

    def test_msgpack_bad_types(self):
        self.raises(TypeError, s_msgpack.en, {1, 2})
        self.raises(TypeError, s_msgpack.en, Exception())
        self.raises(TypeError, s_msgpack.en, s_msgpack.en)

    def test_msgpack_surrogates(self):
        bads = '\u01cb\ufffd\ud842\ufffd\u0012'
        obyts = s_msgpack.en(bads)
        self.isinstance(obyts, bytes)

        outs = s_msgpack.un(obyts)
        self.eq(outs, bads)

        with self.getTestDir() as fdir:
            fd = genfile(fdir, 'test.mpk')
            fd.write(obyts)
            fd.close()

            fd = genfile(fdir, 'test.mpk')
            gen = s_msgpack.iterfd(fd)

            items = [obj for obj in gen]
            self.len(1, items)
            self.eq(outs, bads)

            fd.close()

        unpk = s_msgpack.Unpk()
        ret = unpk.feed(obyts)
        self.len(1, ret)
        self.eq([(13, bads)], ret)

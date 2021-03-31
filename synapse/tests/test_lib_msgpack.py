import msgpack

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.const as s_const
import synapse.lib.msgpack as s_msgpack

import synapse.tests.utils as s_t_utils

class MsgPackTest(s_t_utils.SynTest):

    def test_msgpack_en(self):
        byts = s_msgpack.en(('hehe', 10))
        self.eq(byts, b'\x92\xa4hehe\n')

        byts = s_msgpack._fallback_en(('hehe', 10))
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

    def checkIterfd(self, enfunc):
        t0 = ('5678', {'key': 1})
        t1 = ('1234', {'key': 'haha'})

        with self.getTestDir() as fdir:
            fd = s_common.genfile(fdir, 'test.mpk')
            for obj in (t0, t1):
                fd.write(enfunc(obj))
            fd.close()

            fd = s_common.genfile(fdir, 'test.mpk')
            gen = s_msgpack.iterfd(fd)

            items = [obj for obj in gen]
            self.len(2, items)
            self.sorteq(items, [t0, t1])

            fd.close()
    def test_msgpack_iterfd(self):
        self.checkIterfd(s_msgpack.en)
        self.checkIterfd(s_msgpack._fallback_en)

    def checkIterfile(self, enfunc):
        t0 = ('5678', {'key': 1})
        t1 = ('1234', {'key': 'haha'})

        with self.getTestDir() as fdir:
            fd = s_common.genfile(fdir, 'test.mpk')
            for obj in (t0, t1):
                fd.write(enfunc(obj))
            fd.close()

            gen = s_msgpack.iterfile(s_common.genpath(fdir, 'test.mpk'))

            items = [obj for obj in gen]
            self.len(2, items)
            self.sorteq(items, [t0, t1])

            fd.close()

    def test_msgpack_iterfile(self):
        self.checkIterfile(s_msgpack.en)
        self.checkIterfile(s_msgpack._fallback_en)

    def checkLoadfile(self, enfunc):
        t0 = ('5678', {'key': 1})
        t1 = ('1234', {'key': 'haha'})

        with self.getTestDir() as fdir:
            fd = s_common.genfile(fdir, 'oneobj.mpk')
            fd.write(enfunc(t0))
            fd.close()

            fd = s_common.genfile(fdir, 'twoobjs.mpk')
            for obj in (t0, t1):
                fd.write(enfunc(obj))
            fd.close()

            data = s_msgpack.loadfile(s_common.genpath(fdir, 'oneobj.mpk'))
            self.eq(data, ('5678', {'key': 1}))

            # Files containing multiple objects are not supported
            self.raises(msgpack.exceptions.ExtraData, s_msgpack.loadfile, s_common.genpath(fdir, 'twoobjs.mpk'))

    def test_msgpack_loadfile(self):
        self.checkLoadfile(s_msgpack.en)
        self.checkLoadfile(s_msgpack._fallback_en)

    def checkTypes(self, enfunc):
        # This is a future-proofing test for msgpack to ensure that
        buf = b'\x92\xa4hehe\x85\xa3str\xa41234\xa3int\xcd\x04\xd2\xa5float\xcb@(\xae\x14z\xe1G\xae\xa3bin\xc4\x041234\xa9realworld\xac\xc7\x8b\xef\xbf\xbd\xed\xa1\x82\xef\xbf\xbd\x12'
        struct = (
            'hehe',
            {
                'str': '1234',
                'int': 1234,
                'float': 12.34,
                'bin': b'1234',
                'realworld': '\u01cb\ufffd\ud842\ufffd\u0012'
            }
        )
        unode = s_msgpack.un(buf)
        self.eq(unode, struct)

        # Ensure our use of msgpack.Unpacker can also handle this data
        with self.getTestDir() as dirn:
            with s_common.genfile(dirn, 'test.mpk') as fd:
                fd.write(buf)
            with s_common.genfile(dirn, 'test.mpk') as fd:
                genr = s_msgpack.iterfd(fd)
                objs = list(genr)
                self.len(1, objs)
                self.eq(objs[0], struct)

        # Ensure that our streaming Unpk object can also handle this data
        unpk = s_msgpack.Unpk()
        objs = unpk.feed(buf)
        self.len(1, objs)
        self.eq(objs[0], (71, struct))

        # Generic isok helper
        self.true(s_msgpack.isok(1))
        self.true(s_msgpack.isok('1'))
        self.true(s_msgpack.isok(1.1))
        self.true(s_msgpack.isok(b'1'))
        self.true(s_msgpack.isok(None))
        self.true(s_msgpack.isok(True))
        self.true(s_msgpack.isok(False))
        self.true(s_msgpack.isok([1]))
        self.true(s_msgpack.isok((1,)))
        self.true(s_msgpack.isok({1: 1}))
        # unpackage types
        self.false(s_msgpack.isok({1, 2}))  # set
        self.false(s_msgpack.isok(print))  # function

        buf2 = b'\x81\xc0\xcd\x04\xd2'
        struct2 = {
            None: 1234
        }
        ustruct2 = s_msgpack.un(buf2)
        self.eq(ustruct2, struct2)
        pbuf2 = enfunc(ustruct2)
        self.eq(buf2, pbuf2)

    def test_msgpack_types(self):
        self.checkTypes(s_msgpack.en)
        self.checkTypes(s_msgpack._fallback_en)

    def checkLargeData(self, enfunc):
        big_string = s_const.mebibyte * 129 * 'V'
        struct = ('test', {'key': big_string})

        buf = enfunc(struct)

        unpacked_struct = s_msgpack.un(buf)
        self.eq(struct, unpacked_struct)

        # Ensure our use of msgpack.Unpacker can also handle this data
        with self.getTestDir() as dirn:
            with s_common.genfile(dirn, 'test.mpk') as fd:
                fd.write(buf)
            with s_common.genfile(dirn, 'test.mpk') as fd:
                genr = s_msgpack.iterfd(fd)
                objs = list(genr)
                self.len(1, objs)
                self.eq(objs[0], struct)

        # Ensure that our streaming Unpk object can also handle this data
        unpk = s_msgpack.Unpk()
        objs = unpk.feed(buf)
        self.len(1, objs)
        self.eq(objs[0], (135266320, struct))

    def test_msgpack_large_data(self):
        self.checkLargeData(s_msgpack.en)
        self.checkLargeData(s_msgpack._fallback_en)

    def checkBadTypes(self, enfunc):
        self.raises(s_exc.NotMsgpackSafe, enfunc, {1, 2})
        self.raises(s_exc.NotMsgpackSafe, enfunc, Exception())
        self.raises(s_exc.NotMsgpackSafe, enfunc, s_msgpack.en)
        # too long
        with self.raises(s_exc.NotMsgpackSafe) as cm:
            enfunc({'longlong': 45234928034723904723906})
        self.isin('OverflowError', cm.exception.get('mesg'))

    def test_msgpack_bad_types(self):
        self.checkBadTypes(s_msgpack.en)
        self.checkBadTypes(s_msgpack._fallback_en)

    def checkSurrogates(self, enfunc):
        bads = '\u01cb\ufffd\ud842\ufffd\u0012'
        obyts = enfunc(bads)
        self.isinstance(obyts, bytes)

        outs = s_msgpack.un(obyts)
        self.eq(outs, bads)

        with self.getTestDir() as fdir:
            fd = s_common.genfile(fdir, 'test.mpk')
            fd.write(obyts)
            fd.close()

            fd = s_common.genfile(fdir, 'test.mpk')
            gen = s_msgpack.iterfd(fd)

            items = [obj for obj in gen]
            self.len(1, items)
            self.eq(outs, bads)

            fd.close()

        unpk = s_msgpack.Unpk()
        ret = unpk.feed(obyts)
        self.len(1, ret)
        self.eq([(13, bads)], ret)

    def test_msgpack_surrogates(self):
        self.checkSurrogates(s_msgpack.en)
        self.checkSurrogates(s_msgpack._fallback_en)

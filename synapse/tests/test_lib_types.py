# -*- coding: UTF-8 -*-
import base64

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.types as s_types
import synapse.lib.xact as s_xact

import synapse.tests.common as s_test

class TestTypes(s_test.SynTest):

    def test_hex_type(self):

        # Bad configurations are not allowed for the type
        self.raises(s_exc.BadConfValu, s_types.Hex, None, None, None, {'size': -1})
        self.raises(s_exc.BadConfValu, s_types.Hex, None, None, None, {'size': 1})

        with self.getTestCore() as core:
            # fixme - getTestCore should have this dude loaded in him already!
            modu = core.addCoreMods([('synapse.tests.test_cortex.TestModule', {})])

            t = core.model.type('testhexa')
            # Test norming & index
            testvectors = [
                ('0C', '0c', b'\x0c'),
                ('10', '10', b'\x10'),
                ('010001', '010001', b'\x01\x00\x01'),
                ('0x010001', '010001', b'\x01\x00\x01'),
                ('0FfF', '0fff', b'\x0f\xff'),
                ('012A3e', '012a3e', b'\x01\x2a\x3e'),
                (b'\x01\x00\x01', '010001', b'\x01\x00\x01'),
                (b'\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~',
                 'd41d8cd98f00b204e9800998ecf8427e',
                 b'\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~'),
                ('C', s_exc.BadTypeValu, None),
                ('FfF', s_exc.BadTypeValu, None),
                ('10001', s_exc.BadTypeValu, None),
                ('newp', s_exc.BadTypeValu, None),
                ('0x', s_exc.BadTypeValu, None),
                ('', s_exc.BadTypeValu, None),
                (b'', s_exc.BadTypeValu, None),
                (65537, s_exc.NoSuchFunc, None),
                (0, s_exc.NoSuchFunc, None),
                (-10, s_exc.NoSuchFunc, None),
            ]

            for v, n, b in testvectors:
                if isinstance(n, str):
                    r, subs = t.norm(v)
                    self.eq(r, n)
                    self.eq(subs, {})
                    self.eq(t.indx(r), b)
                else:
                    self.raises(n, t.norm, v)

            # width = 4
            testvectors4 = [
                ('12A4', '12a4', b'\x12\xa4'),
                ('1001', '1001', b'\x10\x01'),
                ('d41d', 'd41d', b'\xd4\x1d'),
                (b'\x10\x01', '1001', b'\x10\x01'),
                (b'\x00\x00', '0000', b'\x00\x00'),
                ('01', s_exc.BadTypeValu, None),
                ('010101', s_exc.BadTypeValu, None),
                (b'\x10\x01\xff', s_exc.BadTypeValu, None),
                (b'\xff', s_exc.BadTypeValu, None),
            ]
            t = core.model.type('testhex4')
            for v, n, b in testvectors4:
                if isinstance(n, str):
                    r, subs = t.norm(v)
                    self.eq(r, n)
                    self.eq(subs, {})
                    self.eq(t.indx(r), b)
                else:
                    self.raises(n, t.norm, v)

            # Do some node creation and lifting
            # TODO - Do we have other lift operators to implement or test??
            with core.xact(write=True) as xact:  # type: s_xact.Xact
                node = xact.addNode('testhexa', '010001')
                self.eq(node.ndef[1], '010001')

            with core.xact() as xact:  # type: s_xact.Xact
                nodes = list(xact.getNodesBy('testhexa', '010001'))
                self.len(1, nodes)

                nodes = list(xact.getNodesBy('testhexa', b'\x01\x00\x01'))
                self.len(1, nodes)

            # Do some fancy prefix searches for testhexa
            valus = ['deadb33f',
                     'deadb33fb33f',
                     'deadb3b3',
                     'deaddead',
                     'DEADBEEF']
            with core.xact(write=True) as xact:  # type: s_xact.Xact
                for valu in valus:
                    node = xact.addNode('testhexa', valu)

            with core.xact() as xact:  # type: s_xact.Xact
                nodes = list(xact.getNodesBy('testhexa', 'dead*'))
                self.len(5, nodes)

                nodes = list(xact.getNodesBy('testhexa', 'deadb3*'))
                self.len(3, nodes)

                nodes = list(xact.getNodesBy('testhexa', 'deadb33fb3*'))
                self.len(1, nodes)

                nodes = list(xact.getNodesBy('testhexa', 'deadde*'))
                self.len(1, nodes)

            # Do some fancy prefix searches for testhex4
            valus = ['0000',
                     '0100',
                     '01ff',
                     '0200',
                     ]
            with core.xact(write=True) as xact:  # type: s_xact.Xact
                for valu in valus:
                    node = xact.addNode('testhex4', valu)

            with core.xact() as xact:  # type: s_xact.Xact
                nodes = list(xact.getNodesBy('testhex4', '00*'))
                self.len(1, nodes)

                nodes = list(xact.getNodesBy('testhex4', '01*'))
                self.len(2, nodes)

                nodes = list(xact.getNodesBy('testhex4', '02*'))
                self.len(1, nodes)

class FIXME(object):
    def test_datatype_basics(self):
        tlib = s_types.TypeLib()
        self.true(tlib.isDataType('inet:url'))
        self.true(isinstance(tlib.getDataType('inet:url'), s_types.DataType))

        self.none(tlib.getDataType('newp'))
        self.raises(NoSuchType, tlib.reqDataType, 'newp')

    def test_datatype_guid(self):
        tlib = s_types.TypeLib()

        self.raises(BadTypeValu, tlib.getTypeParse, 'guid', 'newp')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'guid', 'newp')

        self.eq(tlib.getTypeParse('guid', '000102030405060708090A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq(tlib.getTypeParse('guid', '00010203-0405-0607-0809-0A0B0C0D0E0F')[0],
                '000102030405060708090a0b0c0d0e0f')
        self.eq(tlib.getTypeNorm('guid', '000102030405060708090A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq(tlib.getTypeRepr('guid', '000102030405060708090a0b0c0d0e0f'), '000102030405060708090a0b0c0d0e0f')

    def test_datatype_guid_sub(self):
        tlib = s_types.TypeLib()

        tlib.addType('woot', subof='guid')

        self.raises(BadTypeValu, tlib.getTypeParse, 'woot', 'newp')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'woot', 'newp')

        self.eq(tlib.getTypeParse('woot', '000102030405060708090A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq(tlib.getTypeNorm('woot', '000102030405060708090A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq(tlib.getTypeRepr('guid', '000102030405060708090a0b0c0d0e0f'), '000102030405060708090a0b0c0d0e0f')

    def test_datatype_hash_md5(self):
        tlib = s_types.TypeLib()

        self.raises(BadTypeValu, tlib.getTypeParse, 'hash:md5', 'newp')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'hash:md5', 'newp')

        self.eq(tlib.getTypeParse('hash:md5', '000102030405060708090A0B0C0D0E0F')[0],
                '000102030405060708090a0b0c0d0e0f')
        self.eq(tlib.getTypeNorm('hash:md5', '000102030405060708090A0B0C0D0E0F')[0], '000102030405060708090a0b0c0d0e0f')
        self.eq(tlib.getTypeRepr('hash:md5', '000102030405060708090a0b0c0d0e0f'), '000102030405060708090a0b0c0d0e0f')

    def test_datatype_str(self):
        tlib = s_types.TypeLib()

        self.raises(BadTypeValu, tlib.getTypeNorm, 'str', 10)

        self.eq(tlib.getTypeNorm('str', 'foo')[0], 'foo')
        self.eq(tlib.getTypeParse('str', 'bar')[0], 'bar')

    def test_datatype_str_enums(self):
        tlib = s_types.TypeLib()

        tlib.addType('woot', subof='str', enums='hehe,haha,hoho', lower=1)

        self.raises(BadTypeValu, tlib.getTypeNorm, 'woot', 'asdf')
        self.raises(BadTypeValu, tlib.getTypeParse, 'woot', 'asdf')

        self.eq(tlib.getTypeNorm('woot', 'HeHe')[0], 'hehe')
        self.eq(tlib.getTypeParse('woot', 'HeHe')[0], 'hehe')

    def test_datatype_str_hex(self):
        tlib = s_types.TypeLib()

        # self.raises(BadTypeValu, tlib.getTypeNorm, 'str:hex', 0xFFF)
        self.raises(BadTypeValu, tlib.getTypeNorm, 'str:hex', '0xFFF')
        self.eq(tlib.getTypeNorm('str:hex', 'FfF')[0], 'fff')
        self.eq(tlib.getTypeNorm('str:hex', '12345')[0], '12345')
        self.eq(tlib.getTypeNorm('str:hex', '12A45')[0], '12a45')

        self.raises(BadTypeValu, tlib.getTypeParse, 'str:hex', '0xFFF')
        self.eq(tlib.getTypeParse('str:hex', '10001')[0], '10001')
        self.eq(tlib.getTypeParse('str:hex', 'FFF')[0], 'fff')

        tlib.addType('woot', subof='sepr', sep='/', fields='a,str:hex|b,str:hex')
        self.eq(tlib.getTypeNorm('woot', 'AAA/BBB')[0], 'aaa/bbb')
        self.eq(tlib.getTypeNorm('woot', '123456/BBB')[0], '123456/bbb')  # already str
        self.eq(tlib.getTypeNorm('woot', (123456, 'BBB'))[0], '1e240/bbb')
        self.raises(BadTypeValu, tlib.getTypeParse, 'woot', '123x/aaaa')
        self.raises(BadTypeValu, tlib.getTypeParse, 'woot', '0x123/aaaa')

    def test_datatype_dup(self):
        tlib = s_types.TypeLib()

        self.raises(DupTypeName, tlib.addType, 'inet:port', subof='int')

    def test_datatype_bool(self):
        tlib = s_types.TypeLib()

        self.raises(BadTypeValu, tlib.getTypeParse, 'bool', 'bogus')

        self.true(tlib.getTypeParse('bool', '1')[0])
        self.true(tlib.getTypeParse('bool', 't')[0])
        self.true(tlib.getTypeParse('bool', 'y')[0])
        self.true(tlib.getTypeParse('bool', 'TrUe')[0])
        self.true(tlib.getTypeParse('bool', 'yEs')[0])
        self.true(tlib.getTypeParse('bool', 'ON')[0])

        self.false(tlib.getTypeParse('bool', '0')[0])
        self.false(tlib.getTypeParse('bool', 'f')[0])
        self.false(tlib.getTypeParse('bool', 'n')[0])
        self.false(tlib.getTypeParse('bool', 'FaLsE')[0])
        self.false(tlib.getTypeParse('bool', 'nO')[0])
        self.false(tlib.getTypeParse('bool', 'OFF')[0])

        self.eq(tlib.getTypeRepr('bool', 1), 'True')
        self.eq(tlib.getTypeRepr('bool', 0), 'False')

        self.eq(tlib.getTypeNorm('bool', 9)[0], 1)
        self.eq(tlib.getTypeNorm('bool', 0)[0], 0)

        self.eq(tlib.getTypeNorm('bool', 9)[0], 1)
        self.false(tlib.getTypeNorm('bool', 'f')[0])
        self.false(tlib.getTypeNorm('bool', 'n')[0])
        self.false(tlib.getTypeNorm('bool', 'FaLsE')[0])

    def test_type_comp(self):
        tlib = s_types.TypeLib()
        tlib.addType('foo:bar', subof='comp', fields='hehe=inet:fqdn,haha=inet:ipv4', optfields="time=time")

        valu, subs = tlib.getTypeNorm('foo:bar', ('WOOT.COM', 0x01020304))
        self.eq(valu, '47e2e1c0f894266153f836a75440f803')
        self.eq(subs.get('hehe'), 'woot.com')
        self.eq(subs.get('haha'), 0x01020304)
        self.none(subs.get('time'))

        valu1, subs = tlib.getTypeNorm('foo:bar', ('WOOT.COM', 0x01020304, ('time', '20170101')))
        self.eq(valu1, 'f34a0c6ed2d91772b4790f4da1d2c0d6')
        self.eq(subs.get('hehe'), 'woot.com')
        self.eq(subs.get('haha'), 0x01020304)
        self.eq(subs.get('time'), 1483228800000)

        val2, sub2 = tlib.getTypeNorm('foo:bar', {'hehe': 'WOOT.COM', 'haha': 0x01020304})
        self.eq(valu, val2)
        self.raises(BadTypeValu, tlib.getTypeNorm, 'foo:bar', {})

        val3, sub3 = tlib.getTypeNorm('foo:bar', {'hehe': 'WOOT.COM', 'haha': 0x01020304, 'time': '20170101'})
        self.eq(valu1, val3)
        self.eq(subs, sub3)

        self.raises(BadTypeValu, tlib.getTypeNorm, 'foo:bar', set([1, 2]))

    def test_datatype_int(self):
        tlib = s_types.TypeLib()
        self.eq(tlib.getTypeNorm('int', 1), (1, {}))
        self.eq(tlib.getTypeNorm('int', -1), (-1, {}))
        self.eq(tlib.getTypeNorm('int', 0), (0, {}))
        self.eq(tlib.getTypeNorm('int', '1'), (1, {}))
        self.eq(tlib.getTypeNorm('int', '0x01'), (1, {}))

        self.eq(tlib.getTypeNorm('int', '-1'), (-1, {}))
        self.eq(tlib.getTypeNorm('int', '0'), (0, {}))
        # Bound checking
        self.eq(tlib.getTypeNorm('int', -9223372036854775808), (-9223372036854775808, {}))
        self.eq(tlib.getTypeNorm('int', 9223372036854775807), (9223372036854775807, {}))

        self.raises(BadTypeValu, tlib.getTypeNorm, 'int', 'hehe')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'int', 'one')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'int', 'one')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'int', 1.0)
        self.raises(BadTypeValu, tlib.getTypeNorm, 'int', '1.0')

        self.raises(BadTypeValu, tlib.getTypeNorm, 'int', {})
        self.raises(BadTypeValu, tlib.getTypeNorm, 'int', [])
        self.raises(BadTypeValu, tlib.getTypeNorm, 'int', -9223372036854775809)
        self.raises(BadTypeValu, tlib.getTypeNorm, 'int', 9223372036854775808)

    def test_datatype_int_minmax(self):
        tlib = s_types.TypeLib()

        tlib.addType('woot:min', subof='int', ismin=1)
        tlib.addType('woot:max', subof='int', ismax=1)

        self.eq(tlib.getTypeNorm('woot:min', 20, oldval=40)[0], 20)
        self.eq(tlib.getTypeNorm('woot:min', 40, oldval=20)[0], 20)

        self.eq(tlib.getTypeNorm('woot:max', 20, oldval=40)[0], 40)
        self.eq(tlib.getTypeNorm('woot:max', 40, oldval=20)[0], 40)

    def test_datatype_int_repr(self):
        tlib = s_types.TypeLib()

        self.eq(tlib.getTypeRepr('int', -1), '-1')
        self.eq(tlib.getTypeRepr('int', 1), '1')

        tlib.addType('woot:min', subof='int', ismin=1)
        self.eq(tlib.getTypeRepr('woot:min', 1), '1')

    def test_datatype_fqdn(self):
        tlib = s_types.TypeLib()

        self.eq(tlib.getTypeNorm('inet:fqdn', 'WOOT.COM')[0], 'woot.com')
        self.eq(tlib.getTypeNorm('inet:fqdn', 'WO-OT.COM')[0], 'wo-ot.com')
        self.eq(tlib.getTypeParse('inet:fqdn', 'WOOT.COM')[0], 'woot.com')
        self.eq(tlib.getTypeParse('inet:fqdn', 'WO-OT.COM')[0], 'wo-ot.com')

    #def test_type_stor_info(self):
        #tlib = s_types.TypeLib()
        #self.raises( BadStorValu, tlib.addType, 'fake:newp', subof='comp',fields=() )

    def test_type_pend(self):
        tlib = s_types.TypeLib()
        self.false(tlib.addType('foo', subof='bar'))
        self.true(tlib.addType('bar', subof='int'))
        self.nn(tlib.getDataType('foo'))

    def test_type_gettdef(self):
        tlib = s_types.TypeLib()

        tnfo = tlib.getTypeDef('int')
        self.nn(tnfo)
        self.eq(tnfo[0], 'int')
        self.notin('subof', tnfo[1])
        self.eq(tnfo[1].get('ctor'), 'synapse.lib.types.IntType')

        tnfo = tlib.getTypeDef('str:txt')
        self.notin('ctor', tnfo[1])
        self.eq(tnfo[1].get('subof'), 'str')

        self.none(tlib.getTypeDef('paperboat'))

    def test_type_sepr(self):
        tlib = s_types.TypeLib()
        tlib.addType('siteuser', subof='sepr', sep='/', fields='foo,inet:fqdn|bar,inet:user')
        self.eq(tlib.getTypeNorm('siteuser', 'WOOT.COM/visi')[0], 'woot.com/visi')
        self.eq(tlib.getTypeParse('siteuser', 'WOOT.COM/visi')[0], 'woot.com/visi')

        norm, subs = tlib.getTypeNorm('siteuser', 'WOOT.COM/Visi')
        self.eq(subs.get('foo'), 'woot.com')
        self.eq(subs.get('bar'), 'visi')

    def test_type_sepr_reverse(self):
        tlib = s_types.TypeLib()

        tlib.addType('foo', subof='sepr', sep='/', fields='first,str:lwr|rest,str:lwr', reverse=1)
        foo = tlib.getTypeNorm('foo', '/home/user/Downloads')
        self.eq(foo[1].get('first'), '/home/user')
        self.eq(foo[1].get('rest'), 'downloads')

    def test_type_sepr_parse(self):
        tlib = s_types.TypeLib()
        tlib.addType('woot', subof='sepr', sep='/', fields='a,str:hex|b,str:hex')
        self.eq(tlib.getTypeParse('woot', '12345/67890')[0], '12345/67890')

    def test_type_str_nullval(self):
        tlib = s_types.TypeLib()
        tlib.addType('woot', subof='str', regex='^[0-9]+$', nullval='??')
        self.eq(tlib.getTypeNorm('woot', '10')[0], '10')
        self.eq(tlib.getTypeParse('woot', '10')[0], '10')

        self.eq(tlib.getTypeNorm('woot', '??')[0], '??')
        self.eq(tlib.getTypeParse('woot', '??')[0], '??')

        self.raises(BadTypeValu, tlib.getTypeNorm, 'woot', 'qwer')
        self.raises(BadTypeValu, tlib.getTypeParse, 'woot', 'qwer')

    def test_type_bases(self):
        with self.getRamCore() as core:
            self.eq(tuple(core.getTypeBases('inet:dns:look')), ('guid', 'inet:dns:look'))

    def test_type_issub(self):
        with self.getRamCore() as core:
            self.true(core.isSubType('inet:dns:look', 'guid'))
            self.false(core.isSubType('inet:dns:look', 'int'))
            self.true(core.isSubType('str', 'str'))

    def test_type_getTypeInfo(self):
        with self.getRamCore() as core:
            core.addType('foo:bar', subof='inet:ipv4')
            self.nn(core.getTypeInfo('foo:bar', 'ex'))

    def test_type_json(self):
        tlib = s_types.TypeLib()
        self.eq(tlib.getTypeNorm('json', '{  "woot"       :10}')[0], '{"woot":10}')
        self.eq(tlib.getTypeNorm('json', {'woot': 10})[0], '{"woot":10}')
        self.eq(tlib.getTypeNorm('json', {'hehe': 1, 'foo': 'bar'}), ('{"foo":"bar","hehe":1}', {}))
        self.eq(tlib.getTypeParse('json', '{"woot":10}')[0], '{"woot":10}')

        self.raises(BadTypeValu, tlib.getTypeNorm, 'json', {'hehe', 'haha'})
        self.raises(BadTypeValu, tlib.getTypeNorm, 'json', 'Wow"wow')

    def test_type_time_timeepoch(self):
        tlib = s_types.TypeLib()
        SECOND_MS = 1000
        MINUTE_SEC = 60
        MINUTE_MS = MINUTE_SEC * 1000
        HOUR_SEC = MINUTE_SEC * 60
        HOUR_MS = HOUR_SEC * 1000
        DAY_SEC = HOUR_SEC * 24
        DAY_MS = DAY_SEC * 1000
        EPOCH_FEB_SEC = 2678400
        EPOCH_FEB_MS = 2678400000

        self.eq(tlib.getTypeParse('time', '1970')[0], 0)
        self.eq(tlib.getTypeParse('time:epoch', '1970')[0], 0)
        self.eq(tlib.getTypeParse('time', '1970 02')[0], EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time:epoch', '1970 02')[0], EPOCH_FEB_SEC)
        self.eq(tlib.getTypeParse('time', '1970 0201')[0], EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time:epoch', '1970 0201')[0], EPOCH_FEB_SEC)
        self.eq(tlib.getTypeParse('time', '1970 0202')[0], EPOCH_FEB_MS + DAY_MS)
        self.eq(tlib.getTypeParse('time:epoch', '1970 0202')[0], EPOCH_FEB_SEC + DAY_SEC)
        self.eq(tlib.getTypeParse('time', '1970 0201 00')[0], EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time:epoch', '1970 0201 00')[0], EPOCH_FEB_SEC)
        self.eq(tlib.getTypeParse('time', '1970 0201 01')[0], EPOCH_FEB_MS + HOUR_MS)
        self.eq(tlib.getTypeParse('time:epoch', '1970 0201 01')[0], EPOCH_FEB_SEC + HOUR_SEC)
        self.eq(tlib.getTypeParse('time', '1970 0201 0000')[0], EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time:epoch', '1970 0201 0000')[0], EPOCH_FEB_SEC)
        self.eq(tlib.getTypeParse('time', '1970 0201 0001')[0], EPOCH_FEB_MS + MINUTE_MS)
        self.eq(tlib.getTypeParse('time:epoch', '1970 0201 0001')[0], EPOCH_FEB_SEC + MINUTE_SEC)
        self.eq(tlib.getTypeParse('time', '1970 0201 000000')[0], EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time:epoch', '1970 0201 000000')[0], EPOCH_FEB_SEC)
        self.eq(tlib.getTypeParse('time', '1970 0201 000001')[0], EPOCH_FEB_MS + SECOND_MS)
        self.eq(tlib.getTypeParse('time:epoch', '1970 0201 000001')[0], EPOCH_FEB_SEC + 1)

        # self.raises(BadTypeValu, tlib.getTypeParse, 'time', 0)
        self.raises(BadTypeValu, tlib.getTypeParse, 'time', '19700')
        self.eq(tlib.getTypeParse('time', '1970 0201 000000 0')[0], EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time', '1970 0201 000000 1')[0], EPOCH_FEB_MS + 100)
        self.eq(tlib.getTypeParse('time', '1970 0201 000000 00')[0], EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time', '1970 0201 000000 12')[0], EPOCH_FEB_MS + 120)
        self.eq(tlib.getTypeParse('time', '1970 0201 000000 000')[0], EPOCH_FEB_MS)
        self.eq(tlib.getTypeParse('time', '1970 0201 000000 123')[0], EPOCH_FEB_MS + 123)
        self.eq(tlib.getTypeParse('time', '1970-01-01 00:00:00.010')[0], 10)
        self.eq(tlib.getTypeParse('time', '1q9w7e0r0t1y0u1i0o0p0a0s0d0f0g0h0j')[0], 0)

        # self.raises(BadTypeValu, tlib.getTypeParse, 'time:epoch', 0)braeking
        self.raises(BadTypeValu, tlib.getTypeParse, 'time:epoch', '19700')
        self.raises(BadTypeValu, tlib.getTypeParse, 'time:epoch', '1970 0201 000000 0')
        self.raises(BadTypeValu, tlib.getTypeParse, 'time:epoch', '1970 0201 000000 1')
        self.raises(BadTypeValu, tlib.getTypeParse, 'time:epoch', '1970 0201 000000 00')
        self.raises(BadTypeValu, tlib.getTypeParse, 'time:epoch', '1970 0201 000000 12')
        self.raises(BadTypeValu, tlib.getTypeParse, 'time:epoch', '1970 0201 000000 000')
        self.raises(BadTypeValu, tlib.getTypeParse, 'time:epoch', '1970 0201 000000 123')
        self.raises(BadTypeValu, tlib.getTypeParse, 'time:epoch', '1970-01-01 00:00:00.010')
        self.raises(BadTypeValu, tlib.getTypeParse, 'time:epoch', '1q9w7e0r0t1y0u1i0o0p0a0s0d0f0g0h1j')

        self.eq(tlib.getTypeParse('time', '1970')[0],
                tlib.getTypeParse('time:epoch', '1970')[0] * 1000)  # time should = epoch*1000
        self.eq(tlib.getTypeParse('time', '19700101 123456')[0],
                tlib.getTypeParse('time:epoch', '19700101 123456')[0] * 1000)  # time should = epoch*1000

        self.eq(tlib.getTypeRepr('time', -1), '1969/12/31 23:59:59.999')
        self.eq(tlib.getTypeRepr('time:epoch', -1), '1969/12/31 23:59:59')
        self.eq(tlib.getTypeRepr('time', 0), '1970/01/01 00:00:00.000')
        self.eq(tlib.getTypeRepr('time:epoch', 0), '1970/01/01 00:00:00')
        self.eq(tlib.getTypeRepr('time', 1), '1970/01/01 00:00:00.001')
        self.eq(tlib.getTypeRepr('time:epoch', 1), '1970/01/01 00:00:01')

        self.eq(tlib.getTypeNorm('time', -1)[0], -1)
        self.eq(tlib.getTypeNorm('time:epoch', -1)[0], -1)
        self.eq(tlib.getTypeNorm('time', 0)[0], 0)
        self.eq(tlib.getTypeNorm('time:epoch', 0)[0], 0)
        self.eq(tlib.getTypeNorm('time', 1)[0], 1)
        self.eq(tlib.getTypeNorm('time:epoch', 1)[0], 1)
        self.raises(BadTypeValu, tlib.getTypeNorm, 'time', '0')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'time:epoch', '0')

        self.eq(tlib.getTypeNorm('time', '1969/12/31 23:59:59.999')[0], -1)
        self.eq(tlib.getTypeNorm('time:epoch', '1969/12/31 23:59:59')[0], -1)
        self.eq(tlib.getTypeNorm('time', '1970/01/01 00:00:00.000')[0], 0)
        self.eq(tlib.getTypeNorm('time:epoch', '1970/01/01 00:00:00')[0], 0)
        self.eq(tlib.getTypeNorm('time', '1970/01/01 00:00:00.001')[0], 1)
        self.eq(tlib.getTypeNorm('time:epoch', '1970/01/01 00:00:01')[0], 1)
        self.eq(tlib.getTypeNorm('time', -1)[0], -1)
        self.eq(tlib.getTypeNorm('time:epoch', -1)[0], -1)
        self.eq(tlib.getTypeNorm('time', 0)[0], 0)
        self.eq(tlib.getTypeNorm('time:epoch', 0)[0], 0)
        self.eq(tlib.getTypeNorm('time', 1)[0], 1)
        self.eq(tlib.getTypeNorm('time:epoch', 1)[0], 1)

        # Test "now" as a current time value
        currenttime = now()
        valu = tlib.getTypeNorm('time', 'now')[0]
        # Allow for a potential context switch / system load during test
        #  to push the valu within 1000 milliseconds past currenttime
        self.le(valu - currenttime, 1000)

    def test_type_cast(self):
        tlib = s_types.TypeLib()

        def cast(x):
            return x.upper()

        tlib.addTypeCast("toupper", cast)

        self.eq(tlib.getTypeCast('str:lwr', '  HeHe  '), 'hehe')
        self.eq(tlib.getTypeCast('toupper', 'HeHe'), 'HEHE')
        self.eq(tlib.getTypeCast('make:guid', 'visi'), '98db59098e385f0bfdec8a6a0a6118b3')

    def test_type_str_strip(self):
        tlib = s_types.TypeLib()
        self.eq(tlib.getTypeCast('str:lwr', ' ASDF  '), 'asdf')

    def test_type_xref(self):
        with self.getRamCore() as core:

            core.addType('foo:bar', subof='xref', source='org,ou:org')
            core.addTufoForm('foo:bar', ptype='foo:bar')
            core.addTufoProp('foo:bar', 'org', ptype='ou:org')
            core.addTufoProp('foo:bar', 'xref', ptype='propvalu')
            core.addTufoProp('foo:bar', 'xref:intval', ptype='int')
            core.addTufoProp('foo:bar', 'xref:strval', ptype='str')
            core.addTufoProp('foo:bar', 'xref:prop', ptype='str')

            valu, subs = core.getTypeNorm('foo:bar', ('98db59098e385f0bfdec8a6a0a6118b3', 'inet:fqdn=woot.com'))
            self.eq(subs.get('org'), '98db59098e385f0bfdec8a6a0a6118b3')
            self.eq(subs.get('xref:prop'), 'inet:fqdn')
            self.eq(subs.get('xref'), 'inet:fqdn=woot.com')
            self.eq(subs.get('xref:strval'), 'woot.com')
            self.eq(subs.get('xref:intval'), None)

            valu, subs = core.getTypeNorm('foo:bar', '(98db59098e385f0bfdec8a6a0a6118b3,inet:fqdn=wOOT.com)')
            self.eq(subs.get('org'), '98db59098e385f0bfdec8a6a0a6118b3')
            self.eq(subs.get('xref:prop'), 'inet:fqdn')
            self.eq(subs.get('xref'), 'inet:fqdn=woot.com')
            self.eq(subs.get('xref:strval'), 'woot.com')
            self.eq(subs.get('xref:intval'), None)

            valu, subs = core.getTypeNorm('foo:bar', '(98db59098e385f0bfdec8a6a0a6118b3,inet:ipv4=1.2.3.4)')
            self.eq(subs.get('org'), '98db59098e385f0bfdec8a6a0a6118b3')
            self.eq(subs.get('xref:prop'), 'inet:ipv4')
            self.eq(subs.get('xref'), 'inet:ipv4=1.2.3.4')
            self.eq(subs.get('xref:strval'), None)
            self.eq(subs.get('xref:intval'), 0x01020304)

            valu, subs = core.getTypeNorm('foo:bar', '(98db59098e385f0bfdec8a6a0a6118b3,"inet:passwd=oh=my=graph!")')
            self.eq(subs.get('xref'), 'inet:passwd=oh=my=graph!')
            self.eq(subs.get('xref:strval'), 'oh=my=graph!')
            self.eq(subs.get('xref:intval'), None)

            # Do some node creation via Storm syntax
            nodes = core.eval('addnode(foo:bar, "(98db59098e385f0bfdec8a6a0a6118b3,inet:fqdn=wOOT.com)")')
            self.len(1, nodes)

            nodes = core.eval('addnode(foo:bar, (98db59098e385f0bfdec8a6a0a6118b3,"inet:passwd=oh=my=graph!"))')
            self.len(1, nodes)

            nodes = core.eval('addnode(foo:bar, (98db59098e385f0bfdec8a6a0a6118b3,inet:ipv4=1.2.3.4))')
            self.len(1, nodes)

            nodes = core.eval('[foo:bar=(98db59098e385f0bfdec8a6a0a6118b3,inet:fqdn=acme.com)]')
            self.len(1, nodes)

            nodes = core.eval('[foo:bar=(98db59098e385f0bfdec8a6a0a6118b3,"inet:passwd=oh=my=gosh!")]')
            self.len(1, nodes)

            nodes = core.eval('[foo:bar=(98db59098e385f0bfdec8a6a0a6118b3,inet:ipv4=1.2.3.5)]')
            self.len(1, nodes)

            valu, subs = core.getTypeNorm('foo:bar', 4 * 'deadb33f')
            self.eq(valu, 4 * 'deadb33f')
            self.eq(subs, {})

            # The old XREF syntax no longer works
            self.raises(BadSyntaxError, core.getTypeNorm, 'foo:bar',
                        '98db59098e385f0bfdec8a6a0a6118b3|inet:fqdn|wOOT.com')
            self.raises(NoSuchType, core.getTypeNorm, 'foo:bar',
                        ('98db59098e385f0bfdec8a6a0a6118b3', 'inet:fqdn:zone=0'))
            self.raises(BadTypeValu, core.getTypeNorm, 'foo:bar', 1)
            self.raises(BadTypeValu, core.getTypeNorm, 'foo:bar', ['oh', 'my', 'its', 'broked'])
            self.raises(BadInfoValu, core.addType, 'foo:baz', subof='xref', source='ou=org')

    def test_types_guid(self):
        with self.getRamCore() as core:

            # Random guids from "*"
            v0, _ = core.getPropNorm('guidform', '*')
            v1, _ = core.getPropNorm('guidform', '*')
            self.true(s_common.isguid(v0))
            self.true(s_common.isguid(v1))
            self.ne(v0, v1)

            # Stable guids from strings
            v0, subs0 = core.getPropNorm('guidform', '(foo="1",baz=2)')
            v1, subs1 = core.getPropNorm('guidform', (['baz', '2'], ('foo', '1')))
            v2, _ = core.getPropNorm('guidform', '  (foo="1",baz=2) ')
            v3, _ = core.getPropNorm('guidform', {'foo': '1', 'baz': 2})

            self.eq(v0, '1312b101a21bdfd0d96f896ecc5cc113')
            self.eq(v0, v1)
            self.eq(v0, v2)
            self.eq(v0, v3)

            self.len(2, subs0)
            self.eq(subs0.get('foo'), '1')
            self.eq(subs0.get('baz'), 2)
            self.eq(subs0, subs1)
            # Do partial subs
            v3, subs3 = core.getPropNorm('guidform', '(foo="1")')
            v4, _ = core.getPropNorm('guidform', [['foo', '1']])
            self.eq(v3, '9d13c5c5f307199cfd9861584bac35f2')
            self.eq(v3, v4)
            self.eq(subs0.get('foo'), subs3.get('foo'))
            self.none(subs3.get('baz'))

            # Test a model form with nested subs from a guid type
            v5, subs5 = core.getPropNorm('inet:dns:look', '(time="20171002",a="woot.com/1.2.3.4")')
            self.eq(v5, '78241202d9af8b1403e9e391336922a1')
            self.eq(subs5.get('a'), 'woot.com/1.2.3.4')
            self.eq(subs5.get('a:fqdn'), 'woot.com')
            self.eq(subs5.get('a:fqdn:domain'), 'com')
            self.eq(subs5.get('a:fqdn:host'), 'woot')
            self.eq(subs5.get('a:ipv4'), 0x01020304)
            self.eq(subs5.get('time'), 1506902400000)

            # Add a custom form which is a subtype of guid itself without a separate form
            # which has subs which also include a guid!
            core.addTufoForm('bobboblaw', ptype='guid')
            core.addTufoProp('bobboblaw', 'foo', ptype='str')
            core.addTufoProp('bobboblaw', 'baz', ptype='int')
            core.addTufoProp('bobboblaw', 'ohmai', ptype='guid')
            core.addTufoProp('bobboblaw', 'ohmai:s', ptype='str')
            core.addTufoProp('bobboblaw', 'ohmai:i', ptype='int')
            v6, subs6 = core.getPropNorm('bobboblaw', '(foo="1",baz=2)')
            self.eq(v0, v6)
            self.eq(subs0, subs6)

            # And now with nested subs!
            v7, subs7 = core.getPropNorm('bobboblaw', '(foo="1",baz=2,ohmai=(s=foo, i=137))')
            self.ne(v0, v7)
            self.eq(v7, '706f471a707370fdb8fc3d0590b4dce1')
            self.isin('foo', subs7)
            self.isin('baz', subs7)
            self.isin('ohmai', subs7)
            self.isin('ohmai:s', subs7)
            self.isin('ohmai:i', subs7)
            self.eq(subs7.get('ohmai'), '59cbcbc1b5593d719aeae1e75d05cabf')

            # Bad input
            self.raises(BadTypeValu, core.getPropNorm, 'guidform', '   ')
            self.raises(BadTypeValu, core.getPropNorm, 'guidform', '()')
            self.raises(BadTypeValu, core.getPropNorm, 'guidform', [])
            self.raises(BadTypeValu, core.getPropNorm, 'guidform', '(foo, bar)')
            self.raises(BadTypeValu, core.getPropNorm, 'guidform', (['baz', '2'], ('foo', '1', 'blerp')))
            self.raises(BadTypeValu, core.getPropNorm, 'guidform', '(foo="1",junkProp=2)')
            self.raises(BadTypeValu, core.getPropNorm, 'guidform', '(foo="1",somevalu)')
            self.raises(BadTypeValu, core.getPropNorm, 'guidform', 'totally not a guid')
            self.raises(BadTypeValu, core.getPropNorm, 'guidform', 1234)
            self.raises(BadTypeValu, core.getPropNorm, 'guidform', '$1234')
            self.raises(BadTypeValu, core.getTypeNorm, 'guid', '(foo=1)')

    def test_types_guid_resolver(self):
        with self.getRamCore() as core:
            # use the seed constructor for an org
            onode = core.formTufoByProp('ou:org:alias', 'vertex')

            iden = onode[1].get('ou:org')

            self.raises(BadTypeValu, core.formTufoByProp, 'ou:user', '$newp/visi')

            unode = core.formTufoByProp('ou:user', '$vertex/visi')

            self.eq(unode[1].get('ou:user'), '%s/visi' % iden)
            self.eq(unode[1].get('ou:user:org'), iden)

            self.len(1, core.eval('ou:org=$vertex'))
            self.len(1, core.eval('ou:user:org=$vertex'))

    def test_types_tagtime(self):
        with self.getRamCore() as core:
            valu, subs = core.getTypeNorm('syn:tag', 'Foo.Bar@20161217-20171217')

            self.eq(valu, 'foo.bar')
            self.eq(subs['seen:min'], 1481932800000)
            self.eq(subs['seen:max'], 1513468800000)

    def test_types_comp_optfields(self):
        tlib = s_types.TypeLib()

        tlib.addType('foo:bar', subof='comp', fields='foo=str,bar=int', optfields='baz=str,faz=int')

        subs = (('bar', 20), ('baz', 'asdf'), ('faz', 30), ('foo', 'qwer'))

        v0, s0 = tlib.getTypeNorm('foo:bar', ('qwer', 20, ('baz', 'asdf'), ('faz', 30)))
        v1, s1 = tlib.getTypeNorm('foo:bar', ('qwer', 20, ('faz', 30), ('baz', 'asdf')))
        v2, s2 = tlib.getTypeNorm('foo:bar', '(qwer,20,baz=asdf,faz=30)')
        v3, s3 = tlib.getTypeNorm('foo:bar', '(qwer,20,faz=30,baz=asdf)')

        self.eq(v0, v1)
        self.eq(v1, v2)
        self.eq(v2, v3)

        self.eq(subs, tuple(sorted(s0.items())))
        self.eq(subs, tuple(sorted(s1.items())))
        self.eq(subs, tuple(sorted(s2.items())))
        self.eq(subs, tuple(sorted(s3.items())))

        subs = (('bar', 20), ('baz', 'asdf'), ('foo', 'qwer'))

        v0, s0 = tlib.getTypeNorm('foo:bar', ('qwer', 20, ('baz', 'asdf')))
        v1, s1 = tlib.getTypeNorm('foo:bar', ('qwer', 20, ('baz', 'asdf')))
        v2, s2 = tlib.getTypeNorm('foo:bar', '(qwer,20,baz=asdf)')
        v3, s3 = tlib.getTypeNorm('foo:bar', '(qwer,20,baz=asdf)')

        self.eq(v0, v1)
        self.eq(v1, v2)
        self.eq(v2, v3)

        self.eq(subs, tuple(sorted(s0.items())))
        self.eq(subs, tuple(sorted(s1.items())))
        self.eq(subs, tuple(sorted(s2.items())))
        self.eq(subs, tuple(sorted(s3.items())))

    def test_types_comp_opt_only(self):
        tlib = s_types.TypeLib()

        tlib.addType('foo:bar', subof='comp', optfields='baz=str,faz=int')

        subs = (('baz', 'asdf'), ('faz', 30))

        v0, s0 = tlib.getTypeNorm('foo:bar', (('baz', 'asdf'), ('faz', 30)))
        v1, s1 = tlib.getTypeNorm('foo:bar', (('faz', 30), ('baz', 'asdf')))
        v2, s2 = tlib.getTypeNorm('foo:bar', '(baz=asdf,faz=30)')
        v3, s3 = tlib.getTypeNorm('foo:bar', '(faz=30,baz=asdf)')

        self.eq(v0, v1)
        self.eq(v1, v2)
        self.eq(v2, v3)

        self.eq(subs, tuple(sorted(s0.items())))
        self.eq(subs, tuple(sorted(s1.items())))
        self.eq(subs, tuple(sorted(s2.items())))
        self.eq(subs, tuple(sorted(s3.items())))

    def test_types_storm(self):
        tlib = s_types.TypeLib()
        self.raises(BadTypeValu, tlib.getTypeNorm, 'syn:storm', 'foo((')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'syn:storm', ',foo')
        tlib.getTypeNorm('syn:storm', 'foo:bar +baz=faz')

    def test_types_perm(self):
        tlib = s_types.TypeLib()
        self.raises(BadTypeValu, tlib.getTypeNorm, 'syn:perm', 'foo bar baz')
        self.raises(BadTypeValu, tlib.getTypeNorm, 'syn:perm', 'foo bar=(bar,baz)')
        tlib.getTypeNorm('syn:perm', 'foo:bar baz=faz')
        tlib.getTypeNorm('syn:perm', 'foo:bar   baz=faz     hehe=haha')

    def test_types_propvalu(self):
        with self.getRamCore() as core:

            # Test a list of property/valu
            valu, subs = core.getPropNorm('pvsub:xref', ['inet:ipv4', '1.2.3.4'])
            self.eq(valu, 'inet:ipv4=1.2.3.4')
            self.eq(subs.get('prop'), 'inet:ipv4')
            self.eq(subs.get('intval'), 0x01020304)
            self.notin('strval', subs)

            pvstrs = ['inet:ipv4=1.2.3.4',
                      'inet:ipv4=16909060',
                      'inet:ipv4=0x01020304'
                      ]

            for pvstr in pvstrs:
                valu, subs = core.getPropNorm('pvsub:xref', pvstr)
                self.eq(valu, 'inet:ipv4=1.2.3.4')
                self.eq(subs.get('intval'), 0x01020304)
                self.eq(subs.get('prop'), 'inet:ipv4')
                self.notin('strval', subs)

            # Make some nodes, do a pivot
            node = core.formTufoByProp('inet:ipv4', 0x01020304)
            self.nn(node)
            node = core.formTufoByProp('pvsub', 'blah', xref=['inet:ipv4', '1.2.3.4'])
            self.nn(node)
            self.eq(node[1].get('pvsub:xref'), 'inet:ipv4=1.2.3.4')
            self.eq(node[1].get('pvsub:xref:prop'), 'inet:ipv4')
            self.eq(node[1].get('pvsub:xref:intval'), 0x01020304)
            self.eq(node[1].get('pvsub:xref:prop'), 'inet:ipv4')

            nodes = core.eval('pvsub :xref:intval->inet:ipv4')
            self.len(1, nodes)
            self.eq(nodes[0][1].get('inet:ipv4'), 0x01020304)

            # Actually make some pvform nodes
            t0 = core.formTufoByProp('pvform', 'inet:ipv4=1.2.3.4')
            self.nn(t0)
            t1 = core.formTufoByProp('pvform', 'pvform=inet:ipv4=1.2.3.4')
            self.nn(t1)
            t2 = core.formTufoByProp('pvform', ['pvform', 'inet:ipv4=1.2.3.4'])
            self.nn(t2)
            # We can also eat tuples - in this case our normed value is a str and not a int
            t3 = core.formTufoByProp('pvform', ('inet:asn:name', 'Acme Corporation'))
            self.eq(t3[1].get('pvform:strval'), 'acme corporation')
            self.eq(t3[1].get('pvform:prop'), 'inet:asn:name')
            self.notin('pvform:intval', t3[1])

            # Test a comp type node made a as Provalu
            t4 = core.formTufoByProp('pvform', 'inet:web:post=(vertex.link/pennywise,"Do you want your boat?")')
            self.eq(t4[1].get('pvform:prop'), 'inet:web:post')

            # Bad values
            self.raises(BadTypeValu, core.getPropNorm, 'pvsub:xref', 1234)
            self.raises(BadTypeValu, core.getPropNorm, 'pvsub:xref', '  ')
            self.raises(BadTypeValu, core.getPropNorm, 'pvsub:xref', 'inet:ipv4= 1.2.3.4')
            self.raises(BadTypeValu, core.getPropNorm, 'pvsub:xref', '(inet:ipv4,1.2.3.4)')
            self.raises(BadTypeValu, core.getPropNorm, 'pvsub:xref', ['inet:ipv4', '1.2.3.4', 'opps'])
            # Non-existent valu
            self.raises(BadTypeValu, core.getPropNorm, 'pvsub:xref', 'inet:ip=1.2.3.4')

    def test_types_ndef(self):
        with self.getRamCore() as core:

            # No subs
            valu, subs = core.getTypeNorm('ndef', ('inet:fqdn', 'woot.com'))
            self.eq(valu, 'e247b8451766865f231805fcce989bdf')
            self.eq(subs, {'form': 'inet:fqdn'})
            # Accept lists/tuples via API
            self.eq(core.getTypeNorm('ndef', ['inet:fqdn', 'woot.com'])[0], 'e247b8451766865f231805fcce989bdf')
            self.eq(core.getTypeNorm('ndef', ('inet:fqdn', 'woot.com'))[0], 'e247b8451766865f231805fcce989bdf')
            # Accept  text which we'll parse as a storm list
            self.eq(core.getTypeNorm('ndef', '(inet:fqdn,woot.com)')[0], 'e247b8451766865f231805fcce989bdf')

            # We can ensure that the guid is stable in actual nodes
            self.eq(core.getTypeNorm('ndef', '(syn:core,self)')[0], '90ec8b92deda626d31e2d63e8dbf48be')
            # This is equivalent to the computed form made during formTufoByProp
            self.eq(core.myfo[1].get('node:ndef'), '90ec8b92deda626d31e2d63e8dbf48be')

            # Guid-in, guid-out
            self.eq(core.getTypeNorm('ndef', '90ec8b92deda626d31e2d63e8dbf48be')[0], '90ec8b92deda626d31e2d63e8dbf48be')

            self.raises(BadTypeValu, core.getTypeNorm, 'ndef', '    ')
            self.raises(BadTypeValu, core.getTypeNorm, 'ndef', 'notaguid')
            self.raises(BadTypeValu, core.getTypeNorm, 'ndef', {})
            self.raises(BadTypeValu, core.getTypeNorm, 'ndef', ())
            self.raises(BadTypeValu, core.getTypeNorm, 'ndef', [])
            # Not a form but a property
            self.raises(BadTypeValu, core.getTypeNorm, 'ndef', '(file:bytes:name,balloon.exe)')

            self.raises(ValueError, core.getTypeNorm, 'ndef', ('inet:fqdn', 'woot.com', 'hehe'))
            self.raises(ValueError, core.getTypeNorm, 'ndef', '(inet:fqdn, woot.com, hehe)')

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.types as s_types
import synapse.tests.common as s_test
import synapse.tests.utils as s_utils
import synapse.datamodel as s_datamodel


class TypesTest(s_test.SynTest):

    def test_type(self):
        self.skip('Implement base type test')

    def test_bool(self):
        model = s_datamodel.Model()
        t = model.type('bool')

        self.eq(t.norm(-1), (1, {}))
        self.eq(t.norm(0), (0, {}))
        self.eq(t.norm(1), (1, {}))
        self.eq(t.norm(2), (1, {}))
        self.eq(t.norm(True), (1, {}))
        self.eq(t.norm(False), (0, {}))

        self.eq(t.norm('-1'), (1, {}))
        self.eq(t.norm('0'), (0, {}))
        self.eq(t.norm('1'), (1, {}))

        for s in ('trUe', 'T', 'y', ' YES', 'On '):
            self.eq(t.norm(s), (1, {}))

        for s in ('faLSe', 'F', 'n', 'NO', 'Off '):
            self.eq(t.norm(s), (0, {}))

        self.raises(s_exc.BadTypeValu, t.norm, 'a')

        self.eq(t.repr(1), 'True')
        self.eq(t.repr(0), 'False')

    def test_comp(self):
        self.skip('Implement base comp test')

    def test_fieldhelper(self):
        self.skip('Implement base fieldhelper test')

    def test_guid(self):
        model = s_datamodel.Model()

        guid = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        self.eq(guid.lower(), model.type('guid').norm(guid)[0])
        self.raises(s_exc.BadTypeValu, model.type('guid').norm, 'visi')

        guid = model.type('guid').norm('*')[0]
        self.len(32, guid)

    def test_hex(self):

        # Bad configurations are not allowed for the type
        self.raises(s_exc.BadConfValu, s_types.Hex, None, None, None, {'size': -1})
        self.raises(s_exc.BadConfValu, s_types.Hex, None, None, None, {'size': 1})

        with self.getTestCore() as core:

            t = core.model.type('testhexa')
            # Test norming to index values
            testvectors = [
                ('0C', b'\x0c'),
                ('0X010001', b'\x01\x00\x01'),
                ('0FfF', b'\x0f\xff'),
                ('f12A3e', b'\xf1\x2a\x3e'),
                (b'\x01\x00\x01', b'\x01\x00\x01'),
                (b'\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~',
                 b'\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~'),
                (65537, s_exc.NoSuchFunc),
            ]

            for v, b in testvectors:
                if isinstance(b, bytes):
                    r, subs = t.norm(v)
                    self.isinstance(r, str)
                    self.eq(subs, {})
                    self.eq(t.indx(r), b)
                else:
                    self.raises(b, t.norm, v)

            # width = 4
            testvectors4 = [
                ('d41d', b'\xd4\x1d'),
                (b'\x10\x01', b'\x10\x01'),
                ('01', s_exc.BadTypeValu),
                ('010101', s_exc.BadTypeValu),
                (b'\x10\x01\xff', s_exc.BadTypeValu),
                (b'\xff', s_exc.BadTypeValu),
            ]
            t = core.model.type('testhex4')
            for v, b in testvectors4:
                if isinstance(b, bytes):
                    r, subs = t.norm(v)
                    self.isinstance(r, str)
                    self.eq(subs, {})
                    self.eq(t.indx(r), b)
                else:
                    self.raises(b, t.norm, v)

            # Do some node creation and lifting
            with core.snap(write=True) as snap:  # type: s_snap.Snap
                node = snap.addNode('testhexa', '010001')
                self.eq(node.ndef[1], '010001')

            with core.snap() as snap:  # type: s_snap.Snap
                nodes = list(snap.getNodesBy('testhexa', '010001'))
                self.len(1, nodes)

                nodes = list(snap.getNodesBy('testhexa', b'\x01\x00\x01'))
                self.len(1, nodes)

            # Do some fancy prefix searches for testhexa
            valus = ['deadb33f',
                     'deadb33fb33f',
                     'deadb3b3',
                     'deaddead',
                     'DEADBEEF']
            with core.snap(write=True) as snap:  # type: s_snap.Snap
                for valu in valus:
                    node = snap.addNode('testhexa', valu)

            with core.snap() as snap:  # type: s_snap.Snap
                nodes = list(snap.getNodesBy('testhexa', 'dead*'))
                self.len(5, nodes)

                nodes = list(snap.getNodesBy('testhexa', 'deadb3*'))
                self.len(3, nodes)

                nodes = list(snap.getNodesBy('testhexa', 'deadb33fb3*'))
                self.len(1, nodes)

                nodes = list(snap.getNodesBy('testhexa', 'deadde*'))
                self.len(1, nodes)

                nodes = list(snap.getNodesBy('testhexa', 'b33f*'))
                self.len(0, nodes)

            # Do some fancy prefix searches for testhex4
            valus = ['0000',
                     '0100',
                     '01ff',
                     '0200',
                     ]
            with core.snap(write=True) as snap:  # type: s_snap.Snap
                for valu in valus:
                    node = snap.addNode('testhex4', valu)

            with core.snap() as snap:  # type: s_snap.Snap
                nodes = list(snap.getNodesBy('testhex4', '00*'))
                self.len(1, nodes)

                nodes = list(snap.getNodesBy('testhex4', '01*'))
                self.len(2, nodes)

                nodes = list(snap.getNodesBy('testhex4', '02*'))
                self.len(1, nodes)

                # You can ask for a longer prefix then allowed
                # but you'll get no results
                nodes = list(snap.getNodesBy('testhex4', '022020*'))
                self.len(0, nodes)

    def test_int(self):

        model = s_datamodel.Model()
        t = model.type('int')

        # test ranges
        self.nn(t.norm(-2**63))
        self.raises(s_exc.BadTypeValu, t.norm, (-2**63) - 1)
        self.nn(t.norm(2**63 - 1))
        self.raises(s_exc.BadTypeValu, t.norm, 2**63)

        # test base types that Model snaps in...
        self.eq(t.norm('100')[0], 100)
        self.eq(t.norm('0x20')[0], 32)

        # Index tests
        self.eq(t.indx(-2**63), b'\x00\x00\x00\x00\x00\x00\x00\x00')
        self.eq(t.indx(-1), b'\x7f\xff\xff\xff\xff\xff\xff\xff')
        self.eq(t.indx(0), b'\x80\x00\x00\x00\x00\x00\x00\x00')
        self.eq(t.indx(1), b'\x80\x00\x00\x00\x00\x00\x00\x01')
        self.eq(t.indx(2**63 - 1), b'\xff\xff\xff\xff\xff\xff\xff\xff')
        self.raises(OverflowError, t.indx, 2**63)

        # Test merge
        self.eq(30, t.merge(20, 30))
        self.eq(20, t.merge(30, 20))
        self.eq(20, t.merge(20, 20))

        # Test min and max
        minmax = model.type('int').clone({'min': 10, 'max': 30})
        self.eq(20, minmax.norm(20)[0])
        self.raises(s_exc.BadTypeValu, minmax.norm, 9)
        self.raises(s_exc.BadTypeValu, minmax.norm, 31)
        ismin = model.type('int').clone({'ismin': True})
        self.eq(20, ismin.merge(20, 30))
        ismin = model.type('int').clone({'ismax': True})
        self.eq(30, ismin.merge(20, 30))

        # Test unsigned
        uint64 = model.type('int').clone({'signed': False})
        self.eq(uint64.norm(0)[0], 0)
        self.eq(uint64.norm(-0)[0], 0)
        self.raises(s_exc.BadTypeValu, uint64.norm, -1)
        self.eq(uint64.indx(0), b'\x00\x00\x00\x00\x00\x00\x00\x00')
        self.eq(uint64.indx(2**63), b'\x80\x00\x00\x00\x00\x00\x00\x00')
        self.eq(uint64.indx((2 * 2**63) - 1), b'\xff\xff\xff\xff\xff\xff\xff\xff')
        self.raises(OverflowError, uint64.indx, 2 * 2**63)

        # Test size, 8bit signed
        int8 = model.type('int').clone({'size': 1})
        self.eq(int8.norm(127)[0], 127)
        self.eq(int8.norm(0)[0], 0)
        self.eq(int8.norm(-128)[0], -128)
        self.raises(s_exc.BadTypeValu, int8.norm, 128)
        self.raises(s_exc.BadTypeValu, int8.norm, -129)
        self.eq(int8.indx(127), b'\xff')
        self.eq(int8.indx(0), b'\x80')
        self.eq(int8.indx(-128), b'\x00')
        self.raises(OverflowError, int8.indx, 128)

        # Test size, 128bit signed
        int128 = model.type('int').clone({'size': 16})
        self.eq(int128.norm(2**127 - 1)[0], 170141183460469231731687303715884105727)
        self.eq(int128.norm(0)[0], 0)
        self.eq(int128.norm(-2**127)[0], -170141183460469231731687303715884105728)
        self.raises(s_exc.BadTypeValu, int128.norm, 170141183460469231731687303715884105728)
        self.raises(s_exc.BadTypeValu, int128.norm, -170141183460469231731687303715884105729)
        self.eq(int128.indx(2**127 - 1), b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff')
        self.eq(int128.indx(0), b'\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        self.eq(int128.indx(-2**127), b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        self.raises(OverflowError, int8.indx, 2**128)

        # Invalid Config
        self.raises(s_exc.BadTypeDef, model.type('int').clone, {'min': 100, 'max': 1})

    def test_ival(self):
        model = s_datamodel.Model()
        ival = model.types.get('ival')

        self.eq((1451606400000, 1451606400001), ival.norm('2016')[0])
        self.eq((1451606400000, 1451606400001), ival.norm(1451606400000)[0])
        self.eq((1451606400000, 1483228800000), ival.norm(('2016', '2017'))[0])

    def test_loc(self):
        model = s_datamodel.Model()
        loctype = model.types.get('loc')

        self.eq('us.va', loctype.norm('US.    VA')[0])

    def test_ndef(self):
        self.skip('Implement base ndef test')

    def test_nodeprop(self):
        model = s_datamodel.Model()
        model.addDataModels([('test', s_utils.testmodel)])
        t = model.type('nodeprop')

        expected = (('teststr', 'This is a sTring'), {'subs': {'prop': 'teststr'}})
        self.eq(t.norm('teststr=This is a sTring'), expected)
        self.eq(t.norm(('teststr', 'This is a sTring')), expected)

    def test_range(self):
        model = s_datamodel.Model()
        t = model.type('range')

        self.raises(s_exc.NoSuchFunc, t.norm, 1)
        self.raises(s_exc.BadTypeValu, t.norm, '1')
        self.raises(s_exc.BadTypeValu, t.norm, (1,))
        self.raises(s_exc.BadTypeValu, t.norm, (1, -1))

        norm, info = t.norm((0, 0))
        self.eq(norm, (0, 0))
        self.eq(info['subs']['min'], 0)
        self.eq(info['subs']['max'], 0)

        self.eq((10, 20), t.norm('10-20')[0])

        norm, info = t.norm((-10, 0xFF))
        self.eq(norm, (-10, 255))
        self.eq(info['subs']['min'], -10)
        self.eq(info['subs']['max'], 255)

        self.eq(t.repr((-10, 0xFF)), ('-10', '255'))

        self.eq(t.indx((0, (2**63) - 1)), b'\x80\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\xff\xff\xff\xff')

        # Invalid Config
        self.raises(s_exc.BadTypeDef, model.type('range').clone, {'type': None})
        self.raises(s_exc.BadTypeDef, model.type('range').clone, {'type': ('inet:ipv4', {})})  # inet is not loaded yet

    def test_str(self):

        model = s_datamodel.Model()

        lowr = model.type('str').clone({'lower': True})
        self.eq('foo', lowr.norm('FOO')[0])

        regx = model.type('str').clone({'regex': '^[a-f][0-9]+$'})
        self.eq('a333', regx.norm('a333')[0])
        self.raises(s_exc.BadTypeValu, regx.norm, 'A333')

        regl = model.type('str').clone({'regex': '^[a-f][0-9]+$', 'lower': True})
        self.eq('a333', regl.norm('a333')[0])
        self.eq('a333', regl.norm('A333')[0])

        self.eq(b'haha', model.type('str').indx('haha'))
        byts = s_common.uhex('e2889e')
        self.eq(byts, model.type('str').indx('∞'))

        strp = model.type('str').clone({'strip': True})
        self.eq('foo', strp.norm('  foo \t')[0])
        self.eq(b'foo  bar', strp.indxByPref(' foo  bar')[0][1])
        self.eq(b'foo  bar ', strp.indxByPref(' foo  bar ')[0][1])

        onespace = model.type('str').clone({'onespace': True})
        self.eq('foo', onespace.norm('  foo\t')[0])
        self.eq('hehe haha', onespace.norm('hehe    haha')[0])
        self.eq(b'foo', onespace.indxByPref(' foo')[0][1])
        self.eq(b'foo bar', onespace.indxByPref(' foo  bar')[0][1])
        self.eq(b'foo bar', onespace.indxByPref(' foo  bar ')[0][1])
        self.eq(b'foo ba', onespace.indxByPref(' foo  ba')[0][1])

        enums = model.type('str').clone({'enums': 'hehe,haha,zork'})
        self.eq('hehe', enums.norm('hehe')[0])
        self.eq('haha', enums.norm('haha')[0])
        self.eq('zork', enums.norm('zork')[0])
        self.raises(s_exc.BadTypeValu, enums.norm, 'zing')

    def test_syntag(self):

        model = s_datamodel.Model()
        tagtype = model.type('syn:tag')

        self.eq('foo.bar', tagtype.norm('FOO.BAR')[0])
        self.eq('foo.bar', tagtype.norm('#foo.bar')[0])
        self.eq('foo.bar', tagtype.norm('foo   .   bar')[0])

        tag, info = tagtype.norm('foo')
        subs = info.get('subs')
        self.none(subs.get('up'))
        self.eq('foo', subs.get('base'))
        self.eq(0, subs.get('depth'))

        tag, info = tagtype.norm('foo.bar')
        subs = info.get('subs')
        self.eq('foo', subs.get('up'))

        self.raises(s_exc.BadTypeValu, tagtype.norm, '@#R)(Y')

    def test_time(self):
        self.skip('Implement base time test')

# -*- coding: UTF-8 -*-
import base64

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.datamodel as s_datamodel

import synapse.lib.types as s_types
import synapse.lib.snap as s_snap

import synapse.tests.common as s_test

class TypesTest(s_test.SynTest):

    def test_types_int(self):

        model = s_datamodel.Model()

        # test base types that Model snaps in...
        valu, info = model.type('int').norm('100')
        self.eq(valu, 100)

        valu, info = model.type('int').norm('0x20')
        self.eq(valu, 32)

        byts = s_common.uhex('0000000001020304')
        self.eq(model.type('int').indx(0x01020304), byts)

        minmax = model.type('int').clone({'min': 10, 'max': 30})
        self.eq(20, minmax.norm(20)[0])
        self.raises(s_exc.BadTypeValu, minmax.norm, 9)
        self.raises(s_exc.BadTypeValu, minmax.norm, 31)

        ismin = model.type('int').clone({'ismin': True})
        self.eq(20, ismin.merge(20, 30))

        ismin = model.type('int').clone({'ismax': True})
        self.eq(30, ismin.merge(20, 30))

    def test_types_str(self):

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

    def test_type_guid(self):

        model = s_datamodel.Model()

        guid = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        self.eq(guid.lower(), model.type('guid').norm(guid)[0])
        self.raises(s_exc.BadTypeValu, model.type('guid').norm, 'visi')

        guid = model.type('guid').norm('*')[0]
        self.len(32, guid)

    def test_type_loc(self):

        model = s_datamodel.Model()
        loctype = model.types.get('loc')

        self.eq('us.va', loctype.norm('US.    VA')[0])

    def test_type_time(self):
        model = s_datamodel.Model()
        self.skip('TODO BASE TIME TEST')

    def test_type_ival(self):

        model = s_datamodel.Model()
        ival = model.types.get('ival')

        self.eq((1451606400000, 1451606400001), ival.norm('2016')[0])
        self.eq((1451606400000, 1451606400001), ival.norm(1451606400000)[0])
        self.eq((1451606400000, 1483228800000), ival.norm(('2016', '2017'))[0])

    def test_type_syntag(self):

        model = s_datamodel.Model()
        tagtype = model.type('syn:tag')

        self.eq('foo.bar', tagtype.norm('FOO.BAR')[0])
        self.eq('foo.bar', tagtype.norm('#foo.bar')[0])
        self.eq('foo.bar', tagtype.norm('foo   .   bar')[0])

        tag, info = tagtype.norm('foo')
        subs = info.get('subs')
        self.none(subs.get('up'))
        self.eq('foo', subs.get('base'))
        self.eq(1, subs.get('depth'))

        tag, info = tagtype.norm('foo.bar')
        subs = info.get('subs')
        self.eq('foo', subs.get('up'))

        self.raises(s_exc.BadTypeValu, tagtype.norm, '@#R)(Y')

    def test_hex_type(self):

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

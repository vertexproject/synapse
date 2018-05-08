# -*- coding: UTF-8 -*-
import base64

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.datamodel as s_datamodel

import synapse.lib.types as s_types
import synapse.lib.xact as s_xact

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

    def test_type_time(self):
        model = s_datamodel.Model()
        self.skip('TODO BASE TIME TEST')

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

                nodes = list(xact.getNodesBy('testhexa', 'b33f*'))
                self.len(0, nodes)

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

                # You can ask for a longer prefix then allowed
                # but you'll get no results
                nodes = list(xact.getNodesBy('testhex4', '022020*'))
                self.len(0, nodes)


class Newp:

    def test_datatype_basics(self):
        tlib = s_types.TypeLib()
        self.true(tlib.isDataType('inet:url'))
        self.true(isinstance(tlib.getDataType('inet:url'), s_types.DataType))

        self.none(tlib.getDataType('newp'))
        self.raises(NoSuchType, tlib.reqDataType, 'newp')

    def test_datatype_str_enums(self):
        tlib = s_types.TypeLib()

        tlib.addType('woot', subof='str', enums='hehe,haha,hoho', lower=1)

        self.raises(BadTypeValu, tlib.getTypeNorm, 'woot', 'asdf')
        self.raises(BadTypeValu, tlib.getTypeParse, 'woot', 'asdf')

        self.eq(tlib.getTypeNorm('woot', 'HeHe')[0], 'hehe')
        self.eq(tlib.getTypeParse('woot', 'HeHe')[0], 'hehe')

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

    def test_datatype_int_repr(self):
        tlib = s_types.TypeLib()

        self.eq(tlib.getTypeRepr('int', -1), '-1')
        self.eq(tlib.getTypeRepr('int', 1), '1')

        tlib.addType('woot:min', subof='int', ismin=1)
        self.eq(tlib.getTypeRepr('woot:min', 1), '1')

    def test_type_str_nullval(self):
        tlib = s_types.TypeLib()
        tlib.addType('woot', subof='str', regex='^[0-9]+$', nullval='??')
        self.eq(tlib.getTypeNorm('woot', '10')[0], '10')
        self.eq(tlib.getTypeParse('woot', '10')[0], '10')

        self.eq(tlib.getTypeNorm('woot', '??')[0], '??')
        self.eq(tlib.getTypeParse('woot', '??')[0], '??')

        self.raises(BadTypeValu, tlib.getTypeNorm, 'woot', 'qwer')
        self.raises(BadTypeValu, tlib.getTypeParse, 'woot', 'qwer')

    def test_type_issub(self):
        with self.getRamCore() as core:
            self.true(core.isSubType('inet:dns:look', 'guid'))
            self.false(core.isSubType('inet:dns:look', 'int'))
            self.true(core.isSubType('str', 'str'))

    def test_type_json(self):
        tlib = s_types.TypeLib()
        self.eq(tlib.getTypeNorm('json', '{  "woot"       :10}')[0], '{"woot":10}')
        self.eq(tlib.getTypeNorm('json', {'woot': 10})[0], '{"woot":10}')
        self.eq(tlib.getTypeNorm('json', {'hehe': 1, 'foo': 'bar'}), ('{"foo":"bar","hehe":1}', {}))
        self.eq(tlib.getTypeParse('json', '{"woot":10}')[0], '{"woot":10}')

        self.raises(BadTypeValu, tlib.getTypeNorm, 'json', {'hehe', 'haha'})
        self.raises(BadTypeValu, tlib.getTypeNorm, 'json', 'Wow"wow')

    def test_type_str_strip(self):
        tlib = s_types.TypeLib()
        self.eq(tlib.getTypeCast('str:lwr', ' ASDF  '), 'asdf')

    def test_types_tagtime(self):
        with self.getRamCore() as core:
            valu, subs = core.getTypeNorm('syn:tag', 'Foo.Bar@20161217-20171217')

            self.eq(valu, 'foo.bar')
            self.eq(subs['seen:min'], 1481932800000)
            self.eq(subs['seen:max'], 1513468800000)

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

import math
import synapse.exc as s_exc
import synapse.common as s_common
import synapse.datamodel as s_datamodel

import synapse.lib.time as s_time
import synapse.lib.const as s_const

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist


class TypesTest(s_t_utils.SynTest):

    def test_type(self):
        # Base type tests, mainly sad paths
        model = s_datamodel.Model()
        t = model.type('bool')
        self.eq(t.info.get('bases'), ())
        self.none(t.getCompOffs('newp'))
        self.raises(s_exc.NoSuchCmpr, t.cmpr, val1=1, name='newp', val2=0)

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

    async def test_comp(self):
        async with self.getTestCore() as core:
            t = 'test:complexcomp'
            valu = ('123', 'HAHA')
            async with await core.snap() as snap:
                node = await snap.addNode(t, valu)
            pnode = node.pack(dorepr=True)
            self.eq(pnode[0], (t, (123, 'haha')))
            self.eq(pnode[1].get('repr'), ('123', 'haha'))
            self.eq(pnode[1].get('reprs').get('foo'), '123')
            self.notin('bar', pnode[1].get('reprs'))
            self.eq(node.get('foo'), 123)
            self.eq(node.get('bar'), 'haha')

            typ = core.model.type(t)
            self.eq(typ.info.get('bases'), ('comp',))
            self.raises(s_exc.BadTypeValu, typ.norm,
                        (123, 'haha', 'newp'))
            self.eq(0, typ.getCompOffs('foo'))
            self.eq(1, typ.getCompOffs('bar'))
            self.none(typ.getCompOffs('newp'))

    def test_guid(self):
        model = s_datamodel.Model()

        guid = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        self.eq(guid.lower(), model.type('guid').norm(guid)[0])
        self.raises(s_exc.BadTypeValu, model.type('guid').norm, 'visi')

        guid = model.type('guid').norm('*')[0]
        self.true(s_common.isguid(guid))

        objs = [1, 2, 'three', {'four': 5}]
        tobjs = tuple(objs)
        lnorm, _ = model.type('guid').norm(objs)
        tnorm, _ = model.type('guid').norm(tobjs)
        self.true(s_common.isguid(lnorm))
        self.eq(lnorm, tnorm)

    async def test_hex(self):

        async with self.getTestCore() as core:

            # Bad configurations are not allowed for the type
            with self.raises(s_exc.BadConfValu):
                core.model.type('hex').clone({'size': 1})

            with self.raises(s_exc.BadConfValu):
                core.model.type('hex').clone({'size': -1})

            t = core.model.type('test:hexa')
            # Test norming to index values
            testvectors = [
                ('0C', b'\x0c'),
                ('0X010001', b'\x01\x00\x01'),
                ('0FfF', b'\x0f\xff'),
                ('f12A3e', b'\xf1\x2a\x3e'),
                (b'\x01\x00\x01', b'\x01\x00\x01'),
                (b'\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~',
                 b'\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~'),
                (65537, s_exc.BadTypeValu),
            ]

            for v, b in testvectors:
                if isinstance(b, bytes):
                    r, subs = t.norm(v)
                    self.isinstance(r, str)
                    self.eq(subs, {})
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
                ('01\udcfe0101', s_exc.BadTypeValu),
            ]
            t = core.model.type('test:hex4')
            for v, b in testvectors4:
                if isinstance(b, bytes):
                    r, subs = t.norm(v)
                    self.isinstance(r, str)
                    self.eq(subs, {})
                else:
                    self.raises(b, t.norm, v)

            # Do some node creation and lifting
            async with await core.snap() as snap:
                node = await snap.addNode('test:hexa', '010001')
                self.eq(node.ndef[1], '010001')

            async with await core.snap() as snap:
                nodes = await snap.nodes('test:hexa=010001')
                self.len(1, nodes)

                nodes = await snap.nodes('test:hexa=$byts', opts={'vars': {'byts': b'\x01\x00\x01'}})
                self.len(1, nodes)

            # Do some fancy prefix searches for test:hexa
            valus = ['deadb33f',
                     'deadb33fb33f',
                     'deadb3b3',
                     'deaddead',
                     'DEADBEEF']
            async with await core.snap() as snap:
                for valu in valus:
                    node = await snap.addNode('test:hexa', valu)

            async with await core.snap() as snap:
                nodes = await snap.nodes('test:hexa=dead*')
                self.len(5, nodes)

                nodes = await snap.nodes('test:hexa=deadb3*')
                self.len(3, nodes)

                nodes = await snap.nodes('test:hexa=deadb33fb3*')
                self.len(1, nodes)

                nodes = await snap.nodes('test:hexa=deadde*')
                self.len(1, nodes)

                nodes = await snap.nodes('test:hexa=b33f*')
                self.len(0, nodes)

            # Do some fancy prefix searches for test:hex4
            valus = ['0000',
                     '0100',
                     '01ff',
                     '0200',
                     ]
            async with await core.snap() as snap:
                for valu in valus:
                    node = await snap.addNode('test:hex4', valu)

            async with await core.snap() as snap:
                nodes = await snap.nodes('test:hex4=00*')
                self.len(1, nodes)

                nodes = await snap.nodes('test:hex4=01*')
                self.len(2, nodes)

                nodes = await snap.nodes('test:hex4=02*')
                self.len(1, nodes)

                # You can ask for a longer prefix then allowed
                # but you'll get no results
                nodes = await snap.nodes('test:hex4=022020*')
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
        self.raises(s_exc.BadTypeValu, t.norm, 'newp')
        self.eq(t.norm(True)[0], 1)
        self.eq(t.norm(False)[0], 0)

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

        # Test size, 8bit signed
        int8 = model.type('int').clone({'size': 1})
        self.eq(int8.norm(127)[0], 127)
        self.eq(int8.norm(0)[0], 0)
        self.eq(int8.norm(-128)[0], -128)
        self.raises(s_exc.BadTypeValu, int8.norm, 128)
        self.raises(s_exc.BadTypeValu, int8.norm, -129)

        # Test size, 128bit signed
        int128 = model.type('int').clone({'size': 16})
        self.eq(int128.norm(2**127 - 1)[0], 170141183460469231731687303715884105727)
        self.eq(int128.norm(0)[0], 0)
        self.eq(int128.norm(-2**127)[0], -170141183460469231731687303715884105728)
        self.raises(s_exc.BadTypeValu, int128.norm, 170141183460469231731687303715884105728)
        self.raises(s_exc.BadTypeValu, int128.norm, -170141183460469231731687303715884105729)

        # test both unsigned and signed comparators
        self.true(uint64.cmpr(10, '<', 20))
        self.true(uint64.cmpr(10, '<=', 20))
        self.true(uint64.cmpr(20, '<=', 20))

        self.true(uint64.cmpr(20, '>', 10))
        self.true(uint64.cmpr(20, '>=', 10))
        self.true(uint64.cmpr(20, '>=', 20))

        self.true(int8.cmpr(-10, '<', 20))
        self.true(int8.cmpr(-10, '<=', 20))
        self.true(int8.cmpr(-20, '<=', -20))

        self.true(int8.cmpr(20, '>', -10))
        self.true(int8.cmpr(20, '>=', -10))
        self.true(int8.cmpr(-20, '>=', -20))

        # test integer enums for repr and norm
        eint = model.type('int').clone({'enums': ((1, 'hehe'), (2, 'haha'))})

        self.eq(1, eint.norm(1)[0])
        self.eq(1, eint.norm('1')[0])
        self.eq(1, eint.norm('hehe')[0])
        self.eq(2, eint.norm('haha')[0])
        self.eq(2, eint.norm('HAHA')[0])

        self.eq('hehe', eint.repr(1))
        self.eq('haha', eint.repr(2))

        self.raises(s_exc.BadTypeValu, eint.norm, 0)
        self.raises(s_exc.BadTypeValu, eint.norm, '0')
        self.raises(s_exc.BadTypeValu, eint.norm, 'newp')

        # Invalid Config
        self.raises(s_exc.BadTypeDef, model.type('int').clone, {'min': 100, 'max': 1})
        self.raises(s_exc.BadTypeDef, model.type('int').clone, {'enums': ((1, 'hehe'), (2, 'haha'), (3, 'HAHA'))})
        self.raises(s_exc.BadTypeDef, model.type('int').clone, {'enums': ((1, 'hehe'), (2, 'haha'), (2, 'beep'))})

    async def test_float(self):
        model = s_datamodel.Model()
        t = model.type('float')

        self.nn(t.norm(1.2345)[0])
        self.eq(t.norm('inf')[0], math.inf)
        self.eq(t.norm('-inf')[0], -math.inf)
        self.true(math.isnan(t.norm('NaN')[0]))
        self.eq(t.norm('-0.0')[0], -0.0)
        self.eq(t.norm('42')[0], 42.0)
        minmax = model.type('float').clone({'min': -10.0, 'max': 100.0, 'maxisvalid': True, 'minisvalid': False})
        self.raises(s_exc.BadTypeValu, minmax.norm, 'NaN')
        self.raises(s_exc.BadTypeValu, minmax.norm, '-inf')
        self.raises(s_exc.BadTypeValu, minmax.norm, 'inf')
        self.raises(s_exc.BadTypeValu, minmax.norm, '-10')
        self.raises(s_exc.BadTypeValu, minmax.norm, '-10.00001')
        self.raises(s_exc.BadTypeValu, minmax.norm, '100.00001')
        self.eq(minmax.norm('100.000')[0], 100.0)
        self.true(t.cmpr(10, '<', 20.0))
        self.false(t.cmpr(-math.inf, '>', math.inf))
        self.false(t.cmpr(-math.nan, '<=', math.inf))
        self.true(t.cmpr('inf', '>=', '-0.0'))

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ test:float=42.0 ]')
            self.len(1, nodes)
            nodes = await core.nodes('[ test:float=inf ]')
            self.len(1, nodes)

            self.len(1, await core.nodes('[ test:float=42.0 :closed=0.0]'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('[ test:float=42.0 :closed=-1.0]'))
            self.len(1, await core.nodes('[ test:float=42.0 :closed=360.0]'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('[ test:float=42.0 :closed=NaN]'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('[ test:float=42.0 :closed=360.1]'))

            await self.asyncraises(s_exc.BadTypeValu, core.nodes('[ test:float=42.0 :open=0.0]'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('[ test:float=42.0 :open=360.0]'))
            self.len(1, await core.nodes('[ test:float=42.0 :open=0.001]'))
            self.len(1, await core.nodes('[ test:float=42.0 :open=359.0]'))

    async def test_ival(self):
        model = s_datamodel.Model()
        ival = model.types.get('ival')

        self.eq(('2016/01/01 00:00:00.000', '2017/01/01 00:00:00.000'), ival.repr(ival.norm(('2016', '2017'))[0]))

        self.gt(s_common.now(), ival._normRelStr('-1 min'))

        self.eq((0, 5356800000), ival.norm((0, '1970-03-04'))[0])
        self.eq((1451606400000, 1451606400001), ival.norm('2016')[0])
        self.eq((1451606400000, 1451606400001), ival.norm(1451606400000)[0])
        self.eq((1451606400000, 1451606400001), ival.norm('2016')[0])
        self.eq((1451606400000, 1483228800000), ival.norm(('2016', '  2017'))[0])
        self.eq((1451606400000, 1483228800000), ival.norm(('2016-01-01', '  2017'))[0])
        self.eq((1451606400000, 1483142400000), ival.norm(('2016', '+365 days'))[0])
        self.eq((1448150400000, 1451606400000), ival.norm(('2016', '-40 days'))[0])
        self.eq((1447891200000, 1451347200000), ival.norm(('2016-3days', '-40 days   '))[0])
        self.eq((1451347200000, 0x7fffffffffffffff), ival.norm(('2016-3days', '?'))[0])

        start = s_common.now() + s_time.oneday - 1
        end = ival.norm(('now', '+1day'))[0][1]
        self.lt(start, end)

        oldv = ival.norm(('2016', '2017'))[0]
        newv = ival.norm(('2015', '2018'))[0]
        self.eq((1420070400000, 1514764800000), ival.merge(oldv, newv))

        self.raises(s_exc.BadTypeValu, ival.norm, '?')
        self.raises(s_exc.BadTypeValu, ival.norm, ('', ''))
        self.raises(s_exc.BadTypeValu, ival.norm, ('2016-3days', '+77days', '-40days'))
        self.raises(s_exc.BadTypeValu, ival.norm, ('?', '-1 day'))

        async with self.getTestCore() as core:

            t = core.model.type('test:time')

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'a', {'tick': '2014', '.seen': ('2005', '2006')})
                await node.addTag('foo', valu=('2000', '2001'))

                node = await snap.addNode('test:str', 'b', {'tick': '2015', '.seen': ('8679', '9000')})
                await node.addTag('foo', valu=('2015', '2018'))

                node = await snap.addNode('test:str', 'c', {'tick': '2016', '.seen': ('now-5days', 'now-1day')})
                await node.addTag('bar', valu=('1970', '1990'))

                node = await snap.addNode('test:str', 'd', {'tick': 'now', '.seen': ('now-10days', '?')})
                await node.addTag('baz', valu='now')

                node = await snap.addNode('test:str', 'e', {'tick': 'now-3days', '.seen': ('now+1day', 'now+5days')})
                await node.addTag('biz', valu=('now-1day', 'now+1day'))

                # node whose primary prop is an ival
                node = await snap.addNode('test:ival', (0, 10), {'interval': ("now", "now+4days")})
                node = await snap.addNode('test:ival', (50, 100), {'interval': ("now-2days", "now+2days")})
                node = await snap.addNode('test:ival', ("1995", "1997"), {'interval': ("2010", "2011")})
                node = await snap.addNode('test:ival', ("now-2days", "now+4days"), {'interval': ("201006", "20100605")})
                node = await snap.addNode('test:ival', ("now+21days", "?"), {'interval': ("2000", "2001")})

                # tag of tags
                node = (await snap.nodes('syn:tag=foo'))[0]
                await node.addTag('v.p', valu=('2005', '2006'))

                node = (await snap.nodes('syn:tag=bar'))[0]
                await node.addTag('vert.proj', valu=('20110605', 'now'))

                node = (await snap.nodes('syn:tag=biz'))[0]
                await node.addTag('vertex.project', valu=('now-5days', 'now'))

            await self.agenraises(s_exc.BadSyntax, core.eval('test:str :tick=(20150102, "-4 day")'))

            await self.agenlen(1, core.eval('test:str +:tick@=(now, "-1 day")'))
            await self.agenlen(1, core.eval('test:str +:tick@=2015'))
            await self.agenlen(1, core.eval('test:str +:tick@=(2015, "+1 day")'))
            await self.agenlen(1, core.eval('test:str +:tick@=(20150102+1day, "-4 day")'))
            await self.agenlen(1, core.eval('test:str +:tick@=(20150102, "-4 day")'))
            await self.agenlen(1, core.eval('test:str +:tick@=(now, "-1 day")'))
            await self.agenlen(1, core.eval('test:str +:tick@=("now-1day", "?")'))
            await self.agenlen(1, core.eval('test:str +:tick@=("now+2days", "-3 day")'))
            await self.agenlen(0, core.eval('test:str +:tick@=("now", "now+3days")'))
            await self.agenlen(1, core.eval('test:str +:tick@=("now-2days","now")'))
            await self.agenlen(0, core.eval('test:str +:tick@=("2011", "2014")'))
            await self.agenlen(1, core.eval('test:str +:tick@=("2014", "20140601")'))

            await self.agenlen(1, core.eval('test:str:tick@=(now, "-1 day")'))
            await self.agenlen(1, core.eval('test:str:tick@=2015'))
            await self.agenlen(1, core.eval('test:str:tick@=(2015, "+1 day")'))
            await self.agenlen(1, core.eval('test:str:tick@=(20150102+1day, "-4 day")'))
            await self.agenlen(1, core.eval('test:str:tick@=(20150102, "-4 day")'))
            await self.agenlen(1, core.eval('test:str:tick@=(now, "-1 day")'))
            await self.agenlen(1, core.eval('test:str:tick@=("now-1day", "?")'))
            await self.agenlen(1, core.eval('test:str:tick@=("now+2days", "-3 day")'))
            await self.agenlen(0, core.eval('test:str:tick@=("now", "now+3days")'))
            await self.agenlen(1, core.eval('test:str:tick@=("now-2days","now")'))
            await self.agenlen(0, core.eval('test:str:tick@=("2011", "2014")'))
            await self.agenlen(1, core.eval('test:str:tick@=("2014", "20140601")'))

            await self.agenlen(0, core.eval('.seen@=("2004", "2005")'))
            await self.agenlen(1, core.eval('.seen@=("9000", "9001")'))

            await self.agenlen(2, core.eval('.seen@=("now+6days", "?")'))
            await self.agenlen(2, core.eval('.seen@=(now, "-4 days")'))
            await self.agenlen(2, core.eval('.seen@=(8900, 9500)'))
            await self.agenlen(1, core.eval('.seen@=("2004", "20050201")'))
            await self.agenlen(2, core.eval('.seen@=("now", "-3 days")'))

            await self.agenlen(1, core.eval('test:ival@=1970'))
            await self.agenlen(5, core.eval('test:ival@=(1970, "now+100days")'))
            await self.agenlen(1, core.eval('test:ival@="now"'))
            await self.agenlen(1, core.eval('test:ival@=("now+1day", "now+6days")'))
            await self.agenlen(1, core.eval('test:ival@=("now-9days", "now-1day")'))
            await self.agenlen(1, core.eval('test:ival@=("now-3days", "now+3days")'))
            await self.agenlen(0, core.eval('test:ival@=("1993", "1995")'))
            await self.agenlen(0, core.eval('test:ival@=("1997", "1998")'))

            await self.agenlen(1, core.eval('test:ival:interval@="now+2days"'))
            await self.agenlen(0, core.eval('test:ival:interval@=("now-4days","now-3days")'))
            await self.agenlen(0, core.eval('test:ival:interval@=("now+4days","now+6days")'))
            await self.agenlen(1, core.eval('test:ival:interval@=("now-3days","now-1days")'))
            await self.agenlen(1, core.eval('test:ival:interval@=("now+3days","now+6days")'))
            await self.agenlen(2, core.eval('test:ival:interval@="now+1day"'))
            await self.agenlen(2, core.eval('test:ival:interval@=("20100602","20100603")'))
            await self.agenlen(2, core.eval('test:ival:interval@=("now-10days","now+10days")'))
            await self.agenlen(0, core.eval('test:ival:interval@=("1999", "2000")'))
            await self.agenlen(0, core.eval('test:ival:interval@=("2001", "2002")'))

            await self.agenlen(1, core.eval('test:ival +:interval@="now+2days"'))
            await self.agenlen(0, core.eval('test:ival +:interval@=("now-4days","now-3days")'))
            await self.agenlen(0, core.eval('test:ival +:interval@=("now+4days","now+6days")'))
            await self.agenlen(1, core.eval('test:ival +:interval@=("now-3days","now-1days")'))
            await self.agenlen(1, core.eval('test:ival +:interval@=("now+3days","now+6days")'))
            await self.agenlen(2, core.eval('test:ival +:interval@="now+1day"'))
            await self.agenlen(2, core.eval('test:ival +:interval@=("20100602","20100603")'))
            await self.agenlen(2, core.eval('test:ival +:interval@=("now-10days","now+10days")'))
            await self.agenlen(0, core.eval('test:ival +:interval@=("1999", "2000")'))
            await self.agenlen(0, core.eval('test:ival +:interval@=("2001", "2002")'))

            await self.agenlen(0, core.eval('#foo@=("2013", "2015")'))
            await self.agenlen(0, core.eval('#foo@=("2018", "2019")'))
            await self.agenlen(1, core.eval('#foo@=("1999", "2002")'))
            await self.agenlen(1, core.eval('#foo@="2015"'))
            await self.agenlen(1, core.eval('#foo@=("2010", "20150601")'))
            await self.agenlen(2, core.eval('#foo@=("2000", "2017")'))
            await self.agenlen(1, core.eval('#bar@=("1985", "1995")'))
            await self.agenlen(0, core.eval('#bar@="2000"'))
            await self.agenlen(1, core.eval('#baz@=("now","-1 day")'))
            await self.agenlen(1, core.eval('#baz@=("now-1day", "+1day")'))
            await self.agenlen(1, core.eval('#biz@="now"'))

            await self.agenlen(0, core.eval('#foo +#foo@=("2013", "2015")'))
            await self.agenlen(0, core.eval('#foo +#foo@=("2018", "2019")'))
            await self.agenlen(1, core.eval('#foo +#foo@=("1999", "2002")'))
            await self.agenlen(1, core.eval('#foo +#foo@="2015"'))
            await self.agenlen(1, core.eval('#foo +#foo@=("2010", "20150601")'))
            await self.agenlen(2, core.eval('#foo +#foo@=("2000", "2017")'))
            await self.agenlen(1, core.eval('#bar +#bar@=("1985", "1995")'))
            await self.agenlen(0, core.eval('#bar +#bar@="2000"'))
            await self.agenlen(1, core.eval('#baz +#baz@=("now","-1 day")'))
            await self.agenlen(1, core.eval('#baz +#baz@=("now-1day", "+1day")'))
            await self.agenlen(1, core.eval('#biz +#biz@="now"'))

            await self.agenlen(1, core.eval('#foo=("2015", "2018")'))

            await self.agenlen(0, core.eval('test:str#foo@=("2013", "2015")'))
            await self.agenlen(0, core.eval('test:str#foo@=("2018", "2019")'))
            await self.agenlen(1, core.eval('test:str#foo@=("1999", "2002")'))
            await self.agenlen(1, core.eval('test:str#foo@="2015"'))
            await self.agenlen(1, core.eval('test:str#foo@=("2010", "20150601")'))
            await self.agenlen(2, core.eval('test:str#foo@=("2000", "2017")'))
            await self.agenlen(1, core.eval('test:str#bar@=("1985", "1995")'))
            await self.agenlen(0, core.eval('test:str#bar@="2000"'))
            await self.agenlen(1, core.eval('test:str#baz@=("now","-1 day")'))
            await self.agenlen(1, core.eval('test:str#baz@=("now-1day", "+1day")'))
            await self.agenlen(1, core.eval('test:str#biz@="now"'))

            await self.agenlen(0, core.eval('test:str +#foo@=("2013", "2015")'))
            await self.agenlen(0, core.eval('test:str +#foo@=("2018", "2019")'))
            await self.agenlen(1, core.eval('test:str +#foo@=("1999", "2002")'))
            await self.agenlen(1, core.eval('test:str +#foo@="2015"'))
            await self.agenlen(1, core.eval('test:str +#foo@=("2010", "20150601")'))
            await self.agenlen(2, core.eval('test:str +#foo@=("2000", "2017")'))
            await self.agenlen(1, core.eval('test:str +#bar@=("1985", "1995")'))
            await self.agenlen(0, core.eval('test:str +#bar@="2000"'))
            await self.agenlen(1, core.eval('test:str +#baz@=("now","-1 day")'))
            await self.agenlen(1, core.eval('test:str +#baz@=("now-1day", "+1day")'))
            await self.agenlen(1, core.eval('test:str +#biz@="now"'))

            await self.agenlen(0, core.eval('##v.p@=("2003", "2005")'))
            await self.agenlen(0, core.eval('##v.p@=("2006", "2008")'))
            await self.agenlen(1, core.eval('##vert.proj@="2016"'))
            await self.agenlen(1, core.eval('##vert.proj@=("2010", "2012")'))
            await self.agenlen(1, core.eval('##vert.proj@=("2016", "now+6days")'))
            await self.agenlen(1, core.eval('##vert.proj@=("1995", "now+6 days")'))
            await self.agenlen(1, core.eval('##vertex.project@=("now-9days", "now-3days")'))

            await self.agenlen(0, core.eval('test:str +:tick@=(2020, 2000)'))

            now = s_common.now()
            nodes = await alist(core.eval('[test:guid="*" .seen=("-1 day","?")]'))
            node = nodes[0]
            valu = node.get('.seen')
            self.eq(valu[1], ival.futsize)
            self.true(now - s_const.day <= valu[0] < now)

            # Sad Paths
            q = '[test:str=newp .seen=(2018/03/31,2018/03/30)]'
            await self.agenraises(s_exc.BadTypeValu, core.eval(q))
            q = '[test:str=newp .seen=("+-1 day","+-1 day")]'
            await self.agenraises(s_exc.BadTypeValu, core.eval(q))
            q = '[test:str=newp  .seen=("?","?")]'
            await self.agenraises(s_exc.BadTypeValu, core.eval(q))
            q = '[test:str=newp  .seen=(2018/03/31,2018/03/31)]'
            await self.agenraises(s_exc.BadTypeValu, core.eval(q))
            q = '[test:str=newp .seen=(2008, 2019, 2000)]'
            await self.agenraises(s_exc.BadTypeValu, core.eval(q))
            q = '[test:str=newp .seen=("?","-1 day")]'
            await self.agenraises(s_exc.BadTypeValu, core.eval(q))
            # *range= not supported for ival
            q = 'test:str +:.seen*range=((20090601, 20090701), (20110905, 20110906,))'
            await self.agenraises(s_exc.NoSuchCmpr, core.eval(q))
            q = 'test:str.seen*range=((20090601, 20090701), (20110905, 20110906,))'
            await self.agenraises(s_exc.NoSuchCmpr, core.eval(q))

    async def test_loc(self):
        model = s_datamodel.Model()
        loctype = model.types.get('loc')

        self.eq('us.va', loctype.norm('US.    VA')[0])
        self.eq('', loctype.norm('')[0])
        self.eq('us.va.ओं.reston', loctype.norm('US.    VA.ओं.reston')[0])

        async with self.getTestCore() as core:
            await self.agenlen(1, core.eval('[test:int=1 :loc=us.va.syria]'))
            await self.agenlen(1, core.eval('[test:int=2 :loc=us.va.sydney]'))
            await self.agenlen(1, core.eval('[test:int=3 :loc=""]'))
            await self.agenlen(1, core.eval('[test:int=4 :loc=us.va.fairfax]'))
            await self.agenlen(1, core.eval('[test:int=5 :loc=us.va.fairfax.reston]'))
            await self.agenlen(1, core.eval('[test:int=6 :loc=us.va.fairfax.restonheights]'))
            await self.agenlen(1, core.eval('[test:int=7 :loc=us.va.fairfax.herndon]'))
            await self.agenlen(1, core.eval('[test:int=8 :loc=us.ca.sandiego]'))
            await self.agenlen(1, core.eval('[test:int=9 :loc=us.ओं]'))
            await self.agenlen(1, core.eval('[test:int=10 :loc=us.va]'))
            await self.agenlen(1, core.eval('[test:int=11 :loc=us]'))
            await self.agenlen(1, core.eval('[test:int=12 :loc=us]'))

            await self.agenlen(1, core.eval('test:int:loc=us.va.syria'))
            await self.agenlen(1, core.eval('test:int:loc=us.va.sydney'))
            await self.agenlen(0, core.eval('test:int:loc=us.va.sy'))
            await self.agenlen(1, core.eval('test:int:loc=us.va'))
            await self.agenlen(0, core.eval('test:int:loc=us.v'))
            await self.agenlen(2, core.eval('test:int:loc=us'))
            await self.agenlen(0, core.eval('test:int:loc=u'))
            await self.agenlen(1, core.eval('test:int:loc=""'))

            await self.agenlen(1, core.eval('test:int +:loc="us.va. syria"'))
            await self.agenlen(1, core.eval('test:int +:loc=us.va.sydney'))
            await self.agenlen(0, core.eval('test:int +:loc=us.va.sy'))
            await self.agenlen(1, core.eval('test:int +:loc=us.va'))
            await self.agenlen(0, core.eval('test:int +:loc=us.v'))
            await self.agenlen(2, core.eval('test:int +:loc=us'))
            await self.agenlen(0, core.eval('test:int +:loc=u'))
            await self.agenlen(1, core.eval('test:int +:loc=""'))

            await self.agenlen(0, core.eval('test:int +:loc^=u'))
            await self.agenlen(11, core.eval('test:int +:loc^=us'))
            await self.agenlen(0, core.eval('test:int +:loc^=us.'))
            await self.agenlen(0, core.eval('test:int +:loc^=us.v'))
            await self.agenlen(7, core.eval('test:int +:loc^=us.va'))
            await self.agenlen(0, core.eval('test:int +:loc^=us.va.'))
            await self.agenlen(0, core.eval('test:int +:loc^=us.va.fair'))
            await self.agenlen(4, core.eval('test:int +:loc^=us.va.fairfax'))
            await self.agenlen(0, core.eval('test:int +:loc^=us.va.fairfax.'))
            await self.agenlen(1, core.eval('test:int +:loc^=us.va.fairfax.reston'))
            await self.agenlen(0, core.eval('test:int +:loc^=us.va.fairfax.chantilly'))
            await self.agenlen(1, core.eval('test:int +:loc^=""'))
            await self.agenlen(0, core.eval('test:int +:loc^=23'))

            await self.agenlen(0, core.eval('test:int:loc^=u'))
            await self.agenlen(11, core.eval('test:int:loc^=us'))
            await self.agenlen(0, core.eval('test:int:loc^=us.'))
            await self.agenlen(0, core.eval('test:int:loc^=us.v'))
            await self.agenlen(7, core.eval('test:int:loc^=us.va'))
            await self.agenlen(0, core.eval('test:int:loc^=us.va.'))
            await self.agenlen(0, core.eval('test:int:loc^=us.va.fair'))
            await self.agenlen(4, core.eval('test:int:loc^=us.va.fairfax'))
            await self.agenlen(0, core.eval('test:int:loc^=us.va.fairfax.'))
            await self.agenlen(1, core.eval('test:int:loc^=us.va.fairfax.reston'))
            await self.agenlen(0, core.eval('test:int:loc^=us.va.fairfax.chantilly'))
            await self.agenlen(1, core.eval('test:int:loc^=""'))
            await self.agenlen(0, core.eval('test:int:loc^=23'))

    def test_ndef(self):
        model = s_datamodel.Model()
        model.addDataModels([('test', s_t_utils.testmodel)])
        t = model.type('test:ndef')

        norm, info = t.norm(('test:str', 'Foobar!'))
        self.eq(norm, ('test:str', 'Foobar!'))
        self.eq(info, {'adds': (('test:str', 'Foobar!'),),
                       'subs': {'form': 'test:str'}})

        rval = t.repr(('test:str', 'Foobar!'))
        self.eq(rval, ('test:str', 'Foobar!'))
        rval = t.repr(('test:int', 1234))
        self.eq(rval, ('test:int', '1234'))

        self.raises(s_exc.NoSuchForm, t.norm, ('test:newp', 'newp'))
        self.raises(s_exc.NoSuchForm, t.repr, ('test:newp', 'newp'))
        self.raises(s_exc.BadTypeValu, t.norm, ('newp',))

    def test_nodeprop(self):
        model = s_datamodel.Model()
        model.addDataModels([('test', s_t_utils.testmodel)])
        t = model.type('nodeprop')

        expected = (('test:str', 'This is a sTring'), {'subs': {'prop': 'test:str'}})
        self.eq(t.norm('test:str=This is a sTring'), expected)
        self.eq(t.norm(('test:str', 'This is a sTring')), expected)

        self.raises(s_exc.NoSuchProp, t.norm, ('test:str:newp', 'newp'))
        self.raises(s_exc.BadTypeValu, t.norm, ('test:str:tick', '2020', 'a wild argument appears'))

    def test_range(self):
        model = s_datamodel.Model()
        t = model.type('range')

        self.raises(s_exc.BadTypeValu, t.norm, 1)
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

        # Invalid Config
        self.raises(s_exc.BadTypeDef, model.type('range').clone, {'type': None})
        self.raises(s_exc.BadTypeDef, model.type('range').clone, {'type': ('inet:ipv4', {})})  # inet is not loaded yet

    async def test_range_filter(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'a', {'bar': ('test:str', 'a'), 'tick': '19990101'})
                node = await snap.addNode('test:str', 'b', {'.seen': ('20100101', '20110101'), 'tick': '20151207'})
                node = await snap.addNode('test:str', 'm', {'bar': ('test:str', 'm'), 'tick': '20200101'})
                node = await snap.addNode('test:guid', 'C' * 32)
                node = await snap.addNode('test:guid', 'F' * 32)
                node = await alist(core.eval('[edge:refs=((test:comp, (2048, horton)), (test:comp, (4096, whoville)))]'))
                node = await alist(core.eval('[edge:refs=((test:comp, (9001, "A mean one")), (test:comp, (40000, greeneggs)))]'))
                node = await alist(core.eval('[edge:refs=((test:int, 16), (test:comp, (9999, greenham)))]'))

            nodes = await alist(core.eval('test:str=a +:tick*range=(20000101, 20101201)'))
            self.eq(0, len(nodes))
            nodes = await alist(core.eval('test:str +:tick*range=(19701125, 20151212)'))
            self.eq({node.ndef[1] for node in nodes}, {'a', 'b'})
            nodes = await alist(core.eval('test:comp +:haha*range=(grinch, meanone)'))
            self.eq({node.ndef[1] for node in nodes}, {(2048, 'horton')})
            nodes = await alist(core.eval('test:str +:bar*range=((test:str, c), (test:str, q))'))
            self.eq({node.ndef[1] for node in nodes}, {'m'})
            nodes = await alist(core.eval('test:comp +test:comp*range=((1024, grinch), (4096, zemeanone))'))
            self.eq({node.ndef[1] for node in nodes}, {(2048, 'horton'), (4096, 'whoville')})
            guid0 = 'B' * 32
            guid1 = 'D' * 32
            nodes = await alist(core.eval(f'test:guid +test:guid*range=({guid0}, {guid1})'))
            self.eq({node.ndef[1] for node in nodes}, {'c' * 32})
            nodes = await alist(core.eval('test:int -> test:comp:hehe +test:comp*range=((1000, grinch), (4000, whoville))'))
            self.eq({node.ndef[1] for node in nodes}, {(2048, 'horton')})
            nodes = await alist(core.eval('edge:refs +:n1*range=((test:comp, (1000, green)), (test:comp, (3000, ham)))'))
            self.eq({node.ndef[1] for node in nodes},
                    {(('test:comp', (2048, 'horton')), ('test:comp', (4096, 'whoville')))})

            # The following tests show range working against a string
            nodes = await alist(core.eval('test:str*range=(b, m)'))
            self.len(2, nodes)
            nodes = await alist(core.eval('test:str +test:str*range=(b, m)'))
            self.len(2, nodes)

            # Range against a integer
            async with await core.snap() as snap:
                node = await snap.addNode('test:int', -1)
                node = await snap.addNode('test:int', 0)
                node = await snap.addNode('test:int', 1)
                node = await snap.addNode('test:int', 2)
            nodes = await alist(core.eval('test:int*range=(0, 2)'))
            self.len(3, nodes)
            nodes = await alist(core.eval('test:int +test:int*range=(0, 2)'))
            self.len(3, nodes)

            nodes = await alist(core.eval('test:int*range=(-1, -1)'))
            self.len(1, nodes)
            nodes = await alist(core.eval('test:int +test:int*range=(-1, -1)'))
            self.len(1, nodes)

            # sad path
            await self.agenraises(s_exc.BadCmprValu, core.eval('test:comp +:hehe*range=(0.0.0.0, 1.1.1.1, 6.6.6.6)'))
            await self.agenraises(s_exc.BadCmprValu, core.eval('test:comp +:haha*range=(somestring,) '))
            await self.agenraises(s_exc.BadCmprValu, core.eval('test:str +:bar*range=Foobar'))
            await self.agenraises(s_exc.BadCmprValu, core.eval('test:int +test:int*range=3456'))

    def test_str(self):

        model = s_datamodel.Model()

        lowr = model.type('str').clone({'lower': True})
        self.eq('foo', lowr.norm('FOO')[0])

        self.eq(True, lowr.cmpr('xxherexx', '~=', 'here'))
        self.eq(False, lowr.cmpr('xxherexx', '~=', '^here'))

        self.eq(True, lowr.cmpr('foo', '!=', 'bar'))
        self.eq(False, lowr.cmpr('foo', '!=', 'FOO'))

        self.eq(True, lowr.cmpr('foobar', '^=', 'FOO'))
        self.eq(False, lowr.cmpr('foubar', '^=', 'FOO'))

        regx = model.type('str').clone({'regex': '^[a-f][0-9]+$'})
        self.eq('a333', regx.norm('a333')[0])
        self.raises(s_exc.BadTypeValu, regx.norm, 'A333')

        regl = model.type('str').clone({'regex': '^[a-f][0-9]+$', 'lower': True})
        self.eq('a333', regl.norm('a333')[0])
        self.eq('a333', regl.norm('A333')[0])

        byts = s_common.uhex('e2889e')

        # The real world is a harsh place.
        strp = model.type('str').clone({'strip': True})
        self.eq('foo', strp.norm('  foo \t')[0])

        onespace = model.type('str').clone({'onespace': True})
        self.eq('foo', onespace.norm('  foo\t')[0])
        self.eq('hehe haha', onespace.norm('hehe    haha')[0])

        enums = model.type('str').clone({'enums': 'hehe,haha,zork'})
        self.eq('hehe', enums.norm('hehe')[0])
        self.eq('haha', enums.norm('haha')[0])
        self.eq('zork', enums.norm('zork')[0])
        self.raises(s_exc.BadTypeValu, enums.norm, 'zing')

        strsubs = model.type('str').clone({'regex': r'(?P<first>[ab]+)(?P<last>[zx]+)'})
        norm, info = strsubs.norm('aabbzxxxxxz')
        self.eq(info.get('subs'), {'first': 'aabb', 'last': 'zxxxxxz'})

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
        self.raises(s_exc.BadTypeValu, tagtype.norm, 'foo\udcfe.bar')
        self.raises(s_exc.BadTypeValu, tagtype.norm, 'foo\u200b.bar')
        self.raises(s_exc.BadTypeValu, tagtype.norm, 'foo\u202e.bar')
        self.raises(s_exc.BadTypeValu, tagtype.norm, 'foo.')
        self.raises(s_exc.BadTypeValu, tagtype.norm, '.')
        self.raises(s_exc.BadTypeValu, tagtype.norm, '')
        # Tags including non-english unicode letters are okay
        self.eq('icon.ॐ', tagtype.norm('ICON.ॐ')[0])
        # homoglyphs are also possible
        self.eq('is.ｂob.evil', tagtype.norm('is.\uff42ob.evil')[0])

    async def test_time(self):

        model = s_datamodel.Model()
        ttime = model.types.get('time')

        self.gt(s_common.now(), ttime.norm('-1hour')[0])

        tminmax = ttime.clone({'min': True, 'max': True})
        # Merge testing with tminmax
        now = s_common.now()
        self.eq(now + 1, tminmax.merge(now, now + 1))
        self.eq(now, tminmax.merge(now + 1, now))

        async with self.getTestCore() as core:

            t = core.model.type('test:time')

            # explicitly test our "future/ongoing" value...
            future = 0x7fffffffffffffff
            self.eq(t.norm('?')[0], future)
            self.eq(t.norm(future)[0], future)
            self.eq(t.repr(future), '?')

            # Explicitly test our max time vs. future marker
            maxtime = 253402300799999  # 9999/12/31 23:59:59.999
            self.eq(t.norm(maxtime)[0], maxtime)
            self.eq(t.repr(maxtime), '9999/12/31 23:59:59.999')
            self.eq(t.norm('9999/12/31 23:59:59.999')[0], maxtime)
            self.raises(s_exc.BadTypeValu, t.norm, maxtime + 1)

            tick = t.norm('2014')[0]
            self.eq(t.repr(tick), '2014/01/01 00:00:00.000')

            tock = t.norm('2015')[0]

            self.raises(s_exc.BadCmprValu,
                        t.cmpr, '2015', 'range=', tick)

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'a', {'tick': '2014'})
                node = await snap.addNode('test:str', 'b', {'tick': '2015'})
                node = await snap.addNode('test:str', 'c', {'tick': '2016'})
                node = await snap.addNode('test:str', 'd', {'tick': 'now'})

            nodes = await core.nodes('test:str:tick=2014')
            self.eq({node.ndef[1] for node in nodes}, {'a'})

            nodes = await core.nodes('test:str:tick*range=(2014, 2015)')
            self.eq({node.ndef[1] for node in nodes}, {'a', 'b'})

            nodes = await core.nodes('test:str:tick=201401*')
            self.eq({node.ndef[1] for node in nodes}, {'a'})

            nodes = await core.nodes('test:str:tick*range=("-3000 days", now)')
            self.eq({node.ndef[1] for node in nodes}, {'a', 'b', 'c', 'd'})

            opts = {'vars': {'tick': tick, 'tock': tock}}
            nodes = await core.nodes('test:str:tick*range=($tick, $tock)', opts=opts)
            self.eq({node.ndef[1] for node in nodes}, {'a', 'b'})

            nodes = await core.nodes('test:str:tick*range=(20131231, "+2 days")')
            self.eq({node.ndef[1] for node in nodes}, {'a'})

            nodes = await core.nodes('test:str:tick*range=("-1 day", "+1 day")')
            self.eq({node.ndef[1] for node in nodes}, {'d'})

            nodes = await core.nodes('test:str:tick*range=("-1 days", now)')
            self.eq({node.ndef[1] for node in nodes}, {'d'})

            # Equivalent lift
            nodes = await core.nodes('test:str:tick*range=(now, "-1 days")')
            self.eq({node.ndef[1] for node in nodes}, {'d'})
            # This is equivalent of the previous lift

            self.eq({node.ndef[1] for node in nodes}, {'d'})

            self.true(t.cmpr('2015', '>=', '20140202'))
            self.true(t.cmpr('2015', '>=', '2015'))
            self.true(t.cmpr('2015', '>', '20140202'))
            self.false(t.cmpr('2015', '>', '2015'))

            self.true(t.cmpr('20150202', '<=', '2016'))
            self.true(t.cmpr('20150202', '<=', '2016'))
            self.true(t.cmpr('20150202', '<', '2016'))
            self.false(t.cmpr('2015', '<', '2015'))

            await self.agenlen(1, core.eval('test:str +:tick=2015'))

            await self.agenlen(1, core.eval('test:str +:tick*range=($test, "+- 2day")',
                                            opts={'vars': {'test': '2015'}}))

            await self.agenlen(1, core.eval('test:str +:tick*range=(now, "-+ 1day")'))

            await self.agenlen(1, core.eval('test:str +:tick*range=(2015, "+1 day")'))
            await self.agenlen(1, core.eval('test:str +:tick*range=(20150102, "-3 day")'))
            await self.agenlen(0, core.eval('test:str +:tick*range=(20150201, "+1 day")'))
            await self.agenlen(1, core.eval('test:str +:tick*range=(20150102, "+- 2day")'))
            await self.agenlen(2, core.eval('test:str +:tick*range=(2015, 2016)'))
            await self.agenlen(0, core.eval('test:str +:tick*range=(2016, 2015)'))

            await self.agenlen(2, core.eval('test:str:tick*range=(2015, 2016)'))
            await self.agenlen(0, core.eval('test:str:tick*range=(2016, 2015)'))

            await self.agenlen(1, core.eval('test:str:tick*range=(2015, "+1 day")'))
            await self.agenlen(4, core.eval('test:str:tick*range=(2014, "now")'))
            await self.agenlen(0, core.eval('test:str:tick*range=(20150201, "+1 day")'))
            await self.agenlen(1, core.eval('test:str:tick*range=(now, "+-1 day")'))
            await self.agenlen(0, core.eval('test:str:tick*range=(now, "+1 day")'))

            # Sad path for *range=
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str:tick*range=("+- 1day", "now")')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str:tick*range=("-+ 1day", "now")')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[test:guid="*" :tick="+-1 day"]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str:tick*range=(2015)')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str:tick*range=$tick', opts={'vars': {'tick': tick}})

            await self.agenraises(s_exc.BadCmprValu, core.eval('test:str +:tick*range=(2015)'))
            await self.agenraises(s_exc.BadCmprValu, core.eval('test:str +:tick*range=(2015, 2016, 2017)'))
            await self.agenraises(s_exc.BadTypeValu, core.eval('test:str +:tick*range=("?", "+1 day")'))
            await self.agenraises(s_exc.BadTypeValu, core.eval('test:str +:tick*range=(2000, "?+1 day")'))
            await self.agenraises(s_exc.BadTypeValu, core.eval('test:str:tick*range=("?", "+1 day")'))
            await self.agenraises(s_exc.BadTypeValu, core.eval('test:str:tick*range=(2000, "?+1 day")'))

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 't1', {'tick': '2018/12/02 23:59:59.000'})
                node = await snap.addNode('test:str', 't2', {'tick': '2018/12/03'})
                node = await snap.addNode('test:str', 't3', {'tick': '2018/12/03 00:00:01.000'})

            await self.agenlen(0, core.eval('test:str:tick*range=(2018/12/01, "+24 hours")'))
            await self.agenlen(2, core.eval('test:str:tick*range=(2018/12/01, "+48 hours")'))

            await self.agenlen(0, core.eval('test:str:tick*range=(2018/12/02, "+23 hours")'))
            await self.agenlen(1, core.eval('test:str:tick*range=(2018/12/02, "+86399 seconds")'))
            await self.agenlen(2, core.eval('test:str:tick*range=(2018/12/02, "+24 hours")'))
            await self.agenlen(3, core.eval('test:str:tick*range=(2018/12/02, "+86401 seconds")'))
            await self.agenlen(3, core.eval('test:str:tick*range=(2018/12/02, "+25 hours")'))

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'a', {'tick': '2014'})
                node = await snap.addNode('test:int', node.get('tick') + 1)
                node = await snap.addNode('test:str', 'b', {'tick': '2015'})
                node = await snap.addNode('test:int', node.get('tick') + 1)
                node = await snap.addNode('test:str', 'c', {'tick': '2016'})
                node = await snap.addNode('test:int', node.get('tick') + 1)
                node = await snap.addNode('test:str', 'd', {'tick': 'now'})
                node = await snap.addNode('test:int', node.get('tick') + 1)

            q = 'test:int $end=$node.value() test:str:tick*range=(2015, $end) -test:int'
            nodes = await alist(core.eval(q))
            self.len(6, nodes)
            self.eq({node.ndef[1] for node in nodes}, {'b', 'c', 'd'})

    async def test_edges(self):
        model = s_datamodel.Model()
        e = model.type('edge')
        t = model.type('timeedge')

        self.eq(0, e.getCompOffs('n1'))
        self.eq(1, e.getCompOffs('n2'))
        self.none(e.getCompOffs('newp'))

        self.eq(0, t.getCompOffs('n1'))
        self.eq(1, t.getCompOffs('n2'))
        self.eq(2, t.getCompOffs('time'))
        self.none(t.getCompOffs('newp'))

        # Sad path testing
        self.raises(s_exc.BadTypeValu, e.norm, ('newp',))
        self.raises(s_exc.BadTypeValu, t.norm, ('newp',))

        # Repr testing with the test model
        async with self.getTestCore() as core:
            e = core.model.type('edge')
            t = core.model.type('timeedge')

            norm, _ = e.norm((('test:str', '1234'), ('test:int', '1234')))
            self.eq(norm, (('test:str', '1234'), ('test:int', 1234)))

            norm, _ = t.norm((('test:str', '1234'), ('test:int', '1234'), '2001'))
            self.eq(norm, (('test:str', '1234'), ('test:int', 1234), 978307200000))

            rval = e.repr((('test:str', '1234'), ('test:str', 'hehe')))
            self.eq(rval, (('test:str', '1234'), ('test:str', 'hehe')))

            rval = e.repr((('test:int', 1234), ('test:str', 'hehe')))
            self.eq(rval, (('test:int', '1234'), ('test:str', 'hehe')))

            rval = e.repr((('test:str', 'hehe'), ('test:int', 1234)))
            self.eq(rval, (('test:str', 'hehe'), ('test:int', '1234')))

            rval = e.repr((('test:int', 4321), ('test:int', 1234)))
            self.eq(rval, (('test:int', '4321'), ('test:int', '1234')))

            rval = e.repr((('test:int', 4321), ('test:comp', (1234, 'hehe'))))
            self.eq(rval, (('test:int', '4321'), ('test:comp', ('1234', 'hehe'))))

            tv = 5356800000
            tr = '1970/03/04 00:00:00.000'

            rval = t.repr((('test:str', '1234'), ('test:str', 'hehe'), tv))
            self.eq(rval, (('test:str', '1234'), ('test:str', 'hehe'), tr))

            rval = t.repr((('test:int', 1234), ('test:str', 'hehe'), tv))
            self.eq(rval, (('test:int', '1234'), ('test:str', 'hehe'), tr))

            rval = t.repr((('test:str', 'hehe'), ('test:int', 1234), tv))
            self.eq(rval, (('test:str', 'hehe'), ('test:int', '1234'), tr))

    async def test_types_long_indx(self):

        aaaa = 'A' * 200
        url = f'http://vertex.link/visi?fuzz0={aaaa}&fuzz1={aaaa}'

        async with self.getTestCore() as core:
            opts = {'vars': {'url': url}}
            self.len(1, await core.nodes('[ it:exec:url="*" :url=$url ]', opts=opts))
            self.len(1, await core.nodes('it:exec:url:url=$url', opts=opts))

    async def test_types_array(self):

        mdef = {
            'types': (
                ('test:array', ('array', {'type': 'inet:ipv4'}), {}),
                ('test:arraycomp', ('comp', {'fields': (('ipv4s', 'test:array'), ('int', 'test:int'))}), {}),
                ('test:witharray', ('guid', {}), {}),
            ),
            'forms': (
                ('test:array', {}, (
                )),
                ('test:arraycomp', {}, (
                    ('ipv4s', ('test:array', {}), {}),
                    ('int', ('test:int', {}), {}),
                )),
                ('test:witharray', {}, (
                    ('fqdns', ('array', {'type': 'inet:fqdn', 'uniq': True, 'sorted': True}), {}),
                )),
            ),
        }
        async with self.getTestCore() as core:

            core.model.addDataModels([('asdf', mdef)])

            with self.raises(s_exc.BadTypeDef):
                await core.addFormProp('test:int', '_hehe', ('array', {'type': 'array'}), {})

            nodes = await core.nodes('[ test:array=(1.2.3.4, 5.6.7.8) ]')
            self.len(1, nodes)

            # create a long array (fails pre-020)
            arr = ','.join([str(i) for i in range(300)])
            nodes = await core.nodes(f'[ test:array=({arr}) ]')
            self.len(1, nodes)

            nodes = await core.nodes('test:array*[=1.2.3.4]')
            self.len(1, nodes)

            nodes = await core.nodes('test:array*[=1.2.3.4] | delnode')
            nodes = await core.nodes('test:array*[=1.2.3.4]')
            self.len(0, nodes)

            nodes = await core.nodes('[ test:arraycomp=((1.2.3.4, 5.6.7.8), 10) ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:arraycomp', ((0x01020304, 0x05060708), 10)))
            self.eq(nodes[0].get('int'), 10)
            self.eq(nodes[0].get('ipv4s'), (0x01020304, 0x05060708))

            # make sure "adds" got added
            nodes = await core.nodes('inet:ipv4=1.2.3.4 inet:ipv4=5.6.7.8')
            self.len(2, nodes)

            nodes = await core.nodes('[ test:witharray="*" :fqdns=(woot.com, VERTEX.LINK, vertex.link) ]')
            self.len(1, nodes)

            self.eq(nodes[0].get('fqdns'), ('vertex.link', 'woot.com'))

            nodes = await core.nodes('test:witharray:fqdns=(vertex.link, WOOT.COM)')
            self.len(1, nodes)

            nodes = await core.nodes('test:witharray:fqdns*[=vertex.link]')
            self.len(1, nodes)

            nodes = await core.nodes('test:witharray [ :fqdns=(hehe.com, haha.com) ]')
            self.len(1, nodes)

            nodes = await core.nodes('inet:fqdn=hehe.com inet:fqdn=haha.com')
            self.len(2, nodes)

            # make sure the multi-array entries got deleted
            nodes = await core.nodes('test:witharray:fqdns*[=vertex.link]')
            self.len(0, nodes)

            nodes = await core.nodes('test:witharray:fqdns*[=hehe.com]')
            self.len(1, nodes)

            nodes = await core.nodes('test:witharray:fqdns*[~=ehe]')
            self.len(1, nodes)

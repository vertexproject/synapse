import math
import decimal
import datetime
import synapse.exc as s_exc
import synapse.common as s_common
import synapse.datamodel as s_datamodel

import synapse.lib.time as s_time
import synapse.lib.const as s_const
import synapse.lib.stormtypes as s_stormtypes

import synapse.tests.utils as s_t_utils


class TypesTest(s_t_utils.SynTest):

    async def test_types_normstormvalu(self):

        async with self.getTestCore() as core:

            # size is a non-negative integer
            size = core.model.type('size')
            self.eq(0, (await size.norm(0))[0])
            self.eq(42, (await size.norm('42'))[0])
            with self.raises(s_exc.BadTypeValu):
                await size.norm(-1)

            # fixed-width signed integer types
            for name, bits in (('int8', 8), ('int16', 16), ('int32', 32), ('int64', 64)):
                intt = core.model.type(name)
                self.eq(0, (await intt.norm(0))[0])
                self.eq(2 ** (bits - 1) - 1, (await intt.norm(2 ** (bits - 1) - 1))[0])
                self.eq(-2 ** (bits - 1), (await intt.norm(-2 ** (bits - 1)))[0])
                with self.raises(s_exc.BadTypeValu):
                    await intt.norm(2 ** (bits - 1))
                with self.raises(s_exc.BadTypeValu):
                    await intt.norm(-2 ** (bits - 1) - 1)

            # fixed-width unsigned integer types
            for name, bits in (('uint8', 8), ('uint16', 16), ('uint32', 32), ('uint64', 64)):
                uint = core.model.type(name)
                self.eq(0, (await uint.norm(0))[0])
                self.eq(2 ** bits - 1, (await uint.norm(2 ** bits - 1))[0])
                with self.raises(s_exc.BadTypeValu):
                    await uint.norm(-1)
                with self.raises(s_exc.BadTypeValu):
                    await uint.norm(2 ** bits)

            # a non-form value already normed as this type is reused as-is
            # (same typehash), here re-casting a str typed value to str
            self.eq('Foo', await core.callStorm('$x=$lib.cast(str, Foo) return($lib.cast(str, $x))'))

            # a value of a non-equivalent type re-norms through the target type
            # (loc lowercases on its own norm; str then keeps it verbatim)
            self.eq('us', await core.callStorm('$x=$lib.cast(loc, US) return($lib.cast(str, $x))'))

            # virtual prop values carried by a Valu survive the reuse path
            q = '''
                [ econ:purchase=* :price=13.37 :price.currency=usd ]
                return($lib.cast(econ:price, :price).currency)
            '''
            self.eq('USD', await core.callStorm(q))

            await core.nodes('[test:str=hello]')

            # a NodeRef whose typehash matches a form type takes the existence
            # fast-path: the first norm confirms via getNodeByNdef and caches
            # exists on the ref, the second reuses the cached flag; both skip
            # the node creation work.
            self.len(2, await core.nodes('$ref=$lib.cast(test:str, hello) [test:str=$ref] [test:str=$ref]'))

            # a NodeRef to a node that does not exist falls through to a normal
            # norm of the carried value
            self.len(0, await core.nodes('$ref=$lib.cast(test:str, nope) test:str=$ref'))

    async def test_type(self):
        # Base type tests, mainly sad paths
        model = s_datamodel.getBaseModel()
        t = model.type('bool')
        self.eq(t.info.get('bases'), ('base',))
        with self.raises(s_exc.NoSuchCmpr):
            await t.cmpr(val1=1, name='newp', val2=0)

        str00 = model.type('str').clone({})
        str01 = model.type('str').clone({})
        str02 = model.type('str').clone({'lower': True})
        self.eq(str00, str01)
        self.ne(str01, str02)

    async def test_setvirtinfo(self):
        async with self.getTestCore() as core:
            t = core.model.type('inet:sockaddr')

            iptype = core.model.type('inet:ip')
            porttype = core.model.type('inet:port')
            runttype = core.model.type('syn:type')

            # virt type is a (non-runt) form: the virt is recorded and an add is
            # created which carries the provided norminfo.
            ipnorm, ipinfo = await iptype.norm('1.2.3.4')
            info = {}
            t.setVirtInfo(info, 'ip', ipnorm, iptype, ipinfo)
            self.eq(info['virts'], {'ip': (ipnorm, iptype.stortype)})
            self.eq(info['adds'], [('inet:ip', ipnorm, ipinfo)])

            # virt type is not a form: only the virt is recorded.
            info = {}
            t.setVirtInfo(info, 'port', 80, porttype)
            self.eq(info['virts'], {'port': (80, porttype.stortype)})
            self.notin('adds', info)

            # virt type is a runt form: only the virt is recorded.
            self.true(core.model.form('syn:type').isrunt)
            info = {}
            t.setVirtInfo(info, 'type', 'inet:ip', runttype)
            self.eq(info['virts'], {'type': ('inet:ip', runttype.stortype)})
            self.notin('adds', info)

    async def test_mass(self):

        async with self.getTestCore() as core:

            mass = core.model.type('phys:mass')

            self.eq('0.000042', (await mass.norm('42µg'))[0])
            self.eq('0.2', (await mass.norm('200mg'))[0])
            self.eq('1000', (await mass.norm('1kg'))[0])
            self.eq('606452.504', (await mass.norm('1,337 lbs'))[0])
            self.eq('8490337.73', (await mass.norm('1,337 stone'))[0])

            with self.raises(s_exc.BadTypeValu):
                await mass.norm('1337 newps')

            with self.raises(s_exc.BadTypeValu):
                await mass.norm('newps')

    async def test_velocity(self):
        model = s_datamodel.getBaseModel()
        velo = model.type('velocity')

        with self.raises(s_exc.BadTypeValu):
            await velo.norm('10newps/sec')

        with self.raises(s_exc.BadTypeValu):
            await velo.norm('10km/newp')

        with self.raises(s_exc.BadTypeValu):
            await velo.norm('10km/newp')

        with self.raises(s_exc.BadTypeValu):
            await velo.norm('10newp')

        with self.raises(s_exc.BadTypeValu):
            await velo.norm('-10k/h')

        with self.raises(s_exc.BadTypeValu):
            await velo.norm(-1)

        with self.raises(s_exc.BadTypeValu):
            await velo.norm('')

        self.eq(1, (await velo.norm('mm/sec'))[0])
        self.eq(1, (await velo.norm('1mm/sec'))[0])
        self.eq(407517, (await velo.norm('1337feet/sec'))[0])

        self.eq(514, (await velo.norm('knots'))[0])
        self.eq(299792458000, (await velo.norm('c'))[0])

        self.eq(2777, (await velo.norm('10kph'))[0])
        self.eq(4470, (await velo.norm('10mph'))[0])
        self.eq(10, (await velo.norm(10))[0])

        relv = velo.clone({'relative': True})
        self.eq(-2777, (await relv.norm('-10k/h'))[0])

        self.eq(1, (await velo.norm('1.23'))[0])

        async with self.getTestCore() as core:
            nodes = await core.nodes('[transport:sea:telem=(foo,) :speed=(1.1 * 2) ]')
            self.propeq(nodes[0], 'speed', 2)

    async def test_hugenum(self):

        model = s_datamodel.getBaseModel()
        huge = model.type('hugenum')

        with self.raises(s_exc.BadTypeValu):
            await huge.norm('730750818665451459101843')

        with self.raises(s_exc.BadTypeValu):
            await huge.norm('-730750818665451459101843')

        with self.raises(s_exc.BadTypeValu):
            await huge.norm(None)

        with self.raises(s_exc.BadTypeValu):
            await huge.norm('foo')

        self.eq('0.000000000000000000000001', (await huge.norm('1E-24'))[0])
        self.eq('0.000000000000000000000001', (await huge.norm('1.0E-24'))[0])
        self.eq('0.000000000000000000000001', (await huge.norm('0.000000000000000000000001'))[0])

        self.eq('0', (await huge.norm('1E-25'))[0])
        self.eq('0', (await huge.norm('5E-25'))[0])
        self.eq('0.000000000000000000000001', (await huge.norm('6E-25'))[0])
        self.eq('1.000000000000000000000002', (await huge.norm('1.0000000000000000000000015'))[0])

        bign = '730750818665451459101841.000000000000000000000002'
        self.eq(bign, (await huge.norm(bign))[0])

        big2 = '730750818665451459101841.0000000000000000000000015'
        self.eq(bign, (await huge.norm(big2))[0])

        bign = '-730750818665451459101841.000000000000000000000002'
        self.eq(bign, (await huge.norm(bign))[0])

        big2 = '-730750818665451459101841.0000000000000000000000015'
        self.eq(bign, (await huge.norm(big2))[0])

        with self.raises(s_exc.BadTypeValu):
            await huge.norm('1e+99999999999999999999999999999')

        # hexadecimal and octal integer notation
        self.eq('255', (await huge.norm('0xff'))[0])
        self.eq('255', (await huge.norm('0XFF'))[0])
        self.eq('-255', (await huge.norm('-0xff'))[0])
        self.eq('15', (await huge.norm('0o17'))[0])
        self.eq('15', (await huge.norm('+0o17'))[0])

        with self.raises(s_exc.BadTypeValu):
            await huge.norm('0xnope')

        # native min/max support (closed interval)
        hugemm = huge.clone({'min': 0, 'max': 100})
        self.eq('0', (await hugemm.norm(0))[0])
        self.eq('100', (await hugemm.norm(100))[0])

        with self.raises(s_exc.BadTypeValu):
            await hugemm.norm('-0.1')

        with self.raises(s_exc.BadTypeValu):
            await hugemm.norm('100.1')

        # open interval via minisvalid/maxisvalid
        hugeopen = huge.clone({'min': 0, 'minisvalid': False, 'max': 100, 'maxisvalid': False})
        self.eq('0.1', (await hugeopen.norm('0.1'))[0])

        with self.raises(s_exc.BadTypeValu):
            await hugeopen.norm(0)

        with self.raises(s_exc.BadTypeValu):
            await hugeopen.norm(100)

        # explicit unit suffix matching + defunit repr conversion (non-1 multiplier)
        hugeunit = huge.clone({'units': {'k': '1000', 'm': '1000000'}, 'defunit': 'k'})
        self.eq('5000', (await hugeunit.norm('5k'))[0])
        self.eq('2000000', (await hugeunit.norm('2m'))[0])
        self.eq('5000', (await hugeunit.norm('5000'))[0])

        # whitespace insensitive suffix matching
        self.eq('5000', (await hugeunit.norm('  5  k  '))[0])

        # without a defunit, repr returns the bare normalized value
        self.eq('5000', huge.repr('5000'))

        # defunit conversion on repr (divides by the unit multiplier)
        self.eq('5k', hugeunit.repr('5000'))
        self.eq('2.5k', hugeunit.repr('2500'))

        # unknown suffix is rejected
        with self.raises(s_exc.BadTypeValu):
            await hugeunit.norm('5x')

        # defunit must exist in units
        with self.raises(s_exc.BadTypeDef):
            huge.clone({'defunit': 'k'})

    async def test_percent(self):

        async with self.getTestCore() as core:

            perc = core.model.type('percent')

            self.eq('10.2', (await perc.norm('10.2%'))[0])
            self.eq('10.2', (await perc.norm('10.2'))[0])
            self.eq('10.2', (await perc.norm(10.2))[0])
            self.eq('0', (await perc.norm(0))[0])
            self.eq('100', (await perc.norm('100%'))[0])
            self.eq('33.333333333333333333333333', (await perc.norm('33.333333333333333333333333%'))[0])

            # whitespace around the value and suffix is insensitive
            self.eq('10', (await perc.norm('10%'))[0])
            self.eq('10', (await perc.norm('  10  %  '))[0])

            self.eq('10.2%', perc.repr('10.2'))
            self.eq('0%', perc.repr('0'))
            self.eq('100%', perc.repr('100'))

            # an unknown suffix is rejected
            with self.raises(s_exc.BadTypeValu):
                await perc.norm('10x')

            with self.raises(s_exc.BadTypeValu):
                await perc.norm('-0.1')

            with self.raises(s_exc.BadTypeValu):
                await perc.norm('100.1')

            with self.raises(s_exc.BadTypeValu):
                await perc.norm(101)

            with self.raises(s_exc.BadTypeValu):
                await perc.norm('foo')

            nodes = await core.nodes('[ ou:opening=* :remote=42.5% ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'remote', '42.5')
            self.eq('42.5%', nodes[0].reprs().get('remote'))

            self.len(1, await core.nodes('ou:opening:remote>42'))
            self.len(0, await core.nodes('ou:opening:remote>43'))

    async def test_ratio(self):

        async with self.getTestCore() as core:

            rati = core.model.type('ratio')

            # behaves like percent for the % unit / repr
            self.eq('10.2', (await rati.norm('10.2%'))[0])
            self.eq('10.2', (await rati.norm('10.2'))[0])
            self.eq('10.2', (await rati.norm(10.2))[0])
            self.eq('0', (await rati.norm(0))[0])
            self.eq('10.2%', rati.repr('10.2'))

            # unlike percent, negative values and values over 100 are allowed
            self.eq('-0.1', (await rati.norm('-0.1'))[0])
            self.eq('-25.5', (await rati.norm('-25.5%'))[0])
            self.eq('100.1', (await rati.norm('100.1'))[0])
            self.eq('250', (await rati.norm(250))[0])
            self.eq('-25.5%', rati.repr('-25.5'))

            # an unknown suffix is still rejected
            with self.raises(s_exc.BadTypeValu):
                await rati.norm('10x')

            with self.raises(s_exc.BadTypeValu):
                await rati.norm('foo')

    async def test_taxonomy(self):

        model = s_datamodel.getBaseModel()
        taxo = model.type('taxonomy')
        self.eq('foo.bar.baz.', (await taxo.norm('foo.bar.baz'))[0])
        self.eq('foo.bar.baz.', (await taxo.norm('foo.bar.baz.'))[0])
        self.eq('foo.bar.baz.', (await taxo.norm('foo.bar.baz.'))[0])
        self.eq('foo.bar.baz.', (await taxo.norm(('foo', 'bar', 'baz')))[0])
        self.eq('foo.b_a_r.baz.', (await taxo.norm('foo.b-a-r.baz.'))[0])
        self.eq('foo.b_a_r.baz.', (await taxo.norm('foo.  b   a   r  .baz.'))[0])

        self.eq('foo.bar.baz', taxo.repr('foo.bar.baz.'))

        with self.raises(s_exc.BadTypeValu):
            await taxo.norm('foo.---.baz')

        norm, info = await taxo.norm('foo.bar.baz')
        self.eq(2, info['subs']['depth'][1])
        self.eq('baz', info['subs']['base'][1])
        self.eq('foo.bar.', info['subs']['parent'][1])

        self.true(await taxo.cmpr('foo', '~=', 'foo'))
        self.false(await taxo.cmpr('foo', '~=', 'foo.'))
        self.false(await taxo.cmpr('foo', '~=', 'foo.bar'))
        self.false(await taxo.cmpr('foo', '~=', 'foo.bar.'))
        self.true(await taxo.cmpr('foo.bar', '~=', 'foo'))
        self.true(await taxo.cmpr('foo.bar', '~=', 'foo.'))
        self.true(await taxo.cmpr('foo.bar', '~=', 'foo.bar'))
        self.false(await taxo.cmpr('foo.bar', '~=', 'foo.bar.'))
        self.false(await taxo.cmpr('foo.bar', '~=', 'foo.bar.x'))
        self.true(await taxo.cmpr('foo.bar.baz', '~=', 'bar'))
        self.true(await taxo.cmpr('foo.bar.baz', '~=', '[a-z].bar.[a-z]'))
        self.true(await taxo.cmpr('foo.bar.baz', '~=', r'^foo\.[a-z]+\.baz$'))
        self.true(await taxo.cmpr('foo.bar.baz', '~=', r'\.baz$'))
        self.true(await taxo.cmpr('bar.foo.baz', '~=', 'foo.'))
        self.false(await taxo.cmpr('bar.foo.baz', '~=', r'^foo\.'))
        self.true(await taxo.cmpr('foo.bar.xbazx', '~=', r'\.bar\.'))
        self.true(await taxo.cmpr('foo.bar.xbazx', '~=', '.baz.'))
        self.false(await taxo.cmpr('foo.bar.xbazx', '~=', r'\.baz\.'))

        async with self.getTestCore() as core:
            nodes = await core.nodes('[test:taxonomy=foo.bar.baz :name="title words" :desc="a test taxonomy" :sort=1 ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('test:taxonomy', 'foo.bar.baz.'))
            self.propeq(node, 'name', 'title words')
            self.propeq(node, 'desc', 'a test taxonomy')
            self.propeq(node, 'sort', 1)
            self.propeq(node, 'base', 'baz')
            self.propeq(node, 'depth', 2)
            self.propeq(node, 'parent', 'foo.bar.')

            self.sorteq(
                ['foo.', 'foo.bar.', 'foo.bar.baz.'],
                [n.ndef[1] for n in await core.nodes('test:taxonomy')]
            )

            self.len(0, await core.nodes('test:taxonomy=foo.bar.ba'))
            self.len(1, await core.nodes('test:taxonomy=foo.bar.baz'))
            self.len(1, await core.nodes('test:taxonomy=foo.bar.baz.'))

            self.len(0, await core.nodes('test:taxonomy=(foo, bar, ba)'))
            self.len(1, await core.nodes('test:taxonomy=(foo, bar, baz)'))

            self.len(3, await core.nodes('test:taxonomy^=f'))
            self.len(0, await core.nodes('test:taxonomy^=f.'))
            self.len(2, await core.nodes('test:taxonomy^=foo.b'))
            self.len(0, await core.nodes('test:taxonomy^=foo.b.'))
            self.len(2, await core.nodes('test:taxonomy^=foo.bar'))
            self.len(2, await core.nodes('test:taxonomy^=foo.bar.'))
            self.len(1, await core.nodes('test:taxonomy^=foo.bar.b'))
            self.len(1, await core.nodes('test:taxonomy^=foo.bar.baz'))
            self.len(1, await core.nodes('test:taxonomy^=foo.bar.baz.'))

            self.len(0, await core.nodes('test:taxonomy^=(f,)'))
            self.len(0, await core.nodes('test:taxonomy^=(foo, b)'))
            self.len(2, await core.nodes('test:taxonomy^=(foo, bar)'))
            self.len(1, await core.nodes('test:taxonomy^=(foo, bar, baz)'))

            # just test one conditional since RelPropCond and
            # AbsPropCond (for form and prop) use the same logic
            self.len(1, await core.nodes('test:taxonomy:sort=1 +:parent^=f'))
            self.len(0, await core.nodes('test:taxonomy:sort=1 +:parent^=f.'))
            self.len(1, await core.nodes('test:taxonomy:sort=1 +:parent^=foo.b'))
            self.len(0, await core.nodes('test:taxonomy:sort=1 +:parent^=foo.b.'))
            self.len(1, await core.nodes('test:taxonomy:sort=1 +:parent^=foo.bar'))
            self.len(1, await core.nodes('test:taxonomy:sort=1 +:parent^=foo.bar.'))

            self.len(0, await core.nodes('test:taxonomy:sort=1 +:parent^=(f,)'))
            self.len(0, await core.nodes('test:taxonomy:sort=1 +:parent^=(foo, b)'))
            self.len(1, await core.nodes('test:taxonomy:sort=1 +:parent^=(foo, bar)'))

    async def test_duration(self):
        model = s_datamodel.getBaseModel()
        t = model.type('duration')

        self.eq('2D 00:00:00', t.repr(172800000000))
        self.eq('00:05:00.333333', t.repr(300333333))
        self.eq('11D 11:47:12.344', t.repr(992832344000))
        self.eq('?', t.repr(t.unkdura))
        self.eq('*', t.repr(t.futdura))

        self.eq(300333333, (await t.norm('00:05:00.333333'))[0])
        self.eq(992832344000, (await t.norm('11D 11:47:12.344'))[0])

        self.eq(172800000000, (await t.norm('2D'))[0])
        self.eq(60000000, (await t.norm('1:00'))[0])
        self.eq(60200000, (await t.norm('1:00.2'))[0])
        self.eq(9999999, (await t.norm('9.9999999'))[0])

        with self.raises(s_exc.BadTypeValu):
            await t.norm('    ')

        with self.raises(s_exc.BadTypeValu):
            await t.norm('1:2:3:4')

        with self.raises(s_exc.BadTypeValu):
            await t.norm('1:a:b')

        # the precision opt floors a duration to the given resolution
        secs = t.clone({'precision': 'second'})
        self.eq(300000000, (await secs.norm('300'))[0])
        self.eq(1000000, (await secs.norm('1.5'))[0])
        self.eq(0, (await secs.norm(300000))[0])
        self.eq(60000000, (await secs.norm(60000000))[0])
        self.eq(secs.unkdura, (await secs.norm('?'))[0])
        self.eq(secs.futdura, (await secs.norm('*'))[0])

        with self.raises(s_exc.BadTypeDef):
            t.clone({'precision': 'fortnight'})

    async def test_type_expr_funcs(self):
        model = s_datamodel.getBaseModel()

        time = model.type('time')
        dura = model.type('duration')

        # registry lookups
        self.none(time.getExprFunc('+', 'time'))
        self.nn(time.getExprFunc('-', 'time'))
        self.nn(time.getExprFunc('+', 'duration'))
        self.nn(time.getExprFunc('-', 'duration'))
        self.nn(dura.getExprFunc('+', 'duration'))
        self.nn(dura.getExprFunc('-', 'duration'))
        self.nn(dura.getExprFunc('+', 'time'))
        self.nn(dura.getExprFunc('*', 'int'))

        # reverse handlers live in a separate registry
        self.nn(dura.getExprFunc('*', 'int', reverse=True))
        self.none(dura.getExprFunc('+', 'duration', reverse=True))
        self.none(time.getExprFunc('-', 'time', reverse=True))

        # handlers return (typename, value) ndef tuples
        self.eq(('duration', 5), await time.getExprFunc('-', 'time')(10, 5))
        self.eq(('time', 15), await time.getExprFunc('+', 'duration')(10, 5))
        self.eq(('time', 5), await time.getExprFunc('-', 'duration')(10, 5))
        self.eq(('duration', 15), await dura.getExprFunc('+', 'duration')(10, 5))
        self.eq(('duration', 5), await dura.getExprFunc('-', 'duration')(10, 5))
        self.eq(('time', 15), await dura.getExprFunc('+', 'time')(10, 5))
        self.eq(('duration', 30), await dura.getExprFunc('*', 'int')(10, 3))
        self.eq(('duration', 30), await dura.getExprFunc('*', 'int', reverse=True)(10, 3))

        # custom registration round-trips and overrides
        async def _custom(valu, othr):
            return ('int', valu)

        time.setExprFunc('+', 'newp', _custom)
        self.eq(_custom, time.getExprFunc('+', 'newp'))
        self.eq(('int', 10), await time.getExprFunc('+', 'newp')(10, 5))

        # reverse registration is independent of the forward registry
        self.none(time.getExprFunc('+', 'newp', reverse=True))
        time.setExprFunc('+', 'newp', _custom, reverse=True)
        self.eq(_custom, time.getExprFunc('+', 'newp', reverse=True))
        self.none(time.getExprFunc('+', 'newp2'))

    async def test_bool(self):
        model = s_datamodel.getBaseModel()
        t = model.type('bool')

        self.eq(await t.norm(-1), (1, {}))
        self.eq(await t.norm(0), (0, {}))
        self.eq(await t.norm(1), (1, {}))
        self.eq(await t.norm(2), (1, {}))
        self.eq(await t.norm(True), (1, {}))
        self.eq(await t.norm(False), (0, {}))

        self.eq(await t.norm('-1'), (1, {}))
        self.eq(await t.norm('0'), (0, {}))
        self.eq(await t.norm('1'), (1, {}))

        self.eq(await t.norm(s_stormtypes.Number('1')), (1, {}))
        self.eq(await t.norm(s_stormtypes.Number('0')), (0, {}))

        for s in ('trUe', 'T', 'y', ' YES', 'On '):
            self.eq(await t.norm(s), (1, {}))

        for s in ('faLSe', 'F', 'n', 'NO', 'Off '):
            self.eq(await t.norm(s), (0, {}))

        with self.raises(s_exc.BadTypeValu):
            await t.norm('a')

        self.eq(t.repr(1), 'true')
        self.eq(t.repr(0), 'false')

    async def test_comp(self):
        async with self.getTestCore() as core:
            t = 'test:complexcomp'
            valu = ('123', 'HAHA')
            nodes = await core.nodes('[test:complexcomp=(123, HAHA)]')
            self.len(1, nodes)
            node = nodes[0]
            pnode = node.pack(dorepr=True)
            self.eq(pnode[0], (t, (123, 'haha')))
            self.eq(pnode[1].get('repr'), ('123', 'haha'))
            self.eq(pnode[1].get('reprs').get('foo'), '123')
            self.notin('bar', pnode[1].get('reprs'))
            self.propeq(node, 'foo', 123)
            self.propeq(node, 'bar', 'haha')

            typ = core.model.type(t)
            self.eq(typ.info.get('bases'), ('base', 'comp'))

            with self.raises(s_exc.BadTypeValu):
                await typ.norm((123, 'haha', 'newp'))

    async def test_data(self):
        async with self.getTestCore() as core:
            raw = {'foo': 'bar', 'lol': 12}
            opts = {'vars': {'raw': raw}}
            nodes = await core.nodes('[test:guid=* :raw=$raw]', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'raw', raw)

            nodes = await core.nodes('test:guid:raw=$raw', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'raw', raw)

    async def test_guid(self):
        model = s_datamodel.getBaseModel()

        guid = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        self.eq(guid.lower(), (await model.type('guid').norm(guid))[0])
        with self.raises(s_exc.BadTypeValu):
            await model.type('guid').norm('visi')

        guid = (await model.type('guid').norm('*'))[0]
        self.true(s_common.isguid(guid))

        objs = [1, 2, 'three', {'four': 5}]
        tobjs = tuple(objs)
        lnorm, _ = await model.type('guid').norm(objs)
        tnorm, _ = await model.type('guid').norm(tobjs)
        self.true(s_common.isguid(lnorm))
        self.eq(lnorm, tnorm)

        with self.raises(s_exc.BadTypeValu) as exc:
            await model.type('guid').norm(())
        self.eq(exc.exception.get('name'), 'guid')
        self.eq(exc.exception.get('valu'), ())
        self.eq(exc.exception.get('mesg'), 'Guid list values cannot be empty.')

        async with self.getTestCore() as core:

            nodes00 = await core.nodes('[ ou:org=({"name": "vertex"}) ]')
            self.len(1, nodes00)
            self.propeq(nodes00[0], 'name', 'vertex')

            nodes01 = await core.nodes('[ ou:org=({"name": "vertex"}) :names+="the vertex project"]')
            self.len(1, nodes01)
            self.propeq(nodes01[0], 'name', 'vertex')
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes02 = await core.nodes('[ ou:org=({"name": "the vertex project"}) ]')
            self.len(1, nodes02)
            self.propeq(nodes02[0], 'name', 'vertex')
            self.eq(nodes01[0].ndef, nodes02[0].ndef)

            nodes03 = await core.nodes('[ ou:org=({"name": "vertex", "type": "woot"}) :names+="the vertex project" ]')
            self.len(1, nodes03)
            self.ne(nodes02[0].ndef, nodes03[0].ndef)

            nodes04 = await core.nodes('[ ou:org=({"name": "the vertex project", "type": "woot"}) ]')
            self.len(1, nodes04)
            self.eq(nodes03[0].ndef, nodes04[0].ndef)

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ ou:org=({"email": "woot"}) ]')

            nodes05 = await core.nodes('[ ou:org=({"name": "vertex", "$props": {"motto": "for the people"}}) ]')
            self.len(1, nodes05)
            self.propeq(nodes05[0], 'name', 'vertex')
            self.propeq(nodes05[0], 'motto', 'for the people')
            self.eq(nodes00[0].ndef, nodes05[0].ndef)

            nodes06 = await core.nodes('[ ou:org=({"name": "acme", "$props": {"motto": "HURR DURR"}}) ]')
            self.len(1, nodes06)
            self.propeq(nodes06[0], 'name', 'acme')
            self.propeq(nodes06[0], 'motto', 'HURR DURR')
            self.ne(nodes00[0].ndef, nodes06[0].ndef)

            nodes07 = await core.nodes('[ ou:org=({"name": "goal driven", "emails": ["foo@vertex.link", "bar@vertex.link"]}) ]')
            self.len(1, nodes07)
            self.propeq(nodes07[0], 'emails', ('bar@vertex.link', 'foo@vertex.link'))

            nodes08 = await core.nodes('[ ou:org=({"name": "goal driven", "emails": ["bar@vertex.link", "foo@vertex.link"]}) ]')
            self.len(1, nodes08)
            self.propeq(nodes08[0], 'emails', ('bar@vertex.link', 'foo@vertex.link'))
            self.eq(nodes07[0].ndef, nodes08[0].ndef)

            nodes09 = await core.nodes('[ ou:org=({"name": "vertex"}) :name=foobar :names=() ]')
            nodes10 = await core.nodes('[ ou:org=({"name": "vertex"}) :type=lulz ]')
            self.len(1, nodes09)
            self.len(1, nodes10)
            self.ne(nodes09[0].ndef, nodes10[0].ndef)

            await core.nodes('[ ou:org=* :type=lulz ]')
            await core.nodes('[ ou:org=* :type=hehe ]')
            nodes11 = await core.nodes('[ ou:org=({"name": "vertex", "$props": {"type": "lulz"}}) ]')
            self.len(1, nodes11)

            nodes12 = await core.nodes('[ ou:org=({"name": "vertex", "type": "hehe"}) ]')
            self.len(1, nodes12)
            self.ne(nodes11[0].ndef, nodes12[0].ndef)

            # GUID ctor has a short-circuit where it tries to find an existing ndef before it does,
            # some property deconfliction, and `<form>=({})` when pushed through guid generation gives
            # back the same guid as `<form>=()`, which if we're not careful could lead to an
            # inconsistent case where you fail to make a node because you don't provide any props,
            # make a node with that matching ndef, and then run that invalid GUID ctor query again,
            # and have it return back a node due to the short circuit. So test that we're consistent here.
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ ou:org=({}) ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ ou:org=() ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ ou:org=({}) ]')

            msgs = await core.stormlist('[ ou:org=({"$props": {"desc": "lol"}})]')
            self.len(0, [m for m in msgs if m[0] == 'node'])
            self.stormIsInErr('No values provided for form ou:org', msgs)

            msgs = await core.stormlist('[ou:org=({"name": "burrito corp", "$props": {"phone": "lolnope"}})]')
            self.len(0, [m for m in msgs if m[0] == 'node'])
            self.stormIsInErr('Bad value for prop ou:org:phone: requires a digit string', msgs)

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ ou:org=({"$try": true}) ]')

            # $try can be used at top level, currently only applies to $props
            nodes = await core.nodes('[ou:org=({"name": "burrito corp", "$try": true, "$props": {"phone": "lolnope", "desc": "burritos man"}})]')
            self.len(1, nodes)
            self.none(nodes[0].get('phone'))
            self.propeq(nodes[0], 'name', 'burrito corp')
            self.propeq(nodes[0], 'desc', 'burritos man')

            # $try can also be specified in $props which overrides top level $try
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ou:org=({"name": "burrito corp", "$try": true, "$props": {"$try": false, "phone": "lolnope"}})]')

            await self.asyncraises(s_exc.BadTypeValu, core.nodes("$lib.view.get().addNode(ou:org, ({'name': 'org name 77', 'phone': 'lolnope'}), props=({'desc': 'an org desc'}))"))

            await self.asyncraises(s_exc.BadTypeValu, core.nodes("$lib.view.get().addNode(ou:org, ({'name': 'org name 77'}), props=({'desc': 'an org desc', 'phone': 'lolnope'}))"))

            nodes = await core.nodes("yield $lib.view.get().addNode(ou:org, ({'$try': true, '$props': {'phone': 'invalid'}, 'name': 'org name 77'}), props=({'desc': 'an org desc'}))")
            self.len(1, nodes)
            node = nodes[0]
            self.none(node.get('phone'))
            self.propeq(node, 'name', 'org name 77')
            self.propeq(node, 'desc', 'an org desc')

            nodes = await core.nodes('ou:org=({"name": "the vertex project", "type": "lulz"})')
            self.len(1, nodes)
            orgn = nodes[0].ndef
            self.eq(orgn, nodes11[0].ndef)

            q = '[ entity:contact=* :resolved={ ou:org=({"name": "the vertex project", "type": "lulz"}) } ]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            cont = nodes[0]
            self.eq(cont.get('resolved'), orgn)

            nodes = await core.nodes('entity:contact:resolved={[ ou:org=({"name": "the vertex project", "type": "lulz"})]}')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, cont.ndef)

            self.len(0, await core.nodes('entity:contact:resolved={[ ou:org=({"name": "vertex", "type": "newp"}) ]}'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:guid:iden=({"name": "vertex", "type": "newp"})')

            await core.nodes('[ ou:org=({"name": "origname"}) ]')
            self.len(1, await core.nodes('ou:org=({"name": "origname"}) [ :name=newname ]'))
            self.len(0, await core.nodes('ou:org=({"name": "origname"})'))

            nodes = await core.nodes('[ it:exec:proc=(notime,) ]')
            self.len(1, nodes)

            nodes = await core.nodes('[ it:exec:proc=(nulltime,) ]')
            self.len(1, nodes)

            # Recursive gutors
            nodes = await core.nodes('''[
                inet:service:message=({
                    'id': 'foomesg',
                    'platform': {
                        '$as': 'inet:service:platform',
                        'name': 'fooplatform',
                        'url': 'http://foo.com',
                        'software': {
                            '$as': 'it:software',
                            'name': 'foosoft'
                        }
                    }
                })
            ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[0], 'inet:service:message')
            self.propeq(node, 'id', 'foomesg')
            self.nn(node.get('platform'))

            nodes = await core.nodes('inet:service:message -> inet:service:platform')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'name', 'fooplatform')
            self.propeq(node, 'url', 'http://foo.com')
            self.nn(node.get('software'))

            nodes = await core.nodes('inet:service:message -> inet:service:platform -> it:software')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'name', 'foosoft')

            nodes = await core.nodes('''
                inet:service:message=({
                    'id': 'foomesg',
                    'platform': {
                        '$as': 'inet:service:platform',
                        'name': 'fooplatform',
                        'url': 'http://foo.com',
                        'software': {
                            '$as': 'it:software',
                            'name': 'foosoft'
                        }
                    }
                })
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[0], 'inet:service:message')
            self.propeq(node, 'id', 'foomesg')

            nodes = await core.nodes('''[
                inet:service:message=({
                    'id': 'barmesg',
                    '$props': {
                        'platform': {
                            '$as': 'inet:service:platform',
                            'name': 'barplatform',
                            'url': 'http://bar.com'
                        }
                    }
                })
            ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[0], 'inet:service:message')
            self.propeq(node, 'id', 'barmesg')

            platguid = node.get('platform')[1]
            self.nn(platguid)
            nodes = await core.nodes('inet:service:message:id=barmesg -> inet:service:platform')
            self.len(1, nodes)
            self.eq(platguid, nodes[0].ndef[1])

            # No node lifted if no matching node for inner gutor
            self.len(0, await core.nodes('''
                inet:service:message=({
                    'id': 'foomesg',
                    'platform': {
                        '$as': 'inet:service:platform',
                        'name': 'newp',
                        'url': 'http://foo.com'
                    }
                })
            '''))

            # BadTypeValu comes through from inner gutor
            with self.raises(s_exc.BadTypeValu) as cm:
                await core.nodes('''
                    inet:service:message=({
                        'id': 'foomesg',
                        'platform': {
                            '$as': 'inet:service:platform',
                            'name': 'newp',
                            'url': 'newp'
                        }
                    })
                ''')

            self.eq(cm.exception.get('form'), 'inet:service:platform')
            self.eq(cm.exception.get('prop'), 'url')
            self.eq(cm.exception.get('mesg'), 'Bad value for prop inet:service:platform:url: Invalid/Missing protocol')

            # Ensure inner nodes are not created unless the entire gutor is valid.
            self.len(0, await core.nodes('''[
                inet:service:account?=({
                    "id": "bar",
                    "platform": {"$as": "inet:service:platform", "name": "barplat"},
                    "url": "newp"})
            ]'''))

            self.len(0, await core.nodes('inet:service:platform:name=barplat'))

            # Gutors work for props
            nodes = await core.nodes('''[
                test:str=guidprop
                    :gprop=({'$as': 'test:guid', 'name': 'someprop', '$props': {'size': 5}})
            ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('test:str', 'guidprop'))
            self.nn(node.get('gprop'))

            nodes = await core.nodes('test:str=guidprop -> test:guid')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'name', 'someprop')
            self.propeq(node, 'size', 5)

            with self.raises(s_exc.BadTypeValu) as cm:
                nodes = await core.nodes('''[
                    test:str=newpprop
                        :gprop=({'$as': 'test:guid', 'size': 'newp'})
                ]''')

            self.eq(cm.exception.get('form'), 'test:guid')
            self.eq(cm.exception.get('prop'), 'size')
            self.true(cm.exception.get('mesg').startswith('Bad value for prop test:guid:size: invalid literal'))

            nodes = await core.nodes('''[
                test:str=newpprop
                    :gprop?=({'$as': 'test:guid', 'size': 'newp'})
            ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('test:str', 'newpprop'))
            self.none(node.get('gprop'))

            nodes = await core.nodes('''
                [ test:str=methset ]
                $node.props.gprop = ({'$as': 'test:guid', 'name': 'someprop'})
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('test:str', 'methset'))
            self.nn(node.get('gprop'))

            nodes = await core.nodes('test:str=methset -> test:guid')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'name', 'someprop')
            self.propeq(node, 'size', 5)

            opts = {'vars': {'sha256': 'a01f2460fec1868757aa9194b5043b4dd9992de0f6b932137f36506bd92d9d88'}}
            nodes = await core.nodes('''[ it:app:yara:matched=* :target={[ file:bytes=({"sha256": $sha256}) ]} ]''', opts=opts)
            self.len(1, nodes)

            nodes = await core.nodes('it:app:yara:matched -> *')
            self.len(1, nodes)
            self.propeq(nodes[0], 'sha256', opts['vars']['sha256'])

            nodes = await core.nodes('$chan = {[inet:service:channel=*]} [ inet:service:rule=({"id":"foo", "object": $chan}) ]')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'id', 'foo')
            self.nn(node.get('object'))

            self.len(1, await core.nodes('inet:service:rule :object -> *'))

            # $salt affects the initial guid computation
            salt00 = await core.nodes('[ ou:org=({"name": "saltyorg", "$salt": "salt1"}) ]')
            self.len(1, salt00)
            self.propeq(salt00[0], 'name', 'saltyorg')

            # Same salt and props produces the same guid
            salt01 = await core.nodes('[ ou:org=({"name": "saltyorg", "$salt": "salt1"}) ]')
            self.len(1, salt01)
            self.eq(salt00[0].ndef, salt01[0].ndef)

            # Different salt produces a different initial guid
            nosalt = s_common.guid([('name', ('entity:name', 'saltyorg'))])
            salted = s_common.guid([('name', ('entity:name', 'saltyorg')), ('$salt', 'salt1')])
            self.ne(nosalt, salted)
            self.eq(salt00[0].ndef[1], salted)

            # Deconfliction still finds an existing node with matching props
            salt02 = await core.nodes('[ ou:org=({"name": "saltyorg", "$salt": "othersalt"}) ]')
            self.len(1, salt02)
            self.eq(salt00[0].ndef, salt02[0].ndef)

            # $salt works with $props
            salt03 = await core.nodes('[ ou:org=({"name": "saltyorg", "$salt": "salt1", "$props": {"desc": "a salted org"}}) ]')
            self.len(1, salt03)
            self.eq(salt00[0].ndef, salt03[0].ndef)
            self.propeq(salt03[0], 'desc', 'a salted org')

            # $salt is not stored as a property
            self.none(salt00[0].get('$salt'))

            # $unsets: new node -- constraint trivially satisfied, prop is absent
            nodes = await core.nodes('[ ou:org=({"name": "unsetorg", "$unsets": ["desc"]}) ]')
            self.len(1, nodes)
            self.none(nodes[0].get('desc'))
            self.propeq(nodes[0], 'name', 'unsetorg')

            # $unsets: prop name as Storm variable -- tostor converts Storm Str to Python str
            nodes = await core.nodes('$p = "desc" [ ou:org=({"name": "unsetorg-var", "$unsets": [$p]}) ]')
            self.len(1, nodes)
            self.none(nodes[0].get('desc'))

            # $unsets: existing node, named prop is absent -- constraint satisfied, node returned unchanged
            nodes = await core.nodes('[ ou:org=({"name": "unsetorg", "$unsets": ["phone"]}) ]')
            self.len(1, nodes)
            self.none(nodes[0].get('phone'))

            # $unsets: empty list is a no-op
            nodes = await core.nodes('[ ou:org=({"name": "unsetorg", "$unsets": []}) ]')
            self.len(1, nodes)

            # $unsets: existing node, named prop IS set -- no deconf match, creates a new node
            await core.nodes('[ou:org=({"name": "unsetorg2", "$props": {"desc": "present"}})]')
            nodes = await core.nodes('[ou:org=({"name": "unsetorg2", "$unsets": ["desc"]})]')
            self.len(1, nodes)
            self.none(nodes[0].get('desc'))
            # two distinct ou:org nodes now share name="unsetorg2"
            all_nodes = await core.nodes('ou:org:name="unsetorg2"')
            self.len(2, all_nodes)

            # $unsets: same gutor again finds the node without desc (consistent re-resolution)
            nodes = await core.nodes('[ou:org=({"name": "unsetorg2", "$unsets": ["desc"]})]')
            self.len(1, nodes)
            self.none(nodes[0].get('desc'))

            # $unsets: $props sets a different prop, $unsets checks absence of another (no overlap)
            await core.nodes('[ou:org=({"name": "unsetorg3", "$props": {"desc": "ok"}})]')
            nodes = await core.nodes('[ou:org=({"name": "unsetorg3", "$props": {"desc": "ok"}, "$unsets": ["phone"]})]')
            self.len(1, nodes)
            self.none(nodes[0].get('phone'))

            # $unsets: value must be a list/tuple
            msgs = await core.stormlist('[ ou:org=({"name": "unsetorg", "$unsets": "desc"}) ]')
            self.stormIsInErr('$unsets must be a list of property name strings', msgs)

            # $unsets: list must contain strings
            msgs = await core.stormlist('[ ou:org=({"name": "unsetorg", "$unsets": [42]}) ]')
            self.stormIsInErr('$unsets must be a list of property name strings', msgs)

            # $unsets: unknown prop raises NoSuchProp
            msgs = await core.stormlist('[ ou:org=({"name": "unsetorg", "$unsets": ["newp"]}) ]')
            self.stormIsInErr('No property named', msgs)

            # $unsets: overlap with deconf key raises BadTypeValu
            msgs = await core.stormlist('[ ou:org=({"name": "unsetorg", "$unsets": ["name"]}) ]')
            self.stormIsInErr("Cannot specify 'name' in $unsets", msgs)

            # $unsets: overlap with $props raises BadTypeValu
            msgs = await core.stormlist('[ ou:org=({"name": "unsetorg", "$props": {"desc": "x"}, "$unsets": ["desc"]}) ]')
            self.stormIsInErr("Cannot specify 'desc' in $unsets", msgs)

            # $unsets: $try: true does NOT suppress NoSuchProp
            msgs = await core.stormlist('[ ou:org=({"name": "unsetorg", "$try": true, "$unsets": ["newp"]}) ]')
            self.stormIsInErr('No property named', msgs)

            # $unsets: nested gutor -- inner node prop is absent, constraint satisfied
            await core.nodes('[inet:service:platform=({"name": "unsetplat-ok"})]')
            nodes = await core.nodes('''[
                inet:service:message=({
                    "id": "unsetmsgnested-ok",
                    "$props": {
                        "platform": {
                            "$as": "inet:service:platform",
                            "name": "unsetplat-ok",
                            "$unsets": ["url"]
                        }
                    }
                })
            ]''')
            self.len(1, nodes)
            plats = await core.nodes('inet:service:message:id=unsetmsgnested-ok -> inet:service:platform')
            self.len(1, plats)
            self.none(plats[0].get('url'))

            # $unsets: nested gutor -- inner node has prop set, no match, resolves to new inner node
            await core.nodes('[inet:service:platform=({"name": "unsetplat-bad", "$props": {"url": "http://set.com"}})]')
            nodes = await core.nodes('''[
                inet:service:message=({
                    "id": "unsetmsgnested-bad",
                    "$props": {
                        "platform": {
                            "$as": "inet:service:platform",
                            "name": "unsetplat-bad",
                            "$unsets": ["url"]
                        }
                    }
                })
            ]''')
            self.len(1, nodes)
            plats = await core.nodes('inet:service:message:id=unsetmsgnested-bad -> inet:service:platform')
            self.len(1, plats)
            self.none(plats[0].get('url'))

            # $unsets: works via $lib.view.get().addNode() -- constraint satisfied (prop absent)
            nodes = await core.nodes("yield $lib.view.get().addNode(ou:org, ({'name': 'viewaddorg', '$unsets': ['desc']}))")
            self.len(1, nodes)
            self.none(nodes[0].get('desc'))

            # embed queries can be used as values
            nodes = await core.nodes('[ test:guid=({"name": ${[ test:str=embedq ]} })]')
            self.len(1, nodes)
            self.eq('test:guid', nodes[0].ndef[0])
            self.propeq(nodes[0], 'name', 'embedq', type='test:str')
            self.len(1, await core.nodes('test:str=embedq'))

            # embed query can be used in $props
            nodes = await core.nodes('''[
                test:guid=({
                    "name": "propsq",
                    "$props": {"size": ${[ test:int=42 ]}}
                })
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'size', 42, type='test:int')
            self.len(1, await core.nodes('test:int=42'))

            # embed query for an array prop can yield multiple nodes
            nodes = await core.nodes('[ test:arrayprop=({"strs": ${[ test:str=arr1 test:str=arr2 ]} })]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'strs', ('arr1', 'arr2'))

            # embed query with a return statement
            nodes = await core.nodes('[ test:guid=({"name": ${ [test:str=retq] return($node) }} )]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'name', 'retq', type='test:str')
            self.len(1, await core.nodes('test:str=retq'))

            # a non-array prop requires exactly one yielded node
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ test:guid=({"name": ${[ test:str=multi1 test:str=multi2 ]} })]')

            # zero yielded nodes resolves to None and fails to norm
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ test:guid=({"name": ${ test:str=nope }})]')

            # ?= suppresses the bad-type-valu from the embed query resolution
            nodes = await core.nodes('[ test:guid?=({"name": ${ test:str=nope }})]')
            self.len(0, nodes)

            # embed query handling works for all types
            nodes = await core.nodes('[ test:str=polysrc :poly=${[ test:int=5 ]} ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'poly', 5, type='test:int')
            self.len(1, await core.nodes('test:int=5'))

            # works on arrays as well
            nodes = await core.nodes('[ test:str=polyarrsrc :polyarry=${[ test:int=7 test:int=8 ]} ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'polyarry', (7, 8))
            self.eq({'test:int'}, {item[0] for item in nodes[0].get('polyarry')})

            # the data type stores the query text rather than executing the query
            nodes = await core.nodes('[ test:data=${[ test:str=dataq ]} ]')
            self.len(1, nodes)
            self.isin('test:str=dataq', nodes[0].ndef[1])
            self.len(0, await core.nodes('test:str=dataq'))

            # $as: a poly prop that resolves to many forms (entity:actor) has no
            # default type, so a dictionary guid constructor must name the form
            # to build via $as.
            msgs = await core.stormlist('[ meta:note=* :creator=({"name": "bob smith"}) ]')
            self.stormIsInErr('requires a "$as" key naming the form to construct', msgs)

            nodes = await core.nodes('[ meta:note=* :creator=({"$as": "ps:person", "name": "bob smith"}) ]')
            self.len(1, nodes)
            creator = nodes[0].get('creator')
            self.eq('ps:person', creator[0])
            people = await core.nodes('meta:note:creator -> ps:person')
            self.len(1, people)
            self.propeq(people[0], 'name', 'bob smith', type='entity:name')

            # $as: the same constructor deconflicts to the same node
            nodes = await core.nodes('[ meta:note=* :creator=({"$as": "ps:person", "name": "bob smith"}) ]')
            self.eq(creator, nodes[0].get('creator'))

            # $as: naming a different (allowed) form builds a distinct typed node
            nodes = await core.nodes('[ meta:note=* :creator=({"$as": "entity:contact", "name": "bob smith"}) ]')
            self.eq('entity:contact', nodes[0].get('creator')[0])
            self.ne(creator, nodes[0].get('creator'))

            # $as: a guid form not allowed by the poly raises BadTypeValu...
            msgs = await core.stormlist('[ meta:note=* :creator=({"$as": "inet:service:message", "id": "m1"}) ]')
            self.stormIsInErr('is not allowed for', msgs)

            # ...and $try / ?= suppress it
            nodes = await core.nodes('[ meta:note=* :creator?=({"$as": "inet:service:message", "id": "m1"}) ]')
            self.len(1, nodes)
            self.none(nodes[0].get('creator'))

            # $as: value must be a form name string
            msgs = await core.stormlist('[ meta:note=* :creator=({"$as": 42, "name": "x"}) ]')
            self.stormIsInErr('"$as" must be a form name string', msgs)

            # $as: value must name a guid form (inet:fqdn is a form but not a guid)
            msgs = await core.stormlist('[ meta:note=* :creator=({"$as": "inet:fqdn", "name": "x"}) ]')
            self.stormIsInErr('"$as" value inet:fqdn is not a guid form', msgs)

            # $as: on a single-default poly prop the form may be named explicitly
            nodes = await core.nodes('[ inet:service:message=* :to=({"$as": "inet:service:account", "id": "acct1"}) ]')
            self.len(1, nodes)
            self.eq('inet:service:account', nodes[0].get('to')[0])

            # $as: at the top level the constructed form must match the form being built
            nodes = await core.nodes('[ ou:org=({"$as": "ou:org", "name": "vertex via as"}) ]')
            self.len(1, nodes)
            self.eq('ou:org', nodes[0].ndef[0])
            self.propeq(nodes[0], 'name', 'vertex via as')

            msgs = await core.stormlist('[ ou:org=({"$as": "ps:person", "name": "nope"}) ]')
            self.stormIsInErr('does not match the form ou:org being constructed', msgs)

            # $as: at the top level it must also be a form name string
            msgs = await core.stormlist('[ ou:org=({"$as": 42, "name": "nope"}) ]')
            self.stormIsInErr('"$as" must be a form name string for form ou:org', msgs)

            # $as: works via $lib.view.get().addNode()
            nodes = await core.nodes('yield $lib.view.get().addNode(meta:note, ({"text": "added via as", "$props": {"creator": {"$as": "ps:person", "name": "added via as"}}}))')
            self.len(1, nodes)
            self.eq('ps:person', nodes[0].get('creator')[0])

            # $as: each element of a poly array may name its own form
            nodes = await core.nodes('''[ entity:conflict=* :adversaries=(
                ({"$as": "ps:person", "name": "alice"}),
                ({"$as": "ou:org", "name": "acme"})
            ) ]''')
            self.len(1, nodes)
            self.eq(('ou:org', 'ps:person'), tuple(sorted(a[0] for a in nodes[0].get('adversaries'))))
            self.len(1, await core.nodes('entity:conflict -> ps:person +:name="alice"'))
            self.len(1, await core.nodes('entity:conflict -> ou:org +:name="acme"'))

            # $as: a disallowed form on a poly value nested in $props is skipped
            # under $try rather than raising
            nodes = await core.nodes('''[
                meta:note=({
                    "text": "tryskip note",
                    "$try": true,
                    "$props": {"creator": {"$as": "inet:service:message", "id": "m1"}}
                })
            ]''')
            self.len(1, nodes)
            self.none(nodes[0].get('creator'))

            # ...while without $try the same disallowed form raises
            msgs = await core.stormlist('''[
                meta:note=({
                    "text": "tryskip note2",
                    "$props": {"creator": {"$as": "inet:service:message", "id": "m1"}}
                })
            ]''')
            self.stormIsInErr('is not allowed for', msgs)

            # --- virtual prop keys in gutor dicts ---
            ityp = core.model.type('ival')

            # ival min-only in deconfliction portion: creates an open-ended ival
            nodes_v00 = await core.nodes('[ test:guid=({"name": "ival-virt", "seen.min": "2020"}) ]')
            self.len(1, nodes_v00)
            self.propeq(nodes_v00[0], 'name', 'ival-virt')
            # propeq unwraps poly-wrapped ival to compare raw (min, max, dur) tuple
            self.propeq(nodes_v00[0], 'seen', (1577836800000000, ityp.unksize, ityp.duratype.unkdura))

            # same dict deconflicts to the same node
            nodes_v01 = await core.nodes('[ test:guid=({"name": "ival-virt", "seen.min": "2020"}) ]')
            self.len(1, nodes_v01)
            self.eq(nodes_v00[0].ndef, nodes_v01[0].ndef)

            # different seen.min produces a different node (virt participates in deconfliction)
            nodes_v02 = await core.nodes('[ test:guid=({"name": "ival-virt", "seen.min": "2021"}) ]')
            self.len(1, nodes_v02)
            self.ne(nodes_v00[0].ndef, nodes_v02[0].ndef)

            # min+max: virtlist is threaded in order to form a bounded ival
            nodes_v03 = await core.nodes('[ test:guid=({"name": "ival-bounded", "seen.min": "2020", "seen.max": "2021"}) ]')
            self.len(1, nodes_v03)
            self.propeq(nodes_v03[0], 'seen', (1577836800000000, 1609459200000000, 1609459200000000 - 1577836800000000))

            # same dict deconflicts to the same node
            nodes_v04 = await core.nodes('[ test:guid=({"name": "ival-bounded", "seen.min": "2020", "seen.max": "2021"}) ]')
            self.len(1, nodes_v04)
            self.eq(nodes_v03[0].ndef, nodes_v04[0].ndef)

            # min+max+duration: over-constrained raises BadTypeValu
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ test:guid=({"name": "ival-overcon", "seen.min": "2020", "seen.max": "2021", "seen.duration": "1D"}) ]')

            # unknown dotted key that matches no virt name raises NoSuchVirt
            msgs = await core.stormlist('[ test:guid=({"name": "ival-novirt", "seen.newp": "2020"}) ]')
            self.stormIsInErr('No editable virtual prop named', msgs)

            # dotted key whose base is not a real prop is treated as a plain prop
            # name (not a virt reference) and raises NoSuchProp
            msgs = await core.stormlist('[ test:guid=({"name": "ival-nobase", "newp.min": "2020"}) ]')
            self.stormIsInErr('No property named test:guid:newp.min', msgs)

            # virt key in $props: applied to the node but does not affect the deconf guid
            nodes_v05 = await core.nodes('[ test:guid=({"name": "ival-props-virt"}) ]')
            nodes_v06 = await core.nodes('[ test:guid=({"name": "ival-props-virt", "$props": {"seen.min": "2020"}}) ]')
            self.len(1, nodes_v05)
            self.len(1, nodes_v06)
            self.eq(nodes_v05[0].ndef, nodes_v06[0].ndef)
            self.propeq(nodes_v06[0], 'seen', (1577836800000000, ityp.unksize, ityp.duratype.unkdura))

            # $try=True in $props: bad virt value is silently skipped
            nodes_v07 = await core.nodes('''[
                test:guid=({
                    "name": "ival-try-virt",
                    "$try": true,
                    "$props": {"seen.min": "notadate", "tick": "2020"}
                })
            ]''')
            self.len(1, nodes_v07)
            self.none(nodes_v07[0].get('seen'))
            self.nn(nodes_v07[0].get('tick'))

            # $unsets: dotted virt names are not accepted (prop-only in v1)
            msgs = await core.stormlist('[ test:guid=({"name": "ival-unsets", "$unsets": ["seen.min"]}) ]')
            self.stormIsInErr('No property named', msgs)
    async def test_poly(self):

        async with self.getTestCore() as core:

            valu = 'a' * 32

            # guid types are left out of a poly's default norming list so a value
            # cannot be inadvertently normed into the wrong guid type. test:str:bar
            # allows guid types (test:guid, meta:source, ps:person) which are all
            # dropped from the default norming list.
            ptyp = core.model.prop('test:str:bar').type
            self.true(ptyp.ispoly)
            self.notin('test:guid', ptyp.defaulttypes)
            self.notin('meta:source', ptyp.defaulttypes)
            self.notin('ps:person', ptyp.defaulttypes)

            # the guid types remain allowed members of the poly typeset.
            self.isin('test:guid', ptyp.typeset)
            self.isin('meta:source', ptyp.typeset)

            # a raw string norms to the first non-guid member that accepts it.
            norm, info = await ptyp.norm(valu)
            self.eq(('test:str', valu), norm)

            # array element polys are filtered the same way (test:guid is dropped,
            # so test:int rejects the string and test:auto wins).
            atyp = core.model.prop('test:str:polyarry2').type.arraytype
            self.true(atyp.ispoly)
            self.notin('test:guid', atyp.defaulttypes)
            self.eq(('test:int', 'test:auto', 'test:ro'), atyp.defaulttypes)
            norm, info = await atyp.norm(valu)
            self.eq(('test:auto', valu), norm)

            # non-guid string/int norming is unchanged.
            norm, info = await atyp.norm(5)
            self.eq(('test:int', 5), norm)

            # a single guid member is excluded too; its default norming list is
            # empty and a raw value cannot be normed.
            gstyp = core.model.type('test:guidsingle')
            self.eq((), gstyp.defaulttypes)
            with self.raises(s_exc.BadTypeValu):
                await gstyp.norm(valu)

            # a poly whose members are all guid types also ends up empty.
            gtyp = core.model.type('test:guidpoly')
            self.eq((), gtyp.defaulttypes)
            with self.raises(s_exc.BadTypeValu):
                await gtyp.norm(valu)

    async def test_hex(self):

        async with self.getTestCore() as core:

            # Bad configurations are not allowed for the type
            with self.raises(s_exc.BadConfValu):
                core.model.type('hex').clone({'size': 1})

            with self.raises(s_exc.BadConfValu):
                core.model.type('hex').clone({'size': -1})

            with self.raises(s_exc.BadConfValu):
                core.model.type('hex').clone({'zeropad': 1})

            with self.raises(s_exc.BadConfValu):
                core.model.type('hex').clone({'zeropad': -1})

            t = core.model.type('hex').clone({'zeropad': False})
            self.eq('1010', (await t.norm(b'\x10\x10'))[0])

            t = core.model.type('test:hexa')
            # Test norming to index values
            testvectors = [
                (0xc, '0c'),
                (-0xc, 'f4'),
                ('c', '0c'),
                ('0c', '0c'),
                ('-0c', (s_exc.BadTypeValu, 'Non-hexadecimal digit found')),
                ('0x0c', '0c'),
                ('-0x0c', (s_exc.BadTypeValu, 'Non-hexadecimal digit found')),
                (b'\x0c', '0c'),

                (0x10001, '010001'),
                ('10001', '010001'),
                ('0x10001', '010001'),
                ('010001', '010001'),
                ('0x010001', '010001'),
                (b'\x01\x00\x01', '010001'),

                (0xFfF, '0fff'),
                ('FfF', '0fff'),
                ('0FfF', '0fff'),
                ('0x0FfF', '0fff'),
                (b'\x0F\xfF', '0fff'),

                (b'\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~',
                 'd41d8cd98f00b204e9800998ecf8427e'),

                ('01\udcfe0101', (s_exc.BadTypeValu, 'string argument should contain only ASCII characters')),
            ]

            for valu, expected in testvectors:
                if isinstance(expected, str):
                    norm, subs = await t.norm(valu)
                    self.isinstance(norm, str)
                    self.eq(subs, {})
                    self.eq(norm, expected)
                else:
                    etype, mesg = expected
                    with self.raises(etype) as exc:
                        await t.norm(valu)
                    self.eq(exc.exception.get('mesg'), mesg, f'{valu=}')

            # size = 4
            testvectors4 = [
                (0xc, (s_exc.BadTypeValu, 'Invalid width.')),
                (-0xc, (s_exc.BadTypeValu, 'Invalid width.')),
                ('0c', (s_exc.BadTypeValu, 'Invalid width.')),
                ('0x0c', (s_exc.BadTypeValu, 'Invalid width.')),
                (b'\x0c', (s_exc.BadTypeValu, 'Invalid width.')),

                (0xd41d, 'd41d'),
                ('d41d', 'd41d'),
                ('0xd41d', 'd41d'),
                (b'\xd4\x1d', 'd41d'),

                (0x10001, (s_exc.BadTypeValu, 'Invalid width.')),
                ('10001', (s_exc.BadTypeValu, 'Invalid width.')),
                ('0x10001', (s_exc.BadTypeValu, 'Invalid width.')),
                ('010001', (s_exc.BadTypeValu, 'Invalid width.')),
                ('0x010001', (s_exc.BadTypeValu, 'Invalid width.')),
                (b'\x01\x00\x01', (s_exc.BadTypeValu, 'Invalid width.')),

                ('01\udcfe0101', (s_exc.BadTypeValu, 'string argument should contain only ASCII characters')),
            ]
            t = core.model.type('test:hex4')
            for valu, expected in testvectors4:
                if isinstance(expected, str):
                    norm, subs = await t.norm(valu)
                    self.isinstance(norm, str)
                    self.eq(subs, {})
                    self.eq(norm, expected)
                else:
                    etype, mesg = expected
                    with self.raises(etype) as exc:
                        await t.norm(valu)
                    self.eq(exc.exception.get('mesg'), mesg, f'{valu=}')

            # size = 8, zeropad = True
            testvectors = [
                ('0X12', '00000012'),
                ('0x123', '00000123'),
                ('0X1234', '00001234'),
                ('0x123456', '00123456'),
                ('0X12345678', '12345678'),
                ('56:78', '00005678'),
                ('12:34:56:78', '12345678'),
                (-1, 'ffffffff'),
                (-0xff, 'ffffff01'),
                (1234, '000004d2'),
                (0x12345678, '12345678'),
                (0x123456789a, (s_exc.BadTypeValu, 'Invalid width.')),
                ('::', (s_exc.BadTypeValu, 'No string left after stripping.')),
                ('0x::', (s_exc.BadTypeValu, 'No string left after stripping.')),
                ('0x1234qwer', (s_exc.BadTypeValu, 'Non-hexadecimal digit found')),
                ('0x123456789a', (s_exc.BadTypeValu, 'Invalid width.')),
                (b'\x12', '00000012'),
                (b'\x12\x34', '00001234'),
                (b'\x12\x34\x56', '00123456'),
                (b'\x12\x34\x56\x78', '12345678'),
                (b'\x12\x34\x56\x78\x9a', (s_exc.BadTypeValu, 'Invalid width.')),
            ]
            t = core.model.type('test:hexpad')
            for valu, expected in testvectors:
                if isinstance(expected, str):
                    norm, subs = await t.norm(valu)
                    self.isinstance(norm, str)
                    self.eq(subs, {})
                    self.eq(norm, expected)
                else:
                    etype, mesg = expected
                    with self.raises(etype) as exc:
                        await t.norm(valu)
                    self.eq(exc.exception.get('mesg'), mesg, f'{valu=}')

            # zeropad = 20
            testvectors = [
                (-1, 'ffffffffffffffffffff'),
                (-0xff, 'ffffffffffffffffff01'),
                (0x12, '00000000000000000012'),
                (0x123, '00000000000000000123'),
                (0x1234, '00000000000000001234'),
                (0x123456, '00000000000000123456'),
                (0x12345678, '00000000000012345678'),
                (0x123456789abcdef123456789abcdef, '123456789abcdef123456789abcdef'),
                (-0x123456789abcdef123456789abcdef, 'edcba9876543210edcba9876543211'),
                ('0x12', '00000000000000000012'),
                ('0x123', '00000000000000000123'),
                ('0x1234', '00000000000000001234'),
                ('0x123456', '00000000000000123456'),
                ('0x12345678', '00000000000012345678'),
                ('0x123456789abcdef123456789abcdef', '123456789abcdef123456789abcdef'),
                (b'\x12', '00000000000000000012'),
                (b'\x12\x34', '00000000000000001234'),
                (b'\x12\x34\x56', '00000000000000123456'),
                (b'\x12\x34\x56\x78', '00000000000012345678'),
                (b'\x12\x34\x56\x78', '00000000000012345678'),
                (b'\x12\x34\x56\x78\x9a\xbc\xde\xf1\x23\x45\x67\x89\xab\xcd\xef', '123456789abcdef123456789abcdef'),
            ]
            t = core.model.type('test:zeropad')
            for valu, expected in testvectors:
                if isinstance(expected, str):
                    norm, subs = await t.norm(valu)
                    self.isinstance(norm, str)
                    self.eq(subs, {})
                    self.eq(norm, expected)
                else:
                    etype, mesg = expected
                    with self.raises(etype) as exc:
                        await t.norm(valu)
                    self.eq(exc.exception.get('mesg'), mesg, f'{valu=}')

            # Do some node creation and lifting
            nodes = await core.nodes('[test:hexa="01:00 01"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('test:hexa', '010001'))
            self.len(1, await core.nodes('test:hexa=010001'))
            self.len(1, await core.nodes('test:hexa=(0x10001)'))
            self.len(1, await core.nodes('test:hexa=$byts', opts={'vars': {'byts': b'\x01\x00\x01'}}))

            nodes = await core.nodes('[test:hexa=(-10)]')
            self.len(1, nodes)
            self.eq(nodes[0].repr(), 'f6')

            self.len(1, await core.nodes('test:hexa=(-10)'))

            with self.raises(s_exc.BadTypeValu) as exc:
                await core.callStorm('test:hexa^=(-10)')
            self.eq(exc.exception.get('mesg'), 'Hex prefix lift values must be str, not int.')

            # Do some fancy prefix searches for test:hexa
            valus = ['deadb33f',
                     'deadb33fb33f',
                     'deadb3b3',
                     'deaddead',
                     'DEADBEEF']
            self.len(5, await core.nodes('for $valu in $vals {[test:hexa=$valu]}', opts={'vars': {'vals': valus}}))
            self.len(5, await core.nodes('test:hexa=dead*'))
            self.len(3, await core.nodes('test:hexa=deadb3*'))
            self.len(1, await core.nodes('test:hexa=deadb33fb3*'))
            self.len(1, await core.nodes('test:hexa=deadde*'))
            self.len(0, await core.nodes('test:hexa=b33f*'))
            # Do some fancy prefix searches for test:hex4
            valus = ['0000',
                     '0100',
                     '01ff',
                     '0200',
                     ]
            self.len(4, await core.nodes('for $valu in $vals {[test:hex4=$valu]}', opts={'vars': {'vals': valus}}))
            self.len(1, await core.nodes('test:hex4=00*'))
            self.len(2, await core.nodes('test:hex4=01*'))
            self.len(1, await core.nodes('test:hex4=02*'))
            # You can ask for a longer prefix then allowed
            # but you'll get no results
            self.len(0, await core.nodes('test:hex4=022020*'))

            self.len(1, await core.nodes('[test:hexa=0xf00fb33b00000000]'))
            self.len(1, await core.nodes('test:hexa=0xf00fb33b00000000'))
            self.len(1, await core.nodes('test:hexa^=0xf00fb33b'))
            self.len(1, await core.nodes('test:hexa^=0xf00fb33'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:hexa^=(0xf00fb33b)')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:hexa^=(0xf00fb33)')

            # Check creating and lifting zeropadded hex types
            q = '''
            [
                test:zeropad=11
                test:zeropad=0x22
                test:zeropad=111
                test:zeropad=(0x33)
                test:zeropad=(0x444)
            ]
            '''
            self.len(5, await core.nodes(q))
            self.len(1, await core.nodes('test:zeropad=0x11'))
            self.len(1, await core.nodes('test:zeropad=0x111'))
            self.len(1, await core.nodes('test:zeropad=000000000011'))
            self.len(1, await core.nodes('test:zeropad=00000000000000000011'))  # len=20
            self.len(0, await core.nodes('test:zeropad=0000000000000000000011'))  # len=22
            self.len(1, await core.nodes('test:zeropad=22'))
            self.len(1, await core.nodes('test:zeropad=000000000022'))
            self.len(1, await core.nodes('test:zeropad=00000000000000000022'))  # len=20
            self.len(0, await core.nodes('test:zeropad=0000000000000000000022'))  # len=22
            self.len(1, await core.nodes('test:zeropad=(0x33)'))
            self.len(1, await core.nodes('test:zeropad=000000000033'))
            self.len(1, await core.nodes('test:zeropad=00000000000000000033'))  # len=20
            self.len(0, await core.nodes('test:zeropad=0000000000000000000033'))  # len=22
            self.len(1, await core.nodes('test:zeropad=(0x444)'))
            self.len(1, await core.nodes('test:zeropad=000000000444'))
            self.len(1, await core.nodes('test:zeropad=00000000000000000444'))  # len=20
            self.len(0, await core.nodes('test:zeropad=0000000000000000000444'))  # len=22

    async def test_int(self):

        model = s_datamodel.getBaseModel()
        t = model.type('int')

        # test ranges
        self.nn(await t.norm(-2**63))
        with self.raises(s_exc.BadTypeValu) as cm:
            await t.norm((-2**63) - 1)
        self.isinstance(cm.exception.get('valu'), str)
        self.nn(await t.norm(2**63 - 1))
        with self.raises(s_exc.BadTypeValu) as cm:
            await t.norm(2**63)
        self.isinstance(cm.exception.get('valu'), str)

        # test base types that Model snaps in...
        self.eq((await t.norm('100'))[0], 100)
        self.eq((await t.norm('0x20'))[0], 32)
        with self.raises(s_exc.BadTypeValu):
            await t.norm('newp')
        self.eq((await t.norm(True))[0], 1)
        self.eq((await t.norm(False))[0], 0)
        self.eq((await t.norm(decimal.Decimal('1.0')))[0], 1)
        self.eq((await t.norm(s_stormtypes.Number('1.0')))[0], 1)

        # Test merge
        self.eq(30, t.merge(20, 30))
        self.eq(20, t.merge(30, 20))
        self.eq(20, t.merge(20, 20))

        # Test min and max
        minmax = model.type('int').clone({'min': 10, 'max': 30})
        self.eq(20, (await minmax.norm(20))[0])

        with self.raises(s_exc.BadTypeValu):
            await minmax.norm(9)

        with self.raises(s_exc.BadTypeValu):
            await minmax.norm(31)

        ismin = model.type('int').clone({'ismin': True})
        self.eq(20, ismin.merge(20, 30))
        ismin = model.type('int').clone({'ismax': True})
        self.eq(30, ismin.merge(20, 30))

        # Test unsigned
        uint64 = model.type('int').clone({'signed': False})
        self.eq((await uint64.norm(0))[0], 0)
        self.eq((await uint64.norm(-0))[0], 0)

        with self.raises(s_exc.BadTypeValu):
            await uint64.norm(-1)

        maxv = 2 ** (8 * 8) - 1
        self.eq((await uint64.norm(maxv))[0], maxv)

        with self.raises(s_exc.BadTypeValu):
            await uint64.norm(maxv + 1)

        # Test size, 8bit signed
        int8 = model.type('int').clone({'size': 1})
        self.eq((await int8.norm(127))[0], 127)
        self.eq((await int8.norm(0))[0], 0)
        self.eq((await int8.norm(-128))[0], -128)

        with self.raises(s_exc.BadTypeValu):
            await int8.norm(128)

        with self.raises(s_exc.BadTypeValu):
            await int8.norm(-129)

        # Test size, 128bit signed
        int128 = model.type('int').clone({'size': 16})
        self.eq((await int128.norm(2**127 - 1))[0], 170141183460469231731687303715884105727)
        self.eq((await int128.norm(0))[0], 0)
        self.eq((await int128.norm(-2**127))[0], -170141183460469231731687303715884105728)

        with self.raises(s_exc.BadTypeValu):
            await int128.norm(170141183460469231731687303715884105728)

        with self.raises(s_exc.BadTypeValu):
            await int128.norm(-170141183460469231731687303715884105729)

        # test both unsigned and signed comparators
        self.true(await uint64.cmpr(10, '<', 20))
        self.true(await uint64.cmpr(10, '<=', 20))
        self.true(await uint64.cmpr(20, '<=', 20))

        self.true(await uint64.cmpr(20, '>', 10))
        self.true(await uint64.cmpr(20, '>=', 10))
        self.true(await uint64.cmpr(20, '>=', 20))

        self.true(await int8.cmpr(-10, '<', 20))
        self.true(await int8.cmpr(-10, '<=', 20))
        self.true(await int8.cmpr(-20, '<=', -20))

        self.true(await int8.cmpr(20, '>', -10))
        self.true(await int8.cmpr(20, '>=', -10))
        self.true(await int8.cmpr(-20, '>=', -20))

        # test integer enums for repr and norm
        eint = model.type('int').clone({'enums': ((1, 'hehe'), (2, 'haha'))})

        self.eq(1, (await eint.norm(1))[0])
        self.eq(1, (await eint.norm('1'))[0])
        self.eq(1, (await eint.norm('hehe'))[0])
        self.eq(2, (await eint.norm('haha'))[0])
        self.eq(2, (await eint.norm('HAHA'))[0])

        self.eq('hehe', eint.repr(1))
        self.eq('haha', eint.repr(2))

        await self.asyncraises(s_exc.BadTypeValu, eint.norm(0))
        await self.asyncraises(s_exc.BadTypeValu, eint.norm('0'))
        await self.asyncraises(s_exc.BadTypeValu, eint.norm('newp'))

        # Invalid Config
        self.raises(s_exc.BadTypeDef, model.type('int').clone, {'min': 100, 'max': 1})
        self.raises(s_exc.BadTypeDef, model.type('int').clone, {'enums': ((1, 'hehe'), (2, 'haha'), (3, 'HAHA'))})
        self.raises(s_exc.BadTypeDef, model.type('int').clone, {'enums': ((1, 'hehe'), (2, 'haha'), (2, 'beep'))})

        with self.raises(s_exc.BadTypeDef):
            model.type('int').clone({'ismin': True, 'ismax': True})

    async def test_float(self):
        model = s_datamodel.getBaseModel()
        t = model.type('float')

        self.nn((await t.norm(1.2345))[0])
        self.eq((await t.norm('inf'))[0], math.inf)
        self.eq((await t.norm('-inf'))[0], -math.inf)
        self.true(math.isnan((await t.norm('NaN'))[0]))
        self.eq((await t.norm('-0.0'))[0], -0.0)
        self.eq((await t.norm('42'))[0], 42.0)
        self.eq((await t.norm(s_stormtypes.Number('1.23')))[0], 1.23)
        minmax = model.type('float').clone({'min': -10.0, 'max': 100.0, 'maxisvalid': True, 'minisvalid': False})
        await self.asyncraises(s_exc.BadTypeValu, minmax.norm('NaN'))
        await self.asyncraises(s_exc.BadTypeValu, minmax.norm('-inf'))
        await self.asyncraises(s_exc.BadTypeValu, minmax.norm('inf'))
        await self.asyncraises(s_exc.BadTypeValu, minmax.norm('-10'))
        await self.asyncraises(s_exc.BadTypeValu, minmax.norm('-10.00001'))
        await self.asyncraises(s_exc.BadTypeValu, minmax.norm('100.00001'))
        self.eq((await minmax.norm('100.000'))[0], 100.0)
        self.true(await t.cmpr(10, '<', 20.0))
        self.false(await t.cmpr(-math.inf, '>', math.inf))
        self.false(await t.cmpr(-math.nan, '<=', math.inf))
        self.true(await t.cmpr('inf', '>=', '-0.0'))

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ test:float=42.0 ]')
            self.len(1, nodes)
            nodes = await core.nodes('[ test:float=inf ]')
            self.len(1, nodes)

            nodes = await core.nodes('[ test:float=(42.1) ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:float', 42.1))

            nodes = await core.nodes('[ test:float=($lib.cast(float, 42.1)) ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:float', 42.1))

            self.len(1, await core.nodes('[ test:float=42.0 :closed=0.0]'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('[ test:float=42.0 :closed=-1.0]'))
            self.len(1, await core.nodes('[ test:float=42.0 :closed=360.0]'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('[ test:float=42.0 :closed=NaN]'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('[ test:float=42.0 :closed=360.1]'))

            await self.asyncraises(s_exc.BadTypeValu, core.nodes('[ test:float=42.0 :open=0.0]'))
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('[ test:float=42.0 :open=360.0]'))
            self.len(1, await core.nodes('[ test:float=42.0 :open=0.001]'))
            self.len(1, await core.nodes('[ test:float=42.0 :open=359.0]'))

            self.eq(5, await core.callStorm('return($lib.cast(int, (5.5)))'))

            valu = await core.callStorm('return($lib.cast(test:arrayprop:ints, (1, 2, 3)))')
            self.eq(valu, (1, 2, 3))

            ok, valu = await core.callStorm('return($lib.trycast(test:arrayprop:ints, (1, 2, 3)))')
            self.true(ok)
            self.eq(valu, (1, 2, 3))

    async def test_ival(self):
        model = s_datamodel.getBaseModel()
        ival = model.types.get('ival')

        self.eq('2016-01-01T00:00:00Z - 2017-01-01T00:00:00Z', ival.repr((await ival.norm(('2016', '2017')))[0]))
        self.eq((0, 5356800000000, 5356800000000), (await ival.norm((0, '1970-03-04')))[0])

        # a repr string round-trips back to the same value via norm
        for src in (('2016', '2017'), ('?', '2025-07-12T07:13?'), ('20210102T07?', '20240401T07?'),
                    ('2012?', '20210607?'), ('?', '2025?'), ('2016-01-01', '2016-01-01'), ('2020', '*')):
            valu = (await ival.norm(src))[0]
            self.eq(valu, (await ival.norm(ival.repr(valu)))[0])

        # a bare ' - ' separated string norms as a range
        self.eq((1451606400000000, 1483228800000000, 31622400000000),
                (await ival.norm('2016 - 2017'))[0])
        # a ' - ' range whose bounds are equal becomes a 1us interval
        self.eq((1577836800000000, 1577836800000001, 1), (await ival.norm('2020 - 2020'))[0])
        # ' - ' that is not a valid range falls back to relative-time handling
        self.eq((1575244800000000, 1575244800000001, 1), (await ival.norm('2020 - 30 days'))[0])
        # a range may not begin with the ongoing (*) marker
        with self.raises(s_exc.BadTypeValu):
            await ival.norm('* - 2020')
        # a ' - ' range with min after max is rejected
        with self.raises(s_exc.BadTypeValu):
            await ival.norm('2020-01-01T00:00:00Z - 2019-01-01T00:00:00Z')
        self.eq((1451606400000000, 1451606400000001, 1), (await ival.norm('2016'))[0])
        self.eq((1451606400000000, 1451606400000001, 1), (await ival.norm(1451606400000000))[0])
        self.eq((1451606400000000, 1451606400000001, 1), (await ival.norm(decimal.Decimal(1451606400000000)))[0])
        self.eq((1451606400000000, 1451606400000001, 1), (await ival.norm(s_stormtypes.Number(1451606400000000)))[0])
        self.eq((1451606400000000, 1451606400000001, 1), (await ival.norm('2016'))[0])
        self.eq((1451606400000000, 1483228800000000, 31622400000000), (await ival.norm(('2016', '  2017')))[0])
        self.eq((1451606400000000, 1483228800000000, 31622400000000), (await ival.norm(('2016-01-01', '  2017')))[0])
        self.eq((1451606400000000, 1483142400000000, 31536000000000), (await ival.norm(('2016', '+365 days')))[0])
        self.eq((1448150400000000, 1451606400000000, 3456000000000), (await ival.norm(('2016', '-40 days')))[0])
        self.eq((1447891200000000, 1451347200000000, 3456000000000), (await ival.norm(('2016-3days', '-40 days   ')))[0])
        self.eq((1451347200000000, ival.unksize, ival.duratype.unkdura), (await ival.norm(('2016-3days', '?')))[0])
        self.eq((1593576000000000, 1593576000000001, 1), (await ival.norm('2020-07-04:00'))[0])
        self.eq((1594124993000000, 1594124993000001, 1), (await ival.norm('2020-07-07T16:29:53+04:00'))[0])
        self.eq((1594153793000000, 1594153793000001, 1), (await ival.norm('2020-07-07T16:29:53-04:00'))[0])
        self.eq((1594211393000000, 1594211393000001, 1), (await ival.norm('20200707162953+04:00+1day'))[0])
        self.eq((1594038593000000, 1594038593000001, 1), (await ival.norm('20200707162953+04:00-1day'))[0])
        self.eq((1594240193000000, 1594240193000001, 1), (await ival.norm('20200707162953-04:00+1day'))[0])
        self.eq((1594067393000000, 1594067393000001, 1), (await ival.norm('20200707162953-04:00-1day'))[0])
        self.eq((1594240193000000, 1594240193000001, 1), (await ival.norm('20200707162953EDT+1day'))[0])
        self.eq((1594067393000000, 1594067393000001, 1), (await ival.norm('20200707162953EDT-1day'))[0])
        self.eq((1594240193000000, 1594240193000001, 1), (await ival.norm('7 Jul 2020 16:29:53 EDT+1day'))[0])
        self.eq((1594067393000000, 1594067393000001, 1), (await ival.norm('7 Jul 2020 16:29:53 -0400-1day'))[0])

        # these fail because ival norming will split on a comma
        await self.asyncraises(s_exc.BadTypeValu, ival.norm('Tue, 7 Jul 2020 16:29:53 EDT+1day'))
        await self.asyncraises(s_exc.BadTypeValu, ival.norm('Tue, 7 Jul 2020 16:29:53 -0400+1day'))

        start = s_common.now() + s_time.oneday - 1
        end = (await ival.norm(('now', '+1day')))[0][1]
        self.lt(start, end)

        oldv = (await ival.norm(('2016', '2017')))[0]
        newv = (await ival.norm(('2015', '2018')))[0]
        self.eq((1420070400000000, 1514764800000000, 94694400000000), ival.merge(oldv, newv))

        self.eq((1420070400000000, 1420070400000001, 1), (await ival.norm(('2015', '2015')))[0])
        self.eq((ival.unksize, ival.unksize, ival.duratype.unkdura), (await ival.norm('?'))[0])
        self.eq((ival.unksize, ival.unksize, ival.duratype.unkdura), (await ival.norm(('?', '?')))[0])

        await self.asyncraises(s_exc.BadTypeValu, ival.norm(('', '')))

        # should norming a triple ignore duration if min/max are both set or validate it matches?
        # await self.asyncraises(s_exc.BadTypeValu, ival.norm(('2016-3days', '+77days', '-40days')))

        await self.asyncraises(s_exc.BadTypeValu, ival.norm(('2016-3days', '+77days', '-40days', '-40days')))
        await self.asyncraises(s_exc.BadTypeValu, ival.norm(('?', '-1 day')))

        async with self.getTestCore() as core:

            self.len(1, await core.nodes('[test:str=a :seen=(2005, 2006) :tick=2014 +#foo=(2000, 2001)]'))
            self.len(1, await core.nodes('[test:str=b :seen=(8679, 9000) :tick=2015 +#foo=(2015, 2018)]'))
            self.len(1, await core.nodes('[test:str=c :seen=("now-5days", "now-1day") :tick=2016 +#bar=(1970, 1990)]'))
            self.len(1, await core.nodes('[test:str=d :seen=("now-10days", "?") :tick=now +#baz=now]'))
            self.len(1, await core.nodes('[test:str=e :seen=("now+1day", "now+5days") :tick="now-3days" +#biz=("now-1day", "now+1 day")]'))
            self.len(1, await core.nodes('[test:str=f +#foo ]'))
            # tag of tags
            self.len(1, await core.nodes('[syn:tag=foo +#v.p=(2005, 2006)]'))
            self.len(1, await core.nodes('[syn:tag=bar +#vert.proj=(20110605, now)]'))
            self.len(1, await core.nodes('[syn:tag=biz +#vertex.project=("now-5days", now)]'))

            self.eq(1, await core.count('test:str +:tick@=(now, "-1 day")'))
            self.eq(1, await core.count('test:str +:tick@=2015'))
            self.eq(1, await core.count('test:str +:tick@=(2015, "+1 day")'))
            self.eq(1, await core.count('test:str +:tick@=(20150102+1day, "-4 day")'))
            self.eq(1, await core.count('test:str +:tick@=(20150102, "-4 day")'))
            self.eq(1, await core.count('test:str +:tick@=(now, "-1 day")'))
            self.eq(1, await core.count('test:str +:tick@=("now-1day", "?")'))
            self.eq(1, await core.count('test:str +:tick@=("now+2days", "-3 day")'))
            self.eq(0, await core.count('test:str +:tick@=("now", "now+3days")'))
            self.eq(1, await core.count('test:str +:tick@=("now-2days","now")'))
            self.eq(0, await core.count('test:str +:tick@=("2011", "2014")'))
            self.eq(1, await core.count('test:str +:tick@=("2014", "20140601")'))

            self.eq(1, await core.count('test:str:tick@=(now, "-1 day")'))
            self.eq(1, await core.count('test:str:tick@=2015'))
            self.eq(1, await core.count('test:str:tick@=(2015, "+1 day")'))
            self.eq(1, await core.count('test:str:tick@=(20150102+1day, "-4 day")'))
            self.eq(1, await core.count('test:str:tick@=(20150102, "-4 day")'))
            self.eq(1, await core.count('test:str:tick@=(now, "-1 day")'))
            self.eq(1, await core.count('test:str:tick@=("now-1day", "?")'))
            self.eq(1, await core.count('test:str:tick@=("now+2days", "-3 day")'))
            self.eq(0, await core.count('test:str:tick@=("now", "now+3days")'))
            self.eq(1, await core.count('test:str:tick@=("now-2days","now")'))
            self.eq(0, await core.count('test:str:tick@=("2011", "2014")'))
            self.eq(1, await core.count('test:str:tick@=("2014", "20140601")'))

            self.eq(0, await core.count('#foo@=("2013", "2015")'))
            self.eq(0, await core.count('#foo@=("2018", "2019")'))
            self.eq(1, await core.count('#foo@=("1999", "2002")'))
            self.eq(1, await core.count('#foo@="2015"'))
            self.eq(1, await core.count('#foo@=("2010", "20150601")'))
            self.eq(2, await core.count('#foo@=("2000", "2017")'))
            self.eq(1, await core.count('#bar@=("1985", "1995")'))
            self.eq(0, await core.count('#bar@="2000"'))
            self.eq(1, await core.count('#baz@=("now","-1 day")'))
            self.eq(1, await core.count('#baz@=("now-1day", "+1day")'))
            self.eq(1, await core.count('#biz@="now"'))

            self.eq(0, await core.count('#foo +#foo@=("2013", "2015")'))
            self.eq(0, await core.count('#foo +#foo@=("2018", "2019")'))
            self.eq(1, await core.count('#foo +#foo@=("1999", "2002")'))
            self.eq(1, await core.count('#foo +#foo@="2015"'))
            self.eq(1, await core.count('#foo +#foo@=("2010", "20150601")'))
            self.eq(2, await core.count('#foo +#foo@=("2000", "2017")'))
            self.eq(1, await core.count('#bar +#bar@=("1985", "1995")'))
            self.eq(0, await core.count('#bar +#bar@="2000"'))
            self.eq(1, await core.count('#baz +#baz@=("now","-1 day")'))
            self.eq(1, await core.count('#baz +#baz@=("now-1day", "+1day")'))
            self.eq(1, await core.count('#biz +#biz@="now"'))

            self.eq(1, await core.count('#foo=("2015", "2018")'))

            self.eq(0, await core.count('test:str#foo@=("2013", "2015")'))
            self.eq(0, await core.count('test:str#foo@=("2018", "2019")'))
            self.eq(1, await core.count('test:str#foo@=("1999", "2002")'))
            self.eq(1, await core.count('test:str#foo@="2015"'))
            self.eq(1, await core.count('test:str#foo@=("2010", "20150601")'))
            self.eq(2, await core.count('test:str#foo@=("2000", "2017")'))
            self.eq(1, await core.count('test:str#bar@=("1985", "1995")'))
            self.eq(0, await core.count('test:str#bar@="2000"'))
            self.eq(1, await core.count('test:str#baz@=("now","-1 day")'))
            self.eq(1, await core.count('test:str#baz@=("now-1day", "+1day")'))
            self.eq(1, await core.count('test:str#biz@="now"'))

            self.eq(0, await core.count('test:str +#foo@=("2013", "2015")'))
            self.eq(0, await core.count('test:str +#foo@=("2018", "2019")'))
            self.eq(1, await core.count('test:str +#foo@=("1999", "2002")'))
            self.eq(1, await core.count('test:str +#foo@="2015"'))
            self.eq(1, await core.count('test:str +#foo@=("2010", "20150601")'))
            self.eq(2, await core.count('test:str +#foo@=("2000", "2017")'))
            self.eq(1, await core.count('test:str +#bar@=("1985", "1995")'))
            self.eq(0, await core.count('test:str +#bar@="2000"'))
            self.eq(1, await core.count('test:str +#baz@=("now","-1 day")'))
            self.eq(1, await core.count('test:str +#baz@=("now-1day", "+1day")'))
            self.eq(1, await core.count('test:str +#biz@="now"'))

            self.eq(0, await core.count('##v.p@=("2003", "2005")'))
            self.eq(0, await core.count('##v.p@=("2006", "2008")'))
            self.eq(1, await core.count('##vert.proj@="2016"'))
            self.eq(1, await core.count('##vert.proj@=("2010", "2012")'))
            self.eq(1, await core.count('##vert.proj@=("2016", "now+6days")'))
            self.eq(1, await core.count('##vert.proj@=("1995", "now+6 days")'))
            self.eq(1, await core.count('##vertex.project@=("now-9days", "now-3days")'))

            self.eq(0, await core.count('test:str +:tick@=(2020, 2000)'))

            now = s_common.now()
            nodes = await core.nodes('[test:guid="*" :seen=("-1 day","?")]')
            node = nodes[0]
            valu = node.get('seen')[1]
            self.eq(valu[1], ival.unksize)
            self.true(now - s_const.day <= valu[0] < now)

            # Sad Paths
            q = '[test:str=newp :seen=(2018/03/31,2018/03/30)]'
            with self.raises(s_exc.BadTypeValu):
                await core.nodes(q)
            q = '[test:str=newp :seen=("+-1 day","+-1 day")]'
            with self.raises(s_exc.BadTypeValu):
                await core.nodes(q)
            q = '[test:str=newp :seen=(2008, 2019, 2000, 2040)]'
            with self.raises(s_exc.BadTypeValu):
                await core.nodes(q)
            q = '[test:str=newp :seen=("?","-1 day")]'
            with self.raises(s_exc.BadTypeValu):
                await core.nodes(q)
            # *range= not supported for ival
            q = 'test:str +:seen*range=((20090601, 20090701), (20110905, 20110906,))'
            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes(q)
            q = 'test:str:seen*range=((20090601, 20090701), (20110905, 20110906,))'
            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes(q)

            await core.nodes('''[
                (entity:campaign=* :period=(2020-01-01, 2020-01-02))
                (entity:campaign=* :period=(2021-01-01, 2021-02-01))
                (entity:campaign=* :period=(2022-01-01, 2022-05-01))
                (entity:campaign=* :period=(2023-01-01, 2024-01-01))
                (entity:campaign=* :period=(2024-01-01, 2026-01-01))
                (entity:campaign=*)
            ]''')

            self.len(1, await core.nodes('entity:campaign.created +:period.began=2020-01-01'))
            self.len(2, await core.nodes('entity:campaign.created +:period.began<2022-01-01'))
            self.len(3, await core.nodes('entity:campaign.created +:period.began<=2022-01-01'))
            self.len(3, await core.nodes('entity:campaign.created +:period.began>=2022-01-01'))
            self.len(2, await core.nodes('entity:campaign.created +:period.began>2022-01-01'))
            self.len(1, await core.nodes('entity:campaign.created +:period.began@=2020'))
            self.len(2, await core.nodes('entity:campaign.created +:period.began@=(2020-01-01, 2022-01-01)'))

            self.len(1, await core.nodes('entity:campaign.created +:period.ended=2020-01-02'))
            self.len(2, await core.nodes('entity:campaign.created +:period.ended<2022-05-01'))
            self.len(3, await core.nodes('entity:campaign.created +:period.ended<=2022-05-01'))
            self.len(3, await core.nodes('entity:campaign.created +:period.ended>=2022-05-01'))
            self.len(2, await core.nodes('entity:campaign.created +:period.ended>2022-05-01'))
            self.len(1, await core.nodes('entity:campaign.created +:period.ended@=2022-05-01'))
            self.len(2, await core.nodes('entity:campaign.created +:period.ended@=(2020-01-02, 2022-05-01)'))

            self.len(1, await core.nodes('entity:campaign.created +:period.duration=1D'))
            self.len(1, await core.nodes('entity:campaign.created +:period.duration<31D'))
            self.len(2, await core.nodes('entity:campaign.created +:period.duration<=31D'))
            self.len(4, await core.nodes('entity:campaign.created +:period.duration>=31D'))
            self.len(3, await core.nodes('entity:campaign.created +:period.duration>31D'))

            self.len(0, await core.nodes('entity:campaign.created +:period.began@=(2022-01-01, 2020-01-01)'))

            with self.raises(s_exc.NoSuchFunc):
                await core.nodes('entity:campaign.created +:period.began@=({})')

            self.eq(ival.getVirtType('min'), model.types.get('time'))

            with self.raises(s_exc.NoSuchVirt):
                ival.getVirtType('newp')

            with self.raises(s_exc.NoSuchVirt):
                ival.getVirtGetr('newp')

            ityp = core.model.type('ival')
            styp = core.model.type('timeprecision').stortype

            # test that the most precise time precision wins
            valu = await ival.norm(('?', 'now'))
            self.eq({}, valu[1])

            valu = await ival.norm(('?', '2025-07-12T07:13?'))
            self.eq('? - 2025-07-12T07:13:*', ival.repr(valu[0]))
            self.eq({'virts': {'precision': (s_time.PREC_MINUTE, styp)}}, valu[1])

            valu = await ival.norm(('20210102T07?', '20240401T07?'))
            self.eq('2021-01-02T07:00:00Z - 2024-04-01T07:*', ival.repr(valu[0]))
            self.eq({'virts': {'precision': (s_time.PREC_HOUR, styp)}}, valu[1])

            valu = await ival.norm(('2012?', '20210607?'))
            self.eq('2012-01-01T00:00:00Z - 2021-06-07*', ival.repr(valu[0]))
            self.eq({'virts': {'precision': (s_time.PREC_DAY, styp)}}, valu[1])

            valu = await ival.norm(('202101?', '2025?'))
            self.eq('2021-01-01T00:00:00Z - 2025-01-31*', ival.repr(valu[0]))
            self.eq({'virts': {'precision': (s_time.PREC_MONTH, styp)}}, valu[1])

            valu = await ival.norm(('2021?', '202501?'))
            self.eq('2021-01-01T00:00:00Z - 2025-01-31*', ival.repr(valu[0]))
            self.eq({'virts': {'precision': (s_time.PREC_MONTH, styp)}}, valu[1])

            valu = await ival.norm(('?', '2025?'))
            self.eq('? - 2025-12-31*', ival.repr(valu[0]))
            self.eq({'virts': {'precision': (s_time.PREC_YEAR, styp)}}, valu[1])

            valu = (await ityp.norm('2025-04-05 12:34:56.123456'))[0]
            exp = ((1743856496123456, 1743856496123457, 1), {})
            self.eq(await ityp.normVirt('precision', valu, s_time.PREC_MICRO), exp)

            exp = ((1743856496123000, 1743856496123999, 999), {'virts': {'precision': (s_time.PREC_MILLI, styp)}})
            self.eq(await ityp.normVirt('precision', valu, s_time.PREC_MILLI), exp)

            exp = ((1743856496000000, 1743856496999999, 999999), {'virts': {'precision': (s_time.PREC_SECOND, styp)}})
            self.eq(await ityp.normVirt('precision', valu, s_time.PREC_SECOND), exp)

            exp = ((1743856440000000, 1743856499999999, 59999999), {'virts': {'precision': (s_time.PREC_MINUTE, styp)}})
            self.eq(await ityp.normVirt('precision', valu, s_time.PREC_MINUTE), exp)

            exp = ((1743854400000000, 1743857999999999, 3599999999), {'virts': {'precision': (s_time.PREC_HOUR, styp)}})
            self.eq(await ityp.normVirt('precision', valu, s_time.PREC_HOUR), exp)

            exp = ((1743811200000000, 1743897599999999, 86399999999), {'virts': {'precision': (s_time.PREC_DAY, styp)}})
            self.eq(await ityp.normVirt('precision', valu, s_time.PREC_DAY), exp)

            exp = ((1743465600000000, 1746057599999999, 2591999999999), {'virts': {'precision': (s_time.PREC_MONTH, styp)}})
            self.eq(await ityp.normVirt('precision', valu, s_time.PREC_MONTH), exp)

            exp = ((1735689600000000, 1767225599999999, 31535999999999), {'virts': {'precision': (s_time.PREC_YEAR, styp)}})
            self.eq(await ityp.normVirt('precision', valu, s_time.PREC_YEAR), exp)

            with self.raises(s_exc.BadTypeDef):
                await core.addType('test:int', 'ival', {'precision': 'newp'}, {})

            nodes = await core.nodes('[ test:str=foo :seen=(2021, ?) :seen.duration=1D ]')
            self.propeq(nodes[0], 'seen', (1609459200000000, 1609545600000000, 86400000000))

            nodes = await core.nodes('[ test:str=bar :seen=(?, 2021) :seen.duration=1D ]')
            self.propeq(nodes[0], 'seen', (1609372800000000, 1609459200000000, 86400000000))

            nodes = await core.nodes('[ test:str=baz :seen=(?, ?) :seen.duration=1D ]')
            self.propeq(nodes[0], 'seen', (ityp.unksize, ityp.unksize, 86400000000))

            nodes = await core.nodes('test:str=baz [ :seen.min=2021 ]')
            self.propeq(nodes[0], 'seen', (1609459200000000, 1609545600000000, 86400000000))

            nodes = await core.nodes('[ test:str=faz :seen.duration=1D ]')
            self.propeq(nodes[0], 'seen', (ityp.unksize, ityp.unksize, 86400000000))

            nodes = await core.nodes('test:str=faz [ :seen.max=2021 ]')
            self.propeq(nodes[0], 'seen', (1609372800000000, 1609459200000000, 86400000000))

            nodes = await core.nodes('test:str=faz [ :seen.max=? ]')
            self.propeq(nodes[0], 'seen', (1609372800000000, ityp.unksize, ityp.duratype.unkdura))

            nodes = await core.nodes('test:str=faz [ :seen.min=2022 ]')
            self.propeq(nodes[0], 'seen', (1640995200000000, ityp.unksize, ityp.duratype.unkdura))

            nodes = await core.nodes('test:str=faz [ :seen.max=* ]')
            self.propeq(nodes[0], 'seen', (1640995200000000, ityp.futsize, ityp.duratype.futdura))

            nodes = await core.nodes('test:str=faz [ :seen.min=2021 ]')
            self.propeq(nodes[0], 'seen', (1609459200000000, ityp.futsize, ityp.duratype.futdura))

            nodes = await core.nodes('test:str=faz [ :seen.max=2022 :seen.min=? ]')
            self.propeq(nodes[0], 'seen', (ityp.unksize, 1640995200000000, ityp.duratype.unkdura))

            nodes = await core.nodes('test:str=faz [ :seen.max=2021 :seen.min=? ]')
            self.propeq(nodes[0], 'seen', (ityp.unksize, 1609459200000000, ityp.duratype.unkdura))

            nodes = await core.nodes('test:str=faz [ :seen.duration=* ]')
            self.propeq(nodes[0], 'seen', (ityp.unksize, ityp.futsize, ityp.duratype.futdura))

            nodes = await core.nodes('test:str=faz [ :seen.duration=1D ]')
            self.propeq(nodes[0], 'seen', (ityp.unksize, ityp.unksize, 86400000000))

            nodes = await core.nodes('[ test:str=int :seen=$valu ]', opts={'vars': {'valu': ityp.unksize}})
            self.propeq(nodes[0], 'seen', (ityp.unksize, ityp.unksize, ityp.duratype.unkdura))

            nodes = await core.nodes('[ test:str=merge1 :seen=(?, ?) :seen=(?, 2020) ]')
            self.propeq(nodes[0], 'seen', (ityp.unksize, 1577836800000000, ityp.duratype.unkdura))

            nodes = await core.nodes('[ test:str=merge2 :seen=(?, 2020) :seen=(2019, ?) ]')
            self.propeq(nodes[0], 'seen', (1546300800000000, 1577836800000000, 31536000000000))

            nodes = await core.nodes('[ test:str=merge2 :seen=(?, *) ]')
            self.propeq(nodes[0], 'seen', (1546300800000000, ityp.futsize, ityp.duratype.futdura))

            self.len(0, await core.nodes('[ test:str=fut :seen=(now + 1day, *) ] +:seen.duration'))

            nodes = await core.nodes('[test:str=setprec1 :seen=(20210112, 20220606) :seen.precision=minute]')
            exp = (('ival', (1610409600000000, 1654473659999999, 44064059999999)), {'precision': (s_time.PREC_MINUTE, styp)})
            self.eq(nodes[0].getWithVirts('seen'), exp)
            self.eq(nodes[0].getProps(virts=True)['seen.precision'], s_time.PREC_MINUTE)

            nodes = await core.nodes('[test:str=setprec2 :seen=(?, 20220606) :seen.precision=day]')
            exp = (('ival', (ityp.unksize, 1654559999999999, 18446744073709551615)), {'precision': (s_time.PREC_DAY, styp)})
            self.eq(nodes[0].getWithVirts('seen'), exp)
            packed = nodes[0].pack(virts=True)
            self.eq(packed[1]['props']['seen.precision'], s_time.PREC_DAY)

            nodes = await core.nodes('[test:str=setprec3 :seen=(20210112, ?) :seen.precision=month]')
            exp = (('ival', (1609459200000000, ityp.unksize, 18446744073709551615)), {'precision': (s_time.PREC_MONTH, styp)})
            self.eq(nodes[0].getWithVirts('seen'), exp)

            nodes = await core.nodes('[test:str=setprec3 :seen=(20210112, ?) :seen.precision=microsecond]')
            exp = (('ival', (1609459200000000, ityp.unksize, 18446744073709551615)), None)
            props = nodes[0].getProps(virts=True)
            self.eq(props['seen.precision'], s_time.PREC_MICRO)
            # the precision for default values doesn't get stored
            self.eq(nodes[0].getWithVirts('seen'), exp)

            nodes = await core.nodes('[test:str=setprec4 :seen=(?, ?) :seen.precision=hour]')
            exp = (('ival', (9223372036854775807, 9223372036854775807, 18446744073709551615)), None)
            self.eq(nodes[0].getWithVirts('seen'), exp)

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ test:str=foo :seen=(2021, 2022) :seen.duration=500 ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ test:str=foo :seen.duration=-1D ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ test:str=foo :seen.duration=$valu ]', opts={'vars': {'valu': ityp.duratype.unkdura + 1}})

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ test:str=int :seen=* ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ test:str=int :seen=(*, *) ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ test:str=int :seen=$valu ]', opts={'vars': {'valu': ityp.futsize}})

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str:seen@=(1, 2, 3, 4)')

    async def test_ival_virt_names(self):

        async with self.getTestCore() as core:

            # it:lifespan is an ival which renames the min/max virts to created/removed
            ltype = core.model.type('it:lifespan')
            self.eq(core.model.type('ival').stortype, ltype.stortype)
            self.sorteq(('created', 'removed', 'duration', 'precision'), ltype.virts.keys())

            # the renamed comparators are translated back to the canonical min/max
            self.eq('min<=', (await ltype.getStorCmprs('<=', '2021', virt='created'))[0][0])
            self.eq('max=', (await ltype.getStorCmprs('=', '2022', virt='removed'))[0][0])

            # phys:lifespan renames min/max to created/retired
            ptype = core.model.type('phys:lifespan')
            self.sorteq(('created', 'retired', 'duration', 'precision'), ptype.virts.keys())
            self.eq('max=', (await ptype.getStorCmprs('=', '2022', virt='retired'))[0][0])

            # entity:lifespan renames min/max to began/ended
            etype = core.model.type('entity:lifespan')
            self.sorteq(('began', 'ended', 'duration', 'precision'), etype.virts.keys())
            self.eq('min<=', (await etype.getStorCmprs('<=', '2020', virt='began'))[0][0])

            await core.addFormProp('inet:service:platform', '_life', ('it:lifespan', {}), {'doc': 'x'})
            nodes = await core.nodes('[ inet:service:platform=* :_life=(2020, 2022) ]')
            self.len(1, nodes)
            node = nodes[0]

            # the renamed virts are readable and resolve to the same min/max values
            self.eq(1577836800000000, node.get('_life.created'))
            self.eq(1640995200000000, node.get('_life.removed'))
            self.nn(node.get('_life.duration'))

            # the renamed virts are filterable and round-trip through the storage layer
            self.len(1, await core.nodes('inet:service:platform +:_life.created>=2019'))
            self.len(0, await core.nodes('inet:service:platform +:_life.created>=2021'))
            self.len(1, await core.nodes('inet:service:platform +:_life.removed<2099'))
            self.len(1, await core.nodes('inet:service:platform +:_life.duration>1D'))

            # the original min/max names are no longer present
            with self.raises(s_exc.NoSuchVirt):
                node.get('_life.min')

    async def test_price(self):

        async with self.getTestCore() as core:

            prtype = core.model.type('econ:price')

            # bare numbers behave like a hugenum and capture no currency
            norm, info = await prtype.norm('99')
            self.eq('99', norm)
            self.eq({}, info.get('virts', {}))
            self.eq('99', prtype.reprWithVirts(norm, None))

            norm, info = await prtype.norm(99)
            self.eq('99', norm)
            self.eq({}, info)

            # a trailing currency code is captured into the currency virt
            norm, info = await prtype.norm('99USD')
            self.eq('99', norm)
            self.eq({'currency': ('USD', core.model.type('econ:currency').stortype)}, info['virts'])
            self.eq('99USD', prtype.reprWithVirts(norm, info['virts']))

            # whitespace separated and lower-case currency both work
            norm, info = await prtype.norm('99 usd')
            self.eq('99', norm)
            self.eq('99USD', prtype.reprWithVirts(norm, info['virts']))

            norm, info = await prtype.norm('-12.5eur')
            self.eq('-12.5', norm)
            self.eq('-12.5EUR', prtype.reprWithVirts(norm, info['virts']))

            # scientific notation ends in a digit so is not mis-split
            norm, info = await prtype.norm('1e-24')
            self.eq({}, info.get('virts', {}))

            # an all-alpha or empty numeric part is a bad value
            with self.raises(s_exc.BadTypeValu):
                await prtype.norm('usd')

    async def test_pricerange(self):

        async with self.getTestCore() as core:

            prtype = core.model.type('econ:pricerange')

            # norm from a (min, max) pair
            self.eq(('1.5', '2.2', '0.7'), (await prtype.norm((1.5, 2.2)))[0])
            self.eq(('1.5', '2.2', '0.7'), (await prtype.norm(('1.50', '2.20')))[0])

            # norm from a "min-max" string
            self.eq(('1.5', '2.2', '0.7'), (await prtype.norm('1.50-2.20'))[0])

            # a trailing currency code is captured into the currency virt
            norm, info = await prtype.norm('32-99USD')
            self.eq(('32', '99', '67'), norm)
            self.eq({'currency': ('USD', core.model.type('econ:currency').stortype)}, info['virts'])
            self.eq('32-99USD', prtype.reprWithVirts(norm, info['virts']))

            # lower-case trailing currency is also upper-cased
            norm, info = await prtype.norm('32-99 usd')
            self.eq('32-99USD', prtype.reprWithVirts(norm, info['virts']))

            # no currency -> no virts and the plain 2-tuple repr
            norm, info = await prtype.norm('1.50-2.20')
            self.eq({}, info.get('virts', {}))
            self.eq(('1.5', '2.2'), prtype.reprWithVirts(norm, None))

            # getters
            valu = (await prtype.norm((10, 25)))[0]
            self.eq('10', prtype.getVirtGetr('min')((valu, None, None)))
            self.eq('25', prtype.getVirtGetr('max')((valu, None, None)))
            self.eq('15', prtype.getVirtGetr('delta')((valu, None, None)))

            # repr
            self.eq(('1.5', '2.2'), prtype.repr((await prtype.norm((1.5, 2.2)))[0]))

            # unknown sentinel partial-capture then completion
            self.eq(('?', '?', '?'), (await prtype.norm('?'))[0])
            self.eq(('?', '?', '?'), (await prtype.norm(('?', '?')))[0])

            # set min on empty -> max unknown, delta unknown
            newv, info = await prtype.normVirt('min', None, 5)
            self.eq(('5', '?', '?'), newv)
            self.false(info['merge'])

            # set max recomputes delta
            newv, _ = await prtype.normVirt('max', newv, 12)
            self.eq(('5', '12', '7'), newv)

            # set max on empty -> min unknown, delta unknown
            newv, info = await prtype.normVirt('max', None, 9)
            self.eq(('?', '9', '?'), newv)
            self.false(info['merge'])

            # set max when min unknown but delta known derives min
            base = (await prtype.norm(('?', '?')))[0]
            base, _ = await prtype.normVirt('delta', base, 4)
            self.eq(('?', '?', '4'), base)
            newv, _ = await prtype.normVirt('max', base, 20)
            self.eq(('16', '20', '4'), newv)

            # set min when max known and within range recomputes delta
            base = (await prtype.norm(('?', '20')))[0]
            newv, _ = await prtype.normVirt('min', base, 5)
            self.eq(('5', '20', '15'), newv)

            # delta getter returns None for the unknown sentinel
            unkv = (await prtype.norm(('?', '?')))[0]
            self.none(prtype.getVirtGetr('delta')((unkv, None, None)))
            self.none(prtype.getVirtGetr('max')((unkv, None, None)))
            self.none(prtype.getVirtGetr('min')((unkv, None, None)))

            # currency getter returns None when virts dict lacks the key
            self.none(prtype.getVirtGetr('currency')((unkv, None, {})))

            # set min raises when greater than a known max
            with self.raises(s_exc.BadTypeValu):
                await prtype.normVirt('min', (await prtype.norm(('?', '5')))[0], 10)

            # set max raises when less than a known min
            with self.raises(s_exc.BadTypeValu):
                await prtype.normVirt('max', (await prtype.norm((10, 20)))[0], 5)

            # norm requires a 2-tuple
            with self.raises(s_exc.BadTypeValu):
                await prtype.norm((1, 2, 3))

            # set delta on a one-endpoint-known range derives the other
            newv, _ = await prtype.normVirt('min', None, 5)
            newv, _ = await prtype.normVirt('delta', newv, 3)
            self.eq(('5', '8', '3'), newv)

            # set delta when min unknown but max known derives min
            base = (await prtype.norm(('?', '20')))[0]
            newv, _ = await prtype.normVirt('delta', base, 4)
            self.eq(('16', '20', '4'), newv)

            # currency lives in the virts dict
            newv, info = await prtype.normVirt('currency', (await prtype.norm((1, 2)))[0], 'usd')
            self.eq({'currency': ('USD', core.model.type('econ:currency').stortype)}, info['virts'])

            # errors
            with self.raises(s_exc.BadTypeValu):
                await prtype.norm((5, 2))

            with self.raises(s_exc.BadTypeValu):
                await prtype.norm('1.0')  # no dash

            with self.raises(s_exc.BadTypeValu):
                # over-constraint: both endpoints known
                await prtype.normVirt('delta', (await prtype.norm((1, 5)))[0], 2)

            with self.raises(s_exc.BadTypeValu):
                # negative delta
                await prtype.normVirt('delta', (await prtype.norm(('?', '5')))[0], -1)

            with self.raises(s_exc.BadTypeValu):
                await prtype.normVirt('currency', None, 'usd')

            with self.raises(s_exc.NoSuchVirt):
                prtype.getVirtType('newp')

    async def test_pricechange(self):

        async with self.getTestCore() as core:

            pctype = core.model.type('econ:pricechange')

            # norm from a (start, end) pair, derives delta and rate
            self.eq(('100', '125', '25', '25'), (await pctype.norm((100, 125)))[0])

            # negative delta + rate
            self.eq(('100', '75', '-25', '-25'), (await pctype.norm((100, 75)))[0])

            # rate omitted (unknown) when start == 0
            self.eq(('0', '5', '5', '?'), (await pctype.norm((0, 5)))[0])

            # getters
            valu = (await pctype.norm((100, 125)))[0]
            self.eq('100', pctype.getVirtGetr('start')((valu, None, None)))
            self.eq('125', pctype.getVirtGetr('end')((valu, None, None)))
            self.eq('25', pctype.getVirtGetr('delta')((valu, None, None)))
            self.eq('25', pctype.getVirtGetr('rate')((valu, None, None)))

            # repr
            self.eq(('100', '75'), pctype.repr((await pctype.norm((100, 75)))[0]))

            # pricechange accepts the "start-end" string form
            self.eq(('100', '125', '25', '25'), (await pctype.norm('100-125'))[0])

            # a trailing currency code is captured into the currency virt
            norm, info = await pctype.norm('99-32USD')
            self.eq('99', norm[0])
            self.eq('32', norm[1])
            self.eq('-67', norm[2])
            self.eq({'currency': ('USD', core.model.type('econ:currency').stortype)}, info['virts'])
            self.eq('99-32USD', pctype.reprWithVirts(norm, info['virts']))

            # no currency -> the plain 2-tuple repr
            norm, info = await pctype.norm('100-125')
            self.eq(('100', '125'), pctype.reprWithVirts(norm, None))

            # a negative endpoint can not be expressed as a string (ambiguous
            # with the separator); use a (start, end) tuple instead
            with self.raises(s_exc.BadTypeValu):
                await pctype.norm('-25-100')

            with self.raises(s_exc.BadTypeValu):
                await pctype.norm('100-')

            # unknown sentinel
            self.eq(('?', '?', '?', '?'), (await pctype.norm('?'))[0])

            # set start on empty
            newv, _ = await pctype.normVirt('start', None, 100)
            self.eq(('100', '?', '?', '?'), newv)

            # set end recomputes delta and rate
            newv, _ = await pctype.normVirt('end', newv, 150)
            self.eq(('100', '150', '50', '50'), newv)

            # set signed delta derives the unknown endpoint
            newv, _ = await pctype.normVirt('start', None, 100)
            newv, _ = await pctype.normVirt('delta', newv, -40)
            self.eq(('100', '60', '-40', '-40'), newv)

            # set rate derives the unknown end
            newv, _ = await pctype.normVirt('start', None, 100)
            newv, _ = await pctype.normVirt('rate', newv, 20)
            self.eq(('100', '120', '20', '20'), newv)

            # set delta when start unknown but end known derives start
            base = (await pctype.norm(('?', '?')))[0]
            base, _ = await pctype.normVirt('end', base, 50)
            base, _ = await pctype.normVirt('delta', base, 10)
            self.eq(('40', '50', '10', '25'), base)

            # set end on empty
            newv, info = await pctype.normVirt('end', None, 80)
            self.eq(('?', '80', '?', '?'), newv)
            self.false(info['merge'])

            # set end when start unknown but delta known derives start
            base = (await pctype.norm(('?', '?')))[0]
            base, _ = await pctype.normVirt('delta', base, 10)
            self.eq(('?', '?', '10', '?'), base)
            newv, _ = await pctype.normVirt('end', base, 50)
            self.eq(('40', '50', '10', '25'), newv)

            # set start when end unknown but delta known derives end
            base = (await pctype.norm(('?', '?')))[0]
            base, _ = await pctype.normVirt('delta', base, 10)
            newv, _ = await pctype.normVirt('start', base, 40)
            self.eq(('40', '50', '10', '25'), newv)

            # set start when end unknown but rate known derives end
            base = (await pctype.norm(('?', '?')))[0]
            base, _ = await pctype.normVirt('rate', base, 20)
            self.eq(('?', '?', '?', '20'), base)
            newv, _ = await pctype.normVirt('start', base, 100)
            self.eq(('100', '120', '20', '20'), newv)

            # set rate on a fully-unknown change just records the rate
            base = (await pctype.norm('?'))[0]
            newv, _ = await pctype.normVirt('rate', base, 5)
            self.eq(('?', '?', '?', '5'), newv)

            # set delta to the unknown sentinel on a start-known change leaves
            # the derived end unknown (_deriveEnd returns the sentinel)
            base = (await pctype.norm(('?', '?')))[0]
            base, _ = await pctype.normVirt('start', base, 100)
            newv, _ = await pctype.normVirt('delta', base, '?')
            self.eq(('100', '?', '?', '?'), newv)

            # set delta to the unknown sentinel on an end-known change leaves
            # the derived start unknown (_deriveStart returns the sentinel)
            base = (await pctype.norm(('?', '?')))[0]
            base, _ = await pctype.normVirt('end', base, 100)
            newv, _ = await pctype.normVirt('delta', base, '?')
            self.eq(('?', '100', '?', '?'), newv)

            # getters return None for the unknown sentinel
            unkv = (await pctype.norm('?'))[0]
            self.none(pctype.getVirtGetr('start')((unkv, None, None)))
            self.none(pctype.getVirtGetr('end')((unkv, None, None)))
            self.none(pctype.getVirtGetr('delta')((unkv, None, None)))
            self.none(pctype.getVirtGetr('rate')((unkv, None, None)))

            # currency
            newv, info = await pctype.normVirt('currency', (await pctype.norm((1, 2)))[0], 'usd')
            self.eq({'currency': ('USD', core.model.type('econ:currency').stortype)}, info['virts'])

            # norm requires a 2-tuple
            with self.raises(s_exc.BadTypeValu):
                await pctype.norm((1, 2, 3))

            # over-constraint errors
            with self.raises(s_exc.BadTypeValu):
                await pctype.normVirt('delta', (await pctype.norm((1, 5)))[0], 2)

            with self.raises(s_exc.BadTypeValu):
                await pctype.normVirt('rate', (await pctype.norm((1, 5)))[0], 2)

            with self.raises(s_exc.BadTypeValu):
                await pctype.normVirt('currency', None, 'usd')

    async def test_pricechange_names(self):

        async with self.getTestCore() as core:

            pctype = core.model.type('econ:pricechange')
            rntype = pctype.clone({'names': {'start': 'allocated', 'end': 'spent', 'delta': 'variance'}})

            # the renamed part virts are exposed under the new names
            self.eq(['allocated', 'currency', 'rate', 'spent', 'variance'], sorted(rntype.virts.keys()))
            self.eq(('allocated', 'spent', 'variance', 'rate'), rntype.parts)

            # norm is positional and unchanged; variance == spent - allocated
            norm = (await rntype.norm((5000, 1000)))[0]
            self.eq(('5000', '1000', '-4000', '-80'), norm)

            # getters resolve via the renamed names
            self.eq('5000', rntype.getVirtGetr('allocated')((norm, None, None)))
            self.eq('1000', rntype.getVirtGetr('spent')((norm, None, None)))
            self.eq('-4000', rntype.getVirtGetr('variance')((norm, None, None)))
            self.eq('-80', rntype.getVirtGetr('rate')((norm, None, None)))

            # setters resolve via the renamed names
            newv, _ = await rntype.normVirt('allocated', None, 5000)
            self.eq(('5000', '?', '?', '?'), newv)
            newv, _ = await rntype.normVirt('spent', newv, 1000)
            self.eq(('5000', '1000', '-4000', '-80'), newv)

            newv, _ = await rntype.normVirt('allocated', None, 100)
            newv, _ = await rntype.normVirt('variance', newv, -40)
            self.eq(('100', '60', '-40', '-40'), newv)

            # comparators on the renamed parts translate back to the canonical
            # names before reaching the storage layer
            self.eq((('start<', '6000', rntype.stortype),), await rntype.getStorCmprs('<', 6000, virt='allocated'))
            self.eq((('end>', '10', rntype.stortype),), await rntype.getStorCmprs('>', 10, virt='spent'))
            self.eq((('delta>', '0', rntype.stortype),), await rntype.getStorCmprs('>', 0, virt='variance'))

            # unrenamed parts still lift under their own name
            cmprs = await rntype.getStorCmprs('<', 5, virt='rate')
            self.eq('rate<', cmprs[0][0])

            # renaming a non-part virt or an unknown name is rejected
            with self.raises(s_exc.BadTypeDef):
                pctype.clone({'names': {'currency': 'money'}})

            with self.raises(s_exc.BadTypeDef):
                pctype.clone({'names': {'nosuch': 'nope'}})

    async def test_loc(self):
        model = s_datamodel.getBaseModel()
        loctype = model.types.get('loc')

        self.eq('us.va', (await loctype.norm('US.    VA'))[0])
        self.eq('', (await loctype.norm(''))[0])
        self.eq('us.va.ओं.reston', (await loctype.norm('US.    VA.ओं.reston'))[0])

        async with self.getTestCore() as core:
            self.eq(1, await core.count('[test:int=1 :loc=us.va.syria]'))
            self.eq(1, await core.count('[test:int=2 :loc=us.va.sydney]'))
            self.eq(1, await core.count('[test:int=3 :loc=""]'))
            self.eq(1, await core.count('[test:int=4 :loc=us.va.fairfax]'))
            self.eq(1, await core.count('[test:int=5 :loc=us.va.fairfax.reston]'))
            self.eq(1, await core.count('[test:int=6 :loc=us.va.fairfax.restonheights]'))
            self.eq(1, await core.count('[test:int=7 :loc=us.va.fairfax.herndon]'))
            self.eq(1, await core.count('[test:int=8 :loc=us.ca.sandiego]'))
            self.eq(1, await core.count('[test:int=9 :loc=us.ओं]'))
            self.eq(1, await core.count('[test:int=10 :loc=us.va]'))
            self.eq(1, await core.count('[test:int=11 :loc=us]'))
            self.eq(1, await core.count('[test:int=12 :loc=us]'))

            self.eq(1, await core.count('test:int:loc=us.va.syria'))
            self.eq(1, await core.count('test:int:loc=us.va.sydney'))
            self.eq(0, await core.count('test:int:loc=us.va.sy'))
            self.eq(1, await core.count('test:int:loc=us.va'))
            self.eq(0, await core.count('test:int:loc=us.v'))
            self.eq(2, await core.count('test:int:loc=us'))
            self.eq(0, await core.count('test:int:loc=u'))
            self.eq(1, await core.count('test:int:loc=""'))

            self.eq(1, await core.count('test:int +:loc="us.va. syria"'))
            self.eq(1, await core.count('test:int +:loc=us.va.sydney'))
            self.eq(0, await core.count('test:int +:loc=us.va.sy'))
            self.eq(1, await core.count('test:int +:loc=us.va'))
            self.eq(0, await core.count('test:int +:loc=us.v'))
            self.eq(2, await core.count('test:int +:loc=us'))
            self.eq(0, await core.count('test:int +:loc=u'))
            self.eq(1, await core.count('test:int +:loc=""'))

            self.eq(0, await core.count('test:int +:loc^=u'))
            self.eq(11, await core.count('test:int +:loc^=us'))
            self.eq(0, await core.count('test:int +:loc^=us.'))
            self.eq(0, await core.count('test:int +:loc^=us.v'))
            self.eq(7, await core.count('test:int +:loc^=us.va'))
            self.eq(0, await core.count('test:int +:loc^=us.va.'))
            self.eq(0, await core.count('test:int +:loc^=us.va.fair'))
            self.eq(4, await core.count('test:int +:loc^=us.va.fairfax'))
            self.eq(0, await core.count('test:int +:loc^=us.va.fairfax.'))
            self.eq(1, await core.count('test:int +:loc^=us.va.fairfax.reston'))
            self.eq(0, await core.count('test:int +:loc^=us.va.fairfax.chantilly'))
            self.eq(1, await core.count('test:int +:loc^=""'))
            self.eq(0, await core.count('test:int +:loc^=23'))

            self.eq(0, await core.count('test:int:loc^=u'))
            self.eq(11, await core.count('test:int:loc^=us'))
            self.eq(0, await core.count('test:int:loc^=us.'))
            self.eq(0, await core.count('test:int:loc^=us.v'))
            self.eq(7, await core.count('test:int:loc^=us.va'))
            self.eq(0, await core.count('test:int:loc^=us.va.'))
            self.eq(0, await core.count('test:int:loc^=us.va.fair'))
            self.eq(4, await core.count('test:int:loc^=us.va.fairfax'))
            self.eq(0, await core.count('test:int:loc^=us.va.fairfax.'))
            self.eq(1, await core.count('test:int:loc^=us.va.fairfax.reston'))
            self.eq(0, await core.count('test:int:loc^=us.va.fairfax.chantilly'))
            self.eq(1, await core.count('test:int:loc^=""'))
            self.eq(0, await core.count('test:int:loc^=23'))

    async def test_range(self):
        model = s_datamodel.getBaseModel()
        t = model.type('range')

        await self.asyncraises(s_exc.BadTypeValu, t.norm(1))
        await self.asyncraises(s_exc.BadTypeValu, t.norm('1'))
        await self.asyncraises(s_exc.BadTypeValu, t.norm((1,)))
        await self.asyncraises(s_exc.BadTypeValu, t.norm((1, -1)))

        norm, info = await t.norm((0, 0))
        self.eq(norm, (0, 0))
        self.eq(info['subs']['min'][1], 0)
        self.eq(info['subs']['max'][1], 0)

        self.eq((10, 20), (await t.norm('10-20'))[0])

        norm, info = await t.norm((-10, 0xFF))
        self.eq(norm, (-10, 255))
        self.eq(info['subs']['min'][1], -10)
        self.eq(info['subs']['max'][1], 255)

        self.eq(t.repr((-10, 0xFF)), ('-10', '255'))

        # Invalid Config
        self.raises(s_exc.BadTypeDef, model.type('range').clone, {'type': None})
        self.raises(s_exc.BadTypeDef, model.type('range').clone, {'type': ('inet:ip', {})})  # inet is not loaded yet

    async def test_range_filter(self):
        async with self.getTestCore() as core:
            self.len(1, await core.nodes('[test:str=a :tick=19990101]'))
            self.len(1, await core.nodes('[test:str=b :seen=(20100101, 20110101) :tick=20151207]'))
            self.len(1, await core.nodes('[test:str=m :tick=20200101]'))
            self.len(1, await core.nodes('[test:guid=$valu]', opts={'vars': {'valu': 'C' * 32}}))
            self.len(1, await core.nodes('[test:guid=$valu]', opts={'vars': {'valu': 'F' * 32}}))
            self.len(1, await core.nodes('[test:comp=(2048, horton)]'))
            self.len(1, await core.nodes('[test:comp=(4096, whoville)]'))
            self.len(1, await core.nodes('[test:comp=(9001, "A mean one")]'))
            self.len(1, await core.nodes('[test:comp=(9999, greenham)]'))
            self.len(1, await core.nodes('[test:comp=(40000, greeneggs)]'))

            self.len(0, await core.nodes('test:str=a +:tick*range=(20000101, 20101201)'))
            nodes = await core.nodes('test:str +:tick*range=(19701125, 20151212)')
            self.eq({node.ndef[1] for node in nodes}, {'a', 'b'})
            nodes = await core.nodes('test:comp +:haha*range=(grinch, meanone)')
            self.eq({node.ndef[1] for node in nodes}, {(2048, 'horton')})
            nodes = await core.nodes('test:comp +test:comp*range=((1024, grinch), (4096, zemeanone))')
            self.eq({node.ndef[1] for node in nodes}, {(2048, 'horton'), (4096, 'whoville')})
            guid0 = 'B' * 32
            guid1 = 'D' * 32
            nodes = await core.nodes(f'test:guid +test:guid*range=({guid0}, {guid1})')
            self.eq({node.ndef[1] for node in nodes}, {'c' * 32})
            nodes = await core.nodes('test:int -> test:comp:hehe +test:comp*range=((1000, grinch), (4000, whoville))')
            self.eq({node.ndef[1] for node in nodes}, {(2048, 'horton')})

            # The following tests show range working against a string
            self.len(2, await core.nodes('test:str*range=(b, m)'))
            self.len(2, await core.nodes('test:str +test:str*range=(b, m)'))

            # Range against a integer
            valus = (-1, 0, 1, 2)
            self.len(4, await core.nodes('for $valu in $vals {[test:int=$valu]}', opts={'vars': {'vals': valus}}))
            self.len(3, await core.nodes('test:int*range=(0, 2)'))
            self.len(3, await core.nodes('test:int +test:int*range=(0, 2)'))
            self.len(1, await core.nodes('test:int*range=(-1, -1)'))
            self.len(1, await core.nodes('test:int +test:int*range=(-1, -1)'))

            # sad path
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:comp +:hehe*range=(0.0.0.0, 1.1.1.1, 6.6.6.6)')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:comp +:haha*range=(somestring,)')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:int +test:int*range=3456')

    async def test_str(self):

        model = s_datamodel.getBaseModel()

        lowr = model.type('str').clone({'lower': True})
        self.eq('foo', (await lowr.norm('FOO'))[0])

        uppr = model.type('str').clone({'upper': True})
        self.eq('FOO', (await uppr.norm('foo'))[0])

        with self.raises(s_exc.BadTypeDef):
            model.type('str').clone({'upper': True, 'lower': True})

        self.eq(True, await lowr.cmpr('xxherexx', '~=', 'here'))
        self.eq(False, await lowr.cmpr('xxherexx', '~=', '^here'))

        self.eq(True, await lowr.cmpr('foo', '!=', 'bar'))
        self.eq(False, await lowr.cmpr('foo', '!=', 'FOO'))

        self.eq(True, await lowr.cmpr('foobar', '^=', 'FOO'))
        self.eq(False, await lowr.cmpr('foubar', '^=', 'FOO'))

        # the prefix comparator ctor itself must normalize the prefix text the same way the lift does
        self.true(await (await lowr.getCmprCtor('^=')('FOO'))('foobar'))
        self.false(await (await lowr.getCmprCtor('^=')('FOO'))('foubar'))

        regx = model.type('str').clone({'regex': '^[a-f][0-9]+$'})
        self.eq('a333', (await regx.norm('a333'))[0])
        await self.asyncraises(s_exc.BadTypeValu, regx.norm('A333'))

        regl = model.type('str').clone({'regex': '^[a-f][0-9]+$', 'lower': True})
        self.eq('a333', (await regl.norm('a333'))[0])
        self.eq('a333', (await regl.norm('A333'))[0])

        byts = s_common.uhex('e2889e')

        # The real world is a harsh place.
        strp = model.type('str').clone({'strip': True})
        self.eq('foo', (await strp.norm('  foo \t'))[0])

        onespace = model.type('str').clone({'onespace': True})
        self.eq('foo', (await onespace.norm('  foo\t'))[0])
        self.eq('hehe haha', (await onespace.norm('hehe    haha'))[0])

        # value mapping (applied after case folding and strip)
        mapd = model.type('str').clone({'mapping': {'foo': 'bar', 'baz': 'faz'}})
        self.eq('bar', (await mapd.norm('foo'))[0])
        self.eq('faz', (await mapd.norm('baz'))[0])
        self.eq('other', (await mapd.norm('other'))[0])

        mapu = model.type('str').clone({'upper': True, 'mapping': {'$': 'USD'}})
        self.eq('USD', (await mapu.norm('$'))[0])
        self.eq('USD', (await mapu.norm('  $ '))[0])
        self.eq('GBP', (await mapu.norm('gbp'))[0])

        # the mapping is applied to the prefix value for ^= lifts as well
        self.eq(True, await mapu.cmpr('USDOLLAR', '^=', '$'))

        with self.raises(s_exc.BadTypeDef):
            model.type('str').clone({'mapping': 'newp'})

        enums = model.type('str').clone({'enums': 'hehe,haha,zork'})
        self.eq('hehe', (await enums.norm('hehe'))[0])
        self.eq('haha', (await enums.norm('haha'))[0])
        self.eq('zork', (await enums.norm('zork'))[0])
        await self.asyncraises(s_exc.BadTypeValu, enums.norm(1.23))
        await self.asyncraises(s_exc.BadTypeValu, enums.norm('zing'))

        strsubs = model.type('str').clone({'regex': r'(?P<first>[ab]+)(?P<last>[zx]+)'})
        norm, info = await strsubs.norm('aabbzxxxxxz')
        styp = model.type('str').typehash
        self.eq(info.get('subs'), {'first': (styp, 'aabb', {}), 'last': (styp, 'zxxxxxz', {})})

        flt = model.type('str').clone({})
        self.eq('0.0', (await flt.norm(0.0))[0])
        self.eq('-0.0', (await flt.norm(-0.0))[0])
        self.eq('2.65', (await flt.norm(2.65))[0])
        self.eq('2.65', (await flt.norm(2.65000000))[0])
        self.eq('0.65', (await flt.norm(00.65))[0])
        self.eq('42.0', (await flt.norm(42.0))[0])
        self.eq('42.0', (await flt.norm(42.))[0])
        self.eq('42.0', (await flt.norm(00042.00000))[0])
        self.eq('0.000000000000000000000000001', (await flt.norm(0.000000000000000000000000001))[0])
        self.eq('0.0000000000000000000000000000000000001', (await flt.norm(0.0000000000000000000000000000000000001))[0])
        self.eq('0.00000000000000000000000000000000000000000000001',
                (await flt.norm(0.00000000000000000000000000000000000000000000001))[0])
        self.eq('0.3333333333333333', (await flt.norm(0.333333333333333333333333333))[0])
        self.eq('0.4444444444444444', (await flt.norm(0.444444444444444444444444444))[0])
        self.eq('1234567890.1234567', (await flt.norm(1234567890.123456790123456790123456789))[0])
        self.eq('1234567891.1234567', (await flt.norm(1234567890.123456790123456790123456789 + 1))[0])
        self.eq('1234567890.1234567', (await flt.norm(1234567890.123456790123456790123456789 + 0.0000000001))[0])
        self.eq('2.718281828459045', (await flt.norm(2.718281828459045))[0])
        self.eq('1.23', (await flt.norm(s_stormtypes.Number(1.23)))[0])

    async def test_title(self):

        model = s_datamodel.getBaseModel()

        titl = model.type('title')
        text = model.type('text')

        # title collapses internal whitespace, strips, and preserves case
        self.eq('Foo Bar', (await titl.norm('  Foo   Bar  '))[0])

        # comparison and prefix are case insensitive
        self.eq(True, await titl.cmpr('Foo Bar', '=', 'foo bar'))
        self.eq(False, await titl.cmpr('Foo Bar', '!=', 'foo bar'))
        self.eq(True, await titl.cmpr('Foo Bar', '^=', 'FOO'))

        # title shares the case insensitive text storage
        self.eq(titl.stortype, text.stortype)

        # text remains multi-line and no longer strips by default
        self.eq('  multi\nline  ', (await text.norm('  multi\nline  '))[0])

    async def test_syntag(self):

        model = s_datamodel.getBaseModel()
        tagtype = model.type('syn:tag')

        self.eq('foo.bar', (await tagtype.norm(('FOO', ' BAR')))[0])
        self.eq('foo.st_lucia', (await tagtype.norm(('FOO', 'st.lucia')))[0])

        self.eq('foo.bar', (await tagtype.norm('FOO.BAR'))[0])
        self.eq('foo.bar', (await tagtype.norm('#foo.bar'))[0])
        self.eq('foo.bar', (await tagtype.norm('foo   .   bar'))[0])

        tag, info = await tagtype.norm('foo')
        subs = info.get('subs')
        self.none(subs.get('up'))
        self.eq('foo', subs.get('base')[1])
        self.eq(0, subs.get('depth')[1])

        tag, info = await tagtype.norm('foo.bar')
        subs = info.get('subs')
        self.eq('foo', subs.get('up')[1])

        self.eq('r_y', (await tagtype.norm('@#R)(Y'))[0])
        self.eq('foo.bar', (await tagtype.norm('foo\udcfe.bar'))[0])
        await self.asyncraises(s_exc.BadTypeValu, tagtype.norm('foo.'))
        await self.asyncraises(s_exc.BadTypeValu, tagtype.norm('foo..bar'))
        await self.asyncraises(s_exc.BadTypeValu, tagtype.norm('.'))
        await self.asyncraises(s_exc.BadTypeValu, tagtype.norm(''))
        # Tags including non-english unicode letters are okay
        self.eq('icon.ॐ', (await tagtype.norm('ICON.ॐ'))[0])
        # homoglyphs are also possible
        self.eq('is.ｂob.evil', (await tagtype.norm('is.\uff42ob.evil'))[0])

        self.true(await tagtype.cmpr('foo', '~=', 'foo'))
        self.false(await tagtype.cmpr('foo', '~=', 'foo.'))
        self.false(await tagtype.cmpr('foo', '~=', 'foo.bar'))
        self.false(await tagtype.cmpr('foo', '~=', 'foo.bar.'))
        self.true(await tagtype.cmpr('foo.bar', '~=', 'foo'))
        self.true(await tagtype.cmpr('foo.bar', '~=', 'foo.'))
        self.true(await tagtype.cmpr('foo.bar', '~=', 'foo.bar'))
        self.false(await tagtype.cmpr('foo.bar', '~=', 'foo.bar.'))
        self.false(await tagtype.cmpr('foo.bar', '~=', 'foo.bar.x'))
        self.true(await tagtype.cmpr('foo.bar.baz', '~=', 'bar'))
        self.true(await tagtype.cmpr('foo.bar.baz', '~=', '[a-z].bar.[a-z]'))
        self.true(await tagtype.cmpr('foo.bar.baz', '~=', r'^foo\.[a-z]+\.baz$'))
        self.true(await tagtype.cmpr('foo.bar.baz', '~=', r'\.baz$'))
        self.true(await tagtype.cmpr('bar.foo.baz', '~=', 'foo.'))
        self.false(await tagtype.cmpr('bar.foo.baz', '~=', r'^foo\.'))
        self.true(await tagtype.cmpr('foo.bar.xbazx', '~=', r'\.bar\.'))
        self.true(await tagtype.cmpr('foo.bar.xbazx', '~=', '.baz.'))
        self.false(await tagtype.cmpr('foo.bar.xbazx', '~=', r'\.baz\.'))

    async def test_time(self):

        model = s_datamodel.getBaseModel()
        ttime = model.types.get('time')

        with self.raises(s_exc.BadTypeValu):
            await ttime.norm('0000-00-00')

        self.gt(s_common.now(), (await ttime.norm('-1hour'))[0])

        with self.raises(s_exc.BadTypeDef):
            ttime.clone({'ismin': True, 'ismax': True})

        async with self.getTestCore() as core:

            t = core.model.type('test:time')

            # explicitly test our "future/ongoing" value...
            future = 0x7ffffffffffffffe
            self.eq((await t.norm('*'))[0], future)
            self.eq((await t.norm(future))[0], future)
            self.eq(t.repr(future), '*')

            unk = 0x7fffffffffffffff
            self.eq((await t.norm('?'))[0], unk)
            self.eq((await t.norm(unk))[0], unk)
            self.eq(t.repr(unk), '?')

            # Explicitly test our max time vs. future marker
            maxtime = 253402300799999999  # 9999/12/31 23:59:59.999999
            self.eq((await t.norm(maxtime))[0], maxtime)
            self.eq(t.repr(maxtime), '9999-12-31T23:59:59.999999Z')
            self.eq((await t.norm('9999-12-31T23:59:59.999999Z'))[0], maxtime)
            await self.asyncraises(s_exc.BadTypeValu, t.norm(maxtime + 1))

            tmax = t.clone({'maxfill': True})
            self.eq((await tmax.norm('9999-12-31T23:59:59.999999Z'))[0], maxtime)

            # a maxfill time collapses the filled tail of the time into a *
            self.eq(tmax.repr((await tmax.norm('2021-06-07?'))[0]), '2021-06-07*')
            self.eq(tmax.repr((await tmax.norm('2021-06-07T02?'))[0]), '2021-06-07T02:*')
            self.eq(tmax.repr((await tmax.norm('2021-06-07T02:03?'))[0]), '2021-06-07T02:03:*')
            self.eq(tmax.repr((await tmax.norm('2021-06-07T02:03:04?'))[0]), '2021-06-07T02:03:04.*')
            self.eq(tmax.repr((await tmax.norm('2021-06-07T02:03:04.123?'))[0]), '2021-06-07T02:03:04.123*')
            # coarser precisions keep the (real) last-of-window date
            self.eq(tmax.repr((await tmax.norm('2021-06?'))[0]), '2021-06-30*')
            self.eq(tmax.repr((await tmax.norm('2021?'))[0]), '2021-12-31*')
            # a fully-precise value has no filled tail to collapse
            self.eq(tmax.repr((await tmax.norm('2021-06-07T02:03:04.123456'))[0]), '2021-06-07T02:03:04.123456Z')
            # on a maxfill time a trailing * norms like the reprmax form it emits
            self.eq((await tmax.norm('2021-06-07*'))[0], (await tmax.norm('2021-06-07?'))[0])
            self.eq((await tmax.norm('2021-06-07T02:*'))[0], (await tmax.norm('2021-06-07T02?'))[0])
            # a non-maxfill time leaves a trailing * inert (no maxfill)
            self.eq((await t.norm('2021-06-07*'))[0], (await t.norm('2021-06-07'))[0])
            # the future/unknown markers are unaffected
            self.eq(tmax.repr((await tmax.norm('*'))[0]), '*')
            self.eq(tmax.repr((await tmax.norm('?'))[0]), '?')

            tick = (await t.norm('2014'))[0]
            self.eq(t.repr(tick), '2014-01-01T00:00:00Z')

            tock = (await t.norm('2015'))[0]

            await self.asyncraises(s_exc.BadTypeValu, t.cmpr('2015', 'range=', tick))

            prec = core.model.type('timeprecision')
            styp = prec.stortype

            self.eq(await prec.norm(4), (s_time.PREC_YEAR, {}))
            self.eq(await prec.norm('4'), (s_time.PREC_YEAR, {}))
            self.eq(await prec.norm('year'), (s_time.PREC_YEAR, {}))
            self.eq(prec.repr(s_time.PREC_YEAR), 'year')

            with self.raises(s_exc.BadTypeValu):
                await prec.norm('123')

            with self.raises(s_exc.BadTypeValu):
                await prec.norm(123)

            with self.raises(s_exc.BadTypeValu):
                prec.repr(123)

            self.eq(await t.norm('2025?'), (1735689600000000, {'virts': {'precision': (s_time.PREC_YEAR, styp)}}))
            self.eq(await t.norm('2025-04?'), (1743465600000000, {'virts': {'precision': (s_time.PREC_MONTH, styp)}}))
            self.eq(await t.norm('2025-04-05?'), (1743811200000000, {'virts': {'precision': (s_time.PREC_DAY, styp)}}))
            self.eq(await t.norm('2025-04-05 12?'), (1743854400000000, {'virts': {'precision': (s_time.PREC_HOUR, styp)}}))
            self.eq(await t.norm('2025-04-05 12:34?'), (1743856440000000, {'virts': {'precision': (s_time.PREC_MINUTE, styp)}}))
            self.eq(await t.norm('2025-04-05 12:34:56?'), (1743856496000000, {'virts': {'precision': (s_time.PREC_SECOND, styp)}}))
            self.eq(await t.norm('2025-04-05 12:34:56.1?'), (1743856496100000, {'virts': {'precision': (s_time.PREC_MILLI, styp)}}))
            self.eq(await t.norm('2025-04-05 12:34:56.12?'), (1743856496120000, {'virts': {'precision': (s_time.PREC_MILLI, styp)}}))
            self.eq(await t.norm('2025-04-05 12:34:56.123?'), (1743856496123000, {'virts': {'precision': (s_time.PREC_MILLI, styp)}}))
            self.eq(await t.norm('2025-04-05 12:34:56.1234?'), (1743856496123400, {}))
            self.eq(await t.norm('2025-04-05 12:34:56.12345?'), (1743856496123450, {}))
            self.eq(await t.norm('2025-04-05 12:34:56.123456?'), (1743856496123456, {}))
            self.eq(await t.norm('2025-04-05 12:34:56.123456'), (1743856496123456, {}))

            exp = (1735689600000000, {'virts': {'precision': (s_time.PREC_YEAR, styp)}})
            self.eq(await t.norm(1743856496123456, prec=s_time.PREC_YEAR), exp)

            exp = (1735689600000000, {'virts': {'precision': (s_time.PREC_YEAR, styp)}})
            self.eq(await t.norm(decimal.Decimal(1743856496123456), prec=s_time.PREC_YEAR), exp)

            exp = (1735689600000000, {'virts': {'precision': (s_time.PREC_YEAR, styp)}})
            self.eq(await t.norm(s_stormtypes.Number(1743856496123456), prec=s_time.PREC_YEAR), exp)

            exp = (1743856496123456, {})
            self.eq(await t.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_MICRO), exp)

            exp = (1743856496123000, {'virts': {'precision': (s_time.PREC_MILLI, styp)}})
            self.eq(await t.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_MILLI), exp)

            exp = (1743856496000000, {'virts': {'precision': (s_time.PREC_SECOND, styp)}})
            self.eq(await t.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_SECOND), exp)

            exp = (1743856440000000, {'virts': {'precision': (s_time.PREC_MINUTE, styp)}})
            self.eq(await t.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_MINUTE), exp)

            exp = (1743854400000000, {'virts': {'precision': (s_time.PREC_HOUR, styp)}})
            self.eq(await t.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_HOUR), exp)

            exp = (1743811200000000, {'virts': {'precision': (s_time.PREC_DAY, styp)}})
            self.eq(await t.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_DAY), exp)

            exp = (1743465600000000, {'virts': {'precision': (s_time.PREC_MONTH, styp)}})
            self.eq(await t.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_MONTH), exp)

            exp = (1735689600000000, {'virts': {'precision': (s_time.PREC_YEAR, styp)}})
            self.eq(await t.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_YEAR), exp)

            tmax = t.clone({'maxfill': True})

            exp = (1743856496123456, {})
            self.eq(await tmax.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_MICRO), exp)

            exp = (1743856496123999, {'virts': {'precision': (s_time.PREC_MILLI, styp)}})
            self.eq(await tmax.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_MILLI), exp)

            exp = (1743856496999999, {'virts': {'precision': (s_time.PREC_SECOND, styp)}})
            self.eq(await tmax.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_SECOND), exp)

            exp = (1743856499999999, {'virts': {'precision': (s_time.PREC_MINUTE, styp)}})
            self.eq(await tmax.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_MINUTE), exp)

            exp = (1743857999999999, {'virts': {'precision': (s_time.PREC_HOUR, styp)}})
            self.eq(await tmax.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_HOUR), exp)

            exp = (1743897599999999, {'virts': {'precision': (s_time.PREC_DAY, styp)}})
            self.eq(await tmax.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_DAY), exp)

            exp = (1746057599999999, {'virts': {'precision': (s_time.PREC_MONTH, styp)}})
            self.eq(await tmax.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_MONTH), exp)

            exp = (1767225599999999, {'virts': {'precision': (s_time.PREC_YEAR, styp)}})
            self.eq(await tmax.norm('2025-04-05 12:34:56.123456', prec=s_time.PREC_YEAR), exp)

            self.eq(maxtime, (await tmax.norm('9999-12-31T23:59:59.999999Z', prec=s_time.PREC_YEAR))[0])
            self.eq(maxtime, (await tmax.norm('9999-12-31T23:59:59.999999Z', prec=s_time.PREC_MONTH))[0])
            self.eq(maxtime, (await tmax.norm('9999-12-31T23:59:59.999999Z', prec=s_time.PREC_DAY))[0])
            self.eq(maxtime, (await tmax.norm('9999-12-31T23:59:59.999999Z', prec=s_time.PREC_HOUR))[0])
            self.eq(maxtime, (await tmax.norm('9999-12-31T23:59:59.999999Z', prec=s_time.PREC_MINUTE))[0])
            self.eq(maxtime, (await tmax.norm('9999-12-31T23:59:59.999999Z', prec=s_time.PREC_SECOND))[0])
            self.eq(maxtime, (await tmax.norm('9999-12-31T23:59:59.999999Z', prec=s_time.PREC_MILLI))[0])

            with self.raises(s_exc.BadTypeValu):
                await tmax.norm('2025-04-05 12:34:56.123456', prec=123)

            with self.raises(s_exc.BadTypeDef):
                await core.addType('test:int', 'time', {'precision': 'newp'}, {})

            self.len(1, await core.nodes('[(test:str=a :tick=2014)]'))
            self.len(1, await core.nodes('[(test:str=b :tick=2015)]'))
            self.len(1, await core.nodes('[(test:str=c :tick=2016)]'))
            self.len(1, await core.nodes('[(test:str=d :tick=now)]'))

            nodes = await core.nodes('test:str:tick=2014')
            self.eq({node.ndef[1] for node in nodes}, {'a'})

            nodes = await core.nodes('test:str:tick*range=(2014, 2015)')
            self.eq({node.ndef[1] for node in nodes}, {'a', 'b'})

            nodes = await core.nodes('test:str:tick=201401*')
            self.eq({node.ndef[1] for node in nodes}, {'a'})

            utc = datetime.timezone.utc
            delta = datetime.datetime.now(tz=utc) - datetime.datetime(2014, 1, 1, tzinfo=utc)
            days = delta.days + 14
            nodes = await core.nodes(f'test:str:tick*range=("-{days} days", now)')
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

            self.true(await t.cmpr('2015', '>=', '20140202'))
            self.true(await t.cmpr('2015', '>=', '2015'))
            self.true(await t.cmpr('2015', '>', '20140202'))
            self.false(await t.cmpr('2015', '>', '2015'))

            self.true(await t.cmpr('20150202', '<=', '2016'))
            self.true(await t.cmpr('20150202', '<=', '2016'))
            self.true(await t.cmpr('20150202', '<', '2016'))
            self.false(await t.cmpr('2015', '<', '2015'))

            self.eq(1, await core.count('test:str +:tick=2015'))

            self.eq(1, await core.count('test:str +:tick*range=($test, "+- 2day")',
                                            opts={'vars': {'test': '2015'}}))

            self.eq(1, await core.count('test:str +:tick*range=(now, "-+ 1day")'))

            self.eq(1, await core.count('test:str +:tick*range=(2015, "+1 day")'))
            self.eq(1, await core.count('test:str +:tick*range=(20150102, "-3 day")'))
            self.eq(0, await core.count('test:str +:tick*range=(20150201, "+1 day")'))
            self.eq(1, await core.count('test:str +:tick*range=(20150102, "+- 2day")'))
            self.eq(2, await core.count('test:str +:tick*range=(2015, 2016)'))
            self.eq(0, await core.count('test:str +:tick*range=(2016, 2015)'))

            self.eq(2, await core.count('test:str:tick*range=(2015, 2016)'))
            self.eq(0, await core.count('test:str:tick*range=(2016, 2015)'))

            self.eq(1, await core.count('test:str:tick*range=(2015, "+1 day")'))
            self.eq(4, await core.count('test:str:tick*range=(2014, "now")'))
            self.eq(0, await core.count('test:str:tick*range=(20150201, "+1 day")'))
            self.eq(1, await core.count('test:str:tick*range=(now, "+-1 day")'))
            self.eq(0, await core.count('test:str:tick*range=(now, "+1 day")'))

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

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str +:tick*range=(2015)')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str +:tick*range=(2015, 2016, 2017)')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str +:tick*range=("?", "+1 day")')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str +:tick*range=(2000, "?+1 day")')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str:tick*range=("?", "+1 day")')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str:tick*range=(2000, "?+1 day")')

            self.len(1, await core.nodes('[(test:str=t1 :tick="2018/12/02 23:59:59.000")]'))
            self.len(1, await core.nodes('[(test:str=t2 :tick="2018/12/03")]'))
            self.len(1, await core.nodes('[(test:str=t3 :tick="2018/12/03 00:00:01.000")]'))

            self.eq(0, await core.count('test:str:tick*range=(2018/12/01, "+24 hours")'))
            self.eq(2, await core.count('test:str:tick*range=(2018/12/01, "+48 hours")'))

            self.eq(0, await core.count('test:str:tick*range=(2018/12/02, "+23 hours")'))
            self.eq(1, await core.count('test:str:tick*range=(2018/12/02, "+86399 seconds")'))
            self.eq(2, await core.count('test:str:tick*range=(2018/12/02, "+24 hours")'))
            self.eq(3, await core.count('test:str:tick*range=(2018/12/02, "+86401 seconds")'))
            self.eq(3, await core.count('test:str:tick*range=(2018/12/02, "+25 hours")'))

            self.len(0, await core.nodes('test:guid | delnode --force'))
            await core.nodes('[ test:guid=* :tick=20211031020202 ]')

            # test * suffix syntax
            self.len(1, await core.nodes('test:guid:tick=2021*'))
            self.len(1, await core.nodes('test:guid:tick=202110*'))
            self.len(1, await core.nodes('test:guid:tick=20211031*'))
            self.len(1, await core.nodes('test:guid:tick=2021103102*'))
            self.len(1, await core.nodes('test:guid:tick=202110310202*'))
            self.len(1, await core.nodes('test:guid:tick=20211031020202*'))

            self.len(0, await core.nodes('test:guid:tick=2022*'))
            self.len(0, await core.nodes('test:guid:tick=202210*'))
            self.len(0, await core.nodes('test:guid:tick=20221031*'))
            self.len(0, await core.nodes('test:guid:tick=2022103102*'))
            self.len(0, await core.nodes('test:guid:tick=202210310202*'))
            self.len(0, await core.nodes('test:guid:tick=20221031020202*'))

            self.len(1, await core.nodes('test:guid +:tick=2021*'))
            self.len(1, await core.nodes('test:guid +:tick=202110*'))
            self.len(1, await core.nodes('test:guid +:tick=20211031*'))
            self.len(1, await core.nodes('test:guid +:tick=2021103102*'))
            self.len(1, await core.nodes('test:guid +:tick=202110310202*'))
            self.len(1, await core.nodes('test:guid +:tick=20211031020202*'))

            self.len(0, await core.nodes('test:guid -:tick=2021*'))
            self.len(0, await core.nodes('test:guid -:tick=202110*'))
            self.len(0, await core.nodes('test:guid -:tick=20211031*'))
            self.len(0, await core.nodes('test:guid -:tick=2021103102*'))
            self.len(0, await core.nodes('test:guid -:tick=202110310202*'))
            self.len(0, await core.nodes('test:guid -:tick=20211031020202*'))

            # test <= time * suffix syntax
            self.len(1, await core.nodes('test:guid:tick<=2021*'))
            self.len(1, await core.nodes('test:guid:tick<=202110*'))
            self.len(1, await core.nodes('test:guid:tick<=20211031*'))
            self.len(1, await core.nodes('test:guid:tick<=2021103102*'))
            self.len(1, await core.nodes('test:guid:tick<=202110310202*'))
            self.len(1, await core.nodes('test:guid:tick<=20211031020202*'))

            self.len(0, await core.nodes('test:guid:tick<=2020*'))
            self.len(0, await core.nodes('test:guid:tick<=202010*'))
            self.len(0, await core.nodes('test:guid:tick<=20201031*'))
            self.len(0, await core.nodes('test:guid:tick<=2020103102*'))
            self.len(0, await core.nodes('test:guid:tick<=202010310202*'))
            self.len(0, await core.nodes('test:guid:tick<=20201031020202*'))

            self.len(1, await core.nodes('test:guid +:tick<=2021*'))
            self.len(1, await core.nodes('test:guid +:tick<=202110*'))
            self.len(1, await core.nodes('test:guid +:tick<=20211031*'))
            self.len(1, await core.nodes('test:guid +:tick<=2021103102*'))
            self.len(1, await core.nodes('test:guid +:tick<=202110310202*'))
            self.len(1, await core.nodes('test:guid +:tick<=20211031020202*'))

            self.len(0, await core.nodes('test:guid -:tick<=2021*'))
            self.len(0, await core.nodes('test:guid -:tick<=202110*'))
            self.len(0, await core.nodes('test:guid -:tick<=20211031*'))
            self.len(0, await core.nodes('test:guid -:tick<=2021103102*'))
            self.len(0, await core.nodes('test:guid -:tick<=202110310202*'))
            self.len(0, await core.nodes('test:guid -:tick<=20211031020202*'))

            # test <= time * suffix syntax
            self.len(1, await core.nodes('test:guid:tick<2021*'))
            self.len(1, await core.nodes('test:guid:tick<202110*'))
            self.len(1, await core.nodes('test:guid:tick<20211031*'))
            self.len(1, await core.nodes('test:guid:tick<2021103102*'))
            self.len(1, await core.nodes('test:guid:tick<202110310202*'))
            self.len(1, await core.nodes('test:guid:tick<20211031020202*'))

            self.len(0, await core.nodes('test:guid:tick<2020*'))
            self.len(0, await core.nodes('test:guid:tick<202010*'))
            self.len(0, await core.nodes('test:guid:tick<20201031*'))
            self.len(0, await core.nodes('test:guid:tick<2020103102*'))
            self.len(0, await core.nodes('test:guid:tick<202010310202*'))
            self.len(0, await core.nodes('test:guid:tick<20201031020202*'))

            self.len(1, await core.nodes('test:guid +:tick<2021*'))
            self.len(1, await core.nodes('test:guid +:tick<202110*'))
            self.len(1, await core.nodes('test:guid +:tick<20211031*'))
            self.len(1, await core.nodes('test:guid +:tick<2021103102*'))
            self.len(1, await core.nodes('test:guid +:tick<202110310202*'))
            self.len(1, await core.nodes('test:guid +:tick<20211031020202*'))

            self.len(0, await core.nodes('test:guid -:tick<2021*'))
            self.len(0, await core.nodes('test:guid -:tick<202110*'))
            self.len(0, await core.nodes('test:guid -:tick<20211031*'))
            self.len(0, await core.nodes('test:guid -:tick<2021103102*'))
            self.len(0, await core.nodes('test:guid -:tick<202110310202*'))
            self.len(0, await core.nodes('test:guid -:tick<20211031020202*'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:guid:tick=202*')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:guid:tick=202110310202021*')

        async with self.getTestCore() as core:

            nodes = await core.nodes('[test:str=a :tick=2014]')
            self.len(1, nodes)
            self.len(1, await core.nodes('[test:int=$valu]', opts={'vars': {'valu': nodes[0].get('tick')[1]}}))
            nodes = await core.nodes('[test:str=b :tick=2015]')
            self.len(1, await core.nodes('[test:int=$valu]', opts={'vars': {'valu': nodes[0].get('tick')[1]}}))
            self.len(1, nodes)
            nodes = await core.nodes('[test:str=c :tick=2016]')
            self.len(1, await core.nodes('[test:int=$valu]', opts={'vars': {'valu': nodes[0].get('tick')[1]}}))
            self.len(1, nodes)
            nodes = await core.nodes('[test:str=d :tick=now]')
            self.len(1, await core.nodes('[test:int=$valu]', opts={'vars': {'valu': nodes[0].get('tick')[1]}}))
            self.len(1, nodes)

            q = 'test:int $end=$node.value test:str:tick*range=(2015, $end) -test:int'
            nodes = await core.nodes(q)
            self.len(6, nodes)
            self.eq({node.ndef[1] for node in nodes}, {'b', 'c', 'd'})

            nodes = await core.nodes('[test:str=e :tick=? :tick=2024]')
            self.propeq(nodes[0], 'tick', 1704067200000000)

            retn = await core.callStorm('test:str=a return($lib.trycast(time, :tick))')
            self.eq(retn, (True, 1388534400000000))

            # norming a storm typed value through the time type: an equivalent
            # time typed Valu carrying a precision virt is reused as-is
            self.eq(1735689600000000, await core.callStorm("$x=$lib.cast(time, '2025?') return($lib.cast(time, $x))"))

            # a non-time typed Valu (duration) cast to time re-norms through
            # the time type rather than reusing the value
            self.eq(100, await core.callStorm('$d=$lib.cast(duration, (100)) return($lib.cast(time, $d))'))

            # a NodeRef cast to time norms its carried value
            self.eq(1577836800000,
                    await core.callStorm('$r=$lib.cast(test:int, (1577836800000)) return($lib.cast(time, $r))'))

    async def test_types_long_indx(self):

        aaaa = 'A' * 200
        url = f'http://vertex.link/visi?fuzz0={aaaa}&fuzz1={aaaa}'

        async with self.getTestCore() as core:
            opts = {'vars': {'url': url}}
            self.len(1, await core.nodes('[ it:exec:fetch="*" :url=$url ]', opts=opts))
            self.len(1, await core.nodes('it:exec:fetch:url=$url', opts=opts))

    async def test_types_array(self):

        mdef = {
            'types': (
                ('test:witharray', ('guid', {}), {
                    'props': (
                        ('ips', ('inet:ip', {}), {'array': {}}),
                        ('fqdns', ('inet:fqdn', {}), {'array': {'uniq': True, 'sorted': True, 'split': ','}}),
                    ),
                }),
            ),
        }
        async with self.getTestCore() as core:

            core.model.addModelDefs([mdef])

            with self.raises(s_exc.BadTypeDef):
                await core.addFormProp('test:int', '_hehe', ('array', {}), {'array': {}})

            with self.raises(s_exc.BadTypeDef):
                await core.addFormProp('test:int', '_hehe', ('newp', {}), {'array': {}})

            nodes = await core.nodes('[ test:witharray=* :ips=(1.2.3.4, 5.6.7.8) ]')
            self.len(1, nodes)

            # create a long array (fails pre-020)
            arr = ','.join([f'[4, {i}]' for i in range(300)])
            nodes = await core.nodes(f'[ test:witharray=* :ips=([{arr}]) ]')
            self.len(1, nodes)

            nodes = await core.nodes('test:witharray:ips*[=1.2.3.4]')
            self.len(1, nodes)

            nodes = await core.nodes('test:witharray:ips*[=1.2.3.4] | delnode')
            nodes = await core.nodes('test:witharray:ips*[=1.2.3.4]')
            self.len(0, nodes)

            nodes = await core.nodes('test:witharray | delnode')

            # make sure "adds" got added
            nodes = await core.nodes('inet:ip=1.2.3.4 inet:ip=5.6.7.8')
            self.len(2, nodes)

            nodes = await core.nodes('[ test:witharray="*" :fqdns="woot.com, VERTEX.LINK, vertex.link" ]')
            self.len(1, nodes)

            self.propeq(nodes[0], 'fqdns', ('vertex.link', 'woot.com'))
            self.sorteq(('vertex.link', 'woot.com'), nodes[0].repr('fqdns').split(','))

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

            await core.addFormProp('test:int', '_hehe', ('str', {}), {'array': {}})

            baz = 'baz' * 100

            nodes = await core.nodes(f'[ test:int=1 :_hehe=("foo", "bar", "{baz}") ]')
            self.len(1, nodes)
            self.len(1, await core.nodes('test:int:_hehe*[~=foo]'))
            self.len(1, await core.nodes('test:int:_hehe*[~=baz]'))

            nodes = await core.nodes(f'[ test:int=2 :_hehe=("foo", "bar", "{baz}") ]')
            self.len(1, nodes)
            self.len(2, await core.nodes('test:int:_hehe*[~=foo]'))
            self.len(2, await core.nodes('test:int:_hehe*[~=baz]'))

            nid = nodes[0].nid

            core.getLayer()._testAddPropArrayIndx(nid, 'test:int', '_hehe', (('str', 'newp' * 100),))
            self.len(0, await core.nodes('test:int:_hehe*[~=newp]'))

            await core.addFormProp('test:int', '_vers', ('it:version', {}), {'array': {}})

            await core.nodes('[ test:int=3 :_vers=(v1.2.3, foo1.2.3, 4.5.6) ]')
            self.len(2, await core.nodes('test:int:_vers*[.semver=1.2.3]'))

            await core.nodes('test:int=3 [ :_vers-=v1.2.3 ]')
            self.len(1, await core.nodes('test:int:_vers*[.semver=1.2.3]'))

    async def test_types_typehash(self):
        async with self.getTestCore() as core:
            self.true(core.model.form('inet:asn').type.typehash is not core.model.prop('inet:proto:port').type.typehash)

            self.true(s_common.isguid(core.model.form('inet:fqdn').type.typehash))
            self.true(s_common.isguid(core.model.form('inet:fqdn').typehash))

    async def test_datamodel_text(self):

        async with self.getTestCore() as core:

            await core.nodes('''[
                (test:str=foo :textform=NoCase)
                (test:str=bar :textform=nocase)
                (test:str=baz :textform=newp)
                test:str=nocase
            ]''')

            # lift/filter ignore case
            self.len(2, await core.nodes('test:str:textform=nocase'))
            self.len(2, await core.nodes('test:str:textform=NOCASE'))
            self.len(2, await core.nodes('test:str:textform=nocase +:textform=nocase'))
            self.len(2, await core.nodes('test:str:textform=nocase +:textform=NOCASE'))

            # value contains original case
            nodes = await core.nodes('test:str:textform=nocase')
            self.propeq(nodes[0], 'textform', 'NoCase')
            self.propeq(nodes[1], 'textform', 'nocase')

            # printing uses original case
            msgs = await core.stormlist('test:str:textform=nocase $lib.print(:textform)')
            self.stormIsInPrint('NoCase', msgs)
            self.stormIsInPrint('nocase', msgs)

            # only one node for the form can exist in the view and it retains the original case used
            nodes = await core.nodes('test:text')
            self.len(2, nodes)
            self.sorteq([n.ndef[1] for n in nodes], ('NoCase', 'newp'))

            nodes = await core.nodes('test:text=NoCase')
            nid1 = nodes[0].nid

            nodes = await core.nodes('[ test:text=NOCASE ]')
            self.eq(nodes[0].nid, nid1)

            nodes = await core.nodes('test:text')
            self.len(2, nodes)
            self.sorteq([n.ndef[1] for n in nodes], ('NoCase', 'newp'))

            # pivots use destination's behavior
            self.len(2, await core.nodes('test:str=nocase -> test:str:textform'))

            self.len(3, await core.nodes('test:str:textform -> *'))
            self.len(1, await core.nodes('test:str:textform :textform as test:str -> test:str'))

            self.len(3, await core.nodes('test:text <- *'))
            self.len(3, await core.nodes('test:text -> test:str'))

            # attempting to re-add in a fork still gives the base layer cased node
            viewiden2 = await core.callStorm('return($lib.view.get().fork().iden)')
            nodes = await core.nodes('[ test:text=NOCASE ]', opts={'view': viewiden2})
            self.eq(nodes[0].nid, nid1)
            self.eq(nodes[0].ndef[1], 'NoCase')

            # creating the node in the fork first causes the case to be different but same nid
            await core.nodes('[ test:text=NOCASE2 ]', opts={'view': viewiden2})
            nodes = await core.nodes('[ test:text=noCASE2 ]')
            nid2 = nodes[0].nid
            self.eq(nodes[0].ndef[1], 'noCASE2')

            nodes = await core.nodes('test:text=NOCASE2', opts={'view': viewiden2})
            self.eq(nodes[0].nid, nid2)
            self.eq(nodes[0].ndef[1], 'NOCASE2')

            await core.nodes('[test:str=view :textform=nocase2]')
            self.len(1, await core.nodes('test:str=view -> *', opts={'view': viewiden2}))
            self.len(1, await core.nodes('test:str=view -> *'))

            # merging overwrites casing in the lower layer
            await core.nodes('[ test:text=NOCASE2 ] | merge --apply', opts={'view': viewiden2})
            nodes = await core.nodes('test:text=noCASE2')
            nid2 = nodes[0].nid
            self.eq(nodes[0].ndef[1], 'NOCASE2')

            await core.nodes('[ test:text=NoCase3 ]', opts={'view': viewiden2})
            nodes = await core.nodes('[ test:text=nocase3 ]')
            nid3 = nodes[0].nid
            self.eq(nodes[0].ndef[1], 'nocase3')

            forkview = core.getView(viewiden2)
            await core.nodes('$lib.view.get().merge()', opts={'view': viewiden2})
            self.true(await forkview.waitfini(timeout=5))
            nodes = await core.nodes('test:text=nocase3')
            nid3 = nodes[0].nid
            self.eq(nodes[0].ndef[1], 'NoCase3')

            # node.setValue() can be used to change the value
            nodes = await core.nodes('test:text=nocase2 $node.setValue(nocase2)')
            nid2 = nodes[0].nid
            self.eq(nodes[0].ndef[1], 'nocase2')

            nodes = await core.nodes('test:text=nocase2 $node.setValue(nocase2)')
            nid2 = nodes[0].nid
            self.eq(nodes[0].ndef[1], 'nocase2')

            nodes = await core.nodes('test:str:textform +:textform!=NOCASE')
            self.sorteq([n.get('textform')[1] for n in nodes], ('newp', 'nocase2'))

            nodes = await core.nodes('test:str:textform +:textform^=NEW')
            self.len(1, nodes)
            self.propeq(nodes[0], 'textform', 'newp')

            nodes = await core.nodes('test:str:textform +:textform~="^N.+P$"')
            self.len(1, nodes)
            self.propeq(nodes[0], 'textform', 'newp')

            nodes = await core.nodes('test:str:textform +:textform*in=(NEWP, foo)')
            self.len(1, nodes)
            self.propeq(nodes[0], 'textform', 'newp')

            nodes = await core.nodes('test:str:textform +:textform*range=(NEW, NOC)')
            self.len(1, nodes)
            self.propeq(nodes[0], 'textform', 'newp')

            nodes = await core.nodes('[ file:path="c:/foo/bar.exe" ]')
            self.eq(nodes[0].valuvirts(), {'base': ('bar.exe', 30), 'ext': ('exe', 30), 'dir': ('c:/foo', 30)})

            # setValue updates virts
            nodes = await core.nodes('file:path="c:/foo/bar.exe" $node.setValue("c:/FOO/Bar.EXE")')
            self.eq(nodes[0].valuvirts(), {'base': ('Bar.EXE', 30), 'ext': ('EXE', 30), 'dir': ('c:/FOO', 30)})

            self.true(await core.callStorm('test:str:textform=newp $foo = :textform return(($foo = "NEWP"))'))
            self.true(await core.callStorm('test:str:textform=newp return((:textform = "NEWP"))'))
            self.true(await core.callStorm('test:str:textform=newp return(("NEWP" = :textform))'))
            self.false(await core.callStorm('test:str:textform=newp return((:textform != "NEWP"))'))
            self.true(await core.callStorm('test:str:textform=newp return((:textform != "OTHER"))'))
            self.true(await core.callStorm('test:str:textform=newp return((:textform ^= "NEW"))'))
            self.true(await core.callStorm('test:str:textform=newp return((:textform ~= "^N.+P$"))'))

            # both operands NodeRef
            self.true(await core.callStorm('test:str:textform=newp $foo = :textform return((:textform = $foo))'))

            # type has no cmpr ctor for the operator: arithmetic falls through to expr_*
            await core.nodes('[ test:int=10 :int2=42 ]')
            self.eq(47, await core.callStorm('test:int=10 return((:int2 + 5))'))

            # other side cannot be normed into the type -> BadTypeValu path
            self.false(await core.callStorm('test:int=10 return((:int2 = "notanumber"))'))
            self.true(await core.callStorm('test:int=10 return((:int2 != "notanumber"))'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str:textform +:textform*range=$x', opts={'vars': {'x': 'notatuple'}})

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str:textform +:textform*range=(a, b, c)')

            # new value must resolve to the same value
            with self.raises(s_exc.BadArg):
                await core.nodes('test:text=nocase2 $node.setValue(NEWP)')

            core.getView().wlyr.readonly = True
            with self.raises(s_exc.IsReadOnly):
                await core.nodes('test:text=nocase2 $node.setValue(NoCaSe2)')

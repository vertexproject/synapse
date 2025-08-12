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
from synapse.tests.utils import alist


class TypesTest(s_t_utils.SynTest):

    async def test_type(self):
        # Base type tests, mainly sad paths
        model = s_datamodel.Model()
        t = model.type('bool')
        self.eq(t.info.get('bases'), ('base',))
        self.none(t.getCompOffs('newp'))
        with self.raises(s_exc.NoSuchCmpr):
            await t.cmpr(val1=1, name='newp', val2=0)

        str00 = model.type('str').clone({})
        str01 = model.type('str').clone({})
        str02 = model.type('str').clone({'lower': True})
        self.eq(str00, str01)
        self.ne(str01, str02)

    async def test_mass(self):

        async with self.getTestCore() as core:

            mass = core.model.type('mass')

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
        model = s_datamodel.Model()
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
            self.eq(2, nodes[0].get('speed'))

    async def test_hugenum(self):

        model = s_datamodel.Model()
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

    async def test_taxonomy(self):

        model = s_datamodel.Model()
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
        self.eq(2, info['subs']['depth'])
        self.eq('baz', info['subs']['base'])
        self.eq('foo.bar.', info['subs']['parent'])

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
            nodes = await core.nodes('[test:taxonomy=foo.bar.baz :title="title words" :desc="a test taxonomy" :sort=1 ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('test:taxonomy', 'foo.bar.baz.'))
            self.eq(node.get('title'), 'title words')
            self.eq(node.get('desc'), 'a test taxonomy')
            self.eq(node.get('sort'), 1)
            self.eq(node.get('base'), 'baz')
            self.eq(node.get('depth'), 2)
            self.eq(node.get('parent'), 'foo.bar.')

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
        model = s_datamodel.Model()
        t = model.type('duration')

        self.eq('2D 00:00:00', t.repr(172800000000))
        self.eq('00:05:00.333333', t.repr(300333333))
        self.eq('11D 11:47:12.344', t.repr(992832344000))

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

    async def test_bool(self):
        model = s_datamodel.Model()
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
            self.eq(node.get('foo'), 123)
            self.eq(node.get('bar'), 'haha')

            typ = core.model.type(t)
            self.eq(typ.info.get('bases'), ('base', 'comp'))

            with self.raises(s_exc.BadTypeValu):
                await typ.norm((123, 'haha', 'newp'))

            self.eq(0, typ.getCompOffs('foo'))
            self.eq(1, typ.getCompOffs('bar'))
            self.none(typ.getCompOffs('newp'))

    async def test_guid(self):
        model = s_datamodel.Model()

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
            self.eq('vertex', nodes00[0].get('name'))

            nodes01 = await core.nodes('[ ou:org=({"name": "vertex"}) :names+="the vertex project"]')
            self.len(1, nodes01)
            self.eq('vertex', nodes01[0].get('name'))
            self.eq(nodes00[0].ndef, nodes01[0].ndef)

            nodes02 = await core.nodes('[ ou:org=({"name": "the vertex project"}) ]')
            self.len(1, nodes02)
            self.eq('vertex', nodes02[0].get('name'))
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
            self.eq('vertex', nodes05[0].get('name'))
            self.eq('for the people', nodes05[0].get('motto'))
            self.eq(nodes00[0].ndef, nodes05[0].ndef)

            nodes06 = await core.nodes('[ ou:org=({"name": "acme", "$props": {"motto": "HURR DURR"}}) ]')
            self.len(1, nodes06)
            self.eq('acme', nodes06[0].get('name'))
            self.eq('HURR DURR', nodes06[0].get('motto'))
            self.ne(nodes00[0].ndef, nodes06[0].ndef)

            nodes07 = await core.nodes('[ ou:org=({"name": "goal driven", "emails": ["foo@vertex.link", "bar@vertex.link"]}) ]')
            self.len(1, nodes07)
            self.eq(nodes07[0].get('emails'), ('bar@vertex.link', 'foo@vertex.link'))

            nodes08 = await core.nodes('[ ou:org=({"name": "goal driven", "emails": ["bar@vertex.link", "foo@vertex.link"]}) ]')
            self.len(1, nodes08)
            self.eq(nodes08[0].get('emails'), ('bar@vertex.link', 'foo@vertex.link'))
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
            msgs = await core.stormlist('[ou:org=({"name": "burrito corp", "$try": true, "$props": {"phone": "lolnope", "desc": "burritos man"}})]')
            nodes = [m for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            node = nodes[0][1]
            props = node[1]['props']
            self.none(props.get('phone'))
            self.eq(props.get('name'), 'burrito corp')
            self.eq(props.get('desc'), 'burritos man')

            # $try can also be specified in $props which overrides top level $try
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ou:org=({"name": "burrito corp", "$try": true, "$props": {"$try": false, "phone": "lolnope"}})]')

            await self.asyncraises(s_exc.BadTypeValu, core.nodes("$lib.view.get().addNode(ou:org, ({'name': 'org name 77', 'phone': 'lolnope'}), props=({'desc': 'an org desc'}))"))

            await self.asyncraises(s_exc.BadTypeValu, core.nodes("$lib.view.get().addNode(ou:org, ({'name': 'org name 77'}), props=({'desc': 'an org desc', 'phone': 'lolnope'}))"))

            nodes = await core.nodes("yield $lib.view.get().addNode(ou:org, ({'$try': true, '$props': {'phone': 'invalid'}, 'name': 'org name 77'}), props=({'desc': 'an org desc'}))")
            self.len(1, nodes)
            node = nodes[0]
            self.none(node.get('phone'))
            self.eq(node.get('name'), 'org name 77')
            self.eq(node.get('desc'), 'an org desc')

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
                    'channel': {
                        'id': 'foochannel',
                        'platform': {
                            'name': 'fooplatform',
                            'url': 'http://foo.com'
                        }
                    }
                })
            ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[0], 'inet:service:message')
            self.eq(node.get('id'), 'foomesg')
            self.nn(node.get('channel'))

            nodes = await core.nodes('inet:service:message -> inet:service:channel')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('id'), 'foochannel')
            self.nn(node.get('platform'))

            nodes = await core.nodes('inet:service:message -> inet:service:channel -> inet:service:platform')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('name'), 'fooplatform')
            self.eq(node.get('url'), 'http://foo.com')

            nodes = await core.nodes('''
                inet:service:message=({
                    'id': 'foomesg',
                    'channel': {
                        'id': 'foochannel',
                        'platform': {
                            'name': 'fooplatform',
                            'url': 'http://foo.com'
                        }
                    }
                })
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[0], 'inet:service:message')
            self.eq(node.get('id'), 'foomesg')

            nodes = await core.nodes('''[
                inet:service:message=({
                    'id': 'barmesg',
                    'channel': {
                        'id': 'barchannel',
                        'platform': {
                            'name': 'barplatform',
                            'url': 'http://bar.com'
                        }
                    },
                    '$props': {
                        'platform': {
                            'name': 'barplatform',
                            'url': 'http://bar.com'
                        }
                    }
                })
            ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[0], 'inet:service:message')
            self.eq(node.get('id'), 'barmesg')
            self.nn(node.get('channel'))

            platguid = node.get('platform')
            self.nn(platguid)
            nodes = await core.nodes('inet:service:message:id=barmesg -> inet:service:channel -> inet:service:platform')
            self.len(1, nodes)
            self.eq(platguid, nodes[0].ndef[1])

            # No node lifted if no matching node for inner gutor
            self.len(0, await core.nodes('''
                inet:service:message=({
                    'id': 'foomesg',
                    'channel': {
                        'id': 'foochannel',
                        'platform': {
                            'name': 'newp',
                            'url': 'http://foo.com'
                        }
                    }
                })
            '''))

            # BadTypeValu comes through from inner gutor
            with self.raises(s_exc.BadTypeValu) as cm:
                await core.nodes('''
                    inet:service:message=({
                        'id': 'foomesg',
                        'channel': {
                            'id': 'foochannel',
                            'platform': {
                                'name': 'newp',
                                'url': 'newp'
                            }
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
                    "platform": {"name": "barplat"},
                    "url": "newp"})
            ]'''))

            self.len(0, await core.nodes('inet:service:platform:name=barplat'))

            # Gutors work for props
            nodes = await core.nodes('''[
                test:str=guidprop
                    :gprop=({'name': 'someprop', '$props': {'size': 5}})
            ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('test:str', 'guidprop'))
            self.nn(node.get('gprop'))

            nodes = await core.nodes('test:str=guidprop -> test:guid')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('name'), 'someprop')
            self.eq(node.get('size'), 5)

            with self.raises(s_exc.BadTypeValu) as cm:
                nodes = await core.nodes('''[
                    test:str=newpprop
                        :gprop=({'size': 'newp'})
                ]''')

            self.eq(cm.exception.get('form'), 'test:guid')
            self.eq(cm.exception.get('prop'), 'size')
            self.true(cm.exception.get('mesg').startswith('Bad value for prop test:guid:size: invalid literal'))

            nodes = await core.nodes('''[
                test:str=newpprop
                    :gprop?=({'size': 'newp'})
            ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('test:str', 'newpprop'))
            self.none(node.get('gprop'))

            nodes = await core.nodes('''
                [ test:str=methset ]
                $node.props.gprop = ({'name': 'someprop'})
            ''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('test:str', 'methset'))
            self.nn(node.get('gprop'))

            nodes = await core.nodes('test:str=methset -> test:guid')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('name'), 'someprop')
            self.eq(node.get('size'), 5)

            opts = {'vars': {'sha256': 'a01f2460fec1868757aa9194b5043b4dd9992de0f6b932137f36506bd92d9d88'}}
            nodes = await core.nodes('''[ it:app:yara:match=* :target=('file:bytes', ({"sha256": $sha256})) ]''', opts=opts)
            self.len(1, nodes)

            nodes = await core.nodes('it:app:yara:match -> *')
            self.len(1, nodes)
            self.eq(nodes[0].get('sha256'), opts['vars']['sha256'])

            opts = {'vars': {
                        'phash': 'a01f2460fec1868757aa9194b5043b4dd9992de0f6b932137f36506bd92d9d86',
                        'chash': 'a01f2460fec1868757aa9194b5043b4dd9992de0f6b932137f36506bd92d9d87'
            }}
            nodes = await core.nodes('''[ file:subfile=(({"sha256": $phash}), ({"sha256": $chash})) ]''', opts=opts)
            self.len(1, nodes)

            nodes = await core.nodes('file:subfile -> file:bytes')
            self.len(2, nodes)
            for node in nodes:
                self.nn(node.get('sha256'))

            nodes = await core.nodes('$file = {[file:bytes=*]} [ inet:service:rule=({"id":"foo", "object": $file}) ]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('id'), 'foo')
            self.nn(node.get('object'))

            self.len(1, await core.nodes('inet:service:rule :object -> *'))

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

        model = s_datamodel.Model()
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

    async def test_float(self):
        model = s_datamodel.Model()
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

    async def test_ival(self):
        model = s_datamodel.Model()
        ival = model.types.get('ival')

        self.eq(('2016-01-01T00:00:00Z', '2017-01-01T00:00:00Z'), ival.repr((await ival.norm(('2016', '2017')))[0]))

        self.eq((0, 5356800000000, 5356800000000), (await ival.norm((0, '1970-03-04')))[0])
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
            # node whose primary prop is an ival
            self.len(1, await core.nodes('[test:ival=((0),(10)) :interval=(now, "now+4days")]'))
            self.len(1, await core.nodes('[test:ival=((50),(100)) :interval=("now-2days", "now+2days")]'))
            self.len(1, await core.nodes('[test:ival=(1995, 1997) :interval=(2010, 2011)]'))
            self.len(1, await core.nodes('[test:ival=("now-2days", "now+4days") :interval=(201006, 20100605) ]'))
            self.len(1, await core.nodes('[test:ival=("now+21days", "?") :interval=(2000, 2001)]'))
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

            self.eq(1, await core.count('test:ival@=1970'))
            self.eq(5, await core.count('test:ival@=(1970, "now+100days")'))
            self.eq(1, await core.count('test:ival@="now"'))
            self.eq(1, await core.count('test:ival@=("now+1day", "now+6days")'))
            self.eq(1, await core.count('test:ival@=("now-9days", "now-1day")'))
            self.eq(1, await core.count('test:ival@=("now-3days", "now+3days")'))
            self.eq(0, await core.count('test:ival@=("1993", "1995")'))
            self.eq(0, await core.count('test:ival@=("1997", "1998")'))
            self.eq(1, await core.count('test:ival=("1995", "1997")'))

            self.eq(1, await core.count('test:ival:interval@="now+2days"'))
            self.eq(0, await core.count('test:ival:interval@=("now-4days","now-3days")'))
            self.eq(0, await core.count('test:ival:interval@=("now+4days","now+6days")'))
            self.eq(1, await core.count('test:ival:interval@=("now-3days","now-1days")'))
            self.eq(1, await core.count('test:ival:interval@=("now+3days","now+6days")'))
            self.eq(2, await core.count('test:ival:interval@="now+1day"'))
            self.eq(2, await core.count('test:ival:interval@=("20100602","20100603")'))
            self.eq(2, await core.count('test:ival:interval@=("now-10days","now+10days")'))
            self.eq(0, await core.count('test:ival:interval@=("1999", "2000")'))
            self.eq(0, await core.count('test:ival:interval@=("2001", "2002")'))

            self.eq(1, await core.count('test:ival +:interval@="now+2days"'))
            self.eq(0, await core.count('test:ival +:interval@=("now-4days","now-3days")'))
            self.eq(0, await core.count('test:ival +:interval@=("now+4days","now+6days")'))
            self.eq(1, await core.count('test:ival +:interval@=("now-3days","now-1days")'))
            self.eq(1, await core.count('test:ival +:interval@=("now+3days","now+6days")'))
            self.eq(2, await core.count('test:ival +:interval@="now+1day"'))
            self.eq(2, await core.count('test:ival +:interval@=("20100602","20100603")'))
            self.eq(2, await core.count('test:ival +:interval@=("now-10days","now+10days")'))
            self.eq(0, await core.count('test:ival +:interval@=("1999", "2000")'))
            self.eq(0, await core.count('test:ival +:interval@=("2001", "2002")'))

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
            valu = node.get('seen')
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

            self.len(1, await core.nodes('entity:campaign.created +:period.min=2020-01-01'))
            self.len(2, await core.nodes('entity:campaign.created +:period.min<2022-01-01'))
            self.len(3, await core.nodes('entity:campaign.created +:period.min<=2022-01-01'))
            self.len(3, await core.nodes('entity:campaign.created +:period.min>=2022-01-01'))
            self.len(2, await core.nodes('entity:campaign.created +:period.min>2022-01-01'))
            self.len(1, await core.nodes('entity:campaign.created +:period.min@=2020'))
            self.len(2, await core.nodes('entity:campaign.created +:period.min@=(2020-01-01, 2022-01-01)'))

            self.len(1, await core.nodes('entity:campaign.created +:period.max=2020-01-02'))
            self.len(2, await core.nodes('entity:campaign.created +:period.max<2022-05-01'))
            self.len(3, await core.nodes('entity:campaign.created +:period.max<=2022-05-01'))
            self.len(3, await core.nodes('entity:campaign.created +:period.max>=2022-05-01'))
            self.len(2, await core.nodes('entity:campaign.created +:period.max>2022-05-01'))
            self.len(1, await core.nodes('entity:campaign.created +:period.max@=2022-05-01'))
            self.len(2, await core.nodes('entity:campaign.created +:period.max@=(2020-01-02, 2022-05-01)'))

            self.len(1, await core.nodes('entity:campaign.created +:period.duration=1D'))
            self.len(1, await core.nodes('entity:campaign.created +:period.duration<31D'))
            self.len(2, await core.nodes('entity:campaign.created +:period.duration<=31D'))
            self.len(4, await core.nodes('entity:campaign.created +:period.duration>=31D'))
            self.len(3, await core.nodes('entity:campaign.created +:period.duration>31D'))

            self.len(0, await core.nodes('entity:campaign.created +:period.min@=(2022-01-01, 2020-01-01)'))

            with self.raises(s_exc.NoSuchFunc):
                await core.nodes('entity:campaign.created +:period.min@=({})')

            self.eq(ival.getVirtType(['min']), model.types.get('time'))

            with self.raises(s_exc.NoSuchVirt):
                ival.getVirtType(['min', 'newp'])

            with self.raises(s_exc.NoSuchVirt):
                ival.getVirtGetr(['min', 'newp'])

            ityp = core.model.type('ival')
            styp = core.model.type('timeprecision').stortype
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
                await core.addFormProp('test:int', '_newp', ('ival', {'precision': 'newp'}), {})

            nodes = await core.nodes('[ test:str=foo :seen=(2021, ?) :seen.duration=1D ]')
            self.eq(nodes[0].get('seen'), (1609459200000000, 1609545600000000, 86400000000))

            nodes = await core.nodes('[ test:str=bar :seen=(?, 2021) :seen.duration=1D ]')
            self.eq(nodes[0].get('seen'), (1609372800000000, 1609459200000000, 86400000000))

            nodes = await core.nodes('[ test:str=baz :seen=(?, ?) :seen.duration=1D ]')
            self.eq(nodes[0].get('seen'), (ityp.unksize, ityp.unksize, 86400000000))

            nodes = await core.nodes('test:str=baz [ :seen.min=2021 ]')
            self.eq(nodes[0].get('seen'), (1609459200000000, 1609545600000000, 86400000000))

            nodes = await core.nodes('[ test:str=faz :seen.duration=1D ]')
            self.eq(nodes[0].get('seen'), (ityp.unksize, ityp.unksize, 86400000000))

            nodes = await core.nodes('test:str=faz [ :seen.max=2021 ]')
            self.eq(nodes[0].get('seen'), (1609372800000000, 1609459200000000, 86400000000))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ test:str=foo :seen=(2021, 2022) :seen.duration=500 ]')

    async def test_loc(self):
        model = s_datamodel.Model()
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

    async def test_ndef(self):
        async with self.getTestCore() as core:
            t = core.model.type('test:ndef')

            norm, info = await t.norm(('test:str', 'Foobar!'))
            self.eq(norm, ('test:str', 'Foobar!'))
            self.eq(info, {'adds': (('test:str', 'Foobar!', {}),),
                           'subs': {'form': 'test:str'}})

            rval = t.repr(('test:str', 'Foobar!'))
            self.eq(rval, ('test:str', 'Foobar!'))
            rval = t.repr(('test:int', 1234))
            self.eq(rval, ('test:int', '1234'))

            await self.asyncraises(s_exc.NoSuchForm, t.norm(('test:newp', 'newp')))
            self.raises(s_exc.NoSuchForm, t.repr, ('test:newp', 'newp'))
            await self.asyncraises(s_exc.BadTypeValu, t.norm(('newp',)))

            await core.nodes('[ test:str=ndefs :ndefs=((it:dev:int, 1), (it:dev:int, 2)) ]')
            await core.nodes('[ risk:vulnerable=(foo,) :node=(it:dev:int, 1) ]')
            await core.nodes('[ risk:vulnerable=(bar,) :node=(inet:fqdn, foo.com) ]')

            self.len(1, await core.nodes('risk:vulnerable.created +:node.form=it:dev:int'))
            self.len(1, await core.nodes('risk:vulnerable.created +:node.form=inet:fqdn'))
            self.len(0, await core.nodes('risk:vulnerable.created +:node.form=it:dev:str'))

            self.len(1, await core.nodes('test:str.created +:ndefs*[.form=it:dev:int]'))
            self.len(0, await core.nodes('test:str.created +:ndefs*[.form=it:dev:str]'))

            self.eq('it:dev:int', await core.callStorm('risk:vulnerable=(foo,) return(:node.form)'))

            self.none(await core.callStorm('[ risk:vulnerable=* ] return(:node.form)'))

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:str.created +:ndefs*[.form>it:dev:str]')

            ndef = core.model.type('test:ndef:formfilter1')
            await ndef.norm(('inet:ip', '1.2.3.4'))
            await ndef.norm(('inet:ip', '::1'))

            with self.raises(s_exc.BadTypeValu):
                await ndef.norm(('inet:fqdn', 'newp.com'))

            ndef = core.model.type('test:ndef:formfilter2')

            with self.raises(s_exc.BadTypeValu):
                await ndef.norm(('inet:fqdn', 'newp.com'))

            ndef = core.model.type('test:ndef:formfilter3')
            await ndef.norm(('inet:ip', '1.2.3.4'))
            await ndef.norm(('file:mime:msdoc', s_common.guid()))

            with self.raises(s_exc.BadTypeValu):
                await ndef.norm(('inet:fqdn', 'newp.com'))

    async def test_nodeprop(self):
        async with self.getTestCore() as core:
            t = core.model.type('nodeprop')

            expected = (('test:str', 'This is a sTring'), {'subs': {'prop': 'test:str'}})
            self.eq(await t.norm('test:str=This is a sTring'), expected)
            self.eq(await t.norm(('test:str', 'This is a sTring')), expected)

            await self.asyncraises(s_exc.NoSuchProp, t.norm(('test:str:newp', 'newp')))
            await self.asyncraises(s_exc.BadTypeValu, t.norm(('test:str:tick', '2020', 'a wild argument appears')))

    async def test_range(self):
        model = s_datamodel.Model()
        t = model.type('range')

        await self.asyncraises(s_exc.BadTypeValu, t.norm(1))
        await self.asyncraises(s_exc.BadTypeValu, t.norm('1'))
        await self.asyncraises(s_exc.BadTypeValu, t.norm((1,)))
        await self.asyncraises(s_exc.BadTypeValu, t.norm((1, -1)))

        norm, info = await t.norm((0, 0))
        self.eq(norm, (0, 0))
        self.eq(info['subs']['min'], 0)
        self.eq(info['subs']['max'], 0)

        self.eq((10, 20), (await t.norm('10-20'))[0])

        norm, info = await t.norm((-10, 0xFF))
        self.eq(norm, (-10, 255))
        self.eq(info['subs']['min'], -10)
        self.eq(info['subs']['max'], 255)

        self.eq(t.repr((-10, 0xFF)), ('-10', '255'))

        # Invalid Config
        self.raises(s_exc.BadTypeDef, model.type('range').clone, {'type': None})
        self.raises(s_exc.BadTypeDef, model.type('range').clone, {'type': ('inet:ip', {})})  # inet is not loaded yet

    async def test_range_filter(self):
        async with self.getTestCore() as core:
            self.len(1, await core.nodes('[test:str=a :bar=(test:str, b) :tick=19990101]'))
            self.len(1, await core.nodes('[test:str=b :seen=(20100101, 20110101) :tick=20151207]'))
            self.len(1, await core.nodes('[test:str=m :bar=(test:str, m) :tick=20200101]'))
            self.len(1, await core.nodes('[test:guid=$valu]', opts={'vars': {'valu': 'C' * 32}}))
            self.len(1, await core.nodes('[test:guid=$valu]', opts={'vars': {'valu': 'F' * 32}}))
            self.len(1, await core.nodes('[test:str=n1 :bar=(test:comp, (2048, horton))]'))
            self.len(1, await core.nodes('[test:str=n2 :bar=(test:comp, (9001, "A mean one"))]'))
            self.len(1, await core.nodes('[test:str=n3 :bar=(test:int, 16)]'))
            self.len(1, await core.nodes('[test:comp=(4096, whoville)]'))
            self.len(1, await core.nodes('[test:comp=(9999, greenham)]'))
            self.len(1, await core.nodes('[test:comp=(40000, greeneggs)]'))

            self.len(0, await core.nodes('test:str=a +:tick*range=(20000101, 20101201)'))
            nodes = await core.nodes('test:str +:tick*range=(19701125, 20151212)')
            self.eq({node.ndef[1] for node in nodes}, {'a', 'b'})
            nodes = await core.nodes('test:comp +:haha*range=(grinch, meanone)')
            self.eq({node.ndef[1] for node in nodes}, {(2048, 'horton')})
            nodes = await core.nodes('test:str +:bar*range=((test:str, c), (test:str, q))')
            self.eq({node.ndef[1] for node in nodes}, {'m'})
            nodes = await core.nodes('test:comp +test:comp*range=((1024, grinch), (4096, zemeanone))')
            self.eq({node.ndef[1] for node in nodes}, {(2048, 'horton'), (4096, 'whoville')})
            guid0 = 'B' * 32
            guid1 = 'D' * 32
            nodes = await core.nodes(f'test:guid +test:guid*range=({guid0}, {guid1})')
            self.eq({node.ndef[1] for node in nodes}, {'c' * 32})
            nodes = await core.nodes('test:int -> test:comp:hehe +test:comp*range=((1000, grinch), (4000, whoville))')
            self.eq({node.ndef[1] for node in nodes}, {(2048, 'horton')})
            nodes = await core.nodes('test:str +:bar*range=((test:comp, (1000, green)), (test:comp, (3000, ham)))')
            self.eq({node.ndef[1] for node in nodes}, {'n1'})

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
            with self.raises(s_exc.BadCmprValu):
                await core.nodes('test:comp +:hehe*range=(0.0.0.0, 1.1.1.1, 6.6.6.6)')
            with self.raises(s_exc.BadCmprValu):
                await core.nodes('test:comp +:haha*range=(somestring,)')
            with self.raises(s_exc.BadCmprValu):
                await core.nodes('test:str +:bar*range=Foobar')
            with self.raises(s_exc.BadCmprValu):
                await core.nodes('test:int +test:int*range=3456')

    async def test_str(self):

        model = s_datamodel.Model()

        lowr = model.type('str').clone({'lower': True})
        self.eq('foo', (await lowr.norm('FOO'))[0])

        self.eq(True, await lowr.cmpr('xxherexx', '~=', 'here'))
        self.eq(False, await lowr.cmpr('xxherexx', '~=', '^here'))

        self.eq(True, await lowr.cmpr('foo', '!=', 'bar'))
        self.eq(False, await lowr.cmpr('foo', '!=', 'FOO'))

        self.eq(True, await lowr.cmpr('foobar', '^=', 'FOO'))
        self.eq(False, await lowr.cmpr('foubar', '^=', 'FOO'))

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

        enums = model.type('str').clone({'enums': 'hehe,haha,zork'})
        self.eq('hehe', (await enums.norm('hehe'))[0])
        self.eq('haha', (await enums.norm('haha'))[0])
        self.eq('zork', (await enums.norm('zork'))[0])
        await self.asyncraises(s_exc.BadTypeValu, enums.norm(1.23))
        await self.asyncraises(s_exc.BadTypeValu, enums.norm('zing'))

        strsubs = model.type('str').clone({'regex': r'(?P<first>[ab]+)(?P<last>[zx]+)'})
        norm, info = await strsubs.norm('aabbzxxxxxz')
        self.eq(info.get('subs'), {'first': 'aabb', 'last': 'zxxxxxz'})

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

    async def test_syntag(self):

        model = s_datamodel.Model()
        tagtype = model.type('syn:tag')

        self.eq('foo.bar', (await tagtype.norm(('FOO', ' BAR')))[0])
        self.eq('foo.st_lucia', (await tagtype.norm(('FOO', 'st.lucia')))[0])

        self.eq('foo.bar', (await tagtype.norm('FOO.BAR'))[0])
        self.eq('foo.bar', (await tagtype.norm('#foo.bar'))[0])
        self.eq('foo.bar', (await tagtype.norm('foo   .   bar'))[0])

        tag, info = await tagtype.norm('foo')
        subs = info.get('subs')
        self.none(subs.get('up'))
        self.eq('foo', subs.get('base'))
        self.eq(0, subs.get('depth'))

        tag, info = await tagtype.norm('foo.bar')
        subs = info.get('subs')
        self.eq('foo', subs.get('up'))

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

        model = s_datamodel.Model()
        ttime = model.types.get('time')

        with self.raises(s_exc.BadTypeValu):
            await ttime.norm('0000-00-00')

        self.gt(s_common.now(), (await ttime.norm('-1hour'))[0])

        tminmax = ttime.clone({'min': True, 'max': True})
        # Merge testing with tminmax
        now = s_common.now()
        self.eq(now + 1, tminmax.merge(now, now + 1))
        self.eq(now, tminmax.merge(now + 1, now))

        async with self.getTestCore() as core:

            t = core.model.type('test:time')

            # explicitly test our "future/ongoing" value...
            future = 0x7fffffffffffffff
            self.eq((await t.norm('?'))[0], future)
            self.eq((await t.norm(future))[0], future)
            self.eq(t.repr(future), '?')

            # Explicitly test our max time vs. future marker
            maxtime = 253402300799999999  # 9999/12/31 23:59:59.999999
            self.eq((await t.norm(maxtime))[0], maxtime)
            self.eq(t.repr(maxtime), '9999-12-31T23:59:59.999999Z')
            self.eq((await t.norm('9999-12-31T23:59:59.999999Z'))[0], maxtime)
            await self.asyncraises(s_exc.BadTypeValu, t.norm(maxtime + 1))

            tmax = t.clone({'maxfill': True})
            self.eq((await tmax.norm('9999-12-31T23:59:59.999999Z'))[0], maxtime)

            tick = (await t.norm('2014'))[0]
            self.eq(t.repr(tick), '2014-01-01T00:00:00Z')

            tock = (await t.norm('2015'))[0]

            await self.asyncraises(s_exc.BadCmprValu, t.cmpr('2015', 'range=', tick))

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
                await core.addFormProp('test:int', '_newp', ('time', {'precision': 'newp'}), {})

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

            with self.raises(s_exc.BadCmprValu):
                await core.nodes('test:str +:tick*range=(2015)')
            with self.raises(s_exc.BadCmprValu):
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
            self.len(1, await core.nodes('[test:int=$valu]', opts={'vars': {'valu': nodes[0].get('tick')}}))
            nodes = await core.nodes('[test:str=b :tick=2015]')
            self.len(1, await core.nodes('[test:int=$valu]', opts={'vars': {'valu': nodes[0].get('tick')}}))
            self.len(1, nodes)
            nodes = await core.nodes('[test:str=c :tick=2016]')
            self.len(1, await core.nodes('[test:int=$valu]', opts={'vars': {'valu': nodes[0].get('tick')}}))
            self.len(1, nodes)
            nodes = await core.nodes('[test:str=d :tick=now]')
            self.len(1, await core.nodes('[test:int=$valu]', opts={'vars': {'valu': nodes[0].get('tick')}}))
            self.len(1, nodes)

            q = 'test:int $end=$node.value() test:str:tick*range=(2015, $end) -test:int'
            nodes = await core.nodes(q)
            self.len(6, nodes)
            self.eq({node.ndef[1] for node in nodes}, {'b', 'c', 'd'})

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
                ('test:array', ('array', {'type': 'inet:ip'}), {}),
                ('test:arraycomp', ('comp', {'fields': (('ips', 'test:array'), ('int', 'test:int'))}), {}),
                ('test:witharray', ('guid', {}), {}),
            ),
            'forms': (
                ('test:array', {}, (
                )),
                ('test:arraycomp', {}, (
                    ('ips', ('test:array', {}), {}),
                    ('int', ('test:int', {}), {}),
                )),
                ('test:witharray', {}, (
                    ('fqdns', ('array', {'type': 'inet:fqdn', 'uniq': True, 'sorted': True, 'split': ','}), {}),
                )),
            ),
        }
        async with self.getTestCore() as core:

            core.model.addDataModels([('asdf', mdef)])

            with self.raises(s_exc.BadTypeDef):
                await core.addFormProp('test:int', '_hehe', ('array', {'type': 'array'}), {})

            with self.raises(s_exc.BadTypeDef):
                await core.addFormProp('test:int', '_hehe', ('array', {'type': 'newp'}), {})

            nodes = await core.nodes('[ test:array=(1.2.3.4, 5.6.7.8) ]')
            self.len(1, nodes)

            # create a long array (fails pre-020)
            arr = ','.join([f'[4, {i}]' for i in range(300)])
            nodes = await core.nodes(f'[ test:array=([{arr}]) ]')
            self.len(1, nodes)

            nodes = await core.nodes('test:array*[=1.2.3.4]')
            self.len(1, nodes)

            nodes = await core.nodes('test:array*[=1.2.3.4] | delnode')
            nodes = await core.nodes('test:array*[=1.2.3.4]')
            self.len(0, nodes)

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ test:arraycomp=("1.2.3.4, 5.6.7.8", 10) ]')

            nodes = await core.nodes('[ test:arraycomp=((1.2.3.4, 5.6.7.8), 10) ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:arraycomp', (((4, 0x01020304), (4, 0x05060708)), 10)))
            self.eq(nodes[0].get('int'), 10)
            self.eq(nodes[0].get('ips'), ((4, 0x01020304), (4, 0x05060708)))

            # make sure "adds" got added
            nodes = await core.nodes('inet:ip=1.2.3.4 inet:ip=5.6.7.8')
            self.len(2, nodes)

            nodes = await core.nodes('[ test:witharray="*" :fqdns="woot.com, VERTEX.LINK, vertex.link" ]')
            self.len(1, nodes)

            self.eq(nodes[0].get('fqdns'), ('vertex.link', 'woot.com'))
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

            await core.addFormProp('test:int', '_hehe', ('array', {'type': 'str'}), {})

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

            core.getLayer()._testAddPropArrayIndx(nid, 'test:int', '_hehe', ('newp' * 100,))
            self.len(0, await core.nodes('test:int:_hehe*[~=newp]'))

    async def test_types_typehash(self):
        async with self.getTestCore() as core:
            self.true(core.model.form('inet:fqdn').type.typehash is core.model.prop('inet:dns:a:fqdn').type.typehash)
            self.true(core.model.form('meta:name').type.typehash is core.model.prop('it:network:name').type.typehash)
            self.true(core.model.form('inet:asn').type.typehash is not core.model.prop('inet:proto:port').type.typehash)

            self.true(s_common.isguid(core.model.form('inet:fqdn').type.typehash))
            self.true(s_common.isguid(core.model.form('inet:fqdn').typehash))

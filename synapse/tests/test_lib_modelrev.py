import os
import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.tests.utils as s_tests
import synapse.lib.modelrev as s_modelrev

def nope(*args, **kwargs):
    raise Exception('nope was called')

class ModelRevTest(s_tests.SynTest):

    async def test_cortex_modelrev_init(self):

        with self.getTestDir(mirror='testcore') as dirn:

            async with await s_cortex.Cortex.anit(dirn) as core:
                layr = core.getLayer()
                self.true(layr.fresh)
                self.eq(s_modelrev.maxvers, await layr.getModelVers())

            # no longer "fresh", but lets mark a layer as read only
            # and test the bail condition for layers which we cant update
            async with await s_cortex.Cortex.anit(dirn) as core:

                layr = core.getLayer()
                layr.canrev = False

                mrev = s_modelrev.ModelRev(core)

                mrev.revs = mrev.revs + (((9999, 9999, 9999), nope),)

                with self.raises(s_exc.CantRevLayer):
                    await mrev.revCoreLayers()

            # no longer "fresh"
            async with await s_cortex.Cortex.anit(dirn) as core:

                layr = core.getLayer()
                self.false(layr.fresh)

                self.eq(s_modelrev.maxvers, await layr.getModelVers())

                mrev = s_modelrev.ModelRev(core)

                layr.woot = False

                async def woot(layers):
                    layr.woot = True

                mrev.revs = mrev.revs + (((9999, 9999, 9999), woot),)

                await mrev.revCoreLayers()

                self.true(layr.woot)
                self.eq((9999, 9999, 9999), await layr.getModelVers())

    async def test_modelrev_2_0_1(self):
        async with self.getRegrCore('model-2.0.1') as core:

            nodes = await core.nodes('ou:org=b084f448ee7f95a7e0bc1fd7d3d7fd3b')
            self.len(1, nodes)
            self.len(3, nodes[0].get('industries'))

            nodes = await core.nodes('ou:org=57c2dd4feee21204b1a989b9a796a89d')
            self.len(1, nodes)
            self.len(1, nodes[0].get('industries'))

    async def test_modelrev_0_2_2(self):
        async with self.getRegrCore('model-0.2.2') as core:
            nodes = await core.nodes('inet:web:acct:signup:client:ipv6="::ffff:1.2.3.4"')
            self.len(2001, nodes)

    async def test_modelrev_0_2_3(self):

        async with self.getRegrCore('model-0.2.3') as core:

            nodes = await core.nodes('it:exec:proc:cmd=rar.exe')
            self.len(2001, nodes)

            nodes = await core.nodes('it:cmd')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('it:cmd', 'rar.exe'))

    async def test_modelrev_0_2_4(self):
        async with self.getRegrCore('model-0.2.4') as core:

            nodes = await core.nodes('ps:person=1828dca605977725540bb74f728d9d81')
            self.len(1, nodes)
            self.len(1, nodes[0].get('names'))

            nodes = await core.nodes('ps:person=d26a988f732371e51e36fea0f16ff382')
            self.len(1, nodes)
            self.len(3, nodes[0].get('names'))

            nodes = await core.nodes('ps:person=c92e49791022c88396fa69d9f94281cb')
            self.len(1, nodes)
            self.len(3, nodes[0].get('names'))

            nodes = await core.nodes('ps:person:name=coverage')
            self.len(1003, nodes)
            for node in nodes:
                self.len(1, nodes[0].get('names'))

    async def test_modelrev_0_2_6(self):
        async with self.getRegrCore('model-0.2.6') as core:

            acct = '90b3d80f8bdf9e33b4aeb46c720d3289'
            nodes = await core.nodes(f'it:account={acct}')
            self.len(1, nodes)
            self.len(2, nodes[0].get('groups'))

            g00 = 'd0d235109162501db9d4014a4c2cc4d9'
            g01 = 'bf1999e8c45523bc64803e28b19a34c6'
            nodes = await core.nodes(f'it:account={acct} [:groups=({g00}, {g01}, {g00})]')
            self.len(1, nodes)
            self.len(2, nodes[0].get('groups'))

            url0 = "https://charlie.com/woot"
            url1 = "https://bravo.com/woot"
            url2 = "https://delta.com/woot"
            url3 = "https://alpha.com/woot"

            # created via: f'[it:sec:cve=CVE-2013-9999 :desc="some words" :references=({url0}, {url1}, {url2}, {url3})]'
            nodes = await core.nodes(f'it:sec:cve=CVE-2013-9999')
            self.eq(nodes[0].ndef[1], 'cve-2013-9999')
            self.eq(nodes[0].get('desc'), 'some words')
            self.eq(nodes[0].get('references'), (url3, url1, url0, url2))

    async def test_modelrev_0_2_7_mirror(self):

        vers = '2.85.1-hugenum-indx'

        with self.getRegrDir('cortexes', vers) as regrdir00:

            with self.getRegrDir('cortexes', vers) as regrdir01:

                conf00 = {'nexslog:en': True}

                async with await s_cortex.Cortex.anit(regrdir00, conf=conf00) as core00:

                    self.true(await core00.getLayer().getModelVers() >= (0, 2, 7))

                    conf01 = {'nexslog:en': True, 'mirror': core00.getLocalUrl()}

                async with await s_cortex.Cortex.anit(regrdir01, conf=conf01) as core01:

                    self.eq(await core01.getLayer().getModelVers(), (0, 2, 6))

                    nodes = await core01.nodes('inet:fqdn=baz.com')
                    self.len(1, nodes)
                    node = nodes[0]
                    self.eq(node.props.get('_huge'), '10E-21')
                    self.eq(node.props.get('._univhuge'), '10E-21')
                    self.eq(node.props.get('._hugearray'), ('3.45', '10E-21'))
                    self.eq(node.props.get('._hugearray'), ('3.45', '10E-21'))

                async with await s_cortex.Cortex.anit(regrdir00, conf=conf00) as core00:
                    async with await s_cortex.Cortex.anit(regrdir01, conf=conf01) as core01:

                        await core01.sync()

                        self.true(await core01.getLayer().getModelVers() >= (0, 2, 7))

                        nodes = await core01.nodes('inet:fqdn=baz.com')
                        self.len(1, nodes)
                        node = nodes[0]
                        self.eq(node.props.get('_huge'), '0.00000000000000000001')
                        self.eq(node.props.get('._univhuge'), '0.00000000000000000001')
                        self.eq(node.props.get('._hugearray'), ('3.45', '0.00000000000000000001'))
                        self.eq(node.props.get('._hugearray'), ('3.45', '0.00000000000000000001'))

    async def test_modelrev_0_2_8(self):
        # Test geo:place:name re-norming
        # Test crypto:currency:block:hash re-norming
        # Test crypto:currency:transaction:hash re-norming
        async with self.getRegrCore('2.87.0-geo-crypto') as core:

            # Layer migrations
            nodes = await core.nodes('geo:place:name="big hollywood sign"')
            self.len(1, nodes)

            nodes = await core.nodes('crypto:currency:block:hash')
            self.len(1, nodes)
            valu = nodes[0].get('hash')  # type: str
            self.false(valu.startswith('0x'))

            nodes = await core.nodes('crypto:currency:transaction:hash')
            self.len(1, nodes)
            valu = nodes[0].get('hash')  # type: str
            self.false(valu.startswith('0x'))

            # storm migrations
            nodes = await core.nodes('geo:name')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'big hollywood sign')

            self.len(0, await core.nodes('crypto:currency:transaction:inputs'))
            self.len(0, await core.nodes('crypto:currency:transaction:outputs'))

            nodes = await core.nodes('crypto:payment:input=(i1,) -> crypto:currency:transaction')
            self.len(1, nodes)
            nodes = await core.nodes('crypto:payment:input=(i2,) -> crypto:currency:transaction')
            self.len(1, nodes)
            nodes = await core.nodes(
                'crypto:payment:input=(i2,) -> crypto:currency:transaction +crypto:currency:transaction=(t2,)')
            self.len(1, nodes)
            nodes = await core.nodes(
                'crypto:payment:input=(i2,) -> crypto:currency:transaction +crypto:currency:transaction=(t3,)')
            self.len(0, nodes)
            nodes = await core.nodes('crypto:payment:input=(i3,) -> crypto:currency:transaction')
            self.len(1, nodes)
            nodes = await core.nodes('crypto:payment:output=(o1,) -> crypto:currency:transaction')
            self.len(1, nodes)
            nodes = await core.nodes('crypto:payment:output=(o2,) -> crypto:currency:transaction')
            self.len(1, nodes)
            nodes = await core.nodes(
                'crypto:payment:output=(o2,) -> crypto:currency:transaction +crypto:currency:transaction=(t2,)')
            self.len(1, nodes)
            nodes = await core.nodes(
                'crypto:payment:output=(o2,) -> crypto:currency:transaction +crypto:currency:transaction=(t3,)')
            self.len(0, nodes)
            nodes = await core.nodes('crypto:payment:output=(o3,) -> crypto:currency:transaction')
            self.len(1, nodes)
            self.len(0, await core.nodes('crypto:payment:input=(i4,) -> crypto:currency:transaction'))
            self.len(0, await core.nodes('crypto:payment:output=(o4,) -> crypto:currency:transaction'))

    async def test_modelrev_0_2_9(self):

        async with self.getRegrCore('model-0.2.9') as core:

            # test ou:industry:name -> ou:industryname
            nodes = await core.nodes('ou:industry -> ou:industryname')
            self.len(1, nodes)
            self.eq('foo bar', nodes[0].ndef[1])
            self.len(1, await core.nodes('ou:industryname="foo bar" -> ou:industry'))

            # test the various it:prod:softname conversions
            nodes = await core.nodes('it:prod:soft -> it:prod:softname')
            self.len(3, nodes)
            self.eq(('foo bar', 'baz faz', 'hehe haha'), [n.ndef[1] for n in nodes])

            nodes = await core.nodes('it:prod:softver -> it:prod:softname')
            self.len(3, nodes)
            self.eq(('foo bar', 'baz faz', 'hehe haha'), [n.ndef[1] for n in nodes])

            nodes = await core.nodes('it:mitre:attack:software -> it:prod:softname')
            self.len(3, nodes)
            self.eq(('foo bar', 'baz faz', 'hehe haha'), [n.ndef[1] for n in nodes])

            # test :name pivots
            self.len(1, await core.nodes('it:prod:softname="foo bar" -> it:prod:soft'))
            self.len(1, await core.nodes('it:prod:softname="foo bar" -> it:prod:softver'))
            self.len(1, await core.nodes('it:prod:softname="foo bar" -> it:mitre:attack:software'))

            # test :names pivots
            self.len(1, await core.nodes('it:prod:softname="baz faz" -> it:prod:soft'))
            self.len(1, await core.nodes('it:prod:softname="baz faz" -> it:prod:softver'))
            self.len(1, await core.nodes('it:prod:softname="baz faz" -> it:mitre:attack:software'))

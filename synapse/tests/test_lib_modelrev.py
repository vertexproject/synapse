import synapse.exc as s_exc
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

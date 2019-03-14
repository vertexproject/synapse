import synapse.common as s_common

import synapse.lib.migrate as s_migrate

import synapse.tests.utils as s_testutils

class MigrTest(s_testutils.SynTest):

    async def test_migr_base(self):

        async with self.getTestCore() as core:

            # create a refs to have a ndef edge type
            guid = s_common.guid()
            opts = {'vars': {'guid': guid}}

            nodes = await core.eval('[ test:guid=$guid :size=10 :posneg=100 ]', opts=opts).list()

            self.len(1, nodes)
            self.eq(10, nodes[0].get('size'))
            self.eq(100, nodes[0].get('posneg'))
            self.eq(0, nodes[0].get('posneg:isbig'))

            await core.eval('[ refs=( (test:guid, $guid), (test:comp, (10, test10)) ) +#baz ]', opts=opts).list()

            self.len(1, await core.eval('test:int=10 [ +#foo ]').list())
            self.len(1, await core.eval('test:comp=(10, test10) [ +#bar ]').list())
            self.len(1, await core.eval('[ test:comp=(20, test20) ]').list())

            async with await s_migrate.Migration.anit(core, s_common.guid()) as migr:

                async for layr, buid, valu in migr.getFormTodo('test:int'):
                    if valu == 10:
                        await migr.setNodeForm(layr, buid, 'test:int', valu, valu + 1000)

                # check sub sets via easy prop
                norm, info = core.model.type('test:sub').norm(2000)
                await migr.setPropsByType('test:sub', 100, norm, info)

            self.len(1, await core.eval('test:guid:posneg=2000 +:posneg:isbig=1').list())

            # check main node values *and* indexes
            self.len(0, await core.eval('test:int=10').list())
            self.len(1, await core.eval('test:int=20').list())
            self.len(1, await core.eval('test:int=1010').list())
            self.len(1, await core.eval('test:int#foo').list())

            self.len(1, await core.eval('refs#baz').list())

            refs = await core.eval('test:guid -> refs +#baz').list()

            self.len(1, refs)
            self.eq(refs[0].get('n2'), ('test:comp', (1010, 'test10')))
            self.eq(refs[0].ndef[1], (('test:guid', guid), ('test:comp', (1010, 'test10'))))

            self.len(0, await core.eval('test:comp:hehe=10').list())
            self.len(0, await core.eval('test:comp=(10, test10)').list())
            self.len(2, await core.eval('test:comp').list())
            self.len(1, await core.eval('test:comp=(20, test20)').list())
            self.len(1, await core.eval('test:comp:hehe=20').list())
            self.len(1, await core.eval('test:comp:hehe>=1000').list())
            self.len(1, await core.eval('test:comp:hehe<1000').list())

            self.len(1, await core.eval('test:comp=(1010, test10) +:hehe=1010 +:haha=test10 +#bar').list())
            self.len(1, await core.eval('test:comp:hehe=1010 +:hehe=1010 +:haha=test10 +#bar').list())
            self.len(1, await core.eval('test:comp#bar +:hehe=1010 +:haha=test10 +#bar').list())

            # check that a simple secondary prop got migrated correctly
            opts = {'vars': {'guid': guid}}
            self.len(1, await core.eval('test:guid=$guid +:size=1010', opts=opts).list())
            self.len(1, await core.eval('test:guid:size=1010', opts=opts).list())

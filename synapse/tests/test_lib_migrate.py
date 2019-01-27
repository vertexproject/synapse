import synapse.common as s_common

import synapse.lib.module as s_module
import synapse.lib.migrate as s_migrate

import synapse.tests.utils as s_testutils

class MigrTest(s_testutils.SynTest):

    async def test_migr_base(self):

        async with self.getTestCore() as core:

            # create a refs to have a ndef edge type
            guid = s_common.guid()
            opts = {'vars': {'guid': guid}}

            nodes = await core.eval('[ testguid=$guid :size=10 ]', opts=opts).list()
            self.len(1, nodes)
            self.eq(10, nodes[0].get('size'))

            await core.eval('[ refs=( (testguid, $guid), (testcomp, (10, test10)) ) +#baz ]', opts=opts).list()

            self.len(1, await core.eval('testint=10 [ +#foo ]').list())
            self.len(1, await core.eval('testcomp=(10, test10) [ +#bar ]').list())
            self.len(1, await core.eval('[ testcomp=(20, test20) ]').list())

            async with await s_migrate.Migration.anit(core, s_common.guid()) as migr:

                async for layr, buid, valu in migr.getFormTodo('testint'):
                    if valu == 10:
                        await migr.setNodeForm(layr, buid, 'testint', valu, valu + 1000)

            # check main node values *and* indexes
            self.len(0, await core.eval('testint=10').list())
            self.len(1, await core.eval('testint=20').list())
            self.len(1, await core.eval('testint=1010').list())
            self.len(1, await core.eval('testint#foo').list())

            self.len(1, await core.eval('refs#baz').list())

            refs = await core.eval('testguid -> refs +#baz').list()

            self.len(1, refs)
            self.eq(refs[0].get('n2'), ('testcomp', (1010, 'test10')))
            self.eq(refs[0].ndef[1], (('testguid', guid), ('testcomp', (1010, 'test10'))))

            self.len(0, await core.eval('testcomp:hehe=10').list())
            self.len(0, await core.eval('testcomp=(10, test10)').list())
            self.len(2, await core.eval('testcomp').list())
            self.len(1, await core.eval('testcomp=(20, test20)').list())
            self.len(1, await core.eval('testcomp:hehe=20').list())
            self.len(1, await core.eval('testcomp:hehe>=1000').list())
            self.len(1, await core.eval('testcomp:hehe<1000').list())

            self.len(1, await core.eval('testcomp=(1010, test10) +:hehe=1010 +:haha=test10 +#bar').list())
            self.len(1, await core.eval('testcomp:hehe=1010 +:hehe=1010 +:haha=test10 +#bar').list())
            self.len(1, await core.eval('testcomp#bar +:hehe=1010 +:haha=test10 +#bar').list())

            # check that a simple secondary prop got migrated correctly
            opts = {'vars': {'guid': guid}}
            self.len(1, await core.eval('testguid=$guid +:size=1010', opts=opts).list())
            self.len(1, await core.eval('testguid:size=1010', opts=opts).list())

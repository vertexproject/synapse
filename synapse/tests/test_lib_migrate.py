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

            await core.eval('[ edge:refs=( (test:guid, $guid), (test:comp, (10, test10)) ) +#baz ]', opts=opts).list()

            self.len(1, await core.eval('test:int=10 [ +#foo ]').list())
            self.len(1, await core.eval('test:comp=(10, test10) [ +#bar ]').list())
            self.len(1, await core.eval('[ test:comp=(20, test20) ]').list())

            async with await s_migrate.Migration.anit(core) as migr:

                async for buid, valu in migr.getFormTodo('test:int'):
                    if valu == 10:
                        await migr.editNodeNdef(('test:int', valu), ('test:int', valu + 1000))

            # check main node values *and* indexes
            self.len(0, await core.eval('test:int=10').list())
            self.len(1, await core.eval('test:int=20').list())
            self.len(1, await core.eval('test:int=1010').list())
            self.len(1, await core.eval('test:int#foo').list())

            self.len(1, await core.eval('edge:refs#baz').list())

            self.len(1, await core.eval(f'edge:refs').list())
            self.len(1, await core.eval(f'edge:refs=((test:guid, {guid}), (test:comp, (1010, test10)))').list())
            await core.eval(f'edge:refs=((test:guid, {guid}), (test:comp, (1010, test10)))').list()

            refs = await core.eval('test:guid -> edge:refs +#baz').list()

            self.len(1, refs)

            self.eq(refs[0].get('n2'), ('test:comp', (1010, 'test10')))
            self.eq(refs[0].ndef[1], (('test:guid', guid), ('test:comp', (1010, 'test10'))))

            self.len(1, await core.eval('test:comp:hehe=1010').list())

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

    async def test_migr_formname(self):

        async with self.getTestCore() as core:

            self.len(4, await core.eval('[ test:str=asdf test:str=qwer :tick=2019 +#hehe edge:refs=((test:int, 20), $node) .seen=2015 ] { +edge:refs +#haha }').list())

            # rename all test:str nodes to test:migr
            async with await s_migrate.Migration.anit(core) as migr:
                await migr.setFormName('test:str', 'test:migr')

            self.len(0, await core.eval('test:str').list())
            self.len(2, await core.eval('test:migr').list())

            self.len(0, await core.eval('test:str:tick').list())
            self.len(2, await core.eval('test:migr:tick').list())

            self.len(0, await core.eval('.created +test:str').list())
            self.len(2, await core.eval('.created +test:migr').list())

            self.len(0, await core.eval('#hehe +test:str').list())
            self.len(2, await core.eval('#hehe +test:migr').list())

            self.len(0, await core.eval('test:str.created').list())
            self.len(2, await core.eval('test:migr.created').list())

            self.len(0, await core.eval('test:str#hehe').list())
            self.len(2, await core.eval('test:migr#hehe').list())

            self.len(1, await core.eval('edge:refs=((test:int, 20),(test:migr, asdf))').list())
            self.len(2, await core.eval('edge:refs:n2:form=test:migr').list())

            self.len(1, await core.eval('test:migr^=as').list())
            self.len(2, await core.eval('test:migr:tick*range=(2013, 2020)').list())

            self.len(2, await core.eval('test:migr <- edge:refs').list())

            # check some hand-jammed layer iterators...
            layr = list(core.layers.values())[0]
            await self.agenlen(0, layr.iterFormRows('test:str'))
            await self.agenlen(0, layr.iterPropRows('test:str', 'tick'))

            await self.agenlen(2, layr.iterFormRows('test:migr'))
            await self.agenlen(2, layr.iterPropRows('test:migr', 'tick'))

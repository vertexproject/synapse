import synapse.exc as s_exc

import synapse.lib.nexus as s_nexus
import synapse.tests.utils as s_t_utils

class SampleNexus(s_nexus.Pusher):

    async def __anit__(self, iden, nexsroot=None):
        await s_nexus.Pusher.__anit__(self, iden=iden, nexsroot=nexsroot)
        self.iden = iden

    async def doathing(self, eventdict):
        return await self._push('thing:doathing', eventdict, 'foo')

    @s_nexus.Pusher.onPush('thing:doathing')
    async def _doathinghandler(self, eventdict, anotherparm):
        eventdict['happened'] = self.iden
        return anotherparm

    async def _push(self, event, *args, **kwargs):
        eventdict = args[0]
        eventdict['specialpush'] += 1
        return await s_nexus.Pusher._push(self, event, *args, **kwargs)

    async def doathing2(self, eventdict):
        return await self._push('thing:doathing2', eventdict, 'foo')

    @s_nexus.Pusher.onPush('thing:doathing2', passitem=True)
    async def _doathing2handler(self, eventdict, anotherparm, nexsitem=None):
        nexsoff, nexsmesg = nexsitem
        eventdict['gotindex'] = nexsoff
        return anotherparm

    @s_nexus.Pusher.onPushAuto('auto2')
    async def doathingauto(self, eventdict, anotherparm):
        eventdict['autohappened'] = self.iden
        return anotherparm

    @s_nexus.Pusher.onPushAuto('auto1')
    async def doathingauto2(self, eventdict, anotherparm):
        '''doc'''
        eventdict['autohappened2'] = self.iden
        return anotherparm

    @s_nexus.Pusher.onPushAuto('auto3')
    async def doathingauto3(self, eventdict):
        raise s_exc.SynErr(mesg='Test error')

class SampleNexus2(SampleNexus):
    async def doathing(self, eventdict):
        return await self._push('thing:doathing', eventdict, 'bar')

class NexusTest(s_t_utils.SynTest):

    async def test_nexus(self):

        with self.getTestDir() as dirn:

            async with await s_nexus.NexsRoot.anit(dirn) as nexsroot:
                await nexsroot.startup(None)

                async with await SampleNexus.anit(1, nexsroot=nexsroot) as nexus1:

                    eventdict = {'specialpush': 0}
                    self.eq('foo', await nexus1.doathing(eventdict))
                    self.eq(1, eventdict.get('happened'))

                    self.eq('foo', await nexus1.doathingauto(eventdict, 'foo'))
                    self.eq(1, eventdict.get('autohappened'))

                    self.eq('foo', await nexus1.doathingauto2(eventdict, 'foo'))
                    self.eq(1, eventdict.get('autohappened2'))

                    self.eq('doc', nexus1.doathingauto2.__doc__)

                    self.eq(3, await nexsroot.index())

                    async with await SampleNexus2.anit(2, nexsroot=nexsroot) as testkid:

                        eventdict = {'specialpush': 0}
                        # Tricky inheriting handler funcs themselves
                        self.eq('foo', await nexus1.doathing(eventdict))
                        self.eq('bar', await testkid.doathing(eventdict))
                        self.eq(2, eventdict.get('happened'))

                        # Check offset passing
                        self.eq('foo', await testkid.doathing2(eventdict))
                        self.eq(5, eventdict.get('gotindex'))

                        # Check raising an exception
                        await self.asyncraises(s_exc.SynErr, testkid.doathingauto3(eventdict))

                        with self.getLoggerStream('synapse.lib.nexus') as stream:
                            await nexsroot.recover()

                        stream.seek(0)
                        self.isin('while replaying log', stream.read())

    async def test_nexus_no_logging(self):
        '''
        Pushers/NexsRoot works with donexslog=False
        '''
        with self.getTestDir() as dirn:

            async with await s_nexus.NexsRoot.anit(dirn, donexslog=False) as nexsroot:

                async with await SampleNexus.anit(1, nexsroot=nexsroot) as nexus1:

                    await nexsroot.startup(None)

                    eventdict = {'specialpush': 0}
                    self.eq('foo', await nexus1.doathing(eventdict))
                    self.eq('foo', await nexus1.doathing2(eventdict))
                    self.eq(1, eventdict.get('happened'))
                    self.eq(1, eventdict.get('gotindex'))

                    self.eq(2, await nexsroot.index())

                    async with await SampleNexus2.anit(2, nexsroot=nexsroot) as nexus2:
                        eventdict = {'specialpush': 0}
                        self.eq('bar', await nexus2.doathing(eventdict))
                        self.eq('foo', await nexus2.doathing2(eventdict))
                        self.eq(2, eventdict.get('happened'))
                        self.eq(3, eventdict.get('gotindex'))

    async def test_nexus_setindex(self):

        async with self.getRegrCore('migrated-nexuslog') as core00:

            nexsindx = await core00.getNexsIndx()
            layrindx = max([await layr.getNodeEditOffset() for layr in core00.layers.values()])
            self.eq(nexsindx, layrindx)

            # Make sure a mirror gets updated to the correct index
            url = core00.getLocalUrl()
            core01conf = {'mirror': url}

            async with self.getRegrCore('migrated-nexuslog', conf=core01conf) as core01:

                await core01.sync()

                layrindx = max([await layr.getNodeEditOffset() for layr in core01.layers.values()])
                self.eq(nexsindx, layrindx)

            # Can only move index forward
            self.false(await core00.setNexsIndx(0))

        # Test with nexuslog disabled
        nologconf = {'nexslog:en': False}
        async with self.getRegrCore('migrated-nexuslog', conf=nologconf) as core:

            nexsindx = await core.getNexsIndx()
            layrindx = max([await layr.getNodeEditOffset() for layr in core.layers.values()])
            self.eq(nexsindx, layrindx)

import gc
import random
import asyncio
import contextlib
import collections

import synapse.exc as s_exc

import synapse.lib.coro as s_coro

from synapse.tests.utils import alist
import synapse.tests.utils as s_t_utils

class SnapTest(s_t_utils.SynTest):

    async def test_snap_eval_storm(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                await snap.addNode('test:str', 'hehe')
                await snap.addNode('test:str', 'haha')

                self.len(2, await alist(snap.eval('test:str')))

                await snap.addNode('test:str', 'hoho')

                self.len(3, await alist(snap.storm('test:str')))

    async def test_snap_feed_genr(self):

        async def testGenrFunc(snap, items):
            yield await snap.addNode('test:str', 'foo')
            yield await snap.addNode('test:str', 'bar')

        async with self.getTestCore() as core:

            core.setFeedFunc('test.genr', testGenrFunc)

            await core.addFeedData('test.genr', [])
            self.len(2, await alist(core.eval('test:str')))

            async with await core.snap() as snap:
                nodes = await alist(snap.addFeedNodes('test.genr', []))
                self.len(2, nodes)

            # Sad path test
            async def notagenr(snap, items):
                pass

            core.setFeedFunc('syn.notagenr', notagenr)

            with self.raises(s_exc.BadCtorType) as cm:
                await alist(snap.addFeedNodes('syn.notagenr', []))

            self.eq(cm.exception.get('mesg'),
                    "feed func returned a <class 'coroutine'>, not an async generator.")

    async def test_same_node_different_object(self):
        '''
        Test the problem in which a live node might be evicted out of the snap's buidcache causing two node
        objects to be representing the same logical thing.

        Also tests that creating a node then querying it back returns the same object
        '''
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                nodebuid = None
                snap.buidcache = collections.deque(maxlen=10)

                async def doit():
                    nonlocal nodebuid
                    # Reduce the buid cache so we don't have to make 100K nodes

                    node0 = await snap.addNode('test:int', 0)

                    node = await snap.getNodeByNdef(('test:int', 0))

                    # Test write then read coherency

                    self.eq(node0.buid, node.buid)
                    self.eq(id(node0), id(node))
                    nodebuid = node.buid

                    # Test read, then a bunch of reads, then read coherency

                    await alist(snap.addNodes([(('test:int', x), {}) for x in range(1, 20)]))
                    nodes = await alist(snap.getNodesBy('test:int'))

                    self.eq(nodes[0].buid, node0.buid)
                    self.eq(id(nodes[0]), id(node0))
                    # Hang a attr off of the node
                    setattr(node, '_test', True)

                await doit()  # run in separate function so that objects are gc'd

                gc.collect()

                # Test that coherency goes away (and we don't store all nodes forever)
                await alist(snap.addNodes([(('test:int', x), {}) for x in range(20, 30)]))

                node = await snap.getNodeByNdef(('test:int', 0))
                self.eq(nodebuid, node.buid)
                # Ensure that the node is not the same object as we encountered earlier.
                # We cannot check via id() since it is possible for a pyobject to be
                # allocated at the same location as the old object.
                self.false(hasattr(node, '_test'))

    async def test_addNodes(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                ndefs = ()
                self.len(0, await alist(snap.addNodes(ndefs)))

                ndefs = (
                    (('test:str', 'hehe'), {'props': {'.created': 5, 'tick': 3}, 'tags': {'cool': (1, 2)}}, ),
                )
                result = await alist(snap.addNodes(ndefs))
                self.len(1, result)

                node = result[0]
                self.eq(node.props.get('tick'), 3)
                self.ge(node.props.get('.created', 0), 5)
                self.eq(node.tags.get('cool'), (1, 2))

                nodes = await alist(snap.getNodesBy('test:str', 'hehe'))
                self.len(1, nodes)
                self.eq(nodes[0], node)

    async def test_addNodeRace(self):
        ''' Test when a reader might retrieve a partially constructed node '''
        NUM_TASKS = 2
        failed = False
        done_events = []

        data = list(range(50))
        rnd = random.Random()
        rnd.seed(4)  # chosen by fair dice roll
        rnd.shuffle(data)

        async with self.getTestCore() as core:

            async def write_a_bunch(done_event):
                nonlocal failed
                await asyncio.sleep(0)
                async with await core.snap() as snap:

                    async def waitabit(info):
                        await asyncio.sleep(0.1)

                    snap.on('node:add', waitabit)

                    for i in data:
                        node = await snap.addNode('test:int', i)
                        if node.props.get('.created') is None:
                            failed = True
                            done_event.set()
                            return
                        await asyncio.sleep(0)
                done_event.set()

            for _ in range(NUM_TASKS):
                done_event = asyncio.Event()
                core.schedCoro(write_a_bunch(done_event))
                done_events.append(done_event)

            for event in done_events:
                await event.wait()

            self.false(failed)

    async def test_addNodeRace2(self):
        ''' Test that dependencies between active editatoms don't wedge '''
        bc_done_event = asyncio.Event()
        ab_middle_event = asyncio.Event()
        ab_done_event = asyncio.Event()

        async with self.getTestCore() as core:
            async def bc_writer():
                async with await core.snap() as snap:
                    call_count = 0

                    origGetNodeByBuid = snap.getNodeByBuid

                    async def slowGetNodeByBuid(buid):
                        nonlocal call_count
                        call_count += 1
                        if call_count > 0:
                            await ab_middle_event.wait()
                        return await origGetNodeByBuid(buid)

                    snap.getNodeByBuid = slowGetNodeByBuid

                    await snap.addNode('test:pivcomp', ('woot', 'rofl'))
                bc_done_event.set()

            core.schedCoro(bc_writer())
            await asyncio.sleep(0)

            async def ab_writer():
                async with await core.snap() as snap:

                    origGetNodeByBuid = snap.getNodeByBuid

                    async def slowGetNodeByBuid(buid):
                        ab_middle_event.set()
                        return await origGetNodeByBuid(buid)

                    snap.getNodeByBuid = slowGetNodeByBuid

                    await snap.addNode('test:haspivcomp', 42, props={'have': ('woot', 'rofl')})
                ab_done_event.set()

            core.schedCoro(ab_writer())
            self.true(await s_coro.event_wait(bc_done_event, 5))
            self.true(await s_coro.event_wait(ab_done_event, 5))

    @contextlib.asynccontextmanager
    async def _getTestCoreMultiLayer(self):
        '''
        Custom logic to make a second cortex that puts another cortex's layer underneath.

        Notes:
            This method is broken out so subclasses can override.
        '''
        async with self.getTestCore() as core0:

            async with self.getTestCore() as core1:

                config = {'url': core0.getLocalUrl('*/layer')}
                layr = await core1.addLayer(type='remote', config=config)

                await core1.view.addLayer(layr)
                yield core0, core1

    async def test_cortex_lift_layers_simple(self):
        async with self._getTestCoreMultiLayer() as (core0, core1):
            ''' Test that you can write to core0 and read it from core 1 '''
            self.len(1, await core0.eval('[ inet:ipv4=1.2.3.4 :asn=42 +#woot=(2014, 2015)]').list())
            self.len(1, await core1.eval('inet:ipv4').list())
            self.len(1, await core1.eval('inet:ipv4=1.2.3.4').list())
            self.len(1, await core1.eval('inet:ipv4:asn=42').list())
            self.len(1, await core1.eval('inet:ipv4 +:asn=42').list())
            self.len(1, await core1.eval('inet:ipv4 +#woot').list())

    async def test_cortex_lift_layers_bad_filter(self):
        '''
        Test a two layer cortex where a lift operation gives the wrong result
        '''
        async with self._getTestCoreMultiLayer() as (core0, core1):

            self.len(1, await core0.eval('[ inet:ipv4=1.2.3.4 :asn=42 +#woot=(2014, 2015)]').list())
            self.len(1, await core1.eval('inet:ipv4=1.2.3.4 [ :asn=31337 +#woot=2016 ]').list())

            self.len(0, await core0.eval('inet:ipv4:asn=31337').list())
            self.len(1, await core1.eval('inet:ipv4:asn=31337').list())

            self.len(1, await core0.eval('inet:ipv4:asn=42').list())
            self.len(0, await core1.eval('inet:ipv4:asn=42').list())

    async def test_cortex_lift_layers_dup(self):
        '''
        Test a two layer cortex where a lift operation might give the same node twice incorrectly
        '''
        async with self._getTestCoreMultiLayer() as (core0, core1):
            # add to core1 first so we can cause creation in both...
            self.len(1, await core1.eval('[ inet:ipv4=1.2.3.4 :asn=42 ]').list())
            self.len(1, await core0.eval('[ inet:ipv4=1.2.3.4 :asn=42 ]').list())

            # lift by primary and ensure only one...
            self.len(1, await core1.eval('inet:ipv4').list())

            # lift by secondary and ensure only one...
            self.len(1, await core1.eval('inet:ipv4:asn=42').list())

            # now set one to a diff value that we will ask for but should be masked
            self.len(1, await core0.eval('[ inet:ipv4=1.2.3.4 :asn=99 ]').list())
            self.len(0, await core1.eval('inet:ipv4:asn=99').list())

    async def test_cortex_lift_bytype(self):
        async with self.getTestCore() as core:
            await core.nodes('[ inet:dns:a=(vertex.link, 1.2.3.4) ]')
            nodes = await core.nodes('inet:ipv4*type=1.2.3.4')
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))
            self.eq(nodes[1].ndef, ('inet:dns:a', ('vertex.link', 0x01020304)))

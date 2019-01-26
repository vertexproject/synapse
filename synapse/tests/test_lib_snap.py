import os
import random
import asyncio
import contextlib

import synapse.common as s_common

from synapse.tests.utils import alist
import synapse.tests.utils as s_t_utils

class SnapTest(s_t_utils.SynTest):

    async def test_snap_eval_storm(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                await snap.addNode('teststr', 'hehe')
                await snap.addNode('teststr', 'haha')

                self.len(2, await alist(snap.eval('teststr')))

                await snap.addNode('teststr', 'hoho')

                self.len(3, await alist(snap.storm('teststr')))

    async def test_stor(self):
        async with self.getTestCore() as core:

            # Bulk
            async with await core.snap() as snap:
                snap.bulk = True
                self.eq(snap.bulksops, ())

                self.none(await snap.stor((1,)))
                self.eq(snap.bulksops, (1,))

                self.none(await snap.stor((2,)))
                self.eq(snap.bulksops, (1, 2,))

    async def test_snap_feed_genr(self):

        async def testGenrFunc(snap, items):
            yield await snap.addNode('teststr', 'foo')
            yield await snap.addNode('teststr', 'bar')

        async with self.getTestCore() as core:

            core.setFeedFunc('test.genr', testGenrFunc)

            await core.addFeedData('test.genr', [])
            self.len(2, await alist(core.eval('teststr')))

            async with await core.snap() as snap:
                nodes = await alist(snap.addFeedNodes('test.genr', []))
                self.len(2, nodes)

    async def test_addNodes(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                ndefs = ()
                self.len(0, await alist(snap.addNodes(ndefs)))

                ndefs = (
                    (('teststr', 'hehe'), {'props': {'.created': 5, 'tick': 3}, 'tags': {'cool': (1, 2)}}, ),
                )
                result = await alist(snap.addNodes(ndefs))
                self.len(1, result)

                node = result[0]
                self.eq(node.props.get('tick'), 3)
                self.ge(node.props.get('.created', 0), 5)
                self.eq(node.tags.get('cool'), (1, 2))

                nodes = await alist(snap.getNodesBy('teststr', 'hehe'))
                self.len(1, nodes)
                self.eq(nodes[0], node)

    async def test_addNodeRace(self):
        ''' Test when a reader might retrieve a partially constructed node '''
        NUM_TASKS = 2
        failed = False
        done_events = []
        async with self.getTestCore() as core:

            async def write_a_bunch(done_event):
                nonlocal failed
                data = list(range(50))
                random.seed(4)  # chosen by fair dice roll
                random.shuffle(data)
                await asyncio.sleep(0)
                async with await core.snap() as snap:

                    async def waitabit(info):
                        await asyncio.sleep(0.1)

                    snap.on('node:add', waitabit)

                    for i in data:
                        node = await snap.addNode('testint', i)
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

                    async def slowGetNodeByBuid(buid):
                        nonlocal call_count
                        call_count += 1
                        if call_count > 0:
                            await ab_middle_event.wait()
                        return await snap.buidcache.aget(buid)

                    snap.getNodeByBuid = slowGetNodeByBuid

                    await snap.addNode('pivcomp', ('woot', 'rofl'))
                bc_done_event.set()

            core.schedCoro(bc_writer())
            await asyncio.sleep(0)

            async def ab_writer():
                async with await core.snap() as snap:

                    async def slowGetNodeByBuid(buid):
                        ab_middle_event.set()
                        return await snap.buidcache.aget(buid)

                    snap.getNodeByBuid = slowGetNodeByBuid

                    await snap.addNode('haspivcomp', 42, props={'have': ('woot', 'rofl')})
                ab_done_event.set()

            core.schedCoro(ab_writer())
            await bc_done_event.wait()
            await ab_done_event.wait()

    @contextlib.asynccontextmanager
    async def _getTestCoreMultiLayer(self, first_dirn):
        '''
        Custom logic to make a second cortex that puts another cortex's layer underneath.

        Notes:
            This method is broken out so subclasses can override.
        '''
        tmp, self.alt_write_layer = self.alt_write_layer, None
        layerfn = os.path.join(first_dirn, 'layers', '000-default')
        async with self.getTestCore(extra_layers=[layerfn]) as core:
            yield core
        self.alt_write_layer = tmp

    async def test_cortex_lift_layers_bad_filter(self):
        '''
        Test a two layer cortex where a lift operation gives the wrong result
        '''
        async with self.getTestCore() as core1:
            node = (('inet:ipv4', 1), {'props': {'asn': 42, '.seen': (1, 2)}, 'tags': {'woot': (1, 2)}})
            nodes_core1 = await alist(core1.addNodes([node]))
            await core1.fini()

            async with self._getTestCoreMultiLayer(core1.dirn) as core, await core.snap() as snap:
                # Basic sanity checks

                # Make sure only the top layer is writeable
                self.true(core.layers[0].readonly)
                self.true(core.layers[0].slab.readonly)
                self.false(core.layers[1].readonly)
                self.false(core.layers[1].slab.readonly)

                nodes = await alist(snap.getNodesBy('inet:ipv4', 1))
                self.len(1, nodes)
                nodes = await alist(snap.getNodesBy('inet:ipv4.seen', 1))
                self.len(1, nodes)
                self.eq(nodes_core1[0].pack(), nodes[0].pack())
                nodes = await alist(snap.getNodesBy('inet:ipv4#woot', 1))
                self.len(1, nodes)
                nodes = await alist(snap.getNodesBy('inet:ipv4#woot', 99))
                self.len(0, nodes)

                # Now change asn in the "higher" layer
                changed_node = (('inet:ipv4', 1), {'props': {'asn': 43, '.seen': (3, 4)}, 'tags': {'woot': (3, 4)}})
                nodes = await alist(snap.addNodes([changed_node]))
                # Lookup by prop
                nodes = await alist(snap.getNodesBy('inet:ipv4:asn', 42))
                self.len(0, nodes)

                # Lookup by univ prop
                nodes = await alist(snap.getNodesBy('inet:ipv4.seen', 1))
                self.len(0, nodes)

                # Lookup by formtag
                nodes = await alist(snap.getNodesBy('inet:ipv4#woot', 1))
                self.len(0, nodes)

                # Lookup by tag
                nodes = await alist(snap.getNodesBy('#woot', 1))
                self.len(0, nodes)

    async def test_cortex_lift_layers_dup(self):
        '''
        Test a two layer cortex where a lift operation might give the same node twice incorrectly
        '''
        async with self.getTestCore() as core1:
            node = (('inet:ipv4', 1), {'props': {'asn': 42}})
            nodes_core1 = await alist(core1.addNodes([node]))
            await core1.fini()

            async with self._getTestCoreMultiLayer(core1.dirn) as core, await core.snap() as snap:
                # Basic sanity check first
                nodes = await alist(snap.getNodesBy('inet:ipv4', 1))
                self.len(1, nodes)
                self.eq(nodes_core1[0].pack(), nodes[0].pack())

                # Now set asn in the "higher" layer to the same (by changing it, then changing it back)
                changed_node = (('inet:ipv4', 1), {'props': {'asn': 43}})
                await s_common.aspin(snap.addNodes([changed_node]))
                changed_node = (('inet:ipv4', 1), {'props': {'asn': 42}})
                nodes = await alist(snap.addNodes([changed_node]))
                nodes = await alist(snap.getNodesBy('inet:ipv4:asn', 42))
                self.len(1, nodes)

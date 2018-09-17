import os
import contextlib
import synapse.glob as s_glob

from synapse.tests.utils import alist
import synapse.tests.utils as s_t_utils

class SnapTest(s_t_utils.SynTest):

    async def test_snap_eval_storm(self):

        async with self.agetTestCore() as core:

            with core.snap() as snap:

                await snap.addNode('teststr', 'hehe')
                await snap.addNode('teststr', 'haha')

                self.len(2, await snap.eval('teststr'))

                await snap.addNode('teststr', 'hoho')

                self.len(3, await alist(snap.storm('teststr')))

    async def test_stor(self):
        async with self.agetTestCore() as core:

            # Bulk
            with core.snap() as snap:
                snap.bulk = True
                self.eq(snap.bulksops, ())

                self.none(await snap.stor((1,)))
                self.eq(snap.bulksops, (1,))

                self.none(await snap.stor((2,)))
                self.eq(snap.bulksops, (1, 2,))

    async def test_snap_feed_genr(self):

        def testGenrFunc(snap, items):
            yield snap.addNode('teststr', 'foo')
            yield snap.addNode('teststr', 'bar')

        async with self.agetTestCore() as core:

            core.setFeedFunc('test.genr', testGenrFunc)

            core.addFeedData('test.genr', [])
            self.len(2, await alist(core.eval('teststr')))

            with core.snap() as snap:
                nodes = await alist(snap.addFeedNodes('test.genr', []))
                self.len(2, nodes)

    async def test_addNodes(self):
        async with self.agetTestCore() as core:
            async with core.snap() as snap:
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

    @contextlib.asynccontextmanager
    async def _getTestCoreMultiLayer(self, first_dirn):
        '''
        Custom logic to make a second cortex that puts another cortex's layer underneath.

        Notes:
            This method is broken out so subclasses can override.
        '''
        layerfn = os.path.join(first_dirn, 'layers', '000-default')
        async with self.agetTestCore(extra_layers=[layerfn]) as core:
            yield core

    async def test_cortex_lift_layers_bad_filter(self):
        '''
        Test a two layer cortex where a lift operation gives the wrong result
        '''
        async with self.agetTestCore() as core1:
            node = (('inet:ipv4', 1), {'props': {'asn': 42, '.seen': (1, 2)}, 'tags': {'woot': (1, 2)}})
            nodes_core1 = await alist(core1.addNodes([node]))

            async with self._getTestCoreMultiLayer(core1.dirn) as core, core.snap() as snap:
                # Basic sanity check
                nodes = await alist(snap.getNodesBy('inet:ipv4', 1))
                self.len(1, nodes)
                nodes = await alist(snap.getNodesBy('inet:ipv4.seen', 1))
                self.len(1, nodes)
                self.eq(nodes_core1[0].pack(), nodes[0].pack())
                nodes = await alist(snap.getNodesBy('inet:ipv4#woot', 1))
                self.len(1, nodes)
                nodes = await alist(snap.getNodesBy('inet:ipv4#woot', 99))
                self.len(0, await nodes)

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
        async with self.agetTestCore() as core1:
            node = (('inet:ipv4', 1), {'props': {'asn': 42}})
            nodes_core1 = await alist(core1.addNodes([node]))

            async with self._getTestCoreMultiLayer(core1.dirn) as core, core.snap() as snap:
                # Basic sanity check
                nodes = await alist(snap.getNodesBy('inet:ipv4', 1))
                self.len(1, nodes)
                self.eq(nodes_core1[0].pack(), nodes[0].pack())

                # Now set asn in the "higher" layer to the same (by changing it, then changing it back)
                changed_node = (('inet:ipv4', 1), {'props': {'asn': 43}})
                nodes = await alist(snap.addNodes([changed_node]))
                changed_node = (('inet:ipv4', 1), {'props': {'asn': 42}})
                nodes = await alist(snap.addNodes([changed_node]))
                nodes = await alist(snap.getNodesBy('inet:ipv4:asn', 42))
                self.len(1, nodes)

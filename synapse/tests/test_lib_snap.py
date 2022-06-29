import gc
import random
import asyncio
import contextlib
import collections

import synapse.exc as s_exc
import synapse.common as s_common

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

    async def test_snap_fires(self):
        events = []
        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                def on(evnt):
                    events.append(evnt)
                snap.on('print', on)
                await snap.printf('beep')
                await snap.printf('boop')
                self.len(2, events)
                self.eq(['beep', 'boop'],
                        [m[1].get('mesg') for m in events])

                events.clear()
                snap.on('warn', on)
                await snap.warnonce('warnonce', False, key='valu')
                await snap.warnonce('warnonce', False, key='valu')
                self.len(1, events)
                self.eq(events[0], ('warn', {'mesg': 'warnonce', 'key': 'valu'}))

                events.clear()
                await snap.warn('warn', False, key='valu')
                await snap.warn('warn2', False)
                self.len(2, events)
                self.eq(events[0], ('warn', {'mesg': 'warn', 'key': 'valu'}))
                self.eq(events[1], ('warn', {'mesg': 'warn2'}))

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
                    nodes = await alist(snap.nodesByProp('test:int'))

                    self.eq(nodes[0].buid, node0.buid)
                    self.eq(id(nodes[0]), id(node0))
                    node._test = True

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

                nodes = await alist(snap.nodesByPropValu('test:str', '=', 'hehe'))
                self.len(1, nodes)
                self.eq(nodes[0], node)

                # Make sure that we can still add secondary props even if the node already exists
                node2 = await snap.addNode('test:str', 'hehe', props={'baz': 'test:guid:tick=2020'})
                self.eq(node2, node)
                self.nn(node2.get('baz'))

    async def test_addNodesAuto(self):
        '''
        Secondary props that are forms when set make nodes
        '''
        async with self.getTestCore() as core:
            async with await core.snap() as snap:

                node = await snap.addNode('test:guid', '*')
                await node.set('size', 42)
                nodes = await alist(snap.nodesByPropValu('test:int', '=', 42))
                self.len(1, nodes)

                # For good measure, set a secondary prop that is itself a comp type that has an element that
                # is a form
                node = await snap.addNode('test:haspivcomp', 42)
                await node.set('have', ('woot', 'rofl'))
                nodes = await alist(snap.nodesByPropValu('test:pivcomp', '=', ('woot', 'rofl')))
                self.len(1, nodes)
                nodes = await alist(snap.nodesByProp('test:pivcomp:lulz'))
                self.len(1, nodes)
                nodes = await alist(snap.nodesByPropValu('test:str', '=', 'rofl'))
                self.len(1, nodes)

                # Make sure the sodes didn't get misordered
                node = await snap.addNode('inet:dns:a', ('woot.com', '1.2.3.4'))
                self.eq(node.ndef[0], 'inet:dns:a')

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
        Create a cortex with a second view which has an additional layer above the main layer.

        Notes:
            This method is broken out so subclasses can override.
        '''
        async with self.getTestCore() as core0:

            view0 = core0.view
            layr0 = view0.layers[0]

            ldef1 = await core0.addLayer()
            layr1 = core0.getLayer(ldef1.get('iden'))
            vdef1 = await core0.addView({'layers': [layr1.iden, layr0.iden]})

            yield view0, core0.getView(vdef1.get('iden'))

    async def test_cortex_lift_layers_simple(self):
        async with self._getTestCoreMultiLayer() as (view0, view1):
            ''' Test that you can write to view0 and read it from view1 '''
            self.len(1, await alist(view0.eval('[ inet:ipv4=1.2.3.4 :asn=42 +#woot=(2014, 2015)]')))
            self.len(1, await alist(view1.eval('inet:ipv4')))
            self.len(1, await alist(view1.eval('inet:ipv4=1.2.3.4')))
            self.len(1, await alist(view1.eval('inet:ipv4:asn=42')))
            self.len(1, await alist(view1.eval('inet:ipv4 +:asn=42')))
            self.len(1, await alist(view1.eval('inet:ipv4 +#woot')))

    async def test_cortex_lift_layers_bad_filter(self):
        '''
        Test a two layer cortex where a lift operation gives the wrong result
        '''
        async with self._getTestCoreMultiLayer() as (view0, view1):

            self.len(1, await alist(view0.eval('[ inet:ipv4=1.2.3.4 :asn=42 +#woot=(2014, 2015)]')))
            self.len(1, await alist(view1.eval('inet:ipv4#woot@=2014')))
            self.len(1, await alist(view1.eval('inet:ipv4=1.2.3.4 [ :asn=31337 +#woot=2016 ]')))

            self.len(0, await alist(view0.eval('inet:ipv4:asn=31337')))
            self.len(1, await alist(view1.eval('inet:ipv4:asn=31337')))

            self.len(1, await alist(view0.eval('inet:ipv4:asn=42')))
            self.len(0, await alist(view1.eval('inet:ipv4:asn=42')))

            self.len(1, await alist(view0.eval('[ test:arrayprop="*" :ints=(1, 2, 3) ]')))
            self.len(1, await alist(view1.eval('test:int=2 -> test:arrayprop')))
            self.len(1, await alist(view1.eval('test:arrayprop [ :ints=(4, 5, 6) ]')))

            self.len(0, await alist(view0.eval('test:int=5 -> test:arrayprop')))
            self.len(1, await alist(view1.eval('test:int=5 -> test:arrayprop')))

            self.len(1, await alist(view0.eval('test:int=2 -> test:arrayprop')))
            self.len(0, await alist(view1.eval('test:int=2 -> test:arrayprop')))

            self.len(1, await alist(view1.eval('[ test:int=7 +#atag=2020 ]')))
            self.len(1, await alist(view0.eval('[ test:int=7 +#atag=2021 ]')))

            self.len(0, await alist(view0.eval('test:int#atag@=2020')))
            self.len(1, await alist(view1.eval('test:int#atag@=2020')))

            self.len(1, await alist(view0.eval('test:int#atag@=2021')))
            self.len(0, await alist(view1.eval('test:int#atag@=2021')))

    async def test_cortex_lift_layers_dup(self):
        '''
        Test a two layer cortex where a lift operation might give the same node twice incorrectly
        '''
        async with self._getTestCoreMultiLayer() as (view0, view1):
            # add to view1 first so we can cause creation in both...
            self.len(1, await alist(view1.eval('[ inet:ipv4=1.2.3.4 :asn=42 ]')))
            self.len(1, await alist(view0.eval('[ inet:ipv4=1.2.3.4 :asn=42 ]')))

            # lift by primary and ensure only one...
            self.len(1, await alist(view1.eval('inet:ipv4')))

            # lift by secondary and ensure only one...
            self.len(1, await alist(view1.eval('inet:ipv4:asn=42')))

            # now set one to a diff value that we will ask for but should be masked
            self.len(1, await alist(view0.eval('[ inet:ipv4=1.2.3.4 :asn=99 ]')))
            self.len(0, await alist(view1.eval('inet:ipv4:asn=99')))

    async def test_cortex_lift_bytype(self):
        async with self.getTestCore() as core:
            await core.nodes('[ inet:dns:a=(vertex.link, 1.2.3.4) ]')
            nodes = await core.nodes('inet:ipv4*type=1.2.3.4')
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))
            self.eq(nodes[1].ndef, ('inet:dns:a', ('vertex.link', 0x01020304)))

    async def test_clearcache(self):

        # Type hinting since we dont do the type hinting
        # properly in the Cortex anymore... :(
        import synapse.lib.snap as s_snap

        async with self.getTestCore() as core:
            async with await core.snap() as snap0:  # type: s_snap.Snap

                original_node0 = await snap0.addNode('test:str', 'node0')
                self.len(1, snap0.buidcache)
                self.len(1, snap0.livenodes)
                self.len(0, snap0.tagcache)
                self.len(0, snap0.tagnorms)

                await original_node0.addTag('foo.bar.baz')
                self.len(4, snap0.buidcache)
                self.len(4, snap0.livenodes)
                self.len(3, snap0.tagnorms)

                async with await core.snap() as snap1:  # type: s_snap.Snap
                    snap1_node0 = await snap1.getNodeByNdef(('test:str', 'node0'))
                    await snap1_node0.delTag('foo.bar.baz')
                    self.notin('foo.bar.baz', snap1_node0.tags)
                    # Our reference to original_node0 still has the tag though
                    self.isin('foo.bar.baz', original_node0.tags)

                # We rely on the layer's row cache to be correct in this test.

                # Lift is cached..
                same_node0 = await snap0.getNodeByNdef(('test:str', 'node0'))
                self.eq(id(original_node0), id(same_node0))

                # flush snap0 cache!
                await snap0.clearCache()
                self.len(0, snap0.buidcache)
                self.len(0, snap0.livenodes)
                self.len(0, snap0.tagcache)
                self.len(0, snap0.tagnorms)

                # After clearing the cache and lifting nodes, the new node
                # was lifted directly from the layer.
                new_node0 = await snap0.getNodeByNdef(('test:str', 'node0'))
                self.ne(id(original_node0), id(new_node0))
                self.notin('foo.bar.baz', new_node0.tags)

    async def test_cortex_lift_layers_bad_filter_tagprop(self):
        '''
        Test a two layer cortex where a lift operation gives the wrong result, with tagprops
        '''
        async with self._getTestCoreMultiLayer() as (view0, view1):
            await view0.core.addTagProp('score', ('int', {}), {'doc': 'hi there'})

            self.len(1, await view0.nodes('[ test:int=10 +#woot:score=20 ]'))
            self.len(1, await view1.nodes('#woot:score=20'))
            self.len(1, await view1.nodes('[ test:int=10 +#woot:score=40 ]'))

            self.len(0, await view0.nodes('#woot:score=40'))
            self.len(1, await view1.nodes('#woot:score=40'))

            self.len(1, await view0.nodes('#woot:score=20'))
            self.len(0, await view1.nodes('#woot:score=20'))

    async def test_cortex_lift_layers_dup_tagprop(self):
        '''
        Test a two layer cortex where a lift operation might give the same node twice incorrectly
        '''
        async with self._getTestCoreMultiLayer() as (view0, view1):
            await view0.core.addTagProp('score', ('int', {}), {'doc': 'hi there'})

            self.len(1, await view1.nodes('[ test:int=10 +#woot:score=20 ]'))
            self.len(1, await view0.nodes('[ test:int=10 +#woot:score=20 ]'))

            self.len(1, await view1.nodes('#woot:score=20'))

            self.len(1, await view0.nodes('[ test:int=10 +#woot:score=40 ]'))

    async def test_cortex_lift_layers_ordering(self):

        async with self._getTestCoreMultiLayer() as (view0, view1):

            await view0.core.addTagProp('score', ('int', {}), {'doc': 'hi there'})
            await view0.core.addTagProp('data', ('data', {}), {'doc': 'hi there'})

            await view0.nodes('[ inet:ipv4=1.1.1.4 ]')
            await view1.nodes('inet:ipv4=1.1.1.4 [+#tag]')
            await view0.nodes('inet:ipv4=1.1.1.4 | delnode')
            nodes = await view1.nodes('#tag | uniq')
            self.len(0, nodes)

            await view0.nodes('[ inet:ipv4=1.1.1.4 :asn=4 +#woot:score=4] $node.data.set(woot, 4)')
            await view0.nodes('[ inet:ipv4=1.1.1.1 :asn=1 +#woot:score=1] $node.data.set(woot, 1)')
            await view1.nodes('[ inet:ipv4=1.1.1.2 :asn=2 +#woot:score=2] $node.data.set(woot, 2)')
            await view0.nodes('[ inet:ipv4=1.1.1.3 :asn=3 +#woot:score=3] $node.data.set(woot, 3)')

            await view1.nodes('[ test:str=foo +#woot=2001 ]')
            await view0.nodes('[ test:str=foo +#woot=2001 ]')
            await view0.nodes('[ test:int=1 +#woot=2001 ]')
            await view0.nodes('[ test:int=2 +#woot=2001 ]')

            nodes = await view1.nodes('#woot')
            self.len(7, nodes)

            nodes = await view1.nodes('inet:ipv4')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                valu = node.ndef[1]
                self.gt(valu, last)
                last = valu

            nodes = await view1.nodes('inet:ipv4:asn')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                asn = node.props.get('asn')
                self.gt(asn, last)
                last = asn

            nodes = await view1.nodes('inet:ipv4:asn>0')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                asn = node.props.get('asn')
                self.gt(asn, last)
                last = asn

            nodes = await view1.nodes('inet:ipv4:asn*in=(1,2,3,4)')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                asn = node.props.get('asn')
                self.gt(asn, last)
                last = asn

            nodes = await view1.nodes('inet:ipv4:asn*in=(4,3,2,1)')
            self.len(4, nodes)
            last = 5
            for node in nodes:
                asn = node.props.get('asn')
                self.lt(asn, last)
                last = asn

            nodes = await view1.nodes('#woot:score')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                scor = node.getTagProp('woot', 'score')
                self.gt(scor, last)
                last = scor

            nodes = await view1.nodes('#woot:score>0')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                scor = node.getTagProp('woot', 'score')
                self.gt(scor, last)
                last = scor

            nodes = await view1.nodes('#woot:score*in=(1,2,3,4)')
            self.len(4, nodes)
            last = 0
            for node in nodes:
                scor = node.getTagProp('woot', 'score')
                self.gt(scor, last)
                last = scor

            nodes = await view1.nodes('#woot:score*in=(4,3,2,1)')
            self.len(4, nodes)
            last = 5
            for node in nodes:
                scor = node.getTagProp('woot', 'score')
                self.lt(scor, last)
                last = scor

            await view0.nodes('[ test:arrayform=(3,5,6)]')
            await view0.nodes('[ test:arrayform=(1,2,3)]')
            await view1.nodes('[ test:arrayform=(2,3,4)]')
            await view0.nodes('[ test:arrayform=(3,4,5)]')

            nodes = await view1.nodes('test:arrayform*[=3]')
            self.len(4, nodes)

            nodes = await view1.nodes('test:arrayform*[=2]')
            self.len(2, nodes)

            nodes = await view1.nodes('yield $lib.lift.byNodeData(woot)')
            self.len(4, nodes)

            self.len(1, await view1.nodes('[crypto:x509:cert="*" :identities:fqdns=(somedomain.biz,www.somedomain.biz)]'))
            nodes = await view1.nodes('crypto:x509:cert:identities:fqdns*[="*.biz"]')
            self.len(2, nodes)

            self.len(1, await view1.nodes('[crypto:x509:cert="*" :identities:fqdns=(somedomain.biz,www.somedomain.biz)]'))
            nodes = await view1.nodes('crypto:x509:cert:identities:fqdns*[="*.biz"]')
            self.len(4, nodes)

            await view0.nodes('[ test:data=(123) :data=(123) +#woot:data=(123)]')
            await view1.nodes('[ test:data=foo :data=foo +#woot:data=foo]')
            await view0.nodes('[ test:data=(0) :data=(0) +#woot:data=(0)]')
            await view0.nodes('[ test:data=bar :data=foo +#woot:data=foo]')

            nodes = await view1.nodes('test:data')
            self.len(4, nodes)

            nodes = await view1.nodes('test:data=foo')
            self.len(1, nodes)

            nodes = await view1.nodes('test:data:data')
            self.len(4, nodes)

            nodes = await view1.nodes('test:data:data=foo')
            self.len(2, nodes)

            nodes = await view1.nodes('#woot:data')
            self.len(4, nodes)

            nodes = await view1.nodes('#woot:data=foo')
            self.len(2, nodes)

    async def test_snap_editor(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ media:news=63381924986159aff183f0c85bd8ebad +(refs)> {[ inet:fqdn=vertex.link ]} ]')
            root = core.auth.rootuser
            async with await core.view.snap(user=root) as snap:
                async with snap.getEditor() as editor:
                    fqdn = await editor.addNode('inet:fqdn', 'vertex.link')
                    news = await editor.addNode('media:news', '63381924986159aff183f0c85bd8ebad')
                    self.false(await news.addEdge('refs', s_common.ehex(fqdn.buid)))
                    self.len(0, editor.getNodeEdits())

                    self.true(await news.addEdge('pwns', s_common.ehex(fqdn.buid)))
                    nodeedits = editor.getNodeEdits()
                    self.len(1, nodeedits)
                    self.len(1, nodeedits[0][2])

            self.len(1, await core.nodes('media:news -(pwns)> *'))

            self.len(1, await core.nodes('[ inet:dns:soa=(lol,) :fqdn=vertex.link ]'))
            self.len(1, await core.nodes('inet:dns:soa=(lol,) [ :fqdn=vertex.link ]'))
            with self.raises(s_exc.ReadOnlyProp):
                await core.nodes('inet:dns:soa=(lol,) [ :fqdn=woot.com ]')

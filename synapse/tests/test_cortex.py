import copy
import time
import asyncio
import logging

from unittest.mock import patch

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.coro as s_coro
import synapse.lib.node as s_node
import synapse.lib.layer as s_layer
import synapse.lib.version as s_version

import synapse.tools.backup as s_tools_backup

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

logger = logging.getLogger(__name__)

class CortexTest(s_t_utils.SynTest):
    '''
    The tests that should be run with different types of layers
    '''
    async def test_cortex_must_upgrade(self):

        with self.getTestDir() as dirn:

            async with await s_cortex.Cortex.anit(dirn) as core:
                self.nn(await core.cellinfo.pop('cortex:version'))

            with self.raises(s_exc.BadStorageVersion):
                async with await s_cortex.Cortex.anit(dirn) as core:
                    pass

    async def test_cortex_rawpivot(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:ipv4=1.2.3.4] $ipv4=$node.value() -> { [ inet:dns:a=(woot.com, $ipv4) ] }')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:dns:a', ('woot.com', 0x01020304)))

    async def test_cortex_edges(self):

        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                news = await snap.addNode('media:news', '*')
                ipv4 = await snap.addNode('inet:ipv4', '1.2.3.4')

                await news.addEdge('refs', ipv4.iden())

                n1edges = await alist(news.iterEdgesN1())
                n2edges = await alist(ipv4.iterEdgesN2())

                self.eq(n1edges, (('refs', ipv4.iden()),))
                self.eq(n2edges, (('refs', news.iden()),))

                await news.delEdge('refs', ipv4.iden())

                self.len(0, await alist(news.iterEdgesN1()))
                self.len(0, await alist(ipv4.iterEdgesN2()))

            nodes = await core.nodes('media:news [ +(refs)> {inet:ipv4=1.2.3.4} ]')
            self.eq(nodes[0].ndef[0], 'media:news')

            # check all the walk from N1 syntaxes
            nodes = await core.nodes('media:news -(refs)> *')
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            self.len(0, await core.nodes('media:news -(refs)> mat:spec'))

            nodes = await core.nodes('media:news -(refs)> inet:ipv4')
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('media:news -(refs)> (inet:ipv4,inet:ipv6)')
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('media:news -(*)> *')
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('$types = (refs,hehe) media:news -($types)> *')
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('$types = (*,) media:news -($types)> *')
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            # check all the walk from N2 syntaxes
            nodes = await core.nodes('inet:ipv4 <(refs)- *')
            self.eq(nodes[0].ndef[0], 'media:news')

            nodes = await core.nodes('inet:ipv4 <(*)- *')
            self.eq(nodes[0].ndef[0], 'media:news')

            # coverage for isDestForm()
            self.len(0, await core.nodes('inet:ipv4 <(*)- mat:spec'))
            self.len(0, await core.nodes('media:news -(*)> mat:spec'))
            self.len(0, await core.nodes('inet:ipv4 <(*)- (mat:spec,)'))
            self.len(0, await core.nodes('media:news -(*)> (mat:spec,)'))
            self.len(0, await core.nodes('media:news -((refs,foos))> mat:spec'))
            self.len(0, await core.nodes('inet:ipv4 <((refs,foos))- mat:spec'))

            with self.raises(s_exc.StormRuntimeError):
                self.len(0, await core.nodes('inet:ipv4 <(*)- $(0)'))

            with self.raises(s_exc.StormRuntimeError):
                self.len(0, await core.nodes('media:news -(*)> $(0)'))

            nodes = await core.nodes('$types = (refs,hehe) inet:ipv4 <($types)- *')
            self.eq(nodes[0].ndef[0], 'media:news')

            nodes = await core.nodes('$types = (*,) inet:ipv4 <($types)- *')
            self.eq(nodes[0].ndef[0], 'media:news')

            # get the edge using stormtypes
            msgs = await core.stormlist('media:news for $edge in $node.edges() { $lib.print($edge) }')
            self.stormIsInPrint('refs', msgs)

            msgs = await core.stormlist('media:news for $edge in $node.edges(verb=refs) { $lib.print($edge) }')
            self.stormIsInPrint('refs', msgs)

            # remove the refs edge
            nodes = await core.nodes('media:news [ -(refs)> {inet:ipv4=1.2.3.4} ]')
            self.len(1, nodes)

            # no walking now...
            self.len(0, await core.nodes('media:news -(refs)> *'))

            # now lets add the edge using the n2 syntax
            nodes = await core.nodes('inet:ipv4 [ <(refs)+ { media:news } ]')
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('media:news -(refs)> *')
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('inet:ipv4 [ <(refs)- { media:news } ]')
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            # test refs+pivs in and out
            nodes = await core.nodes('media:news [ +(refs)> { inet:ipv4=1.2.3.4 } ]')
            nodes = await core.nodes('media:news [ :rss:feed=http://www.vertex.link/rss ]')
            nodes = await core.nodes('[ inet:dns:a=(woot.com, 1.2.3.4) ]')

            # we should now be able to edge walk *and* refs out
            nodes = await core.nodes('media:news --> *')
            self.len(2, nodes)
            self.eq(nodes[0].ndef[0], 'inet:url')
            self.eq(nodes[1].ndef[0], 'inet:ipv4')

            # we should now be able to edge walk *and* refs in
            nodes = await core.nodes('inet:ipv4=1.2.3.4 <-- *')
            self.eq(nodes[0].ndef[0], 'inet:dns:a')
            self.eq(nodes[1].ndef[0], 'media:news')

            msgs = await core.stormlist('for $verb in $lib.view.get().getEdgeVerbs() { $lib.print($verb) }')
            self.stormIsInPrint('refs', msgs)

            msgs = await core.stormlist('for $edge in $lib.view.get().getEdges() { $lib.print($edge) }')
            self.stormIsInPrint('refs', msgs)
            self.stormIsInPrint(ipv4.iden(), msgs)
            self.stormIsInPrint(news.iden(), msgs)

            msgs = await core.stormlist('for $edge in $lib.view.get().getEdges(verb=refs) { $lib.print($edge) }')
            self.stormIsInPrint('refs', msgs)
            self.stormIsInPrint(ipv4.iden(), msgs)
            self.stormIsInPrint(news.iden(), msgs)

            # delete an edge that doesn't exist to bounce off the layer
            await core.nodes('media:news [ -(refs)> { [ inet:ipv4=5.5.5.5 ] } ]')

            # add an edge that exists already to bounce off the layer
            await core.nodes('media:news [ +(refs)> { inet:ipv4=1.2.3.4 } ]')

            with self.raises(s_exc.StormRuntimeError) as cm:
                await core.nodes('media:news -(refs)> $(10)')

            self.eq(1, await core.callStorm('''
                $list = $lib.list()
                for $edge in $lib.view.get().getEdges() { $list.append($edge) }
                return($list.size())
            '''))

            # check that auto-deleting a node's edges works
            await core.nodes('media:news | delnode')
            self.eq(0, await core.callStorm('''
                $list = $lib.list()
                for $edge in $lib.view.get().getEdges() { $list.append($edge) }
                return($list.size())
            '''))

            # check that edge node edits dont bork up legacy splice generation
            nodeedits = [(ipv4.buid, 'inet:ipv4', (
                (s_layer.EDIT_EDGE_ADD, (), ()),
                (s_layer.EDIT_EDGE_DEL, (), ()),
            ))]

            self.eq((), await alist(core.view.layers[0].makeSplices(0, nodeedits, {})))

            # Run multiple nodes through edge creation/deletion ( test coverage for perm caching )
            await core.nodes('inet:ipv4 [ <(test)+ { meta:source:name=test }]')
            self.len(2, await core.nodes('meta:source:name=test -(test)> *'))

            await core.nodes('inet:ipv4 [ <(test)-{ meta:source:name=test }]')
            self.len(0, await core.nodes('meta:source:name=test -(test)> *'))

            # Sad path - edges must be a str/list of strs
            with self.raises(s_exc.StormRuntimeError) as cm:
                q = 'inet:ipv4 $edges=$(0) -($edges)> *'
                await core.nodes(q)
            self.eq(cm.exception.get('mesg'),
                    'walk operation expected a string or list.  got: 0.')

    async def test_cortex_callstorm(self):
        async with self.getTestCore() as core:
            self.eq('asdf', await core.callStorm('return (asdf)'))
            async with core.getLocalProxy() as proxy:
                self.eq('qwer', await proxy.callStorm('return (qwer)'))

    async def test_cortex_storm_dmon_log(self):

        async with self.getTestCore() as core:

            iden = await core.callStorm('''
                $que = $lib.queue.add(que)

                $ddef = $lib.dmon.add(${
                    $lib.print(hi)
                    $lib.warn(omg)
                    $que = $lib.queue.get(que)
                    $que.put(done)
                })

                $que.get()
                return($ddef.iden)
            ''')

            opts = {'vars': {'iden': iden}}
            logs = await core.callStorm('return($lib.dmon.log($iden))', opts=opts)
            self.eq(logs[0][1][0], 'print')
            self.eq(logs[0][1][1]['mesg'], 'hi')
            self.eq(logs[1][1][0], 'warn')
            self.eq(logs[1][1][1]['mesg'], 'omg')

            async with core.getLocalProxy() as prox:
                logs = await prox.getStormDmonLog(iden)
                self.eq(logs[0][1][0], 'print')
                self.eq(logs[0][1][1]['mesg'], 'hi')
                self.eq(logs[1][1][0], 'warn')
                self.eq(logs[1][1][1]['mesg'], 'omg')

                self.len(0, await prox.getStormDmonLog('newp'))

    async def test_storm_impersonate(self):

        async with self.getTestCore() as core:

            self.eq(core._userFromOpts(None), core.auth.rootuser)
            self.eq(core._userFromOpts({'user': None}), core.auth.rootuser)

            with self.raises(s_exc.NoSuchUser):
                opts = {'user': 'newp'}
                await core.nodes('[ inet:ipv4=1.2.3.4 ]', opts=opts)

            visi = await core.auth.addUser('visi')
            async with core.getLocalProxy(user='visi') as proxy:

                with self.raises(s_exc.AuthDeny):
                    opts = {'user': core.auth.rootuser.iden}
                    await proxy.eval('[ inet:ipv4=1.2.3.4 ]', opts=opts).list()

                await visi.addRule((True, ('impersonate',)))

                opts = {'user': core.auth.rootuser.iden}
                self.len(1, await proxy.eval('[ inet:ipv4=1.2.3.4 ]', opts=opts).list())

    async def test_nodes(self):

        async with self.getTestCore() as core:
            await core.fini()
            with self.raises(s_exc.IsFini):
                await core.nodes('[ inet:ipv4=1.2.3.4 ]')

    async def test_cortex_prop_deref(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ test:int=10 test:str=woot ]')
            text = '''
                for $prop in (test:int, test:str) {
                    *$prop
                }
            '''
            self.len(2, await core.nodes(text))

            text = '''
                syn:prop=test:int $prop=$node.value() *$prop=10 -syn:prop
            '''
            nodes = await core.nodes(text)
            self.eq(nodes[0].ndef, ('test:int', 10))

            guid = 'da299a896ff52ab0e605341ab910dad5'

            opts = {'vars': {'guid': guid}}
            self.len(2, await core.nodes('[ inet:dns:a=(vertex.link, 1.2.3.4) (inet:iface=$guid :ipv4=1.2.3.4) ]',
                                         opts=opts))

            text = '''
                syn:form syn:prop:ro=1 syn:prop:ro=0

                $prop = $node.value()

                *$prop?=1.2.3.4

                -syn:form
                -syn:prop
            '''
            nodes = await core.nodes(text)
            self.len(3, nodes)

            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))
            self.eq(nodes[1].ndef, ('inet:dns:a', ('vertex.link', 0x01020304)))
            self.eq(nodes[2].ndef, ('inet:iface', guid))

    async def test_cortex_tagprop(self):

        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:

                await core.addTagProp('user', ('str', {}), {})
                await core.addTagProp('score', ('int', {}), {'doc': 'hi there'})
                await core.addTagProp('at', ('geo:latlong', {}), {'doc':
                                                                  'Where the node was when the tag was applied.'})

                # Lifting by a tagprop works before any writes happened
                self.len(0, await core.nodes('#foo.bar:score'))
                self.len(0, await core.nodes('#foo.bar:score=20'))

                await core.nodes('[ test:int=10 +#foo.bar:score=20 ]')
                await core.nodes('[ test:str=lulz +#blah:user=visi ]')
                await core.nodes('[ test:str=wow +#hehe:at=(10, 20) ]')

                # test all the syntax cases...
                self.len(1, await core.nodes('#foo.bar'))
                self.len(1, await core.nodes('#foo.bar:score'))
                self.len(1, await core.nodes('#foo.bar:score=20'))
                self.len(1, await core.nodes('#foo.bar:score<=30'))
                self.len(1, await core.nodes('#foo.bar:score>=10'))
                self.len(1, await core.nodes('#foo.bar:score*range=(10, 30)'))

                self.len(1, await core.nodes('#blah:user^=vi'))
                self.len(1, await core.nodes('#blah:user~=si'))

                self.len(1, await core.nodes('test:int#foo.bar:score'))
                self.len(1, await core.nodes('test:int#foo.bar:score=20'))

                self.len(1, await core.nodes('test:int +#foo.bar'))
                self.len(1, await core.nodes('test:int +#foo.bar:score'))
                self.len(1, await core.nodes('test:int +#foo.bar:score=20'))
                self.len(1, await core.nodes('test:int +#foo.bar:score<=30'))
                self.len(1, await core.nodes('test:int +#foo.bar:score>=10'))
                self.len(1, await core.nodes('test:int +#foo.bar:score*range=(10, 30)'))

                self.len(0, await core.nodes('test:int -#foo.bar'))
                self.len(0, await core.nodes('test:int -#foo.bar:score'))
                self.len(0, await core.nodes('test:int -#foo.bar:score=20'))
                self.len(0, await core.nodes('test:int -#foo.bar:score<=30'))
                self.len(0, await core.nodes('test:int -#foo.bar:score>=10'))
                self.len(0, await core.nodes('test:int -#foo.bar:score*range=(10, 30)'))

                self.len(1, await core.nodes('test:str +#hehe:at*near=((10, 20), 1km)'))

                # test use as a value...
                q = 'test:int $valu=#foo.bar:score [ +#foo.bar:score = $($valu + 20) ] +#foo.bar:score=40'
                self.len(1, await core.nodes(q))

                with self.raises(s_exc.BadTypeValu):
                    self.len(1, await core.nodes('test:int=10 [ +#foo.bar:score=asdf ]'))

                self.len(1, await core.nodes('test:int=10 [ +#foo.bar:score?=asdf ] +#foo.bar:score=40'))

                # test the "set existing" cases for lift indexes
                self.len(1, await core.nodes('test:int=10 [ +#foo.bar:score=100 ]'))
                self.len(1, await core.nodes('#foo.bar'))
                self.len(1, await core.nodes('#foo.bar:score'))
                self.len(1, await core.nodes('#foo.bar:score=100'))
                self.len(1, await core.nodes('#foo.bar:score<=110'))
                self.len(1, await core.nodes('#foo.bar:score>=90'))
                self.len(1, await core.nodes('#foo.bar:score*range=(90, 110)'))

                # remove the tag
                await core.nodes('test:int=10 [ -#foo.bar ]')
                self.len(0, await core.nodes('#foo.bar:score'))
                self.len(0, await core.nodes('#foo.bar:score=100'))
                self.len(1, await core.nodes('test:int=10 -#foo.bar:score'))

                # remove just the tagprop
                await core.nodes('test:int=10 [ +#foo.bar:score=100 ]')
                await core.nodes('test:int=10 [ -#foo.bar:score ]')
                self.len(0, await core.nodes('#foo.bar:score'))
                self.len(0, await core.nodes('#foo.bar:score=100'))
                self.len(1, await core.nodes('test:int=10 -#foo.bar:score'))

                # remove a higher-level tag
                await core.nodes('test:int=10 [ +#foo.bar:score=100 ]')
                nodes = await core.nodes('test:int=10 [ -#foo ]')
                self.len(0, nodes[0].tagprops)
                self.len(0, await core.nodes('#foo'))
                self.len(0, await core.nodes('#foo.bar:score'))
                self.len(0, await core.nodes('#foo.bar:score=100'))
                self.len(1, await core.nodes('test:int=10 -#foo.bar:score'))

                # test for adding two tags with the same prop to the same node
                nodes = await core.nodes('[ test:int=10 +#foo:score=20 +#bar:score=20 ]')
                self.len(1, nodes)
                self.eq(20, nodes[0].getTagProp('foo', 'score'))
                self.eq(20, nodes[0].getTagProp('bar', 'score'))

                #    remove one of the tag props and everything still works
                nodes = await core.nodes('[ test:int=10 -#bar:score ]')
                self.len(1, nodes)
                self.eq(20, nodes[0].getTagProp('foo', 'score'))
                self.false(nodes[0].hasTagProp('bar', 'score'))

                await core.nodes('[ test:int=10 -#foo:score ]')

                #    same, except for _changing_ the tagprop instead of removing
                await core.nodes('test:int=10 [ +#foo:score=20 +#bar:score=20 ]')
                nodes = await core.nodes('test:int=10 [ +#bar:score=30 ]')
                self.len(1, nodes)
                self.eq(20, nodes[0].getTagProp('foo', 'score'))
                self.eq(30, nodes[0].getTagProp('bar', 'score'))

                await core.nodes('test:int=10 [ -#foo -#bar ]')

                with self.raises(s_exc.NoSuchCmpr):
                    await core.nodes('test:int=10 +#foo.bar:score*newp=66')

                modl = await core.getModelDict()
                self.nn(modl['tagprops'].get('score'))

                with self.raises(s_exc.DupPropName):
                    await core.addTagProp('score', ('int', {}), {})

                await core.delTagProp('score')

                with self.raises(s_exc.NoSuchProp):
                    await core.delTagProp('score')

                modl = await core.getModelDict()
                self.none(modl['tagprops'].get('score'))

                with self.raises(s_exc.NoSuchTagProp):
                    await core.nodes('#foo.bar:score')

                with self.raises(s_exc.NoSuchTagProp):
                    await core.nodes('test:int=10 [ +#foo.bar:score=66 ]')

                with self.raises(s_exc.NoSuchTagProp):
                    await core.nodes('test:int=10 +#foo.bar:score=66')

                with self.raises(s_exc.NoSuchType):
                    await core.addTagProp('derp', ('derp', {}), {})

            # Ensure that the tagprops persist
            async with self.getTestCore(dirn=dirn) as core:
                # Ensure we can still work with a tagprop, after restart, that was
                # defined with a type that came from a CoreModule model definition.
                self.len(1, await core.nodes('test:str +#hehe:at*near=((10, 20), 1km)'))

    async def test_cortex_prop_pivot(self):

        async with self.getTestReadWriteCores() as (core, wcore):

            async with await wcore.snap() as snap:
                await snap.addNode('inet:dns:a', ('woot.com', '1.2.3.4'))

            nodes = await core.nodes('inet:dns:a :ipv4 -> *')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            self.len(1, await core.nodes('inet:dns:a :ipv4 -> *'))

    async def test_cortex_of_the_future(self):
        '''
        test "future/ongoing" time stamp.
        '''
        async with self.getTestReadWriteCores() as (core, wcore):

            async with await wcore.snap() as snap:

                node = await snap.addNode('test:str', 'foo')
                await node.addTag('lol', valu=('2015', '?'))

                self.eq((1420070400000, 0x7fffffffffffffff), node.getTag('lol'))

            nodes = [n.pack() async for n in core.eval('test:str=foo +#lol@=2014')]
            self.len(0, nodes)

            nodes = [n.pack() async for n in core.eval('test:str=foo +#lol@=2016')]
            self.len(1, nodes)

    async def test_cortex_noderefs(self):

        async with self.getTestCore() as core:

            sorc = s_common.guid()

            async with await core.snap() as snap:

                node = await snap.addNode('inet:dns:a', ('woot.com', '1.2.3.4'))

                refs = dict(node.getNodeRefs())

                self.eq(refs.get('fqdn'), ('inet:fqdn', 'woot.com'))
                self.eq(refs.get('ipv4'), ('inet:ipv4', 0x01020304))

                await node.seen('now', source=sorc)

                # test un-populated properties
                node = await snap.addNode('ps:contact', '*')
                self.len(0, node.getNodeRefs())

                # test ndef field
                node = await snap.addNode('geo:nloc', (('inet:fqdn', 'woot.com'), '34.1,-118.3', 'now'))
                refs = dict(node.getNodeRefs())
                refs.get('ndef', ('inet:fqdn', 'woot.com'))

                # test un-populated ndef field
                node = await snap.addNode('test:str', 'woot')
                refs = dict(node.getNodeRefs())
                self.none(refs.get('bar'))

                node = await snap.addNode('test:arrayprop', '*')

                # test un-populated array prop
                refs = node.getNodeRefs()
                self.len(0, [r for r in refs if r[0] == 'ints'])

                # test array prop
                await node.set('ints', (1, 2, 3))
                refs = node.getNodeRefs()
                ints = sorted([r[1] for r in refs if r[0] == 'ints'])
                self.eq(ints, (('test:int', 1), ('test:int', 2), ('test:int', 3)))

            opts = {'vars': {'sorc': sorc}}
            nodes = [n.pack() async for n in core.eval('meta:seen:source=$sorc -> *', opts=opts)]

            self.len(2, nodes)
            self.true('inet:dns:a' in [n[0][0] for n in nodes])

            opts = {'vars': {'sorc': sorc}}
            nodes = [n.pack() async for n in core.eval('meta:seen:source=$sorc :node -> *', opts=opts)]

            self.len(1, nodes)
            self.true('inet:dns:a' in [n[0][0] for n in nodes])

    async def test_cortex_iter_props(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                props = {'asn': 10, '.seen': '2016'}
                node = await snap.addNode('inet:ipv4', 0x01020304, props=props)
                self.eq(node.get('asn'), 10)

                props = {'asn': 20, '.seen': '2015'}
                node = await snap.addNode('inet:ipv4', 0x05050505, props=props)
                self.eq(node.get('asn'), 20)

            # rows are (buid, valu) tuples
            layr = core.view.layers[0]
            rows = await alist(layr.iterPropRows('inet:ipv4', 'asn'))

            self.eq((10, 20), tuple(sorted([row[1] for row in rows])))

            # rows are (buid, valu) tuples
            rows = await alist(layr.iterUnivRows('.seen'))

            ivals = ((1420070400000, 1420070400001), (1451606400000, 1451606400001))
            self.eq(ivals, tuple(sorted([row[1] for row in rows])))

            # test iterFormRows as well
            rows = await alist(layr.iterFormRows('inet:ipv4'))
            self.eq((0x01020304, 0x05050505), tuple(sorted([row[1] for row in rows])))

    async def test_cortex_lift_regex(self):

        async with self.getTestCore() as core:

            core.model.addUnivProp('favcolor', ('str', {}), {})

            async with await core.snap() as snap:
                await snap.addNode('test:str', 'hezipha', props={'.favcolor': 'red'})
                await snap.addNode('test:comp', (20, 'lulzlulz'))

            self.len(0, await alist(core.eval('test:comp:haha~="^zerg"')))
            self.len(1, await alist(core.eval('test:comp:haha~="^lulz"')))

            self.len(1, await alist(core.eval('test:str~="zip"')))
            self.len(1, await alist(core.eval('test:str~="zip"')))
            self.len(1, await alist(core.eval('.favcolor~="^r"')))

    async def test_indxchop(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                valu = 'a' * 257
                await snap.addNode('test:str', valu)

                nodes = await snap.nodes('test:str^=aa')
                self.len(1, nodes)

    async def test_tags(self):

        async with self.getTestReadWriteCores() as (core, wcore):

            async with await wcore.snap() as snap:

                await snap.addNode('test:str', 'newp')

                node = await snap.addNode('test:str', 'one')
                await node.addTag('foo.bar', ('2016', '2017'))

                self.eq((1451606400000, 1483228800000), node.getTag('foo.bar', ('2016', '2017')))

                node1 = await snap.addNode('test:comp', (10, 'hehe'))
                await node1.addTag('foo.bar')

            async with await core.snap() as snap:

                self.nn(await snap.getNodeByNdef(('syn:tag', 'foo')))
                self.nn(await snap.getNodeByNdef(('syn:tag', 'foo.bar')))

            async with await core.snap() as snap:

                node = await snap.getNodeByNdef(('test:str', 'one'))

                self.true(node.hasTag('foo'))
                self.true(node.hasTag('foo.bar'))

                self.len(2, await snap.nodes('#foo.bar'))
                self.len(1, await snap.nodes('test:str#foo.bar'))

                with self.raises(s_exc.NoSuchProp):
                    await snap.nodes('test:newp#foo.bar')

            async with await wcore.snap() as snap:

                node = await snap.addNode('test:str', 'one')

                await node.delTag('foo')

                self.false(node.hasTag('foo'))
                self.false(node.hasTag('foo.bar'))

            async with await wcore.snap() as snap:

                node = await snap.addNode('test:str', 'one')
                self.false(node.hasTag('foo'))
                self.false(node.hasTag('foo.bar'))

    async def test_base_types1(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                node = await snap.addNode('test:type10', 'one')
                await node.set('intprop', 21)

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:type10', 'one'))
                self.nn(node)
                self.eq(node.get('intprop'), 21)

    async def test_cortex_pure_cmds(self):

        cdef0 = {

            'name': 'testcmd0',

            'cmdargs': (
                ('tagname', {}),
                ('--domore', {'default': False, 'action': 'store_true'}),
            ),

            'cmdconf': {
                'hehe': 'haha',
            },

            'storm': '$foo=$(10) if $cmdopts.domore { [ +#$cmdconf.hehe ] } [ +#$cmdopts.tagname ]',
        }

        cdef1 = {
            'name': 'testcmd1',
            'cmdargs': (
                ('name', {}),
            ),
            'storm': '''
                $varname = $cmdopts.name
                $realname = $path.vars.$varname
                if $realname {
                    [ inet:user=$realname ] | testcmd0 lulz
                }
            ''',
        }

        with self.getTestDir() as dirn:

            async with await s_cortex.Cortex.anit(dirn) as core:

                async with core.getLocalProxy() as prox:

                    await prox.setStormCmd(cdef0)
                    await prox.setStormCmd(cdef1)

                    nodes = await core.nodes('[ inet:asn=10 ] | testcmd0 zoinks')
                    self.true(nodes[0].tags.get('zoinks'))

                    nodes = await core.nodes('[ inet:asn=11 ] | testcmd0 zoinks --domore')

                    self.true(nodes[0].tags.get('haha'))
                    self.true(nodes[0].tags.get('zoinks'))

                    # test that cmdopts/cmdconf/locals dont leak
                    with self.raises(s_exc.NoSuchVar):
                        q = '[ inet:asn=11 ] | testcmd0 zoinks --domore | if ($cmdopts) {[ +#hascmdopts ]}'
                        nodes = await core.nodes(q)

                    with self.raises(s_exc.NoSuchVar):
                        q = '[ inet:asn=11 ] | testcmd0 zoinks --domore | if ($cmdconf) {[ +#hascmdconf ]}'
                        nodes = await core.nodes(q)

                    with self.raises(s_exc.NoSuchVar):
                        q = '[ inet:asn=11 ] | testcmd0 zoinks --domore | if ($foo) {[ +#hasfoo ]}'
                        nodes = await core.nodes(q)

                    # test nested storm commands
                    nodes = await core.nodes('[ inet:email=visi@vertex.link ] $username = :user | testcmd1 username')
                    self.len(2, nodes)
                    self.eq(nodes[0].ndef, ('inet:user', 'visi'))
                    self.nn(nodes[0].tags.get('lulz'))

            # make sure it's still loaded...
            async with await s_cortex.Cortex.anit(dirn) as core:

                async with core.getLocalProxy() as prox:

                    await core.nodes('[ inet:asn=30 ] | testcmd0 zoinks')

                    await prox.delStormCmd('testcmd0')

                    with self.raises(s_exc.NoSuchCmd):
                        await prox.delStormCmd('newpcmd')

                    with self.raises(s_exc.NoSuchName):
                        await core.nodes('[ inet:asn=31 ] | testcmd0 zoinks')

    async def test_base_types2(self):

        async with self.getTestReadWriteCores() as (core, wcore):

            # Make sure new nodes get different creation times than nodes created in the test CoreModule
            await asyncio.sleep(0.001)

            # Test some default values
            async with await wcore.snap() as snap:

                node = await snap.addNode('test:type10', 'one')
                self.nn(node.get('.created'))
                created = node.reprs().get('.created')

            # open a new snap, committing the previous snap and do some lifts by univ prop
            async with await core.snap() as snap:

                nodes = await snap.nodes('.created')
                self.len(1 + 1, nodes)

                tick = node.get('.created')
                nodes = await snap.nodes('.created=$tick', opts={'vars': {'tick': tick}})
                self.len(1, nodes)

                nodes = await snap.nodes('.created>=2010')
                self.len(1 + 1, nodes)

                nodes = await snap.nodes('.created*range=("2010", "3001")')
                self.len(1 + 1, nodes)

                nodes = await snap.nodes('.created*range=(2010,?)')
                self.len(1 + 1, nodes)

                await self.agenlen(2, core.eval('.created'))
                await self.agenlen(1, core.eval(f'.created="{created}"'))
                await self.agenlen(2, core.eval('.created>2010'))
                await self.agenlen(0, core.eval('.created<2010'))
                # The year the monolith returns
                await self.agenlen(2, core.eval('.created*range=(2010, 3001)'))
                await self.agenlen(2, core.eval('.created*range=("2010", "?")'))

            # The .created time is ro
            with self.raises(s_exc.ReadOnlyProp):
                await core.nodes(f'.created="{created}" [.created=3001]')

            # Open another snap to test some more default value behavior
            async with await wcore.snap() as snap:

                # Grab an updated reference to the first node
                node = (await snap.nodes('test:type10=one'))[0]
                # add another node with default vals
                await snap.addNode('test:type10', 'two')

                # modify default vals on initial node
                await node.set('intprop', 21)
                await node.set('strprop', 'qwer')
                await node.set('locprop', 'us.va.reston')

                node = await snap.addNode('test:comp', (33, 'THIRTY THREE'))

                self.eq(node.get('hehe'), 33)
                self.eq(node.get('haha'), 'thirty three')

                await self.asyncraises(s_exc.ReadOnlyProp, node.set('hehe', 80))

                self.none(await snap.getNodeByNdef(('test:auto', 'autothis')))

                props = {
                    'bar': ('test:auto', 'autothis'),
                    'baz': ('test:type10:strprop', 'WOOT'),
                    'tick': '20160505',
                }
                node = await snap.addNode('test:str', 'woot', props=props)
                self.eq(node.get('bar'), ('test:auto', 'autothis'))
                self.eq(node.get('baz'), ('test:type10:strprop', 'woot'))
                self.eq(node.get('tick'), 1462406400000)

                # add some time range bumper nodes
                await snap.addNode('test:str', 'toolow', props={'tick': '2015'})
                await snap.addNode('test:str', 'toohigh', props={'tick': '2018'})

                self.nn(await snap.getNodeByNdef(('test:auto', 'autothis')))

                # test lifting by prop without value
                nodes = await snap.nodes('test:str:tick')
                self.len(3, nodes)

            async with await wcore.snap() as snap:

                node = await snap.addNode('test:type10', 'one')
                self.eq(node.get('intprop'), 21)

                self.nn(node.get('.created'))

                nodes = await snap.nodes('test:str^=too')
                self.len(2, nodes)

                # test loc prop prefix based lookup
                nodes = await snap.nodes('test:type10:locprop^=us.va')

                self.len(1, nodes)
                self.eq(nodes[0].ndef[1], 'one')

                nodes = await snap.nodes('test:comp=(33, "thirty three")')

                self.len(1, nodes)

                self.eq(nodes[0].get('hehe'), 33)
                self.eq(nodes[0].ndef[1], (33, 'thirty three'))

    async def test_eval(self):
        ''' Cortex.eval test '''

        async with self.getTestCore() as core:

            # test some edit syntax
            async for node in core.eval('[ test:comp=(10, haha) +#foo.bar -#foo.bar ]'):
                self.nn(node.getTag('foo'))
                self.none(node.getTag('foo.bar'))

            # Make sure the 'view' key in optional opts parameter works
            nodes = await alist(core.eval('test:comp', opts={'view': core.view.iden}))
            self.len(1, nodes)

            await self.asyncraises(s_exc.NoSuchView, alist(core.eval('test:comp', opts={'view': 'xxx'})))

            async for node in core.eval('[ test:str="foo bar" :tick=2018]'):
                self.eq(1514764800000, node.get('tick'))
                self.eq('foo bar', node.ndef[1])

            async for node in core.eval('test:str="foo bar" [ -:tick ]'):
                self.none(node.get('tick'))

            async for node in core.eval('[test:guid="*" :tick=2001]'):
                self.true(s_common.isguid(node.ndef[1]))
                self.nn(node.get('tick'))

            nodes = [n.pack() async for n in core.eval('test:str="foo bar" +test:str')]
            self.len(1, nodes)

            nodes = [n.pack() async for n in core.eval('test:str="foo bar" -test:str:tick')]
            self.len(1, nodes)

            qstr = 'test:str="foo bar" +test:str="foo bar" [ :tick=2015 ] +test:str:tick=2015'
            nodes = [n.pack() async for n in core.eval(qstr)]
            self.len(1, nodes)

            # Seed new nodes via nodedefs
            ndef = ('test:comp', (10, 'haha'))
            opts = {'ndefs': (ndef,)}
            # Seed nodes in the query with ndefs
            async for node in core.eval('[-#foo]', opts=opts):
                self.none(node.getTag('foo'))

            # Seed nodes in the query with idens
            opts = {'idens': (nodes[0][1].get('iden'),)}
            nodes = await alist(core.eval('', opts=opts))
            self.len(1, nodes)
            self.eq(nodes[0].pack()[0], ('test:str', 'foo bar'))

            # Seed nodes in the query invalid idens
            opts = {'idens': ('deadb33f',)}
            await self.agenraises(s_exc.NoSuchIden, core.eval('', opts=opts))

            # Test and/or/not
            await alist(core.eval('[test:comp=(1, test) +#meep.morp +#bleep.blorp +#cond]'))
            await alist(core.eval('[test:comp=(2, test) +#meep.morp +#bleep.zlorp +#cond]'))
            await alist(core.eval('[test:comp=(3, foob) +#meep.gorp +#bleep.zlorp +#cond]'))

            q = 'test:comp +(:hehe<2 and :haha=test)'
            self.len(1, await alist(core.eval(q)))

            q = 'test:comp +(:hehe<2 and :haha=foob)'
            self.len(0, await alist(core.eval(q)))

            q = 'test:comp +(:hehe<2 or :haha=test)'
            self.len(2, await alist(core.eval(q)))

            q = 'test:comp +(:hehe<2 or :haha=foob)'
            self.len(2, await alist(core.eval(q)))

            q = 'test:comp +(:hehe<2 or #meep.gorp)'
            self.len(2, await alist(core.eval(q)))
            # TODO Add not tests

            await self.agenraises(s_exc.NoSuchCmpr, core.eval('test:str*near=newp'))
            await self.agenraises(s_exc.NoSuchCmpr, core.eval('test:str +test:str@=2018'))
            await self.agenraises(s_exc.BadTypeValu, core.eval('test:str +#test*near=newp'))
            await self.agenraises(s_exc.NoSuchCmpr, core.eval('test:str +test:str:tick*near=newp'))
            await self.agenraises(s_exc.BadSyntax, core.eval('test:str -> # } limit 10'))
            await self.agenraises(s_exc.BadSyntax, core.eval('test:str -> # { limit 10'))
            await self.agenraises(s_exc.BadSyntax, core.eval(' | | '))
            await self.agenraises(s_exc.BadSyntax, core.eval('[-test:str]'))
            # Scrape is not a default behavior
            await self.agenraises(s_exc.BadSyntax, core.eval('pennywise@vertex.link'))

            await self.agenlen(2, core.eval(('[ test:str=foo test:str=bar ]')))

            opts = {'vars': {'foo': 'bar'}}

            async for node in core.eval('test:str=$foo', opts=opts):
                self.eq('bar', node.ndef[1])

            # Make sure a tag=valu comparison before the tag is accessed works
            self.len(0, await core.nodes('#newp=2020'))

    async def test_cortex_delnode(self):

        data = {}

        def onPropDel(node, oldv):
            data['prop:del'] = True
            self.eq(oldv, 100)

        def onNodeDel(node):
            data['node:del'] = True

        async with self.getTestCore() as core:

            form = core.model.forms.get('test:str')

            form.onDel(onNodeDel)
            form.props.get('tick').onDel(onPropDel)

            async with await core.snap() as snap:

                targ = await snap.addNode('test:pivtarg', 'foo')
                await snap.addNode('test:pivcomp', ('foo', 'bar'))

                await self.asyncraises(s_exc.CantDelNode, targ.delete())

                tstr = await snap.addNode('test:str', 'baz')

                await tstr.set('tick', 100)
                await tstr.addTag('hehe')

                nodes = await snap.nodes('[ test:str=baz :tick=$(100) +#hehe ]')
                self.len(1, nodes)
                self.eq(100, nodes[0].get('tick'))
                self.eq((None, None), nodes[0].getTag('hehe'))

                self.len(1, await core.nodes('#hehe'))
                self.len(1, await snap.nodes('#hehe'))
                self.len(1, await snap.nodes('test:str=baz'))
                self.len(1, await snap.nodes('test:str:tick=$(100)'))

                tagnode = await snap.getNodeByNdef(('syn:tag', 'hehe'))
                with self.raises(s_exc.CantDelNode):
                    await tagnode.delete()

                buid = tstr.buid

                await tstr.delete()

                self.true(data.get('prop:del'))
                self.true(data.get('node:del'))

                # confirm that the snap cache is clear
                self.none(await snap.getNodeByBuid(tstr.buid))
                self.none(await snap.getNodeByNdef(('test:str', 'baz')))

            async with await core.snap() as snap:
                self.len(0, await snap.nodes('test:str:tick'))
                self.eq(None, await snap.getNodeByBuid(buid))

    async def test_pivot_inout(self):

        async def getPackNodes(core, query):
            nodes = sorted([n.pack() async for n in core.eval(query)])
            return nodes

        async with self.getTestReadWriteCores() as (core, wcore):

            # seed a node for pivoting
            await alist(wcore.eval('[ test:pivcomp=(foo,bar) :tick=2018 ]'))
            await alist(wcore.eval('[ edge:refs=((ou:org, "*"), (test:pivcomp,(foo,bar))) ]'))

            self.len(1, await core.nodes('ou:org -> edge:refs:n1'))

            q = 'test:pivcomp=(foo,bar) -> test:pivtarg'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:pivtarg', 'foo'))

            # Regression test:  bug in implicit form pivot where absence of foreign key in source node was treated like
            # a match-any
            await alist(wcore.eval('[ test:int=42 ]'))
            q = 'test:pivcomp -> test:int'
            nodes = await getPackNodes(core, q)
            self.len(0, nodes)

            # Multiple props of source form have type of destination form:  pivot through all the matching props.
            await alist(wcore.eval('[ test:pivcomp=(xxx,yyy) :width=42 ]'))
            q = 'test:pivcomp -> test:int'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)

            q = 'test:pivcomp=(foo,bar) :targ -> test:pivtarg'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:pivtarg', 'foo'))

            q = 'test:str=bar -> test:pivcomp:lulz'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))

            q = 'test:str=bar -+> test:pivcomp:lulz'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('test:str', 'bar'))

            q = 'test:pivcomp=(foo,bar) -+> test:pivtarg'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('test:pivtarg', 'foo'))

            q = 'test:pivcomp=(foo,bar) -> *'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('test:pivtarg', 'foo'))
            self.eq(nodes[1][0], ('test:str', 'bar'))

            q = 'test:pivcomp=(foo,bar) -+> *'
            nodes = await getPackNodes(core, q)
            self.len(3, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('test:pivtarg', 'foo'))
            self.eq(nodes[2][0], ('test:str', 'bar'))

            q = 'test:pivcomp=(foo,bar) :lulz -> test:str'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:str', 'bar'))

            q = 'test:pivcomp=(foo,bar) :lulz -+> test:str'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('test:str', 'bar'))

            q = 'test:str=bar <- *'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))

            q = 'test:str=bar <+- *'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('test:str', 'bar'))

            # A simple edge for testing pivotinfrom with a edge to n2
            await alist(wcore.eval('[ edge:has=((test:str, foobar), (test:str, foo)) ]'))

            q = 'test:str=foobar -+> edge:has'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('edge:has', (('test:str', 'foobar'), ('test:str', 'foo'))))
            self.eq(nodes[1][0], ('test:str', 'foobar'))

            # traverse from node to edge:n1
            q = 'test:str=foo <- edge:has'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('edge:has', (('test:str', 'foobar'), ('test:str', 'foo'))))

            # traverse from node to edge:n1 with a join
            q = 'test:str=foo <+- edge:has'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('edge:has', (('test:str', 'foobar'), ('test:str', 'foo'))))
            self.eq(nodes[1][0], ('test:str', 'foo'))

            # Traverse from a edge to :n2
            # (this is technically a circular query)
            q = 'test:str=foobar -> edge:has <- test:str'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:str', 'foobar'))

            # Traverse from a edge to :n2 with a join
            # (this is technically a circular query)
            q = 'test:str=foobar -> edge:has <+- test:str'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('edge:has', (('test:str', 'foobar'), ('test:str', 'foo'))))
            self.eq(nodes[1][0], ('test:str', 'foobar'))

            # Add tag
            q = 'test:str=bar test:pivcomp=(foo,bar) [+#test.bar]'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            # Lift, filter, pivot in
            q = '#test.bar +test:str <- *'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))

            # Pivot tests with optimized lifts
            q = '#test.bar +test:str <+- *'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)

            q = '#test.bar +test:pivcomp -> *'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)

            q = '#test.bar +test:pivcomp -+> *'
            nodes = await getPackNodes(core, q)
            self.len(3, nodes)

            # tag conditional filters followed by * pivot operators
            # These are all going to yield zero nodes but should
            # parse cleanly.
            q = '#test.bar -#test <- *'
            nodes = await getPackNodes(core, q)
            self.len(0, nodes)

            q = '#test.bar -#test <+- *'
            nodes = await getPackNodes(core, q)
            self.len(0, nodes)

            q = '#test.bar -#test -> *'
            nodes = await getPackNodes(core, q)
            self.len(0, nodes)

            q = '#test.bar -#test -+> *'
            nodes = await getPackNodes(core, q)
            self.len(0, nodes)

            # Do a PropPivotOut with a :prop value which is not a form.
            tgud = s_common.guid()
            tstr = 'boom'
            async with await wcore.snap() as snap:
                await snap.addNode('test:str', tstr)
                await snap.addNode('test:guid', tgud)
                await snap.addNode('test:edge', (('test:guid', tgud), ('test:str', tstr)))

            q = f'test:str={tstr} <- test:edge :n1:form -> *'
            mesgs = await core.stormlist(q)
            self.stormIsInWarn('The source property "n1:form" type "str" is not a form. Cannot pivot.',
                               mesgs)
            self.len(0, [m for m in mesgs if m[0] == 'node'])

            # Setup a propvalu pivot where the secondary prop may fail to norm
            # to the destination prop for some of the inbound nodes.
            await alist(wcore.eval('[ test:comp=(127,newp) ] [test:comp=(127,127)]'))
            mesgs = await core.stormlist('test:comp :haha -> test:int')

            warns = [msg for msg in mesgs if msg[0] == 'warn']
            self.len(1, warns)
            emesg = "BadTypeValu ['newp'] during pivot: invalid literal for int() with base 0: 'newp'"
            self.eq(warns[0][1], {'name': 'test:int', 'valu': 'newp',
                                  'mesg': emesg})
            nodes = [msg for msg in mesgs if msg[0] == 'node']
            self.len(1, nodes)
            self.eq(nodes[0][1][0], ('test:int', 127))

            # Setup a form pivot where the primary prop may fail to norm
            # to the destination prop for some of the inbound nodes.
            async with await core.snap() as snap:
                await snap.addNode('test:int', 10)
                await snap.addNode('test:int', 25)
                await snap.addNode('test:type10', 'test', {'intprop': 25})
            mesgs = await core.stormlist('test:int*in=(10, 25) -> test:type10:intprop')

            warns = [msg for msg in mesgs if msg[0] == 'warn']
            self.len(1, warns)
            emesg = "BadTypeValu [10] during pivot: value is below min=20"
            self.eq(warns[0][1], {'name': 'int', 'valu': 10,
                                  'mesg': emesg})
            nodes = [msg for msg in mesgs if msg[0] == 'node']
            self.len(1, nodes)
            self.eq(nodes[0][1][0], ('test:type10', 'test'))

            # Bad pivots go here
            for q in ['test:pivcomp :lulz <- *',
                      'test:pivcomp :lulz <+- *',
                      'test:pivcomp :lulz <- test:str',
                      'test:pivcomp :lulz <+- test:str',
                      ]:
                await self.agenraises(s_exc.BadSyntax, core.eval(q))

    async def test_cortex_storm_set_univ(self):

        async with self.getTestReadWriteCores() as (core, wcore):

            await alist(wcore.eval('[ test:str=woot .seen=(2014,2015) ]'))

            async with await core.snap() as snap:

                node = await snap.getNodeByNdef(('test:str', 'woot'))
                self.eq(node.get('.seen'), (1388534400000, 1420070400000))

    async def test_cortex_storm_set_tag(self):

        async with self.getTestReadWriteCores() as (core, wcore):

            tick0 = core.model.type('time').norm('2014')[0]
            tick1 = core.model.type('time').norm('2015')[0]
            tick2 = core.model.type('time').norm('2016')[0]

            await self.agenlen(1, wcore.eval('[ test:str=hehe +#foo=(2014,2016) ]'))
            await self.agenlen(1, wcore.eval('[ test:str=haha +#bar=2015 ]'))

            async with await core.snap() as snap:

                node = await snap.getNodeByNdef(('test:str', 'hehe'))
                self.eq(node.getTag('foo'), (tick0, tick2))

                node = await snap.getNodeByNdef(('test:str', 'haha'))
                self.eq(node.getTag('bar'), (tick1, tick1 + 1))

            await self.agenlen(1, wcore.eval('[ test:str=haha +#bar=2016 ]'))

            async with await core.snap() as snap:

                node = await snap.getNodeByNdef(('test:str', 'haha'))
                self.eq(node.getTag('bar'), (tick1, tick2 + 1))

    async def test_cortex_storm_filt_ival(self):

        async with self.getTestReadWriteCores() as (core, wcore):

            await self.agenlen(1, wcore.eval('[ test:str=woot +#foo=(2015,2018) +#bar .seen=(2014,2016) ]'))

            await self.agenlen(1, core.eval('test:str=woot +.seen@=2015'))
            await self.agenlen(0, core.eval('test:str=woot +.seen@=2012'))
            await self.agenlen(1, core.eval('test:str=woot +.seen@=(2012,2015)'))
            await self.agenlen(0, core.eval('test:str=woot +.seen@=(2012,2013)'))

            await self.agenlen(1, core.eval('test:str=woot +.seen@=#foo'))
            await self.agenlen(0, core.eval('test:str=woot +.seen@=#bar'))
            await self.agenlen(0, core.eval('test:str=woot +.seen@=#baz'))

            await self.agenlen(1, core.eval('test:str=woot $foo=#foo +.seen@=$foo'))

            await self.agenlen(1, core.eval('test:str +#foo@=2016'))
            await self.agenlen(1, core.eval('test:str +#foo@=(2015, 2018)'))
            await self.agenlen(1, core.eval('test:str +#foo@=(2014, 2019)'))
            await self.agenlen(0, core.eval('test:str +#foo@=(2014, 20141231)'))

            await self.agenlen(1, wcore.eval('[ inet:dns:a=(woot.com,1.2.3.4) .seen=(2015,2016) ]'))
            await self.agenlen(1, wcore.eval('[ inet:fqdn=woot.com +#bad=(2015,2016) ]'))

            await self.agenlen(1, core.eval('inet:fqdn +#bad $fqdnbad=#bad -> inet:dns:a:fqdn +.seen@=$fqdnbad'))

    async def test_cortex_storm_tagform(self):

        async with self.getTestReadWriteCores() as (core, wcore):

            await self.agenlen(1, wcore.eval('[ test:str=hehe ]'))
            await self.agenlen(1, wcore.eval('[ test:str=haha +#foo ]'))
            await self.agenlen(1, wcore.eval('[ test:str=woot +#foo=(2015,2018) ]'))

            await self.agenlen(2, core.eval('#foo'))
            await self.agenlen(3, core.eval('test:str'))

            await self.agenlen(2, core.eval('test:str#foo'))
            await self.agenlen(1, core.eval('test:str#foo@=2016'))
            await self.agenlen(0, core.eval('test:str#foo@=2020'))

            # test the overlap variants
            await self.agenlen(0, core.eval('test:str#foo@=(2012,2013)'))
            await self.agenlen(0, core.eval('test:str#foo@=(2020,2022)'))
            await self.agenlen(1, core.eval('test:str#foo@=(2012,2017)'))
            await self.agenlen(1, core.eval('test:str#foo@=(2017,2022)'))
            await self.agenlen(1, core.eval('test:str#foo@=(2012,2022)'))

    async def test_cortex_int_indx(self):

        async with self.getTestReadWriteCores() as (core, wcore):

            await alist(wcore.eval('[test:int=20]'))

            await self.agenlen(0, core.eval('test:int>=30'))
            await self.agenlen(1, core.eval('test:int>=20'))
            await self.agenlen(1, core.eval('test:int>=10'))

            await self.agenlen(0, core.eval('test:int>30'))
            await self.agenlen(0, core.eval('test:int>20'))
            await self.agenlen(1, core.eval('test:int>10'))

            await self.agenlen(0, core.eval('test:int<=10'))
            await self.agenlen(1, core.eval('test:int<=20'))
            await self.agenlen(1, core.eval('test:int<=30'))

            await self.agenlen(0, core.eval('test:int<10'))
            await self.agenlen(0, core.eval('test:int<20'))
            await self.agenlen(1, core.eval('test:int<30'))

            await self.agenlen(0, core.eval('test:int +test:int>=30'))
            await self.agenlen(1, core.eval('test:int +test:int>=20'))
            await self.agenlen(1, core.eval('test:int +test:int>=10'))

            await self.agenlen(0, core.eval('test:int +test:int>30'))
            await self.agenlen(0, core.eval('test:int +test:int>20'))
            await self.agenlen(1, core.eval('test:int +test:int>10'))

            await self.agenlen(0, core.eval('test:int +test:int<=10'))
            await self.agenlen(1, core.eval('test:int +test:int<=20'))
            await self.agenlen(1, core.eval('test:int +test:int<=30'))

            await self.agenlen(0, core.eval('test:int +test:int<10'))
            await self.agenlen(0, core.eval('test:int +test:int<20'))
            await self.agenlen(1, core.eval('test:int +test:int<30'))

            # time indx is derived from the same lift helpers
            await alist(wcore.eval('[test:str=foo :tick=201808021201]'))

            await self.agenlen(0, core.eval('test:str:tick>=201808021202'))
            await self.agenlen(1, core.eval('test:str:tick>=201808021201'))
            await self.agenlen(1, core.eval('test:str:tick>=201808021200'))

            await self.agenlen(0, core.eval('test:str:tick>201808021202'))
            await self.agenlen(0, core.eval('test:str:tick>201808021201'))
            await self.agenlen(1, core.eval('test:str:tick>201808021200'))

            await self.agenlen(1, core.eval('test:str:tick<=201808021202'))
            await self.agenlen(1, core.eval('test:str:tick<=201808021201'))
            await self.agenlen(0, core.eval('test:str:tick<=201808021200'))

            await self.agenlen(1, core.eval('test:str:tick<201808021202'))
            await self.agenlen(0, core.eval('test:str:tick<201808021201'))
            await self.agenlen(0, core.eval('test:str:tick<201808021200'))

            await self.agenlen(0, core.eval('test:str +test:str:tick>=201808021202'))
            await self.agenlen(1, core.eval('test:str +test:str:tick>=201808021201'))
            await self.agenlen(1, core.eval('test:str +test:str:tick>=201808021200'))

            await self.agenlen(0, core.eval('test:str +test:str:tick>201808021202'))
            await self.agenlen(0, core.eval('test:str +test:str:tick>201808021201'))
            await self.agenlen(1, core.eval('test:str +test:str:tick>201808021200'))

            await self.agenlen(1, core.eval('test:str +test:str:tick<=201808021202'))
            await self.agenlen(1, core.eval('test:str +test:str:tick<=201808021201'))
            await self.agenlen(0, core.eval('test:str +test:str:tick<=201808021200'))

            await self.agenlen(1, core.eval('test:str +test:str:tick<201808021202'))
            await self.agenlen(0, core.eval('test:str +test:str:tick<201808021201'))
            await self.agenlen(0, core.eval('test:str +test:str:tick<201808021200'))

            await alist(wcore.eval('[test:int=99999]'))
            await self.agenlen(1, core.eval('test:int<=20'))
            await self.agenlen(2, core.eval('test:int>=20'))
            await self.agenlen(1, core.eval('test:int>20'))
            await self.agenlen(0, core.eval('test:int<20'))

    async def test_cortex_univ(self):

        async with self.getTestCore() as core:

            # Ensure that the test model loads a univ property
            prop = core.model.prop('.test:univ')
            self.true(prop.isuniv)

            # Add a univprop directly via API for testing
            core.model.addUnivProp('hehe', ('int', {}), {})

            await self.agenlen(1, core.eval('[ test:str=woot .hehe=20 ]'))
            await self.agenlen(1, core.eval('.hehe'))
            await self.agenlen(1, core.eval('test:str.hehe=20'))
            await self.agenlen(0, core.eval('test:str.hehe=19'))
            await self.agenlen(1, core.eval('.hehe [ -.hehe ]'))
            await self.agenlen(0, core.eval('.hehe'))

        # ensure that we can delete univ props in a authenticated setting
        async with self.getTestCoreAndProxy() as (realcore, core):

            realcore.model.addUnivProp('hehe', ('int', {}), {})
            await self.agenlen(1, realcore.eval('[ test:str=woot .hehe=20 ]'))
            await self.agenlen(1, realcore.eval('[ test:str=pennywise .hehe=8086 ]'))

            podes = await alist(core.eval('test:str=woot [-.hehe]'))
            self.none(s_node.prop(podes[0], '.hehe'))
            podes = await alist(core.eval('test:str=pennywise [-.hehe]'))
            self.none(s_node.prop(podes[0], '.hehe'))

    async def test_storm_cond_has(self):
        async with self.getTestCore() as core:

            await core.nodes('[ inet:ipv4=1.2.3.4 :asn=20 ]')
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 +:asn'))

            with self.raises(s_exc.BadSyntax):
                await core.nodes('[ inet:ipv4=1.2.3.4 +:foo ]')

    async def test_storm_cond_not(self):

        async with self.getTestCore() as core:

            await self.agenlen(1, core.eval('[ test:str=foo +#bar ]'))
            await self.agenlen(1, core.eval('[ test:str=foo +#bar ] +(not .seen)'))
            await self.agenlen(1, core.eval('[ test:str=foo +#bar ] +(#baz or not .seen)'))

    async def test_storm_totags(self):

        async with self.getTestCore() as core:

            nodes = await alist(core.eval('[ test:str=visi +#foo.bar ] -> #'))

            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'foo.bar')

            await self.agenlen(2, core.eval('test:str=visi -> #*'))
            await self.agenlen(1, core.eval('test:str=visi -> #foo.bar'))
            await self.agenlen(1, core.eval('test:str=visi -> #foo.*'))
            await self.agenlen(0, core.eval('test:str=visi -> #baz.*'))

    async def test_storm_fromtags(self):

        async with self.getTestCore() as core:

            await alist(core.eval('[ test:str=visi test:int=20 +#foo.bar ]'))

            nodes = await alist(core.eval('syn:tag=foo.bar -> test:str'))
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'visi')

            await self.agenlen(2, core.eval('syn:tag=foo.bar -> *'))

            # Attempt a formpivot from a syn:tag node to a secondary property
            # which is not valid
            with self.getAsyncLoggerStream('synapse.lib.ast',
                                           'Unknown time format') as stream:
                self.len(0, await core.nodes('syn:tag=foo.bar -> test:str:tick'))
                self.true(await stream.wait(4))

    async def test_storm_tagtags(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=visi +#foo.bar ] -> # [ +#baz.faz ]')

            nodes = await core.nodes('##baz.faz')

            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'visi')

            # make an icky loop of tags...
            await core.nodes('syn:tag=baz.faz [ +#foo.bar ]')

            # should still be ok...
            nodes = await core.nodes('##baz.faz')

            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'visi')

    async def test_storm_cancel(self):

        async with self.getTestCore() as core:

            evnt = asyncio.Event()

            self.len(0, core.boss.ps())

            async def todo():
                async for node in core.eval('[ test:str=foo test:str=bar ] | sleep 10'):
                    evnt.set()

            task = core.schedCoro(todo())

            await evnt.wait()

            synts = core.boss.ps()

            self.len(1, synts)

            await synts[0].kill()

            self.len(0, core.boss.ps())

            await self.asyncraises(asyncio.CancelledError, task)

    async def test_cortex_formcounts(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                nodes = await core.nodes('[ test:str=foo test:str=bar test:int=42 ]')
                self.len(3, nodes)

                self.eq(1, (await core.getFormCounts())['test:int'])
                self.eq(2, (await core.getFormCounts())['test:str'])

            # test that counts persist...
            async with self.getTestCore(dirn=dirn) as core:

                self.eq(1, (await core.getFormCounts())['test:int'])
                self.eq(2, (await core.getFormCounts())['test:str'])

                node = await core.getNodeByNdef(('test:str', 'foo'))
                await node.delete()

                self.eq(1, (await core.getFormCounts())['test:str'])

    async def test_cortex_greedy(self):
        ''' Issue a large snap request, and make sure we can still do stuff in a reasonable amount of time'''

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                event = asyncio.Event()

                async def add_stuff():
                    event.set()
                    ips = ((('inet:ipv4', x), {}) for x in range(20000))

                    await alist(snap.addNodes(ips))

                snap.schedCoro(add_stuff())

                # Wait for him to get started
                before = time.time()
                await event.wait()

                await snap.addNode('inet:dns:a', ('woot.com', 0x01020304))
                delta = time.time() - before

                # Note: before latency improvement, delta was > 4 seconds
                self.lt(delta, 0.5)

            # Make sure the task in flight can be killed in a reasonable time
            delta = time.time() - before
            self.lt(delta, 1.0)

    async def test_storm_pivprop(self):

        async with self.getTestCore() as core:

            self.len(1, await core.nodes('[ inet:asn=200 :name=visi ]'))
            self.len(1, await core.nodes('[ inet:ipv4=1.2.3.4 :asn=200 ]'))
            self.len(1, await core.nodes('[ inet:ipv4=5.6.7.8 :asn=8080 ]'))

            async with await core.snap() as snap:
                self.nn(await snap.getNodeByNdef(('inet:asn', 200)))

            self.len(1, await core.nodes('inet:asn=200 +:name=visi'))

            self.len(1, await core.nodes('inet:asn=200 +:name=visi'))
            nodes = await core.nodes('inet:ipv4 +:asn::name=visi')

            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

class CortexBasicTest(s_t_utils.SynTest):
    '''
    The tests that are unlikely to break with different types of layers installed
    '''
    async def test_cortex_bad_config(self):
        '''
        Try to load the TestModule twice
        '''
        conf = {'modules': [('synapse.tests.utils.TestModule', {'key': 'valu'})]}
        with self.raises(s_exc.ModAlreadyLoaded):
            async with self.getTestCore(conf=conf):
                pass

        async with self.getTestCore() as core:
            with self.raises(s_exc.ModAlreadyLoaded):
                await core.loadCoreModule('synapse.tests.utils.TestModule')

    async def test_cortex_coreinfo(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            coreinfo = await prox.getCoreInfo()

            for field in ('version', 'modeldef', 'stormcmds'):
                self.isin(field, coreinfo)

            layers = list(core.listLayers())
            self.len(1, layers)
            self.eq(layers[0].pack()['name'], 'default')

            views = list(core.listViews())
            self.len(1, views)
            self.eq(views[0].pack()['name'], 'default')

    async def test_cortex_model_dict(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            model = await prox.getModelDict()

            tnfo = model['types'].get('inet:ipv4')

            self.nn(tnfo)
            self.eq(tnfo['info']['doc'], 'An IPv4 address.')

            fnfo = model['forms'].get('inet:ipv4')
            self.nn(fnfo)

            pnfo = fnfo['props'].get('asn')

            self.nn(pnfo)
            self.eq(pnfo['type'][0], 'inet:asn')

            modelt = model['types']

            self.eq('text', model['forms']['inet:whois:rec']['props']['text']['disp']['hint'])

            fname = 'inet:dns:rev'
            cmodel = core.model.form(fname)
            modelf = model['forms'][fname]
            self.eq(cmodel.type.stortype, modelt[fname].get('stortype'))

            self.eq(cmodel.prop('ipv4').type.stortype,
                    modelt.get(modelf['props']['ipv4']['type'][0], {}).get('stortype'))
            self.eq(cmodel.prop('.created').type.stortype,
                    modelt.get(modelf['props']['.created']['type'][0], {}).get('stortype'))

            fname = 'file:bytes'
            cmodel = core.model.form(fname)
            modelf = model['forms'][fname]
            self.eq(cmodel.type.stortype, modelt[fname].get('stortype'))

            self.eq(cmodel.prop('size').type.stortype,
                    modelt.get(modelf['props']['size']['type'][0], {}).get('stortype'))
            self.eq(cmodel.prop('sha256').type.stortype,
                    modelt.get(modelf['props']['sha256']['type'][0], {}).get('stortype'))

            fname = 'test:int'
            cmodel = core.model.form(fname)
            modelf = model['forms'][fname]
            self.eq(cmodel.type.stortype, modelt[fname].get('stortype'))

            self.eq(cmodel.prop('.test:univ').type.stortype,
                    modelt.get(modelf['props']['.test:univ']['type'][0], {}).get('stortype'))

    async def test_storm_graph(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            await prox.addNode('inet:dns:a', ('woot.com', '1.2.3.4'))

            opts = {'graph': True}
            nodes = [n async for n in prox.eval('inet:dns:a', opts=opts)]

            self.len(4, nodes)

            for node in nodes:
                if node[0][0] == 'inet:dns:a':
                    edges = node[1]['path']['edges']
                    idens = list(sorted(e[0] for e in edges))
                    self.eq(idens, ('20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f',
                                    'd7fb3ae625e295c9279c034f5d91a7ad9132c79a9c2b16eecffc8d1609d75849'))

            await prox.addNode('edge:refs', (('test:int', 10), ('test:int', 20)))

            nodes = [n async for n in prox.eval('edge:refs', opts=opts)]

            self.len(3, nodes)
            self.eq(nodes[0][0][0], 'edge:refs')
            edges = nodes[0][1]['path']['edges']
            idens = list(sorted(e[0] for e in edges))
            self.eq(idens, (
                '2ff879e667e9cca52f1c78485f7864c4c5a242c67d4b90105210dde8edf3c068',
                '979b56497b5fd75813676738172c2f435aee3e4bdcf43930843eba5b34bb06fc',
            ))

    async def test_onadd(self):
        arg_hit = {}

        async def testcb(node):
            arg_hit['hit'] = node

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                core.model.form('inet:ipv4').onAdd(testcb)

                node = await snap.addNode('inet:ipv4', '1.2.3.4')
                self.eq(node, arg_hit.get('hit'))

                arg_hit['hit'] = None
                core.model.form('inet:ipv4').offAdd(testcb)
                node = await snap.addNode('inet:ipv4', '1.2.3.5')
                self.none(arg_hit.get('hit'))

    async def test_adddata(self):

        data = ('foo', 'bar', 'baz')

        async with self.getTestCore() as core:

            await core.addFeedData('com.test.record', data)

            vals = [node.ndef[1] async for node in core.eval('test:str')]

            vals.sort()

            self.eq(vals, ('bar', 'baz', 'foo'))

    async def test_cell(self):

        data = ('foo', 'bar', 'baz')

        async with self.getTestCoreAndProxy() as (core, proxy):

            corever = core.cellinfo.get('cortex:version')
            cellver = core.cellinfo.get('synapse:version')
            self.eq(corever, s_version.version)
            self.eq(corever, cellver)

            nodes = ((('inet:user', 'visi'), {}),)

            nodes = await alist(proxy.addNodes(nodes))
            self.len(1, nodes)

            node = await proxy.addNode('test:str', 'foo')

            pack = await proxy.addNodeTag(node[1].get('iden'), '#foo.bar')
            self.eq(pack[1]['tags'].get('foo.bar'), (None, None))

            pack = await proxy.setNodeProp(node[1].get('iden'), 'tick', '2015')
            self.eq(pack[1]['props'].get('tick'), 1420070400000)

            self.len(1, await alist(proxy.eval('test:str#foo.bar')))
            self.len(1, await alist(proxy.eval('test:str:tick=2015')))

            pack = await proxy.delNodeProp(node[1].get('iden'), 'tick')
            self.none(pack[1]['props'].get('tick'))

            iden = s_common.ehex(s_common.buid('newp'))
            await self.asyncraises(s_exc.NoSuchIden, proxy.delNodeProp(iden, 'tick'))

            await proxy.delNodeTag(node[1].get('iden'), '#foo.bar')
            self.len(0, await alist(proxy.eval('test:str#foo.bar')))

            opts = {'ndefs': [('inet:user', 'visi')]}

            nodes = await alist(proxy.eval('', opts=opts))

            self.len(1, nodes)
            self.eq('visi', nodes[0][0][1])

            await proxy.addFeedData('com.test.record', data)

            # test the remote storm result counting API
            self.eq(0, await proxy.count('test:pivtarg'))
            self.eq(1, await proxy.count('inet:user'))
            self.eq(1, await core.count('inet:user'))

            # Test the getFeedFuncs command to enumerate feed functions.
            ret = await proxy.getFeedFuncs()
            resp = {rec.get('name'): rec for rec in ret}
            self.isin('com.test.record', resp)
            self.isin('syn.splice', resp)
            self.isin('syn.nodes', resp)
            self.isin('syn.nodeedits', resp)
            rec = resp.get('syn.nodes')
            self.eq(rec.get('name'), 'syn.nodes')
            self.eq(rec.get('desc'), 'Add nodes to the Cortex via the packed node format.')
            self.eq(rec.get('fulldoc'), 'Add nodes to the Cortex via the packed node format.')

            # Test the stormpkg apis
            otherpkg = {
                'name': 'foosball',
                'version': (0, 0, 1),
            }
            self.none(await proxy.addStormPkg(otherpkg))
            pkgs = await proxy.getStormPkgs()
            self.len(1, pkgs)
            self.eq(pkgs, [otherpkg])
            pkg = await proxy.getStormPkg('foosball')
            self.eq(pkg, otherpkg)
            self.none(await proxy.delStormPkg('foosball'))
            pkgs = await proxy.getStormPkgs()
            self.len(0, pkgs)
            await self.asyncraises(s_exc.NoSuchPkg, proxy.delStormPkg('foosball'))

            # test reqValidStorm
            self.true(await proxy.reqValidStorm('test:str=test'))
            self.true(await proxy.reqValidStorm('1.2.3.4 | spin', {'mode': 'lookup'}))
            self.true(await proxy.reqValidStorm('1.2.3.4 | spin', {'mode': 'autoadd'}))
            with self.raises(s_exc.BadSyntax):
                await proxy.reqValidStorm('1.2.3.4 ')
            with self.raises(s_exc.BadSyntax):
                await proxy.reqValidStorm('| 1.2.3.4 ', {'mode': 'lookup'})
            with self.raises(s_exc.BadSyntax):
                await proxy.reqValidStorm('| 1.2.3.4', {'mode': 'autoadd'})

    async def test_stormcmd(self):

        async with self.getTestCoreAndProxy() as (realcore, core):

            msgs = await alist(core.storm('|help'))
            self.printed(msgs, 'package: synapse')
            self.stormIsInPrint('help', msgs)
            self.stormIsInPrint(': List available commands and a brief description for each.', msgs)

            msgs = await alist(core.storm('help'))
            self.printed(msgs, 'package: synapse')
            self.stormIsInPrint('help', msgs)
            self.stormIsInPrint(': List available commands and a brief description for each.', msgs)

            # test that storm package commands that didn't come from
            # a storm service are displayed
            otherpkg = {
                'name': 'foosball',
                'version': (0, 0, 1),
                'commands': ({
                    'name': 'testcmd',
                    'descr': 'test command',
                    'storm': '[ inet:ipv4=1.2.3.4 ]',
                },)
            }
            self.none(await core.addStormPkg(otherpkg))

            msgs = await alist(core.storm('help'))
            self.printed(msgs, 'package: foosball')
            self.stormIsInPrint('testcmd', msgs)
            self.stormIsInPrint(': test command', msgs)

            await alist(core.eval('[ inet:user=visi inet:user=whippit ]'))

            await self.agenlen(2, core.eval('inet:user'))

            # test cmd as last text syntax
            await self.agenlen(1, core.eval('inet:user | limit 1'))

            await self.agenlen(1, core.eval('inet:user | limit 1      '))

            # test cmd and trailing pipe and whitespace syntax
            await self.agenlen(2, core.eval('inet:user | limit 10 | [ +#foo.bar ]'))
            await self.agenlen(1, core.eval('inet:user | limit 10 | +inet:user=visi'))

            # test invalid option syntax
            msgs = await alist(core.storm('inet:user | limit --woot'))
            self.printed(msgs, 'Usage: limit [options] <count>')
            self.len(0, [m for m in msgs if m[0] == 'node'])

    async def test_onsetdel(self):

        args_hit = None

        async def test_cb(*args):
            nonlocal args_hit
            args_hit = args

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                core.model.prop('inet:ipv4:loc').onSet(test_cb)

                node = await snap.addNode('inet:ipv4', '1.2.3.4')
                await node.set('loc', 'US.  VA')

                self.eq(args_hit, [node, None])

                args_hit = None
                core.model.prop('inet:ipv4:loc').onDel(test_cb)

                await node.pop('loc')
                self.eq(args_hit, [node, 'us.va'])

                self.none(node.get('loc'))

            async with await core.snap() as snap:
                node = await snap.addNode('inet:ipv4', '1.2.3.4')
                self.none(node.get('loc'))

    async def test_cortex_onofftag(self):

        async with self.getTestCore() as core:

            tags = {}

            def onadd(node, tag, valu):
                tags[tag] = valu

            def ondel(node, tag, valu):
                self.none(node.getTag(tag))
                self.false(node.hasTag(tag))
                tags.pop(tag)

            core.onTagAdd('foo', onadd)
            core.onTagAdd('foo.bar', onadd)
            core.onTagAdd('foo.bar.baz', onadd)

            core.onTagDel('foo', ondel)
            core.onTagDel('foo.bar', ondel)
            core.onTagDel('foo.bar.baz', ondel)

            core.onTagAdd('glob.*', onadd)
            core.onTagDel('glob.*', ondel)

            async with await core.snap() as snap:

                node = await snap.addNode('test:str', 'hehe')
                await node.addTag('foo.bar.baz', valu=(200, 300))

                self.eq(tags.get('foo'), (None, None))
                self.eq(tags.get('foo.bar'), (None, None))
                self.eq(tags.get('foo.bar.baz'), (200, 300))

                await node.delTag('foo.bar')

                self.eq(tags.get('foo'), (None, None))

                self.none(tags.get('foo.bar'))
                self.none(tags.get('foo.bar.baz'))

                core.offTagAdd('foo.bar', onadd)
                core.offTagDel('foo.bar', ondel)
                core.offTagAdd('foo.bar', lambda x: 0)
                core.offTagDel('foo.bar', lambda x: 0)

                await node.addTag('foo.bar', valu=(200, 300))
                self.none(tags.get('foo.bar'))

                tags['foo.bar'] = 'fake'
                await node.delTag('foo.bar')
                self.eq(tags.get('foo.bar'), 'fake')

                # Coverage for removing something from a
                # tag we never added a handler for.
                core.offTagAdd('test.newp', lambda x: 0)
                core.offTagDel('test.newp', lambda x: 0)

                # Test tag glob handlers
                await node.addTag('glob.foo', valu=(200, 300))
                self.eq(tags.get('glob.foo'), (200, 300))

                await node.delTag('glob.foo')
                self.none(tags.get('glob.foo'))

                await node.addTag('glob.foo.bar', valu=(200, 300))
                self.none(tags.get('glob.foo.bar'))

                # Test handlers don't run after removed
                core.offTagAdd('glob.*', onadd)
                core.offTagDel('glob.*', ondel)
                await node.addTag('glob.faz', valu=(200, 300))
                self.none(tags.get('glob.faz'))
                tags['glob.faz'] = (1, 2)
                await node.delTag('glob.faz')
                self.eq(tags['glob.faz'], (1, 2))

    async def test_remote_storm(self):

        # Remote storm test paths
        async with self.getTestCoreAndProxy() as (realcore, core):
            # Storm logging
            with self.getAsyncLoggerStream('synapse.cortex', 'Executing storm query {help ask} as [root]') \
                    as stream:
                await alist(core.storm('help ask'))
                self.true(await stream.wait(4))
            # Bad syntax
            mesgs = await alist(core.storm(' | | | '))
            self.len(1, [mesg for mesg in mesgs if mesg[0] == 'init'])
            self.len(1, [mesg for mesg in mesgs if mesg[0] == 'fini'])
            # Lark sensitive test
            self.stormIsInErr("No terminal defined for '|'", mesgs)
            errs = [mesg[1] for mesg in mesgs if mesg[0] == 'err']
            self.eq(errs[0][0], 'BadSyntax')

    async def test_strict(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                node = await snap.addNode('test:str', 'foo')

                await self.asyncraises(s_exc.NoSuchProp, node.set('newpnewp', 10))
                await self.asyncraises(s_exc.BadTypeValu, node.set('tick', (20, 30)))

                snap.strict = False
                self.none(await snap.addNode('test:str', s_common.novalu))

                self.false(await node.set('newpnewp', 10))
                self.false(await node.set('tick', (20, 30)))

    async def test_getcoremods(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            self.nn(core.getCoreMod('synapse.tests.utils.TestModule'))

            # Ensure that the module load creates a node.
            await self.agenlen(1, core.eval('meta:source=8f1401de15918358d5247e21ca29a814'))

            mods = dict(await prox.getCoreMods())

            conf = mods.get('synapse.tests.utils.TestModule')
            self.nn(conf)
            self.eq(conf.get('key'), 'valu')

    async def test_storm_mustquote(self):

        async with self.getTestCore() as core:
            await core.nodes('[ inet:ipv4=1.2.3.4 ]')
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4|limit 20'))

    async def test_storm_cmdname(self):

        class Bork:
            name = 'foo:bar'

        class Bawk:
            name = '.foobar'

        async with self.getTestCore() as core:

            with self.raises(s_exc.BadCmdName):
                core.addStormCmd(Bork)

            with self.raises(s_exc.BadCmdName):
                core.addStormCmd(Bawk)

    async def test_storm_comment(self):

        async with self.getTestCore() as core:

            text = '''
            /* A
               multiline
               comment */
            [ inet:ipv4=1.2.3.4 ] // this is a comment
            // and this too...

            switch $foo {

                // The bar case...

                bar: {
                    [ +#hehe.haha ]
                }

                /*
                   The
                   baz
                   case
                */
                'baz faz': {}
            }
            '''
            opts = {'vars': {'foo': 'bar'}}
            nodes = await alist(core.eval(text, opts=opts))
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef, ('inet:ipv4', 0x01020304))
                self.nn(node.getTag('hehe.haha'))

    async def test_storm_varlistset(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'blob': ('vertex.link', '9001')}}
            text = '($fqdn, $crap) = $blob [ inet:fqdn=$fqdn ]'

            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef, ('inet:fqdn', 'vertex.link'))

    async def test_storm_contbreak(self):

        async with self.getTestCore() as core:

            text = '''
            for $foo in $foos {

                [ inet:ipv4=1.2.3.4 ]

                switch $foo {
                    bar: { [ +#ohai ] break }
                    baz: { [ +#visi ] continue }
                }

                [ inet:ipv4=5.6.7.8 ]

                [ +#hehe ]
            }
            '''
            opts = {'vars': {'foos': ['baz', 'baz']}}
            await core.nodes(text, opts=opts)

            nodes = await core.nodes('inet:ipv4')
            self.len(1, nodes)
            self.nn(nodes[0].getTag('visi'))
            self.none(nodes[0].getTag('hehe'))

            await core.nodes('inet:ipv4 | delnode')

            opts = {'vars': {'foos': ['bar', 'bar']}}
            await core.nodes(text, opts=opts)

            nodes = await core.nodes('inet:ipv4')
            self.len(1, nodes)
            self.nn(nodes[0].getTag('ohai'))
            self.none(nodes[0].getTag('hehe'))

            await core.nodes('inet:ipv4 | delnode')

            opts = {'vars': {'foos': ['lols', 'lulz']}}
            await core.nodes(text, opts=opts)

            nodes = await core.nodes('inet:ipv4')
            for node in nodes:
                self.nn(node.getTag('hehe'))

    async def test_storm_varcall(self):

        async with self.getTestCore() as core:

            text = '''
            for $foo in $foos {

                ($fqdn, $ipv4) = $foo.split("|")

                [ inet:dns:a=($fqdn, $ipv4) ]
            }
            '''
            opts = {'vars': {'foos': ['vertex.link|1.2.3.4']}}
            await core.nodes(text, opts=opts)
            self.len(1, await core.nodes('inet:dns:a=(vertex.link,1.2.3.4)'))

    async def test_storm_dict_deref(self):

        async with self.getTestCore() as core:

            text = '''
            [ test:int=$hehe.haha ]
            '''
            opts = {'vars': {'hehe': {'haha': 20}}}
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 20)

    async def test_storm_varlist_compute(self):

        async with self.getTestCore() as core:

            text = '''
                [ test:str=foo .seen=(2014,2015) ]
                ($tick, $tock) = .seen
                [ test:int=$tick ]
                +test:int
            '''
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 1388534400000)

    async def test_storm_selfrefs(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:fqdn=woot.com ] -> *')

            self.len(1, nodes)
            self.eq('com', nodes[0].ndef[1])

            await core.nodes('inet:fqdn=woot.com | delnode')

            self.len(0, await core.nodes('inet:fqdn=woot.com'))

    async def test_storm_addnode_runtsafe(self):

        async with self.getTestCore() as core:
            # test adding nodes from other nodes output
            q = '[ inet:fqdn=woot.com inet:fqdn=vertex.link ] [ inet:user = :zone ] +inet:user'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            ndefs = list(sorted([n.ndef for n in nodes]))
            self.eq(ndefs, (('inet:user', 'vertex.link'), ('inet:user', 'woot.com')))

    async def test_storm_subgraph(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:ipv4=1.2.3.4 :asn=20 ]')
            await core.nodes('[ inet:dns:a=(woot.com, 1.2.3.4) +#yepr ]')
            await core.nodes('[ inet:dns:a=(vertex.link, 5.5.5.5) +#nope ]')

            rules = {

                'degrees': 2,

                'pivots': ['<- meta:seen <- meta:source'],

                'filters': ['-#nope'],

                'forms': {

                    'inet:fqdn': {
                        'pivots': ['<- *', '-> *'],
                        'filters': ['-inet:fqdn:issuffix=1'],
                    },

                    'syn:tag': {
                        'pivots': ['-> *'],
                    },

                    '*': {
                        'pivots': ['-> #'],
                    },

                }
            }

            seeds = []
            alldefs = {}

            async with await core.snap() as snap:
                async for node, path in snap.storm('inet:fqdn', opts={'graph': rules}):

                    if path.metadata.get('graph:seed'):
                        seeds.append(node.ndef)

                    alldefs[node.ndef] = path.metadata.get('edges')

            # our TLDs should be omits
            self.len(2, seeds)
            self.len(4, alldefs)

            self.isin(('inet:fqdn', 'woot.com'), seeds)
            self.isin(('inet:fqdn', 'vertex.link'), seeds)

            self.nn(alldefs.get(('syn:tag', 'yepr')))
            self.nn(alldefs.get(('inet:dns:a', ('woot.com', 0x01020304))))

            self.none(alldefs.get(('inet:asn', 20)))
            self.none(alldefs.get(('syn:tag', 'nope')))
            self.none(alldefs.get(('inet:dns:a', ('vertex.link', 0x05050505))))

            # now do the same options via the command...
            text = '''
                inet:fqdn | graph
                                --degrees 2
                                --filter { -#nope }
                                --pivot { <- meta:seen <- meta:source }
                                --form-pivot inet:fqdn {<- * | limit 20}
                                --form-pivot inet:fqdn {-> * | limit 20}
                                --form-filter inet:fqdn {-inet:fqdn:issuffix=1}
                                --form-pivot syn:tag {-> *}
                                --form-pivot * {-> #}
            '''

            seeds = []
            alldefs = {}

            async with await core.snap() as snap:

                async for node, path in snap.storm(text):

                    if path.metadata.get('graph:seed'):
                        seeds.append(node.ndef)

                    alldefs[node.ndef] = path.metadata.get('edges')

            # our TLDs should be omits
            self.len(2, seeds)
            self.len(4, alldefs)

            self.isin(('inet:fqdn', 'woot.com'), seeds)
            self.isin(('inet:fqdn', 'vertex.link'), seeds)

            self.nn(alldefs.get(('syn:tag', 'yepr')))
            self.nn(alldefs.get(('inet:dns:a', ('woot.com', 0x01020304))))

            self.none(alldefs.get(('inet:asn', 20)))
            self.none(alldefs.get(('syn:tag', 'nope')))
            self.none(alldefs.get(('inet:dns:a', ('vertex.link', 0x05050505))))

            # filterinput=false behavior
            rules['filterinput'] = False
            seeds = []
            alldefs = {}
            async with await core.snap() as snap:
                async for node, path in snap.storm('inet:fqdn', opts={'graph': rules}):

                    if path.metadata.get('graph:seed'):
                        seeds.append(node.ndef)

                    alldefs[node.ndef] = path.metadata.get('edges')

            # our TLDs are no longer omits
            self.len(4, seeds)
            self.len(6, alldefs)
            self.isin(('inet:fqdn', 'com'), seeds)
            self.isin(('inet:fqdn', 'link'), seeds)
            self.isin(('inet:fqdn', 'woot.com'), seeds)
            self.isin(('inet:fqdn', 'vertex.link'), seeds)

            # yieldfiltered = True
            rules.pop('filterinput', None)
            rules['yieldfiltered'] = True

            seeds = []
            alldefs = {}
            async with await core.snap() as snap:
                async for node, path in snap.storm('inet:fqdn', opts={'graph': rules}):

                    if path.metadata.get('graph:seed'):
                        seeds.append(node.ndef)

                    alldefs[node.ndef] = path.metadata.get('edges')

            # The tlds are omitted, but since we are yieldfiltered=True,
            # we still get the seeds. We also get an inet:dns:a node we
            # previously omitted.
            self.len(4, seeds)
            self.len(7, alldefs)
            self.isin(('inet:dns:a', ('vertex.link', 84215045)), alldefs)

            # refs
            rules = {
                'degrees': 2,
                'refs': True,
            }

            seeds = []
            alldefs = {}
            async with await core.snap() as snap:
                async for node, path in snap.storm('inet:dns:a:fqdn=woot.com',
                                                   opts={'graph': rules}):
                    if path.metadata.get('graph:seed'):
                        seeds.append(node.ndef)

                    alldefs[node.ndef] = path.metadata.get('edges')

            self.len(1, seeds)
            self.len(5, alldefs)
            # We did make it automatically away 2 degrees with just model refs
            self.eq({('inet:dns:a', ('woot.com', 16909060)),
                     ('inet:fqdn', 'woot.com'),
                     ('inet:ipv4', 16909060),
                     ('inet:fqdn', 'com'),
                     ('inet:asn', 20)}, set(alldefs.keys()))

            # Construct a test that encounters nodes which are already
            # in the to-do queue. This is mainly a coverage test.
            q = '[inet:ipv4=0 inet:ipv4=1 inet:ipv4=2 :asn=1138 +#deathstar]'
            await core.nodes(q)

            q = '#deathstar | graph --degrees 2 --refs'
            ndefs = set()
            async with await core.snap() as snap:
                async for node, path in snap.storm(q):
                    ndefs.add(node.ndef)
            self.isin(('inet:asn', 1138), ndefs)

    async def test_storm_two_level_assignment(self):
        async with self.getTestCore() as core:
            q = '$foo=baz $bar=$foo [test:str=$bar]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('baz', nodes[0].ndef[1])

    async def test_storm_quoted_variables(self):
        async with self.getTestCore() as core:
            q = '$"my var"=baz $bar=$"my var" [test:str=$bar]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('baz', nodes[0].ndef[1])

            q = '$d = $lib.dict("field 1"=foo, "field 2"=bar) [test:str=$d.\'field 1\']'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('foo', nodes[0].ndef[1])

            q = '($"a", $"#", $c) = (1, 2, 3) [test:str=$"#"]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('2', nodes[0].ndef[1])

    async def test_storm_lib_custom(self):

        async with self.getTestCore() as core:
            # Test the registered function from test utils
            q = '[ ps:person="*" :name = $lib.test.beep(loud) ]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('a loud beep!', nodes[0].get('name'))

            q = '$test = $lib.test.beep(test) [test:str=$test]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('A test beep!', nodes[0].ndef[1])

            # Regression:  variable substitution in function raises exception
            q = '$foo=baz $test = $lib.test.beep($foo) [test:str=$test]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('A baz beep!', nodes[0].ndef[1])

    async def test_storm_type_node(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ ps:person="*" edge:has=($node, (inet:fqdn,woot.com)) ]')
            self.len(2, nodes)
            self.eq('edge:has', nodes[0].ndef[0])

            nodes = await core.nodes('[test:str=test] [ edge:refs=($node,(test:int, 1234)) ] -test:str')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], (('test:str', 'test'), ('test:int', 1234)))

            nodes = await core.nodes('test:int=1234 [test:str=$node.value()] -test:int')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', '1234'))

            nodes = await core.nodes('test:int=1234 [test:str=$node.form()] -test:int')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'test:int'))

    async def test_storm_subq_size(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:dns:a=(woot.com, 1.2.3.4) inet:dns:a=(vertex.link, 1.2.3.4) ]')

            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }=0 )'))

            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }=2 )'))
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }=3 )'))

            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }!=2 )'))
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }!=3 )'))

            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }>=1 )'))
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }>=2 )'))
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }>=3 )'))

            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }<=1 )'))
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }<=2 )'))
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }<=3 )'))

            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 +{ -> inet:dns:a } < 2 '))
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 +{ -> inet:dns:a } < 3 '))

            self.len(1, await core.nodes('inet:ipv4=1.2.3.4 +{ -> inet:dns:a } > 1 '))
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4 +{ -> inet:dns:a } > 2 '))

    async def test_cortex_in(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                await snap.addNode('test:str', 'a')
                await snap.addNode('test:str', 'b')
                await snap.addNode('test:str', 'c')

            self.len(0, await core.nodes('test:str*in=()'))
            self.len(0, await core.nodes('test:str*in=(d,)'))
            self.len(2, await core.nodes('test:str*in=(a, c)'))
            self.len(1, await core.nodes('test:str*in=(a, d)'))
            self.len(3, await core.nodes('test:str*in=(a, b, c)'))

            self.len(0, await core.nodes('test:str +test:str*in=()'))
            self.len(0, await core.nodes('test:str +test:str*in=(d,)'))
            self.len(2, await core.nodes('test:str +test:str*in=(a, c)'))
            self.len(1, await core.nodes('test:str +test:str*in=(a, d)'))
            self.len(3, await core.nodes('test:str +test:str*in=(a, b, c)'))

    async def test_runt(self):
        async with self.getTestCore() as core:

            # Ensure that lifting by form/prop/values works.
            nodes = await core.nodes('test:runt')
            self.len(4, nodes)

            nodes = await core.nodes('test:runt.created')
            self.len(4, nodes)

            nodes = await core.nodes('test:runt:tick=2010')
            self.len(2, nodes)

            nodes = await core.nodes('test:runt:tick=2001')
            self.len(1, nodes)

            nodes = await core.nodes('test:runt:tick=2019')
            self.len(0, nodes)

            nodes = await core.nodes('test:runt:lulz="beep.sys"')
            self.len(1, nodes)

            nodes = await core.nodes('test:runt:lulz')
            self.len(2, nodes)

            nodes = await core.nodes('test:runt:tick=$foo', {'vars': {'foo': '2010'}})
            self.len(2, nodes)

            # Ensure that non-equality based lift comparators for the test runt nodes work.
            nodes = await core.nodes('test:runt~="b.*"')
            self.len(3, nodes)

            nodes = await core.nodes('test:runt:tick*range=(1999, 2001)')
            self.len(1, nodes)

            # Ensure that a lift by a universal property doesn't lift a runt node
            # accidentally.
            nodes = await core.nodes('.created')
            self.ge(len(nodes), 1)
            self.notin('test:ret', {node.ndef[0] for node in nodes})

            # Ensure we can do filter operations on runt nodes
            nodes = await core.nodes('test:runt +:tick*range=(1999, 2003)')
            self.len(1, nodes)

            nodes = await core.nodes('test:runt -:tick*range=(1999, 2003)')
            self.len(3, nodes)

            # Ensure we can pivot to/from runt nodes
            async with await core.snap() as snap:
                await snap.addNode('test:str', 'beep.sys')

            nodes = await core.nodes('test:runt :lulz -> test:str')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'beep.sys'))

            nodes = await core.nodes('test:str -> test:runt:lulz')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:runt', 'beep'))

            # Lift by ndef/iden/opts does not work since runt support is not plumbed
            # into any caching which those lifts perform.
            ndef = ('test:runt', 'blah')
            iden = '15e33ccff08f9f96b5cea9bf0bcd2a55a96ba02af87f8850ba656f2a31429224'
            nodes = await core.nodes(f'iden {iden}')
            self.len(0, nodes)

            nodes = await core.nodes('', {'idens': [iden]})
            self.len(0, nodes)

            nodes = await core.nodes('', {'ndefs': [ndef]})
            self.len(0, nodes)

            # Ensure that add/edit a read-only runt prop fails, whether or not it exists.
            await self.asyncraises(s_exc.IsRuntForm,
                                   core.nodes('test:runt=beep [:tick=3001]'))
            await self.asyncraises(s_exc.IsRuntForm,
                                   core.nodes('test:runt=woah [:tick=3001]'))

            # Ensure that we can add/edit secondary props which has a callback.
            nodes = await core.nodes('test:runt=beep [:lulz=beepbeep.sys]')
            self.eq(nodes[0].get('lulz'), 'beepbeep.sys')
            await nodes[0].set('lulz', 'beepbeep.sys')  # We can do no-operation edits
            self.eq(nodes[0].get('lulz'), 'beepbeep.sys')

            # We can set props which were not there previously
            nodes = await core.nodes('test:runt=woah [:lulz=woah.sys]')
            self.eq(nodes[0].get('lulz'), 'woah.sys')

            # A edit may throw an exception due to some prop-specific normalization reason.
            await self.asyncraises(s_exc.BadTypeValu, core.nodes('test:runt=woah [:lulz=no.way]'))

            # Setting a property which has no callback or ro fails.
            await self.asyncraises(s_exc.IsRuntForm, core.nodes('test:runt=woah [:newp=pennywise]'))

            # Ensure that delete a read-only runt prop fails, whether or not it exists.
            await self.asyncraises(s_exc.IsRuntForm,
                                   core.nodes('test:runt=beep [-:tick]'))
            await self.asyncraises(s_exc.IsRuntForm,
                                   core.nodes('test:runt=woah [-:tick]'))

            # Ensure that we can delete a secondary prop which has a callback.
            nodes = await core.nodes('test:runt=beep [-:lulz]')
            self.none(nodes[0].get('lulz'))

            nodes = await core.nodes('test:runt=woah [-:lulz]')
            self.none(nodes[0].get('lulz'))

            # Deleting a property which has no callback or ro fails.
            await self.asyncraises(s_exc.IsRuntForm, core.nodes('test:runt=woah [-:newp]'))

            # # Ensure that adding tags on runt nodes fails
            await self.asyncraises(s_exc.IsRuntForm, core.nodes('test:runt=beep [+#hehe]'))
            await self.asyncraises(s_exc.IsRuntForm, core.nodes('test:runt=beep [-#hehe]'))

            # Ensure that adding / deleting test runt nodes fails
            await self.asyncraises(s_exc.IsRuntForm, core.nodes('[test:runt=" oh MY! "]'))
            await self.asyncraises(s_exc.IsRuntForm, core.nodes('test:runt=beep | delnode'))

            # Sad path for underlying Cortex.runRuntLift
            nodes = await alist(core.runRuntLift('test:newp', 'newp'))
            self.len(0, nodes)

    async def test_cortex_view_invalid(self):

        async with self.getTestCore() as core:

            core.view.invalid = s_common.guid()
            with self.raises(s_exc.NoSuchLayer):
                await core.nodes('[ test:str=foo ]')

            core.view.invalid = None
            self.len(1, await core.nodes('[ test:str=foo ]'))

    async def test_tag_globbing(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'n1')
                await node.addTag('foo.bar.baz', (None, None))

                node = await snap.addNode('test:str', 'n2')
                await node.addTag('foo.bad.baz', (None, None))

                node = await snap.addNode('test:str', 'n3')  # No tags on him

            # Setup worked correct
            self.len(3, await core.nodes('test:str'))
            self.len(2, await core.nodes('test:str +#foo'))

            # Now test globbing - exact match for *
            self.len(2, await core.nodes('test:str +#*'))
            self.len(1, await core.nodes('test:str -#*'))

            # Now test globbing - single star matches one tag level
            self.len(2, await core.nodes('test:str +#foo.*.baz'))
            self.len(1, await core.nodes('test:str +#*.bad'))
            # Double stars matches a whole lot more!
            self.len(2, await core.nodes('test:str +#foo.**.baz'))
            self.len(1, await core.nodes('test:str +#**.bar.baz'))
            self.len(2, await core.nodes('test:str +#**.baz'))

    async def test_storm_lift_compute(self):
        async with self.getTestCore() as core:
            self.len(2, await core.nodes('[ inet:dns:a=(vertex.link,1.2.3.4) inet:dns:a=(woot.com,5.6.7.8)]'))
            self.len(4, await core.nodes('inet:dns:a inet:fqdn=:fqdn'))

    async def test_cortex_hive(self):
        async with self.getTestCore() as core:
            await core.hive.set(('visi',), 200)
            async with core.getLocalProxy(share='cortex/hive') as hive:
                self.eq(200, await hive.get(('visi',)))

    async def test_delevent(self):
        ''' Tests deleting a node with a property without an index '''
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                evt_guid = s_common.guid('evt')
                node = await snap.addNode('graph:event', evt_guid, {'name': 'an event', 'data': 'beep'})

                await node.delete(force=True)

    async def test_cortex_delnode_perms(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')

            await visi.addRule((True, ('node', 'add')))
            await visi.addRule((True, ('node', 'prop', 'set')))
            await visi.addRule((True, ('node', 'tag', 'add')))

            opts = {'user': visi.iden}

            await core.nodes('[ test:cycle0=foo :cycle1=bar ]', opts=opts)
            await core.nodes('[ test:cycle1=bar :cycle0=foo ]', opts=opts)

            await core.nodes('[ test:str=foo +#lol ]', opts=opts)

            # no perms and not elevated...
            with self.raises(s_exc.AuthDeny):
                await core.nodes('test:str=foo | delnode', opts=opts)

            await visi.addRule((True, ('node', 'del')))

            # should still deny because node has tag we can't delete
            with self.raises(s_exc.AuthDeny):
                await core.nodes('test:str=foo | delnode', opts=opts)

            await visi.addRule((True, ('node', 'tag', 'del', 'lol')))

            self.len(0, await core.nodes('test:str=foo | delnode', opts=opts))

            with self.raises(s_exc.CantDelNode):
                await core.nodes('test:cycle0=foo | delnode', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('test:cycle0=foo | delnode --force', opts=opts)

            await visi.setAdmin(True)

            self.len(0, await core.nodes('test:cycle0=foo | delnode --force', opts=opts))

    async def test_cortex_cell_splices(self):

        async with self.getTestCore() as core:

            async with core.getLocalProxy() as prox:
                # TestModule creates one node and 3 splices
                await self.agenlen(3, prox.splices((0, 0, 0), 1000))

                await alist(prox.eval('[ test:str=foo ]'))

                splicelist = await alist(prox.splices((0, 0, 0), 1000))
                splicecount = len(splicelist)
                self.ge(splicecount, 3)

                # should get the same splices in reverse order
                splicelist.reverse()
                self.eq(await alist(prox.splicesBack(splicelist[0][0], 1000)), splicelist)
                self.eq(await alist(prox.splicesBack(splicelist[0][0], 3)), splicelist[:3])

                self.eq(await alist(prox.spliceHistory()), [s[1] for s in splicelist])

                visi = await prox.addUser('visi')
                await prox.setUserPasswd(visi['iden'], 'secret')

                await prox.addUserRule(visi['iden'], (True, ('node', 'add')))
                await prox.addUserRule(visi['iden'], (True, ('prop', 'set')))

                async with core.getLocalProxy(user='visi') as asvisi:

                    # normal user can't user splicesBack
                    await self.agenraises(s_exc.AuthDeny, asvisi.splicesBack((1000, 0, 0), 1000))

                    # make sure a normal user only gets their own splices
                    await alist(asvisi.eval('[ test:str=bar ]'))
                    await self.agenlen(2, asvisi.spliceHistory())

                    # should get all splices now as an admin
                    await prox.setUserAdmin(visi['iden'], True)
                    await self.agenlen(splicecount + 2, asvisi.spliceHistory())

    async def test_node_repr(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                node = await snap.addNode('inet:ipv4', 0x01020304)
                self.eq('1.2.3.4', node.repr())

                node = await snap.addNode('inet:dns:a', ('woot.com', 0x01020304))
                self.eq('1.2.3.4', node.repr('ipv4'))

    async def test_coverage(self):

        # misc tests to increase code coverage
        async with self.getTestCore() as core:

            node = (('test:str', 'foo'), {})

            await alist(core.addNodes((node,)))

            self.nn(await core.getNodeByNdef(('test:str', 'foo')))

    async def test_cortex_storm_vars(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'foo': '1.2.3.4'}}

            await self.agenlen(1, core.eval('[ inet:ipv4=$foo ]', opts=opts))
            await self.agenlen(1, core.eval('$bar=5.5.5.5 [ inet:ipv4=$bar ]'))

            await self.agenlen(1, core.eval('[ inet:dns:a=(woot.com,1.2.3.4) ]'))

            await self.agenlen(2, core.eval('inet:dns:a=(woot.com,1.2.3.4) $hehe=:fqdn inet:fqdn=$hehe'))

            await self.agenlen(1, core.eval('inet:dns:a=(woot.com,1.2.3.4) $hehe=:fqdn +:fqdn=$hehe'))
            await self.agenlen(0, core.eval('inet:dns:a=(woot.com,1.2.3.4) $hehe=:fqdn -:fqdn=$hehe'))

            await self.agenlen(1, core.eval('[ test:pivcomp=(hehe,haha) :tick=2015 +#foo=(2014,2016) ]'))
            await self.agenlen(1, core.eval('test:pivtarg=hehe [ .seen=2015 ]'))

            await self.agenlen(1,
                               core.eval('test:pivcomp=(hehe,haha) $ticktock=#foo -> test:pivtarg +.seen@=$ticktock'))

            await self.agenlen(1, core.eval('inet:dns:a=(woot.com,1.2.3.4) [ .seen=(2015,2018) ]'))

            async for node in core.eval('inet:dns:a=(woot.com,1.2.3.4) $seen=.seen :fqdn -> inet:fqdn [ .seen=$seen ]'):
                self.eq(node.get('.seen'), (1420070400000, 1514764800000))

            await self.agenraises(s_exc.NoSuchProp, core.eval('inet:dns:a=(woot.com,1.2.3.4) $newp=.newp'))

            # Vars can also be provided as tuple
            opts = {'vars': {'foo': ('hehe', 'haha')}}
            await self.agenlen(1, core.eval('test:pivcomp=$foo', opts=opts))

            # Vars can also be provided as integers
            norm = core.model.type('time').norm('2015')[0]
            opts = {'vars': {'foo': norm}}
            await self.agenlen(1, core.eval('test:pivcomp:tick=$foo', opts=opts))

    async def test_cortex_snap_eval(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                await self.agenlen(2, snap.eval('[test:str=foo test:str=bar]'))
            await self.agenlen(2, core.eval('test:str'))

    async def test_cortex_nexslogen_off(self):
        '''
        Everything still works when no nexus log is kept
        '''
        conf = {'layer:lmdb:map_async': True,
                'provenance:en': True,
                'nexslog:en': False,
                'layers:logedits': True,
                }
        async with self.getTestCore(conf=conf) as core:
            async with await core.snap() as snap:
                await self.agenlen(2, snap.eval('[test:str=foo test:str=bar]'))
            await self.agenlen(2, core.eval('test:str'))

    async def test_cortex_logedits_off(self):
        '''
        Everything still works when no layer log is kept
        '''
        conf = {'layer:lmdb:map_async': True,
                'provenance:en': True,
                'nexslog:en': True,
                'layers:logedits': False,
                }
        async with self.getTestCore(conf=conf) as core:
            async with await core.snap() as snap:
                await self.agenlen(2, snap.eval('[test:str=foo test:str=bar]'))
            self.len(2, await core.nodes('test:str'))

            layr = core.getLayer()
            await self.agenlen(0, layr.splices())
            await self.agenlen(0, layr.splicesBack())
            await self.agenlen(0, layr.syncNodeEdits(0))
            self.eq(0, await layr.getNodeEditOffset())

            self.nn(await core.stat())

    async def test_feed_syn_nodes(self):
        async with self.getTestCore() as core0:
            q = '[test:int=1 test:int=2 test:int=3]'
            podes = [n.pack() async for n in core0.eval(q)]
            self.len(3, podes)

        async with self.getTestCore() as core1:

            await core1.addFeedData('syn.nodes', podes)
            await self.agenlen(3, core1.eval('test:int'))

            await core1.addTagProp('test', ('int', {}), {})
            async with await core1.snap() as snap:
                node = await snap.getNodeByNdef(('test:int', 1))
                await node.setTagProp('beep.beep', 'test', 1138)
                pode = node.pack()

            pode = (('test:int', 4), pode[1])

            await core1.addFeedData('syn.nodes', [pode])
            nodes = await core1.nodes('test:int=4')
            self.eq(1138, nodes[0].getTagProp('beep.beep', 'test'))

            # Put bad data in
            data = [(('test:str', 'newp'), {'tags': {'test.newp': 'newp'}})]
            await core1.addFeedData('syn.nodes', data)
            self.len(1, await core1.nodes('test:str=newp -#test.newp'))

            data = [(('test:str', 'opps'), {'tagprops': {'test.newp': {'newp': 'newp'}}})]
            await core1.addFeedData('syn.nodes', data)
            self.len(1, await core1.nodes('test:str=opps +#test.newp'))

    async def test_feed_syn_splice(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            mesg = ('node:add', {'ndef': ('test:str', 'foo')})
            await core.addFeedData('syn.splice', [mesg])

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'foo'))
                self.nn(node)

            # test coreapi addFeedData
            mesg = ('node:add', {'ndef': ('test:str', 'foobar')})
            await prox.addFeedData('syn.splice', [mesg])

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'foobar'))
                self.nn(node)

            mesg = ('prop:set', {'ndef': ('test:str', 'foo'), 'prop': 'tick', 'valu': 200})
            await core.addFeedData('syn.splice', [mesg])

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'foo'))
                self.eq(200, node.get('tick'))

            mesg = ('prop:del', {'ndef': ('test:str', 'foo'), 'prop': 'tick'})
            await core.addFeedData('syn.splice', [mesg])

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'foo'))
                self.none(node.get('tick'))

            mesg = ('tag:add', {'ndef': ('test:str', 'foo'), 'tag': 'bar', 'valu': (200, 300)})
            await core.addFeedData('syn.splice', [mesg])

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'foo'))
                self.eq((200, 300), node.getTag('bar'))

            mesg = ('tag:del', {'ndef': ('test:str', 'foo'), 'tag': 'bar'})
            await core.addFeedData('syn.splice', [mesg])

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'foo'))
                self.none(node.getTag('bar'))

            await core.addTagProp('score', ('int', {}), {})
            splice = ('tag:prop:set', {'ndef': ('test:str', 'foo'), 'tag': 'lol', 'prop': 'score', 'valu': 100,
                                       'curv': None})
            await core.addFeedData('syn.splice', [splice])

            self.len(1, await core.nodes('#lol:score=100'))

            splice = ('tag:prop:del', {'ndef': ('test:str', 'foo'), 'tag': 'lol', 'prop': 'score', 'valu': 100})
            await core.addFeedData('syn.splice', [splice])

            self.len(0, await core.nodes('#lol:score=100'))

            mesg = ('node:del', {'ndef': ('test:str', 'foo')})
            await core.addFeedData('syn.splice', [mesg])

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'foo'))
                self.none(node)

            # test feeding to a different view
            vdef2 = await core.view.fork()
            view2_iden = vdef2.get('iden')
            view2 = core.getView(view2_iden)

            mesg = ('node:add', {'ndef': ('test:str', 'bar')})
            await core.addFeedData('syn.splice', [mesg], viewiden=view2_iden)

            async with await core.snap(view=view2) as snap:
                node = await snap.getNodeByNdef(('test:str', 'bar'))
                self.nn(node)

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'bar'))
                self.none(node)

            # test coreapi addFeedData to a different view
            mesg = ('node:add', {'ndef': ('test:str', 'baz')})
            await prox.addFeedData('syn.splice', [mesg], viewiden=view2_iden)

            async with await core.snap(view=view2) as snap:
                node = await snap.getNodeByNdef(('test:str', 'baz'))
                self.nn(node)

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'baz'))
                self.none(node)

            # sad paths
            await self.asyncraises(s_exc.NoSuchView, core.addFeedData('syn.splice', [mesg], viewiden='badiden'))
            await self.asyncraises(s_exc.NoSuchView, prox.addFeedData('syn.splice', [mesg], viewiden='badiden'))

    async def test_feed_syn_nodeedits(self):

        async with self.getTestCoreAndProxy() as (core0, prox0):

            nodelist0 = []
            nodelist0.extend(await core0.nodes('[ test:str=foo ]'))
            nodelist0.extend(await core0.nodes('[ inet:ipv4=1.2.3.4 .seen=(2012,2014) +#foo.bar=(2012, 2014) ]'))

            with self.raises(s_exc.NoSuchLayer):
                async for _, nodeedits in prox0.syncLayerNodeEdits(0, layriden='asdf', wait=False):
                    pass

            with self.raises(s_exc.NoSuchLayer):
                async for _, nodeedits in core0.syncLayerNodeEdits('asdf', 0, wait=False):
                    pass

            editlist = []
            async for _, nodeedits in prox0.syncLayerNodeEdits(0, wait=False):
                editlist.append(nodeedits)

            async with self.getTestCoreAndProxy() as (core1, prox1):

                await prox1.addFeedData('syn.nodeedits', editlist)

                nodelist1 = []
                nodelist1.extend(await core1.nodes('test:str'))
                nodelist1.extend(await core1.nodes('inet:ipv4'))

                nodelist0 = [node.pack() for node in nodelist0]
                nodelist1 = [node.pack() for node in nodelist1]
                self.eq(nodelist0, nodelist1)

                # Try a nodeedits we might get from cmdr
                cmdrnodeedits = s_common.jsonsafe_nodeedits(editlist[1])
                await core0.nodes('test:str=foo | delnode')

                await prox1.addFeedData('syn.nodeedits', [cmdrnodeedits])
                self.len(1, await core1.nodes('test:str'))

    async def test_stat(self):

        async with self.getTestCoreAndProxy() as (realcore, core):
            coreiden = realcore.iden
            ostat = await core.stat()
            self.eq(ostat.get('iden'), coreiden)
            self.isin('layer', ostat)
            await self.agenlen(1, (core.eval('[test:str=123 :tick=2018]')))
            nstat = await core.stat()

            counts = nstat.get('formcounts')
            self.eq(counts.get('test:str'), 1)

    async def test_stat_lock(self):
        self.thisHostMust(hasmemlocking=True)
        conf = {'layers:lockmemory': True}
        async with self.getTestCoreAndProxy(conf=conf) as (realcore, core):
            slab = realcore.view.layers[0].layrslab
            self.true(await asyncio.wait_for(slab.lockdoneevent.wait(), 8))

            nstat = await core.stat()
            layr = nstat.get('layer')
            self.gt(layr.get('lock_goal'), 0)

    async def test_storm_sub_query(self):

        async with self.getTestCore() as core:
            # check that the sub-query can make changes but doesnt effect main query output
            node = (await alist(core.eval('[ test:str=foo +#bar ] { [ +#baz ] -#bar }')))[0]
            self.nn(node.getTag('baz'))

            nodes = await alist(core.eval('[ test:str=oof +#bar ] { [ test:int=0xdeadbeef ] }'))
            await self.agenlen(1, core.eval('test:int=3735928559'))

        # Test using subqueries for filtering
        async with self.getTestCore() as core:
            # Generic tests

            await self.agenlen(1, core.eval('[ test:str=bar +#baz ]'))
            await self.agenlen(1, core.eval('[ test:pivcomp=(foo,bar) ]'))

            await self.agenlen(0, core.eval('test:pivcomp=(foo,bar) -{ :lulz -> test:str +#baz }'))
            await self.agenlen(1, core.eval('test:pivcomp=(foo,bar) +{ :lulz -> test:str +#baz } +test:pivcomp'))

            # Practical real world example

            await self.agenlen(2, core.eval('[ inet:ipv4=1.2.3.4 :loc=us inet:dns:a=(vertex.link,1.2.3.4) ]'))
            await self.agenlen(2, core.eval('[ inet:ipv4=4.3.2.1 :loc=zz inet:dns:a=(example.com,4.3.2.1) ]'))
            await self.agenlen(1, core.eval('inet:ipv4:loc=us'))
            await self.agenlen(1, core.eval('inet:dns:a:fqdn=vertex.link'))
            await self.agenlen(1, core.eval('inet:ipv4:loc=zz'))
            await self.agenlen(1, core.eval('inet:dns:a:fqdn=example.com'))

            # lift all dns, pivot to ipv4 where loc=us, remove the results
            # this should return the example node because the vertex node matches the filter and should be removed
            nodes = await alist(core.eval('inet:dns:a -{ :ipv4 -> inet:ipv4 +:loc=us }'))
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], ('example.com', 67305985))

            # lift all dns, pivot to ipv4 where loc=us, add the results
            # this should return the vertex node because only the vertex node matches the filter
            nodes = await alist(core.eval('inet:dns:a +{ :ipv4 -> inet:ipv4 +:loc=us }'))
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], ('vertex.link', 16909060))

            # lift all dns, pivot to ipv4 where cc!=us, remove the results
            # this should return the vertex node because the example node matches the filter and should be removed
            nodes = await alist(core.eval('inet:dns:a -{ :ipv4 -> inet:ipv4 -:loc=us }'))
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], ('vertex.link', 16909060))

            # lift all dns, pivot to ipv4 where cc!=us, add the results
            # this should return the example node because only the example node matches the filter
            nodes = await alist(core.eval('inet:dns:a +{ :ipv4 -> inet:ipv4 -:loc=us }'))
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], ('example.com', 67305985))

            # lift all dns, pivot to ipv4 where asn=1234, add the results
            # this should return nothing because no nodes have asn=1234
            await self.agenlen(0, core.eval('inet:dns:a +{ :ipv4 -> inet:ipv4 +:asn=1234 }'))

            # lift all dns, pivot to ipv4 where asn!=1234, add the results
            # this should return everything because no nodes have asn=1234
            nodes = await alist(core.eval('inet:dns:a +{ :ipv4 -> inet:ipv4 -:asn=1234 }'))
            self.len(2, nodes)

    async def test_storm_switchcase(self):

        async with self.getTestCore() as core:

            # non-runtsafe switch value
            text = '[inet:ipv4=1 :asn=22] $asn=:asn switch $asn {42: {[+#foo42]} 22: {[+#foo22]}}'
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.nn(nodes[0].getTag('foo22'))
            self.none(nodes[0].getTag('foo42'))

            text = '[inet:ipv4=2 :asn=42] $asn=:asn switch $asn {42: {[+#foo42]} 22: {[+#foo22]}}'
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.none(nodes[0].getTag('foo22'))
            self.nn(nodes[0].getTag('foo42'))

            text = '[inet:ipv4=3 :asn=0] $asn=:asn switch $asn {42: {[+#foo42]} 22: {[+#foo22]}}'
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.none(nodes[0].getTag('foo22'))
            self.none(nodes[0].getTag('foo42'))

            # completely runsafe switch

            text = '$foo=foo switch $foo {foo: {$result=bar} nop: {$result=baz}} [test:str=$result]'
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'bar')

            text = '$foo=nop switch $foo {foo: {$result=bar} nop: {$result=baz}} [test:str=$result]'
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'baz')

            text = '$foo=nop switch $foo {foo: {$result=bar} *: {$result=baz}} [test:str=$result]'
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'baz')

            text = '$foo=xxx $result=xxx switch $foo {foo: {$result=bar} nop: {$result=baz}} [test:str=$result]'
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'xxx')

            text = '$foo=foo switch $foo {foo: {test:str=bar}}'
            nodes = await core.nodes(text)
            self.len(1, nodes)

            opts = {'vars': {'woot': 'hehe'}}
            text = '[test:str=a] switch $woot { hehe: {[+#baz]} }'
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef[1], 'a')
                self.nn(node.getTag('baz'))
                self.none(node.getTag('faz'))
                self.none(node.getTag('jaz'))

            opts = {'vars': {'woot': 'haha hoho'}}
            text = '[test:str=b] switch $woot { hehe: {[+#baz]} "haha hoho": {[+#faz]} "lolz:lulz": {[+#jaz]} }'
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef[1], 'b')
                self.none(node.getTag('baz'))
                self.nn(node.getTag('faz'))
                self.none(node.getTag('jaz'))

            opts = {'vars': {'woot': 'lolz:lulz'}}
            text = "[test:str=c] switch $woot { hehe: {[+#baz]} 'haha hoho': {[+#faz]} 'lolz:lulz': {[+#jaz]} }"
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef[1], 'c')
                self.none(node.getTag('baz'))
                self.none(node.getTag('faz'))
                self.nn(node.getTag('jaz'))

            opts = {'vars': {'woot': 'lulz'}}
            text = '[test:str=c] switch $woot { hehe: {[+#baz]} *: {[+#jaz]} }'
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef[1], 'c')
                self.none(node.getTag('baz'))
                self.nn(node.getTag('jaz'))

            opts = {'vars': {'woot': 'lulz'}}
            text = '''[test:str=c] $form=$node.form() switch $form { 'test:str': {[+#known]} *: {[+#unknown]} }'''
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'c')
            self.nn(node.getTag('known'))
            self.none(node.getTag('unknown'))

    async def test_storm_tagvar(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'tag': 'hehe.haha', 'mtag': '', }}

            nodes = await core.nodes('[ test:str=foo +#$tag ]', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')
            self.nn(node.getTag('hehe.haha'))

            nodes = await core.nodes('#$tag', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')
            self.nn(node.getTag('hehe.haha'))

            nodes = await core.nodes('$tag=hehe.haha test:str=foo +#$tag')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')
            self.nn(node.getTag('hehe.haha'))

            nodes = await core.nodes('[test:str=foo2] $tag="*" test:str +#$tag')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')
            self.nn(node.getTag('hehe.haha'))

            nodes = await core.nodes('$tag=hehe.* test:str +#$tag')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')

            nodes = await core.nodes('[test:str=foo :hehe=newtag] $tag=:hehe [+#$tag]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')
            self.nn(node.getTag('newtag'))

            nodes = await core.nodes('#$tag [ -#$tag ]', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')
            self.none(node.getTag('hehe.haha'))

            mesgs = await core.stormlist('$var=timetag test:str=foo [+#$var=2019] $lib.print(#$var)')
            podes = [m[1] for m in mesgs if m[0] == 'node']
            self.len(1, podes)
            pode = podes[0]
            self.true(s_node.tagged(pode, '#timetag'))

            mesgs = await core.stormlist('test:str=foo $var=$node.value() [+#$var=2019] $lib.print(#$var)')
            self.stormIsInPrint('(1546300800000, 1546300800001)', mesgs)
            podes = [m[1] for m in mesgs if m[0] == 'node']
            self.len(1, podes)
            pode = podes[0]
            self.true(s_node.tagged(pode, '#foo'))

            nodes = await core.nodes('$d = $lib.dict(foo=bar) [test:str=yop +#$d.foo]')
            self.len(1, nodes)
            self.nn(nodes[0].getTag('bar'))

            q = '[test:str=yop +#$lib.str.format("{first}.{last}", first=foo, last=bar)]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.nn(nodes[0].getTag('foo.bar'))

            q = '$foo=(tag1,tag2,tag3) [test:str=x +#$foo]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.nn(nodes[0].getTag('tag1'))
            self.nn(nodes[0].getTag('tag2'))
            self.nn(nodes[0].getTag('tag3'))

            nodes = await core.nodes('[ test:str=foo +?#$mtag +?#$tag ]', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')
            self.nn(node.getTag('hehe.haha'))

            q = '$foo=(tag1,?,tag3) [test:str=x +?#$foo]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.nn(nodes[0].getTag('tag1'))
            self.nn(nodes[0].getTag('tag3'))

            q = '$t1="" $t2="" $t3=tag3 [test:str=x -#$t1 +?#$t2 +?#$t3]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.nn(nodes[0].getTag('tag3'))

            mesgs = await core.stormlist('test:str=foo $var=$node.value() [+?#$var=2019] $lib.print(#$var)')
            self.stormIsInPrint('(1546300800000, 1546300800001)', mesgs)
            podes = [m[1] for m in mesgs if m[0] == 'node']
            self.len(1, podes)
            pode = podes[0]
            self.true(s_node.tagged(pode, '#foo'))

            mesgs = await core.stormlist('$var="" test:str=foo [+?#$var=2019] $lib.print(#$var)')
            podes = [m[1] for m in mesgs if m[0] == 'node']
            self.len(1, podes)
            pode = podes[0]
            self.true(s_node.tagged(pode, '#timetag'))

            nodes = await core.nodes('$d = $lib.dict(foo="") [test:str=yop +?#$d.foo +#tag1]')
            self.len(1, nodes)
            self.none(nodes[0].getTag('foo.*'))
            self.nn(nodes[0].getTag('tag1'))

    async def test_storm_forloop(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'fqdns': ('foo.com', 'bar.com')}}

            vals = []
            async for node in core.eval('for $fqdn in $fqdns { [ inet:fqdn=$fqdn ] }', opts=opts):
                vals.append(node.ndef[1])

            self.sorteq(('bar.com', 'foo.com'), vals)

            opts = {'vars': {'dnsa': (('foo.com', '1.2.3.4'), ('bar.com', '5.6.7.8'))}}

            vals = []
            async for node in core.eval('for ($fqdn, $ipv4) in $dnsa { [ inet:dns:a=($fqdn,$ipv4) ] }', opts=opts):
                vals.append(node.ndef[1])

            self.eq((('foo.com', 0x01020304), ('bar.com', 0x05060708)), vals)

            with self.raises(s_exc.StormVarListError):
                await core.nodes('for ($fqdn,$ipv4,$boom) in $dnsa { [ inet:dns:a=($fqdn,$ipv4) ] }', opts=opts)

            q = '[ inet:ipv4=1.2.3.4 +#hehe +#haha ] for ($foo,$bar,$baz) in $node.tags() {[+#$foo]}'
            with self.raises(s_exc.StormVarListError):
                await core.nodes(q)

            await core.nodes('inet:ipv4=1.2.3.4 for $tag in $node.tags() { [ +#hoho ] { [inet:ipv4=5.5.5.5 +#$tag] } continue [ +#visi ] }')  # noqa: E501
            self.len(1, await core.nodes('inet:ipv4=5.5.5.5 +#hehe +#haha -#visi'))

            q = 'inet:ipv4=1.2.3.4 for $tag in $node.tags() { [ +#hoho ] { [inet:ipv4=6.6.6.6 +#$tag] } break [ +#visi ]}'  # noqa: E501
            self.len(1, await core.nodes(q))
            q = 'inet:ipv4=6.6.6.6 +(#hehe or #haha) -(#hehe and #haha) -#visi'
            self.len(1, await core.nodes(q))

            q = 'inet:ipv4=1.2.3.4 for $tag in $node.tags() { [test:str=$tag] }'  # noqa: E501
            nodes = await core.nodes(q)
            self.eq([n.ndef[0] for n in nodes], [*['test:str', 'inet:ipv4'] * 3])

            # non-runsafe iteration over a dictionary
            q = '''$dict=$lib.dict(key1=valu1, key2=valu2) [(test:str=test1) (test:str=test2)]
            for ($key, $valu) in $dict {
                [:hehe=$valu]
            }
            '''
            nodes = await core.nodes(q)
            # Each input node is yielded *twice* from the runtime
            self.len(4, nodes)
            self.eq({'test1', 'test2'}, {n.ndef[1] for n in nodes})
            for node in nodes:
                self.eq(node.get('hehe'), 'valu2')

            # None values don't yield anything
            q = '''$foo = $lib.dict()
            for $name in $foo.bar { [ test:str=$name ] }
            '''
            nodes = await core.nodes(q)
            self.len(0, nodes)

            # Even with a inbound node, zero loop iterations will not yield inbound nodes.
            q = '''test:str=test1 $foo = $lib.dict()
            for $name in $foo.bar { [ test:str=$name ] }
            '''
            nodes = await core.nodes(q)
            self.len(0, nodes)

    async def test_storm_whileloop(self):

        async with self.getTestCore() as core:
            q = '$x = 0 while $($x < 10) { $x=$($x+1) [test:int=$x]}'
            nodes = await core.nodes(q)
            self.len(10, nodes)

            # It should work the same with a continue at the end
            q = '$x = 0 while $($x < 10) { $x=$($x+1) [test:int=$x] continue}'
            nodes = await core.nodes(q)
            self.len(10, nodes)

            # Non Runtsafe test
            q = '''
            test:int=4 test:int=5 $x=$node.value()
            while 1 {
                $x=$($x-1)
                if $($x=$(2)) {continue}
                elif $($x=$(1)) {break}
                $lib.print($x)
            } '''
            msgs = await core.stormlist(q)
            prints = [m[1].get('mesg') for m in msgs if m[0] == 'print']
            self.eq(['3', '4', '3'], prints)

            # Non runtsafe yield test
            q = 'test:int=4 while $node.value() { [test:str=$node.value()] break}'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = '$x = 10 while 1 { $x=$($x-2) if $($x=$(4)) {continue} [test:int=$x]  if $($x<=0) {break} }'
            nodes = await core.nodes(q)
            self.eq([8, 6, 2, 0], [n.ndef[1] for n in nodes])

    async def test_storm_varmeth(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'blob': 'woot.com|1.2.3.4'}}
            nodes = await alist(core.eval('[ inet:dns:a=$blob.split("|") ]', opts=opts))

            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef[0], 'inet:dns:a')
                self.eq(node.ndef[1], ('woot.com', 0x01020304))

    async def test_storm_formpivot(self):

        async with self.getTestCore() as core:

            nodes = await alist(core.eval('[ inet:dns:a=(woot.com,1.2.3.4) ]'))

            # this tests getdst()
            nodes = await alist(core.eval('inet:fqdn=woot.com -> inet:dns:a'))
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef, ('inet:dns:a', ('woot.com', 0x01020304)))

            # this tests getsrc()
            nodes = await alist(core.eval('inet:fqdn=woot.com -> inet:dns:a -> inet:ipv4'))
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef, ('inet:ipv4', 0x01020304))

            with self.raises(s_exc.NoSuchPivot):
                nodes = await core.nodes('[ test:int=10 ] -> test:type')

            nodes = await core.nodes('[ test:str=woot :bar=(inet:fqdn, woot.com) ] -> inet:fqdn')
            self.eq(nodes[0].ndef, ('inet:fqdn', 'woot.com'))

    async def test_storm_expressions(self):
        async with self.getTestCore() as core:

            async def _test(q, ansr):
                nodes = await core.nodes(f'[test:int={q}]')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('test:int', ansr))

            await _test('$(42)', 42)
            await _test('$(2 + 4)', 6)
            await _test('$(4 - 2)', 2)
            await _test('$(4 -2)', 2)
            await _test('$(4- 2)', 2)
            await _test('$(4-2)', 2)
            await _test('$(2 * 4)', 8)
            await _test('$(1 + 2 * 4)', 9)
            await _test('$(1 + 2 * 4)', 9)
            await _test('$((1 + 2) * 4)', 12)
            await _test('$(1 < 1)', 0)
            await _test('$(1 <= 1)', 1)
            await _test('$(1 > 1)', 0)
            await _test('$(1 >= 1)', 1)
            await _test('$(1 >= 1 + 1)', 0)
            await _test('$(1 >= 1 + 1 * -2)', 1)
            await _test('$(1 - 1 - 1)', -1)
            await _test('$(4 / 2 / 2)', 1)
            await _test('$(1 / 2)', 0)
            await _test('$(1 != 1)', 0)
            await _test('$(2 != 1)', 1)
            await _test('$(2 = 1)', 0)
            await _test('$(2 = 2)', 1)
            await _test('$(2 = 2.0)', 1)
            await _test('$("foo" = "foo")', 1)
            await _test('$("foo" != "foo")', 0)
            await _test('$("foo2" = "foo")', 0)
            await _test('$("foo2" != "foo")', 1)
            await _test('$(0 and 1)', 0)
            await _test('$(1 and 1)', 1)
            await _test('$(1 or 1)', 1)
            await _test('$(0 or 0)', 0)
            await _test('$(1 or 0)', 1)
            await _test('$(not 0)', 1)
            await _test('$(not 1)', 0)
            await _test('$(1 or 0 and 0)', 1)  # and > or
            await _test('$(not 1 and 1)', 0)  # not > and
            await _test('$(not 1 > 1)', 1)  # cmp > not

            opts = {'vars': {'none': None}}
            # runtsafe
            nodes = await core.nodes('if $($none) {[test:str=yep]}', opts=opts)
            self.len(0, nodes)

            # non-runtsafe
            nodes = await core.nodes('[test:int=42] if $($none) {[test:str=$node]} else {spin}', opts=opts)
            self.len(0, nodes)

            nodes = await core.nodes('if $(not $none) {[test:str=yep]}', opts=opts)
            self.len(1, nodes)
            nodes = await core.nodes('[test:int=42] if $(not $none) {[test:str=yep]} else {spin}', opts=opts)
            self.len(2, nodes)

            # TODO:  implement move-along mechanism
            # await _test('$(1 / 0)', 0)

            # Test non-runtsafe
            q = '[test:type10=1 :intprop=24] $val=:intprop [test:int=$(1 + $val)]'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('test:int', 25))

            # Test invalid comparisons
            q = '$val=(1,2,3) [test:str=$("foo" >= $val)]'
            await self.asyncraises(s_exc.BadCast, core.nodes(q))

            q = '$val=(1,2,3) [test:str=$($val >= "foo")]'
            await self.asyncraises(s_exc.BadCast, core.nodes(q))

            q = '$val=42 [test:str=$(42<$val)]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'false'))

            q = '[test:str=foo :hehe=42] [test:str=$(not :hehe<42)]'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'true'))

    async def test_storm_filter_vars(self):
        '''
        Test variable filters (e.g. +$foo) and expression filters (e.g. +$(:hehe < 4))

        '''
        async with self.getTestCore() as core:

            # variable filter, non-runtsafe, true path
            q = '[test:type10=1 :strprop=1] $foo=:strprop +$foo'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            # variable filter, non-runtsafe, false path
            q = '[test:type10=1 :strprop=1] $foo=:strprop -$foo'
            nodes = await core.nodes(q)
            self.len(0, nodes)

            # variable filter, runtsafe, true path
            q = '[test:type10=1 :strprop=1] $foo=1 +$foo'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            # variable filter, runtsafe, false path
            q = '[test:type10=1 :strprop=1] $foo=$(0) -$foo'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            # expression filter, non-runtsafe, true path
            q = '[test:type10=2 :strprop=1] | spin | test:type10 +$(:strprop)'
            nodes = await core.nodes(q)
            self.len(2, nodes)

            # expression filter, non-runtsafe, false path
            q = '[test:type10=1 :strprop=1] -$(:strprop + 0)'
            nodes = await core.nodes(q)
            self.len(0, nodes)

            # expression filter, runtsafe, true path
            q = '[test:type10=1 :strprop=1] +$(1)'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            # expression filter, runtsafe, false path
            q = '[test:type10=1 :strprop=1] -$(0)'
            nodes = await core.nodes(q)
            self.len(1, nodes)

    async def test_storm_filter(self):
        async with self.getTestCore() as core:
            q = '[test:str=test +#test=(2018,2019)]'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = 'test:str=test $foo=test $bar=(2018,2019) +#$foo=$bar'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = 'test:str=test $foo=$node.value() $bar=(2018,2019) +#$foo=$bar'
            nodes = await core.nodes(q)
            self.len(1, nodes)

    async def test_storm_ifstmt(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[test:int=1 :int2=1] if :int2 {[+#woot]}')
            self.true(nodes[0].hasTag('woot'))
            nodes = await core.nodes('[test:int=1 :int2=0] if $(:int2) {[+#woot2]}')
            self.false(nodes[0].hasTag('woot2'))

            nodes = await core.nodes('[test:int=1 :int2=1] if $(:int2) {[+#woot3]} else {[+#nowoot3]}')
            self.true(nodes[0].hasTag('woot3'))
            self.false(nodes[0].hasTag('nowoot3'))

            nodes = await core.nodes('[test:int=2 :int2=0] if $(:int2) {[+#woot3]} else {[+#nowoot3]}')
            self.false(nodes[0].hasTag('woot3'))
            self.true(nodes[0].hasTag('nowoot3'))

            q = '[test:int=0 :int2=0] if $(:int2) {[+#woot41]} elif $($node.value()) {[+#woot42]}'
            nodes = await core.nodes(q)
            self.false(nodes[0].hasTag('woot41'))
            self.false(nodes[0].hasTag('woot42'))

            q = '[test:int=0 :int2=1] if $(:int2) {[+#woot51]} elif $($node.value()) {[+#woot52]}'
            nodes = await core.nodes(q)
            self.true(nodes[0].hasTag('woot51'))
            self.false(nodes[0].hasTag('woot52'))

            q = '[test:int=1 :int2=1] if $(:int2) {[+#woot61]} elif $($node.value()) {[+#woot62]}'
            nodes = await core.nodes(q)
            self.true(nodes[0].hasTag('woot61'))
            self.false(nodes[0].hasTag('woot62'))

            q = '[test:int=2 :int2=0] if $(:int2) {[+#woot71]} elif $($node.value()) {[+#woot72]}'
            nodes = await core.nodes(q)
            self.false(nodes[0].hasTag('woot71'))
            self.true(nodes[0].hasTag('woot72'))

            q = ('[test:int=0 :int2=0] if $(:int2) {[+#woot81]} '
                 'elif $($node.value()) {[+#woot82]} else {[+#woot83]}')
            nodes = await core.nodes(q)
            self.false(nodes[0].hasTag('woot81'))
            self.false(nodes[0].hasTag('woot82'))
            self.true(nodes[0].hasTag('woot83'))

            q = ('[test:int=0 :int2=42] if $(:int2) {[+#woot91]} '
                 'elif $($node.value()){[+#woot92]}else {[+#woot93]}')
            nodes = await core.nodes(q)
            self.true(nodes[0].hasTag('woot91'))
            self.false(nodes[0].hasTag('woot92'))
            self.false(nodes[0].hasTag('woot93'))

            q = ('[test:int=1 :int2=0] if $(:int2){[+#woota1]} '
                 'elif $($node.value()) {[+#woota2]} else {[+#woota3]}')
            nodes = await core.nodes(q)
            self.false(nodes[0].hasTag('woota1'))
            self.true(nodes[0].hasTag('woota2'))
            self.false(nodes[0].hasTag('woota3'))

            q = ('[test:int=1 :int2=1] if $(:int2) {[+#wootb1]} '
                 'elif $($node.value()) {[+#wootb2]} else{[+#wootb3]}')
            nodes = await core.nodes(q)
            self.true(nodes[0].hasTag('wootb1'))
            self.false(nodes[0].hasTag('wootb2'))
            self.false(nodes[0].hasTag('wootb3'))

            # Runtsafe condition with nodes
            nodes = await core.nodes('[test:str=yep2] if $(1) {[+#woot]}')
            self.true(nodes[0].hasTag('woot'))

            # Runtsafe condition with nodes, condition is false
            nodes = await core.nodes('[test:str=yep2] if $(0) {[+#woot2]}')
            self.false(nodes[0].hasTag('woot2'))

            # Completely runtsafe, condition is true
            q = '$foo=yawp if $foo {$bar=lol} else {$bar=rofl} [test:str=yep3 +#$bar]'
            nodes = await core.nodes(q)
            self.true(nodes[0].hasTag('lol'))
            self.false(nodes[0].hasTag('rofl'))

            # Completely runtsafe, condition is false
            q = '$foo=$(0) if $($foo) {$bar=lol} else {$bar=rofl} [test:str=yep4 +#$bar]'
            nodes = await core.nodes(q)
            self.false(nodes[0].hasTag('lol'))
            self.true(nodes[0].hasTag('rofl'))

            # Non-constant runtsafe
            q = '$vals=(1,2,3,4) for $i in $vals {if $($i="1") {[test:int=$i]}}'
            nodes = await core.nodes(q)
            self.len(1, nodes)

    async def test_storm_order(self):
        q = '''[test:str=foo :hehe=bar] $tvar=$lib.text() $tvar.add(1) $tvar.add(:hehe) $lib.print($tvar.str()) '''
        async with self.getTestCore() as core:
            mesgs = await core.stormlist(q)
            self.stormIsInPrint('1bar', mesgs)

    async def test_cortex_mirror(self):

        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')

            async with self.getTestCore(dirn=path00) as core00:
                await core00.nodes('[ inet:ipv4=1.2.3.4 ]')

            s_tools_backup.backup(path00, path01)

            async with self.getTestCore(dirn=path00) as core00:

                self.false(core00.conf.get('mirror'))

                await core00.nodes('[ inet:ipv4=1.2.3.4 ]')
                await core00.nodes('$lib.queue.add(hehe)')
                q = 'trigger.add node:add --form inet:fqdn --query {$lib.queue.get(hehe).put($node.repr())}'
                await core00.nodes(q)

                url = core00.getLocalUrl()

                core01conf = {'nexslog:en': False, 'mirror': url}
                with self.raises(s_exc.BadConfValu):
                    async with await s_cortex.Cortex.anit(dirn=path01, conf=core01conf) as core01:
                        self.fail('Should never get here.')

                core01conf = {'mirror': url}
                async with await s_cortex.Cortex.anit(dirn=path01, conf=core01conf) as core01:

                    await core00.nodes('[ inet:fqdn=vertex.link ]')
                    await core00.nodes('queue.add visi')

                    await core01.sync()

                    self.len(1, await core01.nodes('inet:fqdn=vertex.link'))

                    q = 'for ($offs, $fqdn) in $lib.queue.get(hehe).gets(wait=0) { inet:fqdn=$fqdn }'
                    self.len(2, await core01.nodes(q))

                    msgs = await core01.stormlist('queue.list')
                    self.stormIsInPrint('visi', msgs)

                    # Validate that mirrors can still write
                    await core01.nodes('queue.add visi2')
                    msgs = await core01.stormlist('queue.list')
                    self.stormIsInPrint('visi2', msgs)

                    await core01.nodes('[ inet:fqdn=www.vertex.link ]')
                    self.len(1, await core01.nodes('inet:fqdn=www.vertex.link'))

                    # Exceptions shall raise from the followerLoop
                    await self.asyncraises(s_exc.SynErr, core01.delView(core01.view.iden))

                await core00.nodes('[ inet:ipv4=5.5.5.5 ]')

                # test what happens when we go down and come up again...
                async with await s_cortex.Cortex.anit(dirn=path01, conf=core01conf) as core01:

                    await core00.nodes('[ inet:fqdn=woot.com ]')
                    await core01.sync()

                    q = 'for ($offs, $fqdn) in $lib.queue.get(hehe).gets(wait=0) { inet:fqdn=$fqdn }'
                    self.len(5, await core01.nodes(q))
                    self.len(1, await core01.nodes('inet:ipv4=5.5.5.5'))

            # now lets start up in the opposite order...
            async with await s_cortex.Cortex.anit(dirn=path01, conf=core01conf) as core01:

                async with await s_cortex.Cortex.anit(dirn=path00) as core00:

                    self.len(1, await core00.nodes('[ inet:ipv4=6.6.6.6 ]'))

                    await core01.sync()

                    self.len(1, await core01.nodes('inet:ipv4=6.6.6.6'))

                # what happens if *he* goes down and comes back up again?
                async with await s_cortex.Cortex.anit(dirn=path00) as core00:

                    await core00.nodes('[ inet:ipv4=7.7.7.7 ]')

                    await core01.sync()

                    self.len(1, (await core01.nodes('inet:ipv4=7.7.7.7')))

                # Try a write with the leader down
                with patch('synapse.lib.nexus.FOLLOWER_WRITE_WAIT_S', 2):
                    await self.asyncraises(s_exc.LinkErr, core01.nodes('[inet:ipv4=7.7.7.8]'))

                # Bring the leader back up and try again
                async with await s_cortex.Cortex.anit(dirn=path00) as core00:
                    self.len(1, await core01.nodes('[ inet:ipv4=7.7.7.8 ]'))

                # remove the mirrorness from the Cortex and ensure that we can
                # write to the Cortex. This will move the core01 ahead of
                # core00 & core01 can become the leader.
                await core01.promote()

                self.len(1, await core01.nodes('[inet:ipv4=9.9.9.8]'))
                new_url = core01.getLocalUrl()
                new_conf = {'mirror': new_url}
                async with await s_cortex.Cortex.anit(dirn=path00, conf=new_conf) as core00:
                    await core00.sync()
                    self.len(1, await core00.nodes('inet:ipv4=9.9.9.8'))

    async def test_norms(self):
        async with self.getTestCoreAndProxy() as (core, prox):
            # getPropNorm base tests
            norm, info = await core.getPropNorm('test:str', 1234)
            self.eq(norm, '1234')
            self.eq(info, {})

            norm, info = await core.getPropNorm('test:comp', ('1234', '1234'))
            self.eq(norm, (1234, '1234'))
            self.eq(info, {'subs': {'hehe': 1234, 'haha': '1234'}, 'adds': []})

            await self.asyncraises(s_exc.BadTypeValu, core.getPropNorm('test:int', 'newp'))
            await self.asyncraises(s_exc.NoSuchProp, core.getPropNorm('test:newp', 'newp'))

            norm, info = await prox.getPropNorm('test:str', 1234)
            self.eq(norm, '1234')
            self.eq(info, {})

            norm, info = await prox.getPropNorm('test:comp', ('1234', '1234'))
            self.eq(norm, (1234, '1234'))
            self.eq(info, {'subs': {'hehe': 1234, 'haha': '1234'}, 'adds': ()})

            await self.asyncraises(s_exc.BadTypeValu, prox.getPropNorm('test:int', 'newp'))
            await self.asyncraises(s_exc.NoSuchProp, prox.getPropNorm('test:newp', 'newp'))

            # getTypeNorm base tests
            norm, info = await core.getTypeNorm('test:str', 1234)
            self.eq(norm, '1234')
            self.eq(info, {})

            norm, info = await core.getTypeNorm('test:comp', ('1234', '1234'))
            self.eq(norm, (1234, '1234'))
            self.eq(info, {'subs': {'hehe': 1234, 'haha': '1234'}, 'adds': []})

            await self.asyncraises(s_exc.BadTypeValu, core.getTypeNorm('test:int', 'newp'))
            await self.asyncraises(s_exc.NoSuchType, core.getTypeNorm('test:newp', 'newp'))

            norm, info = await prox.getTypeNorm('test:str', 1234)
            self.eq(norm, '1234')
            self.eq(info, {})

            norm, info = await prox.getTypeNorm('test:comp', ('1234', '1234'))
            self.eq(norm, (1234, '1234'))
            self.eq(info, {'subs': {'hehe': 1234, 'haha': '1234'}, 'adds': ()})

            await self.asyncraises(s_exc.BadTypeValu, prox.getTypeNorm('test:int', 'newp'))
            await self.asyncraises(s_exc.NoSuchType, prox.getTypeNorm('test:newp', 'newp'))

            # getPropNorm can norm sub props
            norm, info = await core.getPropNorm('test:str:tick', '3001')
            self.eq(norm, 32535216000000)
            self.eq(info, {})
            # but getTypeNorm won't handle that
            await self.asyncraises(s_exc.NoSuchType, core.getTypeNorm('test:str:tick', '3001'))

            # getTypeNorm can norm types which aren't defined as forms/props
            norm, info = await core.getTypeNorm('test:lower', 'ASDF')
            self.eq(norm, 'asdf')
            # but getPropNorm won't handle that
            await self.asyncraises(s_exc.NoSuchProp, core.getPropNorm('test:lower', 'ASDF'))

    async def test_view_setlayers(self):

        async with self.getTestCore() as core:

            self.len(1, await core.nodes('[ test:str=deflayr ]'))

            newlayr = (await core.addLayer()).get('iden')
            deflayr = (await core.getLayerDef()).get('iden')

            vdef = {'layers': (deflayr,)}
            view = (await core.addView(vdef)).get('iden')

            opts = {'view': view}
            self.len(1, await core.nodes('test:str=deflayr', opts=opts))

            await core.setViewLayers((newlayr, deflayr), iden=view)

            self.len(1, await core.nodes('[ test:str=newlayr ]', opts=opts))
            self.len(0, await core.nodes('test:str=newlayr'))

    async def test_cortex_lockmemory(self):
        '''
        Verify that dedicated configuration setting impacts the layer
        '''
        conf = {'layers:lockmemory': False}
        async with self.getTestCore(conf=conf) as core:
            layr = core.view.layers[0]
            self.false(layr.lockmemory)

        conf = {'layers:lockmemory': True}
        async with self.getTestCore(conf=conf) as core:
            layr = core.view.layers[0]
            self.true(layr.lockmemory)

    async def test_cortex_storm_lib_dmon(self):
        async with self.getTestCoreAndProxy() as (core, prox):
            nodes = await core.nodes('''

                $lib.print(hi)

                $tx = $lib.queue.add(tx)
                $rx = $lib.queue.add(rx)

                $ddef = $lib.dmon.add(${

                    $rx = $lib.queue.get(tx)
                    $tx = $lib.queue.get(rx)

                    $ipv4 = nope
                    for ($offs, $ipv4) in $rx.gets(wait=1) {
                        [ inet:ipv4=$ipv4 ]
                        $rx.cull($offs)
                        $tx.put($ipv4)
                    }
                })

                $tx.put(1.2.3.4)

                for ($xoff, $xpv4) in $rx.gets(size=1, wait=1) { }

                $lib.print(xed)

                inet:ipv4=$xpv4

                $lib.dmon.del($ddef.iden)

                $lib.queue.del(tx)
                $lib.queue.del(rx)
            ''')
            self.len(1, nodes)
            self.len(0, await prox.getStormDmons())

            with self.raises(s_exc.NoSuchIden):
                await core.nodes('$lib.dmon.del(newp)')

    async def test_cortex_spawn_notsupported(self):

        async with self.getTestCore() as core:
            core.spawncorector = None
            with self.raises(s_exc.FeatureNotSupported):
                await core.getSpawnInfo()

    async def test_cortex_storm_dmon_ps(self):

        with self.getTestDir() as dirn:

            async with await s_cortex.Cortex.anit(dirn) as core:
                async with core.getLocalProxy() as prox:
                    await core.nodes('$lib.queue.add(visi)')
                    ddef = {'storm': '$lib.queue.get(visi).put(done) for $tick in $lib.time.ticker(1) {}'}
                    dmonpack = await prox.addStormDmon(ddef)
                    dmoniden = dmonpack.get('iden')
                    # Storm task pairs are promoted as tasks
                    retn = await prox.ps()
                    dmon_loop_tasks = [task for task in retn if task.get('name') == 'storm:dmon:loop']
                    dmon_main_tasks = [task for task in retn if task.get('name') == 'storm:dmon:main']
                    self.len(1, dmon_loop_tasks)
                    self.len(1, dmon_main_tasks)
                    self.eq(dmon_loop_tasks[0].get('info').get('iden'), dmoniden)
                    self.eq(dmon_main_tasks[0].get('info').get('iden'), dmoniden)
                    # We can kill the loop task and it will respawn
                    mpid = dmon_main_tasks[0].get('iden')
                    lpid = dmon_loop_tasks[0].get('iden')
                    self.true(await prox.kill(lpid))
                    await asyncio.sleep(0)
                    retn = await prox.ps()
                    dmon_loop_tasks = [task for task in retn if task.get('name') == 'storm:dmon:loop']
                    dmon_main_tasks = [task for task in retn if task.get('name') == 'storm:dmon:main']
                    self.len(1, dmon_loop_tasks)
                    self.len(1, dmon_main_tasks)
                    self.eq(dmon_main_tasks[0].get('iden'), mpid)
                    self.ne(dmon_loop_tasks[0].get('iden'), lpid)
                    # If we kill the main task, there is no respawn
                    self.true(await prox.kill(mpid))
                    await asyncio.sleep(0)
                    retn = await prox.ps()
                    dmon_loop_tasks = [task for task in retn if task.get('name') == 'storm:dmon:loop']
                    dmon_main_tasks = [task for task in retn if task.get('name') == 'storm:dmon:main']
                    self.len(0, dmon_loop_tasks)
                    self.len(0, dmon_main_tasks)

                    iden = 'XXX'
                    with self.raises(s_exc.NoSuchIden):
                        await prox.delStormDmon(iden)

                    with self.raises(s_exc.SchemaViolation):
                        await core.runStormDmon(iden, {})

                    with self.raises(s_exc.SchemaViolation):
                        await core.runStormDmon(iden, {'user': 'XXX'})

            async with await s_cortex.Cortex.anit(dirn) as core:
                # two entries means he ran twice ( once on add and once on restart )
                await core.nodes('$lib.queue.get(visi).gets(size=2)')

    async def test_cortex_storm_dmon_view(self):

        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                self.len(1, await core.nodes('[test:int=1]'))
                await core.nodes('$q=$lib.queue.add(dmon)')
                vdef2 = await core.view.fork()
                view2_iden = vdef2.get('iden')

                q = '''
                $lib.dmon.add(${
                    $q = $lib.queue.get(dmon)
                     for ($offs, $item) in $q.gets(size=3, wait=12)
                        {
                            [ test:int=$item ]
                            $lib.print("made {ndef}", ndef=$node.ndef())
                            $q.cull($offs)
                        }
                    }, name=viewdmon)
                '''
                # Iden is captured from the current snap
                await core.nodes(q, opts={'view': view2_iden})
                await asyncio.sleep(0)

                q = '''$q = $lib.queue.get(dmon) $q.puts((1, 3, 5))'''
                with self.getAsyncLoggerStream('synapse.lib.storm',
                                               "made ('test:int', 5)") as stream:
                    await core.nodes(q)
                    self.true(await stream.wait(6))

                nodes = await core.nodes('test:int', opts={'view': view2_iden})
                self.len(3, nodes)
                nodes = await core.nodes('test:int')
                self.len(1, nodes)

                # Kill the dmon and remove view2
                await core.stormdmons.stop()

                await core.delView(view2_iden)
                with self.raises(s_exc.NoSuchView):
                    await core.nodes('test:int', opts={'view': view2_iden})

            with self.getAsyncLoggerStream('synapse.lib.storm',
                                           'Dmon View is invalid. Exiting Dmon') as stream:
                async with self.getTestCore(dirn=dirn) as core:
                    self.true(await stream.wait(6))
                    msgs = await core.stormlist('dmon.list')
                    self.stormIsInPrint('fatal error: invalid view', msgs)

    async def test_cortex_storm_cmd_bads(self):

        async with self.getTestCore() as core:

            with self.raises(s_exc.BadCmdName):
                await core.setStormCmd({'name': ')(*&#$)*', 'storm': ''})

            with self.raises(s_exc.CantDelCmd):
                await core.delStormCmd('sleep')

    async def test_cortex_storm_lib_dmon_cmds(self):
        async with self.getTestCore() as core:
            await core.nodes('''
                $q = $lib.queue.add(visi)
                $lib.queue.add(boom)

                $lib.dmon.add(${
                    $lib.print('Starting wootdmon')
                    $lib.queue.get(visi).put(blah)
                    for ($offs, $item) in $lib.queue.get(boom).gets(wait=1) {
                        [ inet:ipv4=$item ]
                    }
                }, name=wootdmon)

                for ($offs, $item) in $q.gets(size=1) { $q.cull($offs) }
            ''')

            await asyncio.sleep(0)

            # dmon is now fully running
            msgs = await core.stormlist('dmon.list')
            self.stormIsInPrint('(wootdmon            ): running', msgs)

            dmon = list(core.stormdmons.dmons.values())[0]

            # make the dmon blow up
            await core.nodes('''
                $lib.queue.get(boom).put(hehe)
                for ($offs, $item) in $q.gets(size=1) { $q.cull($offs) }
            ''')

            self.true(await s_coro.event_wait(dmon.err_evnt, 6))

            msgs = await core.stormlist('dmon.list')
            self.stormIsInPrint('(wootdmon            ): error', msgs)

    async def test_cortex_storm_dmon_exit(self):

        async with self.getTestCore() as core:

            await core.nodes('''
                $q = $lib.queue.add(visi)
                $lib.user.vars.set(foo, $(10))

                $lib.dmon.add(${

                    $foo = $lib.user.vars.get(foo)

                    $lib.queue.get(visi).put(step)

                    if $( $foo = 20 ) {
                        for $tick in $lib.time.ticker(10) {
                            $lib.print(woot)
                        }
                    }

                    $lib.user.vars.set(foo, $(20))

                }, name=wootdmon)

            ''')
            # wait for him to exit once and loop...
            await core.nodes('for $x in $lib.queue.get(visi).gets(size=2) {}')
            await core.stormlist('for $x in $lib.queue.get(visi).gets(size=2) { $lib.print(hehe) }')

    async def test_cortex_ext_model(self):

        with self.getTestDir() as dirn:

            async with await s_cortex.Cortex.anit(dirn) as core:

                # blowup for bad names
                with self.raises(s_exc.BadPropDef):
                    await core.addFormProp('inet:ipv4', 'visi', ('int', {}), {})

                with self.raises(s_exc.BadPropDef):
                    await core.addUnivProp('woot', ('str', {'lower': True}), {})

                with self.raises(s_exc.NoSuchForm):
                    await core.addFormProp('inet:newp', '_visi', ('int', {}), {})

                await core.addFormProp('inet:ipv4', '_visi', ('int', {}), {})
                await core.addUnivProp('_woot', ('str', {'lower': True}), {})

                nodes = await core.nodes('[inet:ipv4=1.2.3.4 :_visi=30 ._woot=HEHE ]')
                self.len(1, nodes)

                self.len(1, await core.nodes('syn:prop:base="_visi"'))
                self.len(1, await core.nodes('syn:prop=inet:ipv4._woot'))
                self.len(1, await core.nodes('._woot=hehe'))

            async with await s_cortex.Cortex.anit(dirn) as core:

                nodes = await core.nodes('[inet:ipv4=5.5.5.5 :_visi=100]')
                self.len(1, nodes)

                nodes = await core.nodes('inet:ipv4:_visi>30')
                self.len(1, nodes)

                nodes = await core.nodes('._woot=hehe')
                self.len(1, nodes)

                with self.raises(s_exc.CantDelUniv):
                    await core.delUnivProp('_woot')

                await core.nodes('._woot [ -._woot ]')

                self.nn(core.model.prop('._woot'))
                self.nn(core.model.prop('inet:ipv4._woot'))
                self.nn(core.model.form('inet:ipv4').prop('._woot'))

                await core.delUnivProp('_woot')

                with self.raises(s_exc.NoSuchUniv):
                    await core.delUnivProp('_woot')

                self.none(core.model.prop('._woot'))
                self.none(core.model.prop('inet:ipv4._woot'))
                self.none(core.model.form('inet:ipv4').prop('._woot'))

                self.nn(core.model.prop('inet:ipv4:_visi'))
                self.nn(core.model.form('inet:ipv4').prop('_visi'))

                await core.nodes('inet:ipv4:_visi [ -:_visi ]')
                await core.delFormProp('inet:ipv4', '_visi')

                with self.raises(s_exc.NoSuchProp):
                    await core.delFormProp('inet:ipv4', '_visi')

                self.none(core.model.prop('inet:ipv4._visi'))
                self.none(core.model.form('inet:ipv4').prop('._visi'))

                # test the remote APIs
                async with core.getLocalProxy() as prox:

                    await prox.addUnivProp('_r100', ('str', {}), {})
                    self.len(1, await core.nodes('inet:ipv4=1.2.3.4 [ ._r100=woot ]'))

                    with self.raises(s_exc.CantDelUniv):
                        await prox.delUnivProp('_r100')

                    self.len(1, await core.nodes('._r100 [ -._r100 ]'))
                    await prox.delUnivProp('_r100')

                    await prox.addFormProp('inet:ipv4', '_blah', ('int', {}), {})
                    self.len(1, await core.nodes('inet:ipv4=1.2.3.4 [ :_blah=10 ]'))

                    self.len(1, await core.nodes('inet:ipv4=1.2.3.4 [ -:_blah ]'))
                    await prox.delFormProp('inet:ipv4', '_blah')

                    with self.raises(s_exc.NoSuchProp):
                        await prox.delFormProp('inet:ipv4', 'asn')

                    with self.raises(s_exc.NoSuchUniv):
                        await prox.delUnivProp('seen')

                    await prox.addTagProp('added', ('time', {}), {})

                    with self.raises(s_exc.NoSuchTagProp):
                        await core.nodes('inet:ipv4=1.2.3.4 [ +#foo.bar:time="2049" ]')

                    self.len(1, await core.nodes('inet:ipv4=1.2.3.4 [ +#foo.bar:added="2049" ]'))

                    await core.nodes('#foo.bar [ -#foo ]')
                    await prox.delTagProp('added')

    async def test_cortex_axon(self):
        async with self.getTestCore() as core:
            # By default, a cortex has a local Axon instance available
            await core.axready.wait()
            size, sha2 = await core.axon.put(b'asdfasdf')
            self.eq(size, 8)
            self.eq(s_common.ehex(sha2), '2413fb3709b05939f04cf2e92f7d0897fc2596f9ad0b8a9ea855c7bfebaae892')
        self.true(core.axon.isfini)
        self.false(core.axready.is_set())

        with self.getTestDir() as dirn:

            async with self.getTestAxon(dirn=dirn) as axon:
                aurl = axon.getLocalUrl()

            conf = {'axon': aurl}
            async with self.getTestCore(conf=conf) as core:
                async with self.getTestAxon(dirn=dirn) as axon:
                    self.true(await asyncio.wait_for(core.axready.wait(), 10))

                    # Use dyncalls, not direct object access.
                    asdfhash_h = '2413fb3709b05939f04cf2e92f7d0897fc2596f9ad0b8a9ea855c7bfebaae892'
                    size, sha2 = await core.callStorm('return( $lib.bytes.put($buf) )',
                                                      {'vars': {'buf': b'asdfasdf'}})
                    self.eq(size, 8)
                    self.eq(sha2, asdfhash_h)
                    self.true(await core.callStorm('return( $lib.bytes.has($hash) )',
                                                   {'vars': {'hash': asdfhash_h}}))

                unset = False
                for _ in range(20):
                    aset = core.axready.is_set()
                    if aset is False:
                        unset = True
                        break
                    await asyncio.sleep(0.1)
                self.true(unset)

                async with self.getTestAxon(dirn=dirn) as axon:
                    self.true(await asyncio.wait_for(core.axready.wait(), 10))
                    # ensure we can use the proxy
                    self.eq(await axon.metrics(),
                            await core.axon.metrics())

    async def test_cortex_delLayerView(self):
        async with self.getTestCore() as core:

            # Can't delete the default view
            await self.asyncraises(s_exc.SynErr, core.delView(core.view.iden))

            # Can't delete a layer in a view
            await self.asyncraises(s_exc.SynErr, core.delLayer(core.view.layers[0].iden))

            # Can't delete a nonexistent view
            await self.asyncraises(s_exc.NoSuchView, core.delView('XXX'))

            # Can't delete a nonexistent layer
            await self.asyncraises(s_exc.NoSuchLayer, core.delLayer('XXX'))

            # Fork the main view
            vdef2 = await core.view.fork()
            view2_iden = vdef2.get('iden')

            # Can't delete a view twice
            await core.delView(view2_iden)
            await self.asyncraises(s_exc.NoSuchView, core.delView(view2_iden))

    async def test_cortex_view_opts(self):
        '''
        Test that the view opts work
        '''
        async with self.getTestCore() as core:
            nodes = await alist(core.eval('[ test:int=11 ]'))
            self.len(1, nodes)
            viewiden = core.view.iden

            nodes = await alist(core.eval('test:int=11', opts={'view': viewiden}))
            self.len(1, nodes)

            await self.agenraises(s_exc.NoSuchView, core.eval('test:int=11', opts={'view': 'NOTAVIEW'}))

    async def test_cortex_getLayer(self):
        async with self.getTestCore() as core:
            layr = core.view.layers[0]
            self.eq(layr, core.getLayer())
            self.eq(layr, core.getLayer(core.iden))
            self.none(core.getLayer('XXX'))

            view = core.view
            self.eq(view, core.getView())
            self.eq(view, core.getView(view.iden))
            self.eq(view, core.getView(core.iden))
            self.none(core.getView('xxx'))

    async def test_cortex_cronjob_perms(self):
        async with self.getTestCore() as realcore:
            async with realcore.getLocalProxy() as core:
                fred = await core.addUser('fred')
                await core.setUserPasswd(fred['iden'], 'secret')
                cdef = {'storm': '[test:str=foo]', 'reqs': {'dayofmonth': 1},
                        'incunit': None, 'incvals': None}
                adef = await core.addCronJob(cdef)
                iden = adef.get('iden')

            async with realcore.getLocalProxy(user='fred') as core:
                # Rando user can't make cron jobs
                cdef = {'storm': '[test:int=1]', 'reqs': {'month': 1},
                        'incunit': None, 'incvals': None}
                await self.asyncraises(s_exc.AuthDeny, core.addCronJob(cdef))

                # Rando user can't mod cron jobs
                await self.asyncraises(s_exc.AuthDeny, core.updateCronJob(iden, '[test:str=bar]'))

                # Rando user doesn't see any cron jobs
                self.len(0, await core.listCronJobs())

                # Rando user can't delete cron jobs
                await self.asyncraises(s_exc.AuthDeny, core.delCronJob(iden))

                # Rando user can't enable/disable cron jobs
                await self.asyncraises(s_exc.AuthDeny, core.enableCronJob(iden))
                await self.asyncraises(s_exc.AuthDeny, core.disableCronJob(iden))

    async def test_cortex_migrationmode(self):
        async with self.getTestCore() as core:
            async with core.getLocalProxy(user='root') as prox:

                await prox.addUser('fred', passwd='secret')

                self.true(core.agenda.enabled)
                self.true(core.trigson)
                async with await core.snap() as snap:
                    self.true(snap.trigson)

                # add triggers
                # node:add case
                tdef = {'cond': 'node:add', 'form': 'test:str', 'storm': '[ test:int=1 ]'}
                await core.view.addTrigger(tdef)
                await core.nodes('[ test:str=foo ]')
                self.len(1, await core.nodes('test:int'))

                # node:del case
                tdef = {'cond': 'node:del', 'storm': '[ test:int=2 ]', 'form': 'test:str'}
                await core.view.addTrigger(tdef)
                await core.nodes('test:str=foo | delnode')
                self.len(2, await core.nodes('test:int'))

                # tag:add case
                tdef = {'cond': 'tag:add', 'storm': '[ test:int=3 ]', 'tag': 'footag'}
                await core.view.addTrigger(tdef)
                await core.nodes('[ test:str=foo +#footag ]')
                self.len(3, await core.nodes('test:int'))

                # enable migration mode
                await prox.enableMigrationMode()

                self.false(core.agenda.enabled)
                self.false(core.trigson)
                async with await core.snap() as snap:
                    self.false(snap.trigson)

                # check that triggers don't fire
                await core.nodes('test:int | delnode')
                await core.nodes('[test:str=foo] [+#footag] | delnode')
                self.len(0, await core.nodes('test:int'))

                # disable migration mode
                await prox.disableMigrationMode()

                self.true(core.agenda.enabled)
                self.true(core.trigson)
                async with await core.snap() as snap:
                    self.true(snap.trigson)

                # check that triggers fire
                await core.nodes('[test:str=foo] [+#footag] | delnode')
                self.len(3, await core.nodes('test:int'))

            async with core.getLocalProxy(user='fred') as prox:
                # non-admin cannot enable/disable migration mode
                await self.asyncraises(s_exc.AuthDeny, prox.enableMigrationMode())
                await self.asyncraises(s_exc.AuthDeny, prox.disableMigrationMode())

    async def test_cortex_watch(self):

        async with self.getTestCore() as core:

            async with core.getLocalProxy() as prox:

                async def nodes():
                    await asyncio.sleep(0.1)    # due to telepath proxy causing task switch
                    await core.nodes('[ test:int=10 +#foo.bar +#baz.faz ]')
                    await core.nodes('test:int=10 [ -#foo.bar -#baz.faz ]')

                task = core.schedCoro(nodes())

                data = []
                async for mesg in prox.watch({'tags': ['foo.bar', 'baz.*']}):
                    data.append(mesg)
                    if len(data) == 4:
                        break

                await asyncio.wait_for(task, timeout=1)

                self.eq(data[0][0], 'tag:add')
                self.eq(data[0][1]['tag'], 'foo.bar')

                self.eq(data[1][0], 'tag:add')
                self.eq(data[1][1]['tag'], 'baz.faz')

                self.eq(data[2][0], 'tag:del')
                self.eq(data[2][1]['tag'], 'foo.bar')

                self.eq(data[3][0], 'tag:del')
                self.eq(data[3][1]['tag'], 'baz.faz')

    async def test_stormpkg_sad(self):
        base_pkg = {
            'name': 'boom',
            'desc': 'The boom Module',
            'version': (0, 0, 1),
            'modules': [
                {
                    'name': 'boom.mod',
                    'storm': '''
                    function f(a) {return ($a)}
                    ''',
                },
            ],
            'commands': [
                {
                    'name': 'boom.cmd',
                    'storm': '''
                    $boomlib = $lib.import(boom.mod)
                    $retn = $boomlib.f($arg)
                    ''',
                },
            ],
        }
        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                # await core.addStormPkg(base_pkg)
                pkg = copy.deepcopy(base_pkg)
                pkg.pop('name')
                with self.raises(s_exc.SchemaViolation) as cm:
                    await core.addStormPkg(pkg)
                self.eq(cm.exception.errinfo.get('mesg'),
                        "data must contain ['name', 'version'] properties")

                pkg = copy.deepcopy(base_pkg)
                pkg.pop('version')
                with self.raises(s_exc.SchemaViolation) as cm:
                    await core.addStormPkg(pkg)
                self.eq(cm.exception.errinfo.get('mesg'),
                        "data must contain ['name', 'version'] properties")

                pkg = copy.deepcopy(base_pkg)
                pkg['modules'][0].pop('name')
                with self.raises(s_exc.SchemaViolation) as cm:
                    await core.addStormPkg(pkg)
                self.eq(cm.exception.errinfo.get('mesg'),
                        "data must contain ['name', 'storm'] properties")

                pkg = copy.deepcopy(base_pkg)
                pkg.pop('version')
                await core.pkghive.set('boom_pkg', pkg)

            with self.getAsyncLoggerStream('synapse.cortex',
                                           'Error loading pkg') as stream:
                async with self.getTestCore(dirn=dirn) as core:
                    self.true(await stream.wait(6))

    async def test_cortex_view_persistence(self):
        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                view = core.view
                NKIDS = 20
                for _ in range(NKIDS):
                    await view.fork()

                self.len(NKIDS + 1, core.layers)

            async with self.getTestCore(dirn=dirn) as core:
                self.len(NKIDS + 1, core.layers)
                for view in core.views.values():
                    if view == core.view:
                        continue
                    self.eq(core.view, view.parent)

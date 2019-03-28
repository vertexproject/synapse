import time
import asyncio


import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.coro as s_coro
import synapse.lib.node as s_node
import synapse.lib.msgpack as s_msgpack

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class CortexTest(s_t_utils.SynTest):

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

    async def test_cortex_prop_pivot(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                await snap.addNode('inet:dns:a', ('woot.com', '1.2.3.4'))

            nodes = [n.pack() async for n in core.eval('inet:dns:a :ipv4 -> *')]
            self.len(1, nodes)
            self.eq(nodes[0][0], ('inet:ipv4', 0x01020304))

            # 3: init + inet:ipv4 + fini
            await self.agenlen(3, core.streamstorm('inet:dns:a :ipv4 -> *'))

    async def test_cortex_of_the_future(self):

        # test "future/ongoing" time stamp.
        async with self.getTestCore() as core:

            async with await core.snap() as snap:

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

    @s_glob.synchelp
    async def test_feed_conf(self):

        async with self.getTestCryo() as cryo:

            host, port = await cryo.dmon.listen('tcp://127.0.0.1:0/')

            cryo.insecure = True

            tname = 'tank:blahblah'
            #host, port = dst_dmon.addr
            tank_addr = f'tcp://{host}:{port}/*/{tname}'

            recs = ['a', 'b', 'c']

            conf = {
                'feeds': [
                    {'type': 'com.test.record',
                     'cryotank': tank_addr,
                     'size': 1,
                     }
                ],
            }

            # initialize the tank and get his iden
            async with await s_telepath.openurl(tank_addr) as tank:
                iden = await tank.iden()

            # Spin up a source core configured to eat data from the cryotank
            with self.getTestDir() as dirn:

                async with self.getTestCore(dirn=dirn, conf=conf) as core:

                    waiter = core.waiter(3, 'core:feed:loop')

                    async with await s_telepath.openurl(tank_addr) as tank:
                        await tank.puts(recs)
                    # self.true(evt.wait(3))
                    self.true(await waiter.wait(4))

                    offs = await core.view.layers[0].getOffset(iden)
                    self.eq(offs, 3)
                    await self.agenlen(3, core.storm('test:str'))

    async def test_cortex_coreinfo(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            coreinfo = await prox.getCoreInfo()

            for field in ('version', 'modeldef', 'stormcmds'):
                self.isin(field, coreinfo)

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

    async def test_storm_graph(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            await prox.addNode('inet:dns:a', ('woot.com', '1.2.3.4'))

            opts = {'graph': True}
            nodes = [n async for n in prox.eval('inet:dns:a', opts=opts)]

            self.len(5, nodes)

            for node in nodes:
                if node[0][0] == 'inet:dns:a':
                    edges = node[1]['path']['edges']
                    idens = list(sorted(e[0] for e in edges))
                    self.eq(idens, ('20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f',
                                    'd7fb3ae625e295c9279c034f5d91a7ad9132c79a9c2b16eecffc8d1609d75849'))

    async def test_splice_cryo(self):

        async with self.getTestCryo() as cryo:

            tank_addr = cryo.getLocalUrl(share='cryotank/blahblah')

            # Spin up a source core configured to send splices to dst core
            with self.getTestDir() as dirn:
                conf = {
                    'splice:cryotank': tank_addr,
                }
                async with self.getTestCore(dirn=dirn, conf=conf) as src_core:

                    waiter = src_core.waiter(2, 'core:splice:cryotank:sent')
                    # Form a node and make sure that it exists
                    async with await src_core.snap() as snap:
                        await snap.addNode('test:str', 'teehee')
                        self.nn(await snap.getNodeByNdef(('test:str', 'teehee')))

                    await waiter.wait(timeout=10)
                    await src_core.fini()
                    await src_core.waitfini()

            # Now that the src core is closed, make sure that the splice exists in the tank
            tank = cryo.tanks.get('blahblah')
            slices = [x async for x in tank.slice(0, size=1000)]
            # # TestModule creates one node and 3 splices

            self.len(3 + 2, slices)
            slices = slices[3:]
            data = slices[0]
            self.isinstance(data[1], tuple)
            self.len(2, data[1])
            self.eq(data[1][0], 'node:add')
            self.eq(data[1][1].get('ndef'), ('test:str', 'teehee'))
            self.nn(data[1][1].get('user'))
            self.ge(data[1][1].get('time'), 0)

            data = slices[1]
            self.isinstance(data[1], tuple)
            self.len(2, data[1])
            self.eq(data[1][0], 'prop:set')
            self.eq(data[1][1].get('ndef'), ('test:str', 'teehee'))
            self.eq(data[1][1].get('prop'), '.created')
            self.ge(data[1][1].get('valu'), 0)
            self.none(data[1][1].get('oldv'))
            self.nn(data[1][1].get('user'))
            self.ge(data[1][1].get('time'), 0)

    async def test_splice_sync(self):

        async with self.getTestCore() as core0:
            evt = asyncio.Event()

            def onAdd(node):
                evt.set()

            core0.model.form('test:str').onAdd(onAdd)

            # Spin up a source core configured to send splices to dst core
            conf = {
                'splice:sync': core0.getLocalUrl(),
            }
            async with self.getTestCore(conf=conf) as core1:

                # Form a node and make sure that it exists
                waiter = core1.waiter(2, 'core:splice:sync:sent')
                async with await core1.snap() as snap:
                    await snap.addNode('test:str', 'teehee')
                    self.nn(await snap.getNodeByNdef(('test:str', 'teehee')))

                await waiter.wait(timeout=5)

            self.true(await s_coro.event_wait(evt, timeout=3))

            # Now that the src core is closed, make sure that the node exists
            # in the dst core without creating it
            async with await core0.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'teehee'))
                self.eq(node.ndef, ('test:str', 'teehee'))

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

    async def test_indxchop(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                valu = 'a' * 257
                await snap.addNode('test:str', valu)

                nodes = await alist(snap.getNodesBy('test:str', 'aa', cmpr='^='))
                self.len(1, nodes)

    async def test_cell(self):

        data = ('foo', 'bar', 'baz')

        async with self.getTestCoreAndProxy() as (core, proxy):

            nodes = ((('inet:user', 'visi'), {}), )

            nodes = await alist(proxy.addNodes(nodes))
            self.len(1, nodes)

            nodes = await alist(proxy.getNodesBy('inet:user', 'visi'))
            self.len(1, nodes)
            self.eq('visi', nodes[0][0][1])

            node = await proxy.addNode('test:str', 'foo')

            pack = await proxy.addNodeTag(node[1].get('iden'), '#foo.bar')
            self.eq(pack[1]['tags'].get('foo.bar'), (None, None))

            pack = await proxy.setNodeProp(node[1].get('iden'), 'tick', '2015')
            self.eq(pack[1]['props'].get('tick'), 1420070400000)

            self.len(1, await alist(proxy.eval('test:str#foo.bar')))
            self.len(1, await alist(proxy.eval('test:str:tick=2015')))

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

    async def test_stormcmd(self):

        async with self.getTestCoreAndProxy() as (realcore, core):

            msgs = await alist(core.storm('|help'))
            self.printed(msgs, 'help: List available commands and a brief description for each.')

            msgs = await alist(core.storm('help'))
            self.printed(msgs, 'help: List available commands and a brief description for each.')

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
            self.printed(msgs, 'usage: limit [-h] count')
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

                self.eq(args_hit, [node, '??'])

                args_hit = None
                core.model.prop('inet:ipv4:loc').onDel(test_cb)

                await node.pop('loc')
                self.eq(args_hit, [node, 'us.va'])

                self.none(node.get('loc'))

            async with await core.snap() as snap:
                node = await snap.addNode('inet:ipv4', '1.2.3.4')
                self.none(node.get('loc'))

    async def test_tags(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                await snap.addNode('test:str', 'newp')

                node = await snap.addNode('test:str', 'one')
                await node.addTag('foo.bar', ('2016', '2017'))

                self.eq((1451606400000, 1483228800000), node.getTag('foo.bar', ('2016', '2017')))

                node1 = await snap.addNode('test:comp', (10, 'hehe'))
                await node1.addTag('foo.bar')

                self.nn(await snap.getNodeByNdef(('syn:tag', 'foo')))
                self.nn(await snap.getNodeByNdef(('syn:tag', 'foo.bar')))

            async with await core.snap() as snap:

                node = await snap.getNodeByNdef(('test:str', 'one'))

                self.true(node.hasTag('foo'))
                self.true(node.hasTag('foo.bar'))

                await self.agenraises(s_exc.NoSuchForm, snap.getNodesBy('noway#foo.bar'))

                self.len(2, await alist(snap.getNodesBy('#foo.bar')))
                self.len(1, await alist(snap.getNodesBy('test:str#foo.bar')))

            async with await core.snap() as snap:

                node = await snap.addNode('test:str', 'one')

                await node.delTag('foo')

                self.false(node.hasTag('foo'))
                self.false(node.hasTag('foo.bar'))

            async with await core.snap() as snap:

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

    async def test_base_types2(self):

        async with self.getTestCore() as core:

            # Test some default values
            async with await core.snap() as snap:

                node = await snap.addNode('test:type10', 'one')
                self.nn(node.get('.created'))
                created = node.reprs().get('.created')

                self.eq(node.get('intprop'), 20)
                self.eq(node.get('locprop'), '??')
                self.eq(node.get('strprop'), 'asdf')

                self.true(s_common.isguid(node.get('guidprop')))

            # open a new snap, commiting the previous snap and do some lifts by univ prop
            async with await core.snap() as snap:

                nodes = await alist(snap.getNodesBy('.created', ))
                self.len(1 + 1, nodes)

                nodes = await alist(snap.getNodesBy('.created', node.get('.created')))
                self.len(1, nodes)

                nodes = await alist(snap.getNodesBy('.created', '2010', cmpr='>='))
                self.len(1 + 1, nodes)

                nodes = await alist(snap.getNodesBy('.created', ('2010', '3001'), cmpr='*range='))
                self.len(1 + 1, nodes)

                nodes = await alist(snap.getNodesBy('.created', ('2010', '?'), cmpr='*range='))
                self.len(1 + 1, nodes)

                await self.agenlen(2, core.eval('.created'))
                await self.agenlen(1, core.eval(f'.created="{created}"'))
                await self.agenlen(2, core.eval('.created>2010'))
                await self.agenlen(0, core.eval('.created<2010'))
                # The year the monolith returns
                await self.agenlen(2, core.eval('.created*range=(2010, 3001)'))
                await self.agenlen(2, core.eval('.created*range=("2010", "?")'))

            # The .created time is ro
            await self.asyncraises(s_exc.ReadOnlyProp, core.eval(f'.created="{created}" [.created=3001]').list())

            # Open another snap to test some more default value behavior
            async with await core.snap() as snap:
                # Grab an updated reference to the first node
                node = (await alist(snap.getNodesBy('test:type10', 'one')))[0]
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
                nodes = await alist(snap.getNodesBy('test:str:tick'))
                self.len(3, nodes)

            async with await core.snap() as snap:

                node = await snap.addNode('test:type10', 'one')
                self.eq(node.get('intprop'), 21)

                self.nn(node.get('.created'))

                nodes = await alist(snap.getNodesBy('test:str', 'too', cmpr='^='))
                self.len(2, nodes)

                # test loc prop prefix based lookup
                nodes = await alist(snap.getNodesBy('test:type10:locprop', 'us.va', cmpr='^='))

                self.len(1, nodes)
                self.eq(nodes[0].ndef[1], 'one')

                nodes = await alist(snap.getNodesBy('test:comp', (33, 'thirty three')))

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

            # Seed new nodes via nodedesf
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
            await self.agenraises(s_exc.BadSyntax, core.eval('test:str +#test*near=newp'))
            await self.agenraises(s_exc.NoSuchCmpr, core.eval('test:str +test:str:tick*near=newp'))
            await self.agenraises(s_exc.BadSyntax, core.eval(' | | '))
            await self.agenraises(s_exc.BadSyntax, core.eval('[-test:str]'))
            # Scrape is not a default behavior
            await self.agenraises(s_exc.BadSyntax, core.eval('pennywise@vertex.link'))

            await self.agenlen(2, core.eval(('[ test:str=foo test:str=bar ]')))

            opts = {'vars': {'foo': 'bar'}}

            async for node in core.eval('test:str=$foo', opts=opts):
                self.eq('bar', node.ndef[1])

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
            self.len(0, [mesg for mesg in mesgs if mesg[0] == 'init'])
            self.len(1, [mesg for mesg in mesgs if mesg[0] == 'fini'])
            mesgs = [mesg for mesg in mesgs if mesg[0] == 'err']
            self.len(1, mesgs)
            enfo = mesgs[0][1]
            self.eq(enfo[0], 'BadSyntax')

    async def test_feed_splice(self):

        iden = s_common.guid()

        async with self.getTestCore() as core:

            offs = await core.getFeedOffs(iden)
            self.eq(0, offs)

            mesg = ('node:add', {'ndef': ('test:str', 'foo')})
            offs = await core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            self.eq(1, offs)

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'foo'))
                self.nn(node)

            mesg = ('prop:set', {'ndef': ('test:str', 'foo'), 'prop': 'tick', 'valu': 200})
            offs = await core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'foo'))
                self.eq(200, node.get('tick'))

            mesg = ('prop:del', {'ndef': ('test:str', 'foo'), 'prop': 'tick'})
            offs = await core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'foo'))
                self.none(node.get('tick'))

            mesg = ('tag:add', {'ndef': ('test:str', 'foo'), 'tag': 'bar', 'valu': (200, 300)})
            offs = await core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'foo'))
                self.eq((200, 300), node.getTag('bar'))

            mesg = ('tag:del', {'ndef': ('test:str', 'foo'), 'tag': 'bar'})
            offs = await core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('test:str', 'foo'))
                self.none(node.getTag('bar'))

    async def test_splice_generation(self):

        async with self.getTestCore() as core:

            await alist(core.eval('[test:str=hello]'))
            await alist(core.eval('test:str=hello [:tick="2001"]'))
            await alist(core.eval('test:str=hello [:tick="2002"]'))
            await alist(core.eval('test:str [+#foo.bar]'))
            await alist(core.eval('test:str [+#foo.bar=(2000,2002)]'))
            await alist(core.eval('test:str [+#foo.bar=(2000,20020601)]'))
            await alist(core.eval('test:str [-#foo]'))
            await alist(core.eval('test:str [-:tick]'))
            await alist(core.eval('test:str | delnode --force'))

            _splices = await alist(core.view.layers[0].splices(0, 10000))
            splices = []
            # strip out user and time
            for splice in _splices:
                splice[1].pop('user', None)
                splice[1].pop('time', None)
                splice[1].pop('prov', None)
                splices.append(splice)

            # Ensure the splices are unique
            self.len(len(splices), {s_msgpack.en(s) for s in splices})

            # Check to ensure a few expected splices exist
            mesg = ('node:add', {'ndef': ('test:str', 'hello')})
            self.isin(mesg, splices)

            mesg = ('prop:set', {'ndef': ('test:str', 'hello'), 'prop': 'tick', 'valu': 978307200000})
            self.isin(mesg, splices)

            mesg = ('prop:set',
                    {'ndef': ('test:str', 'hello'), 'prop': 'tick', 'valu': 1009843200000, 'oldv': 978307200000})
            self.isin(mesg, splices)

            mesg = ('tag:add', {'ndef': ('test:str', 'hello'), 'tag': 'foo', 'valu': (None, None)})
            self.isin(mesg, splices)

            mesg = ('tag:add', {'ndef': ('test:str', 'hello'), 'tag': 'foo.bar', 'valu': (None, None)})
            self.isin(mesg, splices)

            mesg = ('tag:add', {'ndef': ('test:str', 'hello'), 'tag': 'foo.bar', 'valu': (946684800000, 1009843200000)})
            self.isin(mesg, splices)

            mesg = ('tag:add', {'ndef': ('test:str', 'hello'), 'tag': 'foo.bar', 'valu': (946684800000, 1022889600000)})
            self.isin(mesg, splices)

            mesg = ('tag:del', {'ndef': ('test:str', 'hello'), 'tag': 'foo', 'valu': (None, None)})
            self.isin(mesg, splices)

            mesg = ('prop:del', {'ndef': ('test:str', 'hello'), 'prop': 'tick', 'valu': 1009843200000})
            self.isin(mesg, splices)

            mesg = ('node:del', {'ndef': ('test:str', 'hello')})
            self.isin(mesg, splices)

    async def test_strict(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                node = await snap.addNode('test:str', 'foo')

                await self.asyncraises(s_exc.NoSuchProp, node.set('newpnewp', 10))
                await self.asyncraises(s_exc.BadPropValu, node.set('tick', (20, 30)))

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

                tagnode = await snap.getNodeByNdef(('syn:tag', 'hehe'))
                await self.asyncraises(s_exc.CantDelNode, tagnode.delete())

                buid = tstr.buid

                await tstr.delete()

                self.true(data.get('prop:del'))
                self.true(data.get('node:del'))

                # confirm that the snap cache is clear
                self.none(await snap.getNodeByBuid(tstr.buid))
                self.none(await snap.getNodeByNdef(('test:str', 'baz')))

            async with await core.snap() as snap:

                # test that secondary props are gone at the row level...
                prop = snap.model.prop('test:str:tick')
                lops = prop.getLiftOps(100)
                await self.agenlen(0, snap.getLiftRows(lops))

                # test that primary prop is gone at the row level...
                prop = snap.model.prop('test:str')
                lops = prop.getLiftOps('baz')
                await self.agenlen(0, snap.getLiftRows(lops))

                # check that buid rows are gone...
                self.eq(None, await snap.getNodeByBuid(buid))

                # final top level API check
                self.none(await snap.getNodeByNdef(('test:str', 'baz')))

    async def test_cortex_delnode_perms(self):

        async with self.getTestCoreAndProxy() as (realcore, core):

            await core.addAuthUser('visi')
            await core.setUserPasswd('visi', 'secret')

            await core.addAuthRule('visi', (True, ('node:add',)))
            await core.addAuthRule('visi', (True, ('prop:set',)))
            await core.addAuthRule('visi', (True, ('tag:add',)))

            uconf = {'user': 'visi', 'passwd': 'secret'}

            async with realcore.getLocalProxy(user='visi') as asvisi:

                await alist(asvisi.eval('[ test:cycle0=foo :cycle1=bar ]'))
                await alist(asvisi.eval('[ test:cycle1=bar :cycle0=foo ]'))

                await alist(asvisi.eval('[ test:str=foo +#lol ]'))

                # no perms and not elevated...
                await self.agenraises(s_exc.AuthDeny, asvisi.eval('test:str=foo | delnode'))

                rule = (True, ('node:del',))
                await core.addAuthRule('visi', rule)

                # should still deny because node has tag we can't delete
                await self.agenraises(s_exc.AuthDeny, asvisi.eval('test:str=foo | delnode'))

                rule = (True, ('tag:del', 'lol'))
                await core.addAuthRule('visi', rule)

                await self.agenlen(0, asvisi.eval('test:str=foo | delnode'))

                await self.agenraises(s_exc.CantDelNode, asvisi.eval('test:cycle0=foo | delnode'))
                await self.agenraises(s_exc.AuthDeny, asvisi.eval('test:cycle0=foo | delnode --force'))

                await core.setAuthAdmin('visi', True)

                await self.agenlen(0, asvisi.eval('test:cycle0=foo | delnode --force'))

    async def test_cortex_cell_splices(self):

        async with self.getTestCore() as core:

            async with core.getLocalProxy() as prox:
                # TestModule creates one node and 3 splices
                await self.agenlen(3, prox.splices(0, 1000))

                await alist(prox.eval('[ test:str=foo ]'))

                self.ge(len(await alist(prox.splices(0, 1000))), 3)

    async def test_pivot_inout(self):

        async def getPackNodes(core, query):
            nodes = sorted([n.pack() async for n in core.eval(query)])
            return nodes

        async with self.getTestCore() as core:

            # seed a node for pivoting
            await alist(core.eval('[ test:pivcomp=(foo,bar) :tick=2018 ]'))
            await alist(core.eval('[ edge:refs=((ou:org, "*"), (test:pivcomp,(foo,bar))) ]'))

            self.len(1, await core.eval('ou:org -> edge:refs:n1').list())

            q = 'test:pivcomp=(foo,bar) -> test:pivtarg'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:pivtarg', 'foo'))

            # Regression test:  bug in implicit form pivot where absence of foreign key in source node was treated like
            # a match-any
            await alist(core.eval('[ test:int=42 ]'))
            q = 'test:pivcomp -> test:int'
            nodes = await getPackNodes(core, q)
            self.len(0, nodes)

            # Multiple props of source form have type of destination form:  pivot through all the matching props.
            await alist(core.eval('[ test:pivcomp=(xxx,yyy) :width=42 ]'))
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
            await alist(core.eval('[ edge:has=((test:str, foobar), (test:str, foo)) ]'))

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

            # Setup a propvalu pivot where the secondary prop may fail to norm
            # to the destination prop for some of the inbound nodes.
            await alist(core.eval('[ test:comp=(127,newp) ] [test:comp=(127,127)]'))
            mesgs = await alist(core.streamstorm('test:comp :haha -> test:int'))

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
                node = await snap.addNode('test:int', 10)
                node = await snap.addNode('test:int', 25)
                node = await snap.addNode('test:type10', 'test', {'intprop': 25})
            mesgs = await alist(core.streamstorm('test:int*in=(10, 25) -> test:type10:intprop'))

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

    async def test_cortex_storm_set_univ(self):

        async with self.getTestCore() as core:

            await alist(core.eval('[ test:str=woot .seen=(2014,2015) ]'))

            async with await core.snap() as snap:

                node = await snap.getNodeByNdef(('test:str', 'woot'))
                self.eq(node.get('.seen'), (1388534400000, 1420070400000))

    async def test_cortex_storm_set_tag(self):

        async with self.getTestCore() as core:

            tick0 = core.model.type('time').norm('2014')[0]
            tick1 = core.model.type('time').norm('2015')[0]
            tick2 = core.model.type('time').norm('2016')[0]

            await self.agenlen(1, core.eval('[ test:str=hehe +#foo=(2014,2016) ]'))
            await self.agenlen(1, core.eval('[ test:str=haha +#bar=2015 ]'))

            async with await core.snap() as snap:

                node = await snap.getNodeByNdef(('test:str', 'hehe'))
                self.eq(node.getTag('foo'), (tick0, tick2))

                node = await snap.getNodeByNdef(('test:str', 'haha'))
                self.eq(node.getTag('bar'), (tick1, tick1 + 1))

            await self.agenlen(1, core.eval('[ test:str=haha +#bar=2016 ]'))

            async with await core.snap() as snap:

                node = await snap.getNodeByNdef(('test:str', 'haha'))
                self.eq(node.getTag('bar'), (tick1, tick2 + 1))

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

            await self.agenlen(1, core.eval('test:pivcomp=(hehe,haha) $ticktock=#foo -> test:pivtarg +.seen@=$ticktock'))

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

    async def test_cortex_storm_filt_ival(self):

        async with self.getTestCore() as core:

            await self.agenlen(1, core.eval('[ test:str=woot +#foo=(2015,2018) +#bar .seen=(2014,2016) ]'))

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

            await self.agenlen(1, core.eval('[ inet:dns:a=(woot.com,1.2.3.4) .seen=(2015,2016) ]'))
            await self.agenlen(1, core.eval('[ inet:fqdn=woot.com +#bad=(2015,2016) ]'))

            await self.agenlen(1, core.eval('inet:fqdn +#bad $fqdnbad=#bad -> inet:dns:a:fqdn +.seen@=$fqdnbad'))

    async def test_cortex_storm_tagform(self):

        async with self.getTestCore() as core:

            await self.agenlen(1, core.eval('[ test:str=hehe ]'))
            await self.agenlen(1, core.eval('[ test:str=haha +#foo ]'))
            await self.agenlen(1, core.eval('[ test:str=woot +#foo=(2015,2018) ]'))

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

    async def test_cortex_storm_indx_none(self):
        async with self.getTestCore() as core:
            await self.agenraises(s_exc.NoSuchIndx, core.eval('graph:node:data=10'))

    async def _validate_feed(self, core, gestdef, guid, seen, pack=False):

        async def awaitagen(obj):
            '''
            Remote async gen methods act differently than local cells in that an extra await is needed.
            '''
            if s_coro.iscoro(obj):
                return await obj
            return obj
        # Helper for syn_ingest tests
        await core.addFeedData('syn.ingest', [gestdef])

        # Nodes are made from the forms directive
        q = 'test:str=1234 test:str=duck test:str=knight'
        await self.agenlen(3, await awaitagen(core.eval(q)))
        q = 'test:int=1234'
        await self.agenlen(1, await awaitagen(core.eval(q)))
        q = 'test:pivcomp=(hehe,haha)'
        await self.agenlen(1, await awaitagen(core.eval(q)))

        # packed nodes are made from the nodes directive
        nodes = await alist(await awaitagen(core.eval('test:str=ohmy')))
        if pack:
            nodes = [node.pack() for node in nodes]
        self.len(1, nodes)
        node = nodes[0]
        self.eq(node[1]['props'].get('bar'), ('test:int', 137))
        self.eq(node[1]['props'].get('tick'), 978307200000)
        self.isin('beep.beep', node[1]['tags'])
        self.isin('beep.boop', node[1]['tags'])
        self.isin('test.foo', node[1]['tags'])

        nodes = await alist(await awaitagen(core.eval('test:int=8675309')))
        if pack:
            nodes = [node.pack() for node in nodes]
        self.len(1, nodes)
        node = nodes[0]
        self.isin('beep.morp', node[1]['tags'])
        self.isin('test.foo', node[1]['tags'])

        # Sources are made, as are seen nodes.
        q = f'meta:source={guid} -> meta:seen:source'
        nodes = await alist(await awaitagen(core.eval(q)))
        if pack:
            nodes = [node.pack() for node in nodes]
        self.len(9, nodes)
        for node in nodes:
            self.isin('.seen', node[1].get('props', {}))

        # Included tags are made
        await self.agenlen(9, await awaitagen(core.eval(f'#test')))

        # As are tag times
        nodes = await alist(await awaitagen(core.eval('#test.baz')))
        if pack:
            nodes = [node.pack() for node in nodes]
        self.eq(nodes[0][1].get('tags', {}).get('test.baz', ()),
                (1388534400000, 1420070400000))

        # Edges are made
        await self.agenlen(1, await awaitagen(core.eval('edge:refs')))
        await self.agenlen(1, await awaitagen(core.eval('edge:wentto')))

    async def test_syn_ingest_remote(self):
        guid = s_common.guid()
        seen = s_common.now()
        gestdef = self.getIngestDef(guid, seen)

        # Test Remote Cortex
        async with self.getTestCoreAndProxy() as (realcore, core):

            # Setup user permissions
            await core.addAuthRole('creator')
            await core.addAuthRule('creator', (True, ('node:add',)))
            await core.addAuthRule('creator', (True, ('prop:set',)))
            await core.addAuthRule('creator', (True, ('tag:add',)))
            await core.addUserRole('root', 'creator')
            await self._validate_feed(core, gestdef, guid, seen)

    async def test_syn_ingest_local(self):
        guid = s_common.guid()
        seen = s_common.now()
        gestdef = self.getIngestDef(guid, seen)

        async with self.getTestCore() as core:
            await self._validate_feed(core, gestdef, guid, seen, pack=True)

    async def test_cortex_int_indx(self):

        async with self.getTestCore() as core:

            await alist(core.eval('[test:int=20]'))

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
            await alist(core.eval('[test:str=foo :tick=201808021201]'))

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

            await alist(core.eval('[test:int=99999]'))
            await self.agenlen(1, core.eval('test:int<=20'))
            await self.agenlen(2, core.eval('test:int>=20'))
            await self.agenlen(1, core.eval('test:int>20'))
            await self.agenlen(0, core.eval('test:int<20'))

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

    async def test_cortex_univ(self):

        async with self.getTestCore() as core:

            # Ensure that the test model loads a univ property
            prop = core.model.prop('.test:univ')
            self.isinstance(prop, s_datamodel.Univ)

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

    async def test_cortex_snap_eval(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                await self.agenlen(2, snap.eval('[test:str=foo test:str=bar]'))
            await self.agenlen(2, core.eval('test:str'))

    async def test_feed_syn_nodes(self):
        async with self.getTestCore() as core0:
            q = '[test:int=1 test:int=2 test:int=3]'
            podes = [n.pack() async for n in core0.eval(q)]
            self.len(3, podes)
        async with self.getTestCore() as core1:
            await core1.addFeedData('syn.nodes', podes)
            await self.agenlen(3, core1.eval('test:int'))

    async def test_stat(self):

        async with self.getTestCoreAndProxy() as (realcore, core):
            coreiden = realcore.iden
            ostat = await core.stat()
            self.eq(ostat.get('iden'), coreiden)
            self.isin('layer', ostat)
            await self.agenlen(1, (core.eval('[test:str=123 :tick=2018]')))
            nstat = await core.stat()
            self.ge(nstat.get('layer').get('splicelog_indx'), ostat.get('layer').get('splicelog_indx'))

            core_counts = realcore.counts
            counts = nstat.get('formcounts')
            self.eq(counts.get('test:str'), 1)
            self.eq(counts, core_counts)

    async def test_offset(self):
        async with self.getTestCoreAndProxy() as (realcore, core):
            iden = s_common.guid()
            self.eq(await core.getFeedOffs(iden), 0)
            self.none(await core.setFeedOffs(iden, 10))
            self.eq(await core.getFeedOffs(iden), 10)
            self.none(await core.setFeedOffs(iden, 0))
            self.eq(await core.getFeedOffs(iden), 0)
            await self.asyncraises(s_exc.BadConfValu, core.setFeedOffs(iden, -1))

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

    async def test_storm_cond_has(self):
        async with self.getTestCore() as core:

            await core.eval('[ inet:ipv4=1.2.3.4 :asn=20 ]').list()
            self.len(1, await core.eval('inet:ipv4=1.2.3.4 +:asn').list())

            with self.raises(s_exc.BadSyntax):
                await core.eval('[ inet:ipv4=1.2.3.4 +:foo ]').list()

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
                self.len(0, await core.eval('syn:tag=foo.bar -> test:str:tick').list())
                self.true(await stream.wait(4))

    async def test_storm_tagtags(self):

        async with self.getTestCore() as core:

            await core.eval('[ test:str=visi +#foo.bar ] -> # [ +#baz.faz ]').spin()

            nodes = await core.eval('##baz.faz').list()
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'visi')

            # make an icky loop of tags...
            await alist(core.eval('syn:tag=baz.faz [ +#foo.bar ]'))

            # should still be ok...
            nodes = await alist(core.eval('##baz.faz'))
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

                await core.eval('[ test:str=foo test:str=bar test:int=42 ]').spin()

                self.eq(1, core.counts['test:int'])
                self.eq(2, core.counts['test:str'])

                core.counts['test:str'] = 99

                await core.eval('reindex --form-counts').spin()

                self.eq(1, core.counts['test:int'])
                self.eq(2, core.counts['test:str'])

            # test that counts persist...
            async with self.getTestCore(dirn=dirn) as core:

                self.eq(1, core.counts['test:int'])
                self.eq(2, core.counts['test:str'])

                node = await core.getNodeByNdef(('test:str', 'foo'))
                await node.delete()

                self.eq(1, core.counts['test:str'])

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

    async def test_storm_switchcase(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'woot': 'hehe'}}
            text = '[test:str=a] switch $woot { hehe: {[+#baz]} }'
            nodes = await core.eval(text, opts=opts).list()
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef[1], 'a')
                self.nn(node.getTag('baz'))
                self.none(node.getTag('faz'))
                self.none(node.getTag('jaz'))

            opts = {'vars': {'woot': 'haha hoho'}}
            text = '[test:str=b] switch $woot { hehe: {[+#baz]} haha hoho: {[+#faz]} "lolz:lulz": {[+#jaz]} }'
            nodes = await core.eval(text, opts=opts).list()
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef[1], 'b')
                self.none(node.getTag('baz'))
                self.nn(node.getTag('faz'))
                self.none(node.getTag('jaz'))

            opts = {'vars': {'woot': 'lolz:lulz'}}
            text = '[test:str=c] switch $woot { hehe: {[+#baz]} haha hoho: {[+#faz]} "lolz:lulz": {[+#jaz]} }'
            nodes = await core.eval(text, opts=opts).list()
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef[1], 'c')
                self.none(node.getTag('baz'))
                self.none(node.getTag('faz'))
                self.nn(node.getTag('jaz'))

            opts = {'vars': {'woot': 'lulz'}}
            text = '[test:str=c] switch $woot { hehe: {[+#baz]} *: {[+#jaz]} }'
            nodes = await core.eval(text, opts=opts).list()
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef[1], 'c')
                self.none(node.getTag('baz'))
                self.nn(node.getTag('jaz'))

    async def test_storm_tagvar(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'tag': 'hehe.haha'}}

            async for node in core.eval('[ test:str=foo +#$tag ]', opts=opts):
                self.eq(node.ndef[1], 'foo')
                self.nn(node.getTag('hehe.haha'))

            async for node in core.eval('#$tag', opts=opts):
                self.eq(node.ndef[1], 'foo')
                self.nn(node.getTag('hehe.haha'))

            async for node in core.eval('#$tag [ -#$tag ]', opts=opts):
                self.eq(node.ndef[1], 'foo')
                self.none(node.getTag('hehe.haha'))

    async def test_storm_forloop(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'fqdns': ('foo.com', 'bar.com')}}

            vals = []
            async for node in core.eval('for $fqdn in $fqdns { [ inet:fqdn=$fqdn ] }', opts=opts):
                vals.append(node.ndef[1])

            self.eq(('bar.com', 'foo.com'), sorted(vals))

            opts = {'vars': {'dnsa': (('foo.com', '1.2.3.4'), ('bar.com', '5.6.7.8'))}}

            vals = []
            async for node in core.eval('for ($fqdn, $ipv4) in $dnsa { [ inet:dns:a=($fqdn,$ipv4) ] }', opts=opts):
                vals.append(node.ndef[1])

            self.eq((('foo.com', 0x01020304), ('bar.com', 0x05060708)), vals)

            with self.raises(s_exc.StormVarListError):
                await core.eval('for ($fqdn,$ipv4,$boom) in $dnsa { [ inet:dns:a=($fqdn,$ipv4) ] }', opts=opts).list()

            with self.raises(s_exc.StormVarListError):
                await core.eval('[ inet:ipv4=1.2.3.4 +#hehe +#haha ] for ($foo,$bar,$baz) in $node.tags() {[+#$foo]}').list()

            await core.eval('inet:ipv4=1.2.3.4 for $tag in $node.tags() { [ +#hoho ] { [inet:ipv4=5.5.5.5 +#$tag] } continue [ +#visi ] }').list()
            self.len(1, await core.eval('inet:ipv4=5.5.5.5 +#hehe +#haha -#visi').list())

            await core.eval('inet:ipv4=1.2.3.4 for $tag in $node.tags() { [ +#hoho ] { [inet:ipv4=6.6.6.6 +#$tag] } break [ +#visi ]}').list()
            self.len(1, await core.eval('inet:ipv4=6.6.6.6 +(#hehe or #haha) -(#hehe and #haha) -#visi').list())

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
                nodes = await alist(core.eval('inet:ipv4 -> test:str'))

    async def test_storm_mustquote(self):

        async with self.getTestCore() as core:
            await core.storm('[ inet:ipv4=1.2.3.4 ]').list()
            self.len(1, await core.storm('inet:ipv4=1.2.3.4|limit 20').list())

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
                baz faz: {}
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

            nodes = await core.eval(text, opts=opts).list()
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef, ('inet:fqdn', 'vertex.link'))

    async def test_storm_pivprop(self):

        async with self.getTestCore() as core:

            await core.eval('[ inet:asn=200 :name=visi ]').spin()
            await core.eval('[ inet:ipv4=1.2.3.4 :asn=200 ]').spin()
            await core.eval('[ inet:ipv4=5.6.7.8 :asn=8080 ]').spin()

            nodes = await core.eval('inet:ipv4 +:asn::name=visi').list()
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

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
            await core.eval(text, opts=opts).list()

            nodes = await core.eval('inet:ipv4').list()
            self.len(1, nodes)
            self.nn(nodes[0].getTag('visi'))
            self.none(nodes[0].getTag('hehe'))

            await core.eval('inet:ipv4 | delnode').list()

            opts = {'vars': {'foos': ['bar', 'bar']}}
            await core.eval(text, opts=opts).list()

            nodes = await core.eval('inet:ipv4').list()
            self.len(1, nodes)
            self.nn(nodes[0].getTag('ohai'))
            self.none(nodes[0].getTag('hehe'))

            await core.eval('inet:ipv4 | delnode').list()

            opts = {'vars': {'foos': ['lols', 'lulz']}}
            await core.eval(text, opts=opts).list()

            nodes = await core.eval('inet:ipv4').list()
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
            await core.eval(text, opts=opts).list()
            self.len(1, await core.eval('inet:dns:a=(vertex.link,1.2.3.4)').list())

    async def test_storm_dict_deref(self):

        async with self.getTestCore() as core:

            text = '''
            [ test:int=$hehe.haha ]
            '''
            opts = {'vars': {'hehe': {'haha': 20}}}
            nodes = await core.eval(text, opts=opts).list()
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
            nodes = await core.eval(text).list()
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 1388534400000)

    async def test_storm_selfrefs(self):

        async with self.getTestCore() as core:

            nodes = await core.eval('[ inet:fqdn=woot.com ] -> *').list()

            self.len(1, nodes)
            self.eq('com', nodes[0].ndef[1])

            await core.eval('inet:fqdn=woot.com | delnode').list()

            self.len(0, await core.eval('inet:fqdn=woot.com').list())

    async def test_storm_addnode_runtsafe(self):

        async with self.getTestCore() as core:
            # test adding nodes from other nodes output
            nodes = await core.eval('[ inet:fqdn=woot.com inet:fqdn=vertex.link ] [ inet:user = :zone ] +inet:user').list()
            self.len(2, nodes)
            ndefs = list(sorted([n.ndef for n in nodes]))
            self.eq(ndefs, (('inet:user', 'vertex.link'), ('inet:user', 'woot.com')))

    async def test_storm_subgraph(self):

        async with self.getTestCore() as core:

            await core.eval('[ inet:ipv4=1.2.3.4 :asn=20 ]').list()
            await core.eval('[ inet:dns:a=(woot.com, 1.2.3.4) +#yepr ]').list()
            await core.eval('[ inet:dns:a=(vertex.link, 5.5.5.5) +#nope ]').list()

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

            async for node, path in core.storm('inet:fqdn', opts={'graph': rules}):

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

            async for node, path in core.storm(text):

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

    async def test_storm_lib_time(self):

        async with self.getTestCore() as core:
            nodes = await core.eval('[ ps:person="*" :dob = $lib.time.fromunix(20) ]').list()
            self.len(1, nodes)
            self.eq(20000, nodes[0].get('dob'))

    async def test_storm_two_level_assignment(self):
        async with self.getTestCore() as core:
            q = '$foo=baz $bar=$foo [test:str=$bar]'
            nodes = await core.eval(q).list()
            self.len(1, nodes)
            self.eq('baz', nodes[0].ndef[1])

    async def test_storm_lib_custom(self):

        async with self.getTestCore() as core:
            # Test the registered function from test utils
            q = '[ ps:person="*" :name = $lib.test.beep(loud) ]'
            nodes = await core.eval(q).list()
            self.len(1, nodes)
            self.eq('a loud beep!', nodes[0].get('name'))

            q = '$test = $lib.test.beep(test) [test:str=$test]'
            nodes = await core.eval(q).list()
            self.len(1, nodes)
            self.eq('A test beep!', nodes[0].ndef[1])

            # Regression:  variable substitution in function raises exception
            q = '$foo=baz $test = $lib.test.beep($foo) [test:str=$test]'
            nodes = await core.eval(q).list()
            self.len(1, nodes)
            self.eq('A baz beep!', nodes[0].ndef[1])

    async def test_storm_type_node(self):

        async with self.getTestCore() as core:
            nodes = await core.eval('[ ps:person="*" edge:has=($node, (inet:fqdn,woot.com)) ]').list()
            self.len(2, nodes)
            self.eq('edge:has', nodes[1].ndef[0])

            nodes = await core.eval('[test:str=test] [ edge:refs=($node,(test:int, 1234)) ] -test:str').list()
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], (('test:str', 'test'), ('test:int', 1234)))

            nodes = await core.eval('test:int=1234 [test:str=$node.value()] -test:int').list()
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', '1234'))

            nodes = await core.eval('test:int=1234 [test:str=$node.form()] -test:int').list()
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'test:int'))

    async def test_storm_subq_size(self):

        async with self.getTestCore() as core:

            await core.storm('[ inet:dns:a=(woot.com, 1.2.3.4) inet:dns:a=(vertex.link, 1.2.3.4) ]').list()

            self.len(0, await core.storm('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }=0 )').list())

            self.len(1, await core.storm('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }=2 )').list())
            self.len(0, await core.storm('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }=3 )').list())

            self.len(0, await core.storm('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }!=2 )').list())
            self.len(1, await core.storm('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }!=3 )').list())

            self.len(1, await core.storm('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }>=1 )').list())
            self.len(1, await core.storm('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }>=2 )').list())
            self.len(0, await core.storm('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }>=3 )').list())

            self.len(0, await core.storm('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }<=1 )').list())
            self.len(1, await core.storm('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }<=2 )').list())
            self.len(1, await core.storm('inet:ipv4=1.2.3.4 +( { -> inet:dns:a }<=3 )').list())

            self.len(0, await core.storm('inet:ipv4=1.2.3.4 +{ -> inet:dns:a } < 2 ').list())
            self.len(1, await core.storm('inet:ipv4=1.2.3.4 +{ -> inet:dns:a } < 3 ').list())

            self.len(1, await core.storm('inet:ipv4=1.2.3.4 +{ -> inet:dns:a } > 1 ').list())
            self.len(0, await core.storm('inet:ipv4=1.2.3.4 +{ -> inet:dns:a } > 2 ').list())

    async def test_cortex_in(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'a')
                node = await snap.addNode('test:str', 'b')
                node = await snap.addNode('test:str', 'c')

            self.len(0, await core.storm('test:str*in=()').list())
            self.len(0, await core.storm('test:str*in=(d)').list())
            self.len(2, await core.storm('test:str*in=(a, c)').list())
            self.len(1, await core.storm('test:str*in=(a, d)').list())
            self.len(3, await core.storm('test:str*in=(a, b, c)').list())

            self.len(0, await core.storm('test:str +test:str*in=()').list())
            self.len(0, await core.storm('test:str +test:str*in=(d)').list())
            self.len(2, await core.storm('test:str +test:str*in=(a, c)').list())
            self.len(1, await core.storm('test:str +test:str*in=(a, d)').list())
            self.len(3, await core.storm('test:str +test:str*in=(a, b, c)').list())

    async def test_runt(self):
        async with self.getTestCore() as core:

            # Ensure that lifting by form/prop/values works.
            nodes = await core.eval('test:runt').list()
            self.len(4, nodes)

            nodes = await core.eval('test:runt.created').list()
            self.len(4, nodes)

            nodes = await core.eval('test:runt:tick=2010').list()
            self.len(2, nodes)

            nodes = await core.eval('test:runt:tick=2001').list()
            self.len(1, nodes)

            nodes = await core.eval('test:runt:tick=2019').list()
            self.len(0, nodes)

            nodes = await core.eval('test:runt:lulz="beep.sys"').list()
            self.len(1, nodes)

            nodes = await core.eval('test:runt:lulz').list()
            self.len(2, nodes)

            nodes = await core.eval('test:runt:tick=$foo', {'vars': {'foo': '2010'}}).list()
            self.len(2, nodes)

            # Ensure that a lift by a universal property doesn't lift a runt node
            # accidentally.
            nodes = await core.eval('.created').list()
            self.ge(len(nodes), 1)
            self.notin('test:ret', {node.ndef[0] for node in nodes})

            # Ensure we can do filter operations on runt nodes
            nodes = await core.eval('test:runt +:tick*range=(1999, 2003)').list()
            self.len(1, nodes)

            nodes = await core.eval('test:runt -:tick*range=(1999, 2003)').list()
            self.len(3, nodes)

            # Ensure we can pivot to/from runt nodes
            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'beep.sys')

            nodes = await core.eval('test:runt :lulz -> test:str').list()
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'beep.sys'))

            nodes = await core.eval('test:str -> test:runt:lulz').list()
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:runt', 'beep'))

            # Lift by ndef/iden/opts does not work since runt support is not plumbed
            # into any caching which those lifts perform.
            ndef = ('test:runt', 'blah')
            iden = '15e33ccff08f9f96b5cea9bf0bcd2a55a96ba02af87f8850ba656f2a31429224'
            nodes = await core.eval(f'iden {iden}').list()
            self.len(0, nodes)

            nodes = await core.eval('', {'idens': [iden]}).list()
            self.len(0, nodes)

            nodes = await core.eval('', {'ndefs': [ndef]}).list()
            self.len(0, nodes)

            # Ensure that add/edit a read-only runt prop fails, whether or not it exists.
            await self.asyncraises(s_exc.IsRuntForm,
                                   core.eval('test:runt=beep [:tick=3001]').list())
            await self.asyncraises(s_exc.IsRuntForm,
                                   core.eval('test:runt=woah [:tick=3001]').list())

            # Ensure that we can add/edit secondary props which has a callback.
            nodes = await core.eval('test:runt=beep [:lulz=beepbeep.sys]').list()
            self.eq(nodes[0].get('lulz'), 'beepbeep.sys')
            await nodes[0].set('lulz', 'beepbeep.sys')  # We can do no-operation edits
            self.eq(nodes[0].get('lulz'), 'beepbeep.sys')

            # We can set props which were not there previously
            nodes = await core.eval('test:runt=woah [:lulz=woah.sys]').list()
            self.eq(nodes[0].get('lulz'), 'woah.sys')

            # A edit may throw an exception due to some prop-specific normalization reason.
            await self.asyncraises(s_exc.BadPropValu, core.eval('test:runt=woah [:lulz=no.way]').list())

            # Setting a property which has no callback or ro fails.
            await self.asyncraises(s_exc.IsRuntForm, core.eval('test:runt=woah [:newp=pennywise]').list())

            # Ensure that delete a read-only runt prop fails, whether or not it exists.
            await self.asyncraises(s_exc.IsRuntForm,
                                   core.eval('test:runt=beep [-:tick]').list())
            await self.asyncraises(s_exc.IsRuntForm,
                                   core.eval('test:runt=woah [-:tick]').list())

            # Ensure that we can delete a secondary prop which has a callback.
            nodes = await core.eval('test:runt=beep [-:lulz]').list()
            self.none(nodes[0].get('lulz'))

            nodes = await core.eval('test:runt=woah [-:lulz]').list()
            self.none(nodes[0].get('lulz'))

            # Deleting a property which has no callback or ro fails.
            await self.asyncraises(s_exc.IsRuntForm, core.eval('test:runt=woah [-:newp]').list())

            # # Ensure that adding tags on runt nodes fails
            await self.asyncraises(s_exc.IsRuntForm, core.eval('test:runt=beep [+#hehe]').list())
            await self.asyncraises(s_exc.IsRuntForm, core.eval('test:runt=beep [-#hehe]').list())

            # Ensure that adding / deleting test runt nodes fails
            await self.asyncraises(s_exc.IsRuntForm, core.eval('[test:runt=" oh MY! "]').list())
            await self.asyncraises(s_exc.IsRuntForm, core.eval('test:runt=beep | delnode').list())

            # Ensure that non-equality based lift comparators for the test runt nodes fails.
            await self.asyncraises(s_exc.BadCmprValu, core.eval('test:runt~="b.*"').list())
            await self.asyncraises(s_exc.BadCmprValu, core.eval('test:runt:tick*range=(1999, 2001)').list())

            # Sad path for underlying Cortex.runRuntLift
            await self.agenraises(s_exc.NoSuchLift, core.runRuntLift('test:newp', 'newp'))

    async def test_cortex_view_borked(self):

        async with self.getTestCore() as core:

            core.view.borked = s_common.guid()
            with self.raises(s_exc.NoSuchLayer):
                await core.eval('[ test:str=foo ]').list()

            core.view.borked = None
            self.len(1, await core.eval('[ test:str=foo ]').list())

    async def test_tag_globbing(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'n1')
                await node.addTag('foo.bar.baz', (None, None))

                node = await snap.addNode('test:str', 'n2')
                await node.addTag('foo.bad.baz', (None, None))

                node = await snap.addNode('test:str', 'n3')  # No tags on him

            # Setup worked correct
            self.len(3, await core.eval('test:str').list())
            self.len(2, await core.eval('test:str +#foo').list())

            # Now test globbing - exact match for *
            self.len(2, await core.eval('test:str +#*').list())
            self.len(1, await core.eval('test:str -#*').list())

            # Now test globbing - single star matches one tag level
            self.len(2, await core.eval('test:str +#foo.*.baz').list())
            self.len(1, await core.eval('test:str +#*.bad').list())
            # Double stars matches a whole lot more!
            self.len(2, await core.eval('test:str +#foo.**.baz').list())
            self.len(1, await core.eval('test:str +#**.bar.baz').list())
            self.len(2, await core.eval('test:str +#**.baz').list())

    async def test_provstackmigration_pre010(self):
        async with self.getRegrCore('pre-010') as core:
            provstacks = list(core.provstor.provStacks(0, 1000))
            self.gt(len(provstacks), 5)
            self.false(core.view.layers[0].layrslab.dbexists('prov'))
            self.false(core.view.layers[0].layrslab.dbexists('provs'))

    async def test_storm_lift_compute(self):
        async with self.getTestCore() as core:
            self.len(2, await core.nodes('[ inet:dns:a=(vertex.link,1.2.3.4) inet:dns:a=(woot.com,5.6.7.8)]'))
            self.len(4, await core.nodes('inet:dns:a inet:fqdn=:fqdn'))

    async def test_cortex_hive(self):
        async with self.getTestCore() as core:
            await core.hive.set(('visi',), 200)
            async with core.getLocalProxy(share='cortex/hive') as hive:
                self.eq(200, await hive.get(('visi',)))

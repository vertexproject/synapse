import asyncio
import unittest

from unittest.mock import patch

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.coro as s_coro

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class CortexTest(s_t_utils.SynTest):

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

                node = await snap.addNode('teststr', 'foo')
                await node.addTag('lol', valu=('2015', '?'))

                self.eq((1420070400000, 0x7fffffffffffffff), node.getTag('lol'))

            nodes = [n.pack() async for n in core.eval('teststr=foo +#lol@=2014')]
            self.len(0, nodes)

            nodes = [n.pack() async for n in core.eval('teststr=foo +#lol@=2016')]
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
            nodes = [n.pack() async for n in core.eval('seen:source=$sorc -> *', opts=opts)]

            self.len(2, nodes)
            self.true('inet:dns:a' in [n[0][0] for n in nodes])

            opts = {'vars': {'sorc': sorc}}
            nodes = [n.pack() async for n in core.eval('seen:source=$sorc :node -> *', opts=opts)]

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
            rows = await alist((core.layer.iterPropRows('inet:ipv4', 'asn')))

            self.eq((10, 20), tuple(sorted([row[1] for row in rows])))

            # rows are (buid, valu) tuples
            rows = await alist(core.layer.iterUnivRows('.seen'))

            ivals = ((1420070400000, 1420070400001), (1451606400000, 1451606400001))
            self.eq(ivals, tuple(sorted([row[1] for row in rows])))

    async def test_cortex_lift_regex(self):
        async with self.getTestCore() as core:
            core.model.addUnivProp('favcolor', ('str', {}), {})

            async with await core.snap() as snap:
                await snap.addNode('teststr', 'hezipha', props={'.favcolor': 'red'})
                await snap.addNode('testcomp', (20, 'lulzlulz'))

            self.len(0, await alist(core.eval('testcomp:haha~="^zerg"')))
            self.len(1, await alist(core.eval('testcomp:haha~="^lulz"')))

            self.len(1, await alist(core.eval('teststr~="zip"')))
            self.len(1, await alist(core.eval('teststr~="zip"')))
            self.len(1, await alist(core.eval('.favcolor~="^r"')))

    @s_glob.synchelp
    @patch('synapse.lib.lmdb.DEFAULT_MAP_SIZE', s_t_utils.TEST_MAP_SIZE)
    async def test_feed_conf(self):
        async with self.getTestDmon(mirror='cryodmon') as dst_dmon:

            name = 'cryo00'
            tname = 'tank:blahblah'
            host, port = dst_dmon.addr
            tank_addr = f'tcp://{host}:{port}/{name}/{tname}'

            recs = ['a', 'b', 'c']

            conf = {
                'feeds': [
                    {'type': 'com.test.record',
                     'cryotank': tank_addr,
                     'size': 1,
                     }
                ],
                'modules': ('synapse.tests.utils.TestModule',),
            }

            # initialize the tank and get his iden
            async with await s_telepath.openurl(tank_addr) as tank:
                iden = await tank.getCellIden()

            # Spin up a source core configured to eat data from the cryotank
            with self.getTestDir() as dirn:

                async with await self.getTestCell(dirn, 'cortex', conf=conf) as core:

                    waiter = core.waiter(3, 'core:feed:loop')

                    async with await s_telepath.openurl(tank_addr) as tank:
                        await tank.puts(recs)
                    # self.true(evt.wait(3))
                    self.true(await waiter.wait(4))

                    offs = await core.layer.getOffset(iden)
                    self.eq(offs, 3)
                    await self.agenlen(3, core.storm('teststr'))

            with self.getTestDir() as dirn:
                # Sad path testing
                conf['feeds'][0]['type'] = 'com.clown'
                await self.asyncraises(s_exc.NoSuchType, self.getTestCell(dirn, 'cortex', conf=conf))

    async def test_cortex_model_dict(self):

        async with self.getTestDmon(mirror='dmoncore') as dmon, \
                await self.agetTestProxy(dmon, 'core') as core:

            model = await core.getModelDict()

            tnfo = model['types'].get('inet:ipv4')

            self.nn(tnfo)
            self.eq(tnfo['info']['doc'], 'An IPv4 address.')

            fnfo = model['forms'].get('inet:ipv4')
            self.nn(fnfo)

            pnfo = fnfo['props'].get('asn')

            self.nn(pnfo)
            self.eq(pnfo['type'][0], 'inet:asn')

    async def test_storm_graph(self):

        async with self.getTestDmon(mirror='dmoncore') as dmon, \
                await self.agetTestProxy(dmon, 'core') as core:

            await core.addNode('inet:dns:a', ('woot.com', '1.2.3.4'))

            opts = {'graph': True}
            nodes = await alist(await core.eval('inet:dns:a', opts=opts))

            self.len(5, nodes)

            for node in nodes:
                if node[0][0] == 'inet:dns:a':
                    edges = node[1]['path']['edges']
                    idens = list(sorted(e[0] for e in edges))
                    self.eq(idens, ('20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f', 'd7fb3ae625e295c9279c034f5d91a7ad9132c79a9c2b16eecffc8d1609d75849'))

    @s_glob.synchelp
    @patch('synapse.lib.lmdb.DEFAULT_MAP_SIZE', s_t_utils.TEST_MAP_SIZE)
    async def test_splice_cryo(self):
        async with self.getTestDmon(mirror='cryodmon') as dst_dmon:
            name = 'cryo00'
            host, port = dst_dmon.addr
            tank_addr = f'tcp://{host}:{port}/{name}/tank:blahblah'

            # Spin up a source core configured to send splices to dst core
            with self.getTestDir() as dirn:
                conf = {
                    'splice:cryotank': tank_addr,
                    'modules': ('synapse.tests.utils.TestModule',),
                }
                src_core = await self.getTestCell(dirn, 'cortex', conf=conf)

                waiter = src_core.waiter(2, 'core:splice:cryotank:sent')
                # Form a node and make sure that it exists
                async with await src_core.snap() as snap:
                    await snap.addNode('teststr', 'teehee')
                    self.nn(await snap.getNodeByNdef(('teststr', 'teehee')))

                await waiter.wait(timeout=3)
                await src_core.fini()
                await src_core.waitfini()

            # Now that the src core is closed, make sure that the splice exists in the tank
            tankcell = dst_dmon.shared.get(name)
            tank = tankcell.tanks.get('tank:blahblah')
            slices = list(tank.slice(0, 1000))
            # # TestModule creates one node and 3 splices
            self.len(3 + 2, slices)

            slices = slices[3:]
            data = slices[0]
            self.isinstance(data[1], tuple)
            self.len(2, data[1])
            self.eq(data[1][0], 'node:add')
            self.eq(data[1][1].get('ndef'), ('teststr', 'teehee'))
            self.eq(data[1][1].get('user'), '?')
            self.ge(data[1][1].get('time'), 0)

            data = slices[1]
            self.isinstance(data[1], tuple)
            self.len(2, data[1])
            self.eq(data[1][0], 'prop:set')
            self.eq(data[1][1].get('ndef'), ('teststr', 'teehee'))
            self.eq(data[1][1].get('prop'), '.created')
            self.ge(data[1][1].get('valu'), 0)
            self.none(data[1][1].get('oldv'))
            self.eq(data[1][1].get('user'), '?')
            self.ge(data[1][1].get('time'), 0)

    async def test_splice_sync(self):
        async with self.getTestDmon(mirror='dmoncore') as dst_dmon:
            name = 'core'
            host, port = dst_dmon.addr
            dst_core = dst_dmon.shared.get(name)
            dst_core_addr = f'tcp://{host}:{port}/{name}'
            evt = asyncio.Event(loop=dst_dmon.loop)

            def onAdd(node):
                evt.set()

            dst_core.model.form('teststr').onAdd(onAdd)

            # Spin up a source core configured to send splices to dst core
            with self.getTestDir() as dirn:
                conf = {
                    'splice:sync': dst_core_addr,
                    'modules': ('synapse.tests.utils.TestModule',),
                }
                async with await self.getTestCell(dirn, 'cortex', conf=conf) as src_core:
                    # Form a node and make sure that it exists
                    waiter = src_core.waiter(2, 'core:splice:sync:sent')
                    async with await src_core.snap() as snap:
                        await snap.addNode('teststr', 'teehee')
                        self.nn(await snap.getNodeByNdef(('teststr', 'teehee')))

                    await waiter.wait(timeout=3)

            self.true(await s_coro.event_wait(evt, timeout=3))
            # Now that the src core is closed, make sure that the node exists
            # in the dst core without creating it
            async with await dst_core.snap() as snap:
                node = await snap.getNodeByNdef(('teststr', 'teehee'))
                self.eq(node.ndef, ('teststr', 'teehee'))

    async def test_onadd(self):
        arg_hit = {}

        async def testcb(node):
            arg_hit['hit'] = node

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                core.model.form('inet:ipv4').onAdd(testcb)

                node = await snap.addNode('inet:ipv4', '1.2.3.4')
                self.eq(node, arg_hit.get('hit'))

    async def test_adddata(self):

        data = ('foo', 'bar', 'baz')

        async with self.getTestCore() as core:

            await core.addFeedData('com.test.record', data)

            vals = [node.ndef[1] async for node in core.eval('teststr')]

            vals.sort()

            self.eq(vals, ('bar', 'baz', 'foo'))

    async def test_indxchop(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                valu = 'a' * 257
                await snap.addNode('teststr', valu)

                nodes = await alist(snap.getNodesBy('teststr', 'aa', cmpr='^='))
                self.len(1, nodes)

    async def test_cell(self):

        data = ('foo', 'bar', 'baz')

        async with self.getTestDmon(mirror='dmoncore') as dmon, \
                await self.agetTestProxy(dmon, 'core') as core:

            nodes = ((('inet:user', 'visi'), {}), )

            nodes = await alist(await core.addNodes(nodes))
            self.len(1, nodes)

            nodes = await alist(await core.getNodesBy('inet:user', 'visi'))
            self.len(1, nodes)
            self.eq('visi', nodes[0][0][1])

            node = await core.addNode('teststr', 'foo')

            pack = await core.addNodeTag(node[1].get('iden'), '#foo.bar')
            self.eq(pack[1]['tags'].get('foo.bar'), (None, None))

            pack = await core.setNodeProp(node[1].get('iden'), 'tick', '2015')
            self.eq(pack[1]['props'].get('tick'), 1420070400000)

            self.len(1, await alist(await core.eval('teststr#foo.bar')))
            self.len(1, await alist(await core.eval('teststr:tick=2015')))

            await core.delNodeTag(node[1].get('iden'), '#foo.bar')
            self.len(0, await alist(await core.eval('teststr#foo.bar')))

            opts = {'ndefs': [('inet:user', 'visi')]}

            nodes = await alist(await core.eval('', opts=opts))

            self.len(1, nodes)
            self.eq('visi', nodes[0][0][1])

            await core.addFeedData('com.test.record', data)

            # test the remote storm result counting API
            self.eq(0, await core.count('pivtarg'))
            self.eq(1, await core.count('inet:user'))

    async def test_stormcmd(self):

        async with self.getTestDmon(mirror='dmoncore') as dmon, \
                await self.agetTestProxy(dmon, 'core') as core:

            msgs = await alist(await core.storm('|help'))
            self.printed(msgs, 'help: List available commands and a brief description for each.')

            msgs = await alist(await core.storm('help'))
            self.printed(msgs, 'help: List available commands and a brief description for each.')

            await alist(await core.eval('[ inet:user=visi inet:user=whippit ]'))

            await self.agenlen(2, await core.eval('inet:user'))

            # test cmd as last text syntax
            await self.agenlen(1, await core.eval('inet:user | limit 1'))

            # test cmd and trailing pipe syntax
            await self.agenlen(1, await core.eval('inet:user | limit 1|'))

            # test cmd and trailing pipe and whitespace syntax
            await self.agenlen(1, await core.eval('inet:user | limit 1    |     '))

            # test cmd and trailing pipe and whitespace syntax
            await self.agenlen(2, await core.eval('inet:user | limit 10 | [ +#foo.bar ]'))
            await self.agenlen(1, await core.eval('inet:user | limit 10 | +inet:user=visi'))

            # test invalid option syntax
            msgs = await alist(await core.storm('inet:user | limit --woot'))
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

                await snap.addNode('teststr', 'newp')

                node = await snap.addNode('teststr', 'one')
                await node.addTag('foo.bar', ('2016', '2017'))

                self.eq((1451606400000, 1483228800000), node.getTag('foo.bar', ('2016', '2017')))

                node1 = await snap.addNode('testcomp', (10, 'hehe'))
                await node1.addTag('foo.bar')

                self.nn(await snap.getNodeByNdef(('syn:tag', 'foo')))
                self.nn(await snap.getNodeByNdef(('syn:tag', 'foo.bar')))

            async with await core.snap() as snap:

                node = await snap.getNodeByNdef(('teststr', 'one'))

                self.true(node.hasTag('foo'))
                self.true(node.hasTag('foo.bar'))

                await self.agenraises(s_exc.NoSuchForm, snap.getNodesBy('noway#foo.bar'))

                self.len(2, await alist(snap.getNodesBy('#foo.bar')))
                self.len(1, await alist(snap.getNodesBy('teststr#foo.bar')))

            async with await core.snap() as snap:

                node = await snap.addNode('teststr', 'one')

                await node.delTag('foo')

                self.false(node.hasTag('foo'))
                self.false(node.hasTag('foo.bar'))

            async with await core.snap() as snap:

                node = await snap.addNode('teststr', 'one')
                self.false(node.hasTag('foo'))
                self.false(node.hasTag('foo.bar'))

    async def test_base_types1(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                node = await snap.addNode('testtype10', 'one')
                await node.set('intprop', 21)

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('testtype10', 'one'))
                self.nn(node)
                self.eq(node.get('intprop'), 21)

    async def test_base_types2(self):
        async with self.getTestCore() as core:

            # Test some default values
            async with await core.snap() as snap:

                node = await snap.addNode('testtype10', 'one')
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

            # Open another snap to test some more default value behavior
            async with await core.snap() as snap:
                # Grab an updated reference to the first node
                node = (await alist(snap.getNodesBy('testtype10', 'one')))[0]
                # add another node with default vals
                await snap.addNode('testtype10', 'two')

                # modify default vals on initial node
                await node.set('intprop', 21)
                await node.set('strprop', 'qwer')
                await node.set('locprop', 'us.va.reston')

                node = await snap.addNode('testcomp', (33, 'THIRTY THREE'))

                self.eq(node.get('hehe'), 33)
                self.eq(node.get('haha'), 'thirty three')

                await self.asyncraises(s_exc.ReadOnlyProp, node.set('hehe', 80))

                self.none(await snap.getNodeByNdef(('testauto', 'autothis')))

                props = {
                    'bar': ('testauto', 'autothis'),
                    'baz': ('testtype10:strprop', 'WOOT'),
                    'tick': '20160505',
                }
                node = await snap.addNode('teststr', 'woot', props=props)
                self.eq(node.get('bar'), ('testauto', 'autothis'))
                self.eq(node.get('baz'), ('testtype10:strprop', 'woot'))
                self.eq(node.get('tick'), 1462406400000)

                nodes = await alist(snap.getNodesBy('teststr:tick', '20160505'))
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('teststr', 'woot'))

                # add some time range bumper nodes
                await snap.addNode('teststr', 'toolow', props={'tick': '2015'})
                await snap.addNode('teststr', 'toohigh', props={'tick': '2018'})

                # test a few time range syntax options...
                nodes = await alist(snap.getNodesBy('teststr:tick', '2016*'))
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('teststr', 'woot'))

                # test a few time range syntax options...
                nodes = await alist(snap.getNodesBy('teststr:tick', ('2016', '2017'), cmpr='*range='))
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('teststr', 'woot'))

                nodes = await alist(snap.getNodesBy('teststr:tick', ('2016', '2017'), cmpr='*range='))
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('teststr', 'woot'))

                self.nn(await snap.getNodeByNdef(('testauto', 'autothis')))

                # test lifting by prop without value
                nodes = await alist(snap.getNodesBy('teststr:tick'))
                self.len(3, nodes)

            async with await core.snap() as snap:

                node = await snap.addNode('testtype10', 'one')
                self.eq(node.get('intprop'), 21)

                self.nn(node.get('.created'))

                nodes = await alist(snap.getNodesBy('teststr', 'too', cmpr='^='))
                self.len(2, nodes)

                # test loc prop prefix based lookup
                nodes = await alist(snap.getNodesBy('testtype10:locprop', 'us.va'))

                self.len(1, nodes)
                self.eq(nodes[0].ndef[1], 'one')

                nodes = await alist(snap.getNodesBy('testcomp', (33, 'thirty three')))

                self.len(1, nodes)

                self.eq(nodes[0].get('hehe'), 33)
                self.eq(nodes[0].ndef[1], (33, 'thirty three'))

    @unittest.skip('functionality temporarily removed')
    async def test_pivprop(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                pivc = await snap.addNode('pivcomp', ('woot', 'rofl'))
                self.eq(pivc.get('targ'), 'woot')

                pivt = await snap.getNodeByNdef(('pivtarg', 'woot'))
                await pivt.set('name', 'visi')
                self.nn(pivt)

            async with await core.snap() as snap:
                pivc = await snap.getNodeByNdef(('pivcomp', ('woot', 'rofl')))
                self.eq(pivc.get('targ::name'), 'visi')

    async def test_eval(self):
        ''' Cortex.eval test '''

        async with self.getTestCore() as core:

            # test some edit syntax
            async for node in core.eval('[ testcomp=(10, haha) +#foo.bar -#foo.bar ]'):
                self.nn(node.getTag('foo'))
                self.none(node.getTag('foo.bar'))

            async for node in core.eval('[ teststr="foo bar" :tick=2018]'):
                self.eq(1514764800000, node.get('tick'))
                self.eq('foo bar', node.ndef[1])

            async for node in core.eval('teststr="foo bar" [ -:tick ]'):
                self.none(node.get('tick'))

            async for node in core.eval('[testguid="*" :tick=2001]'):
                self.true(s_common.isguid(node.ndef[1]))
                self.nn(node.get('tick'))

            nodes = [n.pack() async for n in core.eval('teststr="foo bar" +teststr')]
            self.len(1, nodes)

            nodes = [n.pack() async for n in core.eval('teststr="foo bar" -teststr:tick')]
            self.len(1, nodes)

            qstr = 'teststr="foo bar" +teststr="foo bar" [ :tick=2015 ] +teststr:tick=2015'
            nodes = [n.pack() async for n in core.eval(qstr)]
            self.len(1, nodes)

            # Seed new nodes via nodedesf
            ndef = ('testcomp', (10, 'haha'))
            opts = {'ndefs': (ndef,)}
            # Seed nodes in the query with ndefs
            async for node in core.eval('[-#foo]', opts=opts):
                self.none(node.getTag('foo'))

            # Seed nodes in the query with idens
            opts = {'idens': (nodes[0][1].get('iden'),)}
            nodes = await alist(core.eval('', opts=opts))
            self.len(1, nodes)
            self.eq(nodes[0].pack()[0], ('teststr', 'foo bar'))

            # Test and/or/not
            await alist(core.eval('[testcomp=(1, test) +#meep.morp +#bleep.blorp +#cond]'))
            await alist(core.eval('[testcomp=(2, test) +#meep.morp +#bleep.zlorp +#cond]'))
            await alist(core.eval('[testcomp=(3, foob) +#meep.gorp +#bleep.zlorp +#cond]'))

            q = 'testcomp +(:hehe<2 and :haha=test)'
            self.len(1, await alist(core.eval(q)))

            q = 'testcomp +(:hehe<2 and :haha=foob)'
            self.len(0, await alist(core.eval(q)))

            q = 'testcomp +(:hehe<2 or :haha=test)'
            self.len(2, await alist(core.eval(q)))

            q = 'testcomp +(:hehe<2 or :haha=foob)'
            self.len(2, await alist(core.eval(q)))

            q = 'testcomp +(:hehe<2 or #meep.gorp)'
            self.len(2, await alist(core.eval(q)))
            # TODO Add not tests

            await self.agenraises(s_exc.NoSuchOpt, core.eval('%foo=asdf'))
            await self.agenraises(s_exc.BadOptValu, core.eval('%limit=asdf'))
            await self.agenraises(s_exc.NoSuchCmpr, core.eval('teststr*near=newp'))
            await self.agenraises(s_exc.NoSuchCmpr, core.eval('teststr +teststr@=2018'))
            await self.agenraises(s_exc.NoSuchCmpr, core.eval('teststr +#test*near=newp'))
            await self.agenraises(s_exc.NoSuchCmpr, core.eval('teststr +teststr:tick*near=newp'))
            await self.agenraises(s_exc.BadStormSyntax, core.eval(' | | '))
            await self.agenraises(s_exc.BadStormSyntax, core.eval('[-teststr]'))

            await self.agenlen(2, core.eval(('[ teststr=foo teststr=bar ]')))
            await self.agenlen(1, core.eval(('teststr %limit=1')))

            opts = {'vars': {'foo': 'bar'}}

            async for node in core.eval('teststr=$foo', opts=opts):
                self.eq('bar', node.ndef[1])

    async def test_remote_storm(self):

        # Remote storm test paths
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            pconf = {'user': 'root', 'passwd': 'root'}
            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:
                # Storm logging
                with self.getAsyncLoggerStream('synapse.cortex', 'Executing storm query [help ask] as [root]') \
                        as stream:
                    await alist(await core.storm('help ask'))
                    self.true(await stream.wait(4))
                # Bad syntax
                mesgs = await alist(await core.storm(' | | | '))
                self.len(0, [mesg for mesg in mesgs if mesg[0] == 'init'])
                self.len(1, [mesg for mesg in mesgs if mesg[0] == 'fini'])
                mesgs = [mesg for mesg in mesgs if mesg[0] == 'err']
                self.len(1, mesgs)
                enfo = mesgs[0][1]
                self.eq(enfo[0], 'BadStormSyntax')

    async def test_feed_splice(self):

        iden = s_common.guid()

        async with self.getTestCore() as core:

            offs = await core.getFeedOffs(iden)
            self.eq(0, offs)

            mesg = ('node:add', {'ndef': ('teststr', 'foo')})
            offs = await core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            self.eq(1, offs)

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('teststr', 'foo'))
                self.nn(node)

            mesg = ('prop:set', {'ndef': ('teststr', 'foo'), 'prop': 'tick', 'valu': 200})
            offs = await core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('teststr', 'foo'))
                self.eq(200, node.get('tick'))

            mesg = ('prop:del', {'ndef': ('teststr', 'foo'), 'prop': 'tick'})
            offs = await core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('teststr', 'foo'))
                self.none(node.get('tick'))

            mesg = ('tag:add', {'ndef': ('teststr', 'foo'), 'tag': 'bar', 'valu': (200, 300)})
            offs = await core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('teststr', 'foo'))
                self.eq((200, 300), node.getTag('bar'))

            mesg = ('tag:del', {'ndef': ('teststr', 'foo'), 'tag': 'bar'})
            offs = await core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('teststr', 'foo'))
                self.none(node.getTag('bar'))

    async def test_splice_generation(self):

        async with self.getTestCore() as core:

            await alist(core.eval('[teststr=hello]'))
            await alist(core.eval('teststr=hello [:tick="2001"]'))
            await alist(core.eval('teststr=hello [:tick="2002"]'))
            await alist(core.eval('teststr [+#foo.bar]'))
            await alist(core.eval('teststr [+#foo.bar=(2000,2002)]'))
            await alist(core.eval('teststr [+#foo.bar=(2000,20020601)]'))
            await alist(core.eval('teststr [-#foo]'))
            await alist(core.eval('teststr [-:tick]'))
            await alist(core.eval('teststr | delnode --force'))

            _splices = await alist(core.layer.splices(0, 10000))
            splices = []
            # strip out user and time
            for splice in _splices:
                splice[1].pop('user', None)
                splice[1].pop('time', None)
                splices.append(splice)
            # Check to ensure a few expected splices exist
            mesg = ('node:add', {'ndef': ('teststr', 'hello')})
            self.isin(mesg, splices)

            mesg = ('prop:set', {'ndef': ('teststr', 'hello'), 'prop': 'tick', 'valu': 978307200000, 'oldv': None})
            self.isin(mesg, splices)

            mesg = ('prop:set',
                    {'ndef': ('teststr', 'hello'), 'prop': 'tick', 'valu': 1009843200000, 'oldv': 978307200000})
            self.isin(mesg, splices)

            mesg = ('tag:add', {'ndef': ('teststr', 'hello'), 'tag': 'foo', 'valu': (None, None)})
            self.isin(mesg, splices)

            mesg = ('tag:add', {'ndef': ('teststr', 'hello'), 'tag': 'foo.bar', 'valu': (None, None)})
            self.isin(mesg, splices)

            mesg = ('tag:add', {'ndef': ('teststr', 'hello'), 'tag': 'foo.bar', 'valu': (946684800000, 1009843200000)})
            self.isin(mesg, splices)

            mesg = ('tag:add', {'ndef': ('teststr', 'hello'), 'tag': 'foo.bar', 'valu': (946684800000, 1022889600000)})
            self.isin(mesg, splices)

            mesg = ('tag:del', {'ndef': ('teststr', 'hello'), 'tag': 'foo', 'valu': (None, None)})
            self.isin(mesg, splices)

            mesg = ('prop:del', {'ndef': ('teststr', 'hello'), 'prop': 'tick', 'valu': 1009843200000})
            self.isin(mesg, splices)

            mesg = ('node:del', {'ndef': ('teststr', 'hello')})
            self.isin(mesg, splices)

    async def test_strict(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                node = await snap.addNode('teststr', 'foo')

                await self.asyncraises(s_exc.NoSuchProp, node.set('newpnewp', 10))
                await self.asyncraises(s_exc.BadPropValu, node.set('tick', (20, 30)))

                snap.strict = False

                self.none(await snap.addNode('teststr', s_common.novalu))

                self.false(await node.set('newpnewp', 10))
                self.false(await node.set('tick', (20, 30)))

    async def test_getcoremods(self):
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            pconf = {'user': 'root', 'passwd': 'root'}

            core = dmon.shared.get('core')
            self.nn(core.getCoreMod('synapse.tests.utils.TestModule'))

            # Ensure that the module load creates a node.
            await self.agenlen(1, core.eval('source=8f1401de15918358d5247e21ca29a814'))

            async with await self.agetTestProxy(dmon, 'core', **pconf) as prox:

                mods = await prox.getCoreMods()

                mods = {k: v for k, v in mods}
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

            form = core.model.forms.get('teststr')

            form.onDel(onNodeDel)
            form.props.get('tick').onDel(onPropDel)

            async with await core.snap() as snap:

                targ = await snap.addNode('pivtarg', 'foo')
                await snap.addNode('pivcomp', ('foo', 'bar'))

                await self.asyncraises(s_exc.CantDelNode, targ.delete())

                tstr = await snap.addNode('teststr', 'baz')
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
                self.none(await snap.getNodeByNdef(('teststr', 'baz')))

            async with await core.snap() as snap:

                # test that secondary props are gone at the row level...
                prop = snap.model.prop('teststr:tick')
                lops = prop.getLiftOps(100)
                await self.agenlen(0, snap.getLiftRows(lops))

                # test that primary prop is gone at the row level...
                prop = snap.model.prop('teststr')
                lops = prop.getLiftOps('baz')
                await self.agenlen(0, snap.getLiftRows(lops))

                # check that buid rows are gone...
                self.eq(None, await snap._getNodeByBuid(buid))

                # final top level API check
                self.none(await snap.getNodeByNdef(('teststr', 'baz')))

    async def test_cortex_delnode_perms(self):

        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            pconf = {'user': 'root', 'passwd': 'root'}

            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:

                await alist(await core.eval('sudo | [ cycle0=foo :cycle1=bar ]'))
                await alist(await core.eval('sudo | [ cycle1=bar :cycle0=foo ]'))

                await alist(await core.eval('sudo | [ teststr=foo +#lol ]'))

                # no perms and not elevated...
                await self.agenraises(s_exc.AuthDeny, await core.eval('teststr=foo | delnode'))

                rule = (True, ('node:del',))
                await core.addAuthRule('root', rule)

                # should still deny because node has tag we can't delete
                await self.agenraises(s_exc.AuthDeny, await core.eval('teststr=foo | delnode'))

                rule = (True, ('tag:del', 'lol'))
                await core.addAuthRule('root', rule)

                await self.agenlen(0, await core.eval('teststr=foo | delnode'))

                await self.agenraises(s_exc.CantDelNode, await core.eval('cycle0=foo | delnode'))

                await self.agenlen(0, await core.eval('cycle0=foo | delnode --force'))

    async def test_cortex_sudo(self):

        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            pconf = {'user': 'root', 'passwd': 'root'}

            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:

                await self.agenraises(s_exc.AuthDeny, await core.eval('[ inet:ipv4=1.2.3.4 ]'))

                nodes = await alist(await core.eval('sudo | [ inet:ipv4=1.2.3.4 ]'))
                self.len(1, nodes)

    async def test_cortex_cell_splices(self):

        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            pconf = {'user': 'root', 'passwd': 'root'}

            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:
                # TestModule creates one node and 3 splices
                await self.agenlen(3, await core.splices(0, 1000))

                await alist(await core.eval('sudo | [ teststr=foo ]'))

                self.ge(len(await alist(await core.splices(0, 1000))), 5)

    async def test_pivot_inout(self):

        async def getPackNodes(core, query):
            nodes = sorted([n.pack() async for n in core.eval(query)])
            return nodes

        async with self.getTestCore() as core:
            # seed a node for pivoting
            await alist(core.eval('[ pivcomp=(foo,bar) :tick=2018 ]'))

            q = 'pivcomp=(foo,bar) -> pivtarg'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('pivtarg', 'foo'))

            q = 'pivcomp=(foo,bar) :targ -> pivtarg'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('pivtarg', 'foo'))

            q = 'teststr=bar -> pivcomp:lulz'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('pivcomp', ('foo', 'bar')))

            q = 'teststr=bar -+> pivcomp:lulz'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('teststr', 'bar'))

            q = 'pivcomp=(foo,bar) -+> pivtarg'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('pivtarg', 'foo'))

            q = 'pivcomp=(foo,bar) -> *'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('pivtarg', 'foo'))
            self.eq(nodes[1][0], ('teststr', 'bar'))

            q = 'pivcomp=(foo,bar) -+> *'
            nodes = await getPackNodes(core, q)
            self.len(3, nodes)
            self.eq(nodes[0][0], ('pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('pivtarg', 'foo'))
            self.eq(nodes[2][0], ('teststr', 'bar'))

            q = 'pivcomp=(foo,bar) :lulz -> teststr'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('teststr', 'bar'))

            q = 'pivcomp=(foo,bar) :lulz -+> teststr'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('teststr', 'bar'))

            q = 'teststr=bar <- *'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('pivcomp', ('foo', 'bar')))

            q = 'teststr=bar <+- *'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('teststr', 'bar'))

            # A simple edge for testing pivotinfrom with a edge to n2
            await alist(core.eval('[has=((teststr, foobar), (teststr, foo))]'))

            q = 'teststr=foobar -+> has'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('has', (('teststr', 'foobar'), ('teststr', 'foo'))))
            self.eq(nodes[1][0], ('teststr', 'foobar'))

            # traverse from node to edge:n1
            q = 'teststr=foo <- has'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('has', (('teststr', 'foobar'), ('teststr', 'foo'))))

            # traverse from node to edge:n1 with a join
            q = 'teststr=foo <+- has'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('has', (('teststr', 'foobar'), ('teststr', 'foo'))))
            self.eq(nodes[1][0], ('teststr', 'foo'))

            # Traverse from a edge to :n2
            # (this is technically a circular query)
            q = 'teststr=foobar -> has <- teststr'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('teststr', 'foobar'))

            # Traverse from a edge to :n2 with a join
            # (this is technically a circular query)
            q = 'teststr=foobar -> has <+- teststr'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('has', (('teststr', 'foobar'), ('teststr', 'foo'))))
            self.eq(nodes[1][0], ('teststr', 'foobar'))

            # Add tag
            q = 'teststr=bar pivcomp=(foo,bar) [+#test.bar]'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            # Lift, filter, pivot in
            q = '#test.bar +teststr <- *'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('pivcomp', ('foo', 'bar')))

            # Pivot tests with optimized lifts
            q = '#test.bar +teststr <+- *'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)

            q = '#test.bar +pivcomp -> *'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)

            q = '#test.bar +pivcomp -+> *'
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
            await alist(core.eval('[ testcomp=(127,newp) ] [testcomp=(127,127)]'))
            mesgs = await alist(core.streamstorm('testcomp :haha -> testint'))

            warns = [msg for msg in mesgs if msg[0] == 'warn']
            self.len(1, warns)
            emesg = "BadTypeValu ['newp'] during pivot: invalid literal for int() with base 0: 'newp'"
            self.eq(warns[0][1], {'name': 'testint', 'valu': 'newp',
                                  'mesg': emesg})
            nodes = [msg for msg in mesgs if msg[0] == 'node']
            self.len(1, nodes)
            self.eq(nodes[0][1][0], ('testint', 127))

            # Bad pivots go here
            for q in ['pivcomp :lulz <- *',
                      'pivcomp :lulz <+- *',
                      'pivcomp :lulz <- teststr',
                      'pivcomp :lulz <+- teststr',
                      ]:
                await self.agenraises(s_exc.BadStormSyntax, core.eval(q))

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

            node = (('teststr', 'foo'), {})

            await alist(core.addNodes((node,)))

            self.nn(await core.getNodeByNdef(('teststr', 'foo')))

    async def test_cortex_storm_set_univ(self):

        async with self.getTestCore() as core:

            await alist(core.eval('[ teststr=woot .seen=(2014,2015) ]'))

            async with await core.snap() as snap:

                node = await snap.getNodeByNdef(('teststr', 'woot'))
                self.eq(node.get('.seen'), (1388534400000, 1420070400000))

    async def test_cortex_storm_set_tag(self):

        async with self.getTestCore() as core:

            tick0 = core.model.type('time').norm('2014')[0]
            tick1 = core.model.type('time').norm('2015')[0]
            tick2 = core.model.type('time').norm('2016')[0]

            await self.agenlen(1, core.eval('[ teststr=hehe +#foo=(2014,2016) ]'))
            await self.agenlen(1, core.eval('[ teststr=haha +#bar=2015 ]'))

            async with await core.snap() as snap:

                node = await snap.getNodeByNdef(('teststr', 'hehe'))
                self.eq(node.getTag('foo'), (tick0, tick2))

                node = await snap.getNodeByNdef(('teststr', 'haha'))
                self.eq(node.getTag('bar'), (tick1, tick1 + 1))

            await self.agenlen(1, core.eval('[ teststr=haha +#bar=2016 ]'))

            async with await core.snap() as snap:

                node = await snap.getNodeByNdef(('teststr', 'haha'))
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

            await self.agenlen(1, core.eval('[ pivcomp=(hehe,haha) :tick=2015 +#foo=(2014,2016) ]'))
            await self.agenlen(1, core.eval('pivtarg=hehe [ .seen=2015 ]'))

            await self.agenlen(1, core.eval('pivcomp=(hehe,haha) $ticktock=#foo -> pivtarg +.seen@=$ticktock'))

            await self.agenlen(1, core.eval('inet:dns:a=(woot.com,1.2.3.4) [ .seen=(2015,2018) ]'))

            async for node in core.eval('inet:dns:a=(woot.com,1.2.3.4) $seen=.seen :fqdn -> inet:fqdn [ .seen=$seen ]'):
                self.eq(node.get('.seen'), (1420070400000, 1514764800000))

            await self.agenraises(s_exc.BadStormSyntax, core.eval('inet:dns:a=(woot.com,1.2.3.4) $newp=.newp'))

            # Vars can also be provided as tuple
            opts = {'vars': {'foo': ('hehe', 'haha')}}
            await self.agenlen(1, core.eval('pivcomp=$foo', opts=opts))

            # Vars can also be provided as integers
            norm = core.model.type('time').norm('2015')[0]
            opts = {'vars': {'foo': norm}}
            await self.agenlen(1, core.eval('pivcomp:tick=$foo', opts=opts))

    async def test_cortex_storm_filt_ival(self):

        async with self.getTestCore() as core:

            await self.agenlen(1, core.eval('[ teststr=woot +#foo=(2015,2018) +#bar .seen=(2014,2016) ]'))

            await self.agenlen(1, core.eval('teststr=woot +.seen@=2015'))
            await self.agenlen(0, core.eval('teststr=woot +.seen@=2012'))
            await self.agenlen(1, core.eval('teststr=woot +.seen@=(2012,2015)'))
            await self.agenlen(0, core.eval('teststr=woot +.seen@=(2012,2013)'))

            await self.agenlen(1, core.eval('teststr=woot +.seen@=#foo'))
            await self.agenlen(0, core.eval('teststr=woot +.seen@=#bar'))
            await self.agenlen(0, core.eval('teststr=woot +.seen@=#baz'))

            await self.agenlen(1, core.eval('teststr=woot $foo=#foo +.seen@=$foo'))

            await self.agenlen(1, core.eval('teststr +#foo@=2016'))
            await self.agenlen(1, core.eval('teststr +#foo@=(2015, 2018)'))
            await self.agenlen(1, core.eval('teststr +#foo@=(2014, 2019)'))
            await self.agenlen(0, core.eval('teststr +#foo@=(2014, 20141231)'))

            await self.agenlen(1, core.eval('[ inet:dns:a=(woot.com,1.2.3.4) .seen=(2015,2016) ]'))
            await self.agenlen(1, core.eval('[ inet:fqdn=woot.com +#bad=(2015,2016) ]'))

            await self.agenlen(1, core.eval('inet:fqdn +#bad $fqdnbad=#bad -> inet:dns:a:fqdn +.seen@=$fqdnbad'))

            # await self.agenlen(1, core.eval('[ teststr=woot +#foo=(2015,2018) .seen=(2014,2016) ]'))

    async def test_cortex_storm_tagform(self):

        async with self.getTestCore() as core:

            await self.agenlen(1, core.eval('[ teststr=hehe ]'))
            await self.agenlen(1, core.eval('[ teststr=haha +#foo ]'))
            await self.agenlen(1, core.eval('[ teststr=woot +#foo=(2015,2018) ]'))

            await self.agenlen(2, core.eval('#foo'))
            await self.agenlen(3, core.eval('teststr'))

            await self.agenlen(2, core.eval('teststr#foo'))
            await self.agenlen(1, core.eval('teststr#foo@=2016'))
            await self.agenlen(0, core.eval('teststr#foo@=2020'))

            # test the overlap variants
            await self.agenlen(0, core.eval('teststr#foo@=(2012,2013)'))
            await self.agenlen(0, core.eval('teststr#foo@=(2020,2022)'))
            await self.agenlen(1, core.eval('teststr#foo@=(2012,2017)'))
            await self.agenlen(1, core.eval('teststr#foo@=(2017,2022)'))
            await self.agenlen(1, core.eval('teststr#foo@=(2012,2022)'))

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
        q = 'teststr=1234 teststr=duck teststr=knight'
        await self.agenlen(3, await awaitagen(core.eval(q)))
        q = 'testint=1234'
        await self.agenlen(1, await awaitagen(core.eval(q)))
        q = 'pivcomp=(hehe,haha)'
        await self.agenlen(1, await awaitagen(core.eval(q)))

        # packed nodes are made from the nodes directive
        nodes = await alist(await awaitagen(core.eval('teststr=ohmy')))
        if pack:
            nodes = [node.pack() for node in nodes]
        self.len(1, nodes)
        node = nodes[0]
        self.eq(node[1]['props'].get('bar'), ('testint', 137))
        self.eq(node[1]['props'].get('tick'), 978307200000)
        self.isin('beep.beep', node[1]['tags'])
        self.isin('beep.boop', node[1]['tags'])
        self.isin('test.foo', node[1]['tags'])

        nodes = await alist(await awaitagen(core.eval('testint=8675309')))
        if pack:
            nodes = [node.pack() for node in nodes]
        self.len(1, nodes)
        node = nodes[0]
        self.isin('beep.morp', node[1]['tags'])
        self.isin('test.foo', node[1]['tags'])

        # Sources are made, as are seen nodes.
        q = f'source={guid} -> seen:source'
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
        await self.agenlen(1, await awaitagen(core.eval('refs')))
        await self.agenlen(1, await awaitagen(core.eval('wentto')))

    async def test_syn_ingest_remote(self):
        guid = s_common.guid()
        seen = s_common.now()
        gestdef = self.getIngestDef(guid, seen)

        # Test Remote Cortex
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            pconf = {'user': 'root', 'passwd': 'root'}
            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:

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

            await alist(core.eval('[testint=20]'))

            await self.agenlen(0, core.eval('testint>=30'))
            await self.agenlen(1, core.eval('testint>=20'))
            await self.agenlen(1, core.eval('testint>=10'))

            await self.agenlen(0, core.eval('testint>30'))
            await self.agenlen(0, core.eval('testint>20'))
            await self.agenlen(1, core.eval('testint>10'))

            await self.agenlen(0, core.eval('testint<=10'))
            await self.agenlen(1, core.eval('testint<=20'))
            await self.agenlen(1, core.eval('testint<=30'))

            await self.agenlen(0, core.eval('testint<10'))
            await self.agenlen(0, core.eval('testint<20'))
            await self.agenlen(1, core.eval('testint<30'))

            await self.agenlen(0, core.eval('testint +testint>=30'))
            await self.agenlen(1, core.eval('testint +testint>=20'))
            await self.agenlen(1, core.eval('testint +testint>=10'))

            await self.agenlen(0, core.eval('testint +testint>30'))
            await self.agenlen(0, core.eval('testint +testint>20'))
            await self.agenlen(1, core.eval('testint +testint>10'))

            await self.agenlen(0, core.eval('testint +testint<=10'))
            await self.agenlen(1, core.eval('testint +testint<=20'))
            await self.agenlen(1, core.eval('testint +testint<=30'))

            await self.agenlen(0, core.eval('testint +testint<10'))
            await self.agenlen(0, core.eval('testint +testint<20'))
            await self.agenlen(1, core.eval('testint +testint<30'))

            # time indx is derived from the same lift helpers
            await alist(core.eval('[teststr=foo :tick=201808021201]'))

            await self.agenlen(0, core.eval('teststr:tick>=201808021202'))
            await self.agenlen(1, core.eval('teststr:tick>=201808021201'))
            await self.agenlen(1, core.eval('teststr:tick>=201808021200'))

            await self.agenlen(0, core.eval('teststr:tick>201808021202'))
            await self.agenlen(0, core.eval('teststr:tick>201808021201'))
            await self.agenlen(1, core.eval('teststr:tick>201808021200'))

            await self.agenlen(1, core.eval('teststr:tick<=201808021202'))
            await self.agenlen(1, core.eval('teststr:tick<=201808021201'))
            await self.agenlen(0, core.eval('teststr:tick<=201808021200'))

            await self.agenlen(1, core.eval('teststr:tick<201808021202'))
            await self.agenlen(0, core.eval('teststr:tick<201808021201'))
            await self.agenlen(0, core.eval('teststr:tick<201808021200'))

            await self.agenlen(0, core.eval('teststr +teststr:tick>=201808021202'))
            await self.agenlen(1, core.eval('teststr +teststr:tick>=201808021201'))
            await self.agenlen(1, core.eval('teststr +teststr:tick>=201808021200'))

            await self.agenlen(0, core.eval('teststr +teststr:tick>201808021202'))
            await self.agenlen(0, core.eval('teststr +teststr:tick>201808021201'))
            await self.agenlen(1, core.eval('teststr +teststr:tick>201808021200'))

            await self.agenlen(1, core.eval('teststr +teststr:tick<=201808021202'))
            await self.agenlen(1, core.eval('teststr +teststr:tick<=201808021201'))
            await self.agenlen(0, core.eval('teststr +teststr:tick<=201808021200'))

            await self.agenlen(1, core.eval('teststr +teststr:tick<201808021202'))
            await self.agenlen(0, core.eval('teststr +teststr:tick<201808021201'))
            await self.agenlen(0, core.eval('teststr +teststr:tick<201808021200'))

            await alist(core.eval('[testint=99999]'))
            await self.agenlen(1, core.eval('testint<=20'))
            await self.agenlen(2, core.eval('testint>=20'))
            await self.agenlen(1, core.eval('testint>20'))
            await self.agenlen(0, core.eval('testint<20'))

    async def test_cortex_ontag(self):

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

            async with await core.snap() as snap:

                node = await snap.addNode('teststr', 'hehe')
                await node.addTag('foo.bar.baz', valu=(200, 300))

                self.eq(tags.get('foo'), (None, None))
                self.eq(tags.get('foo.bar'), (None, None))
                self.eq(tags.get('foo.bar.baz'), (200, 300))

                await node.delTag('foo.bar')

                self.eq(tags.get('foo'), (None, None))

                self.none(tags.get('foo.bar'))
                self.none(tags.get('foo.bar.baz'))

    async def test_cortex_del_univ(self):

        async with self.getTestCore() as core:

            core.model.addUnivProp('hehe', ('int', {}), {})

            await self.agenlen(1, core.eval('[ teststr=woot .hehe=20 ]'))
            await self.agenlen(1, core.eval('.hehe'))
            await self.agenlen(1, core.eval('.hehe [ -.hehe ]'))
            await self.agenlen(0, core.eval('.hehe'))

    async def test_cortex_snap_eval(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                await self.agenlen(2, snap.eval('[teststr=foo teststr=bar]'))
            await self.agenlen(2, core.eval('teststr'))

    async def test_feed_syn_nodes(self):
        async with self.getTestCore() as core0:
            q = '[testint=1 testint=2 testint=3]'
            podes = [n.pack() async for n in core0.eval(q)]
            self.len(3, podes)
        async with self.getTestCore() as core1:
            await core1.addFeedData('syn.nodes', podes)
            await self.agenlen(3, core1.eval('testint'))

    async def test_stat(self):

        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            coreiden = dmon.shared['core'].iden
            pconf = {'user': 'root', 'passwd': 'root'}
            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:
                ostat = await core.stat()
                self.eq(ostat.get('iden'), coreiden)
                self.isin('layer', ostat)
                await self.agenlen(1, (await core.eval('sudo | [teststr=123 :tick=2018]')))
                nstat = await core.stat()
                self.gt(nstat.get('layer').get('splicelog_indx'), ostat.get('layer').get('splicelog_indx'))

    async def test_offset(self):
        async with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            pconf = {'user': 'root', 'passwd': 'root'}
            async with await self.agetTestProxy(dmon, 'core', **pconf) as core:
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
            node = (await alist(core.eval('[ teststr=foo +#bar ] { [ +#baz ] -#bar }')))[0]
            self.nn(node.getTag('baz'))

            nodes = await alist(core.eval('[ teststr=oof +#bar ] { [ testint=0xdeadbeef ] }'))
            await self.agenlen(1, core.eval('testint=3735928559'))

        # Test using subqueries for filtering
        async with self.getTestCore() as core:
            # Generic tests

            await self.agenlen(1, core.eval('[ teststr=bar +#baz ]'))
            await self.agenlen(1, core.eval('[ pivcomp=(foo,bar) ]'))

            await self.agenlen(0, core.eval('pivcomp=(foo,bar) -{ :lulz -> teststr +#baz }'))
            await self.agenlen(1, core.eval('pivcomp=(foo,bar) +{ :lulz -> teststr +#baz } +pivcomp'))

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

    async def test_storm_cond_not(self):

        async with self.getTestCore() as core:

            await self.agenlen(1, core.eval('[ teststr=foo +#bar ]'))
            await self.agenlen(1, core.eval('[ teststr=foo +#bar ] +(not .seen)'))
            await self.agenlen(1, core.eval('[ teststr=foo +#bar ] +(#baz or not .seen)'))

    async def test_storm_minmax(self):

        async with self.getTestCore() as core:

            minval = core.model.type('time').norm('2015')[0]
            maxval = core.model.type('time').norm('2017')[0]

            await self.agenlen(1, core.eval('[ testguid="*" :tick=2015 ]'))
            await self.agenlen(1, core.eval('[ testguid="*" :tick=2016 ]'))
            await self.agenlen(1, core.eval('[ testguid="*" :tick=2017 ]'))

            async for node in core.eval('testguid | max tick'):
                self.eq(node.get('tick'), maxval)

            async for node in core.eval('testguid | min tick'):
                self.eq(node.get('tick'), minval)

    async def test_storm_totags(self):

        async with self.getTestCore() as core:

            nodes = await alist(core.eval('[ teststr=visi +#foo.bar ] -> #'))

            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'foo.bar')

            await self.agenlen(2, core.eval('teststr=visi -> #*'))
            await self.agenlen(1, core.eval('teststr=visi -> #foo.*'))
            await self.agenlen(0, core.eval('teststr=visi -> #baz.*'))

    async def test_storm_fromtags(self):

        async with self.getTestCore() as core:

            await alist(core.eval('[ teststr=visi testint=20 +#foo.bar ]'))

            nodes = await alist(core.eval('syn:tag=foo.bar -> teststr'))
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'visi')

            await self.agenlen(2, core.eval('syn:tag=foo.bar -> *'))

            await self.agenraises(s_exc.BadTypeValu, core.eval('syn:tag=foo.bar -> teststr:tick'))

    async def test_storm_tagtags(self):

        async with self.getTestCore() as core:

            await core.eval('[ teststr=visi +#foo.bar ] -> # [ +#baz.faz ]').spin()

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

            async def doit():
                return await core.eval('[ inet:ipv4=1.2.3.4 inet:ipv4=5.6.7.8 ] | sleep 0.5').spin()

            task = core.schedCoro(doit())

            runts = core.ps()
            self.len(1, runts)
            runts[0][1].cancel()

            await self.asyncraises(Cancel, task)

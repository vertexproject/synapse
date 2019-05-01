import asyncio

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class StormTest(s_t_utils.SynTest):

    async def test_storm_sudo(self):

        async with self.getTestCore() as core:

            user = await core.auth.addUser('sudoer')

            async with core.getLocalProxy(user='sudoer') as prox:

                with self.raises(s_exc.AuthDeny):
                    await s_common.aspin(prox.eval('[ test:str=woot ]'))

                with self.raises(s_exc.AuthDeny):
                    await s_common.aspin(prox.eval('sudo | [ test:str=woot ]'))

                rule = (True, ('storm', 'cmd', 'sudo'))

                await user.addRule(rule)

                with self.raises(s_exc.AuthDeny):
                    await s_common.aspin(prox.eval('[ test:str=woot ]'))

                await s_common.aspin(prox.eval('sudo | [ test:str=woot ]'))

    async def test_storm_movetag(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'foo')
                await node.addTag('hehe.haha', valu=(20, 30))

                tagnode = await snap.getNodeByNdef(('syn:tag', 'hehe.haha'))

                await tagnode.set('doc', 'haha doc')
                await tagnode.set('title', 'haha title')

            await s_common.aspin(core.eval('movetag #hehe #woot'))

            await self.agenlen(0, core.eval('#hehe'))
            await self.agenlen(0, core.eval('#hehe.haha'))

            await self.agenlen(1, core.eval('#woot'))
            await self.agenlen(1, core.eval('#woot.haha'))

            async with await core.snap() as snap:

                newt = await core.getNodeByNdef(('syn:tag', 'woot.haha'))

                self.eq(newt.get('doc'), 'haha doc')
                self.eq(newt.get('title'), 'haha title')

                node = await snap.getNodeByNdef(('test:str', 'foo'))
                self.eq((20, 30), node.tags.get('woot.haha'))

                self.none(node.tags.get('hehe'))
                self.none(node.tags.get('hehe.haha'))

                node = await snap.getNodeByNdef(('syn:tag', 'hehe'))
                self.eq('woot', node.get('isnow'))

                node = await snap.getNodeByNdef(('syn:tag', 'hehe.haha'))
                self.eq('woot.haha', node.get('isnow'))

                node = await snap.addNode('test:str', 'bar')

                # test isnow plumbing
                await node.addTag('hehe.haha')

                self.nn(node.tags.get('woot'))
                self.nn(node.tags.get('woot.haha'))

                self.none(node.tags.get('hehe'))
                self.none(node.tags.get('hehe.haha'))

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'foo')
                await node.addTag('hehe', valu=(20, 30))

                tagnode = await snap.getNodeByNdef(('syn:tag', 'hehe'))

                await tagnode.set('doc', 'haha doc')

            await s_common.aspin(core.eval('movetag #hehe #woot'))

            await self.agenlen(0, core.eval('#hehe'))
            await self.agenlen(1, core.eval('#woot'))

            async with await core.snap() as snap:
                newt = await core.getNodeByNdef(('syn:tag', 'woot'))

                self.eq(newt.get('doc'), 'haha doc')

        # Test moving a tag which has tags on it.
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'V')
                await node.addTag('a.b.c', (None, None))
                tnode = await snap.getNodeByNdef(('syn:tag', 'a.b'))
                await tnode.addTag('foo', (None, None))

            await alist(core.eval('movetag #a.b #a.m'))
            await self.agenlen(2, core.eval('#foo'))
            await self.agenlen(1, core.eval('syn:tag=a.b +#foo'))
            await self.agenlen(1, core.eval('syn:tag=a.m +#foo'))

        # Test moving a tag to itself
        async with self.getTestCore() as core:
            await self.agenraises(s_exc.BadOperArg, core.eval('movetag #foo.bar #foo.bar'))

        # Test moving a tag which does not exist
        async with self.getTestCore() as core:
            await self.agenraises(s_exc.BadOperArg, core.eval('movetag #foo.bar #duck.knight'))

        # Test moving a tag to another tag which is a string prefix of the source
        async with self.getTestCore() as core:
            # core.conf['storm:log'] = True
            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'V')
                await node.addTag('aaa.b.ccc', (None, None))
                await node.addTag('aaa.b.ddd', (None, None))
                node = await snap.addNode('test:str', 'Q')
                await node.addTag('aaa.barbarella.ccc', (None, None))

            await alist(core.eval('movetag #aaa.b #aaa.barbarella'))

            await self.agenlen(7, core.eval('syn:tag'))
            await self.agenlen(1, core.eval('syn:tag=aaa.barbarella.ccc'))
            await self.agenlen(1, core.eval('syn:tag=aaa.barbarella.ddd'))

    async def test_storm_spin(self):

        async with self.getTestCore() as core:

            await self.agenlen(0, core.eval('[ test:str=foo test:str=bar ] | spin'))
            await self.agenlen(2, core.eval('test:str=foo test:str=bar'))

    async def test_storm_reindex(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                node = await snap.addNode('inet:ipv4', '127.0.0.1')
                self.eq('loopback', node.get('type'))
                await node.set('type', 'borked')

            await s_common.aspin(core.eval('inet:ipv4 | reindex --subs'))

            async with await core.snap() as snap:
                node = await snap.getNodeByNdef(('inet:ipv4', 0x7f000001))
                self.eq('loopback', node.get('type'))

        async with self.getTestCore() as core:
            # Set handlers
            async def _onAdd(node):
                await node.snap.fire('test:node:add')

            async def _onSet(node, oldv):
                await node.snap.fire('test:prop:set')

            async def _onTagAdd(node, tag, valu):
                await node.snap.fire('test:tag:add')

            core.model.form('test:str').onAdd(_onAdd)
            core.model.prop('test:str:tick').onSet(_onSet)
            core.onTagAdd('test.tag', _onTagAdd)

            nodes = await core.eval('[test:str=beep :tick=3001 +#test.tag.foo]').list()
            self.len(1, nodes)

            nodes = await core.eval('[test:str=newp]').list()
            self.len(1, nodes)

            nodes = await core.eval('[test:guid="*" :tick=3001 +#test.bleep.bloop]').list()
            self.len(1, nodes)

            args = [('--fire-handler=test:str', 'test:node:add'),
                    ('--fire-handler=test:str:tick', 'test:prop:set'),
                    ('--fire-handler=#test.tag', 'test:tag:add')]
            for arg, ename in args:
                async with await core.snap() as snap:
                    events = {}
                    async def func(event):
                        name, _ = event
                        events[name] = True
                    snap.link(func)
                    q = 'test:str=beep | reindex ' + arg
                    nodes = await snap.storm(q).list()
                    self.true(events.get(ename))
                    # sad path in loop
                    events.clear()
                    q = 'test:guid | reindex ' + arg
                    nodes = await snap.storm(q).list()
                    self.eq(events, {})

            # More sad paths
            async with await core.snap() as snap:
                events = {}

                async def func(event):
                    name, _ = event
                    events[name] = True

                snap.link(func)
                q = 'test:str=newp | reindex --fire-handler=test:str:tick'
                nodes = await snap.storm(q).list()
                self.eq(events, {})

            await self.asyncraises(s_exc.NoSuchProp, core.eval('reindex --fire-handler=test:newp').list())

            # Generic sad path for not having any arguments.
            mesgs = await core.streamstorm('reindex').list()
            self.stormIsInPrint('reindex: error: one of the arguments', mesgs)
            self.stormIsInPrint('is required', mesgs)

    async def test_storm_count(self):

        async with self.getTestCoreAndProxy() as (realcore, core):
            await self.agenlen(2, core.eval('[ test:str=foo test:str=bar ]'))

            mesgs = await alist(core.storm('test:str=foo test:str=bar | count |  [+#test.tag]'))
            nodes = [mesg for mesg in mesgs if mesg[0] == 'node']
            self.len(2, nodes)
            prints = [mesg for mesg in mesgs if mesg[0] == 'print']
            self.len(1, prints)
            self.eq(prints[0][1].get('mesg'), 'Counted 2 nodes.')

            mesgs = await alist(core.storm('test:str=newp | count'))
            prints = [mesg for mesg in mesgs if mesg[0] == 'print']
            self.len(1, prints)
            self.eq(prints[0][1].get('mesg'), 'Counted 0 nodes.')
            nodes = [mesg for mesg in mesgs if mesg[0] == 'node']
            self.len(0, nodes)

    async def test_storm_uniq(self):
        async with self.getTestCore() as core:
            q = "[test:comp=(123, test) test:comp=(123, duck) test:comp=(123, mode)]"
            await self.agenlen(3, core.eval(q))
            nodes = await alist(core.eval('test:comp -> *'))
            self.len(3, nodes)
            nodes = await alist(core.eval('test:comp -> * | uniq | count'))
            self.len(1, nodes)

    async def test_storm_iden(self):
        async with self.getTestCore() as core:
            q = "[test:str=beep test:str=boop]"
            nodes = await alist(core.eval(q))
            self.len(2, nodes)
            idens = [node.iden() for node in nodes]

            iq = ' '.join(idens)
            # Demonstrate the iden lift does pass through previous nodes in the pipeline
            q = f'[test:str=hehe] | iden {iq} | count'
            mesgs = await alist(core.storm(q))
            self.len(3, mesgs)

            q = 'iden newp'
            with self.getLoggerStream('synapse.lib.snap', 'Failed to decode iden') as stream:
                await self.agenlen(0, core.eval(q))
                self.true(stream.wait(1))

            q = 'iden deadb33f'
            with self.getLoggerStream('synapse.lib.snap', 'iden must be 32 bytes') as stream:
                await self.agenlen(0, core.eval(q))
                self.true(stream.wait(1))

    async def test_storm_input(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:

                node = await snap.addNode('test:str', 'woot')
                await s_common.aspin(node.storm('[ +#hehe ]'))

                await self.agenlen(1, snap.eval('#hehe'))

                await s_common.aspin(node.storm('[ -#hehe ]'))
                await self.agenlen(0, snap.eval('#hehe'))

    async def test_minmax(self):

        async with self.getTestCore() as core:

            minval = core.model.type('time').norm('2015')[0]
            midval = core.model.type('time').norm('2016')[0]
            maxval = core.model.type('time').norm('2017')[0]

            async with await core.snap() as snap:
                # Ensure each node we make has its own discrete created time.
                await asyncio.sleep(0.01)
                node = await snap.addNode('test:guid', '*', {'tick': '2015',
                                                             '.seen': '2015'})
                minc = node.get('.created')
                await asyncio.sleep(0.01)
                node = await snap.addNode('test:guid', '*', {'tick': '2016',
                                                             '.seen': '2016'})
                await asyncio.sleep(0.01)
                node = await snap.addNode('test:guid', '*', {'tick': '2017',
                                                             '.seen': '2017'})
                await asyncio.sleep(0.01)
                node = await snap.addNode('test:str', '1', {'tick': '2016'})

            # Relative paths
            nodes = await core.eval('test:guid | max :tick').list()
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), maxval)

            nodes = await core.eval('test:guid | min :tick').list()
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), minval)

            # Full paths
            nodes = await core.eval('test:guid | max test:guid:tick').list()
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), maxval)

            nodes = await core.eval('test:guid | min test:guid:tick').list()
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), minval)

            # Implicit form filtering with a full path
            nodes = await core.eval('.created | max test:str:tick').list()
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), midval)

            nodes = await core.eval('.created | min test:str:tick').list()
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), midval)

            # Universal prop for relative path
            nodes = await core.eval('.created>=$minc | max .created',
                                    {'vars': {'minc': minc}}).list()
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), midval)

            nodes = await core.eval('.created>=$minc | min .created',
                                    {'vars': {'minc': minc}}).list()
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), minval)

            # Universal prop for full paths
            nodes = await core.eval('.created>=$minc  | max test:str.created',
                                    {'vars': {'minc': minc}}).list()
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), midval)

            nodes = await core.eval('.created>=$minc  | min test:str.created',
                                    {'vars': {'minc': minc}}).list()
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), midval)

            # Variables evaluated
            nodes = await core.eval('test:guid ($tick, $tock) = .seen | min $tick').list()
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), minval)

            nodes = await core.eval('test:guid ($tick, $tock) = .seen | max $tock').list()
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), maxval)

            text = '''[ inet:ipv4=1.2.3.4 inet:ipv4=5.6.7.8 ]
                      { +inet:ipv4=1.2.3.4 [ :asn=10 ] }
                      { +inet:ipv4=5.6.7.8 [ :asn=20 ] }
                      $asn = :asn | min $asn'''

            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(0x01020304, nodes[0].ndef[1])

            text = '''[ inet:ipv4=1.2.3.4 inet:ipv4=5.6.7.8 ]
                      { +inet:ipv4=1.2.3.4 [ :asn=10 ] }
                      { +inet:ipv4=5.6.7.8 [ :asn=20 ] }
                      $asn = :asn | max $asn'''

            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(0x05060708, nodes[0].ndef[1])

            # Sad paths where there are no nodes which match the specified values.
            await self.agenlen(0, core.eval('test:guid | max :newp'))
            await self.agenlen(0, core.eval('test:guid | min :newp'))

            # Sad path for a form, not a property; and does not exist at all
            await self.agenraises(s_exc.BadSyntax,
                                  core.eval('test:guid | max test:newp'))
            await self.agenraises(s_exc.BadSyntax,
                                  core.eval('test:guid | min test:newp'))

    async def test_getstormeval(self):

        # Use testechocmd to exercise all of Cmd.getStormEval
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'fancystr',
                                          {'tick': 1234,
                                           'hehe': 'haha',
                                           '.seen': '3001'})

            q = 'test:str $foo=:tick | testechocmd $foo'
            mesgs = await core.streamstorm(q).list()
            self.stormIsInPrint('[1234]', mesgs)

            q = 'test:str| testechocmd :tick'
            mesgs = await core.streamstorm(q).list()
            self.stormIsInPrint('[1234]', mesgs)

            q = 'test:str| testechocmd .seen'
            mesgs = await core.streamstorm(q).list()
            self.stormIsInPrint('[(32535216000000, 32535216000001)]', mesgs)

            q = 'test:str| testechocmd test:str'
            mesgs = await core.streamstorm(q).list()
            self.stormIsInPrint('[fancystr]', mesgs)

            q = 'test:str| testechocmd test:str:hehe'
            mesgs = await core.streamstorm(q).list()
            self.stormIsInPrint('[haha]', mesgs)

            q = 'test:str| testechocmd test:int'
            mesgs = await core.streamstorm(q).list()
            self.stormIsInPrint('[None]', mesgs)

            q = 'test:str| testechocmd test:int:loc'
            mesgs = await core.streamstorm(q).list()
            self.stormIsInPrint('[None]', mesgs)

            q = 'test:str| testechocmd test:newp'
            mesgs = await core.streamstorm(q).list()
            errs = [m for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            self.eq(errs[0][1][0], 'BadSyntax')

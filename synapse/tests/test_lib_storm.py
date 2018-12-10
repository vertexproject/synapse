import unittest

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.node as s_node

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class StormTest(s_t_utils.SynTest):

    async def test_storm_movetag(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                node = await snap.addNode('teststr', 'foo')
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

                node = await snap.getNodeByNdef(('teststr', 'foo'))
                self.eq((20, 30), node.tags.get('woot.haha'))

                self.none(node.tags.get('hehe'))
                self.none(node.tags.get('hehe.haha'))

                node = await snap.getNodeByNdef(('syn:tag', 'hehe'))
                self.eq('woot', node.get('isnow'))

                node = await snap.getNodeByNdef(('syn:tag', 'hehe.haha'))
                self.eq('woot.haha', node.get('isnow'))

                node = await snap.addNode('teststr', 'bar')

                # test isnow plumbing
                await node.addTag('hehe.haha')

                self.nn(node.tags.get('woot'))
                self.nn(node.tags.get('woot.haha'))

                self.none(node.tags.get('hehe'))
                self.none(node.tags.get('hehe.haha'))

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                node = await snap.addNode('teststr', 'foo')
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
                node = await snap.addNode('teststr', 'V')
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
                node = await snap.addNode('teststr', 'V')
                await node.addTag('aaa.b.ccc', (None, None))
                await node.addTag('aaa.b.ddd', (None, None))
                node = await snap.addNode('teststr', 'Q')
                await node.addTag('aaa.barbarella.ccc', (None, None))

            await alist(core.eval('movetag #aaa.b #aaa.barbarella'))

            await self.agenlen(7, core.eval('syn:tag'))
            await self.agenlen(1, core.eval('syn:tag=aaa.barbarella.ccc'))
            await self.agenlen(1, core.eval('syn:tag=aaa.barbarella.ddd'))

    async def test_storm_spin(self):

        async with self.getTestCore() as core:

            await self.agenlen(0, core.eval('[ teststr=foo teststr=bar ] | spin'))
            await self.agenlen(2, core.eval('teststr=foo teststr=bar'))

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

    async def test_storm_count(self):

        async with self.getTestDmon(mirror='dmoncore') as dmon, \
                await self.agetTestProxy(dmon, 'core') as core:
            await self.agenlen(2, await core.eval('[ teststr=foo teststr=bar ]'))

            mesgs = await alist(await core.storm('teststr=foo teststr=bar | count |  [+#test.tag]'))
            nodes = [mesg for mesg in mesgs if mesg[0] == 'node']
            self.len(2, nodes)
            prints = [mesg for mesg in mesgs if mesg[0] == 'print']
            self.len(1, prints)
            self.eq(prints[0][1].get('mesg'), 'Counted 2 nodes.')

            mesgs = await alist(await core.storm('teststr=newp | count'))
            prints = [mesg for mesg in mesgs if mesg[0] == 'print']
            self.len(1, prints)
            self.eq(prints[0][1].get('mesg'), 'Counted 0 nodes.')
            nodes = [mesg for mesg in mesgs if mesg[0] == 'node']
            self.len(0, nodes)

    async def test_storm_uniq(self):
        async with self.getTestCore() as core:
            q = "[testcomp=(123, test) testcomp=(123, duck) testcomp=(123, mode)]"
            await self.agenlen(3, core.eval(q))
            nodes = await alist(core.eval('testcomp -> *'))
            self.len(3, nodes)
            nodes = await alist(core.eval('testcomp -> * | uniq | count'))
            self.len(1, nodes)

    async def test_storm_iden(self):
        async with self.getTestCore() as core:
            q = "[teststr=beep teststr=boop]"
            nodes = await alist(core.eval(q))
            self.len(2, nodes)
            idens = [node.iden() for node in nodes]

            iq = ' '.join(idens)
            # Demonstrate the iden lift does pass through previous nodes in the pipeline
            q = f'[teststr=hehe] | iden {iq} | count'
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

                node = await snap.addNode('teststr', 'woot')
                await s_common.aspin(node.storm('[ +#hehe ]'))

                await self.agenlen(1, snap.eval('#hehe'))

                await s_common.aspin(node.storm('[ -#hehe ]'))
                await self.agenlen(0, snap.eval('#hehe'))

    async def test_noderefs(self):

        async with self.getTestCore() as core:
            await self.agenlen(1, core.eval('[pivcomp=(foo, 123)]'))
            tguid = s_common.guid()
            await self.agenlen(1, core.eval(f'[testguid={tguid} :tick=2015]'))
            await self.agenlen(1, core.eval('teststr=123 [:baz="testguid:tick=2015"]'))

            # Sad path
            await self.agenraises(s_exc.BadOperArg, core.eval('teststr | noderefs -d 0'))

            # # Default behavior is a single degree out
            q = 'pivcomp | noderefs'
            await self.agenlen(2, core.eval(q))

            # Can join input nodes to output
            q = 'pivcomp | noderefs --join'
            await self.agenlen(3, core.eval(q))

            # Can go out multiple degrees
            q = 'pivcomp | noderefs -j --degrees 2'
            await self.agenlen(4, core.eval(q))

            srcguid = s_common.guid()
            await self.agenlen(2, core.eval(f'[source={srcguid} +#omit.nopiv] [seen=({srcguid}, (pivtarg, foo))]'))

            q = 'pivcomp | noderefs --join --degrees 2'
            await self.agenlen(5, core.eval(q))

            q = 'pivcomp | noderefs --join -d 3'
            await self.agenlen(6, core.eval(q))

            # We can traverse edges in both directions
            nodes = await alist(core.eval('[refs=((teststr, 123), (testint, 123))]'))
            self.len(1, nodes)
            ref_iden = nodes[0].iden()

            q = 'teststr=123 | noderefs'
            nodes = await alist(core.eval(q))
            self.len(3, nodes)
            self.eq({n.ndef[0] for n in nodes}, {'testguid', 'refs', 'pivcomp'})

            q = 'teststr=123 | noderefs --traverse-edge'
            nodes = await alist(core.eval(q))
            self.len(3, nodes)
            self.eq({n.ndef[0] for n in nodes}, {'testguid', 'pivcomp', 'testint'})

            q = 'testint=123 | noderefs'
            nodes = await alist(core.eval(q))
            self.len(1, nodes)
            self.eq({n.ndef[0] for n in nodes}, {'refs'})

            q = 'testint=123 | noderefs -te'
            nodes = await alist(core.eval(q))
            self.len(1, nodes)
            self.eq({n.ndef[0] for n in nodes}, {'teststr'})

            # Prevent inclusion of a form, and the traversal across said form/tag
            # Use long and short form arguments
            await self.agenlen(1, core.eval(f'[seen=({srcguid}, (teststr, pennywise))]'))

            q = 'teststr=pennywise | noderefs -d 3'
            await self.agenlen(3, core.eval(q))

            q = 'teststr=pennywise | noderefs -d 3 --omit-traversal-form=source'
            await self.agenlen(2, core.eval(q))
            q = 'teststr=pennywise | noderefs -d 3 -otf=source'
            await self.agenlen(2, core.eval(q))

            q = 'teststr=pennywise | noderefs -d 3 --omit-form=source'
            await self.agenlen(1, core.eval(q))
            q = 'teststr=pennywise | noderefs -d 3 -of=source'
            await self.agenlen(1, core.eval(q))

            q = 'teststr=pennywise | noderefs -d 3 --omit-traversal-tag=omit.nopiv --omit-traversal-tag=test'
            await self.agenlen(2, core.eval(q))
            q = 'teststr=pennywise | noderefs -d 3 -ott=omit.nopiv -ott=test'
            await self.agenlen(2, core.eval(q))

            q = 'teststr=pennywise | noderefs -d 3 --omit-tag=omit'
            await self.agenlen(1, core.eval(q))
            q = 'teststr=pennywise | noderefs -d 3 -ot=omit'
            await self.agenlen(1, core.eval(q))

            # Do a huge traversal that includes paths
            q = 'teststr=pennywise | noderefs --join -d 9'
            mesgs = await alist(core.storm(q, opts={'path': True}))
            nodes = [mesg[0] for mesg in mesgs]
            self.isin(ref_iden, {n.iden() for n in nodes})
            paths = [mesg[1] for mesg in mesgs]
            self.len(10, paths)
            self.len(1, paths[0].nodes)
            self.len(9, paths[9].nodes)

            # Paths may change depending on traversal options
            q = 'teststr=pennywise | noderefs --join -d 9 --traverse-edge'
            mesgs = await alist(core.storm(q, opts={'path': True}))
            nodes = [mesg[0] for mesg in mesgs]
            self.notin(ref_iden, {n.iden() for n in nodes})
            paths = [mesg[1] for mesg in mesgs]
            self.len(9, paths)
            self.len(1, paths[0].nodes)
            self.len(9, paths[8].nodes)
            # Ensure that the ref_iden is present in the path since
            # we did move through it.
            self.isin(ref_iden, {n.iden() for n in paths[8].nodes})

            # Start from multiple nodes and get their refs
            q = 'teststr | noderefs -d 3'
            nodes = await alist(core.eval(q))
            self.len(9, nodes)

            # Refs from multiple sources may be globally uniqued
            q = 'teststr | noderefs -d 3 --unique'
            nodes = await alist(core.eval(q))
            self.len(8, nodes)

            # And he has a short arg too
            q = 'teststr | noderefs -d 3 -u'
            nodes = await alist(core.eval(q))
            self.len(8, nodes)

            # Coverage for the pivot-in optimization.
            guid = s_common.guid()
            await alist(core.eval(f'[inet:ipv4=1.2.3.4 :asn=10] [seen=({guid}, (inet:asn, 10))]'))
            nodes = await alist(core.eval('inet:asn=10 | noderefs -of inet:ipv4 --join -d 3'))
            forms = {node.form.full for node in nodes}
            self.eq(forms, {'source', 'inet:asn', 'seen'})

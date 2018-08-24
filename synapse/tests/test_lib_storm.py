import synapse.common as s_common
import synapse.lib.storm as s_storm

import synapse.tests.common as s_test_common

class StormTest(s_test_common.SynTest):

    def test_storm_movetag(self):

        with self.getTestCore() as core:

            with core.snap() as snap:
                node = snap.addNode('teststr', 'foo')
                node.addTag('hehe.haha', valu=(20, 30))

                tagnode = snap.getNodeByNdef(('syn:tag', 'hehe.haha'))

                tagnode.set('doc', 'haha doc')
                tagnode.set('title', 'haha title')

            list(core.eval('movetag #hehe #woot'))

            self.len(0, list(core.eval('#hehe')))
            self.len(0, list(core.eval('#hehe.haha')))

            self.len(1, list(core.eval('#woot')))
            self.len(1, list(core.eval('#woot.haha')))

            with core.snap() as snap:

                newt = core.getNodeByNdef(('syn:tag', 'woot.haha'))

                self.eq(newt.get('doc'), 'haha doc')
                self.eq(newt.get('title'), 'haha title')

                node = snap.getNodeByNdef(('teststr', 'foo'))
                self.eq((20, 30), node.tags.get('woot.haha'))

                self.none(node.tags.get('hehe'))
                self.none(node.tags.get('hehe.haha'))

                node = snap.getNodeByNdef(('syn:tag', 'hehe'))
                self.eq('woot', node.get('isnow'))

                node = snap.getNodeByNdef(('syn:tag', 'hehe.haha'))
                self.eq('woot.haha', node.get('isnow'))

                node = snap.addNode('teststr', 'bar')

                # test isnow plumbing
                node.addTag('hehe.haha')

                self.nn(node.tags.get('woot'))
                self.nn(node.tags.get('woot.haha'))

                self.none(node.tags.get('hehe'))
                self.none(node.tags.get('hehe.haha'))

    def test_storm_spin(self):

        with self.getTestCore() as core:

            self.len(0, list(core.eval('[ teststr=foo teststr=bar ] | spin')))
            self.len(2, list(core.eval('teststr=foo teststr=bar')))

    def test_storm_reindex(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                node = snap.addNode('inet:ipv4', '127.0.0.1')
                self.eq('loopback', node.get('type'))
                node.set('type', 'borked')

            list(core.eval('inet:ipv4 | reindex --subs'))

            with core.snap() as snap:
                node = snap.getNodeByNdef(('inet:ipv4', 0x7f000001))
                self.eq('loopback', node.get('type'))

    def test_storm_count(self):

        with self.getTestCore() as core:
            self.len(2, list(core.eval('[ teststr=foo teststr=bar ]')))
            mesgs = list(core.storm('teststr=foo teststr=bar | count |  [+#test.tag]'))
            nodes = [mesg for mesg in mesgs if mesg[0] == 'node']
            self.len(2, nodes)
            prints = [mesg for mesg in mesgs if mesg[0] == 'print']
            self.len(1, prints)
            self.eq(prints[0][1].get('mesg'), 'Counted 2 nodes.')

            mesgs = list(core.storm('teststr=newp | count'))
            prints = [mesg for mesg in mesgs if mesg[0] == 'print']
            self.len(1, prints)
            self.eq(prints[0][1].get('mesg'), 'Counted 0 nodes.')
            nodes = [mesg for mesg in mesgs if mesg[0] == 'node']
            self.len(0, nodes)

    def test_storm_uniq(self):
        with self.getTestCore() as core:
            q = "[testcomp=(123, test) testcomp=(123, duck) testcomp=(123, mode)]"
            self.len(3, core.eval(q))
            nodes = list(core.eval('testcomp -> *'))
            self.len(3, nodes)
            nodes = list(core.eval('testcomp -> * | uniq | count'))
            self.len(1, nodes)

    def test_storm_iden(self):
        with self.getTestCore() as core:
            q = "[teststr=beep teststr=boop]"
            nodes = list(core.eval(q))
            self.len(2, nodes)
            idens = [node.iden() for node in nodes]

            iq = ' '.join(idens)
            # Demonstrate the iden lift does pass through previous nodes in the pipeline
            q = f'[teststr=hehe] | iden {iq} | count'
            mesgs = list(core.storm(q))
            self.len(3, [mesg for mesg in mesgs if mesg[0] == 'node'])

            q = 'iden newp'
            with self.getLoggerStream('synapse.lib.snap', 'Failed to decode iden') as stream:
                self.len(0, list(core.eval(q)))
                self.true(stream.wait(1))

    def test_refs(self):

        from pprint import pprint

        with self.getTestCore() as core:

            self.len(1, core.eval('[pivcomp=(foo, 123)]'))
            tguid = s_common.guid()
            self.len(1, core.eval(f'[testguid={tguid} :tick=2015]'))
            self.len(1, core.eval('teststr=123 [:baz="testguid:tick=2015"]'))

            # Default behavior is a single degree out
            q = 'pivcomp | refs'
            self.len(2, core.eval(q))

            # Can join input nodes to output
            q = 'pivcomp | refs --join'
            self.len(3, core.eval(q))

            # Can go out multiple degrees
            q = 'pivcomp | refs --join --degrees 2'
            self.len(4, core.eval(q))

            srcguid = s_common.guid()
            self.len(2, core.eval(f'[source={srcguid} +#omit.nopiv] [seen=({srcguid}, (pivtarg, foo))]'))

            q = 'pivcomp | refs --join --degrees 2'
            self.len(5, core.eval(q))

            q = 'pivcomp | refs --join --degrees 3'
            self.len(6, core.eval(q))

            # We can traverse edges in both directions
            self.len(1, core.eval('[refs=((teststr, 123), (testint, 123))]'))

            q = 'teststr=123 | refs'
            nodes = list(core.eval(q))
            self.len(3, nodes)
            self.eq({n.ndef[0] for n in nodes}, {'testguid', 'refs', 'pivcomp'})

            q = 'teststr=123 | refs --traverse-edge'
            nodes = list(core.eval(q))
            self.len(3, nodes)
            self.eq({n.ndef[0] for n in nodes}, {'testguid', 'pivcomp', 'testint'})

            q = 'testint=123 | refs'
            nodes = list(core.eval(q))
            self.len(1, nodes)
            self.eq({n.ndef[0] for n in nodes}, {'refs'})

            q = 'testint=123 | refs --traverse-edge'
            nodes = list(core.eval(q))
            self.len(1, nodes)
            self.eq({n.ndef[0] for n in nodes}, {'teststr'})

            # Prevent inclusion of a form, and the traversal across said form/tag
            self.len(1, core.eval(f'[seen=({srcguid}, (teststr, pennywise))]'))

            q = 'teststr=pennywise | refs -d 3'
            self.len(3, core.eval(q))
            q = 'teststr=pennywise | refs -d 3 --omit-traversal-form=source'
            self.len(2, core.eval(q))
            q = 'teststr=pennywise | refs -d 3 --omit-form=source'
            self.len(1, core.eval(q))

            q = 'teststr=pennywise | refs -d 3 --omit-traversal-tag=omit.nopiv --omit-traversal-tag=test'
            self.len(2, core.eval(q))
            q = 'teststr=pennywise | refs -d 3 --omit-tag=omit'
            self.len(1, core.eval(q))

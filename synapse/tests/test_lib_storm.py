import synapse.common as s_common
import synapse.lib.storm as s_storm

import synapse.tests.common as s_test_common

class StormTest(s_test_common.SynTest):

    def test_storm_movetag(self):

        with self.getTestCore() as core:

            with core.snap() as snap:
                node = snap.addNode('teststr', 'foo')
                node.addTag('hehe.haha', valu=(20, 30))

            list(core.eval('movetag #hehe #woot'))

            self.len(0, list(core.eval('#hehe')))
            self.len(0, list(core.eval('#hehe.haha')))

            self.len(1, list(core.eval('#woot')))
            self.len(1, list(core.eval('#woot.haha')))

            with core.snap() as snap:

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

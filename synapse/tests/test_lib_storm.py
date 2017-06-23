import synapse.cortex as s_cortex
import synapse.lib.storm as s_storm
import synapse.cores.common as s_common

from synapse.tests.common import *

class StormTest(SynTest):
    def test_storm_cmpr_norm(self):
        with s_cortex.openurl('ram:///') as core:
            core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            self.eq(len(core.eval('inet:dns:a:ipv4="1.2.3.4"')), 1)
            self.eq(len(core.eval('inet:dns:a:ipv4="1.2.3.4" -:ipv4="1.2.3.4"')), 0)
            self.eq(len(core.eval('inet:dns:a:ipv4="1.2.3.4" +:ipv4="1.2.3.4"')), 1)

    def test_storm_pivot(self):
        with s_cortex.openurl('ram:///') as core:
            core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            core.formTufoByProp('inet:dns:a', 'vertex.vis/5.6.7.8')
            core.formTufoByProp('inet:dns:a', 'vertex.link/5.6.7.8')

            node = core.eval('inet:ipv4="1.2.3.4" inet:ipv4->inet:dns:a:ipv4')[0]

            self.nn(node)
            self.eq(node[1].get('inet:dns:a'), 'woot.com/1.2.3.4')

            node = core.eval('inet:dns:a="woot.com/1.2.3.4" :ipv4->inet:ipv4')[0]

            self.nn(node)
            self.eq(node[1].get('inet:ipv4'), 0x01020304)

            node = core.eval('inet:fqdn="woot.com" ->inet:dns:a:fqdn')[0]

            self.nn(node)
            self.eq(node[1].get('inet:dns:a'), 'woot.com/1.2.3.4')

            self.eq(len(core.eval('inet:dns:a:ipv4="5.6.7.8" :fqdn->inet:fqdn')), 2)

            self.eq(len(core.eval('inet:ipv4="5.6.7.8" -> inet:dns:a:ipv4')), 2)
            self.eq(len(core.eval('inet:ipv4="5.6.7.8" inet:ipv4->inet:dns:a:ipv4')), 2)

    def test_storm_setprop(self):
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce',1)

            node = core.formTufoByProp('inet:fqdn', 'vertex.link')

            node = core.eval('inet:fqdn=vertex.link setprop(created="2016-05-05",updated="2017/05/05")')[0]

            self.eq(node[1].get('inet:fqdn'), 'vertex.link')
            self.eq(node[1].get('inet:fqdn:created'), 1462406400000)
            self.eq(node[1].get('inet:fqdn:updated'), 1493942400000)

    def test_storm_filt_regex(self):

        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce',1)

            iden0 = guid()
            iden1 = guid()
            iden2 = guid()

            node0 = core.formTufoByProp('file:bytes', iden0)
            node1 = core.formTufoByProp('file:bytes', iden1, name='woot.exe')
            node2 = core.formTufoByProp('file:bytes', iden2, name='toow.exe')

            nodes = core.eval('file:bytes +:name~=exe')
            self.eq( len(nodes), 2 )

    def test_storm_alltag(self):

        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce',1)

            iden = guid()
            node = core.formTufoByProp('inet:fqdn','vertex.link')

            core.addTufoTag(node,'foo.bar')
            core.addTufoTag(node,'baz.faz')

            node = core.eval('#foo.bar')[0]

            self.eq( node[1].get('inet:fqdn'), 'vertex.link' )

            self.nn( node[1].get('#baz') )
            self.nn( node[1].get('#foo.bar') )

    def test_storm_addtag(self):
        with s_cortex.openurl('ram:///') as core:
            iden = guid()
            node = core.formTufoByProp('inet:fqdn', 'vertex.link')

            node = core.eval('inet:fqdn=vertex.link addtag(foo.bar,baz.faz)')[0]

            self.eq(node[1].get('inet:fqdn'), 'vertex.link')

            self.nn(node[1].get('#foo'))
            self.nn(node[1].get('#foo.bar'))
            self.nn(node[1].get('#baz'))
            self.nn(node[1].get('#baz.faz'))

    def test_storm_deltag(self):
        with s_cortex.openurl('ram:///') as core:
            iden = guid()
            node = core.formTufoByProp('inet:fqdn', 'vertex.link')

            core.addTufoTag(node, 'foo.bar')
            core.addTufoTag(node, 'baz.faz')

            node = core.eval('inet:fqdn=vertex.link deltag(foo,baz.faz)')[0]

            self.eq(node[1].get('inet:fqdn'), 'vertex.link')

            self.nn(node[1].get('#baz'))
            self.none(node[1].get('#foo'))
            self.none(node[1].get('#foo.bar'))
            self.none(node[1].get('#baz.faz'))

    def test_storm_refs(self):

        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce',1)

            iden = guid()
            core.formTufoByProp('inet:dns:a','foo.com/1.2.3.4')
            core.formTufoByProp('inet:dns:a','bar.com/1.2.3.4')

            self.eq( len(core.eval('inet:ipv4=1.2.3.4 refs(in)')), 3 )
            self.eq( len(core.eval('inet:ipv4=1.2.3.4 refs(in,limit=1)')), 2 )

            self.eq( len(core.eval('inet:dns:a=foo.com/1.2.3.4 refs(out)')), 3 )
            self.eq( len(core.eval('inet:dns:a=foo.com/1.2.3.4 refs(out,limit=1)')), 2 )

    def test_storm_tag_query(self):
        # Ensure that non-glob tag filters operate as expected.
        with s_cortex.openurl('ram:///') as core:  # type: s_common.Cortex
            node1 = core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            node2 = core.formTufoByProp('inet:dns:a', 'vertex.vis/5.6.7.8')
            node3 = core.formTufoByProp('inet:dns:a', 'vertex.link/5.6.7.8')

            core.addTufoTags(node1, ['aka.foo.bar.baz', 'aka.duck.quack.loud', 'src.clowntown'])
            core.addTufoTags(node2, ['aka.foo.duck.baz', 'aka.duck.quack.loud', 'src.clowntown'])
            core.addTufoTags(node3, ['aka.foo.bar.knight', 'aka.duck.sound.loud', 'src.clowntown'])

            nodes = core.eval('inet:dns:a +#src.clowntown')
            self.eq(len(nodes), 3)

            nodes = core.eval('inet:dns:a +#src')
            self.eq(len(nodes), 3)

            nodes = core.eval('inet:dns:a +#aka.duck.quack')
            self.eq(len(nodes), 2)

            nodes = core.eval('inet:dns:a +#aka.foo.bar.knight')
            self.eq(len(nodes), 1)

            nodes = core.eval('inet:dns:a +#src.internet')
            self.eq(len(nodes), 0)

            nodes = core.eval('inet:dns:a -#aka.foo.bar')
            self.eq(len(nodes), 1)

    def test_storm_tag_glob(self):
        # Ensure that glob operators with tag filters operate properly.
        with s_cortex.openurl('ram:///') as core:  # type: s_common.Cortex
            node1 = core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            node2 = core.formTufoByProp('inet:dns:a', 'vertex.vis/5.6.7.8')
            node3 = core.formTufoByProp('inet:dns:a', 'vertex.link/5.6.7.8')
            node4 = core.formTufoByProp('inet:dns:a', 'clowntown.link/10.11.12.13')

            core.addTufoTags(node1, ['aka.bar.baz',
                                     'aka.duck.quack.loud',
                                     'src.clowntown',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.ca.san_francisco'])
            core.addTufoTags(node2, ['aka.duck.baz',
                                     'aka.duck.quack.loud',
                                     'src.clowntown',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.va.san_francisco'])
            core.addTufoTags(node3, ['aka.bar.knight',
                                     'aka.duck.sound.loud',
                                     'src.clowntown',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.nv.perfection'])
            core.addTufoTags(node4, ['aka.bar.knightdark',
                                     'aka.duck.sound.loud',
                                     'src.clowntown',
                                     'loc.milkyway.galactic_arm_a.sol.mars.us.tx.perfection'])

            nodes = core.eval('inet:dns:a +#aka.*.baz')
            self.eq(len(nodes), 2)

            nodes = core.eval('inet:dns:a +#aka.duck.*.loud')
            self.eq(len(nodes), 4)

            nodes = core.eval('inet:dns:a +#aka.*.sound.loud')
            self.eq(len(nodes), 2)

            nodes = core.eval('inet:dns:a -#aka.*.baz')
            self.eq(len(nodes), 2)

            nodes = core.eval('inet:dns:a +#aka.*.loud')
            self.eq(len(nodes), 0)

            nodes = core.eval('inet:dns:a +#aka.*.*.loud')
            self.eq(len(nodes), 4)

            nodes = core.eval('inet:dns:a +#aka.*.*.*.loud')
            self.eq(len(nodes), 0)

            nodes = core.eval('inet:dns:a +#aka.*.knight')
            self.eq(len(nodes), 1)

            nodes = core.eval('inet:dns:a +#aka.**.loud')
            self.eq(len(nodes), 4)

            nodes = core.eval('inet:dns:a +#loc.**.perfection')
            self.eq(len(nodes), 2)

            nodes = core.eval('inet:dns:a +#loc.**.sol.*.us')
            self.eq(len(nodes), 4)

            nodes = core.eval('inet:dns:a +#loc.*.galactic_arm_a.**.us.*.perfection')
            self.eq(len(nodes), 2)

            nodes = core.eval('inet:dns:a +#**.baz')
            self.eq(len(nodes), 2)

            nodes = core.eval('inet:dns:a +#**.mars')
            self.eq(len(nodes), 1)

            nodes = core.eval('inet:dns:a -#**.mars.*.tx')
            self.eq(len(nodes), 3)

            nodes = core.eval('inet:dns:a +#loc.milkyway.*arm*.**.tx')
            self.eq(len(nodes), 1)

            nodes = core.eval('inet:dns:a +#loc.**.u*')
            self.eq(len(nodes), 4)

            nodes = core.eval('inet:dns:a +#loc.milkyway.galactic**.tx')
            self.eq(len(nodes), 1)

    def test_storm_tag_jointag(self):
        with s_cortex.openurl('ram:///') as core:  # type: s_common.Cortex
            node1 = core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            node2 = core.formTufoByProp('inet:fqdn', 'vertex.vis')
            node3 = core.formTufoByProp('inet:url', 'https://vertex.link')
            node4 = core.formTufoByProp('inet:netuser', 'clowntown.link/pennywise')

            core.addTufoTags(node1, ['aka.bar.baz',
                                     'aka.duck.quack.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.ca.san_francisco'])
            core.addTufoTags(node2, ['aka.duck.baz',
                                     'aka.duck.quack.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.va.san_francisco'])
            core.addTufoTags(node3, ['aka.bar.knight',
                                     'aka.duck.sound.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.nv.perfection'])
            core.addTufoTags(node4, ['aka.bar.knightdark',
                                     'aka.duck.sound.loud',
                                     'loc.milkyway.galactic_arm_a.sol.mars.us.tx.perfection'])

            nodes = core.eval('inet:dns:a jointags()')
            self.eq(len(nodes), 2)

            nodes = core.eval('inet:dns:a jointags(inet:fqdn, limit=2)')
            self.eq(len(nodes), 1)
            self.eq(nodes[0][1].get('tufo:form'), 'inet:fqdn')

            nodes = core.eval('inet:dns:a jointags(ps:tokn, inet:fqdn)')
            self.eq(len(nodes), 1)
            self.eq(nodes[0][1].get('tufo:form'), 'inet:fqdn')

            nodes = core.eval('inet:dns:a jointags(ps:tokn)')
            self.eq(len(nodes), 0)

            nodes = core.eval('inet:dns:a jointags(ps:tokn, keep_nodes=1)')
            self.eq(len(nodes), 1)

            nodes = core.eval('inet:dns:a jointags(inet:fqdn, keep_nodes=1)')
            self.eq(len(nodes), 2)

            nodes = core.eval('inet:dns:a jointags(limit=1)')
            self.eq(len(nodes), 1)

    def test_storm_tag_totag(self):
        with s_cortex.openurl('ram:///') as core:  # type: s_common.Cortex
            node1 = core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            node2 = core.formTufoByProp('inet:fqdn', 'vertex.vis')
            node3 = core.formTufoByProp('inet:url', 'https://vertex.link')
            node4 = core.formTufoByProp('inet:netuser', 'clowntown.link/pennywise')
            node5 = core.formTufoByProp('geo:loc', 'derry')

            core.addTufoTags(node1, ['aka.bar.baz',
                                     'aka.duck.quack.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.ca.san_francisco'])
            core.addTufoTags(node2, ['aka.duck.baz',
                                     'aka.duck.quack.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.va.san_francisco'])
            core.addTufoTags(node3, ['aka.bar.knight',
                                     'aka.duck.sound.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.nv.perfection'])
            core.addTufoTags(node4, ['aka.bar.knightdark',
                                     'aka.duck.sound.loud',
                                     'loc.milkyway.galactic_arm_a.sol.mars.us.tx.perfection'])

            nodes = core.eval('inet:dns:a totags()')
            self.eq(len(nodes), 3)

            nodes = core.eval('inet:dns:a totags(leaf=0)')
            self.eq(len(nodes), 14)

            nodes = core.eval('#aka.duck.quack.loud totags()')
            self.eq(len(nodes), 5)

            nodes = core.eval('#aka.duck totags()')
            self.eq(len(nodes), 10)

            nodes = core.eval('ps:tokn totags()')
            self.eq(len(nodes), 0)

            # Tag input
            nodes = core.eval('syn:tag=aktoa.bar.baz totags()')
            self.eq(len(nodes), 0)

            # Tagless node input
            nodes = core.eval('geo:loc=derry totags()')
            self.eq(len(nodes), 0)

    def test_storm_tag_fromtag(self):
        with s_cortex.openurl('ram:///') as core:  # type: s_common.Cortex
            node1 = core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            node2 = core.formTufoByProp('inet:fqdn', 'vertex.vis')
            node3 = core.formTufoByProp('inet:url', 'https://vertex.link')
            node4 = core.formTufoByProp('inet:netuser', 'clowntown.link/pennywise')
            core.addTufoTags(node1, ['aka.bar.baz',
                                     'aka.duck.quack.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.ca.san_francisco'])
            core.addTufoTags(node2, ['aka.duck.baz',
                                     'aka.duck.quack.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.va.san_francisco'])
            core.addTufoTags(node3, ['aka.bar.knight',
                                     'aka.duck.sound.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.nv.perfection'])
            core.addTufoTags(node4, ['aka.bar.knightdark',
                                     'aka.duck.sound.loud',
                                     'loc.milkyway.galactic_arm_a.sol.mars.us.tx.perfection'])

            nodes = core.eval('syn:tag=aka.bar.baz fromtags()')
            self.eq(len(nodes), 1)

            nodes = core.eval('syn:tag=aka.bar fromtags()')
            self.eq(len(nodes), 3)

            nodes = core.eval('syn:tag=aka.duck fromtags()')
            self.eq(len(nodes), 4)

            nodes = core.eval('syn:tag=aka.bar.baz fromtags(inet:dns:a)')
            self.eq(len(nodes), 1)

            nodes = core.eval('syn:tag=aka.bar.baz fromtags(inet:dns:a, ps:tokn)')
            self.eq(len(nodes), 1)

            nodes = core.eval('syn:tag=aka.bar.baz fromtags(ps:tokn)')
            self.eq(len(nodes), 0)

            nodes = core.eval('syn:tag=spam.and.eggs fromtags()')
            self.eq(len(nodes), 0)

            nodes = core.eval('syn:tag=aka.duck fromtags(limit=2)')
            self.eq(len(nodes), 2)

            # Non-tag input
            nodes = core.eval('inet:dns:a fromtags()')
            self.eq(len(nodes), 0)

            nodes = core.eval('syn:tag:base=bar fromtags()')
            self.eq(len(nodes), 3)

    def test_storm_lift(self):

        with s_cortex.openurl('ram:///') as core:

            core.formTufoByProp('inet:ipv4','1.2.3.4')
            core.formTufoByProp('inet:ipv4','5.6.7.8')

            self.eq(2, len(core.eval('lift(inet:ipv4)')))
            self.eq(1, len(core.eval('lift(inet:ipv4, limit=1)')))
            self.eq(1, len(core.eval('lift(inet:ipv4, 1.2.3.4)')))
            self.eq(1, len(core.eval('lift(inet:ipv4, 2.0.0.0, by=lt)')))

    def test_storm_lifts_by(self):
        # Test various lifts by handlers
        with s_cortex.openurl('ram:///') as core:  # type: s_common.Cortex
            node1 = core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            node2 = core.formTufoByProp('inet:fqdn', 'vertex.vis')
            node3 = core.formTufoByProp('inet:url', 'https://vertex.link')
            node4 = core.formTufoByProp('inet:netuser', 'clowntown.link/pennywise')

            core.addTufoTags(node1, ['aka.foo.bar.baz', 'aka.duck.quack.loud', 'src.clowntown'])
            core.addTufoTags(node2, ['aka.foo.duck.baz', 'aka.duck.quack.loud', 'src.clowntown'])
            core.addTufoTags(node3, ['aka.foo.bar.knight', 'aka.duck.sound.loud', 'src.clowntown'])

            # Lift by tags
            nodes = core.eval('inet:dns:a*tag=src.clowntown')
            self.eq(len(nodes), 1)

            # Lift by type
            nodes = core.eval('inet:user*type=pennywise')
            self.eq(len(nodes), 2)

            # Lift by inet:cidr
            nodes = core.eval('inet:dns:a:ipv4*inet:cidr=1.2.0.0/16')
            self.eq(len(nodes), 1)

            # Lift by dark
            nodes = core.eval('tag*dark=aka')
            self.eq(len(nodes), 3)

            nodes = core.eval('tag*dark=aka.duck.quack')
            self.eq(len(nodes), 2)

            nodes = core.eval('tag*dark=aka.foo.bar.knight')
            self.eq(len(nodes), 1)

            nodes = core.eval('tag*dark=loc')
            self.eq(len(nodes), 0)

    def test_storm_addnode(self):
        with s_cortex.openurl('ram:///') as core:
            node = core.eval('addnode(inet:ipv4,1.2.3.4,asn=0xf0f0f0f0)')[0]
            self.eq(node[1].get('inet:ipv4'),0x01020304)
            self.eq(node[1].get('inet:ipv4:asn'),0xf0f0f0f0)

    def test_storm_delnode(self):
        with s_cortex.openurl('ram:///') as core:
            node = core.formTufoByProp('inet:ipv4',0x01020304)
            core.eval('inet:ipv4=1.2.3.4 delnode()')
            self.nn(core.getTufoByProp('inet:ipv4',0x01020304))
            core.eval('inet:ipv4=1.2.3.4 delnode(force=1)')
            self.none(core.getTufoByProp('inet:ipv4',0x01020304))

    def test_storm_editmode(self):
        with s_cortex.openurl('ram:///') as core:
            node = core.formTufoByProp('inet:ipv4',0x01020304)

            core.eval('inet:ipv4=1.2.3.4 [ #foo.bar ]')
            self.eq( len(core.eval('#foo.bar')), 1 )

            core.eval('inet:ipv4=1.2.3.4 [ +#foo.bar.baz ]')
            self.eq( len(core.eval('#foo.bar.baz')), 1 )

            core.eval('inet:ipv4=1.2.3.4 [ -#foo.bar ]')
            self.eq( len(core.eval('#foo')), 1 )
            self.eq( len(core.eval('#foo.bar')), 0 )
            self.eq( len(core.eval('#foo.bar.baz')), 0 )

            core.eval(' [ inet:ipv4=5.6.7.8 :cc=US #hehe.haha ]')

            self.eq( len(core.eval('#hehe.haha')), 1 )

            node = core.eval('inet:ipv4=5.6.7.8')[0]
            self.eq( node[1].get('inet:ipv4:cc'), 'us' )

class LimitTest(SynTest):

    def test_limit_default(self):
        # LimitHelper would normally be used with the kwlist arg limit,
        # which if not specified would default to None when the .get()
        # is performed on the kwlist dictionary.
        limt = s_storm.LimitHelp(None)
        self.eq(limt.reached(), False)
        self.eq(limt.get(), None)
        self.eq(limt.dec(), False)
        self.eq(limt.dec(100), False)

    def test_limit_behavior(self):
        n = 4
        limt = s_storm.LimitHelp(n)
        self.eq(limt.get(), 4)
        self.eq(limt.reached(), False)

        self.eq(limt.dec(), False)
        self.eq(limt.get(), 3)
        self.eq(limt.dec(4), True)

    def test_limit_behavior_negatives(self):
        n = 4
        limt = s_storm.LimitHelp(n)
        self.eq(limt.dec(0), False)
        self.eq(limt.get(), 4)

        self.eq(limt.dec(-1), False)
        self.eq(limt.get(), 4)

        self.eq(limt.dec(4), True)
        self.eq(limt.get(), 0)
        self.eq(limt.reached(), True)
        self.eq(limt.dec(-1), True)
        self.eq(limt.get(), 0)

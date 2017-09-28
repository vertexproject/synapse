import synapse.lib.tufo as s_tufo
import synapse.lib.storm as s_storm
import synapse.cores.common as s_common

from synapse.tests.common import *

class StormTest(SynTest):
    def test_storm_cmpr_norm(self):
        with self.getRamCore() as core:
            core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            self.eq(len(core.eval('inet:dns:a:ipv4="1.2.3.4"')), 1)
            self.eq(len(core.eval('inet:dns:a:ipv4="1.2.3.4" -:ipv4="1.2.3.4"')), 0)
            self.eq(len(core.eval('inet:dns:a:ipv4="1.2.3.4" +:ipv4="1.2.3.4"')), 1)

    def test_storm_pivot(self):
        with self.getRamCore() as core:
            core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            core.formTufoByProp('inet:dns:a', 'vertex.vis/5.6.7.8')
            core.formTufoByProp('inet:dns:a', 'vertex.link/5.6.7.8')

            node = core.eval('inet:ipv4="1.2.3.4" inet:ipv4->inet:dns:a:ipv4')[0]

            self.nn(node)
            self.eq(node[1].get('inet:dns:a'), 'woot.com/1.2.3.4')

            node = core.eval('inet:ipv4="1.2.3.4" pivot(inet:ipv4,inet:dns:a:ipv4)')[0]

            self.nn(node)
            self.eq(node[1].get('inet:dns:a'), 'woot.com/1.2.3.4')

            node = core.eval('inet:dns:a="woot.com/1.2.3.4" :ipv4->inet:ipv4')[0]

            self.nn(node)
            self.eq(node[1].get('inet:ipv4'), 0x01020304)

            node = core.eval('inet:dns:a="woot.com/1.2.3.4" pivot(:ipv4, inet:ipv4)')[0]

            self.nn(node)
            self.eq(node[1].get('inet:ipv4'), 0x01020304)

            node = core.eval('inet:fqdn="woot.com" ->inet:dns:a:fqdn')[0]

            self.nn(node)
            self.eq(node[1].get('inet:dns:a'), 'woot.com/1.2.3.4')

            node = core.eval('inet:fqdn="woot.com" pivot(inet:dns:a:fqdn)')[0]

            self.nn(node)
            self.eq(node[1].get('inet:dns:a'), 'woot.com/1.2.3.4')

            self.eq(len(core.eval('inet:dns:a:ipv4="5.6.7.8" :fqdn->inet:fqdn')), 2)
            self.eq(len(core.eval('inet:ipv4="5.6.7.8" -> inet:dns:a:ipv4')), 2)
            self.eq(len(core.eval('inet:ipv4="5.6.7.8" inet:ipv4->inet:dns:a:ipv4')), 2)

            self.eq(len(core.eval('inet:dns:a:ipv4="5.6.7.8" pivot(:fqdn,inet:fqdn)')), 2)
            self.eq(len(core.eval('inet:ipv4="5.6.7.8" pivot(inet:dns:a:ipv4)')), 2)
            self.eq(len(core.eval('inet:ipv4="5.6.7.8" pivot(inet:ipv4, inet:dns:a:ipv4)')), 2)

    def test_storm_setprop(self):
        with self.getRamCore() as core:

            # relative key/val syntax, explicitly relative vals
            node = core.formTufoByProp('inet:web:acct', 'vertex.link/pennywise')
            node = core.formTufoByProp('inet:web:acct', 'vertex.link/visi')
            node = core.eval('inet:web:acct=vertex.link/pennywise setprop(:realname="Robert Gray")')[0]

            self.eq(node[1].get('inet:web:acct'), 'vertex.link/pennywise')
            self.eq(node[1].get('inet:web:acct:realname'), 'robert gray')

            # Can set multiple props at once
            cmd = 'inet:web:acct=vertex.link/pennywise setprop(:seen:min="2000", :seen:max="2017")'
            node = core.eval(cmd)[0]
            self.nn(node[1].get('inet:web:acct:seen:min'))
            self.nn(node[1].get('inet:web:acct:seen:max'))

            # old / bad syntax fails
            # kwlist key/val syntax is no longer valid in setprop()
            node = core.formTufoByProp('inet:fqdn', 'vertex.link')
            bad_cmd = 'inet:fqdn=vertex.link setprop(created="2016-05-05",updated="2017/05/05")'
            self.raises(BadSyntaxError, core.eval, bad_cmd)
            # a rel prop which isn't valid for the node is bad
            bad_cmd = 'inet:fqdn=vertex.link setprop(:typocreated="2016-05-05")'
            self.raises(BadSyntaxError, core.eval, bad_cmd)
            # full prop syntax is not acceptable
            bad_cmd = 'inet:web:acct=vertex.link/pennywise setprop(inet:web:acct:signup="1970-01-01")'
            self.raises(BadSyntaxError, core.eval, bad_cmd)

    def test_storm_filt_regex(self):
        with self.getRamCore() as core:

            iden0 = guid()
            iden1 = guid()
            iden2 = guid()

            node0 = core.formTufoByProp('file:bytes', iden0)
            node1 = core.formTufoByProp('file:bytes', iden1, name='woot.exe')
            node2 = core.formTufoByProp('file:bytes', iden2, name='toow.exe')

            nodes = core.eval('file:bytes +:name~=exe')
            self.eq(len(nodes), 2)

    def test_storm_alltag(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('inet:fqdn', 'vertex.link')

            core.addTufoTag(node, 'foo.bar')
            core.addTufoTag(node, 'baz.faz')

            # test alltag macro syntax
            node = core.eval('#foo.bar')[0]

            self.eq(node[1].get('inet:fqdn'), 'vertex.link')

            self.nn(node[1].get('#baz'))
            self.nn(node[1].get('#foo.bar'))

            # test alltag macro syntax with limit
            core.eval('[ inet:fqdn=hehe.com inet:fqdn=haha.com #lol ]')
            self.eq(len(core.eval('#lol limit(1)')), 1)

    def test_storm_limit(self):
        with self.getRamCore() as core:
            # test that the limit operator correctly handles being first (no opers[-1])
            # and will subsequently filter down to the correct number of nodes
            nodes = core.eval('[ inet:ipv4=1.2.3.4 inet:ipv4=3.4.5.6 ]')
            self.eq(len(core.eval(' limit(1) ', data=nodes)), 1)

            # test that the limit() operator reaches backward to limit a previous oper
            # during the planning pass...
            oper = core.plan(core.parse(' inet:ipv4 limit(1) '))[0]
            opts = dict(oper[1].get('kwlist'))
            self.eq(opts.get('limit'), 1)

            self.raises(BadSyntaxError, core.eval, 'inet:ipv4 limit()')
            self.raises(BadSyntaxError, core.eval, 'inet:ipv4 limit(nodes=10)')
            self.raises(BadSyntaxError, core.eval, 'inet:ipv4 limit(woot)')

    def test_storm_addtag(self):
        with self.getRamCore() as core:
            iden = guid()
            node = core.formTufoByProp('inet:fqdn', 'vertex.link')

            node = core.eval('inet:fqdn=vertex.link addtag(foo.bar,baz.faz)')[0]

            self.eq(node[1].get('inet:fqdn'), 'vertex.link')

            self.nn(node[1].get('#foo'))
            self.nn(node[1].get('#foo.bar'))
            self.nn(node[1].get('#baz'))
            self.nn(node[1].get('#baz.faz'))

    def test_storm_deltag(self):
        with self.getRamCore() as core:
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
        with self.getRamCore() as core:
            core.formTufoByProp('inet:dns:a', 'foo.com/1.2.3.4')
            core.formTufoByProp('inet:dns:a', 'bar.com/1.2.3.4')

            self.eq(len(core.eval('inet:ipv4=1.2.3.4 refs(in)')), 3)
            self.eq(len(core.eval('inet:ipv4=1.2.3.4 refs(in,limit=1)')), 2)

            self.eq(len(core.eval('inet:dns:a=foo.com/1.2.3.4 refs(out)')), 3)
            self.eq(len(core.eval('inet:dns:a=foo.com/1.2.3.4 refs(out,limit=1)')), 2)

            # Try refs() with a file:txtref node.  This uses propvalu to do the pivoting
            fnode = core.formTufoByProp('file:bytes:md5', 'd41d8cd98f00b204e9800998ecf8427e')
            form, pprop = s_tufo.ndef(fnode)
            node = core.formTufoByProp('file:txtref', '({},inet:ipv4=1.2.3.4)'.format(pprop))
            nodes = core.eval('file:txtref refs()')
            self.eq(len(nodes), 3)
            forms = {s_tufo.ndef(node)[0] for node in nodes}
            self.eq(forms, {'inet:ipv4', 'file:bytes', 'file:txtref'})

            # Make sure we're also pivoting on something with a "=" in the valu
            # since we have to do a split operation inside of the refs() operator
            self.nn(core.formTufoByProp('inet:passwd', 'oh=my=graph!'))
            node = core.formTufoByProp('file:txtref', '({},"inet:passwd=oh=my=graph!")'.format(pprop))
            form, pprop = s_tufo.ndef(node)
            nodes = core.eval('file:txtref={} refs()'.format(pprop))
            self.eq(len(nodes), 3)
            forms = {s_tufo.ndef(node)[0] for node in nodes}
            self.eq(forms, {'file:bytes', 'file:txtref', 'inet:passwd'})

            # Try refs() with a non-XREF type which has propvalu properties.
            f1 = core.formTufoByProp('pvsub', 'hai', xref='inet:ipv4=1.2.3.4')
            self.nn(f1)
            nodes = core.eval('pvsub refs()')
            self.eq(len(nodes), 2)

    def test_storm_tag_query(self):
        # Ensure that non-glob tag filters operate as expected.
        with self.getRamCore() as core:  # type: s_common.Cortex
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
        with self.getRamCore() as core:  # type: s_common.Cortex
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
        with self.getRamCore() as core:  # type: s_common.Cortex

            node1 = core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            node2 = core.formTufoByProp('inet:fqdn', 'vertex.vis')
            node3 = core.formTufoByProp('inet:url', 'https://vertex.link')
            node4 = core.formTufoByProp('inet:web:acct', 'clowntown.link/pennywise')

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

            nodes = core.eval('inet:dns:a jointags(ps:tokn,inet:fqdn)')
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
        with self.getRamCore() as core:  # type: s_common.Cortex
            node1 = core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            node2 = core.formTufoByProp('inet:fqdn', 'vertex.vis')
            node3 = core.formTufoByProp('inet:url', 'https://vertex.link')
            node4 = core.formTufoByProp('inet:web:acct', 'clowntown.link/pennywise')

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
        with self.getRamCore() as core:  # type: s_common.Cortex
            node1 = core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            node2 = core.formTufoByProp('inet:fqdn', 'vertex.vis')
            node3 = core.formTufoByProp('inet:url', 'https://vertex.link')
            node4 = core.formTufoByProp('inet:web:acct', 'clowntown.link/pennywise')
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
        with self.getRamCore() as core:
            core.formTufoByProp('inet:ipv4', '1.2.3.4')
            core.formTufoByProp('inet:ipv4', '5.6.7.8')

            self.len(2, core.eval('lift(inet:ipv4)'))
            self.len(1, core.eval('lift(inet:ipv4, limit=1)'))
            self.len(1, core.eval('lift(inet:ipv4, 1.2.3.4)'))
            self.len(1, core.eval('lift(inet:ipv4, 2.0.0.0, by=lt)'))

    def test_storm_lifts_by(self):
        # Test various lifts by handlers
        with self.getRamCore() as core:  # type: s_common.Cortex

            node1 = core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            node2 = core.formTufoByProp('inet:fqdn', 'vertex.vis')
            node3 = core.formTufoByProp('inet:url', 'https://vertex.link')
            node4 = core.formTufoByProp('inet:web:acct', 'clowntown.link/pennywise')

            core.addTufoDark(node1, 'hehe', 'haha')
            core.addTufoDark(node2, 'hehe', 'haha')
            core.addTufoDark(node3, 'hehe', 'haha')

            core.addTufoTags(node1, ['aka.foo.bar.baz', 'aka.duck.quack.loud', 'src.clowntown'])
            core.addTufoTags(node2, ['aka.foo.duck.baz', 'aka.duck.quack.loud', 'src.clowntown'])
            core.addTufoTags(node3, ['aka.foo.bar.knight', 'aka.duck.sound.loud', 'src.clowntown'])

            # Lift by tags
            nodes = core.eval('inet:dns:a*tag=src.clowntown')
            self.len(1, nodes)

            # Lift by type
            nodes = core.eval('inet:user*type=pennywise')
            self.len(2, nodes)

            # Lift by inet:cidr
            nodes = core.eval('inet:dns:a:ipv4*inet:cidr=1.2.0.0/16')
            self.len(1, nodes)

            # Lift by dark
            nodes = core.eval('hehe*dark=haha')
            self.len(3, nodes)

    def test_storm_addnode(self):
        with self.getRamCore() as core:
            # add a node with addnode(<form>,<valu>) syntax
            node = core.eval('addnode(inet:ipv4,1.2.3.4)')[0]

            self.eq(node[1].get('inet:ipv4'), 0x01020304)
            self.eq(node[1].get('inet:ipv4:asn'), -1)

            # confirm that addnode() updates props on existing nodes
            node = core.eval('addnode(inet:ipv4, 1.2.3.4, :asn=0xf0f0f0f0)')[0]
            self.eq(node[1].get('inet:ipv4:asn'), 0xf0f0f0f0)

            # confirm that addnode() requires : prefix on relative props
            self.raises(BadSyntaxError, core.eval, 'addnode(inet:ipv4, 1.2.3.4, asn=20)')

    def test_storm_delnode(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('inet:ipv4', 0x01020304)
            core.eval('inet:ipv4=1.2.3.4 delnode()')
            self.nn(core.getTufoByProp('inet:ipv4', 0x01020304))
            core.eval('inet:ipv4=1.2.3.4 delnode(force=1)')
            self.none(core.getTufoByProp('inet:ipv4', 0x01020304))

    def test_storm_delnode_caching(self):
        with self.getRamCore() as core:
            core.setConfOpt('caching', True)
            node = core.formTufoByProp('inet:ipv4', 0x01020304)
            core.eval('inet:ipv4=1.2.3.4 delnode()')
            self.nn(core.getTufoByProp('inet:ipv4', 0x01020304))
            core.eval('inet:ipv4=1.2.3.4 delnode(force=1)')
            self.none(core.getTufoByProp('inet:ipv4', 0x01020304))

    def test_storm_editmode(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('inet:ipv4', 0x01020304)

            core.eval('inet:ipv4=1.2.3.4 [ #foo.bar ]')
            self.len(1, core.eval('#foo.bar'))

            core.eval('inet:ipv4=1.2.3.4 [ +#foo.bar.baz ]')
            self.len(1, core.eval('#foo.bar.baz'))

            core.eval('inet:ipv4=1.2.3.4 [ -#foo.bar ]')
            self.len(1, core.eval('#foo'))
            self.len(0, core.eval('#foo.bar'))
            self.len(0, core.eval('#foo.bar.baz'))

            core.eval(' [ inet:ipv4=5.6.7.8 :cc=US #hehe.haha ]')

            self.len(1, core.eval('#hehe.haha'))

            node = core.eval('inet:ipv4=5.6.7.8')[0]
            self.eq(node[1].get('inet:ipv4:cc'), 'us')

    def test_storm_tag_ival(self):
        with self.getRamCore() as core:
            node = core.eval('[ inet:ipv4=1.2.3.4  +#foo.bar@2016-2017 ] ')[0]

            minv = node[1].get('>#foo.bar')
            maxv = node[1].get('<#foo.bar')
            self.eq((minv, maxv), (1451606400000, 1483228800000))

            node = core.eval('[ inet:ipv4=5.6.7.8 +#foo.bar@2014 ] ')[0]

            self.eq(s_tufo.ival(node, '#foo.bar'), (1388534400000, 1388534400000))

            nodes = core.eval('inet:ipv4 +#foo.bar@201606')
            self.len(1, nodes)
            self.eq(nodes[0][1].get('inet:ipv4'), 0x01020304)

            nodes = core.eval('inet:ipv4 +#foo.bar@201602-2019')
            self.len(1, nodes)
            self.eq(nodes[0][1].get('inet:ipv4'), 0x01020304)

            nodes = core.eval('inet:ipv4 -#foo.bar@201606')
            self.len(1, nodes)
            self.eq(nodes[0][1].get('inet:ipv4'), 0x05060708)

            nodes = core.eval('inet:ipv4 -#foo.bar@2015-201606')
            self.len(1, nodes)
            self.eq(nodes[0][1].get('inet:ipv4'), 0x05060708)

    def test_storm_edit_end(self):
        with self.getRamCore() as core:
            self.len(0, core.eval(' [ inet:dns:a="woot.com/1.2.3.4" ] +:seen:min >= "2014" '))

    def test_storm_show_help(self):
        show0 = {
            'columns': ['inet:ipv4', ':cc', '#foo.*'],
        }

        with self.getRamCore() as core:
            node0 = core.eval('[inet:ipv4=108.111.118.101 :cc=kd #foo.bar #hehe.haha ]')[0]
            node1 = core.eval('[inet:ipv4=1.2.3.4 :cc=vv #foo.bar #hehe.haha ]')[0]

            nodes = core.eval('inet:ipv4')

            shlp = s_storm.ShowHelp(core, show0)

            self.eq(shlp._getShowFunc('#')(node1), '#foo.bar #hehe.haha')

            self.eq(shlp._getShowFunc(':cc')(node1), 'vv')
            self.eq(shlp._getShowFunc('#foo.*')(node1), '#foo.bar')
            self.eq(shlp._getShowFunc('inet:ipv4')(node1), '1.2.3.4')

            rows = list(sorted(shlp.rows(nodes)))
            self.eq(rows, [
                ['1.2.3.4', 'vv', '#foo.bar'],
                ['108.111.118.101', 'kd', '#foo.bar'],
            ])

            rows = list(sorted(shlp.pad(rows)))
            self.eq(rows, [
                ['        1.2.3.4', 'vv', '#foo.bar'],
                ['108.111.118.101', 'kd', '#foo.bar'],
            ])

            shlp.show['order'] = 'inet:ipv4:cc'
            rows = list(shlp.rows(nodes))
            self.eq(rows, [
                ['108.111.118.101', 'kd', '#foo.bar'],
                ['1.2.3.4', 'vv', '#foo.bar'],
            ])

    def test_storm_guid_operator(self):
        with self.getRamCore() as core:
            node0 = core.formTufoByProp('inet:ipv4', '1.2.3.4')
            node1 = core.formTufoByProp('inet:ipv4', '4.5.6.7')

            nodes = core.eval('guid()')
            self.len(0, nodes)

            nodes = core.eval('guid(%s)' % node0[0])
            self.eq(nodes[0][1].get('inet:ipv4'), 0x01020304)

            nodes = core.eval('guid(%s,%s)' % (node0[0], node1[0]))
            vals = list(sorted(v[1].get('inet:ipv4') for v in nodes))
            self.eq(vals, [0x01020304, 0x04050607])

            # We can lift dark rows using guid() but kind of an easter egg.
            core.addTufoDark(node0, 'foo:bar', 'duck:knight')
            nodes = core.eval('guid(%s)' % node0[0][::-1])
            self.len(1, nodes)
            self.eq(node0[0], nodes[0][0][::-1])

    def test_storm_guid_stablegen(self):
        with self.getRamCore() as core:
            node0 = core.eval(' [ guidform = (foo="1") ] ')[0]
            self.nn(node0)
            self.isin('.new', node0[1])
            self.eq(node0[1].get('guidform:foo'), '1')
            self.none(node0[1].get('guidform:baz'))

            node1 = core.eval('addnode(guidform, (foo="1"))')[0]
            self.nn(node1)
            self.notin('.new', node1[1])
            self.eq(node0[0], node1[0])

            node2 = core.eval('addnode(ps:hasnetuser, ((guidname="bob gray"),vertex.link/pennywise))')[0]
            self.eq(node2[1].get('ps:hasnetuser'), 'faebe657f7a5839ecda3f8af15293893/vertex.link/pennywise')

            node3 = core.eval('addnode(ou:hasnetuser, ((alias="vertex"),vertex.link/pennywise))')[0]
            self.eq(node3[1].get('ou:hasnetuser'), 'e0d1c290732ac433444afe7b5825f94d')
            self.eq(node3[1].get('ou:hasnetuser:netuser'), 'vertex.link/pennywise')

    def test_storm_task(self):
        with self.getRamCore() as core:
            foo = []
            bar = []
            baz = []
            sekrit = []

            def make_handler(store):
                def handler(evt):
                    store.append(evt)

                return handler

            core.on('task:foo', foo.append)
            core.on('task:bar', bar.append)
            core.on('task:baz', baz.append)
            core.on('task:sekrit:priority1', sekrit.append)

            core.formTufoByProp('inet:ipv4', 0x01020304)
            core.formTufoByProp('inet:ipv4', 0x05060708)

            nodes = core.eval('inet:ipv4 task(foo, bar, baz, sekrit:priority1, key=valu)')

            # We don't consume nodes when tasking
            self.len(2, nodes)

            # Events were fired
            self.len(2, foo)
            self.len(2, bar)
            self.len(2, baz)
            self.len(2, sekrit)

            # Events contained data we expected
            evt = foo[0]
            self.eq(evt[0], 'task:foo')
            self.isinstance(evt[1].get('node'), tuple)
            self.eq(evt[1].get('storm'), True)
            self.eq(evt[1].get('key'), 'valu')

            evt = sekrit[0]
            self.eq(evt[0], 'task:sekrit:priority1')
            self.isinstance(evt[1].get('node'), tuple)
            self.eq(evt[1].get('storm'), True)
            self.eq(evt[1].get('key'), 'valu')

            # We have to know queue names to add nodes too
            self.raises(BadSyntaxError, core.eval, 'inet:ipv4 task()')

    def test_storm_tree(self):
        with self.getRamCore() as core:
            node0 = core.formTufoByProp('inet:ipv4', '1.2.3.4')
            node1 = core.formTufoByProp('inet:ipv4', '4.5.6.7')
            core.addTufoTags(node0,
                             ['foo.bar.baz',
                              'foo.bar.duck',
                              'blah.blah.blah'])
            core.addTufoTags(node1,
                             ['foo.bar.baz',
                              'foo.baz.knight',
                              'blah.blah.blah',
                              'knights.ni'])

            nodes = core.eval('syn:tag=foo tree(syn:tag, syn:tag:up)')
            self.len(6, nodes)

            nodes = core.eval('syn:tag=foo tree(syn:tag, syn:tag:up, recurlim=1)')
            self.len(3, nodes)

            nodes = core.eval('syn:tag=foo.bar tree(syn:tag, syn:tag:up)')
            self.len(3, nodes)

            nodes = core.eval('syn:tag=foo.baz tree(syn:tag, syn:tag:up)')
            self.len(2, nodes)

            nodes = core.eval('syn:tag=blah tree(syn:tag, syn:tag:up)')
            self.len(3, nodes)

            nodes = core.eval('syn:tag=blah tree(syn:tag, syn:tag:up, recurlim=1)')
            self.len(2, nodes)

            nodes = core.eval('syn:tag=foo tree(syn:tag:up)')
            self.len(6, nodes)

            o0 = core.formTufoByProp('ou:org:alias', 'master')
            o1 = core.formTufoByProp('ou:org:alias', 's1')
            o2 = core.formTufoByProp('ou:org:alias', 's2')
            o3 = core.formTufoByProp('ou:org:alias', 's3')
            o4 = core.formTufoByProp('ou:org:alias', 's4')
            o5 = core.formTufoByProp('ou:org:alias', 's5')
            o6 = core.formTufoByProp('ou:org:alias', 's6')

            s01 = core.formTufoByProp('ou:suborg', [o0[1].get('ou:org'), o1[1].get('ou:org')])
            s02 = core.formTufoByProp('ou:suborg', [o0[1].get('ou:org'), o2[1].get('ou:org')])
            s13 = core.formTufoByProp('ou:suborg', [o1[1].get('ou:org'), o3[1].get('ou:org')])
            s14 = core.formTufoByProp('ou:suborg', [o1[1].get('ou:org'), o4[1].get('ou:org')])
            s45 = core.formTufoByProp('ou:suborg', [o4[1].get('ou:org'), o5[1].get('ou:org')])
            s46 = core.formTufoByProp('ou:suborg', [o4[1].get('ou:org'), o6[1].get('ou:org')])

            nodes = core.eval('ou:org:alias=master -> ou:suborg:org tree(ou:suborg:sub, ou:suborg:org) :sub-> ou:org')
            self.len(6, nodes)

            nodes = core.eval('ou:org:alias=master -> ou:suborg:org tree(:sub, ou:suborg:org) :sub-> ou:org')
            self.len(6, nodes)

            nodes = core.eval('ou:org:alias=s2 -> ou:suborg:org tree(ou:suborg:sub, ou:suborg:org) :sub-> ou:org')
            self.len(0, nodes)

            nodes = core.eval('ou:org:alias=s1 -> ou:suborg:org tree(ou:suborg:sub, ou:suborg:org) :sub-> ou:org')
            self.len(4, nodes)

            nodes = core.eval('ou:org:alias=s4 -> ou:suborg:org tree(ou:suborg:sub, ou:suborg:org) :sub-> ou:org')
            self.eq(len(nodes), 2)

            nodes = core.eval('ou:org:alias=master -> ou:suborg:org tree(ou:suborg:sub, ou:suborg:org, recurlim=1) '
                              ':sub-> ou:org')
            self.eq(len(nodes), 4)

            # Tree up instead of down
            nodes = core.eval('ou:org:alias=s6 -> ou:suborg:sub tree(ou:suborg:org, ou:suborg:sub) :org-> ou:org')
            self.eq(len(nodes), 3)

            # fqdn tests
            f0 = core.formTufoByProp('inet:fqdn', 'woohoo.wow.vertex.link')
            f1 = core.formTufoByProp('inet:fqdn', 'woot.woot.vertex.link')
            f2 = core.formTufoByProp('inet:fqdn', 'wow.ohmy.clowntown.vertex.link')

            nodes = core.eval('inet:fqdn=vertex.link tree(inet:fqdn, inet:fqdn:domain)')
            self.eq(len(nodes), 8)

            nodes = core.eval('inet:fqdn=vertex.link tree(inet:fqdn:domain)')
            self.eq(len(nodes), 8)

            nodes = core.eval('inet:fqdn=vertex.link tree(inet:fqdn:domain, recurlim=1)')
            self.eq(len(nodes), 4)

            nodes = core.eval('inet:fqdn=vertex.link tree(inet:fqdn:domain, recurlim=2)')
            self.eq(len(nodes), 7)

            # tree up
            nodes = core.eval('inet:fqdn=vertex.link tree(inet:fqdn:domain, inet:fqdn)')
            self.eq(len(nodes), 2)

            nodes = core.eval('inet:fqdn=woot.woot.vertex.link tree(inet:fqdn:domain, inet:fqdn)')
            self.eq(len(nodes), 4)

            nodes = core.eval('inet:fqdn=wow.ohmy.clowntown.vertex.link tree(inet:fqdn:domain, inet:fqdn)')
            self.eq(len(nodes), 5)

    def test_storm_delprop(self):
        with self.getRamCore() as core:
            t0 = core.formTufoByProp('inet:fqdn', 'vertex.link', created="20170101")
            self.isin('inet:fqdn:created', t0[1])
            # Operator syntax requires force=1
            core.eval('inet:fqdn=vertex.link delprop(:created)')
            t0 = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.isin('inet:fqdn:created', t0[1])

            core.eval('inet:fqdn=vertex.link delprop(:created, force=0)')
            t0 = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.isin('inet:fqdn:created', t0[1])

            core.eval('inet:fqdn=vertex.link delprop(:created, force=1)')
            t0 = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.notin('inet:fqdn:created', t0[1])

            # Re-add the prop and delete the prop via the macro syntax directly
            t0 = core.setTufoProps(t0, created="20170101")
            self.isin('inet:fqdn:created', t0[1])
            core.eval('inet:fqdn=vertex.link [ -:created ]')
            t0 = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.notin('inet:fqdn:created', t0[1])

            # Delete muliple props via macro syntax
            t0 = core.setTufoProps(t0, created="20170101", updated="20170201")
            self.isin('inet:fqdn:created', t0[1])
            self.isin('inet:fqdn:updated', t0[1])
            core.eval('inet:fqdn=vertex.link [ -:created  -:updated]')
            t0 = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.notin('inet:fqdn:created', t0[1])
            self.notin('inet:fqdn:updated', t0[1])

            # Cannot delete "ro" props via delprop
            t1 = core.formTufoByProp('inet:web:acct', 'vertex.link/pennywise')
            self.isin('inet:web:acct:user', t1[1])
            # Operator syntax requires force=1
            result = core.ask('inet:web:acct [ -:user ]')
            self.eq(result.get('data'), [])
            self.eq(result.get('oplog')[1].get('excinfo').get('err'), 'CantDelProp')
            t1 = core.getTufoByProp('inet:web:acct', 'vertex.link/pennywise')
            self.isin('inet:web:acct:user', t1[1])
            result = core.ask('inet:web:acct delprop(:user, force=1)')
            self.eq(result.get('data'), [])
            self.eq(result.get('oplog')[1].get('excinfo').get('err'), 'CantDelProp')
            t1 = core.getTufoByProp('inet:web:acct', 'vertex.link/pennywise')
            self.isin('inet:web:acct:user', t1[1])

            # Syntax errors
            self.raises(BadSyntaxError, core.eval, 'inet:fqdn=vertex.link delprop()')
            self.raises(BadSyntaxError, core.eval, 'inet:fqdn=vertex.link delprop(host)')
            self.raises(BadSyntaxError, core.eval, 'inet:fqdn=vertex.link delprop(force=1)')
            self.raises(BadSyntaxError, core.eval, 'inet:fqdn=vertex.link delprop(host, force=1)')
            self.raises(BadSyntaxError, core.eval, 'inet:fqdn=vertex.link delprop(host, created)')
            self.raises(BadSyntaxError, core.eval, 'inet:fqdn=vertex.link [ -: ]')
            self.raises(BadSyntaxError, core.eval, 'inet:fqdn=vertex.link [ -: host]')

    def test_storm_lift_limit(self):

        with s_cortex.openurl('ram:///') as core:

            self.none(core.getLiftLimit())
            self.eq(core.getLiftLimit(10, 20, 30), 30)

            core.setConfOpt('storm:limit:lift', 100)
            self.eq(core.getLiftLimit(), 100)

            for i in range(200):
                node = core.formTufoByProp('inet:ipv4', i)
                core.addTufoTag(node, 'woot')

            self.eq(100, len(core.eval('#woot')))
            self.eq(200, len(core.eval('#woot limit(1000)')))

            self.eq(100, len(core.eval('inet:ipv4')))
            self.eq(200, len(core.eval('inet:ipv4^1000')))
            self.eq(200, len(core.eval('inet:ipv4 limit(1000)')))

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

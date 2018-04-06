import synapse.common as s_common
import synapse.lib.auth as s_auth
import synapse.lib.tufo as s_tufo
import synapse.lib.storm as s_storm
import synapse.cores.common as s_cores_common

from synapse.tests.common import *

class StormTest(SynTest):

    def test_storm_addxref(self):
        with self.getRamCore() as core:
            self.raises(BadSyntaxError, core.eval, 'addxref()')
            self.len(0, core.eval('addxref(a,b,c)'))

            fnod = core.formTufoByProp('file:bytes', 'd41d8cd98f00b204e9800998ecf8427e')
            anod = core.formTufoByProp('inet:web:action', '*', act='laughed', acct='vertex.link/user1')

            fiden = fnod[1].get('file:bytes')
            aiden = anod[1].get('inet:web:action')

            qstr = 'addxref(inet:web:actref, file:bytes, %s)' % fiden
            self.len(0, core.eval(qstr))  # nothing to create xref from, as no inet:web:actions were lifted

            # create an xref in storm
            nodes = core.eval('inet:web:action ' + qstr)
            self.len(1, nodes)
            stormnode = nodes[0]

            # make sure the result of creating the node w/ cortex api is the same
            corenode = core.formTufoByProp('inet:web:actref', '(%s,file:bytes=%s)' % (aiden, fiden))
            self.eq(s_tufo.ndef(stormnode), s_tufo.ndef(corenode))

    def test_storm_nexttag(self):
        with self.getRamCore() as core:
            self.raises(BadSyntaxError, core.eval, 'nexttag()')
            self.raises(NoSuchSeq, core.eval, 'nexttag(foo)')  # nexttag does not automatically create a sequence
            core.eval('[syn:seq=foo]')

            node = core.eval('nexttag(foo)')
            self.eq(node[0][1].get('syn:tag'), 'foo0')

            node = core.eval('nexttag(foo)')
            self.eq(node[0][1].get('syn:tag'), 'foo1')

            node = core.eval('nexttag(foo)')
            self.eq(node[0][1].get('syn:tag'), 'foo2')

            self.raises(NoSuchSeq, core.eval, 'nexttag(bar)')
            self.raises(NoSuchSeq, core.eval, 'nexttag(bar.baz)')
            core.eval('[syn:seq=bar.baz]')
            self.raises(NoSuchSeq, core.eval, 'nexttag(bar)')

            node = core.eval('nexttag(bar.baz)')
            self.eq(node[0][1].get('syn:tag'), 'bar.baz0')

            core.eval('[syn:seq=docdtag]')
            node = core.eval('nexttag(docdtag, doc=hehe)')
            self.eq(node[0][1].get('syn:tag'), 'docdtag0')
            self.eq(node[0][1].get('syn:tag:doc'), 'hehe')
            node = core.eval('nexttag(docdtag)')
            self.eq(node[0][1].get('syn:tag'), 'docdtag1')
            self.eq(node[0][1].get('syn:tag:doc'), '??')

    def test_storm_nosuchcmpr(self):
        with self.getRamCore() as core:
            self.raises(NoSuchCmpr, core.eval, 'intform +notgonnahappen(1,2,3)')

    def test_storm_nosuchoper(self):
        with self.getRamCore() as core:
            self.raises(NoSuchOper, core.eval, 'intform notgonnahappen()')

    def test_storm_cmpr_norm(self):
        with self.getRamCore() as core:
            core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            self.len(1, core.eval('inet:dns:a:ipv4="1.2.3.4"'))
            self.len(0, core.eval('inet:dns:a:ipv4="1.2.3.4" -:ipv4="1.2.3.4"'))
            self.len(1, core.eval('inet:dns:a:ipv4="1.2.3.4" +:ipv4="1.2.3.4"'))

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

            self.len(2, core.eval('inet:dns:a:ipv4="5.6.7.8" :fqdn->inet:fqdn'))
            self.len(2, core.eval('inet:ipv4="5.6.7.8" -> inet:dns:a:ipv4'))
            self.len(2, core.eval('inet:ipv4="5.6.7.8" inet:ipv4->inet:dns:a:ipv4'))

            self.len(2, core.eval('inet:dns:a:ipv4="5.6.7.8" pivot(:fqdn,inet:fqdn)'))
            self.len(2, core.eval('inet:ipv4="5.6.7.8" pivot(inet:dns:a:ipv4)'))
            self.len(2, core.eval('inet:ipv4="5.6.7.8" pivot(inet:ipv4, inet:dns:a:ipv4)'))

            self.raises(BadSyntaxError, core.eval, 'inet:ipv4="5.6.7.8" pivot()')
            self.raises(BadSyntaxError, core.eval, 'inet:ipv4="5.6.7.8" pivot(:fqdn, inet:fqdn, hehe:haha)')
            self.raises(BadOperArg, core.eval, 'inet:ipv4="5.6.7.8" pivot(inet:dns:a:ipv4, limit=-1)')

    def test_storm_join(self):
        with self.getRamCore() as core:
            n1 = core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            n2 = core.formTufoByProp('inet:dns:a', 'vertex.vis/5.6.7.8')
            n3 = core.formTufoByProp('inet:dns:a', 'vertex.link/5.6.7.8')
            # Strip .new
            for node in [n1, n2, n3]:
                del node[1]['.new']

            i1 = core.getTufoByProp('inet:ipv4', '1.2.3.4')
            i2 = core.getTufoByProp('inet:ipv4', '5.6.7.8')
            f1 = core.getTufoByProp('inet:fqdn', 'woot.com')
            f2 = core.getTufoByProp('inet:fqdn', 'vertex.vis')
            f3 = core.getTufoByProp('inet:fqdn', 'vertex.link')

            nodes = core.eval('inet:ipv4="1.2.3.4" inet:ipv4<-inet:dns:a:ipv4')
            self.sorteq(nodes, [n1, i1])

            nodes = core.eval('inet:ipv4="1.2.3.4" join(inet:ipv4,inet:dns:a:ipv4)')
            self.sorteq(nodes, [n1, i1])

            nodes = core.eval('inet:dns:a="woot.com/1.2.3.4" :ipv4<-inet:ipv4')
            self.sorteq(nodes, [n1, i1])

            nodes = core.eval('inet:dns:a="woot.com/1.2.3.4" join(:ipv4, inet:ipv4)')
            self.sorteq(nodes, [n1, i1])

            nodes = core.eval('inet:fqdn="woot.com" <-inet:dns:a:fqdn')
            self.sorteq(nodes, [f1, n1])

            node = core.eval('inet:fqdn="woot.com" join(inet:dns:a:fqdn)')
            self.sorteq(nodes, [f1, n1])

            self.sorteq(core.eval('inet:dns:a:ipv4="5.6.7.8" :fqdn<-inet:fqdn'), [n2, n3, f2, f3])
            self.sorteq(core.eval('inet:ipv4="5.6.7.8" <- inet:dns:a:ipv4'), [i2, n2, n3])
            self.sorteq(core.eval('inet:ipv4="5.6.7.8" inet:ipv4<-inet:dns:a:ipv4'), [i2, n2, n3])

            self.sorteq(core.eval('inet:dns:a:ipv4="5.6.7.8" join(:fqdn,inet:fqdn)'), [n2, n3, f2, f3])
            self.sorteq(core.eval('inet:ipv4="5.6.7.8" join(inet:dns:a:ipv4)'), [i2, n2, n3])
            self.sorteq(core.eval('inet:ipv4="5.6.7.8" join(inet:ipv4, inet:dns:a:ipv4)'), [i2, n2, n3])

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

            # Can use the "now" string on a time prop to set it to that valu
            currenttime = now()
            cmd = 'inet:web:acct=vertex.link/pennywise setprop(:seen:max="now")'
            node = core.eval(cmd)[0]
            self.le(node[1].get('inet:web:acct:seen:max') - currenttime, 1000)

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
            self.len(2, nodes)

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
            self.len(1, core.eval('#lol limit(1)'))

    def test_storm_limit(self):
        with self.getRamCore() as core:
            # test that the limit operator correctly handles being first (no opers[-1])
            # and will subsequently filter down to the correct number of nodes
            nodes = core.eval('[ inet:ipv4=1.2.3.4 inet:ipv4=3.4.5.6 ]')
            self.len(1, core.eval(' limit(1) ', data=nodes))

            # test that the limit() operator reaches backward to limit a previous oper
            # during the planning pass...
            oper = core.plan(core.parse(' inet:ipv4 limit(1) '))[0]
            opts = dict(oper[1].get('kwlist'))
            self.eq(opts.get('limit'), 1)

            self.raises(BadSyntaxError, core.eval, 'inet:ipv4 limit()')
            self.raises(BadSyntaxError, core.eval, 'inet:ipv4 limit(nodes=10)')
            self.raises(BadSyntaxError, core.eval, 'inet:ipv4 limit(woot)')

    def test_storm_plan_lift_tag(self):
        with self.getRamCore() as core:
            nodes = core.eval('[ inet:ipv4=1.2.3.4 inet:ipv4=3.4.5.6 ]')
            nodes = [core.addTufoTag(node, 'hehe.haha') for node in nodes]
            core.addTufoTag(nodes[0], 'hehe.woah')

            # For reference purposes
            plain_lift_oper = core.parse('inet:ipv4')[0]
            plain_filt_oper = core.parse('+#hehe.haha')[0]
            plain_filt_oper_neg = core.parse('-#hehe.haha')[0]

            upinsts = core.plan(core.parse('inet:ipv4^3=1.2.3.4 +#hehe.haha'))
            self.len(2, upinsts)

            insts = core.plan(core.parse('inet:ipv4 +#hehe.haha'))
            self.len(1, insts)
            oper = insts[0]
            self.eq(oper[0], 'lift')
            kwlist = dict(oper[1].get('kwlist'))
            self.eq(kwlist.get('by'), 'tag')
            pargs = oper[1].get('args')
            self.eq(pargs, ('inet:ipv4', 'hehe.haha'))

            self.len(1, core.eval('inet:ipv4 +#hehe.woah'))
            self.len(2, core.eval('inet:ipv4 +#hehe.haha'))

            # limits are untouched by this optimization
            self.len(1, core.eval('inet:ipv4^1 +#hehe.haha'))

            # non-existent tags lift nothing
            self.len(0, core.eval('inet:ipv4 +#oh.my'))

            # Chaining multiple filter operators one after another
            # only consumes the first filter
            insts = core.plan(core.parse('inet:ipv4 +#hehe.haha +#hehe.woah'))
            self.len(2, insts)
            oper = insts[0]
            self.eq(oper[0], 'lift')
            kwlist = dict(oper[1].get('kwlist'))
            self.eq(kwlist.get('by'), 'tag')
            pargs = oper[1].get('args')
            self.eq(pargs, ('inet:ipv4', 'hehe.haha'))

            oper = insts[1]
            self.eq(oper[0], 'filt')
            pargs = oper[1].get('valu')
            self.eq(pargs, 'hehe.woah')

            self.len(1, core.eval('inet:ipv4 +#hehe.haha +#hehe.woah'))

            # A negative filter is not optimized in any fashion
            insts = core.plan(core.parse('inet:ipv4 -#hehe.haha'))
            self.eq(insts, [plain_lift_oper, plain_filt_oper_neg])

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

    def test_storm_refs_ndef(self):
        with self.getRamCore() as core:
            pnode = core.formTufoByProp('ps:person', 32 * '0')
            enode = core.formTufoByProp('inet:email', 'c00l@vertex.link')
            pvalu = pnode[1].get('ps:person')
            phas0 = core.formTufoByProp('ps:person:has', (pvalu, ('inet:email', 'c00l@vertex.link')))
            core.formTufoByProp('ps:person:has', (pvalu, ('inet:fqdn', 'vertex.link')))

            fnode = core.formTufoByProp('file:bytes:md5', 'd41d8cd98f00b204e9800998ecf8427e')
            _, fvalu = s_tufo.ndef(fnode)
            core.formTufoByProp('file:txtref', (fvalu, ('ps:person:has', phas0[1].get('ps:person:has'))))

            outnodes = core.eval('ps:person:has refs(out)')  # out
            outforms = {node[1]['tufo:form'] for node in outnodes}
            self.len(5, outnodes)
            self.sorteq(outforms, ['inet:email', 'inet:fqdn', 'ps:person:has', 'ps:person'])

            outnodes = core.eval('ps:person:has refs(out, limit=0)')  # out
            limtoutforms = {node[1]['tufo:form'] for node in outnodes}
            self.len(2, outnodes)
            self.sorteq(limtoutforms, ['ps:person:has'])

            outnodes = core.eval('ps:person:has refs(out, limit=1)')  # out
            limtoutforms = {node[1]['tufo:form'] for node in outnodes}
            self.len(3, outnodes)
            [self.isin(form, ['inet:email', 'inet:fqdn', 'ps:person:has', 'ps:person']) for form in limtoutforms]

            innodes = core.eval('ps:person:has refs(in)')  # in
            informs = {node[1]['tufo:form'] for node in innodes}
            self.len(3, innodes)
            self.sorteq(informs, ['file:txtref', 'ps:person:has'])  # Nothing refs in to these nodes

            expected_bothforms = informs.union(outforms)

            bothnodes = core.eval('ps:person:has refs()')  # in and out
            bothforms = {node[1]['tufo:form'] for node in bothnodes}
            self.len(6, bothnodes)
            self.sorteq(expected_bothforms, bothforms)

    def test_storm_refs(self):
        with self.getRamCore() as core:
            core.formTufoByProp('inet:dns:a', 'foo.com/1.2.3.4')
            core.formTufoByProp('inet:dns:a', 'bar.com/1.2.3.4')

            self.len(3, core.eval('inet:ipv4=1.2.3.4 refs(in)'))
            self.len(2, core.eval('inet:ipv4=1.2.3.4 refs(in,limit=1)'))

            self.len(3, core.eval('inet:dns:a=foo.com/1.2.3.4 refs(out)'))
            self.len(2, core.eval('inet:dns:a=foo.com/1.2.3.4 refs(out,limit=1)'))

            # Try refs() with a file:txtref node.  This uses propvalu to do the pivoting
            fnode = core.formTufoByProp('file:bytes:md5', 'd41d8cd98f00b204e9800998ecf8427e')
            form, pprop = s_tufo.ndef(fnode)
            node = core.formTufoByProp('file:txtref', '({},inet:ipv4=1.2.3.4)'.format(pprop))
            nodes = core.eval('file:txtref refs()')
            self.len(3, nodes)
            forms = {s_tufo.ndef(node)[0] for node in nodes}
            self.eq(forms, {'inet:ipv4', 'file:bytes', 'file:txtref'})

            # Make sure we're also pivoting on something with a "=" in the valu
            # since we have to do a split operation inside of the refs() operator
            self.nn(core.formTufoByProp('inet:passwd', 'oh=my=graph!'))
            node = core.formTufoByProp('file:txtref', '({},"inet:passwd=oh=my=graph!")'.format(pprop))
            form, pprop = s_tufo.ndef(node)
            nodes = core.eval('file:txtref={} refs()'.format(pprop))
            self.len(3, nodes)
            forms = {s_tufo.ndef(node)[0] for node in nodes}
            self.eq(forms, {'file:bytes', 'file:txtref', 'inet:passwd'})

            # Try refs() with a non-XREF type which has propvalu properties.
            f1 = core.formTufoByProp('pvsub', 'hai', xref='inet:ipv4=1.2.3.4')
            self.nn(f1)
            nodes = core.eval('pvsub refs()')
            self.len(2, nodes)

            # Try refs() on a node which points to a ref node
            t0 = core.formTufoByProp('inet:ipv4', '1.2.3.5')
            t1 = core.formTufoByProp('inet:web:acct', 'vertex.link/pennywise')
            t2 = core.formTufoByProp('inet:web:post', '(vertex.link/pennywise,"Smells like cottoncandy")')
            form, valu = s_tufo.ndef(t2)
            t3 = core.formTufoByProp('inet:web:postref', [valu, ['inet:ipv4', '1.2.3.5']])
            for node in [t0, t1, t2, t3]:
                self.nn(node)
            nodes = core.eval('inet:ipv4=1.2.3.5 refs(in)')
            self.len(2, nodes)

            forms = set()
            valus = set()
            for node in nodes:
                form, valu = s_tufo.ndef(node)
                forms.add(form)
                valus.add(valu)
            self.eq(forms, {'inet:ipv4', 'inet:web:postref'})
            self.isin(t0[1].get('inet:ipv4'), valus)
            self.isin(t3[1].get('inet:web:postref'), valus)

            nodes = core.eval('inet:ipv4=1.2.3.5 refs()')
            self.len(3, nodes)

    def test_storm_tag_query(self):
        # Ensure that non-glob tag filters operate as expected.
        with self.getRamCore() as core:  # type: s_cores_common.Cortex
            node1 = core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            node2 = core.formTufoByProp('inet:dns:a', 'vertex.vis/5.6.7.8')
            node3 = core.formTufoByProp('inet:dns:a', 'vertex.link/5.6.7.8')

            core.addTufoTags(node1, ['aka.foo.bar.baz', 'aka.duck.quack.loud', 'src.clowntown'])
            core.addTufoTags(node2, ['aka.foo.duck.baz', 'aka.duck.quack.loud', 'src.clowntown'])
            core.addTufoTags(node3, ['aka.foo.bar.knight', 'aka.duck.sound.loud', 'src.clowntown'])

            nodes = core.eval('inet:dns:a +#src.clowntown')
            self.len(3, nodes)

            nodes = core.eval('inet:dns:a +#src')
            self.len(3, nodes)

            nodes = core.eval('inet:dns:a +#aka.duck.quack')
            self.len(2, nodes)

            nodes = core.eval('inet:dns:a +#aka.foo.bar.knight')
            self.len(1, nodes)

            nodes = core.eval('inet:dns:a +#src.internet')
            self.len(0, nodes)

            nodes = core.eval('inet:dns:a -#aka.foo.bar')
            self.len(1, nodes)

    def test_storm_tag_glob(self):
        # Ensure that glob operators with tag filters operate properly.
        with self.getRamCore() as core:  # type: s_cores_common.Cortex
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
            self.len(2, nodes)

            nodes = core.eval('inet:dns:a +#aka.duck.*.loud')
            self.len(4, nodes)

            nodes = core.eval('inet:dns:a +#aka.*.sound.loud')
            self.len(2, nodes)

            nodes = core.eval('inet:dns:a -#aka.*.baz')
            self.len(2, nodes)

            nodes = core.eval('inet:dns:a +#aka.*.loud')
            self.len(0, nodes)

            nodes = core.eval('inet:dns:a +#aka.*.*.loud')
            self.len(4, nodes)

            nodes = core.eval('inet:dns:a +#aka.*.*.*.loud')
            self.len(0, nodes)

            nodes = core.eval('inet:dns:a +#aka.*.knight')
            self.len(1, nodes)

            nodes = core.eval('inet:dns:a +#aka.**.loud')
            self.len(4, nodes)

            nodes = core.eval('inet:dns:a +#loc.**.perfection')
            self.len(2, nodes)

            nodes = core.eval('inet:dns:a +#loc.**.sol.*.us')
            self.len(4, nodes)

            nodes = core.eval('inet:dns:a +#loc.*.galactic_arm_a.**.us.*.perfection')
            self.len(2, nodes)

            nodes = core.eval('inet:dns:a +#**.baz')
            self.len(2, nodes)

            nodes = core.eval('inet:dns:a +#**.mars')
            self.len(1, nodes)

            nodes = core.eval('inet:dns:a -#**.mars.*.tx')
            self.len(3, nodes)

            nodes = core.eval('inet:dns:a +#loc.milkyway.*arm*.**.tx')
            self.len(1, nodes)

            nodes = core.eval('inet:dns:a +#loc.**.u*')
            self.len(4, nodes)

            nodes = core.eval('inet:dns:a +#loc.milkyway.galactic**.tx')
            self.len(1, nodes)

    def test_storm_tag_jointag(self):
        with self.getRamCore() as core:  # type: s_cores_common.Cortex

            dnsa0 = core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            dnsa1 = core.formTufoByProp('inet:dns:a', 'example.com/4.3.2.1')
            fqdn0 = core.formTufoByProp('inet:fqdn', 'vertex.vis')
            url0 = core.formTufoByProp('inet:url', 'https://vertex.link')
            acct0 = core.formTufoByProp('inet:web:acct', 'clowntown.link/pennywise')

            core.addTufoTags(dnsa0, ['aka.bar.baz',
                                     'aka.duck.quack.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.ca.san_francisco'])
            core.addTufoTags(fqdn0, ['aka.duck.baz',
                                     'aka.duck.quack.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.va.san_francisco'])
            core.addTufoTags(url0, ['aka.bar.knight',
                                     'aka.duck.sound.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.nv.perfection'])
            core.addTufoTags(acct0, ['aka.bar.knightdark',
                                     'aka.duck.sound.loud',
                                     'loc.milkyway.galactic_arm_a.sol.mars.us.tx.perfection'])

            nodes = core.eval('inet:dns:a jointags()')
            self.len(3, nodes)
            self.eq(nodes[0][1].get('tufo:form'), 'inet:dns:a')
            self.eq(nodes[1][1].get('tufo:form'), 'inet:dns:a')
            self.eq(nodes[2][1].get('tufo:form'), 'inet:fqdn')

            # Demonstrate that the same query w/ form args will filter the results
            nodes = core.eval('inet:dns:a jointags(inet:dns:a)')  # all 2 dns nodes, join tagged dns (1) nodes, so still 2
            self.len(2, nodes)
            self.eq(nodes[0][1].get('tufo:form'), 'inet:dns:a')
            nodes = core.eval('inet:dns:a jointags(inet:fqdn)')  # all 2 dns nodes, join tagged fqdn (1) nodes, so 3
            self.len(3, nodes)
            self.eq(nodes[0][1].get('tufo:form'), 'inet:dns:a')
            self.eq(nodes[1][1].get('tufo:form'), 'inet:dns:a')
            self.eq(nodes[2][1].get('tufo:form'), 'inet:fqdn')
            nodes = core.eval('inet:dns:a jointags(inet:fqdn,inet:dns:a)')  # all 2 dns nodes, join tagged dns (1) and fqdn (1) nodes, so 3
            self.len(3, nodes)
            self.eq(nodes[0][1].get('tufo:form'), 'inet:dns:a')
            self.eq(nodes[1][1].get('tufo:form'), 'inet:dns:a')
            self.eq(nodes[2][1].get('tufo:form'), 'inet:fqdn')
            nodes = core.eval('inet:dns:a jointags(inet:ipv4,inet:dns:a)')  # all 2 dns nodes, join tagged ipv4 (0) and dns (1) nodes
            self.len(2, nodes)
            self.eq(nodes[0][1].get('tufo:form'), 'inet:dns:a')
            self.eq(nodes[1][1].get('tufo:form'), 'inet:dns:a')
            nodes = core.eval('inet:dns:a jointags(inet:ipv4)')  # all 2 dns nodes, join tagged ipv4 nodes (0)
            self.len(2, nodes)
            self.eq(nodes[0][1].get('tufo:form'), 'inet:dns:a')
            self.eq(nodes[1][1].get('tufo:form'), 'inet:dns:a')

            # Demonstrate that limits work
            self.len(3, core.eval('inet:dns:a jointags()'))
            self.len(3, core.eval('inet:dns:a jointags(limit=4)'))
            self.len(3, core.eval('inet:dns:a jointags(inet:dns:a,inet:fqdn,limit=4)'))
            self.len(3, core.eval('inet:dns:a jointags(limit=3)'))
            self.len(3, core.eval('inet:dns:a jointags(inet:dns:a,inet:fqdn,limit=3)'))
            self.len(3, core.eval('inet:dns:a jointags(limit=2)'))
            self.len(3, core.eval('inet:dns:a jointags(inet:dns:a,inet:fqdn,limit=2)'))
            self.len(3, core.eval('inet:dns:a jointags(limit=1)'))
            self.len(3, core.eval('inet:dns:a jointags(inet:dns:a,inet:fqdn,limit=1)'))
            self.len(2, core.eval('inet:dns:a jointags(limit=0)'))
            self.len(2, core.eval('inet:dns:a jointags(inet:dns:a,inet:fqdn,limit=0)'))

            # Demonstrate invalid input
            self.raises(BadOperArg, core.eval, 'inet:dns:a jointags(limit=-1)')
            self.raises(BadOperArg, core.eval, 'inet:dns:a jointags(inet:dns:a,inet:fqdn,limit=-1)')

    def test_storm_tag_pivottag(self):
        with self.getRamCore() as core:  # type: s_cores_common.Cortex

            dnsa0 = core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            dnsa1 = core.formTufoByProp('inet:dns:a', 'example.com/4.3.2.1')
            fqdn0 = core.formTufoByProp('inet:fqdn', 'vertex.vis')
            url0 = core.formTufoByProp('inet:url', 'https://vertex.link')
            acct0 = core.formTufoByProp('inet:web:acct', 'clowntown.link/pennywise')

            core.addTufoTags(dnsa0, ['aka.bar.baz',
                                     'aka.duck.quack.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.ca.san_francisco'])
            core.addTufoTags(fqdn0, ['aka.duck.baz',
                                     'aka.duck.quack.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.va.san_francisco'])
            core.addTufoTags(url0, ['aka.bar.knight',
                                     'aka.duck.sound.loud',
                                     'loc.milkyway.galactic_arm_a.sol.earth.us.nv.perfection'])
            core.addTufoTags(acct0, ['aka.bar.knightdark',
                                     'aka.duck.sound.loud',
                                     'loc.milkyway.galactic_arm_a.sol.mars.us.tx.perfection'])

            # Lift all of the inet:dns:a (get 2 nodes), pivot from those nodes to tagged nodes
            # Only one of the inet:dns:a is tagged, pivot from it and return it and its fqdn which is also tagged
            nodes = core.eval('inet:dns:a pivottags()')
            self.len(2, nodes)
            self.eq(nodes[0][1].get('tufo:form'), 'inet:dns:a')
            self.eq(nodes[1][1].get('tufo:form'), 'inet:fqdn')

            # Demonstrate that the same query w/ form args will filter the results
            nodes = core.eval('inet:dns:a pivottags(inet:dns:a)')
            self.len(1, nodes)
            self.eq(nodes[0][1].get('tufo:form'), 'inet:dns:a')
            nodes = core.eval('inet:dns:a pivottags(inet:fqdn)')
            self.len(1, nodes)
            self.eq(nodes[0][1].get('tufo:form'), 'inet:fqdn')
            nodes = core.eval('inet:dns:a pivottags(inet:fqdn,inet:dns:a)')
            self.len(2, nodes)
            self.eq(nodes[0][1].get('tufo:form'), 'inet:dns:a')
            self.eq(nodes[1][1].get('tufo:form'), 'inet:fqdn')
            nodes = core.eval('inet:dns:a pivottags(inet:ipv4,inet:dns:a)')  # there is no ipv4
            self.len(1, nodes)
            self.eq(nodes[0][1].get('tufo:form'), 'inet:dns:a')
            nodes = core.eval('inet:dns:a pivottags(inet:ipv4)')  # there is no ipv4
            self.len(0, nodes)

            # Demonstrate that limits work
            self.len(2, core.eval('inet:dns:a pivottags()'))
            self.len(2, core.eval('inet:dns:a pivottags(limit=3)'))
            self.len(2, core.eval('inet:dns:a pivottags(inet:dns:a,inet:fqdn,limit=3)'))
            self.len(2, core.eval('inet:dns:a pivottags(limit=2)'))
            self.len(2, core.eval('inet:dns:a pivottags(inet:dns:a,inet:fqdn,limit=2)'))
            self.len(1, core.eval('inet:dns:a pivottags(limit=1)'))
            self.len(1, core.eval('inet:dns:a pivottags(inet:dns:a,inet:fqdn,limit=1)'))
            self.len(0, core.eval('inet:dns:a pivottags(limit=0)'))
            self.len(0, core.eval('inet:dns:a pivottags(inet:dns:a,inet:fqdn,limit=0)'))

            # Demonstrate invalid input
            self.raises(BadOperArg, core.eval, 'inet:dns:a pivottags(limit=-1)')
            self.raises(BadOperArg, core.eval, 'inet:dns:a pivottags(inet:dns:a,inet:fqdn,limit=-1)')

    def test_storm_tag_totag(self):
        with self.getRamCore() as core:  # type: s_cores_common.Cortex
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
            self.len(3, nodes)

            nodes = core.eval('inet:dns:a totags(leaf=0)')
            self.len(14, nodes)

            nodes = core.eval('#aka.duck.quack.loud totags()')
            self.len(5, nodes)

            nodes = core.eval('#aka.duck totags()')
            self.len(10, nodes)

            nodes = core.eval('#aka.duck totags(limit=3)')
            self.len(3, nodes)

            nodes = core.eval('#aka.duck totags(limit=0)')
            self.len(0, nodes)

            nodes = core.eval('ps:tokn totags()')
            self.len(0, nodes)

            # Tag input
            nodes = core.eval('syn:tag=aktoa.bar.baz totags()')
            self.len(0, nodes)

            # Tagless node input
            nodes = core.eval('geo:loc=derry totags()')
            self.len(0, nodes)

            self.raises(BadOperArg, core.eval, '#aka.duck totags(limit=-1)')

    def test_storm_tag_fromtag(self):
        with self.getRamCore() as core:  # type: s_cores_common.Cortex
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
            self.len(1, nodes)

            nodes = core.eval('syn:tag=aka.bar fromtags()')
            self.len(3, nodes)

            nodes = core.eval('syn:tag=aka.duck fromtags()')
            self.len(4, nodes)

            nodes = core.eval('syn:tag=aka.bar.baz fromtags(inet:dns:a)')
            self.len(1, nodes)

            nodes = core.eval('syn:tag=aka.bar.baz fromtags(inet:dns:a, ps:tokn)')
            self.len(1, nodes)

            nodes = core.eval('syn:tag=aka.bar.baz fromtags(ps:tokn)')
            self.len(0, nodes)

            nodes = core.eval('syn:tag=spam.and.eggs fromtags()')
            self.len(0, nodes)

            nodes = core.eval('syn:tag=aka.duck fromtags(limit=2)')
            self.len(2, nodes)

            # Non-tag input
            nodes = core.eval('inet:dns:a fromtags()')
            self.len(0, nodes)

            nodes = core.eval('syn:tag:base=bar fromtags()')
            self.len(3, nodes)

    def test_storm_lift(self):
        with self.getRamCore() as core:
            core.formTufoByProp('inet:ipv4', '1.2.3.4')
            core.formTufoByProp('inet:ipv4', '5.6.7.8')

            self.len(2, core.eval('lift(inet:ipv4)'))
            self.len(1, core.eval('lift(inet:ipv4, limit=1)'))
            self.len(1, core.eval('lift(inet:ipv4, 1.2.3.4)'))
            self.len(1, core.eval('lift(inet:ipv4, 2.0.0.0, by=lt)'))
            self.raises(BadSyntaxError, core.eval, 'lift()')
            self.raises(BadSyntaxError, core.eval, 'lift(inet:ipv4, 2.0.0.0, 1.0.0.0)')

    def test_storm_lifts_by(self):
        # Test various lifts by handlers
        with self.getRamCore() as core:  # type: s_cores_common.Cortex

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

    def test_storm_cmpr_in(self):
        with self.getRamCore() as core:  # type: s_cores_common.Cortex
            core.formTufoByProp('intform', 0)
            core.formTufoByProp('intform', 1)
            core.formTufoByProp('intform', 2)
            core.formTufoByProp('intform', 1000)

            self.len(0, core.eval('intform +in(intform, (-1))'))
            self.len(1, core.eval('intform +in(intform, (0))'))
            self.len(3, core.eval('intform -in(intform, (0))'))
            self.len(1, core.eval('intform +in(intform, (1))'))
            self.len(1, core.eval('intform +in(intform, (2))'))
            self.len(1, core.eval('intform +in(intform, (1000))'))
            self.len(0, core.eval('intform +in(intform, (1001))'))
            self.len(2, core.eval('intform +in(intform, (1,2))'))
            self.len(3, core.eval('intform +in(intform, (0,1,2))'))
            self.len(4, core.eval('intform +in(intform, (0,1,2,1000))'))
            self.len(4, core.eval('intform +in(intform, (-1,0,1,2,1000,1001))'))
            self.len(3, core.eval('intform +in(intform, (0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16))'))

    def test_storm_cmpr_range(self):
        with self.getRamCore() as core:  # type: s_cores_common.Cortex
            core.formTufoByProp('intform', 0)
            core.formTufoByProp('intform', 1)
            core.formTufoByProp('intform', 2)
            core.formTufoByProp('intform', 1000)

            nodes = core.eval('intform +range(intform, (-1,0))')
            self.len(1, nodes)

            nodes = core.eval('intform -range(intform, (-1,0))')
            self.len(3, nodes)

            nodes = core.eval('intform +range(intform, (-10000,10000))')
            self.len(4, nodes)

            nodes = core.eval('intform +range(intform, (0,0))')
            self.len(1, nodes)

            nodes = core.eval('intform +range(intform, (0,1))')
            self.len(2, nodes)

            nodes = core.eval('intform +range(intform, (0,3))')
            self.len(3, nodes)

            nodes = core.eval('intform +range(intform, (0,4))')
            self.len(3, nodes)

            core.formTufoByProp('inet:ipv4', 0)
            core.formTufoByProp('inet:ipv4', 1)
            core.formTufoByProp('inet:ipv4', 2)
            core.formTufoByProp('inet:ipv4', 1000)

            nodes = core.eval('inet:ipv4 +range(inet:ipv4, ("0.0.0.0","0.0.0.10"))')
            self.len(3, nodes)

            nodes = core.eval('inet:ipv4 +range(:asn, (0,1))')
            self.len(0, nodes)

            # Relative property
            nodes = core.eval('inet:ipv4 +range(:asn, (-1,1))')
            self.len(4, nodes)

            # Invalid property
            nodes = core.eval('inet:ipv4 +range(:asn_wat, (-1,1))')
            self.len(0, nodes)  # NOTE: no exception is raised

            # Invalid range
            self.raises(BadTypeValu, core.eval, 'intform +range(intform, (asdf, ghjk))')

    def test_storm_cmpr_seen(self):
        with self.getRamCore() as core:  # type: s_cores_common.Cortex
            core.formTufoByProp('inet:web:acct', 'vertex.link/user0', **{'seen:min': 0, 'seen:max': 0})
            core.formTufoByProp('inet:web:acct', 'vertex.link/user1', **{'seen:min': 1483228800000, 'seen:max': 1514764800000})  # 2017-2018
            core.formTufoByProp('inet:web:acct', 'vertex.link/user2', **{'seen:min': 2493072000000, 'seen:max': 2493072000000})  # 2049
            core.formTufoByProp('intform', 2493072000000)

            self.raises(BadTypeValu, core.eval, 'inet:web:acct +seen(0)')  # expecting date time in string
            self.len(0, core.eval('inet:web:acct +seen(2016)'))
            self.len(1, core.eval('inet:web:acct +seen(2016, 2017, 2025)'))
            self.len(2, core.eval('inet:web:acct +seen(2016, 2017, 2025, 2049)'))

            self.len(1, core.eval('inet:web:acct +seen(2017)'))
            self.len(1, core.eval('inet:web:acct +seen(2018)'))
            self.len(0, core.eval('inet:web:acct +seen(2019)'))

            self.len(0, core.eval('inet:web:acct +seen(2048)'))
            self.len(1, core.eval('inet:web:acct +seen(2049)'))
            self.len(0, core.eval('inet:web:acct +seen(2050)'))

            self.len(0, core.eval('intform +seen(2049)'))

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

            self.raises(BadSyntaxError, core.eval, 'addnode()')

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

            # Setting RO nodes on guid nodes made without secondary props / subs
            # Testing only - do NOT make comp nodes like this
            ouhnode = core.eval('[compfqdn=*]')[0]
            self.nn(ouhnode)
            self.notin('compfqdn:guid', ouhnode[1])
            self.notin('compfqdn:fqdn', ouhnode[1])

            # Set the missing props
            query = 'compfqdn=%s [:guid=%s :fqdn=woot.com]' % (ouhnode[1].get('compfqdn'), 32 * 'a')
            ouhnode = core.eval(query)[0]
            self.eq(ouhnode[1].get('compfqdn:guid'), 32 * 'a')
            self.eq(ouhnode[1].get('compfqdn:fqdn'), 'woot.com')

            # We cannot change ro values via set prop mode
            query = 'compfqdn=%s [:guid=%s :fqdn=vertex.link]' % (ouhnode[1].get('compfqdn'), 32 * 'b')
            ouhnode = core.eval(query)[0]
            self.eq(ouhnode[1].get('compfqdn:guid'), 32 * 'a')
            self.eq(ouhnode[1].get('compfqdn:fqdn'), 'woot.com')

    def test_storm_tag_ival(self):
        with self.getRamCore() as core:

            node = core.eval('[ inet:ipv4=1.2.3.4  +#foo.bar@2016-2017 ] ')[0]
            minv = node[1].get('>#foo.bar')
            maxv = node[1].get('<#foo.bar')
            self.eq((minv, maxv), (1451606400000, 1483228800000))
            self.len(0, core.eval(' inet:ipv4=1.2.3.7 +#foo.bar@2016-2017 '))

            node = core.eval('[ inet:ipv4=5.6.7.8 +#foo.bar@2014 ] ')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), (1388534400000, 1388534400000))
            self.len(1, core.eval(' [inet:ipv4=5.6.7.9 +#foo.baz@2001] '))
            self.len(0, core.eval(' inet:ipv4=5.6.7.9 +#foo.baz@2001-2002 '))
            self.len(0, core.eval(' inet:ipv4=5.6.7.9 +#foo.baz@2049 '))
            self.len(0, core.eval(' inet:ipv4=5.6.7.9 +#foo.baz@2049-2149 '))

            nodes = core.eval('inet:ipv4 +#foo.bar@201606')
            self.len(1, nodes)
            self.eq(nodes[0][1].get('inet:ipv4'), 0x01020304)

            nodes = core.eval('inet:ipv4 +#foo.bar@201602-2019')
            self.len(1, nodes)
            self.eq(nodes[0][1].get('inet:ipv4'), 0x01020304)

            nodes = core.eval('inet:ipv4 -#foo.bar')
            self.len(1, nodes)  # 5.6.7.9

            nodes = core.eval('inet:ipv4 +#foo.bar')
            self.len(2, nodes)  # 1.2.3.4, 5.6.7.8

            nodes = core.eval('inet:ipv4 +#foo.baz')
            self.len(1, nodes)  # 5.6.7.9

            nodes = core.eval('inet:ipv4 -#foo.baz')
            self.len(2, nodes)  # 1.2.3.4, 5.6.7.8

            nodes = core.eval('inet:ipv4 -#foo.bar@201606')
            self.len(2, nodes)  # 5.6.7.8, 5.6.7.9

            nodes = core.eval('inet:ipv4 +#foo.bar@201606')
            self.len(1, nodes)  # 1.2.3.4

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
            self.eq(shlp._getShowFunc(':wat')(node1), '')

            self.eq(shlp._getShowFunc('#foo.*')(node1), '#foo.bar')
            self.eq(shlp._getShowFunc('inet:ipv4')(node1), '1.2.3.4')
            self.eq(shlp._getShowFunc('wat')(node1), '')

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

            pnode = core.eval('addnode(ps:person, (guidname="bob gray"))')[0]
            pguid = pnode[1].get('ps:person')
            self.eq(pguid, 'faebe657f7a5839ecda3f8af15293893')

            node2 = core.eval('addnode(ps:person:has, (faebe657f7a5839ecda3f8af15293893,(inet:web:acct,vertex.link/pennywise)))')[0]
            self.eq(node2[1].get('ps:person:has'), 'e845e52f7bd78385291d3df6c1aeda31')
            self.eq(node2[1].get('ps:person:has:person'), 'faebe657f7a5839ecda3f8af15293893')
            self.eq(node2[1].get('ps:person:has:xref'), 'inet:web:acct=vertex.link/pennywise')
            self.eq(node2[1].get('ps:person:has:xref:prop'), 'inet:web:acct')
            self.eq(node2[1].get('ps:person:has:xref:node'), '600ec8667d978eba100b8a412f7154ae')

            onode = core.eval('addnode(ou:org, (name="clowns"))')[0]
            oguid = onode[1].get('ou:org')
            self.eq(oguid, 'd4556f76e65043a138f7899db9d27cf1')

            node3 = core.eval('addnode(ou:org:has, (d4556f76e65043a138f7899db9d27cf1, (inet:web:acct,vertex.link/pennywise)))')[0]
            self.eq(node3[1].get('ou:org:has'), '378c9905f931af5786a753d10c0cd20b')
            self.eq(node3[1].get('ou:org:has:org'), 'd4556f76e65043a138f7899db9d27cf1')
            self.eq(node3[1].get('ou:org:has:xref'), 'inet:web:acct=vertex.link/pennywise')
            self.eq(node3[1].get('ou:org:has:xref:prop'), 'inet:web:acct')
            self.eq(node3[1].get('ou:org:has:xref:node'), '600ec8667d978eba100b8a412f7154ae')

    def test_storm_task(self):
        with self.getRamCore() as core:
            foo = []
            bar = []
            baz = []
            sekrit = []

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
            self.len(1, foo)
            self.len(1, bar)
            self.len(1, baz)
            self.len(1, sekrit)

            # Events contained data we expected
            evt = foo[0]
            self.eq(evt[0], 'task:foo')
            # My nodes are a list since they haven't gone through telepath
            self.isinstance(evt[1].get('nodes'), list)
            nodes = evt[1].get('nodes')
            self.len(2, nodes)
            for node in nodes:
                pprop, valu = s_tufo.ndef(node)
                self.eq(pprop, 'inet:ipv4')
            self.eq(evt[1].get('storm'), True)
            self.eq(evt[1].get('key'), 'valu')

            evt = sekrit[0]
            self.eq(evt[0], 'task:sekrit:priority1')
            # My nodes are a list since they haven't gone through telepath
            self.isinstance(evt[1].get('nodes'), list)
            self.eq(evt[1].get('storm'), True)
            self.eq(evt[1].get('key'), 'valu')

            # We have to know queue names to add nodes too
            self.raises(BadSyntaxError, core.eval, 'inet:ipv4 task()')

            # We have some task names too!
            nodes = core.eval('get:tasks()')
            self.len(4, nodes)

    def test_storm_task_telepath(self):
        with self.getDmonCore() as core_prox:
            foo = []

            def foo_append(data):
                foo.append(data)

            core_prox.on('task:foo', foo_append)

            core_prox.formTufoByProp('inet:ipv4', 0x01020304)
            core_prox.formTufoByProp('inet:ipv4', 0x05060708)

            nodes = core_prox.eval('inet:ipv4 task(foo, key=valu)')

            # We don't consume nodes when tasking
            self.len(2, nodes)

            # Events were fired
            self.len(1, foo)

            # Events contained data we expected
            evt = foo[0]
            self.eq(evt[0], 'task:foo')
            # My nodes are a tuple since they have gone through telepath
            self.isinstance(evt[1].get('nodes'), tuple)
            nodes = evt[1].get('nodes')
            self.len(2, nodes)
            for node in nodes:
                pprop, valu = s_tufo.ndef(node)
                self.eq(pprop, 'inet:ipv4')
            self.eq(evt[1].get('storm'), True)
            self.eq(evt[1].get('key'), 'valu')

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

            nodes = core.eval('syn:tag=foo tree(syn:tag, syn:tag:up, recurlim=2)')
            self.len(6, nodes)

            nodes = core.eval('syn:tag=foo tree(syn:tag, syn:tag:up, recurlim=3)')
            self.len(6, nodes)

            nodes = core.eval('syn:tag=foo tree(syn:tag, syn:tag:up, limit=4)')
            self.len(5, nodes)  # 1 src node + 4 additional nodes lifted

            nodes = core.eval('syn:tag=foo tree(syn:tag, syn:tag:up, recurlim=12345)')
            self.len(6, nodes)

            nodes = core.eval('syn:tag=foo tree(syn:tag, syn:tag:up, recurlim=0)')  # 0 means no recursion limit
            self.len(6, nodes)

            self.raises(s_common.BadSyntaxError, core.eval, 'syn:tag=foo tree()')
            self.raises(s_common.BadOperArg, core.eval, 'syn:tag=foo tree(syn:tag, syn:tag:up, recurlim=0.123)')
            self.raises(s_common.BadOperArg, core.eval, 'syn:tag=foo tree(syn:tag, syn:tag:up, recurlim=-1)')

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
            self.len(2, nodes)

            nodes = core.eval('ou:org:alias=master -> ou:suborg:org tree(ou:suborg:sub, ou:suborg:org, recurlim=1) '
                              ':sub-> ou:org')
            self.len(4, nodes)

            # Tree up instead of down
            nodes = core.eval('ou:org:alias=s6 -> ou:suborg:sub tree(ou:suborg:org, ou:suborg:sub) :org-> ou:org')
            self.len(3, nodes)

            # fqdn tests
            f0 = core.formTufoByProp('inet:fqdn', 'woohoo.wow.vertex.link')
            f1 = core.formTufoByProp('inet:fqdn', 'woot.woot.vertex.link')
            f2 = core.formTufoByProp('inet:fqdn', 'wow.ohmy.clowntown.vertex.link')

            nodes = core.eval('inet:fqdn=vertex.link tree(inet:fqdn, inet:fqdn:domain)')
            self.len(8, nodes)

            nodes = core.eval('inet:fqdn=vertex.link tree(inet:fqdn:domain)')
            self.len(8, nodes)

            nodes = core.eval('inet:fqdn=vertex.link tree(inet:fqdn:domain, recurlim=1)')
            self.len(4, nodes)

            nodes = core.eval('inet:fqdn=vertex.link tree(inet:fqdn:domain, recurlim=2)')
            self.len(7, nodes)

            # tree up
            nodes = core.eval('inet:fqdn=vertex.link tree(inet:fqdn:domain, inet:fqdn)')
            self.len(2, nodes)

            nodes = core.eval('inet:fqdn=woot.woot.vertex.link tree(inet:fqdn:domain, inet:fqdn)')
            self.len(4, nodes)

            nodes = core.eval('inet:fqdn=wow.ohmy.clowntown.vertex.link tree(inet:fqdn:domain, inet:fqdn)')
            self.len(5, nodes)

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

    def test_storm_query_log(self):
        with self.getRamCore() as core:
            with self.getLoggerStream('synapse.lib.storm') as stream:
                core.eval('#HAHA')
            stream.seek(0)
            mesgs = stream.read()
            self.eq('', mesgs.strip())

            core.setConfOpt('storm:query:log:en', 1)
            core.setConfOpt('storm:query:log:level', logging.ERROR)

            with self.getLoggerStream('synapse.lib.storm') as stream:
                core.eval('#HAHA')
            stream.seek(0)
            mesgs = stream.read()
            e = 'Executing storm query [#HAHA] as [{}]'.format(s_auth.whoami())
            self.eq(e, mesgs.strip())

    def test_storm_pivot_runt(self):
        with self.getRamCore() as core:
            # Ensure that pivot and join operations work
            self.true(len(core.eval('syn:prop:ptype=it:host :form->syn:form')) > 1)
            self.true(len(core.eval('syn:prop:ptype=it:host :form<-syn:form')) > 1)
            # Ensure limits are covered
            self.len(3, core.eval('syn:prop:ptype=it:host :form->syn:form limit(3)'))

    def test_storm_prop_gtor(self):
        with self.getRamCore() as core:

            fqdn = core.formTufoByProp('inet:fqdn', 'woot.com')

            gtor = core._getPropGtor(':zone')
            self.eq(gtor(fqdn), ('inet:fqdn:zone', 1))

            gtor = core._getPropGtor('inet:fqdn:zone')
            self.eq(gtor(fqdn), ('inet:fqdn:zone', 1))

    def test_storm_gettasks(self):
        with self.getRamCore() as core:

            def f1(mesg):
                pass

            def f2(mesg):
                pass

            core.on('task:hehe:haha', f1)
            core.on('task:hehe:haha', f2)
            core.on('task:wow', f1)

            nodes = core.eval('get:tasks()')
            self.len(2, nodes)
            for node in nodes:
                self.none(node[0])
                self.eq(node[1].get('tufo:form'), 'task')
                self.isin(node[1].get('task'), ('hehe:haha', 'wow'))

    def test_storm_filtsub(self):
        with self.getRamCore() as core:
            core.ask('[ inet:ipv4=1.2.3.4 :cc=us inet:dns:a=vertex.link/1.2.3.4 ]')
            core.ask('[ inet:ipv4=4.3.2.1 :cc=zz inet:dns:a=example.com/4.3.2.1 ]')

            self.len(1, core.eval('inet:ipv4:cc=us'))
            self.len(1, core.eval('inet:dns:a:fqdn=vertex.link'))
            self.len(1, core.eval('inet:ipv4:cc=zz'))
            self.len(1, core.eval('inet:dns:a:fqdn=example.com'))

            # lift all dns, pivot to ipv4 where cc=us (calls take), remove the results
            # this should return the example node because the vertex node matches the filter and should be removed
            nodes = core.eval('inet:dns:a -{ :ipv4 -> inet:ipv4 +:cc=us }')
            self.len(1, nodes)
            self.eq(nodes[0][1].get('inet:dns:a'), 'example.com/4.3.2.1')

            # lift all dns, pivot to ipv4 where cc=us (calls take), add the results
            # this should return the vertex node because only the vertex node matches the filter
            nodes = core.eval('inet:dns:a +{ :ipv4 -> inet:ipv4 +:cc=us }')
            self.len(1, nodes)
            self.eq(nodes[0][1].get('inet:dns:a'), 'vertex.link/1.2.3.4')

            # lift all dns, pivot to ipv4 where cc!=us (calls take), remove the results
            # this should return the vertex node because the example node matches the filter and should be removed
            nodes = core.eval('inet:dns:a -{ :ipv4 -> inet:ipv4 -:cc=us }')
            self.len(1, nodes)
            self.eq(nodes[0][1].get('inet:dns:a'), 'vertex.link/1.2.3.4')

            # lift all dns, pivot to ipv4 where cc!=us (calls take), add the results
            # this should return the example node because only the example node matches the filter
            nodes = core.eval('inet:dns:a +{ :ipv4 -> inet:ipv4 -:cc=us }')
            self.len(1, nodes)
            self.eq(nodes[0][1].get('inet:dns:a'), 'example.com/4.3.2.1')

            # lift all dns, pivot to ipv4 where asn=1234 (calls take), add the results
            # this should return nothing because no nodes have asn=1234
            self.len(0, core.eval('inet:dns:a +{ :ipv4 -> inet:ipv4 +:asn=1234 }'))

            # lift all dns, pivot to ipv4 where asn!=1234 (calls take), add the results
            # this should return everything because no nodes have asn=1234
            nodes = core.eval('inet:dns:a +{ :ipv4 -> inet:ipv4 -:asn=1234 }')
            self.len(2, nodes)
            nodes.sort(key=lambda x: x[1].get('inet:dns:a'))
            self.eq(nodes[0][1].get('inet:dns:a'), 'example.com/4.3.2.1')
            self.eq(nodes[1][1].get('inet:dns:a'), 'vertex.link/1.2.3.4')

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

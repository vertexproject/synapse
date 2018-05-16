import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.types as s_types
import synapse.lib.module as s_module

from synapse.tests.common import *

class CortexTest(SynTest):

    def test_cortex_onadd(self):

        with self.getTestCore() as core:

            with core.snap(write=True) as snap:

                func = CallBack()
                core.model.form('inet:ipv4').onAdd(func)

                node = snap.addNode('inet:ipv4', '1.2.3.4')
                self.eq(node.buid, func.args[0].buid)

    def test_cortex_indxchop(self):

        with self.getTestCore() as core:

            with core.snap(write=True) as snap:
                valu = 'a' * 257
                node = snap.addNode('teststr', valu)

                nodes = list(snap.getNodesBy('teststr', 'aa', cmpr='^='))
                self.len(1, nodes)

    def test_cortex_cell(self):

        with self.getTestDmon(mirror='dmoncore') as dmon:

            core = dmon.shared.get('core')

            nodes = ((('inet:user', 'visi'), {}), )

            core.addNodes(nodes)
            nodes = list(core.getNodesBy('inet:user', 'visi'))

            proxy = dmon._getTestProxy('core')
            nodes = list(proxy.getNodesBy('inet:user', 'visi'))

    def test_cortex_onsetdel(self):

        with self.getTestCore() as core:

            with core.snap(write=True) as snap:

                func = CallBack()
                core.model.prop('inet:ipv4:loc').onSet(func)

                node = snap.addNode('inet:ipv4', '1.2.3.4')
                node.set('loc', 'US.  VA')

                self.eq(func.args[0].buid, node.buid)
                self.eq(func.args[1], '??')

                func = CallBack()
                core.model.prop('inet:ipv4:loc').onDel(func)

                node.pop('loc')

                self.eq(func.args[0].buid, node.buid)
                self.eq(func.args[1], 'us.va')

                self.none(node.get('loc'))

            with core.snap() as snap:
                node = snap.addNode('inet:ipv4', '1.2.3.4')
                self.none(node.get('loc'))

    def test_cortex_tags(self):

        with self.getTestCore() as core:

            with core.snap(write=True) as snap:

                snap.addNode('teststr', 'newp')

                node = snap.addNode('teststr', 'one')
                node.addTag('foo.bar', ('2016', '2017'))

                self.eq((1451606400000, 1483228800000), node.getTag('foo.bar', ('2016', '2017')))

                node1 = snap.addNode('testcomp', (10, 'hehe'))
                node1.addTag('foo.bar')

                self.nn(snap.getNodeByNdef(('syn:tag', 'foo')))
                self.nn(snap.getNodeByNdef(('syn:tag', 'foo.bar')))

            with core.snap() as snap:

                node = snap.getNodeByNdef(('teststr', 'one'))

                self.true(node.hasTag('foo'))
                self.true(node.hasTag('foo.bar'))

                self.raises(s_exc.NoSuchForm, list, snap.getNodesBy('noway#foo.bar'))

                self.len(2, list(snap.getNodesBy('#foo.bar')))
                self.len(1, list(snap.getNodesBy('teststr#foo.bar')))

            with core.snap(write=True) as snap:

                node = snap.addNode('teststr', 'one')

                node.delTag('foo')

                self.false(node.hasTag('foo'))
                self.false(node.hasTag('foo.bar'))

            with core.snap() as snap:

                node = snap.addNode('teststr', 'one')
                self.false(node.hasTag('foo'))
                self.false(node.hasTag('foo.bar'))

    def test_cortex_base_types(self):

        with self.getTestCore() as core:

            with core.snap(write=True) as snap:
                node = snap.addNode('testtype10', 'one')
                node.set('intprop', 21)

            with core.snap() as snap:
                node = snap.getNodeByNdef(('testtype10', 'one'))
                self.nn(node)
                self.eq(node.get('intprop'), 21)

        with self.getTestCore() as core:

            with core.snap(write=True) as snap:

                node = snap.addNode('testtype10', 'one')
                self.nn(node.get('.created'))

                nodes = list(snap.getNodesBy('.created', '2010', cmpr='>='))

                self.eq(node.get('intprop'), 20)
                self.eq(node.get('locprop'), '??')
                self.eq(node.get('strprop'), 'asdf')

                self.true(s_common.isguid(node.get('guidprop')))

                # add another node with default vals
                snap.addNode('testtype10', 'two')

                # modify default vals on initial node
                node.set('intprop', 21)
                node.set('strprop', 'qwer')
                node.set('locprop', 'us.va.reston')

                node = snap.addNode('testcomp', (33, 'THIRTY THREE'))

                self.eq(node.get('hehe'), 33)
                self.eq(node.get('haha'), 'thirty three')

                self.false(node.set('hehe', 80))

                self.none(snap.getNodeByNdef(('testauto', 'autothis')))

                props = {
                    'bar': ('testauto', 'autothis'),
                    'baz': ('testtype10:strprop', 'WOOT'),
                    'tick': '20160505',
                }
                node = snap.addNode('teststr', 'woot', props=props)
                self.eq(node.get('bar'), ('testauto', 'autothis'))
                self.eq(node.get('baz'), ('testtype10:strprop', 'woot'))
                self.eq(node.get('tick'), 1462406400000)

                nodes = list(snap.getNodesBy('teststr:tick', '20160505'))
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('teststr', 'woot'))

                # add some time range bumper nodes
                snap.addNode('teststr', 'toolow', props={'tick': '2015'})
                snap.addNode('teststr', 'toohigh', props={'tick': '2018'})

                # test a few time range syntax options...
                nodes = list(snap.getNodesBy('teststr:tick', '2016*'))
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('teststr', 'woot'))

                # test a few time range syntax options...
                nodes = list(snap.getNodesBy('teststr:tick', ('2016', '2017'), cmpr='*range='))
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('teststr', 'woot'))

                nodes = list(snap.getNodesBy('teststr:tick', ('2016', '2017'), cmpr='*range='))
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('teststr', 'woot'))

                self.false(node.set('newp:newp', 20))

                self.nn(snap.getNodeByNdef(('testauto', 'autothis')))

                # test lifting by prop without value
                nodes = list(snap.getNodesBy('teststr:tick'))
                self.len(3, nodes)

            with core.snap(write=True) as snap:

                node = snap.addNode('testtype10', 'one')
                print(repr(node.pack()))
                self.eq(node.get('intprop'), 21)

                self.nn(node.get('.created'))

                nodes = list(snap.getNodesBy('teststr', 'too', cmpr='^='))
                self.len(2, nodes)

                # test loc prop prefix based lookup
                nodes = list(snap.getNodesBy('testtype10:locprop', 'us.va'))

                self.len(1, nodes)
                self.eq(nodes[0].ndef[1], 'one')

                nodes = list(snap.getNodesBy('testcomp', (33, 'thirty three')))

                self.len(1, nodes)

                self.eq(nodes[0].get('hehe'), 33)
                self.eq(nodes[0].ndef[1], (33, 'thirty three'))

    def test_cortex_pivprop(self):

        with self.getTestCore() as core:

            with core.snap(write=True) as snap:

                pivc = snap.addNode('pivcomp', ('woot', 'rofl'))
                self.eq(pivc.get('targ'), 'woot')

                pivt = snap.getNodeByNdef(('pivtarg', 'woot'))
                pivt.set('name', 'visi')
                self.nn(pivt)

            with core.snap() as snap:
                pivc = snap.getNodeByNdef(('pivcomp', ('woot', 'rofl')))
                self.eq(pivc.get('targ::name'), 'visi')

#FIXME THIS ALL GOES AWAY #################################################
class FIXME:

    def test_cortex_stats(self):
        rows = [
            (guid(), 'foo:bar', 1, 99),
            (guid(), 'foo:bar', 2, 99),
            (guid(), 'foo:bar', 3, 99),
            (guid(), 'foo:bar', 5, 99),
            (guid(), 'foo:bar', 8, 99),
            (guid(), 'foo:bar', 13, 99),
            (guid(), 'foo:bar', 21, 99),
        ]

        core = s_cortex.openurl('ram://')
        core.addRows(rows)

        self.eq(core.getStatByProp('sum', 'foo:bar'), 53)
        self.eq(core.getStatByProp('count', 'foo:bar'), 7)

        self.eq(core.getStatByProp('min', 'foo:bar'), 1)
        self.eq(core.getStatByProp('max', 'foo:bar'), 21)

        self.eq(core.getStatByProp('mean', 'foo:bar'), 7.571428571428571)

        self.eq(core.getStatByProp('any', 'foo:bar'), 1)
        self.eq(core.getStatByProp('all', 'foo:bar'), 1)

        histo = core.getStatByProp('histo', 'foo:bar')
        self.eq(histo.get(13), 1)

        self.raises(NoSuchStat, core.getStatByProp, 'derp', 'inet:ipv4')

        # Stats props both accept a valu and are normed
        self.nn(core.formTufoByProp('inet:ipv4', 0x01020304))
        self.nn(core.formTufoByProp('inet:ipv4', 0x05060708))
        self.eq(core.getStatByProp('count', 'inet:ipv4'), 2)
        self.eq(core.getStatByProp('count', 'inet:ipv4', 0x01020304), 1)
        self.eq(core.getStatByProp('count', 'inet:ipv4', '1.2.3.4'), 1)

    def test_cortex_fire_set(self):

        with self.getRamCore() as core:

            tufo = core.formTufoByProp('strform', 'hehe', bar='lol')

            msgs = wait = core.waiter(1, 'node:prop:set')

            core.setTufoProps(tufo, bar='hah')

            evts = wait.wait(timeout=2)

            self.eq(evts[0][0], 'node:prop:set')
            self.eq(evts[0][1]['node'][0], tufo[0])
            self.eq(evts[0][1]['form'], 'strform')
            self.eq(evts[0][1]['valu'], 'hehe')
            self.eq(evts[0][1]['prop'], 'strform:bar')
            self.eq(evts[0][1]['newv'], 'hah')
            self.eq(evts[0][1]['oldv'], 'lol')

    def test_cortex_tags(self):

        core = s_cortex.openurl('ram://')
        core.setConfOpt('caching', 1)

        core.addTufoForm('foo', ptype='str')

        hehe = core.formTufoByProp('foo', 'hehe')

        wait = core.waiter(2, 'node:tag:add')
        core.addTufoTag(hehe, 'lulz.rofl')
        wait.wait(timeout=2)

        wait = core.waiter(1, 'node:tag:add')
        core.addTufoTag(hehe, 'lulz.rofl.zebr')
        wait.wait(timeout=2)

        wait = self.getTestWait(core, 1, 'node:tag:add')
        core.addTufoTag(hehe, 'duck.quack.rofl')
        wait.wait(timeout=2)

        lulz = core.getTufoByProp('syn:tag', 'lulz')

        self.none(lulz[1].get('syn:tag:up'))
        self.eq(lulz[1].get('syn:tag:doc'), '')
        self.eq(lulz[1].get('syn:tag:title'), '')
        self.eq(lulz[1].get('syn:tag:depth'), 0)
        self.eq(lulz[1].get('syn:tag:base'), 'lulz')

        rofl = core.getTufoByProp('syn:tag', 'lulz.rofl')

        self.eq(rofl[1].get('syn:tag:doc'), '')
        self.eq(rofl[1].get('syn:tag:title'), '')
        self.eq(rofl[1].get('syn:tag:up'), 'lulz')

        self.eq(rofl[1].get('syn:tag:depth'), 1)
        self.eq(rofl[1].get('syn:tag:base'), 'rofl')

        tags = core.getTufosByProp('syn:tag:base', 'rofl')
        self.len(2, tags)
        tags = core.getTufosByProp('syn:tag:base', 'rofl', limit=1)
        self.len(1, tags)
        tags = core.getTufosByProp('syn:tag:base', 'rofl', limit=0)
        self.len(0, tags)

        wait = core.waiter(2, 'node:tag:del')
        hehe = core.delTufoTag(hehe, 'lulz.rofl')
        self.nn(hehe)
        self.isin('#lulz', hehe[1])
        self.notin('#lulz.rofl', hehe[1])
        self.notin('#lulz.rofl.zebr', hehe[1])
        wait.wait(timeout=2)

        wait = core.waiter(1, 'node:tag:del')
        core.delTufo(lulz)
        wait.wait(timeout=2)
        # tag and subs should be wiped

        self.none(core.getTufoByProp('syn:tag', 'lulz'))
        self.none(core.getTufoByProp('syn:tag', 'lulz.rofl'))
        self.none(core.getTufoByProp('syn:tag', 'lulz.rofl.zebr'))

        self.eq(len(core.getTufosByTag('lulz', form='foo')), 0)
        self.eq(len(core.getTufosByTag('lulz.rofl', form='foo')), 0)
        self.eq(len(core.getTufosByTag('lulz.rofl.zebr', form='foo')), 0)

        # Now we need to retag a node, ensure that the tag is on the node and the syn:tag nodes exist again
        wait = core.waiter(1, 'node:tag:add')
        node = core.addTufoTag(hehe, 'lulz.rofl.zebr')
        wait.wait(timeout=2)

        self.isin('#lulz.rofl.zebr', node[1])
        self.nn(core.getTufoByProp('syn:tag', 'lulz'))
        self.nn(core.getTufoByProp('syn:tag', 'lulz.rofl'))
        self.nn(core.getTufoByProp('syn:tag', 'lulz.rofl.zebr'))

        # Ensure we're making nodes which have a timebox
        node = core.addTufoTag(node, 'foo.bar@20171217')
        self.eq(s_tufo.ival(node, '#foo.bar'), (1513468800000, 1513468800000))
        # Ensure the times argument is respected
        node = core.addTufoTag(node, 'foo.duck', times=(1513382400000, 1513468800000))
        self.eq(s_tufo.ival(node, '#foo.duck'), (1513382400000, 1513468800000))

        # Recreate expected results from #320 to ensure
        # we're also doing the same via storm
        self.eq(len(core.eval('[inet:fqdn=w00t.com +#some.tag]')), 1)
        self.eq(len(core.eval('inet:fqdn=w00t.com')), 1)
        self.eq(len(core.eval('inet:fqdn=w00t.com +node:created<1')), 0)
        self.eq(len(core.eval('inet:fqdn=w00t.com +node:created>1')), 1)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0)')), 2)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0, limit=3)')), 2)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0, limit=2)')), 2)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0, limit=1)')), 1)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0, limit=0)')), 0)
        self.raises(BadOperArg, core.eval, 'inet:fqdn=w00t.com totags(leaf=0, limit=-1)')
        self.eq(len(core.eval('syn:tag=some')), 1)
        self.eq(len(core.eval('syn:tag=some.tag')), 1)
        self.eq(len(core.eval('syn:tag=some delnode(force=1)')), 0)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0)')), 0)
        self.eq(len(core.eval('inet:fqdn=w00t.com [ +#some.tag ]')), 1)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0)')), 2)
        self.eq(len(core.eval('syn:tag=some')), 1)
        self.eq(len(core.eval('syn:tag=some.tag')), 1)
        core.fini()

    def test_cortex_splices(self):

        with self.getRamCore() as core0, self.getRamCore() as core1:

            # Form a tufo before we start sending splices
            tufo_before1 = core0.formTufoByProp('strform', 'before1')
            tufo_before2 = core0.formTufoByProp('strform', 'before2')
            core0.addTufoTag(tufo_before2, 'hoho')  # this will not be synced

            # Start sending splices
            def splicecore(mesg):
                core1.splice(mesg[1].get('mesg'))

            core0.on('splice', splicecore)
            core0.delTufo(tufo_before1)

            # Add node by forming it
            tufo0 = core0.formTufoByProp('strform', 'bar', foo='faz')
            tufo1 = core1.getTufoByProp('strform', 'bar')

            self.eq(tufo1[1].get('strform'), 'bar')
            self.eq(tufo1[1].get('strform:foo'), 'faz')

            # Add tag to existing node
            tufo0 = core0.addTufoTag(tufo0, 'hehe')
            tufo1 = core1.getTufoByProp('strform', 'bar')

            self.true(s_tufo.tagged(tufo1, 'hehe'))

            # Del tag from existing node
            core0.delTufoTag(tufo0, 'hehe')
            tufo1 = core1.getTufoByProp('strform', 'bar')
            self.false(s_tufo.tagged(tufo1, 'hehe'))

            # Set prop on existing node
            core0.setTufoProp(tufo0, 'foo', 'lol')
            tufo1 = core1.getTufoByProp('strform', 'bar')
            self.eq(tufo1[1].get('strform:foo'), 'lol')

            # Del existing node
            core0.delTufo(tufo0)
            tufo1 = core1.getTufoByProp('strform', 'bar')
            self.none(tufo1)

            # Tag a node in first core, ensure it does not get formed in the second core.
            # This is because only node:add splices make nodes.
            core0.addTufoTag(tufo_before2, 'hehe')
            tufo1 = core1.getTufoByProp('strform', 'before2')
            self.none(tufo1)
            core0.delTufoTag(tufo_before2, 'hehe')
            tufo1 = core1.getTufoByProp('strform', 'before2')
            self.none(tufo1)

            # Add a complicated node which fires a bunch of autoadd nodes and
            # ensure they are populated in the second core
            postref_tufo = core0.formTufoByProp('inet:web:postref',
                                                (('vertex.link/user', 'mypost 0.0.0.0'),
                                                 ('inet:ipv4', 0)))
            self.nn(core1.getTufoByProp('inet:web:post',
                                        ('vertex.link/user', 'mypost 0.0.0.0')))
            self.eq(postref_tufo[1]['tufo:form'], 'inet:web:postref')
            self.eq(postref_tufo[1]['inet:web:postref'], '804ec63392f4ea031bb3fd004dee209d')
            self.eq(postref_tufo[1]['inet:web:postref:post'], '68bc4607f0518963165536921d6e86fa')
            self.eq(postref_tufo[1]['inet:web:postref:xref'], 'inet:ipv4=0.0.0.0')
            self.eq(postref_tufo[1]['inet:web:postref:xref:prop'], 'inet:ipv4')
            self.eq(postref_tufo[1]['inet:web:postref:xref:intval'], 0)

            # Ensure we got the deconflicted node that was already made, not a new node
            post_tufo = core1.formTufoByProp('inet:web:post',
                                             ('vertex.link/user', 'mypost 0.0.0.0'))
            self.notin('.new', post_tufo[1])
            self.eq(post_tufo[1]['inet:web:post'], postref_tufo[1]['inet:web:postref:post'])
            # Ensure that subs on the autoadd node are formed properly
            self.eq(post_tufo[1].get('inet:web:post:acct'), 'vertex.link/user')
            self.eq(post_tufo[1].get('inet:web:post:text'), 'mypost 0.0.0.0')
            # Ensure multiple subs were made into nodes
            self.nn(core1.getTufoByProp('inet:web:acct', 'vertex.link/user'))
            self.nn(core1.getTufoByProp('inet:user', 'user'))
            self.nn(core1.getTufoByProp('inet:fqdn', 'vertex.link'))
            self.nn(core1.getTufoByProp('inet:fqdn', 'link'))

    def test_cortex_splices_user(self):
        splices = []
        with self.getRamCore() as core:  # type: s_cores_common.Cortex
            def add_splice(mesg):
                splice = mesg[1].get('mesg')
                splices.append(splice)
            core.on('splice', add_splice)

            t0 = core.formTufoByProp('strform', 'hi')
            t0 = core.setTufoProp(t0, 'baz', 123)
            t0 = core.addTufoTag(t0, 'hello.gaiz')
            t0 = core.delTufoTag(t0, 'hello.gaiz')

            t0 = core.setTufoIval(t0, 'dude', (1, 2))
            t0 = core.delTufoIval(t0, 'dude')

            users = {splice[1].get('user') for splice in splices}
            self.eq(users, {'root@localhost'})

            with s_auth.runas('evil.haxx0r'):
                t0 = core.delTufoProp(t0, 'baz')

            users = {splice[1].get('user') for splice in splices}
            self.eq(users, {'root@localhost', 'evil.haxx0r'})

            with s_auth.runas('bob.grey@vertex.link'):
                t0 = core.delTufo(t0)
                self.none(t0)

            users = {splice[1].get('user') for splice in splices}
            self.eq(users, {'root@localhost', 'evil.haxx0r',
                            'bob.grey@vertex.link'})

    def test_cortex_dict(self):
        core = s_cortex.openurl('ram://')
        core.addTufoForm('foo:bar', ptype='int')
        core.addTufoForm('baz:faz', ptype='int', defval=22)

        modl = core.getModelDict()
        self.eq(modl['forms'][-2:], ['foo:bar', 'baz:faz'])
        self.eq(modl['props']['foo:bar'][1]['ptype'], 'int')
        self.eq(modl['props']['baz:faz'][1]['defval'], 22)

        core.fini()

    def test_cortex_comp(self):
        core = s_cortex.openurl('ram://')

        fields = 'fqdn,inet:fqdn|ipv4,inet:ipv4|time,time:epoch'
        core.addType('foo:a', subof='comp', fields=fields)

        core.addTufoForm('foo:a', ptype='foo:a')
        core.addTufoProp('foo:a', 'fqdn', ptype='inet:fqdn')
        core.addTufoProp('foo:a', 'ipv4', ptype='inet:ipv4')
        core.addTufoProp('foo:a', 'time', ptype='time:epoch')

        arec = ('wOOt.com', 0x01020304, 0x00404040)

        dnsa = core.formTufoByProp('foo:a', arec)

        fval = guid(('woot.com', 0x01020304, 0x00404040))

        self.eq(dnsa[1].get('foo:a'), fval)
        self.eq(dnsa[1].get('foo:a:fqdn'), 'woot.com')
        self.eq(dnsa[1].get('foo:a:ipv4'), 0x01020304)
        self.eq(dnsa[1].get('foo:a:time'), 0x00404040)

        core.fini()

    def test_cortex_enforce(self):

        with self.getRamCore() as core:
            # Disable enforce for first set of tests
            core.setConfOpt('enforce', 0)

            core.addTufoForm('foo:bar', ptype='inet:email')

            core.addTufoForm('foo:baz', ptype='inet:email')
            core.addTufoProp('foo:baz', 'fqdn', ptype='inet:fqdn')
            core.addTufoProp('foo:baz', 'haha', ptype='int')

            cofo = core.getTufoByProp('syn:core', 'self')
            self.nn(cofo)
            self.false(core.enforce)

            self.true(core.isSetPropOk('foo:bar:customprop'))
            self.true(core.isSetPropOk('foo:baz:fqdn'))
            self.true(core.isSetPropOk('foo:baz:haha'))
            self.true(core.isSetPropOk('foo:baz:duck'))

            # we can make nodes from props (not forms!)
            node0 = core.formTufoByProp('foo:baz:fqdn', 'woot.com')
            self.nn(node0)
            self.eq(node0[1].get('tufo:form'), 'foo:baz:fqdn')
            self.eq(node0[1].get('foo:baz:fqdn'), 'woot.com')

            # Now re-enable enforce
            core.setConfOpt('enforce', 1)

            self.true(core.enforce)

            self.false(core.isSetPropOk('foo:bar:customprop'))
            self.true(core.isSetPropOk('foo:baz:fqdn'))
            self.true(core.isSetPropOk('foo:baz:haha'))
            self.false(core.isSetPropOk('foo:baz:duck'))

            tufo0 = core.formTufoByProp('foo:bar', 'foo@bar.com', hehe=10, haha=20)
            tufo1 = core.formTufoByProp('foo:baz', 'foo@bar.com', hehe=10, haha=20)

            # did it remove the non-declared props and subprops?
            self.none(tufo0[1].get('foo:bar:fqdn'))
            self.none(tufo0[1].get('foo:bar:hehe'))
            self.none(tufo0[1].get('foo:bar:haha'))

            # did it selectivly keep the declared props and subprops
            self.eq(tufo1[1].get('foo:baz:haha'), 20)
            self.eq(tufo1[1].get('foo:baz:fqdn'), 'bar.com')

            self.none(tufo1[1].get('foo:baz:hehe'))
            self.none(tufo1[1].get('foo:baz:user'))

            tufo0 = core.setTufoProps(tufo0, fqdn='visi.com', hehe=11)
            tufo1 = core.setTufoProps(tufo1, fqdn='visi.com', hehe=11, haha=21)

            self.none(tufo0[1].get('foo:bar:fqdn'))
            self.none(tufo0[1].get('foo:bar:hehe'))

            self.none(tufo1[1].get('foo:baz:hehe'))

            self.eq(tufo1[1].get('foo:baz:haha'), 21)
            self.eq(tufo1[1].get('foo:baz:fqdn'), 'visi.com')

            # Prevent the core from storing new types it does not know about
            self.raises(NoSuchForm, core.formTufoByProp, 'foo:duck', 'something')
            # Ensure that we cannot form nodes from Types alone - we must use forms
            self.raises(NoSuchForm, core.formTufoByProp, 'str', 'we all float down here')
            self.raises(NoSuchForm, core.formTufoByProp, 'inet:srv4', '1.2.3.4:8080')
            # Ensure that we cannot form nodes from non-form prop's which do not have ctors
            self.raises(NoSuchForm, core.formTufoByProp, 'foo:baz:fqdn', 'woot.com')

    def test_cortex_minmax(self):

        with self.getRamCore() as core:

            core.addTufoForm('foo', ptype='str')
            core.addTufoProp('foo', 'min', ptype='int:min')
            core.addTufoProp('foo', 'max', ptype='int:max')

            props = {'min': 20, 'max': 20}
            tufo0 = core.formTufoByProp('foo', 'derp', **props)

            tufo0 = core.setTufoProp(tufo0, 'min', 30)
            self.eq(tufo0[1].get('foo:min'), 20)

            tufo0 = core.setTufoProp(tufo0, 'min', 10)
            self.eq(tufo0[1].get('foo:min'), 10)

            tufo0 = core.setTufoProp(tufo0, 'max', 10)
            self.eq(tufo0[1].get('foo:max'), 20)

            tufo0 = core.setTufoProp(tufo0, 'max', 30)
            self.eq(tufo0[1].get('foo:max'), 30)

    def test_cortex_minmax_epoch(self):

        with self.getRamCore() as core:

            core.addTufoForm('foo', ptype='str')
            core.addTufoProp('foo', 'min', ptype='time:epoch:min')
            core.addTufoProp('foo', 'max', ptype='time:epoch:max')

            props = {'min': 20, 'max': 20}
            tufo0 = core.formTufoByProp('foo', 'derp', **props)

            tufo0 = core.setTufoProp(tufo0, 'min', 30)
            self.eq(tufo0[1].get('foo:min'), 20)

            tufo0 = core.setTufoProp(tufo0, 'min', 10)
            self.eq(tufo0[1].get('foo:min'), 10)

            tufo0 = core.setTufoProp(tufo0, 'max', 10)
            self.eq(tufo0[1].get('foo:max'), 20)

            tufo0 = core.setTufoProp(tufo0, 'max', 30)
            self.eq(tufo0[1].get('foo:max'), 30)

    def test_cortex_by_type(self):

        with self.getRamCore() as core:

            core.addTufoForm('foo', ptype='str')
            core.addTufoProp('foo', 'min', ptype='time:epoch:min')
            core.addTufoProp('foo', 'max', ptype='time:epoch:max')

            core.addTufoForm('bar', ptype='str')
            core.addTufoProp('bar', 'min', ptype='time:epoch:min')
            core.addTufoProp('bar', 'max', ptype='time:epoch:max')

            core.addTufoForm('baz', ptype='str')
            core.addTufoProp('baz', 'min', ptype='time:epoch')
            core.addTufoProp('baz', 'max', ptype='time:epoch')

            props = {'min': 20, 'max': 20}

            tufo0 = core.formTufoByProp('foo', 'hurr', **props)
            tufo1 = core.formTufoByProp('bar', 'durr', **props)
            tufo2 = core.formTufoByProp('baz', 'durr', **props)

            want = tuple(sorted([tufo0[0], tufo1[0]]))

            res0 = core.getTufosByPropType('time:epoch:min', valu=20)
            self.eq(tuple(sorted([r[0] for r in res0])), want)

    def test_cortex_caching(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar', baz=2)
            tufo1 = core.formTufoByProp('strform', 'baz', baz=2)

            answ0 = core.getTufosByProp('strform')
            answ1 = core.getTufosByProp('strform', valu='bar')

            self.eq(len(answ0), 2)
            self.eq(len(answ1), 1)

            self.eq(len(core.cache_fifo), 0)
            self.eq(len(core.cache_bykey), 0)
            self.eq(len(core.cache_byiden), 0)
            self.eq(len(core.cache_byprop), 0)

            core.setConfOpt('caching', 1)

            self.eq(core.caching, 1)

            answ0 = core.getTufosByProp('strform')

            self.eq(len(answ0), 2)
            self.eq(len(core.cache_fifo), 1)
            self.eq(len(core.cache_bykey), 1)
            self.eq(len(core.cache_byiden), 2)
            self.eq(len(core.cache_byprop), 1)

            tufo0 = core.formTufoByProp('strform', 'bar')
            tufo0 = core.addTufoTag(tufo0, 'hehe')

            self.eq(len(core.getTufosByTag('hehe', form='strform')), 1)
            core.delTufoTag(tufo0, 'hehe')

            tufo0 = core.getTufoByProp('strform', 'bar')
            self.noprop(tufo0[1], '#hehe')

    def test_cortex_caching_set(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar', baz=10)
            tufo1 = core.formTufoByProp('strform', 'baz', baz=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('strform:baz')
            tufs1 = core.getTufosByProp('strform:baz', valu=10)
            tufs2 = core.getTufosByProp('strform:baz', valu=11)
            tufs3 = core.getTufosByProp('strform:baz', valu=10, limit=2)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)
            self.eq(len(tufs2), 0)
            self.eq(len(tufs3), 2)

            # inspect the details of the cache data structures when setTufoProps
            # causes an addition or removal...
            self.nn(core.cache_bykey.get(('strform:baz', 10, None)))
            self.nn(core.cache_bykey.get(('strform:baz', None, None)))

            # we should have hit the unlimited query and not created a new cache hit...
            self.none(core.cache_bykey.get(('strform:baz', 10, 2)))

            self.nn(core.cache_byiden.get(tufo0[0]))
            self.nn(core.cache_byiden.get(tufo1[0]))

            self.nn(core.cache_byprop.get(('strform:baz', 10)))
            self.nn(core.cache_byprop.get(('strform:baz', None)))

            core.setTufoProp(tufo0, 'baz', 11)

            # the cached results should be updated
            tufs0 = core.getTufosByProp('strform:baz')
            tufs1 = core.getTufosByProp('strform:baz', valu=10)
            tufs2 = core.getTufosByProp('strform:baz', valu=11)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 1)
            self.eq(len(tufs2), 1)

            self.eq(tufs1[0][0], tufo1[0])
            self.eq(tufs2[0][0], tufo0[0])

    def test_cortex_caching_add_tufo(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar', baz=10)
            tufo1 = core.formTufoByProp('strform', 'baz', baz=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('strform:baz')
            tufs1 = core.getTufosByProp('strform:baz', valu=10)
            tufs2 = core.getTufosByProp('strform:baz', valu=11)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)
            self.eq(len(tufs2), 0)

            tufo2 = core.formTufoByProp('strform', 'lol', baz=10)

            tufs0 = core.getTufosByProp('strform:baz')
            tufs1 = core.getTufosByProp('strform:baz', valu=10)
            tufs2 = core.getTufosByProp('strform:baz', valu=11)

            self.eq(len(tufs0), 3)
            self.eq(len(tufs1), 3)
            self.eq(len(tufs2), 0)

    def test_cortex_caching_del_tufo(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar', baz=10)
            tufo1 = core.formTufoByProp('strform', 'baz', baz=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('strform:baz')
            tufs1 = core.getTufosByProp('strform:baz', valu=10)
            tufs2 = core.getTufosByProp('strform:baz', valu=11)

            # Ensure we have cached the tufos we're deleting.
            self.nn(core.cache_byiden.get(tufo0[0]))
            self.nn(core.cache_byiden.get(tufo1[0]))

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)
            self.eq(len(tufs2), 0)

            # Delete an uncached object - here the tufo contents was cached
            # during lifts but the object itself is a different tuple id()
            core.delTufo(tufo0)

            tufs0 = core.getTufosByProp('strform:baz')
            tufs1 = core.getTufosByProp('strform:baz', valu=10)
            tufs2 = core.getTufosByProp('strform:baz', valu=11)

            self.eq(len(tufs0), 1)
            self.eq(len(tufs1), 1)
            self.eq(len(tufs2), 0)

            # Delete an object which was actually cached during lift
            core.delTufo(tufs0[0])
            tufs0 = core.getTufosByProp('strform:baz')
            self.eq(len(tufs0), 0)

    def test_cortex_caching_del_tufo_prop(self):
        with self.getRamCore() as core:
            core.setConfOpt('caching', 1)
            t0 = core.formTufoByProp('strform', 'stuff', baz=10)
            self.eq(t0[1].get('strform:baz'), 10)
            core.delTufoProp(t0, 'baz')
            t0 = core.getTufoByProp('strform', 'stuff')
            self.eq(t0[1].get('strform:baz'), None)

    def test_cortex_caching_atlimit(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar', baz=10)
            tufo1 = core.formTufoByProp('strform', 'baz', baz=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('strform:baz', limit=2)
            tufs1 = core.getTufosByProp('strform:baz', valu=10, limit=2)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)

            # when an entry is deleted from a cache result that was at it's limit
            # it should be fully invalidated

            core.delTufo(tufo0)

            self.none(core.cache_bykey.get(('strform:baz', None, 2)))
            self.none(core.cache_bykey.get(('strform:baz', 10, 2)))

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar', baz=10)
            tufo1 = core.formTufoByProp('strform', 'baz', baz=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('strform:baz', limit=2)
            tufs1 = core.getTufosByProp('strform:baz', valu=10, limit=2)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)

            tufo2 = core.formTufoByProp('strform', 'baz', baz=10)

            # when an entry is added from a cache result that was at it's limit
            # it should *not* be invalidated

            self.nn(core.cache_bykey.get(('strform:baz', None, 2)))
            self.nn(core.cache_bykey.get(('strform:baz', 10, 2)))

    def test_cortex_caching_under_limit(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar', baz=10)
            tufo1 = core.formTufoByProp('strform', 'baz', baz=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('strform:baz', limit=9)
            tufs1 = core.getTufosByProp('strform:baz', valu=10, limit=9)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)

            # when an entry is deleted from a cache result that was under it's limit
            # it should be removed but *not* invalidated

            core.delTufo(tufo0)

            self.nn(core.cache_bykey.get(('strform:baz', None, 9)))
            self.nn(core.cache_bykey.get(('strform:baz', 10, 9)))

            tufs0 = core.getTufosByProp('strform:baz', limit=9)
            tufs1 = core.getTufosByProp('strform:baz', valu=10, limit=9)

            self.eq(len(tufs0), 1)
            self.eq(len(tufs1), 1)

    def test_cortex_caching_oneref(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar')

            core.setConfOpt('caching', 1)

            ref0 = core.getTufosByProp('strform', valu='bar')[0]
            ref1 = core.getTufosByProp('strform', valu='bar')[0]

            self.eq(id(ref0), id(ref1))

    def test_cortex_caching_tags(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar')
            tufo1 = core.formTufoByProp('strform', 'baz')

            core.addTufoTag(tufo0, 'hehe')

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByTag('hehe', form='strform')

            core.addTufoTag(tufo1, 'hehe')

            tufs1 = core.getTufosByTag('hehe', form='strform')
            self.eq(len(tufs1), 2)

            core.delTufoTag(tufo0, 'hehe')

            tufs2 = core.getTufosByTag('hehe', form='strform')
            self.eq(len(tufs2), 1)

    def test_cortex_caching_new(self):

        with self.getRamCore() as core:

            core.setConfOpt('caching', 1)

            tufo0 = core.formTufoByProp('strform', 'bar')
            tufo1 = core.formTufoByProp('strform', 'bar')

            self.true(tufo0[1].get('.new'))
            self.false(tufo1[1].get('.new'))

    def test_cortex_caching_disable(self):

        with self.getRamCore() as core:

            core.setConfOpt('caching', 1)

            tufo = core.formTufoByProp('strform', 'bar')

            self.nn(core.cache_byiden.get(tufo[0]))
            self.nn(core.cache_bykey.get(('strform', 'bar', 1)))
            self.nn(core.cache_byprop.get(('strform', 'bar')))
            self.eq(len(core.cache_fifo), 1)

            core.setConfOpt('caching', 0)

            self.none(core.cache_byiden.get(tufo[0]))
            self.none(core.cache_bykey.get(('strform', 'bar', 1)))
            self.none(core.cache_byprop.get(('strform', 'bar')))
            self.eq(len(core.cache_fifo), 0)

    def test_cortex_reqstor(self):
        # Ensure that the cortex won't let us store data that is invalid
        # This requires us to disable enforcement, since otherwise all
        # data is normed and that fails with BadTypeValu instead
        with self.getRamCore() as core:
            core.setConfOpt('enforce', 0)
            self.raises(BadPropValu, core.formTufoByProp, 'foo:bar', True)

    def test_cortex_splicefd(self):
        with self.getTestDir() as path:
            with genfile(path, 'savefile.mpk') as fd:
                with self.getRamCore() as core:
                    core.addSpliceFd(fd)

                    tuf0 = core.formTufoByProp('inet:fqdn', 'woot.com')
                    tuf1 = core.formTufoByProp('inet:fqdn', 'newp.com')

                    core.addTufoTag(tuf0, 'foo.bar')
                    # this should leave the tag foo
                    core.delTufoTag(tuf0, 'foo.bar')

                    core.delTufo(tuf1)

                fd.seek(0)

                with self.getRamCore() as core:

                    core.eatSpliceFd(fd)

                    self.none(core.getTufoByProp('inet:fqdn', 'newp.com'))
                    self.nn(core.getTufoByProp('inet:fqdn', 'woot.com'))

                    self.eq(len(core.getTufosByTag('foo.bar', form='inet:fqdn')), 0)
                    self.eq(len(core.getTufosByTag('foo', form='inet:fqdn')), 1)

    def test_cortex_addmodel(self):

        with self.getRamCore() as core:

            core.addDataModel('a.foo.module',
                {
                    'prefix': 'foo',

                    'types': (
                        ('foo:bar', {'subof': 'str:lwr'}),
                    ),

                    'forms': (
                        ('foo:baz', {'ptype': 'foo:bar'}, [
                            ('faz', {'ptype': 'str:lwr'}),
                        ]),
                    ),
                })

            tyfo = core.getTufoByProp('syn:type', 'foo:bar')
            self.eq(tyfo[1].get('syn:type:subof'), 'str:lwr')

            fofo = core.getTufoByProp('syn:form', 'foo:baz')
            self.eq(fofo[1].get('syn:form:ptype'), 'foo:bar')

            pofo = core.getTufoByProp('syn:prop', 'foo:baz:faz')
            self.eq(pofo[1].get('syn:prop:ptype'), 'str:lwr')

            tuf0 = core.formTufoByProp('foo:baz', 'AAA', faz='BBB')
            self.eq(tuf0[1].get('foo:baz'), 'aaa')
            self.eq(tuf0[1].get('foo:baz:faz'), 'bbb')

            self.nn(core.getTufoByProp('syn:type', 'foo:bar'))
            self.nn(core.getTufoByProp('syn:form', 'foo:baz'))
            self.nn(core.getTufoByProp('syn:prop', 'foo:baz:faz'))

        with self.getRamCore() as core:
            core.addDataModels([('a.foo.module',
                {
                    'prefix': 'foo',
                    'version': 201612201147,

                    'types': (
                        ('foo:bar', {'subof': 'str:lwr'}),
                    ),

                    'forms': (
                        ('foo:baz', {'ptype': 'foo:bar'}, [
                            ('faz', {'ptype': 'str:lwr'}),
                        ]),
                    ),
                })])

            tuf0 = core.formTufoByProp('foo:baz', 'AAA', faz='BBB')
            self.eq(tuf0[1].get('foo:baz'), 'aaa')
            self.eq(tuf0[1].get('foo:baz:faz'), 'bbb')

            self.nn(core.getTufoByProp('syn:type', 'foo:bar'))
            self.nn(core.getTufoByProp('syn:form', 'foo:baz'))
            self.nn(core.getTufoByProp('syn:prop', 'foo:baz:faz'))

    def test_cortex_splicepump(self):

        with s_cortex.openurl('ram://') as core0:

            with s_cortex.openurl('ram://') as core1:

                with core0.getSplicePump(core1):
                    tufo0 = core0.formTufoByProp('inet:fqdn', 'woot.com')

                tufo1 = core1.getTufoByProp('inet:fqdn', 'woot.com')
                self.nn(tufo1)

                # node:created rows are not sent with the splice and will be created by the target core
                self.ge(tufo1[1]['node:created'], tufo0[1]['node:created'])

    def test_cortex_snap_deadlock(self):
        N = 100
        fd = tempfile.NamedTemporaryFile()
        evnt = threading.Event()
        dmon = s_daemon.Daemon()
        pool = s_threads.Pool(size=4, maxsize=8)

        with s_cortex.openurl('sqlite:///%s' % fd.name) as core:

            def populate():
                for i in range(N):
                    core.formTufoByProp('inet:ipv4', str(i), **{})
                evnt.set()

            dmon.share('core', core)
            link = dmon.listen('tcp://127.0.0.1:0/core')
            prox = s_telepath.openurl('tcp://127.0.0.1:%d/core' % link[1]['port'])

            pool.call(populate)
            for i in range(N):
                tufos = prox.getTufosByProp('inet:ipv4')

            self.true(evnt.wait(timeout=3))
            pool.fini()

    def test_cortex_seed(self):

        with self.getRamCore() as core:

            def seedFooBar(prop, valu, **props):
                return core.formTufoByProp('inet:fqdn', valu, **props)

            core.addSeedCtor('foo:bar', seedFooBar)
            tufo = core.formTufoByProp('foo:bar', 'woot.com')
            self.eq(tufo[1].get('inet:fqdn'), 'woot.com')

    def test_cortex_bytype(self):
        with self.getRamCore() as core:
            core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            self.eq(len(core.eval('inet:ipv4*type="1.2.3.4"')), 2)

    def test_cortex_seq(self):
        with self.getRamCore() as core:

            core.formTufoByProp('syn:seq', 'foo')
            node = core.formTufoByProp('syn:seq', 'bar', nextvalu=10, width=4)

            self.eq(core.nextSeqValu('foo'), 'foo0')
            self.eq(core.nextSeqValu('foo'), 'foo1')

            self.eq(core.nextSeqValu('bar'), 'bar0010')
            self.eq(core.nextSeqValu('bar'), 'bar0011')

            self.raises(NoSuchSeq, core.nextSeqValu, 'lol')

    def test_cortex_ingest(self):

        data = {'results': {'fqdn': 'woot.com', 'ipv4': '1.2.3.4'}}

        with self.getRamCore() as core:

            idef = {
                'ingest': {
                    'forms': [
                        ['inet:fqdn', {'path': 'results/fqdn'}]
                    ]
                }
            }

            core.setGestDef('test:whee', idef)

            self.nn(core.getTufoByProp('syn:ingest', 'test:whee'))
            self.none(core.getTufoByProp('inet:fqdn', 'woot.com'))
            self.none(core.getTufoByProp('inet:ipv4', '1.2.3.4'))

            core.addGestData('test:whee', data)

            self.nn(core.getTufoByProp('inet:fqdn', 'woot.com'))
            self.none(core.getTufoByProp('inet:ipv4', '1.2.3.4'))

            idef['ingest']['forms'].append(('inet:ipv4', {'path': 'results/ipv4'}))

            core.setGestDef('test:whee', idef)
            core.addGestData('test:whee', data)

            self.nn(core.getTufoByProp('inet:fqdn', 'woot.com'))
            self.nn(core.getTufoByProp('inet:ipv4', '1.2.3.4'))

    def test_cortex_tagform(self):

        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:fqdn', 'vertex.link')

            core.addTufoTag(node, 'foo.bar')

            tdoc = core.getTufoByProp('syn:tagform', ('foo.bar', 'inet:fqdn'))

            self.nn(tdoc)

            self.eq(tdoc[1].get('syn:tagform:tag'), 'foo.bar')
            self.eq(tdoc[1].get('syn:tagform:form'), 'inet:fqdn')

            self.eq(tdoc[1].get('syn:tagform:doc'), '??')
            self.eq(tdoc[1].get('syn:tagform:title'), '??')

    def test_cortex_splices_errs(self):

        splices = [
            ('newp:fake', {}),
            ('node:add', {'form': 'inet:fqdn', 'valu': 'vertex.link'})
        ]

        with self.getRamCore() as core:
            errs = core.splices(splices)
            self.eq(len(errs), 1)
            self.eq(errs[0][0][0], 'newp:fake')
            self.nn(core.getTufoByProp('inet:fqdn', 'vertex.link'))

    def test_cortex_norm_fail(self):
        with self.getRamCore() as core:
            core.formTufoByProp('inet:web:acct', 'vertex.link/visi')
            self.raises(BadTypeValu, core.eval, 'inet:web:acct="totally invalid input"')

    def test_cortex_local(self):
        splices = []
        with self.getRamCore() as core:

            core.on('splice', splices.append)
            node = core.formTufoByProp('syn:splice', None)

            self.nn(node)
            self.nn(node[0])

        self.eq(len(splices), 0)

    def test_cortex_module(self):

        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:ipv4', '1.2.3.4')
            self.eq(node[1].get('inet:ipv4:asn'), -1)

            mods = (('synapse.tests.test_cortex.CoreTestModule', {'foobar': True}), )

            core.setConfOpt('rev:model', 1)
            core.setConfOpt('modules', mods)

            # Get a list of modules which are loaded in the Cortex
            modules = core.getCoreMods()
            self.gt(len(modules), 2)
            self.isin('synapse.models.syn.SynMod', modules)
            self.isin('synapse.tests.test_cortex.CoreTestModule', modules)

            # directly access the module so we can confirm it gets fini()
            modu = core.coremods.get('synapse.tests.test_cortex.CoreTestModule')

            self.true(modu.foobar)

            self.nn(core.getTypeInst('test:type1'))
            self.nn(core.getTypeInst('test:type2'))
            self.none(core.getTypeInst('test:type3'))

            self.eq(core.getModlVers('test'), 201707210101)

            node = core.formTufoByProp('inet:ipv4', '1.2.3.5')
            self.eq(node[1].get('inet:ipv4:asn'), 10)

            iden = guid()
            node = core.formTufoByProp('ou:org', iden)
            core.delTufo(node)

            self.len(1, modu.added)
            self.len(1, modu.deled)

            self.eq(modu.added[0][0], node[0])
            self.eq(modu.deled[0][0], node[0])

        self.true(modu.isfini)

    def test_cortex_modlvers(self):

        with self.getRamCore() as core:

            self.eq(core.getModlVers('hehe'), -1)

            core.setModlVers('hehe', 10)
            self.eq(core.getModlVers('hehe'), 10)

            core.setModlVers('hehe', 20)
            self.eq(core.getModlVers('hehe'), 20)

    def test_cortex_modlrevs(self):

        with self.getRamCore() as core:

            def v0():
                core.formTufoByProp('inet:fqdn', 'foo.com')

            def v1():
                core.formTufoByProp('inet:fqdn', 'bar.com')

            def v2():
                core.formTufoByProp('inet:fqdn', 'baz.com')

            core.setConfOpt('rev:model', 0)
            self.raises(NoRevAllow, core.revModlVers, 'grok', 0, v0)

            core.setConfOpt('rev:model', 1)

            self.true(core.revModlVers('grok', 0, v0))
            self.true(core.revModlVers('grok', 1, v1))

            self.nn(core.getTufoByProp('inet:fqdn', 'foo.com'))
            self.nn(core.getTufoByProp('inet:fqdn', 'bar.com'))
            self.none(core.getTufoByProp('inet:fqdn', 'baz.com'))

            self.eq(core.getModlVers('grok'), 1)

            core.setModlVers('grok', 2)
            core.revModlVers('grok', 2, v2)

            self.none(core.getTufoByProp('inet:fqdn', 'baz.com'))

    def test_cortex_isnew(self):
        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'test.db')
            with s_cortex.openurl('sqlite:///%s' % (path,)) as core:
                self.true(core.isnew)

            with s_cortex.openurl('sqlite:///%s' % (path,)) as core:
                self.false(core.isnew)

    def test_cortex_getbytag(self):

        with self.getRamCore() as core:

            node0 = core.formTufoByProp('inet:user', 'visi')
            node1 = core.formTufoByProp('inet:ipv4', 0x01020304)

            core.addTufoTag(node0, 'foo')
            core.addTufoTag(node1, 'foo')

            self.eq(len(core.getTufosByTag('foo')), 2)
            self.eq(len(core.getTufosByTag('foo', form='inet:user')), 1)
            self.eq(len(core.getTufosByTag('foo', form='inet:ipv4')), 1)

    def test_cortex_tag_ival(self):

        splices = []
        def append(mesg):
            splices.append(mesg[1].get('mesg'))

        with self.getRamCore() as core:

            core.on('splice', append)

            node = core.eval('[ inet:ipv4=1.2.3.4 +#foo.bar@20171217 ]')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), (1513468800000, 1513468800000))

            node = core.eval('[ inet:ipv4=1.2.3.4 +#foo.bar@2018 ]')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), (1513468800000, 1514764800000))

            node = core.eval('[ inet:ipv4=1.2.3.4 +#foo.bar@2011-2018 ]')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), (1293840000000, 1514764800000))

            node = core.eval('[ inet:ipv4=1.2.3.4 +#foo.bar@2012 ]')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), (1293840000000, 1514764800000))

            node = core.eval('[ inet:ipv4=1.2.3.4 +#foo.bar@2012-2013 ]')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), (1293840000000, 1514764800000))

        with self.getRamCore() as core:
            core.splices(splices)
            core.on('splice', append)
            node = core.eval('inet:ipv4=1.2.3.4')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), (1293840000000, 1514764800000))
            core.eval('inet:ipv4=1.2.3.4 [ -#foo.bar ]')

        with self.getRamCore() as core:
            core.splices(splices)
            node = core.eval('inet:ipv4=1.2.3.4')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), None)

    def test_cortex_module_datamodel_migration(self):
        self.skipTest('Needs global model registry available')
        with self.getRamCore() as core:

            # Enforce data model consistency.
            core.setConfOpt('enforce', 1)

            mods = (('synapse.tests.test_cortex.CoreTestDataModelModuleV0', {}),)
            core.setConfOpt('modules', mods)

            self.eq(core.getModlVers('test'), 0)
            self.nn(core.getTypeInst('foo:bar'))

            node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
            self.eq(node[1].get('tufo:form'), 'foo:bar')
            self.gt(node[1].get('node:created'), 1483228800000)
            self.eq(node[1].get('foo:bar'), 'I am a bar foo.')
            self.none(node[1].get('foo:bar:duck'))

            # Test a module which will bump the module version and do a
            # migration as well as add a property type.
            mods = (('synapse.tests.test_cortex.CoreTestDataModelModuleV1', {}),)
            core.setConfOpt('modules', mods)

            self.eq(core.getModlVers('test'), 201707210101)

            node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
            self.eq(node[1].get('foo:bar:duck'), 'mallard')

            node = core.formTufoByProp('foo:bar', 'I am a robot', duck='mandarin')
            self.eq(node[1].get('foo:bar:duck'), 'mandarin')

    def test_cortex_splice_propdel(self):

        with self.getRamCore() as core:
            tufo = core.formTufoByProp('strform', 'haha', foo='bar', bar='faz')
            splice = ('node:prop:del', {'form': 'strform', 'valu': 'haha', 'prop': 'foo'})
            core.splice(splice)

            self.eq(len(core.eval('strform:foo')), 0)
            self.eq(len(core.eval('strform:bar')), 1)

    def test_cortex_module_datamodel_migration_persistent(self):

        # Show that while the data model itself is not persistent, we can run modelrev
        # functions to modify the DB (present in CoreTestDataModelModuleV1) when we have
        # a model change which may affect persistent data.

        with self.getTestDir() as dirn:

            # Test with a safefile based ram cortex
            savefile = os.path.join(dirn, 'savefile.mpk')

            with s_cortex.openurl('ram://', savefile=savefile) as core:
                # Enforce data model consistency.
                core.setConfOpt('enforce', 1)

                mods = (('synapse.tests.test_cortex.CoreTestDataModelModuleV0', {}),)
                core.setConfOpt('modules', mods)

                self.eq(core.getModlVers('test'), 0)
                self.nn(core.getTypeInst('foo:bar'))

                node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
                self.eq(node[1].get('tufo:form'), 'foo:bar')
                self.gt(node[1].get('node:created'), 1483228800000)
                self.eq(node[1].get('foo:bar'), 'I am a bar foo.')
                self.none(node[1].get('foo:bar:duck'))

            with s_cortex.openurl('ram://', savefile=savefile) as core:
                self.eq(core.getModlVers('test'), 0)
                # We are unable to form a node with the custom type with enforce enabled
                self.raises(NoSuchForm, core.formTufoByProp, 'foo:bar', 'I am a bar foo.')
                # But if we disable we can get the node which exists in the cortex
                core.setConfOpt('enforce', 0)
                node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
                self.false(node[1].get('.new'))
                # Re-enable type enforcement
                core.setConfOpt('enforce', 1)

                # Show the model is not yet present
                self.none(core.getTypeInst('foo:bar'))
                mods = (('synapse.tests.test_cortex.CoreTestDataModelModuleV1', {}),)
                core.setConfOpt('modules', mods)
                # Show the model is now loaded
                self.nn(core.getTypeInst('foo:bar'))

                self.eq(core.getModlVers('test'), 201707210101)
                self.true('foo:bar:duck' in core.props)

                node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
                self.eq(node[1].get('foo:bar:duck'), 'mallard')
                node2 = core.formTufoByProp('foo:bar', 'I am a robot', duck='mandarin')
                self.eq(node2[1].get('foo:bar:duck'), 'mandarin')

            # Test with a SQLite backed cortex
            path = os.path.join(dirn, 'testmodelmigration.db')

            with s_cortex.openurl('sqlite:///%s' % (path,)) as core:
                # Enforce data model consistency.
                core.setConfOpt('enforce', 1)

                mods = (('synapse.tests.test_cortex.CoreTestDataModelModuleV0', {}),)
                core.setConfOpt('modules', mods)

                self.eq(core.getModlVers('test'), 0)
                self.nn(core.getTypeInst('foo:bar'))

                node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
                self.eq(node[1].get('tufo:form'), 'foo:bar')
                self.gt(node[1].get('node:created'), 1483228800000)
                self.eq(node[1].get('foo:bar'), 'I am a bar foo.')
                self.none(node[1].get('foo:bar:duck'))

            with s_cortex.openurl('sqlite:///%s' % (path,)) as core:
                self.eq(core.getModlVers('test'), 0)
                # We are unable to form a node with the custom type with enforce enabled
                self.raises(NoSuchForm, core.formTufoByProp, 'foo:bar', 'I am a bar foo.')
                # But if we disable we can get the node which exists in the cortex
                core.setConfOpt('enforce', 0)
                node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
                self.false(node[1].get('.new'))
                # Re-enable type enforcement
                core.setConfOpt('enforce', 1)

                # Show the model is not yet present
                self.none(core.getTypeInst('foo:bar'))
                mods = (('synapse.tests.test_cortex.CoreTestDataModelModuleV1', {}),)
                core.setConfOpt('modules', mods)
                # Show the model is now loaded
                self.nn(core.getTypeInst('foo:bar'))

                self.eq(core.getModlVers('test'), 201707210101)
                self.true('foo:bar:duck' in core.props)

                node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
                self.eq(node[1].get('foo:bar:duck'), 'mallard')
                node2 = core.formTufoByProp('foo:bar', 'I am a robot', duck='mandarin')
                self.eq(node2[1].get('foo:bar:duck'), 'mandarin')

    def test_cortex_lift_by_cidr(self):

        with self.getRamCore() as core:
            # Add a bunch of nodes
            for n in range(0, 256):
                r = core.formTufoByProp('inet:ipv4', '192.168.1.{}'.format(n))
                r = core.formTufoByProp('inet:ipv4', '192.168.2.{}'.format(n))
                r = core.formTufoByProp('inet:ipv4', '192.168.200.{}'.format(n))

            # Confirm we have nodes
            self.eq(len(core.eval('inet:ipv4="192.168.1.0"')), 1)
            self.eq(len(core.eval('inet:ipv4="192.168.1.255"')), 1)
            self.eq(len(core.eval('inet:ipv4="192.168.2.0"')), 1)
            self.eq(len(core.eval('inet:ipv4="192.168.2.255"')), 1)
            self.eq(len(core.eval('inet:ipv4="192.168.200.0"')), 1)

            # Do cidr lifts
            nodes = core.eval('inet:ipv4*inet:cidr=192.168.2.0/24')
            nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
            self.eq(len(nodes), 256)
            test_repr = core.getTypeRepr('inet:ipv4', nodes[10][1].get('inet:ipv4'))
            self.eq(test_repr, '192.168.2.10')
            test_repr = core.getTypeRepr('inet:ipv4', nodes[0][1].get('inet:ipv4'))
            self.eq(test_repr, '192.168.2.0')
            test_repr = core.getTypeRepr('inet:ipv4', nodes[-1][1].get('inet:ipv4'))
            self.eq(test_repr, '192.168.2.255')

            nodes = core.eval('inet:ipv4*inet:cidr=192.168.200.0/24')
            self.eq(len(nodes), 256)
            test_repr = core.getTypeRepr('inet:ipv4', nodes[10][1].get('inet:ipv4'))
            self.true(test_repr.startswith('192.168.200.'))

            nodes = core.eval('inet:ipv4*inet:cidr=192.168.1.0/24')
            self.eq(len(nodes), 256)
            nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
            test_repr = core.getTypeRepr('inet:ipv4', nodes[10][1].get('inet:ipv4'))
            self.eq(test_repr, '192.168.1.10')

            # Try a complicated /24
            nodes = core.eval('inet:ipv4*inet:cidr=192.168.1.1/24')
            self.eq(len(nodes), 256)
            nodes.sort(key=lambda x: x[1].get('inet:ipv4'))

            test_repr = core.getTypeRepr('inet:ipv4', nodes[0][1].get('inet:ipv4'))
            self.eq(test_repr, '192.168.1.0')
            test_repr = core.getTypeRepr('inet:ipv4', nodes[255][1].get('inet:ipv4'))
            self.eq(test_repr, '192.168.1.255')

            # Try a /23
            nodes = core.eval('inet:ipv4*inet:cidr=192.168.0.0/23')
            self.eq(len(nodes), 256)
            test_repr = core.getTypeRepr('inet:ipv4', nodes[10][1].get('inet:ipv4'))
            self.true(test_repr.startswith('192.168.1.'))

            # Try a /25
            nodes = core.eval('inet:ipv4*inet:cidr=192.168.1.0/25')
            nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
            self.eq(len(nodes), 128)
            test_repr = core.getTypeRepr('inet:ipv4', nodes[-1][1].get('inet:ipv4'))
            self.true(test_repr.startswith('192.168.1.127'))

            # Try a /25
            nodes = core.eval('inet:ipv4*inet:cidr=192.168.1.128/25')
            nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
            self.eq(len(nodes), 128)
            test_repr = core.getTypeRepr('inet:ipv4', nodes[0][1].get('inet:ipv4'))
            self.true(test_repr.startswith('192.168.1.128'))

            # Try a /16
            nodes = core.eval('inet:ipv4*inet:cidr=192.168.0.0/16')
            self.eq(len(nodes), 256 * 3)

    def test_cortex_formtufosbyprops(self):

        with self.getRamCore() as core:
            with s_daemon.Daemon() as dmon:
                dmon.share('core', core)
                link = dmon.listen('tcp://127.0.0.1:0/core')
                with s_cortex.openurl('tcp://127.0.0.1:%d/core' % link[1]['port']) as prox:
                    items = (
                        ('inet:fqdn', 'vertex.link', {'zone': 1}),
                        ('inet:url', 'bad', {}),
                        ('bad', 'good', {'wat': 3}),
                    )
                    actual = prox.formTufosByProps(items)

                    self.isinstance(actual, tuple)
                    self.eq(len(actual), 3)

                    self.isinstance(actual[0], tuple)
                    self.eq(len(actual[0]), 2)
                    self.eq(actual[0][1]['tufo:form'], 'inet:fqdn')
                    self.gt(actual[0][1]['node:created'], 1483228800000)
                    self.eq(actual[0][1]['inet:fqdn'], 'vertex.link')
                    self.eq(actual[0][1]['inet:fqdn:zone'], 1)

                    self.isinstance(actual[1], tuple)
                    self.eq(actual[1][0], None)
                    self.eq(actual[1][1]['tufo:form'], 'syn:err')
                    # NOTE: ephemeral data does not get node:created
                    self.eq(actual[1][1]['syn:err'], 'BadTypeValu')
                    for s in ['BadTypeValu', 'name=', 'inet:url', 'valu=', 'bad']:
                        self.isin(s, actual[1][1]['syn:err:errmsg'])

                    self.isinstance(actual[2], tuple)
                    self.eq(actual[2][0], None)
                    self.eq(actual[2][1]['tufo:form'], 'syn:err')
                    # NOTE: ephemeral data does not get node:created
                    self.eq(actual[2][1]['syn:err'], 'NoSuchForm')
                    for s in ['NoSuchForm', 'name=', 'bad']:
                        self.isin(s, actual[2][1]['syn:err:errmsg'])

    def test_cortex_reqprops(self):

        with self.getRamCore() as core:
            core.setConfOpt('enforce', 0)
            core.addDataModel('woot', {
                'forms': (
                    ('hehe:haha', {'ptype': 'str'}, (
                        ('hoho', {'ptype': 'str', 'req': 1}),
                    )),
                ),
            })

            core.setConfOpt('enforce', 0)

            # Required prop not provided but enforce=0.
            t0 = core.formTufoByProp('hehe:haha', 'lulz')
            self.nn(t0)

            # enable enforce
            core.setConfOpt('enforce', 1)

            # fails without required prop present
            self.raises(PropNotFound, core.formTufoByProp, 'hehe:haha', 'rofl')

            # Works with required prop present
            t0 = core.formTufoByProp('hehe:haha', 'rofl', hoho='wonk')
            self.nn(t0)

    def test_cortex_runts(self):

        with self.getRamCore() as core:

            core.addDataModel('hehe', {'forms': (
                ('hehe:haha', {'ptype': 'str'}, (
                    ('hoho', {'ptype': 'int'}),
                )),
            )})

            core.addRuntNode('hehe:haha', 'woot', props={'hoho': 20, 'lulz': 'rofl'})

            # test that nothing hit the storage layer...
            self.eq(len(core.getRowsByProp('hehe:haha')), 0)

            node = core.getTufoByProp('hehe:haha', 'woot')
            self.nn(node)

            # check that it is ephemeral
            self.none(node[0])

            # check that all props made it in
            self.eq(node[1].get('hehe:haha:hoho'), 20)
            self.eq(node[1].get('hehe:haha:lulz'), 'rofl')

            # check that only model'd props are indexed
            self.nn(core.getTufoByProp('hehe:haha:hoho', 20))
            self.none(core.getTufoByProp('hehe:haha:lulz', 'rofl'))

            node = core.addRuntNode('hehe:haha', 'ohmy')
            self.eq(node[1].get('hehe:haha:hoho'), None)

    def test_cortex_trigger(self):

        with self.getRamCore() as core:

            node = core.formTufoByProp('syn:trigger', '*', on='node:add form=inet:fqdn', run='[ #foo ]', en=1)
            self.eq(node[1].get('syn:trigger:on'), 'node:add form=inet:fqdn')
            self.eq(node[1].get('syn:trigger:run'), '[ #foo ]')

            node = core.formTufoByProp('syn:trigger', '*', on='node:tag:add form=inet:fqdn tag=foo', run='[ #baz ]', en=1)

            node = core.formTufoByProp('inet:fqdn', 'vertex.link')

            self.nn(node[1].get('#foo'))
            self.nn(node[1].get('#baz'))

    def test_cortex_auth(self):

        with self.getRamCore() as core:

            core.formTufoByProp('syn:auth:user', 'visi@vertex.link')
            core.formTufoByProp('syn:auth:user', 'fred@woot.com')
            core.formTufoByProp('syn:auth:user', 'root@localhost')

            core.formTufoByProp('syn:auth:role', 'root')
            core.formTufoByProp('syn:auth:role', 'newb')

            rule = (True, ('*', {}))
            core.addRoleRule('root', rule)
            core.addUserRule('root@localhost', rule)
            core.addUserRule('root@localhost', (True, ('rm:me', {})))

            self.nn(core.getRoleAuth('root'))
            self.nn(core.getUserAuth('root@localhost'))

            self.raises(NoSuchUser, core.getUserAuth, 'newp')
            self.raises(NoSuchRole, core.getRoleAuth, 'newp')

            self.eq(len(core.getUserRules('root@localhost')), 2)

            core.delUserRule('root@localhost', 1)
            self.eq(len(core.getUserRules('root@localhost')), 1)

            rule = (True, ('node:add', {'form': 'inet:*'}))

            core.addRoleRule('newb', rule)
            self.eq(len(core.getRoleRules('newb')), 1)

            core.delRoleRule('newb', 0)
            self.eq(len(core.getRoleRules('newb')), 0)

            core.setRoleRules('newb', ())
            self.eq(len(core.getRoleRules('newb')), 0)

            # test the short circuit before auth is enabled
            core.reqperm(('node:add', {'form': 'inet:fqdn'}), user='newp')
            self.true(core.allowed(('node:add', {'form': 'inet:fqdn'}), user='newp'))

            core.setConfOpt('auth:en', 1)

            self.raises(NoSuchUser, core.addUserRule, 'hehe', ('stuff', {}))
            self.raises(NoSuchRole, core.addRoleRule, 'hehe', ('stuff', {}))

            with s_auth.runas('fred@woot.com'):

                self.false(core.allowed(('node:add', {'form': 'ou:org'})))

                rule = (True, ('node:add', {'form': 'ou:org'}))
                core.addUserRule('fred@woot.com', rule)

                perm = ('node:add', {'form': 'ou:org'})
                core.reqperm(perm)
                self.true(core.allowed(perm))
                self.eq(len(core.getUserRules('fred@woot.com')), 1)

                core.setUserRules('fred@woot.com', ())
                self.eq(len(core.getUserRules('fred@woot.com')), 0)

                perm = ('node:add', {'form': 'ou:org'})
                self.false(core.allowed(perm))
                self.raises(AuthDeny, core.reqperm, perm)

            with s_auth.runas('root@localhost'):
                self.true(core.allowed(('fake', {})))

            with s_auth.runas('visi@vertex.link'):

                self.false(core.allowed(('fake', {})))

                node = core.formTufoByProp('syn:auth:userrole', ('visi@vertex.link', 'root'))
                self.true(core.allowed(('fake', {})))

                core.delTufo(core.getTufoByProp('syn:auth:role', 'root'))
                self.false(core.allowed(('fake', {})))

            core.delTufo(core.getTufoByProp('syn:auth:user', 'fred@woot.com'))

            self.raises(NoSuchUser, core.addUserRule, 'fred@woot.com', ('stuff', {}))
            self.raises(NoSuchRole, core.addRoleRule, 'root', ('stuff', {}))

    def test_cortex_formtufobytufo(self):
        with self.getRamCore() as core:
            _t0iden = guid()
            _t0 = (_t0iden, {'tufo:form': 'inet:ipv4', 'inet:ipv4': '1.2.3.4', 'inet:ipv4:asn': 1024})
            t0 = core.formTufoByTufo(_t0)
            form, valu = s_tufo.ndef(t0)
            self.eq(form, 'inet:ipv4')
            self.eq(valu, 0x01020304)
            self.eq(t0[1].get('inet:ipv4:asn'), 1024)
            self.eq(t0[1].get('inet:ipv4:cc'), '??')
            self.ne(t0[0], _t0iden)

            t1 = core.formTufoByTufo((None, {'tufo:form': 'strform', 'strform': 'oh hai',
                                             'strform:haha': 1234, 'strform:foo': 'sup'}))

            form, valu = s_tufo.ndef(t1)
            self.gt(t1[1]['node:created'], 1483228800000)
            self.eq(form, 'strform')
            self.eq(valu, 'oh hai')
            self.eq(t1[1].get('strform:foo'), 'sup')
            self.none(t1[1].get('strform:bar'))
            self.none(t1[1].get('strform:baz'))
            self.none(t1[1].get('strform:haha'))

    def test_cortex_fifos_busref(self):
        with self.getTestDir() as dirn:

            url = 'dir:///' + dirn
            with s_cortex.openurl(url) as core:
                node = core.formTufoByProp('syn:fifo', '(haHA)', desc='test fifo')
                name = node[1].get('syn:fifo:name')

                # refcount is set to 1 when the fifo is created (when the syn:fifo node is formed),
                #   then incremented when getCoreFifo is called
                fiforef_0 = core.getCoreFifo(name)
                self.eq(2, fiforef_0._syn_refs)

                # Add 3 more refs
                fiforef_1 = core.getCoreFifo(name)
                fiforef_2 = core.getCoreFifo(name)
                fiforef_3 = core.getCoreFifo(name)
                self.eq(5, fiforef_0._syn_refs)

                # Begin to remove them
                fiforef_3.fini()
                self.eq(4, fiforef_0._syn_refs)
                fiforef_2.fini()
                self.eq(3, fiforef_0._syn_refs)
                fiforef_1.fini()
                self.eq(2, fiforef_0._syn_refs)

            # refs are finied, but the fifo is not finid because not all of the refs were closed yet
            self.false(fiforef_0.isfini)
            fiforef_1.fini()
            self.true(fiforef_0.isfini)
            self.eq(0, fiforef_0._syn_refs)

    def test_cortex_fifos(self):

        with self.getTestDir() as dirn:

            url = 'dir:///' + dirn
            with s_cortex.openurl(url) as core:

                self.raises(NoSuchFifo, core.getCoreFifo, '(haha)')

                node = core.formTufoByProp('syn:fifo', '(haHA)', desc='test fifo')
                iden = node[1].get('syn:fifo')
                name = node[1].get('syn:fifo:name')
                desc = node[1].get('syn:fifo:desc')

                self.eq(iden, 'adb4864c8e5f2a2a44b454981e731b8b')
                self.eq(name, 'haha')
                self.eq(desc, 'test fifo')

                # Assert that the fifo dir was created by simply forming the syn:fifo node
                path = core.getCorePath('fifos', iden)
                self.true(os.path.isdir(path))

                self.raises(NoSuchFifo, core.getCoreFifo, 'shouldntexist')

                sent = []
                core.subCoreFifo(name, sent.append)

                core.putCoreFifo(name, 'foo')
                core.putCoreFifo(name, 'bar')

                self.len(2, sent)
                self.eq(sent[0][2], 'foo')
                self.eq(sent[1][2], 'bar')

                core.ackCoreFifo(name, sent[0][0])

                sent = []
                core.subCoreFifo(name, sent.append)
                self.len(1, sent)
                self.eq(sent[0][2], 'bar')

                with s_daemon.Daemon() as dmon:

                    link = dmon.listen('tcp://127.0.0.1:0/')
                    dmon.share('core', core)

                    port = link[1].get('port')
                    prox = s_telepath.openurl('tcp://127.0.0.1/core', port=port)

                    data = []
                    def fifoxmit(mesg):
                        data.append(mesg)
                        name = mesg[1].get('name')
                        seqn = mesg[1].get('qent')[0]
                        prox.fire('fifo:ack', seqn=seqn, name=name)

                    prox.on('fifo:xmit', fifoxmit, name='haha')

                    wait = prox.waiter(1, 'fifo:xmit')
                    prox.subCoreFifo('haha')

                    self.nn(wait.wait(timeout=1))

                    self.len(1, data)

                    wait = prox.waiter(2, 'fifo:xmit')
                    ackwait = core.waiter(2, 'fifo:ack')

                    core.extCoreFifo('haha', ('lulz', 'rofl'))

                    self.nn(wait.wait(timeout=1))
                    self.nn(ackwait.wait(timeout=1))

                    self.len(3, data)

                    waiter = prox.waiter(1, 'tele:sock:init')
                    subwait = core.waiter(1, 'fifo:sub')

                    prox._tele_sock.fini()

                    self.nn(waiter.wait(timeout=1))
                    self.nn(subwait.wait(timeout=1))

                    waiter = prox.waiter(1, 'fifo:xmit')
                    core.putCoreFifo('haha', 'zonk')
                    self.nn(waiter.wait(timeout=1))

                    self.len(4, data)

                core.delTufo(node)

                self.false(os.path.isdir(path))
                self.raises(NoSuchFifo, core.getCoreFifo, 'haha')

    def test_cortex_fifos_fifodir(self):

        def run_tests(node):
            self.eq(node[1].get('syn:fifo'), 'adb4864c8e5f2a2a44b454981e731b8b')
            self.eq(node[1].get('syn:fifo:name'), 'haha')
            self.eq(node[1].get('syn:fifo:desc'), 'test fifo')
            path = core.getCorePath('fifos', 'adb4864c8e5f2a2a44b454981e731b8b')
            self.true(os.path.isdir(path))

        with self.getTestDir() as dirn:
            url = 'dir:///' + dirn

            # create the fifo and put a message into it, close the cortex
            with s_cortex.openurl(url) as core:
                core.formTufoByProp('syn:fifo', '(FoO)')
                core.formTufoByProp('syn:fifo', '(bAr)')
                core.formTufoByProp('syn:fifo', '(BAz)')
                node = core.formTufoByProp('syn:fifo', '(haHA)', desc='test fifo')
                run_tests(node)

                core.getCoreFifo('haha')
                core.getCoreFifo('haha')
                fifo = core.getCoreFifo('haha')
                self.eq(4, fifo._syn_refs)

                core.putCoreFifo('haha', 'mymesg')

            # make sure that the fifo still exists and is reloaded after the cortex was closed and reopened
            with s_cortex.openurl(url) as core:
                node = core.getTufoByProp('syn:fifo', '(haHA)')  # make sure that it is still there
                run_tests(node)

            # make sure that the fifo still works correctly after the cortex was closed and reopened
            with s_cortex.openurl(url) as core:
                fifo = core.getCoreFifo('haha')
                self.eq(2, fifo._syn_refs)  # make sure that the old refs were cleaned up

                actual = []
                core.subCoreFifo('haha', actual.append)  # messages should persist
                self.eq(2, fifo._syn_refs)  # calling subCoreFifo shouldn't incr refs

                self.len(1, actual)
                self.len(3, actual[0])
                self.eq(actual[0][2], 'mymesg')  # make sure the original message survived

                core.delTufo(node)

            # make sure that the fifo is really removed after its node is removed
            with s_cortex.openurl(url) as core:
                self.raises(NoSuchFifo, core.getCoreFifo, 'haha')
                path = core.getCorePath('fifos', 'adb4864c8e5f2a2a44b454981e731b8b')
                self.false(os.path.isdir(path))

    def test_cortex_universal_props(self):
        with self.getRamCore() as core:
            myfo = core.myfo

            node = core.getTufoByProp('node:ndef', '90ec8b92deda626d31e2d63e8dbf48be')
            self.eq(node[0], myfo[0])

            node = core.getTufoByProp('tufo:form', 'syn:core')
            self.eq(node[0], myfo[0])

            nodes = core.getTufosByProp('node:created', myfo[1].get('node:created'))
            self.ge(len(nodes), 1)
            rvalu = core.getPropRepr('node:created', myfo[1].get('node:created'))
            self.isinstance(rvalu, str)
            nodes2 = core.getTufosByProp('node:created', rvalu)
            self.eq(len(nodes), len(nodes2))

            # We can have a data model which has a prop which is a ndef type
            modl = {
                'types': (
                    ('ndefxref', {'subof': 'comp', 'fields': 'ndef,node:ndef|strdude,strform|time,time'}),
                ),
                'forms': (
                    ('ndefxref', {}, (
                        ('ndef', {'req': 1, 'ro': 1, 'doc': 'ndef to a node', 'ptype': 'ndef'}),
                        ('strdude', {'req': 1, 'ro': 1, 'doc': 'strform thing', 'ptype': 'strform'}),
                        ('time', {'req': 1, 'ro': 1, 'doc': 'time thing was seen', 'ptype': 'time'})
                    )),
                )
            }
            core.addDataModel('unitst', modl)

            # Make an node which refers to another node by its node:ndef value
            node = core.formTufoByProp('ndefxref', '(90ec8b92deda626d31e2d63e8dbf48be,"hehe","2017")')
            self.nn(node)
            self.isin('.new', node[1])

            # We can also provide values which will be prop-normed by the NDefType
            # This means we can create arbitrary linkages which may eventually exist
            nnode = core.formTufoByProp('ndefxref', '((syn:core,self),"hehe","2017")')
            self.notin('.new', nnode[1])
            self.eq(node[0], nnode[0])
            self.nn(core.getTufoByProp('strform', 'hehe'))

            # Use storm to pivot across this node to the ndef node
            nodes = core.eval('ndefxref :ndef->node:ndef')
            self.len(1, nodes)
            self.eq(nodes[0][0], myfo[0])

            # Use storm to pivot from the ndef node to the ndefxref node
            nodes = core.eval('syn:core=self node:ndef->ndefxref:ndef')
            self.len(1, nodes)
            self.eq(nodes[0][0], node[0])

            # Lift nodes by node:created text timestamp
            nodes = core.eval('node:created>={}'.format(rvalu))
            self.ge(len(nodes), 3)

            # We can add a new universal prop via API
            nprop = core.addPropDef('node:tstfact',
                                    ro=1,
                                    univ=1,
                                    ptype='str:lwr',
                                    doc='A fact about a node.',
                                    )
            self.isinstance(nprop, tuple)
            self.isin('node:tstfact', core.getUnivProps())
            self.notin('node:tstfact', core.unipropsreq)
            self.nn(core.getPropDef('node:tstfact'))

            node = core.formTufoByProp('inet:ipv4', 0x01020304)
            self.nn(node)
            self.notin('node:tstfact', node[1])
            # Set the non-required prop via setTufoProps()
            node = core.setTufoProps(node, **{'node:tstfact': ' THIS node is blue.  '})
            self.eq(node[1].get('node:tstfact'), 'this node is blue.')

            # The uniprop is ro and cannot be changed once set
            node = core.setTufoProps(node, **{'node:tstfact': 'hehe'})
            self.eq(node[1].get('node:tstfact'), 'this node is blue.')

            # We can have a mutable, non ro universal prop on a node though!
            nprop = core.addPropDef('node:tstopinion',
                                    univ=1,
                                    ptype='str:lwr',
                                    doc='A opinion about a node.',
                                    )
            node = core.setTufoProps(node, **{'node:tstopinion': ' THIS node is good Ash.  '})
            self.eq(node[1].get('node:tstopinion'), 'this node is good ash.')

            # We can change the prop of the uniprop on this node.
            node = core.setTufoProps(node, **{'node:tstopinion': 'this node is BAD ash.'})
            self.eq(node[1].get('node:tstopinion'), 'this node is bad ash.')

            # Lastly - we can add a universal prop which is required but breaks node creation
            # Do NOT do this in the real world - its a bad idea.
            nprop = core.addPropDef('node:tstevil',
                                    univ=1,
                                    req=1,
                                    ptype='bool',
                                    doc='No more nodes!',
                                    )
            self.nn(nprop)
            self.raises(PropNotFound, core.formTufoByProp, 'inet:ipv4', 0x01020305)
            # We can add a node:add handler to populate this new universal prop though!
            def foo(mesg):
                fulls = mesg[1].get('props')
                fulls['node:tstevil'] = 1
            core.on('node:form', foo)
            # We can form nodes again, but they're all evil.
            node = core.formTufoByProp('inet:ipv4', 0x01020305)
            self.nn(node)
            self.eq(node[1].get('node:tstevil'), 1)
            core.off('node:form', foo)

            # We cannot add a universal prop which is associated with a form
            self.raises(BadPropConf, core.addPropDef, 'node:poorform', univ=1, req=1, ptype='bool', form='file:bytes')

    def test_cortex_gettasks(self):
        with self.getRamCore() as core:

            def f1(mesg):
                pass

            def f2(mesg):
                pass

            core.on('task:hehe:haha', f1)
            core.on('task:hehe:haha', f2)
            core.on('task:wow', f1)

            tasks = core.getCoreTasks()
            self.len(2, tasks)
            self.isin('hehe:haha', tasks)
            self.isin('wow', tasks)

    def test_cortex_dynalias(self):
        conf = {
            'ctors': [
                [
                    'core',
                    'syn:cortex',
                    {
                        'url': 'ram:///',
                        'storm:query:log:en': 1,
                        'modules': [
                            [
                                'synapse.tests.test_cortex.CoreTestModule',
                                {'foobar': True}
                            ]
                        ]
                    }
                ]
            ],
            'share': [
                [
                    'core',
                    {}
                ]
            ],
            'listen': [
                'tcp://0.0.0.0:0/'
            ]
        }

        with s_daemon.Daemon() as dmon:
            dmon.loadDmonConf(conf)
            link = dmon.links()[0]
            port = link[1].get('port')
            with s_cortex.openurl('tcp://0.0.0.0/core', port=port) as prox:
                self.isin('synapse.tests.test_cortex.CoreTestModule', prox.getCoreMods())
                self.eq(prox.getConfOpt('storm:query:log:en'), 1)

    def test_cortex_axon(self):
        self.skipLongTest()

        visihash = hashlib.sha256(b'visi').digest()
        craphash = hashlib.sha256(b'crap').digest()
        foobarhash = hashlib.sha256(b'foobar').digest()

        with self.getAxonCore() as env:
            env.core.setConfOpt('cellpool:timeout', 3)

            core = s_telepath.openurl(env.core_url)
            env.add('_core_prox', core, fini=True)  # ensure the Proxy object is fini'd

            wants = core._axonclient_wants([visihash, craphash, foobarhash])
            self.len(3, wants)
            self.istufo(core.formNodeByBytes(b'visi'))
            with io.BytesIO(b'foobar') as fd:
                self.istufo(core.formNodeByFd(fd))
            wants = core._axonclient_wants([visihash, craphash, foobarhash])
            self.len(1, wants)

            # Pull out the axon config an shut it down
            axonpath = os.path.split(env.axon.getCellPath())[0]
            axonconf = env.axon.getConfOpts()
            env.axon.fini()
            env.axon.waitfini(timeout=30)

            # Make sure that it doesn't work
            self.raises(Exception, core._axonclient_wants, [visihash, craphash, foobarhash], timeout=2)
            # Turn the axon back on
            w = env.core.cellpool.waiter(1, 'cell:add')
            axon = s_axon.AxonCell(axonpath, axonconf)
            env.add('axon', axon, fini=True)
            self.true(axon.cellpool.neurwait(timeout=3))
            # Make sure the api still works.
            self.nn(w.wait(4))
            wants = core._axonclient_wants([visihash, craphash, foobarhash])

            self.len(1, wants)

            neurhost, neurport = env.neuron.getCellAddr()
            axonauth = env.axon.getCellAuth()
            axonauth = enbase64(s_msgpack.en(axonauth))
            # Ensure that Axon fns do not execute on a core without an axon
            with self.getRamCore() as othercore:
                othercore.setConfOpt('cellpool:timeout', 3)
                self.raises(NoSuchOpt, othercore.formNodeByBytes, b'visi', name='visi.bin')
                with io.BytesIO(b'foobar') as fd:
                    self.raises(NoSuchOpt, othercore.formNodeByFd, fd, name='foobar.exe')

                othercore.setConfOpt('cellpool:conf', {'fake': 'fake'})
                self.false(othercore.axon_ready)
                self.false(othercore.cellpool_ready)
                othercore.setConfOpt('cellpool:conf', {'auth': axonauth})
                self.false(othercore.axon_ready)
                self.false(othercore.cellpool_ready)
                othercore.setConfOpt('cellpool:conf', {'auth': axonauth, 'host': neurhost})
                self.false(othercore.cellpool_ready)
                self.false(othercore.axon_ready)

                othercore.setConfOpt('cellpool:conf', {'auth': axonauth, 'host': neurhost, 'port': neurport + 1})
                self.false(othercore.cellpool_ready)
                self.false(othercore.axon_ready)

                othercore.setConfOpt('cellpool:conf', {'auth': axonauth, 'host': neurhost, 'port': neurport})
                self.true(othercore.cellpool_ready)
                self.false(othercore.axon_ready)

                othercore.setConfOpt('axon:name', 'axon@localhost')
                self.true(othercore.axon_ready)

                wants = othercore._axonclient_wants([visihash, craphash, foobarhash])
                self.len(1, wants)
                self.istufo(othercore.formNodeByBytes(b'crap'))
                wants = othercore._axonclient_wants([visihash, craphash, foobarhash])
                self.len(0, wants)

            # ensure that we can configure a cellpool/axon via conf options
            conf = {
                'cellpool:conf': {'auth': axonauth, 'host': neurhost, 'port': neurport},
                'axon:name': 'axon@localhost',
                'cellpool:timeout': 6,
            }
            with s_cortex.openurl('ram://', conf) as rcore:
                wants = rcore._axonclient_wants([visihash, craphash, foobarhash])
                self.len(0, wants)

    def test_cortex_splice_examples(self):

        with self.getRamCore() as core:

            node_add_splice = ('node:add', {
                    'form': 'inet:fqdn',
                    'valu': 'vertex.link',
                    'tags': ['hehe.haha'],
                    'props': {'expires': '2017'},
                })
            node_add_splice_props = ('node:add', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'props': {'expires': '2018'},
            })
            node_add_splice_tags = ('node:add', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'tags': ('foo.bar',
                         'oh.my')
            })
            node_prop_set_splice = ('node:prop:set', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'prop': 'expires',
                'newv': '2019',
            })
            node_prop_del_splice = ('node:prop:del', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'prop': 'expires',
            })
            node_tag_add_splice = ('node:tag:add', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'tag': 'hehe.haha',
            })
            node_tag_add_splice2 = ('node:tag:add', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'tag': 'hehe.woah',
            })
            node_tag_del_splice = ('node:tag:del', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'tag': 'hehe.woah',
            })
            node_tag_del_splice2 = ('node:tag:del', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'tag': 'hehe',
            })
            node_ival_set_splice = ('node:ival:set', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'prop': '#woah',
                'ival': (100, 200)
            })
            node_ival_del_splice = ('node:ival:del', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'prop': '#woah',
            })
            node_del_splice = ('node:del', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
            })

            splices = (node_add_splice,)

            core.splices(splices)
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.nn(node)
            self.nn(node[1].get('#hehe.haha'))
            self.eq(node[1].get('inet:fqdn:expires'), 1483228800000)

            core.splice(node_add_splice_props)
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.eq(node[1].get('inet:fqdn:expires'), 1514764800000)

            core.splice(node_add_splice_tags)
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.true(s_tufo.tagged(node, 'foo.bar'))
            self.true(s_tufo.tagged(node, 'oh.my'))

            core.splices((node_prop_set_splice,))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.eq(node[1].get('inet:fqdn:expires'), 1546300800000)

            core.splices((node_prop_del_splice,))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.none(node[1].get('inet:fqdn:expires'))

            core.splices((node_tag_add_splice, node_tag_add_splice2))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.true(s_tufo.tagged(node, 'hehe'))
            self.true(s_tufo.tagged(node, 'hehe.haha'))
            self.true(s_tufo.tagged(node, 'hehe.woah'))

            core.splices((node_tag_del_splice,))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.true(s_tufo.tagged(node, 'hehe'))
            self.true(s_tufo.tagged(node, 'hehe.haha'))
            self.false(s_tufo.tagged(node, 'hehe.woah'))

            core.splices((node_tag_del_splice2,))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.false(s_tufo.tagged(node, 'hehe'))
            self.false(s_tufo.tagged(node, 'hehe.haha'))
            self.false(s_tufo.tagged(node, 'hehe.woah'))

            core.splices((node_ival_set_splice,))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.eq(node[1].get('<#woah'), 200)
            self.eq(node[1].get('>#woah'), 100)

            core.splices((node_ival_del_splice,))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.none(node[1].get('<#woah'))
            self.none(node[1].get('>#woah'))

            core.splices((node_del_splice,))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.none(node)

            # set / del splices do not make nodes
            events = []
            core.link(events.append)
            splices = (
                node_prop_set_splice,
                node_prop_del_splice,
                node_ival_del_splice,
                node_ival_set_splice,
                node_tag_add_splice,
                node_tag_add_splice2,
                node_tag_del_splice,
                node_tag_del_splice2,
                node_del_splice
            )
            core.splices(splices)
            self.eq(events, [])
            core.unlink(events.append)

class FIXME:

    def test_nonexist_ctor(self):
        self.raises(NoSuchImpl, s_cortex.openstore, 'delaylinememory:///')

    def test_storage_snap_spliced(self):

        # Ensure that spliced events don't get fired through a
        # StoreXct without a Cortex
        eventd = {}

        def foo(event):
            eventd[event[0]] = eventd.get(event[0], 0) + 1

        with s_cortex.openstore('ram:///') as store:
            store.on('foo', foo)
            store.on('splice', foo)
            with store.getCoreXact() as snap:
                snap.fire('foo', key='valu')
                snap.fire('bar', key='valu')
                snap.spliced('foo', key='valu')
        self.eq(eventd, {'foo': 1})

    def test_storage_confopts(self):
        conf = {'rev:storage': 0}

        with s_cortex.openstore('ram:///', storconf=conf) as stor:
            self.eq(stor.getConfOpt('rev:storage'), 0)

    def test_storage_rowmanipulation(self):
        with self.getTestDir() as temp:
            finl = os.path.join(temp, 'test.db')
            url = 'sqlite:///%s' % finl

            with s_cortex.openstore(url) as store:
                self.isinstance(store, s_cores_storage.Storage)
                # Add rows directly to the storage object
                rows = []
                tick = s_common.now()
                rows.append(('1234', 'foo:bar:baz', 'yes', tick))
                rows.append(('1234', 'tufo:form', 'foo:bar', tick))
                rows.append(('1234', 'node:created', 1483228800000, tick))
                store.addRows(rows)

            # Retrieve the node via the Cortex interface
            with s_cortex.openurl(url) as core:
                node = core.getTufoByIden('1234')
                self.nn(node)
                self.eq(node[1].get('tufo:form'), 'foo:bar')
                self.eq(node[1].get('node:created'), 1483228800000)
                self.eq(node[1].get('foo:bar:baz'), 'yes')

    def test_storage_row_manipulation(self):
        # Add rows to an new cortex db
        with self.getTestDir() as temp:
            finl = os.path.join(temp, 'test.db')
            url = 'sqlite:///%s' % finl

            with s_cortex.openstore(url) as store:
                self.isinstance(store, s_cores_storage.Storage)
                # Add rows directly to the storage object
                rows = []
                tick = s_common.now()
                rows.append(('1234', 'foo:bar:baz', 'yes', tick))
                rows.append(('1234', 'tufo:form', 'foo:bar', tick))
                rows.append(('1234', 'node:created', 1483228800000, tick))
                store.addRows(rows)

            # Retrieve the node via the Cortex interface
            with s_cortex.openurl(url) as core:
                node = core.getTufoByIden('1234')
                self.nn(node)
                self.eq(node[1].get('tufo:form'), 'foo:bar')
                self.eq(node[1].get('node:created'), 1483228800000)
                self.eq(node[1].get('foo:bar:baz'), 'yes')

    def test_storage_handler_misses(self):
        with s_cortex.openstore('ram:///') as store:
            self.raises(NoSuchGetBy, store.getJoinsBy, 'clowns', 'inet:ipv4', 0x01020304)
            self.raises(NoSuchGetBy, store.reqJoinByMeth, 'clowns')
            self.raises(NoSuchGetBy, store.reqRowsByMeth, 'clowns')
            self.raises(NoSuchGetBy, store.reqSizeByMeth, 'clowns')

    def test_storage_handler_defaults(self):
        with s_cortex.openstore('ram:///') as store:
            self.nn(store.reqJoinByMeth('range'))
            self.nn(store.reqRowsByMeth('range'))
            self.nn(store.reqSizeByMeth('range'))

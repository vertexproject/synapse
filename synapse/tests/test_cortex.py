import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.common as s_test

class CortexTest(s_test.SynTest):

    def test_onadd(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                func = s_test.CallBack()
                core.model.form('inet:ipv4').onAdd(func)

                node = snap.addNode('inet:ipv4', '1.2.3.4')
                self.eq(node.buid, func.args[0].buid)

    def test_adddata(self):

        data = ('foo', 'bar', 'baz')

        with self.getTestCore() as core:

            core.addFeedData('com.test.record', data)

            vals = []
            for node in core.eval('teststr'):
                vals.append(node.ndef[1])

            vals.sort()

            self.eq(vals, ('bar', 'baz', 'foo'))

    def test_indxchop(self):

        with self.getTestCore() as core:

            with core.snap() as snap:
                valu = 'a' * 257
                snap.addNode('teststr', valu)

                nodes = list(snap.getNodesBy('teststr', 'aa', cmpr='^='))
                self.len(1, nodes)

    def test_cell(self):

        data = ('foo', 'bar', 'baz')

        with self.getTestDmon(mirror='dmoncore') as dmon:

            core = dmon._getTestProxy('core')

            nodes = ((('inet:user', 'visi'), {}), )

            nodes = list(core.addNodes(nodes))
            self.len(1, nodes)

            nodes = list(core.getNodesBy('inet:user', 'visi'))
            self.len(1, nodes)
            self.eq('visi', nodes[0][0][1])

            opts = {'ndefs': [('inet:user', 'visi')]}

            nodes = list(core.eval('', opts=opts))

            self.len(1, nodes)
            self.eq('visi', nodes[0][0][1])

            core.addFeedData('com.test.record', data)

            # test the remote storm result counting API
            self.eq(0, core.count('pivtarg'))
            self.eq(1, core.count('inet:user'))

    def test_stormcmd(self):

        with self.getTestCore() as core:

            msgs = list(core.storm('|help'))
            self.printed(msgs, 'help: List available commands and a brief description for each.')

            msgs = list(core.storm('help'))
            self.printed(msgs, 'help: List available commands and a brief description for each.')

            list(core.eval('[ inet:user=visi inet:user=whippit ]'))

            self.len(2, list(core.eval('inet:user')))

            # test cmd as last text syntax
            self.len(1, list(core.eval('inet:user | limit 1')))

            # test cmd and trailing pipe syntax
            self.len(1, list(core.eval('inet:user | limit 1|')))

            # test cmd and trailing pipe and whitespace syntax
            self.len(1, list(core.eval('inet:user | limit 1    |     ')))

            # test cmd and trailing pipe and whitespace syntax
            self.len(2, list(core.eval('inet:user | limit 10 | [ +#foo.bar ]')))
            self.len(1, list(core.eval('inet:user | limit 10 | +inet:user=visi')))

            # test invalid option sytnax
            msgs = list(core.storm('inet:user | limit --woot'))
            self.printed(msgs, 'usage: limit [-h] count')
            self.len(0, [m for m in msgs if m[0] == 'node'])

    def test_onsetdel(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                func = s_test.CallBack()
                core.model.prop('inet:ipv4:loc').onSet(func)

                node = snap.addNode('inet:ipv4', '1.2.3.4')
                node.set('loc', 'US.  VA')

                self.eq(func.args[0].buid, node.buid)
                self.eq(func.args[1], '??')

                func = s_test.CallBack()
                core.model.prop('inet:ipv4:loc').onDel(func)

                node.pop('loc')

                self.eq(func.args[0].buid, node.buid)
                self.eq(func.args[1], 'us.va')

                self.none(node.get('loc'))

            with core.snap() as snap:
                node = snap.addNode('inet:ipv4', '1.2.3.4')
                self.none(node.get('loc'))

    def test_tags(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

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

            with core.snap() as snap:

                node = snap.addNode('teststr', 'one')

                node.delTag('foo')

                self.false(node.hasTag('foo'))
                self.false(node.hasTag('foo.bar'))

            with core.snap() as snap:

                node = snap.addNode('teststr', 'one')
                self.false(node.hasTag('foo'))
                self.false(node.hasTag('foo.bar'))

    def test_base_types(self):

        with self.getTestCore() as core:

            with core.snap() as snap:
                node = snap.addNode('testtype10', 'one')
                node.set('intprop', 21)

            with core.snap() as snap:
                node = snap.getNodeByNdef(('testtype10', 'one'))
                self.nn(node)
                self.eq(node.get('intprop'), 21)

        with self.getTestCore() as core:

            with core.snap() as snap:

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

                self.raises(s_exc.ReadOnlyProp, node.set, 'hehe', 80)

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

                self.nn(snap.getNodeByNdef(('testauto', 'autothis')))

                # test lifting by prop without value
                nodes = list(snap.getNodesBy('teststr:tick'))
                self.len(3, nodes)

            with core.snap() as snap:

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

    def test_pivprop(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                pivc = snap.addNode('pivcomp', ('woot', 'rofl'))
                self.eq(pivc.get('targ'), 'woot')

                pivt = snap.getNodeByNdef(('pivtarg', 'woot'))
                pivt.set('name', 'visi')
                self.nn(pivt)

            with core.snap() as snap:
                pivc = snap.getNodeByNdef(('pivcomp', ('woot', 'rofl')))
                self.eq(pivc.get('targ::name'), 'visi')

    def test_storm(self):

        with self.getTestCore() as core:

            # test some edit syntax
            for node in core.eval('[ testcomp=(10, haha) +#foo.bar -#foo.bar ]'):
                self.nn(node.getTag('foo'))
                self.none(node.getTag('foo.bar'))

            for node in core.eval('[ teststr="foo bar" :tick=2018]'):
                self.eq(1514764800000, node.get('tick'))
                self.eq('foo bar', node.ndef[1])

            for node in core.eval('teststr="foo bar" [ -:tick ]'):
                self.none(node.get('tick'))

            for node in core.eval('[ pivcomp=(foo,bar) ] -> pivtarg'):
                self.eq(node.ndef[0], 'pivtarg')
                self.eq(node.ndef[1], 'foo')

            for node in core.eval('pivcomp=(foo,bar) :targ -> pivtarg'):
                self.eq(node.ndef[0], 'pivtarg')
                self.eq(node.ndef[1], 'foo')

            nodes = sorted([n.pack() for n in core.eval('pivcomp=(foo,bar) -> pivtarg')])

            self.len(1, nodes)
            self.eq(nodes[0][0], ('pivtarg', 'foo'))

            nodes = sorted([n.pack() for n in core.eval('pivcomp=(foo,bar) -+> pivtarg')])

            self.len(2, nodes)
            self.eq(nodes[0][0], ('pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('pivtarg', 'foo'))

            nodes = [n.pack() for n in core.eval('teststr="foo bar" +teststr')]
            self.len(1, nodes)

            nodes = [n.pack() for n in core.eval('teststr="foo bar" -teststr:tick')]
            self.len(1, nodes)

            qstr = 'teststr="foo bar" +teststr="foo bar" [ :tick=2015 ] +teststr:tick=2015'
            nodes = [n.pack() for n in core.eval(qstr)]
            self.len(1, nodes)

            ndef = ('testcomp', (10, 'haha'))
            opts = {'ndefs': (ndef,)}

            for node in core.eval('[-#foo]', opts=opts):
                self.none(node.getTag('foo'))

            def wind(func, text):
                return list(func(text))

            self.raises(s_exc.NoSuchOpt, wind, core.eval, '%foo=asdf')
            self.raises(s_exc.BadOptValu, wind, core.eval, '%limit=asdf')

            self.len(2, list(core.eval(('[ teststr=foo teststr=bar ]'))))
            self.len(1, list(core.eval(('teststr %limit=1'))))

            opts = {'vars': {'foo': 'bar'}}

            for node in core.eval('teststr=$foo', opts=opts):
                self.eq('bar', node.ndef[1])

    def test_feed_splice(self):

        iden = s_common.guid()

        with self.getTestCore() as core:

            offs = core.getFeedOffs(iden)
            self.eq(0, offs)

            mesg = ('node:add', {'ndef': ('teststr', 'foo')})
            offs = core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            self.eq(1, offs)

            with core.snap() as snap:
                node = snap.getNodeByNdef(('teststr', 'foo'))
                self.nn(node)

            mesg = ('prop:set', {'ndef': ('teststr', 'foo'), 'prop': 'tick', 'valu': 200})
            offs = core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            with core.snap() as snap:
                node = snap.getNodeByNdef(('teststr', 'foo'))
                self.eq(200, node.get('tick'))

            mesg = ('prop:del', {'ndef': ('teststr', 'foo'), 'prop': 'tick'})
            offs = core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            with core.snap() as snap:
                node = snap.getNodeByNdef(('teststr', 'foo'))
                self.none(node.get('tick'))

            mesg = ('tag:add', {'ndef': ('teststr', 'foo'), 'tag': 'bar', 'valu': (200, 300)})
            offs = core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            with core.snap() as snap:
                node = snap.getNodeByNdef(('teststr', 'foo'))
                self.eq((200, 300), node.getTag('bar'))

            mesg = ('tag:del', {'ndef': ('teststr', 'foo'), 'tag': 'bar'})
            offs = core.addFeedData('syn.splice', [mesg], seqn=(iden, offs))

            with core.snap() as snap:
                node = snap.getNodeByNdef(('teststr', 'foo'))
                self.none(node.getTag('bar'))

    def test_strict(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                node = snap.addNode('teststr', 'foo')

                self.raises(s_exc.NoSuchProp, node.set, 'newpnewp', 10)
                self.raises(s_exc.BadPropValu, node.set, 'tick', (20, 30))

                snap.strict = False

                self.none(snap.addNode('teststr', s_common.novalu))

                self.false(node.set('newpnewp', 10))
                self.false(node.set('tick', (20, 30)))

    def test_getcoremods(self):
        with self.getTestDmon(mirror='dmoncoreauth') as dmon:
            pconf = {'user': 'root', 'passwd': 'root'}
            with dmon._getTestProxy('core', **pconf) as core:
                mods = core.getCoreMods()
                mods = {k: v for k, v in mods}
                conf = mods.get('synapse.tests.utils.TestModule')
                self.nn(conf)
                self.eq(conf.get('key'), 'valu')

    def test_cortex_delnode(self):

        data = {}

        def onPropDel(node, oldv):
            data['prop:del'] = True
            self.eq(oldv, 100)

        def onNodeDel(node):
            data['node:del'] = True

        with self.getTestCore() as core:

            form = core.model.forms.get('teststr')

            form.onDel(onNodeDel)
            form.props.get('tick').onDel(onPropDel)

            with core.snap() as snap:

                targ = snap.addNode('pivtarg', 'foo')
                pivo = snap.addNode('pivcomp', ('foo', 'bar'))

                self.raises(s_exc.CantDelNode, targ.delete)

                tstr = snap.addNode('teststr', 'baz')
                tstr.set('tick', 100)

                buid = tstr.buid

                tstr.delete()

                self.true(data.get('prop:del'))
                self.true(data.get('node:del'))

                # confirm that the snap cache is clear
                self.none(snap.getNodeByBuid(tstr.buid))
                self.none(snap.getNodeByNdef(('teststr', 'baz')))

            with core.snap() as snap:

                # test that secondary props are gone at the row level...
                prop = snap.model.prop('teststr:tick')
                lops = prop.getLiftOps(100)
                self.len(0, list(snap.getLiftRows(lops)))

                # test that primary prop is gone at the row level...
                prop = snap.model.prop('teststr')
                lops = prop.getLiftOps('baz')
                self.len(0, list(snap.getLiftRows(lops)))

                # check that buid rows are gone...
                self.len(0, list(snap._getBuidProps(buid)))

                # final top level API check
                self.none(snap.getNodeByNdef(('teststr', 'baz')))

    def test_cortex_delnode_perms(self):

        with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            pconf = {'user': 'root', 'passwd': 'root'}

            with dmon._getTestProxy('core', **pconf) as core:

                list(core.eval('sudo | [ cycle0=foo :cycle1=bar ]'))
                list(core.eval('sudo | [ cycle1=bar :cycle0=foo ]'))

                list(core.eval('sudo | [ teststr=foo +#lol ]'))

                # no perms and not elevated...
                self.raises(s_exc.AuthDeny, list, core.eval('teststr=foo | delnode'))

                rule = (True, ('node:del',))
                core.addAuthRule('root', rule)

                # should still deny because node has tag we can't delete
                self.raises(s_exc.AuthDeny, list, core.eval('teststr=foo | delnode'))

                rule = (True, ('tag:del', 'lol'))
                core.addAuthRule('root', rule)

                self.len(0, list(core.eval('teststr=foo | delnode')))

                self.raises(s_exc.CantDelNode, list, core.eval('cycle0=foo | delnode'))

                self.len(0, list(core.eval('cycle0=foo | delnode --force')))

    def test_cortex_sudo(self):

        with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            pconf = {'user': 'root', 'passwd': 'root'}

            with dmon._getTestProxy('core', **pconf) as core:

                self.raises(s_exc.AuthDeny, list, core.eval('[ inet:ipv4=1.2.3.4 ]'))

                nodes = list(core.eval('sudo | [ inet:ipv4=1.2.3.4 ]'))
                self.len(1, nodes)

                core.addAuthUser('foo')
                core.setUserPasswd('foo', 'bar')

        # Ensure a non-admin user, using sudo, still fails when they
        # have elevated themselves
        pconf = {'user': 'foo', 'passwd': 'bar'}
        with dmon._getTestProxy('core', **pconf) as core:
            q = 'sudo | [ inet:ipv4=1.2.3.5 ]'
            self.genraises(s_exc.AuthDeny, core.eval, q)

    def test_cortex_snap_cancel(self):

        with self.getTestCore() as core:

            with core.snap() as snap:
                snap.cancel()
                self.raises(s_exc.Canceled, snap.getNodeByNdef, ('teststr', 'foo'))

            with core.snap() as snap:

                snap.addNode('teststr', 'foo')
                snap.addNode('teststr', 'bar')

                genr = snap.getNodesBy('teststr')

                self.nn(next(genr))

                snap.cancel()

                self.raises(s_exc.Canceled, next, genr)

    def test_cortex_cell_splices(self):

        with self.getTestDmon(mirror='dmoncoreauth') as dmon:

            pconf = {'user': 'root', 'passwd': 'root'}

            with dmon._getTestProxy('core', **pconf) as core:

                self.len(0, list(core.splices(0, 1000)))

                list(core.eval('sudo | [ teststr=foo ]'))

                self.ge(len(list(core.splices(0, 1000))), 2)

    def test_pivot_inout(self):

        with self.getTestCore() as core:

            list(core.eval('[ pivcomp=(foo,bar) :tick=2018 ]'))

            nodes = sorted([n.pack() for n in core.eval('pivcomp=(foo,bar) -> *')])

            self.len(2, nodes)
            self.eq(nodes[0][0], ('pivtarg', 'foo'))
            self.eq(nodes[1][0], ('teststr', 'bar'))

            nodes = sorted([n.pack() for n in core.eval('pivcomp=(foo,bar) -+> *')])

            self.len(3, nodes)
            self.eq(nodes[0][0], ('pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('pivtarg', 'foo'))
            self.eq(nodes[2][0], ('teststr', 'bar'))

            nodes = sorted([n.pack() for n in core.eval('teststr=bar <- *')])

            self.len(1, nodes)
            self.eq(nodes[0][0], ('pivcomp', ('foo', 'bar')))

            nodes = sorted([n.pack() for n in core.eval('teststr=bar <+- *')])

            self.len(2, nodes)
            self.eq(nodes[0][0], ('pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('teststr', 'bar'))

    def test_node_repr(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                node = snap.addNode('inet:ipv4', 0x01020304)
                self.eq('1.2.3.4', node.repr())

                node = snap.addNode('inet:dns:a', ('woot.com', 0x01020304))
                self.eq('1.2.3.4', node.repr('ipv4'))

    def test_coverage(self):

        # misc tests to increase code coverage
        with self.getTestCore() as core:

            node = (('teststr', 'foo'), {})

            list(core.addNodes((node,)))

            self.nn(core.getNodeByNdef(('teststr', 'foo')))

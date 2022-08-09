import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.node as s_node

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class NodeTest(s_t_utils.SynTest):

    async def test_pack(self):
        form = 'test:str'
        valu = 'cool'
        props = {'tick': 12345}

        async with self.getTestCore() as core:

            await core.addTagProp('score', ('int', {}), {})
            await core.addTagProp('note', ('str', {'lower': True, 'strip': 'True'}), {})

            async with await core.snap() as snap:

                node = await snap.addNode(form, valu, props=props)
                await node.setTagProp('foo', 'score', 10)
                await node.setTagProp('foo', 'note', " This is a really cool tag! ")

                iden, info = node.pack()
                self.eq(iden, ('test:str', 'cool'))
                self.eq(info.get('tags'), {'foo': (None, None)})
                self.eq(info.get('tagprops'), {'foo': {'score': 10, 'note': 'this is a really cool tag!'}})
                props = {k: v for (k, v) in info.get('props', {}).items() if not k.startswith('.')}
                self.eq(props, {'tick': 12345})

                iden, info = node.pack(dorepr=True)
                self.eq(iden, ('test:str', 'cool'))
                self.eq(info.get('tags'), {'foo': (None, None)})
                props = {k: v for (k, v) in info.get('props', {}).items() if not k.startswith('.')}
                self.eq(props, {'tick': 12345})
                self.eq(info.get('repr'), None)
                reprs = {k: v for (k, v) in info.get('reprs', {}).items() if not k.startswith('.')}
                self.eq(reprs, {'tick': '1970/01/01 00:00:12.345'})
                tagpropreprs = info.get('tagpropreprs')
                self.eq(tagpropreprs, {'foo': {'score': '10'}})

                # Set a property on the node which is extra model and pack it.
                # This situation can be encountered in a multi-layer situation
                # where one Cortex can have model knowledge and set props
                # that another Cortex (sitting on top of the first one) lifts
                # a node which has props the second cortex doens't know about.
                node.props['.newp'] = 1
                node.props['newp'] = (2, 3)
                node.tagprops['foo']['valu'] = 10
                iden, info = node.pack(dorepr=True)
                props, reprs = info.get('props'), info.get('reprs')
                tagprops, tagpropreprs = info.get('tagprops'), info.get('tagpropreprs')
                self.eq(props.get('.newp'), 1)
                self.eq(props.get('newp'), (2, 3))
                self.eq(tagprops, {'foo': {'score': 10, 'note': 'this is a really cool tag!', 'valu': 10}})

                # without model knowledge it is impossible to repr a value so it should
                # *not* be in the repr dict
                self.none(reprs.get('newp'))
                self.none(reprs.get('.newp'))
                self.eq(tagpropreprs, {'foo': {'score': '10'}})

    async def test_set(self):
        form = 'test:str'
        valu = 'cool'
        props = {'tick': 12345}

        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                self.true(snap.strict)  # Following assertions based on snap.strict being true
                node = await snap.addNode(form, valu, props=props)

                self.false(await node.set('tick', 12345))
                self.true(await node.set('tick', 123456))
                await self.asyncraises(s_exc.NoSuchProp, node.set('notreal', 12345))

                ronode = await snap.addNode('test:comp', (1, 's'))
                await self.asyncraises(s_exc.ReadOnlyProp, ronode.set('hehe', 2))
                snap.strict = False
                self.false(await ronode.set('hehe', 3))
                snap.strict = True

    async def test_has(self):
        form = 'test:str'
        valu = 'cool'
        props = {'tick': 12345}

        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(form, valu, props=props)

                self.true(node.has('tick'))
                self.true(node.has('.created'))
                self.false(node.has('nope'))
                self.false(node.has('.nope'))

    async def test_get(self):
        form = 'test:str'
        valu = 'cool'
        props = {'tick': 12345}

        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(form, valu, props=props)
                await node.addTag('cool', valu=(1, 2))

                self.eq(node.get('tick'), 12345)
                self.none(node.get('nope'))

                self.eq(node.get('#cool'), (1, 2))
                self.none(node.get('#newp'))

    async def test_pop(self):
        form = 'test:str'
        valu = 'cool'
        props = {'tick': 12345}

        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(form, valu, props=props)
                await node.addTag('cool', valu=(1, 2))

                await self.asyncraises(s_exc.NoSuchProp, node.pop('nope'))
                snap.strict = False
                self.false(await node.pop('nope'))
                snap.strict = True

                ronode = await snap.addNode('test:comp', (1, 's'))
                await self.asyncraises(s_exc.ReadOnlyProp, ronode.pop('hehe'))
                snap.strict = False
                self.false(await ronode.pop('hehe'))
                snap.strict = True

    async def test_repr(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:

                form = 'test:str'
                valu = 'cool'
                props = {'tick': 12345}
                node = await snap.addNode(form, valu, props=props)
                self.eq('cool', node.repr())
                self.eq(node.repr('tick'), '1970/01/01 00:00:12.345')

                form = 'test:threetype'
                valu = 'cool'
                node = await snap.addNode(form, valu)
                self.eq(node.repr(), '3')
                reprs = {k: v for (k, v) in node.reprs().items() if not k.startswith('.')}
                self.eq(reprs.get('three'), '3')

    async def test_tags(self):
        form = 'test:str'
        valu = 'cool'
        props = {'tick': 12345}

        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                self.true(snap.strict)

                node = await snap.addNode(form, valu, props=props)

                # Add a tag
                await node.addTag('cool', valu=(1, 2))
                self.eq(node.getTag('cool'), (1, 2))
                await node.addTag('cool', valu=(1, 2))  # Add again
                self.eq(node.getTag('cool'), (1, 2))
                await node.addTag('cool', valu=(1, 3))  # Add again with different valu
                self.eq(node.getTag('cool'), (1, 3))
                await node.addTag('cool', valu=(-5, 0))  # Add again with different valu
                self.eq(node.getTag('cool'), (-5, 3))  # merges...

                self.true(node.hasTag('cool'))
                self.true(node.hasTag('#cool'))
                self.false(node.hasTag('notcool'))
                self.false(node.hasTag('#notcool'))

                # Demonstrate that valu is only applied at the level that addTag is called
                await node.addTag('cool.beans.abc', valu=(1, 8))
                self.eq(node.getTag('cool.beans.abc'), (1, 8))
                self.eq(node.getTag('cool.beans'), (None, None))

                await self.asyncraises(s_exc.NoSuchProp, node.pop('nope'))
                snap.strict = False
                self.false(await node.pop('nope'))
                snap.strict = True

    async def test_helpers(self):
        form = 'test:str'
        valu = 'cool'
        props = {'tick': 12345,
                 'hehe': 'hehe',
                 }
        tval = (None, None)

        async with self.getTestCore() as core:
            await core.addTagProp('score', ('int', {}), {})
            await core.addTagProp('note', ('str', {'lower': True, 'strip': 'True'}), {})
            async with await core.snap() as snap:
                node = await snap.addNode(form, valu, props=props)
                await node.addTag('test.foo.bar.duck', tval)
                await node.addTag('test.foo.baz', tval)
                await node.addTag('test.foo.time', ('2016', '2019'))
                await node.addTag('test.foo', ('2015', '2017'))
                await node.setTagProp('test', 'score', 0)
                await node.setTagProp('test', 'note', 'Words')

                pode = node.pack(dorepr=True)

                node2 = await snap.addNode('test:int', '1234')
                pode2 = node2.pack(dorepr=True)

        self.eq(s_node.ndef(pode), ('test:str', 'cool'))
        self.eq(s_node.reprNdef(pode), ('test:str', 'cool'))
        self.eq(s_node.ndef(pode2), ('test:int', 1234))
        self.eq(s_node.reprNdef(pode2), ('test:int', '1234'))

        e = 'bf1198c5f28dae61d595434b0788dd6f7206b1e62d06b0798e012685f1abc85d'
        self.eq(s_node.iden(pode), e)

        self.true(s_node.tagged(pode, 'test'))
        self.true(s_node.tagged(pode, '#test.foo.bar'))
        self.true(s_node.tagged(pode, 'test.foo.bar.duck'))
        self.false(s_node.tagged(pode, 'test.foo.bar.newp'))

        self.len(3, s_node.tags(pode, leaf=True))
        self.len(5, s_node.tagsnice(pode))
        self.len(6, s_node.tags(pode))
        self.eq(s_node.reprTag(pode, '#test.foo.bar'), '')
        self.eq(s_node.reprTag(pode, '#test.foo.time'), '(2016/01/01 00:00:00.000, 2019/01/01 00:00:00.000)')
        self.none(s_node.reprTag(pode, 'test.foo.newp'))

        self.eq(s_node.prop(pode, 'hehe'), 'hehe')
        self.eq(s_node.prop(pode, 'tick'), 12345)
        self.eq(s_node.prop(pode, ':tick'), 12345)
        self.eq(s_node.prop(pode, 'test:str:tick'), 12345)
        self.none(s_node.prop(pode, 'newp'))

        self.eq(s_node.reprProp(pode, 'hehe'), 'hehe')
        self.eq(s_node.reprProp(pode, 'tick'), '1970/01/01 00:00:12.345')
        self.eq(s_node.reprProp(pode, ':tick'), '1970/01/01 00:00:12.345')
        self.eq(s_node.reprProp(pode, 'test:str:tick'), '1970/01/01 00:00:12.345')
        self.none(s_node.reprProp(pode, 'newp'))

        self.eq(s_node.reprTagProps(pode, 'test'),
                [('note', 'words'), ('score', '0')])
        self.eq(s_node.reprTagProps(pode, 'newp'), [])
        self.eq(s_node.reprTagProps(pode, 'test.foo'), [])

        props = s_node.props(pode)
        self.isin('.created', props)
        self.isin('tick', props)
        self.notin('newp', props)

    async def test_storm(self):

        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                query = await snap.core.getStormQuery('')
                async with snap.getStormRuntime(query) as runt:
                    node = await snap.addNode('test:comp', (42, 'lol'))
                    nodepaths = await alist(node.storm(runt, '-> test:int'))
                    self.len(1, nodepaths)
                    self.eq(nodepaths[0][0].ndef, ('test:int', 42))

                    nodepaths = await alist(node.storm(runt, '-> test:int [:loc=$foo]', opts={'vars': {'foo': 'us'}}))
                    self.eq(nodepaths[0][0].props.get('loc'), 'us')

                    path = nodepaths[0][1].fork(node)  # type: s_node.Path
                    path.vars['zed'] = 'ca'

                    # Path present, opts not present
                    nodes = await alist(node.storm(runt, '-> test:int [:loc=$zed] $bar=$foo', path=path))
                    self.eq(nodes[0][0].props.get('loc'), 'ca')
                    # path is not updated due to frame scope
                    self.none(path.vars.get('bar'), 'us')

                    # Path present, opts present but no opts['vars']
                    nodes = await alist(node.storm(runt, '-> test:int [:loc=$zed] $bar=$foo', opts={}, path=path))
                    self.eq(nodes[0][0].props.get('loc'), 'ca')
                    # path is not updated due to frame scope
                    self.none(path.vars.get('bar'))

                    # Path present, opts present with vars
                    nodes = await alist(node.storm(runt, '-> test:int [:loc=$zed] $bar=$baz',
                                                   opts={'vars': {'baz': 'ru'}},
                                                   path=path))
                    self.eq(nodes[0][0].props.get('loc'), 'ca')
                    # path is not updated due to frame scope
                    self.none(path.vars.get('bar'))

                    # Path can push / pop vars in frames
                    self.eq(path.getVar('key'), s_common.novalu)
                    self.len(0, path.frames)
                    path.initframe({'key': 'valu'})
                    self.len(1, path.frames)
                    self.eq(path.getVar('key'), 'valu')
                    path.finiframe()
                    self.len(0, path.frames)
                    self.eq(path.getVar('key'), s_common.novalu)

                    # Path can push / pop a runt as well
                    # This example is *just* a test example to show the variable movement,
                    # not as actual runtime movement..
                    path.initframe({'key': 'valu'})
                    self.eq(path.getVar('key'), 'valu')
                    path.finiframe()
                    self.eq(path.getVar('key'), s_common.novalu)

                    # Path clone() creates a fully independent Path object
                    pcln = path.clone()
                    # Ensure that path vars are independent
                    await pcln.setVar('bar', 'us')
                    self.eq(pcln.getVar('bar'), 'us')
                    self.eq(path.getVar('bar'), s_common.novalu)
                    # Ensure the path nodes are independent
                    self.eq(len(pcln.nodes), len(path.nodes))
                    pcln.nodes.pop(-1)
                    self.ne(len(pcln.nodes), len(path.nodes))

                    # push a frame and clone it - ensure clone mods do not
                    # modify the original path
                    path.initframe({'key': 'valu'})
                    self.len(1, path.frames)
                    pcln = path.clone()
                    self.len(1, pcln.frames)
                    self.eq(path.getVar('key'), 'valu')
                    self.eq(pcln.getVar('key'), 'valu')
                    pcln.finiframe()
                    path.finiframe()
                    await pcln.setVar('bar', 'us')
                    self.eq(pcln.getVar('bar'), 'us')
                    self.eq(path.getVar('bar'), s_common.novalu)
                    self.eq(pcln.getVar('key'), s_common.novalu)
                    self.eq(path.getVar('key'), s_common.novalu)

                    # Check that finiframe without frames resets vars
                    path.finiframe()
                    self.len(0, path.frames)
                    self.eq(s_common.novalu, path.getVar('bar'))

        # Ensure that path clone() behavior in storm is as expected
        # with a real-world style test..
        async with self.getTestCore() as core:
            await core.nodes('[test:int=1 test:int=2]')
            q = '''test:int
            $x = $node.value()
            for $var in (1, 2) { } // The forloop here is used as a node multiplier
            $x = $( $x + 1 )
            $lib.fire(test, valu=$node.value(), x=$x)
            -test:int'''
            msgs = await core.stormlist(q)
            data = collections.defaultdict(set)
            for m in msgs:
                if m[0] == 'storm:fire':
                    for k, v in m[1].get('data').items():
                        data[k].add(v)
            self.eq(dict(data),
                    {'valu': {1, 2}, 'x': {2, 3}})

    async def test_node_repr(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :loc=us ]')
            self.len(1, nodes)

            node = nodes[0]

            self.eq('1.2.3.4', nodes[0].repr())

            self.eq('us', node.repr('loc'))

            with self.raises(s_exc.NoSuchProp):
                node.repr('newp')

            self.none(node.repr('dns:rev'))

    async def test_node_data(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :loc=us ]')
            self.len(1, nodes)

            node = nodes[0]

            self.none(await node.getData('foo'))

            await node.setData('foo', 123)
            self.eq(123, await node.getData('foo'))

            await node.setData('foo', 123)
            self.eq(123, await node.getData('foo'))

            await node.setData('bar', (4, 5, 6))
            self.eq((4, 5, 6), await node.getData('bar'))
            self.eq(123, await node.getData('foo'))

            self.eq([('foo', 123), ('bar', (4, 5, 6))], await alist(node.iterData()))

            self.eq(123, await node.popData('foo'))
            self.none(await node.getData('foo'))
            self.none(await node.popData('foo'))

            self.eq((4, 5, 6), await node.getData('bar'))

            await node.delete()
            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :loc=us ]')
            node = nodes[0]

            self.none(await node.getData('foo'))
            self.none(await node.getData('bar'))

            # Add sad path for setting invalid node data
            with self.raises(s_exc.MustBeJsonSafe):
                await node.setData('newp', {1, 2, 3})

    async def test_node_tagprops(self):
        async with self.getTestCore() as core:
            await core.addTagProp('score', ('int', {}), {})
            await core.addTagProp('limit', ('int', {}), {})
            nodes = await core.nodes('[ test:int=10 ]')
            node = nodes[0]

            self.eq(node.tagprops, {})
            await node.setTagProp('foo.test', 'score', 20)
            await node.setTagProp('foo.test', 'limit', 1000)
            self.eq(node.tagprops, {'foo.test': {'score': 20, 'limit': 1000}})

            await node.delTagProp('foo.test', 'score')
            self.eq(node.tagprops, {'foo.test': {'limit': 1000}})

            await node.setTagProp('foo.test', 'score', 50)
            node.tagprops['foo.test'].pop('score')
            await node.delTagProp('foo.test', 'score')
            self.eq(node.tagprops, {'foo.test': {'limit': 1000}})
            node.tagprops['foo.test'].pop('limit')
            self.eq(node.tagprops, {'foo.test': {}})

    async def test_node_edges(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:ipv4=1.2.3.4 inet:ipv4=5.5.5.5]')
            with self.raises(s_exc.BadArg):
                await nodes[0].addEdge('foo', 'bar')
            with self.raises(s_exc.BadArg):
                await nodes[0].delEdge('foo', 'bar')

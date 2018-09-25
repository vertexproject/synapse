import synapse.exc as s_exc

import synapse.lib.node as s_node

import synapse.tests.utils as s_t_utils

#FIXME:  need a sync test

class NodeTest(s_t_utils.SynTest):

    async def test_pack(self):
        form = 'teststr'
        valu = 'cool'
        props = {'tick': 12345}

        async with self.agetTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(form, valu, props=props)

                iden, info = node.pack()
                self.eq(iden, ('teststr', 'cool'))
                self.eq(info.get('tags'), {})
                props = {k: v for (k, v) in info.get('props', {}).items() if not k.startswith('.')}
                self.eq(props, {'tick': 12345})

                iden, info = node.pack(dorepr=True)
                self.eq(iden, ('teststr', 'cool'))
                self.eq(info.get('tags'), {})
                props = {k: v for (k, v) in info.get('props', {}).items() if not k.startswith('.')}
                self.eq(props, {'tick': 12345})
                self.eq(info.get('repr'), None)
                reprs = {k: v for (k, v) in info.get('reprs', {}).items() if not k.startswith('.')}
                self.eq(reprs, {'tick': '1970/01/01 00:00:12.345'})

                # Set a property on the node which is extra model and pack it.
                # This situation can be encountered in a multi-layer situation
                # where one Cortex can have model knowledge and set props
                # that another Cortex (sitting on top of the first one) lifts
                # a node which has props the second cortex doens't know about.
                node.props['.newp'] = 1
                node.props['newp'] = (2, 3)
                iden, info = node.pack(dorepr=True)
                props, reprs = info.get('props'), info.get('reprs')
                self.eq(props.get('.newp'), 1)
                self.eq(props.get('newp'), (2, 3))
                self.eq(reprs.get('.newp'), '1')
                self.eq(reprs.get('newp'), '(2, 3)')

    async def test_set(self):
        form = 'teststr'
        valu = 'cool'
        props = {'tick': 12345}

        async with self.agetTestCore() as core:
            async with await core.snap() as snap:
                self.true(snap.strict)  # Following assertions based on snap.strict being true
                node = await snap.addNode(form, valu, props=props)

                self.false(await node.set('tick', 12345))
                self.none(await node.set('tick', 123456))
                await self.asyncraises(s_exc.NoSuchProp, node.set('notreal', 12345))

                ronode = await snap.addNode('testcomp', (1, 's'))
                await self.asyncraises(s_exc.ReadOnlyProp, ronode.set('hehe', 2))
                snap.strict = False
                self.false(await ronode.set('hehe', 3))
                snap.strict = True

    async def test_has(self):
        form = 'teststr'
        valu = 'cool'
        props = {'tick': 12345}

        async with self.agetTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(form, valu, props=props)

                self.true(node.has('tick'))
                self.true(node.has('.created'))
                self.false(node.has('nope'))
                self.false(node.has('.nope'))

    async def test_get(self):
        form = 'teststr'
        valu = 'cool'
        props = {'tick': 12345}

        async with self.agetTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(form, valu, props=props)
                await node.addTag('cool', valu=(1, 2))

                self.eq(node.get('tick'), 12345)
                self.none(node.get('nope'))

                self.none(node.get('#cool'))

                # FIXME:  disabled implicit pivot temporarily
                # self.raises(s_exc.NoSuchProp, node.get, 'neat::tick')  # implicit pivot from neat (not a prop) to tick
                # self.raises(s_exc.NoSuchForm, node.get, 'tick::tick')  # implicit pivot from neat to tick (not a form)
                # self.none(node.get('bar::bar'))  # implicit piviot from bar to bar

    async def test_pop(self):
        form = 'teststr'
        valu = 'cool'
        props = {'tick': 12345}

        async with self.agetTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(form, valu, props=props)
                await node.addTag('cool', valu=(1, 2))

                await self.asyncraises(s_exc.NoSuchProp, node.pop('nope'))
                snap.strict = False
                self.false(await node.pop('nope'))
                snap.strict = True

                ronode = await snap.addNode('testcomp', (1, 's'))
                await self.asyncraises(s_exc.ReadOnlyProp, ronode.pop('hehe'))
                snap.strict = False
                self.false(await ronode.pop('hehe'))
                snap.strict = True

    async def test_repr(self):
        async with self.agetTestCore() as core:
            async with await core.snap() as snap:

                form = 'teststr'
                valu = 'cool'
                props = {'tick': 12345}
                node = await snap.addNode(form, valu, props=props)
                self.none(node.repr())
                self.eq(node.repr('tick'), '1970/01/01 00:00:12.345')

                form = 'testthreetype'
                valu = 'cool'
                node = await snap.addNode(form, valu)
                self.eq(node.repr(), '3')
                reprs = {k: v for (k, v) in node.reprs().items() if not k.startswith('.')}
                self.eq(reprs.get('three'), '3')

    async def test_tags(self):
        form = 'teststr'
        valu = 'cool'
        props = {'tick': 12345}

        async with self.agetTestCore() as core:
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
                self.eq(node.getTag('cool'), (-5, 3)) # merges...

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
        form = 'teststr'
        valu = 'cool'
        props = {'tick': 12345}
        tval = (None, None)

        async with self.agetTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode(form, valu, props=props)
                await node.addTag('test.foo.bar.duck', tval)
                await node.addTag('test.foo.baz', tval)
                pode = node.pack(dorepr=True)

        self.eq(s_node.ndef(pode), ('teststr', 'cool'))

        e = '15985dca780f125a6cefdcbd332c64faa505116ea652b1702a3df81e29e98732'
        self.eq(s_node.iden(pode), e)

        self.true(s_node.tagged(pode, 'test'))
        self.true(s_node.tagged(pode, '#test.foo.bar'))
        self.true(s_node.tagged(pode, 'test.foo.bar.duck'))
        self.false(s_node.tagged(pode, 'test.foo.bar.newp'))

        self.len(2, s_node.tags(pode, leaf=True))
        self.len(5, s_node.tags(pode))

        self.eq(s_node.prop(pode, 'tick'), 12345)
        self.eq(s_node.prop(pode, ':tick'), 12345)
        self.eq(s_node.prop(pode, 'teststr:tick'), 12345)
        self.none(s_node.prop(pode, 'newp'))

        props = s_node.props(pode)
        self.isin('.created', props)
        self.isin('tick', props)
        self.notin('newp', props)

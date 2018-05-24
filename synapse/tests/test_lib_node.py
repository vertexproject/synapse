import synapse.exc as s_exc
import synapse.tests.common as s_t_common

class NodeTest(s_t_common.SynTest):

    def test_pack(self):
        form = 'teststr'
        valu = 'cool'
        props = {'tick': 12345}

        with self.getTestCore() as core:
            with core.snap(write=True) as snap:
                node = snap.addNode(form, valu, props=props)

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

    def test_set(self):
        form = 'teststr'
        valu = 'cool'
        props = {'tick': 12345}

        with self.getTestCore() as core:
            with core.snap(write=True) as snap:
                self.true(snap.strict)  # Following assertions based on snap.strict being true
                node = snap.addNode(form, valu, props=props)

                self.false(node.set('tick', 12345))
                self.raises(s_exc.NoSuchProp, node.set, 'notreal', 12345)

                # FIXME do these
                # Strict mode disabled
                # no perms
                # readonly prop
                # merge
                # auto adds / subprops
                # wasset event

    def test_has(self):
        form = 'teststr'
        valu = 'cool'
        props = {'tick': 12345}

        with self.getTestCore() as core:
            with core.snap(write=True) as snap:
                node = snap.addNode(form, valu, props=props)

                self.true(node.has('tick'))
                self.true(node.has('.created'))
                self.false(node.has('nope'))
                self.false(node.has('.nope'))

    def test_get(self):
        form = 'teststr'
        valu = 'cool'
        props = {'tick': 12345}

        with self.getTestCore() as core:
            with core.snap(write=True) as snap:
                node = snap.addNode(form, valu, props=props)
                node.addTag('cool', valu=(1, 2))

                self.eq(node.get('tick'), 12345)
                self.none(node.get('nope'))

                self.none(node.get('#cool'))

                self.raises(s_exc.NoSuchProp, node.get, 'neat::tick')  # implicit pivot from neat (not a prop) to tick
                self.raises(s_exc.NoSuchForm, node.get, 'tick::tick')  # implicit pivot from neat to tick (not a form)
                self.none(node.get('bar::bar'))  # implicit piviot from bar to bar
    '''
    To Test: set (finish), pop, repr, reprs, hasTag, getTag, addTag, delTag
    '''

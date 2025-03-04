import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.node as s_node

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class NodeTest(s_t_utils.SynTest):

    async def test_pack(self):

        async with self.getTestCore() as core:

            await core.addTagProp('score', ('int', {}), {})
            await core.addTagProp('note', ('str', {'lower': True, 'strip': 'True'}), {})
            q = '[test:str=cool :tick=(12345) +#foo:score=10 +#foo:note=" This is a really cool tag! "]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            node = nodes[0]

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

    async def test_get_has_pop_repr_set(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[test:str=cool :tick=(12345) +#cool=((1), (2))]')
            self.len(1, nodes)
            node = nodes[0]

            self.true(node.has('tick'))
            self.true(node.has('.created'))
            self.false(node.has('nope'))
            self.false(node.has('.nope'))

            self.eq(node.get('tick'), 12345)
            self.none(node.get('nope'))
            self.eq(node.get('#cool'), (1, 2))
            self.none(node.get('#newp'))

            self.eq('cool', node.repr())
            self.eq(node.repr('tick'), '1970/01/01 00:00:12.345')

            self.false(await node.set('tick', 12345))
            self.true(await node.set('tick', 123456))
            with self.raises(s_exc.NoSuchProp):
                await node.set('notreal', 12345)
            with self.raises(s_exc.ReadOnlyProp):
                await node.set('.created', 12345)

            # Pop tests - these are destructive to the node
            with self.raises(s_exc.NoSuchProp):
                await node.pop('nope')
            with self.raises(s_exc.ReadOnlyProp):
                await node.pop('.created')
            self.true(await node.pop('tick'))
            self.false(await node.pop('tick'))

            nodes = await core.nodes('[test:threetype=cool]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.repr(), '3')
            reprs = {k: v for (k, v) in node.reprs().items() if not k.startswith('.')}
            self.eq(reprs.get('three'), '3')

    async def test_tags(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[test:str=cool :tick=(12345)]')
            self.len(1, nodes)
            node = nodes[0]

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

    async def test_node_helpers(self):

        def _test_pode(strpode, intpode):
            self.eq(s_node.ndef(strpode), ('test:str', 'cool'))
            self.eq(s_node.reprNdef(strpode), ('test:str', 'cool'))
            self.eq(s_node.ndef(intpode), ('test:int', 1234))
            self.eq(s_node.reprNdef(intpode), ('test:int', '1234'))

            e = 'bf1198c5f28dae61d595434b0788dd6f7206b1e62d06b0798e012685f1abc85d'
            self.eq(s_node.iden(strpode), e)

            self.true(s_node.tagged(strpode, 'test'))
            self.true(s_node.tagged(strpode, '#test.foo.bar'))
            self.true(s_node.tagged(strpode, 'test.foo.bar.duck'))
            self.false(s_node.tagged(strpode, 'test.foo.bar.newp'))

            self.len(3, s_node.tags(strpode, leaf=True))
            self.len(5, s_node.tagsnice(strpode))
            self.len(6, s_node.tags(strpode))
            self.eq(s_node.reprTag(strpode, '#test.foo.bar'), '')
            self.eq(s_node.reprTag(strpode, '#test.foo.time'), '(2016/01/01 00:00:00.000, 2019/01/01 00:00:00.000)')
            self.none(s_node.reprTag(strpode, 'test.foo.newp'))

            self.eq(s_node.prop(strpode, 'hehe'), 'hehe')
            self.eq(s_node.prop(strpode, 'tick'), 12345)
            self.eq(s_node.prop(strpode, ':tick'), 12345)
            self.eq(s_node.prop(strpode, 'test:str:tick'), 12345)
            self.none(s_node.prop(strpode, 'newp'))

            self.eq(s_node.reprProp(strpode, 'hehe'), 'hehe')
            self.eq(s_node.reprProp(strpode, 'tick'), '1970/01/01 00:00:12.345')
            self.eq(s_node.reprProp(strpode, ':tick'), '1970/01/01 00:00:12.345')
            self.eq(s_node.reprProp(strpode, 'test:str:tick'), '1970/01/01 00:00:12.345')
            self.none(s_node.reprProp(strpode, 'newp'))

            self.eq(s_node.reprTagProps(strpode, 'test'),
                    [('note', 'words'), ('score', '0')])
            self.eq(s_node.reprTagProps(strpode, 'newp'), [])
            self.eq(s_node.reprTagProps(strpode, 'test.foo'), [])

            props = s_node.props(strpode)
            self.isin('.created', props)
            self.isin('tick', props)
            self.notin('newp', props)

        async with self.getTestCore() as core:
            await core.addTagProp('score', ('int', {}), {})
            await core.addTagProp('note', ('str', {'lower': True, 'strip': 'True'}), {})
            q = '''[test:str=cool :tick=(12345) :hehe=hehe +#test.foo.bar.duck +#test.foo.baz
            +#test.foo.time=(2016, 2019) +#test.foo=(2015, 2017) +#test:score=0 +#test:note=Words]'''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            node = nodes[0]
            pode = node.pack(dorepr=True)

            nodes = await core.nodes('[test:int=1234]')
            self.len(1, nodes)
            node2 = nodes[0]
            pode2 = node2.pack(dorepr=True)

            _test_pode(strpode=pode, intpode=pode2)

            # Now get those packed nodes via Telepath
            async with core.getLocalProxy() as prox:
                telepath_nodes = []
                async for m in prox.storm('test:str=cool test:int=1234',
                                          opts={'repr': True}):
                    if m[0] == 'node':
                        telepath_nodes.append(m[1])
                self.len(2, telepath_nodes)
                telepath_pode = [n for n in telepath_nodes if n[0][0] == 'test:str'][0]
                telepath_pode2 = [n for n in telepath_nodes if n[0][0] == 'test:int'][0]
                _test_pode(strpode=telepath_pode, intpode=telepath_pode2)

            # Now get those packed nodes via HTTPAPI
            self.none(await core.callStorm('return($lib.auth.users.byname(root).setPasswd(root))'))
            _, port = await core.addHttpsPort(0, host='127.0.0.1')
            https_nodes = []
            async with self.getHttpSess() as sess:
                async with sess.post(f'https://localhost:{port}/api/v1/login',
                                     json={'user': 'root', 'passwd': 'root'}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq('root', retn['result']['name'])

                body = {'query': 'test:str=cool test:int=1234',
                        'opts': {'repr': True}}
                async with sess.get(f'https://localhost:{port}/api/v1/storm', json=body) as resp:
                    async for byts, x in resp.content.iter_chunks():
                        if not byts:
                            break
                        mesg = s_json.loads(byts)
                        if mesg[0] == 'node':
                            https_nodes.append(mesg[1])

            self.len(2, https_nodes)
            http_pode = [n for n in https_nodes if n[0][0] == 'test:str'][0]
            http_pode2 = [n for n in https_nodes if n[0][0] == 'test:int'][0]
            _test_pode(strpode=http_pode, intpode=http_pode2)

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

                    link = {'type': 'runtime'}
                    path = nodepaths[0][1].fork(node, link)  # type: s_node.Path
                    path.vars['zed'] = 'ca'

                    # Path present, opts not present
                    nodes = await alist(node.storm(runt, '-> test:int [:loc=$zed] $bar=$foo', path=path))
                    self.eq(nodes[0][0].props.get('loc'), 'ca')
                    # path is not updated due to frame scope
                    self.none(path.vars.get('bar'), 'us')
                    self.len(2, path.links)
                    self.eq({'type': 'prop', 'prop': 'hehe'}, path.links[0][1])
                    self.eq(link, path.links[1][1])

                    # Path present, opts present but no opts['vars']
                    nodes = await alist(node.storm(runt, '-> test:int [:loc=$zed] $bar=$foo', opts={}, path=path))
                    self.eq(nodes[0][0].props.get('loc'), 'ca')
                    # path is not updated due to frame scope
                    self.none(path.vars.get('bar'))
                    self.len(2, path.links)
                    self.eq({'type': 'prop', 'prop': 'hehe'}, path.links[0][1])
                    self.eq(link, path.links[1][1])

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
                    # Ensure the link elements are independent
                    pcln.links.append({'type': 'edge', 'verb': 'seen'})
                    self.len(3, pcln.links)
                    self.len(2, path.links)

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

    async def test_node_delete(self):
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=foo +(baz)> { [test:str=baz] } ]')
            await core.nodes('test:str=foo | delnode')
            self.len(0, await core.nodes('test:str=foo'))

            await core.nodes('[ test:str=foo <(bar)+ { test:str=foo } ]')
            await core.nodes('test:str=foo | delnode')
            self.len(0, await core.nodes('test:str=foo'))

            edgeq = 'for $edge in $lib.layer.get().getEdges() { $lib.print($edge) }'

            msgs = await core.stormlist(edgeq)
            self.len(0, [m for m in msgs if m[0] == 'print'])

            await core.nodes('[ test:str=foo <(baz)+ { [test:str=baz] } ]')
            await self.asyncraises(s_exc.CantDelNode, core.nodes('test:str=foo | delnode'))

            await core.nodes('test:str=foo | delnode --force')
            self.len(0, await core.nodes('test:str=foo'))

            msgs = await core.stormlist(edgeq)
            self.len(1, [m for m in msgs if m[0] == 'print'])

            q = '''
            [test:str=delfoo test:str=delbar]
            { test:str=delfoo [ +(bar)> { test:str=delbar } ] }
            { test:str=delbar [ +(foo)> { test:str=delfoo } ] }
            '''
            nodes = await core.nodes(q)
            self.len(2, nodes)

            foo, bar = nodes
            fooedges = [edge async for edge in foo.iterEdgesN1()]
            baredges = [edge async for edge in bar.iterEdgesN1()]

            self.len(2, fooedges)
            self.len(2, baredges)

            msgs = await core.stormlist('test:str=delfoo | delnode')
            self.stormIsInErr('Other nodes still have light edges to this node.', msgs)

            nodes = await core.nodes('test:str=delfoo')
            self.len(1, nodes)

            msgs = await core.stormlist('test:str=delfoo | delnode --deledges')
            self.stormHasNoWarnErr(msgs)

            nodes = await core.nodes('test:str=delfoo')
            self.len(0, nodes)

            msgs = await core.stormlist('test:str=delbar | delnode')
            self.stormHasNoWarnErr(msgs)

            nodes = await core.nodes('[test:str=delfoo]')
            self.len(1, nodes)
            foo = nodes[0]

            q = '''
            for $ii in $lib.range(1200) {
                $valu = `bar{$ii}`
                [ test:str=$valu +(foo)> { test:str=delfoo } ]
            }
            '''
            msgs = await core.stormlist(q)
            self.stormHasNoWarnErr(msgs)

            fooedges = [edge async for edge in foo.iterEdgesN2()]

            self.len(1200, fooedges)

            msgs = await core.stormlist('test:str=delfoo | delnode --deledges')
            self.stormHasNoWarnErr(msgs)

            nodes = await core.nodes('test:str=delfoo')
            self.len(0, nodes)

    async def test_node_remove_missing_basetag(self):

        async with self.getTestCore() as core:

            base = await core.callStorm('return($lib.view.get().iden)')
            fork = await core.callStorm('return($lib.view.get().fork().iden)')

            await core.nodes('[test:str=neato +#foo.one]', opts={'view': base})
            await core.nodes('test:str=neato | [ +#foo.two ]', opts={'view': fork})

            await core.nodes('test:str=neato | [ -#foo ]', opts={'view': base})

            othr = await core.nodes('test:str=neato', opts={'view': fork})
            self.len(1, othr)
            self.isin('foo.two', othr[0].tags)
            self.notin('foo', othr[0].tags)

            msgs = await core.stormlist('test:str=neato | [ -#foo ]', opts={'view': fork})
            edits = [m[1] for m in msgs if m[0] == 'node:edits']
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, edits)
            self.len(1, edits[0]['edits'][0][2])

            self.len(1, nodes)
            self.len(0, nodes[0][1]['tags'])

            await core.nodes('[test:int=12 +#ping.pong.neato.burrito]', opts={'view': base})
            await core.nodes('test:int=12 | [ +#ping.pong.awesome.possum ]', opts={'view': fork})

            await core.nodes('test:int=12 | [ -#ping.pong]', opts={'view': base})

            othr = await core.nodes('test:int=12', opts={'view': fork})
            self.len(1, othr)
            self.isin('ping', othr[0].tags)
            self.isin('ping.pong.awesome', othr[0].tags)
            self.isin('ping.pong.awesome.possum', othr[0].tags)

            self.notin('ping.pong', othr[0].tags)

            msgs = await core.stormlist('test:int=12 | [ -#ping.pong ]', opts={'view': fork})
            edits = [m[1] for m in msgs if m[0] == 'node:edits']
            nodes = [m[1] for m in msgs if m[0] == 'node']

            self.len(1, edits)
            self.len(2, edits[0]['edits'][0][2])

            self.len(1, nodes)
            self.len(1, nodes[0][1]['tags'])
            self.isin('ping', nodes[0][1]['tags'])

            nodes = await core.nodes('test:int=12 | [ -#p ]')
            self.len(1, nodes)
            self.len(1, nodes[0].tags)
            self.isin('ping', nodes[0].tags)

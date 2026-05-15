import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.time as s_time
import synapse.lib.layer as s_layer

import synapse.tests.utils as s_test

class StormlibModelTest(s_test.SynTest):

    async def test_stormlib_model_basics(self):

        async with self.getTestCore() as core:

            q = '$val = $lib.model.type(inet:ipv4).repr(42) [test:str=$val]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', '0.0.0.42'))

            q = '$val = $lib.model.type(bool).repr(1) [test:str=$val]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'true'))

            self.eq('inet:dns:a', await core.callStorm('return($lib.model.form(inet:dns:a).type.name)'))
            self.eq('inet:ipv4', await core.callStorm('return($lib.model.prop(inet:dns:a:ipv4).type.name)'))
            self.eq(s_layer.STOR_TYPE_U32, await core.callStorm('return($lib.model.prop(inet:dns:a:ipv4).type.stortype)'))
            self.eq('inet:dns:a', await core.callStorm('return($lib.model.type(inet:dns:a).name)'))

            self.eq('1.2.3.4', await core.callStorm('return($lib.model.type(inet:ipv4).repr($(0x01020304)))'))
            self.eq('123', await core.callStorm('return($lib.model.type(int).repr((1.23 *100)))'))
            self.eq((123, {}), await core.callStorm('return($lib.model.type(int).norm((1.23 *100)))'))
            self.eq(0x01020304, await core.callStorm('return($lib.model.type(inet:ipv4).norm(1.2.3.4).index(0))'))
            self.eq({'subs': {'type': 'unicast'}}, await core.callStorm('return($lib.model.type(inet:ipv4).norm(1.2.3.4).index(1))'))
            self.eq('inet:dns:a:ipv4', await core.callStorm('return($lib.model.form(inet:dns:a).prop(ipv4).full)'))
            self.eq('inet:dns:a', await core.callStorm('return($lib.model.prop(inet:dns:a:ipv4).form.name)'))

            await core.addTagProp('score', ('int', {}), {})
            self.eq('score', await core.callStorm('return($lib.model.tagprop(score).name)'))
            self.eq('int', await core.callStorm('return($lib.model.tagprop(score).type.name)'))

            self.true(await core.callStorm('return(($lib.model.prop(".created").form = $lib.null))'))

            mesgs = await core.stormlist('$lib.print($lib.model.form(ou:name))')
            self.stormIsInPrint("model:form: {'name': 'ou:name'", mesgs)

            mesgs = await core.stormlist('$lib.pprint($lib.model.form(ou:name))')
            self.stormIsInPrint("{'name': 'ou:name'", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.model.form(ou:name).type)')
            self.stormIsInPrint("model:type: ('ou:name'", mesgs)

            mesgs = await core.stormlist('$lib.pprint($lib.model.form(ou:name).type)')
            self.stormIsInPrint("('ou:name'", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.model.prop(ps:contact:orgname))')
            self.stormIsInPrint("model:property: {'name': 'orgname'", mesgs)

            mesgs = await core.stormlist('$lib.pprint($lib.model.prop(ps:contact:orgname))')
            self.stormIsInPrint("'type': ('ou:name'", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.model.tagprop(score))')
            self.stormIsInPrint("model:tagprop: {'name': 'score'", mesgs)

            mesgs = await core.stormlist('$lib.pprint($lib.model.tagprop(score))')
            self.stormIsInPrint("'name': 'score'", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.model.type(int))')
            self.stormIsInPrint("model:type: ('int', ('base'", mesgs)

            mesgs = await core.stormlist("$item=$lib.model.tagprop('score') $lib.pprint($item.type)")
            self.stormIsInPrint("('int',\n ('base',", mesgs)

            mesgs = await core.stormlist("$item=$lib.model.tagprop('score') $lib.print($item.type)")
            self.stormIsInPrint("model:type: ('int', ('base'", mesgs)

            self.false(await core.callStorm('return($lib.model.type(int).mutable)'))
            self.false(await core.callStorm('return($lib.model.type(str).mutable)'))
            self.true(await core.callStorm('return($lib.model.type(data).mutable)'))
            self.true(await core.callStorm('return($lib.model.type(array).mutable)'))

    async def test_stormlib_model_edge(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                user = await core.auth.addUser('ham')
                asuser = {'user': user.iden}

                mesgs = await core.stormlist('model.edge.list', opts=asuser)
                self.stormIsInPrint('No edge verbs found in the current view', mesgs)

                await core.nodes('[ media:news="*" ]')
                await core.nodes('[ inet:ipv4=1.2.3.4 ]')

                await core.nodes('media:news [ +(refs)> {inet:ipv4=1.2.3.4} ]')

                # Basics
                mesgs = await core.stormlist('model.edge.list', opts=asuser)
                self.stormIsInPrint('refs', mesgs)

                mesgs = await core.stormlist('model.edge.set refs doc "foobar"', opts=asuser)
                self.stormIsInPrint('Set edge key: verb=refs key=doc', mesgs)

                mesgs = await core.stormlist('model.edge.list', opts=asuser)
                self.stormIsInPrint('foobar', mesgs)

                mesgs = await core.stormlist('model.edge.get refs', opts=asuser)
                self.stormIsInPrint('foobar', mesgs)

                await core.stormlist('model.edge.set refs doc "boom bam"', opts=asuser)
                mesgs = await core.stormlist('model.edge.get refs')
                self.stormIsInPrint('boom bam', mesgs)

                # This test will need to change if we add more valid keys.
                keys = await core.callStorm('return( $lib.model.edge.validkeys() )')
                self.eq(keys, ('doc', ))

                # Multiple verbs
                await core.nodes('media:news [ +(cat)> {inet:ipv4=1.2.3.4} ]')
                await core.nodes('media:news [ <(dog)+ {inet:ipv4=1.2.3.4} ]')
                await core.nodes('model.edge.set cat doc "ran up a tree"')

                mesgs = await core.stormlist('model.edge.list')
                self.stormIsInPrint('boom bam', mesgs)
                self.stormIsInPrint('cat', mesgs)
                self.stormIsInPrint('ran up a tree', mesgs)
                self.stormIsInPrint('dog', mesgs)

                mesgs = await core.stormlist('model.edge.get dog')
                self.stormIsInPrint('verb=dog', mesgs)

                # Multiple adds on a verb
                await core.nodes('[ media:news="*" +(refs)> { [inet:ipv4=2.3.4.5] } ]')
                await core.nodes('[ media:news="*" +(refs)> { [inet:ipv4=3.4.5.6] } ]')
                elist = await core.callStorm('return($lib.model.edge.list())')
                self.sorteq(['refs', 'cat', 'dog'], [e[0] for e in elist])

                # Delete entry
                mesgs = await core.stormlist('model.edge.del refs doc', opts=asuser)
                self.stormIsInPrint('Deleted edge key: verb=refs key=doc', mesgs)

                elist = await core.callStorm('return($lib.model.edge.list())')
                self.isin('refs', [e[0] for e in elist])
                self.notin('boom bam', [e[1].get('doc', '') for e in elist])

                # If the edge is no longer in the view it will not show in the list
                await core.nodes('media:news [ -(cat)> {inet:ipv4=1.2.3.4} ]')
                elist = await core.callStorm('return($lib.model.edge.list())')
                self.notin('cat', [e[0] for e in elist])

                # Hive values persist even if all edges were deleted
                await core.nodes('media:news [ +(cat)> {inet:ipv4=1.2.3.4} ]')
                mesgs = await core.stormlist('model.edge.list')
                self.stormIsInPrint('ran up a tree', mesgs)

                # Forked view
                vdef2 = await core.view.fork()
                view2opts = {'view': vdef2.get('iden')}

                await core.nodes('[ ou:org="*" ] [ <(seen)+ { [inet:ipv4=5.5.5.5] } ]', opts=view2opts)

                elist = await core.callStorm('return($lib.model.edge.list())', opts=view2opts)
                self.sorteq([('cat', 'ran up a tree'), ('dog', ''), ('refs', ''), ('seen', '')],
                            [(e[0], e[1].get('doc', '')) for e in elist])

                elist = await core.callStorm('return($lib.model.edge.list())')
                self.sorteq([('cat', 'ran up a tree'), ('dog', ''), ('refs', '')],
                            [(e[0], e[1].get('doc', '')) for e in elist])

                # Error conditions - set
                mesgs = await core.stormlist('model.edge.set missing')
                self.stormIsInErr('The argument <key> is required', mesgs)

                with self.raises(s_exc.NoSuchProp):
                    await core.nodes('model.edge.set refs newp foo')

                mesgs = await core.stormlist('model.edge.set refs doc')
                self.stormIsInErr('The argument <valu> is required', mesgs)

                with self.raises(s_exc.NoSuchName):
                    await core.nodes('model.edge.set newp doc yowza')

                # Error conditions - get
                mesgs = await core.stormlist('model.edge.get')
                self.stormIsInErr('The argument <verb> is required', mesgs)

                with self.raises(s_exc.NoSuchName):
                    await core.nodes('model.edge.get newp')

                # Error conditions - del
                mesgs = await core.stormlist('model.edge.del missing')
                self.stormIsInErr('The argument <key> is required', mesgs)

                with self.raises(s_exc.NoSuchProp):
                    await core.nodes('model.edge.del refs newp')

                with self.raises(s_exc.NoSuchProp):
                    await core.nodes('model.edge.del dog doc')

                with self.raises(s_exc.NoSuchName):
                    await core.nodes('model.edge.del newp doc')

            # edge defintions persist
            async with self.getTestCore(dirn=dirn) as core:
                elist = await core.callStorm('return($lib.model.edge.list())')
                self.sorteq([('cat', 'ran up a tree'), ('dog', ''), ('refs', '')],
                            [(e[0], e[1].get('doc', '')) for e in elist])

    async def test_stormlib_model_depr(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                # create both a deprecated form and a node with a deprecated prop
                await core.nodes('[ ou:org=* :sic=1234 ou:hasalias=($node.repr(), foobar) ]')

                with self.raises(s_exc.NoSuchProp):
                    await core.nodes('model.deprecated.lock newp:newp')

                # lock a prop and a form/type
                await core.nodes('model.deprecated.lock ou:org:sic')
                await core.nodes('model.deprecated.lock ou:hasalias')

                with self.raises(s_exc.IsDeprLocked):
                    await core.nodes('ou:org [ :sic=5678 ]')

                with self.raises(s_exc.IsDeprLocked):
                    await core.nodes('[ou:hasalias=(*, hehe)]')

                with self.getLoggerStream('synapse.lib.snap') as stream:
                    data = (
                        (('ou:org', ('t0',)), {'props': {'sic': '5678'}}),
                    )
                    await core.addFeedData('syn.nodes', data)
                    await stream.expect('Prop ou:org:sic is locked due to deprecation', timeout=1)
                    nodes = await core.nodes('ou:org=(t0,)')
                    self.none(nodes[0].get('sic'))

                # Coverage test for node.set()
                async with await core.snap() as snap:
                    snap.strict = False
                    _msgs = []
                    def append(evnt):
                        _msgs.append(evnt)
                    snap.link(append)
                    nodes = await snap.nodes('ou:org=(t0,) [ :sic=5678 ]')
                    snap.unlink(append)
                    self.stormIsInWarn('Prop ou:org:sic is locked due to deprecation', _msgs)
                    self.none(nodes[0].get('sic'))

                    snap.strict = True
                    with self.raises(s_exc.IsDeprLocked):
                        await snap.nodes('ou:org=(t0,) [ :sic=5678 ]')

                # End coverage test

                mesgs = await core.stormlist('model.deprecated.locks')
                self.stormIsInPrint('ou:org:sic: true', mesgs)
                self.stormIsInPrint('ou:hasalias: true', mesgs)
                self.stormIsInPrint('it:reveng:funcstr: false', mesgs)

                await core.nodes('model.deprecated.lock --unlock ou:org:sic')
                await core.nodes('ou:org [ :sic=5678 ]')
                await core.nodes('model.deprecated.lock ou:org:sic')

            # ensure that the locks persisted and got loaded correctly
            async with self.getTestCore(dirn=dirn) as core:

                mesgs = await core.stormlist('model.deprecated.check')
                # warn due to unlocked
                self.stormIsInWarn('it:reveng:funcstr', mesgs)
                # warn due to existing
                self.stormIsInWarn('ou:org:sic', mesgs)
                self.stormIsInWarn('ou:hasalias', mesgs)
                self.stormIsInPrint('Your cortex contains deprecated model elements', mesgs)

                await core.nodes('model.deprecated.lock *')

                mesgs = await core.stormlist('model.deprecated.locks')
                self.stormIsInPrint('it:reveng:funcstr: true', mesgs)

                await core.nodes('ou:org [ -:sic ]')
                await core.nodes('ou:hasalias | delnode')

                mesgs = await core.stormlist('model.deprecated.check')
                self.stormIsInPrint('Congrats!', mesgs)

    async def test_stormlib_model_depr_check(self):

        conf = {
            'modules': [
                'synapse.tests.test_datamodel.DeprecatedModel',
            ]
        }

        with self.getTestDir() as dirn:
            async with self.getTestCore(conf=conf, dirn=dirn) as core:
                mesgs = await core.stormlist('model.deprecated.check')

                self.stormIsInWarn('.pdep is not yet locked', mesgs)
                self.stormNotInWarn('test:dep:easy.pdep is not yet locked', mesgs)

    async def test_stormlib_model_migration(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ test:str=src test:str=dst test:str=deny test:str=other ]')
            otheriden = nodes[3].iden()

            lowuser = await core.auth.addUser('lowuser')
            aslow = {'user': lowuser.iden}

            # copy node data

            await self.asyncraises(s_exc.BadArg, core.nodes('test:str=src $lib.model.migration.copyData($node, newp)'))
            await self.asyncraises(s_exc.BadArg, core.nodes('test:str=dst $lib.model.migration.copyData(newp, $node)'))

            nodes = await core.nodes('''
                test:str=src
                $node.data.set(a, a-src)
                $node.data.set(b, b-src)
                $n=$node -> {
                    test:str=dst
                    $node.data.set(a, a-dst)
                    $lib.model.migration.copyData($n, $node)
                }
            ''')
            self.len(1, nodes)
            self.sorteq(
                [('a', 'a-dst'), ('b', 'b-src')],
                [data async for data in nodes[0].iterData()]
            )

            nodes = await core.nodes('''
                test:str=src $n=$node -> {
                    test:str=dst
                    $lib.model.migration.copyData($n, $node, overwrite=$lib.true)
                }
            ''')
            self.len(1, nodes)
            self.sorteq(
                [('a', 'a-src'), ('b', 'b-src')],
                [data async for data in nodes[0].iterData()]
            )

            q = 'test:str=src $n=$node -> { test:str=deny $lib.model.migration.copyData($n, $node) }'
            await self.asyncraises(s_exc.AuthDeny, core.nodes(q, opts=aslow))

            # copy edges

            await self.asyncraises(s_exc.BadArg, core.nodes('test:str=src $lib.model.migration.copyEdges($node, newp)'))
            await self.asyncraises(s_exc.BadArg, core.nodes('test:str=dst $lib.model.migration.copyEdges(newp, $node)'))

            nodes = await core.nodes('''
                test:str=src
                [ <(foo)+ { test:str=other } +(bar)> { test:str=other } ]
                $n=$node -> {
                    test:str=dst
                    $lib.model.migration.copyEdges($n, $node)
                }
            ''')
            self.len(1, nodes)
            self.eq([('bar', otheriden)], [edge async for edge in nodes[0].iterEdgesN1()])
            self.eq([('foo', otheriden)], [edge async for edge in nodes[0].iterEdgesN2()])

            q = 'test:str=src $n=$node -> { test:str=deny $lib.model.migration.copyEdges($n, $node) }'
            await self.asyncraises(s_exc.AuthDeny, core.nodes(q, opts=aslow))

            # copy tags

            await self.asyncraises(s_exc.BadArg, core.nodes('test:str=src $lib.model.migration.copyTags($node, newp)'))
            await self.asyncraises(s_exc.BadArg, core.nodes('test:str=dst $lib.model.migration.copyTags(newp, $node)'))

            await core.nodes('$lib.model.ext.addTagProp(test, (str, ({})), ({}))')

            nodes = await core.nodes('''
                test:str=src
                [ +#foo=(2010, 2012) +#foo.bar +#baz:test=src ]
                $n=$node -> {
                    test:str=dst
                    [ +#foo=(2010, 2011) +#baz:test=dst ]
                    $lib.model.migration.copyTags($n, $node)
                }
            ''')
            self.len(1, nodes)
            self.sorteq([
                ('baz', (None, None)),
                ('foo', (s_time.parse('2010'), s_time.parse('2012'))),
                ('foo.bar', (None, None))
            ], nodes[0].getTags())
            self.eq([], nodes[0].getTagProps('foo'))
            self.eq([], nodes[0].getTagProps('foo.bar'))
            self.eq([('test', 'dst')], [(k, nodes[0].getTagProp('baz', k)) for k in nodes[0].getTagProps('baz')])

            nodes = await core.nodes('''
                test:str=src $n=$node -> {
                    test:str=dst
                    $lib.model.migration.copyTags($n, $node, overwrite=$lib.true)
                }
            ''')
            self.len(1, nodes)
            self.eq([('test', 'src')], [(k, nodes[0].getTagProp('baz', k)) for k in nodes[0].getTagProps('baz')])

            q = 'test:str=src $n=$node -> { test:str=deny $lib.model.migration.copyTags($n, $node) }'
            await self.asyncraises(s_exc.AuthDeny, core.nodes(q, opts=aslow))

            # copy extended properties
            await self.asyncraises(s_exc.BadArg, core.nodes('test:str=src $lib.model.migration.copyExtProps($node, newp)'))
            await self.asyncraises(s_exc.BadArg, core.nodes('test:str=dst $lib.model.migration.copyExtProps(newp, $node)'))

            await core.addFormProp('test:str', '_foo', ('str', {}), {})

            srciden = s_common.guid()
            dstiden = s_common.guid()

            opts = {'vars': {'srciden': srciden, 'dstiden': dstiden}}
            await core.callStorm('''
                [ test:str=$srciden :_foo=foobarbaz ]
                $n=$node -> {
                    [ test:str=$dstiden ]
                    $lib.model.migration.copyExtProps($n, $node)
                }
            ''', opts=opts)

            nodes = await core.nodes('test:str=$dstiden', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('_foo'), 'foobarbaz')

    async def test_stormlib_model_migrations_risk_hasvuln_vulnerable(self):

        async with self.getTestCore() as core:

            await core.nodes('$lib.model.ext.addTagProp(test, (str, ({})), ({}))')
            await core.nodes('$lib.model.ext.addFormProp(risk:hasvuln, _test, (ps:contact, ({})), ({}))')

            await core.nodes('[ risk:vuln=* it:prod:softver=* +#test ]')

            opts = {
                'vars': {
                    'guid00': (guid00 := 'c6f158a4d8e267a023b06415a04bf583'),
                    'guid01': (guid01 := 'e98f7eada5f5057bc3181ab3fab1f7d5'),
                    'guid02': (guid02 := '99b27f37f5cc1681ad0617e7c97a4094'),
                }
            }

            # nodes with 1 vulnerable node get matching guids
            # all data associated with hasvuln (except ext props) are migrated

            nodes = await core.nodes('''
                [ risk:hasvuln=$guid00
                    :software={ it:prod:softver#test }
                    :vuln={ risk:vuln#test }
                    :_test={[ ps:contact=* ]}
                    .seen=(2010, 2011)
                    +#test=(2012, 2013)
                    +#test.foo:test=hi
                    <(seen)+ {[ meta:source=* :name=foo ]}
                    +(refs)> {[ ps:contact=* :name=bar ]}
                ]
                $node.data.set(baz, bam)
                $n=$node -> { yield $lib.model.migration.s.riskHasVulnToVulnerable($n) }
            ''', opts=opts)
            self.len(1, nodes)
            self.eq(guid00, nodes[0].ndef[1])
            self.eq([
                ('test', (s_time.parse('2012'), s_time.parse('2013'))),
                ('test.foo', (None, None))
            ], nodes[0].getTags())
            self.eq('hi', nodes[0].getTagProp('test.foo', 'test'))
            self.eq('bam', await nodes[0].getData('baz'))

            self.len(1, await core.nodes('risk:vulnerable#test <(seen)- meta:source +:name=foo'))
            self.len(1, await core.nodes('risk:vulnerable#test -(refs)> ps:contact +:name=bar'))
            self.len(1, await core.nodes('risk:vulnerable#test :vuln -> risk:vuln +#test'))
            self.len(1, await core.nodes('risk:vulnerable#test :node -> * +it:prod:softver +#test'))

            # migrate guids - node existence not required

            nodes = await core.nodes('''
                [ risk:hasvuln=$guid01
                    :software=$lib.guid()
                    :vuln=$lib.guid()
                ]
                $n=$node -> { yield $lib.model.migration.s.riskHasVulnToVulnerable($n) }
            ''', opts=opts)
            self.len(1, nodes)
            self.eq(guid01, nodes[0].ndef[1])
            self.nn(nodes[0].get('node'))
            self.nn(nodes[0].get('vuln'))

            # multi-prop - unique guids by prop

            nodes = await core.nodes('''
                [ risk:hasvuln=$guid02
                    :hardware={[ it:prod:hardware=* ]}
                    :host={[ it:host=* ]}
                    :item={[ mat:item=* ]}
                    :org={[ ou:org=* ]}
                    :person={[ ps:person=* ]}
                    :place={[ geo:place=* ]}
                    :software={ it:prod:softver#test }
                    :spec={[ mat:spec=* ]}
                    :vuln={ risk:vuln#test }
                    +#test2
                ]
                $n=$node -> { yield $lib.model.migration.s.riskHasVulnToVulnerable($n) }
            ''', opts=opts)
            self.len(8, nodes)
            self.false(any(n.ndef[1] == guid02 for n in nodes))
            self.true(all(n.hasTag('test2') for n in nodes))
            nodes.sort(key=lambda n: n.get('node'))
            self.eq(
                ['geo:place', 'it:host', 'it:prod:hardware', 'it:prod:softver',
                 'mat:item', 'mat:spec', 'ou:org', 'ps:person'],
                [n.get('node')[0] for n in nodes]
            )

            self.len(2, await core.nodes('it:prod:softver#test -> risk:vulnerable +{ :vuln -> risk:vuln +#test }'))

            # nodata

            self.len(1, await core.nodes('risk:vulnerable=$guid00 $node.data.pop(baz)', opts=opts))

            nodes = await core.nodes('''
                risk:hasvuln=$guid00 $n=$node
                -> { yield $lib.model.migration.s.riskHasVulnToVulnerable($n, nodata=$lib.true) }
            ''', opts=opts)
            self.len(1, nodes)
            self.none(await nodes[0].getData('baz'))

            # no-ops

            self.len(0, await core.nodes('''
                [ risk:hasvuln=* ]
                $n=$node -> { yield $lib.model.migration.s.riskHasVulnToVulnerable($n) }
            '''))

            self.len(0, await core.nodes('''
                [ risk:hasvuln=* :vuln={[ risk:vuln=* ]} ]
                $n=$node -> { yield $lib.model.migration.s.riskHasVulnToVulnerable($n) }
            '''))

            self.len(0, await core.nodes('''
                [ risk:hasvuln=* :host={[ it:host=* ]} ]
                $n=$node -> { yield $lib.model.migration.s.riskHasVulnToVulnerable($n) }
            '''))

            # perms

            lowuser = await core.auth.addUser('low')
            aslow = {'user': lowuser.iden}

            await lowuser.addRule((True, ('node', 'tag', 'add')))

            await core.nodes('''
                [ risk:hasvuln=*
                    :vuln={[ risk:vuln=* ]}
                    :host={[ it:host=* ]}
                    .seen=2010
                    +#test.low
                ]
            ''')

            scmd = '''
                risk:hasvuln#test.low $n=$node
                -> {
                   yield $lib.model.migration.s.riskHasVulnToVulnerable($n)
                }
            '''

            with self.raises(s_exc.AuthDeny) as ectx:
                await core.nodes(scmd, opts=aslow)
            self.eq(perm := 'node.add.risk:vulnerable', ectx.exception.errinfo['perm'])
            await lowuser.addRule((True, perm.split('.')))

            with self.raises(s_exc.AuthDeny) as ectx:
                await core.nodes(scmd, opts=aslow)
            self.eq(perm := 'node.prop.set.risk:vulnerable.vuln', ectx.exception.errinfo['perm'])
            await lowuser.addRule((True, perm.split('.')))

            with self.raises(s_exc.AuthDeny) as ectx:
                await core.nodes(scmd, opts=aslow)
            self.eq(perm := 'node.prop.set.risk:vulnerable.node', ectx.exception.errinfo['perm'])
            await lowuser.addRule((True, perm.split('.')))

            with self.raises(s_exc.AuthDeny) as ectx:
                await core.nodes(scmd, opts=aslow)
            self.eq(perm := 'node.prop.set.risk:vulnerable..seen', ectx.exception.errinfo['perm'])
            await lowuser.addRule((True, perm.split('.', maxsplit=4)))

            self.len(1, await core.nodes(scmd, opts=aslow))

            # bad inputs

            with self.raises(s_exc.BadArg) as ectx:
                await core.nodes('[ it:host=* ] $lib.model.migration.s.riskHasVulnToVulnerable($node)')
            self.isin('only accepts risk:hasvuln nodes', ectx.exception.errinfo['mesg'])

            with self.raises(s_exc.BadArg) as ectx:
                await core.nodes('$lib.model.migration.s.riskHasVulnToVulnerable(newp)')
            self.isin('must be a node', ectx.exception.errinfo['mesg'])

    async def test_stormlib_model_migration_s_inet_ssl_to_tls_servercert(self):
        async with self.getRegrCore('inet_ssl_to_tls_servercert') as core:
            nodes = await core.nodes('meta:source')
            self.len(1, nodes)

            nodes = await core.nodes('meta:source -(seen)> *')
            self.len(3, nodes)
            for node in nodes:
                self.eq(node.ndef[0], 'inet:ssl:cert')

            nodes = await core.nodes('inet:ssl:cert')
            self.len(3, nodes)

            nodes = await core.nodes('file:bytes')
            self.len(3, nodes)

            nodes = await core.nodes('crypto:x509:cert')
            self.len(2, nodes)

            nodes = await core.nodes('inet:tls:servercert')
            self.len(0, nodes)

            q = 'inet:ssl:cert | $lib.model.migration.s.inetSslCertToTlsServerCert($node)'
            await core.nodes(q)

            nodes = await core.nodes('file:bytes')
            self.len(3, nodes)

            nodes = await core.nodes('crypto:x509:cert')
            self.len(3, nodes)

            nodes = await core.nodes('inet:tls:servercert')
            self.len(3, nodes)

            nodes = await core.nodes('crypto:x509:cert=(cert1,)')
            self.len(1, nodes)
            cert1 = nodes[0]

            nodes = await core.nodes('inet:tls:servercert:server="tcp://1.2.3.4:443"')
            self.len(1, nodes)
            self.eq(nodes[0].get('.seen'), (1688947200000, 1688947200001))
            self.eq(nodes[0].get('server'), 'tcp://1.2.3.4:443')
            self.eq(nodes[0].get('cert'), cert1.ndef[1])
            self.isin('ssl.migration.one', nodes[0].tags)

            nodes = await core.nodes('crypto:x509:cert=(cert2,)')
            self.len(1, nodes)
            cert2 = nodes[0]

            nodes = await core.nodes('inet:tls:servercert:server="tcp://[fe80::1]:8080"')
            self.len(1, nodes)
            self.none(nodes[0].get('.seen'))
            self.eq(nodes[0].get('server'), 'tcp://[fe80::1]:8080')
            self.eq(nodes[0].get('cert'), cert2.ndef[1])
            self.isin('ssl.migration.two', nodes[0].tags)

            sha256 = 'aa0366ffb013ba2053e45cd7e4bcc8acd6a6c1bafc82eddb4e155876734c5e25'
            opts = {'vars': {'sha256': sha256}}

            nodes = await core.nodes('file:bytes=$sha256', opts=opts)
            self.len(1, nodes)
            file = nodes[0]

            # This cert was created by the migration code so do a little extra
            # checking
            nodes = await core.nodes('crypto:x509:cert:file=$sha256', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('file'), file.ndef[1])
            self.eq(nodes[0].ndef, ('crypto:x509:cert', s_common.guid(sha256)))
            cert3 = nodes[0]

            nodes = await core.nodes('inet:tls:servercert:server="tcp://8.8.8.8:53" $node.data.load(foo)')
            self.len(1, nodes)
            self.none(nodes[0].get('.seen'))
            self.eq(nodes[0].get('server'), 'tcp://8.8.8.8:53')
            self.eq(nodes[0].get('cert'), cert3.ndef[1])
            self.isin('ssl.migration.three', nodes[0].tags)
            self.eq(nodes[0].nodedata, {'foo': 'bar'})

            # Check that edges were migrated
            nodes = await core.nodes('meta:source -(seen)> *')
            self.len(6, nodes)
            self.sorteq(
                [k.ndef[0] for k in nodes],
                (
                    'inet:ssl:cert', 'inet:ssl:cert', 'inet:ssl:cert',
                    'inet:tls:servercert', 'inet:tls:servercert', 'inet:tls:servercert',
                )
            )

            with self.raises(s_exc.BadArg) as exc:
                await core.callStorm('inet:server | $lib.model.migration.s.inetSslCertToTlsServerCert($node)')
            self.isin(', not inet:server', exc.exception.get('mesg'))

        async with self.getRegrCore('inet_ssl_to_tls_servercert') as core:
            q = 'inet:ssl:cert | $lib.model.migration.s.inetSslCertToTlsServerCert($node, nodata=$lib.true)'
            await core.nodes(q)

            nodes = await core.nodes('inet:tls:servercert:server="tcp://8.8.8.8:53" $node.data.load(foo)')
            self.len(1, nodes)
            self.none(nodes[0].get('.seen'))
            self.eq(nodes[0].get('server'), 'tcp://8.8.8.8:53')
            self.eq(nodes[0].get('cert'), cert3.ndef[1])
            self.isin('ssl.migration.three', nodes[0].tags)
            self.eq(nodes[0].nodedata, {'foo': None})

    async def test_stormlib_model_migrations_inet_service_message_client(self):

        async with self.getTestCore() as core:

            await core.nodes('''[
                (inet:service:message=* :client:address=1.2.3.4 :client=2.3.4.5)
                (inet:service:message=* :client:address=3.4.5.6)
                (inet:service:message=* :client=4.5.6.7)
            ]''')

            nodes = await core.nodes('''
                inet:service:message
                $lib.model.migration.s.inetServiceMessageClientAddress($node)
            ''')

            self.len(3, nodes)

            for node in nodes:
                self.none(node.get('client:address'))

            exp = ['tcp://2.3.4.5', 'tcp://3.4.5.6', 'tcp://4.5.6.7']
            self.sorteq(exp, [n.get('client') for n in nodes])

            ndata = [n for n in nodes if await n.getData('migration:inet:service:message:client:address')]
            self.len(1, ndata)
            self.eq(ndata[0].get('client'), 'tcp://2.3.4.5')
            self.eq(await ndata[0].getData('migration:inet:service:message:client:address'), 'tcp://1.2.3.4')

    async def test_stormlib_model_migration_fuse_nodes(self):

        async with self.getTestCore() as core:

            # --- Validation errors ---

            await core.nodes('[ test:str=fuse-src00 test:str=fuse-dst00 ]')

            # src must be a node
            await self.asyncraises(s_exc.BadArg,
                core.nodes('test:str=fuse-src00 $lib.model.migration.fuseNodes($node, newp)'))

            # dst must be a node
            await self.asyncraises(s_exc.BadArg,
                core.nodes('test:str=fuse-src00 $lib.model.migration.fuseNodes(newp, $node)'))

            # src and dst must be the same form
            guidval = s_common.guid()
            opts = {'vars': {'guidval': guidval}}
            await core.nodes('[ test:guid=$guidval ]', opts=opts)
            await self.asyncraises(s_exc.BadArg,
                core.nodes('test:str=fuse-src00 $n=$node -> { test:guid=$guidval $lib.model.migration.fuseNodes($n, $node) }',
                           opts=opts))

            # src runt form raises IsRuntForm
            await self.asyncraises(s_exc.IsRuntForm,
                core.nodes('test:runt=beep $n=$node -> { test:runt=boop $lib.model.migration.fuseNodes($n, $node) }'))

            # self-fuse warns and no-ops
            mesgs = await core.stormlist(
                'test:str=fuse-src00 $lib.model.migration.fuseNodes($node, $node)')
            self.stormIsInWarn('src and dst are the same node', mesgs)
            self.len(1, await core.nodes('test:str=fuse-src00'))

            # --- Basic happy path ---

            await core.addTagProp('tp', ('str', {}), {})
            await core.addFormProp('test:str', '_efoo', ('str', {}), {})

            opts = {'vars': {'hsrc': 'hp-src', 'hdst': 'hp-dst'}}

            await core.nodes('''
                [ test:str=$hsrc
                    :hehe=srcval
                    :tick=2020
                    .seen=(2010, 2020)
                    +#foo.bar=(2015, 2016)
                    +#foo.bar:tp=src-tp
                    +#src.only
                    :_efoo=srcext
                ]
                $node.data.set(k1, src-k1)
                $node.data.set(k2, src-k2)
            ''', opts=opts)

            await core.nodes('''
                [ test:str=$hdst
                    :hehe=dstval
                    :tick=2019
                    .seen=(2015, 2025)
                    +#foo.bar=(2018, 2022)
                    +#foo.bar:tp=dst-tp
                    +#dst.only
                ]
                $node.data.set(k1, dst-k1)
                $node.data.set(k3, dst-k3)
            ''', opts=opts)

            dstcreated = (await core.nodes('test:str=$hdst', opts=opts))[0].get('.created')
            self.nn(dstcreated)

            # set up N1 and N2 edges on src
            await core.nodes('[ test:str=hp-edge-other ]')
            await core.nodes('test:str=$hsrc [ +(refs)> { test:str=hp-edge-other } ]', opts=opts)
            await core.nodes('test:str=hp-edge-other [ +(seen)> { test:str=$hsrc } ]', opts=opts)

            # fuse src into dst
            await core.nodes('test:str=$hsrc $n=$node -> { test:str=$hdst $lib.model.migration.fuseNodes($n, $node) }',
                              opts=opts)

            # src is deleted
            self.len(0, await core.nodes('test:str=$hsrc', opts=opts))

            nodes = await core.nodes('test:str=$hdst', opts=opts)
            self.len(1, nodes)
            dst = nodes[0]

            # primary props: src wins on conflict
            self.eq('srcval', dst.get('hehe'))
            self.eq(s_time.parse('2020'), dst.get('tick'))

            # .created is preserved from dst
            self.eq(dstcreated, dst.get('.created'))

            # .seen is unioned: (min(2010,2015), max(2020,2025)) = (2010, 2025)
            self.eq((s_time.parse('2010'), s_time.parse('2025')), dst.get('.seen'))

            # tags: both sets present
            self.isin('foo.bar', dst.tags)
            self.isin('dst.only', dst.tags)
            self.isin('src.only', dst.tags)

            # tag ival: union (min(2015,2018), max(2016,2022)) = (2015, 2022)
            self.eq((s_time.parse('2015'), s_time.parse('2022')), dst.tags.get('foo.bar'))

            # tagprop: src wins
            self.eq('src-tp', dst.getTagProp('foo.bar', 'tp'))

            # nodedata: src wins k1, additive k2 and k3
            self.eq('src-k1', await dst.getData('k1'))
            self.eq('src-k2', await dst.getData('k2'))
            self.eq('dst-k3', await dst.getData('k3'))

            # ext prop
            self.eq('srcext', dst.get('_efoo'))

            # N1 edge (src was N1: src -(refs)> other) → dst -(refs)> other
            edgeother = (await core.nodes('test:str=hp-edge-other'))[0]
            n1edges = [e async for e in dst.iterEdgesN1()]
            self.isin(('refs', edgeother.iden()), n1edges)

            # N2 edge (src was N2: other -(seen)> src) → other -(seen)> dst
            n2edges = [e async for e in dst.iterEdgesN2()]
            self.isin(('seen', edgeother.iden()), n2edges)

            # --- .seen union: src has .seen but dst does not ---

            opts = {'vars': {'ssrc': 'seen-src', 'sdst': 'seen-dst'}}
            await core.nodes('[ test:str=$ssrc .seen=(2020, 2021) test:str=$sdst ]', opts=opts)

            await core.nodes('test:str=$ssrc $n=$node -> { test:str=$sdst $lib.model.migration.fuseNodes($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$ssrc', opts=opts))
            nodes = await core.nodes('test:str=$sdst', opts=opts)
            self.len(1, nodes)
            self.eq((s_time.parse('2020'), s_time.parse('2021')), nodes[0].get('.seen'))

            # --- Form-typed scalar ref rewrite ---
            # test:guid:name is test:str-typed; should be rewritten from src to dst

            opts = {'vars': {'r1src': 'ref-scalar-src', 'r1dst': 'ref-scalar-dst',
                             'r1guid': s_common.guid()}}
            await core.nodes('[ test:str=$r1src test:str=$r1dst ]', opts=opts)
            await core.nodes('[ test:guid=$r1guid :name=$r1src ]', opts=opts)

            await core.nodes('test:str=$r1src $n=$node -> { test:str=$r1dst $lib.model.migration.fuseNodes($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$r1src', opts=opts))
            nodes = await core.nodes('test:guid=$r1guid', opts=opts)
            self.len(1, nodes)
            self.eq('ref-scalar-dst', nodes[0].get('name'))

            # --- Form-typed array ref rewrite + dedup ---
            # test:arrayprop:strsnosplit is array(test:str); contains both src and dst → dedup to just dst

            opts = {'vars': {'r2src': 'arr-src', 'r2dst': 'arr-dst', 'r2ap': s_common.guid()}}
            await core.nodes('[ test:str=$r2src test:str=$r2dst ]', opts=opts)
            await core.nodes('[ test:arrayprop=$r2ap :strsnosplit=($r2src, $r2dst) ]', opts=opts)

            await core.nodes('test:str=$r2src $n=$node -> { test:str=$r2dst $lib.model.migration.fuseNodes($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$r2src', opts=opts))
            nodes = await core.nodes('test:arrayprop=$r2ap', opts=opts)
            self.len(1, nodes)
            arrv = nodes[0].get('strsnosplit')
            self.notin('arr-src', arrv)
            self.isin('arr-dst', arrv)

            # --- Form-typed array ref rewrite (src only, no dedup) ---
            # When only src is in the array (dst not present), dst is appended after src is removed.

            opts = {'vars': {'r2bsrc': 'arr2-src', 'r2bdst': 'arr2-dst', 'r2bap': s_common.guid()}}
            await core.nodes('[ test:str=$r2bsrc test:str=$r2bdst ]', opts=opts)
            await core.nodes('[ test:arrayprop=$r2bap :strsnosplit=($r2bsrc,) ]', opts=opts)

            await core.nodes('test:str=$r2bsrc $n=$node -> { test:str=$r2bdst $lib.model.migration.fuseNodes($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$r2bsrc', opts=opts))
            nodes = await core.nodes('test:arrayprop=$r2bap', opts=opts)
            self.len(1, nodes)
            arrv = nodes[0].get('strsnosplit')
            self.notin('arr2-src', arrv)
            self.isin('arr2-dst', arrv)

            # --- Ndef scalar ref rewrite ---
            # test:str:bar is ndef-typed; points at (test:str, src) → rewrites to (test:str, dst)

            opts = {'vars': {'r3src': 'ndef-src', 'r3dst': 'ndef-dst', 'r3ref': 'ndef-ref'}}
            await core.nodes('[ test:str=$r3src test:str=$r3dst ]', opts=opts)
            await core.nodes('[ test:str=$r3ref :bar=(test:str, $r3src) ]', opts=opts)

            await core.nodes('test:str=$r3src $n=$node -> { test:str=$r3dst $lib.model.migration.fuseNodes($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$r3src', opts=opts))
            nodes = await core.nodes('test:str=$r3ref', opts=opts)
            self.len(1, nodes)
            self.eq(('test:str', 'ndef-dst'), nodes[0].get('bar'))

            # --- Ndef array ref rewrite + dedup ---
            # test:str:ndefs is array(ndef); contains both (test:str, src) and (test:str, dst) → dedup to just dst

            opts = {'vars': {'r4src': 'ndefa-src', 'r4dst': 'ndefa-dst', 'r4ref': 'ndefa-ref'}}
            await core.nodes('[ test:str=$r4src test:str=$r4dst ]', opts=opts)
            await core.nodes('[ test:str=$r4ref :ndefs=((test:str, $r4src), (test:str, $r4dst)) ]', opts=opts)

            await core.nodes('test:str=$r4src $n=$node -> { test:str=$r4dst $lib.model.migration.fuseNodes($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$r4src', opts=opts))
            nodes = await core.nodes('test:str=$r4ref', opts=opts)
            self.len(1, nodes)
            ndefs = nodes[0].get('ndefs')
            self.notin(('test:str', 'ndefa-src'), ndefs)
            self.isin(('test:str', 'ndefa-dst'), ndefs)

            # --- Non-comp RO ref: warn and skip ---
            # test:rostr:strref is test:str-typed and read-only but NOT a comp sub-prop.
            # fuseNodes() warns and skips it; the prop on the referrer is left unchanged.

            opts = {'vars': {'nc1src': 'ncomp-src', 'nc1dst': 'ncomp-dst', 'nc1guid': s_common.guid()}}
            await core.nodes('[ test:str=$nc1src test:str=$nc1dst ]', opts=opts)
            await core.nodes('[ test:rostr=$nc1guid :strref=$nc1src ]', opts=opts)

            mesgs = await core.stormlist(
                'test:str=$nc1src $n=$node -> { test:str=$nc1dst $lib.model.migration.fuseNodes($n, $node) }',
                opts=opts)
            self.stormIsInWarn('cannot rewrite read-only ref', mesgs)

            # src is deleted (force=True; remaining refs become dangling)
            self.len(0, await core.nodes('test:str=$nc1src', opts=opts))

            # referrer prop is unchanged (skipped, not rewritten)
            nodes = await core.nodes('test:rostr=$nc1guid', opts=opts)
            self.len(1, nodes)
            self.eq('ncomp-src', nodes[0].get('strref'))

            # --- Comp-form RO ref rename ---
            # test:pivcomp:lulz is test:str-typed and read-only (comp sub-prop).
            # Fusing the lulz value triggers recursive comp rename.

            opts = {'vars': {'c1src': 'comp-src', 'c1dst': 'comp-dst', 'c1targ': 'comp-pivtarg'}}
            await core.nodes('[ test:str=$c1src test:str=$c1dst ]', opts=opts)
            await core.nodes('[ test:pivcomp=($c1targ, $c1src) ]', opts=opts)

            await core.nodes('test:str=$c1src $n=$node -> { test:str=$c1dst $lib.model.migration.fuseNodes($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$c1src', opts=opts))
            self.len(0, await core.nodes('test:pivcomp=($c1targ, $c1src)', opts=opts))
            nodes = await core.nodes('test:pivcomp=($c1targ, $c1dst)', opts=opts)
            self.len(1, nodes)
            self.eq('comp-dst', nodes[0].get('lulz'))

            # --- Cycle: src.ref = dst (primary prop copy produces self-ref on dst) ---

            opts = {'vars': {'cy1src': 'cycle1-src', 'cy1dst': 'cycle1-dst'}}
            await core.nodes('[ test:str=$cy1src :somestr=$cy1dst test:str=$cy1dst ]', opts=opts)

            await core.nodes('test:str=$cy1src $n=$node -> { test:str=$cy1dst $lib.model.migration.fuseNodes($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$cy1src', opts=opts))
            nodes = await core.nodes('test:str=$cy1dst', opts=opts)
            self.len(1, nodes)
            self.eq('cycle1-dst', nodes[0].get('somestr'))

            # --- Cycle: dst.ref = src (_rewriteRefs rewrites dst's prop to self-ref) ---

            opts = {'vars': {'cy2src': 'cycle2-src', 'cy2dst': 'cycle2-dst'}}
            await core.nodes('[ test:str=$cy2src test:str=$cy2dst :somestr=$cy2src ]', opts=opts)

            await core.nodes('test:str=$cy2src $n=$node -> { test:str=$cy2dst $lib.model.migration.fuseNodes($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$cy2src', opts=opts))
            nodes = await core.nodes('test:str=$cy2dst', opts=opts)
            self.len(1, nodes)
            self.eq('cycle2-dst', nodes[0].get('somestr'))

            # --- Permissions: node.del on src form denied for low-privilege user ---

            await core.nodes('[ test:str=p-src test:str=p-dst ]')

            lowuser = await core.auth.addUser('lowuser')
            aslow = {'user': lowuser.iden}

            await self.asyncraises(s_exc.AuthDeny,
                core.nodes('test:str=p-src $n=$node -> { test:str=p-dst $lib.model.migration.fuseNodes($n, $node) }',
                           opts=aslow))

            # src unchanged after failed fuse (no partial edits)
            self.len(1, await core.nodes('test:str=p-src'))

            # --- Preflight: missing node.prop.set on src primary prop ---

            await core.nodes('[ test:str=p-prop-src :hehe=42 test:str=p-prop-dst ]')

            lowprop = await core.auth.addUser('lowprop')
            await lowprop.addRule((True, ('node', 'del')))
            aslowprop = {'user': lowprop.iden}

            with self.raises(s_exc.AuthDeny) as ectx:
                await core.nodes(
                    'test:str=p-prop-src $n=$node -> { test:str=p-prop-dst $lib.model.migration.fuseNodes($n, $node) }',
                    opts=aslowprop)

            self.isin('node.prop.set', ectx.exception.errinfo['perm'])
            # src unchanged (preflight raised before any writes)
            nodes = await core.nodes('test:str=p-prop-src')
            self.len(1, nodes)
            self.eq('42', nodes[0].get('hehe'))

            # --- Preflight: missing node.tag.add when src has tags ---

            await core.nodes('[ test:str=p-tag-src +#preflight.tag test:str=p-tag-dst ]')

            lowtag = await core.auth.addUser('lowtag')
            await lowtag.addRule((True, ('node', 'del')))
            await lowtag.addRule((True, ('node', 'prop', 'set')))
            aslowtag = {'user': lowtag.iden}

            with self.raises(s_exc.AuthDeny) as ectx:
                await core.nodes(
                    'test:str=p-tag-src $n=$node -> { test:str=p-tag-dst $lib.model.migration.fuseNodes($n, $node) }',
                    opts=aslowtag)

            self.isin('node.tag.add', ectx.exception.errinfo['perm'])
            self.len(1, await core.nodes('test:str=p-tag-src'))

            # --- Preflight: missing node.edge.add when src has a light edge ---

            await core.nodes('[ test:str=p-edge-n2 test:str=p-edge-src test:str=p-edge-dst ]')
            await core.nodes('test:str=p-edge-src [ <(refs)+ { test:str=p-edge-n2 } ]')

            lowedge = await core.auth.addUser('lowedge')
            await lowedge.addRule((True, ('node', 'del')))
            await lowedge.addRule((True, ('node', 'prop', 'set')))
            await lowedge.addRule((True, ('node', 'tag', 'add')))
            aslowedge = {'user': lowedge.iden}

            with self.raises(s_exc.AuthDeny) as ectx:
                await core.nodes(
                    'test:str=p-edge-src $n=$node -> { test:str=p-edge-dst $lib.model.migration.fuseNodes($n, $node) }',
                    opts=aslowedge)

            self.isin('node.edge.add', ectx.exception.errinfo['perm'])
            self.len(1, await core.nodes('test:str=p-edge-src'))

            # --- Preflight: missing confirmPropSet for inbound ref prop ---
            # Grant all direct perms; withhold node.prop.set on the referrer's prop.

            await core.nodes('[ test:str=p-ref-src test:str=p-ref-dst ]')
            await core.nodes('[ test:guid=(p-ref-guid,) :name=p-ref-src ]')

            lowref = await core.auth.addUser('lowref')
            await lowref.addRule((True, ('node', 'del')))
            await lowref.addRule((True, ('node', 'prop', 'set', 'test:str')))
            await lowref.addRule((True, ('node', 'tag', 'add')))
            await lowref.addRule((True, ('node', 'edge', 'add')))
            await lowref.addRule((True, ('node', 'data', 'set')))
            aslowref = {'user': lowref.iden}

            with self.raises(s_exc.AuthDeny) as ectx:
                await core.nodes(
                    'test:str=p-ref-src $n=$node -> { test:str=p-ref-dst $lib.model.migration.fuseNodes($n, $node) }',
                    opts=aslowref)

            self.isin('node.prop.set', ectx.exception.errinfo['perm'])
            # src not deleted; referrer still points at src
            self.len(1, await core.nodes('test:str=p-ref-src'))
            ref_nodes = await core.nodes('test:guid=(p-ref-guid,)')
            self.len(1, ref_nodes)
            self.eq('p-ref-src', ref_nodes[0].get('name'))

            # --- Preflight: admin short-circuit --- admin bypasses perm scan ---
            # Admin of the write layer skips the entire preflight scan; fuse succeeds
            # even with no explicit perms granted.

            await core.nodes('[ test:str=p-admin-src :hehe=99 +#admin.tag test:str=p-admin-dst ]')
            await core.nodes('[ test:guid=(p-admin-ref,) :name=p-admin-src ]')

            adminuser = await core.auth.addUser('adminuser')
            await adminuser.setAdmin(True)
            asadmin = {'user': adminuser.iden}

            await core.nodes(
                'test:str=p-admin-src $n=$node -> { test:str=p-admin-dst $lib.model.migration.fuseNodes($n, $node) }',
                opts=asadmin)

            self.len(0, await core.nodes('test:str=p-admin-src'))
            nodes = await core.nodes('test:str=p-admin-dst')
            self.len(1, nodes)
            self.eq('99', nodes[0].get('hehe'))
            # referrer rewritten to dst
            ref_nodes = await core.nodes('test:guid=(p-admin-ref,)')
            self.len(1, ref_nodes)
            self.eq('p-admin-dst', ref_nodes[0].get('name'))

            # --- Preflight: non-admin, .seen with dstv is None (first-set .seen path) ---
            # Exercises the confirmPropSet branch when dst has no .seen (dstv is None).

            fullperm = await core.auth.addUser('fullperm')
            await fullperm.addRule((True, ('node',)))
            asfull = {'user': fullperm.iden}

            opts_pfa = {'vars': {'pfasrc': 'pfa-src', 'pfadst': 'pfa-dst'}}
            await core.nodes('[ test:str=$pfasrc .seen=(2020, 2021) test:str=$pfadst ]', opts=opts_pfa)

            await core.nodes(
                'test:str=$pfasrc $n=$node -> { test:str=$pfadst $lib.model.migration.fuseNodes($n, $node) }',
                opts=opts_pfa | asfull)

            self.len(0, await core.nodes('test:str=$pfasrc', opts=opts_pfa))

            # --- Preflight: non-admin full-perm fuse — exercises all preflight scan loops ---
            # src has .seen (merge path, merged != dstv), a tag, N1 and N2 edges (distinct
            # verbs so the N2 verbs.add line is reached), nodedata, an inbound scalar form ref
            # (non-RO prop, hits confirmPropSet + break), and an inbound comp ref (RO comp prop,
            # hits layerConfirm node.del + break). Also drives the array and ndef scan loops.

            opts_pfb = {'vars': {
                'pfbsrc': 'pfb-src', 'pfbdst': 'pfb-dst',
                'pfbn1tgt': 'pfb-n1tgt', 'pfbn2src': 'pfb-n2src',
                'pfbtarg': 'pfb-targ',
            }}
            # src: .seen=(2019, 2021), tag, dst: .seen=(2020, 2020)
            # merged=(2019,2021) != dstv=(2020,2020) → lines 926-928 covered.
            await core.nodes(
                '[ test:str=$pfbsrc .seen=(2019, 2021) +#pfb.tag '
                '  test:str=$pfbdst .seen=(2020, 2020) '
                '  test:str=$pfbn1tgt test:str=$pfbn2src ]',
                opts=opts_pfb)
            # N1 edge from src (verb=refs) and N2 edge on src (verb=linked, distinct from refs).
            await core.nodes('test:str=$pfbsrc [ +(refs)> { test:str=$pfbn1tgt } ]', opts=opts_pfb)
            await core.nodes('test:str=$pfbsrc [ <(linked)+ { test:str=$pfbn2src } ]', opts=opts_pfb)
            # Nodedata on src.
            await core.nodes('test:str=$pfbsrc $node.data.set(pfbkey, pfbdata)', opts=opts_pfb)
            # Inbound scalar form ref (test:guid.name is non-RO, type test:str).
            await core.nodes('[ test:guid=(pfb-fuse-guid,) :name=$pfbsrc ]', opts=opts_pfb)
            # Inbound RO comp ref (test:pivcomp.lulz is RO, type test:str).
            await core.nodes('[ test:pivcomp=($pfbtarg, $pfbsrc) ]', opts=opts_pfb)

            await core.nodes(
                'test:str=$pfbsrc $n=$node -> { test:str=$pfbdst $lib.model.migration.fuseNodes($n, $node) }',
                opts=opts_pfb | asfull)

            self.len(0, await core.nodes('test:str=$pfbsrc', opts=opts_pfb))
            nodes = await core.nodes('test:str=$pfbdst', opts=opts_pfb)
            self.len(1, nodes)
            # .seen was merged: min(2019, 2020) / max(2021, 2020) → (2019, 2021)
            pfb_seen = nodes[0].get('.seen')
            self.true(pfb_seen[0] <= pfb_seen[1])

            # --- Forked view: all nodes created in the fork's write layer ---
            # This is the recommended workflow: create a fork whose write layer holds src,
            # dst, and any inbound referrers; fuse there; parent view is unaffected.

            opts = {'vars': {'fvsrc': 'fv-src', 'fvdst': 'fv-dst', 'fvguid': s_common.guid()}}

            # Fork first so the parent view stays clean.
            vdef2 = await core.view.fork()
            view2iden = vdef2.get('iden')
            view2opts = {'view': view2iden}

            # Create src, dst, and a referrer all in the fork's write layer.
            # :name is test:str-typed, so this auto-creates test:str=fv-src in the fork's wlyr.
            await core.nodes('[ test:str=$fvsrc :hehe=srcval ]', opts=opts | view2opts)
            await core.nodes('[ test:str=$fvdst ]', opts=opts | view2opts)
            await core.nodes('[ test:guid=$fvguid :name=$fvsrc ]', opts=opts | view2opts)

            # Fuse in the fork.
            await core.nodes(
                'test:str=$fvsrc $n=$node -> { test:str=$fvdst $lib.model.migration.fuseNodes($n, $node) }',
                opts=opts | view2opts)

            # src is gone from the fork.
            self.len(0, await core.nodes('test:str=$fvsrc', opts=opts | view2opts))
            # dst is present and carries merged content from src.
            nodes = await core.nodes('test:str=$fvdst', opts=opts | view2opts)
            self.len(1, nodes)
            self.eq('srcval', nodes[0].get('hehe'))
            # referrer's name is rewritten to dst.
            nodes = await core.nodes('test:guid=$fvguid', opts=opts | view2opts)
            self.len(1, nodes)
            self.eq('fv-dst', nodes[0].get('name'))

            # Parent view is unaffected: src, dst, and referrer were only in the fork.
            self.len(0, await core.nodes('test:str=$fvsrc', opts=opts))
            self.len(0, await core.nodes('test:str=$fvdst', opts=opts))
            self.len(0, await core.nodes('test:guid=$fvguid', opts=opts))

            # --- Forked view: src in parent layer → warn, content merged, src not deleted ---
            # When src's ndef lives in a parent layer, fuseNodes warns and merges content
            # into dst but skips the delete. The caller is responsible for deleting src
            # from the appropriate view.

            opts = {'vars': {'fv2src': 'fv2-src', 'fv2dst': 'fv2-dst'}}
            await core.nodes('[ test:str=$fv2src :hehe=fv2srcval test:str=$fv2dst ]', opts=opts)

            vdef3 = await core.view.fork()
            view3opts = {'view': vdef3.get('iden')}

            mesgs = await core.stormlist(
                'test:str=$fv2src $n=$node -> { test:str=$fv2dst $lib.model.migration.fuseNodes($n, $node) }',
                opts=opts | view3opts)
            self.stormIsInWarn('cannot delete src node', mesgs)

            # content is merged: dst now has src's hehe prop
            nodes = await core.nodes('test:str=$fv2dst', opts=opts | view3opts)
            self.len(1, nodes)
            self.eq('fv2srcval', nodes[0].get('hehe'))

            # src is NOT deleted (it lives in the parent layer)
            self.len(1, await core.nodes('test:str=$fv2src', opts=opts | view3opts))

            # --- Forked view: src and comp both in parent layer → both warn ---
            # Creating test:pivcomp=(fv3targ, fv3src) in the parent auto-creates test:str=fv3src
            # in the parent layer. Both src and the comp referrer therefore live in the parent;
            # fuseNodes warns for both: src is not deleted, comp is not renamed.

            opts = {'vars': {'fv3src': 'fv3-src', 'fv3dst': 'fv3-dst', 'fv3targ': 'fv3-targ'}}
            await core.nodes('[ test:str=$fv3dst ]', opts=opts)
            await core.nodes('[ test:pivcomp=($fv3targ, $fv3src) ]', opts=opts)

            vdef4 = await core.view.fork()
            view4opts = {'view': vdef4.get('iden')}

            mesgs = await core.stormlist(
                'test:str=$fv3src $n=$node -> { test:str=$fv3dst $lib.model.migration.fuseNodes($n, $node) }',
                opts=opts | view4opts)

            # two warnings: src not deleted (in parent), comp not renamed (also in parent)
            self.stormIsInWarn('cannot delete src node', mesgs)
            self.stormIsInWarn('cannot rename comp form', mesgs)

            # src persists (in parent layer, not deleted)
            self.len(1, await core.nodes('test:str=$fv3src', opts=opts | view4opts))

            # old comp persists (unrewritten; also in parent layer)
            self.len(1, await core.nodes('test:pivcomp=($fv3targ, $fv3src)', opts=opts | view4opts))

            # new comp was never created
            self.len(0, await core.nodes('test:pivcomp=($fv3targ, $fv3dst)', opts=opts | view4opts))

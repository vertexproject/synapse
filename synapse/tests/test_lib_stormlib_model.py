import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.time as s_time
import synapse.lib.layer as s_layer
import synapse.lib.nodefuse as s_nodefuse

import synapse.tools.backup as s_tools_backup

import synapse.tests.utils as s_test

from unittest import mock

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

    async def test_stormlib_model_migration_fuse(self):

        async with self.getTestCore() as core:

            # --- Validation errors ---

            await core.nodes('[ test:str=fuse-src00 test:str=fuse-dst00 ]')

            # src must be a node
            await self.asyncraises(s_exc.BadArg,
                core.nodes('test:str=fuse-src00 $lib.model.migration.fuse($node, newp)'))

            # dst must be a node
            await self.asyncraises(s_exc.BadArg,
                core.nodes('test:str=fuse-src00 $lib.model.migration.fuse(newp, $node)'))

            # src and dst must be the same form
            guidval = s_common.guid()
            opts = {'vars': {'guidval': guidval}}
            await core.nodes('[ test:guid=$guidval ]', opts=opts)
            await self.asyncraises(s_exc.BadArg,
                core.nodes('test:str=fuse-src00 $n=$node -> { test:guid=$guidval $lib.model.migration.fuse($n, $node) }',
                           opts=opts))

            # src runt form raises IsRuntForm
            await self.asyncraises(s_exc.IsRuntForm,
                core.nodes('test:runt=beep $n=$node -> { test:runt=boop $lib.model.migration.fuse($n, $node) }'))

            # self-fuse warns and no-ops
            mesgs = await core.stormlist(
                'test:str=fuse-src00 $lib.model.migration.fuse($node, $node)')
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
                    :_efoo=dstext
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

            await core.nodes('test:str=$hsrc $n=$node -> { test:str=$hdst $lib.model.migration.fuse($n, $node) }',
                             opts=opts)

            # src is deleted
            self.len(0, await core.nodes('test:str=$hsrc', opts=opts))

            nodes = await core.nodes('test:str=$hdst', opts=opts)
            self.len(1, nodes)
            dst = nodes[0]

            # primary props: dst wins on conflict, since dst is the survivor
            self.eq('dstval', dst.get('hehe'))
            self.eq(s_time.parse('2019'), dst.get('tick'))

            # .created is preserved from dst, since it is read only
            self.eq(dstcreated, dst.get('.created'))

            # .seen is unioned by the storage layer regardless of conflict policy:
            # (min(2010,2015), max(2020,2025))
            self.eq((s_time.parse('2010'), s_time.parse('2025')), dst.get('.seen'))

            # tags: both sets present
            self.isin('foo.bar', dst.tags)
            self.isin('dst.only', dst.tags)
            self.isin('src.only', dst.tags)

            # tag ival: union (min(2015,2018), max(2016,2022))
            self.eq((s_time.parse('2015'), s_time.parse('2022')), dst.tags.get('foo.bar'))

            # tagprop: dst wins on conflict
            self.eq('dst-tp', dst.getTagProp('foo.bar', 'tp'))

            # nodedata: dst wins k1 on conflict, additive k2 and k3
            self.eq('dst-k1', await dst.getData('k1'))
            self.eq('src-k2', await dst.getData('k2'))
            self.eq('dst-k3', await dst.getData('k3'))

            # ext prop: dst wins on conflict
            self.eq('dstext', dst.get('_efoo'))

            # N1 edge (src -(refs)> other) becomes dst -(refs)> other
            edgeother = (await core.nodes('test:str=hp-edge-other'))[0]
            n1edges = [e async for e in dst.iterEdgesN1()]
            self.isin(('refs', edgeother.iden()), n1edges)

            # N2 edge (other -(seen)> src) becomes other -(seen)> dst
            n2edges = [e async for e in dst.iterEdgesN2()]
            self.isin(('seen', edgeother.iden()), n2edges)

            # --- .seen when src has it and dst does not ---

            opts = {'vars': {'ssrc': 'seen-src', 'sdst': 'seen-dst'}}
            await core.nodes('[ test:str=$ssrc .seen=(2020, 2021) test:str=$sdst ]', opts=opts)

            await core.nodes('test:str=$ssrc $n=$node -> { test:str=$sdst $lib.model.migration.fuse($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$ssrc', opts=opts))
            nodes = await core.nodes('test:str=$sdst', opts=opts)
            self.len(1, nodes)
            self.eq((s_time.parse('2020'), s_time.parse('2021')), nodes[0].get('.seen'))

            # --- Form-typed scalar ref rewrite ---

            opts = {'vars': {'r1src': 'ref-scalar-src', 'r1dst': 'ref-scalar-dst',
                             'r1guid': s_common.guid()}}
            await core.nodes('[ test:str=$r1src test:str=$r1dst ]', opts=opts)
            await core.nodes('[ test:guid=$r1guid :name=$r1src ]', opts=opts)

            await core.nodes('test:str=$r1src $n=$node -> { test:str=$r1dst $lib.model.migration.fuse($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$r1src', opts=opts))
            nodes = await core.nodes('test:guid=$r1guid', opts=opts)
            self.len(1, nodes)
            self.eq('ref-scalar-dst', nodes[0].get('name'))

            # --- Form-typed array ref rewrite + dedup ---

            opts = {'vars': {'r2src': 'arr-src', 'r2dst': 'arr-dst', 'r2ap': s_common.guid()}}
            await core.nodes('[ test:str=$r2src test:str=$r2dst ]', opts=opts)
            await core.nodes('[ test:arrayprop=$r2ap :strsnosplit=($r2src, $r2dst) ]', opts=opts)

            await core.nodes('test:str=$r2src $n=$node -> { test:str=$r2dst $lib.model.migration.fuse($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$r2src', opts=opts))
            nodes = await core.nodes('test:arrayprop=$r2ap', opts=opts)
            self.len(1, nodes)
            arrv = nodes[0].get('strsnosplit')
            self.notin('arr-src', arrv)
            self.isin('arr-dst', arrv)

            # --- Form-typed array ref rewrite (src only, dst appended) ---

            opts = {'vars': {'r2bsrc': 'arr2-src', 'r2bdst': 'arr2-dst', 'r2bap': s_common.guid()}}
            await core.nodes('[ test:str=$r2bsrc test:str=$r2bdst ]', opts=opts)
            await core.nodes('[ test:arrayprop=$r2bap :strsnosplit=($r2bsrc,) ]', opts=opts)

            await core.nodes('test:str=$r2bsrc $n=$node -> { test:str=$r2bdst $lib.model.migration.fuse($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$r2bsrc', opts=opts))
            nodes = await core.nodes('test:arrayprop=$r2bap', opts=opts)
            self.len(1, nodes)
            arrv = nodes[0].get('strsnosplit')
            self.notin('arr2-src', arrv)
            self.isin('arr2-dst', arrv)

            # --- Ndef scalar ref rewrite (via the byndef reverse index) ---

            opts = {'vars': {'r3src': 'ndef-src', 'r3dst': 'ndef-dst', 'r3ref': 'ndef-ref'}}
            await core.nodes('[ test:str=$r3src test:str=$r3dst ]', opts=opts)
            await core.nodes('[ test:str=$r3ref :bar=(test:str, $r3src) ]', opts=opts)

            await core.nodes('test:str=$r3src $n=$node -> { test:str=$r3dst $lib.model.migration.fuse($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$r3src', opts=opts))
            nodes = await core.nodes('test:str=$r3ref', opts=opts)
            self.len(1, nodes)
            self.eq(('test:str', 'ndef-dst'), nodes[0].get('bar'))

            # --- Ndef array ref rewrite + dedup ---

            opts = {'vars': {'r4src': 'ndefa-src', 'r4dst': 'ndefa-dst', 'r4ref': 'ndefa-ref'}}
            await core.nodes('[ test:str=$r4src test:str=$r4dst ]', opts=opts)
            await core.nodes('[ test:str=$r4ref :ndefs=((test:str, $r4src), (test:str, $r4dst)) ]', opts=opts)

            await core.nodes('test:str=$r4src $n=$node -> { test:str=$r4dst $lib.model.migration.fuse($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$r4src', opts=opts))
            nodes = await core.nodes('test:str=$r4ref', opts=opts)
            self.len(1, nodes)
            ndefs = nodes[0].get('ndefs')
            self.notin(('test:str', 'ndefa-src'), ndefs)
            self.isin(('test:str', 'ndefa-dst'), ndefs)

            # --- Non-comp read-only ref is rewritten with a warning ---
            # test:rostr:strref is test:str-typed and read-only but not a comp sub-prop.
            # There is no read-only enforcement in the storage layer, so it is rewritten
            # rather than left dangling at a deleted node.

            opts = {'vars': {'nc1src': 'ncomp-src', 'nc1dst': 'ncomp-dst', 'nc1guid': s_common.guid()}}
            await core.nodes('[ test:str=$nc1src test:str=$nc1dst ]', opts=opts)
            await core.nodes('[ test:rostr=$nc1guid :strref=$nc1src ]', opts=opts)

            mesgs = await core.stormlist(
                'test:str=$nc1src $n=$node -> { test:str=$nc1dst $lib.model.migration.fuse($n, $node) }',
                opts=opts)
            self.stormIsInWarn('rewrote read-only property', mesgs)

            self.len(0, await core.nodes('test:str=$nc1src', opts=opts))

            nodes = await core.nodes('test:rostr=$nc1guid', opts=opts)
            self.len(1, nodes)
            self.eq('ncomp-dst', nodes[0].get('strref'))

            # --- Comp-form read-only ref causes a comp rename ---
            # test:pivcomp:lulz is test:str-typed and read-only, so the comp's primary
            # value changes and the old comp node is fused into the renamed one.

            opts = {'vars': {'c1src': 'comp-src', 'c1dst': 'comp-dst', 'c1targ': 'comp-pivtarg'}}
            await core.nodes('[ test:str=$c1src test:str=$c1dst ]', opts=opts)
            await core.nodes('[ test:pivcomp=($c1targ, $c1src) +#comptag ]', opts=opts)

            await core.nodes('test:str=$c1src $n=$node -> { test:str=$c1dst $lib.model.migration.fuse($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$c1src', opts=opts))
            self.len(0, await core.nodes('test:pivcomp=($c1targ, $c1src)', opts=opts))
            nodes = await core.nodes('test:pivcomp=($c1targ, $c1dst)', opts=opts)
            self.len(1, nodes)
            self.eq('comp-dst', nodes[0].get('lulz'))

            # the renamed comp carried the old comp's tags over
            self.isin('comptag', nodes[0].tags)

            # --- Cycle: src references dst ---

            opts = {'vars': {'cy1src': 'cycle1-src', 'cy1dst': 'cycle1-dst'}}
            await core.nodes('[ test:str=$cy1src :somestr=$cy1dst test:str=$cy1dst ]', opts=opts)

            await core.nodes('test:str=$cy1src $n=$node -> { test:str=$cy1dst $lib.model.migration.fuse($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$cy1src', opts=opts))
            nodes = await core.nodes('test:str=$cy1dst', opts=opts)
            self.len(1, nodes)
            self.eq('cycle1-dst', nodes[0].get('somestr'))

            # --- Cycle: dst references src, becoming a self reference ---

            opts = {'vars': {'cy2src': 'cycle2-src', 'cy2dst': 'cycle2-dst'}}
            await core.nodes('[ test:str=$cy2src test:str=$cy2dst :somestr=$cy2src ]', opts=opts)

            await core.nodes('test:str=$cy2src $n=$node -> { test:str=$cy2dst $lib.model.migration.fuse($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$cy2src', opts=opts))
            nodes = await core.nodes('test:str=$cy2dst', opts=opts)
            self.len(1, nodes)
            self.eq('cycle2-dst', nodes[0].get('somestr'))

            # --- Cycle: src references itself, so the reference follows the node ---

            opts = {'vars': {'cy3src': 'cycle3-src', 'cy3dst': 'cycle3-dst'}}
            await core.nodes(
                '[ test:str=$cy3src :somestr=$cy3src :bar=(test:str, $cy3src) test:str=$cy3dst ]', opts=opts)

            await core.nodes('test:str=$cy3src $n=$node -> { test:str=$cy3dst $lib.model.migration.fuse($n, $node) }',
                             opts=opts)

            self.len(0, await core.nodes('test:str=$cy3src', opts=opts))
            nodes = await core.nodes('test:str=$cy3dst', opts=opts)
            self.len(1, nodes)

            # src referenced itself, so dst references itself rather than the node which is
            # now gone. leaving these pointed at src would dangle, and would also mean a
            # repeat of the same fuse still had references to rewrite.
            self.eq('cycle3-dst', nodes[0].get('somestr'))
            self.eq(('test:str', 'cycle3-dst'), nodes[0].get('bar'))

            # --- A comp form which cannot be re-normalized is warned about ---

            opts = {'vars': {'bnsrc': 'badnorm-src', 'bndst': 'badnorm-dst', 'bntarg': 'badnorm-targ'}}
            await core.nodes('[ test:str=$bnsrc test:str=$bndst ]', opts=opts)
            await core.nodes('[ test:pivcomp=($bntarg, $bnsrc) ]', opts=opts)

            comptype = core.model.form('test:pivcomp').type

            def badnorm(valu):
                raise s_exc.BadTypeValu(mesg='comp norm go boom')

            with mock.patch.object(comptype, 'norm', badnorm):
                mesgs = await core.stormlist(
                    'test:str=$bnsrc $n=$node -> { test:str=$bndst $lib.model.migration.fuse($n, $node) }',
                    opts=opts)

            self.stormIsInWarn('cannot re-normalize comp form', mesgs)

            # the old comp is left alone rather than being half renamed
            self.len(1, await core.nodes('test:pivcomp=($bntarg, $bnsrc)', opts=opts))

    async def test_stormlib_model_migration_fuse_ival_merge(self):

        # Interval typed properties and tag properties are unioned by the storage layer
        # rather than one side winning, and this generalizes beyond the special-cased
        # .seen property to any ival-typed prop or tagprop.
        async with self.getTestCore() as core:

            await core.addTagProp('ivaltp', ('ival', {}), {})

            opts = {'vars': {'isrc': (100, 200), 'idst': (300, 400)}}

            await core.nodes('''
                [ test:ival=$isrc :interval=(2020, 2021) +#foo:ivaltp=(2020, 2021) ]
            ''', opts=opts)

            await core.nodes('''
                [ test:ival=$idst :interval=(2022, 2023) +#foo:ivaltp=(2022, 2023) ]
            ''', opts=opts)

            await core.nodes(
                'test:ival=$isrc $n=$node -> { test:ival=$idst $lib.model.migration.fuse($n, $node) }',
                opts=opts)

            self.len(0, await core.nodes('test:ival=$isrc', opts=opts))
            nodes = await core.nodes('test:ival=$idst', opts=opts)
            self.len(1, nodes)

            self.eq((s_time.parse('2020'), s_time.parse('2023')), nodes[0].get('interval'))
            self.eq((s_time.parse('2020'), s_time.parse('2023')), nodes[0].getTagProp('foo', 'ivaltp'))

    async def test_stormlib_model_migration_fuse_multilayer(self):

        async with self.getTestCore() as core:

            # two layers which each independently hold src, and a view over both of them.
            # The fuse emits the same node delete to each layer, but the view can only
            # observe it once, so its node:del trigger must only fire once.
            layr0 = await core.callStorm('return($lib.layer.add().iden)')
            layr1 = await core.callStorm('return($lib.layer.add().iden)')

            opts = {'vars': {'layr0': layr0, 'layr1': layr1}}
            view0 = await core.callStorm('return($lib.view.add(($layr0,)).iden)', opts=opts)
            view1 = await core.callStorm('return($lib.view.add(($layr1,)).iden)', opts=opts)
            both = await core.callStorm('return($lib.view.add(($layr1, $layr0)).iden)', opts=opts)

            await core.nodes('[ test:str=ml-src test:str=ml-dst ]', opts={'view': view0})
            await core.nodes('[ test:str=ml-src test:str=ml-dst ]', opts={'view': view1})

            # src really is in both of the view's layers
            nodes = await core.nodes('test:str=ml-src', opts={'view': both})
            self.len(1, nodes)
            self.len(2, [sode for sode in await nodes[0].getStorNodes() if sode.get('valu')])

            tdef = {'cond': 'node:del', 'form': 'test:str', 'storm': '$lib.queue.gen(mlq).put(deleted)'}
            await core.callStorm('return($lib.trigger.add($tdef))',
                                 opts={'vars': {'tdef': tdef}, 'view': both})

            await core.nodes(
                'test:str=ml-src $n=$node -> { test:str=ml-dst $lib.model.migration.fuse($n, $node) }',
                opts={'view': both})

            self.len(0, await core.nodes('test:str=ml-src', opts={'view': both}))
            self.len(0, await core.nodes('test:str=ml-src', opts={'view': view0}))
            self.len(0, await core.nodes('test:str=ml-src', opts={'view': view1}))

            # exactly one node:del consequence, not one per layer
            self.eq(1, await core.callStorm('return($lib.queue.gen(mlq).size())'))

    async def test_stormlib_model_migration_fuse_shared_comp(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=sc-src test:str=sc-dst ]')

            # the same comp node written into two different fork layers. Both layers hold
            # the comp's read-only :lulz prop, so the rename is discovered twice and the
            # second one must be skipped.
            vdef = await core.view.fork()
            forka = vdef.get('iden')
            vdef = await core.view.fork()
            forkb = vdef.get('iden')

            await core.nodes('[ test:pivcomp=(sc-targ, sc-src) ]', opts={'view': forka})
            await core.nodes('[ test:pivcomp=(sc-targ, sc-src) ]', opts={'view': forkb})

            await core.nodes(
                'test:str=sc-src $n=$node -> { test:str=sc-dst $lib.model.migration.fuse($n, $node) }')

            for viewiden in (forka, forkb):
                self.len(0, await core.nodes('test:str=sc-src', opts={'view': viewiden}))
                self.len(0, await core.nodes('test:pivcomp=(sc-targ, sc-src)', opts={'view': viewiden}))
                nodes = await core.nodes('test:pivcomp=(sc-targ, sc-dst)', opts={'view': viewiden})
                self.len(1, nodes)
                self.eq('sc-dst', nodes[0].get('lulz'))

    async def test_stormlib_model_migration_fuse_toobig(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=deg-src :hehe=srcval +#degtag test:str=deg-dst ]')

            # a fuse is applied as a single nexus operation, so it cannot be flushed in
            # chunks. force the edit ceiling low enough that it must refuse.
            with mock.patch.object(s_nodefuse, 'maxlayeredits', 1):
                with self.raises(s_exc.BadArg) as cm:
                    await core.nodes(
                        'test:str=deg-src $n=$node -> { test:str=deg-dst $lib.model.migration.fuse($n, $node) }')

            self.isin('cannot be split into smaller batches', cm.exception.get('mesg'))

            # nothing was applied, so src is intact and dst did not gain anything
            self.len(1, await core.nodes('test:str=deg-src'))

            nodes = await core.nodes('test:str=deg-dst')
            self.len(1, nodes)
            self.none(nodes[0].get('hehe'))
            self.notin('degtag', nodes[0].tags)

            # under the ceiling it completes normally
            await core.nodes(
                'test:str=deg-src $n=$node -> { test:str=deg-dst $lib.model.migration.fuse($n, $node) }')

            self.len(0, await core.nodes('test:str=deg-src'))
            nodes = await core.nodes('test:str=deg-dst')
            self.len(1, nodes)
            self.eq('srcval', nodes[0].get('hehe'))
            self.isin('degtag', nodes[0].tags)

    async def test_stormlib_model_migration_fuse_single_nexus_op(self):

        async with self.getTestCore() as core:

            await core.nodes('''[
                test:str=atom-src :hehe=srcval +#atomtag
                test:str=atom-dst
            ]''')

            # fork so that the fuse writes to more than one layer
            vdef = await core.view.fork()
            forkopts = {'view': vdef.get('iden')}
            await core.nodes('test:str=atom-src [ :tick=2020 ]', opts=forkopts)

            # The whole fuse is a single nexus operation, no matter how many layers it writes
            # to. The nexus applies one operation at a time for the whole Cortex, so no other
            # write can land between the reads which compute the edits and the writes which
            # apply them. Note that this is isolation rather than atomicity: the edits are
            # still written one call per layer, so a failure part way through can leave some
            # layers updated.
            offs = await core.nexsroot.index()

            await core.nodes(
                'test:str=atom-src $n=$node -> { test:str=atom-dst $lib.model.migration.fuse($n, $node) }',
                opts=forkopts)

            self.eq(1, await core.nexsroot.index() - offs)

            self.len(0, await core.nodes('test:str=atom-src', opts=forkopts))

            nodes = await core.nodes('test:str=atom-dst', opts=forkopts)
            self.len(1, nodes)
            self.eq('srcval', nodes[0].get('hehe'))
            self.eq(s_time.parse('2020'), nodes[0].get('tick'))
            self.isin('atomtag', nodes[0].tags)

    async def test_stormlib_model_migration_fuse_nexus_mirror(self):

        # a fuse is applied as one nexus operation, which a mirror replays for itself, so the
        # mirror must end up with exactly the same state as the leader
        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')

            async with self.getTestCore(dirn=path00) as core00:
                pass

            s_tools_backup.backup(path00, path01)

            async with self.getTestCore(dirn=path00) as core00:

                await core00.nodes('''[
                    test:str=mir-src :hehe=srcval :somestr=mir-src +#mirtag=(2020, 2021)
                    test:str=mir-dst
                ]''')
                await core00.nodes('test:str=mir-src [ +(refs)> { test:str=mir-dst } ]')
                await core00.nodes('[ test:arrayprop="*" :strs=(mir-src,) ]')

                core01conf = {'mirror': core00.getLocalUrl()}

                async with self.getTestCore(dirn=path01, conf=core01conf) as core01:

                    await core01.sync()

                    await core00.nodes(
                        'test:str=mir-src $n=$node -> { test:str=mir-dst $lib.model.migration.fuse($n, $node) }')

                    await core01.sync()

                    for core in (core00, core01):

                        self.len(0, await core.nodes('test:str=mir-src'))

                        nodes = await core.nodes('test:str=mir-dst')
                        self.len(1, nodes)
                        self.eq('srcval', nodes[0].get('hehe'))
                        self.eq('mir-dst', nodes[0].get('somestr'))
                        self.isin('mirtag', nodes[0].tags)

                        # the edge from src to dst became a self edge on dst
                        edges = await core.nodes('test:str=mir-dst -(refs)> test:str')
                        self.len(1, edges)
                        self.eq(('test:str', 'mir-dst'), edges[0].ndef)

                        # the inbound array reference was rewritten
                        nodes = await core.nodes('test:arrayprop')
                        self.len(1, nodes)
                        self.eq(('mir-dst',), nodes[0].get('strs'))

    async def test_stormlib_model_migration_fuse_selfref_array(self):

        async with self.getTestCore() as core:

            # --- an array which references src has that entry repointed at dst ---

            opts = {'vars': {'src': 'arr-src', 'dst': 'arr-dst', 'other': 'arr-other'}}
            await core.nodes('[ test:str=$other test:str=$dst ]', opts=opts)
            await core.nodes('[ test:str=$src :ndefs=((test:str, $src), (test:str, $other)) ]', opts=opts)

            await core.nodes(
                'test:str=$src $n=$node -> { test:str=$dst $lib.model.migration.fuse($n, $node) }', opts=opts)

            self.len(0, await core.nodes('test:str=$src', opts=opts))

            nodes = await core.nodes('test:str=$dst', opts=opts)
            self.len(1, nodes)

            ndefs = nodes[0].get('ndefs')
            self.isin(('test:str', 'arr-dst'), ndefs)
            self.isin(('test:str', 'arr-other'), ndefs)
            self.notin(('test:str', 'arr-src'), ndefs)

            # --- an array which does not reference src is transferred unchanged ---

            opts = {'vars': {'src': 'arr2-src', 'dst': 'arr2-dst', 'other': 'arr-other'}}
            await core.nodes('[ test:str=$dst ]', opts=opts)
            await core.nodes('[ test:str=$src :ndefs=((test:str, $other),) ]', opts=opts)

            await core.nodes(
                'test:str=$src $n=$node -> { test:str=$dst $lib.model.migration.fuse($n, $node) }', opts=opts)

            self.len(0, await core.nodes('test:str=$src', opts=opts))

            nodes = await core.nodes('test:str=$dst', opts=opts)
            self.len(1, nodes)
            self.eq((('test:str', 'arr-other'),), nodes[0].get('ndefs'))

    async def test_stormlib_model_migration_fuse_selfedge(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=se-src test:str=se-dst ]')
            await core.nodes('test:str=se-src [ +(refs)> { test:str=se-src } ]')

            self.len(1, await core.nodes('test:str=se-src -(refs)> test:str'))

            await core.nodes(
                'test:str=se-src $n=$node -> { test:str=se-dst $lib.model.migration.fuse($n, $node) }')

            self.len(0, await core.nodes('test:str=se-src'))

            # src had an edge to itself, so dst has an edge to itself rather than a dangling
            # edge to the node which is now gone
            nodes = await core.nodes('test:str=se-dst -(refs)> test:str')
            self.len(1, nodes)
            self.eq(('test:str', 'se-dst'), nodes[0].ndef)

            self.len(0, await core.nodes('test:str -(refs)> test:str +test:str=se-src'))

    async def test_stormlib_model_migration_fuse_admin(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=perm-src :hehe=srcval test:str=perm-dst ]')

            user = await core.auth.addUser('fuser')

            # every node rule in the book is still not enough, fuse() writes to layers
            # well outside the scope of any single view
            await user.addRule((True, ('node',)))
            await user.addRule((True, ('view',)))

            opts = {'user': user.iden}

            with self.raises(s_exc.AuthDeny) as cm:
                await core.nodes(
                    'test:str=perm-src $n=$node -> { test:str=perm-dst $lib.model.migration.fuse($n, $node) }',
                    opts=opts)

            self.isin('requires global admin', cm.exception.get('mesg'))

            # nothing was changed
            self.len(1, await core.nodes('test:str=perm-src'))

            # an admin can do it
            await user.setAdmin(True)
            await core.nodes(
                'test:str=perm-src $n=$node -> { test:str=perm-dst $lib.model.migration.fuse($n, $node) }',
                opts=opts)

            self.len(0, await core.nodes('test:str=perm-src'))
            self.eq('srcval', (await core.nodes('test:str=perm-dst'))[0].get('hehe'))

    async def test_stormlib_model_migration_fuse_layers(self):

        async with self.getTestCore() as core:

            baselayr = core.getView().layers[0]

            await core.nodes('[ test:str=lyr-src :hehe=basehehe test:str=lyr-dst ]')

            vdef = await core.view.fork()
            forkiden = vdef.get('iden')
            forkopts = {'view': forkiden}
            forklayr = core.getView(forkiden).layers[0]

            # :tick, node data and an N1 light edge on src are written to the fork's write
            # layer, while src's primary property stays in the base layer. That leaves the
            # fork layer holding state for src without holding src itself.
            await core.nodes('[ test:str=lyr-other ]')
            await core.nodes('''
                test:str=lyr-src [ :tick=2020 +(refs)> { test:str=lyr-other } ]
                $node.data.set(forkkey, forkval)
            ''', opts=forkopts)

            await core.nodes(
                'test:str=lyr-src $n=$node -> { test:str=lyr-dst $lib.model.migration.fuse($n, $node) }',
                opts=forkopts)

            # --- Cortex wide: src is gone from the fork AND from the parent view ---
            self.len(0, await core.nodes('test:str=lyr-src', opts=forkopts))
            self.len(0, await core.nodes('test:str=lyr-src'))

            # --- Per layer placement: each prop stays in the layer it was stored in ---
            nodes = await core.nodes('test:str=lyr-dst', opts=forkopts)
            self.len(1, nodes)
            self.eq('basehehe', nodes[0].get('hehe'))
            self.eq(s_time.parse('2020'), nodes[0].get('tick'))
            self.eq(baselayr.iden, nodes[0].bylayer['props']['hehe'])
            self.eq(forklayr.iden, nodes[0].bylayer['props']['tick'])

            # the node data and light edge which lived in the fork layer moved to dst, and
            # were cleaned off src even though src's primary property was in another layer
            self.eq('forkval', await nodes[0].getData('forkkey'))
            self.len(1, await core.nodes('test:str=lyr-dst -(refs)> test:str', opts=forkopts))

            # the parent view only sees the prop which lives in the base layer
            nodes = await core.nodes('test:str=lyr-dst')
            self.len(1, nodes)
            self.eq('basehehe', nodes[0].get('hehe'))
            self.none(nodes[0].get('tick'))
            self.none(await nodes[0].getData('forkkey'))

    async def test_stormlib_model_migration_fuse_shared_layer(self):

        async with self.getTestCore() as core:

            baselayr = core.getView().layers[0]

            await core.nodes('[ test:str=shr-src :hehe=woot test:str=shr-dst ]')

            # three forks all sharing the one base layer
            for _ in range(3):
                await core.view.fork()

            self.len(3, core.viewsbylayer[baselayr.iden][1:])

            counts = collections.defaultdict(int)
            realsave = s_layer.Layer._storNodeEdits

            async def _storNodeEdits(self, nodeedits, meta, nexsitem):
                counts[self.iden] += 1
                return await realsave(self, nodeedits, meta, nexsitem)

            with mock.patch.object(s_layer.Layer, '_storNodeEdits', _storNodeEdits):
                await core.nodes(
                    'test:str=shr-src $n=$node -> { test:str=shr-dst $lib.model.migration.fuse($n, $node) }')

            # the shared base layer is written exactly once, not once per view. a layer records
            # its node edit log entry at the nexus offset it was applied at, so applying twice
            # within the one fuse operation would overwrite the first entry.
            self.eq(1, counts[baselayr.iden])

            self.len(0, await core.nodes('test:str=shr-src'))

    async def test_stormlib_model_migration_fuse_readonly(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=ro-src :hehe=basehehe test:str=ro-dst ]')

            vdef = await core.view.fork()
            forkiden = vdef.get('iden')
            forkopts = {'view': forkiden}
            forklayr = core.getView(forkiden).layers[0]

            await core.nodes('test:str=ro-src [ :tick=2020 ]', opts=forkopts)

            baselayr = core.getView().layers[0]
            await baselayr.setLayerInfo('readonly', True)

            mesgs = await core.stormlist(
                'test:str=ro-src $n=$node -> { test:str=ro-dst $lib.model.migration.fuse($n, $node) }',
                opts=forkopts)

            self.stormIsInWarn('because it is read only', mesgs)
            self.stormIsInWarn('will still be visible', mesgs)

            # the read only layer was not touched, so src survives there
            self.len(1, await core.nodes('test:str=ro-src'))
            self.eq('basehehe', (await core.nodes('test:str=ro-src'))[0].get('hehe'))

            # but the writable fork layer was fused, so src lost its fork-layer prop
            # and dst gained it
            nodes = await core.nodes('test:str=ro-dst', opts=forkopts)
            self.len(1, nodes)
            self.eq(s_time.parse('2020'), nodes[0].get('tick'))
            self.eq(forklayr.iden, nodes[0].bylayer['props']['tick'])

            await baselayr.setLayerInfo('readonly', False)

    async def test_stormlib_model_migration_fuse_mirror(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=mir-src :hehe=woot test:str=mir-dst ]')

            baselayr = core.getView().layers[0]

            # a mirrored layer would forward our edits upstream, so it is skipped
            baselayr.ismirror = True
            try:
                mesgs = await core.stormlist(
                    'test:str=mir-src $n=$node -> { test:str=mir-dst $lib.model.migration.fuse($n, $node) }')

                self.stormIsInWarn('because it is a mirror', mesgs)
                self.stormIsInWarn('will still be visible', mesgs)

            finally:
                baselayr.ismirror = False

            # nothing was changed
            self.len(1, await core.nodes('test:str=mir-src'))
            self.none((await core.nodes('test:str=mir-dst'))[0].get('hehe'))

    async def test_stormlib_model_migration_fuse_triggers(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=trig-src :hehe=srcval test:str=trig-dst ]')

            vdef = await core.view.fork()
            forkiden = vdef.get('iden')
            forkopts = {'view': forkiden}

            # a prop:set trigger in each view, writing to a different form
            tdef = {'cond': 'prop:set', 'prop': 'test:str:hehe', 'storm': '[ test:int=1000 ]'}
            await core.callStorm('return($lib.trigger.add($tdef))', opts={'vars': {'tdef': tdef}})

            tdef = {'cond': 'prop:set', 'prop': 'test:str:hehe', 'storm': '[ test:int=2000 ]'}
            await core.callStorm('return($lib.trigger.add($tdef))',
                                 opts={'vars': {'tdef': tdef}, 'view': forkiden})

            # a node:del trigger in the fork
            tdef = {'cond': 'node:del', 'form': 'test:str', 'storm': '[ test:int=3000 ]'}
            await core.callStorm('return($lib.trigger.add($tdef))',
                                 opts={'vars': {'tdef': tdef}, 'view': forkiden})

            await core.nodes(
                'test:str=trig-src $n=$node -> { test:str=trig-dst $lib.model.migration.fuse($n, $node) }')

            # each view's prop:set trigger fired, in its own view
            self.len(1, await core.nodes('test:int=1000'))
            self.len(0, await core.nodes('test:int=2000'))
            self.len(1, await core.nodes('test:int=2000', opts=forkopts))

            # the fork saw src disappear too, so its node:del trigger fired
            self.len(1, await core.nodes('test:int=3000', opts=forkopts))

    async def test_stormlib_model_migration_fuse_trigger_shadowed(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=shad-src :hehe=srcval test:str=shad-dst ]')

            vdef = await core.view.fork()
            forkiden = vdef.get('iden')
            forkopts = {'view': forkiden}

            # the fork's write layer already has its own :hehe on dst, which shadows
            # whatever the base layer holds
            await core.nodes('test:str=shad-dst [ :hehe=forkval ]', opts=forkopts)

            # NOTE: the triggers filter to dst. Deleting src also emits a prop del for its
            # :hehe, and a prop del fires prop:set handlers just as a delnode does, so an
            # unfiltered trigger would fire for src's teardown in every view.
            tdef = {'cond': 'prop:set', 'prop': 'test:str:hehe',
                    'storm': 'if ($node.value() = "shad-dst") { [ test:int=1000 ] }'}
            await core.callStorm('return($lib.trigger.add($tdef))', opts={'vars': {'tdef': tdef}})

            tdef = {'cond': 'prop:set', 'prop': 'test:str:hehe',
                    'storm': 'if ($node.value() = "shad-dst") { [ test:int=2000 ] }'}
            await core.callStorm('return($lib.trigger.add($tdef))',
                                 opts={'vars': {'tdef': tdef}, 'view': forkiden})

            await core.nodes(
                'test:str=shad-src $n=$node -> { test:str=shad-dst $lib.model.migration.fuse($n, $node) }')

            # src's :hehe was written to the base layer, so the base view observes dst
            # gaining it and its trigger fires
            self.len(1, await core.nodes('test:int=1000'))
            self.eq('srcval', (await core.nodes('test:str=shad-dst'))[0].get('hehe'))

            # the fork's own write layer still shadows that value, so from the fork dst
            # did not change and its trigger must not fire
            self.eq('forkval', (await core.nodes('test:str=shad-dst', opts=forkopts))[0].get('hehe'))
            self.len(0, await core.nodes('test:int=2000', opts=forkopts))

    async def test_stormlib_model_migration_fuse_trigger_nodeadd(self):

        async with self.getTestCore() as core:

            vdef = await core.view.fork()
            forkiden = vdef.get('iden')
            forkopts = {'view': forkiden}

            tdef = {'cond': 'node:add', 'form': 'test:str', 'storm': '[ test:int=1000 ]'}
            await core.callStorm('return($lib.trigger.add($tdef))', opts={'vars': {'tdef': tdef}})

            tdef = {'cond': 'node:add', 'form': 'test:str', 'storm': '[ test:int=2000 ]'}
            await core.callStorm('return($lib.trigger.add($tdef))',
                                 opts={'vars': {'tdef': tdef}, 'view': forkiden})

            # dst already exists in the base layer, so it is visible in both views and
            # no node:add is observable anywhere
            await core.nodes('[ test:str=na-src :hehe=woot test:str=na-dst ]')

            await core.nodes('test:int | delnode')
            await core.nodes('test:int | delnode', opts=forkopts)

            await core.nodes(
                'test:str=na-src $n=$node -> { test:str=na-dst $lib.model.migration.fuse($n, $node) }')

            self.len(0, await core.nodes('test:int=1000'))
            self.len(0, await core.nodes('test:int=2000', opts=forkopts))

    async def test_stormlib_model_migration_fuse_recovery(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=rec-src :hehe=srcval +#rectag test:str=rec-dst ]')

            q = 'test:str=rec-src $n=$node -> { test:str=rec-dst $lib.model.migration.fuse($n, $node) }'

            # --- a layer which fails is warned about and then raises ---
            async def badsave(self, nodeedits, meta, nexsitem):
                raise s_exc.SynErr(mesg='layer go boom')

            with mock.patch.object(s_layer.Layer, '_storNodeEdits', badsave):
                mesgs = await core.stormlist(q)

            self.stormIsInWarn('failed to apply edits to layer', mesgs)
            self.stormIsInErr('failed to apply edits to some layers', mesgs)

            # nothing was applied
            self.len(1, await core.nodes('test:str=rec-src'))
            self.none((await core.nodes('test:str=rec-dst'))[0].get('hehe'))

            # --- re-running completes it ---
            await core.nodes(q)

            self.len(0, await core.nodes('test:str=rec-src'))
            nodes = await core.nodes('test:str=rec-dst')
            self.len(1, nodes)
            self.eq('srcval', nodes[0].get('hehe'))
            self.isin('rectag', nodes[0].tags)

            # --- running it again is a clean no-op ---
            mesgs = await core.stormlist(q)
            self.stormNotInWarn('failed to apply edits', mesgs)

            self.len(0, await core.nodes('test:str=rec-src'))
            self.eq('srcval', (await core.nodes('test:str=rec-dst'))[0].get('hehe'))

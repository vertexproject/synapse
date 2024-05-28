import synapse.exc as s_exc
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

                with self.getAsyncLoggerStream('synapse.lib.snap',
                                               'Prop ou:org:sic is locked due to deprecation') as stream:
                    data = (
                        (('ou:org', ('t0',)), {'props': {'sic': '5678'}}),
                    )
                    await core.addFeedData('syn.nodes', data)
                    self.true(await stream.wait(1))
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

    async def test_model_migration_s_itSecCpe_2_170_0(self):

        async with self.getRegrCore('itSecCpe_2_170_0') as core:
            # Migrate it:sec:cpe nodes with a valid CPE2.3, valid CPE2.2
            q = 'it:sec:cpe +#test.cpe.23valid +#test.cpe.22valid'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            self.eq(
                [
                    ('it:sec:cpe', 'cpe:2.3:a:abine:donottrackme_-_mobile_privacy:1.1.8:*:*:*:*:android:*:*'),
                    ('it:sec:cpe', 'cpe:2.3:a:01generator:pireospay:-:*:*:*:*:prestashop:*:*')
                ],
                [node.ndef for node in nodes]
            )

            q = '''
            it:sec:cpe +#test.cpe.23valid +#test.cpe.22valid
            $lib.debug=$lib.true
            $lib.model.migration.s.itSecCpe_2_170_0($node)
            $node.data.load(migration.s.itSecCpe_2_170_0)
            '''
            nodes = await core.nodes(q)

            data = nodes[0].nodedata['migration.s.itSecCpe_2_170_0']
            self.nn(data)
            self.eq(data['status'], 'success')
            self.none(data.get('reason'))

            data = nodes[1].nodedata['migration.s.itSecCpe_2_170_0']
            self.nn(data)
            self.eq(data['status'], 'success')
            self.none(data.get('reason'))

        async with self.getRegrCore('itSecCpe_2_170_0') as core:
            # Migrate it:sec:cpe nodes with a valid CPE2.3, invalid CPE2.2
            q = '''
            it:sec:cpe +#test.cpe.23valid +#test.cpe.22invalid
            $lib.debug=$lib.true
            $lib.model.migration.s.itSecCpe_2_170_0($node)
            '''
            nodes = await core.nodes(q)
            self.len(3, nodes)
            self.eq(
                [
                    ('it:sec:cpe', 'cpe:2.3:a:1c:1c\\:enterprise:-:*:*:*:*:*:*:*'),
                    ('it:sec:cpe', 'cpe:2.3:o:zyxel:nas542_firmware:5.21\\%28aazf.15\\%29co:*:*:*:*:*:*:*'),
                    ('it:sec:cpe', 'cpe:2.3:a:abinitio:control\\>center:-:*:*:*:*:*:*:*'),
                ],
                [node.ndef for node in nodes]
            )

            q = '''
            it:sec:cpe +#test.cpe.23valid +#test.cpe.22invalid
            $node.data.load(migration.s.itSecCpe_2_170_0)
            '''
            nodes = await core.nodes(q)
            self.len(3, nodes)

            data = nodes[0].nodedata['migration.s.itSecCpe_2_170_0']
            self.nn(data)
            self.eq(data['status'], 'success')
            self.eq(data['updated'], ['v2_2', 'product'])
            self.eq(nodes[0].get('v2_2'), 'cpe:/a:1c:1c%3aenterprise:-')
            self.eq(nodes[0].get('product'), '1c:enterprise')

            data = nodes[1].nodedata['migration.s.itSecCpe_2_170_0']
            self.nn(data)
            self.eq(data['status'], 'success')
            self.none(data.get('valu'))
            self.eq(data['updated'], ['v2_2', 'version'])
            self.eq(nodes[1].get('v2_2'), 'cpe:/o:zyxel:nas542_firmware:5.21%2528aazf.15%2529co')
            self.eq(nodes[1].get('version'), '5.21%28aazf.15%29co')

            data = nodes[2].nodedata['migration.s.itSecCpe_2_170_0']
            self.nn(data)
            self.eq(data['status'], 'success')
            self.eq(data['updated'], ['v2_2', 'product'])
            self.eq(nodes[2].get('v2_2'), 'cpe:/a:abinitio:control%3ecenter:-')
            self.eq(nodes[2].get('product'), 'control>center')

            # The migration of this node was not correct because the CPE2.3 string (primary property) is valid but was
            # not created correctly due to a bad CPE2.2 input value. Now we update :v2_2 to be correct, and re-run the
            # migration. This time, we specify `prefer_v22=True` and `force=True` so the migration will use the updated
            # :v2_2 prop for reparsing the strings. Force will cause the migration to continue past the check where both
            # the primary property and :v2_2 are valid.
            q = '''
            it:sec:cpe:product=nas542_firmware [ :v2_2="cpe:/o:zyxel:nas542_firmware:5.21%28aazf.15%29co" ]
            $lib.debug=$lib.true
            $lib.model.migration.s.itSecCpe_2_170_0($node, prefer_v22=$lib.true, force=$lib.true)
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)

            # Lift the updated node and check the migration did what was expected.
            q = '''
            it:sec:cpe:product=nas542_firmware
            $node.data.load(migration.s.itSecCpe_2_170_0)
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)

            data = nodes[0].nodedata['migration.s.itSecCpe_2_170_0']
            self.nn(data)
            self.eq(data['status'], 'success')
            self.eq(data['updated'], ['version'])
            self.eq(data['valu'], 'cpe:2.3:o:zyxel:nas542_firmware:5.21\\(aazf.15\\)co:*:*:*:*:*:*:*')
            self.eq(nodes[0].get('v2_2'), 'cpe:/o:zyxel:nas542_firmware:5.21%28aazf.15%29co')
            self.eq(nodes[0].get('version'), '5.21(aazf.15)co')

        async with self.getRegrCore('itSecCpe_2_170_0') as core:
            # Migrate it:sec:cpe nodes with a invalid CPE2.3, valid CPE2.2
            q = '''
            it:sec:cpe +#test.cpe.23invalid +#test.cpe.22valid
            $lib.debug=$lib.true
            $lib.model.migration.s.itSecCpe_2_170_0($node)
            '''
            nodes = await core.nodes(q)
            self.len(4, nodes)
            self.eq(
                [
                    ('it:sec:cpe', 'cpe:2.3:h:d\\-link:dir\\-850l:*:*:*:*:*:*:*:*'),
                    ('it:sec:cpe', 'cpe:2.3:a:acurax:under_construction_%2f_maintenance_mode:-::~~~wordpress~~:*:*:*:*:*'),
                    ('it:sec:cpe', 'cpe:2.3:a:10web:social_feed_for_instagram:1.0.0::~~premium~wordpress~~:*:*:*:*:*'),
                    ('it:sec:cpe', 'cpe:2.3:o:zyxel:nas326_firmware:5.21%28aazf.14%29c0:*:*:*:*:*:*:*'),
                ],
                [node.ndef for node in nodes]
            )

            q = '''
            it:sec:cpe +#test.cpe.23invalid +#test.cpe.22valid
            $node.data.load(migration.s.itSecCpe_2_170_0)
            '''
            nodes = await core.nodes(q)
            self.len(4, nodes)

            data = nodes[0].nodedata['migration.s.itSecCpe_2_170_0']
            self.nn(data)
            self.eq(data['status'], 'success')
            self.eq(data['updated'], ['vendor', 'product'])
            self.eq(data['valu'], 'cpe:2.3:h:d-link:dir-850l:*:*:*:*:*:*:*:*')
            self.eq(nodes[0].get('vendor'), 'd-link')
            self.eq(nodes[0].get('product'), 'dir-850l')

            data = nodes[1].nodedata['migration.s.itSecCpe_2_170_0']
            self.nn(data)
            self.eq(data['status'], 'success')
            self.eq(data['updated'], ['product', 'update', 'edition', 'target_sw'])
            self.eq(data['valu'], 'cpe:2.3:a:acurax:under_construction_\\/_maintenance_mode:-:*:*:*:*:wordpress:*:*')
            self.eq(nodes[1].get('product'), 'under_construction_/_maintenance_mode')
            self.eq(nodes[1].get('update'), '*')
            self.eq(nodes[1].get('edition'), '*')
            self.eq(nodes[1].get('target_sw'), 'wordpress')

            data = nodes[2].nodedata['migration.s.itSecCpe_2_170_0']
            self.nn(data)
            self.eq(data['status'], 'success')
            self.eq(data['updated'], ['update', 'edition', 'sw_edition', 'target_sw'])
            self.eq(data['valu'], 'cpe:2.3:a:10web:social_feed_for_instagram:1.0.0:*:*:*:premium:wordpress:*:*')
            self.eq(nodes[2].get('update'), '*')
            self.eq(nodes[2].get('edition'), '*')
            self.eq(nodes[2].get('sw_edition'), 'premium')
            self.eq(nodes[2].get('target_sw'), 'wordpress')

            data = nodes[3].nodedata['migration.s.itSecCpe_2_170_0']
            self.nn(data)
            self.eq(data['status'], 'success')
            self.eq(data['updated'], ['version'])
            self.eq(data['valu'], 'cpe:2.3:o:zyxel:nas326_firmware:5.21\\(aazf.14\\)c0:*:*:*:*:*:*:*')
            self.eq(nodes[3].get('version'), '5.21(aazf.14)c0')

        async with self.getRegrCore('itSecCpe_2_170_0') as core:
            # Migrate it:sec:cpe nodes with a invalid CPE2.3, invalid CPE2.2
            q = '''
            it:sec:cpe +#test.cpe.23invalid +#test.cpe.22invalid
            $lib.debug=$lib.true
            $lib.model.migration.s.itSecCpe_2_170_0($node)
            '''
            msgs = await core.stormlist(q)
            mesg = 'itSecCpe_2_170_0(it:sec:cpe=cpe:2.3:a:openbsd:openssh:8.2p1 ubuntu-4ubuntu0.2:*:*:*:*:*:*:*): '
            mesg += 'Unable to migrate due to invalid data. Primary property and :v2_2 are both invalid.'
            self.stormIsInWarn(mesg, msgs)

            ndefs = [m[1][0] for m in msgs if m[0] == 'node']
            self.eq(
                [
                    ('it:sec:cpe', 'cpe:2.3:a:openbsd:openssh:7.4\r\n:*:*:*:*:*:*:*'),
                    ('it:sec:cpe', 'cpe:2.3:a:openbsd:openssh:8.2p1 ubuntu-4ubuntu0.2:*:*:*:*:*:*:*')
                ],
                ndefs
            )

            q = '''
            it:sec:cpe +#test.cpe.23invalid +#test.cpe.22invalid
            $node.data.load(migration.s.itSecCpe_2_170_0)
            '''
            nodes = await core.nodes(q)
            self.len(2, nodes)

            for node in nodes:
                data = node.nodedata['migration.s.itSecCpe_2_170_0']
                self.eq(data, {
                    'status': 'failed',
                    'reason': 'Unable to migrate due to invalid data. Primary property and :v2_2 are both invalid.',
                })

            # Now update the :v2_2 on one of the nodes and migrate again
            q = '''
            it:sec:cpe:version^=8.2p1 [ :v2_2="cpe:/a:openbsd:openssh:8.2p1_ubuntu-4ubuntu0.2" ]
            $lib.debug=$lib.true
            $lib.model.migration.s.itSecCpe_2_170_0($node)
            '''
            msgs = await core.stormlist(q)
            self.stormHasNoWarnErr(msgs)

            q = '''
            it:sec:cpe:version^=8.2p1
            $node.data.load(migration.s.itSecCpe_2_170_0)
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)

            data = nodes[0].nodedata['migration.s.itSecCpe_2_170_0']
            self.nn(data)
            self.eq(data['status'], 'success')
            self.eq(data['updated'], ['version'])
            self.eq(data['valu'], 'cpe:2.3:a:openbsd:openssh:8.2p1_ubuntu-4ubuntu0.2:*:*:*:*:*:*:*')
            self.eq(nodes[0].get('version'), '8.2p1_ubuntu-4ubuntu0.2')

            # Run the migration again to make sure we identify already migrated
            # nodes correctly and bail early.
            q = '''
            it:sec:cpe:version^=8.2p1
            $lib.debug=$lib.true
            $lib.model.migration.s.itSecCpe_2_170_0($node)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint(f'DEBUG: itSecCpe_2_170_0(it:sec:cpe=cpe:2.3:a:openbsd:openssh:8.2p1 ubuntu-4ubuntu0.2:*:*:*:*:*:*:*): Node already migrated.', msgs)

            q = '''
            it:sec:cpe:version^=8.2p1
            $lib.debug=$lib.true
            $lib.model.migration.s.itSecCpe_2_170_0($node, force=$lib.true)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint(f'DEBUG: itSecCpe_2_170_0(it:sec:cpe=cpe:2.3:a:openbsd:openssh:8.2p1 ubuntu-4ubuntu0.2:*:*:*:*:*:*:*): No property updates required.', msgs)

        async with self.getTestCore() as core:
            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.model.migration.s.itSecCpe_2_170_0(newp)')

            with self.raises(s_exc.BadArg):
                await core.callStorm('[ inet:fqdn=vertex.link ] $lib.model.migration.s.itSecCpe_2_170_0($node)')

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

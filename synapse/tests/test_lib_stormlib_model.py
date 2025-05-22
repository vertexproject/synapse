import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.time as s_time
import synapse.lib.layer as s_layer

import synapse.tests.utils as s_test

class StormlibModelTest(s_test.SynTest):

    async def test_stormlib_model_basics(self):

        async with self.getTestCore() as core:

            q = '$val = $lib.model.type(inet:ip).repr(([4, 42])) [test:str=$val]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', '0.0.0.42'))

            q = '$val = $lib.model.type(bool).repr(1) [test:str=$val]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'true'))

            self.eq('inet:dns:a', await core.callStorm('return($lib.model.form(inet:dns:a).type.name)'))
            self.eq('inet:ip', await core.callStorm('return($lib.model.prop(inet:dns:a:ip).type.name)'))
            self.eq(s_layer.STOR_TYPE_IPADDR, await core.callStorm('return($lib.model.prop(inet:dns:a:ip).type.stortype)'))
            self.eq('inet:dns:a', await core.callStorm('return($lib.model.type(inet:dns:a).name)'))

            self.eq('1.2.3.4', await core.callStorm('return($lib.model.type(inet:ip).repr(([4, $(0x01020304)])))'))
            self.eq('123', await core.callStorm('return($lib.model.type(int).repr((1.23 *100)))'))
            self.eq((123, {}), await core.callStorm('return($lib.model.type(int).norm((1.23 *100)))'))
            self.eq((4, 0x01020304), await core.callStorm('return($lib.model.type(inet:ip).norm(1.2.3.4).index(0))'))
            self.eq({'subs': {'type': 'unicast', 'version': 4}}, await core.callStorm('return($lib.model.type(inet:ip).norm(1.2.3.4).index(1))'))
            self.eq('inet:dns:a:ip', await core.callStorm('return($lib.model.form(inet:dns:a).prop(ip).full)'))
            self.eq('inet:dns:a', await core.callStorm('return($lib.model.prop(inet:dns:a:ip).form.name)'))

            await core.addTagProp('score', ('int', {}), {})
            self.eq('score', await core.callStorm('return($lib.model.tagprop(score).name)'))
            self.eq('int', await core.callStorm('return($lib.model.tagprop(score).type.name)'))

            self.eq('risk:attack', await core.callStorm('return($lib.model.edge(risk:attack, used, risk:vuln).n1form)'))
            self.eq('used', await core.callStorm('return($lib.model.edge(risk:attack, used, risk:vuln).verb)'))
            self.eq('risk:vuln', await core.callStorm('return($lib.model.edge(risk:attack, used, risk:vuln).n2form)'))
            self.none(await core.callStorm('return($lib.model.edge(risk:attack, newp, risk:vuln))'))

            self.true(await core.callStorm('return(($lib.model.prop(".created").form = $lib.null))'))

            mesgs = await core.stormlist('$lib.print($lib.model.form(meta:name))')
            self.stormIsInPrint("model:form: {'name': 'meta:name'", mesgs)

            mesgs = await core.stormlist('$lib.pprint($lib.model.form(meta:name))')
            self.stormIsInPrint("{'name': 'meta:name'", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.model.form(meta:name).type)')
            self.stormIsInPrint("model:type: ('meta:name'", mesgs)

            mesgs = await core.stormlist('$lib.pprint($lib.model.form(meta:name).type)')
            self.stormIsInPrint("('meta:name'", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.model.prop(entity:contact:name))')
            self.stormIsInPrint("model:property: {'name': 'name'", mesgs)

            mesgs = await core.stormlist('$lib.pprint($lib.model.prop(entity:contact:name))')
            self.stormIsInPrint("'type': ('meta:name'", mesgs)

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

            mesgs = await core.stormlist('$lib.print($lib.model.edge(risk:attack, used, risk:vuln))')
            self.stormIsInPrint("model:edge: (('risk:attack', 'used', 'risk:vuln'), {'doc':", mesgs)

            mesgs = await core.stormlist('$lib.pprint($lib.model.edge(risk:attack, used, risk:vuln))')
            self.stormIsInPrint("(('risk:attack', 'used', 'risk:vuln'),\n {'doc':", mesgs)

    async def test_stormlib_model_depr(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                await core._addDataModels(s_test.deprmodel)

                # create both a deprecated form and a node with a deprecated prop
                await core.nodes('[ test:deprform=* :deprprop2=foo test:deprprop=baz ]')

                with self.raises(s_exc.NoSuchProp):
                    await core.nodes('model.deprecated.lock newp:newp')

                # lock a prop and a form/type
                await core.nodes('model.deprecated.lock test:deprform:deprprop2')
                await core.nodes('model.deprecated.lock test:deprprop')

                with self.raises(s_exc.IsDeprLocked):
                    await core.nodes('test:deprform [ :deprprop2=baz ]')

                with self.raises(s_exc.IsDeprLocked):
                    await core.nodes('[test:deprprop=newp]')

                with self.getAsyncLoggerStream('synapse.lib.view',
                                               'Prop test:deprform:deprprop2 is locked due to deprecation') as stream:
                    data = (
                        (('test:deprform', 'depr'), {'props': {'deprprop2': '5678'}}),
                    )
                    await core.addFeedData(data)
                    self.true(await stream.wait(1))
                    nodes = await core.nodes('test:deprform=depr')
                    self.none(nodes[0].get('deprprop2'))

                mesgs = await core.stormlist('model.deprecated.locks')
                self.stormIsInPrint('test:deprform:deprprop2: true', mesgs)
                self.stormIsInPrint('test:deprprop: true', mesgs)
                self.stormIsInPrint('test:deprform2: false', mesgs)

                await core.nodes('model.deprecated.lock --unlock test:deprform:deprprop2')
                await core.nodes('test:deprform [ :deprprop2=bar ]')
                await core.nodes('model.deprecated.lock test:deprform:deprprop2')

            # ensure that the locks persisted and got loaded correctly
            async with self.getTestCore(dirn=dirn) as core:

                await core._addDataModels(s_test.deprmodel)

                mesgs = await core.stormlist('model.deprecated.check')
                # warn due to unlocked
                self.stormIsInWarn('test:deprform2', mesgs)
                # warn due to existing
                self.stormIsInWarn('test:deprform:deprprop2', mesgs)
                self.stormIsInWarn('test:deprprop', mesgs)
                self.stormIsInPrint('Your cortex contains deprecated model elements', mesgs)

                await core.nodes('model.deprecated.lock *')

                mesgs = await core.stormlist('model.deprecated.locks')
                self.stormIsInPrint('test:deprform2: true', mesgs)

                await core.nodes('test:deprform [ -:deprprop2 ]')
                await core.nodes('test:deprprop | delnode')

                mesgs = await core.stormlist('model.deprecated.check')
                self.stormIsInPrint('Congrats!', mesgs)

    async def test_stormlib_model_depr_check(self):

        async with self.getTestCore() as core:

            await core._addDataModels(s_test.deprmodel)

            mesgs = await core.stormlist('model.deprecated.check')

            self.stormIsInWarn('.pdep is not yet locked', mesgs)
            self.stormNotInWarn('test:dep:easy.pdep is not yet locked', mesgs)

    async def test_stormlib_model_migration(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ test:str=src test:str=dst test:str=deny test:str=other ]')
            othernid = nodes[3].nid

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
                [ <(refs)+ { test:str=other } +(refs)> { test:str=other } ]
                $n=$node -> {
                    test:str=dst
                    $lib.model.migration.copyEdges($n, $node)
                }
            ''')
            self.len(1, nodes)
            self.eq([('refs', othernid)], [edge async for edge in nodes[0].iterEdgesN1()])
            self.eq([('refs', othernid)], [edge async for edge in nodes[0].iterEdgesN2()])

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

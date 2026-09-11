import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.time as s_time
import synapse.lib.layer as s_layer
import synapse.lib.nodefuse as s_nodefuse

import synapse.tests.utils as s_test

from unittest import mock

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
            self.eq('inet:ip', await core.callStorm('return($lib.model.prop(inet:dns:a:ip).types.0.name)'))
            self.eq(s_layer.STOR_TYPE_IPADDR, await core.callStorm('return($lib.model.prop(inet:dns:a:ip).types.0.stortype)'))
            self.eq('inet:dns:a', await core.callStorm('return($lib.model.type(inet:dns:a).name)'))

            self.eq('1.2.3.4', await core.callStorm('return($lib.model.type(inet:ip).repr(([4, $(0x01020304)])))'))
            self.eq('123', await core.callStorm('return($lib.model.type(int).repr((1.23 *100)))'))
            self.eq((123, {}), await core.callStorm('return($lib.model.type(int).norm((1.23 *100)))'))
            self.eq((4, 0x01020304), await core.callStorm('return($lib.model.type(inet:ip).norm(1.2.3.4).index(0))'))
            self.eq('inet:dns:a:ip', await core.callStorm('return($lib.model.form(inet:dns:a).prop(ip).full)'))
            self.eq('inet:dns:a', await core.callStorm('return($lib.model.prop(inet:dns:a:ip).form.name)'))

            styp = core.model.type('str').typehash
            ityp = core.model.type('int').clone({'enums': ((4, '4'), (6, '6'))}).typehash

            exp = {'subs': {'type': (styp, 'unicast', {}), 'version': (ityp, 4, {})}}
            self.eq(exp, await core.callStorm('return($lib.model.type(inet:ip).norm(1.2.3.4).index(1))'))

            await core.addTagProp('_score', ('int', {}), {})
            self.eq('_score', await core.callStorm('return($lib.model.tagprop(_score).name)'))
            self.eq('int', await core.callStorm('return($lib.model.tagprop(_score).type.name)'))

            self.eq('entity:action', await core.callStorm('return($lib.model.edge(risk:attack, used, risk:vuln).n1form)'))
            self.eq('used', await core.callStorm('return($lib.model.edge(risk:attack, used, risk:vuln).verb)'))
            self.eq('meta:usable', await core.callStorm('return($lib.model.edge(risk:attack, used, risk:vuln).n2form)'))
            self.none(await core.callStorm('return($lib.model.edge(risk:attack, newp, risk:vuln))'))

            self.true(await core.callStorm('return(($lib.model.prop(".created").form = null))'))

            mesgs = await core.stormlist('$lib.print($lib.model.form(entity:name))')
            self.stormIsInPrint("model:form: {'name': 'entity:name'", mesgs)

            mesgs = await core.stormlist('$lib.pprint($lib.model.form(entity:name))')
            self.stormIsInPrint("{'name': 'entity:name'", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.model.form(entity:name).type)')
            self.stormIsInPrint("model:type: ('entity:name'", mesgs)

            mesgs = await core.stormlist('$lib.pprint($lib.model.form(entity:name).type)')
            self.stormIsInPrint("('entity:name'", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.model.prop(entity:contact:name))')
            self.stormIsInPrint("model:property: {'name': 'name'", mesgs)

            mesgs = await core.stormlist('$lib.pprint($lib.model.prop(entity:contact:name))')
            self.stormIsInPrint("{'types': ('entity:name',)}", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.model.tagprop(_score))')
            self.stormIsInPrint("model:tagprop: {'name': '_score'", mesgs)

            mesgs = await core.stormlist('$lib.pprint($lib.model.tagprop(_score))')
            self.stormIsInPrint("'name': '_score'", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.model.type(int))')
            self.stormIsInPrint("model:type: ('int', ('base'", mesgs)

            mesgs = await core.stormlist("$item=$lib.model.tagprop('_score') $lib.pprint($item.type)")
            self.stormIsInPrint("('int',\n ('base',", mesgs)

            mesgs = await core.stormlist("$item=$lib.model.tagprop('_score') $lib.print($item.type)")
            self.stormIsInPrint("model:type: ('int', ('base'", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.model.edge(risk:attack, used, risk:vuln))')
            self.stormIsInPrint("model:edge: (('entity:action', 'used', 'meta:usable'), {'doc':", mesgs)

            self.false(await core.callStorm('return($lib.model.type(int).mutable)'))
            self.false(await core.callStorm('return($lib.model.type(str).mutable)'))
            self.true(await core.callStorm('return($lib.model.type(data).mutable)'))
            self.true(await core.callStorm('return($lib.model.type(array).mutable)'))

            props = await core.callStorm('return($lib.model.form(test:str).props)')
            self.isin('poly', props)

            mesgs = await core.stormlist('$lib.print($lib.model.form(test:str).props.poly)')
            self.stormIsInPrint("model:property: {'name': 'poly'", mesgs)

            mesgs = await core.stormlist('for ($k, $v) in $lib.model.form(test:str).props { $lib.print(`{$k} {$v}`) }')
            self.stormIsInPrint("poly model:property: {'name': 'poly'", mesgs)

            self.true(await core.callStorm('return(("poly" in $lib.model.form(test:str).props))'))
            self.false(await core.callStorm('return(("newp" in $lib.model.form(test:str).props))'))

            types = await core.callStorm('return($lib.model.form(test:str).props.poly.types)')
            types = [tdef[0] for tdef in types]
            self.isin('test:int', types)
            self.isin('test:hasiface', types)

            types = await core.callStorm('return($lib.model.form(test:str).props.polyarry.types)')
            types = [tdef[0] for tdef in types]
            self.isin('test:int', types)
            self.isin('test:hasiface', types)

            self.len(1, await core.callStorm('return($lib.model.form(test:str).props.hehe.types)'))

            self.true(await core.callStorm('return($lib.model.form(test:comp).props.hehe.computed)'))
            self.false(await core.callStorm('return($lib.model.form(test:hugenum).props.huge.computed)'))

    async def test_stormlib_model_depr(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                await core._addModelDefs(s_test.deprmodel)

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

                with self.getLoggerStream('synapse.lib.view') as stream:
                    data = (
                        (('test:deprform', 'depr'), {'props': {'deprprop2': ('5678', {'t': 'test:str'})}}),
                    )
                    await core.addFeedData(data)
                    await stream.expect('Prop test:deprform:deprprop2 is locked due to deprecation', timeout=1)
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

                await core._addModelDefs(s_test.deprmodel)

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

            await core._addModelDefs(s_test.deprmodel)

            mesgs = await core.stormlist('model.deprecated.check')

            self.stormIsInWarn(':pdep is not yet locked', mesgs)
            self.stormNotInWarn('test:dep:easy:pdep is not yet locked', mesgs)

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
                    $lib.model.migration.copyData($n, $node, overwrite=(true))
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

            await core.nodes('$lib.model.ext.addTagProp(_test, (str, ({})), ({}))')

            nodes = await core.nodes('''
                test:str=src
                [ +#foo=(2010, 2012) +#foo.bar +#baz:_test=src ]
                $n=$node -> {
                    test:str=dst
                    [ +#foo=(2010, 2011) +#baz:_test=dst ]
                    $lib.model.migration.copyTags($n, $node)
                }
            ''')
            self.len(1, nodes)
            self.sorteq([
                ('baz', (None, None, None)),
                ('foo', (s_time.parse('2010'), s_time.parse('2012'), 63072000000000)),
                ('foo.bar', (None, None, None))
            ], nodes[0].getTags())
            self.eq([], nodes[0].getTagProps('foo'))
            self.eq([], nodes[0].getTagProps('foo.bar'))
            self.eq([('_test', 'dst')], [(k, nodes[0].getTagProp('baz', k)) for k in nodes[0].getTagProps('baz')])

            nodes = await core.nodes('''
                test:str=src $n=$node -> {
                    test:str=dst
                    $lib.model.migration.copyTags($n, $node, overwrite=(true))
                }
            ''')
            self.len(1, nodes)
            self.eq([('_test', 'src')], [(k, nodes[0].getTagProp('baz', k)) for k in nodes[0].getTagProps('baz')])

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
            self.propeq(nodes[0], '_foo', 'foobarbaz')

    async def test_stormlib_model_migration_fuse(self):

        fuse = 'test:str=$src $n=$node -> { test:str=$dst $lib.model.migration.fuse($n, $node) }'

        async with self.getTestCore() as core:

            # --- Validation errors ---

            await core.nodes('[ test:str=v-src test:str=v-dst ]')

            await self.asyncraises(s_exc.BadArg,
                core.nodes('test:str=v-src $lib.model.migration.fuse($node, newp)'))

            await self.asyncraises(s_exc.BadArg,
                core.nodes('test:str=v-src $lib.model.migration.fuse(newp, $node)'))

            # src and dst must share a form or an inheritance chain
            guidval = s_common.guid()
            opts = {'vars': {'guidval': guidval}}
            await core.nodes('[ test:guid=$guidval ]', opts=opts)
            await self.asyncraises(s_exc.BadArg,
                core.nodes('test:str=v-src $n=$node -> { test:guid=$guidval '
                           '$lib.model.migration.fuse($n, $node) }', opts=opts))

            # runt forms are refused from either side, and are reported as runt rather than
            # as a form mismatch even when the other side is not a runt form at all
            await self.asyncraises(s_exc.IsRuntForm,
                core.nodes('syn:form=test:str $n=$node -> { syn:form=test:int '
                           '$lib.model.migration.fuse($n, $node) }'))

            await self.asyncraises(s_exc.IsRuntForm,
                core.nodes('syn:form=test:str $n=$node -> { test:str=v-src '
                           '$lib.model.migration.fuse($n, $node) }'))

            await self.asyncraises(s_exc.IsRuntForm,
                core.nodes('test:str=v-src $n=$node -> { syn:form=test:str '
                           '$lib.model.migration.fuse($n, $node) }'))

            # a self fuse warns and no-ops
            mesgs = await core.stormlist('test:str=v-src $lib.model.migration.fuse($node, $node)')
            self.stormIsInWarn('src and dst are the same node', mesgs)
            self.len(1, await core.nodes('test:str=v-src'))

            # --- Basic happy path ---

            await core.addTagProp('_tp', ('str', {}), {})
            await core.addFormProp('test:str', '_efoo', ('str', {}), {})

            opts = {'vars': {'src': 'hp-src', 'dst': 'hp-dst'}}

            await core.nodes('''
                [ test:str=$src
                    :hehe=srcval
                    :tick=2020
                    :seen=(2010, 2020)
                    +#foo.bar=(2015, 2016)
                    +#foo.bar:_tp=src-tp
                    +#src.only
                    :_efoo=srcext
                ]
                $node.data.set(k1, src-k1)
                $node.data.set(k2, src-k2)
            ''', opts=opts)

            await core.nodes('''
                [ test:str=$dst
                    :hehe=dstval
                    :tick=2019
                    :seen=(2015, 2025)
                    +#foo.bar=(2018, 2022)
                    +#foo.bar:_tp=dst-tp
                    +#dst.only
                    :_efoo=dstext
                ]
                $node.data.set(k1, dst-k1)
                $node.data.set(k3, dst-k3)
            ''', opts=opts)

            dstcreated = (await core.nodes('test:str=$dst', opts=opts))[0].getMeta('created')
            self.nn(dstcreated)

            # set up N1 and N2 edges on src
            await core.nodes('[ test:str=hp-other ]')
            await core.nodes('test:str=$src [ +(refs)> { test:str=hp-other } ]', opts=opts)
            await core.nodes('test:str=hp-other [ +(refs)> { test:str=$src } ]', opts=opts)

            await core.nodes(fuse, opts=opts)

            # src is deleted
            self.len(0, await core.nodes('test:str=$src', opts=opts))

            nodes = await core.nodes('test:str=$dst', opts=opts)
            self.len(1, nodes)
            dst = nodes[0]

            # secondary props: dst wins on conflict, since dst is the survivor
            self.propeq(dst, 'hehe', 'dstval')
            self.propeq(dst, 'tick', s_time.parse('2019'))

            # .created is node meta and min merges, so dst keeps the earlier of the two
            self.eq(dstcreated, dst.getMeta('created'))

            # an ival typed prop merges rather than having one value win:
            # (min(2010,2015), max(2020,2025)). Node.get() returns a typed value, so the
            # interval itself is the second element.
            (_, seen) = dst.get('seen')
            self.eq(s_time.parse('2010'), seen[0])
            self.eq(s_time.parse('2025'), seen[1])

            # tags: both sets present
            tags = dict(dst.getTags())
            self.isin('foo.bar', tags)
            self.isin('dst.only', tags)
            self.isin('src.only', tags)

            # tag ival: union (min(2015,2018), max(2016,2022))
            self.eq(s_time.parse('2015'), tags['foo.bar'][0])
            self.eq(s_time.parse('2022'), tags['foo.bar'][1])

            # tagprop: dst wins on conflict
            self.eq('dst-tp', dst.getTagProp('foo.bar', '_tp'))

            # extended prop: dst wins on conflict
            self.propeq(dst, '_efoo', 'dstext')

            # nodedata: dst wins k1 on conflict, additive k2 and k3
            self.sorteq(
                [('k1', 'dst-k1'), ('k2', 'src-k2'), ('k3', 'dst-k3')],
                [item async for item in dst.iterData()]
            )

            # both edge directions moved to dst
            self.eq(['refs'], [verb async for (verb, nid) in dst.iterEdgesN1()])
            self.eq(['refs'], [verb async for (verb, nid) in dst.iterEdgesN2()])

    async def test_stormlib_model_migration_fuse_merge_types(self):
        '''
        3.x storage overwrites rather than merging, so the fuse computes the merge itself
        through Type.merge(). A type which does not merge returns dst's value.
        '''
        async with self.getTestCore() as core:

            opts = {'vars': {'src': 'mt-src', 'dst': 'mt-dst'}}

            # test:guid:seen is an ival, test:guid:tick is a plain time
            srcguid = s_common.guid()
            dstguid = s_common.guid()
            opts = {'vars': {'srcguid': srcguid, 'dstguid': dstguid}}

            await core.nodes('[ test:guid=$srcguid :seen=(2010, 2015) :tick=2020 :size=10 ]', opts=opts)
            await core.nodes('[ test:guid=$dstguid :seen=(2012, 2013) :tick=2019 :size=20 ]', opts=opts)

            await core.nodes('''
                test:guid=$srcguid $n=$node -> { test:guid=$dstguid
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=opts)

            nodes = await core.nodes('test:guid=$dstguid', opts=opts)
            self.len(1, nodes)
            dst = nodes[0]

            # ival merges to the union rather than dst winning
            (_, seen) = dst.get('seen')
            self.eq(s_time.parse('2010'), seen[0])
            self.eq(s_time.parse('2015'), seen[1])

            # non merging types keep dst's value
            self.propeq(dst, 'tick', s_time.parse('2019'))
            self.propeq(dst, 'size', 20)

    async def test_stormlib_model_migration_fuse_virts(self):
        '''
        A transferred value must stay reachable by a lift, which it only is if the
        (stortype, virts) pair stored alongside it describes it.
        '''
        async with self.getTestCore() as core:

            srcguid = s_common.guid()
            dstguid = s_common.guid()
            opts = {'vars': {'srcguid': srcguid, 'dstguid': dstguid}}

            # :comp is a comp typed prop, whose virts carry the per field stortypes, and
            # :server is a poly whose virts carry its own storage shape
            await core.nodes('''
                [ test:guid=$srcguid :comp=(10, foo) :server=tcp://1.2.3.4:80 ]
            ''', opts=opts)
            await core.nodes('[ test:guid=$dstguid ]', opts=opts)

            await core.nodes('''
                test:guid=$srcguid $n=$node -> { test:guid=$dstguid
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=opts)

            # the transferred values must be liftable, not merely present in the sode
            nodes = await core.nodes('test:guid:comp=(10, foo)')
            self.len(1, nodes)
            self.eq(dstguid, nodes[0].ndef[1])

            nodes = await core.nodes('test:guid:server=tcp://1.2.3.4:80')
            self.len(1, nodes)
            self.eq(dstguid, nodes[0].ndef[1])

    async def test_stormlib_model_migration_fuse_refs(self):

        async with self.getTestCore() as core:

            # --- a poly reference and an array of poly references are repointed ---

            await core.nodes('[ test:str=r-src test:str=r-dst ]')
            await core.nodes('[ test:str=r-ref :somestr=r-src ]')
            await core.nodes('[ test:arrayprop=(a1,) :strs=(r-src, keepme) ]')

            await core.nodes('''
                test:str=r-src $n=$node -> { test:str=r-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.len(0, await core.nodes('test:str=r-src'))

            nodes = await core.nodes('test:str=r-ref')
            self.eq(('test:str', 'r-dst'), nodes[0].get('somestr'))

            nodes = await core.nodes('test:arrayprop:strs*[=r-dst]')
            self.len(1, nodes)
            self.isin(('test:str', 'keepme'), nodes[0].get('strs'))
            self.notin(('test:str', 'r-src'), nodes[0].get('strs'))

    async def test_stormlib_model_migration_fuse_selfref(self):

        async with self.getTestCore() as core:

            # a reference src holds to itself, and an edge from src to itself, follow the
            # node rather than being left pointing at a deleted node
            await core.nodes('[ test:str=s-src :somestr=s-src ]')
            await core.nodes('[ test:str=s-dst ]')
            await core.nodes('test:str=s-src [ +(refs)> { test:str=s-src } ]')

            await core.nodes('''
                test:str=s-src $n=$node -> { test:str=s-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.len(0, await core.nodes('test:str=s-src'))

            nodes = await core.nodes('test:str=s-dst')
            self.len(1, nodes)
            dst = nodes[0]

            self.eq(('test:str', 's-dst'), dst.get('somestr'))

            edges = [(verb, nid) async for (verb, nid) in dst.iterEdgesN1()]
            self.eq([('refs', dst.nid)], edges)

    async def test_stormlib_model_migration_fuse_comp_cascade(self):

        async with self.getTestCore() as core:

            # a computed comp key slot referencing src renames the comp node itself. :tick is
            # not computed, so it is carried across rather than rebuilt for the new value.
            await core.nodes('[ test:str=c-src test:str=c-dst ]')
            await core.nodes('[ test:pivcomp=(c-targ, c-src) :tick=2020 +#comptag ]')

            await core.nodes('''
                test:str=c-src $n=$node -> { test:str=c-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.len(0, await core.nodes('test:str=c-src'))

            nodes = await core.nodes('test:pivcomp')
            self.len(1, nodes)
            self.eq((('test:pivtarg', 'c-targ'), ('test:str', 'c-dst')), nodes[0].ndef[1])
            self.eq(('test:str', 'c-dst'), nodes[0].get('lulz'))
            self.isin('comptag', dict(nodes[0].getTags()))
            self.propeq(nodes[0], 'tick', s_time.parse('2020'))

    async def test_stormlib_model_migration_fuse_comp_multislot(self):
        '''
        A comp may embed the same renamed node in more than one of its own slots, so every
        slot has to be remapped by that single rename rather than only the one whose
        reference happened to be discovered first.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:pivtarg=ms-src test:pivtarg=ms-dst ]')
            await core.nodes('[ test:pivcomp2=(ms-src, ms-src) +#both ]')
            await core.nodes('[ test:pivcomp2=(ms-src, other) +#one ]')

            await core.nodes('''
                test:pivtarg=ms-src $n=$node -> { test:pivtarg=ms-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.len(0, await core.nodes('test:pivtarg=ms-src'))

            byvalu = {node.ndef[1]: node for node in await core.nodes('test:pivcomp2')}
            self.len(2, byvalu)

            both = byvalu[(('test:pivtarg', 'ms-dst'), ('test:pivtarg', 'ms-dst'))]
            self.isin('both', dict(both.getTags()))
            self.eq(('test:pivtarg', 'ms-dst'), both.get('targ1'))
            self.eq(('test:pivtarg', 'ms-dst'), both.get('targ2'))

            one = byvalu[(('test:pivtarg', 'ms-dst'), ('test:pivtarg', 'other'))]
            self.isin('one', dict(one.getTags()))

    async def test_stormlib_model_migration_fuse_cascade_fixpoint(self):
        '''
        A comp slot may name another comp which is itself still being resolved, so the
        destinations are iterated to a fixpoint rather than computed in one pass.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:int=10 test:int=20 ]')
            await core.nodes('[ test:acomp=(((10, aaa), (99, zzz)), nnn) ]')

            await core.nodes('''
                test:int=10 $n=$node -> { test:int=20
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.len(0, await core.nodes('test:int=10'))

            # the whole three level cascade is renamed
            nodes = await core.nodes('test:acomp')
            self.len(1, nodes)
            self.eq(
                (('test:compcomp', (('test:comp', (('test:int', 20), ('test:lower', 'aaa'))),
                                    ('test:comp', (('test:int', 99), ('test:lower', 'zzz'))))),
                 ('test:lower', 'nnn')),
                nodes[0].ndef[1])

            # only the slot which named src changed
            self.sorteq(
                [(('test:int', 20), ('test:lower', 'aaa')),
                 (('test:int', 99), ('test:lower', 'zzz'))],
                [node.ndef[1] for node in await core.nodes('test:comp')])

    async def test_stormlib_model_migration_fuse_gutor(self):
        '''
        A guid form whose primary value is the hash of its own deconfliction set is not
        renamed: a computed property which is not a comp key slot is rewritten in place.
        This is a documented gap.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=g-src test:str=g-dst ]')
            nodes = await core.nodes('[ test:fusegutor=({"strref": "g-src"}) :note=hi ]')
            guid = nodes[0].ndef[1]

            await core.nodes('''
                test:str=g-src $n=$node -> { test:str=g-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.len(0, await core.nodes('test:str=g-src'))

            nodes = await core.nodes('test:fusegutor')
            self.len(1, nodes)

            # the guid is unchanged, so it no longer matches its own deconfliction set
            self.eq(guid, nodes[0].ndef[1])
            self.eq(('test:str', 'g-dst'), nodes[0].get('strref'))
            self.propeq(nodes[0], 'note', 'hi')

    async def test_stormlib_model_migration_fuse_gutor_reingest(self):
        '''
        Constructing the node again from its original deconfliction set after the fuse does
        not deconflict to it, since the deconfliction re-check sees the rewritten property.
        A second node is created and src is re-created along with it. Pinned here because
        this is what the documented guid gap costs in practice, and because it settles at
        one extra node rather than adding one per attempt.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=g-src test:str=g-dst ]')
            nodes = await core.nodes('[ test:fusegutor=({"strref": "g-src"}) :note=hi ]')
            guid = nodes[0].ndef[1]

            await core.nodes('''
                test:str=g-src $n=$node -> { test:str=g-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.len(0, await core.nodes('test:str=g-src'))

            # the original deconfliction set no longer finds the fused node
            for _ in range(3):
                await core.nodes('[ test:fusegutor=({"strref": "g-src"}) ]')

                nodes = await core.nodes('test:fusegutor')
                self.len(2, nodes)

            # src is back, re-created by the deconfliction set which still names it
            self.len(1, await core.nodes('test:str=g-src'))

            bynode = {node.ndef[1]: node for node in nodes}

            # the fused node keeps the analytical data
            fused = bynode.pop(guid)
            self.eq(('test:str', 'g-dst'), fused.get('strref'))
            self.propeq(fused, 'note', 'hi')

            # and the new node holds only the deconfliction property
            (dupe,) = bynode.values()
            self.eq(('test:str', 'g-src'), dupe.get('strref'))
            self.none(dupe.get('note'))

    async def test_stormlib_model_migration_fuse_gutor_reingest_fused(self):
        '''
        Constructing the node from its deconfliction set with the fused value substituted in
        does deconflict to it, stale primary value and all: the exact guid misses, and
        Guid._getGuidByNorms() then lifts by the deconfliction properties and finds it. This
        bounds the documented gap - the node stays reachable, and only a construction from
        the pre-fuse value forks - so it is pinned alongside the fork itself.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=g-src test:str=g-dst ]')
            nodes = await core.nodes('[ test:fusegutor=({"strref": "g-src"}) :note=hi ]')
            guid = nodes[0].ndef[1]

            await core.nodes('''
                test:str=g-src $n=$node -> { test:str=g-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            # the fused value finds the node rather than creating a second one
            for _ in range(3):
                nodes = await core.nodes('[ test:fusegutor=({"strref": "g-dst"}) ]')
                self.len(1, nodes)
                self.eq(guid, nodes[0].ndef[1])

            self.len(1, await core.nodes('test:fusegutor'))

            # and neither the node's data nor the deleted src is disturbed
            nodes = await core.nodes('test:fusegutor')
            self.propeq(nodes[0], 'note', 'hi')
            self.len(0, await core.nodes('test:str=g-src'))

    async def test_stormlib_model_migration_fuse_inherit(self):

        async with self.getTestCore() as core:

            # --- child into parent ---

            await core.nodes('[ test:inhstr2=i-src :name=srcname :child1=childonly ]')
            await core.nodes('[ test:inhstr=i-dst ]')

            # test:str:inhstr is a poly declared for the PARENT form, so a reference may be
            # filed under either the parent or the concrete child
            await core.nodes('[ test:str=i-r1 :inhstr={ test:inhstr2=i-src } ]')
            await core.nodes('[ test:str=i-r2 :inhstr={ test:inhstr=i-dst } ]')

            mesgs = await core.stormlist('''
                test:inhstr2=i-src $n=$node -> { test:inhstr=i-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            # a prop only the child form declares has nowhere to go on the parent
            self.stormIsInWarn('cannot transfer test:inhstr2:child1 to test:inhstr', mesgs)

            self.len(0, await core.nodes('test:inhstr2=i-src'))

            nodes = await core.nodes('test:inhstr=i-dst')
            self.len(1, nodes)

            # dst's own form survives; a fuse never reclassifies a node
            self.eq(('test:inhstr', 'i-dst'), nodes[0].ndef)
            self.propeq(nodes[0], 'name', 'srcname')

            # a reference filed under the concrete child form moves to dst's own form
            nodes = await core.nodes('test:str=i-r1')
            self.eq(('test:inhstr', 'i-dst'), nodes[0].get('inhstr'))

            nodes = await core.nodes('test:str=i-r2')
            self.eq(('test:inhstr', 'i-dst'), nodes[0].get('inhstr'))

            # --- parent into child ---

            await core.nodes('[ test:inhstr=p-src :name=pname ]')
            await core.nodes('[ test:inhstr2=p-dst :child1=keepme ]')
            await core.nodes('[ test:str=p-r1 :inhstr={ test:inhstr=p-src } ]')

            await core.nodes('''
                test:inhstr=p-src $n=$node -> { test:inhstr2=p-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.len(0, await core.nodes('test:inhstr=p-src'))

            nodes = await core.nodes('test:inhstr2=p-dst')
            self.len(1, nodes)
            self.eq(('test:inhstr2', 'p-dst'), nodes[0].ndef)
            self.propeq(nodes[0], 'name', 'pname')
            self.propeq(nodes[0], 'child1', 'keepme')

            # the reference was filed under the ancestor both forms share, so it stays
            # filed under it
            nodes = await core.nodes('test:str=p-r1')
            self.eq(('test:inhstr', 'p-dst'), nodes[0].get('inhstr'))

    async def test_stormlib_model_migration_fuse_inherit_refuse(self):
        '''
        A property declared for a child form cannot hold a parent form node, so repointing
        it is refused while the fuse is still being computed and nothing is changed.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:inhstr2=rf-src ]')
            await core.nodes('[ test:inhstr=rf-dst ]')
            await core.nodes('[ test:fusechildref=(rf1,) :ref={ test:inhstr2=rf-src } ]')

            await self.asyncraises(s_exc.BadTypeValu, core.nodes('''
                test:inhstr2=rf-src $n=$node -> { test:inhstr=rf-dst
                    $lib.model.migration.fuse($n, $node) }
            '''))

            # nothing was changed
            self.len(1, await core.nodes('test:inhstr2=rf-src'))
            nodes = await core.nodes('test:fusechildref')
            self.eq(('test:inhstr2', 'rf-src'), nodes[0].get('ref'))

    async def test_stormlib_model_migration_fuse_multilayer(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=ml-src :hehe=lower +#low ]')
            await core.nodes('[ test:str=ml-dst ]')

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': viewiden}

            await core.nodes('test:str=ml-src [ :tick=2021 +#upper ]', opts=opts)

            await core.nodes('''
                test:str=ml-src $n=$node -> { test:str=ml-dst
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=opts)

            # src is gone from every view, not just the one the fuse ran in
            self.len(0, await core.nodes('test:str=ml-src'))
            self.len(0, await core.nodes('test:str=ml-src', opts=opts))

            # each value stays in the layer it was written to
            base = (await core.nodes('test:str=ml-dst'))[0]
            self.propeq(base, 'hehe', 'lower')
            self.none(base.get('tick'))
            self.eq(['low'], sorted(tag for (tag, valu) in base.getTags()))

            fork = (await core.nodes('test:str=ml-dst', opts=opts))[0]
            self.propeq(fork, 'hehe', 'lower')
            self.propeq(fork, 'tick', s_time.parse('2021'))
            self.eq(['low', 'upper'], sorted(tag for (tag, valu) in fork.getTags()))

    async def test_stormlib_model_migration_fuse_tombstones(self):

        async with self.getTestCore() as core:

            # --- a tombstone on dst which would mask a transferred value is removed ---

            await core.nodes('[ test:str=tm-src ]')
            await core.nodes('[ test:str=tm-dst :hehe=basehehe ]')

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': viewiden}

            await core.nodes('test:str=tm-src [ :hehe=srchehe ]', opts=opts)
            await core.nodes('test:str=tm-dst [ -:hehe ]', opts=opts)

            self.none((await core.nodes('test:str=tm-dst', opts=opts))[0].get('hehe'))

            await core.nodes('''
                test:str=tm-src $n=$node -> { test:str=tm-dst
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=opts)

            # the transferred value is visible rather than still masked
            self.propeq((await core.nodes('test:str=tm-dst', opts=opts))[0], 'hehe', 'srchehe')

            # the base layer kept its own value
            self.propeq((await core.nodes('test:str=tm-dst'))[0], 'hehe', 'basehehe')

    async def test_stormlib_model_migration_fuse_nodedata_tombstone(self):

        async with self.getTestCore() as core:

            # a node data tombstone on dst masks the value being transferred to it the same
            # way a prop tombstone does, so it is removed rather than taking precedence

            await core.nodes('[ test:str=nd-src ]')
            await core.nodes('[ test:str=nd-dst ]')

            await core.nodes('test:str=nd-dst $node.data.set(ndkey, basevalu)')

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': viewiden}

            await core.nodes('test:str=nd-src $node.data.set(ndkey, srcvalu)', opts=opts)
            await core.nodes('test:str=nd-dst $node.data.pop(ndkey)', opts=opts)

            # dst's tombstone masks the base layer value
            masked = (await core.nodes('test:str=nd-dst', opts=opts))[0]
            self.eq([], [item async for item in masked.iterData()])

            await core.nodes('''
                test:str=nd-src $n=$node -> { test:str=nd-dst
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=opts)

            # the transferred value is visible rather than still masked
            dst = (await core.nodes('test:str=nd-dst', opts=opts))[0]
            self.eq([('ndkey', 'srcvalu')], [item async for item in dst.iterData()])

            # the base layer kept its own value
            base = (await core.nodes('test:str=nd-dst'))[0]
            self.eq([('ndkey', 'basevalu')], [item async for item in base.iterData()])

    async def test_stormlib_model_migration_fuse_src_tombstones(self):

        async with self.getTestCore() as core:

            # state src holds only as a tombstone is affirmatively absent, so it is not
            # transferred as though it were live
            await core.nodes('[ test:str=st-src :hehe=basehehe +#basetag ]')
            await core.nodes('[ test:str=st-dst ]')

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': viewiden}

            await core.nodes('test:str=st-src [ -:hehe -#basetag ]', opts=opts)

            await core.nodes('''
                test:str=st-src $n=$node -> { test:str=st-dst
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=opts)

            self.len(0, await core.nodes('test:str=st-src'))
            self.len(0, await core.nodes('test:str=st-src', opts=opts))

            # the base layer transfer still happened, and src's fork tombstones did not
            # cause anything to be written into the fork
            base = (await core.nodes('test:str=st-dst'))[0]
            self.propeq(base, 'hehe', 'basehehe')
            self.eq(['basetag'], sorted(tag for (tag, valu) in base.getTags()))

    async def test_stormlib_model_migration_fuse_admin(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=ad-src test:str=ad-dst ]')

            lowuser = await core.auth.addUser('fuselow')
            aslow = {'user': lowuser.iden}

            await self.asyncraises(s_exc.AuthDeny, core.nodes('''
                test:str=ad-src $n=$node -> { test:str=ad-dst
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=aslow))

            # nothing was changed
            self.len(1, await core.nodes('test:str=ad-src'))

    async def test_stormlib_model_migration_fuse_readonly(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=ro-src :hehe=srcval ]')
            await core.nodes('[ test:str=ro-dst ]')

            layr = core.getView().layers[0]

            await layr.setLayerInfo('readonly', True)

            mesgs = await core.stormlist('''
                test:str=ro-src $n=$node -> { test:str=ro-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.stormIsInWarn('because it is read only', mesgs)

            await layr.setLayerInfo('readonly', False)

            # src is still there, since the only layer holding it could not be written
            self.len(1, await core.nodes('test:str=ro-src'))

    async def test_stormlib_model_migration_fuse_no_triggers(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=tg-src :hehe=srcval +#tg.tag ]')
            await core.nodes('[ test:str=tg-dst ]')

            for tdef in (
                {'cond': 'node:add', 'form': 'test:int', 'storm': '[ test:str=fired ]'},
                {'cond': 'prop:set', 'prop': 'test:str:hehe', 'storm': '[ test:int=1 ]'},
                {'cond': 'tag:add', 'tag': 'tg.tag', 'storm': '[ test:int=2 ]'},
            ):
                await core.callStorm('return($lib.trigger.add($tdef))', opts={'vars': {'tdef': tdef}})

            await core.nodes('''
                test:str=tg-src $n=$node -> { test:str=tg-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.propeq((await core.nodes('test:str=tg-dst'))[0], 'hehe', 'srcval')

            # a fuse rewrites the same data across every layer rather than making an
            # analytical change in one view, so no view's triggers are the right ones
            self.len(0, await core.nodes('test:int'))
            self.len(0, await core.nodes('test:str=fired'))

    async def test_stormlib_model_migration_fuse_rerun(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=rr-src :hehe=srcval +#rr.tag ]')
            await core.nodes('[ test:str=rr-dst ]')
            await core.nodes('[ test:str=rr-ref :somestr=rr-src ]')

            fuse = '''
                test:str=rr-src $n=$node -> { test:str=rr-dst
                    $lib.model.migration.fuse($n, $node) }
            '''

            await core.nodes(fuse)

            nodes = await core.nodes('test:str=rr-dst')
            self.propeq(nodes[0], 'hehe', 'srcval')

            # re-running with the same arguments is a no-op rather than an error, which is
            # what makes an interrupted fuse recoverable
            await core.nodes('[ test:str=rr-src ]')
            await core.nodes(fuse)

            self.len(0, await core.nodes('test:str=rr-src'))
            nodes = await core.nodes('test:str=rr-dst')
            self.propeq(nodes[0], 'hehe', 'srcval')
            self.eq(('test:str', 'rr-dst'), (await core.nodes('test:str=rr-ref'))[0].get('somestr'))

    def test_nodefuse_edit_chunks(self):
        '''
        iterEditChunks() must never split a single nodeedit, since the edits for one nid are
        order dependent, and must preserve the order it is given them in.
        '''
        nodeedits = [
            (1, 'test:str', [('a',), ('b',), ('c',)]),
            (2, 'test:str', [('d',)]),
            (3, 'test:str', [('e',), ('f',)]),
        ]

        # one chunk when the budget covers everything
        chunks = list(s_nodefuse.iterEditChunks(nodeedits, chunk=100))
        self.eq([nodeedits], chunks)

        # a nodeedit is never split, so a chunk overshoots rather than splitting one
        chunks = list(s_nodefuse.iterEditChunks(nodeedits, chunk=1))
        self.eq([[nodeedits[0]], [nodeedits[1]], [nodeedits[2]]], chunks)

        # order is preserved across a boundary which falls between nodeedits
        chunks = list(s_nodefuse.iterEditChunks(nodeedits, chunk=3))
        self.eq([[nodeedits[0]], [nodeedits[1], nodeedits[2]]], chunks)

        # nothing in, nothing out
        self.eq([], list(s_nodefuse.iterEditChunks([])))

        # the default is the module constant
        self.eq(1000, s_nodefuse.maxchunkedits)

    async def test_stormlib_model_migration_fuse_chunked(self):
        '''
        A fuse larger than one chunk spans several nexus operations per layer and must
        still complete.
        '''
        async with self.getTestCore() as core:

            with mock.patch.object(s_nodefuse, 'maxchunkedits', 2):

                await core.nodes('[ test:str=ch-src test:str=ch-dst ]')

                # enough inbound references to need several chunks
                for indx in range(12):
                    opts = {'vars': {'name': f'ch-ref{indx}'}}
                    await core.nodes('[ test:str=$name :somestr=ch-src ]', opts=opts)

                await core.nodes('''
                    test:str=ch-src $n=$node -> { test:str=ch-dst
                        $lib.model.migration.fuse($n, $node) }
                ''')

            self.len(0, await core.nodes('test:str=ch-src'))
            self.len(12, await core.nodes('test:str:somestr=ch-dst'))

    async def test_stormlib_model_migration_fuse_isnew_per_layer(self):
        '''
        A dst which does not exist in a layer yet is created there, and needs its computed
        properties, which describe dst rather than src and are copied from whichever layer
        already holds them.
        '''
        async with self.getTestCore() as core:

            # dst lives only in the base layer, and carries a property which is NOT computed
            # alongside the ones which are
            await core.nodes('[ test:comp=(20, bbb) :seen=(2000, 2001) ]')

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': viewiden}

            # src lives only in the fork layer, so the fork is a layer dst is new in
            await core.nodes('[ test:comp=(10, aaa) :seen=(2010, 2015) +#srconly ]', opts=opts)

            await core.nodes('''
                test:comp=(10, aaa) $n=$node -> { test:comp=(20, bbb)
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=opts)

            self.len(0, await core.nodes('test:comp=(10, aaa)', opts=opts))

            nodes = await core.nodes('test:comp=(20, bbb)', opts=opts)
            self.len(1, nodes)
            dst = nodes[0]

            # src's state came across into the fork
            self.isin('srconly', dict(dst.getTags()))

            # dst's computed props still describe dst, not src
            self.propeq(dst, 'hehe', 20)
            self.propeq(dst, 'haha', 'bbb')

            # and dst is liftable by them from the fork, so the copied (stortype, virts)
            # pairs describe the values they accompany
            nodes = await core.nodes('test:comp:hehe=20', opts=opts)
            self.len(1, nodes)
            self.eq((('test:int', 20), ('test:lower', 'bbb')), nodes[0].ndef[1])

    async def test_stormlib_model_migration_fuse_tagprop_merge(self):

        async with self.getTestCore() as core:

            await core.addTagProp('_ival', ('ival', {}), {})
            await core.addTagProp('_str', ('str', {}), {})

            await core.nodes('''
                [ test:str=tp-src +#foo:_ival=(2010, 2015) +#foo:_str=srcstr ]
            ''')
            await core.nodes('''
                [ test:str=tp-dst +#foo:_ival=(2012, 2020) +#foo:_str=dststr ]
            ''')

            await core.nodes('''
                test:str=tp-src $n=$node -> { test:str=tp-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            nodes = await core.nodes('test:str=tp-dst')
            self.len(1, nodes)
            dst = nodes[0]

            # an ival tagprop merges to the union rather than dst winning
            ival = dst.getTagProp('foo', '_ival')
            self.eq(s_time.parse('2010'), ival[0])
            self.eq(s_time.parse('2020'), ival[1])

            # a non merging tagprop keeps dst's value
            self.eq('dststr', dst.getTagProp('foo', '_str'))

    async def test_stormlib_model_migration_fuse_tagprop_tombstone(self):

        async with self.getTestCore() as core:

            await core.addTagProp('_str', ('str', {}), {})

            await core.nodes('[ test:str=tpt-src ]')
            await core.nodes('[ test:str=tpt-dst +#foo:_str=basestr ]')

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': viewiden}

            await core.nodes('test:str=tpt-src [ +#foo:_str=srcstr ]', opts=opts)
            await core.nodes('test:str=tpt-dst [ -#foo:_str ]', opts=opts)

            self.none((await core.nodes('test:str=tpt-dst', opts=opts))[0].getTagProp('foo', '_str'))

            await core.nodes('''
                test:str=tpt-src $n=$node -> { test:str=tpt-dst
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=opts)

            # the tombstone which would have masked the transferred value was removed
            nodes = await core.nodes('test:str=tpt-dst', opts=opts)
            self.eq('srcstr', nodes[0].getTagProp('foo', '_str'))

            # the base layer kept its own value
            nodes = await core.nodes('test:str=tpt-dst')
            self.eq('basestr', nodes[0].getTagProp('foo', '_str'))

    async def test_stormlib_model_migration_fuse_novalu_layer(self):
        '''
        A layer may hold node data or light edges for src without holding src's primary
        property, in which case there is no node delete to clean them up and they have to be
        removed explicitly.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=nv-src test:str=nv-dst test:str=nv-other ]')

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': viewiden}

            # node data and an edge are added in the fork, where src has no primary property
            await core.nodes('test:str=nv-src $node.data.set(forkkey, forkvalu)', opts=opts)
            await core.nodes('test:str=nv-src [ +(refs)> { test:str=nv-other } ]', opts=opts)

            await core.nodes('''
                test:str=nv-src $n=$node -> { test:str=nv-dst
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=opts)

            self.len(0, await core.nodes('test:str=nv-src', opts=opts))
            self.len(0, await core.nodes('test:str=nv-src'))

            nodes = await core.nodes('test:str=nv-dst', opts=opts)
            self.len(1, nodes)
            dst = nodes[0]

            self.eq([('forkkey', 'forkvalu')], [item async for item in dst.iterData()])
            self.eq(['refs'], [verb async for (verb, nid) in dst.iterEdgesN1()])

    async def test_stormlib_model_migration_fuse_apply_failure(self):
        '''
        A layer which cannot be written is recorded and reported rather than aborting the
        rest of the fuse, and the fuse is re-runnable.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=af-src :hehe=srcval ]')
            await core.nodes('[ test:str=af-dst ]')

            layr = core.getView().layers[0]

            async def boom(*args, **kwargs):
                raise s_exc.SynErr(mesg='boom')

            with mock.patch.object(layr, 'saveNodeEdits', boom):
                with self.raises(s_exc.SynErr) as cm:
                    await core.nodes('''
                        test:str=af-src $n=$node -> { test:str=af-dst
                            $lib.model.migration.fuse($n, $node) }
                    ''')

            self.isin('failed to apply edits to some layers', cm.exception.get('mesg'))
            self.eq([layr.iden], cm.exception.get('layers'))

            # nothing was applied, so a re-run completes the fuse
            self.len(1, await core.nodes('test:str=af-src'))

            await core.nodes('''
                test:str=af-src $n=$node -> { test:str=af-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.len(0, await core.nodes('test:str=af-src'))
            self.propeq((await core.nodes('test:str=af-dst'))[0], 'hehe', 'srcval')

    async def test_stormlib_model_migration_fuse_became_readonly(self):
        '''
        A layer is re-checked before its edits are computed, since discovery happens before
        anything is applied.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=br-src :hehe=srcval ]')
            await core.nodes('[ test:str=br-dst ]')

            layr = core.getView().layers[0]

            realGetLayerEdits = s_nodefuse.NodeFuser.getLayerEdits

            async def getLayerEdits(self, srcndef, dstndef):
                await realGetLayerEdits(self, srcndef, dstndef)
                # the layer becomes read only after discovery but before the apply
                layr.readonly = True

            with mock.patch.object(s_nodefuse.NodeFuser, 'getLayerEdits', getLayerEdits):
                mesgs = await core.stormlist('''
                    test:str=br-src $n=$node -> { test:str=br-dst
                        $lib.model.migration.fuse($n, $node) }
                ''')

            layr.readonly = False

            self.stormIsInWarn('became read only while the fuse was being computed', mesgs)

            # nothing was applied
            self.len(1, await core.nodes('test:str=br-src'))

    async def test_nodefuse_req_renames_resolved(self):
        '''
        The single hop rename assumption is checked rather than inferred. No model construct
        reaches it today - test_stormlib_model_migration_fuse_model_canary() is what fails
        if one appears - so the rename map is seeded directly here.
        '''
        async with self.getTestCore() as core:

            useriden = core.auth.rootuser.iden

            async with await s_nodefuse.NodeFuser.anit(core, useriden) as fuser:

                # a two hop chain: g-src renames to g-mid, which is itself renamed
                await fuser._setRename(('test:str', 'g-src'), ('test:str', 'g-mid'), None)
                await fuser._setRename(('test:str', 'g-mid'), ('test:str', 'g-dst'), None)

                with self.raises(s_exc.SynErr) as cm:
                    await fuser._reqRenamesResolved()

                self.isin('which is itself being renamed', cm.exception.get('mesg'))

            # and a fully resolved map passes
            async with await s_nodefuse.NodeFuser.anit(core, useriden) as fuser:

                await fuser._setRename(('test:str', 'r-src'), ('test:str', 'r-dst'), None)

                self.none(await fuser._reqRenamesResolved())

    async def test_stormlib_model_migration_fuse_model_canary(self):
        '''
        Pin the model constructs NodeFuser's rename handling was written against.

        A computed property which can name a node is handled one of two ways. Where it
        restates one of its own form's comp key slots, the node holding it is itself
        renamed by the fuse (_discoverCascadeSrcs). Where it does not, it is rewritten in
        place once every rename is known (_rewriteRefs). Only s_types.Comp produces the
        first, which is what lets _computeRenames() resolve every rename in a single hop.

        A form type class appearing in this set which is not listed below is a construct
        neither of those two behaviors was written for. Whoever adds one has to decide
        which of the two it needs, and re-check the single hop assumption asserted at the
        end of _computeRenames() if it can rename. Pinning the set here makes that a
        deliberate decision rather than one inherited by default, since the wrong default
        is silent: an in place rewrite of a property the primary value is derived from
        leaves the node inconsistent with its own value and raises nothing.
        '''
        async with self.getTestCore() as core:

            model = core.model

            classes = set()

            for form in model.forms.values():

                # the test model carries deliberate edge cases of its own, each covered by
                # a fuse test above
                if form.name.startswith('test:'):
                    continue

                for prop in form.props.values():

                    if not prop.info.get('computed'):
                        continue

                    # a property can only name a node if it is typed as a form or is poly
                    ptyp = prop.type
                    if model.form(ptyp.name) is None and not ptyp.ispoly:
                        continue

                    classes.add(form.type.__class__.__name__)

            # Comp is the only entry which cascades. The rest one-way derive their computed
            # props from a primary value which is not itself a function of the referenced
            # node, so an inbound reference is rewritten in place and the node keeps its own
            # value - fusing inet:fqdn=vertex.link away does not rename www.vertex.link.
            expect = {
                'Comp',
                'Cpe23Str',
                'Data',
                'Email',
                'FileBase',
                'Fqdn',
                'IPRange',
                'LangCode',
                'Passwd',
                'Rfc2822Addr',
                'SockAddr',
                'Str',
                'Tag',
                'Taxonomy',
                'Url',
            }

            mesg = ('The set of form type classes carrying a computed property which can name a node '
                    'has changed. $lib.model.migration.fuse() either renames such a node (comp key '
                    'slots) or rewrites the property in place (everything else) - see '
                    'NodeFuser._discoverCascadeSrcs(). Decide which the new construct needs, re-check '
                    'the single hop rename assumption at the end of NodeFuser._computeRenames() if it '
                    'can rename, and update this set.')

            self.eq(expect, classes, msg=mesg)

    async def test_stormlib_model_migration_fuse_became_fini(self):
        '''
        A layer deleted between discovery and the apply is skipped with a warning of its own,
        rather than raising into the failed layer path which would tell the operator to
        re-run against a layer which no longer exists.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=bf-src :hehe=srcval ]')
            await core.nodes('[ test:str=bf-dst ]')

            layr = core.getView().layers[0]

            realGetLayerEdits = s_nodefuse.NodeFuser.getLayerEdits

            async def getLayerEdits(self, srcndef, dstndef):
                await realGetLayerEdits(self, srcndef, dstndef)
                # the layer goes away after discovery but before the apply
                layr.isfini = True

            with mock.patch.object(s_nodefuse.NodeFuser, 'getLayerEdits', getLayerEdits):
                mesgs = await core.stormlist('''
                    test:str=bf-src $n=$node -> { test:str=bf-dst
                        $lib.model.migration.fuse($n, $node) }
                ''')

            layr.isfini = False

            self.stormIsInWarn('was deleted while the fuse was being computed', mesgs)

            # skipped rather than recorded as a failed layer, so no re-run is advised
            self.stormNotInWarn('Re-run fuse() with the same arguments to complete it', mesgs)

            # nothing was applied
            self.len(1, await core.nodes('test:str=bf-src'))

    async def test_stormlib_model_migration_fuse_selfref_array(self):
        '''
        An array property on src which references src must follow the node, and be
        re-normalized afterwards since an array type may be uniq and/or sorted.
        '''
        async with self.getTestCore() as core:

            srcguid = s_common.guid()
            dstguid = s_common.guid()
            othguid = s_common.guid()
            opts = {'vars': {'srcguid': srcguid, 'dstguid': dstguid, 'othguid': othguid}}

            await core.nodes('[ test:arrayprop=$othguid ]', opts=opts)
            await core.nodes('[ test:arrayprop=$dstguid ]', opts=opts)

            # test:arrayprop:children is an array of test:arrayprop, so src's own array
            # holds a reference to src itself alongside an unrelated one
            await core.nodes('''
                [ test:arrayprop=$srcguid
                    :children+={ test:arrayprop=$srcguid }
                    :children+={ test:arrayprop=$othguid }
                ]
            ''', opts=opts)

            await core.nodes('''
                test:arrayprop=$srcguid $n=$node -> { test:arrayprop=$dstguid
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=opts)

            self.len(0, await core.nodes('test:arrayprop=$srcguid', opts=opts))

            nodes = await core.nodes('test:arrayprop=$dstguid', opts=opts)
            self.len(1, nodes)

            children = nodes[0].get('children')
            self.isin(('test:arrayprop', dstguid), children)
            self.isin(('test:arrayprop', othguid), children)
            self.notin(('test:arrayprop', srcguid), children)

            # the rewritten array is still liftable by element, so it was re-normalized
            nodes = await core.nodes('test:arrayprop:children*[=$dstguid]', opts=opts)
            self.len(1, nodes)
            self.eq(dstguid, nodes[0].ndef[1])

    async def test_stormlib_model_migration_fuse_array_unchanged(self):
        '''
        An array property holding no reference to any node this fuse renames is transferred
        exactly as it was stored, rather than being re-normalized into the same value.
        '''
        async with self.getTestCore() as core:

            srcguid = s_common.guid()
            dstguid = s_common.guid()
            othguid = s_common.guid()
            opts = {'vars': {'srcguid': srcguid, 'dstguid': dstguid, 'othguid': othguid}}

            await core.nodes('[ test:arrayprop=$othguid test:arrayprop=$dstguid ]', opts=opts)
            await core.nodes('''
                [ test:arrayprop=$srcguid :children+={ test:arrayprop=$othguid } ]
            ''', opts=opts)

            await core.nodes('''
                test:arrayprop=$srcguid $n=$node -> { test:arrayprop=$dstguid
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=opts)

            self.len(0, await core.nodes('test:arrayprop=$srcguid', opts=opts))

            nodes = await core.nodes('test:arrayprop=$dstguid', opts=opts)
            self.len(1, nodes)
            self.eq((('test:arrayprop', othguid),), nodes[0].get('children'))

            # and it is still liftable by element on dst
            nodes = await core.nodes('test:arrayprop:children*[=$othguid]', opts=opts)
            self.len(1, nodes)
            self.eq(dstguid, nodes[0].ndef[1])

    async def test_stormlib_model_migration_fuse_crossform_refs(self):
        '''
        A cross form fuse checks each referring property once rather than once per referring
        node, and an array property is checked through its member type since that is what
        holds the reference.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:inhstr2=xf-src :name=srcname ]')
            await core.nodes('[ test:inhstr=xf-dst test:inhstr=xf-keep ]')

            # two nodes referencing src through the SAME property
            await core.nodes('[ test:str=xf-r1 :inhstr={ test:inhstr2=xf-src } ]')
            await core.nodes('[ test:str=xf-r2 :inhstr={ test:inhstr2=xf-src } ]')

            # test:str:inhstrarry is an ARRAY of test:inhstr
            await core.nodes('''
                [ test:str=xf-r3
                    :inhstrarry+={ test:inhstr2=xf-src }
                    :inhstrarry+={ test:inhstr=xf-keep }
                ]
            ''')

            await core.nodes('''
                test:inhstr2=xf-src $n=$node -> { test:inhstr=xf-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.len(0, await core.nodes('test:inhstr2=xf-src'))
            self.propeq((await core.nodes('test:inhstr=xf-dst'))[0], 'name', 'srcname')

            for valu in ('xf-r1', 'xf-r2'):
                nodes = await core.nodes(f'test:str={valu}')
                self.eq(('test:inhstr', 'xf-dst'), nodes[0].get('inhstr'))

            nodes = await core.nodes('test:str=xf-r3')
            arry = nodes[0].get('inhstrarry')
            self.isin(('test:inhstr', 'xf-dst'), arry)
            self.isin(('test:inhstr', 'xf-keep'), arry)
            self.notin(('test:inhstr2', 'xf-src'), arry)

            # the rewritten array is still liftable by element
            nodes = await core.nodes('test:str:inhstrarry*[=xf-dst]')
            self.len(1, nodes)
            self.eq(('test:str', 'xf-r3'), nodes[0].ndef)

    async def test_stormlib_model_migration_fuse_iface_poly_refs(self):
        '''
        A poly declared for an interface is returned by Model.getPropsByType() for every form
        in an inheritance chain which implements that interface, so the same inbound reference
        is found more than once and must only be rewritten once.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:fusekid=if-src test:fusekid=if-dst test:fusekid=if-keep ]')

            # test:fuseholder:one and :many are polys declared for test:fuseiface, which both
            # test:fusekid and its parent test:fusebase implement
            await core.nodes('''
                [ test:fuseholder=(if1,)
                    :one={ test:fusekid=if-src }
                    :many+={ test:fusekid=if-src }
                    :many+={ test:fusekid=if-keep }
                ]
            ''')

            await core.nodes('''
                test:fusekid=if-src $n=$node -> { test:fusekid=if-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.len(0, await core.nodes('test:fusekid=if-src'))

            nodes = await core.nodes('test:fuseholder')
            self.len(1, nodes)
            self.eq(('test:fusekid', 'if-dst'), nodes[0].get('one'))

            many = nodes[0].get('many')
            self.isin(('test:fusekid', 'if-dst'), many)
            self.isin(('test:fusekid', 'if-keep'), many)
            self.notin(('test:fusekid', 'if-src'), many)

            # both rewritten references are still liftable
            self.len(1, await core.nodes('test:fuseholder:one={ test:fusekid=if-dst }'))
            self.len(1, await core.nodes('test:fuseholder:many*[={ test:fusekid=if-dst }]'))

    async def test_stormlib_model_migration_fuse_visited_refs(self):
        '''
        A referring node which is itself being fused away redirects its own references and
        light edges in its own pass, so they are not also rewritten under a node which is
        about to be deleted.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:pivtarg=vs-src test:pivtarg=vs-dst ]')

            # the comp's own comp key slot names src, so the comp is renamed by this fuse. It
            # also references src through a plain property and through a light edge.
            await core.nodes('''
                [ test:fusecomp=(vs-src, nnn)
                    :other={ test:pivtarg=vs-src }
                    +(refs)> { test:pivtarg=vs-src }
                ]
            ''')

            await core.nodes('''
                test:pivtarg=vs-src $n=$node -> { test:pivtarg=vs-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.len(0, await core.nodes('test:pivtarg=vs-src'))

            nodes = await core.nodes('test:fusecomp')
            self.len(1, nodes)
            comp = nodes[0]

            # the comp was renamed, and both its property and its edge followed
            self.eq((('test:pivtarg', 'vs-dst'), ('test:lower', 'nnn')), comp.ndef[1])
            self.eq(('test:pivtarg', 'vs-dst'), comp.get('other'))

            dst = (await core.nodes('test:pivtarg=vs-dst'))[0]
            self.eq([('refs', dst.nid)], [(verb, nid) async for (verb, nid) in comp.iterEdgesN1()])

    async def test_stormlib_model_migration_fuse_tag_contained(self):
        '''
        A tag interval dst already holds which contains src's is left alone rather than being
        rewritten with the identical union.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=tc-src +#foo=(2012, 2015) ]')
            await core.nodes('[ test:str=tc-dst +#foo=(2010, 2020) ]')

            await core.nodes('''
                test:str=tc-src $n=$node -> { test:str=tc-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            nodes = await core.nodes('test:str=tc-dst')
            self.len(1, nodes)

            valu = dict(nodes[0].getTags())['foo']
            self.eq(s_time.parse('2010'), valu[0])
            self.eq(s_time.parse('2020'), valu[1])

    async def test_stormlib_model_migration_fuse_src_tombstone_teardown(self):
        '''
        Tombstones src holds in a layer are removed along with the rest of its state there,
        and a tombstone dst holds for a tag src is transferring is cleared first so the
        transferred tag is not written straight back underneath a mask.
        '''
        async with self.getTestCore() as core:

            await core.addTagProp('_str', ('str', {}), {})

            await core.nodes('[ test:str=tt-other test:str=tt-dst ]')
            await core.nodes('''
                [ test:str=tt-src
                    +#gone:_str=basestr
                    +(refs)> { test:str=tt-other }
                ]
            ''')
            await core.nodes('test:str=tt-src $node.data.set(basekey, basevalu)')
            await core.nodes('test:str=tt-other [ +(refs)> { test:str=tt-src } ]')
            await core.nodes('test:str=tt-dst [ +#masked=(2020, 2025) ]')

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': viewiden}

            # in the fork, src holds a live tag plus a tombstone for each of the things it
            # holds live in the base layer, and dst tombstones the tag src is transferring
            await core.nodes('test:str=tt-src [ +#masked=(2010, 2015) ]', opts=opts)
            await core.nodes('test:str=tt-src [ -#gone:_str ]', opts=opts)
            await core.nodes('test:str=tt-src $node.data.pop(basekey)', opts=opts)
            await core.nodes('test:str=tt-src [ -(refs)> { test:str=tt-other } ]', opts=opts)
            await core.nodes('test:str=tt-other [ -(refs)> { test:str=tt-src } ]', opts=opts)
            await core.nodes('test:str=tt-dst [ -#masked ]', opts=opts)

            self.notin('masked', dict((await core.nodes('test:str=tt-dst', opts=opts))[0].getTags()))

            await core.nodes('''
                test:str=tt-src $n=$node -> { test:str=tt-dst
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=opts)

            self.len(0, await core.nodes('test:str=tt-src'))
            self.len(0, await core.nodes('test:str=tt-src', opts=opts))

            # dst's tombstone was cleared, so the tag src held live in the fork is visible
            # rather than written and immediately masked
            fork = (await core.nodes('test:str=tt-dst', opts=opts))[0]
            self.isin('masked', dict(fork.getTags()))

            # what src held live in the BASE layer transferred there, since a tombstone only
            # makes src's state absent in the layer holding the tombstone
            self.eq('basestr', fork.getTagProp('gone', '_str'))
            self.eq([('basekey', 'basevalu')], [item async for item in fork.iterData()])
            self.eq(['refs'], [verb async for (verb, nid) in fork.iterEdgesN1()])

            # src's own tombstones in the fork were torn down along with the rest of its
            # state there, rather than being left behind to mask a later node which happens
            # to have the same value
            await core.nodes('[ test:str=tt-src +#gone:_str=newstr ]')
            await core.nodes('test:str=tt-src $node.data.set(basekey, newvalu)')

            again = (await core.nodes('test:str=tt-src', opts=opts))[0]
            self.eq('newstr', again.getTagProp('gone', '_str'))
            self.eq([('basekey', 'newvalu')], [item async for item in again.iterData()])

    async def test_stormlib_model_migration_fuse_novalu_tombstone(self):
        '''
        A layer may hold nothing for src but a tombstone, with no primary property of its own
        to delete, so the tombstone itself is what has to be removed.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=nt-src test:str=nt-dst ]')

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': viewiden}

            # deleting src in the fork leaves the fork holding a tombstone for it rather than
            # a primary property of its own
            await core.nodes('test:str=nt-src | delnode', opts=opts)
            self.len(0, await core.nodes('test:str=nt-src', opts=opts))

            # the fuse runs in the base view, where src is still visible
            await core.nodes('''
                test:str=nt-src $n=$node -> { test:str=nt-dst
                    $lib.model.migration.fuse($n, $node) }
            ''')

            self.len(0, await core.nodes('test:str=nt-src'))
            self.len(0, await core.nodes('test:str=nt-src', opts=opts))
            self.len(1, await core.nodes('test:str=nt-dst', opts=opts))

            # the fork's tombstone was removed rather than left behind to mask a later node
            # which happens to have the same value
            await core.nodes('[ test:str=nt-src ]')
            self.len(1, await core.nodes('test:str=nt-src', opts=opts))

    async def test_stormlib_model_migration_fuse_computed_props_layers(self):
        '''
        dst's computed properties are collected across every layer which holds them, with the
        first layer to name one winning, so a dst present in more than one layer does not
        queue the same computed property twice.
        '''
        async with self.getTestCore() as core:

            # dst lives in the base layer
            await core.nodes('[ test:comp=(20, bbb) ]')

            view1 = await core.callStorm('return($lib.view.get().fork().iden)')
            opts1 = {'view': view1}

            # a first fuse creates dst in fork1's layer, computed properties and all
            await core.nodes('[ test:comp=(10, aaa) +#one ]', opts=opts1)
            await core.nodes('''
                test:comp=(10, aaa) $n=$node -> { test:comp=(20, bbb)
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=opts1)

            # so a second fuse, from a layer below that one, finds dst's computed properties
            # in two layers rather than one
            view2 = await core.callStorm('return($lib.view.get($iden).fork().iden)',
                                         opts={'vars': {'iden': view1}})
            opts2 = {'view': view2}

            await core.nodes('[ test:comp=(30, ccc) +#two ]', opts=opts2)
            await core.nodes('''
                test:comp=(30, ccc) $n=$node -> { test:comp=(20, bbb)
                    $lib.model.migration.fuse($n, $node) }
            ''', opts=opts2)

            self.len(0, await core.nodes('test:comp=(30, ccc)', opts=opts2))

            nodes = await core.nodes('test:comp=(20, bbb)', opts=opts2)
            self.len(1, nodes)
            dst = nodes[0]

            self.propeq(dst, 'hehe', 20)
            self.propeq(dst, 'haha', 'bbb')
            self.isin('one', dict(dst.getTags()))
            self.isin('two', dict(dst.getTags()))

            # and it is liftable by a computed property from the newest fork
            nodes = await core.nodes('test:comp:hehe=20', opts=opts2)
            self.len(1, nodes)
            self.eq((('test:int', 20), ('test:lower', 'bbb')), nodes[0].ndef[1])

    async def test_stormlib_model_migration_fuse_stale_comp_prop(self):
        '''
        A comp node whose computed comp key property disagrees with its own primary value is
        discovered as a cascade rename by that property, but has no new value to rename to.
        The fuse refuses while nothing has been changed yet.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ test:int=10 test:int=20 ]')
            comp = (await core.nodes('[ test:comp=(99, zzz) ]'))[0]

            # point the comp's computed hehe property at test:int=10 without touching the
            # comp's own primary value, which still says 99
            prop = core.model.prop('test:comp:hehe')
            (stortype, virts) = prop.type.getStorInfo(('test:int', 10))

            # the outer nodeedit names its node by plain int, while Node.nid is the 8 byte
            # encoded form the layer indexes with
            await core.getLayer().saveNodeEdits([
                (s_common.int64un(comp.nid), 'test:comp', (
                    (s_layer.EDIT_PROP_SET, ('hehe', ('test:int', 10), stortype, virts)),
                )),
            ], {})

            self.len(1, await core.nodes('test:comp:hehe=10'))

            await self.asyncraises(s_exc.BadTypeValu, core.nodes('''
                test:int=10 $n=$node -> { test:int=20
                    $lib.model.migration.fuse($n, $node) }
            '''))

            # nothing was changed
            self.len(1, await core.nodes('test:int=10'))
            nodes = await core.nodes('test:comp')
            self.len(1, nodes)
            self.eq((('test:int', 99), ('test:lower', 'zzz')), nodes[0].ndef[1])

    async def test_stormlib_model_migration_fuse_renorm_failure(self):
        '''
        Re-normalizing a rewritten value can fail. A comp form's own primary value is refused
        before anything is applied, while an array property is left un-normalized with a
        warning rather than left pointing at a node which is about to be deleted.
        '''
        async with self.getTestCore() as core:

            # --- a comp form's new primary value cannot be re-normalized ---

            await core.nodes('[ test:int=10 test:int=20 ]')
            await core.nodes('[ test:comp=(10, aaa) ]')

            comptype = core.model.form('test:comp').type

            with mock.patch.object(comptype, 'normFromTypedValu',
                                   side_effect=s_exc.BadTypeValu(mesg='comp boom')):
                await self.asyncraises(s_exc.BadTypeValu, core.nodes('''
                    test:int=10 $n=$node -> { test:int=20
                        $lib.model.migration.fuse($n, $node) }
                '''))

            # the refusal happened during discovery, so nothing was changed
            self.len(1, await core.nodes('test:int=10'))
            self.len(1, await core.nodes('test:comp=(10, aaa)'))

            # --- an array property cannot be re-normalized ---

            srcguid = s_common.guid()
            dstguid = s_common.guid()
            opts = {'vars': {'srcguid': srcguid, 'dstguid': dstguid}}

            await core.nodes('[ test:arrayprop=$dstguid ]', opts=opts)
            await core.nodes('''
                [ test:arrayprop=$srcguid :children+={ test:arrayprop=$srcguid } ]
            ''', opts=opts)

            arrtype = core.model.prop('test:arrayprop:children').type

            with mock.patch.object(arrtype, 'normFromTypedValu',
                                   side_effect=s_exc.BadTypeValu(mesg='array boom')):
                mesgs = await core.stormlist('''
                    test:arrayprop=$srcguid $n=$node -> { test:arrayprop=$dstguid
                        $lib.model.migration.fuse($n, $node) }
                ''', opts=opts)

            self.stormIsInWarn('cannot re-normalize array property', mesgs)

            # the reference still followed the node rather than being left dangling
            self.len(0, await core.nodes('test:arrayprop=$srcguid', opts=opts))
            nodes = await core.nodes('test:arrayprop=$dstguid', opts=opts)
            self.len(1, nodes)
            self.eq((('test:arrayprop', dstguid),), nodes[0].get('children'))

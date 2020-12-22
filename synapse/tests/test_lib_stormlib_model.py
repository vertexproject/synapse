import synapse.exc as s_exc
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
            self.eq(nodes[0].ndef, ('test:str', 'True'))

            self.eq('inet:dns:a', await core.callStorm('return($lib.model.form(inet:dns:a).type.name)'))
            self.eq('inet:ipv4', await core.callStorm('return($lib.model.prop(inet:dns:a:ipv4).type.name)'))
            self.eq(s_layer.STOR_TYPE_U32, await core.callStorm('return($lib.model.prop(inet:dns:a:ipv4).type.stortype)'))
            self.eq('inet:dns:a', await core.callStorm('return($lib.model.type(inet:dns:a).name)'))

            self.eq('1.2.3.4', await core.callStorm('return($lib.model.type(inet:ipv4).repr($(0x01020304)))'))
            self.eq(0x01020304, await core.callStorm('return($lib.model.type(inet:ipv4).norm(1.2.3.4).index(0))'))
            self.eq('inet:dns:a:ipv4', await core.callStorm('return($lib.model.form(inet:dns:a).prop(ipv4).full)'))
            self.eq('inet:dns:a', await core.callStorm('return($lib.model.prop(inet:dns:a:ipv4).form.name)'))

            await core.addTagProp('score', ('int', {}), {})
            self.eq('score', await core.callStorm('return($lib.model.tagprop(score).name)'))
            self.eq('int', await core.callStorm('return($lib.model.tagprop(score).type.name)'))

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
                self.stormIsInPrint('The argument <key> is required', mesgs)

                with self.raises(s_exc.NoSuchProp):
                    await core.nodes('model.edge.set refs newp foo')

                mesgs = await core.stormlist('model.edge.set refs doc')
                self.stormIsInPrint('The argument <valu> is required', mesgs)

                with self.raises(s_exc.NoSuchName):
                    await core.nodes('model.edge.set newp doc yowza')

                # Error conditions - get
                mesgs = await core.stormlist('model.edge.get')
                self.stormIsInPrint('The argument <verb> is required', mesgs)

                with self.raises(s_exc.NoSuchName):
                    await core.nodes('model.edge.get newp')

                # Error conditions - del
                mesgs = await core.stormlist('model.edge.del missing')
                self.stormIsInPrint('The argument <key> is required', mesgs)

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

                mesgs = await core.stormlist('model.deprecated.locks')
                self.stormIsInPrint('ou:org:sic: True', mesgs)
                self.stormIsInPrint('ou:hasalias: True', mesgs)
                self.stormIsInPrint('it:reveng:funcstr: False', mesgs)

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
                self.stormIsInPrint('it:reveng:funcstr: True', mesgs)

                await core.nodes('ou:org [ -:sic ]')
                await core.nodes('ou:hasalias | delnode')

                mesgs = await core.stormlist('model.deprecated.check')
                self.stormIsInPrint('Congrats!', mesgs)

import synapse.exc as s_exc
import synapse.tests.utils as s_test

class EdgeInfoTest(s_test.SynTest):

    async def test_stormlib_edgeinfo(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                user = await core.auth.addUser('ham')
                asuser = {'user': user.iden}

                mesgs = await core.stormlist('edge.list', opts=asuser)
                self.stormIsInPrint('No edge entries found', mesgs)

                await core.nodes('[ media:news="*" ]')
                await core.nodes('[ inet:ipv4=1.2.3.4 ]')

                await core.nodes('media:news [ +(refs)> {inet:ipv4=1.2.3.4} ]')

                # Basics
                mesgs = await core.stormlist('edge.list', opts=asuser)
                self.stormIsInPrint('refs', mesgs)

                mesgs = await core.stormlist('edge.set refs "foobar"', opts=asuser)
                self.stormIsInPrint('Set edge info: refs', mesgs)

                mesgs = await core.stormlist('edge.list', opts=asuser)
                self.stormIsInPrint('foobar', mesgs)

                mesgs = await core.stormlist('edge.get refs', opts=asuser)
                self.stormIsInPrint('foobar', mesgs)

                await core.stormlist('edge.set refs "boom bam"', opts=asuser)
                mesgs = await core.stormlist('edge.get refs')
                self.stormIsInPrint('boom bam', mesgs)

                # Multiple verbs
                await core.nodes('media:news [ +(cat)> {inet:ipv4=1.2.3.4} ]')
                await core.nodes('media:news [ <(dog)+ {inet:ipv4=1.2.3.4} ]')
                await core.nodes('edge.set cat "ran up a tree"')

                mesgs = await core.stormlist('edge.list')
                self.stormIsInPrint('boom bam', mesgs)
                self.stormIsInPrint('cat', mesgs)
                self.stormIsInPrint('dog', mesgs)

                # Multiple adds on a verb
                await core.nodes('[ media:news="*" +(refs)> { [inet:ipv4=2.3.4.5] } ]')
                await core.nodes('[ media:news="*" +(refs)> { [inet:ipv4=3.4.5.6] } ]')
                elist = await core.callStorm('return($lib.edge.list())')
                self.sorteq(['refs', 'cat', 'dog'], [e[0] for e in elist])

                # Delete entry
                mesgs = await core.stormlist('edge.del refs', opts=asuser)
                self.stormIsInPrint('Deleted edge entry', mesgs)

                elist = await core.callStorm('return($lib.edge.list())')
                self.notin('refs', [e[0] for e in elist])

                # Deleting the actual edge doesn't change the entry
                await core.nodes('media:news [ -(cat)> {inet:ipv4=1.2.3.4} ]')
                self.nn(await core.callStorm('return($lib.edge.get(cat))'))

                # Error conditions
                mesgs = await core.stormlist('edge.set missing')
                self.stormIsInPrint('The argument <info> is required', mesgs)

                mesgs = await core.stormlist('edge.get newp')
                self.stormIsInPrint('Edge entry not found', mesgs)

                with self.raises(s_exc.NoSuchName):
                    await core.nodes('edge.set newp "newp newp"')

                with self.raises(s_exc.NoSuchName):
                    await core.nodes('edge.del newp')

            # edge defintions persist
            async with self.getTestCore(dirn=dirn) as core:
                elist = await core.callStorm('return($lib.edge.list())')
                self.sorteq([('cat', 'ran up a tree'), ('dog', '')], [(e[0], e[1]['info']) for e in elist])

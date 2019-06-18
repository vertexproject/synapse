import synapse.common as s_common
import synapse.tests.utils as s_test

class AstTest(s_test.SynTest):

    async def test_ast_subq_vars(self):

        async with self.getTestCore() as core:

            # Show a runtime variable being smashed by a subquery
            # variable assignment
            q = '''
                $loc=newp
                [ test:comp=(10, lulz) ]
                { -> test:int [ :loc=haha ] $loc=:loc }
                $lib.print($loc)
            '''
            msgs = await core.streamstorm(q).list()
            self.stormIsInPrint('haha', msgs)

            # Show that a computed variable being smashed by a
            # subquery variable assignment with multiple nodes
            # traveling through a subquery.
            async with await core.snap() as snap:
                await snap.addNode('test:comp', (30, 'w00t'))
                await snap.addNode('test:comp', (40, 'w00t'))
                await snap.addNode('test:int', 30, {'loc': 'sol'})
                await snap.addNode('test:int', 40, {'loc': 'mars'})

            q = '''
                test:comp:haha=w00t
                { -> test:int $loc=:loc }
                $lib.print($loc)
                -test:comp
            '''
            msgs = await core.streamstorm(q).list()
            self.stormIsInPrint('sol', msgs)
            self.stormIsInPrint('mars', msgs)

import synapse.common as s_common
import synapse.tests.utils as s_test

class AstTest(s_test.SynTest):

    async def test_ast_subq_vars(self):

        async with self.getTestCore() as core:

            q = '''
                $loc=newp
                [ test:comp=(10, lulz) ]
                { -> test:int [ :loc=haha ] $loc=:loc }
                $lib.print($loc)
            '''
            msgs = [m async for m in core.streamstorm(q)]
            self.printed(msgs, 'haha')

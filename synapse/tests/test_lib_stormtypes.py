import synapse.tests.utils as s_test

class StormTypesTest(s_test.SynTest):

    async def test_storm_node_tags(self):

        async with self.getTestCore() as core:

            await core.eval('[ test:comp=(20, haha) +#foo +#bar test:comp=(30, hoho) ]').list()

            q = '''
            test:comp
            for $tag in $node.tags() {
                -> test:int [ +#$tag ]
            }
            '''

            await core.eval(q).list()

            self.len(1, await core.eval('test:int#foo').list())
            self.len(1, await core.eval('test:int#bar').list())

            q = '''
            test:comp
            for $tag in $node.tags(fo*) {
                -> test:int [ -#$tag ]
            }
            '''
            await core.eval(q).list()

            self.len(0, await core.eval('test:int#foo').list())
            self.len(1, await core.eval('test:int#bar').list())

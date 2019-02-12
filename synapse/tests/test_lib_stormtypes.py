import synapse.tests.utils as s_test

class StormTypesTest(s_test.SynTest):

    async def test_storm_node_tags(self):

        async with self.getTestCore() as core:

            await core.eval('[ testcomp=(20, haha) +#foo +#bar testcomp=(30, hoho) ]').list()

            q = '''
            testcomp
            for $tag in $node.tags() {
                -> testint [ +#$tag ]
            }
            '''

            await core.eval(q).list()

            self.len(1, await core.eval('testint#foo').list())
            self.len(1, await core.eval('testint#bar').list())

            q = '''
            testcomp
            for $tag in $node.tags(fo*) {
                -> testint [ -#$tag ]
            }
            '''
            await core.eval(q).list()

            self.len(0, await core.eval('testint#foo').list())
            self.len(1, await core.eval('testint#bar').list())

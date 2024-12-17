import synapse.exc as s_exc
import synapse.tests.utils as s_test

class TodoTest(s_test.SynTest):

    async def test_lib_stormlib_todo(self):

        async with self.getTestCore() as core:

            valu = await core.callStorm('return($lib.todo.parse("foo"))')
            self.eq(valu, ('foo', (), {}))

            valu = await core.callStorm('return($lib.todo.parse("foo bar baz"))')
            self.eq(valu, ('foo', ('bar', 'baz'), {}))

            valu = await core.callStorm('return($lib.todo.parse("foo bar baz --key valu"))')
            self.eq(valu, ('foo', ('bar', 'baz'), {'key': 'valu'}))

            valu = await core.callStorm('return($lib.todo.parse(("foo", ("bar", "baz"), ({"key": "valu"}))))')
            self.eq(valu, ('foo', ('bar', 'baz'), {'key': 'valu'}))

            q = '''
                $todo = $lib.todo.parse("foo bar baz --key valu")
                return(($todo.name, $todo.args, $todo.kwargs))
            '''
            valu = await core.callStorm(q)
            self.eq(valu, ('foo', ('bar', 'baz'), {'key': 'valu'}))

            valu = await core.callStorm('return($lib.todo.parse(("foo",)))')
            self.eq(valu, ('foo', (), {}))

            valu = await core.callStorm('return($lib.todo.parse(("foo", ("bar", "baz"))))')
            self.eq(valu, ('foo', ('bar', 'baz'), {}))

            valu = await core.callStorm('return($lib.todo.parse(("foo", "bar")))')
            self.eq(valu, ('foo', ('bar',), {}))

            valu = await core.callStorm('return($lib.todo.parse("just_a_name"))')
            self.eq(valu, ('just_a_name', (), {}))

            valu = await core.callStorm('return($lib.todo.parse(42))')
            self.eq(valu, ('42', (), {}))

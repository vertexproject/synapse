import synapse.exc as s_exc

import synapse.lib.stormlib.json as s_json

import synapse.tests.utils as s_test

class JsonTest(s_test.SynTest):

    async def test_stormlib_json(self):

        async with self.getTestCore() as core:

            self.eq(((1, 2, 3)), await core.callStorm('return($lib.json.load("[1, 2, 3]"))'))
            self.eq(('["foo", "bar", "baz"]'), await core.callStorm('return($lib.json.save((foo, bar, baz)))'))

            with self.raises(s_exc.BadJsonText):
                await core.callStorm('return($lib.json.load(foo))')

            with self.raises(s_exc.MustBeJsonSafe):
                await core.callStorm('return($lib.json.save($lib.print))')

            # jsonschema tests
            self.true(s_json.compileJsSchema(s_test.test_schema))
            resp = s_json.runJsSchema(s_test.test_schema, {'key:integer': 137})
            self.eq(137, resp.get('key:integer'))
            self.eq('Default string!', resp.get('key:string'))

            opts = {'vars': {'schema': s_test.test_schema}}
            q = '''$schemaObj = $lib.json.schema($schema)
            $item=$lib.dict()
            $item."key:integer"=(4)
            return ( $schemaObj.validate($item) )
            '''
            isok, valu = await core.callStorm(q, opts=opts)
            self.true(isok)
            self.eq(4, valu.get('key:integer'))
            self.eq('Default string!', valu.get('key:string'))

            q = '''$schemaObj = $lib.json.schema($schema)
            $item=$lib.dict()
            $item."key:integer"=4
            return ( $schemaObj.validate($item) )
            '''
            isok, valu = await core.callStorm(q, opts=opts)
            self.false(isok)
            self.eq('data.key:integer must be integer', valu.get('mesg'))

            with self.raises(s_exc.StormRuntimeError):
                q = '$schemaObj=$lib.json.schema((foo, bar))'
                await core.callStorm(q)

            q = '''
            $schemaObj = $lib.json.schema($schema, use_default=$lib.false)
            $item = ({"key:integer": 4})
            return($schemaObj.validate($item))
            '''
            isok, valu = await core.callStorm(q, opts={'vars': {'schema': s_test.test_schema}})
            self.true(isok)
            self.eq(4, valu.get('key:integer'))
            self.notin('key:string', valu)

            # Print a json schema obj
            q = "$schemaObj = $lib.json.schema($schema) $lib.print('schema={s}', s=$schemaObj)"
            msgs = await core.stormlist(q, opts=opts)
            self.stormIsInPrint('storm:json:schema: {', msgs)

            q = "$schemaObj = $lib.json.schema($schema) return ( $schemaObj.schema() )"
            schema = await core.callStorm(q, opts=opts)
            self.eq(schema, s_test.test_schema)

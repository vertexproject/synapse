import io
import json

import orjson

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json

import synapse.tests.utils as s_test

class JsonTest(s_test.SynTest):

    async def test_lib_json_loads(self):
        self.eq({'a': 'b'}, s_json.loads('{"a": "b"}'))

        with self.raises(s_exc.BadJsonText) as exc:
            s_json.loads('newp')
        self.eq(exc.exception.get('mesg'), 'Expecting value: line 1 column 1 (char 0)')

    async def test_lib_json_load(self):
        with self.getTestDir() as dirn:

            with s_common.genfile(dirn, 'file00') as file00:
                file00.write(b'{"a": "b"}')

            with s_common.genfile(dirn, 'file00') as file00:
                self.eq({'a': 'b'}, s_json.load(file00))

            with s_common.genfile(dirn, 'empty') as empty:
                with self.raises(s_exc.BadJsonText) as exc:
                    s_json.load(empty)
                self.eq(exc.exception.get('mesg'), 'Expecting value: line 1 column 1 (char 0)')

            buf = io.BytesIO(b'{"a": "b"}')
            self.eq({'a': 'b'}, s_json.load(buf))

            buf = io.StringIO('{"a": "b"}')
            self.eq({'a': 'b'}, s_json.load(buf))

    async def test_lib_json_load_surrogates(self):

        inval = '{"a": "😀\ud83d\ude47"}'
        outval = {'a': '😀\ud83d\ude47'}

        # orjson.dumps fails because of the surrogate pairs
        with self.raises(orjson.JSONDecodeError):
            orjson.loads(inval)

        # stdlib json.loads passes because of voodoo magic
        self.eq(outval, json.loads(inval))

        self.eq(outval, s_json.loads(inval))

        buf = io.StringIO(inval)
        self.eq(outval, s_json.load(buf))

        buf = io.BytesIO(inval.encode('utf8', errors='surrogatepass'))
        self.eq(outval, s_json.load(buf))

    async def test_lib_json_dump_surrogates(self):
        inval = {'a': '😀\ud83d\ude47'}
        outval = b'{"a": "\\ud83d\\ude00\\ud83d\\ude47"}'

        # orjson.dumps fails because of the surrogate pairs
        with self.raises(TypeError):
            orjson.dumps(inval)

        # stdlib json.dumps passes because of voodoo magic
        self.eq(outval.decode(), json.dumps(inval))

        self.eq(outval, s_json.dumps(inval))
        self.eq(outval + b'\n', s_json.dumps(inval, newline=True))

        buf = io.BytesIO()
        s_json.dump(inval, buf)
        self.eq(outval, buf.getvalue())

    async def test_lib_json_dumps(self):
        self.eq(b'{"c":"d","a":"b"}', s_json.dumps({'c': 'd', 'a': 'b'}))
        self.eq(b'{"a":"b","c":"d"}', s_json.dumps({'c': 'd', 'a': 'b'}, sort_keys=True))
        self.eq(b'{\n  "c": "d",\n  "a": "b"\n}', s_json.dumps({'c': 'd', 'a': 'b'}, indent=True))
        self.eq(b'{"c":"d","a":"b"}\n', s_json.dumps({'c': 'd', 'a': 'b'}, newline=True))

        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.dumps({}.items())
        self.eq(exc.exception.get('mesg'), 'Type is not JSON serializable: dict_items')

        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.dumps({1: 'foo'})
        self.eq(exc.exception.get('mesg'), 'Dict key must be str')

        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.dumps({'\ud83d\ude47': {}.items()})
        self.eq(exc.exception.get('mesg'), 'Object of type dict_items is not JSON serializable')

        self.eq(b'"dict_items([])"', s_json.dumps({}.items(), default=str))

    async def test_lib_json_dump(self):
        with self.getTestDir() as dirn:
            binfn = s_common.genpath(dirn, 'bin.json')

            with open(binfn, 'wb') as binfp:
                s_json.dump({'c': 'd', 'a': 'b'}, binfp)

            with open(binfn, 'rb') as binfp:
                self.eq(b'{"c":"d","a":"b"}', binfp.read())

        buf = io.BytesIO()
        s_json.dump({'c': 'd', 'a': 'b'}, buf)
        self.eq(b'{"c":"d","a":"b"}', buf.getvalue())

    async def test_jsload(self):
        with self.getTestDir() as dirn:
            with s_common.genfile(dirn, 'jsload.json') as fp:
                fp.write(b'{"a":"b"}')

            obj = s_json.jsload(dirn, 'jsload.json')
            self.eq({'a': 'b'}, obj)

            s_common.genfile(dirn, 'empty.json').close()
            self.none(s_json.jsload(dirn, 'empty.json'))

    async def test_jslines(self):
        with self.getTestDir() as dirn:
            with s_common.genfile(dirn, 'jslines.json') as fp:
                fp.write(b'{"a":"b"}\n{"c":"d"}')

            objs = [k for k in s_json.jslines(dirn, 'jslines.json')]
            self.len(2, objs)
            self.eq([{'a': 'b'}, {'c': 'd'}], objs)

    async def test_jssave(self):
        with self.getTestDir() as dirn:
            s_json.jssave({'a': 'b'}, dirn, 'jssave.json')

            with s_common.genfile(dirn, 'jssave.json') as fd:
                data = fd.read()

            self.eq(data, b'{\n  "a": "b"\n}')

    async def test_lib_json_reqjsonsafe(self):
        self.none(s_json.reqjsonsafe('foo'))
        self.none(s_json.reqjsonsafe({'foo': 'bar'}))
        self.none(s_json.reqjsonsafe(['foo', 'bar']))

        buf = io.BytesIO()

        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.reqjsonsafe(buf)
        self.isin('Type is not JSON serializable: _io.BytesIO', exc.exception.get('mesg'))

        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.reqjsonsafe({'foo': buf})
        self.isin('Type is not JSON serializable: _io.BytesIO', exc.exception.get('mesg'))

        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.reqjsonsafe(['foo', buf])
        self.isin('Type is not JSON serializable: _io.BytesIO', exc.exception.get('mesg'))

        items = (
            (None, None),
            (1234, None),
            ('1234', None),
            ({'asdf': 'haha'}, None),
            ({'a': (1,), 'b': [{'': 4}, 56, None, {'t': True, 'f': False}, 'oh my']}, None),
            (b'1234', s_exc.MustBeJsonSafe),
            ({'a': 'a', 2: 2}, s_exc.MustBeJsonSafe),
            ({'a', 'b', 'c'}, s_exc.MustBeJsonSafe),
            (s_common.novalu, s_exc.MustBeJsonSafe),
        )
        for (item, eret) in items:
            if eret is None:
                self.none(s_json.reqjsonsafe(item))
            else:
                with self.raises(eret):
                    s_json.reqjsonsafe(item)

        text = '😀\ud83d\ude47'
        s_json.reqjsonsafe(text)
        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.reqjsonsafe(text, strict=True)
        self.eq(exc.exception.get('mesg'), 'str is not valid UTF-8: surrogates not allowed')

    async def test_lib_json_data_at_rest(self):
        async with self.getRegrCore('json-data') as core:
            badjson = {
                1: 'foo',
                'foo': '😀\ud83d\ude47',
            }

            goodjson = {
                '1': 'foo',
                'foo': '😀',
            }

            # We can lift nodes with bad :data
            nodes = await core.nodes('it:log:event')
            self.len(1, nodes)
            self.eq(nodes[0].get('data'), badjson)

            iden = nodes[0].iden()

            # We can't lift nodes with bad data by querying the prop directly
            opts = {'vars': {'data': badjson}}
            with self.raises(s_exc.BadTypeValu):
                await core.callStorm('it:log:event:data=$data', opts=opts)

            # We can't set nodes with bad data
            with self.raises(s_exc.BadTypeValu):
                await core.callStorm('[ it:log:event=* :data=$data ]', opts=opts)

            # We can overwrite bad :data props
            opts = {'vars': {'data': goodjson}}
            nodes = await core.nodes('it:log:event:data [ :data=$data ]', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].iden(), iden)
            self.eq(nodes[0].get('data'), goodjson)

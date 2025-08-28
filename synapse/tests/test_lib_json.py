import io
import json

import yyjson

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

        # yyjson.loads fails because of the surrogate pairs
        with self.raises(ValueError):
            yyjson.loads(inval)

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

        # yyjson.dumps fails because of the surrogate pairs
        with self.raises(UnicodeEncodeError):
            yyjson.dumps(inval)

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
        self.eq(exc.exception.get('mesg'), "TypeError: Object of type 'dict_items' is not JSON serializable")

        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.dumps({1: 'foo'})
        self.eq(exc.exception.get('mesg'), "TypeError: Dictionary keys must be strings")

        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.dumps({'\ud83d\ude47': {}.items()})
        self.eq(exc.exception.get('mesg'), "TypeError: Dictionary keys must be strings")

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

    async def test_lib_json_large_integers(self):
        valu = [
            1, 2,
            -1, -2,
            1.0, 2.0,
            -1.0, -2.0,
            2**63, -2**63, -2**63 - 1,
            2**64, -2**64, 2**64 + 1,
            2**128, 2**128 + 1,
            -2**128, -2**128 - 1,
        ]

        self.eq(valu, s_json.loads(s_json.dumps(valu)))

    async def test_lib_json_control_strings(self):
        valus = [
            'line1"line2',
            'line1/line2',
            'line1\\line2',
            'line1\bline2',
            'line1\fline2',
            'line1\nline2',
            'line1\rline2',
            'line1\tline2',
            'line1\u0009line2',
            'line1\u1000line2',
            'line1\u2000line2',
            'line1\u3000line2',
        ]

        with self.getLoggerStream('synapse.lib.json') as stream:
            async with self.getTestCore() as core:
                for valu in valus:
                    q = '$lib.print($valu) $lib.print($lib.json.save($valu))'
                    msgs = await core.stormlist(q, opts={'vars': {'valu': valu}})
                    self.stormHasNoWarnErr(msgs)

                    self.eq(s_json.loads(s_json.dumps(valu)), valu)

        stream.seek(0)
        data = stream.read()
        self.notin('fallback JSON', data)

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

        msg = "Object of type '_io.BytesIO' is not JSON serializable"
        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.reqjsonsafe(buf)
        self.isin(msg, exc.exception.get('mesg'))

        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.reqjsonsafe({'foo': buf})
        self.isin(msg, exc.exception.get('mesg'))

        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.reqjsonsafe(['foo', buf])
        self.isin(msg, exc.exception.get('mesg'))

        items = (
            (None, None),
            (1234, None),
            ('1234', None),
            ('1234"', None),
            ({'asdf': 'haha'}, None),
            ({'a': (1,), 'b': [{'': 4}, 56, None, {'t': True, 'f': False}, 'oh my']}, None),
            (b'1234', s_exc.MustBeJsonSafe),
            (b'1234"', s_exc.MustBeJsonSafe),
            ({'a': float('nan')}, s_exc.MustBeJsonSafe),
            ({'a': 'a', 2: 2}, s_exc.MustBeJsonSafe),
            ({'a', 'b', 'c'}, s_exc.MustBeJsonSafe),
            (s_common.novalu, s_exc.MustBeJsonSafe),
        )
        for (item, eret) in items:
            if eret is None:
                self.none(s_json.reqjsonsafe(item), msg=item)
            else:
                with self.raises(eret):
                    s_json.reqjsonsafe(item)

        for text in ['😀', 'asdf', 'asdf"', '"asdf']:
            s_json.reqjsonsafe(text)

        text = ['😀\ud83d\ude47']
        s_json.reqjsonsafe(text)
        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.reqjsonsafe(text, strict=True)
        self.eq(exc.exception.get('mesg'), "'utf-8' codec can't encode characters in position 1-2: surrogates not allowed")

        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.reqjsonsafe(b'1234', strict=True)
        self.eq(exc.exception.get('mesg'), 'Object of type bytes is not JSON serializable')

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

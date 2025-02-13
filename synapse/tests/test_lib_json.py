import io

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json

import synapse.tests.utils as s_test

class JsonTest(s_test.SynTest):

    async def test_lib_json_loads(self):
        self.eq({'a': 'b'}, s_json.loads('{"a": "b"}'))

        with self.raises(s_exc.BadJsonText) as exc:
            s_json.loads('newp')
        self.eq(exc.exception.get('mesg'), 'invalid literal: line 1 column 1 (char 0)')

    async def test_lib_json_load(self):
        with self.getTestDir() as dirn:

            with s_common.genfile(dirn, 'file00') as file00:
                file00.write(b'{"a": "b"}')

            with s_common.genfile(dirn, 'file00') as file00:
                self.eq({'a': 'b'}, s_json.load(file00))

            with s_common.genfile(dirn, 'empty') as empty:
                with self.raises(s_exc.BadJsonText) as exc:
                    s_json.load(empty)
                self.eq(exc.exception.get('mesg'), 'Cannot read empty file.')

            buf = io.BytesIO(b'{"a": "b"}')
            self.eq({'a': 'b'}, s_json.load(buf))

            buf = io.StringIO('{"a": "b"}')
            self.eq({'a': 'b'}, s_json.load(buf))

    async def test_lib_json_dumps(self):
        self.eq('{"c":"d","a":"b"}', s_json.dumps({'c': 'd', 'a': 'b'}))
        self.eq('{"a":"b","c":"d"}', s_json.dumps({'c': 'd', 'a': 'b'}, sort_keys=True))
        self.eq('{\n  "c": "d",\n  "a": "b"\n}', s_json.dumps({'c': 'd', 'a': 'b'}, indent=True))
        self.eq(b'{"c":"d","a":"b"}', s_json.dumps({'c': 'd', 'a': 'b'}, asbytes=True))
        self.eq('{"c":"d","a":"b"}\n', s_json.dumps({'c': 'd', 'a': 'b'}, append_newline=True))

        with self.raises(s_exc.MustBeJsonSafe) as exc:
            s_json.dumps({}.items())
        self.eq(exc.exception.get('mesg'), 'Type is not JSON serializable: dict_items')

        self.eq('"dict_items([])"', s_json.dumps({}.items(), default=str))

    async def test_lib_json_dump(self):
        with self.getTestDir() as dirn:
            binfn = s_common.genpath(dirn, 'bin.json')
            txtfn = s_common.genpath(dirn, 'txt.json')

            with open(binfn, 'wb') as binfp:
                s_json.dump({'c': 'd', 'a': 'b'}, binfp)

            with open(binfn, 'rb') as binfp:
                self.eq(b'{"c":"d","a":"b"}', binfp.read())

            with open(txtfn, 'w') as txtfp:
                s_json.dump({'c': 'd', 'a': 'b'}, txtfp)

            with open(txtfn, 'r') as txtfp:
                self.eq('{"c":"d","a":"b"}', txtfp.read())

        buf = io.BytesIO()
        s_json.dump({'c': 'd', 'a': 'b'}, buf)
        self.eq(b'{"c":"d","a":"b"}', buf.getvalue())

        buf = io.StringIO()
        s_json.dump({'c': 'd', 'a': 'b'}, buf)
        self.eq('{"c":"d","a":"b"}', buf.getvalue())

    async def test_jsload(self):
        with self.getTestDir() as dirn:
            with s_common.genfile(dirn, 'jsload.json') as fp:
                fp.write(b'{"a":"b"}')

            obj = s_common.jsload(dirn, 'jsload.json')
            self.eq({'a': 'b'}, obj)

            s_common.genfile(dirn, 'empty.json').close()
            self.none(s_common.jsload(dirn, 'empty.json'))

    async def test_jslines(self):
        with self.getTestDir() as dirn:
            with s_common.genfile(dirn, 'jslines.json') as fp:
                fp.write(b'{"a":"b"}\n{"c":"d"}')

            objs = [k for k in s_common.jslines(dirn, 'jslines.json')]
            self.len(2, objs)
            self.eq([{'a': 'b'}, {'c': 'd'}], objs)

    async def test_jssave(self):
        with self.getTestDir() as dirn:
            s_common.jssave({'a': 'b'}, dirn, 'jssave.json')

            with s_common.genfile(dirn, 'jssave.json') as fd:
                data = fd.read()

            self.eq(data, b'{\n  "a": "b"\n}')

    async def test_lib_json_reqjsonsafe(self):
        pass

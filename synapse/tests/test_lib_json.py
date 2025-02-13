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

            file00 = s_common.genfile(dirn, 'file00')
            file00.write(b'{"a": "b"}')
            file00.close()

            file00 = s_common.genfile(dirn, 'file00')
            self.eq({'a': 'b'}, s_json.load(file00))

            empty = s_common.genfile(dirn, 'empty')

            with self.raises(s_exc.BadJsonText) as exc:
                s_json.load(empty)
            self.eq(exc.exception.get('mesg'), 'Cannot read empty file.')

    # FIXME: Implement below tests if this PR gets the thumbs up during discussion
    async def test_lib_json_dumps(self):
        pass

    async def test_lib_json_dump(self):
        pass

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

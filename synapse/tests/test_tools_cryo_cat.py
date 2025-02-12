import io

import msgpack

import unittest.mock as mock

import synapse.exc as s_exc

import synapse.lib.msgpack as s_msgpack
import synapse.tests.utils as s_t_utils
import synapse.tools.cryo.cat as s_cryocat

class CryoCatTest(s_t_utils.SynTest):

    async def test_cryocat(self):

        async with self.getTestCryo() as cryo:

            cryourl = cryo.getLocalUrl(share='cryotank/hehe')

            argv = ['--ingest', cryourl]
            retn, outp = await self.execToolMain(s_cryocat.main, argv)

            self.eq(1, retn)

            # Happy path jsonl ingest
            outp = self.getTestOutp()
            argv = ['--ingest', '--jsonl', cryourl]
            inp = io.StringIO('{"foo": "bar"}\n[]\n')
            with self.redirectStdin(inp):
                retn, outp = await self.execToolMain(s_cryocat.main, argv)
            self.eq(0, retn)

            # Sad path jsonl ingest
            argv = ['--ingest', '--jsonl', cryourl]
            inp = io.StringIO('{"foo: "bar"}\n[]\n')
            with self.redirectStdin(inp):
                with self.raises(s_exc.BadJsonText):
                    retn, outp = await self.execToolMain(s_cryocat.main, argv)

            # Happy path msgpack ingest
            argv = ['--ingest', '--msgpack', cryourl]
            to_ingest1 = s_msgpack.en({'foo': 'bar'})
            to_ingest2 = s_msgpack.en(['lol', 'brb'])
            inp = mock.Mock()
            inp.buffer = io.BytesIO(to_ingest1 + to_ingest2)
            with self.redirectStdin(inp):
                retn, outp = await self.execToolMain(s_cryocat.main, argv)
            self.eq(0, retn)

            # Sad path msgpack ingest
            argv = ['--ingest', '--msgpack', cryourl]
            good_encoding = s_msgpack.en({'foo': 'bar'})
            bad_encoding = bytearray(good_encoding)
            bad_encoding[2] = 0xff
            inp = mock.Mock()
            inp.buffer = io.BytesIO(bad_encoding)
            with self.redirectStdin(inp):
                with self.raises(msgpack.UnpackValueError):
                    retn, outp = await self.execToolMain(s_cryocat.main, argv)

            argv = ['--offset', '0', '--size', '1', cryourl]
            retn, outp = await self.execToolMain(s_cryocat.main, argv)
            self.eq(0, retn)
            self.true(outp.expect("(0, {'foo': 'bar'})"))

        async with self.getTestCryo() as cryo:

            cryourl = cryo.getLocalUrl(share='cryotank/hehe')

            items = [(None, {'key': i}) for i in range(20)]

            tank = await cryo.init('hehe')
            await tank.puts(items)

            argv = ['--offset', '0', '--jsonl', '--size', '2', '--omit-offset', cryourl]
            retn, outp = await self.execToolMain(s_cryocat.main, argv)
            self.true(outp.expect('[null,{"key":0}]\n[null,{"key":1}]\n'))

            argv = ['--offset', '0', '--size', '20', cryourl]
            retn, outp = await self.execToolMain(s_cryocat.main, argv)
            self.eq(0, retn)
            self.true(outp.expect("(0, (None, {'key': 0}))"))
            self.true(outp.expect("(9, (None, {'key': 9}))"))
            self.true(outp.expect("(19, (None, {'key': 19}))"))

            argv = ['--offset', '10', '--size', '20', cryourl]
            retn, outp = await self.execToolMain(s_cryocat.main, argv)
            self.eq(0, retn)
            self.false(outp.expect("(9, (None, {'key': 9}))", throw=False))

            stdout = mock.Mock()
            stdout.buffer = io.BytesIO()

            with mock.patch('sys.stdout', stdout):
                with self.getLoggerStream('synapse.tools.cryo.cat') as stream:
                    argv = ['--verbose', '--msgpack', '--size', '20', cryourl]
                    retn, _ = await self.execToolMain(s_cryocat.main, argv)
                    self.eq(0, retn)

                stream.seek(0)
                mesgs = stream.read()
                self.isin(f'connecting to: {cryourl}', mesgs)

            stdout.buffer.seek(0)
            outdata = list(msgpack.Unpacker(stdout.buffer, raw=False, use_list=False))
            self.eq(items, outdata)

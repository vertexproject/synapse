import io
from unittest.mock import Mock

import msgpack

import synapse.cryotank as s_cryotank

import synapse.tools.cryo.cat as s_cryocat

from synapse.tests.common import *

class CryoCatTest(SynTest):

    def cell_populate(self, port, auth):
        # Populate the cell with data
        addr = ('127.0.0.1', port)
        user = s_cryotank.CryoUser(auth, addr, timeout=2)
        nodes = [(None, {'key': i}) for i in range(10)]
        user.puts('test:hehe', nodes, 4)
        self.len(10, list(user.slice('test:hehe', 0, 100)))
        user.puts('test:haha', nodes, 4)
        self.len(2, user.list())

    def test_cryocat(self):

        with self.getTestDir() as dirn:

            conf = {'host': '127.0.0.1'}

            celldir = os.path.join(dirn, 'cell')
            authfp = os.path.join(dirn, 'user.auth')

            with s_cryotank.CryoCell(celldir, conf) as cell:

                port = cell.getCellPort()
                auth = cell.genUserAuth('visi@vertex.link')
                self.cell_populate(port, auth)

                with genfile(authfp) as fd:
                    fd.write(s_msgpack.en(auth))
                addr = 'cell://127.0.0.1:%s/%s' % (port, 'test:hehe')

                outp = self.getTestOutp()
                argv = ['--list', addr]
                with self.getLoggerStream('synapse.tools.cryo.cat') as stream:
                    self.eq(s_cryocat.main(argv, outp), 1)
                stream.seek(0)
                log_msgs = stream.read()
                self.isin('Currently requires --authfile', log_msgs)

                outp = self.getTestOutp()
                argv = ['-v', '--list', '--authfile', authfp, addr]
                self.eq(s_cryocat.main(argv, outp), 0)
                self.true(outp.expect('test:hehe'))
                self.true(outp.expect('test:haha'))

                # Make sure that --ingest without a format dies
                outp = self.getTestOutp()
                argv = ['--ingest', '--authfile', authfp, addr]
                self.eq(s_cryocat.main(argv, outp), 1)

                # Happy path jsonl ingest
                outp = self.getTestOutp()
                argv = ['--ingest', '--jsonl', '--authfile', authfp, addr]
                inp = io.StringIO('{"foo": "bar"}\n[]\n')
                with self.redirectStdin(inp):
                    self.eq(s_cryocat.main(argv, outp), 0)

                # Sad path jsonl ingest
                outp = self.getTestOutp()
                argv = ['--ingest', '--jsonl', '--authfile', authfp, addr]
                inp = io.StringIO('{"foo: "bar"}\n[]\n')
                with self.redirectStdin(inp):
                    self.raises(Exception, s_cryocat.main, argv, outp)

                # Happy path msgpack ingest
                outp = self.getTestOutp()
                argv = ['--ingest', '--msgpack', '--authfile', authfp, addr]
                to_ingest1 = s_msgpack.en({'foo': 'bar'})
                to_ingest2 = s_msgpack.en(['lol', 'brb'])
                inp = Mock()
                inp.buffer = io.BytesIO(to_ingest1 + to_ingest2)
                with self.redirectStdin(inp):
                    self.eq(s_cryocat.main(argv, outp), 0)

                # Sad path msgpack ingest
                outp = self.getTestOutp()
                argv = ['--ingest', '--msgpack', '--authfile', authfp, addr]
                good_encoding = s_msgpack.en({'foo': 'bar'})
                bad_encoding = bytearray(good_encoding)
                bad_encoding[2] = 0xff
                inp = Mock()
                inp.buffer = io.BytesIO(bad_encoding)
                with self.redirectStdin(inp):
                    self.raises(msgpack.exceptions.UnpackValueError, s_cryocat.main, argv, outp)

                outp = self.getTestOutp()
                argv = ['--offset', '0', '--size', '1', '--authfile', authfp, addr]
                self.eq(s_cryocat.main(argv, outp), 0)
                self.true(outp.expect("(0, (None, {'key': 0}))"))

                outp = self.getTestOutp()
                argv = ['--offset', '0', '--jsonl', '--size', '2', '--omit-offset', '--authfile', authfp, addr]
                self.eq(s_cryocat.main(argv, outp), 0)
                self.true(outp.expect('[null, {"key": 0}]\n[null, {"key": 1}]\n'))

                outp = self.getTestOutp()
                argv = ['--offset', '0', '--size', '20', '--authfile', authfp, addr]
                self.eq(s_cryocat.main(argv, outp), 0)
                self.true(outp.expect("(0, (None, {'key': 0}))"))
                self.true(outp.expect("(9, (None, {'key': 9}))"))

                # Verify the ingested data
                self.true(outp.expect("(10, {'foo': 'bar'})"))
                self.true(outp.expect("(11, ())"))
                self.true(outp.expect("(12, {'foo': 'bar'})"))
                self.true(outp.expect("(13, ('lol', 'brb'))"))
                self.false(outp.expect("(14, (None, {'key': 10}))", throw=False))

                outp = self.getTestOutp()
                argv = ['--offset', '10', '--size', '20', '--authfile', authfp, addr]
                self.eq(s_cryocat.main(argv, outp), 0)
                self.false(outp.expect("(9, (None, {'key': 9}))", throw=False))
                self.false(outp.expect("(10, (None, {'key': 10}))", throw=False))

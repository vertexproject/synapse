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
                with self.assertLogs(logger='synapse.tools.cryo.cat', level='ERROR') as logs:
                    self.eq(s_cryocat.main(argv, outp), 1)
                self.true(logs[0][0].message.startswith('Currently requires --authfile'))

                outp = self.getTestOutp()
                argv = ['--list', '--authfile', authfp, addr]
                self.eq(s_cryocat.main(argv, outp), 0)
                self.true(outp.expect('test:hehe'))
                self.true(outp.expect('test:haha'))

                outp = self.getTestOutp()
                argv = ['--offset', '0', '--size', '1', '--authfile', authfp, addr]
                self.eq(s_cryocat.main(argv, outp), 0)
                self.true(outp.expect("(0, (None, {'key': 0}))"))

                outp = self.getTestOutp()
                argv = ['--offset', '0', '--jsonl', '--size', '2', '--authfile', authfp, addr]
                self.eq(s_cryocat.main(argv, outp), 0)
                self.true(outp.expect('[0, [null, {"key": 0}]]\n[1, [null, {"key": 1}]]\n'))

                outp = self.getTestOutp()
                argv = ['--offset', '0', '--size', '20', '--authfile', authfp, addr]
                self.eq(s_cryocat.main(argv, outp), 0)
                self.true(outp.expect("(0, (None, {'key': 0}))"))
                self.true(outp.expect("(9, (None, {'key': 9}))"))
                self.false(outp.expect("(10, (None, {'key': 10}))", throw=False))

                outp = self.getTestOutp()
                argv = ['--offset', '10', '--size', '20', '--authfile', authfp, addr]
                self.eq(s_cryocat.main(argv, outp), 0)
                self.false(outp.expect("(9, (None, {'key': 9}))", throw=False))
                self.false(outp.expect("(10, (None, {'key': 10}))", throw=False))

import os

import synapse.common as s_common

import synapse.lib.cmdr as s_cmdr

import synapse.tests.utils as s_t_utils

class CmdHiveTest(s_t_utils.SynTest):

    async def test_hive(self):
        with self.getTestDir() as dirn:
            async with self.getTestDmon('dmoncore') as dmon, await self.agetTestProxy(dmon, 'core') as core:
                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)

                await cmdr.runCmdLine('hive ls notadir')
                self.true(outp.expect('Path not found'))

                await cmdr.runCmdLine('hive edit foo/bar [1,2,3,4]')
                await cmdr.runCmdLine('hive ls')
                self.true(outp.expect('foo'))

                await cmdr.runCmdLine('hive get foo/bar')
                self.true(outp.expect('foo/bar: (1, 2, 3, 4)'))

                await cmdr.runCmdLine('hive ls foo')
                self.true(outp.expect('bar'))

                await cmdr.runCmdLine('hive rm foo')
                outp.clear()
                await cmdr.runCmdLine('hive ls foo')
                self.true(outp.expect('Path not found'))

                fn = os.path.join(dirn, 'test.json')

                with open(fn, 'w') as fh:
                    fh.write('{"foo": 123}')

                await cmdr.runCmdLine(f'hive edit foo/bar2 -f {fn}')
                await cmdr.runCmdLine('hive get foo/bar2')
                self.true(outp.expect("foo/bar2: {'foo': 123}"))

                os.environ['EDITOR'] = 'echo [1,2,3] > '
                await cmdr.runCmdLine(f'hive edit foo/bar3 --editor')
                await cmdr.runCmdLine('hive get foo/bar3')
                self.true(outp.expect('foo/bar3: (1, 2, 3)'))


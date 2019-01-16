import os

import synapse.lib.cmdr as s_cmdr

import synapse.tests.utils as s_t_utils

_json_output = '''[
    1,
    2,
    3,
    4
]'''

class CmdHiveTest(s_t_utils.SynTest):

    async def test_hive(self):
        with self.getTestDir() as dirn:
            async with self.getTestDmon('dmoncore') as dmon, await self.agetTestProxy(dmon, 'core') as core:
                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)

                await cmdr.runCmdLine('hive ls notadir')
                self.true(outp.expect('Path not found'))

                outp.clear()
                await cmdr.runCmdLine('hive edit foo/bar [1,2,3,4]')
                await cmdr.runCmdLine('hive ls')
                self.true(outp.expect('foo'))

                outp.clear()
                await cmdr.runCmdLine('hive get foo/bar')
                self.true(outp.expect('foo/bar:\n(1, 2, 3, 4)'))
                outp.clear()

                await cmdr.runCmdLine('hive get --json foo/bar')
                self.true(outp.expect('foo/bar:\n' + _json_output))

                await cmdr.runCmdLine('hive ls foo')
                self.true(outp.expect('bar'))

                await cmdr.runCmdLine('hive rm foo')
                outp.clear()
                await cmdr.runCmdLine('hive ls foo')
                self.true(outp.expect('Path not found'))

                fn = os.path.join(dirn, 'test.json')

                with open(fn, 'w') as fh:
                    fh.write('{"foo": 123}')

                outp.clear()
                await cmdr.runCmdLine(f'hive edit foo/bar2 -f {fn}')
                await cmdr.runCmdLine('hive get foo/bar2')
                self.true(outp.expect("foo/bar2:\n{'foo': 123}"))

                outp.clear()
                fn = os.path.join(dirn, 'empty.json')
                with open(fn, 'w') as fh:
                    pass
                await cmdr.runCmdLine(f'hive edit foo/empty -f {fn}')
                self.true(outp.expect('Empty file.  Not writing key.'))

                # Editor tests
                outp.clear()
                with self.setTstEnvars(EDITOR='', VISUAL=''):
                    await cmdr.runCmdLine(f'hive edit foo/bar3 --editor')
                    self.true(outp.expect('Environment variable VISUAL or EDITOR must be set for --editor'))

                outp.clear()
                with self.setTstEnvars(EDITOR='echo [1,2,3] > '):

                    await cmdr.runCmdLine(f'hive edit foo/bar3 --editor')
                    await cmdr.runCmdLine('hive get foo/bar3')
                    self.true(outp.expect('foo/bar3:\n(1, 2, 3)'))

                outp.clear()
                with self.setTstEnvars(VISUAL='echo [1,2,3] > '):
                    await cmdr.runCmdLine(f'hive edit foo/bar4 --editor')
                    await cmdr.runCmdLine('hive get foo/bar4')
                    self.true(outp.expect('foo/bar4:\n(1, 2, 3)'))

                outp.clear()
                with self.setTstEnvars(VISUAL='echo [1,2,3] > '):
                    await cmdr.runCmdLine(f'hive edit foo/bar4 --editor')
                    self.true(outp.expect('Valu not changed.  Not writing key.'))

                outp.clear()
                await cmdr.item.setHiveKey(('foo', 'notJson'), {'newp': b'deadb33f'})
                with self.setTstEnvars(VISUAL='echo [1,2,3] > '):
                    await cmdr.runCmdLine(f'hive edit foo/notJson --editor')
                    self.true(outp.expect('Value is not JSON-encodable, therefore not editable.'))

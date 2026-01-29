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

            async with self.getTestCoreAndProxy() as (realcore, core):

                outp = self.getTestOutp()
                cmdr = await s_cmdr.getItemCmdr(core, outp=outp)

                await cmdr.runCmdLine('hive')
                self.true(outp.expect('Manipulates values'))

                await cmdr.runCmdLine('hive notacmd')
                self.true(outp.expect('invalid choice'))

                await cmdr.runCmdLine('hive ls notadir')
                self.true(outp.expect('Path not found'))

                outp.clear()
                await cmdr.runCmdLine('hive mod foo/bar [1,2,3,4]')
                await cmdr.runCmdLine('hive ls')
                self.true(outp.expect('foo'))
                await cmdr.runCmdLine('hive list')
                self.true(outp.expect('foo'))

                outp.clear()
                await cmdr.runCmdLine('hive get notakey')
                self.true(outp.expect('not present'))

                outp.clear()
                await cmdr.runCmdLine('hive get foo/bar')
                self.true(outp.expect('foo/bar:\n(1, 2, 3, 4)'))

                outp.clear()
                await cmdr.runCmdLine('hive get --json foo/bar')
                self.true(outp.expect('foo/bar:\n' + _json_output))

                outp.clear()
                await core.setHiveKey(('bin',), b'1234')
                await cmdr.runCmdLine('hive get bin')
                self.true(outp.expect("bin:\nb'1234'"))

                await cmdr.runCmdLine('hive ls foo')
                self.true(outp.expect('bar'))

                await cmdr.runCmdLine('hive rm foo')
                outp.clear()
                await cmdr.runCmdLine('hive ls foo')
                self.true(outp.expect('Path not found'))

                await cmdr.runCmdLine('hive edit foo/bar [1,2,3,4]')
                await cmdr.runCmdLine('hive del foo')
                outp.clear()
                await cmdr.runCmdLine('hive ls foo')
                self.true(outp.expect('Path not found'))

                fn = os.path.join(dirn, 'test.json')

                with open(fn, 'w') as fh:
                    fh.write('{"foo": 123}')

                outp.clear()
                await cmdr.runCmdLine(f'hive edit foo/foo asimplestring')
                await cmdr.runCmdLine('hive get foo/foo')
                self.true(outp.expect('foo/foo:\nasimplestring'))

                outp.clear()
                await cmdr.runCmdLine(f'hive edit foo/bar2 -f {fn}')
                await cmdr.runCmdLine('hive get foo/bar2')
                self.true(outp.expect("foo/bar2:\n{'foo': 123}"))

                with open(fn, 'w') as fh:
                    fh.write('just a string')

                await cmdr.runCmdLine(f'hive edit --string foo/bar2 -f {fn}')
                await cmdr.runCmdLine('hive get foo/bar2')
                self.true(outp.expect("foo/bar2:\njust a string"))

                ofn = os.path.join(dirn, 'test.output')
                outp.clear()
                await cmdr.runCmdLine(f'hive get --file {ofn} foo/bar2')
                self.true(outp.expect(f'Saved the hive entry [foo/bar2] to {ofn}'))
                with open(ofn, 'rb') as fh:
                    self.eq(fh.read(), b'just a string')

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
                with self.setTstEnvars(EDITOR='echo \'{"foo": 42}\' > '):

                    await cmdr.runCmdLine(f'hive edit foo/bar3 --editor')
                    await cmdr.runCmdLine('hive get foo/bar3')
                    self.true(outp.expect("foo/bar3:\n{'foo': 42}"))

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

                with self.setTstEnvars(VISUAL='echo [1,2,3] > '):
                    await cmdr.runCmdLine(f'hive edit foo/notJson --editor --string')
                    self.true(outp.expect('Existing value is not a string, therefore not editable as a string'))
                    await cmdr.item.setHiveKey(('foo', 'notJson'), 'foo')
                    outp.clear()

                    await cmdr.runCmdLine(f'hive edit foo/notJson --editor --string')
                    await cmdr.runCmdLine('hive get foo/notJson')
                    self.true(outp.expect("foo/notJson:\n[1,2,3]"))

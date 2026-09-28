import sys
import asyncio

import synapse.exc as s_exc

import synapse.lib.cmd as s_cmd

import synapse.tests.utils as s_test

class CmdTest(s_test.SynTest):

    def test_lib_cmd_parser_exitcode(self):

        outp = self.getTestOutp()
        pars = s_cmd.Parser(prog='synapse.tools.newp', outp=outp)
        pars.add_argument('--hehe', type=int)

        with self.raises(s_exc.ParserExit) as cm:
            pars.parse_args(['--help'])
        self.eq(0, cm.exception.get('exitcode'))
        self.none(cm.exception.get('status'))
        outp.expect('usage: synapse.tools.newp')

        with self.raises(s_exc.ParserExit) as cm:
            pars.parse_args(['--hehe', 'haha'])
        self.eq(2, cm.exception.get('exitcode'))
        outp.expect("invalid int value: 'haha'")

    async def runTool(self, *argv):
        # exitmain is only reachable from a real process entry point, so drive the
        # tool as a subprocess to observe the exit code a shell would see.
        proc = await asyncio.create_subprocess_exec(sys.executable, '-m', *argv,
                                                    stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        return proc.returncode, stdout.decode()

    async def test_lib_cmd_exitmain_status(self):

        # --help is a success, not a failure
        rc, text = await self.runTool('synapse.tools.aha.list', '--help')
        self.eq(0, rc)
        self.isin('usage: synapse.tools.aha.list', text)

        rc, text = await self.runTool('synapse.tools.aha.list', '-h')
        self.eq(0, rc)

        # a usage error exits with the argparse convention of 2
        rc, text = await self.runTool('synapse.tools.aha.list', '--newp')
        self.eq(2, rc)
        self.isin('unrecognized arguments: --newp', text)

        # missing required positional args are a usage error as well
        rc, text = await self.runTool('synapse.tools.axon.copy', '--help')
        self.eq(0, rc)

        rc, text = await self.runTool('synapse.tools.axon.copy')
        self.eq(2, rc)

        rc, text = await self.runTool('synapse.tools.cortex.csv', '--help')
        self.eq(0, rc)

        rc, text = await self.runTool('synapse.tools.cortex.csv')
        self.eq(2, rc)

        rc, text = await self.runTool('synapse.tools.service.healthcheck', '--help')
        self.eq(0, rc)

        rc, text = await self.runTool('synapse.tools.service.healthcheck')
        self.eq(2, rc)

        # a usage error from shutdown never contacts the service
        rc, text = await self.runTool('synapse.tools.service.shutdown', '--newp')
        self.eq(2, rc)
        self.notin('Error while attempting graceful shutdown', text)

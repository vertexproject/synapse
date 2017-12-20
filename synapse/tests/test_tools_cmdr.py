import synapse.lib.cli as s_cli
import synapse.lib.cmdr as s_cmdr
import synapse.lib.scope as s_scope
import synapse.lib.mixins as s_mixins

import synapse.tools.cmdr as s_tools_cmdr

from synapse.tests.common import *

class ToolCmdrTest(SynTest):
    def test_tools_cmdr_cli(self):
        with self.getDmonCore() as core:
            link = s_scope.get('syn:test:link')
            port = link[1].get('port')
            url = 'tcp://127.0.0.1:%s/core00' % port

            outp = self.getTestOutp()
            cmdg = CmdGenerator(['help',
                                 'quit'])
            with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
                argv = [url]
                s_tools_cmdr.main(argv, outp)
            self.true(outp.expect('ask'))
            self.true(outp.expect('quit'))
            self.true(outp.expect('o/'))

    def test_tools_cmdr_cliserver(self):
        with self.getRamCore() as core:
            url = 'local://%s/server?retry=10' % guid()

            dmon = s_daemon.Daemon()
            dmon.listen(url)
            server = s_cmdr.CliServer(core)

            dmon.share('server', server, fini=True)

            outp = self.getTestOutp()
            cmdg = CmdGenerator(['help',
                                 'quit'])
            with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
                argv = [url]
                s_tools_cmdr.main(argv, outp)
            self.true(outp.expect('ask'))
            self.true(outp.expect('quit'))
            self.true(outp.expect('o/'))

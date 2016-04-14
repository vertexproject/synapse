
from synapse.tests.common import SynTest
from synapse.tools.dmon import getArgParser

import synapse.lib.cli as s_cli

class TestArgParser(SynTest):

    def test_getArgParser_logLevel(self):
        for level in ['debug', 'info', 'warning', 'error', 'critical']:
            p = getArgParser()
            args = p.parse_args(['--log-level', level])
            self.eq(args.log_level, level)

    def test_getArgParser_logLevel_exception(self):
        for level in ['all', 'notice']:
            with self.assertRaises(s_cli.CmdArgErr):
                p = getArgParser()
                p.parse_args(['--log-level', level])

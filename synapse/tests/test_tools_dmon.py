
import os
import sys
import argparse
import tempfile

import synapse.tools.dmon as s_dmon

from synapse.tests.common import SynTest
from synapse.tools.dmon import getArgParser

class TestArgParser(SynTest):

    def test_getArgParser_logLevel(self):
        for level in ['debug', 'info', 'warning', 'error', 'critical']:
            p = getArgParser()
            args = p.parse_args(['--log-level', level, 'fakedir'])
            self.eq(args.log_level, level.upper())

    def test_getArgParser_logLevel_exception(self):
        for level in ['all', 'notice']:
            with self.raises(SystemExit):
                p = getArgParser()
                p.parse_args(['--log-level', level, 'fakedir'])

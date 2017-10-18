
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
            args = p.parse_args(['--log-level', level])
            self.eq(args.log_level, level.upper())

    def test_getArgParser_logLevel_exception(self):
        for level in ['all', 'notice']:
            with self.raises(SystemExit):
                p = getArgParser()
                p.parse_args(['--log-level', level])

    def test_getArgParser_bools(self):
        p = getArgParser()
        args = p.parse_args(['--lsboot'])
        self.true(args.lsboot)

        args = p.parse_args(['--onboot'])
        self.true(args.onboot)

        args = p.parse_args(['--noboot'])
        self.true(args.noboot)

        args = p.parse_args(['--asboot'])
        self.true(args.asboot)

class TestMain(SynTest):

    def getTempConfig(self):
        t = tempfile.NamedTemporaryFile()
        t.write(b'''
        {
            "title": "my title"
        }''')
        t.flush()
        return t

    def test_main_lsboot(self):
        self.thisHostMustNot(platform='windows')

        tfile = self.getTempConfig()

        out0 = self.getTestOutp()
        out1 = self.getTestOutp()

        s_dmon.main(['--log-level', 'debug', '--lsboot'], out0)
        s_dmon.main(['--noboot', tfile.name], out1)

        tfile.close()

    def test_main_logging(self):

        out0 = self.getTestOutp()
        out1 = self.getTestOutp()

        with self.getLoggerStream('synapse.tools.dmon') as stream:
            s_dmon.main(['--log-level', 'DEBUG', '--lsboot'], out0)
            stream.seek(0)
            mesgs = stream.read()
        self.isin('log level set to DEBUG', mesgs)

        os.environ['SYN_DMON_LOG_LEVEL'] = 'DEBUG'
        with self.getLoggerStream('synapse.tools.dmon') as stream:
            s_dmon.main(['--lsboot'], out1)
            stream.seek(0)
            mesgs = stream.read()
        del os.environ['SYN_DMON_LOG_LEVEL']
        self.isin('log level set to DEBUG', mesgs)

    def test_main_onboot(self):
        self.thisHostMustNot(platform='windows')

        tfile = self.getTempConfig()

        s_dmon.main(['--onboot', tfile.name])
        tfile.close()

import io
import os
import unittest.mock as mock

import synapse.exc as s_exc

import synapse.tests.utils as s_t_utils
import synapse.tools.storm.validate as s_validate

class TestStormValidate(s_t_utils.SynTest):

    async def test_tools_storm_validate_file(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'test.storm')
            with open(fpath, 'w') as fd:
                fd.write('inet:fqdn=example.com\n')

            outp = self.getTestOutp()
            ret = await s_validate.main([fpath], outp=outp)
            self.eq(ret, 0)
            outp.expect('ok')

    async def test_tools_storm_validate_file_bad(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'bad.storm')
            with open(fpath, 'w') as fd:
                fd.write('%%%badquery\n')

            outp = self.getTestOutp()
            ret = await s_validate.main([fpath], outp=outp)
            self.eq(ret, 1)
            outp.expect('BadSyntax')

    async def test_tools_storm_validate_file_bad_column(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'bad.storm')
            with open(fpath, 'w') as fd:
                fd.write('inet:fqdn=x |\n')

            outp = self.getTestOutp()
            ret = await s_validate.main([fpath], outp=outp)
            self.eq(ret, 1)
            outp.expect('BadSyntax')
            outp.expect('column:')

    async def test_tools_storm_validate_stdin(self):
        outp = self.getTestOutp()
        with mock.patch('sys.stdin', io.StringIO('inet:fqdn=example.com\n')):
            ret = await s_validate.main(['-'], outp=outp)
        self.eq(ret, 0)
        outp.expect('ok')

    async def test_tools_storm_validate_stdin_bad(self):
        outp = self.getTestOutp()
        with mock.patch('sys.stdin', io.StringIO('%%%badquery\n')):
            ret = await s_validate.main(['-'], outp=outp)
        self.eq(ret, 1)
        outp.expect('BadSyntax')

    async def test_tools_storm_validate_empty(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'empty.storm')
            with open(fpath, 'w') as fd:
                fd.write('')

            outp = self.getTestOutp()
            ret = await s_validate.main([fpath], outp=outp)
            self.eq(ret, 1)
            outp.expect('No Storm query text provided')

    async def test_tools_storm_validate_empty_stdin(self):
        outp = self.getTestOutp()
        with mock.patch('sys.stdin', io.StringIO('')):
            ret = await s_validate.main(['-'], outp=outp)
        self.eq(ret, 1)
        outp.expect('No Storm query text provided')

    async def test_tools_storm_validate_mode(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'lookup.storm')
            with open(fpath, 'w') as fd:
                fd.write('1.2.3.4\n')

            outp = self.getTestOutp()
            ret = await s_validate.main(['--mode', 'lookup', fpath], outp=outp)
            self.eq(ret, 0)
            outp.expect('ok')

    async def test_tools_storm_validate_help(self):
        outp = self.getTestOutp()
        with self.raises(s_exc.ParserExit):
            await s_validate.main(['-h'], outp=outp)

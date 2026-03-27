import io
import os
import unittest.mock as mock

import synapse.exc as s_exc

import synapse.tests.utils as s_t_utils
import synapse.tools.storm.validate as s_validate

class TestStormValidate(s_t_utils.SynTest):

    async def test_tools_storm_validate_file(self):

        with self.getTestDir() as dirn:

            # Valid query
            fpath = os.path.join(dirn, 'good.storm')
            with open(fpath, 'w') as fd:
                fd.write('inet:fqdn=example.com\n')

            outp = self.getTestOutp()
            self.eq(await s_validate.main([fpath], outp=outp), 0)
            outp.expect('ok')

            # Invalid query (no column info)
            fpath = os.path.join(dirn, 'bad.storm')
            with open(fpath, 'w') as fd:
                fd.write('%%%badquery\n')

            outp = self.getTestOutp()
            self.eq(await s_validate.main([fpath], outp=outp), 1)
            outp.expect('BadSyntax')

            # Invalid query (with column info)
            fpath = os.path.join(dirn, 'badcol.storm')
            with open(fpath, 'w') as fd:
                fd.write('inet:fqdn=x |\n')

            outp = self.getTestOutp()
            self.eq(await s_validate.main([fpath], outp=outp), 1)
            outp.expect('BadSyntax')
            outp.expect('column:')

            # Empty file
            fpath = os.path.join(dirn, 'empty.storm')
            with open(fpath, 'w') as fd:
                fd.write('')

            outp = self.getTestOutp()
            self.eq(await s_validate.main([fpath], outp=outp), 1)
            outp.expect('No Storm query text provided')

            # Lookup mode
            fpath = os.path.join(dirn, 'lookup.storm')
            with open(fpath, 'w') as fd:
                fd.write('1.2.3.4\n')

            outp = self.getTestOutp()
            self.eq(await s_validate.main(['--mode', 'lookup', fpath], outp=outp), 0)
            outp.expect('ok')

    async def test_tools_storm_validate_stdin(self):

        outp = self.getTestOutp()
        with mock.patch('sys.stdin', io.StringIO('inet:fqdn=example.com\n')):
            self.eq(await s_validate.main(['-'], outp=outp), 0)
        outp.expect('ok')

        outp = self.getTestOutp()
        with mock.patch('sys.stdin', io.StringIO('%%%badquery\n')):
            self.eq(await s_validate.main(['-'], outp=outp), 1)
        outp.expect('BadSyntax')

        outp = self.getTestOutp()
        with mock.patch('sys.stdin', io.StringIO('')):
            self.eq(await s_validate.main(['-'], outp=outp), 1)
        outp.expect('No Storm query text provided')

    async def test_tools_storm_validate_help(self):
        outp = self.getTestOutp()
        with self.raises(s_exc.ParserExit):
            await s_validate.main(['-h'], outp=outp)

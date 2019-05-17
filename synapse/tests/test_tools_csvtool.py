import csv

import synapse.common as s_common

import synapse.tests.utils as s_t_utils

import synapse.tools.csvtool as s_csvtool

csvfile = b'''ipv4,fqdn,notes
1.2.3.4,vertex.link,malware
8.8.8.8,google.com,whitelist
'''

csvstorm = b'''
    for ($ipv4, $fqdn, $note) in $rows {
        [ inet:dns:a=($fqdn,$ipv4) ]
    }
'''

# count is used for test coverage.
csvstorm_export = b'''
test:int $lib.csv.emit($node, :loc) | count
'''

class CsvToolTest(s_t_utils.SynTest):

    async def test_csvtool(self):

        async with self.getTestCore() as core:

            url = core.getLocalUrl()

            dirn = s_common.gendir(core.dirn, 'junk')

            logpath = s_common.genpath(dirn, 'csvtest.log')

            csvpath = s_common.genpath(dirn, 'csvtest.csv')
            with s_common.genfile(csvpath) as fd:
                fd.write(csvfile)

            stormpath = s_common.genpath(dirn, 'csvtest.storm')
            with s_common.genfile(stormpath) as fd:
                fd.write(csvstorm)

            argv = ['--csv-header', '--debug', '--cortex', url, '--logfile', logpath, stormpath, csvpath]
            outp = self.getTestOutp()

            await s_csvtool.main(argv, outp=outp)

            outp.expect('2 nodes (9 created)')

    async def test_csvtool_local(self):

        with self.getTestDir() as dirn:

            logpath = s_common.genpath(dirn, 'csvtest.log')

            csvpath = s_common.genpath(dirn, 'csvtest.csv')
            with s_common.genfile(csvpath) as fd:
                fd.write(csvfile)

            stormpath = s_common.genpath(dirn, 'csvtest.storm')
            with s_common.genfile(stormpath) as fd:
                fd.write(csvstorm)

            argv = ['--csv-header', '--debug', '--test', '--logfile', logpath, stormpath, csvpath]
            outp = self.getTestOutp()

            await s_csvtool.main(argv, outp=outp)
            outp.expect('2 nodes (9 created)')

    async def test_csvtool_cli(self):

        with self.getTestDir() as dirn:

            logpath = s_common.genpath(dirn, 'csvtest.log')

            csvpath = s_common.genpath(dirn, 'csvtest.csv')
            with s_common.genfile(csvpath) as fd:
                fd.write(csvfile)

            stormpath = s_common.genpath(dirn, 'csvtest.storm')
            with s_common.genfile(stormpath) as fd:
                fd.write(csvstorm)

            argv = ['--csv-header', '--debug', '--cli', '--test', '--logfile', logpath, stormpath, csvpath]
            outp = self.getTestOutp()

            cmdg = s_t_utils.CmdGenerator(['storm --hide-props inet:fqdn', EOFError()])

            with self.withTestCmdr(cmdg):
                await s_csvtool.main(argv, outp=outp)

            outp.expect('inet:fqdn=google.com')
            outp.expect('2 nodes (9 created)')

    async def test_csvtool_export(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:int=20 :loc=us ]')
            await core.nodes('[ test:int=30 :loc=cn ]')

            url = core.getLocalUrl()

            dirn = s_common.gendir(core.dirn, 'junk')

            csvpath = s_common.genpath(dirn, 'csvtest.csv')

            stormpath = s_common.genpath(dirn, 'csvtest.storm')
            with s_common.genfile(stormpath) as fd:
                fd.write(csvstorm_export)

            # test a few no-no cases
            argv = ['--test', '--export', stormpath, csvpath]
            outp = self.getTestOutp()
            await s_csvtool.main(argv, outp=outp)
            outp.expect('--export requires --cortex')

            argv = ['--cortex', url, '--export', stormpath, csvpath, 'lol.csv']
            outp = self.getTestOutp()
            await s_csvtool.main(argv, outp=outp)
            outp.expect('--export requires exactly 1 csvfile')

            argv = ['--cortex', url, '--export', stormpath, csvpath]
            outp = self.getTestOutp()

            await s_csvtool.main(argv, outp=outp)

            outp.expect('Counted 2 nodes.')
            outp.expect('2 csv rows')

            with open(csvpath, 'r') as fd:
                rows = [row for row in csv.reader(fd)]
                self.eq(rows, (['20', 'us'], ['30', 'cn']))

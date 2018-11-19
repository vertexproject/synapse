import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cmd as s_cmd
import synapse.lib.coro as s_coro

import synapse.tools.csvtool as s_csvtool

import synapse.tests.utils as s_t_utils

csvfile = b'''ipv4,fqdn,notes
1.2.3.4,vertex.link,malware
8.8.8.8,google.com,whitelist
'''

csvstorm = b'''
    for ($ipv4, $fqdn, $note) in $rows {
        [ inet:dns:a=($fqdn,$ipv4) ]
    }
'''

class CsvToolTest(s_t_utils.SynTest):

    async def test_csvtool(self):

        async with self.getTestDmon(mirror='dmoncore') as dmon:

            url = self.getTestUrl(dmon, 'core')

            with self.getTestDir() as dirn:

                logpath = s_common.genpath(dirn, 'csvtest.log')

                csvpath = s_common.genpath(dirn, 'csvtest.csv')
                with s_common.genfile(csvpath) as fd:
                    fd.write(csvfile)

                stormpath = s_common.genpath(dirn, 'csvtest.storm')
                with s_common.genfile(stormpath) as fd:
                    fd.write(csvstorm)

                podes = []

                argv = ['--csv-header', '--debug', '--logfile', logpath, url, stormpath, csvpath]
                outp = self.getTestOutp()

                await s_coro.executor(s_csvtool.main, argv, outp=outp)

                outp.expect('2 nodes (9 created)')

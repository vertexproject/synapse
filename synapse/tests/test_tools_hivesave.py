import os

import unittest.mock as mock

import synapse.common as s_common
import synapse.tests.utils as s_test

import synapse.lib.cell as s_cell
import synapse.lib.hive as s_hive
import synapse.lib.msgpack as s_msgpack

import synapse.tools.hive.save as s_hivesave

class HiveSaveTest(s_test.SynTest):

    async def test_tools_hivesave_vercheck(self):
        with self.getTestDir() as dirn:

            hivepath0 = os.path.join(dirn, 'hivesave0.mpk')

            async with self.getTestHiveDmon() as dmon:
                hurl = self.getTestUrl(dmon, 'hive')

                argv = [hurl, hivepath0]

                def _getOldSynVers(self):
                    return (0, 0, 0)

                with mock.patch('synapse.telepath.Proxy._getSynVers', _getOldSynVers):
                    outp = self.getTestOutp()
                    retn = await s_hivesave.main(argv, outp=outp)
                    outp.expect('Hive version 0.0.0 is outside of the hive.save supported range')
                    self.eq(1, retn)

    async def test_tools_hivesave(self):

        with self.getTestDir() as dirn:

            hivepath0 = os.path.join(dirn, 'hivesave0.mpk')
            yamlpath0 = os.path.join(dirn, 'hivesave0.yaml')

            async with self.getTestHiveDmon() as dmon:

                hive = dmon.shared.get('hive')
                await hive.set(('baz', 'faz'), 'visi')

                hurl = self.getTestUrl(dmon, 'hive')

                retn = await s_hivesave.main([hurl, hivepath0])
                self.eq(0, retn)

                tree = s_msgpack.loadfile(hivepath0)
                self.eq('visi', tree['kids']['baz']['kids']['faz']['value'])

                await s_hivesave.main(['--path', 'baz', '--yaml', hurl, yamlpath0])

                tree = s_common.yamlload(yamlpath0)
                self.eq('visi', tree['kids']['faz']['value'])

            hivepath1 = os.path.join(dirn, 'hivesave1.mpk')
            yamlpath1 = os.path.join(dirn, 'hivesave1.yaml')

            path = os.path.join(dirn, 'cell')
            async with await s_cell.Cell.anit(path) as cell:

                await cell.hive.set(('hehe', 'haha'), 20)
                curl = cell.getLocalUrl()

                await s_hivesave.main([curl, hivepath1])
                tree = s_msgpack.loadfile(hivepath1)
                self.eq(20, tree['kids']['hehe']['kids']['haha']['value'])

                await s_hivesave.main(['--path', 'hehe', '--yaml', curl, yamlpath1])
                tree = s_common.yamlload(yamlpath1)

                self.eq(20, tree['kids']['haha']['value'])

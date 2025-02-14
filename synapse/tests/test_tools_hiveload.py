import os

import unittest.mock as mock

import synapse.common as s_common
import synapse.tests.utils as s_test

import synapse.lib.cell as s_cell
import synapse.lib.msgpack as s_msgpack

import synapse.tools.hive.load as s_hiveload

htree0 = {
    'kids': {
        'hehe': {'value': 20},
        'haha': {'value': 30, 'kids': {
            'foo': {'value': 'bar'},
            'baz': {'value': 'faz'},
        }},
    },
}

htree1 = {
    'kids': {
        'hehe': {'value': 20},
        'haha': {'value': 30, 'kids': {
            'baz': {'value': 'faz'},
        }},
    },
}

class HiveLoadTest(s_test.SynTest):

    async def test_tools_hiveload_vercheck(self):
        with self.getTestDir() as dirn:

            hivepath0 = os.path.join(dirn, 'hivesave0.mpk')
            s_msgpack.dumpfile(htree0, hivepath0)

            async with self.getTestCell() as cell:
                hurl = cell.getLocalUrl()

                argv = [hurl, hivepath0]

                def _getOldSynVers(self):
                    return (0, 0, 0)

                with mock.patch('synapse.telepath.Proxy._getSynVers', _getOldSynVers):
                    outp = self.getTestOutp()
                    retn = await s_hiveload.main(argv, outp=outp)
                    outp.expect('WARNING: "synapse.tools.hive.load" is deprecated in 2.167.0 and will be removed in 3.0.0')
                    outp.expect('Hive version 0.0.0 is outside of the hive.load supported range')
                    self.eq(1, retn)

    async def test_tools_hiveload(self):

        with self.getTestDir() as dirn:

            hivepath0 = os.path.join(dirn, 'hivepath0.mpk')
            hivepath1 = os.path.join(dirn, 'hivepath1.mpk')
            yamlpath0 = os.path.join(dirn, 'hivepath0.yaml')

            s_msgpack.dumpfile(htree0, hivepath0)
            s_msgpack.dumpfile(htree1, hivepath1)
            s_common.yamlsave(htree0, yamlpath0)

            async with self.getTestCell() as cell:
                hurl = cell.getLocalUrl()

                retn = await s_hiveload.main([hurl, hivepath0])
                self.eq(0, retn)

                self.eq(20, await cell.hive.get(('hehe',)))
                self.eq(30, await cell.hive.get(('haha',)))
                self.eq('bar', await cell.hive.get(('haha', 'foo')))
                self.eq('faz', await cell.hive.get(('haha', 'baz')))

                retn = await s_hiveload.main([hurl, hivepath1])
                self.eq(0, retn)

                self.eq(20, await cell.hive.get(('hehe',)))
                self.eq(30, await cell.hive.get(('haha',)))
                self.eq('bar', await cell.hive.get(('haha', 'foo')))
                self.eq('faz', await cell.hive.get(('haha', 'baz')))

                retn = await s_hiveload.main(['--trim', hurl, hivepath1])
                self.eq(0, retn)

                self.eq(20, await cell.hive.get(('hehe',)))
                self.eq(30, await cell.hive.get(('haha',)))
                self.eq('faz', await cell.hive.get(('haha', 'baz')))

                self.none(await cell.hive.get(('haha', 'foo')))

            async with self.getTestCell() as cell:
                hurl = cell.getLocalUrl()

                await s_hiveload.main(['--path', 'v/i/s/i', '--yaml', hurl, yamlpath0])
                self.eq('bar', await cell.hive.get(('v', 'i', 's', 'i', 'haha', 'foo')))

            path = os.path.join(dirn, 'cell')
            async with await s_cell.Cell.anit(path) as cell:
                curl = cell.getLocalUrl()
                await s_hiveload.main(['--path', 'gronk', curl, hivepath0])
                self.eq('bar', await cell.hive.get(('gronk', 'haha', 'foo')))
                await s_hiveload.main(['--trim', '--path', 'gronk', curl, hivepath1])
                self.none(await cell.hive.get(('gronk', 'haha', 'foo')))
                await s_hiveload.main(['--path', 'v/i/s/i', '--yaml', curl, yamlpath0])
                self.eq('bar', await cell.hive.get(('v', 'i', 's', 'i', 'haha', 'foo')))

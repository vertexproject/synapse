import os
import copy
import glob
import json
import shutil
import asyncio
import binascii
import itertools
import contextlib
import collections

import synapse.exc as s_exc
import synapse.cortex as s_cortex
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

import synapse.lib.cell as s_cell
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.modelrev as s_modelrev
import synapse.lib.stormsvc as s_stormsvc

import synapse.tools.migrate3x as s_migr

REGR_CORE = '3x-migr2'

class MigrationTest(s_t_utils.SynTest):

    @contextlib.asynccontextmanager
    async def _getTestMigrCore(self, conf):
        with self.getRegrDir('cortexes', REGR_CORE) as src:
            with self.getTestDir(copyfrom=conf.get('dest')) as dest:
                tconf = copy.deepcopy(conf)
                tconf['src'] = src
                tconf['dest'] = dest

                async with await s_migr.Migrator.anit(tconf) as migr:
                    yield migr, dest

    async def test_migr_basic(self):
        conf = {
            'src': None,
            'dest': None,
        }

        async with self._getTestMigrCore(conf) as (migr, dest):

            await migr.migrate()
            await migr.fini()

            async with await s_cortex.Cortex.anit(dest, conf=None) as core:

#                nodes = await core.nodes('.created')
                nodes = await core.nodes('inet:url -(refs)> meta:event:type:taxonomy')
                self.len(2, nodes)
                self.eq(nodes[0].ndef[1], 'nowhitespace.url.')
                self.eq(nodes[1].ndef[1], 'whitespace.url.')

                nodes = await core.nodes('inet:url <(refs)- meta:event:type:taxonomy')
                self.len(2, nodes)
                self.eq(nodes[0].ndef[1], 'merged.one.')
                self.eq(nodes[1].ndef[1], 'merged.two.')
#                nodes = await core.nodes('meta:event:type:taxonomy')
                for n in nodes:
                    print(n)

                nodes = await core.nodes('inet:url=http://whitespace.trigger')
                self.len(1, nodes)
                self.nn(nodes[0].get('#trig.migr'))

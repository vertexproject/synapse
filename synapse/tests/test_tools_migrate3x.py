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

REGR_CORE = '3x-migr3'

class MigrationTest(s_t_utils.SynTest):

    @contextlib.asynccontextmanager
    async def _getTestMigrCore(self, conf, regrname=REGR_CORE):
        with self.getRegrDir('cortexes', regrname) as src:
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

                nodes = await core.nodes('inet:url -(refs)> meta:event:type:taxonomy')
                self.len(2, nodes)
                self.eq(nodes[0].ndef[1], 'nowhitespace.url.')
                self.eq(nodes[1].ndef[1], 'whitespace.url.')

                nodes = await core.nodes('inet:url <(refs)- meta:event:type:taxonomy')
                self.len(2, nodes)
                self.eq(nodes[0].ndef[1], 'merged.one.')
                self.eq(nodes[1].ndef[1], 'merged.two.')

                nodes = await core.nodes('meta:source:type:taxonomy')
                self.len(1, nodes)

                nodes = await core.nodes('inet:url=http://whitespace.trigger')
                self.len(1, nodes)
                self.nn(nodes[0].get('#trig.migr'))

                nodes = await core.nodes('inet:ip')
                self.len(3, nodes)

                self.len(1, await core.nodes('inet:ip:version=4'))
                self.len(2, await core.nodes('inet:ip:version=6'))

                nodes = await core.nodes('risk:attack')
                self.len(1, nodes)
                self.none(nodes[0].get('target:host'))
                self.none(nodes[0].get('target:org'))
                self.none(nodes[0].get('via:ipv6'))
                self.none(nodes[0].get('via:ipv6'))

                nodes = await core.nodes('risk:attack -(targets)> *')
                self.len(2, nodes)

                nodes = await core.nodes('risk:attack -(targets)> ou:org')
                self.len(1, nodes)
                self.eq(nodes[0].get('name'), 'coolorg')

                nodes = await core.nodes('risk:attack -(targets)> it:host')
                self.len(1, nodes)
                self.eq(nodes[0].get('name'), 'coolhost')

                self.len(1, await core.nodes('risk:attack -(uses)> inet:ip +:version=4'))
                self.len(1, await core.nodes('risk:attack -(uses)> inet:ip +:version=6'))

                nodes = await core.nodes('lang:translation')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('lang:translation', s_common.guid(('notenglish',))))
                self.eq(nodes[0].get('desc'), 'somedesc')
                self.eq(nodes[0].get('input'), 'notenglish')
                self.eq(nodes[0].get('output'), 'english')
                self.eq(nodes[0].get('output:lang'), 'en')

    async def test_migr_layeroffs(self):
        conf = {
            'src': None,
            'dest': None,
        }

        async with self._getTestMigrCore(conf, regrname='pushpull-v2') as (migr, dest):
            await migr.migrate()
            await migr.fini()

            async with await s_cortex.Cortex.anit(dest, conf=None) as core:

                # test view has our nodes from the source cortex-view
                nodes = await core.nodes('ps:contact', opts={'view': '41552988daf582ac7d05813a834e9c26'})
                self.len(3, nodes)

                # test offset is returned from the layer's hotcount
                q = '$layer=$lib.layer.get($layr2) return ($layer)'
                opts = {'vars': {'layr2': 'dd924b9a39f26638411a719dfff6caca'}}
                layrinfo = await core.callStorm(q, opts=opts)
                pulls = layrinfo.get('pulls')
                self.len(1, pulls)
                pdef = list(pulls.values())[0]
                self.eq(23, pdef.get('offs', 0))

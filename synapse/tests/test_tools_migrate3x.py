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

import synapse.tools.cortex.migrate3x as s_migr

REGR_CORE = '2.x.x-3.0.0-migr'

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

                pretrim = []
                async for item in core.nexsroot.iter(0):
                    if item[1][1] == 'nexslog:cull':
                        break
                    pretrim.append(item[1])
                    self.eq(item[1][1], 'edits')

                self.len(4, pretrim)

                self.eq(core.nexsvers, s_cell.NEXUS_VERSION)

                oldp = await core.auth.getUserByName('oldpass')
                self.none(oldp.info.get('passwd'))
                self.none(oldp.info.get('onepass'))

                visi = await core.auth.getUserByName('visi')
                self.true(visi.allowed(('node', 'data', 'del')))
                self.true(visi.allowed(('node', 'prop', 'set', 'inet:ip')))
                self.true(visi.allowed(('node', 'prop', 'set', 'inet:ip', 'asn')))

                self.true(visi.allowed(('storm', 'macro', 'add')))
                self.true(visi.allowed(('storm', 'macro', 'edit')))
                self.true(visi.allowed(('storm', 'macro', 'admin')))

                self.true(visi.allowed(('auth', 'user', 'del', 'profile')))
                self.true(visi.allowed(('auth', 'user', 'add')))
                self.true(visi.allowed(('auth', 'role', 'add')))

                self.true(visi.allowed(('httpapi', 'set')))
                self.true(visi.allowed(('log', 'warning')))
                self.true(visi.allowed(('inet', 'imap', 'connect')))

                self.true(visi.allowed(('globals', 'del')))
                self.true(visi.allowed(('graph', 'add')))
                self.true(visi.allowed(('cron', 'set', 'user')))
                self.none(visi.allowed(('depr', '.newp')))

                layriden = core.getLayer().iden
                rusr = await core.auth.getUserByName('roleuser')
                self.false(rusr.allowed(('node', 'data', 'del')))
                self.false(rusr.allowed(('node', 'data', 'del', 'bar')))
                self.false(rusr.allowed(('node', 'data', 'del'), gateiden=layriden))
                self.true(rusr.allowed(('node', 'data', 'del', 'bar'), gateiden=layriden))

                self.false(rusr.allowed(('node', 'prop', 'set', 'inet:ip'), gateiden=layriden))
                self.true(rusr.allowed(('node', 'prop', 'set', 'inet:ip', 'asn'), gateiden=layriden))

                self.true(rusr.allowed(('auth', 'user', 'del')))
                self.true(rusr.allowed(('auth', 'role', 'del')))
                self.true(rusr.allowed(('cron', 'set', 'user')))
                self.none(rusr.allowed(('depr', '.newp'), gateiden=layriden))

                crons = core.agenda.list()
                self.len(3, crons)

                for appt in crons:
                    self.false(appt[1].enabled)

                cron = [appt[1] for appt in crons if appt[1].storm == '$foo=userview'][0]
                userview = core.auth.user(cron.user).profile.get('cortex:view')
                self.nn(cron.view)
                self.eq(cron.view, userview)

                cron = [appt[1] for appt in crons if appt[1].storm == '$foo=ok'][0]
                self.eq(cron.user, core.auth.rootuser.iden)
                self.nn(cron.view)
                self.ne(cron.view, core.view.iden)

                cron = [appt[1] for appt in crons if appt[1].storm == '$foo=coreview'][0]
                userview = core.auth.user(cron.user).profile.get('cortex:view')
                self.none(userview)
                self.nn(cron.view)
                self.eq(cron.view, core.view.iden)

                self.len(1, [trig for trig in core.view.trigdict.values() if trig['creator'] == core.auth.rootuser.iden])
                self.len(1, [trig for trig in core.view.trigdict.values() if trig['creator'] == visi.iden])

                # Triggers are disabled
                for trig in core.view.trigdict.values():
                    self.false(trig['enabled'])

                # Async trigger queues are cleared
                self.eq(0, core.view.trigqueue.size)

                # Old layer config values are removed
                for layr in core.layers.values():
                    self.none(layr.layrinfo.get('mirror'))
                    self.none(layr.layrinfo.get('upstream'))

                q = f"return($lib.inet.http.oauth.v2.getProvider({s_common.guid('providerconf00')}))"
                conf = await core.callStorm(q)
                self.none(conf.get('ssl_verify'))
                self.eq(conf.get('ssl'), {'verify': False})

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
                self.none(nodes[0].get('#trig.migr'))

                nodes = await core.nodes('inet:ip')
                self.len(2, nodes)

                self.len(1, await core.nodes('inet:ip:version=4'))
                self.len(1, await core.nodes('inet:ip:version=6'))

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

                nodes = await core.nodes('lang:translation=(lang:trans, notenglish)')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('lang:translation', s_common.guid(('lang:trans', 'notenglish'))))
                self.eq(nodes[0].get('desc'), 'somedesc')
                self.eq(nodes[0].get('input'), ('lang:phrase', 'notenglish'))
                self.eq(nodes[0].get('output'), 'english')
                self.eq(nodes[0].get('output:lang'), '1551445c4c921443a28e145007a01ab7')

                nodes = await core.nodes('lang:translation=(lang:trans, notenglish) -> lang:language')
                self.len(1, nodes)
                self.eq(nodes[0].get('code'), 'en')

                nodes = await core.nodes('lang:translation=(wasguid,)')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('lang:translation', s_common.guid(('wasguid',))))
                self.eq(nodes[0].get('desc'), 'guiddesc')
                self.eq(nodes[0].get('input'), ('lang:phrase', 'green'))
                self.eq(nodes[0].get('input:lang'), '1551445c4c921443a28e145007a01ab7')
                self.eq(nodes[0].get('output'), 'vert')
                self.eq(nodes[0].get('output:lang'), '3b62218b11431099f96dd99dc4bf5083')

                nodes = await core.nodes('lang:translation=(wasguid,) :input:lang -> *')
                self.len(1, nodes)
                self.eq(nodes[0].get('code'), 'en')

                nodes = await core.nodes('lang:translation=(wasguid,) :output:lang -> *')
                self.len(1, nodes)
                self.eq(nodes[0].get('code'), 'fr')

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
                nodes = await core.nodes('entity:contact', opts={'view': '41552988daf582ac7d05813a834e9c26'})
                self.len(3, nodes)

                # test offset is returned from the layer's hotcount
                q = '$layer=$lib.layer.get($layr2) return ($layer)'
                opts = {'vars': {'layr2': 'dd924b9a39f26638411a719dfff6caca'}}
                layrinfo = await core.callStorm(q, opts=opts)
                pulls = layrinfo.get('pulls')
                self.len(1, pulls)
                pdef = list(pulls.values())[0]
                self.eq(23, pdef.get('offs', 0))

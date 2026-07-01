import os
import copy
import shutil
import contextlib
import unittest.mock as mock

import synapse.cortex as s_cortex
import synapse.common as s_common
import synapse.datamodel as s_datamodel

import synapse.models as s_models

import synapse.tests.utils as s_t_utils

import synapse.lib.cell as s_cell
import synapse.lib.layer as s_layer
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.msgpack as s_msgpack
import synapse.lib.slabseqn as s_slabseqn
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.multislabseqn as s_multislabseqn

import synapse.tools.cortex.migrate3x as s_migr

REGR_CORE = '2.x.x-3.0.0-migr'

# inet:fqdn values whose idna normalization changed across idna versions, as
# (a-label stored by the older idna, value the current idna produces). The label
# in each case was 'a<codepoint>a.link'. The migration must repair the stored
# a-label by decoding it and renormalizing under the current idna.
FQDN_IDNA_DRIFT = (
    ('xn--aa-iuk.link', 'aa.link'),  # U+115F HANGUL CHOSEONG FILLER
    ('xn--aa-luk.link', 'aa.link'),  # U+1160 HANGUL JUNGSEONG FILLER
    ('xn--aa-gto.link', 'aa.link'),  # U+17B4 KHMER VOWEL INHERENT AQ
    ('xn--aa-jto.link', 'aa.link'),  # U+17B5 KHMER VOWEL INHERENT AA
    ('xn--aa-luk.link', 'aa.link'),  # U+3164 HANGUL FILLER
    ('xn--aa-648h.link', 'xn--aa-sgb.link'),  # U+A7CB LATIN CAPITAL LETTER RAMS HORN
    ('xn--aa-s58h.link', 'xn--aa-v58h.link'),  # U+A7D2 LATIN CAPITAL LETTER DOUBLE THORN
    ('xn--aa-y58h.link', 'xn--aa-158h.link'),  # U+A7D4 LATIN CAPITAL LETTER DOUBLE WYNN
    ('xn--aa-n68h.link', 'xn--aa-kya.link'),  # U+A7DC LATIN CAPITAL LETTER LAMBDA WITH STROKE
    ('xn--aa-g88h.link', 'asa.link'),  # U+A7F1 MODIFIER LETTER CAPITAL S
    ('xn--aa-luk.link', 'aa.link'),  # U+FFA0 HALFWIDTH HANGUL FILLER
    ('xn--aa-ev20a.link', 'aaa.link'),  # U+1CCD6 OUTLINED LATIN CAPITAL LETTER A
    ('xn--aa-hv20a.link', 'aba.link'),  # U+1CCD7 OUTLINED LATIN CAPITAL LETTER B
    ('xn--aa-kv20a.link', 'aca.link'),  # U+1CCD8 OUTLINED LATIN CAPITAL LETTER C
    ('xn--aa-nv20a.link', 'ada.link'),  # U+1CCD9 OUTLINED LATIN CAPITAL LETTER D
    ('xn--aa-qv20a.link', 'aea.link'),  # U+1CCDA OUTLINED LATIN CAPITAL LETTER E
    ('xn--aa-tv20a.link', 'afa.link'),  # U+1CCDB OUTLINED LATIN CAPITAL LETTER F
    ('xn--aa-wv20a.link', 'aga.link'),  # U+1CCDC OUTLINED LATIN CAPITAL LETTER G
    ('xn--aa-zv20a.link', 'aha.link'),  # U+1CCDD OUTLINED LATIN CAPITAL LETTER H
    ('xn--aa-2v20a.link', 'aia.link'),  # U+1CCDE OUTLINED LATIN CAPITAL LETTER I
    ('xn--aa-5v20a.link', 'aja.link'),  # U+1CCDF OUTLINED LATIN CAPITAL LETTER J
    ('xn--aa-8v20a.link', 'aka.link'),  # U+1CCE0 OUTLINED LATIN CAPITAL LETTER K
    ('xn--aa-cw20a.link', 'ala.link'),  # U+1CCE1 OUTLINED LATIN CAPITAL LETTER L
    ('xn--aa-fw20a.link', 'ama.link'),  # U+1CCE2 OUTLINED LATIN CAPITAL LETTER M
    ('xn--aa-iw20a.link', 'ana.link'),  # U+1CCE3 OUTLINED LATIN CAPITAL LETTER N
    ('xn--aa-lw20a.link', 'aoa.link'),  # U+1CCE4 OUTLINED LATIN CAPITAL LETTER O
    ('xn--aa-ow20a.link', 'apa.link'),  # U+1CCE5 OUTLINED LATIN CAPITAL LETTER P
    ('xn--aa-rw20a.link', 'aqa.link'),  # U+1CCE6 OUTLINED LATIN CAPITAL LETTER Q
    ('xn--aa-uw20a.link', 'ara.link'),  # U+1CCE7 OUTLINED LATIN CAPITAL LETTER R
    ('xn--aa-xw20a.link', 'asa.link'),  # U+1CCE8 OUTLINED LATIN CAPITAL LETTER S
    ('xn--aa-0w20a.link', 'ata.link'),  # U+1CCE9 OUTLINED LATIN CAPITAL LETTER T
    ('xn--aa-3w20a.link', 'aua.link'),  # U+1CCEA OUTLINED LATIN CAPITAL LETTER U
    ('xn--aa-6w20a.link', 'ava.link'),  # U+1CCEB OUTLINED LATIN CAPITAL LETTER V
    ('xn--aa-9w20a.link', 'awa.link'),  # U+1CCEC OUTLINED LATIN CAPITAL LETTER W
    ('xn--aa-dx20a.link', 'axa.link'),  # U+1CCED OUTLINED LATIN CAPITAL LETTER X
    ('xn--aa-gx20a.link', 'aya.link'),  # U+1CCEE OUTLINED LATIN CAPITAL LETTER Y
    ('xn--aa-jx20a.link', 'aza.link'),  # U+1CCEF OUTLINED LATIN CAPITAL LETTER Z
    ('xn--aa-mx20a.link', 'a0a.link'),  # U+1CCF0 OUTLINED DIGIT ZERO
    ('xn--aa-px20a.link', 'a1a.link'),  # U+1CCF1 OUTLINED DIGIT ONE
    ('xn--aa-sx20a.link', 'a2a.link'),  # U+1CCF2 OUTLINED DIGIT TWO
    ('xn--aa-vx20a.link', 'a3a.link'),  # U+1CCF3 OUTLINED DIGIT THREE
    ('xn--aa-yx20a.link', 'a4a.link'),  # U+1CCF4 OUTLINED DIGIT FOUR
    ('xn--aa-1x20a.link', 'a5a.link'),  # U+1CCF5 OUTLINED DIGIT FIVE
    ('xn--aa-4x20a.link', 'a6a.link'),  # U+1CCF6 OUTLINED DIGIT SIX
    ('xn--aa-7x20a.link', 'a7a.link'),  # U+1CCF7 OUTLINED DIGIT SEVEN
    ('xn--aa-by20a.link', 'a8a.link'),  # U+1CCF8 OUTLINED DIGIT EIGHT
    ('xn--aa-ey20a.link', 'a9a.link'),  # U+1CCF9 OUTLINED DIGIT NINE
)

# drift a-labels the current idna can no longer decode (the codepoint was
# unassigned when an older idna stored it). They are indistinguishable from opaque
# values that merely look like punycode, so the migration guard leaves them
# unchanged rather than risk renormalizing a value that was never a real encoding.
FQDN_IDNA_UNDECODABLE = (
    'xn--aa-648h.link',  # U+A7CB LATIN CAPITAL LETTER RAMS HORN
    'xn--aa-n68h.link',  # U+A7DC LATIN CAPITAL LETTER LAMBDA WITH STROKE
)

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

    @contextlib.asynccontextmanager
    async def _getBareMigr(self, *, model=False, stors=False):
        '''
        Construct a Migrator with throwaway source/dest dirs. Avoids
        any regression-cortex setup and only invokes ``__anit__``.
        '''
        with self.getTestDir() as src:
            with self.getTestDir() as dest:
                s_common.gendir(src, 'layers')
                conf = {'src': src, 'dest': dest}
                async with await s_migr.Migrator.anit(conf) as migr:
                    if stors:
                        await migr._initStors()
                    if model:
                        migr.model = s_datamodel.Model()
                        mdefs = []
                        for path in s_models.modeldefs:
                            if (defs := s_dyndeps.getDynLocal(path)) is not None:
                                mdefs.extend(defs)
                        migr.model.addModelDefs(mdefs)
                        migr.ivaltype = migr.model.type('ival')
                        migr.oldmodel = s_migr._get2xModel()
                        migr.fullpropmap = {}
                        for formname, fdef in migr.oldmodel['forms'].items():
                            for propname in fdef['props'].keys():
                                migr.fullpropmap[f'{formname}:{propname}'] = (formname, propname)
                    yield migr, src, dest

    async def test_migr_basic(self):
        conf = {
            'src': None,
            'dest': None,
        }

        async with self._getTestMigrCore(conf) as (migr, dest):

            await migr.migrate()
            await migr.fini()

            # capture the destination nexus log before the cortex starts (so it only
            # contains what the migration wrote). The value-change edits the migration
            # appends to record how nodes reached their 3.x state come after the final
            # nexs:vers:set marker.
            dpath = os.path.join(dest, 'slabs', 'nexuslog')
            async with await s_multislabseqn.MultiSlabSeqn.anit(dpath) as nexslog:
                nexitems = [item async for _, item in nexslog.iter(0)]

            versidx = max(i for i, it in enumerate(nexitems) if it[1] == 'nexs:vers:set')
            migrlog = [it for it in nexitems[versidx + 1:] if it[1] == 'edits']
            self.true(len(migrlog) > 0)

            # every migration value-change edit carries the single migration timestamp
            self.true(all(it[5] == migr.migrtime for it in migrlog))

            # flatten the per-node edits the migration recorded as value changes
            migrne = [ne for it in migrlog for ne in it[2][0]]

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

                self.true(visi.allowed(('auth', 'user', 'profile', 'del')))
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
                    # cron time values are migrated from float epoch-seconds to int epoch-micros
                    self.isinstance(appt[1].nexttime, int)

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
                self.propeq(nodes[0], 'name', 'coolorg', type='entity:name')

                nodes = await core.nodes('risk:attack -(targets)> it:host')
                self.len(1, nodes)
                self.propeq(nodes[0], 'name', 'coolhost', type='it:hostname')

                self.len(1, await core.nodes('risk:attack -(uses)> inet:ip +:version=4'))
                self.len(1, await core.nodes('risk:attack -(uses)> inet:ip +:version=6'))

                nodes = await core.nodes('lang:translation=(wasguid,)')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('lang:translation', s_common.guid(('wasguid',))))
                self.propeq(nodes[0], 'desc', 'guiddesc', type='text')
                self.propeq(nodes[0], 'input', 'green', type='text')
                self.propeq(nodes[0], 'input:lang', '1551445c4c921443a28e145007a01ab7', type='lang:language')
                self.propeq(nodes[0], 'output', 'vert', type='text')
                self.propeq(nodes[0], 'output:lang', '3b62218b11431099f96dd99dc4bf5083', type='lang:language')

                nodes = await core.nodes('lang:translation=(wasguid,) :input:lang -> *')
                self.len(1, nodes)
                self.propeq(nodes[0], 'code', 'en', type='lang:code')

                nodes = await core.nodes('lang:translation=(wasguid,) :output:lang -> *')
                self.len(1, nodes)
                self.propeq(nodes[0], 'code', 'fr', type='lang:code')

                # lang:translation engine prop migrated
                self.nn(nodes[0])
                self.nn((await core.nodes('lang:translation=(wasguid,) +:engine'))[0])

                # the migration recorded its value changes in the nexus log so a node's
                # history can be followed by its nid to see how it reached its 3.x state.

                # inet:ipv4 -> inet:ip changed the primary value (and buid), so the new
                # node's value-change is recorded under its new nid as a node add.
                ip4 = (await core.nodes('inet:ip:version=4'))[0]
                ip4nid = s_common.int64un(ip4.nid)
                ip4edits = [edits for (nid, form, edits) in migrne if nid == ip4nid and form == 'inet:ip']
                self.true(any(edit[0] == s_layer.EDIT_NODE_ADD for edits in ip4edits for edit in edits))

                # lang:translation was restructured by a full migration; its primary node
                # value-changes are recorded under its nid.
                lt = (await core.nodes('lang:translation=(wasguid,)'))[0]
                ltnid = s_common.int64un(lt.nid)
                self.true(any(nid == ltnid and form == 'lang:translation' for (nid, form, _) in migrne))

                # risk:attack props were converted to edges; the new edges are recorded.
                self.true(any(edit[0] == s_layer.EDIT_EDGE_ADD for (_, _, edits) in migrne for edit in edits))

                # tags/tagprops/nodedata/edges that were faithfully reproduced ( not
                # changed by the migration ) are not re-recorded as value changes.
                self.notin(s_layer.EDIT_TAG_SET, [edit[0] for (_, _, edits) in migrne for edit in edits])
                self.notin(s_layer.EDIT_NODEDATA_SET, [edit[0] for (_, _, edits) in migrne for edit in edits])

                # extended-model form node migrated
                self.len(1, await core.nodes('_cover:ext=42'))

                # node carrying a tag, tagprop, nodedata, extended prop, and edges
                nodes = await core.nodes('it:dev:str=coverstr')
                self.len(1, nodes)
                self.nn(nodes[0].getTag('cover.tag'))
                self.eq(42, nodes[0].getTagProp('cover.tag', 'coverscore'))
                self.propeq(nodes[0], '_coverprop', 7)
                self.eq(('foo', 'bar'), await nodes[0].getData('coverkey'))

                self.len(1, await core.nodes('it:dev:str=coverstr -(_coveredge)> it:dev:str=coverdst'))
                self.len(1, await core.nodes('it:dev:str=coverstr -(refs)> inet:ip'))

                # ou:asset survived even though its ndef prop could not be migrated
                self.len(1, await core.nodes('ou:asset=(coverasset,)'))

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

    async def test_migr_auth_rules_cron(self):
        conf = {
            'src': None,
            'dest': None,
        }

        async with self._getTestMigrCore(conf, regrname='cron-creator-to-user') as (migr, dest):

            await migr.migrate()
            await migr.fini()

            async with await s_cortex.Cortex.anit(dest, conf=None) as core:

                auth = core.auth

                user = await auth.reqUserByName('testuser')
                role = await auth.reqRoleByName('testrole')

                urules = user.getRules()
                self.isin((True, ('cron', 'set', 'user')), urules)

                rrules = role.getRules()
                self.isin((True, ('cron', 'set', 'user', 'extra')), rrules)

    async def test_migr_auth_rules_profile(self):
        conf = {
            'src': None,
            'dest': None,
        }

        async with self._getTestMigrCore(conf, regrname='2.192.0-auth-rules-migr') as (migr, dest):

            await migr.migrate()
            await migr.fini()

            async with await s_cortex.Cortex.anit(dest, conf=None) as core:

                auth = core.auth

                user = await auth.reqUserByName('visi')
                role = await auth.reqRoleByName('visi-role')

                # user rules: auth.user.*.profile.* -> auth.user.profile.*.*
                urules = user.getRules()
                self.isin((True, ('auth', 'user', 'profile', 'get', 'fullname')), urules)
                self.isin((True, ('auth', 'user', 'profile', 'set', 'fullname')), urules)
                self.isin((True, ('auth', 'user', 'profile', 'del', 'fullname')), urules)

                # role rules: auth.role.*.profile.* -> auth.role.profile.*.*
                rrules = role.getRules()
                self.isin((False, ('auth', 'user', 'profile', 'del', 'nickname')), rrules)

    async def test_migr_edit_transformers_pure(self):
        '''Cover module-level migrNodeAdd/Del, migrPropDel, migrTagDel, migrTagPropDel,
        migrNodeDataSet, migrNodeDataDel. All take ``(migr, edit)`` and the migr arg
        is unused for these so ``None`` is fine.'''
        self.eq(await s_migr.migrNodeAdd(None, ('valu', s_layer.STOR_TYPE_UTF8)),
                ('valu', s_layer.STOR_TYPE_UTF8, {}))
        self.eq(await s_migr.migrNodeDel(None, ('valu',)), 'valu')
        self.eq(await s_migr.migrPropDel(None, ('asn', 'oldv', s_layer.STOR_TYPE_I64, 0)), 'asn')
        self.eq(await s_migr.migrTagDel(None, ('cno.fakeape', None, None)), 'cno.fakeape')
        self.eq(await s_migr.migrTagPropDel(None, ('cno.fakeape', 'risk', None, None, s_layer.STOR_TYPE_I64)),
                ('cno.fakeape', 'risk'))
        self.eq(await s_migr.migrNodeDataSet(None, ('foo', {'a': 1}, None)), ('foo', {'a': 1}))
        self.eq(await s_migr.migrNodeDataDel(None, ('foo', {'a': 1})), 'foo')

    async def test_migr_ival_branches(self):
        '''Cover module-level migrIval ``(None, None)`` branch and norm branch.'''
        async with self._getBareMigr(model=True) as (migr, _, _):
            self.eq(await s_migr.migrIval(migr, (None, None)), (None, None, None))

            expected = (await migr.ivaltype.norm((1577836800000, 1577923200000)))[0]
            self.eq(await s_migr.migrIval(migr, (1577836800000, 1577923200000)), expected)

    async def test_migr_propset_tagset_tagpropset_ival(self):
        '''Cover migrPropSet, migrTagSet, migrTagPropSet (both STOR_TYPE_IVAL and
        scalar branches). For the IVAL branch, ``migrIval`` returns the normed
        ival value (the ``(min, max, dura)`` triple) from ``ivaltype.norm``.'''
        async with self._getBareMigr(model=True) as (migr, _, _):
            # migrPropSet - scalar
            edit = ('name', 'visi', None, s_layer.STOR_TYPE_UTF8)
            self.eq(await s_migr.migrPropSet(migr, edit),
                    ('name', 'visi', s_layer.STOR_TYPE_UTF8, {}))

            # migrPropSet - ival branch
            normval = (await migr.ivaltype.norm((1577836800000, 1577923200000)))[0]
            ivaledit = ('seen', (1577836800000, 1577923200000), None, s_layer.STOR_TYPE_IVAL)
            self.eq(await s_migr.migrPropSet(migr, ivaledit),
                    ('seen', normval, s_layer.STOR_TYPE_IVAL, {}))

            # migrTagSet - always passes through migrIval; for (None, None) the
            # 3-tuple shortcut is returned (no wrapping).
            self.eq(await s_migr.migrTagSet(migr, ('cno.fakeape', (None, None), None)),
                    ('cno.fakeape', (None, None, None)))

            # migrTagSet with real ival -> returns the full norm tuple
            self.eq(await s_migr.migrTagSet(migr, ('cno.fakeape', (1577836800000, 1577923200000), None)),
                    ('cno.fakeape', normval))

            # migrTagPropSet - scalar
            tpedit = ('cno.fakeape', 'risk', 42, None, s_layer.STOR_TYPE_I64)
            self.eq(await s_migr.migrTagPropSet(migr, tpedit),
                    ('cno.fakeape', 'risk', 42, s_layer.STOR_TYPE_I64, {}))

            # migrTagPropSet - ival branch
            tpival = ('cno.fakeape', 'seen', (1577836800000, 1577923200000), None, s_layer.STOR_TYPE_IVAL)
            self.eq(await s_migr.migrTagPropSet(migr, tpival),
                    ('cno.fakeape', 'seen', normval, s_layer.STOR_TYPE_IVAL, {}))

    async def test_migr_rule_path_branches(self):
        '''Cover module-level _migrRulePath: dotted-segment guard, node-add/del form
        rename, node-prop fullpropmap + form/prop rename, every permmigrs entry,
        and passthrough.'''
        async with self._getBareMigr(model=True) as (migr, _, _):

            fm = migr.formmigr
            pm = migr.propmigr
            fp = migr.fullpropmap

            # dotted segment -> None
            self.none(s_migr._migrRulePath(fm, pm, fp, ('storm', 'lib.cortex')))

            # node-add form rename via formmigr
            self.eq(s_migr._migrRulePath(fm, pm, fp, ('node', 'add', 'inet:ipv4')),
                    ('node', 'add', 'inet:ip'))

            # node-del form rename
            self.eq(s_migr._migrRulePath(fm, pm, fp, ('node', 'del', 'hash:md5')),
                    ('node', 'del', 'crypto:hash:md5'))

            # node-prop set: form unchanged when fullpropmap resolves (inet:ipv4 -> inet:ip)
            self.eq(s_migr._migrRulePath(fm, pm, fp, ('node', 'prop', 'set', 'inet:ipv4', 'asn')),
                    ('node', 'prop', 'set', 'inet:ip', 'asn'))

            # node-prop set: len-4 path whose form segment is a full 'form:prop'
            # resolved via fullpropmap (inet:ipv4:asn -> inet:ip + asn)
            self.eq(s_migr._migrRulePath(fm, pm, fp, ('node', 'prop', 'set', 'inet:ipv4:asn')),
                    ('node', 'prop', 'set', 'inet:ip', 'asn'))

            # node-prop set: form + prop rename (ou:org -> ou:org:type:taxonomy is wrong;
            # ou:org keeps name, prop 'orgtype' -> 'type')
            self.eq(s_migr._migrRulePath(fm, pm, fp, ('node', 'prop', 'set', 'ou:org', 'orgtype')),
                    ('node', 'prop', 'set', 'ou:org', 'type'))

            # every permmigrs pair
            permmigrs = (
                (('auth', 'user', 'pop'), ('auth', 'user', 'del')),
                (('storm', 'lib', 'auth', 'users'), ('auth', 'user')),
                (('storm', 'lib', 'auth', 'roles'), ('auth', 'role')),
                (('storm', 'lib', 'cortex', 'httpapi'), ('httpapi',)),
                (('storm', 'lib', 'log'), ('log',)),
                (('storm', 'inet'), ('inet',)),
                (('cron', 'set', 'creator'), ('cron', 'set', 'user')),
                (('macro', 'add'), ('storm', 'macro', 'add')),
                (('macro', 'edit'), ('storm', 'macro', 'edit')),
                (('macro', 'admin'), ('storm', 'macro', 'admin')),
                (('node', 'data', 'pop'), ('node', 'data', 'del')),
                (('globals', 'pop'), ('globals', 'del')),
                (('storm', 'graph', 'add'), ('graph', 'add')),
            )
            for oldperm, newperm in permmigrs:
                self.eq(s_migr._migrRulePath(fm, pm, fp, oldperm + ('extra',)),
                        newperm + ('extra',))

            # passthrough for unrecognized path
            unknown = ('queue', 'add', 'foo')
            self.eq(s_migr._migrRulePath(fm, pm, fp, unknown), unknown)

    async def test_migrauth_gateinfo_and_dropped_rules(self):
        '''Cover MigrAuth._migrRules over authgates plus rulePathFn-dropped paths.'''
        def rulePathFn(path):
            # drop paths whose first segment contains a dot
            for part in path:
                if '.' in part:
                    return None
            return path

        with self.getTestDir() as dirn:
            async with await s_lmdbslab.Slab.anit(s_common.genpath(dirn, 'auth.lmdb')) as slab:
                authkv = slab.getSafeKeyVal('auth')
                rolekv = authkv.getSubKeyVal('role:info:')

                gateiden = s_common.guid()
                roleiden = s_common.guid()
                rolekv.set(roleiden, {
                    'iden': roleiden,
                    'rules': [(True, ('foo.bar', 'baz'))],  # dotted -> dropped
                    'authgates': {
                        gateiden: {'rules': [(True, ('node', 'data', 'del'))]},
                    },
                })

                s_migr.MigrAuth(authkv, rulePathFn).migrate()

                info = rolekv.get(roleiden)
                self.eq(info['rules'], [])
                self.isin((True, ('node', 'data', 'del')),
                          info['authgates'][gateiden]['rules'])

    async def test_chkvalid_invalid_then_valid(self):
        '''Cover _chkValid both branches: bad version + missing cell.guid, then valid.'''
        async with self._getBareMigr(stors=True) as (migr, _, dest):

            migr.cellinfo.set('cell:version', (2, 100, 0))
            self.false(await migr._chkValid())

            migr.cellinfo.set('cell:version', (2, 192, 0))
            iden = s_common.guid()
            with s_common.genfile(dest, 'cell.guid') as fd:
                fd.write(iden.encode())

            self.true(await migr._chkValid())
            self.eq(migr.celliden, iden)

    async def test_nid_storage_helpers(self):
        '''Cover _genIndxNid (idempotent for same buid), _genBuidNid, setNidNdef,
        getNidByBuid, hasNidNdef, getNidNdef, and that nextnid advances.'''
        async with self._getBareMigr(stors=True) as (migr, _, _):

            ndef = ('test:str', 'visi')
            buid = s_common.buid(ndef)

            self.none(migr.getNidByBuid(buid))

            nid1 = migr._genIndxNid(buid, ndef)
            self.nn(nid1)

            # repeat call returns same nid (no second allocation)
            nid2 = migr._genIndxNid(buid, ndef)
            self.eq(nid1, nid2)

            # _genBuidNid advances nextnid
            startnext = migr.nextnid
            otherbuid = s_common.buid(('test:str', 'other'))
            othernid = migr._genBuidNid(otherbuid)
            self.eq(migr.nextnid, startnext + 1)
            self.ne(nid1, othernid)

            self.eq(migr.getNidByBuid(buid), nid1)

            # hasNidNdef False until ndef is stored via setNidNdef
            fakenid = s_common.int64en(9999999)
            fakendef = ('test:str', 'fresh')
            self.false(migr.hasNidNdef(fakenid))
            migr.setNidNdef(fakenid, fakendef)
            self.true(migr.hasNidNdef(fakenid))
            self.eq(migr.getNidNdef(fakenid), list(fakendef))
            self.eq(migr.nextnid, 10000000)

    async def test_migr_node_edge_paths(self):
        '''Cover migrNodeEdge skip-unknown, v3stor lookup, and migrinfo fallback.'''
        async with self._getBareMigr(stors=True) as (migr, _, _):

            # unknown buid -> returns None (skip edge)
            unknownbuid = s_common.buid(('test:str', 'nope'))
            self.none(await s_migr.migrNodeEdge(migr, ('refs', unknownbuid.hex())))

            # buid registered via setNidNdef -> returns (verb, int_nid)
            ndef = ('test:str', 'cool')
            buid = s_common.buid(ndef)
            nid = migr._genIndxNid(buid, ndef)
            (verb, n2int) = await s_migr.migrNodeEdge(migr, ('refs', buid.hex()))
            self.eq(verb, 'refs')
            self.eq(n2int, s_common.int64un(nid))

            # buid only in migrinfo (not v3stor) -> fallback returns migrated nid
            otherbuid = s_common.buid(('test:str', 'other'))
            othernid = s_common.int64en(7777)
            migr.migrslab._put(otherbuid, s_msgpack.en((othernid, otherbuid, 'test:str', 'other', {})),
                               db=migr.migrinfo)
            (verb, n2int) = await s_migr.migrNodeEdge(migr, ('refs', otherbuid.hex()))
            self.eq(verb, 'refs')
            self.eq(n2int, s_common.int64un(othernid))

    async def test_migrlog_add_str_and_bytes_keys(self):
        '''Cover _migrlogAdd over both bytes and string key inputs.'''
        async with self._getBareMigr(stors=True) as (migr, _, _):

            await migr._migrlogAdd('cell', 'prog', 'foo', 'val-str')
            await migr._migrlogAdd('cell', 'prog', b'bar', 'val-bytes')

            stored = {}
            for lkey, lval in migr.migrslab.scanByFull(db=migr.migrdb):
                stored[lkey] = s_msgpack.un(lval)

            self.eq(stored[b'cell\x00prog\x00foo'], 'val-str')
            self.eq(stored[b'cell\x00prog\x00bar'], 'val-bytes')

    async def test_main_argparse_errors(self):
        '''Cover main() argparse: required --src and bad --log-level both exit.'''
        with self.raises(SystemExit):
            await s_migr.main([])

        with self.raises(SystemExit):
            await s_migr.main(['--src', '/tmp/x', '--log-level', 'bogus'])

    async def test_main_dispatch(self):
        '''Cover main() default migrate() path. Uses ``unittest.mock.patch.object`` to swap Migrator.anit
        so no real migration runs.'''
        captured = {}

        class _StubMigr:
            def __init__(self, conf):
                captured['conf'] = conf
                self.migrate = mock.AsyncMock()
                self.fini = mock.AsyncMock()

        async def _fakeAnit(conf=None):
            return _StubMigr(conf)

        with self.getTestDir() as srcdir:
            with mock.patch.object(s_migr.Migrator, 'anit', new=_fakeAnit):
                migr = await s_migr.main(['--src', srcdir])
                self.eq(captured['conf']['src'], srcdir)
                migr.migrate.assert_awaited()
                migr.fini.assert_awaited()

    async def test_migr_toguidnorm(self):
        '''Cover module-level toguidnorm which norms a single value as a guid tuple.'''
        async with self._getBareMigr(model=True) as (migr, _, _):
            gtyp = migr.model.type('guid')
            valu, info = await s_migr.toguidnorm(migr, 'foo', {'type': gtyp})
            self.eq(valu, (await gtyp.norm(('foo',)))[0])

    async def test_migr_fqdndecnorm(self):
        '''The inet:fqdn form and inet:fqdn typed props (including arrays) get a
        decode + renormalize migration so values stored by an older idna library
        are renormalized to match the current normalization.'''
        async with self._getBareMigr(model=True, stors=True) as (migr, _, _):

            await migr._migrDatamodel()

            # the inet:fqdn form is registered with the fqdn decode + renorm
            # migration and its type is populated
            self.eq(migr.formmigr['inet:fqdn'][0], s_migr.fqdndecnorm)
            self.nn(migr.formmigr['inet:fqdn'][1].get('type'))

            # a direct inet:fqdn prop and an array-of-inet:fqdn prop are both
            # registered with the fqdn callback carrying the old type name
            self.eq(migr.propmigr['inet:dns:a']['fqdn'][0], s_migr.fqdndecnorm)
            self.eq(migr.propmigr['inet:dns:a']['fqdn'][1].get('oldname'), 'inet:fqdn')
            self.eq(migr.propmigr['ou:org']['dns:mx'][0], s_migr.fqdndecnorm)

            ftyp = migr.model.type('inet:fqdn')

            # an older idna stored 'a<U+115F>a.link' as 'xn--aa-iuk.link'; decoding
            # and renormalizing it strips the now-ignored codepoint to 'aa.link'
            valu, info = await s_migr.fqdndecnorm(migr, 'xn--aa-iuk.link', {'type': ftyp})
            self.eq(valu, 'aa.link')

            # a scalar value with no encoded label is short circuited: returned
            # unchanged with empty norminfo and without renormalizing
            valu, info = await s_migr.fqdndecnorm(migr, 'vertex.link', {'type': ftyp})
            self.eq(valu, 'vertex.link')
            self.eq(info, {})

            # a poly-typed fqdn prop wraps the renormalized value
            ptyp = migr.model.prop('inet:dns:a:fqdn').type
            valu, info = await s_migr.fqdndecnorm(migr, 'xn--aa-iuk.link', {'type': ptyp})
            self.eq(valu, ('inet:fqdn', 'aa.link'))

            # a poly prop with a non-drifting value is still reshaped (not short
            # circuited) since the destination is not a bare fqdn
            valu, info = await s_migr.fqdndecnorm(migr, 'vertex.link', {'type': ptyp})
            self.eq(valu, ('inet:fqdn', 'vertex.link'))

            # array-of-fqdn values are decoded element-wise (only encoded labels)
            # and renormalized through the array type
            atyp = migr.model.prop('ou:org:dns:mx').type
            valu, info = await s_migr.fqdndecnorm(migr, ('xn--aa-iuk.link', 'vertex.link'), {'type': atyp})
            self.eq(valu, (('inet:fqdn', 'aa.link'), ('inet:fqdn', 'vertex.link')))

    async def test_migr_fqdndecnorm_driftset(self):
        '''Every known idna drift case is accounted for: decoding the a-label stored
        by an older idna and renormalizing it produces the value the current idna
        emits (default-ignorable stripping, case-folding, compatibility
        decompositions). The two labels the current idna can no longer decode are
        left unchanged by the guard, since they cannot be distinguished from opaque
        punycode literals.'''
        async with self._getBareMigr(model=True) as (migr, _, _):
            ftyp = migr.model.type('inet:fqdn')

            self.gt(len(FQDN_IDNA_DRIFT), 40)
            for stored, expected in FQDN_IDNA_DRIFT:
                valu, _ = await s_migr.fqdndecnorm(migr, stored, {'type': ftyp})
                if stored in FQDN_IDNA_UNDECODABLE:
                    self.eq(valu, stored)
                else:
                    self.eq(valu, expected)

            # an opaque value that merely looks like punycode (idna cannot decode
            # it) is left unchanged, matching a fresh norm()
            opaque = 'xn--lskfjaslkdfjaslfj.link'
            valu, _ = await s_migr.fqdndecnorm(migr, opaque, {'type': ftyp})
            self.eq(valu, opaque)
            self.eq(valu, (await ftyp.norm(opaque))[0])

    async def test_migr_urldecnorm(self):
        '''The inet:url form and inet:url typed props (including arrays) get a
        decode + renormalize migration so the idna encoded host of a stored url is
        renormalized to match the current normalization.'''
        async with self._getBareMigr(model=True, stors=True) as (migr, _, _):

            await migr._migrDatamodel()

            # the inet:url form and inet:url typed props (direct and array) are
            # registered with the url decode + renorm migration
            self.eq(migr.formmigr['inet:url'][0], s_migr.urldecnorm)
            self.nn(migr.formmigr['inet:url'][1].get('type'))
            self.eq(migr.propmigr['biz:rfp']['url'][0], s_migr.urldecnorm)
            self.eq(migr.propmigr['crypto:x509:cert']['crl:urls'][0], s_migr.urldecnorm)

            utyp = migr.model.type('inet:url')

            # the punycode host stored by an older idna is decoded and renormalized,
            # dropping the now-ignored codepoint, while the path is left untouched
            valu, info = await s_migr.urldecnorm(migr, 'http://xn--aa-iuk.link/p', {'type': utyp})
            self.eq(valu, 'http://aa.link/p')

            # only the host (authority) is decoded; an identical token in the path
            # is preserved verbatim
            valu, info = await s_migr.urldecnorm(migr, 'http://xn--aa-iuk.link/xn--aa-iuk.link', {'type': utyp})
            self.eq(valu, 'http://aa.link/xn--aa-iuk.link')

            # user info and ports survive the host decode
            valu, info = await s_migr.urldecnorm(migr, 'http://user:pass@xn--aa-iuk.link:8080/p', {'type': utyp})
            self.eq(valu, 'http://user:pass@aa.link:8080/p')

            # a url with no encoded host is still renormalized but otherwise unchanged
            valu, info = await s_migr.urldecnorm(migr, 'http://vertex.link/p', {'type': utyp})
            self.eq(valu, 'http://vertex.link/p')

            # an encoded label that appears only in the path (not the host) is
            # left untouched
            valu, info = await s_migr.urldecnorm(migr, 'http://vertex.link/xn--aa-iuk.link', {'type': utyp})
            self.eq(valu, 'http://vertex.link/xn--aa-iuk.link')

            # a hostless url (e.g. local file) with an encoded token in the path
            # has no host sub to decode and is left untouched
            valu, info = await s_migr.urldecnorm(migr, 'file:///xn--aa-iuk/p', {'type': utyp})
            self.eq(valu, 'file:///xn--aa-iuk/p')

            # inet:url was originally renormalized to strip whitespace; urldecnorm
            # must remain a superset of that, fixing whitespace AND the idna host
            # drift in a single pass (plain renorm leaves the punycode host as-is)
            valu, info = await s_migr.urldecnorm(migr, 'http://xn--aa-iuk.link/path  ', {'type': utyp})
            self.eq(valu, 'http://aa.link/path')

            # a poly-typed url prop wraps the renormalized value
            ptyp = migr.model.prop('biz:rfp:url').type
            valu, info = await s_migr.urldecnorm(migr, 'http://xn--aa-iuk.link/p', {'type': ptyp})
            self.eq(valu, ('inet:url', 'http://aa.link/p'))

            # array-of-url values are decoded element-wise (only encoded hosts)
            atyp = migr.model.prop('crypto:x509:cert:crl:urls').type
            valu, info = await s_migr.urldecnorm(migr, ('http://xn--aa-iuk.link/p', 'http://vertex.link/q'), {'type': atyp})
            self.eq(valu, (('inet:url', 'http://aa.link/p'), ('inet:url', 'http://vertex.link/q')))

    async def test_migr_arrayproptoedge(self):
        '''Cover module-level arrayproptoedge: emits one edge per array member and
        returns novalu.'''
        async with self._getBareMigr(stors=True) as (migr, _, _):
            edits = []
            opts = {'verb': 'refs', 'destform': 'inet:fqdn'}
            valu, norminfo = await s_migr.arrayproptoedge(migr, ('vertex.link', 'woot.com'), opts, edits=edits)
            self.eq(valu, s_common.novalu)
            self.none(norminfo)
            self.len(2, edits)
            self.eq(edits[0][0], s_layer.EDIT_EDGE_ADD)
            self.eq(edits[0][1][0], 'refs')

    async def test_migr_secstoduration(self):
        '''Cover module-level secstoduration which scales a TTL in seconds to
        the microseconds stored by the duration type.'''
        async with self._getBareMigr() as (migr, _, _):
            valu, info = await s_migr.secstoduration(migr, 300, {})
            self.eq(valu, 300000000)
            self.eq(info, {})

    async def test_migr_currencytocurrencies(self):
        '''Cover module-level currencytocurrencies which renames the scalar
        pol:vitals:currency prop to the pol:vitals:currencies array.'''
        async with self._getBareMigr(model=True) as (migr, _, _):
            edits = []
            valu, info = await s_migr.currencytocurrencies(migr, 'usd', {}, edits=edits)
            self.eq(valu, s_common.novalu)
            self.none(info)
            self.len(1, edits)
            self.eq(edits[0][0], s_layer.EDIT_PROP_SET)
            self.eq(edits[0][1][0], 'currencies')
            self.eq(edits[0][1][1], ('usd',))

    async def test_migr_langtranslation_missing_destprops(self):
        '''Cover langtranslation _propEdit/_langPropEdit returning None when the
        destination model prop does not exist.'''
        async with self._getBareMigr(stors=True) as (migr, _, _):
            migr.model = mock.Mock()
            migr.model.prop = mock.Mock(return_value=None)

            sode = {
                'valu': ('30773ecd0c3b295371e90d8852ff8387', s_layer.STOR_TYPE_GUID),
                'props': {
                    'input': ('green', s_layer.STOR_TYPE_UTF8),
                    'input:lang': ('en', s_layer.STOR_TYPE_UTF8),
                    'output': ('vert', s_layer.STOR_TYPE_UTF8),
                    'output:lang': ('fr', s_layer.STOR_TYPE_UTF8),
                    'engine': ('30773ecd0c3b295371e90d8852ff8387', s_layer.STOR_TYPE_GUID),
                    'desc': ('guiddesc', s_layer.STOR_TYPE_UTF8),
                },
            }
            edits = []
            nodeedits = []
            await s_migr.langtranslation(migr, sode, edits, nodeedits)

            # The node-add for the translation guid is still emitted; all prop
            # edits were dropped because the destination props are missing.
            self.eq(edits, [(s_layer.EDIT_NODE_ADD, ('30773ecd0c3b295371e90d8852ff8387', s_layer.STOR_TYPE_GUID, {}))])
            # input:lang / output:lang still emit the language node-adds (without code).
            self.len(2, nodeedits)

    async def test_migr_langtranslation_bcp47(self):
        '''Legacy 2.x lang:code values are translated to canonical BCP-47.'''
        async with self._getBareMigr(model=True, stors=True) as (migr, _, _):

            sode = {
                'valu': ('30773ecd0c3b295371e90d8852ff8387', s_layer.STOR_TYPE_GUID),
                'props': {
                    'input:lang': ('pt.br', s_layer.STOR_TYPE_UTF8),
                    'output:lang': ('xx.yy.zz', s_layer.STOR_TYPE_UTF8),
                },
            }
            edits = []
            nodeedits = []
            await s_migr.langtranslation(migr, sode, edits, nodeedits)

            codes = []
            for (nid, form, subedits) in nodeedits:
                for edit in subedits:
                    if edit[0] == s_layer.EDIT_PROP_SET and edit[1][0] == 'code':
                        # lang:code is a form, so the code prop stores a poly ref
                        codes.append(edit[1][1][1])

            # the dotted separator is translated to a canonical BCP-47 tag, while a
            # value that is not a valid tag falls back to its raw form
            self.sorteq(['pt-BR', 'xx.yy.zz'], codes)

    async def test_migr_repocomment(self):
        '''Cover repocommentmigr folding 2.x repo issue/diff comments into the
        generic inet:service:comment form.'''
        async with self._getBareMigr(model=True) as (migr, _, _):

            issue = s_common.guid()
            creator = s_common.guid()
            replyto = s_common.guid()
            platform = s_common.guid()

            sode = {
                'valu': (s_common.guid(), s_layer.STOR_TYPE_GUID),
                'props': {
                    'issue': (issue, s_layer.STOR_TYPE_GUID),
                    'creator': (creator, s_layer.STOR_TYPE_GUID),
                    'replyto': (replyto, s_layer.STOR_TYPE_GUID),
                    'platform': (platform, s_layer.STOR_TYPE_GUID),
                    'status': ('open', s_layer.STOR_TYPE_UTF8),
                    'text': ('a comment on an issue', s_layer.STOR_TYPE_UTF8),
                    'url': ('https://github.com/vertexproject/synapse/issues/1#c1', s_layer.STOR_TYPE_UTF8),
                    'updated': (93, s_layer.STOR_TYPE_MINTIME),
                },
            }
            edits = []
            await s_migr.repocommentmigr(migr, sode, edits, [])

            self.eq(edits[0][0], s_layer.EDIT_NODE_ADD)
            sets = {e[1][0]: e[1][1] for e in edits if e[0] == s_layer.EDIT_PROP_SET}

            # :issue is folded into the :about commentable poly reference
            self.eq(sets['about'], ('it:dev:repo:issue', issue))
            # the inet:service:object :creator carries over directly
            self.eq(sets['creator'], ('inet:service:account', creator))
            # form-typed props are stored as poly (form, guid) references
            self.eq(sets['replyto'], ('inet:service:comment', replyto))
            self.eq(sets['platform'], ('inet:service:platform', platform))
            self.eq(sets['status'], ('title', 'open'))
            self.eq(sets['text'], ('text', 'a comment on an issue'))
            self.eq(sets['url'], ('inet:url', 'https://github.com/vertexproject/synapse/issues/1#c1'))
            # props with no inet:service:comment equivalent are dropped
            self.notin('updated', sets)
            self.notin('issue', sets)

        async with self._getBareMigr(model=True) as (migr, _, _):

            diff = s_common.guid()
            sode = {
                'valu': (s_common.guid(), s_layer.STOR_TYPE_GUID),
                'props': {
                    'diff': (diff, s_layer.STOR_TYPE_GUID),
                    'text': ('types types types', s_layer.STOR_TYPE_UTF8),
                    'line': (100, s_layer.STOR_TYPE_I64),
                    'offset': (100, s_layer.STOR_TYPE_I64),
                },
            }
            edits = []
            await s_migr.repocommentmigr(migr, sode, edits, [])

            sets = {e[1][0]: e[1][1] for e in edits if e[0] == s_layer.EDIT_PROP_SET}
            # :diff is folded into the :about commentable poly reference
            self.eq(sets['about'], ('it:dev:repo:diff', diff))
            self.eq(sets['text'], ('text', 'types types types'))
            # the diff-specific :line / :offset props are dropped
            self.notin('line', sets)
            self.notin('offset', sets)

        # when the destination props are missing only the node-add is emitted
        async with self._getBareMigr(model=True) as (migr, _, _):
            migr.model = mock.Mock()
            migr.model.prop = mock.Mock(return_value=None)

            sode = {
                'valu': (s_common.guid(), s_layer.STOR_TYPE_GUID),
                'props': {
                    'issue': (s_common.guid(), s_layer.STOR_TYPE_GUID),
                    'creator': (s_common.guid(), s_layer.STOR_TYPE_GUID),
                    'text': ('x', s_layer.STOR_TYPE_UTF8),
                },
            }
            edits = []
            await s_migr.repocommentmigr(migr, sode, edits, [])
            self.eq(edits, [(s_layer.EDIT_NODE_ADD, (sode['valu'][0], s_layer.STOR_TYPE_GUID, {}))])

    async def test_migr_repolabel(self):
        '''Cover repolabelmigr / repoissuelabelmigr generalizing the 2.x repo label
        forms into inet:service:label / inet:service:labeled.'''
        async with self._getBareMigr(model=True) as (migr, _, _):

            sode = {
                'valu': (s_common.guid(), s_layer.STOR_TYPE_GUID),
                'props': {
                    'id': ('lbl-1', s_layer.STOR_TYPE_UTF8),
                    'title': ('good first issue', s_layer.STOR_TYPE_UTF8),
                    'desc': ('newcomer friendly', s_layer.STOR_TYPE_UTF8),
                },
            }
            edits = []
            await s_migr.repolabelmigr(migr, sode, edits, [])

            self.eq(edits[0][0], s_layer.EDIT_NODE_ADD)
            sets = {e[1][0]: e[1][1] for e in edits if e[0] == s_layer.EDIT_PROP_SET}
            # the 2.x :title becomes the :name
            self.eq(sets['name'], ('title', 'good first issue'))
            self.eq(sets['desc'], ('text', 'newcomer friendly'))
            self.notin('title', sets)

        async with self._getBareMigr(model=True) as (migr, _, _):

            issue = s_common.guid()
            label = s_common.guid()
            creator = s_common.guid()
            platform = s_common.guid()

            sode = {
                'valu': (s_common.guid(), s_layer.STOR_TYPE_GUID),
                'props': {
                    'issue': (issue, s_layer.STOR_TYPE_GUID),
                    'label': (label, s_layer.STOR_TYPE_GUID),
                    'creator': (creator, s_layer.STOR_TYPE_GUID),
                    'platform': (platform, s_layer.STOR_TYPE_GUID),
                    'status': ('applied', s_layer.STOR_TYPE_UTF8),
                    'applied': (93, s_layer.STOR_TYPE_MINTIME),
                },
            }
            edits = []
            await s_migr.repoissuelabelmigr(migr, sode, edits, [])

            sets = {e[1][0]: e[1][1] for e in edits if e[0] == s_layer.EDIT_PROP_SET}
            # the labeled issue becomes the :about labelable reference
            self.eq(sets['about'], ('it:dev:repo:issue', issue))
            # :label points at the renamed inet:service:label form
            self.eq(sets['label'], ('inet:service:label', label))
            self.eq(sets['creator'], ('inet:service:account', creator))
            self.eq(sets['platform'], ('inet:service:platform', platform))
            self.eq(sets['status'], ('title', 'applied'))
            # the diff-only :applied timestamp has no equivalent and is dropped
            self.notin('applied', sets)
            self.notin('issue', sets)

        # when the destination props are missing only the node-add is emitted
        async with self._getBareMigr(model=True) as (migr, _, _):
            migr.model = mock.Mock()
            migr.model.prop = mock.Mock(return_value=None)

            sode = {
                'valu': (s_common.guid(), s_layer.STOR_TYPE_GUID),
                'props': {'title': ('x', s_layer.STOR_TYPE_UTF8)},
            }
            edits = []
            await s_migr.repolabelmigr(migr, sode, edits, [])
            self.eq(edits, [(s_layer.EDIT_NODE_ADD, (sode['valu'][0], s_layer.STOR_TYPE_GUID, {}))])

            sode = {
                'valu': (s_common.guid(), s_layer.STOR_TYPE_GUID),
                'props': {'issue': (s_common.guid(), s_layer.STOR_TYPE_GUID)},
            }
            edits = []
            await s_migr.repoissuelabelmigr(migr, sode, edits, [])
            self.eq(edits, [(s_layer.EDIT_NODE_ADD, (sode['valu'][0], s_layer.STOR_TYPE_GUID, {}))])

    async def test_migr_migrate_guards(self):
        '''Cover migrate() dirn-None guard and the _setupDest False short-circuit.'''
        async with self._getBareMigr() as (migr, _, dest):
            migr.dirn = None
            with self.raises(Exception):
                await migr.migrate()

            migr.dirn = dest
            with mock.patch.object(migr, '_setupDest', mock.AsyncMock(return_value=False)) as setup:
                await migr.migrate()
                setup.assert_awaited()

    async def test_migr_initstors_nextnid(self):
        '''Cover _initStors computing nextnid from a pre-existing v3 nid2ndef key.'''
        async with self._getBareMigr() as (migr, _, dest):
            v3path = os.path.join(dest, 'slabs', 'layersv3.lmdb')
            async with await s_lmdbslab.Slab.anit(v3path) as pre:
                nid2ndef = pre.initdb('nid2ndef')
                pre._put(s_common.int64en(41), s_msgpack.en(('test:str', 'x')), db=nid2ndef)

            await migr._initStors()
            self.eq(migr.nextnid, 42)

    async def test_migr_dirn_rerun(self):
        '''Cover _migrDirn over a fresh dest (gendir) and a re-run where the dest
        already contains layers/files/axon/slabs/views/dirs.'''
        conf = {'src': None, 'dest': None}
        async with self._getTestMigrCore(conf) as (migr, dest):

            # remove dest so the gendir branch runs
            shutil.rmtree(dest)
            await migr._migrDirn()
            self.true(os.path.exists(dest))

            # nexus.lmdb (kept by the slabs cleanup) and views/ (no exists handling)
            # would be re-copied by backup on the second run; drop them so the
            # re-run does not collide.
            nexp = os.path.join(dest, 'slabs', 'nexus.lmdb')
            if os.path.exists(nexp):
                shutil.rmtree(nexp)

            viewp = os.path.join(dest, 'views')
            if os.path.exists(viewp):
                shutil.rmtree(viewp)

            # second run: dest now populated, exercises the exists branches
            await migr._migrDirn()
            self.true(os.path.exists(os.path.join(dest, 'cell.guid')))

    async def test_migr_nodeedits_branches(self):
        '''Cover migrNodeEdits: migrated form with no migrinfo (skip) and the
        2-element edit item branch.'''
        async with self._getBareMigr(stors=True) as (migr, _, _):

            # migrated form (hash:md5) with no migrinfo entry -> skipped
            migbuid = s_common.buid(('hash:md5', 'd41d8cd98f00b204e9800998ecf8427e'))
            skipped = await migr.migrNodeEdits([(migbuid, 'hash:md5', ())])
            self.eq(skipped, [])

            # non-migrated form -> _genBuidNid; 2-element edit item
            buid = s_common.buid(('it:dev:str', 'vertex.link'))
            edit = (s_layer.EDIT_NODE_ADD, ('vertex.link', s_layer.STOR_TYPE_UTF8))
            out = await migr.migrNodeEdits([(buid, 'it:dev:str', (edit,))])
            self.len(1, out)
            self.eq(out[0][1], 'it:dev:str')
            self.eq(out[0][2][0][0], s_layer.EDIT_NODE_ADD)

    async def test_migr_extmodel_branches(self):
        '''Cover _migrExtmodel deprecated-form/prop removal, add errors, and the
        extforms/extprops pops.'''
        async with self._getBareMigr(model=True, stors=True) as (migr, _, _):

            extforms = migr.cortexdata.getSubKeyVal('model:forms:')
            extforms.set('_dep:form', ('_dep:form', 'int', {}, {'deprecated': True}))
            extforms.set('_bad:form', ('_bad:form', 'newp:newp:newp', {}, {}))

            extprops = migr.cortexdata.getSubKeyVal('model:props:')
            extprops.set('it:dev:str:_depprop', ('it:dev:str', '_depprop', ('int', {}), {'deprecated': True}))

            await migr._migrExtmodel()

            self.isin('_dep:form', migr.remforms)
            self.none(migr.extforms.get('_dep:form'))

            self.isin('it:dev:str:_depprop', migr.remprops)
            self.none(migr.extprops.get('it:dev:str:_depprop'))

    async def test_migr_indxabrv_and_freespace(self):
        '''Cover getAbrvIndx (round-trip with setIndxAbrv) and checkFreeSpace.'''
        async with self._getBareMigr(stors=True) as (migr, _, _):
            abrv = migr.setIndxAbrv(b'\x00\x01', 'a', 'b')
            self.eq(migr.getAbrvIndx(abrv), ('a', 'b'))
            self.none(migr.checkFreeSpace())

    async def test_migr_storm_pkg_vers(self):
        '''Cover _migrStormPkgVers moving a storm package storage:version from the
        2.x package vars into the 3.x package state, and skipping packages that
        have no storage:version var.'''
        async with self._getBareMigr(stors=True) as (migr, _, _):

            pkgdefs = migr.cortexdata.getSubKeyVal('storm:packages:')
            pkgdefs.set('coverpkg', {'name': 'coverpkg'})
            pkgdefs.set('covernopkg', {'name': 'covernopkg'})

            migr.cortexdata.getSubKeyVal('stormpkg:vars:coverpkg:').set('storage:version', 3)
            # a package without storage:version exercises the skip branch
            migr.cortexdata.getSubKeyVal('stormpkg:vars:covernopkg:').set('other', 1)

            migr._migrStormPkgVers()

            self.eq(3, migr.cortexdata.getSubKeyVal('stormpkg:state:coverpkg:').get('storage:version'))
            self.none(migr.cortexdata.getSubKeyVal('stormpkg:vars:coverpkg:').get('storage:version'))
            self.none(migr.cortexdata.getSubKeyVal('stormpkg:state:covernopkg:').get('storage:version'))

    async def test_migr_translate_crafted_layer(self):
        '''Cover translateLayerNodeEdits edge/error branches by scanning a crafted
        source layer slab: a formless node, a deleted-form node with no migrinfo
        (unkbuids), a migrated node whose norminfo carries an unknown sub, a node
        with a deleted prop, a node with an ndef prop pointing at a renamed form,
        and a node with a dangling edge plus an invalid-verb edge.'''
        async with self._getBareMigr(model=True, stors=True) as (migr, src, _):

            migr.extedges = migr.cortexdata.getSubKeyVal('model:edges:')
            migr.propmigr['inet:fqdn'] = {'_delprop': (None, None)}

            iden = s_common.guid()
            os.makedirs(os.path.join(src, 'layers', iden))
            lpath = os.path.join(src, 'layers', iden, 'layer_v2.lmdb')
            ndpath = os.path.join(src, 'layers', iden, 'nodedata.lmdb')

            # formless node
            buidA = s_common.buid(('a',))
            sodeA = {'valu': ('x', s_layer.STOR_TYPE_UTF8)}

            # deleted/renamed form with no migrinfo value -> unkbuids
            buidB = s_common.buid(('hash:md5', 'b'))
            sodeB = {'form': 'hash:md5', 'valu': ('b', s_layer.STOR_TYPE_UTF8)}

            # migrated node (via migrinfo) whose norminfo sub is unknown in the model
            buidG = s_common.buid(('hash:md5', 'g'))
            sodeG = {'form': 'hash:md5', 'valu': ('rawg', s_layer.STOR_TYPE_UTF8)}
            migv = s_msgpack.en((s_common.int64en(5000), s_common.buid(('it:dev:str', 'g')),
                                 'it:dev:str', 'gval', {'subs': {'fakesub': (0, 5)}, 'virts': None}))
            migr.migrslab._put(buidG, migv, db=migr.migrinfo)

            # surviving node with a deleted prop
            buidD = s_common.buid(('inet:fqdn', 'd.com'))
            migr._genIndxNid(buidD, ('inet:fqdn', 'd.com'))
            sodeD = {'form': 'inet:fqdn', 'valu': ('d.com', s_layer.STOR_TYPE_UTF8),
                     'props': {'_delprop': ('x', s_layer.STOR_TYPE_UTF8)}}

            # non-migrated form with an unregistered buid -> _genBuidNid
            buidF = s_common.buid(('it:dev:str', 'fdev'))
            sodeF = {'form': 'it:dev:str', 'valu': ('fdev', s_layer.STOR_TYPE_UTF8)}

            # surviving node with ndef props: one pointing at a renamed form
            # (migrates) and one pointing at a deleted form (migr func is None and
            # raises, hitting the failure branch)
            buidC = s_common.buid(('it:dev:str', 'cnode'))
            migr._genIndxNid(buidC, ('it:dev:str', 'cnode'))
            sodeC = {'form': 'it:dev:str', 'valu': ('cnode', s_layer.STOR_TYPE_UTF8),
                     'props': {'_ndefprop': (('hash:md5', 'd41d8cd98f00b204e9800998ecf8427e'),
                                             s_layer.STOR_TYPE_NDEF),
                               '_ndefbad': (('edge:refs', 'xxx'), s_layer.STOR_TYPE_NDEF)}}

            # surviving node with a dangling edge and an invalid-verb edge
            buidE = s_common.buid(('it:dev:str', 'esrc'))
            migr._genIndxNid(buidE, ('it:dev:str', 'esrc'))
            sodeE = {'form': 'it:dev:str', 'valu': ('esrc', s_layer.STOR_TYPE_UTF8)}

            n2tgt = s_common.buid(('it:dev:str', 'etgt'))
            migr._genIndxNid(n2tgt, ('it:dev:str', 'etgt'))
            n2dangle = s_common.buid(('it:dev:str', 'nope'))

            async with await s_lmdbslab.Slab.anit(lpath) as lslab:
                bybuidv3 = lslab.initdb('bybuidv3')
                edgesn1 = lslab.initdb('edgesn1', dupsort=True)
                for buid, sode in ((buidA, sodeA), (buidB, sodeB), (buidG, sodeG),
                                   (buidD, sodeD), (buidC, sodeC), (buidE, sodeE),
                                   (buidF, sodeF)):
                    lslab._put(buid, s_msgpack.en(sode), db=bybuidv3)

                lslab._put(buidE + b'plainverb', n2tgt, db=edgesn1, dupdata=True)
                lslab._put(buidE + b'danglverb', n2dangle, db=edgesn1, dupdata=True)

            async with await s_lmdbslab.Slab.anit(ndpath) as ndslab:
                ndslab.initdb('nodedata')

            layr = mock.Mock()
            layr.iden = iden

            nodeedits = [ne async for ne in migr.translateLayerNodeEdits(layr)]
            forms = [form for ne in nodeedits for (_, form, _) in ne]

            # the surviving nodes produced edits; the formless and unkbuids nodes did not
            self.isin('it:dev:str', forms)
            self.isin('inet:fqdn', forms)
            self.nn(migr.migrslab.get(buidB + s_common.uhex(iden), db=migr.unkbuids))

            # the invalid verb was auto-prefixed and a wildcard edge registered
            self.nn(migr.model.edgeIsValid('it:dev:str', '_plainverb', 'it:dev:str'))

    async def test_migr_layerbuids_extforms(self):
        '''Cover _migrLayerBuids extended-form skips: deprecated type (no model
        type) and an out-of-range stortype.'''
        async with self._getBareMigr(model=True, stors=True) as (migr, src, _):

            migr.extforms = {
                '_dep:ext': ('_dep:ext', 'no:such:type', {}, {}),
                '_big:ext': ('_big:ext', 'int', {}, {}),
            }

            iden = s_common.guid()
            os.makedirs(os.path.join(src, 'layers', iden))
            lpath = os.path.join(src, 'layers', iden, 'layer_v2.lmdb')
            async with await s_lmdbslab.Slab.anit(lpath) as lslab:
                name2abrv = lslab.initdb('propabrv:byts2abrv', dupsort=True, dupfixed=True)
                lslab._put(s_msgpack.en(('_dep:ext', None)), b'\x00\x00\x00\x00\x00\x00\x00\x01',
                           db=name2abrv, dupdata=True)
                lslab._put(s_msgpack.en(('_big:ext', None)), b'\x00\x00\x00\x00\x00\x00\x00\x02',
                           db=name2abrv, dupdata=True)

            newlayr = mock.Mock()
            newlayr.stortypes = [mock.Mock(), mock.Mock()]

            await migr._migrLayerBuids(iden, newlayr)

    async def test_migr_layerbuids_decode_and_migrfunc(self):
        '''Cover _migrLayerBuids decode-index failure, the bybuidv3 fallback (both
        the missing-buid warning and the value lookup), and a raising migr func.'''
        async with self._getBareMigr(model=True, stors=True) as (migr, src, _):

            async def boom(*args, **kwargs):
                raise Exception('boom')

            # inject a migration for inet:fqdn whose func always raises
            migr.formmigr['inet:fqdn'] = (boom, {'name': 'it:dev:str'})

            iden = s_common.guid()
            os.makedirs(os.path.join(src, 'layers', iden))
            lpath = os.path.join(src, 'layers', iden, 'layer_v2.lmdb')

            abrv = b'\x00\x00\x00\x00\x00\x00\x00\x01'
            buid1 = s_common.buid(('inet:fqdn', 'one'))
            buid2 = s_common.buid(('inet:fqdn', 'two'))

            async with await s_lmdbslab.Slab.anit(lpath) as lslab:
                name2abrv = lslab.initdb('propabrv:byts2abrv', dupsort=True, dupfixed=True)
                byprop = lslab.initdb('byprop', dupsort=True)
                bybuidv3 = lslab.initdb('bybuidv3')

                lslab._put(s_msgpack.en(('inet:fqdn', None)), abrv, db=name2abrv, dupdata=True)
                lslab._put(abrv + b'idx1', buid1, db=byprop, dupdata=True)
                lslab._put(abrv + b'idx2', buid2, db=byprop, dupdata=True)
                # buid1 has a sode (value fallback -> raising migr func); buid2 has none
                lslab._put(buid1, s_msgpack.en({'form': 'inet:fqdn', 'valu': ('one', s_layer.STOR_TYPE_UTF8)}),
                           db=bybuidv3)

            # oldmodel inet:fqdn stortype is 17; give the matching stor a decodeIndx
            # that always raises so the bybuidv3 fallback is taken.
            stors = [mock.Mock() for _ in range(20)]
            stors[17].decodeIndx = mock.Mock(side_effect=Exception('bad index'))
            newlayr = mock.Mock()
            newlayr.stortypes = stors

            await migr._migrLayerBuids(iden, newlayr)

    async def test_migr_nexslog_crafted(self):
        '''Cover _migrNexslog edge branches: a pre-trim edit whose meta lacks a
        time, a nexus edit for a nonexistent layer, a nexus edit with no matching
        nodeedits entry, and an edit whose time falls back to the nexus args.'''
        async with self._getBareMigr(stors=True) as (migr, src, dest):

            migr.celliden = s_common.guid()
            iden = s_common.guid()
            migr.layrdefs.set(iden, {})

            # per-layer nodeedits seqn: offs 0 is pre-trim (meta without time),
            # offs 5 is referenced by the main loop with meta=None
            nepath = os.path.join(src, 'layers', iden, 'nodeedits.lmdb')
            async with await s_lmdbslab.Slab.anit(nepath) as neslab:
                seqn = s_slabseqn.SlabSeqn(neslab, 'nodeedits')
                seqn.add(([], {'user': 'x'}), indx=0)
                seqn.add(([], None), indx=5)

            other = s_common.guid()
            spath = os.path.join(src, 'slabs', 'nexuslog')
            async with await s_multislabseqn.MultiSlabSeqn.anit(spath) as srclog:
                await srclog.add((iden, 'init', (), {}, None), indx=0)
                await srclog.add((iden, 'init', (), {}, None), indx=1)
                await srclog.add((iden, 'init', (), {}, None), indx=2)
                await srclog.add((other, 'edits', (None, None), {}, None), indx=3)
                await srclog.add((iden, 'edits', (None, None), {}, None), indx=4)
                await srclog.add((iden, 'edits', (None, {'time': 12345}), {}, None), indx=5)
                # cull so the persisted firstindx > 0, exercising the pre-trim path
                await srclog.cull(2)

            await migr._migrNexslog()

            dpath = os.path.join(dest, 'slabs', 'nexuslog')
            async with await s_multislabseqn.MultiSlabSeqn.anit(dpath) as dstlog:
                tail = [item async for _, item in dstlog.iter(0)]
            # the final nexs:vers:set marker was always written
            self.eq(tail[-1][1], 'nexs:vers:set')

import os
import copy
import http
import time
import asyncio
import hashlib
import logging

import regex

from unittest import mock

import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.models as s_models
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.node as s_node
import synapse.lib.time as s_time
import synapse.lib.layer as s_layer
import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.msgpack as s_msgpack
import synapse.lib.schemas as s_schemas
import synapse.lib.version as s_version
import synapse.lib.jsonstor as s_jsonstor
import synapse.lib.stormsvc as s_stormsvc

import synapse.tools.service.backup as s_tools_backup
import synapse.tools.service.promote as s_tools_promote

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

logger = logging.getLogger(__name__)

class HasCoreCell(s_cortex.HasCore, s_cell.Cell):
    # a minimal Cell which mixes in HasCore to exercise the mixin directly.
    confdefs = {
        'http:proxy': {
            'description': 'Proxy URL threaded into the embedded cortex.',
            'type': 'string',
        },
        'tls:ca:dir': {
            'description': 'CA dir threaded into the embedded cortex.',
            'type': 'string',
        },
    }

    corelinked = False
    embcalled = False

    async def _initEmbeddedCore(self, core):
        await super()._initEmbeddedCore(core)
        self.embcalled = True

    async def _onLinkCore(self, proxy, urlinfo):
        # exercise the overridable onlink hook ( and keep the cached info via super )
        await super()._onLinkCore(proxy, urlinfo)
        self.corelinked = True

class HasCoreTest(s_t_utils.SynTest):

    async def test_cortex_hascore_embedded(self):
        # a standalone ( non-aha ) HasCore cell boots an embedded cortex, reaches
        # it via a local client, and threads its http:proxy / tls:ca:dir conf.
        with self.getTestDir() as dirn:

            cadir = s_common.gendir(dirn, 'cas')
            proxyurl = 'socks5://user:pass@127.0.0.1:1'
            conf = {'http:proxy': proxyurl, 'tls:ca:dir': cadir}

            async with await HasCoreCell.anit(dirn, conf=conf) as cell:

                # getCore() returns a proxy even for the embedded cortex
                core = await cell.getCore()
                self.eq(1, await core.callStorm('return((1))'))

                # the _initEmbeddedCore hook ran and the embedded cortex got the conf
                self.true(cell.embcalled)
                self.eq(proxyurl, cell._has_core.conf.get('http:proxy'))
                self.eq(cadir, cell._has_core.conf.get('tls:ca:dir'))

                # the local client link fired _onLinkCore ( populating cached info )
                self.true(cell.corelinked)
                self.true(cell._has_coreinfo)
                info = await cell.getCoreInfo()
                self.isin('cell', info)

                # force the lazy getCoreInfo fetch path
                cell._has_coreinfo = {}
                self.isin('cell', await cell.getCoreInfo())

    async def test_cortex_hascore_aha(self):
        # an aha client HasCore cell resolves the cortex by cell type ( aha://cortex... )
        async with self.getTestAha() as aha:

            async with self.addSvcToAha(aha, '00.cortex', s_cortex.Cortex):

                async with self.addSvcToAha(aha, '00.hascore', HasCoreCell) as cell:

                    # remote: no embedded cortex, resolved via aha
                    self.none(cell._has_core)
                    self.false(cell.embcalled)

                    core = await asyncio.wait_for(cell.getCore(), timeout=10)
                    self.eq(1, await core.callStorm('return((1))'))

                    # the overridable _onLinkCore hook fired on connect
                    self.true(cell.corelinked)

                    info = await cell.getCoreInfo()
                    self.isin('cell', info)

class CortexTest(s_t_utils.SynTest):
    '''
    The tests that should be run with different types of layers
    '''
    async def test_cortex_readonly(self):
        '''
        A read-only Cortex with no AHA deployment connects directly to the
        leader's embedded jsonstor and axon unix sockets rather than booting its
        own. Its pkg:add handler
        drops any copy it already loaded (tracked in the in-memory stormpkgs,
        since pkgdefs reads through to the leader's current def) before
        (re)loading, and makes no durable write.
        '''
        with self.getTestDir() as dirn:

            # write with the leader, then release its slabs so the read-only
            # Cortex can open the shared dirn in this same process.
            svciden = s_common.guid()
            async with self.getTestCore(dirn=dirn) as core:
                await core.nodes('[ inet:ip=1.2.3.4 ]')
                # seed a durable svcdef so the read-only cortex sees it read
                # through to the leader's committed svcdefs. It has no ``url``,
                # so the read-only cortex's boot-time _initStormSvcs logs a
                # benign "initStormService ... failed: BadArg" warning when it
                # tries to connect; a real sdef always carries a url.
                core.svcdefs.set(svciden, {'iden': svciden, 'name': 'testsvc'})

            # stand the leader's embedded jsonstor / axon back up on their own
            # sockets so the read-only Cortex has live services to connect to.
            jsonpath = os.path.join(dirn, 'jsonstor')
            axonpath = os.path.join(dirn, 'axon')
            storconf = {'health:sysctl:checks': False}

            async with await s_jsonstor.JsonStorCell.anit(jsonpath, conf=storconf) as jsoncell, \
                       await s_axon.Axon.anit(axonpath, conf=storconf) as axoncell:

                async with await s_cortex.Cortex.anit(dirn, readonly=True) as core:

                    # the read-only cortex connects to the leader's jsonstor /
                    # axon sockets via telepath clients rather than booting its
                    # own embedded cells.
                    self.none(core._has_jsonstor)
                    self.none(core._has_axon)
                    self.nn(await asyncio.wait_for(core.getJsonStor(), timeout=10))
                    self.nn(await asyncio.wait_for(core.getAxon(), timeout=10))
                    self.nn(await core.getAxonInfo())

                    pkgdef = {
                        'name': 'testpkg',
                        'version': (0, 0, 1),
                        'commands': ({'name': 'testcmd', 'storm': 'inet:ip'},),
                    }

                    # first replay: nothing loaded yet, so it just loads
                    await core._addStormPkg(pkgdef)
                    self.nn(core.stormpkgs.get('testpkg'))
                    self.nn(core.getStormCmd('testcmd'))

                    # a second replay finds the loaded copy and drops it before
                    # (re)loading to match the replayed event
                    await core._addStormPkg(pkgdef)
                    self.nn(core.stormpkgs.get('testpkg'))
                    self.nn(core.getStormCmd('testcmd'))

                    # setStormSvcEvents / _runStormSvcAdd are called on the
                    # read-only cortex when a storm service connects, but a
                    # reader takes no part in service event tracking (only the
                    # active leader runs the add/del hooks that consume evts).
                    evts = {'add': {'storm': '$lib.print(hi)'}}
                    sdef = await core.setStormSvcEvents(svciden, evts)
                    self.notin('evts', sdef)

                    self.none(await core._runStormSvcAdd(svciden))

                    stored = core.svcdefs.get(svciden)
                    self.notin('evts', stored)
                    self.notin('added', stored)

    async def test_cortex_nexuscommit(self):
        # the Cortex commits its slabs after each nexus transaction rather than
        # on the timed sync loop: its slabs are commitpulse=False and an applied
        # edit is durable (committed) as soon as it returns, with no timer wait.
        async with self.getTestCore() as core:

            self.true(core.nexuscommit)

            # cortex-owned slabs opt out of the periodic pulse
            self.false(core.slab.commitpulse)
            self.false(core.v3stor.commitpulse)
            self.false(core.nexsroot.nexsslab.commitpulse)

            layr = core.getLayer()
            self.false(layr.layrslab.commitpulse)
            self.false(layr.dataslab.commitpulse)

            # the periodic sync loop skips commitpulse=False slabs, so the only
            # thing that can commit them is the per-transaction commit in
            # NexsRoot._eat. syncLoopOnce here is therefore a no-op for the layer.
            await core.nodes('[ inet:ip=1.2.3.4 ]')
            await layr.layrslab.syncLoopOnce()

            # edit:indx read fresh from the committed slab (bypassing the
            # in-memory HotCount cache) matches the applied edit offset - the
            # edit was made durable by the nexus transaction, not a timer.
            committed = layr.editindx.getFresh('edit:indx', defv=-1)
            self.eq(committed, layr.getEditIndx())
            self.gt(committed, -1)

    async def test_cortex_commitpulse(self):
        # the commit pulse signals the offset of each committed nexus transaction.
        async with self.getTestCore() as core:

            self.true(core.nexuscommit)

            genr = core.getNexusCommitPulse()
            try:
                # the first item is the last FULLY committed offset at attach
                # time (never the not-yet-written next offset).
                first = await asyncio.wait_for(genr.__anext__(), timeout=6)
                self.eq(first, await core.getNexsIndx() - 1)

                # a committed transaction pulses its offset, and that offset is
                # already durable when the pulse fires.
                await core.nodes('[ inet:ip=1.2.3.4 ]')
                offs = await core.getNexsIndx() - 1

                pulsed = first
                while pulsed < offs:
                    pulsed = await asyncio.wait_for(genr.__anext__(), timeout=6)

                self.eq(pulsed, offs)

                layr = core.getLayer()
                self.ge(layr.editindx.getFresh('edit:indx', defv=-1), pulsed)

            finally:
                await genr.aclose()

            # over a telepath proxy the offsets are pushed directly on the link
            # (rather than yielded through the daemon genr loop).
            async with core.getLocalProxy() as prox:
                genr = prox.getNexusCommitPulse().__aiter__()
                try:
                    first = await asyncio.wait_for(genr.__anext__(), timeout=6)
                    self.eq(first, await core.getNexsIndx() - 1)

                    await core.nodes('[ inet:ip=5.6.7.8 ]')
                    offs = await core.getNexsIndx() - 1

                    pulsed = first
                    while pulsed < offs:
                        pulsed = await asyncio.wait_for(genr.__anext__(), timeout=6)

                    self.eq(pulsed, offs)

                finally:
                    await genr.aclose()

    async def test_cortex_basics(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                with self.raises(s_exc.NoSuchProp):
                    await core.setPropLocked('newp', True)

                with self.raises(s_exc.NoSuchTagProp):
                    await core.setTagPropLocked('newp', True)

                await core.addTagProp('_score', ('int', {}), {})

                await core.setPropLocked('inet:ip:asn', True)
                await core.setTagPropLocked('_score', True)

                with self.raises(s_exc.IsDeprLocked):
                    await core.nodes('[ inet:ip=1.2.3.4 :asn=99 ]')
                with self.raises(s_exc.IsDeprLocked):
                    await core.nodes('[ inet:ip=1.2.3.4 +#foo:_score=10 ]')

            # test persistence...
            async with self.getTestCore(dirn=dirn) as core:

                with self.raises(s_exc.IsDeprLocked):
                    await core.nodes('[ inet:ip=1.2.3.4 :asn=99 ]')
                with self.raises(s_exc.IsDeprLocked):
                    await core.nodes('[ inet:ip=1.2.3.4 +#foo:_score=10 ]')

                await core.setPropLocked('inet:ip:asn', False)
                await core.setTagPropLocked('_score', False)

                await core.nodes('[ inet:ip=1.2.3.4 :asn=99 +#foo:_score=10 ]')

    async def test_cortex_cellguid(self):
        iden = s_common.guid()
        conf = {'cell:guid': iden}
        async with self.getTestCore(conf=conf) as core00:
            async with self.getTestCore(conf=conf) as core01:
                self.eq(core00.iden, core01.iden)
                self.eq(core00._has_jsonstor.iden, core01._has_jsonstor.iden)
                self.eq(core00._has_jsonstor.auth.allrole.iden, core01._has_jsonstor.auth.allrole.iden)
                self.eq(core00._has_jsonstor.auth.rootuser.iden, core01._has_jsonstor.auth.rootuser.iden)

    async def test_cortex_jsonstor_iden_migration(self):
        # a pre-existing embedded jsonstor whose cell.guid drifted from the
        # deterministic iden ( derived from the cortex iden ) is migrated back
        # on the next boot.
        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:
                self.eq(s_common.guid((core.iden, 'jsonstor')), core._has_jsonstor.iden)

            # stamp the embedded jsonstor with a mismatched iden
            idenpath = os.path.join(dirn, 'jsonstor', 'cell.guid')
            with open(idenpath, 'w') as fd:
                fd.write(s_common.guid())

            async with self.getTestCore(dirn=dirn) as core:
                self.eq(s_common.guid((core.iden, 'jsonstor')), core._has_jsonstor.iden)

    async def test_cortex_handoff(self):

        with self.getTestDir() as dirn:
            async with self.getTestAha() as aha:

                conf = {'aha:provision': await aha.addAhaSvcProv('00.cortex')}

                async with self.getTestCore(conf=conf) as core00:

                    with self.raises(s_exc.BadArg):
                        await core00.handoff(core00.getLocalUrl())

                    self.false((await core00.getCellInfo())['cell']['nexus']['uplink:ready'])
                    self.none((await core00.getCellInfo())['cell']['parent'])

                    # provision with the new hostname
                    conf = {'aha:provision': await aha.addAhaSvcProv('01.cortex')}
                    async with self.getTestCore(conf=conf) as core01:

                        # test out connecting to the leader but having aha chose a mirror
                        async with s_telepath.loadTeleCell(core01.dirn):
                            # wait for the mirror to think it's ready...
                            await asyncio.wait_for(core01.nexsroot.ready.wait(), timeout=3)
                            async with await s_telepath.openurl('aha://cortex...?mirror=true') as proxy:
                                self.eq(await core01.getCellRunId(), await proxy.getCellRunId())

                        await core01.nodes('[ inet:ip=1.2.3.4 ]')
                        self.len(1, await core00.nodes('inet:ip=1.2.3.4'))

                        self.true(core00.isactive)
                        self.false(core01.isactive)

                        self.true(await s_coro.event_wait(core01.nexsroot.miruplink, timeout=2))
                        self.false((await core00.getCellInfo())['cell']['nexus']['uplink:ready'])
                        self.true((await core01.getCellInfo())['cell']['nexus']['uplink:ready'])
                        self.none((await core00.getCellInfo())['cell']['parent'])
                        self.eq((await core01.getCellInfo())['cell']['parent'], 'aha://cortex...')

                        outp = s_output.OutPutStr()
                        argv = ('--url', core01.getLocalUrl())
                        ret = await s_tools_promote.main(argv, outp=outp)  # this is a graceful promotion
                        self.eq(ret, 0)

                        self.true(core01.isactive)
                        self.false(core00.isactive)

                        self.true(await s_coro.event_wait(core00.nexsroot.miruplink, timeout=2))
                        self.true((await core00.getCellInfo())['cell']['nexus']['uplink:ready'])
                        self.false((await core01.getCellInfo())['cell']['nexus']['uplink:ready'])
                        # Note: The following mirror may change when SYN-7659 is addressed and greater
                        # control over the topology update is available during the promotion process.
                        self.eq((await core00.getCellInfo())['cell']['parent'], 'aha://cortex...')
                        self.none((await core01.getCellInfo())['cell']['parent'])

                        # parent is dynamic ( derived from the leadership term ) and is
                        # never written to cell.mods.yaml at runtime by promote/handoff.
                        mods00 = s_common.yamlload(core00.dirn, 'cell.mods.yaml')
                        mods01 = s_common.yamlload(core01.dirn, 'cell.mods.yaml')
                        self.none(mods00)
                        self.none(mods01)

                        await core00.nodes('[inet:ip=5.5.5.5]')
                        self.len(1, await core01.nodes('inet:ip=5.5.5.5'))

                        # After doing the promotion, provision another mirror cortex.
                        conf = {'aha:provision': await aha.addAhaSvcProv('02.cortex')}
                        async with self.getTestCore(conf=conf) as core02:
                            self.false(core02.isactive)
                            mods02 = s_common.yamlload(core02.dirn, 'cell.mods.yaml')
                            self.none(mods02)
                            # The mirror writeback and change distribution works
                            self.len(0, await core01.nodes('inet:ip=6.6.6.6'))
                            self.len(0, await core00.nodes('inet:ip=6.6.6.6'))
                            self.len(1, await core02.nodes('[inet:ip=6.6.6.6]'))
                            await core00.sync()
                            self.len(1, await core01.nodes('inet:ip=6.6.6.6'))
                            self.len(1, await core00.nodes('inet:ip=6.6.6.6'))
                            # list mirrors
                            exp = ['aha://00.cortex.synapse', 'aha://02.cortex.synapse']
                            self.sorteq(exp, await core00.getMirrorUrls())
                            self.sorteq(exp, await core01.getMirrorUrls())
                            self.sorteq(exp, await core02.getMirrorUrls())
                            self.true(await s_coro.event_wait(core02.nexsroot.miruplink, timeout=2))
                            self.true((await core00.getCellInfo())['cell']['nexus']['uplink:ready'])
                            self.false((await core01.getCellInfo())['cell']['nexus']['uplink:ready'])
                            self.true((await core02.getCellInfo())['cell']['nexus']['uplink:ready'])

    async def test_cortex_usernotifs(self):

        async def testUserNotifs(core):
            async with core.getLocalProxy() as proxy:
                root = core.auth.rootuser.iden
                indx = await proxy.addUserNotif(root, 'hehe', mesgdata={'foo': 'bar'})
                self.nn(indx)
                item = await proxy.getUserNotif(indx)
                self.eq(root, item[0])
                self.eq('hehe', item[2])
                self.eq({'foo': 'bar'}, item[3])
                msgs = [x async for x in proxy.iterUserNotifs(root)]

                self.len(1, msgs)
                self.eq(root, msgs[0][1][0])
                self.eq('hehe', msgs[0][1][2])
                self.eq({'foo': 'bar'}, msgs[0][1][3])

                await proxy.delUserNotif(indx)
                self.none(await proxy.getUserNotif(indx))

                retn = []
                done = asyncio.Event()
                async def watcher():
                    async for item in proxy.watchAllUserNotifs():
                        retn.append(item)
                        done.set()
                        return
                core.schedCoro(watcher())
                await asyncio.sleep(0.1)
                await proxy.addUserNotif(root, 'lolz')
                await asyncio.wait_for(done.wait(), timeout=2)
                self.len(1, retn)
                self.eq(retn[0][1][0], root)
                self.eq(retn[0][1][2], 'lolz')

        # test a local jsonstor
        async with self.getTestCore() as core:
            await testUserNotifs(core)

        # test with a remote jsonstor located by cell type via AHA
        async with self.getTestCoreProv() as (core, axon, jsonstor):
            await testUserNotifs(core)

    async def test_cortex_jsonstor(self):

        async def testCoreJson(core):
            self.none(await core.getJsonObj('foo'))
            self.none(await core.getJsonObjProp('foo', 'bar'))
            self.none(await core.setJsonObj('foo', {'bar': 'baz'}))
            self.true(await core.setJsonObjProp('foo', 'zip', 'zop'))

            self.true(await core.hasJsonObj('foo'))
            self.false(await core.hasJsonObj('newp'))

            self.eq('baz', await core.getJsonObjProp('foo', 'bar'))
            self.eq({'bar': 'baz', 'zip': 'zop'}, await core.getJsonObj('foo'))

            self.true(await core.delJsonObjProp('foo', 'bar'))
            self.eq({'zip': 'zop'}, await core.getJsonObj('foo'))
            self.none(await core.delJsonObj('foo'))
            self.none(await core.getJsonObj('foo'))

            await core.setJsonObj('foo/bar', 'zoinks')
            items = [x async for x in core.getJsonObjs(('foo'))]
            self.eq(items, ((('bar',), 'zoinks'),))

        # test with a remote jsonstor located by cell type via AHA
        async with self.getTestCoreProv() as (core, axon, jsonstor):
            await testCoreJson(core)

        # test a local jsonstor
        async with self.getTestCore() as core:
            await testCoreJson(core)

        # test a local jsonstor and mirror writeback
        with self.getTestDir() as dirn:
            path00 = os.path.join(dirn, 'core00')
            path01 = os.path.join(dirn, 'core01')
            conf00 = {'nexslog:en': True}
            async with self.getTestCore(dirn=path00, conf=conf00) as core00:
                self.true(core00.isactive)

            s_tools_backup.backup(path00, path01)
            async with self.getTestCore(dirn=path00, conf=conf00) as core00:
                conf01 = {'nexslog:en': True, 'parent': core00.getLocalUrl()}
                async with self.getTestCore(dirn=path01, conf=conf01) as core01:
                    await testCoreJson(core01)
                    self.eq(await core00.getJsonObj('foo/bar'), 'zoinks')
                    self.eq(await core01.getJsonObj('foo/bar'), 'zoinks')

        # test a local jsonstor and mirror sync
        with self.getTestDir() as dirn:
            path00 = os.path.join(dirn, 'core00')
            path01 = os.path.join(dirn, 'core01')
            conf00 = {'nexslog:en': True}
            async with self.getTestCore(dirn=path00, conf=conf00) as core00:
                self.true(core00.isactive)

            s_tools_backup.backup(path00, path01)
            async with self.getTestCore(dirn=path00, conf=conf00) as core00:
                conf01 = {'nexslog:en': True, 'parent': core00.getLocalUrl()}
                async with self.getTestCore(dirn=path01, conf=conf01) as core01:
                    await testCoreJson(core00)
                    await core01.sync()
                    self.eq(await core00.getJsonObj('foo/bar'), 'zoinks')
                    self.eq(await core01.getJsonObj('foo/bar'), 'zoinks')

        # Test startup sequencing. We must create the child cells prior to
        # the nexus recover() call from occuring :)
        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                await core.callStorm('$lib.jsonstor.set((path,), hehe)')

            with self.getLoggerStream('synapse.lib.nexus') as stream:
                async with self.getTestCore(dirn=dirn) as core:
                    q = 'return( $lib.jsonstor.get((path,)) )'
                    self.eq('hehe', await core.callStorm(q))
            self.notin('Exception while replaying log', stream.getvalue())

    async def test_cortex_must_upgrade(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:
                core.cellinfo.set('synapse:version', (2, 180, 1))

            with self.raises(s_exc.BadStorageVersion) as cexc:
                async with self.getTestCore(dirn=dirn) as core:
                    pass

            self.isin('The cortex storage directory is from a Synapse', cexc.exception.get('mesg'))
            self.isin(f'is not compatible with the allowed versions: {s_cortex.Cortex._reqSynStorVers}', cexc.exception.get('mesg'))

    async def test_cortex_stormiface(self):
        pkgdef = {
            'name': 'foobar',
            'modules': [
                {'name': 'foobar',
                 'interfaces': ['lookup'],
                 'storm': '''
                     function lookup(tokens) {
                        $looks = ()
                        for $token in $tokens { $looks.append( (inet:fqdn, $token) ) }
                        return($looks)
                     }
                    /* coverage mop up */
                    [ ou:org=* ]
                 '''
                },
                {'name': 'search0',
                 'interfaces': ['search'],
                 'storm': '''
                     function search(tokens) {
                        emit ((0), foo)
                        emit ((10), baz)
                     }
                 '''
                },
                {'name': 'search1',
                 'interfaces': ['search'],
                 'storm': '''
                     function search(tokens) {
                        emit ((1), bar)
                        emit ((11), faz)
                     }
                    /* coverage mop up */
                    [ ou:org=* ]
                 '''
                },
                {'name': 'coverage', 'storm': ''},
                {'name': 'boom', 'interfaces': ['boom'], 'storm': '''
                    function boom() { $lib.raise(omg, omg) return() }
                    function boomgenr() { emit ((0), woot) $lib.raise(omg, omg) }
                '''},
            ]
        }

        async with self.getTestCore() as core:

            self.none(core.modsbyiface.get('lookup'))

            mods = await core.getStormIfaces('lookup')
            self.len(0, mods)
            self.len(0, core.modsbyiface.get('lookup'))

            core.loadStormPkg(pkgdef)

            mods = await core.getStormIfaces('lookup')
            self.len(1, mods)
            self.len(1, core.modsbyiface.get('lookup'))

            todo = s_common.todo('lookup', ('vertex.link', 'woot.com'))
            vals = [r async for r in core.view.callStormIface('lookup', todo)]
            self.eq(((('inet:fqdn', 'vertex.link'), ('inet:fqdn', 'woot.com')),), vals)

            todo = s_common.todo('newp')
            vals = [r async for r in core.view.callStormIface('lookup', todo)]
            self.eq([], vals)

            vals = [r async for r in core.view.mergeStormIface('lookup', todo)]
            self.eq([], vals)

            todo = s_common.todo('search', ('hehe', 'haha'))
            vals = [r async for r in core.view.mergeStormIface('search', todo)]
            self.eq(((0, 'foo'), (1, 'bar'), (10, 'baz'), (11, 'faz')), vals)

            with self.raises(s_exc.StormRaise):
                todo = s_common.todo('boomgenr')
                [r async for r in core.view.mergeStormIface('boom', todo)]

            todo = s_common.todo('boom')
            vals = [r async for r in core.view.callStormIface('boom', todo)]
            self.eq((), vals)

            core._dropStormPkg(pkgdef)
            self.none(core.modsbyiface.get('lookup'))

            mods = await core.getStormIfaces('lookup')
            self.len(0, mods)
            self.len(0, core.modsbyiface.get('lookup'))

    async def test_cortex_lookup_search_dedup(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:email=foo@bar.com ]')

            nodes = await core.nodes('foo@bar.com', opts={'mode': 'lookup'})
            self.eq(['inet:email'], [n.ndef[0] for n in nodes])

            # scrape results are not deduplicated
            nodes = await core.nodes('foo@bar.com foo@bar.com', opts={'mode': 'lookup'})
            self.eq(['inet:email', 'inet:email'], [n.ndef[0] for n in nodes])

            await core.nodes('[ entity:name="vertex project" ]')

            # hint-based results *are* deduplicated against themselves via lookup remainder
            nodes = await core.nodes('vertex vertex', opts={'mode': 'lookup'})
            self.eq(['entity:name'], [n.ndef[0] for n in nodes])

    async def test_cortex_lookmiss(self):
        async with self.getTestCore() as core:
            msgs = await core.stormlist('1.2.3.4 vertex.link', opts={'mode': 'lookup'})
            miss = [m for m in msgs if m[0] == 'look:miss']
            self.len(2, miss)
            self.eq(('inet:ip', (4, 16909060)), miss[0][1]['ndef'])
            self.eq(('inet:fqdn', 'vertex.link'), miss[1][1]['ndef'])

    async def test_cortex_axonapi(self):

        # local axon...
        async with self.getTestCore() as core:

            async with core.getLocalProxy() as proxy:

                async with await proxy.getAxonUpload() as upload:
                    await upload.write(b'asdfasdf')
                    size, sha256 = await upload.save()
                    self.eq(8, size)

                bytelist = []
                async for byts in proxy.getAxonBytes(s_common.ehex(sha256)):
                    bytelist.append(byts)
                self.eq(b'asdfasdf', b''.join(bytelist))

        # remote axon located by cell type via AHA
        async with self.getTestCoreProv() as (core, axon, jsonstor):

            async with core.getLocalProxy() as proxy:

                async with await proxy.getAxonUpload() as upload:
                    await upload.write(b'asdfasdf')
                    size, sha256 = await upload.save()
                    self.eq(8, size)

                bytelist = []
                async for byts in proxy.getAxonBytes(s_common.ehex(sha256)):
                    bytelist.append(byts)
                self.eq(b'asdfasdf', b''.join(bytelist))

    async def test_cortex_divert(self):

        async with self.getTestCore() as core:

            storm = '''
            function x(y) {
                [ ou:org=* ou:org=* +#foo]
            }

            [ inet:fqdn=vertex.link inet:fqdn=woot.com ]

            // yield and pernode
            divert (true) $x($node)
            '''
            nodes = await core.nodes(storm)
            self.len(4, nodes)
            self.len(4, [n for n in nodes if n.ndef[0] == 'ou:org'])

            storm = '''
            function x(y) {
                [ ou:org=* ou:org=* +#bar]
            }

            [ inet:fqdn=vertex.link inet:fqdn=woot.com ]

            // yield and pernode
            divert (false) $x($node)
            '''
            nodes = await core.nodes(storm)
            self.len(2, nodes)
            self.len(2, [n for n in nodes if n.ndef[0] == 'inet:fqdn'])
            self.len(4, await core.nodes('ou:org +#bar'))

            storm = '''
            function x(y) {
                [ ou:org=* ou:org=* +#baz]
            }

            [ inet:fqdn=vertex.link inet:fqdn=woot.com ]

            // yield and pernode
            divert (true) $x(hithere)
            '''
            nodes = await core.nodes(storm)
            self.len(4, nodes)
            self.len(4, [n for n in nodes if n.ndef[0] == 'ou:org'])
            self.len(4, await core.nodes('ou:org +#baz'))

            storm = '''
            function x(y) {
                [ ou:org=* ou:org=* +#faz]
            }

            [ inet:fqdn=vertex.link inet:fqdn=woot.com ]

            // yield and pernode
            divert (false) $x(hithere)
            '''
            nodes = await core.nodes(storm)
            self.len(2, nodes)
            self.len(2, [n for n in nodes if n.ndef[0] == 'inet:fqdn'])
            self.len(4, await core.nodes('ou:org +#faz'))

            # functions that don't return a generator
            storm = '''
            function x() {
                $lst = ()
                [ ou:org=* ou:org=* +#cat ]
                $lst.append($node)
                fini { return($lst) }
            }

            divert (true) $x()
            '''
            await self.asyncraises(s_exc.BadArg, core.nodes(storm))
            self.len(2, await core.nodes('ou:org +#cat'))

            storm = '''
            function x() {
                $lst = ()
                [ ou:org=* ou:org=* +#dog ]
                $lst.append($node)
                fini { return($lst) }
            }

            [ inet:fqdn=vertex.link inet:fqdn=woot.com ]

            divert (true) $x()
            '''
            await self.asyncraises(s_exc.BadArg, core.nodes(storm))
            self.len(4, await core.nodes('ou:org +#dog'))

            # functions that return a generator
            storm = '''
            function y() {
                [ ou:org=* ou:org=* +#cow ]
            }
            function x() {
                $lib.print(heythere)
                return($y())
            }

            divert (true) $x()
            '''
            mesgs = await core.stormlist(storm)
            self.len(1, [m for m in mesgs if (m[0] == 'print' and m[1]['mesg'] == 'heythere')])
            self.len(2, [m for m in mesgs if (m[0] == 'node' and m[1][0][0] == 'ou:org')])
            self.len(2, await core.nodes('ou:org +#cow'))

            storm = '''
            function y() {
                [ ou:org=* ou:org=* +#camel ]
            }
            function x() {
                $lib.print(heythere)
                return($y())
            }

            [ inet:fqdn=vertex.link inet:fqdn=woot.com ]

            divert (false) $x()
            '''
            mesgs = await core.stormlist(storm)
            self.len(3, [m for m in mesgs if (m[0] == 'print' and m[1]['mesg'] == 'heythere')])
            self.len(2, [m for m in mesgs if (m[0] == 'node' and m[1][0][0] == 'inet:fqdn')])
            self.len(4, await core.nodes('ou:org +#camel'))

            storm = 'function foo(n) {} divert (true) $foo($node)'
            mesgs = await core.stormlist(storm)
            self.len(0, [mesg[1] for mesg in mesgs if mesg[0] == 'err'])

            # runtsafe with 0 nodes
            orgcount = len(await core.nodes('ou:org'))
            storm = '''
            function y() {
                [ ou:org=* ]
                [ ou:org=* ]
                [ ou:org=* ]
                [ ou:org=* ]
            }
            divert --size 2 (true) $y()
            '''
            self.len(2, await core.nodes(storm))
            self.eq(orgcount + 2, len(await core.nodes('ou:org')))

            orgcount = len(await core.nodes('ou:org'))
            storm = '''
            function y() {
                [ ou:org=* ]
                [ ou:org=* ]
                [ ou:org=* ]
                [ ou:org=* ]
            }
            divert --size 2 (false) $y()
            '''
            self.len(0, await core.nodes(storm))
            self.eq(orgcount + 2, len(await core.nodes('ou:org')))

            orgcount = len(await core.nodes('ou:org'))
            storm = '''
            function y(n) {
                [ ou:org=* ]
                [ ou:org=* ]
                [ ou:org=* ]
                [ ou:org=* ]
            }

            [ entity:contact=* ]
            [ entity:contact=* ]
            divert --size 2 (true) $y($node)
            '''
            self.len(4, await core.nodes(storm))
            self.eq(orgcount + 4, len(await core.nodes('ou:org')))

            orgcount = len(await core.nodes('ou:org'))
            storm = '''
            function y(n) {
                [ ou:org=* ]
                [ ou:org=* ]
                [ ou:org=* ]
                [ ou:org=* ]
            }

            [ entity:contact=* ]
            [ entity:contact=* ]
            divert --size 2 (false) $y($node)
            '''
            self.len(2, await core.nodes(storm))
            self.eq(orgcount + 4, len(await core.nodes('ou:org')))

            # running pernode with runtsafe args
            storm = '''
                function y(nn) { yield $nn }
                [ test:str=foo test:str=bar ]
                $n=(null) $n=$node divert (true) $y($n)
            '''
            self.sorteq(['foo', 'bar'], [n.ndef[1] for n in await core.nodes(storm)])

            # empty input with non-runtsafe args
            storm = '''
            function x(y) {
                [ ou:org=* ]
            }
            divert (true) $x($node)
            '''
            self.len(0, await core.nodes(storm))

    async def test_cortex_limits(self):
        async with self.getTestCore(conf={'max:nodes': 10}) as core:
            self.len(1, await core.nodes('[ ou:org=* ]'))
            with self.raises(s_exc.HitLimit):
                await core.nodes('[ inet:ip=1.2.3.0/24 ]')

    async def test_cortex_rawpivot(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:ip=1.2.3.4] $ip=$node.value -> { [ inet:dns:a=(woot.com, $ip) ] }')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:dns:a', ('woot.com', (4, 0x01020304))))

    async def test_cortex_edges(self):

        async with self.getTestCore() as core:

            await core.nodes('[ meta:source=* :name=test ]')

            nodes = await core.nodes('[test:guid=*]')
            self.len(1, nodes)
            news = nodes[0]

            nodes = await core.nodes('[inet:ip=1.2.3.4]')
            self.len(1, nodes)
            ip = nodes[0]

            await news.addEdge('refs', ip.nid)

            n1edges = await alist(news.iterEdgesN1())
            n2edges = await alist(ip.iterEdgesN2())

            self.eq(n1edges, (('refs', ip.nid),))
            self.eq(n2edges, (('refs', news.nid),))

            await news.delEdge('refs', ip.nid)

            with self.raises(s_exc.BadArg):
                await news.addEdge('refs', s_common.int64en(99999))

            self.len(0, await alist(news.iterEdgesN1()))
            self.len(0, await alist(ip.iterEdgesN2()))

            nodes = await core.nodes('test:guid [ +(refs)> {inet:ip=1.2.3.4} ]')
            self.eq(nodes[0].ndef[0], 'test:guid')

            # check all the walk from N1 syntaxes
            nodes = await core.nodes('test:guid -(refs)> *')
            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))

            self.len(0, await core.nodes('test:guid -(refs)> mat:spec'))

            nodes = await core.nodes('test:guid -(refs)> inet:ip')
            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))

            nodes = await core.nodes('test:guid -(refs)> (inet:ip,)')
            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))

            nodes = await core.nodes('test:guid -(*)> *')
            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))

            nodes = await core.nodes('$types = (refs,hehe) test:guid -($types)> *')
            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))

            nodes = await core.nodes('$types = (*,) test:guid -($types)> *')
            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))

            # check all the walk from N2 syntaxes
            nodes = await core.nodes('inet:ip <(refs)- *')
            self.eq(nodes[0].ndef[0], 'test:guid')

            nodes = await core.nodes('inet:ip <(*)- *')
            self.eq(nodes[0].ndef[0], 'test:guid')

            layr = core.getLayer()
            self.eq(1, layr.getEdgeVerbCount('refs'))
            self.eq(0, layr.getEdgeVerbCount('newp'))

            self.eq(1, layr.getEdgeVerbCount('refs', n1form='test:guid'))
            self.eq(0, layr.getEdgeVerbCount('refs', n2form='test:guid'))
            self.eq(0, layr.getEdgeVerbCount('refs', n1form='inet:ip'))
            self.eq(1, layr.getEdgeVerbCount('refs', n2form='inet:ip'))
            self.eq(1, layr.getEdgeVerbCount('refs', n1form='test:guid', n2form='inet:ip'))

            self.eq(0, layr.getEdgeVerbCount('refs', n1form='newp'))
            self.eq(0, layr.getEdgeVerbCount('refs', n2form='newp'))

            self.true(core.model.edgeIsValid('test:guid', 'refs', 'inet:ip'))

            # coverage for isDestForm()
            self.len(0, await core.nodes('inet:ip <(*)- mat:spec'))
            self.len(0, await core.nodes('test:guid -(*)> mat:spec'))
            self.len(0, await core.nodes('inet:ip <(*)- (mat:spec,)'))
            self.len(0, await core.nodes('test:guid -(*)> (mat:spec,)'))
            self.len(0, await core.nodes('test:guid -((refs,foos))> mat:spec'))
            self.len(0, await core.nodes('inet:ip <((refs,foos))- mat:spec'))

            with self.raises(s_exc.BadSyntax):
                self.len(0, await core.nodes('inet:ip <(*)- $(0)'))

            with self.raises(s_exc.BadSyntax):
                self.len(0, await core.nodes('test:guid -(*)> $(0)'))

            with self.raises(s_exc.NoSuchForm):
                self.len(0, await core.nodes('test:guid -(*)> test:newp'))

            nodes = await core.nodes('$types = (refs,hehe) inet:ip <($types)- *')
            self.eq(nodes[0].ndef[0], 'test:guid')

            nodes = await core.nodes('$types = (*,) inet:ip <($types)- *')
            self.eq(nodes[0].ndef[0], 'test:guid')

            # get the edge using stormtypes
            msgs = await core.stormlist('test:guid for $edge in $node.edges() { $lib.print($edge) }')
            self.stormIsInPrint('refs', msgs)

            msgs = await core.stormlist('test:guid for $edge in $node.edges(verb=refs) { $lib.print($edge) }')
            self.stormIsInPrint('refs', msgs)

            # remove the refs edge
            nodes = await core.nodes('test:guid [ -(refs)> {inet:ip=1.2.3.4} ]')
            self.len(1, nodes)

            # no walking now...
            self.len(0, await core.nodes('test:guid -(refs)> *'))

            # now lets add the edge using the n2 syntax
            nodes = await core.nodes('inet:ip [ <(refs)+ { test:guid } ]')
            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))

            nodes = await core.nodes('test:guid -(refs)> *')
            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))

            nodes = await core.nodes('inet:ip [ <(refs)- { test:guid } ]')
            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))

            # test refs+pivs in and out
            nodes = await core.nodes('test:guid [ +(refs)> { inet:ip=1.2.3.4 } ]')
            nodes = await core.nodes('test:guid [ :size=27492 ]')
            nodes = await core.nodes('[ inet:dns:a=(woot.com, 1.2.3.4) ]')

            # we should now be able to edge walk *and* refs out
            nodes = await core.nodes('test:guid --> *')
            self.len(2, nodes)
            self.eq(nodes[0].ndef[0], 'test:int')
            self.eq(nodes[1].ndef[0], 'inet:ip')

            # we should now be able to edge walk *and* refs in
            nodes = await core.nodes('inet:ip=1.2.3.4 <-- *')
            forms = [n.ndef[0] for n in nodes]
            self.isin('inet:dns:a', forms)
            self.isin('test:guid', forms)

            msgs = await core.stormlist('for $verb in $lib.view.get().getEdgeVerbs() { $lib.print($verb) }')
            self.stormIsInPrint('refs', msgs)

            msgs = await core.stormlist('for $edge in $lib.view.get().getEdges() { $lib.print($edge) }')
            self.stormIsInPrint('refs', msgs)
            self.stormIsInPrint(str(ip.intnid()), msgs)
            self.stormIsInPrint(str(news.intnid()), msgs)

            msgs = await core.stormlist('for $edge in $lib.view.get().getEdges(verb=refs) { $lib.print($edge) }')
            self.stormIsInPrint('refs', msgs)
            self.stormIsInPrint(str(ip.intnid()), msgs)
            self.stormIsInPrint(str(news.intnid()), msgs)

            # delete an edge that doesn't exist to bounce off the layer
            await core.nodes('test:guid [ -(refs)> { [ inet:ip=5.5.5.5 ] } ]')

            # add an edge that exists already to bounce off the layer
            await core.nodes('test:guid [ +(refs)> { inet:ip=1.2.3.4 } ]')

            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:guid -(refs)> $(10)')

            self.eq(1, await core.callStorm('''
                $list = ()
                for $edge in $lib.view.get().getEdges() { $list.append($edge) }
                return($list.size())
            '''))

            # check that auto-deleting a node's edges works
            await core.nodes('test:guid | delnode')
            self.eq(0, await core.callStorm('''
                $list = ()
                for $edge in $lib.view.get().getEdges() { $list.append($edge) }
                return($list.size())
            '''))

            # Run multiple nodes through edge creation/deletion ( test coverage for perm caching )
            await core.nodes('inet:ip [ <(seen)+ { meta:source:name=test }]')
            self.len(2, await core.nodes('meta:source:name=test -(seen)> *'))

            await core.nodes('inet:ip [ <(seen)-{ meta:source:name=test }]')
            self.len(0, await core.nodes('meta:source:name=test -(seen)> *'))

            # Sad path - edges must be a str/list of strs
            with self.raises(s_exc.StormRuntimeError) as cm:
                q = 'inet:ip $edges=$(0) -($edges)> *'
                await core.nodes(q)
            self.eq(cm.exception.get('mesg'),
                    'walk operation expected a string or list.  got: 0.')

            await core.nodes('[test:guid=*]')

            nodes = await core.nodes('$n = {[it:dev:str=foo]} test:guid [ +(refs)> $n ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'test:guid')

            nodes = await core.nodes('test:guid -(refs)> it:dev:str')
            self.len(1, nodes)

            q = '''
            function foo() {
                for $x in $lib.range(5) {
                    [ it:dev:int=$x ]
                    emit $node
                }
            }
            test:guid [ +(refs)> $foo() ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'test:guid')

            nodes = await core.nodes('test:guid -(refs)> it:dev:int')
            self.len(5, nodes)

            nodes = await core.nodes('$n = {[it:dev:str=foo]} test:guid [ -(refs)> $n ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'test:guid')

            nodes = await core.nodes('test:guid -(refs)> it:dev:str')
            self.len(0, nodes)

            q = '''
            function foo() {
                for $x in $lib.range(5) {
                    [ it:dev:int=$x ]
                    emit $node
                }
            }
            test:guid [ -(refs)> $foo() ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'test:guid')

            nodes = await core.nodes('test:guid -(refs)> it:dev:int')
            self.len(0, nodes)

            nodes = await core.nodes('$n = {[it:dev:str=foo]} test:guid [ <(refs)+ $n ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'test:guid')

            nodes = await core.nodes('test:guid <(refs)- it:dev:str')
            self.len(1, nodes)

            q = '''
            function foo() {
                for $x in $lib.range(5) {
                    [ it:dev:int=$x ]
                    emit $node
                }
            }
            test:guid [ <(refs)+ $foo() ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'test:guid')

            nodes = await core.nodes('test:guid <(refs)- it:dev:int')
            self.len(5, nodes)

            nodes = await core.nodes('$n = {[it:dev:str=foo]} test:guid [ <(refs)- $n ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'test:guid')

            nodes = await core.nodes('test:guid <(refs)- it:dev:str')
            self.len(0, nodes)

            q = '''
            function foo() {
                for $x in $lib.range(5) {
                    [ it:dev:int=$x ]
                    emit $node
                }
            }
            test:guid [ <(refs)- $foo() ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'test:guid')

            nodes = await core.nodes('test:guid <(refs)- it:dev:int')
            self.len(0, nodes)

            await core.nodes('[test:guid=*]')

            nodes = await core.nodes('$n = {[it:dev:str=foo]} $edge=refs test:guid [ +($edge)> $n ]')
            self.len(2, nodes)

            nodes = await core.nodes('test:guid -(refs)> it:dev:str')
            self.len(2, nodes)

            nodes = await core.nodes('$n = {[it:dev:str=foo]} $edge=refs test:guid [ -($edge)> $n ]')
            self.len(2, nodes)

            nodes = await core.nodes('test:guid -(refs)> it:dev:str')
            self.len(0, nodes)

    async def test_cortex_callstorm(self):

        async with self.getTestCore(conf={'auth:passwd': 'root'}) as core:

            visi = await core.auth.addUser('visi')
            await visi.setPasswd('secret')

            self.eq('asdf', await core.callStorm('return (asdf)'))
            async with core.getLocalProxy() as proxy:
                self.eq('qwer', await proxy.callStorm('return (qwer)'))

                q = '$x=($lib.undef, 1, 2, $lib.queue.gen(beep)) return($x)'
                retn = await proxy.callStorm(q)
                self.eq(('1', '2'), retn)

                with self.raises(s_exc.StormRuntimeError):
                    q = '$foo=() $bar=$foo.index(10) return ( $bar )'
                    await proxy.callStorm(q)

                with self.raises(s_exc.SynErr) as cm:
                    q = 'return ( $lib.exit() )'
                    await proxy.callStorm(q)
                self.eq(cm.exception.get('errx'), 'StormExit')

                with self.raises(s_exc.StormRaise) as cm:
                    await proxy.callStorm('$lib.raise(Foo, bar, hehe=haha, key=(1))')

                self.eq(cm.exception.get('errname'), 'Foo')
                self.eq(cm.exception.get('mesg'), 'bar')
                self.eq(cm.exception.get('hehe'), 'haha')
                self.eq(cm.exception.get('key'), 1)

                # We convert StormLoopCtrl and StormGenrCtrl into StormRuntimeError
                opts = {'vars': {'i': 2}}
                q = 'if ($i = 2) { break }'
                with self.raises(s_exc.StormRuntimeError) as cm:
                    await core.callStorm(q, opts=opts)
                self.eq(cm.exception.get('mesg'),
                        'Loop control statement "break" used outside of a loop.')

                q = 'if ($i = 2) { continue }'
                with self.raises(s_exc.StormRuntimeError) as cm:
                    await core.callStorm(q, opts=opts)
                self.eq(cm.exception.get('mesg'),
                        'Loop control statement "continue" used outside of a loop.')

                q = 'if ($i = 2) { stop }'
                with self.raises(s_exc.StormRuntimeError) as cm:
                    await core.callStorm(q, opts=opts)
                self.eq(cm.exception.get('mesg'),
                        'Generator control statement "stop" used outside of a generator function.')

            with self.getLoggerStream('synapse.lib.view') as stream:
                async with core.getLocalProxy() as proxy:

                    # async cancellation test
                    coro = proxy.callStorm('$lib.time.sleep(3) return ( true )')
                    try:
                        await asyncio.wait_for(coro, timeout=0.1)
                    except asyncio.TimeoutError:
                        logger.exception('Woohoo!')

                await stream.expect('callStorm cancelled', timeout=6)

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            # the storm/call API is restricted to X-API-KEY authentication only
            visikey, _ = await core.addUserApiKey(visi.iden, 'callstorm')
            rootkey, _ = await core.addUserApiKey(core.auth.rootuser.iden, 'callstorm')

            async with self.getHttpSess(port=port) as sess:
                # impersonation by a non-admin is denied
                body = {'query': 'return(asdf)', 'opts': {'user': core.auth.rootuser.iden}}
                async with sess.get(f'https://localhost:{port}/api/v3/storm/call', json=body,
                                    headers={'X-API-KEY': visikey}) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)

            async with self.getHttpSess(port=port) as sess:
                resp = await sess.post(f'https://localhost:{port}/api/v3/storm/call')
                self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)

                # a session cookie does not grant access to the storm/call API
                async with sess.post(f'https://localhost:{port}/api/v3/login',
                                     json={'user': 'root', 'passwd': 'root'}) as resp:
                    self.eq('ok', (await resp.json()).get('status'))

                async with sess.get(f'https://localhost:{port}/api/v3/storm/call',
                                    json={'query': 'return (asdf)'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)

            async with self.getHttpSess() as sess:
                headers = {'X-API-KEY': rootkey}

                body = {'query': 'return (asdf)'}
                async with sess.get(f'https://localhost:{port}/api/v3/storm/call', json=body, headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq('asdf', retn['result'])

                body = {'query': '$foo=() $bar=$foo.index(10) return ( $bar )'}
                async with sess.get(f'https://localhost:{port}/api/v3/storm/call', json=body, headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    retn = await resp.json()
                    self.eq('err', retn.get('status'))
                    self.eq('StormRuntimeError', retn.get('code'))
                    self.eq('list index out of range', retn.get('mesg'))

                body = {'query': 'return ( $lib.exit() )'}
                async with sess.post(f'https://localhost:{port}/api/v3/storm/call', json=body, headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    retn = await resp.json()
                    self.eq('err', retn.get('status'))
                    self.eq('StormExit', retn.get('code'))
                    self.eq('StormExit: ', retn.get('mesg'))

                # No body
                async with sess.get(f'https://localhost:{port}/api/v3/storm/call', headers=headers) as resp:
                    retn = await resp.json()
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    self.eq('err', retn.get('status'))
                    self.eq('SchemaViolation', retn.get('code'))

    async def test_cortex_storm_dmon_log(self):

        async with self.getTestCore() as core:

            with self.getLoggerStream('synapse.storm.log') as stream:
                iden = await core.callStorm('''
                    $que = $lib.queue.add(foo)

                    $ddef = $lib.dmon.add(${
                        $lib.print(hi)
                        $lib.warn(omg)
                        $s = `Running {$auto.type} {$auto.iden}`
                        $lib.log.info($s, ({"iden": $auto.iden}))
                        $que = $lib.queue.byname(foo)
                        $que.put(done)
                    })

                    $que.get()
                    return($ddef.iden)
                ''')
                await stream.expect('Running dmon', timeout=6)

            mesg = stream.jsonlines()[0]
            self.eq(mesg.get('message'), f'Running dmon {iden}')
            self.eq(mesg['params'].get('iden'), iden)

            opts = {'vars': {'iden': iden}}
            logs = await core.callStorm('return($lib.dmon.log($iden))', opts=opts)
            self.eq(logs[0][1][0], 'print')
            self.eq(logs[0][1][1]['mesg'], 'hi')
            self.eq(logs[1][1][0], 'warn')
            self.eq(logs[1][1][1]['mesg'], 'omg')

            async with core.getLocalProxy() as prox:
                logs = await prox.getStormDmonLog(iden)
                self.eq(logs[0][1][0], 'print')
                self.eq(logs[0][1][1]['mesg'], 'hi')
                self.eq(logs[1][1][0], 'warn')
                self.eq(logs[1][1][1]['mesg'], 'omg')

                self.len(0, await prox.getStormDmonLog('newp'))

    async def test_storm_impersonate_and_sudo(self):

        async with self.getTestCore() as core:

            self.eq(core._userFromOpts(None), core.auth.rootuser)
            self.eq(core._userFromOpts({'user': None}), core.auth.rootuser)

            with self.raises(s_exc.NoSuchUser):
                opts = {'user': 'newp'}
                await core.nodes('[ inet:ip=1.2.3.4 ]', opts=opts)

            visi = await core.auth.addUser('visi')
            async with core.getLocalProxy(user='visi') as proxy:

                opts = {'user': core.auth.rootuser.iden}
                with self.raises(s_exc.AuthDeny):
                    await proxy.callStorm('[ inet:ip=1.2.3.4 ]', opts=opts)

                await visi.setAdmin(True)

                opts = {'user': core.auth.rootuser.iden}
                self.eq(1, await proxy.count('[ inet:ip=1.2.3.4 ]', opts=opts))

                await visi.setAdmin(False)
                await visi.addRule((True, ('storm', 'sudo')))

                opts = {'sudo': True}
                self.nn(await proxy.callStorm('return({[ it:dev:str=woot ]})', opts=opts))

    async def test_nodes(self):

        async with self.getTestCore() as core:
            await core.fini()
            with self.raises(s_exc.IsFini):
                await core.nodes('[ inet:ip=1.2.3.4 ]')

    async def test_cortex_prop_deref(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ test:int=10 test:str=woot ]')
            text = '''
                for $prop in (test:int, test:str) {
                    *$prop
                }
            '''
            self.len(2, await core.nodes(text))

            text = '''
                syn:prop=test:int $prop=$node.value *$prop=10 -syn:prop
            '''
            nodes = await core.nodes(text)
            self.eq(nodes[0].ndef, ('test:int', 10))

            guid = 'da299a896ff52ab0e605341ab910dad5'

            opts = {'vars': {'guid': guid}}
            self.len(2, await core.nodes('[ inet:dns:a=(vertex.link, 1.2.3.4) (it:nic=$guid :ip=1.2.3.4) ]',
                                         opts=opts))

            text = '''
                syn:form syn:prop:computed=1 syn:prop:computed=0

                $prop = $node.value

                *$prop?=1.2.3.4

                -syn:form
                -syn:prop
            '''
            nodes = await core.nodes(text)
            self.len(3, nodes)

            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))
            self.eq(nodes[1].ndef, ('inet:dns:a', ('vertex.link', (4, 0x01020304))))
            self.eq(nodes[2].ndef, ('it:nic', guid))

    async def test_cortex_tagprop(self):

        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:

                await core.addTagProp('_user', ('str', {}), {})
                await core.addTagProp('_score', ('int', {'min': 0, 'max': 110}), {'doc': 'hi there'})
                await core.addTagProp('_at', ('geo:latlong', {}), {'doc':
                                                                   'Where the node was when the tag was applied.'})

                # Lifting by a tagprop works before any writes happened
                self.len(0, await core.nodes('#foo.bar:_score'))
                self.len(0, await core.nodes('#foo.bar:_score=20'))

                await core.nodes('[ test:int=10 +#foo.bar:_score=20 ]')
                await core.nodes('[ test:str=lulz +#blah:_user=visi ]')
                await core.nodes('[ test:str=wow +#hehe:_at=(10, 20) ]')

                # test all the syntax cases...
                self.len(1, await core.nodes('#foo.bar'))
                self.len(1, await core.nodes('#foo.bar:_score'))
                self.len(1, await core.nodes('#foo.bar:_score=20'))
                self.len(1, await core.nodes('#foo.bar:_score<=30'))
                self.len(1, await core.nodes('#foo.bar:_score>=10'))
                self.len(1, await core.nodes('#foo.bar:_score*range=(10, 30)'))
                self.len(1, await core.nodes('$tag=foo.bar $prop=_score #$tag:$prop'))
                self.len(1, await core.nodes('$tag=foo.bar $prop=_score #$tag:$prop=20'))

                self.len(1, await core.nodes('#blah:_user^=vi'))
                self.len(1, await core.nodes('#blah:_user~=si'))

                self.len(1, await core.nodes('test:int#foo.bar:_score'))
                self.len(1, await core.nodes('test:int#foo.bar:_score=20'))
                self.len(1, await core.nodes('$form=test:int $tag=foo.bar *$form#$tag'))
                self.len(1, await core.nodes('$form=test:int $tag=foo.bar $prop=_score *$form#$tag:$prop'))

                self.len(1, await core.nodes('test:int +#foo.bar'))
                self.len(1, await core.nodes('test:int +#foo.bar:_score'))
                self.len(1, await core.nodes('test:int +#foo.bar:_score=20'))
                self.len(1, await core.nodes('test:int +#foo.bar:_score<=30'))
                self.len(1, await core.nodes('test:int +#foo.bar:_score>=10'))
                self.len(1, await core.nodes('test:int +#foo.bar:_score*range=(10, 30)'))
                self.len(1, await core.nodes('test:int +#*:_score'))
                self.len(1, await core.nodes('test:int +#foo.*:_score'))
                self.len(1, await core.nodes('$tag=* test:int +#*:_score'))
                self.len(1, await core.nodes('$tag=foo.* test:int +#foo.*:_score'))

                self.len(0, await core.nodes('test:int -#foo.bar'))
                self.len(0, await core.nodes('test:int -#foo.bar:_score'))
                self.len(0, await core.nodes('test:int -#foo.bar:_score=20'))
                self.len(0, await core.nodes('test:int -#foo.bar:_score<=30'))
                self.len(0, await core.nodes('test:int -#foo.bar:_score>=10'))
                self.len(0, await core.nodes('test:int -#foo.bar:_score*range=(10, 30)'))

                self.len(1, await core.nodes('test:str +#hehe:_at*near=((10, 20), 1km)'))

                # test use as a value...
                q = 'test:int $valu=#foo.bar:_score [ +#foo.bar:_score = $($valu + 20) ] +#foo.bar:_score=40'
                self.len(1, await core.nodes(q))

                with self.raises(s_exc.BadTypeValu):
                    self.len(1, await core.nodes('test:int=10 [ +#foo.bar:_score=asdf ]'))

                self.len(1, await core.nodes('test:int=10 [ +#foo.bar:_score?=asdf ] +#foo.bar:_score=40'))

                # test the "set existing" cases for lift indexes
                self.len(1, await core.nodes('test:int=10 [ +#foo.bar:_score=100 ]'))
                self.len(1, await core.nodes('#foo.bar'))
                self.len(1, await core.nodes('#foo.bar:_score'))
                self.len(1, await core.nodes('#foo.bar:_score=100'))
                self.len(1, await core.nodes('#foo.bar:_score<=110'))
                self.len(1, await core.nodes('#foo.bar:_score>=90'))
                self.len(1, await core.nodes('#foo.bar:_score*range=(90, 110)'))

                # remove the tag
                await core.nodes('test:int=10 [ -#foo.bar ]')
                self.len(0, await core.nodes('#foo.bar:_score'))
                self.len(0, await core.nodes('#foo.bar:_score=100'))
                self.len(1, await core.nodes('test:int=10 -#foo.bar:_score'))

                # remove just the tagprop
                await core.nodes('test:int=10 [ +#foo.bar:_score=100 ]')
                await core.nodes('test:int=10 [ -#foo.bar:_score ]')
                self.len(0, await core.nodes('#foo.bar:_score'))
                self.len(0, await core.nodes('#foo.bar:_score=100'))
                self.len(1, await core.nodes('test:int=10 -#foo.bar:_score'))

                # remove a higher-level tag
                self.len(1, await core.nodes('test:int=10 [ +#foo.bar:_score=100 ]'))
                nodes = await core.nodes('test:int=10 [ -#foo ]')
                self.len(0, nodes[0]._getTagPropsDict())
                self.len(0, await core.nodes('#foo'))
                self.len(0, await core.nodes('#foo.bar:_score'))
                self.len(0, await core.nodes('#foo.bar:_score=100'))
                self.len(1, await core.nodes('test:int=10'))
                self.len(1, await core.nodes('test:int=10 -#foo.bar:_score'))

                # test for adding two tags with the same prop to the same node
                nodes = await core.nodes('[ test:int=10 +#foo:_score=20 +#bar:_score=20 ]')
                self.len(1, nodes)
                self.eq(20, nodes[0].getTagProp('foo', '_score'))
                self.eq(20, nodes[0].getTagProp('bar', '_score'))

                # remove one of the tag props and everything still works
                nodes = await core.nodes('[ test:int=10 -#bar:_score ]')
                self.len(1, nodes)
                self.eq(20, nodes[0].getTagProp('foo', '_score'))
                self.false(nodes[0].hasTagProp('bar', '_score'))

                await core.nodes('[ test:int=10 -#foo:_score ]')

                # same, except for _changing_ the tagprop instead of removing
                await core.nodes('test:int=10 [ +#foo:_score=20 +#bar:_score=20 ]')
                nodes = await core.nodes('test:int=10 [ +#bar:_score=30 ]')
                self.len(1, nodes)
                self.eq(20, nodes[0].getTagProp('foo', '_score'))
                self.eq(30, nodes[0].getTagProp('bar', '_score'))

                await core.nodes('test:int=10 [ -#foo -#bar ]')

                nodes = await core.nodes('$tag=foo $prop=_score $valu=5 test:int=10 [ +#$tag:$prop=$valu ]')
                self.eq(5, nodes[0].getTagProp('foo', '_score'))

                q = '''
                    $list=(["foo", "_score", 20])
                    [ test:int=10 +#$list.index(0):$list.index(1)=$list.index(2) ]
                '''
                nodes = await core.nodes(q)
                self.eq(20, nodes[0].getTagProp('foo', '_score'))

                with self.raises(s_exc.NoSuchCmpr):
                    await core.nodes('test:int=10 +#foo:_score*newp=66')

                nodes = await core.nodes('$tag=foo $prop=_score test:int=10 [ -#$tag:$prop ]')
                self.false(nodes[0].hasTagProp('foo', '_score'))

                modl = await core.getModelDict()
                self.nn(modl['tagprops'].get('_score'))

                with self.raises(s_exc.DupPropName):
                    await core.addTagProp('_score', ('int', {}), {})

                with self.raises(s_exc.BadTypeValu):
                    await core.nodes('test:int=10 [ +#bar:_score=200 ]')

                with self.raises(s_exc.BadTypeValu):
                    await core.nodes('test:int=10 [ +#bar:_score=-200 ]')

                await core.delTagProp('_score')

                with self.raises(s_exc.NoSuchTagProp):
                    await core.delTagProp('_score')

                modl = await core.getModelDict()
                self.none(modl['tagprops'].get('_score'))

                with self.raises(s_exc.NoSuchTagProp):
                    await core.nodes('#foo.bar:_score')

                with self.raises(s_exc.NoSuchTagProp):
                    await core.nodes('test:int=10 [ +#foo.bar:_score=66 ]')

                with self.raises(s_exc.NoSuchTagProp):
                    await core.nodes('test:int=10 +#foo.bar:_score=66')

                with self.raises(s_exc.NoSuchTagProp):
                    await core.nodes('test:int=10 $lib.print(#foo.bar:_score)')

                with self.raises(s_exc.NoSuchType):
                    await core.addTagProp('_derp', ('derp', {}), {})

                # Extended tagprop names must begin with '_'
                with self.raises(s_exc.BadPropDef) as cm:
                    await core.addTagProp('nounderscore', ('int', {}), {})
                self.isin('must begin with "_"', cm.exception.get('mesg'))

                # Tagprops may only use immutable types
                with self.raises(s_exc.BadPropDef) as cm:
                    await core.addTagProp('_bad', ('data', {}), {})
                self.isin('immutable', cm.exception.get('mesg'))

                # Standard built-in tagprops are present and not user-deletable
                self.nn(core.model.tagprop('tlp'))
                self.nn(core.model.tagprop('confidence'))
                self.false(core.model.tagprop('tlp').isext)
                self.false(core.model.tagprop('confidence').isext)
                with self.raises(s_exc.BadPropDef):
                    await core.delTagProp('tlp')
                with self.raises(s_exc.BadPropDef):
                    await core.delTagProp('confidence')

                with self.raises(s_exc.BadTypeValu):
                    await core.nodes("$tag=(foo, bar) test:int#$tag:prop")

                with self.raises(s_exc.BadTypeValu):
                    await core.nodes("$tag=(foo, bar) test:int +#$tag:prop")

                with self.raises(s_exc.BadTypeValu):
                    await core.nodes("$tag=(foo, bar) test:int +#$tag:prop=5")

                with self.raises(s_exc.BadTypeValu):
                    await core.nodes("test:int $tag=(foo, bar) $lib.print(#$tag:prop)")

                with self.raises(s_exc.BadTypeValu):
                    await core.nodes("test:int $tag=(foo, bar) [ +#$tag:prop=foo ]")

                with self.raises(s_exc.BadTypeValu):
                    await core.nodes("test:int $tag=(foo, bar) [ -#$tag:prop ]")

                await core.addForm('_low:str', 'str', {'lower': True}, {})
                await core.addTagProp('_lowstr', ('_low:str', {}), {})
                await core.addTagProp('_normstr', ('_low:str', {'lower': False}), {})

                await core.nodes('''[
                    test:str=foo
                    +#foo:_lowstr=fooBAR
                    (test:str=bar :hehe=nprop)
                ]''')

                nodes = await core.nodes('_low:str=foobar <- *')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('test:str', 'foo'))

                vdef2 = await core.view.fork()
                forkopts = {'view': vdef2.get('iden')}
                self.len(1, await core.nodes('_low:str=foobar <- *', opts=forkopts))

                await core.nodes('[ test:str=foo +#foo:_lowstr=otherval ]', opts=forkopts)
                self.len(1, await core.nodes('_low:str=foobar <- *'))
                self.len(0, await core.nodes('_low:str=foobar <- *', opts=forkopts))

                await core.nodes('[ test:str=foo -#foo:_lowstr]', opts=forkopts)
                self.len(0, await core.nodes('_low:str=foobar <- *', opts=forkopts))

                # Duplicate values in multiple layers of a view only return once
                await core.nodes('[ test:str=foo +#foo:_lowstr=dupstr ]', opts=forkopts)
                await core.nodes('[ test:str=foo +#foo:_lowstr=dupstr ]')
                self.len(1, await core.nodes('_low:str=dupstr <- *', opts=forkopts))

                # Renorming coverage for props with different typeopts
                await core.nodes('[ test:str=foo +#foo:_normstr=normstr ]')
                self.len(1, await core.nodes('_low:str=normstr <- *', opts=forkopts))

                forkview = core.getView(vdef2.get('iden'))
                forklayriden = forkview.wlyr.iden
                await core.delView(vdef2.get('iden'))
                await core.delLayer(forklayriden)
                await core.nodes('_low:str | delnode')

                # Can't delete a type still in use by tagprops
                with self.raises(s_exc.CantDelType):
                    await core.delForm('_low:str')

                await core.nodes('test:str=foo [ -#foo:_lowstr -#foo:_normstr]')
                await core.delTagProp('_lowstr')
                await core.delTagProp('_normstr')
                await core.delForm('_low:str')

                await core.addTagProp('_serv', ('inet:server', {}), {})

                await core.nodes('[ test:str=bar +#bar:_serv=1.2.3.4:80 ]')
                await core.nodes('[ test:str=nop +#bar:_serv=1.2.3.4:123 ]')
                await core.nodes('[ test:int=1 +#bar:_serv=1.2.3.4:80 ]')

                self.len(2, await core.nodes('#bar:_serv.port=80'))
                self.len(2, await core.nodes('#bar:_serv.port<100'))
                self.len(1, await core.nodes('#bar:_serv.port>100'))
                self.len(1, await core.nodes('test:str#bar:_serv.port=80'))
                self.len(1, await core.nodes('test:str#bar:_serv.port<100'))
                self.len(1, await core.nodes('test:str#bar:_serv.port>100'))

                await core.nodes('test:str=nop [ +#bar:_serv=1.2.3.4:99 ]')
                self.len(0, await core.nodes('#bar:_serv.port>100'))
                self.len(0, await core.nodes('test:str#bar:_serv.port>100'))

                self.eq(80, await core.callStorm('test:str#bar:_serv.port=80 return(#bar:_serv.port)'))

                layr = core.getLayer()
                indxby = s_layer.IndxByTagPropVirt(layr, 'test:str', 'bar', '_serv', 'port')
                self.eq(str(indxby), 'IndxByTagPropVirt: test:str#bar:_serv.port')

                indxby = s_layer.IndxByTagPropVirt(layr, None, 'bar', '_serv', 'port')
                self.eq(str(indxby), 'IndxByTagPropVirt: #bar:_serv.port')

                indxby = s_layer.IndxByTagPropVirt(layr, None, None, '_serv', 'port')
                self.eq(str(indxby), 'IndxByTagPropVirt: #*:_serv.port')

                vals = []
                rvals = []
                servtype = core.model.type('inet:server')
                norm = (await servtype.norm('1.2.3.4:80'))[0]
                cmprvals = (('=', norm, servtype.stortype),)
                async for item in layr.liftByTagPropValu(None, None, '_serv', cmprvals):
                    vals.append(item[0])

                async for item in layr.liftByTagPropValu(None, None, '_serv', cmprvals, reverse=True):
                    rvals.append(item[0])

                self.eq(vals, rvals[::-1])
                self.len(2, vals)

                self.len(3, await core.nodes('#bar:_serv.port'))
                await core.nodes('#bar:_serv [ -#bar:_serv ]')
                self.len(0, await core.nodes('#bar:_serv.port'))

                self.len(0, await alist(layr.liftByTagProp(None, None, '_serv', reverse=True)))
                self.len(0, await alist(layr.liftByTagPropValu(None, None, '_serv', cmprvals)))

                await core.addTagProp('_time', ('time', {}), {})
                prec = await core.callStorm('[ test:str=time +#foo:_time=2020-01? ] return(#foo:_time.precision)')
                self.eq(s_time.PREC_MONTH, prec)
                prec = await core.callStorm('test:str=time [ +#foo:_time=2020? ] return(#foo:_time.precision)')
                self.eq(s_time.PREC_YEAR, prec)

                await core.addTagProp('_ival', ('ival', {}), {})
                prec = await core.callStorm('[ test:str=ival +#foo:_ival=2020 ] return(#foo:_ival.precision)')
                self.eq(s_time.PREC_MICRO, prec)
                prec = await core.callStorm('test:str=ival [ +#foo:_ival.precision=day ] return(#foo:_ival.precision)')
                self.eq(s_time.PREC_DAY, prec)
                prec = await core.callStorm('test:str=ival [ +#foo:_ival.precision?=newp ] return(#foo:_ival.precision)')
                self.eq(s_time.PREC_DAY, prec)

                with self.raises(s_exc.BadTypeValu):
                    await core.nodes('test:str=ival [ +#foo:_ival.precision=newp ]')

                await core.nodes('test:str=ival [ +#foo:_ival.precision=year ]')

                await core.nodes('test:str=time [ -#foo:_time ]')
                await core.nodes('test:str=ival [ -#foo:_ival ]')

            # Ensure that the tagprops persist
            async with self.getTestCore(dirn=dirn) as core:
                # Ensure we can still work with a tagprop, after restart, that was
                # defined with a type that came from a CoreModule model definition.
                self.len(1, await core.nodes('test:str +#hehe:_at*near=((10, 20), 1km)'))

    async def test_cortex_prop_pivot(self):

        async with self.getTestReadWriteCores() as (core, wcore):
            self.len(1, await wcore.nodes('[inet:dns:a=(woot.com, 1.2.3.4)]'))

            nodes = await core.nodes('inet:dns:a :ip -> *')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))

            self.len(1, await core.nodes('inet:dns:a :ip -> *'))

    async def test_cortex_noderefs(self):

        async with self.getTestCore() as core:

            sorc = s_common.guid()
            nodes = await core.nodes('[inet:dns:a=(woot.com, 1.2.3.4)]')
            self.len(1, nodes)
            node = nodes[0]

            refs = dict(node.getNodeRefs())
            self.eq(refs.get('fqdn'), ('inet:fqdn', 'woot.com'))
            self.eq(refs.get('ip'), ('inet:ip', (4, 0x01020304)))

            # test un-populated properties
            nodes = await core.nodes('[entity:contact="*"]')
            self.len(1, nodes)
            node = nodes[0]
            self.len(0, node.getNodeRefs())
            # test un-populated array prop
            nodes = await core.nodes('[test:arrayprop="*"]')
            self.len(1, nodes)
            node = nodes[0]
            refs = node.getNodeRefs()
            self.len(0, [r for r in refs if r[0] == 'ints'])
            # test array prop
            await node.set('ints', (1, 2, 3))
            refs = node.getNodeRefs()
            ints = sorted([r[1] for r in refs if r[0] == 'ints'])
            self.eq(ints, (('test:int', 1), ('test:int', 2), ('test:int', 3)))

    async def test_cortex_lift_regex(self):

        async with self.getTestCore() as core:
            self.len(1, await core.nodes('[test:str=hezipha]'))
            self.len(1, await core.nodes('[test:compcomp=((20, lulzlulz),(40, lulz))]'))

            self.len(0, await core.nodes('test:comp:haha~="^zerg"'))
            self.len(1, await core.nodes('test:comp:haha~="^lulz$"'))
            self.len(1, await core.nodes('test:compcomp~="^lulz"'))
            self.len(0, await core.nodes('test:compcomp~="^newp"'))
            self.len(1, await core.nodes('test:str~="zip"'))

    async def test_cortex_lift_reverse(self):

        async with self.getTestCore() as core:

            async def nodeVals(query, prop=None, tag=None):
                nodes = await core.nodes(query)
                if prop:
                    return [node.get(prop)[1] for node in nodes]
                if tag:
                    return [node.getTag(tag) for node in nodes]
                return [node.ndef[1] for node in nodes]

            async def buidRevEq(query):
                # TODO buid based ordering is not stable (and shouldn't be)
                val1 = list(sorted(await nodeVals(query)))
                val2 = list(sorted(await nodeVals(f'reverse({query})')))
                self.len(5, val1)
                self.len(5, val2)
                self.eq(val1, val2)

            await core.nodes('for $x in $lib.range(5) {[ test:int=$x ]}')

            self.eq([0, 1, 2, 3, 4], await nodeVals('test:int'))
            self.eq([4, 3, 2, 1, 0], await nodeVals('reverse(test:int)'))

            self.eq([0, 1, 2, 3], await nodeVals('test:int<=3'))
            self.eq([3, 2, 1, 0], await nodeVals('reverse(test:int<=3)'))

            self.eq([0, 1, 2], await nodeVals('test:int<3'))
            self.eq([2, 1, 0], await nodeVals('reverse(test:int<3)'))

            self.eq([2, 3, 4], await nodeVals('test:int>=2'))
            self.eq([4, 3, 2], await nodeVals('reverse(test:int>=2)'))

            self.eq([3, 4], await nodeVals('test:int>2'))
            self.eq([4, 3], await nodeVals('reverse(test:int>2)'))

            self.eq([1, 2, 3], await nodeVals('test:int*range=(1, 3)'))
            self.eq([3, 2, 1], await nodeVals('reverse(test:int*range=(1, 3))'))

            await core.nodes('for $x in $lib.range(5) {[ file:bytes=* :size=5 ]}')
            await buidRevEq('file:bytes:size=5')

            await core.nodes('for $x in $lib.range(3) {[ test:str=`foo{$x}` test:str=`bar{$x}` ]}')

            self.eq(['foo0', 'foo1', 'foo2'], await nodeVals('test:str~=foo'))
            self.eq(['foo2', 'foo1', 'foo0'], await nodeVals('reverse(test:str~=foo)'))

            await core.nodes('for $x in $lib.range(5) {[ risk:vuln=($x,) :name=eq :desc=`v{$x}` ]}')
            await buidRevEq('risk:vuln:name=eq')

            self.eq(['v2', 'v3', 'v4'], await nodeVals('risk:vuln:desc*range=(v2, v4)', prop='desc'))
            self.eq(['v4', 'v3', 'v2'], await nodeVals('reverse(risk:vuln:desc*range=(v2, v4))', prop='desc'))

            self.eq(['v0', 'v1', 'v2', 'v3', 'v4'], await nodeVals('risk:vuln:desc^=v', prop='desc'))
            self.eq(['v4', 'v3', 'v2', 'v1', 'v0'], await nodeVals('reverse(risk:vuln:desc^=v)', prop='desc'))

            await core.nodes('for $x in $lib.range(5) {[ inet:ip=([4, $x]) :place:loc=`foo.bar` ]}')
            await buidRevEq('inet:ip:place:loc=foo.bar')

            await core.nodes('for $x in $lib.range(3) {[ inet:ip=([4, $x]) :place:loc=`loc.{$x}` ]}')

            self.eq(['loc.0', 'loc.1', 'loc.2'], await nodeVals('inet:ip:place:loc^=loc', prop='place:loc'))
            self.eq(['loc.2', 'loc.1', 'loc.0'], await nodeVals('reverse(inet:ip:place:loc^=loc)', prop='place:loc'))

            await core.nodes('for $x in $lib.range(5) {[ inet:fqdn=`f{$x}.lk` ]}')

            self.eq(['f0.lk', 'f1.lk', 'f2.lk', 'f3.lk', 'f4.lk'], await nodeVals('inet:fqdn=*.lk'))
            self.eq(['f4.lk', 'f3.lk', 'f2.lk', 'f1.lk', 'f0.lk'], await nodeVals('reverse(inet:fqdn=*.lk)'))

            await core.nodes('for $x in $lib.range(5) {[ inet:ip=`::{$x}` ]}')

            self.eq([(6, 0), (6, 1), (6, 2), (6, 3), (6, 4)], await nodeVals('inet:ip>="::"'))
            self.eq([(6, 4), (6, 3), (6, 2), (6, 1), (6, 0)], await nodeVals('reverse(inet:ip>="::")'))

            self.eq([(6, 0), (6, 1), (6, 2), (6, 3)], await nodeVals('inet:ip<=([6, 3])'))
            self.eq([(6, 3), (6, 2), (6, 1), (6, 0)], await nodeVals('reverse(inet:ip<=([6, 3]))'))

            self.eq([(6, 0), (6, 1), (6, 2)], await nodeVals('inet:ip<([6, 3])'))
            self.eq([(6, 2), (6, 1), (6, 0)], await nodeVals('reverse(inet:ip<([6, 3]))'))

            self.eq([(6, 2), (6, 3), (6, 4)], await nodeVals('inet:ip>=([6, 2])'))
            self.eq([(6, 4), (6, 3), (6, 2)], await nodeVals('reverse(inet:ip>=([6, 2]))'))

            self.eq([(6, 3), (6, 4)], await nodeVals('inet:ip>([6, 2])'))
            self.eq([(6, 4), (6, 3)], await nodeVals('reverse(inet:ip>([6, 2]))'))

            self.eq([(6, 1), (6, 2), (6, 3)], await nodeVals('inet:ip*range=(([6, 1]), ([6, 3]))'))
            self.eq([(6, 3), (6, 2), (6, 1)], await nodeVals('reverse(inet:ip*range=(([6, 1]), ([6, 3])))'))

            await core.nodes('for $x in $lib.range(5) {[ inet:server=`[::5]:{$x}` ]}')
            await buidRevEq('inet:server.ip="::5"')

            await core.nodes('for $x in $lib.range(5) {[ test:hugenum=$x ]}')

            self.eq(['0', '1', '2', '3', '4'], await nodeVals('test:hugenum'))
            self.eq(['4', '3', '2', '1', '0'], await nodeVals('reverse(test:hugenum)'))

            self.eq(['0', '1', '2', '3'], await nodeVals('test:hugenum<=3'))
            self.eq(['3', '2', '1', '0'], await nodeVals('reverse(test:hugenum<=3)'))

            self.eq(['0', '1', '2'], await nodeVals('test:hugenum<3'))
            self.eq(['2', '1', '0'], await nodeVals('reverse(test:hugenum<3)'))

            self.eq(['2', '3', '4'], await nodeVals('test:hugenum>=2'))
            self.eq(['4', '3', '2'], await nodeVals('reverse(test:hugenum>=2)'))

            self.eq(['3', '4'], await nodeVals('test:hugenum>2'))
            self.eq(['4', '3'], await nodeVals('reverse(test:hugenum>2)'))

            self.eq(['1', '2', '3'], await nodeVals('test:hugenum*range=(1, 3)'))
            self.eq(['3', '2', '1'], await nodeVals('reverse(test:hugenum*range=(1, 3))'))

            await core.nodes('for $x in $lib.range(5) {[ econ:purchase=* :price=5 ]}')
            await buidRevEq('econ:purchase:price=5')

            await core.nodes('for $x in $lib.range(5) {[ test:float=($x - 2) ]}')

            self.eq([0.0, 1.0, 2.0, -1.0, -2.0], await nodeVals('test:float'))
            self.eq([-2.0, -1.0, 2.0, 1.0, 0.0], await nodeVals('reverse(test:float)'))

            self.eq([-2.0, -1.0, 0.0, 1.0], await nodeVals('test:float<=1'))
            self.eq([1.0, 0.0, -1.0, -2.0], await nodeVals('reverse(test:float<=1)'))

            self.eq([-2.0, -1.0, 0.0], await nodeVals('test:float<1'))
            self.eq([0.0, -1.0, -2.0], await nodeVals('reverse(test:float<1)'))

            self.eq([-1.0, 0.0, 1.0, 2.0], await nodeVals('test:float>=-1'))
            self.eq([2.0, 1.0, 0.0, -1.0], await nodeVals('reverse(test:float>=-1)'))

            self.eq([0.0, 1.0, 2.0], await nodeVals('test:float>=0'))
            self.eq([2.0, 1.0, 0.0], await nodeVals('reverse(test:float>=0)'))

            self.eq([0.0, 1.0, 2.0], await nodeVals('test:float>-1'))
            self.eq([2.0, 1.0, 0.0], await nodeVals('reverse(test:float>-1)'))

            self.eq([-1.0, 0.0, 1.0], await nodeVals('test:float*range=(-1, 1)'))
            self.eq([1.0, 0.0, -1.0], await nodeVals('reverse(test:float*range=(-1, 1))'))

            self.eq([0.0, 1.0], await nodeVals('test:float*range=(0, 1)'))
            self.eq([1.0, 0.0], await nodeVals('reverse(test:float*range=(0, 1))'))

            self.eq([-2.0, -1.0], await nodeVals('test:float*range=(-2, -1)'))
            self.eq([-1.0, -2.0], await nodeVals('reverse(test:float*range=(-2, -1))'))

            await core.nodes('for $x in $lib.range(5) {[ risk:vuln=* :cvss:v3_0:score=1.0 ]}')
            await buidRevEq('risk:vuln:cvss:v3_0:score=1.0')

            a_guid = "a" * 32
            opts = {'vars': {'guid': a_guid}}
            await core.nodes('for $x in $lib.range(5) {[ risk:vuln=* :reporter={[ou:org=$guid]} ]}', opts=opts)
            await buidRevEq(f'risk:vuln:reporter={a_guid}')

            pref = 'a' * 31
            await core.nodes(f'for $x in $lib.range(3) {{[ test:guid=`{pref}{{$x}}` ]}}')

            self.eq([f'{pref}0', f'{pref}1', f'{pref}2'], await nodeVals(f'test:guid^={pref[:-1]}'))
            self.eq([f'{pref}2', f'{pref}1', f'{pref}0'], await nodeVals(f'reverse(test:guid^={pref[:-1]})'))

            await core.nodes('for $x in $lib.range(5) {[ it:exec:proc:create=* :time=`202{$x}` ]}')

            self.eq((1609459200000000, 1640995200000000),
                    await nodeVals('it:exec:proc:create:time@=(2021, 2023)', prop='time'))
            self.eq((1640995200000000, 1609459200000000),
                    await nodeVals('reverse(it:exec:proc:create:time@=(2021, 2023))', prop='time'))

            await core.nodes('for $x in $lib.range(5) {[ test:str=$x :seen=`202{$x}` ]}')

            i2021 = (1609459200000000, 1609459200000001, 1)
            i2022 = (1640995200000000, 1640995200000001, 1)
            self.eq([i2021, i2022], await nodeVals('test:str:seen@=(2021, 2023)', prop='seen'))
            self.eq([i2022, i2021], await nodeVals('reverse(test:str:seen@=(2021, 2023))', prop='seen'))

            await core.nodes('for $x in $lib.range(5) {[ test:int=$x :seen=(2025, 2026) ]}')
            await buidRevEq('test:int:seen=(2025, 2026)')

            await core.nodes('for $x in $lib.range(5) {[ test:guid=($x,) :raw=(["foo"]) ]}')
            await buidRevEq('test:guid:raw=(["foo"])')

            await core.nodes('for $x in $lib.range(5) {[ test:guid=* :raw=`bar{$x}` ]}')
            await buidRevEq('test:guid:raw~=bar')

            await core.nodes('for $x in $lib.range(5) {[ geo:telem=* :place:latlong=(90, 90) ]}')
            await buidRevEq('geo:telem:place:latlong=(90, 90)')

            await core.nodes('for $x in $lib.range(5) {[ geo:telem=* :place:latlong=($x, $x) ]}')

            self.eq([(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)],
                    await nodeVals('geo:telem:place:latlong*near=((0, 0), 400km)', prop='place:latlong'))
            self.eq([(2.0, 2.0), (1.0, 1.0), (0.0, 0.0)],
                    await nodeVals('reverse(geo:telem:place:latlong*near=((0, 0), 400km))', prop='place:latlong'))

            await core.nodes('for $x in $lib.range(5) {[ test:int=$x +#foo=2021 ]}')
            await buidRevEq('test:int#foo')
            await buidRevEq('test:int#foo=2021')

            await core.addTagProp('_test', ('int', {}), {})
            await core.nodes('for $x in $lib.range(5) {[ test:int=$x +#foo:_test=10 ]}')
            await buidRevEq('#foo:_test')
            await buidRevEq('test:int#foo:_test=10')

    async def test_indxchop(self):

        async with self.getTestCore() as core:

            self.len(1, await core.nodes('[test:str=$valu]', opts={'vars': {'valu': 'a' * 258}}))
            self.len(1, await core.nodes('test:str^=aa'))

            # values longer than the index size are truncated with an appended
            # hash so they remain distinct for equality lifts
            size = s_layer.LAYER_UTF8_INDEX_SIZE
            base = 'z' * (size + 10)
            vala = base + 'AAAA'
            valb = base + 'BBBB'
            opts = {'vars': {'a': vala, 'b': valb}}
            self.len(1, await core.nodes('[test:str=$a]', opts=opts))
            self.len(1, await core.nodes('[test:str=$b]', opts=opts))

            self.eq(['test:str', vala], (await core.nodes('test:str=$a', opts=opts))[0].ndef)
            self.eq(['test:str', valb], (await core.nodes('test:str=$b', opts=opts))[0].ndef)
            self.len(2, await core.nodes('test:str^=zzz'))

            # a ^= prefix within the retained base ( LAYER_UTF8_INDEX_SIZE
            # bytes ) matches the index directly
            self.len(2, await core.nodes('test:str^=$p', opts={'vars': {'p': 'z' * (size - 8)}}))

            # a longer prefix uses the partial index and filters on the real
            # value so overflowing values still match as expected
            self.len(2, await core.nodes('test:str^=$p', opts={'vars': {'p': 'z' * (size + 5)}}))
            self.len(1, await core.nodes('test:str^=$a', opts=opts))
            self.eq(['test:str', vala], (await core.nodes('test:str^=$a', opts=opts))[0].ndef)
            self.len(0, await core.nodes('test:str^=$p', opts={'vars': {'p': base + 'C'}}))

            # poly props filter through the member type the same way
            self.len(1, await core.nodes('[test:str=pnode :poly=$a]', opts=opts))
            self.eq(['test:str', 'pnode'], (await core.nodes('test:str:poly^=$a', opts=opts))[0].ndef)

    async def test_tags(self):

        async with self.getTestReadWriteCores() as (core, wcore):

            self.len(1, await wcore.nodes('[(test:str=newp)]'))

            nodes = await wcore.nodes('[(test:str=one +#foo.bar=(2016, 2017))]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq((1451606400000000, 1483228800000000, 31622400000000), node.getTag('foo.bar', ('2016', '2017')))

            nodes = await wcore.nodes('[(test:comp=(10, hehe) +#foo.bar)]')
            self.len(1, nodes)

            self.len(1, await core.nodes('syn:tag=foo'))
            self.len(1, await core.nodes('syn:tag=foo.bar'))

            nodes = await core.nodes('test:str=one')
            self.len(1, nodes)
            node = nodes[0]
            self.true(node.hasTag('foo'))
            self.true(node.hasTag('foo.bar'))

            self.len(2, await core.nodes('#foo.bar'))
            self.len(1, await core.nodes('test:str#foo.bar'))

            with self.raises(s_exc.NoSuchForm):
                await core.nodes('test:newp#foo.bar')

            # delete a tag and it persists
            nodes = await wcore.nodes('test:str=one [-#foo]')
            self.len(1, nodes)
            node = nodes[0]
            self.false(node.hasTag('foo'))
            self.false(node.hasTag('foo.bar'))

            nodes = await wcore.nodes('test:str=one')
            self.len(1, nodes)
            node = nodes[0]
            self.false(node.hasTag('foo'))
            self.false(node.hasTag('foo.bar'))

            # Can norm a list of tag parts into a tag string and use it
            nodes = await wcore.nodes("$foo=('foo', 'bar.baz') $foo=$lib.cast('syn:tag', $foo) [test:int=0 +#$foo]")
            self.len(1, nodes)
            self.eq(set(nodes[0].getTagNames()), {'foo', 'foo.bar_baz'})

            nodes = await wcore.nodes("$foo=('foo', '...V...') $foo=$lib.cast('syn:tag', $foo) [test:int=1 +#$foo]")
            self.len(1, nodes)
            self.eq(set(nodes[0].getTagNames()), {'foo', 'foo.v'})

            # Cannot norm a list of tag parts directly when making tags on a node
            with self.raises(s_exc.BadTypeValu):
                await wcore.nodes("$foo=(('foo', 'bar.baz'),) [test:int=2 +#$foo]")

            # Can set a list of tags directly
            nodes = await wcore.nodes('$foo=("foo", "bar.baz") [test:int=3 +#$foo]')
            self.len(1, nodes)
            self.eq(set(nodes[0].getTagNames()), {'foo', 'bar', 'bar.baz'})

            nodes = await wcore.nodes('$foo=(["foo", "bar.baz"]) [test:int=4 +#$foo]')
            self.len(1, nodes)
            self.eq(set(nodes[0].getTagNames()), {'foo', 'bar', 'bar.baz'})

            nodes = await wcore.nodes('$foo=$lib.set("foo", "bar") [test:int=5 +#$foo]')
            self.len(1, nodes)
            self.eq(set(nodes[0].getTagNames()), {'foo', 'bar'})

            nodes = await wcore.nodes('$tags=(foo, bar, baz) [test:str=lol +#$tags=`200{$lib.len($node.tags())}`]')
            self.len(1, nodes)
            tags = nodes[0].getTags()
            self.len(3, tags)
            for name, valu in tags:
                self.eq(valu, (946684800000000, 946684800000001, 1))

            await self.asyncraises(s_exc.BadTypeValu, wcore.nodes("$tag='' #$tag"))
            await self.asyncraises(s_exc.BadTypeValu, wcore.nodes("$tag='' #$tag=2020"))
            await self.asyncraises(s_exc.BadTypeValu, wcore.nodes("$tag=(null) #foo.$tag"))
            await self.asyncraises(s_exc.BadTypeValu, wcore.nodes("$tag=(foo, bar) #$tag"))
            await self.asyncraises(s_exc.BadTypeValu, wcore.nodes("$tag=(foo, bar) ##$tag"))
            await self.asyncraises(s_exc.BadTypeValu, wcore.nodes("$tag=(foo, bar) inet:fqdn#$tag"))
            await self.asyncraises(s_exc.BadTypeValu, wcore.nodes("test:int $tag=(null) +#foo.$tag"))
            await self.asyncraises(s_exc.BadTypeValu, wcore.nodes("test:int $tag=(foo, bar) $lib.print(#$tag)"))
            await self.asyncraises(s_exc.BadTypeValu, wcore.nodes("test:int $tag=(foo, bar) +#$tag"))
            await self.asyncraises(s_exc.BadTypeValu, wcore.nodes("test:int $tag=(foo, bar) +#$tag=2020"))

    async def test_base_types1(self):

        async with self.getTestCore() as core:
            self.len(1, await core.nodes('[test:type10=one :intprop=21]'))
            nodes = await core.nodes('test:type10=one')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'intprop', 21)

    async def test_cortex_pure_cmds(self):

        cdef0 = {

            'name': 'testcmd0',

            'cmdargs': (
                ('tagname', {}),
                ('--domore', {'default': False, 'action': 'store_true'}),
            ),

            'cmdconf': {
                'hehe': 'haha',
            },

            'storm': '''
                $foo=$(10)
                if $cmdopts.domore {
                    [ +#$cmdconf.hehe ]
                }
                $lib.print(TAGNAME)
                $lib.print($cmdopts)
                [ +#$cmdopts.tagname ]
            ''',
        }

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                await core.setStormCmd(cdef0)

                nodes = await core.nodes('[ inet:asn=10 ] | testcmd0 zoinks')
                self.true(nodes[0].getTag('zoinks'))

                nodes = await core.nodes('[ inet:asn=11 ] | testcmd0 zoinks --domore')

                self.true(nodes[0].getTag('haha'))
                self.true(nodes[0].getTag('zoinks'))

                # test that cmdopts/cmdconf/locals dont leak
                with self.raises(s_exc.NoSuchVar):
                    q = '[ inet:asn=11 ] | testcmd0 zoinks --domore | if ($cmdopts) {[ +#hascmdopts ]}'
                    nodes = await core.nodes(q)

                with self.raises(s_exc.NoSuchVar):
                    q = '[ inet:asn=11 ] | testcmd0 zoinks --domore | if ($cmdconf) {[ +#hascmdconf ]}'
                    nodes = await core.nodes(q)

                with self.raises(s_exc.NoSuchVar):
                    q = '[ inet:asn=11 ] | testcmd0 zoinks --domore | if ($foo) {[ +#hasfoo ]}'
                    nodes = await core.nodes(q)

            # make sure it's still loaded...
            async with self.getTestCore(dirn=dirn) as core:

                await core.nodes('[ inet:asn=30 ] | testcmd0 zoinks')

                await core.delStormCmd('testcmd0')

                with self.raises(s_exc.NoSuchCmd):
                    await core.delStormCmd('newpcmd')

                with self.raises(s_exc.NoSuchName):
                    await core.nodes('[ inet:asn=31 ] | testcmd0 zoinks')

    async def test_base_types2(self):

        async with self.getTestReadWriteCores() as (core, wcore):

            # Test some default values
            nodes = await wcore.nodes('[test:type10=one]')
            self.len(1, nodes)
            node = nodes[0]
            tick = node.get('.created')
            created = node.repr('.created')

            utick = node.get('.updated')
            updated = node.repr('.updated')
            self.eq(tick, utick)
            self.eq(created, updated)

            self.len(1, await core.nodes('.created'))
            self.len(1, await core.nodes('.created=$tick', opts={'vars': {'tick': tick}}))
            self.len(1, await core.nodes('.created>=2010'))
            self.len(1, await core.nodes('.created>2010'))
            self.len(0, await core.nodes('.created<2010'))
            # The year the monolith returns
            self.len(1, await core.nodes('.created*range=(2010, 3001)'))
            self.len(1, await core.nodes('.created*range=("2010", "?")'))

            self.len(1, await core.nodes('.updated<=now'))
            self.len(0, await core.nodes('.updated>now'))
            self.len(1, await core.nodes('.updated=$tick', opts={'vars': {'tick': utick}}))

            vdef2 = await core.view.fork()
            forkopts = {'view': vdef2.get('iden')}

            await core.nodes('[test:str=foo]', opts=forkopts)
            self.len(2, await core.nodes('.created', opts=forkopts))

            # Add another node with a different created time in between our node with different values in
            # two layers to check non-mergesort deduping.
            await core.nodes('[test:str=bar]')
            await core.nodes('[test:str=foo]')
            self.len(3, await core.nodes('.created', opts=forkopts))

            forkopts['vars'] = {'tick': tick}
            self.len(2, await core.nodes('.created>$tick', opts=forkopts))
            self.len(0, await core.nodes('.created?=newp', opts=forkopts))

            nodes = await core.nodes('.created', opts=forkopts)
            revnodes = await core.nodes('reverse(.created)', opts=forkopts)
            self.eq(nodes, revnodes[::-1])

            with self.raises(s_exc.NoSuchProp):
                await core.nodes('.newp>1')

            self.len(1, await wcore.nodes('test:type10=one [:intprop=21 :strprop=qwer :locprop=us.va.reston]'))
            nodes = await wcore.nodes('[test:comp=(33, "THIRTY THREE")]')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'hehe', 33)
            self.propeq(node, 'haha', 'thirty three')

            utick = await core.callStorm('test:type10=one return(.updated)')
            self.gt(utick, tick)

            with self.raises(s_exc.ReadOnlyProp):
                await wcore.nodes('test:comp=(33, "THIRTY THREE") [ :hehe = 80]')

            self.len(0, await wcore.nodes('test:auto=autothis'))
            q = '[test:str=woot :bar={[test:auto=autothis]} :tick=20160505]'
            nodes = await wcore.nodes(q)
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'bar', 'autothis')
            self.propeq(node, 'tick', 1462406400000000)
            self.len(1, await wcore.nodes('test:auto=autothis'))
            # add some time range bumper nodes
            self.len(1, await wcore.nodes('[test:str=toolow :tick=2015]'))
            self.len(1, await wcore.nodes('[test:str=toohigh :tick=2018]'))
            # test lifting by prop without value
            self.len(3, await core.nodes('test:str:tick'))
            nodes = await core.nodes('test:type10=one')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'intprop', 21)
            self.nn(node.get('.created'))
            self.len(2, await core.nodes('test:str^=too'))
            # Loc prop lookup
            nodes = await core.nodes('test:type10:locprop^=us.va')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('test:type10', 'one'))

    async def test_eval(self):
        ''' Cortex.eval test '''

        async with self.getTestCore() as core:

            # test some edit syntax
            nodes = await core.nodes('[ test:comp=(10, haha) +#foo.bar -#foo.bar ]')
            self.len(1, nodes)
            self.nn(nodes[0].getTag('foo'))
            self.none(nodes[0].getTag('foo.bar'))

            # Make sure the 'view' key in optional opts parameter works
            nodes = await core.nodes('test:comp', opts={'view': core.view.iden})
            self.len(1, nodes)

            with self.raises(s_exc.NoSuchView):
                await core.nodes('test:comp', opts={'view': 'xxx'})

            nodes = await core.nodes('[ test:str="foo bar" :tick=2018]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'tick', 1514764800000000)
            self.eq('foo bar', nodes[0].ndef[1])

            nodes = await core.nodes('test:str="foo bar" [ -:tick ]')
            self.len(1, nodes)
            self.none(nodes[0].get('tick'))

            msgs = await core.stormlist('test:str [ -:newp ]')
            self.stormIsInErr('No property named newp.', msgs)

            msgs = await core.stormlist('test:str -test:str:newp')
            self.stormIsInErr('No property named test:str:newp.', msgs)

            msgs = await core.stormlist('test:str +test:newp>newp')
            self.stormIsInErr('No property named test:newp.', msgs)

            nodes = await core.nodes('[test:guid="*" :tick=2001]')
            self.len(1, nodes)
            self.true(s_common.isguid(nodes[0].ndef[1]))
            self.nn(nodes[0].get('tick'))

            nodes = await core.nodes('test:str="foo bar" +test:str')
            self.len(1, nodes)

            nodes = await core.nodes('test:str="foo bar" -test:str:tick')
            self.len(1, nodes)

            qstr = 'test:str="foo bar" +test:str="foo bar" [ :tick=2015 ] +test:str:tick=2015'
            nodes = await core.nodes(qstr)
            self.len(1, nodes)

            # Seed new nodes via nodedefs
            ndef = ('test:comp', (10, 'haha'))
            opts = {'ndefs': (ndef,)}
            # Seed nodes in the query with ndefs
            nodes = await core.nodes('[-#foo]', opts=opts)
            self.len(1, nodes)
            self.none(nodes[0].getTag('foo'))

            # RuntNodes can go through ndefs as well
            self.len(1, await core.nodes('$lib.print(yep)', opts={'ndefs': (('syn:form', 'test:str'),)}))

            # Seed nodes in the query with nids
            foobar = (await core.nodes('test:str="foo bar"'))[0]
            opts = {'nids': (foobar.intnid(),)}
            nodes = await core.nodes('', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'foo bar'))

            # Seed nodes in the query invalid nids
            opts = {'nids': ('deadb33f',)}
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('', opts=opts)

            opts = {'nids': (None,)}
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('', opts=opts)

            opts = {'nids': (None,)}
            msgs = await core.stormlist('', opts=opts)
            self.stormIsInErr('Node IDs must be integers', msgs)

            # init / fini messages contain tick/tock/took/count information
            msgs = await core.stormlist('{}')
            self.len(2, msgs)

            (ityp, info) = msgs[0]
            self.eq('init', ityp)
            self.gt(info.get('tick'), 0)
            self.gt(info.get('abstick'), 0)
            self.eq(info.get('text'), '{}')
            self.eq(info.get('hash'), '99914b932bd37a50b983c5e7c90ae93b')

            (ftyp, fnfo) = msgs[1]
            self.eq('fini', ftyp)
            self.eq(fnfo.get('count'), 0)
            took = fnfo.get('took')
            self.ge(took, 0)
            self.ge(fnfo.get('tock'), info.get('tick'))
            self.ge(fnfo.get('abstock'), info.get('abstick'))
            self.eq(took, fnfo.get('tock') - info.get('tick'))
            self.eq(took, fnfo.get('abstock') - info.get('abstick'))

            # count = 2
            msgs = await core.stormlist('test:comp=(10, haha) test:str="foo bar" ')
            self.len(4, msgs)

            (ftyp, fnfo) = msgs[-1]
            self.eq('fini', ftyp)
            self.eq(fnfo.get('count'), 2)

            # Test and/or/not
            await core.nodes('[test:comp=(1, test) +#meep.morp +#bleep.blorp +#cond]')
            await core.nodes('[test:comp=(2, test) +#meep.morp +#bleep.zlorp +#cond]')
            await core.nodes('[test:comp=(3, foob) +#meep.gorp +#bleep.zlorp +#cond]')

            q = 'test:comp +(:hehe<2 and :haha=test)'
            self.len(1, await core.nodes(q))

            q = 'test:comp +(:hehe<2 and :haha=foob)'
            self.len(0, await core.nodes(q))

            q = 'test:comp +(:hehe<2 or :haha=test)'
            self.len(2, await core.nodes(q))

            q = 'test:comp +(:hehe<2 or :haha=foob)'
            self.len(2, await core.nodes(q))

            q = 'test:comp +(:hehe<2 or #meep.gorp)'
            self.len(2, await core.nodes(q))
            # TODO Add not tests

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:str*near=newp')
            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:str +test:str@=2018')
            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:str +test:str:tick*near=newp')
            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:str +#test*near=newp')
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('test:str +#test*in=newp')
            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str -> # } limit 10')
            with self.raises(s_exc.BadSyntax):
                await core.nodes('test:str -> # { limit 10')
            with self.raises(s_exc.BadSyntax):
                await core.nodes(' | | ')
            with self.raises(s_exc.BadSyntax):
                await core.nodes('[-test:str]')

            # Bad syntax in messge stream
            mesgs = await alist(core.storm(' | | | '))
            self.len(1, [mesg for mesg in mesgs if mesg[0] == 'init'])
            self.len(1, [mesg for mesg in mesgs if mesg[0] == 'fini'])
            # We still get a texthash
            texthash = [mesg for mesg in mesgs if mesg[0] == 'init'][0][1].get('hash')
            self.eq(texthash, hashlib.md5(' | | | '.encode()).hexdigest())
            # Lark sensitive test
            self.stormIsInErr("Unexpected token '|'", mesgs)
            errs = [mesg[1] for mesg in mesgs if mesg[0] == 'err']
            self.eq(errs[0][0], 'BadSyntax')

            # Scrape is not a default behavior
            with self.raises(s_exc.BadSyntax):
                await core.nodes('pennywise@vertex.link')

            self.len(2, await core.nodes(('[ test:str=foo test:str=bar ]')))

            opts = {'vars': {'foo': 'bar'}}

            nodes = await core.nodes('test:str=$foo', opts=opts)
            self.len(1, nodes)
            self.eq('bar', nodes[0].ndef[1])

            # Make sure a tag=valu comparison before the tag is accessed works
            self.len(0, await core.nodes('#newp=2020'))

    async def test_cortex_delnode(self):

        data = {}

        def onPropDel(node):
            data['prop:del'] = True

        def onNodeDel(node):
            data['node:del'] = True

        async with self.getTestCore() as core:

            form = core.model.forms.get('test:str')

            form.onDel(onNodeDel)
            form.props.get('tick').onDel(onPropDel)

            nodes = await core.nodes('[test:pivtarg=foo]')
            self.len(1, nodes)
            targ = nodes[0]

            self.len(1, await core.nodes('[test:pivcomp=(foo, bar)]'))

            with self.raises(s_exc.CantDelNode):
                await targ.delete()

            nodes = await core.nodes('[test:str=foo]')
            self.len(1, nodes)
            targ = nodes[0]
            self.len(1, await core.nodes('[test:arrayprop=* :strs=(foo, bar)]'))

            with self.raises(s_exc.CantDelNode):
                await targ.delete()

            nodes = await core.nodes('[(test:str=baz :tick=(100) +#hehe)]')
            self.len(1, nodes)
            tstr = nodes[0]

            nodes = await core.nodes('syn:tag=hehe')
            self.len(1, nodes)
            tagnode = nodes[0]

            with self.raises(s_exc.CantDelNode):
                await tagnode.delete()

            nid = tstr.intnid()
            await tstr.delete()

            self.true(data.get('prop:del'))
            self.true(data.get('node:del'))

            self.len(0, await core.nodes('test:str=baz'))
            self.len(0, await core.nodes('', opts={'nids': (nid,)}))
            self.len(0, await core.nodes('test:str:tick'))

    async def test_pivot_inout(self):

        async def getPackNodes(core, query):
            nodes = await core.nodes(query)
            nodes = sorted([n.pack() for n in nodes])
            return nodes

        async with self.getTestReadWriteCores() as (core, wcore):
            # seed a node for pivoting

            await core.nodes('[ test:pivcomp=(foo,bar) :tick=2018 ]')
            await wcore.nodes('[ test:str=foo :bar={[meta:source=*]} ]')

            self.len(1, await core.nodes('meta:source -> test:str:bar'))

            q = 'test:pivcomp=(foo,bar) -> test:pivtarg'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:pivtarg', 'foo'))

            # Regression test:  bug in implicit form pivot where absence of foreign key in source node was treated like
            # a match-any
            await wcore.nodes('[ test:int=42 ]')
            q = 'test:pivcomp -> test:int'
            nodes = await getPackNodes(core, q)
            self.len(0, nodes)

            # Multiple props of source form have type of destination form:  pivot through all the matching props.
            await wcore.nodes('[ test:pivcomp=(xxx,yyy) :width=42 ]')
            q = 'test:pivcomp -> test:int'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)

            q = 'test:pivcomp=(foo,bar) :targ -> test:pivtarg'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:pivtarg', 'foo'))

            q = 'test:pivcomp=(foo,bar) :targ -+> test:pivtarg'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('test:pivtarg', 'foo'))

            q = 'test:pivcomp=(foo,bar) :targ -+> *'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('test:pivtarg', 'foo'))

            q = 'test:str=bar -> test:pivcomp:lulz'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))

            q = 'test:str=bar -+> test:pivcomp:lulz'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('test:str', 'bar'))

            q = 'test:pivcomp=(foo,bar) -+> test:pivtarg'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('test:pivtarg', 'foo'))

            q = 'test:pivcomp=(foo,bar) -> *'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('test:pivtarg', 'foo'))
            self.eq(nodes[1][0], ('test:str', 'bar'))

            q = 'test:pivcomp=(foo,bar) -+> *'
            nodes = await getPackNodes(core, q)
            self.len(3, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('test:pivtarg', 'foo'))
            self.eq(nodes[2][0], ('test:str', 'bar'))

            q = 'test:pivcomp=(foo,bar) :lulz -> test:str'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:str', 'bar'))

            q = 'test:pivcomp=(foo,bar) :lulz -+> test:str'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('test:str', 'bar'))

            q = 'test:str=bar <- *'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))

            q = 'test:str=bar <+- *'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))
            self.eq(nodes[1][0], ('test:str', 'bar'))

            # Add tag
            q = 'test:str=bar test:pivcomp=(foo,bar) [+#test.bar]'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            # Lift, filter, pivot in
            q = '#test.bar +test:str <- *'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:pivcomp', ('foo', 'bar')))

            # Pivot tests with optimized lifts
            q = '#test.bar +test:str <+- *'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)

            q = '#test.bar +test:pivcomp -> *'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)

            q = '#test.bar +test:pivcomp -+> *'
            nodes = await getPackNodes(core, q)
            self.len(3, nodes)

            # tag a tag
            q = '[syn:tag=biz.meta +#super.foo +#super.baz +#second.tag]'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)

            # join syn:tag to tags
            q = 'syn:tag -+> #'
            base = await getPackNodes(core, 'syn:tag')
            nodes = await getPackNodes(core, q)
            self.len(9, base)
            self.len(12, nodes)

            q = 'syn:tag:base=meta -+> #'
            nodes = await getPackNodes(core, q)
            self.len(4, nodes)
            self.eq(nodes[0][0], ('syn:tag', 'biz.meta'))
            self.eq(nodes[1][0], ('syn:tag', 'second.tag'))
            self.eq(nodes[2][0], ('syn:tag', 'super.baz'))
            self.eq(nodes[3][0], ('syn:tag', 'super.foo'))

            q = 'syn:tag:base=meta -+> #*'
            nodes = await getPackNodes(core, q)
            self.len(6, nodes)
            self.eq(nodes[0][0], ('syn:tag', 'biz.meta'))
            self.eq(nodes[1][0], ('syn:tag', 'second'))
            self.eq(nodes[2][0], ('syn:tag', 'second.tag'))
            self.eq(nodes[3][0], ('syn:tag', 'super'))
            self.eq(nodes[4][0], ('syn:tag', 'super.baz'))
            self.eq(nodes[5][0], ('syn:tag', 'super.foo'))

            q = 'syn:tag:base=meta -+> #test'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('syn:tag', 'biz.meta'))

            q = 'syn:tag:base=meta -+> #second'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('syn:tag', 'biz.meta'))
            self.eq(nodes[1][0], ('syn:tag', 'second'))

            q = 'syn:tag:base=meta -+> #second.tag'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('syn:tag', 'biz.meta'))
            self.eq(nodes[1][0], ('syn:tag', 'second.tag'))

            q = 'syn:tag:base=meta -+> #super.*'
            nodes = await getPackNodes(core, q)
            self.len(3, nodes)
            self.eq(nodes[0][0], ('syn:tag', 'biz.meta'))
            self.eq(nodes[1][0], ('syn:tag', 'super.baz'))
            self.eq(nodes[2][0], ('syn:tag', 'super.foo'))

            q = 'syn:tag:base=meta -+> #super.baz'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('syn:tag', 'biz.meta'))
            self.eq(nodes[1][0], ('syn:tag', 'super.baz'))

            # tag a node
            q = '[test:str=tagyourtags +#biz.meta]'
            nodes = await getPackNodes(core, q)
            self.len(1, nodes)
            self.eq(nodes[0][0], ('test:str', 'tagyourtags'))

            q = 'test:str -+> #'
            nodes = await getPackNodes(core, q)
            self.len(6, nodes)
            self.eq(nodes[0][0], ('syn:tag', 'biz.meta'))
            self.eq(nodes[1][0], ('syn:tag', 'test.bar'))
            self.eq(nodes[2][0], ('test:str', 'bar'))
            self.eq(nodes[3][0], ('test:str', 'foo'))
            self.eq(nodes[4][0], ('test:str', 'tagyourtags'))
            self.eq(nodes[5][0], ('test:str', 'yyy'))

            q = 'test:str -+> #*'
            nodes = await getPackNodes(core, q)
            self.len(8, nodes)
            self.eq(nodes[0][0], ('syn:tag', 'biz'))
            self.eq(nodes[1][0], ('syn:tag', 'biz.meta'))
            self.eq(nodes[2][0], ('syn:tag', 'test'))
            self.eq(nodes[3][0], ('syn:tag', 'test.bar'))
            self.eq(nodes[4][0], ('test:str', 'bar'))
            self.eq(nodes[5][0], ('test:str', 'foo'))
            self.eq(nodes[6][0], ('test:str', 'tagyourtags'))
            self.eq(nodes[7][0], ('test:str', 'yyy'))

            q = 'test:str=bar -+> #'
            nodes = await getPackNodes(core, q)
            self.len(2, nodes)
            self.eq(nodes[0][0], ('syn:tag', 'test.bar'))
            self.eq(nodes[1][0], ('test:str', 'bar'))

            # tag conditional filters followed by * pivot operators
            # These are all going to yield zero nodes but should
            # parse cleanly.
            q = '#test.bar -#test <- *'
            nodes = await getPackNodes(core, q)
            self.len(0, nodes)

            q = '#test.bar -#test <+- *'
            nodes = await getPackNodes(core, q)
            self.len(0, nodes)

            q = '#test.bar -#test -> *'
            nodes = await getPackNodes(core, q)
            self.len(0, nodes)

            q = '#test.bar -#test -+> *'
            nodes = await getPackNodes(core, q)
            self.len(0, nodes)

            # Setup a propvalu pivot where the secondary prop may fail to norm
            # to the destination prop for some of the inbound nodes.
            await wcore.nodes('[ test:comp=(127,newp) ] [test:comp=(127,127)]')
            mesgs = await core.stormlist('test:comp :haha as test:int -> test:int')

            warns = [msg for msg in mesgs if msg[0] == 'warn']
            self.len(0, warns)
            nodes = [msg for msg in mesgs if msg[0] == 'node']
            self.len(1, nodes)
            self.eq(nodes[0][1][0], ('test:int', 127))

            # Setup a form pivot where the primary prop may fail to norm
            # to the destination prop for some of the inbound nodes.
            self.len(1, await core.nodes('[test:int=10]'))
            self.len(1, await core.nodes('[test:int=25]'))
            self.len(1, await core.nodes('[(test:type10=test :intprop=25)]'))
            mesgs = await core.stormlist('test:int*in=(10, 25) -> test:type10:intprop')

            warns = [msg for msg in mesgs if msg[0] == 'warn']
            self.len(0, warns)
            nodes = [msg for msg in mesgs if msg[0] == 'node']
            self.len(1, nodes)
            self.eq(nodes[0][1][0], ('test:type10', 'test'))

            msgs = await core.stormlist('test:int :loc -> test:newp')
            self.stormIsInErr('No property named test:newp', msgs)

            # poly pivots
            await core.nodes('''
                [
                    ( test:str=ndefpivdst )
                    ( test:str=ndefpivsrc :bar={test:str=ndefpivdst} )
                    ( test:str=ndefpivprp :bar={test:str=ndefpivdst} )
                ]
            ''')

            nodes = await core.nodes('test:str=ndefpivsrc -> test:str')
            self.eq(['ndefpivdst'], [n.ndef[1] for n in nodes])

            nodes = await core.nodes('test:str=ndefpivsrc -> test:str:bar')
            self.len(0, nodes)

            nodes = await core.nodes('test:str=ndefpivdst -> test:str:bar')
            self.sorteq(['ndefpivprp', 'ndefpivsrc'], [n.ndef[1] for n in nodes])

            nodes = await core.nodes('test:str=ndefpivsrc :bar -> * +test:str')
            self.eq(['ndefpivdst'], [n.ndef[1] for n in nodes])

            nodes = await core.nodes('test:str=ndefpivsrc :bar -> test:str:bar')
            self.sorteq(['ndefpivprp', 'ndefpivsrc'], [n.ndef[1] for n in nodes])

            nodes = await core.nodes('test:str=ndefpivsrc :bar -> test:str')
            self.eq(['ndefpivdst'], [n.ndef[1] for n in nodes])

            nodes = await core.nodes('test:str=ndefpivsrc :bar -> test:int')
            self.len(0, nodes)

            # Bad pivot syntax go here
            for q in ['test:pivcomp :lulz <- *',
                      'test:pivcomp :lulz <+- *',
                      'test:pivcomp :lulz <- test:str',
                      'test:pivcomp :lulz <+- test:str',
                      ]:
                with self.raises(s_exc.BadSyntax):
                    await core.nodes(q)

    async def test_cortex_storm_set_tag(self):

        async with self.getTestReadWriteCores() as (core, wcore):

            tick0 = (await core.model.type('time').norm('2014'))[0]
            tick1 = (await core.model.type('time').norm('2015'))[0]
            tick2 = (await core.model.type('time').norm('2016'))[0]

            self.len(1, await wcore.nodes('[ test:str=hehe +#foo=(2014,2016) ]'))
            self.len(1, await wcore.nodes('[ test:str=haha +#bar=2015 ]'))

            nodes = await core.nodes('test:str=hehe')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.getTag('foo')[:2], (tick0, tick2))

            nodes = await core.nodes('test:str=haha')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.getTag('bar')[:2], (tick1, tick1 + 1))

            view = core.getView()
            node = await view.getNodeByNdef(('test:str', 'haha'))
            self.eq(node.getTag('bar')[:2], (tick1, tick1 + 1))

            self.len(1, await wcore.nodes('[ test:str=haha +#bar=2016 ]'))
            nodes = await core.nodes('test:str=haha')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.getTag('bar')[:2], (tick1, tick2 + 1))

            # Sad path
            with self.raises(s_exc.BadTypeValu) as cm:
                await core.nodes('test:str=hehe [+#newp.tag=(2022,2001)]')
            self.eq(cm.exception.get('valu'), ('2022', '2001'))

    async def test_cortex_storm_filt_ival(self):

        async with self.getTestReadWriteCores() as (core, wcore):

            self.len(1, await wcore.nodes('[ test:str=woot +#foo=(2015,2018) +#bar :seen=(2014,2016) ]'))

            self.len(1, await core.nodes('test:str=woot +:seen@=2015'))
            self.len(0, await core.nodes('test:str=woot +:seen@=2012'))
            self.len(1, await core.nodes('test:str=woot +:seen@=(2012,2015)'))
            self.len(0, await core.nodes('test:str=woot +:seen@=(2012,2013)'))

            self.len(1, await core.nodes('test:str=woot +:seen@=#foo'))
            self.len(0, await core.nodes('test:str=woot +:seen@=#bar'))
            self.len(0, await core.nodes('test:str=woot +:seen@=#baz'))

            self.len(1, await core.nodes('test:str=woot $foo=#foo +:seen@=$foo'))

            self.len(1, await core.nodes('test:str +#foo@=2016'))
            self.len(1, await core.nodes('test:str +#foo@=(2015, 2018)'))
            self.len(1, await core.nodes('test:str +#foo@=(2014, 2019)'))
            self.len(0, await core.nodes('test:str +#foo@=(2014, 20141231)'))

            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('test:str +#foo==(2022,2023)')

    async def test_cortex_storm_tagform(self):

        async with self.getTestReadWriteCores() as (core, wcore):

            self.len(1, await wcore.nodes('[ test:str=hehe ]'))
            self.len(1, await wcore.nodes('[ test:str=haha +#foo ]'))
            self.len(1, await wcore.nodes('[ test:str=woot +#foo=(2015,2018) ]'))

            self.len(2, await core.nodes('#foo'))
            self.len(3, await core.nodes('test:str'))

            self.len(2, await core.nodes('test:str#foo'))
            self.len(1, await core.nodes('test:str#foo@=2016'))
            self.len(0, await core.nodes('test:str#foo@=2020'))

            # test the overlap variants
            self.len(0, await core.nodes('test:str#foo@=(2012,2013)'))
            self.len(0, await core.nodes('test:str#foo@=(2020,2022)'))
            self.len(1, await core.nodes('test:str#foo@=(2012,2017)'))
            self.len(1, await core.nodes('test:str#foo@=(2017,2022)'))
            self.len(1, await core.nodes('test:str#foo@=(2012,2022)'))

    async def test_cortex_int_indx(self):

        async with self.getTestReadWriteCores() as (core, wcore):

            await wcore.nodes('[test:int=20]')

            self.len(0, await core.nodes('test:int>=30'))
            self.len(1, await core.nodes('test:int>=20'))
            self.len(1, await core.nodes('test:int>=10'))

            self.len(0, await core.nodes('test:int>30'))
            self.len(0, await core.nodes('test:int>20'))
            self.len(1, await core.nodes('test:int>10'))

            self.len(0, await core.nodes('test:int<=10'))
            self.len(1, await core.nodes('test:int<=20'))
            self.len(1, await core.nodes('test:int<=30'))

            self.len(0, await core.nodes('test:int<10'))
            self.len(0, await core.nodes('test:int<20'))
            self.len(1, await core.nodes('test:int<30'))

            self.len(0, await core.nodes('test:int +test:int>=30'))
            self.len(1, await core.nodes('test:int +test:int>=20'))
            self.len(1, await core.nodes('test:int +test:int>=10'))

            self.len(0, await core.nodes('test:int +test:int>30'))
            self.len(0, await core.nodes('test:int +test:int>20'))
            self.len(1, await core.nodes('test:int +test:int>10'))

            self.len(0, await core.nodes('test:int +test:int<=10'))
            self.len(1, await core.nodes('test:int +test:int<=20'))
            self.len(1, await core.nodes('test:int +test:int<=30'))

            self.len(0, await core.nodes('test:int +test:int<10'))
            self.len(0, await core.nodes('test:int +test:int<20'))
            self.len(1, await core.nodes('test:int +test:int<30'))

            # time indx is derived from the same lift helpers
            await wcore.nodes('[test:str=foo :tick=201808021201]')

            self.len(0, await core.nodes('test:str:tick>=201808021202'))
            self.len(1, await core.nodes('test:str:tick>=201808021201'))
            self.len(1, await core.nodes('test:str:tick>=201808021200'))

            self.len(0, await core.nodes('test:str:tick>201808021202'))
            self.len(0, await core.nodes('test:str:tick>201808021201'))
            self.len(1, await core.nodes('test:str:tick>201808021200'))

            self.len(1, await core.nodes('test:str:tick<=201808021202'))
            self.len(1, await core.nodes('test:str:tick<=201808021201'))
            self.len(0, await core.nodes('test:str:tick<=201808021200'))

            self.len(1, await core.nodes('test:str:tick<201808021202'))
            self.len(0, await core.nodes('test:str:tick<201808021201'))
            self.len(0, await core.nodes('test:str:tick<201808021200'))

            self.len(0, await core.nodes('test:str +test:str:tick>=201808021202'))
            self.len(1, await core.nodes('test:str +test:str:tick>=201808021201'))
            self.len(1, await core.nodes('test:str +test:str:tick>=201808021200'))

            self.len(0, await core.nodes('test:str +test:str:tick>201808021202'))
            self.len(0, await core.nodes('test:str +test:str:tick>201808021201'))
            self.len(1, await core.nodes('test:str +test:str:tick>201808021200'))

            self.len(1, await core.nodes('test:str +test:str:tick<=201808021202'))
            self.len(1, await core.nodes('test:str +test:str:tick<=201808021201'))
            self.len(0, await core.nodes('test:str +test:str:tick<=201808021200'))

            self.len(1, await core.nodes('test:str +test:str:tick<201808021202'))
            self.len(0, await core.nodes('test:str +test:str:tick<201808021201'))
            self.len(0, await core.nodes('test:str +test:str:tick<201808021200'))

            await wcore.nodes('[test:int=99999]')
            self.len(1, await core.nodes('test:int<=20'))
            self.len(2, await core.nodes('test:int>=20'))
            self.len(1, await core.nodes('test:int>20'))
            self.len(0, await core.nodes('test:int<20'))

    async def test_storm_cond_has(self):
        async with self.getTestCore() as core:

            await core.nodes('[ inet:ip=1.2.3.4 :asn=20 ]')
            self.len(1, await core.nodes('inet:ip=1.2.3.4 +:asn'))

            with self.raises(s_exc.BadSyntax):
                await core.nodes('[ inet:ip=1.2.3.4 +:foo ]')

    async def test_storm_cond_not(self):

        async with self.getTestCore() as core:

            self.len(1, await core.nodes('[ test:str=foo +#bar ]'))
            self.len(1, await core.nodes('[ test:str=foo +#bar ] +(not :seen)'))
            self.len(1, await core.nodes('[ test:str=foo +#bar ] +(#baz or not :seen)'))

    async def test_storm_totags(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ test:str=visi +#foo.bar ] -> #')

            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'foo.bar')

            self.len(2, await core.nodes('test:str=visi -> #*'))
            self.len(1, await core.nodes('test:str=visi -> #foo.bar'))
            self.len(1, await core.nodes('test:str=visi -> #foo.*'))
            self.len(0, await core.nodes('test:str=visi -> #baz.*'))

    async def test_storm_fromtags(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=visi test:int=20 +#foo.bar ]')

            nodes = await core.nodes('syn:tag=foo.bar -> test:str')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'visi')

            self.len(2, await core.nodes('syn:tag=foo.bar -> *'))

            await core.nodes('[ test:str=time :tick=2020 +#2020 ]')

            # Attempt a formpivot from a syn:tag node to a secondary property
            # which may not be valid
            msgs = await core.stormlist('syn:tag -> test:str:tick')
            self.stormHasNoWarnErr(msgs)
            self.len(1, [m for m in msgs if m[0] == 'node'])

    async def test_storm_tagtags(self):

        async with self.getTestCore() as core:

            await core.nodes('[ test:str=visi +#foo.bar ] -> # [ +#baz.faz ]')

            nodes = await core.nodes('##baz.faz')

            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'visi')

            # make an icky loop of tags...
            await core.nodes('syn:tag=baz.faz [ +#foo.bar ]')

            # should still be ok...
            nodes = await core.nodes('##baz.faz')

            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'visi')

    async def test_storm_cancel(self):

        async with self.getTestCore() as core:

            evnt = asyncio.Event()

            synts = core.boss.ps()
            if len(synts) == 1 and synts[0].name == 'cortex:migration:layers':
                await synts[0].waitfini(5)

            self.len(0, core.boss.ps())

            async def todo():
                async for mesg in core.storm('[ test:str=foo test:str=bar ] | sleep 10'):
                    if mesg[0] == 'node':
                        evnt.set()

            task = core.schedCoro(todo())

            await evnt.wait()

            synts = core.boss.ps()

            self.len(1, synts)

            await synts[0].kill()

            self.len(0, core.boss.ps())

            await self.asyncraises(asyncio.CancelledError, task)

    async def test_cortex_formcounts(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                nodes = await core.nodes('[ test:str=foo test:str=bar test:int=42 ]')
                self.len(3, nodes)

                self.eq(1, (await core.getFormCounts())['test:int'])
                self.eq(2, (await core.getFormCounts())['test:str'])

            # test that counts persist...
            async with self.getTestCore(dirn=dirn) as core:

                self.eq(1, (await core.getFormCounts())['test:int'])
                self.eq(2, (await core.getFormCounts())['test:str'])

                node = await core.getView().getNodeByNdef(('test:str', 'foo'))
                await node.delete()

                self.eq(1, (await core.getFormCounts())['test:str'])

    async def test_cortex_greedy(self):
        ''' Issue a large request, and make sure we can still do stuff in a reasonable amount of time'''

        async with self.getTestCore() as core:
            # Prime the fork pool on a solo run
            self.len(0, await core.nodes('.created | spin'))
            event = asyncio.Event()
            async def add_stuff():
                vals = list(range(20000))
                event.set()
                msgs = await core.stormlist('for $i in $vals {[test:int=$i]} | spin',
                                             opts={'editformat': 'none', 'vars': {'vals': vals}})
                self.stormHasNoWarnErr(msgs)

            fut = core.schedCoro(add_stuff())

            # Wait for him to get started
            before = time.time()
            await event.wait()

            nodes = await core.nodes('[test:str=hehe]')
            self.len(1, nodes)
            delta = time.time() - before

            # Note: before latency improvement, delta was > 4 seconds
            self.lt(delta, 0.5)

        # Make sure the task in flight can be killed in a reasonable time
        delta = time.time() - before
        self.lt(delta, 1.0)

    async def test_storm_multinode_lift_edit(self):

        # Editing nodes while iterating a lift that yields multiple nodes sharing
        # the lifted value must not re-emit nodes. Each edit bumps
        # the node "updated" meta time, which deletes an index row in the same
        # db the lift cursor is walking; the storage layer must keep the lift
        # cursor consistent so each node is yielded exactly once.
        async with self.getTestCore() as core:

            self.len(3, await core.nodes('''
                [
                    inet:fqdn=ns1.example.com
                    inet:whois:record=( { "fqdn": "example.com", "created": "2024/03/27 03:00", "updated": "2026/03/22 11:37" } )
                    inet:whois:record=( { "fqdn": "example.com", "created": "2024/03/27 03:00", "updated": "2024/09/18 22:46" } )
                ]
            '''))

            # the two records share :fqdn, so this prop-value lift yields two nodes
            self.len(2, await core.nodes('inet:whois:record:fqdn=example.com'))

            # prop-value lift + tag edit
            nodes = await core.nodes('inet:whois:record:fqdn=example.com [ +#foo ]')
            self.len(2, nodes)
            self.true(all(node.getTag('foo') is not None for node in nodes))

            # prop-value lift + scalar prop edit
            nodes = await core.nodes('inet:whois:record:fqdn=example.com [ :updated=2020/01/01 ]')
            self.len(2, nodes)

            # prop-value lift + array prop edit
            self.len(2, await core.nodes('inet:whois:record:fqdn=example.com [ :nameservers+=ns1.example.com ]'))

            # form lift + tag edit (multiple nodes of one form)
            self.len(2, await core.nodes('inet:whois:record [ +#bar ]'))

            # explicit pivot into the shared-value lift, with and without an edit
            self.len(2, await core.nodes('inet:fqdn=ns1.example.com $ns=$node :zone -> inet:whois:record:fqdn'))
            self.len(2, await core.nodes('inet:fqdn=ns1.example.com $ns=$node :zone -> inet:whois:record:fqdn [ :nameservers+=$ns ]'))

    async def test_storm_pivprop(self):

        async with self.getTestCore() as core:

            self.len(1, await core.nodes('[ inet:asn=200 :registrant:name=visi ]'))
            self.len(1, await core.nodes('[ inet:ip=1.2.3.4 :asn=200 ]'))
            self.len(1, await core.nodes('[ inet:ip=5.6.7.8 :asn=8080 ]'))
            self.len(1, await core.nodes('[ inet:ip=6.7.8.9 ]'))

            self.len(1, await core.nodes('inet:asn=200 +:registrant:name=visi'))

            self.len(1, await core.nodes('inet:asn=200 +:registrant:name=visi'))
            nodes = await core.nodes('inet:ip +:asn::registrant:name=visi')

            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))

            nodes = await core.nodes('inet:ip +:asn::registrant:name')
            self.len(1, nodes)

            self.len(1, await core.nodes('inet:ip.created +:asn::registrant:name'))

            await core.nodes('[ entity:contact=* :email=visi@vertex.link ]')
            nodes = await core.nodes('entity:contact +:email::fqdn=vertex.link')
            self.len(1, nodes)

            nodes = await core.nodes('entity:contact +:email::fqdn')
            self.len(1, nodes)

            nodes = await core.nodes('entity:contact +:org::url::host::notaprop')
            self.len(0, nodes)

            # test pivprop with an extmodel prop
            await core.addForm('_hehe:haha', 'int', {}, {'doc': 'The hehe:haha form.'})
            await core.addFormProp('inet:asn', '_pivo', ('_hehe:haha', {}), {})

            self.len(1, await core.nodes('inet:asn=200 [ :_pivo=10 ]'))

            nodes = await core.nodes('inet:ip +:asn::_pivo=10')
            self.len(1, nodes)

            nodes = await core.nodes('inet:ip +:asn::_pivo')
            self.len(1, nodes)

            # try to pivot to a node that no longer exists
            await core.nodes('inet:asn | delnode --force')

            nodes = await core.nodes('inet:ip +:asn::name')
            self.len(0, nodes)

            # try to pivot to deleted form/props for coverage
            self.len(1, await core.nodes('[ inet:asn=200 :_pivo=10 ]'))

            core.model.delForm('_hehe:haha')
            # TODO: add a cached lookup for whether this could be possible with the current model and raise
            # with self.raises(s_exc.NoSuchForm):
            #    await core.nodes('inet:ip +:asn::_pivo::notaprop')

            await core.nodes('[ou:position=* :contact={[entity:contact=* :email=a@v.lk]}]')
            await core.nodes('[ou:position=* :contact={[entity:contact=* :email=b@v.lk]}]')
            await core.nodes('[ou:position=* :contact={[entity:contact=* :email=c@v.lk]}]')
            await core.nodes('[ou:position=* :contact={[entity:contact=* :emails=(a@v.lk, b@v.lk)]}]')
            await core.nodes('[ou:position=* :contact={[entity:contact=* :emails=(c@v.lk, d@v.lk)]}]')
            await core.nodes('[ou:position=* :contact={[entity:contact=* :emails=(a@v.lk, d@v.lk)]}]')

            nodes = await core.nodes('ou:position:contact::email::username=a')
            self.len(1, nodes)
            for node in nodes:
                self.eq('ou:position', node.ndef[0])

            nodes = await core.nodes('ou:position:contact::email::username*in=(a, b)')
            self.len(2, nodes)
            for node in nodes:
                self.eq('ou:position', node.ndef[0])

            nodes = await core.nodes('ou:position:contact::emails*[=a@v.lk]')
            self.len(2, nodes)
            for node in nodes:
                self.eq('ou:position', node.ndef[0])

            nodes = await core.nodes('ou:position:contact::emails*[in=(a@v.lk, c@v.lk)]')
            self.len(3, nodes)
            for node in nodes:
                self.eq('ou:position', node.ndef[0])

            await core.nodes('[entity:contributed=* :actor={[entity:contact=* :email=foo@vertex.link ]}]')
            await core.nodes('[entity:contributed=* :actor={[entity:contact=* :email=bar@vertex.link ]}]')
            await core.nodes('[entity:contributed=* :actor={[entity:contact=* :email=baz@vertex.link ]}]')
            await core.nodes('[entity:contributed=* :actor={[entity:contact=* :email=faz@vertex.link ]}]')

            await core.nodes('[entity:contributed=* :actor={[entity:contact=* :emails=(foo@vertex.link, bar@vertex.link) ]}]')
            await core.nodes('[entity:contributed=* :actor={[entity:contact=* :emails=(baz@vertex.link, faz@vertex.link) ]}]')
            await core.nodes('[entity:contributed=* :actor={[entity:contact=* :emails=(foo@vertex.link, faz@vertex.link) ]}]')

            nodes = await core.nodes('entity:contributed:actor::email::username=foo')
            self.len(1, nodes)
            for node in nodes:
                self.eq('entity:contributed', node.ndef[0])

            nodes = await core.nodes('entity:contributed:actor::email::username*in=(foo, bar)')
            self.len(2, nodes)
            for node in nodes:
                self.eq('entity:contributed', node.ndef[0])

            nodes = await core.nodes('entity:contributed:actor::emails*[=foo@vertex.link]')
            self.len(2, nodes)
            for node in nodes:
                self.eq('entity:contributed', node.ndef[0])

            nodes = await core.nodes('entity:contributed:actor::emails*[in=(foo@vertex.link, baz@vertex.link)]')
            self.len(3, nodes)
            for node in nodes:
                self.eq('entity:contributed', node.ndef[0])

            await core.nodes('[test:str=1 :pivvirt={[test:virtiface=* :server=tcp://1.2.3.4]}]')
            await core.nodes('[test:str=2 :pivvirt={[test:virtiface=* :server=udp://1.2.3.4]}]')
            await core.nodes('[test:str=3 :pivvirt={[test:virtiface=* :server=gre://1.2.3.4]}]')
            await core.nodes('[test:str=4 :pivvirt={[test:virtiface=* :servers=(tcp://1.2.3.4, tcp://2.3.4.5)]}]')
            await core.nodes('[test:str=5 :pivvirt={[test:virtiface=* :servers=(udp://1.2.3.4, udp://2.3.4.5)]}]')
            await core.nodes('[test:str=6 :pivvirt={[test:virtiface=* :servers=(tcp://1.2.3.4, udp://2.3.4.5)]}]')

            nodes = await core.nodes('test:str:pivvirt::server::proto=tcp')
            self.len(1, nodes)
            for node in nodes:
                self.eq('test:str', node.ndef[0])

            nodes = await core.nodes('test:str::pivvirt::server::proto=tcp')
            self.len(1, nodes)
            for node in nodes:
                self.eq('test:str', node.ndef[0])

            nodes = await core.nodes('test:str:pivvirt::server::proto*in=(tcp, udp)')
            self.len(2, nodes)
            for node in nodes:
                self.eq('test:str', node.ndef[0])

            nodes = await core.nodes('test:str:pivvirt::servers*[=tcp://1.2.3.4]')
            self.len(2, nodes)
            for node in nodes:
                self.eq('test:str', node.ndef[0])

            nodes = await core.nodes('test:str::pivvirt::servers*[=tcp://1.2.3.4]')
            self.len(2, nodes)
            for node in nodes:
                self.eq('test:str', node.ndef[0])

            nodes = await core.nodes('test:str:pivvirt::servers*[in=(tcp://1.2.3.4, udp://1.2.3.4)]')
            self.len(3, nodes)
            for node in nodes:
                self.eq('test:str', node.ndef[0])

            # TODO: add a cached lookup for whether this could be possible with the current model and raise
            # with self.raises(s_exc.NoSuchProp):
            #    nodes = await core.nodes('entity:contact:email::newp=a')

            await core.nodes('[it:exec:fetch=* :request={[inet:http:request=* :flow={[inet:flow=* :client=tcp://1.2.3.4]} ]}]')
            await core.nodes('[it:exec:fetch=* :request={[inet:http:request=* :flow={[inet:flow=* :client=tcp://5.6.7.8]} ]}]')
            await core.nodes('[it:exec:fetch=* :request={[inet:http:request=* :flow={[inet:flow=* :client=tcp://1.2.3.5]} ]}]')

            self.len(2, await core.nodes('it:exec:fetch:request::flow::client.ip*in=(1.2.3.4, 5.6.7.8)'))

            await core.nodes('inet:ip=1.2.3.4 [:asn=5]')
            await core.nodes('inet:ip=1.2.3.5 [:asn=6]')
            await core.nodes('inet:ip=5.6.7.8 [:asn=7]')

            # liftpropby with embed lift through virt
            self.len(1, await core.nodes('it:exec:fetch:request::flow::client.ip::asn>6'))
            self.len(2, await core.nodes('it:exec:fetch:request::flow::client.ip::asn*in=(5,6)'))

            # liftpropvirtby with embed lift through virt
            await core.nodes('inet:ip=1.2.3.4 [:seen=(2020,2021)]')
            await core.nodes('inet:ip=5.6.7.8 [:seen=(2022,2023)]')

            self.len(1, await core.nodes('it:exec:fetch:request::flow::client.ip::seen.min>2020'))
            self.len(2, await core.nodes('it:exec:fetch:request::flow::client.ip::seen.min*in=(2020,2022)'))

            # liftbyarray with embed lift through virt
            await core.nodes('inet:asn=5 [:registrant={[ps:person=* :titles=(analyst,researcher)]}]')
            await core.nodes('inet:asn=6 [:registrant={[ps:person=* :titles=(analyst,engineer)]}]')
            await core.nodes('inet:asn=7 [:registrant={[ps:person=* :titles=(manager,)]}]')

            self.len(2, await core.nodes('it:exec:fetch:request::flow::client.ip::asn::registrant::titles*[=analyst]'))
            self.len(1, await core.nodes('it:exec:fetch:request::flow::client.ip::asn::registrant::titles*[=manager]'))

            # embed lift through virt with no value
            self.len(0, await core.nodes('it:exec:fetch:request::flow::client.port::asn=5'))

            # embed lift through virt with no node
            await core.nodes('[it:exec:fetch=* :request={[inet:http:request=* :flow={[inet:flow=* :client=tcp://9.9.9.9]} ]}]')
            await core.nodes('inet:ip=9.9.9.9 [:asn=42]')
            self.len(1, await core.nodes('it:exec:fetch:request::flow::client.ip::asn=42'))
            await core.nodes('inet:ip=9.9.9.9 | delnode --force')
            self.len(0, await core.nodes('it:exec:fetch:request::flow::client.ip::asn=42'))

            await core.nodes('[test:str=nvirt1 :bar={[test:guid=* :seen=2020]} ]')
            await core.nodes('[test:str=nvirt2 :bar={[test:guid=* :seen=2021]} ]')
            await core.nodes('[test:str=nvirt3 :bar={[test:guid=* :seen=2022]} ]')

            nodes = await core.nodes('test:str:bar::seen.min>2020')
            self.len(2, nodes)
            for node in nodes:
                self.eq('test:str', node.ndef[0])

            nodes = await core.nodes('test:str::bar::seen.min>2020')
            self.len(2, nodes)
            for node in nodes:
                self.eq('test:str', node.ndef[0])

            await core.nodes('test:str:bar::seen.min>2021 [ -:bar ]')
            await core.nodes('test:guid:seen.min>2021 | delnode')
            self.len(1, await core.nodes('test:str:bar::seen.min>2020'))

            await core.nodes('[test:str=avirt1 :bar={[test:virtiface=* :servers=(tcp://1.2.3.4, udp://2.3.4.5)]}]')
            await core.nodes('[test:str=avirt2 :bar={[test:virtiface=* :servers=(udp://1.2.3.4, udp://2.3.4.5)]}]')
            await core.nodes('[test:str=avirt3 :bar={[test:virtiface=* :servers=(tcp://4.5.6.7, udp://7.8.4.5)]}]')

            nodes = await core.nodes('test:str:bar::servers*[.ip=1.2.3.4]')
            self.len(2, nodes)
            for node in nodes:
                self.eq('test:str', node.ndef[0])

            nodes = await core.nodes('test:str::bar::servers*[.ip=1.2.3.4]')
            self.len(2, nodes)
            for node in nodes:
                self.eq('test:str', node.ndef[0])

            sha256 = 'fd0a257397ee841ccd3b6ba76ad59c70310fd402ea3c9392d363f754ddaa67b5'
            opts = {'vars': {'sha256': sha256}}
            await core.nodes('''[
                file:mime:jpg=* :file=${[ file:bytes=({"sha256": $sha256}) ]}
                file:mime:gif=* :file=${[ file:bytes=({"sha256": $sha256}) ]}
            ]''', opts=opts)

            nodes = await core.nodes('file:mime:image:file::sha256=$sha256', opts=opts)
            self.len(2, nodes)
            self.eq('file:mime:jpg', nodes[0].ndef[0])
            self.eq('file:mime:gif', nodes[1].ndef[0])

            # When pivoting through mixed types, don't raise BadTypeValu for incompatible operations
            # since they could be valid in some cases
            self.len(0, await core.nodes('test:str:bar::seen*[=tcp]'))
            self.len(0, await core.nodes('test:str:bar::seen>2020'))

            await core.nodes('[test:str=newp :bar={[test:str=newp :hehe=newp]}]')
            self.len(0, await core.nodes('test:str:bar::hehe::foo=baz'))

            # test pivprop through a non-form type raises NoSuchForm
            await core.nodes('[test:str=hehe :hehe=notaform]')
            with self.raises(s_exc.NoSuchForm):
                await core.nodes('test:str=hehe +:hehe::tick=2020')

class CortexBasicTest(s_t_utils.SynTest):
    '''
    The tests that are unlikely to break with different types of layers installed
    '''
    async def test_storm_on_callbacks(self):

        async with self.getTestCore() as core:

            # Test on:add callback - creating a test:onstorm node should auto-set :tick
            nodes = await core.nodes('[test:onstorm=*]')
            self.len(1, nodes)
            self.nn(nodes[0].get('tick'))
            self.propeq(nodes[0], 'tick', 1735689600000000)

            # Test on:set callback - setting :name should copy it to :hehe
            nodes = await core.nodes('[test:onstorm=* :name=foobar]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'hehe', 'foobar')

            # Test on:set fires on update too
            iden = nodes[0].ndef[1]
            nodes = await core.nodes(f'test:onstorm={iden} [:name=bazqux]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'hehe', 'bazqux')

            # Test on:del callback - deleting :ondelprop should set :hehe to "deleted"
            nodes = await core.nodes(f'test:onstorm={iden} [:ondelprop=hi]')
            self.len(1, nodes)
            nodes = await core.nodes(f'test:onstorm={iden} [-:ondelprop]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'hehe', 'deleted')

            # Test that callbacks run as the calling user with asroot elevation
            visi = await core.auth.addUser('visi')
            await visi.addRule((True, ('node', 'add')))
            await visi.addRule((True, ('node', 'prop', 'set')))
            opts = {'user': visi.iden}
            nodes = await core.nodes('[test:onstorm=*]', opts=opts)
            self.len(1, nodes)
            self.nn(nodes[0].get('tick'))

            # Test error handling - bad storm query in on.set callback logs error but doesn't crash
            with self.getLoggerStream('synapse.datamodel') as stream:
                await core.addFormProp('test:onstorm', '_badstorm', ('str', {}), {
                    'on': {'set': {'q': '| badcommand'}},
                })
                nodes = await core.nodes(f'test:onstorm={iden} [:_badstorm=test]')
                await stream.expect('on.set model callback error', timeout=6)
                self.len(1, nodes)

            # Test error handling - bad storm query in on.del prop callback logs error but doesn't crash
            with self.getLoggerStream('synapse.datamodel') as stream:
                await core.addFormProp('test:onstorm', '_baddel', ('str', {}), {
                    'on': {'del': {'q': '| badcommand'}},
                })
                await core.nodes(f'test:onstorm={iden} [:_baddel=test]')
                nodes = await core.nodes(f'test:onstorm={iden} [-:_baddel]')
                await stream.expect('on.del model callback error', timeout=6)
                self.len(1, nodes)

            # Test error handling - bad storm query in form on.add callback logs error but doesn't crash
            form = core.model.form('test:onstorm')
            saved = form.onstormadd
            form.onstormadd = '| badcommand'
            with self.getLoggerStream('synapse.datamodel') as stream:
                nodes = await core.nodes('[test:onstorm=*]')
                await stream.expect('on.add model callback error', timeout=6)
                self.len(1, nodes)

            # Test error handling - bad storm query in form on.del callback logs error but doesn't crash
            form.onstormadd = saved
            form.onstormdel = '| badcommand'
            with self.getLoggerStream('synapse.datamodel') as stream:
                nodes = await core.nodes('test:onstorm | delnode')
                await stream.expect('on.del model callback error', timeout=6)

        # Test on:add callback on a ctor-defined form
        async with self.getTestCore() as core:
            nodes = await core.nodes('[test:ctoronstorm=foobar]')
            self.len(1, nodes)
            self.nn(nodes[0].get('tick'))

        # Test on:add callback on a type-defined form
        async with self.getTestCore() as core:
            nodes = await core.nodes('[test:onstorm2=*]')
            self.len(1, nodes)
            self.nn(nodes[0].get('tick'))

    async def test_cortex_coreinfo(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            coreinfo = await prox.getCoreInfoV2()

            for field in ('version', 'modeldict', 'stormdocs'):
                self.isin(field, coreinfo)

            layers = list(core.listLayers())
            self.len(1, layers)
            lyr = layers[0]
            info = await lyr.pack()
            self.eq(info['name'], 'default')

            views = list(core.listViews())
            self.len(1, views)
            view = views[0]
            info = await view.pack()
            self.eq(info['name'], 'default')

    async def test_cortex_model_dict(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            model = await prox.getModelDict()

            tnfo = model['types'].get('inet:ip')

            self.nn(tnfo)
            self.eq(tnfo['info']['doc'], 'An IPv4 or IPv6 address.')
            self.none(tnfo.get('virts'))

            tnfo = model['types'].get('inet:sockaddr')
            self.eq(tnfo['virts'], {'ip': 'inet:ip', 'port': 'inet:port'})
            self.eq(tnfo['lift_cmprs'], ('=', '~=', '?=', 'in=', 'range=', '^='))
            self.eq(tnfo['filter_cmprs'], ('=', '!=', '~=', '^=', 'in=', 'range='))

            fnfo = model['forms'].get('inet:ip')
            self.nn(fnfo)

            pnfo = fnfo['props'].get('asn')

            self.nn(pnfo)
            self.eq(pnfo['type'][0], 'poly')

            modelt = model['types']

            self.eq('yara', model['forms']['it:app:yara:rule']['props']['text']['display']['syntax'])

            fname = 'inet:dns:rev'
            cmodel = core.model.form(fname)
            modelf = model['forms'][fname]
            self.eq(cmodel.type.stortype, modelt[fname].get('stortype'))

            self.eq(cmodel.prop('ip').type.stortype,
                    modelt.get(modelf['props']['ip']['type'][0], {}).get('stortype'))

            fname = 'file:bytes'
            cmodel = core.model.form(fname)
            modelf = model['forms'][fname]
            self.eq(cmodel.type.stortype, modelt[fname].get('stortype'))

            self.eq(cmodel.prop('size').type.stortype,
                    modelt.get(modelf['props']['size']['type'][0], {}).get('stortype'))
            self.eq(cmodel.prop('sha256').type.stortype,
                    modelt.get(modelf['props']['sha256']['type'][0], {}).get('stortype'))

            fname = 'test:int'
            cmodel = core.model.form(fname)
            modelf = model['forms'][fname]
            self.eq(cmodel.type.stortype, modelt[fname].get('stortype'))

            mimemeta = model['interfaces'].get('file:mime:meta')
            self.nn(mimemeta)
            self.isin('props', mimemeta)
            self.eq('file', mimemeta['props'][0][0])

    async def test_storm_graph(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            await core.nodes('[ inet:dns:a=(woot.com, 1.2.3.4) ]')

            opts = {'graph': True}
            msgs = await prox.storm('inet:dns:a', opts=opts).list()
            nodes = [m[1] for m in msgs if m[0] == 'node']

            self.len(4, nodes)

            for node in nodes:
                if node[0][0] == 'inet:dns:a':
                    self.len(0, node[1]['path']['edges'])
                elif node[0][0] == 'inet:ip':
                    self.eq(node[1]['path']['edges'], (
                        (0, {'type': 'prop', 'prop': 'ip', 'reverse': True}),
                    ))
                elif node[0] == ('inet:fqdn', 'woot.com'):
                    self.eq(node[1]['path']['edges'], (
                        (0, {'type': 'prop', 'prop': 'fqdn', 'reverse': True}),
                    ))

    async def test_onadd(self):
        arg_hit = {}

        async def testcb(node):
            arg_hit['hit'] = node

        async with self.getTestCore() as core:
            core.model.form('test:str').onAdd(testcb)

            nodes = await core.nodes('[test:str=hello]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node, arg_hit.get('hit'))

            arg_hit['hit'] = None
            core.model.form('test:str').offAdd(testcb)
            nodes = await core.nodes('[test:str=goodbye]')
            self.len(1, nodes)
            self.none(arg_hit.get('hit'))

    async def test_cell(self):

        async with self.getTestCoreAndProxy() as (core, proxy):

            cellver = core.cellinfo.get('synapse:version')
            self.eq(cellver, s_version.version)

            # test the remote storm result counting API
            self.eq(0, await proxy.count('test:pivtarg'))

            # Test the stormpkg apis
            otherpkg = {
                'name': 'foosball',
                'version': '0.0.1',
                'dependencies': {'synapse': {'version': '>=3.0.0b3,<4.0.0'}},
            }
            self.none(await proxy.addStormPkg(otherpkg))
            pkgs = await proxy.getStormPkgs()
            self.len(1, pkgs)
            self.eq(pkgs, [otherpkg])
            pkg = await proxy.getStormPkg('foosball')
            self.eq(pkg, otherpkg)
            self.none(await proxy.delStormPkg('foosball'))
            pkgs = await proxy.getStormPkgs()
            self.len(0, pkgs)
            await self.asyncraises(s_exc.NoSuchPkg, proxy.delStormPkg('foosball'))

            self.none(await core._delStormPkg('foosball'))

            # This segfaults in regex < 2022.9.11
            query = '''test:str~="(?(?<=A)|(?(?![^B])C|D))"'''
            msgs = await core.stormlist(query)

            # test reqValidStorm
            self.true(await proxy.reqValidStorm('test:str=test'))
            self.true(await proxy.reqValidStorm('1.2.3.4 | spin', opts={'mode': 'lookup'}))
            with self.raises(s_exc.BadArg):
                await proxy.reqValidStorm('1.2.3.4 | spin', opts={'mode': 'autoadd'})
            with self.raises(s_exc.BadSyntax):
                await proxy.reqValidStorm('1.2.3.4 ')
            with self.raises(s_exc.BadSyntax):
                await proxy.reqValidStorm('| 1.2.3.4 ', opts={'mode': 'lookup'})

            # test isValidStorm
            ok, info = await proxy.isValidStorm('test:str=test')
            self.true(ok)
            self.eq(info, {})

            ok, info = await proxy.isValidStorm('1.2.3.4 | spin', opts={'mode': 'lookup'})
            self.true(ok)
            self.eq(info, {})

            ok, info = await proxy.isValidStorm('1.2.3.4 | spin', opts={'mode': 'autoadd'})
            self.false(ok)
            self.eq(info[0], 'BadArg')

            ok, info = await proxy.isValidStorm('1.2.3.4 ')
            self.false(ok)
            self.eq(info[0], 'BadSyntax')
            self.isin('mesg', info[1])

            ok, info = await proxy.isValidStorm('| 1.2.3.4 ', opts={'mode': 'lookup'})
            self.false(ok)
            self.eq(info[0], 'BadSyntax')

            ok, info = await proxy.isValidStorm(12345678)
            self.false(ok)
            self.eq(info[0], 'TypeError')

    async def test_stormcmd(self):

        async with self.getTestCoreAndProxy() as (realcore, core):

            await realcore.nodes('[ it:dev:str=visi it:dev:str=whippit ]')

            self.eq(2, await core.count('it:dev:str'))

            # test cmd as last text syntax
            self.eq(1, await core.count('it:dev:str | limit 1'))

            self.eq(1, await core.count('it:dev:str | limit 1      '))

            # test cmd and trailing pipe and whitespace syntax
            self.eq(2, await core.count('it:dev:str | limit 10 | [ +#foo.bar ]'))
            self.eq(1, await core.count('it:dev:str | limit 10 | +it:dev:str=visi'))

            # test invalid option syntax
            msgs = await alist(core.storm('it:dev:str | limit --woot'))
            self.printed(msgs, 'Usage: limit [options] <count>')
            self.len(0, [m for m in msgs if m[0] == 'node'])

            oldverpkg = {
                'name': 'versionfail',
                'version': (0, 0, 1),
                'dependencies': {'synapse': {'version': '>=1337.0.0,<2000.0.0'}},
                'commands': ()
            }

            with self.raises(s_exc.StormPkgRequires):
                await core.addStormPkg(oldverpkg)

            oldverpkg = {
                'name': 'versionfail',
                'version': (0, 0, 1),
                'dependencies': {'synapse': {'version': '>=1337.0.0,<2000.0.0'}},
                'commands': ()
            }

            with self.raises(s_exc.StormPkgRequires):
                await core.addStormPkg(oldverpkg)

            oldverpkg = {
                'name': 'versionfail',
                'version': (0, 0, 1),
                'dependencies': {'synapse': {'version': '>=0.0.1,<2.0.0'}},
                'commands': ()
            }

            with self.raises(s_exc.StormPkgRequires):
                await core.addStormPkg(oldverpkg)

            noverpkg = {
                'name': 'nomin',
                'version': (0, 0, 1),
                'commands': ()
            }

            await core.addStormPkg(noverpkg)

            badcmdpkg = {
                'name': 'badcmd',
                'version': (0, 0, 1),
                'commands': ({
                    'name': 'invalidCMD',
                    'descr': 'test command',
                    'storm': '',
                },)
            }

            await self.asyncraises(s_exc.SchemaViolation, core.addStormPkg(badcmdpkg))
            await self.asyncraises(s_exc.BadArg, s_common.aspin(core.storm(None)))

    async def test_onsetdel(self):

        arg_hit = {}

        async def test_cb(node):
            arg_hit['hit'] = (node,)

        async with self.getTestCore() as core:
            core.model.prop('test:str:hehe').onSet(test_cb)

            nodes = await core.nodes('[test:str=hi :hehe=haha]')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'hehe', 'haha')
            self.eq(node, arg_hit['hit'][0])

            arg_hit.clear()
            nodes = await core.nodes('test:str=hi [:hehe=weee]')
            self.len(1, nodes)
            node = nodes[0]

            self.propeq(node, 'hehe', 'weee')
            self.eq(node, arg_hit['hit'][0])

            arg_hit.clear()
            core.model.prop('test:str:hehe').onDel(test_cb)

            nodes = await core.nodes('test:str=hi [-:hehe]')
            self.len(1, nodes)
            node = nodes[0]
            self.none(node.get('hehe'))
            self.eq(node, arg_hit['hit'][0])

    async def test_storm_logging(self):
        async with self.getTestCoreAndProxy() as (realcore, core):
            view = await core.callStorm('return( $lib.view.get().iden )')
            self.nn(view)

            # Storm logging
            with self.getLoggerStream('synapse.storm') as stream:
                await alist(core.storm('help ask'))
                await stream.expect('Executing storm query {help ask} as [root]', timeout=4)

            mesg = 'Executing storm query {help foo} as [root]'
            with self.getLoggerStream('synapse.storm') as stream:
                await alist(core.storm('help foo', opts={'show': ('init', 'fini', 'print',)}))
                await stream.expect(mesg, timeout=4)

            mesg = stream.jsonlines()[0]
            self.eq(mesg['params'].get('view'), view)
            self.eq(mesg['params'].get('text'), 'help foo')
            self.eq(mesg['username'], 'root')

            udef = await core.addUser('foouser', )
            await core.setUserAdmin(udef.get('iden'), True)
            asfoo = {'user': udef.get('iden')}

            with self.getLoggerStream('synapse.storm') as stream:
                await alist(core.storm('help ask', opts=asfoo))

            mesg = stream.jsonlines()[0]
            self.eq(mesg['params'].get('view'), view)
            self.eq(mesg['params'].get('text'), 'help ask')
            self.eq(mesg['username'], 'foouser')

            q = '[test:str=hehe] [test:int=$node.value]'
            with self.getLoggerStream('synapse.lib.view') as stream:
                await alist(core.storm(q, opts=asfoo))
            msgs = stream.jsonlines()
            emsg = [m for m in msgs if 'Error during storm execution' in m.get('message')][0]
            self.eq(emsg['params'].get('view'), view)
            self.eq(emsg['params'].get('text'), q)
            self.eq(emsg['username'], 'foouser')

    async def test_storm_mustquote(self):

        async with self.getTestCore() as core:
            await core.nodes('[ inet:ip=1.2.3.4 ]')
            self.len(1, await core.nodes('inet:ip=1.2.3.4|limit 20'))

    async def test_storm_cmdname(self):

        class Bork:
            name = 'foo:bar'

        class Bawk:
            name = '.foobar'

        async with self.getTestCore() as core:

            with self.raises(s_exc.BadCmdName):
                core.addStormCmd(Bork)

            with self.raises(s_exc.BadCmdName):
                core.addStormCmd(Bawk)

    async def test_storm_comment(self):

        async with self.getTestCore() as core:

            text = '''
            /* A
               multiline
               comment */
            [ inet:ip=1.2.3.4 ] // this is a comment
            // and this too...

            switch $foo {

                // The bar case...

                bar: {
                    [ +#hehe.haha ]
                }

                /*
                   The
                   baz
                   case
                */
                'baz faz': {}
            }
            '''
            opts = {'vars': {'foo': 'bar'}}
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ip', (4, 0x01020304)))
            self.nn(nodes[0].getTag('hehe.haha'))

    async def test_storm_contbreak(self):

        async with self.getTestCore() as core:

            text = '''
            for $foo in $foos {

                [ inet:ip=1.2.3.4 ]

                switch $foo {
                    bar: { [ +#ohai ] break }
                    baz: { [ +#visi ] continue }
                }

                [ inet:ip=5.6.7.8 ]

                [ +#hehe ]
            }
            '''
            opts = {'vars': {'foos': ['baz', 'baz']}}
            await core.nodes(text, opts=opts)

            nodes = await core.nodes('inet:ip')
            self.len(1, nodes)
            self.nn(nodes[0].getTag('visi'))
            self.none(nodes[0].getTag('hehe'))

            await core.nodes('inet:ip | delnode')

            opts = {'vars': {'foos': ['bar', 'bar']}}
            await core.nodes(text, opts=opts)

            nodes = await core.nodes('inet:ip')
            self.len(1, nodes)
            self.nn(nodes[0].getTag('ohai'))
            self.none(nodes[0].getTag('hehe'))

            await core.nodes('inet:ip | delnode')

            opts = {'vars': {'foos': ['lols', 'lulz']}}
            await core.nodes(text, opts=opts)

            nodes = await core.nodes('inet:ip')
            for node in nodes:
                self.nn(node.getTag('hehe'))

            # Break and Continue cannot cross function boundaries and will instead raise a catchable StormRuntimeError
            keywords = ('break', 'continue')
            base_func_q = '''
            function inner(v) {
                if ( $v = 2 ) {
                    KEYWORD
                }
                return ( $v )
            }
            $N = (5)

            for $valu in $lib.range($N) {
                $lib.print(`{$inner($valu)}/{$N}`)
            }
            '''
            func_catch_q = '''
            function inner(v) {
                if ( $v = 2 ) {
                    KEYWORD
                }
                return ( $v )
            }
            $N = (5)
            try {
                for $valu in $lib.range($N) {
                    $lib.print(`{$inner($valu)}/{$N}`)
                }
            } catch StormRuntimeError as err {
                $lib.print(`caught: {$err.mesg}`)
            }
            '''
            for keyword in keywords:
                q = base_func_q.replace('KEYWORD', keyword)
                msgs = await core.stormlist(q)
                self.stormIsInPrint('1/5', msgs)
                self.stormNotInPrint('2/5', msgs)
                self.stormIsInErr(f'function inner - Loop control statement "{keyword}" used outside of a loop.',
                                  msgs)

                q = func_catch_q.replace('KEYWORD', keyword)
                msgs = await core.stormlist(q)
                self.stormIsInPrint('1/5', msgs)
                self.stormNotInPrint('2/5', msgs)
                self.stormIsInPrint(f'function inner - Loop control statement "{keyword}" used outside of a loop.',
                                    msgs)

            # The toplevel use of the keywords will convert them into StormRuntimeError in the message stream
            # but prevent them from being caught.
            base_top_q = '''
            $N = (5)
            for $j in $lib.range($N) {
                if ($j = 2) { break }
                $lib.print(`{$j}/{$N}`)
            }
            if ($j = 2) {
                KEYWORD
            }
            '''
            top_catch_q = '''
            $N = (5)
            for $j in $lib.range($N) {
                if ($j = 2) { break }
                $lib.print(`{$j}/{$N}`)
            }
            try {
                if ($j = 2) {
                    KEYWORD
                }
            } catch StormRuntimeError as err {
                $lib.print(`caught: {$err.mesg}`)
            }
            '''
            for keyword in keywords:
                q = base_top_q.replace('KEYWORD', keyword)
                msgs = await core.stormlist(q)
                self.stormIsInPrint('1/5', msgs)
                self.stormNotInPrint('2/5', msgs)
                self.stormIsInErr(f'Loop control statement "{keyword}" used outside of a loop.',
                                  msgs)
                errname = [m[1][0] for m in msgs if m[0] == 'err'][0]
                self.eq(errname, 'StormRuntimeError')

                q = top_catch_q.replace('KEYWORD', keyword)
                msgs = await core.stormlist(q)
                self.stormIsInPrint('1/5', msgs)
                self.stormNotInPrint('2/5', msgs)
                self.stormIsInErr(f'Loop control statement "{keyword}" used outside of a loop.',
                                    msgs)
                errname = [m[1][0] for m in msgs if m[0] == 'err'][0]
                self.eq(errname, 'StormRuntimeError')

    async def test_storm_varcall(self):

        async with self.getTestCore() as core:

            text = '''
            for $foo in $foos {

                ($fqdn, $ip) = $foo.split("|")

                [ inet:dns:a=($fqdn, $ip) ]
            }
            '''
            opts = {'vars': {'foos': ['vertex.link|1.2.3.4']}}
            await core.nodes(text, opts=opts)
            self.len(1, await core.nodes('inet:dns:a=(vertex.link,1.2.3.4)'))

    async def test_storm_dict_deref(self):

        async with self.getTestCore() as core:

            text = '''
            [ test:int=$hehe.haha ]
            '''
            opts = {'vars': {'hehe': {'haha': 20}}}
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 20)

            text = '''
            $a=({'foo': 'bar'})
            $b=({'baz': 'foo'})
            [ test:str=$a.`{$b.baz}` ]
            '''
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'bar')

            text = '''
            $a=({'foo': 'cool'})
            $b=({'baz': 'foo'})
            [ test:str=$a.($b.baz) ]
            '''
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'cool')

            text = '''
            $foo = ({})
            $bar=({'baz': 'buzz'})
            $foo.`{$bar.baz}` = fuzz
            [ test:str=$foo.buzz ]
            '''
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'fuzz')

            text = '''
            $foo = ({})
            $bar=({'baz': 'fuzz'})
            $foo.($bar.baz) = buzz
            [ test:str=$foo.fuzz ]
            '''
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'buzz')

            self.eq('BAZ', await core.callStorm("$foo=({'bar': 'baz'}) return($foo.('bar').upper())"))
            self.eq('BAZ', await core.callStorm("$foo=({'bar': 'baz'}) return($foo.$('bar').upper())"))
            self.eq('BAZ', await core.callStorm("return(({'bar': 'baz'}).('bar').upper())"))
            self.eq('BAZ', await core.callStorm("return(({'bar': 'baz'}).$('bar').upper())"))
            self.eq('BAZ', await core.callStorm("return((({'bar': 'baz'}).('bar').upper()))"))
            self.eq('BAZ', await core.callStorm("return((({'bar': 'baz'}).$('bar').upper()))"))

            # setitem and deref both toprim the key
            text = '''
            $x = ({})
            $y = (1.23)
            $x.$y = "foo"
            for ($k, $v) in $x { return(($k, $x.$k)) }
            '''
            self.eq((1.23, 'foo'), await core.callStorm(text))

            # constructor also toprims all keys
            text = '''
            $y = (1.23)
            $x = ({
                $y: "foo"
            })
            for ($k, $v) in $x { return(($k, $x.$k)) }
            '''
            self.eq((1.23, 'foo'), await core.callStorm(text))

            text = '''
            $y=(null) [ inet:fqdn=foo.com ] $y=$node spin |
            $x = ({
                "cool": {
                    $y: "foo"
                }
            })
            for ($k, $v) in $x {
                for ($k2, $v2) in $v {
                    return(($k2, $x.$k.$k2))
                }
            }
            '''
            self.eq(('foo.com', 'foo'), await core.callStorm(text))

            # using a mutable key raises an exception
            text = '''
            $x = ({})
            $y = ([(1.23)])
            $x.$y = "foo"
            '''
            await self.asyncraises(s_exc.BadArg, core.nodes(text))

            text = '''
            $y = ([(1.23)])
            $x = ({
                $y: "foo"
            })
            '''
            await self.asyncraises(s_exc.BadArg, core.nodes(text))

    async def test_storm_varlist_compute(self):

        async with self.getTestCore() as core:

            text = '''
                [ test:str=foo :seen=(2014,2015) ]
                ($tick, $tock) = :seen
                [ test:int=$tick ]
                +test:int
            '''
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 1388534400000000)

    async def test_storm_selfrefs(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:fqdn=woot.com ] -> *')

            self.len(1, nodes)
            self.eq('com', nodes[0].ndef[1])

            await core.nodes('inet:fqdn=woot.com | delnode')

            self.len(0, await core.nodes('inet:fqdn=woot.com'))

    async def test_storm_addnode_runtsafe(self):

        async with self.getTestCore() as core:
            # test adding nodes from other nodes output
            q = '[ inet:fqdn=woot.com inet:fqdn=vertex.link ] [ it:dev:str = :zone ] +it:dev:str'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            ndefs = list(sorted([n.ndef for n in nodes]))
            self.eq(ndefs, (('it:dev:str', 'vertex.link'), ('it:dev:str', 'woot.com')))

    async def test_storm_subgraph(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:ip=1.2.3.4 :asn=20 ]')
            await core.nodes('[ inet:dns:a=(woot.com, 1.2.3.4) +#yepr ]')
            await core.nodes('[ inet:dns:a=(vertex.link, 5.5.5.5) +#nope ]')
            await core.nodes('[ inet:fqdn=vertex.link <(refs)+ {[ test:guid=cd5d6bff3fd78bbf1eee91afc80a50dd ]} ]')

            rules = {

                'degrees': 2,

                'pivots': [],

                'filters': ['-#nope'],

                'forms': {

                    'inet:fqdn': {
                        'pivots': ['<- *', '-> *'],
                        'filters': ['-inet:fqdn:issuffix=1'],
                    },

                    'syn:tag': {
                        'pivots': ['-> *'],
                    },

                    '*': {
                        'pivots': ['-> #'],
                    },

                }
            }

            def checkGraph(seeds, alldefs):
                # our TLDs should be omits
                self.len(2, seeds)
                self.len(5, alldefs)

                self.isin(('inet:fqdn', 'woot.com'), seeds)
                self.isin(('inet:fqdn', 'vertex.link'), seeds)

                self.nn(alldefs.get(('syn:tag', 'yepr')))
                self.nn(alldefs.get(('inet:dns:a', ('woot.com', (4, 0x01020304)))))

                self.none(alldefs.get(('inet:asn', 20)))
                self.none(alldefs.get(('syn:tag', 'nope')))
                self.none(alldefs.get(('inet:dns:a', ('vertex.link', (4, 0x05050505)))))

            seeds = []
            alldefs = {}

            async for node in core.view.iterStormPodes('inet:fqdn', opts={'graph': rules}):
                if node[1]['path'].get('graph:seed'):
                    seeds.append(node[0])

                alldefs[node[0]] = node[1]['path'].get('edges')

            checkGraph(seeds, alldefs)

            rules['name'] = 'foo'
            iden = await core.callStorm('return($lib.graph.add($rules).iden)', opts={'vars': {'rules': rules}})

            gdef = await core.addStormGraph(rules)
            iden2 = gdef['iden']

            mods = {
                'name': 'bar',
                'desc': 'foorules',
                'refs': True,
                'edges': False,
                'forms': {},
                'pivots': ['<(seen)- meta:source'],
                'degrees': 3,
                'filters': ['+#nope'],
                'filterinput': False,
                'yieldfiltered': True
            }

            await core.callStorm('$lib.graph.mod($iden, $info)', opts={'vars': {'iden': iden2, 'info': mods}})

            q = '$lib.graph.mod($iden, ({"iden": "foo"}))'
            await self.asyncraises(s_exc.BadArg, core.callStorm(q, opts={'vars': {'iden': iden2}}))

            gdef['scope'] = 'power-up'
            gdef['power-up'] = 'newp'
            await self.asyncraises(s_exc.SynErr, core._addStormGraph(gdef))

            gdef = await core.callStorm('return($lib.graph.get($iden))', opts={'vars': {'iden': iden}})
            self.eq(gdef['name'], 'foo')
            self.eq(gdef['creator'], core.auth.rootuser.iden)

            gdefs = await core.callStorm('return($lib.graph.list())')
            self.len(2, gdefs)
            self.eq(gdefs[0]['name'], 'bar')
            self.eq(gdefs[0]['creator'], core.auth.rootuser.iden)
            self.eq(gdefs[1]['name'], 'foo')
            self.eq(gdefs[1]['creator'], core.auth.rootuser.iden)

            seeds = []
            alldefs = {}
            async for node in core.view.iterStormPodes('inet:fqdn $lib.graph.activate($iden)', opts={'vars': {'iden': iden}}):

                if node[1]['path'].get('graph:seed'):
                    seeds.append(node[0])

                alldefs[node[0]] = node[1]['path'].get('edges')

            checkGraph(seeds, alldefs)

            seeds = []
            alldefs = {}
            async for node in core.view.iterStormPodes('inet:fqdn', opts={'graph': iden}):

                if node[1]['path'].get('graph:seed'):
                    seeds.append(node[0])

                alldefs[node[0]] = node[1]['path'].get('edges')

            checkGraph(seeds, alldefs)

            # now do the same options via the command...
            text = '''
                inet:fqdn | graph
                                --degrees 2
                                --filter { -#nope }
                                --pivot {}
                                --form-pivot inet:fqdn {<- * | limit 20}
                                --form-pivot inet:fqdn {-> * | limit 20}
                                --form-filter inet:fqdn {-inet:fqdn:issuffix=1}
                                --form-pivot syn:tag {-> *}
                                --form-pivot * {-> #}
            '''

            seeds = []
            alldefs = {}
            async for node in core.view.iterStormPodes(text):

                if node[1]['path'].get('graph:seed'):
                    seeds.append(node[0])

                alldefs[node[0]] = node[1]['path'].get('edges')

            checkGraph(seeds, alldefs)

            # filterinput=false behavior
            rules['filterinput'] = False
            seeds = []
            alldefs = {}
            async for node in core.view.iterStormPodes('inet:fqdn', opts={'graph': rules}):

                if node[1]['path'].get('graph:seed'):
                    seeds.append(node[0])

                alldefs[node[0]] = node[1]['path'].get('edges')

            # our TLDs are no longer omits
            self.len(4, seeds)
            self.len(7, alldefs)
            self.isin(('inet:fqdn', 'com'), seeds)
            self.isin(('inet:fqdn', 'link'), seeds)
            self.isin(('inet:fqdn', 'woot.com'), seeds)
            self.isin(('inet:fqdn', 'vertex.link'), seeds)

            # yieldfiltered = True
            rules.pop('filterinput', None)
            rules['yieldfiltered'] = True

            seeds = []
            alldefs = {}
            async for node in core.view.iterStormPodes('inet:fqdn', opts={'graph': rules}):

                if node[1]['path'].get('graph:seed'):
                    seeds.append(node[0])

                alldefs[node[0]] = node[1]['path'].get('edges')

            # The tlds are omitted, but since we are yieldfiltered=True,
            # we still get the seeds. We also get an inet:dns:a node we
            # previously omitted.
            self.len(4, seeds)
            self.len(8, alldefs)
            self.isin(('inet:dns:a', ('vertex.link', (4, 84215045))), alldefs)

            # refs
            rules = {
                'degrees': 2,
                'refs': True,
            }

            seeds = []
            alldefs = {}
            async for node in core.view.iterStormPodes('inet:dns:a:fqdn=woot.com', opts={'graph': rules}):

                if node[1]['path'].get('graph:seed'):
                    seeds.append(node[0])

                alldefs[node[0]] = node[1]['path'].get('edges')

            self.len(1, seeds)
            self.len(5, alldefs)
            # We did make it automatically away 2 degrees with just model refs
            self.eq({('inet:dns:a', ('woot.com', (4, 16909060))),
                     ('inet:fqdn', 'woot.com'),
                     ('inet:ip', (4, 16909060)),
                     ('inet:fqdn', 'com'),
                     ('inet:asn', 20)}, set(alldefs.keys()))

            # Construct a test that encounters nodes which are already
            # in the to-do queue. This is mainly a coverage test.
            q = '[inet:ip=([4, 0]) inet:ip=([4, 1]) inet:ip=([4, 2]) :asn=1138 +#deathstar]'
            await core.nodes(q)

            q = '#deathstar | graph --degrees 2'
            ndefs = set()
            async for node in core.view.iterStormPodes(q):
                ndefs.add(node[0])
            self.isin(('inet:asn', 1138), ndefs)

            # Runtsafety test
            q = '[ test:int=1 ]  | graph --degrees $node.value'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            opts = {'vars': {'iden': iden, 'iden2': iden2}}
            q = '''
            function acti() {
                $lib.graph.activate($iden)
                return($lib.graph.get())
            }
            return($acti().iden)'''

            self.eq(iden, await core.callStorm(q, opts=opts))
            self.none(await core.callStorm('return($lib.graph.get())'))

            otherpkg = {
                'name': 'graph.powerup',
                'version': '0.0.1',
                'graphs': [{'name': 'testgraph'}]
            }
            await core.addStormPkg(otherpkg)

            visi = await core.auth.addUser('visi')
            uopts = dict(opts)
            uopts['user'] = visi.iden
            opts['vars']['useriden'] = visi.iden

            await self.asyncraises(s_exc.AuthDeny, core.nodes('$lib.graph.del($iden2)', opts=uopts))
            await core.nodes('$lib.graph.grant($iden2, users, $useriden, 3)', opts=opts)

            await core.nodes('$lib.graph.mod($iden2, ({"name": "newname"}))', opts=uopts)
            gdef = await core.callStorm('return($lib.graph.get($iden2))', opts=opts)
            self.eq(gdef['name'], 'newname')

            await core.nodes('$lib.graph.revoke($iden2, users, $useriden)', opts=opts)
            await self.asyncraises(s_exc.AuthDeny, core.nodes('$lib.graph.mod($iden2, ({"name": "newp"}))', opts=uopts))

            await core.nodes('$lib.graph.grant($iden2, users, $useriden, 3)', opts=opts)
            await core.nodes('$lib.graph.del($iden2)', opts=uopts)

            self.len(2, await core.callStorm('return($lib.graph.list())', opts=opts))

            q = '$lib.graph.del($lib.guid(graph.powerup, testgraph))'
            await self.asyncraises(s_exc.AuthDeny, core.nodes(q))

            await core.callStorm('pkg.del graph.powerup')
            await core.callStorm('return($lib.graph.del($iden))', opts={'vars': {'iden': iden}})

            gdefs = await core.callStorm('return($lib.graph.list())')
            self.len(0, gdefs)

            await self.asyncraises(s_exc.NoSuchIden, core.nodes('$lib.graph.del(foo)'))
            await self.asyncraises(s_exc.NoSuchIden, core.nodes('$lib.graph.get(foo)'))
            await self.asyncraises(s_exc.NoSuchIden, core.nodes('$lib.graph.activate(foo)'))
            await self.asyncraises(s_exc.NoSuchIden, core.delStormGraph('foo'))

            q = '$lib.graph.add(({"name": "foo", "forms": {"newp": {}}}))'
            await self.asyncraises(s_exc.NoSuchForm, core.nodes(q))

            # default to full pivots including
            rules = {
                'refs': True,
                'edges': True,
                'degrees': 1,
            }
            msgs = await core.stormlist('inet:fqdn=vertex.link', opts={'graph': rules})

            nodes = {m[1][0]: m[1] for m in msgs if m[0] == 'node'}
            self.len(2, nodes)

            props = set()
            for edge in nodes[('inet:fqdn', 'link')][1]['path']['edges']:
                if edge[1].get('type') == 'prop':
                    props.add(edge[1].get('prop'))

            self.isin('domain', props)

            # include a light edge
            rules = {
                'refs': True,
                'edges': True,
                'degrees': 1,
                'forms': {
                    'inet:fqdn': {
                        'pivots': ['<(*)- *']
                    }
                }
            }

            msgs = await core.stormlist('inet:fqdn=vertex.link', opts={'graph': rules})

            nodes = {m[1][0]: m[1] for m in msgs if m[0] == 'node'}
            self.len(3, nodes)

            edgeinfo = nodes[('test:guid', 'cd5d6bff3fd78bbf1eee91afc80a50dd')][1]['path']['edges'][1][1]
            self.eq({'type': 'edge', 'verb': 'refs'}, edgeinfo)

            iden = await core.callStorm('''
                $rules = ({
                    "name": "graph proj",
                    "forms": {
                        "biz:deal": {
                            "pivots": [" --> *", " <-- *"],
                        },
                        "pol:country": {
                            "pivots": ["--> *", "<-- *"],
                            "filters": ["-file:bytes"]
                        },
                        "*": {
                            "pivots": ["-> #"]
                        }
                    },
                })
                return($lib.graph.add($rules).iden)
            ''')

            guids = {
                'race': 'cdd9e140d78830fb46d880dd36b62961',
                'biz': 'c5352253cb13545205664e088ad210f0',
                'orgA': '2e5dcdb52552ca22fa7996158588ea01',
                'orgB': '9ea20ce1375d0ff0d16acfe807289a95',
                'pol': '111e3b57f9bbf973febe74b1e98e89f8'
            }

            await core.callStorm('''[
                (pol:country=$pol
                    :name="some government"
                    :flag={[ file:bytes=({"sha256": "fd0a257397ee841ccd3b6ba76ad59c70310fd402ea3c9392d363f754ddaa67b5"}) ]}
                    <(refs)+ { [ pol:race=$race ] }
                    +#some.stuff)
                (ou:org=$orgA
                   :email=foo@bar.com)
                (ou:org=$orgB
                   :email=neato@burrito.org
                   +#rep.stuff)
                (biz:deal=$biz
                    :buyer={[ ou:org=$orgA ]}
                    :seller={[ ou:org=$orgB ]}
                    <(refs)+ { pol:country=$pol })
            ]''', opts={'vars': guids})

            nodes = await core.nodes('biz:deal | $lib.graph.activate($iden)', opts={'vars': {'iden': iden}})
            self.len(4, nodes)
            ndefs = set([n.ndef for n in nodes])
            self.eq(ndefs, set([
                ('biz:deal', guids['biz']),
                ('ou:org', guids['orgA']),
                ('ou:org', guids['orgB']),
                ('pol:country', guids['pol']),
            ]))

        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                visi = await core.auth.addUser('visi')
                opts = {'user': visi.iden}

                await core.addStormPkg(otherpkg)
                await core.nodes('$lib.graph.add(({"name": "foo"}))', opts=opts)
                await core.nodes('$lib.graph.add(({"name": "bar"}))')
                self.len(3, await core.callStorm('return($lib.graph.list())', opts=opts))

            async with self.getTestCore(dirn=dirn) as core:
                self.len(3, await core.callStorm('return($lib.graph.list())', opts=opts))

                gdef = await core.callStorm('return($lib.graph.add(({"name": "nodef"})))')
                self.eq(1, gdef['permissions']['default'])

                gdef = await core.callStorm('return($lib.graph.add(({"name": "def", "permissions": {"default": 0}})))')
                self.eq(0, gdef['permissions']['default'])

    async def test_graph_projection_query_validation(self):
        async with self.getTestCore() as core:
            valid = {
                'name': 'valid',
                'forms': {
                    'inet:fqdn': {
                        'pivots': ['<- *'],
                        'filters': []
                    }
                }
            }

            self.nn(await core.addStormGraph(valid))

            bad_form_pivot = {
                'name': 'bad form pivot',
                'forms': {
                    'inet:fqdn': {
                        'pivots': ['<- * |||'],
                        'filters': []
                    }
                }
            }

            await self.asyncraises(s_exc.BadSyntax, core.addStormGraph(bad_form_pivot))

            bad_form_filter = {
                'name': 'bad form filter',
                'forms': {
                    'inet:fqdn': {
                        'pivots': [],
                        'filters': ['+++:wat']
                    }
                }
            }

            await self.asyncraises(s_exc.BadSyntax, core.addStormGraph(bad_form_filter))

            bad_global_filter = {
                'name': 'bad global filter',
                'filters': ['+++:wat']
            }

            await self.asyncraises(s_exc.BadSyntax, core.addStormGraph(bad_global_filter))

            bad_global_pivot = {
                'name': 'bad global pivot',
                'pivots': ['-> * |||']
            }

            await self.asyncraises(s_exc.BadSyntax, core.addStormGraph(bad_global_pivot))

    async def test_storm_two_level_assignment(self):
        async with self.getTestCore() as core:
            q = '$foo=baz $bar=$foo [test:str=$bar]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('baz', nodes[0].ndef[1])

    async def test_storm_quoted_variables(self):
        async with self.getTestCore() as core:
            q = '$"my var"=baz $bar=$"my var" [test:str=$bar]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('baz', nodes[0].ndef[1])

            q = '$d = ({"field 1": "foo", "field 2": "bar"}) [test:str=$d.\'field 1\']'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('foo', nodes[0].ndef[1])

            q = '($"a", $"#", $c) = (1, 2, 3) [test:str=$"#"]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('2', nodes[0].ndef[1])

    async def test_storm_type_node(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ test:int=1234 ] [test:str=$node.value] -test:int')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', '1234'))

            nodes = await core.nodes('test:int=1234 [test:str=$node.form] -test:int')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'test:int'))

    async def test_storm_subq_size(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:dns:a=(woot.com, 1.2.3.4) inet:dns:a=(vertex.link, 1.2.3.4) ]')

            self.len(0, await core.nodes('inet:ip=1.2.3.4 +( { -> inet:dns:a }=0 )'))

            self.len(1, await core.nodes('inet:ip=1.2.3.4 +( { -> inet:dns:a }=2 )'))
            self.len(0, await core.nodes('inet:ip=1.2.3.4 +( { -> inet:dns:a }=3 )'))

            self.len(0, await core.nodes('inet:ip=1.2.3.4 +( { -> inet:dns:a }!=2 )'))
            self.len(1, await core.nodes('inet:ip=1.2.3.4 +( { -> inet:dns:a }!=3 )'))

            self.len(1, await core.nodes('inet:ip=1.2.3.4 +( { -> inet:dns:a }>=1 )'))
            self.len(1, await core.nodes('inet:ip=1.2.3.4 +( { -> inet:dns:a }>=2 )'))
            self.len(0, await core.nodes('inet:ip=1.2.3.4 +( { -> inet:dns:a }>=3 )'))

            self.len(0, await core.nodes('inet:ip=1.2.3.4 +( { -> inet:dns:a }<=1 )'))
            self.len(1, await core.nodes('inet:ip=1.2.3.4 +( { -> inet:dns:a }<=2 )'))
            self.len(1, await core.nodes('inet:ip=1.2.3.4 +( { -> inet:dns:a }<=3 )'))

            self.len(0, await core.nodes('inet:ip=1.2.3.4 +{ -> inet:dns:a } < 2 '))
            self.len(1, await core.nodes('inet:ip=1.2.3.4 +{ -> inet:dns:a } < 3 '))

            self.len(1, await core.nodes('inet:ip=1.2.3.4 +{ -> inet:dns:a } > 1 '))
            self.len(0, await core.nodes('inet:ip=1.2.3.4 +{ -> inet:dns:a } > 2 '))

            with self.raises(s_exc.NoSuchCmpr) as cm:
                await core.nodes('inet:ip=1.2.3.4 +{ -> inet:dns:a } @ 2')

            await core.nodes('[ risk:attack=* +(used)> {[ it:dev:str=foo ]} ]')
            await core.nodes('[ risk:attack=* +(used)> {[ it:dev:str=bar ]} ]')

            q = 'risk:attack +{ -(used)> * $valu=$node.value } $lib.print($valu)'
            msgs = await core.stormlist(q)
            self.sorteq([m[1]['mesg'] for m in msgs if m[0] == 'print'], ['foo', 'bar'])

            q = 'risk:attack +{ -(used)> * $valu=$node.value } = 1 $lib.print($valu)'
            msgs = await core.stormlist(q)
            self.sorteq([m[1]['mesg'] for m in msgs if m[0] == 'print'], ['foo', 'bar'])

            q = 'risk:attack -{ -(used)> * $valu=$node.value } = 2 $lib.print($valu)'
            msgs = await core.stormlist(q)
            self.sorteq([m[1]['mesg'] for m in msgs if m[0] == 'print'], ['foo', 'bar'])

            q = 'risk:attack +{ -(used)> * $valu=$node.value } > 0 $lib.print($valu)'
            msgs = await core.stormlist(q)
            self.sorteq([m[1]['mesg'] for m in msgs if m[0] == 'print'], ['foo', 'bar'])

            q = 'risk:attack -{ -(used)> * $valu=$node.value } > 1 $lib.print($valu)'
            msgs = await core.stormlist(q)
            self.sorteq([m[1]['mesg'] for m in msgs if m[0] == 'print'], ['foo', 'bar'])

            q = 'risk:attack +{ -(used)> * $valu=$node.value } >= 1 $lib.print($valu)'
            msgs = await core.stormlist(q)
            self.sorteq([m[1]['mesg'] for m in msgs if m[0] == 'print'], ['foo', 'bar'])

            q = 'risk:attack -{ -(used)> * $valu=$node.value } >= 2 $lib.print($valu)'
            msgs = await core.stormlist(q)
            self.sorteq([m[1]['mesg'] for m in msgs if m[0] == 'print'], ['foo', 'bar'])

            q = 'risk:attack +{ -(used)> * $valu=$node.value } < 2 $lib.print($valu)'
            msgs = await core.stormlist(q)
            self.sorteq([m[1]['mesg'] for m in msgs if m[0] == 'print'], ['foo', 'bar'])

            q = 'risk:attack -{ -(used)> * $valu=$node.value } < 1 $lib.print($valu)'
            msgs = await core.stormlist(q)
            self.sorteq([m[1]['mesg'] for m in msgs if m[0] == 'print'], ['foo', 'bar'])

            q = 'risk:attack +{ -(used)> * $valu=$node.value } <= 1 $lib.print($valu)'
            msgs = await core.stormlist(q)
            self.sorteq([m[1]['mesg'] for m in msgs if m[0] == 'print'], ['foo', 'bar'])

            q = 'risk:attack -{ -(used)> * $valu=$node.value } <= 0 $lib.print($valu)'
            msgs = await core.stormlist(q)
            self.sorteq([m[1]['mesg'] for m in msgs if m[0] == 'print'], ['foo', 'bar'])

            q = 'risk:attack +{ -(used)> * $valu=$node.value } != 0 $lib.print($valu)'
            msgs = await core.stormlist(q)
            self.sorteq([m[1]['mesg'] for m in msgs if m[0] == 'print'], ['foo', 'bar'])

            q = 'risk:attack -{ -(used)> * $valu=$node.value } != 1 $lib.print($valu)'
            msgs = await core.stormlist(q)
            self.sorteq([m[1]['mesg'] for m in msgs if m[0] == 'print'], ['foo', 'bar'])

    async def test_cortex_in(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[test:str=a test:str=b test:str=c]')
            self.len(3, nodes)

            self.len(0, await core.nodes('test:str*in=()'))
            self.len(0, await core.nodes('test:str*in=(d,)'))
            self.len(2, await core.nodes('test:str*in=(a, c)'))
            self.len(1, await core.nodes('test:str*in=(a, d)'))
            self.len(3, await core.nodes('test:str*in=(a, b, c)'))

            self.len(0, await core.nodes('test:str +test:str*in=()'))
            self.len(0, await core.nodes('test:str +test:str*in=(d,)'))
            self.len(2, await core.nodes('test:str +test:str*in=(a, c)'))
            self.len(1, await core.nodes('test:str +test:str*in=(a, d)'))
            self.len(3, await core.nodes('test:str +test:str*in=(a, b, c)'))

    async def test_cortex_view_invalid(self):

        async with self.getTestCore() as core:

            core.view.invalid = s_common.guid()
            with self.raises(s_exc.NoSuchLayer):
                await core.nodes('[ test:str=foo ]')

            core.view.invalid = None
            self.len(1, await core.nodes('[ test:str=foo ]'))

    async def test_tag_globbing(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[(test:str=n1 +#foo.bar.baz)] [(test:str=n2 +#foo.bad.baz)] [test:str=n3]')
            self.len(3, nodes)

            # Setup worked correct
            self.len(3, await core.nodes('test:str'))
            self.len(2, await core.nodes('test:str +#foo'))

            # Now test globbing - exact match for *
            self.len(2, await core.nodes('test:str +#*'))
            self.len(1, await core.nodes('test:str -#*'))

            # Now test globbing - single star matches one tag level
            self.len(2, await core.nodes('test:str +#foo.*.baz'))
            self.len(1, await core.nodes('test:str +#*.bad'))
            self.len(2, await core.nodes('test:str +#foo*'))
            self.len(1, await core.nodes('test:str +#foo.bar.baz*'))
            # Double stars matches a whole lot more!
            self.len(2, await core.nodes('test:str +#foo.**.baz'))
            self.len(1, await core.nodes('test:str +#**.bar.baz'))
            self.len(2, await core.nodes('test:str +#**.baz'))
            self.len(1, await core.nodes('test:str +#foo.bar.baz**'))

    async def test_storm_lift_compute(self):
        async with self.getTestCore() as core:
            self.len(2, await core.nodes('[ inet:dns:a=(vertex.link,1.2.3.4) inet:dns:a=(woot.com,5.6.7.8)]'))
            self.len(4, await core.nodes('inet:dns:a inet:fqdn=:fqdn'))

    async def test_cortex_delnode_perms(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')

            await visi.addRule((True, ('node', 'add')))
            await visi.addRule((True, ('node', 'prop', 'set')))
            await visi.addRule((True, ('node', 'tag', 'add')))

            opts = {'user': visi.iden}

            await core.nodes('[ test:cycle0=foo :cycle1=bar ]', opts=opts)
            await core.nodes('[ test:cycle1=bar :cycle0=foo ]', opts=opts)

            await core.nodes('[ test:str=foo +#lol ]', opts=opts)

            # no perms and not elevated...
            with self.raises(s_exc.AuthDeny):
                await core.nodes('test:str=foo | delnode', opts=opts)

            await visi.addRule((True, ('node', 'del')))

            self.len(0, await core.nodes('test:str=foo | delnode', opts=opts))

            with self.raises(s_exc.CantDelNode):
                await core.nodes('test:cycle0=foo | delnode', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('test:cycle0=foo | delnode --force', opts=opts)

            await visi.setAdmin(True)

            self.len(0, await core.nodes('test:cycle0=foo | delnode --force', opts=opts))

    async def test_node_repr(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[inet:ip=$valu]', opts={'vars': {'valu': (4, 0x01020304)}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq('1.2.3.4', node.repr())

            nodes = await core.nodes('[inet:dns:a=(woot.com, 1.2.3.4)]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq('1.2.3.4', node.repr('ip'))

    async def test_cortex_storm_vars(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'foo': '1.2.3.4'}}

            self.len(1, await core.nodes('[ inet:ip=$foo ]', opts=opts))
            self.len(1, await core.nodes('$bar=5.5.5.5 [ inet:ip=$bar ]'))

            self.len(1, await core.nodes('[ inet:dns:a=(woot.com,1.2.3.4) ]'))

            self.len(2, await core.nodes('inet:dns:a=(woot.com,1.2.3.4) $hehe=:fqdn inet:fqdn=$hehe'))

            self.len(1, await core.nodes('inet:dns:a=(woot.com,1.2.3.4) $hehe=:fqdn +:fqdn=$hehe'))
            self.len(0, await core.nodes('inet:dns:a=(woot.com,1.2.3.4) $hehe=:fqdn -:fqdn=$hehe'))

            self.len(1, await core.nodes('[ test:pivcomp=(hehe,haha) :tick=2015 +#foo=(2014,2016) ]'))
            self.len(1, await core.nodes('test:pivtarg=hehe [ :seen=2015 ]'))

            self.len(1, await core.nodes('test:pivcomp=(hehe,haha) $ticktock=#foo -> test:pivtarg +:seen@=$ticktock'))

            self.len(1, await core.nodes('test:pivcomp=(hehe,haha) [ :seen=(2015,2018) ]'))

            nodes = await core.nodes('test:pivcomp=(hehe,haha) $seen=:seen :targ -> test:pivtarg [ :seen=$seen ]')
            self.len(1, nodes)
            node = nodes[0]
            self.propeq(node, 'seen', (1420070400000000, 1514764800000000, 94694400000000))

            with self.raises(s_exc.NoSuchProp):
                await core.nodes('inet:dns:a=(woot.com,1.2.3.4) $newp=:newp')

            # Vars can also be provided as tuple
            opts = {'vars': {'foo': ('hehe', 'haha')}}
            self.len(1, await core.nodes('test:pivcomp=$foo', opts=opts))

            # Vars can also be provided as integers
            norm = (await core.model.type('time').norm('2015'))[0]
            opts = {'vars': {'foo': norm}}
            self.len(1, await core.nodes('test:pivcomp:tick=$foo', opts=opts))

    async def test_cortex_nexslogen_off(self):
        '''
        Everything still works when no nexus log is kept
        '''
        conf = {'nexslog:en': False}
        async with self.getTestCore(conf=conf) as core:
            self.len(2, await core.nodes('[test:str=foo test:str=bar]'))
            self.len(2, await core.nodes('test:str'))

    async def test_feed_syn_nodes(self):

        async with self.getTestCore() as core0:

            await core0._addModelDefs(s_t_utils.deprmodel)

            podes = []

            node1 = (await core0.nodes('[ test:int=1 ]'))[0]
            await node1.setData('foo', 'bar')
            pack = node1.pack()
            pack[1]['nodedata'] = {'foo': 'bar'}
            pack[1]['edges'] = (('refs', ('inet:ip', '1.2.3.4')),
                                ('newp', ('test:newp', 'newp')),
                                ('newp', ('test:int', 'newp')))
            podes.append(pack)

            node2 = (await core0.nodes('[ test:int=2 ] | [ +(refs)> { test:int=1 } ]'))[0]
            pack = node2.pack()
            pack[1]['edges'] = (('refs', node1.ndef), )
            podes.append(pack)

            node3 = (await core0.nodes('[ test:int=3 ]'))[0]
            podes.append(node3.pack())

            node = (await core0.nodes('[ test:int=4 ]'))[0]
            pack = node.pack()
            pack[1]['edges'] = [('refs', ('inet:ip', f'{y}')) for y in range(500)]
            podes.append(pack)

        async with self.getTestCore() as core1:

            await core1._addModelDefs(s_t_utils.deprmodel)

            await core1.addFeedData(podes)
            self.len(4, await core1.nodes('test:int'))
            self.len(1, await core1.nodes('test:int=1 -(refs)> inet:ip +inet:ip=1.2.3.4'))
            self.len(0, await core1.nodes('test:int=1 -(newp)> *'))

            node1 = (await core1.nodes('test:int=1'))[0]
            self.eq('bar', await node1.getData('foo'))
            self.len(1, await core1.nodes('test:int=2 -(refs)> *'))

            await core1.addTagProp('_test', ('int', {}), {})

            msgs = await core1.stormlist('test:int=1 [+#beep.beep:_test=1138]')
            self.stormHasNoWarnErr(msgs)
            pode = [m[1] for m in msgs if m[0] == 'node'][0]
            pode = (('test:int', 4), pode[1])

            await core1.addFeedData([pode])
            nodes = await core1.nodes('test:int=4')
            self.eq(1138, nodes[0].getTagProp('beep.beep', '_test'))

            # Put bad data in
            data = [(('test:str', 'newp'), {'tags': {'test.newp': 'newp'}})]
            await core1.addFeedData(data)
            self.len(1, await core1.nodes('test:str=newp -#test.newp'))

            data = [(('test:str', 'opps'), {'tagprops': {'test.newp': {'newp': 'newp'}}})]
            await core1.addFeedData(data)
            self.len(1, await core1.nodes('test:str=opps +#test.newp'))

            data = [(('test:str', 'ahh'), {'nodedata': 123})]
            await core1.addFeedData(data)
            nodes = await core1.nodes('test:str=ahh')
            self.len(1, nodes)
            await self.agenlen(0, nodes[0].iterData())

            data = [(('test:str', 'baddata'), {'nodedata': {123: 'newp',
                                                            'newp': b'123'}})]
            await core1.addFeedData(data)
            nodes = await core1.nodes('test:str=baddata')
            self.len(1, nodes)
            await self.agenlen(0, nodes[0].iterData())

            data = [(('test:str', 'beef'), {'edges': [('badverb', {})]})]
            await core1.addFeedData(data)
            nodes = await core1.nodes('test:str=beef')
            self.len(1, nodes)
            await self.agenlen(0, nodes[0].iterEdgesN1())

            data = [(('test:str', 'fake'), {'edges': [('newp', s_common.ehex(s_common.buid('fake')))]})]
            await core1.addFeedData(data)
            nodes = await core1.nodes('test:str=fake')
            self.len(1, nodes)
            await self.agenlen(0, nodes[0].iterEdgesN1())

            data = [(('syn:cmd', 'newp'), {})]
            await core1.addFeedData(data)
            self.len(0, await core1.nodes('syn:cmd=newp'))

            data = [(('test:str', 'beef'), {'edges': [('newp', ('syn:form', 'newp'))]})]
            await core1.addFeedData(data)
            nodes = await core1.nodes('test:str=beef')
            self.len(1, nodes)
            await self.agenlen(0, nodes[0].iterEdgesN1())

            # Feed into a forked view
            vdef2 = await core1.view.fork()
            view2_iden = vdef2.get('iden')

            data = [(('test:int', 1), {'tags': {'noprop': [None, None, None]},
                                       'tagprops': {'noprop': {'_test': 'newp'}}})]
            await core1.addFeedData(data, viewiden=view2_iden)
            self.len(1, await core1.nodes('test:int=1 +#noprop', opts={'view': view2_iden}))

            data = [(('test:int', 1), {'tags': {'noprop': (None, None, None),
                                                'noprop.two': (None, None, None)},
                                       'tagprops': {'noprop': {'_test': 1}}})]
            await core1.addFeedData(data, viewiden=view2_iden)
            nodes = await core1.nodes('test:int=1 +#noprop.two', opts={'view': view2_iden})
            self.len(1, nodes)
            self.eq(1, nodes[0].getTagProp('noprop', '_test'))

            # Test a bulk add
            tags = {'tags': {'test': (2020, 2022)}}
            data = [(('test:int', x), tags) for x in range(2001)]
            await core1.addFeedData(data)
            nodes = await core1.nodes('test:int#test')
            self.len(2001, nodes)

            await core1.nodes('movetag test newtag')

            data = [(('test:int', 1), {'props': {'int2': ('int', 2)},
                                       'tags': {'test': [2020, 2021]},
                                       'tagprops': {'noprop': {'_test': 1}}})]
            await core1.addFeedData(data, viewiden=view2_iden)
            nodes = await core1.nodes('test:int=1 +#newtag', opts={'view': view2_iden})
            self.len(1, nodes)
            self.propeq(nodes[0], 'int2', 2)
            self.eq(1, nodes[0].getTagProp('noprop', '_test'))

            data = [(('test:int', 1), {'tags': {'test': (2020, 2022)}})]
            await core1.addFeedData(data, viewiden=view2_iden)
            nodes = await core1.nodes('test:int=1 +#newtag', opts={'view': view2_iden})
            self.len(1, nodes)
            self.eq((2020, 2022, 2), nodes[0].getTag('newtag'))

            await core1.setTagModel('test', 'regex', (None, '[0-9]{4}'))

            # This tag doesn't match the regex but should still make the node
            data = [(
                ('test:int', 8),
                {'tags': {'test.12345': (None, None, None)},
                 'tagprops': {'test.12345': {'score': (1, 1)}}}
            )]
            await core1.addFeedData(data)
            self.len(1, await core1.nodes('test:int=8 -#test.12345'))

            data = [(('test:int', 8), {'tags': {'test.1234': (None, None, None)}})]
            await core1.addFeedData(data)
            self.len(0, await core1.nodes('test:int=8 -#newtag.1234'))

            core1.view.layers[0].readonly = True
            data = [(('test:int', 8), {'tags': {'test.1235': (None, None, None)}})]
            await self.asyncraises(s_exc.IsReadOnly, core1.addFeedData(data))

            await core1.nodes('model.deprecated.lock test:deprform:deprprop2')

            data = [(('test:deprform', 'foo'), {'props': {'deprprop2': ('test:str', 'bar'),
                                                          'okayprop': ('str', 'foo')}})]
            await core1.addFeedData(data, viewiden=view2_iden)
            nodes = await core1.nodes('test:deprform=foo', opts={'view': view2_iden})
            self.len(1, nodes)
            self.nn(nodes[0].get('okayprop'))
            self.none(nodes[0].get('deprprop2'))

            await core1.nodes('model.deprecated.lock test:deprprop')

            data = [(('test:deprform', 'dform'), {'props': {'deprprop': (('test:deprprop', '1'),
                                                                          ('test:deprprop', '2')),
                                                            'okayprop': ('str', 'okay')}})]
            await core1.addFeedData(data, viewiden=view2_iden)
            nodes = await core1.nodes('test:deprform=dform', opts={'view': view2_iden})
            self.len(1, nodes)
            self.nn(nodes[0].get('okayprop'))
            self.none(nodes[0].get('deprprop'))
            self.len(0, await core1.nodes('test:deprprop', opts={'view': view2_iden}))

            # TODO: we skip locked forms when attempting to norm
            # should we raise IsDeprLocked if there are locked forms and no unlocked forms norm successfully??
            with self.raises(s_exc.BadTypeValu):
                q = '[test:deprform=dform :deprprop=(1, 2)]'
                await core1.nodes(q, opts={'view': view2_iden})

        # Round-trip poly-valued props through pack()/addFeedData. Poly props
        # (and the implicit poly wrap on every non-array secondary prop) are
        # exported as (typename, value) tuples; addNodes must accept that form.
        async with self.getTestCore() as srccore:

            rtpodes = []

            # Auto-poly wrap on a plain int prop.
            node = (await srccore.nodes('[test:int=2001 :int2=42]'))[0]
            rtpodes.append(node.pack())

            # Multi-type poly with a form-typed value -- target node must be
            # recreated on import.
            node = (await srccore.nodes('[test:str=polyfqdn :poly={[ inet:fqdn=vertex.link ]}]'))[0]
            self.eq(('inet:fqdn', 'vertex.link'), node.get('poly'))
            rtpodes.append(node.pack())

            # Multi-type poly with a non-form typed value.
            node = (await srccore.nodes('[test:str=polyint :poly={[ test:int=1138 ]}]'))[0]
            self.eq(('test:int', 1138), node.get('poly'))
            rtpodes.append(node.pack())

            # Poly with a Comp inner type -- the round-tripped value is a
            # (typename, comp-tuple) shape that the previous import path
            # mis-normalized.
            node = (await srccore.nodes('[test:str=polysrv :poly={[ inet:server="1.2.3.4:80" ]}]'))[0]
            self.eq('inet:server', node.get('poly')[0])
            rtpodes.append(node.pack())

            # Poly array with mixed-typed elements.
            node = (await srccore.nodes('''
                [test:str=polyarr :polyarry={[test:int=7 test:str=bee]}]
            '''))[0]
            self.isin(('test:int', 7), node.get('polyarry'))
            self.isin(('test:str', 'bee'), node.get('polyarry'))
            rtpodes.append(node.pack())

        async with self.getTestCore() as dstcore:

            await dstcore.addFeedData(rtpodes)

            # Auto-poly wrap survived.
            nodes = await dstcore.nodes('test:int=2001')
            self.len(1, nodes)
            self.propeq(nodes[0], 'int2', 42)

            # Form-typed poly value preserved AND the referenced node was
            # created via the adds info from normFromTypedValu.
            nodes = await dstcore.nodes('test:str=polyfqdn')
            self.len(1, nodes)
            self.eq(('inet:fqdn', 'vertex.link'), nodes[0].get('poly'))
            self.len(1, await dstcore.nodes('inet:fqdn=vertex.link'))

            # Non-form typed poly value preserved.
            nodes = await dstcore.nodes('test:str=polyint')
            self.len(1, nodes)
            self.eq(('test:int', 1138), nodes[0].get('poly'))

            # Comp-inner poly value preserved without being mistaken for a
            # bare (typename, value) tuple by the default_types fallback.
            nodes = await dstcore.nodes('test:str=polysrv')
            self.len(1, nodes)
            polysrv = nodes[0].get('poly')
            self.eq('inet:server', polysrv[0])

            # Poly array round-tripped with both elements preserved.
            nodes = await dstcore.nodes('test:str=polyarr')
            self.len(1, nodes)
            polyarr = nodes[0].get('polyarry')
            self.isin(('test:int', 7), polyarr)
            self.isin(('test:str', 'bee'), polyarr)

            # Sad path: a typed-tuple whose typename isn't allowed by the poly
            # is rejected per-prop (warned, not raised); the node still lands
            # with whatever other props were valid.
            data = [(('test:str', 'badpoly'),
                     {'props': {'poly': ('it:dev:int', 7), 'tick': ('test:time', 1)}})]
            await dstcore.addFeedData(data)
            nodes = await dstcore.nodes('test:str=badpoly')
            self.len(1, nodes)
            self.none(nodes[0].get('poly'))
            self.nn(nodes[0].get('tick'))

            # Sad path: a non-tuple value for a poly prop is rejected.
            data = [(('test:str', 'rawpoly'),
                     {'props': {'poly': 42, 'tick': ('test:time', 2)}})]
            await dstcore.addFeedData(data)
            nodes = await dstcore.nodes('test:str=rawpoly')
            self.len(1, nodes)
            self.none(nodes[0].get('poly'))
            self.nn(nodes[0].get('tick'))

            # Sad path: a non-list/tuple value for an array prop is rejected.
            data = [(('test:str', 'rawarr'),
                     {'props': {'polyarry': 42, 'tick': ('test:time', 3)}})]
            await dstcore.addFeedData(data)
            nodes = await dstcore.nodes('test:str=rawarr')
            self.len(1, nodes)
            self.none(nodes[0].get('polyarry'))
            self.nn(nodes[0].get('tick'))

            # Empty array still lands as an empty tuple.
            data = [(('test:str', 'emptyarr'), {'props': {'polyarry': ()}})]
            await dstcore.addFeedData(data)
            nodes = await dstcore.nodes('test:str=emptyarr')
            self.len(1, nodes)
            self.eq((), nodes[0].get('polyarry'))

            # Duplicate elements in a uniq=True poly array get deduped on
            # import via Array._finalizeNorms; a Comp-typed element also
            # propagates virts through Array.normFromTypedValu's accumulator
            # (ip/port virts from inet:server.norm).
            data = [(('test:str', 'dupevirts'),
                     {'props': {'polyarry': (('test:int', 1), ('test:int', 1),
                                              ('inet:server', 'tcp://1.2.3.4:80'))}})]
            await dstcore.addFeedData(data)
            nodes = await dstcore.nodes('test:str=dupevirts')
            self.len(1, nodes)
            polyarr = nodes[0].get('polyarry')
            self.isin(('test:int', 1), polyarr)
            self.true(any(elem[0] == 'inet:server' for elem in polyarr))
            self.len(2, polyarr)

            # Computed props are silently skipped by the typed path so a
            # round-tripped pode with computed values in the props dict
            # doesn't blow up.
            data = [(('test:pivcomp', ('x', 'y')),
                     {'props': {'targ': ('test:pivtarg', 'x'), 'tick': ('time', 1)}})]
            await dstcore.addFeedData(data)
            nodes = await dstcore.nodes('test:pivcomp=(x, y)')
            self.len(1, nodes)
            self.nn(nodes[0].get('tick'))

    async def test_storm_sub_query(self):

        async with self.getTestCore() as core:
            # check that the sub-query can make changes but doesnt effect main query output
            nodes = await core.nodes('[ test:str=foo +#bar ] { [ +#baz ] -#bar }')
            node = nodes[0]
            self.nn(node.getTag('baz'))

            await core.nodes('[ test:str=oof +#bar ] { [ test:int=0xdeadbeef ] }')
            self.len(1, await core.nodes('test:int=3735928559'))

        # Test using subqueries for filtering
        async with self.getTestCore() as core:
            # Generic tests

            self.len(1, await core.nodes('[ test:str=bar +#baz ]'))
            self.len(1, await core.nodes('[ test:pivcomp=(foo,bar) ]'))

            self.len(0, await core.nodes('test:pivcomp=(foo,bar) -{ :lulz -> test:str +#baz }'))
            self.len(1, await core.nodes('test:pivcomp=(foo,bar) +{ :lulz -> test:str +#baz } +test:pivcomp'))

            # Practical real world example

            self.len(2, await core.nodes('[ inet:ip=1.2.3.4 :place:loc=us inet:dns:a=(vertex.link,1.2.3.4) ]'))
            self.len(2, await core.nodes('[ inet:ip=4.3.2.1 :place:loc=zz inet:dns:a=(example.com,4.3.2.1) ]'))
            self.len(1, await core.nodes('inet:ip::place:loc=us'))
            self.len(1, await core.nodes('inet:dns:a:fqdn=vertex.link'))
            self.len(1, await core.nodes('inet:ip:place:loc=zz'))
            self.len(1, await core.nodes('inet:dns:a:fqdn=example.com'))

            # lift all dns, pivot to ip where loc=us, remove the results
            # this should return the example node because the vertex node matches the filter and should be removed
            nodes = await core.nodes('inet:dns:a -{ :ip -> inet:ip +:place:loc=us }')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], ('example.com', (4, 67305985)))

            # lift all dns, pivot to ip where loc=us, add the results
            # this should return the vertex node because only the vertex node matches the filter
            nodes = await core.nodes('inet:dns:a +{ :ip -> inet:ip +:place:loc=us }')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], ('vertex.link', (4, 16909060)))

            # lift all dns, pivot to ip where cc!=us, remove the results
            # this should return the vertex node because the example node matches the filter and should be removed
            nodes = await core.nodes('inet:dns:a -{ :ip -> inet:ip -:place:loc=us }')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], ('vertex.link', (4, 16909060)))

            # lift all dns, pivot to ip where cc!=us, add the results
            # this should return the example node because only the example node matches the filter
            nodes = await core.nodes('inet:dns:a +{ :ip -> inet:ip -:place:loc=us }')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], ('example.com', (4, 67305985)))

            # lift all dns, pivot to ip where asn=1234, add the results
            # this should return nothing because no nodes have asn=1234
            self.len(0, await core.nodes('inet:dns:a +{ :ip -> inet:ip +:asn=1234 }'))

            # lift all dns, pivot to ip where asn!=1234, add the results
            # this should return everything because no nodes have asn=1234
            nodes = await core.nodes('inet:dns:a +{ :ip -> inet:ip -:asn=1234 }')
            self.len(2, nodes)

    async def test_storm_switchcase(self):

        async with self.getTestCore() as core:

            # non-runtsafe switch value
            text = '[inet:ip=([4, 1]) :asn=22] $asn=:asn switch $asn {42: {[+#foo42]} 22: {[+#foo22]}}'
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.nn(nodes[0].getTag('foo22'))
            self.none(nodes[0].getTag('foo42'))

            text = '[inet:ip=([4, 2]) :asn=42] $asn=:asn switch $asn {42: {[+#foo42]} 22: {[+#foo22]}}'
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.none(nodes[0].getTag('foo22'))
            self.nn(nodes[0].getTag('foo42'))

            text = '[inet:ip=([4, 3]) :asn=0] $asn=:asn switch $asn {42: {[+#foo42]} 22: {[+#foo22]}}'
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.none(nodes[0].getTag('foo22'))
            self.none(nodes[0].getTag('foo42'))

            # completely runsafe switch

            text = '$foo=foo switch $foo {foo: {$result=bar} nop: {$result=baz}} [test:str=$result]'
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'bar')

            text = '$foo=nop switch $foo {foo: {$result=bar} nop: {$result=baz}} [test:str=$result]'
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'baz')

            text = '$foo=nop switch $foo {foo: {$result=bar} *: {$result=baz}} [test:str=$result]'
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'baz')

            text = '$foo=xxx $result=xxx switch $foo {foo: {$result=bar} nop: {$result=baz}} [test:str=$result]'
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 'xxx')

            text = '$foo=foo switch $foo {foo: {test:str=bar}}'
            nodes = await core.nodes(text)
            self.len(1, nodes)

            opts = {'vars': {'woot': 'hehe'}}
            text = '[test:str=a] switch $woot { hehe: {[+#baz]} }'
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef[1], 'a')
                self.nn(node.getTag('baz'))
                self.none(node.getTag('faz'))
                self.none(node.getTag('jaz'))

            opts = {'vars': {'woot': 'haha hoho'}}
            text = '[test:str=b] switch $woot { hehe: {[+#baz]} "haha hoho": {[+#faz]} "lolz:lulz": {[+#jaz]} }'
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef[1], 'b')
                self.none(node.getTag('baz'))
                self.nn(node.getTag('faz'))
                self.none(node.getTag('jaz'))

            opts = {'vars': {'woot': 'lolz:lulz'}}
            text = "[test:str=c] switch $woot { hehe: {[+#baz]} 'haha hoho': {[+#faz]} 'lolz:lulz': {[+#jaz]} }"
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef[1], 'c')
                self.none(node.getTag('baz'))
                self.none(node.getTag('faz'))
                self.nn(node.getTag('jaz'))

            opts = {'vars': {'woot': 'lulz'}}
            text = '[test:str=c] switch $woot { hehe: {[+#baz]} *: {[+#jaz]} }'
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef[1], 'c')
                self.none(node.getTag('baz'))
                self.nn(node.getTag('jaz'))

            opts = {'vars': {'woot': 'lulz'}}
            text = '''[test:str=c] $form=$node.form switch $form { 'test:str': {[+#known]} *: {[+#unknown]} }'''
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'c')
            self.nn(node.getTag('known'))
            self.none(node.getTag('unknown'))

            q = '$valu={[test:str=foo]} switch $valu { foo: {test:str=foo return($node.value) } }'
            self.eq('foo', await core.callStorm(q))

            # multi-value switch cases
            q = '''
            [test:str=$inval]
            switch $node.value {
                "foo": { return($node.value) }
                ("boo", "bar"): { return($node.value) }
                (coo, car): { return($node.value) }
                ('doo', 'dar'): { return($node.value) }
                ("goo", 'gar', gaz): { return($node.value) }
            }
            $lib.raise(BadArg, `Failed match on {$inval}`)
            '''
            for inval in ('foo', 'boo', 'bar', 'coo', 'car', 'doo', 'dar', 'goo', 'gar', 'gaz'):
                valu = await core.callStorm(q, opts={'vars': {'inval': inval}})
                self.eq(valu, inval)

            # bare asterisk is allowed as a multi-value
            valu = await core.callStorm('$foo="*" switch $foo { *:{ return(default) } (someval, *): { return(multi) } }')
            self.eq(valu, 'multi')

            # multiple default cases is invalid
            msgs = await core.stormlist('$foo=foo switch $foo { *:{} *:{} }')
            self.stormIsInErr('Switch statements cannot have more than one default case. Found 2.', msgs)

            # multi-value case without a comma
            msgs = await core.stormlist('$foo=foo switch $foo { (foo bar): { $lib.print(woot) } }')
            self.stormIsInErr('Unexpected token', msgs)
            self.stormIsInErr('expecting one of: case multi-value, double-quoted string, single-quoted string', msgs)

            # multi-value case without a second value
            msgs = await core.stormlist('$foo=foo switch $foo { (foo, ): { $lib.print(woot) } }')
            self.stormIsInErr('Unexpected token', msgs)
            self.stormIsInErr('expecting one of: case multi-value, double-quoted string, single-quoted string', msgs)

            # multi-value case without a comma or second value
            msgs = await core.stormlist('$foo=foo switch $foo { (foo): { $lib.print(woot) } }')
            self.stormIsInErr('Unexpected token', msgs)
            self.stormIsInErr('expecting one of: ,', msgs)

    async def test_storm_tagvar(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'tag': 'hehe.haha', 'mtag': '', }}

            nodes = await core.nodes('[ test:str=foo +#$tag ]', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')
            self.nn(node.getTag('hehe.haha'))

            nodes = await core.nodes('#$tag', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')
            self.nn(node.getTag('hehe.haha'))

            nodes = await core.nodes('$tag=hehe.haha test:str=foo +#$tag')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')
            self.nn(node.getTag('hehe.haha'))

            nodes = await core.nodes('[test:str=foo2] $tag="*" test:str +#$tag')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')
            self.nn(node.getTag('hehe.haha'))

            nodes = await core.nodes('$tag=hehe.* test:str +#$tag')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')

            nodes = await core.nodes('[test:str=foo :hehe=newtag] $tag=:hehe [+#$tag]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')
            self.nn(node.getTag('newtag'))

            nodes = await core.nodes('#$tag [ -#$tag ]', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')
            self.none(node.getTag('hehe.haha'))

            mesgs = await core.stormlist('$var=timetag test:str=foo [+#$var=2019] $lib.print(#$var)')
            podes = [m[1] for m in mesgs if m[0] == 'node']
            self.len(1, podes)
            pode = podes[0]
            self.true(s_node.tagged(pode, '#timetag'))

            mesgs = await core.stormlist('test:str=foo $var=$node.value [+#$var=2019] $lib.print(#$var)')
            self.stormIsInPrint('2019-01-01T00:00:00Z - 2019-01-01T00:00:00.000001Z', mesgs)
            podes = [m[1] for m in mesgs if m[0] == 'node']
            self.len(1, podes)
            pode = podes[0]
            self.true(s_node.tagged(pode, '#foo'))

            nodes = await core.nodes('$d = ({"foo": "bar"}) [test:str=yop +#$d.foo]')
            self.len(1, nodes)
            self.nn(nodes[0].getTag('bar'))

            q = '$t="{first}.{last}" [test:str=yop +#$t.format(first=foo, last=bar)]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.nn(nodes[0].getTag('foo.bar'))

            q = '$foo=(tag1,tag2,tag3) [test:str=x +#$foo]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.nn(nodes[0].getTag('tag1'))
            self.nn(nodes[0].getTag('tag2'))
            self.nn(nodes[0].getTag('tag3'))

            nodes = await core.nodes('[ test:str=foo +?#$mtag +?#$tag ]', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], 'foo')
            self.nn(node.getTag('hehe.haha'))

            q = '$foo=(tag1,?,tag3) [test:str=x +?#$foo]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.nn(nodes[0].getTag('tag1'))
            self.nn(nodes[0].getTag('tag3'))

            q = '$t1="" $t2="" $t3=tag3 [test:str=x -#$t1 +?#$t2 +?#$t3]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.nn(nodes[0].getTag('tag3'))

            mesgs = await core.stormlist('test:str=foo $var=$node.value [+?#$var=2019] $lib.print(#$var)')
            self.stormIsInPrint('2019-01-01T00:00:00Z - 2019-01-01T00:00:00.000001Z', mesgs)
            podes = [m[1] for m in mesgs if m[0] == 'node']
            self.len(1, podes)
            pode = podes[0]
            self.true(s_node.tagged(pode, '#foo'))

            mesgs = await core.stormlist('$var="" test:str=foo [+?#$var=2019]')
            podes = [m[1] for m in mesgs if m[0] == 'node']
            self.len(1, podes)
            pode = podes[0]
            self.true(s_node.tagged(pode, '#timetag'))

            nodes = await core.nodes('$d = ({"foo": ""}) [test:str=yop +?#$d.foo +#tag1]')
            self.len(1, nodes)
            self.none(nodes[0].getTag('foo.*'))
            self.nn(nodes[0].getTag('tag1'))

    async def test_storm_forloop(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'fqdns': ('foo.com', 'bar.com')}}

            nodes = await core.nodes('for $fqdn in $fqdns { [ inet:fqdn=$fqdn ] }', opts=opts)
            self.sorteq(('bar.com', 'foo.com'), [n.ndef[1] for n in nodes])

            opts = {'vars': {'dnsa': (('foo.com', '1.2.3.4'), ('bar.com', '5.6.7.8'))}}

            nodes = await core.nodes('for ($fqdn, $ip) in $dnsa { [ inet:dns:a=($fqdn,$ip) ] }', opts=opts)
            self.eq((('foo.com', (4, 0x01020304)), ('bar.com', (4, 0x05060708))), [n.ndef[1] for n in nodes])

            with self.raises(s_exc.StormVarListError):
                await core.nodes('for ($fqdn,$ip,$boom) in $dnsa { [ inet:dns:a=($fqdn,$ip) ] }', opts=opts)

            q = '[ inet:ip=1.2.3.4 +#hehe +#haha ] for ($foo,$bar,$baz) in $node.tags() {[+#$foo]}'
            with self.raises(s_exc.StormVarListError):
                await core.nodes(q)

            await core.nodes('inet:ip=1.2.3.4 for $tag in $node.tags() { [ +#hoho ] { [inet:ip=5.5.5.5 +#$tag] } continue [ +#visi ] }')  # noqa: E501
            self.len(1, await core.nodes('inet:ip=5.5.5.5 +#hehe +#haha -#visi'))

            self.len(1, await core.nodes('''
                inet:ip=1.2.3.4
                for $tag in $node.tags() {
                    [ +#hoho ]
                    { [inet:ip=6.6.6.6 +#$tag] }
                    break
                    [ +#visi ]
                }
            '''))
            q = 'inet:ip=6.6.6.6 +(#hehe or #haha) -(#hehe and #haha) -#visi'
            self.len(1, await core.nodes(q))

            q = 'inet:ip=1.2.3.4 for $tag in $node.tags() { [test:str=$tag] }'  # noqa: E501
            nodes = await core.nodes(q)
            self.eq([n.ndef[0] for n in nodes], [*['test:str', 'inet:ip'] * 3])

            # non-runsafe iteration over a dictionary
            q = '''$dict=({"key1": "valu1", "key2": "valu2"}) [(test:str=test1) (test:str=test2)]
            for ($key, $valu) in $dict {
                [:hehe=$valu]
            }
            '''
            nodes = await core.nodes(q)
            # Each input node is yielded *twice* from the runtime
            self.len(4, nodes)
            self.eq({'test1', 'test2'}, {n.ndef[1] for n in nodes})
            for node in nodes:
                self.propeq(node, 'hehe', 'valu2')

            # None values don't yield anything
            q = '''$foo = ({})
            for $name in $foo.bar { [ test:str=$name ] }
            '''
            nodes = await core.nodes(q)
            self.len(0, nodes)

            # Even with a inbound node, zero loop iterations will not yield inbound nodes.
            q = '''test:str=test1 $foo = ({})
            for $name in $foo.bar { [ test:str=$name ] }
            '''
            nodes = await core.nodes(q)
            self.len(0, nodes)

            q = '''$list=([["inet:fqdn", "nest.com"]])
            for ($form, $valu) in $list { [ *$form=$valu ] }
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(('inet:fqdn', 'nest.com'), nodes[0].ndef)

            q = '''inet:fqdn=nest.com $list=([[$node.form, $node.value]])
            for ($form, $valu) in $list { [ *$form=$valu ] }
            '''
            nodes = await core.nodes(q)
            self.len(2, nodes)
            self.eq(('inet:fqdn', 'nest.com'), nodes[0].ndef)
            self.eq(('inet:fqdn', 'nest.com'), nodes[1].ndef)

            with self.raises(s_exc.StormRuntimeError) as err:
                await core.nodes('[ it:dev:int=1 ] for $n in $node.value { }')
            self.isin("'int' object is not iterable: 1", err.exception.errinfo.get('mesg'))

            with self.raises(s_exc.StormRuntimeError) as err:
                await core.nodes('for $n in { .created return($node) } { }')
            self.isin("'node' object is not iterable", err.exception.errinfo.get('mesg'))

    async def test_storm_whileloop(self):

        async with self.getTestCore() as core:
            q = '$x = 0 while $($x < 10) { $x=$($x+1) [test:int=$x]}'
            nodes = await core.nodes(q)
            self.len(10, nodes)

            # It should work the same with a continue at the end
            q = '$x = 0 while $($x < 10) { $x=$($x+1) [test:int=$x] continue}'
            nodes = await core.nodes(q)
            self.len(10, nodes)

            # Non Runtsafe test
            q = '''
            test:int=4 test:int=5 $x=$node.value
            while 1 {
                $x=$($x-1)
                if $($x=$(2)) {continue}
                elif $($x=$(1)) {break}
                $lib.print($x)
            } '''
            msgs = await core.stormlist(q)
            prints = [m[1].get('mesg') for m in msgs if m[0] == 'print']
            self.eq(['3', '4', '3'], prints)

            # Non runtsafe yield test
            q = 'test:int=4 while $node.value { [test:str=$node.value] break}'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = '$x = 10 while 1 { $x=$($x-2) if $($x=$(4)) {continue} [test:int=$x]  if $($x<=0) {break} }'
            nodes = await core.nodes(q)
            self.eq([8, 6, 2, 0], [n.ndef[1] for n in nodes])

    async def test_storm_varmeth(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'blob': 'woot.com|1.2.3.4'}}
            nodes = await core.nodes('[ inet:dns:a=$blob.split("|") ]', opts=opts)

            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef[0], 'inet:dns:a')
                self.eq(node.ndef[1], ('woot.com', (4, 0x01020304)))

    async def test_storm_formpivot(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:dns:a=(woot.com,1.2.3.4) ]')

            # this tests getdst()
            nodes = await core.nodes('inet:fqdn=woot.com -> inet:dns:a')
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef, ('inet:dns:a', ('woot.com', (4, 0x01020304))))

            # this tests getsrc()
            nodes = await core.nodes('inet:fqdn=woot.com -> inet:dns:a -> inet:ip')
            self.len(1, nodes)
            for node in nodes:
                self.eq(node.ndef, ('inet:ip', (4, 0x01020304)))

            with self.raises(s_exc.NoSuchPivot):
                nodes = await core.nodes('[ test:int=10 ] -> test:taxonomy')

            nodes = await core.nodes('[ test:str=woot :bar={[inet:fqdn=woot.com]} ] -> inet:fqdn')
            self.eq(nodes[0].ndef, ('inet:fqdn', 'woot.com'))

    async def test_storm_expressions(self):
        async with self.getTestCore() as core:

            async def _test(q, ansr):
                nodes = await core.nodes(f'[test:int={q}]')
                self.len(1, nodes)
                self.eq(nodes[0].ndef, ('test:int', ansr))

            await _test('$(42)', 42)
            await _test('$(2 + 4)', 6)
            await _test('$(4 - 2)', 2)
            await _test('$(4 -2)', 2)
            await _test('$(4- 2)', 2)
            await _test('$(4-2)', 2)
            await _test('$(2 * 4)', 8)
            await _test('$(1 + 2 * 4)', 9)
            await _test('$(1 + 2 * 4)', 9)
            await _test('$((1 + 2) * 4)', 12)
            await _test('$(1 < 1)', 0)
            await _test('$(1 <= 1)', 1)
            await _test('$(1 > 1)', 0)
            await _test('$(1 >= 1)', 1)
            await _test('$(1 >= 1 + 1)', 0)
            await _test('$(1 >= 1 + 1 * -2)', 1)
            await _test('$(1 - 1 - 1)', -1)
            await _test('$(4 / 2 / 2)', 1)
            await _test('$(1 / 2)', 0)
            await _test('$(1 != 1)', 0)
            await _test('$(2 != 1)', 1)
            await _test('$(2 = 1)', 0)
            await _test('$(2 = 2)', 1)
            await _test('$(2 = 2.0)', 1)
            await _test('$("foo" = "foo")', 1)
            await _test('$("foo" != "foo")', 0)
            await _test('$("foo2" = "foo")', 0)
            await _test('$("foo2" != "foo")', 1)
            await _test('$(0 and 1)', 0)
            await _test('$(1 and 1)', 1)
            await _test('$(1 or 1)', 1)
            await _test('$(0 or 0)', 0)
            await _test('$(1 or 0)', 1)
            await _test('$(not 0)', 1)
            await _test('$(not 1)', 0)
            await _test('$(1 or 0 and 0)', 1)  # and > or
            await _test('$(not 1 and 1)', 0)  # not > and
            await _test('$(not 1 > 1)', 1)  # cmp > not

            opts = {'vars': {'none': None}}
            # runtsafe
            nodes = await core.nodes('if $($none) {[test:str=yep]}', opts=opts)
            self.len(0, nodes)

            # non-runtsafe
            nodes = await core.nodes('[test:int=42] if $($none) {[test:str=$node]} else {spin}', opts=opts)
            self.len(0, nodes)

            nodes = await core.nodes('if $(not $none) {[test:str=yep]}', opts=opts)
            self.len(1, nodes)
            nodes = await core.nodes('[test:int=42] if $(not $none) {[test:str=yep]} else {spin}', opts=opts)
            self.len(2, nodes)

            # TODO:  implement move-along mechanism
            # await _test('$(1 / 0)', 0)

            # Test non-runtsafe
            q = '[test:type10=1 :intprop=24] $val=:intprop [test:int=$(1 + $val)]'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('test:int', 25))

            # Test invalid comparisons
            q = '$val=(1,2,3) [test:str=$("foo" >= $val)]'
            await self.asyncraises(s_exc.BadCast, core.nodes(q))

            q = '$val=(1,2,3) [test:str=$($val >= "foo")]'
            await self.asyncraises(s_exc.BadCast, core.nodes(q))

            q = '$val=42 [test:str=$(42<$val)]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'false'))

            q = '[test:str=foo :hehe=42] [test:str=$(not :hehe<42)]'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'true'))

            with self.raises(s_exc.StormRuntimeError) as cm:
                await core.nodes('$x=(1 / 0)')
            self.eq('Cannot divide by zero', cm.exception.get('mesg'))

            with self.raises(s_exc.StormRuntimeError) as cm:
                await core.nodes('$x=(1 % 0)')
            self.eq('Cannot divide by zero', cm.exception.get('mesg'))

            with self.raises(s_exc.StormRuntimeError) as cm:
                await core.nodes('$x=(1.0 / 0.0)')
            self.eq('Cannot divide by zero', cm.exception.get('mesg'))

            with self.raises(s_exc.StormRuntimeError) as cm:
                await core.nodes('$x=(1.0 % 0.0)')
            self.eq('Invalid operation on a Number', cm.exception.get('mesg'))

    async def test_storm_filter_vars(self):
        '''
        Test variable filters (e.g. +$foo) and expression filters (e.g. +$(:hehe < 4))

        '''
        async with self.getTestCore() as core:

            # variable filter, non-runtsafe, true path
            q = '[test:type10=1 :strprop=1] $foo=:strprop +$foo'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            # variable filter, non-runtsafe, false path
            q = '[test:type10=1 :strprop=1] $foo=:strprop -$foo'
            nodes = await core.nodes(q)
            self.len(0, nodes)

            # variable filter, runtsafe, true path
            q = '[test:type10=1 :strprop=1] $foo=1 +$foo'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            # variable filter, runtsafe, false path
            q = '[test:type10=1 :strprop=1] $foo=$(0) -$foo'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            # expression filter, non-runtsafe, true path
            q = '[test:type10=2 :strprop=1] | spin | test:type10 +$(:strprop)'
            nodes = await core.nodes(q)
            self.len(2, nodes)

            # expression filter, non-runtsafe, false path
            q = '[test:type10=1 :strprop=1] -$(:strprop + 0)'
            nodes = await core.nodes(q)
            self.len(0, nodes)

            # expression filter, runtsafe, true path
            q = '[test:type10=1 :strprop=1] +$(1)'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            # expression filter, runtsafe, false path
            q = '[test:type10=1 :strprop=1] -$(0)'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = '''[test:guid=(g0,) :tick="1992/06/19 22:22:17.000000"]
            -(test:guid:size <= 16384 and test:guid:tick < 2014/01/01)'''
            self.len(1, await core.nodes(q))

    async def test_storm_filter(self):
        async with self.getTestCore() as core:
            q = '[test:str=test +#test=(2018,2019)]'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = 'test:str=test $foo=test $bar=(2018,2019) +#$foo=$bar'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = 'test:str=test $foo=$node.value $bar=(2018,2019) +#$foo=$bar'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            # Filter by var as node
            q = '[ps:person=*] $person = $node { [(test:str=foo :bar=$person)] } -ps:person test:str +:bar=$person'
            nodes = await core.nodes(q)
            self.len(1, nodes)

    async def test_storm_ifstmt(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[test:int=1 :int2=1] if :int2 {[+#woot]}')
            self.true(nodes[0].hasTag('woot'))
            nodes = await core.nodes('[test:int=1 :int2=0] if $(:int2) {[+#woot2]}')
            self.false(nodes[0].hasTag('woot2'))

            nodes = await core.nodes('[test:int=1 :int2=1] if $(:int2) {[+#woot3]} else {[+#nowoot3]}')
            self.true(nodes[0].hasTag('woot3'))
            self.false(nodes[0].hasTag('nowoot3'))

            nodes = await core.nodes('[test:int=2 :int2=0] if $(:int2) {[+#woot3]} else {[+#nowoot3]}')
            self.false(nodes[0].hasTag('woot3'))
            self.true(nodes[0].hasTag('nowoot3'))

            q = '[test:int=0 :int2=0] if $(:int2) {[+#woot41]} elif $($node.value) {[+#woot42]}'
            nodes = await core.nodes(q)
            self.false(nodes[0].hasTag('woot41'))
            self.false(nodes[0].hasTag('woot42'))

            q = '[test:int=0 :int2=1] if $(:int2) {[+#woot51]} elif $($node.value) {[+#woot52]}'
            nodes = await core.nodes(q)
            self.true(nodes[0].hasTag('woot51'))
            self.false(nodes[0].hasTag('woot52'))

            q = '[test:int=1 :int2=1] if $(:int2) {[+#woot61]} elif $($node.value) {[+#woot62]}'
            nodes = await core.nodes(q)
            self.true(nodes[0].hasTag('woot61'))
            self.false(nodes[0].hasTag('woot62'))

            q = '[test:int=2 :int2=0] if $(:int2) {[+#woot71]} elif $($node.value) {[+#woot72]}'
            nodes = await core.nodes(q)
            self.false(nodes[0].hasTag('woot71'))
            self.true(nodes[0].hasTag('woot72'))

            q = ('[test:int=0 :int2=0] if $(:int2) {[+#woot81]} '
                 'elif $($node.value) {[+#woot82]} else {[+#woot83]}')
            nodes = await core.nodes(q)
            self.false(nodes[0].hasTag('woot81'))
            self.false(nodes[0].hasTag('woot82'))
            self.true(nodes[0].hasTag('woot83'))

            q = ('[test:int=0 :int2=42] if $(:int2) {[+#woot91]} '
                 'elif $($node.value){[+#woot92]}else {[+#woot93]}')
            nodes = await core.nodes(q)
            self.true(nodes[0].hasTag('woot91'))
            self.false(nodes[0].hasTag('woot92'))
            self.false(nodes[0].hasTag('woot93'))

            q = ('[test:int=1 :int2=0] if $(:int2){[+#woota1]} '
                 'elif $($node.value) {[+#woota2]} else {[+#woota3]}')
            nodes = await core.nodes(q)
            self.false(nodes[0].hasTag('woota1'))
            self.true(nodes[0].hasTag('woota2'))
            self.false(nodes[0].hasTag('woota3'))

            q = ('[test:int=1 :int2=1] if $(:int2) {[+#wootb1]} '
                 'elif $($node.value) {[+#wootb2]} else{[+#wootb3]}')
            nodes = await core.nodes(q)
            self.true(nodes[0].hasTag('wootb1'))
            self.false(nodes[0].hasTag('wootb2'))
            self.false(nodes[0].hasTag('wootb3'))

            # Runtsafe condition with nodes
            nodes = await core.nodes('[test:str=yep2] if $(1) {[+#woot]}')
            self.true(nodes[0].hasTag('woot'))

            # Runtsafe condition with nodes, condition is false
            nodes = await core.nodes('[test:str=yep2] if $(0) {[+#woot2]}')
            self.false(nodes[0].hasTag('woot2'))

            # Completely runtsafe, condition is true
            q = '$foo=yawp if $foo {$bar=lol} else {$bar=rofl} [test:str=yep3 +#$bar]'
            nodes = await core.nodes(q)
            self.true(nodes[0].hasTag('lol'))
            self.false(nodes[0].hasTag('rofl'))

            # Completely runtsafe, condition is false
            q = '$foo=$(0) if $($foo) {$bar=lol} else {$bar=rofl} [test:str=yep4 +#$bar]'
            nodes = await core.nodes(q)
            self.false(nodes[0].hasTag('lol'))
            self.true(nodes[0].hasTag('rofl'))

            # Non-constant runtsafe
            q = '$vals=(1,2,3,4) for $i in $vals {if $($i="1") {[test:int=$i]}}'
            nodes = await core.nodes(q)
            self.len(1, nodes)

    async def test_storm_order(self):
        q = '''[test:str=foo :hehe=bar] $tvar=() $tvar.append(1) $tvar.append(:hehe) $lib.print(('').join($tvar)) '''
        async with self.getTestCore() as core:
            mesgs = await core.stormlist(q)
            self.stormIsInPrint('1bar', mesgs)

    async def test_cortex_mirror(self):

        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')

            async with self.getTestCore(dirn=path00) as core00:
                await core00.nodes('[ inet:ip=1.2.3.4 ]')

            s_tools_backup.backup(path00, path01)

            async with self.getTestCore(dirn=path00) as core00:

                self.false(core00.conf.get('parent'))

                await core00.nodes('[ inet:ip=1.2.3.4 ]')

                ip00 = await core00.nodes('[ inet:ip=3.3.3.3 ]')

                qiden = await core00.callStorm('$q = $lib.queue.add(hehe) return($q.iden)')
                q = 'trigger.add node:add --form inet:fqdn {$lib.queue.byname(hehe).put($node.repr())}'
                msgs = await core00.stormlist(q)

                ddef = await core00.callStorm('return($lib.dmon.add(${$lib.time.sleep(10)}, name=hehedmon))')
                await core00.callStorm('return($lib.dmon.del($iden))', opts={'vars': {'iden': ddef.get('iden')}})

                url = core00.getLocalUrl()

                core01conf = {'parent': url}

                async with self.getTestCore(dirn=path01, conf=core01conf) as core01:

                    await core00.nodes('[ inet:fqdn=vertex.link ]')
                    await core00.nodes('queue.add visi')

                    await core01.sync()

                    ip01 = await core01.nodes('inet:ip=3.3.3.3')
                    self.eq(ip00[0].get('.created'), ip01[0].get('.created'))

                    self.len(1, await core01.nodes('inet:fqdn=vertex.link'))

                    q = 'for ($offs, $fqdn) in $lib.queue.byname(hehe).gets(wait=0) { inet:fqdn=$fqdn }'
                    self.len(2, await core01.nodes(q))

                    msgs = await core01.stormlist('queue.list')
                    self.stormIsInPrint('visi', msgs)

                    opts = {'vars': {'iden': ddef.get('iden')}}
                    ddef1 = await core01.callStorm('return($lib.dmon.get($iden))', opts=opts)
                    self.none(ddef1)

                    # Validate that mirrors can still write
                    await core01.nodes('queue.add visi2')
                    msgs = await core01.stormlist('queue.list')
                    self.stormIsInPrint('visi2', msgs)

                    await core01.nodes('[ inet:fqdn=www.vertex.link ]')
                    self.len(1, await core01.nodes('inet:fqdn=www.vertex.link'))

                    # modHttpExtApi stamps 'updated' in its top half and pushes it,
                    # so the mirror applies the SAME timestamp on replay rather than
                    # recomputing s_common.now() and diverging from the leader.
                    unfo = await core00.addUser('httpuser')
                    hadef = await core00.addHttpExtApi({
                        'path': 'foo/bar',
                        'owner': unfo.get('iden'),
                        'view': core00.getView().iden,
                    })
                    hiden = hadef.get('iden')

                    # sleep so a recomputed now() on the mirror would differ
                    await asyncio.sleep(0.005)
                    hmod = await core00.modHttpExtApi(hiden, 'name', 'wow')
                    self.gt(hmod.get('updated'), hadef.get('updated'))

                    await core01.sync()

                    hmirror = await core01.getHttpExtApi(hiden)
                    self.eq('wow', hmirror.get('name'))
                    self.eq(hmod.get('updated'), hmirror.get('updated'))
                    self.eq(hmod.get('created'), hmirror.get('created'))

                    # get the nexus index
                    nexusind = core01.nexsroot.nexslog.index()

                await core00.nodes('[ inet:ip=5.5.5.5 ]')

                # test what happens when we go down and come up again...
                async with self.getTestCore(dirn=path01, conf=core01conf) as core01:

                    # check that startup does not create any events
                    self.eq(nexusind, core01.nexsroot.nexslog.index())

                    await core00.nodes('[ inet:fqdn=woot.com ]')
                    await core01.sync()

                    q = 'for ($offs, $fqdn) in $lib.queue.byname(hehe).gets(wait=0) { inet:fqdn=$fqdn }'
                    self.len(5, await core01.nodes(q))
                    self.len(1, await core01.nodes('inet:ip=5.5.5.5'))

                    opts = {'vars': {'iden': ddef.get('iden')}}
                    ddef = await core01.callStorm('return($lib.dmon.get($iden))', opts=opts)
                    self.none(ddef)

                    await core00.callStorm('queue.del $iden', opts={'vars': {'iden': qiden}})
                    await core01.sync()

                    self.none(await core00.getAuthGate('queue:hehe'))
                    self.none(await core01.getAuthGate('queue:hehe'))

            # now lets start up in the opposite order...
            async with self.getTestCore(dirn=path01, conf=core01conf) as core01:

                async with self.getTestCore(dirn=path00) as core00:

                    self.len(1, await core00.nodes('[ inet:ip=6.6.6.6 ]'))

                    await core01.sync()

                    self.len(1, await core01.nodes('inet:ip=6.6.6.6'))

                # what happens if *he* goes down and comes back up again?
                async with self.getTestCore(dirn=path00) as core00:

                    await core00.nodes('[ inet:ip=7.7.7.7 ]')

                    await core01.sync()

                    self.len(1, (await core01.nodes('inet:ip=7.7.7.7')))

                # Try a write with the leader down
                with mock.patch('synapse.lib.nexus.FOLLOWER_WRITE_WAIT_S', 2):
                    await self.asyncraises(s_exc.LinkErr, core01.nodes('[inet:ip=7.7.7.8]'))

                # Bring the leader back up and try again
                async with self.getTestCore(dirn=path00) as core00:
                    self.len(1, await core01.nodes('[ inet:ip=7.7.7.8 ]'))

                # remove the mirrorness from the Cortex and ensure that we can
                # write to the Cortex. This will move the core01 ahead of
                # core00 & core01 can become the leader. The old leader is
                # down, so this must be a forced promotion. An explicit parent
                # pins the service as a follower, so clear it before promoting.
                core01.conf.pop('parent', None)
                await core01.promote(force=True)
                self.false(core01.nexsroot._mirready.is_set())

                self.len(1, await core01.nodes('[inet:ip=9.9.9.8]'))
                new_url = core01.getLocalUrl()
                new_conf = {'parent': new_url}
                async with self.getTestCore(dirn=path00, conf=new_conf) as core00:
                    await core00.sync()
                    self.len(1, await core00.nodes('inet:ip=9.9.9.8'))

    async def test_cortex_mirror_culled(self):

        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'core00')    # upstream
            path01 = s_common.gendir(dirn, 'core01')    # mirror
            path02 = s_common.gendir(dirn, 'core02')    # mirror of mirror
            path02b = s_common.gendir(dirn, 'core02b')  # mirror of mirror restore

            async with self.getTestCore(dirn=path00) as core00:
                await core00.nodes('[ inet:ip=1.2.3.4 ]')

            s_tools_backup.backup(path00, path01)
            s_tools_backup.backup(path00, path02)

            async with self.getTestCore(dirn=path00) as core00:

                url00 = core00.getLocalUrl()

                lowuser = await core00.auth.addUser('low')
                opts = {'user': lowuser.iden}
                await self.asyncraises(s_exc.AuthDeny, core00.callStorm('$lib.cell.trimNexsLog()', opts=opts))

                async with self.getTestCore(dirn=path01, conf={'parent': url00}) as core01:

                    url01 = core01.getLocalUrl()

                    async with self.getTestCore(dirn=path02, conf={'parent': url01}) as core02:

                        url02 = core02.getLocalUrl()
                        consumers = [url01, url02]
                        opts = {'vars': {'cons': consumers}}
                        strim = 'return($lib.cell.trimNexsLog(consumers=$cons))'

                        await core00.nodes('[ inet:ip=10.0.0.0/28 ]')
                        ips00 = await core00.count('inet:ip')

                        await core01.sync()
                        await core02.sync()

                        self.eq(ips00, await core01.count('inet:ip'))
                        self.eq(ips00, await core02.count('inet:ip'))

                        ind = await core00.getNexsIndx()
                        ret = await core00.callStorm(strim, opts=opts)
                        self.eq(ind, ret)

                        await core01.sync()
                        await core02.sync()

                        # all the logs match
                        log00 = await alist(core00.nexsroot.nexslog.iter(0))
                        log01 = await alist(core01.nexsroot.nexslog.iter(0))
                        log02 = await alist(core02.nexsroot.nexslog.iter(0))
                        self.true(log00 == log01 == log02)

                        # simulate a waiter timing out
                        with mock.patch('synapse.cortex.CoreApi.waitNexsOffs', return_value=False):
                            await self.asyncraises(s_exc.SynErr, core00.callStorm(strim, opts=opts))

                    # consumer offline
                    await self.asyncraises(s_exc.NoSuchPath, core00.callStorm(strim, opts=opts))

                    # admin can still cull and break the mirror
                    await core00.nodes('[ inet:ip=127.0.0.1/28 ]')

                    ind = await core00.rotateNexsLog()
                    await core01.sync()
                    self.true(await core00.cullNexsLog(ind - 1))
                    await core01.sync()

                    log00 = await alist(core00.nexsroot.nexslog.iter(0))
                    log01 = await alist(core01.nexsroot.nexslog.iter(0))
                    self.eq(log00, log01)

                    with self.getLoggerStream('synapse.lib.nexus') as stream:
                        async with self.getTestCore(dirn=path02, conf={'parent': url01}) as core02:
                            await stream.expect('offset is out of sync', timeout=6)
                            self.true(core02.nexsroot.isfini)

                # restore mirror
                s_tools_backup.backup(path01, path02b)

                async with self.getTestCore(dirn=path01, conf={'parent': url00}) as core01:

                    url01 = core01.getLocalUrl()

                    async with self.getTestCore(dirn=path02b, conf={'parent': url01}) as core02:

                        url02 = core02.getLocalUrl()
                        opts = {'vars': {'url01': url01, 'url02': url02}}
                        strim = 'return($lib.cell.trimNexsLog(consumers=($url01, $url02), timeout=(null)))'

                        await core00.nodes('[ inet:ip=11.0.0.0/28 ]')
                        ips00 = await core00.count('inet:ip')

                        await core01.sync()
                        await core02.sync()

                        self.eq(ips00, await core01.count('inet:ip'))
                        self.eq(ips00, await core02.count('inet:ip'))

                        # all the logs match
                        log00 = await alist(core00.nexsroot.nexslog.iter(0))
                        log01 = await alist(core01.nexsroot.nexslog.iter(0))
                        log02 = await alist(core02.nexsroot.nexslog.iter(0))
                        self.true(log00 == log01 == log02)

                        rng00 = core00.nexsroot.nexslog._ranges
                        rng01 = core01.nexsroot.nexslog._ranges
                        rng02 = core02.nexsroot.nexslog._ranges
                        self.true(rng00 == rng01 == rng02)

                        # can call trim from a mirror
                        # NOTE: core02 will have a prox to itself to wait for offset
                        ind = await core02.getNexsIndx()
                        ret = await core02.callStorm(strim, opts=opts)
                        self.eq(ind, ret)

                        await core01.sync()
                        await core02.sync()

                        # all the logs match
                        log00 = await alist(core00.nexsroot.nexslog.iter(0))
                        log01 = await alist(core01.nexsroot.nexslog.iter(0))
                        log02 = await alist(core02.nexsroot.nexslog.iter(0))
                        self.true(log00 == log01 == log02)

    async def test_cortex_mirror_of_mirror(self):

        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')
            path02 = s_common.gendir(dirn, 'core02')
            path02a = s_common.gendir(dirn, 'core02a')

            async with self.getTestCore(dirn=path00) as core00:
                await core00.nodes('[ inet:ip=1.2.3.4 ]')

            s_tools_backup.backup(path00, path01)
            s_tools_backup.backup(path01, path02)
            s_tools_backup.backup(path01, path02a)

            async with self.getTestCore(dirn=path00) as core00:

                self.false(core00.conf.get('parent'))

                await core00.nodes('[ inet:ip=1.2.3.4 ]')
                await core00.nodes('$lib.queue.add(hehe)')
                q = 'trigger.add node:add --form inet:fqdn {$lib.queue.get(hehe).put($node.repr())}'
                await core00.nodes(q)

                url = core00.getLocalUrl()

                core01conf = {'parent': url}
                async with self.getTestCore(dirn=path01, conf=core01conf) as core01:
                    url2 = core01.getLocalUrl()

                    core02conf = {'parent': url2}
                    async with self.getTestCore(dirn=path02, conf=core02conf) as core02:

                        await core00.nodes('[ inet:fqdn=vertex.link ]')
                        await core00.nodes('queue.add visi')

                        await core01.sync()
                        self.len(1, await core01.nodes('inet:fqdn=vertex.link'))

                        await core02.sync()

                        self.len(1, await core02.nodes('inet:fqdn=vertex.link'))

                        # Changes from the bottom get dispersed
                        self.len(1, await core02.nodes('[ inet:fqdn=test.vertex.link ]'))
                        self.len(1, await core00.nodes('inet:fqdn=test.vertex.link'))
                        self.len(1, await core01.nodes('inet:fqdn=test.vertex.link'))

                        # Changes from the middle get dispersed
                        self.len(1, await core01.nodes('[ inet:fqdn=test2.vertex.link ]'))
                        self.len(1, await core00.nodes('inet:fqdn=test2.vertex.link'))
                        await core02.sync()
                        self.len(1, await core02.nodes('inet:fqdn=test2.vertex.link'))

                        # Bring up a sibling mirror to the bottom
                        async with self.getTestCore(dirn=path02a, conf=core02conf) as core02a:
                            self.len(1, await core02a.nodes('[ inet:fqdn=test3.vertex.link ]'))
                            self.len(1, await core02a.nodes('inet:fqdn=test2.vertex.link'))

                            # Make sure sibling can see changes from other sibling
                            await core02.sync()
                            self.len(1, await core02.nodes('inet:fqdn=test3.vertex.link'))

                            logentrycount00 = await core00.nexsroot.index()
                            logentrycount01 = await core01.nexsroot.index()
                            logentrycount02 = await core02.nexsroot.index()
                            logentrycount02a = await core02a.nexsroot.index()

                            self.eq(logentrycount00, logentrycount01)
                            self.eq(logentrycount01, logentrycount02)
                            self.eq(logentrycount02, logentrycount02a)

    async def test_norms(self):
        async with self.getTestCoreAndProxy() as (core, prox):
            # getPropNorm base tests
            norm, info = await core.getPropNorm('test:str', 1234)
            self.eq(norm, '1234')
            self.eq(info, {})

            intt = core.model.type('test:int')
            lowt = core.model.type('test:lower')
            enfo = {'subs': {'hehe': (intt.typehash, 1234, {}),
                             'haha': (lowt.typehash, '1234', {})},
                    'adds': (('test:int', 1234, {}),)}

            norm, info = await core.getPropNorm('test:comp', ('1234', '1234'))
            self.eq(norm, (1234, '1234'))
            self.eq(info, enfo)

            await self.asyncraises(s_exc.BadTypeValu, core.getPropNorm('test:int', 'newp'))
            await self.asyncraises(s_exc.NoSuchProp, core.getPropNorm('test:newp', 'newp'))

            norm, info = await prox.getPropNorm('test:str', 1234)
            self.eq(norm, '1234')
            self.eq(info, {})

            norm, info = await prox.getPropNorm('test:comp', ('1234', '1234'))
            self.eq(norm, (1234, '1234'))
            self.eq(info, enfo)

            await self.asyncraises(s_exc.BadTypeValu, prox.getPropNorm('test:int', 'newp'))
            await self.asyncraises(s_exc.NoSuchProp, prox.getPropNorm('test:newp', 'newp'))

            # getTypeNorm base tests
            norm, info = await core.getTypeNorm('test:str', 1234)
            self.eq(norm, '1234')
            self.eq(info, {})

            norm, info = await core.getTypeNorm('test:comp', ('1234', '1234'))
            self.eq(norm, (1234, '1234'))
            self.eq(info, enfo)

            await self.asyncraises(s_exc.BadTypeValu, core.getTypeNorm('test:int', 'newp'))
            await self.asyncraises(s_exc.NoSuchType, core.getTypeNorm('test:newp', 'newp'))

            norm, info = await prox.getTypeNorm('test:str', 1234)
            self.eq(norm, '1234')
            self.eq(info, {})

            norm, info = await prox.getTypeNorm('test:comp', ('1234', '1234'))
            self.eq(norm, (1234, '1234'))
            self.eq(info, enfo)

            await self.asyncraises(s_exc.BadTypeValu, prox.getTypeNorm('test:int', 'newp'))
            await self.asyncraises(s_exc.NoSuchType, prox.getTypeNorm('test:newp', 'newp'))

            # getPropNorm can norm sub props
            norm, info = await core.getPropNorm('test:str:tick', '3001')
            self.eq(norm, ('test:time', 32535216000000000))
            self.eq(info, {})
            # but getTypeNorm won't handle that
            await self.asyncraises(s_exc.NoSuchType, core.getTypeNorm('test:str:tick', '3001'))

            # specify typeopts to getTypeNorm/getPropNorm
            norm, info = await prox.getTypeNorm('array', ('  TIME   ', '   pass   ', '   the  '), typeopts={'uniq': True, 'sorted': True, 'type': 'test:lower'})
            self.eq(norm, (('test:lower', 'pass'), ('test:lower', 'the'), ('test:lower', 'time')))

            norm, info = await prox.getPropNorm('test:comp', "1234:comedy", typeopts={'sepr': ':'})
            self.eq(norm, (1234, "comedy"))

            # getTypeNorm can norm types which aren't defined as forms/props
            norm, info = await core.getTypeNorm('test:lower', 'ASDF')
            self.eq(norm, 'asdf')
            # but getPropNorm won't handle that
            await self.asyncraises(s_exc.NoSuchProp, core.getPropNorm('test:lower', 'ASDF'))

    async def test_addview(self):
        async with self.getTestCore() as core:
            visi = await core.auth.addUser('visi')

            (await core.addLayer()).get('iden')
            deflayr = (await core.getLayerDef()).get('iden')

            vdef = {'layers': (deflayr,)}
            view = (await core.addView(vdef)).get('iden')
            self.nn(core.getView(view))
            self.false(visi.allowed(('view', 'read'), gateiden=view))

            vdef['worldreadable'] = True
            view = (await core.addView(vdef)).get('iden')
            self.nn(core.getView(view))
            self.true(visi.allowed(('view', 'read'), gateiden=view))

            # Missing layers
            vdef = {'name': 'mylayer'}
            await self.asyncraises(s_exc.SchemaViolation, core.addView(vdef))

            # Layer not a string
            vdef = {'layers': (123,)}
            await self.asyncraises(s_exc.SchemaViolation, core.addView(vdef))

    async def test_view_setlayers(self):

        async with self.getTestCore() as core:

            self.len(1, await core.nodes('[ test:str=deflayr ]'))

            newlayr = (await core.addLayer()).get('iden')
            deflayr = (await core.getLayerDef()).get('iden')

            vdef = {'layers': (deflayr,)}
            view = (await core.addView(vdef)).get('iden')

            opts = {'view': view}
            self.len(1, await core.nodes('test:str=deflayr', opts=opts))

            await core.setViewLayers((newlayr, deflayr), iden=view)

            self.len(1, await core.nodes('[ test:str=newlayr ]', opts=opts))
            self.len(0, await core.nodes('test:str=newlayr'))

    async def test_view_set_parent(self):
        async with self.getTestCore() as core:

            layer1 = (await core.addLayer()).get('iden')
            layer2 = (await core.addLayer()).get('iden')
            layer3 = (await core.addLayer()).get('iden')
            layer4 = (await core.addLayer()).get('iden')

            videna = (await core.addView(
                {'layers': (layer1,)}
            )).get('iden')

            videnb = (await core.addView(
                {'layers': (layer2, layer3)}
            )).get('iden')

            videnc = (await core.addView(
                {'layers': (layer4,)}
            )).get('iden')

            viewa = core.getView(videna)
            viewb = core.getView(videnb)

            self.len(1, viewa.layers)
            self.len(2, viewb.layers)

            await viewa.setViewInfo('parent', videnb)

            # Make sure View A has all the layers we expect it to have - one
            # from itself and two from View B. Also make sure they're in the
            # order we expect.
            self.len(3, viewa.layers)
            self.eq(layer1, viewa.layers[0].iden)
            self.eq(layer2, viewa.layers[1].iden)
            self.eq(layer3, viewa.layers[2].iden)

            self.len(2, viewb.layers)

            # This fails because viewb has more than one layer
            with self.raises(s_exc.BadArg):
                await viewb.setViewInfo('parent', videnc)

    async def test_cortex_storm_lib_dmon(self):

        with self.getTestDir() as dirn:

            async with self.getTestCoreAndProxy(dirn=dirn) as (core, prox):
                nodes = await core.nodes('''

                    $lib.print(hi)

                    $tx = $lib.queue.add(tx)
                    $rx = $lib.queue.add(rx)

                    $ddef = $lib.dmon.add(${

                        $rx = $lib.queue.byname(tx)
                        $tx = $lib.queue.byname(rx)

                        $ip = nope
                        for ($offs, $ip) in $rx.gets(wait=1) {
                            [ inet:ip=$ip ]
                            $rx.cull($offs)
                            $tx.put($ip)
                        }
                    })

                    $tx.put(1.2.3.4)

                    for ($xoff, $xpv4) in $rx.gets(size=1, wait=1) { }

                    $lib.print(xed)

                    inet:ip=$xpv4

                    $lib.dmon.del($ddef.iden)

                    $lib.queue.del($tx.iden)
                    $lib.queue.del($rx.iden)
                ''')
                self.len(1, nodes)
                self.len(0, await prox.getStormDmons())

                with self.raises(s_exc.NoSuchIden):
                    await core.nodes('$lib.dmon.del(newp)')

                await core.stormlist('auth.user.add user')
                user = await core.auth.getUserByName('user')
                asuser = {'user': user.iden}

                ddef = await core.callStorm('return($lib.dmon.add(${$lib.print(foo)}))')
                self.isinstance(ddef, dict)
                iden = ddef.get('iden')
                asuser['vars'] = {'iden': iden}

                with self.raises(s_exc.AuthDeny):
                    await core.callStorm('$lib.dmon.del($iden)', opts=asuser)

                # remove the dmon without a nexus entry to verify recover works
                await core._delStormDmon(iden)
                self.none(await core.callStorm('return($lib.dmon.get($iden))', opts=asuser))
                self.eq('storm:dmon:add', (await core.nexsroot.nexslog.last())[1][1])

            async with self.getTestCoreAndProxy(dirn=dirn) as (core, prox):

                self.nn(await core.callStorm('return($lib.dmon.get($iden))', opts=asuser))
                self.nn(core.stormdmondefs.get(iden))

    async def test_cortex_storm_dmon_view(self):

        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                # twiddle the dmon manager
                self.true(core.stormdmons.enabled)
                await core.stormdmons.stop()
                await core.stormdmons.start()
                self.len(1, await core.nodes('[test:int=1]'))
                await core.nodes('$q=$lib.queue.add(dmon)')
                vdef2 = await core.view.fork()
                view2_iden = vdef2.get('iden')

                q = '''
                $lib.dmon.add(${
                    $q = $lib.queue.byname(dmon)
                    for ($offs, $item) in $q.gets(size=3, wait=12)
                        {
                            [ test:int=$item ]
                            $lib.print(`made {$node.ndef}`)
                            $q.cull($offs)
                        }
                    }, name=viewdmon)
                '''
                await core.nodes(q, opts={'view': view2_iden})

                q = '''$q = $lib.queue.byname(dmon) $q.puts((1, 3, 5))'''
                with self.getLoggerStream('synapse.lib.storm') as stream:
                    await core.nodes(q)
                    await stream.expect("made ('test:int', 5)", timeout=6)

                nodes = await core.nodes('test:int', opts={'view': view2_iden})
                self.len(3, nodes)
                nodes = await core.nodes('test:int')
                self.len(1, nodes)

                visi = await core.auth.addUser('visi')
                await visi.setAdmin(True)
                await visi.setProfileValu('cortex:view', view2_iden)

                await core.nodes('$q=$lib.queue.add(dmon2)')
                q = '''
                $q = $lib.queue.byname(dmon2)
                for ($offs, $item) in $q.gets(size=3, wait=12) {
                    [ test:str=$item ]
                    $lib.print(`made {$node.ndef}`)
                    $q.cull($offs)
                }
                '''
                ddef = {'user': visi.iden, 'storm': q, 'iden': s_common.guid()}
                await core.addStormDmon(ddef)

                with self.raises(s_exc.DupIden):
                    await core.addStormDmon(ddef)

                q = '''$q = $lib.queue.byname(dmon2) $q.puts((1, 3, 5))'''
                with self.getLoggerStream('synapse.lib.storm') as stream:
                    await core.nodes(q)
                    await stream.expect("made ('test:str', '5')", timeout=6)

                nodes = await core.nodes('test:str', opts={'view': view2_iden})
                self.len(3, nodes)
                nodes = await core.nodes('test:str')
                self.len(0, nodes)

                # Kill the dmon and remove view2
                await core.stormdmons.stop()

                await core.delView(view2_iden)
                with self.raises(s_exc.NoSuchView):
                    await core.nodes('test:int', opts={'view': view2_iden})

            with self.getLoggerStream('synapse.lib.storm') as stream:
                async with self.getTestCore(dirn=dirn) as core:
                    await stream.expect('Dmon View is invalid. Stopping Dmon', timeout=6)
                    msgs = await core.stormlist('dmon.list')
                    self.stormIsInPrint('fatal error: invalid view', msgs)

    async def test_cortex_storm_dmon_add_view(self):

        async with self.getTestCore() as core:

            await core.nodes('$lib.queue.add(dmon)')
            vdef2 = await core.view.fork()
            view2_iden = vdef2.get('iden')

            # Specify an alternate view via ddef and verify stormopts.view is set
            dmonq = '''
                $q = $lib.queue.byname(dmon)
                for ($offs, $item) in $q.gets(size=3, wait=12) {
                    [ test:int=$item ]
                    $lib.print(`made {$node.ndef}`)
                    $q.cull($offs)
                }
            '''
            ddef = await core.callStorm(
                'return($lib.dmon.add($storm, name=viewdmon, ddef=({"stormopts": {"view": $view}})))',
                opts={'vars': {'storm': dmonq, 'view': view2_iden}},
            )
            self.eq(ddef['stormopts']['view'], view2_iden)

            await asyncio.sleep(0)

            q = '''$q = $lib.queue.byname(dmon) $q.puts((10, 20, 30))'''
            with self.getLoggerStream('synapse.lib.storm') as stream:
                await core.nodes(q)
                await stream.expect("made ('test:int', 30)")

            # Nodes should be in the forked view
            nodes = await core.nodes('test:int', opts={'view': view2_iden})
            self.len(3, nodes)

            # Nodes should not be in the default view
            nodes = await core.nodes('test:int')
            self.len(0, nodes)

            # Specifying an invalid view raises NoSuchView
            with self.raises(s_exc.NoSuchView):
                await core.callStorm(
                    '$lib.dmon.add($storm, name=baddmon, ddef=({"stormopts": {"view": $view}}))',
                    opts={'vars': {'storm': '$lib.print(hi)', 'view': 'newp'}},
                )

            # Verify permission check uses the specified view gateiden
            visi = await core.auth.addUser('visi')
            await visi.addRule((True, ('dmon', 'add')), gateiden=core.view.iden)

            async with core.getLocalProxy(user='visi') as proxy:
                # visi has dmon.add on default view but not on view2
                with self.raises(s_exc.AuthDeny):
                    await proxy.callStorm(
                        '$lib.dmon.add($storm, name=testperm, ddef=({"stormopts": {"view": $view}}))',
                        opts={'vars': {'storm': '$lib.print(hi)', 'view': view2_iden}},
                    )

                # Grant on view2 and it should work
                await visi.addRule((True, ('dmon', 'add')), gateiden=view2_iden)
                await proxy.callStorm(
                    '$lib.dmon.add($storm, name=testperm, ddef=({"stormopts": {"view": $view}}))',
                    opts={'vars': {'storm': '$lib.print(hi)', 'view': view2_iden}},
                )

    async def test_cortex_storm_cmd_bads(self):

        async with self.getTestCore() as core:

            with self.raises(s_exc.BadCmdName):
                await core.setStormCmd({'name': ')(*&#$)*', 'storm': ''})

            with self.raises(s_exc.CantDelCmd):
                await core.delStormCmd('sleep')

            self.none(await core._delStormCmd('newp'))

    async def test_cortex_storm_lib_dmon_cmds(self):
        async with self.getTestCore() as core:
            await core.nodes('''
                $q = $lib.queue.add(visi)
                $lib.queue.add(boom)

                $lib.dmon.add(${
                    $lib.print('Starting wootdmon')
                    $lib.queue.byname(visi).put(blah)
                    for ($offs, $item) in $lib.queue.byname(boom).gets(wait=1) {
                        [ inet:ip=$item ]
                    }
                }, name=wootdmon)

                for ($offs, $item) in $q.gets(size=1) { $q.cull($offs) }
            ''')

            # dmon is now fully running
            msgs = await core.stormlist('dmon.list')
            self.stormIsInPrint('(wootdmon            ): running', msgs)

            dmon = list(core.stormdmons.dmons.values())[0]

            # make the dmon blow up
            await core.nodes('''
                $lib.queue.byname(boom).put(hehe)
                $q = $lib.queue.byname(visi)
                for ($offs, $item) in $q.gets(size=1) { $q.cull($offs) }
            ''')

            self.true(await s_coro.event_wait(dmon.err_evnt, 6))

            msgs = await core.stormlist('dmon.list')
            self.stormIsInPrint('(wootdmon            ): error', msgs)

            # invalid storm query
            await self.asyncraises(s_exc.BadSyntax, core.nodes('$lib.dmon.add(" | | | ")'))

    async def test_cortex_storm_dmon_exit(self):

        async with self.getTestCore() as core:

            await core.nodes('''
                $q = $lib.queue.add(visi)
                $lib.auth.users.get().vars.foo = $(10)

                $lib.dmon.add(${

                    $foo = $lib.auth.users.get().vars.foo

                    $lib.queue.byname(visi).put(step)

                    if $( $foo = 20 ) {
                        for $tick in $lib.time.ticker(10) {
                            $lib.print(woot)
                        }
                    }

                    $lib.auth.users.get().vars.foo = $(20)

                }, name=wootdmon)

            ''')
            # wait for him to exit once and loop...
            await core.nodes('for $x in $lib.queue.byname(visi).gets(size=2) {}')
            await core.stormlist('for $x in $lib.queue.byname(visi).gets(size=2) { $lib.print(hehe) }')

    async def test_cortex_ext_model(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                with self.raises(s_exc.BadFormDef):
                    await core.addForm('inet:ip', 'int', {}, {})

                with self.raises(s_exc.NoSuchForm):
                    await core.delForm('_newp')

                with self.raises(s_exc.NoSuchType):
                    await core.addForm('_inet:ip', 'foo', {}, {})

                # blowup for bad names
                with self.raises(s_exc.BadPropDef):
                    await core.addFormProp('inet:ip', 'visi', ('int', {}), {})

                with self.raises(s_exc.NoSuchForm):
                    await core.addFormProp('inet:newp', '_visi', ('int', {}), {})

                await core.addFormProp('inet:ip', '_visi', ('int', {}), {})

                nodes = await core.nodes('[inet:ip=1.2.3.4 :_visi=30 ]')
                self.len(1, nodes)

                self.len(1, await core.nodes('syn:prop:base="_visi"'))

                await core.addForm('_hehe:haha', 'int', {}, {'doc': 'The hehe:haha form.', 'deprecated': True})
                self.len(1, await core.nodes('[ _hehe:haha=10 ]'))

                with self.raises(s_exc.DupFormName):
                    await core.addForm('_hehe:haha', 'int', {}, {'doc': 'The hehe:haha form.', 'deprecated': True})

                await core.addFormProp('_hehe:haha', '_visi', ('str', {}), {})
                self.len(1, await core.nodes('_hehe:haha [ :_visi=lolz ]'))

                await core.addEdge(('inet:fqdn', '_goes', None), {})
                await core._addEdge(('inet:fqdn', '_goes', None), {})

                with self.raises(s_exc.DupEdgeType):
                    await core.addEdge(('inet:fqdn', '_goes', None), {})

                await core.addType('_test:type', 'str', {}, {'interfaces': [('meta:taxonomy', {})]})
                self.eq([('meta:taxonomy', {})], core.model.type('_test:type').info.get('interfaces'))

                with self.raises(s_exc.NoSuchType):
                    await core.addType('_test:newp', 'newp', {}, {})

                with self.raises(s_exc.BadTypeDef):
                    await core.addType('_test:newp', 'array', {'type': 'newp'}, {})

                # manually edit in borked entries
                core.exttypes.set('_type:bork', ('_type:bork', None, None, None))
                core.extforms.set('_hehe:bork', ('_hehe:bork', 'int', None, None))
                core.extedges.set(s_common.guid('newp'), ((None, '_does', 'newp'), {}))

            async with self.getTestCore(dirn=dirn) as core:

                self.none(core.model.form('_hehe:bork'))
                self.none(core.model.edge((None, '_does', 'newp')))

                self.nn(core.model.edge(('inet:fqdn', '_goes', None)))

                self.len(1, await core.nodes('_hehe:haha=10'))
                self.len(1, await core.nodes('_hehe:haha:_visi=lolz'))

                prop = core.model.prop('inet:ip:_visi')
                nodes = await core.nodes('[inet:ip=5.5.5.5 :_visi=100]')
                self.len(1, nodes)

                nodes = await core.nodes('inet:ip:_visi>30')
                self.len(1, nodes)

                self.nn(core.model.type('_test:type'))
                self.nn(core.model.prop('inet:ip:_visi'))
                self.nn(core.model.form('inet:ip').prop('_visi'))

                await core.nodes('inet:ip:_visi [ -:_visi ]')
                await core.delFormProp('inet:ip', '_visi')

                with self.raises(s_exc.NoSuchProp):
                    await core.delFormProp('inet:ip', '_visi')

                with self.raises(s_exc.CantDelProp):
                    await core.delFormProp('_hehe:haha', '_visi')

                with self.raises(s_exc.NoSuchForm):
                    await core.delForm('_hehe:newpnewp')

                with self.raises(s_exc.CantDelForm):
                    await core.delForm('_hehe:haha')

                with self.raises(s_exc.BadFormDef):
                    await core.delForm('hehe:haha')

                with self.raises(s_exc.NoSuchEdge):
                    await core.delEdge(('newp', 'newp', 'newp'))

                with self.raises(s_exc.NoSuchType):
                    await core.delType('_newp')

                await core._delEdge(('newp', 'newp', 'newp'))

                prop = core.model.prop('_hehe:haha:_visi')
                await core.nodes('_hehe:haha [ -:_visi ]')
                await core.delFormProp('_hehe:haha', '_visi')

                await core.nodes('_hehe:haha | delnode')
                await core.delForm('_hehe:haha')

                self.none(core.model.form('_hehe:haha'))
                self.none(core.model.type('_hehe:haha'))
                self.none(core.model.prop('_hehe:haha:_visi'))
                self.none(core.model.prop('inet:ip._visi'))
                self.none(core.model.form('inet:ip').prop('._visi'))

                vdef2 = await core.view.fork()
                opts = {'view': vdef2.get('iden')}

                await core.addTagProp('_added', ('time', {}), {})

                await core.nodes('inet:ip=1.2.3.4 [ +#foo.bar ]')
                await core.nodes('inet:ip=1.2.3.4 [ +#foo.bar:_added="2049" ]', opts=opts)

                with self.raises(s_exc.CantDelProp):
                    await core.delTagProp('_added')

                await core.nodes('inet:ip=1.2.3.4 [ -#foo.bar:_added ]', opts=opts)
                await core.delTagProp('_added')

                # test the remote APIs
                async with core.getLocalProxy() as prox:

                    await prox.addFormProp('inet:ip', '_blah', ('int', {}), {})
                    self.len(1, await core.nodes('inet:ip=1.2.3.4 [ :_blah=10 ]'))

                    self.len(1, await core.nodes('inet:ip=1.2.3.4 [ -:_blah ]'))
                    await prox.delFormProp('inet:ip', '_blah')

                    with self.raises(s_exc.NoSuchProp):
                        await prox.delFormProp('inet:ip', 'asn')

                    await prox.addTagProp('_added', ('time', {}), {})

                    with self.raises(s_exc.NoSuchTagProp):
                        await core.nodes('inet:ip=1.2.3.4 [ +#foo.bar:_time="2049" ]')

                    self.len(1, await core.nodes('inet:ip=1.2.3.4 [ +#foo.bar:_added="2049" ]'))

                    await core.nodes('#foo.bar [ -#foo ]')
                    await prox.delTagProp('_added')

                    await prox.addForm('_hehe:hoho', 'str', {}, {})
                    self.nn(core.model.form('_hehe:hoho'))
                    self.len(1, await core.nodes('[ _hehe:hoho=lololol ]'))

                    await core.nodes('_hehe:hoho | delnode')
                    await prox.delForm('_hehe:hoho')
                    self.none(core.model.form('_hehe:hoho'))

                    with self.raises(s_exc.BadPropDef):
                        await prox.addFormProp('test:str', '_blah:blah^blah', ('int', {}), {})
                    with self.raises(s_exc.BadPropDef):
                        await prox.addTagProp('_blah:blah^blah', ('int', {}), {})

        # Mirrors on newer model versions should not be able to add extended model elements
        # based on model elements the leader doesn't have
        async with self.getTestAha() as aha:

            conf = {'aha:provision': await aha.addAhaSvcProv('00.cortex')}
            core00 = await aha.enter_context(self.getTestCore(conf=conf))

            conf = {'aha:provision': await aha.addAhaSvcProv('01.cortex')}
            core01 = await aha.enter_context(self.getTestCore(conf=conf))

            # Add a type directly to the mirror's model to simulate different model version
            core01.model.addType('_newmodel:type', 'str', {}, {})

            with self.raises(s_exc.NoSuchType):
                await core01.addType('_test:type', '_newmodel:type', {}, {})

            await core01.sync()
            self.none(core01.model.type('_test:type'))

            with self.raises(s_exc.NoSuchType):
                await core01.addForm('_hehe:haha', '_newmodel:type', {}, {})

            await core01.sync()
            self.none(core01.model.form('_hehe:haha'))

            with self.raises(s_exc.NoSuchType):
                await core01.addFormProp('inet:asn', '_newer', ('_newmodel:type', {}), {})

            await core01.sync()
            self.none(core01.model.prop('inet:asn:_newer'))

            with self.raises(s_exc.NoSuchType):
                await core01.addTagProp('_user', ('_newmodel:type', {}), {})

            await core01.sync()
            self.none(core01.model.tagprop('_user'))

            core01.model.addForm('_newmodel:type', {}, {})

            with self.raises(s_exc.NoSuchForm):
                await core01.addEdge(('_newmodel:type', '_foo', None), {})

            await core01.sync()
            self.none(core01.model.edge(('_newmodel:type', '_foo', None)))

    async def test_cortex_axon(self):
        async with self.getTestCore() as core:
            # By default, a cortex has a local Axon instance available
            await core.getAxon()
            size, sha2 = await (await core.getAxon()).put(b'asdfasdf')
            self.eq(size, 8)
            self.eq(s_common.ehex(sha2), '2413fb3709b05939f04cf2e92f7d0897fc2596f9ad0b8a9ea855c7bfebaae892')
        self.true(core._has_axon.isfini)

        with self.getTestDir() as dirn:

            async with self.getTestAha() as aha:

                # an AHA deployed cortex locates a remote axon by cell type. the
                # ClientV2 axon client connects ( and reconnects ) on its own.
                async with self.addSvcToAha(aha, '00.axon', s_axon.Axon, dirn=dirn) as axon, \
                        self.addSvcToAha(aha, '00.jsonstor', s_jsonstor.JsonStorCell), \
                        self.addSvcToAha(aha, '00.cortex', s_cortex.Cortex) as core:

                    # Use dyncalls, not direct object access.
                    asdfhash_h = '2413fb3709b05939f04cf2e92f7d0897fc2596f9ad0b8a9ea855c7bfebaae892'
                    size, sha2 = await core.callStorm('return( $lib.axon.put($buf) )',
                                                      {'vars': {'buf': b'asdfasdf'}})
                    self.eq(size, 8)
                    self.eq(sha2, asdfhash_h)
                    self.true(await core.callStorm('return( $lib.axon.has($hash) )',
                                                   {'vars': {'hash': asdfhash_h}}))

                    # ensure the cortex can use the remote axon proxy
                    coreaxon = await core.getAxon()
                    self.eq(await axon.metrics(), await coreaxon.metrics())

    async def test_cortex_delLayerView(self):

        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:

                # Can't delete the default view
                await self.asyncraises(s_exc.SynErr, core.delView(core.view.iden))

                # Can't delete a layer in a view
                await self.asyncraises(s_exc.SynErr, core.delLayer(core.view.layers[0].iden))

                # Can't delete a nonexistent view
                await self.asyncraises(s_exc.NoSuchView, core.delView('XXX'))

                # Can't delete a nonexistent layer
                await self.asyncraises(s_exc.NoSuchLayer, core.delLayer('XXX'))

                # Fork the main view
                vdef2 = await core.view.fork()
                view2_iden = vdef2.get('iden')

                # Can't delete a view twice
                await core.delView(view2_iden)
                await self.asyncraises(s_exc.NoSuchView, core.delView(view2_iden))

                layr = await core.addLayer()
                layriden = layr['iden']
                vdef3 = {'layers': (layriden,)}
                view3_iden = (await core.addView(vdef3)).get('iden')

                opts = {'view': view3_iden}
                await core.callStorm('$lib.view.get().set(protected, (true))', opts=opts)

                await self.asyncraises(s_exc.CantDelView, core.delView(view3_iden))

                await core.callStorm('$lib.view.get().set(protected, (false))', opts=opts)

                view3 = core.getView(view3_iden)
                vdef4 = await view3.fork()

                deadlayr = view3.layers[0].iden
                view4_iden = vdef4.get('iden')
                view4 = core.getView(view4_iden)

                self.eq(view4.parent, view3)
                self.len(2, view4.layers)

                await core.auth.rootuser.setPasswd('secret')
                host, port = await core.dmon.listen('tcp://127.0.0.1:0/')
                layr2 = await core.callStorm('$layer=$lib.layer.add() return($layer)')
                varz = {'iden': layriden, 'tgt': layr2.get('iden'), 'port': port}
                opts = {'vars': varz, 'view': view3_iden}

                pullq = '$layer=$lib.layer.get($iden).addPull(`tcp://root:secret@127.0.0.1:{$port}/*/layer/{$tgt}`)'
                pushq = '$layer=$lib.layer.get($iden).addPush(`tcp://root:secret@127.0.0.1:{$port}/*/layer/{$tgt}`)'
                msgs = await core.stormlist(pullq, opts=opts)
                self.stormHasNoWarnErr(msgs)

                msgs = await core.stormlist(pushq, opts=opts)
                self.stormHasNoWarnErr(msgs)

                coros = len(core.activecoros)

                layridens = [lyr.iden for lyr in view4.layers if lyr.iden != view3.layers[0].iden]
                events = [
                    {'event': 'view:setlayers', 'info': {'iden': view4.iden, 'layers': layridens}},
                    {'event': 'view:set', 'info': {'iden': view4.iden, 'name': 'parent', 'valu': None}}
                ]
                task = core.schedCoro(s_t_utils.waitForBehold(core, events))

                await core.delView(view3_iden)
                await core.delLayer(deadlayr)

                await asyncio.wait_for(task, timeout=1)

                # push/pull activecoros have been deleted
                self.len(coros - 2, core.activecoros)

                self.none(view4.parent)
                self.len(1, view4.layers)
                self.none(core.getLayer(deadlayr))

                vdef5 = await view4.fork()
                view5 = core.getView(vdef5.get('iden'))

                usedlayr = view4.layers[0].iden
                vdef6 = {'layers': (usedlayr,)}
                view6 = core.getView((await core.addView(vdef6)).get('iden'))

                # The layer is still used by view6 (an unrelated view), so
                # delete only the view and leave the layer in place.
                await core.delView(view4_iden)
                await self.asyncraises(s_exc.LayerInUse, core.delLayer(usedlayr))

                self.none(view5.parent)
                self.len(1, view5.layers)

                self.nn(core.getLayer(usedlayr))
                self.eq([usedlayr], [lyr.iden for lyr in view6.layers])

                layrs = list(core.layers.keys())
                viewdefs = {}
                for vdef in await core.getViewDefs():
                    vdef['layers'] = [layr['iden'] for layr in vdef['layers']]
                    viewdefs[vdef['iden']] = vdef

            async with self.getTestCore(dirn=dirn) as core:
                self.sorteq(layrs, list(core.layers.keys()))

                viewdefs2 = {}
                for vdef in await core.getViewDefs():
                    vdef['layers'] = [layr['iden'] for layr in vdef['layers']]
                    viewdefs2[vdef['iden']] = vdef

                self.eq(len(viewdefs), len(viewdefs2))

                for iden, vdef in viewdefs.items():
                    self.eq(vdef, viewdefs2.get(iden))

    async def test_cortex_view_opts(self):
        '''
        Test that the view opts work
        '''
        async with self.getTestCore() as core:
            nodes = await core.nodes('[ test:int=11 ]')
            self.len(1, nodes)
            viewiden = core.view.iden

            nodes = await core.nodes('test:int=11', opts={'view': viewiden})
            self.len(1, nodes)

            with self.raises(s_exc.NoSuchView):
                await core.nodes('test:int=11', opts={'view': 'NOTAVIEW'})

    async def test_cortex_getLayer(self):
        async with self.getTestCore() as core:
            layr = core.view.layers[0]
            self.eq(layr, core.getLayer())
            self.none(core.getLayer('XXX'))

            view = core.view
            self.eq(view, core.getView())
            self.eq(view, core.getView(view.iden))
            self.none(core.getView('xxx'))

    async def test_cortex_cron_deluser(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            await visi.setAdmin(True)

            asvisi = {'user': visi.iden}
            await core.stormlist('cron.add daily@13:37 {$lib.print(woot)}', opts=asvisi)
            await core.auth.delUser(visi.iden)

            self.len(1, await core.callStorm('return($lib.cron.list())'))
            msgs = await core.stormlist('cron.list')
            self.stormIsInPrint('$lib.print(woot)', msgs)

    async def test_cortex_behold(self):
        async with self.getTestCore() as core:
            async with core.getLocalProxy() as prox:
                class TstServ(s_stormsvc.StormSvc):
                    _storm_svc_name = 'tstserv'
                    _storm_svc_vers = '0.0.2'
                    _storm_svc_pkgs = [
                        {  # type: ignore
                            'name': 'foo',
                            'version': (0, 0, 1),
                            'dependencies': {'synapse': {'version': '>=2.100.0,<3.0.0'}},
                            'modules': [],
                            'commands': []
                        }
                    ]

                async def action():
                    await asyncio.sleep(0.1)
                    await core.callStorm('return($lib.view.get().fork())')
                    await core.callStorm('return($lib.cron.add(hourly@:30, "{meta:note=*}"))')
                    tdef = {'cond': 'node:add', 'storm': '[test:str="foobar"]', 'form': 'test:int'}
                    opts = {'vars': {'tdef': tdef}}
                    trig = await core.callStorm('return($lib.trigger.add($tdef))', opts=opts)
                    opts = {'vars': {'trig': trig['iden'], 'edits': {'enabled': False}}}

                    await core.callStorm('$lib.trigger.mod($trig, $edits)', opts=opts)
                    await core.callStorm('return($lib.trigger.del($trig))', opts=opts)

                    async with self.getTestDmon() as dmon:
                        dmon.share('tstservone', TstServ())
                        host, port = dmon.addr
                        surl = f'tcp://127.0.0.1:{port}/tstservone'
                        await core.callStorm(f'service.add alegitservice {surl}')
                        await core.callStorm('$lib.service.wait(alegitservice)')

                task = core.schedCoro(action())
                replay = s_common.envbool('SYNDEV_NEXUS_REPLAY')
                dlen = 9 if replay else 8

                data = []
                async for mesg in prox.behold():
                    data.append(mesg)
                    if len(data) == dlen:
                        break

                await asyncio.wait_for(task, timeout=1)
                self.eq(data[0]['event'], 'layer:add')
                self.gt(data[0]['offset'], 0)
                self.len(1, data[0]['gates'])
                self.true(type(data[0]['info']) is dict)
                self.true(type(data[0]['gates']) is tuple)
                self.len(1, data[0]['gates'])

                self.eq(data[1]['event'], 'view:add')
                self.gt(data[1]['offset'], data[0]['offset'])
                self.true(type(data[1]['info']) is dict)
                self.true(type(data[1]['gates']) is tuple)
                self.len(1, data[1]['gates'])

                self.eq(data[2]['event'], 'cron:add')
                self.gt(data[2]['offset'], data[1]['offset'])
                self.true(type(data[2]['info']) is dict)
                self.true(type(data[2]['gates']) is tuple)
                self.len(1, data[2]['gates'])

                view = await core.callStorm('return($lib.view.get().iden)')

                self.eq(data[3]['event'], 'trigger:add')
                self.gt(data[3]['offset'], data[2]['offset'])
                self.len(1, data[3]['gates'])
                self.false(data[3]['info']['async'])
                self.eq(data[3]['info']['cond'], 'node:add')
                self.true(data[3]['info']['enabled'])
                self.eq(data[3]['info']['form'], 'test:int')
                self.eq(data[3]['info']['storm'], '[test:str="foobar"]')
                self.eq(data[3]['info']['username'], 'root')
                self.eq(data[3]['info']['view'], view)

                self.eq(data[4]['event'], 'trigger:set')
                self.gt(data[4]['offset'], data[3]['offset'])
                self.len(1, data[4]['gates'])
                self.eq(data[4]['info']['name'], 'enabled')
                self.false(data[4]['info']['valu'])
                self.eq(data[4]['info']['view'], view)

                off = 5
                if replay:
                    self.eq(data[off]['event'], 'trigger:set')
                    self.gt(data[off]['offset'], data[3]['offset'])
                    self.len(1, data[off]['gates'])
                    self.eq(data[off]['info']['name'], 'enabled')
                    self.false(data[off]['info']['valu'])
                    self.eq(data[off]['info']['view'], view)
                    off += 1

                self.eq(data[off]['event'], 'trigger:del')
                self.gt(data[off]['offset'], data[4]['offset'])
                self.len(1, data[off]['gates'])
                self.nn(data[off]['info'].get('iden'))
                self.eq(data[off]['info']['view'], view)
                off += 1

                self.eq(data[off]['event'], 'svc:add')
                self.eq(data[off]['info']['name'], 'alegitservice')
                off += 1

                self.eq(data[off]['event'], 'svc:set')
                self.eq(data[off]['info']['name'], 'alegitservice')
                self.eq(data[off]['info']['svcname'], 'tstserv')
                self.eq(data[off]['info']['version'], '0.0.2')
                self.eq(data[off]['info']['iden'], data[off - 1]['info']['iden'])

    async def test_stormpkg_sad(self):
        base_pkg = {
            'name': 'boom',
            'desc': 'The boom Module',
            'version': (0, 0, 1),
            'dependencies': {'synapse': {'version': '>=3.0.0b3,<4.0.0'}},
            'modules': [
                {
                    'name': 'boom.mod',
                    'storm': '''
                    function f(a) {return ($a)}
                    ''',
                },
            ],
            'commands': [
                {
                    'name': 'boom.cmd',
                    'storm': '''
                    $boomlib = $lib.import(boom.mod)
                    $retn = $boomlib.f($arg)
                    ''',
                },
            ],
        }
        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                pkg = copy.deepcopy(base_pkg)
                pkg.pop('name')
                with self.raises(s_exc.SchemaViolation) as cm:
                    await core.addStormPkg(pkg)
                self.eq(cm.exception.errinfo.get('mesg'),
                        "data must contain ['name'] properties")

                pkg = copy.deepcopy(base_pkg)
                pkg.pop('version')
                with self.raises(s_exc.SchemaViolation) as cm:
                    await core.addStormPkg(pkg)
                self.eq(cm.exception.errinfo.get('mesg'),
                        "data must contain ['version'] properties")

                pkg = copy.deepcopy(base_pkg)
                pkg['modules'][0].pop('name')
                with self.raises(s_exc.SchemaViolation) as cm:
                    await core.addStormPkg(pkg)
                self.eq(cm.exception.errinfo.get('mesg'),
                        "data.modules[0] must contain ['name'] properties")

                pkg = copy.deepcopy(base_pkg)
                pkg['commands'][0]['cmdargs'] = ((
                    '--debug',
                    {'default': False},
                    {'help': 'Words'},
                ),)
                with self.raises(s_exc.SchemaViolation) as cm:
                    await core.addStormPkg(pkg)
                self.eq(cm.exception.errinfo.get('mesg'),
                        "data.commands[0].cmdargs[0] must contain only specified items")

                pkg = copy.deepcopy(base_pkg)
                pkg['configvars'] = (
                    {'name': 'foo', 'varname': 'foo', 'desc': 'foo', 'scopes': ['self'],
                     'type': 'newp'},
                )
                with self.raises(s_exc.NoSuchType) as cm:
                    await core.addStormPkg(pkg)
                self.eq(cm.exception.errinfo.get('mesg'),
                        "Storm package boom has unknown config var type newp.")

                pkg = copy.deepcopy(base_pkg)
                pkg['configvars'] = (
                    {'name': 'foo', 'varname': 'foo', 'desc': 'foo', 'scopes': ['self'],
                     'type': ['inet:fqdn', ['str', 'newp']]},
                )
                with self.raises(s_exc.NoSuchType) as cm:
                    await core.addStormPkg(pkg)
                self.eq(cm.exception.errinfo.get('mesg'),
                        "Storm package boom has unknown config var type newp.")

    async def test_stormpkg_deps(self):

        async with self.getTestCore() as core:

            # a dependencies.synapse entry whose version spec matches the running
            # synapse version loads fine
            pkg = {
                'name': 'depsynok',
                'version': (0, 0, 1),
                'dependencies': {
                    'synapse': {'version': '>=3.0.0b1,<4.0.0'},
                },
            }
            await core.addStormPkg(pkg)
            self.nn(await core.getStormPkg('depsynok'))

            # a dependencies.synapse entry whose version spec does NOT match the
            # running synapse version raises StormPkgRequires
            pkg = {
                'name': 'depsynbad',
                'version': (0, 0, 1),
                'dependencies': {
                    'synapse': {'version': '>=1337.0.0,<2000.0.0'},
                },
            }
            with self.raises(s_exc.StormPkgRequires):
                await core.addStormPkg(pkg)
            self.none(await core.getStormPkg('depsynbad'))

            # a non-optional dependency on a package that is not loaded raises
            # StormPkgRequires
            pkg = {
                'name': 'depmissing',
                'version': (0, 0, 1),
                'dependencies': {
                    'notloaded': {'version': '>=1.0.0'},
                },
            }
            with self.raises(s_exc.StormPkgRequires):
                await core.addStormPkg(pkg)
            self.none(await core.getStormPkg('depmissing'))

            # the same missing dependency marked optional loads successfully
            pkg = {
                'name': 'depmissingopt',
                'version': (0, 0, 1),
                'dependencies': {
                    'notloaded': {'version': '>=1.0.0', 'optional': True},
                },
            }
            await core.addStormPkg(pkg)
            self.nn(await core.getStormPkg('depmissingopt'))

            # a conflict entry that matches an already loaded package's version
            # raises StormPkgConflicts
            confbase = {
                'name': 'confbase',
                'version': '1.2.3',
            }
            await core.addStormPkg(confbase)

            pkg = {
                'name': 'confpkg',
                'version': (0, 0, 1),
                'conflicts': {
                    'confbase': {'version': '>=1.0.0,<2.0.0'},
                },
            }
            with self.raises(s_exc.StormPkgConflicts):
                await core.addStormPkg(pkg)
            self.none(await core.getStormPkg('confpkg'))

            # the base Cortex only PKG_PROVIDES the reserved "synapse" name; a
            # dependency on "synapse-enterprise" (an enterprise-only reserved
            # name) is treated as an unloaded package and raises
            # StormPkgRequires rather than resolving to the running version
            self.eq(('synapse',), core.PKG_PROVIDES)

            pkg = {
                'name': 'depsynentnotprovided',
                'version': (0, 0, 1),
                'dependencies': {
                    'synapse-enterprise': {'version': '>=3.0.0b3,<4.0.0'},
                },
            }
            with self.raises(s_exc.StormPkgRequires):
                await core.addStormPkg(pkg)
            self.none(await core.getStormPkg('depsynentnotprovided'))

    async def test_stormpkg_schema(self):

        pkgdef = {
            'name': 'schemapkg',
            'version': '0.0.1',
            'title': 'A Schema Test Power-Up',
            'dependencies': {
                'synapse': {'version': '>=3.0.0b1,<4.0.0'},
                'other': {'version': '>=1.0.0', 'optional': True, 'desc': 'an optional dep'},
            },
            'conflicts': {
                'legacy': {'version': '<1.0.0', 'desc': 'an old conflicting pkg'},
            },
        }
        s_schemas.reqValidPkgdef(pkgdef)

    async def test_cortex_view_persistence(self):
        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                view = core.view
                NKIDS = 3
                for _ in range(NKIDS):
                    await view.fork()

                self.len(NKIDS + 1, core.layers)

            async with self.getTestCore(dirn=dirn) as core:
                self.len(NKIDS + 1, core.layers)
                for view in core.views.values():
                    if view == core.view:
                        continue
                    self.eq(core.view, view.parent)

    async def test_cortex_vars(self):

        async with self.getTestCore() as core:

            await core.auth.addUser('visi')
            async with core.getLocalProxy(user='visi') as proxy:
                with self.raises(s_exc.AuthDeny):
                    await proxy.setStormVar('hehe', 'haha')
                with self.raises(s_exc.AuthDeny):
                    await proxy.getStormVar('hehe')
                with self.raises(s_exc.AuthDeny):
                    await proxy.popStormVar('hehe')

            async with core.getLocalProxy() as proxy:
                self.eq('haha', await proxy.setStormVar('hehe', 'haha'))
                self.eq('haha', await proxy.getStormVar('hehe'))
                self.eq('hoho', await proxy.getStormVar('lolz', default='hoho'))
                self.eq('haha', await proxy.popStormVar('hehe'))
                self.eq('hoho', await proxy.popStormVar('lolz', default='hoho'))

    async def test_cortex_all_layr_read(self):
        async with self.getTestCore() as core:
            layr = core.getView().layers[0].iden
            visi = await core.auth.addUser('visi')
            # the default layer is a member of the worldreadable default view, so
            # any user can read it without a standalone layer read permission.
            self.true(core.userCanReadLayer(visi, layr))

    async def test_cortex_export(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            await visi.setPasswd('secret')

            await core.auth.rootuser.setPasswd('secret')

            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            altview = await core.callStorm('$layr = $lib.layer.add() return($lib.view.add(layers=($layr.iden,)).iden)')

            await core.addTagProp('_user', ('str', {}), {'doc': 'real nice tagprop ya got there'})
            await core.addTagProp('_rank', ('int', {}), {'doc': 'be a shame if'})
            await core.addTagProp('_file', ('file:path', {}), {'doc': 'something happened to it'})

            await core.nodes('[ inet:email=visi@vertex.link +#visi.woot:_rank=43 +#foo.bar:_user=vertex ]')
            await core.nodes('[ inet:fqdn=hehe.com ]')
            await core.nodes('[doc:report = * :title="Vertex Project Winning" +#visi:_file="/foo/bar/baz" +#visi.woot:_rank=1 +(refs)> { inet:email=visi@vertex.link inet:fqdn=hehe.com }]')

            async with core.getLocalProxy() as proxy:

                opts = {}
                podes = []

                async for p in proxy.exportStorm('doc:report inet:email', opts=opts):
                    if not podes:
                        tasks = [t for t in core.boss.tasks.values() if t.name == 'storm:export']
                        self.true(len(tasks) == 1 and tasks[0].info.get('view') == core.view.iden)
                    podes.append(p)

                meta = podes.pop(0)
                iden = core.auth.rootuser.iden
                created = meta['created']
                self.eq(meta, {
                    'type': 'meta',
                    'vers': 1,
                    'forms': {'doc:report': 1, 'inet:email': 1},
                    'edges': {'doc:report': {'refs': ('inet:email',)}},
                    'count': 2,
                    'creatorname': 'root',
                    'creatoriden': iden,
                    'created': created,
                    'synapse_ver': s_version.version,
                    'query': 'doc:report inet:email'
                })

                self.len(2, podes)
                news = [p for p in podes if p[0][0] == 'doc:report'][0]
                email = [p for p in podes if p[0][0] == 'inet:email'][0]

                self.nn(email[1]['tags']['visi'])
                self.nn(email[1]['tags']['visi.woot'])
                self.nn(email[1]['tags'].get('foo'))
                self.nn(email[1]['tags'].get('foo.bar'))
                self.len(2, email[1]['tagprops'])
                self.eq(email[1]['tagprops'], {'foo.bar': {'_user': 'vertex'}, 'visi.woot': {'_rank': 43}})
                self.len(2, news[1]['tagprops'])
                self.eq(news[1]['tagprops'], {'visi': {'_file': '/foo/bar/baz'}, 'visi.woot': {'_rank': 1}})
                self.len(1, news[1]['edges'])
                self.eq(news[1]['edges'][0], ('refs', ('inet:email', 'visi@vertex.link')))

                # concat the bytes and add back to the axon
                byts = b''.join(s_msgpack.en(p) for p in podes)
                size, sha256b = await (await core.getAxon()).put(byts)
                sha256 = s_common.ehex(sha256b)

                opts = {'view': altview, 'vars': {'sha256': sha256}}
                with self.raises(s_exc.BadDataValu) as cm:
                    await proxy.callStorm('return($lib.feed.fromAxon($sha256))', opts=opts)
                self.isin('Invalid syn.nodes data.', cm.exception.get('mesg'))

                # try-again w/ meta node: concat the bytes and add back to the axon
                byts = s_msgpack.en(meta) + b''.join(s_msgpack.en(p) for p in podes)
                size, sha256b = await (await core.getAxon()).put(byts)
                sha256 = s_common.ehex(sha256b)
                opts['vars']['sha256'] = sha256

                self.eq(2, await proxy.callStorm('return($lib.feed.fromAxon($sha256))', opts=opts))
                self.len(1, await core.nodes('doc:report -(refs)> *', opts={'view': altview}))
                self.eq(2, await proxy.feedFromAxon(sha256))

                opts['limit'] = 1
                self.len(2, await alist(proxy.exportStorm('doc:report inet:email', opts=opts)))

            # the storm/export API is restricted to X-API-KEY authentication only
            visikey, _ = await core.addUserApiKey(visi.iden, 'export')
            rootkey, _ = await core.addUserApiKey(core.auth.rootuser.iden, 'export')

            async with self.getHttpSess(port=port) as sess:
                resp = await sess.post(f'https://localhost:{port}/api/v3/storm/export')
                self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)

                # a session cookie does not grant access to the storm/export API
                async with sess.post(f'https://localhost:{port}/api/v3/login',
                                     json={'user': 'root', 'passwd': 'secret'}) as resp:
                    self.eq('ok', (await resp.json()).get('status'))

                async with sess.post(f'https://localhost:{port}/api/v3/storm/export',
                                     json={'query': 'doc:report inet:email'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)

            async with self.getHttpSess(port=port) as sess:
                # impersonation by a non-admin is denied
                body = {'query': 'inet:ip', 'opts': {'user': core.auth.rootuser.iden}}
                async with sess.get(f'https://localhost:{port}/api/v3/storm/export', json=body,
                                    headers={'X-API-KEY': visikey}) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)

            async with self.getHttpSess(port=port) as sess:
                headers = {'X-API-KEY': rootkey}

                resp = await sess.post(f'https://localhost:{port}/api/v3/storm/export', headers=headers)
                self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                reply = await resp.json()
                self.eq('err', reply.get('status'))
                self.eq('SchemaViolation', reply.get('code'))

                body = {'query': 'doc:report inet:email'}
                resp = await sess.post(f'https://localhost:{port}/api/v3/storm/export', json=body, headers=headers)
                self.eq(resp.status, http.HTTPStatus.OK)
                byts = await resp.read()

                podes = [i[1] for i in s_msgpack.Unpk().feed(byts)]
                meta = podes.pop(0)
                self.eq(meta['edges'], {'doc:report': {'refs': ('inet:email',)}})

                news = [p for p in podes if p[0][0] == 'doc:report'][0]
                email = [p for p in podes if p[0][0] == 'inet:email'][0]

                self.nn(email[1]['tags']['visi'])
                self.nn(email[1]['tags']['visi.woot'])
                self.nn(email[1]['tags'].get('foo'))
                self.nn(email[1]['tags'].get('foo.bar'))
                self.len(1, news[1]['edges'])
                self.eq(news[1]['edges'][0], ('refs', ('inet:email', 'visi@vertex.link')))

                body = {'query': 'inet:ip=asdfasdf'}
                resp = await sess.post(f'https://localhost:{port}/api/v3/storm/export', json=body, headers=headers)
                retval = await resp.json()
                self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                self.eq('err', retval['status'])
                self.eq('BadTypeValu', retval['code'])

            async def boom(*args, **kwargs):
                for x in (): yield x
                raise s_exc.BadArg()

            core._has_axon.iterMpkFile = boom
            with self.raises(s_exc.BadArg):
                await core.feedFromAxon(s_common.ehex(sha256b))

    async def test_cortex_feed_remote_axon(self):

        async with self.getTestCoreProv() as (core, axon, jsonstor):
            await core.auth.rootuser.setPasswd('root')
            host, port = await core.dmon.listen('tcp://127.0.0.1:0')
            curl = f'tcp://root:root@127.0.0.1:{port}/*'

            test_data = b'foobar'
            size, sha256b = await axon.put(test_data)
            sha256 = s_common.ehex(sha256b)
            opts = {'vars': {'sha256': sha256}}

            async with await s_telepath.ClientV2.anit(curl) as client_obj:
                proxy = await client_obj.proxy()
                with self.raises(s_exc.BadDataValu) as cm:
                    await proxy.callStorm('$lib.feed.fromAxon($sha256)', opts=opts)
                self.isin('Invalid syn.nodes data.', cm.exception.get('mesg'))

    async def test_cortex_export_toaxon(self):
        async with self.getTestCore() as core:
            await core.nodes('[inet:dns:a=(vertex.link, 1.2.3.4)]')
            size, sha256 = await core.exportStormToAxon('.created')
            byts = b''.join([b async for b in (await core.getAxon()).get(s_common.uhex(sha256))])
            self.isin(b'vertex.link', byts)

    async def test_cortex_export_metadata(self):

        async with self.getTestCore() as core:
            rootiden = core.auth.rootuser.iden
            with self.raises(s_exc.BadVersion) as cexc:
                meta = {'type': 'meta', 'vers': 2, 'forms': {}, 'count': 0, 'synapse_ver': '3.0.0',
                        'creatorname': 'root', 'creatoriden': rootiden, 'created': 1710000000000}
                await core.reqValidExportStormMeta(meta)
            self.isin('Unsupported export version', cexc.exception.get('mesg'))

            with self.raises(s_exc.BadVersion) as cexc:
                meta = {'type': 'meta', 'vers': 1, 'forms': {}, 'count': 0, 'synapse_ver': '3abc',
                        'creatorname': 'root', 'creatoriden': rootiden, 'created': 1710000000000}
                await core.reqValidExportStormMeta(meta)
            self.isin('Malformed synapse version', cexc.exception.get('mesg'))

    async def test_cortex_lookup_mode(self):
        async with self.getTestCoreAndProxy() as (_core, proxy):
            retn = await proxy.count('[inet:email=foo.com@vertex.link]')
            self.eq(1, retn)

            opts = {'mode': 'lookup'}
            retn = await proxy.count('foo.com@vertex.link', opts=opts)
            self.eq(1, retn)

    async def test_tag_model(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            asvisi = {'user': visi.iden}

            self.len(0, await core.callStorm('return($lib.model.tags.list())'))

            self.none(await core.callStorm('return($lib.model.tags.get(foo.bar))'))
            self.none(await core.callStorm('return($lib.model.tags.pop(foo.bar, regex))'))

            with self.raises(s_exc.SchemaViolation):
                await core.nodes('$lib.model.tags.set(cno.cve, newp, newp)')

            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.model.tags.set(cno.cve, regex, ())', opts=asvisi)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.model.tags.pop(cno.cve, regex)', opts=asvisi)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.model.tags.del(cno.cve)', opts=asvisi)

            await core.nodes('''
                $regx = ((null), (null), "[0-9]{4}", "[0-9]{5}")
                $lib.model.tags.set(cno.cve, regex, $regx)
            ''')

            nodes = await core.nodes('[ inet:ip=1.2.3.4 +#cno.cve.2021.12345 ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ inet:ip=1.2.3.4 +#cno.cve.foo ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ inet:ip=1.2.3.4 +#cno.cve.2021.hehe ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ inet:ip=1.2.3.4 +#cno.cve.2021.123456 ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ inet:ip=1.2.3.4 +#cno.cve.12345 ]')

            nodes = await core.nodes('[ test:str=beep +?#cno.cve.12345 ]')
            self.len(1, nodes)
            self.none(nodes[0].get('#cno'))
            self.none(nodes[0].get('#cno.cve'))
            self.none(nodes[0].get('#cno.cve.12345'))

            self.eq((None, None, '[0-9]{4}', '[0-9]{5}'), await core.callStorm('''
                return($lib.model.tags.pop(cno.cve, regex))
            '''))

            self.none(await core.callStorm('return($lib.model.tags.pop(cno.cve, regex))'))

            await core.nodes('[ inet:ip=1.2.3.4 +#cno.cve.2021.hehe ]')

            await core.setTagModel('cno.cve', 'regex', (None, None, '[0-9]{4}', '[0-9]{5}'))
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ inet:ip=1.2.3.4 +#cno.cve.2021.haha ]')

            ok, valu = await core.callStorm('return($lib.trycast(syn:tag, cno.cve.2021.haha))')
            self.false(ok)
            self.eq(valu['err'], 'BadTypeValu')
            self.true(valu['errfile'].endswith('synapse/lib/types.py'))
            self.eq(valu['errinfo'], {
                'mesg': 'Tag part (haha) of tag (cno.cve.2021.haha) does not match the tag model regex: [[0-9]{5}]',
                'name': 'syn:tag',
                'valu': 'cno.cve.2021.haha'
            })
            self.gt(valu['errline'], 0)
            self.eq(valu['errmsg'],
                    "BadTypeValu: mesg='Tag part (haha) of tag (cno.cve.2021.haha) does "
                    "not match the tag model regex: [[0-9]{5}]' name='syn:tag' "
                    "valu='cno.cve.2021.haha'"
            )

            with self.raises(s_exc.BadTypeValu):
                await core.callStorm('return($lib.cast(syn:tag, cno.cve.2021.haha))')

            self.none(await core.callStorm('$lib.model.tags.del(cno.cve)'))
            self.none(await core.callStorm('return($lib.model.tags.get(cno.cve))'))

            await core.nodes('[ inet:ip=1.2.3.4 +#cno.cve.2021.haha ]')

            # clear out the #cno.cve tags and test prune behavior.
            await core.nodes('#cno.cve [ -#cno.cve ]')

            await core.nodes('[ inet:ip=1.2.3.4 +#cno.cve.2021.12345.foo +#cno.cve.2021.55555.bar ]')

            await core.nodes('$lib.model.tags.set(cno.cve, prune, (2))')

            # test that the pruning behavior detects non-leaf boundaries
            nodes = await core.nodes('[ inet:ip=1.2.3.4 -#cno.cve.2021.55555 ]')
            self.sorteq(('cno', 'cno.cve', 'cno.cve.2021', 'cno.cve.2021.12345', 'cno.cve.2021.12345.foo'), [t[0] for t in nodes[0].getTags()])

            # double delete shouldn't prune
            nodes = await core.nodes('[ inet:ip=1.2.3.4 -#cno.cve.2021.55555 ]')
            self.sorteq(('cno', 'cno.cve', 'cno.cve.2021', 'cno.cve.2021.12345', 'cno.cve.2021.12345.foo'), [t[0] for t in nodes[0].getTags()])

            # test that the pruning behavior stops at the correct level
            nodes = await core.nodes('[ inet:ip=1.2.3.4 -#cno.cve.2021.12345.foo ]')
            self.sorteq(('cno', 'cno.cve', 'cno.cve.2021', 'cno.cve.2021.12345'), [t[0] for t in nodes[0].getTags()])

            # test that the pruning behavior detects when it needs to prune
            nodes = await core.nodes('[ inet:ip=1.2.3.4 -#cno.cve.2021.12345 ]')
            self.len(1, nodes)
            self.eq((('cno', (None, None, None)),), nodes[0].getTags())

            # test that the prune caches get cleared correctly
            await core.nodes('$lib.model.tags.pop(cno.cve, prune)')
            await core.nodes('[ inet:ip=1.2.3.4 +#cno.cve.2021.12345 ]')
            nodes = await core.nodes('[ inet:ip=1.2.3.4 -#cno.cve.2021.12345 ]')
            self.len(1, nodes)
            self.sorteq(('cno', 'cno.cve', 'cno.cve.2021'), [t[0] for t in nodes[0].getTags()])

            with self.raises(s_exc.SchemaViolation):
                await core.nodes('$lib.model.tags.set(cno.cve, prune, (0))')

    async def test_cortex_layr_read_authdeny(self):
        # CortexApi/LayerApi layer reads are gated by Cortex.reqUserCanReadLayer;
        # a non-admin user who cannot read a layer (its view is not readable to
        # them, and they are not an admin of the layer's gate) is denied.
        async with self.getTestCore() as core:
            # the fork view (created by root) is not worldreadable, so visi cannot
            # read it -- and therefore cannot read its write layer either.
            forklayr = await core.callStorm('return($lib.view.get().fork().layers.0.iden)')

            await core.auth.addUser('visi')

            async with core.getLocalProxy(user='visi') as prox:
                await self.agenraises(s_exc.AuthDeny, prox.iterFormRows(forklayr, 'inet:ip'))

    async def test_cortex_iterrows(self):

        async with self.getTestCoreAndProxy() as (core, prox):
            await core.addTagProp('_score', ('int', {}), {})

            nodes = await core.nodes('[(inet:ip=([4, 1]) :asn=10 +#foo=(2020,2021) +#foo:_score=42)]')
            self.len(1, nodes)
            nid1 = nodes[0].intnid()

            nodes = await core.nodes('[(inet:ip=([4, 2]) :asn=20 +#foo=(2019,2020) +#foo:_score=41)]')
            self.len(1, nodes)
            nid2 = nodes[0].intnid()

            nodes = await core.nodes('[(inet:ip=([4, 3]) :asn=30 +#foo=(2018, 2020) +#foo:_score=99)]')
            self.len(1, nodes)
            nid3 = nodes[0].intnid()

            self.len(1, await core.nodes('[test:str=yolo]'))
            self.len(1, await core.nodes('[test:str=$valu]', opts={'vars': {'valu': 'z' * 500}}))

            badiden = 'xxx'
            await self.agenraises(s_exc.NoSuchLayer, prox.iterPropRows(badiden, 'inet:ip', 'asn'))

            # rows are (nid, valu) tuples
            layriden = core.view.layers[0].iden
            rows = await alist(prox.iterPropRows(layriden, 'inet:ip', 'asn'))

            self.eq((10, 20, 30), tuple(sorted([row[1][1] for row in rows])))

            tm = lambda x, y: (s_time.parse(x), s_time.parse(y), s_time.parse(y) - s_time.parse(x))  # NOQA

            # iterFormRows
            await self.agenraises(s_exc.NoSuchLayer, prox.iterFormRows(badiden, 'inet:ip'))

            rows = await alist(prox.iterFormRows(layriden, 'inet:ip'))
            self.eq([(nid1, (4, 1)), (nid2, (4, 2)), (nid3, (4, 3))], rows)

            # iterTagRows
            expect = sorted(
                [
                    (nid1, (tm('2020', '2021'))),
                    (nid2, (tm('2019', '2020'))),
                    (nid3, (tm('2018', '2020'))),
                ], key=lambda x: x[1])

            await self.agenraises(s_exc.NoSuchLayer, prox.iterTagRows(badiden, 'foo', form='newpform'))
            rows = await alist(prox.iterTagRows(layriden, 'foo', form='newpform'))
            self.eq([], rows)

            rows = await alist(prox.iterTagRows(layriden, 'foo', form='inet:ip'))
            self.eq(expect, rows)

            rows = await alist(prox.iterTagRows(layriden, 'foo', form='inet:ip', starttupl=expect[1]))
            self.eq(expect[1:], rows)

            expect = [
                (nid2, 41,),
                (nid1, 42,),
                (nid3, 99,),
            ]

            await self.agenraises(s_exc.NoSuchLayer, prox.iterTagPropRows(badiden, 'foo', '_score', form='inet:ip',
                                                                          stortype=s_layer.STOR_TYPE_I64,
                                                                          startvalu=42))

            rows = await alist(prox.iterTagPropRows(layriden, 'foo', '_score', form='inet:ip',
                                                    stortype=s_layer.STOR_TYPE_I64, startvalu=42))
            self.eq(expect[1:], rows)

    async def test_cortex_depr_props_warning(self):

        with self.getTestDir() as dirn:
            with self.getLoggerStream('synapse.cortex') as stream:

                async with self.getTestCore(dirn=dirn) as core:

                    await core._addModelDefs(s_t_utils.deprmodel)

                    # Create a test:deprprop so it doesn't generate a warning
                    await core.callStorm('[test:dep:easy=foobar :guid=* as test:guid]')

                    # Lock test:deprprop:ext so it doesn't generate a warning
                    await core.callStorm('model.deprecated.lock test:dep:str')

                # Check that we saw the warnings
                data = stream.getvalue()
                self.eq(1, data.count('deprecated properties unlocked'))
                self.isin('deprecated properties unlocked and not in use', data)

                match = regex.search(r'Detected (?P<count>\d+) deprecated properties', data)
                count = int(match.groupdict().get('count'))

                stream.clear()

                async with self.getTestCore(dirn=dirn) as core:
                    await core._addModelDefs(s_t_utils.deprmodel)

                # Check that the warnings are gone now
                data = stream.getvalue()

                if (count - 3) == 0:
                    self.eq(0, data.count('deprecated properties unlocked'))
                else:
                    self.eq(1, data.count('deprecated properties unlocked'))
                    self.isin(f'Detected {count - 3} deprecated properties', data)

    async def test_cortex_modelrev_task(self):

        async def dummy(self):
            await asyncio.Future()

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core00:
                await self.waitForActiveMigration(core00)

            with mock.patch('synapse.lib.modelrev.ModelRev.revCoreLayers', dummy):
                conf01 = {'parent': 'tcp://root:root@127.0.0.1:0'}
                async with self.getTestCore(dirn=dirn, conf=conf01) as core01:

                    # clear the explicit parent pin before promoting.
                    core01.conf.pop('parent', None)
                    await core01.promote(force=True)
                    await asyncio.sleep(0)

                    task = await core01.callStorm('''
                        for $task in $lib.task.list() {
                            if ($task.name = "cortex:migration:layers") {
                                return($task)
                            }
                        }
                    ''')
                    self.nn(task)
                    self.true(task['protected'])
                    self.true(task['background'])

                    self.true(await core01.isCellActive())

                    # automation tasks start concurrently with the migration
                    self.nn(core01.view.trigtask)

                    emesg = 'Task cortex:migration:layers is protected.'

                    # cannot kill through exposed Storm APIs

                    opts = {'vars': {'iden': task['iden']}}

                    with self.raises(s_exc.SynErr) as cm:
                        await core01.nodes('task.kill $iden', opts=opts)
                    self.eq(cm.exception.get('mesg'), emesg)

                    # cannot kill through exposed Telepath APIs

                    async with core01.getLocalProxy() as proxy:

                        with self.raises(s_exc.SynErr) as cm:
                            await proxy.killTask(task['iden'])
                        self.eq(cm.exception.get('mesg'), emesg)

                        with self.raises(s_exc.SynErr) as cm:
                            await proxy.kill(task['iden'])
                        self.eq(cm.exception.get('mesg'), emesg)

                    # internal kill still works

                    self.nn(rtask := core01.boss.get(task['iden']))
                    await rtask.kill(safe=False)
                    self.none(core01.boss.get(task['iden']))

    async def test_cortex_automation_during_migration(self):

        evnt = asyncio.Event()

        async def dummy(self):
            await evnt.wait()

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core00:
                tdef = {'cond': 'node:add', 'form': 'inet:fqdn', 'storm': '[test:str=triggered]'}
                await core00.view.addTrigger(tdef)
                await self.waitForActiveMigration(core00)

            with mock.patch('synapse.lib.modelrev.ModelRev.revCoreLayers', dummy):
                conf01 = {'parent': 'tcp://root:root@127.0.0.1:0'}
                async with self.getTestCore(dirn=dirn, conf=conf01) as core01:

                    # clear the explicit parent pin before promoting.
                    core01.conf.pop('parent', None)
                    await core01.promote(force=True)
                    await asyncio.sleep(0)

                    # trigger fires during migration (not silently dropped)
                    await core01.nodes('[inet:fqdn=vertex.link]')
                    self.len(1, await core01.nodes('test:str=triggered'))

                    # trigger task is alive while migration is blocked
                    self.nn(core01.view.trigtask)

                    evnt.set()
                    await self.waitForActiveMigration(core01)

    async def test_cortex_vaults(self):
        '''
        Simple usage testing.
        '''
        async with self.getTestCore() as core:

            vtype1 = 'synapse-test1'
            vtype2 = 'synapse-test2'

            # Create some test users
            visi1 = await core.auth.addUser('visi1')
            visi2 = await core.auth.addUser('visi2')
            contributor = await core.auth.addRole('contributor')
            await visi1.grant(contributor.iden)

            gvault = {
                'name': 'global1',
                'type': vtype1,
                'scope': 'global',
                'owner': None,
                'configs': {},
                'secrets': {},
            }
            giden = await core.addVault(gvault)

            rvault = {
                'name': 'role1',
                'type': vtype1,
                'scope': 'role',
                'owner': contributor.iden,
                'configs': {},
                'secrets': {},
            }
            riden = await core.addVault(rvault)

            uvault = {
                'name': 'user1',
                'type': vtype1,
                'scope': 'user',
                'owner': visi1.iden,
                'configs': {},
                'secrets': {},
            }
            uiden = await core.addVault(uvault)

            svault = {
                'name': 'unscoped1',
                'type': vtype1,
                'scope': None,
                'owner': visi1.iden,
                'configs': {},
                'secrets': {},
            }
            siden = await core.addVault(svault)

            vault = core.getVault(giden)
            self.eq(vault.get('iden'), giden)

            vault = core.getVaultByName('global1')
            self.eq(vault.get('iden'), giden)

            vault = core.getVaultByType(vtype1, visi1.iden, scope='global')
            self.eq(vault.get('iden'), giden)

            vault = core.getVaultByType(vtype1, visi1.iden, scope='role')
            self.eq(vault.get('iden'), riden)

            vault = core.getVaultByType(vtype1, visi1.iden, scope='user')
            self.eq(vault.get('iden'), uiden)

            vault = core.reqVault(giden)
            self.eq(vault.get('iden'), giden)

            vault = core.reqVaultByName('global1')
            self.eq(vault.get('iden'), giden)
            self.eq(vault.get('name'), 'global1')

            vault = core.reqVaultByType(vtype1, visi1.iden, scope='global')
            self.eq(vault.get('iden'), giden)

            self.true(await core.setVaultConfigs(giden, 'color', 'orange'))
            self.true(await core.setVaultSecrets(giden, 'apikey', 'foobar'))

            await core.replaceVaultConfigs(giden, {'rubiks': 'cube'})
            vault = core.reqVault(giden)
            self.eq({'rubiks': 'cube'}, vault['configs'])

            await core.replaceVaultSecrets(giden, {'secret': 'squirrel'})
            vault = core.reqVault(giden)
            self.eq({'secret': 'squirrel'}, vault['secrets'])

            vaults = list(core.listVaults())
            self.len(4, vaults)

            self.true(await core.setVaultPerm(giden, visi1.iden, s_cell.PERM_EDIT))

            self.true(await core.renameVault(giden, 'global2'))
            vault = core.reqVaultByName('global2')
            self.eq(vault.get('iden'), giden)
            self.eq(vault.get('name'), 'global2')

            with self.raises(s_exc.DupName):
                await core.renameVault(giden, 'global2')

            self.none(await core.delVault('asdf'))

            await core.delVault(giden)
            vaults = list(core.listVaults())
            self.len(3, vaults)

    async def test_cortex_vault_type_schemas(self):
        '''
        A vault type's single JSON schema (applied to the whole vault) validates
        vaults of that type, registered either from a storm package "vaults"
        field or via the generic addVaultType() API. Versions are append-only.
        '''
        def _schema(configs, secrets=None):
            props = {'configs': configs}
            if secrets is not None:
                props['secrets'] = secrets
            return {'type': 'object', 'properties': props}

        confsch = {
            'type': 'object',
            'properties': {
                'host': {'type': 'string'},
                'port': {'type': 'integer', 'default': 443},
            },
            'required': ['host'],
            'additionalProperties': False,
        }
        secsch = {
            'type': 'object',
            'properties': {'password': {'type': 'string'}},
            'additionalProperties': False,
        }
        schema = _schema(confsch, secsch)

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')

            def _vdef(name, vtype, configs, secrets):
                return {'name': name, 'type': vtype, 'scope': None,
                        'owner': visi.iden, 'configs': configs, 'secrets': secrets}

            # (1) package registration from the pkgdef "vaults" field happens
            # when the package is added (before it is loaded)
            pkgvtype = 'synapse-test:pkg'
            pkgdef = {
                'name': 'synapse-test-vaults',
                'version': (0, 0, 1),
                'vaults': {pkgvtype: {'version': 1, 'schema': copy.deepcopy(schema)}},
            }
            await core.addStormPkg(pkgdef)
            self.eq(1, core.getVaultType(pkgvtype)['version'])

            # (2) generic, nexus-persisted registration
            genvtype = 'synapse-test:gen'
            await core.addVaultType({'name': genvtype, 'version': 1, 'schema': schema})
            self.eq(1, core.getVaultType(genvtype)['version'])

            self.isin(genvtype, [v['name'] for v in core.listVaultTypes()])

            geniden = None
            for vtype in (pkgvtype, genvtype):
                # valid configs are accepted and schema defaults are filled
                iden = await core.addVault(_vdef(f'ok-{vtype}', vtype, {'host': 'h'}, {'password': 'p'}))
                self.eq(443, core.getVault(iden)['configs']['port'])
                if vtype == genvtype:
                    geniden = iden

                # missing required / unknown config / bad secret rejected
                await self.asyncraises(s_exc.SchemaViolation, core.addVault(_vdef(f'b1-{vtype}', vtype, {}, {})))
                await self.asyncraises(s_exc.SchemaViolation,
                                       core.addVault(_vdef(f'b2-{vtype}', vtype, {'host': 'h', 'x': 1}, {})))
                await self.asyncraises(s_exc.SchemaViolation,
                                       core.addVault(_vdef(f'b3-{vtype}', vtype, {'host': 'h'}, {'nope': 'x'})))

                # replace + single-key set validate the resulting vault
                await self.asyncraises(s_exc.SchemaViolation, core.replaceVaultConfigs(iden, {'port': 1}))
                await self.asyncraises(s_exc.SchemaViolation, core.setVaultConfigs(iden, 'x', 1))
                await self.asyncraises(s_exc.SchemaViolation, core.setVaultConfigs(iden, 'host', s_common.novalu))
                await core.setVaultConfigs(iden, 'host', 'h2')
                self.eq('h2', core.getVault(iden)['configs']['host'])

            tighter = _schema({
                'type': 'object',
                'properties': {'host': {'type': 'string'}, 'region': {'type': 'string'}},
                'required': ['host', 'region'],
                'additionalProperties': False,
            })

            # re-registering an existing version with a byte-identical
            # definition is an idempotent no-op
            self.eq(genvtype, await core.addVaultType({'name': genvtype, 'version': 1, 'schema': schema}))
            self.eq(1, core.getVaultType(genvtype)['version'])

            # ...but re-registering the same version with a different definition
            # is rejected
            await self.asyncraises(s_exc.BadArg,
                                   core.addVaultType({'name': genvtype, 'version': 1, 'schema': tighter}))

            # a version below the latest is rejected
            await self.asyncraises(s_exc.BadArg, core.addVaultType({'name': genvtype, 'version': 0, 'schema': schema}))

            # a version is append-only: the new version becomes latest, the old
            # one is retained, and existing vaults stay at their own version
            await core.addVaultType({'name': genvtype, 'version': 2, 'schema': tighter})
            self.eq(2, core.getVaultType(genvtype)['version'])
            self.eq(1, core.getVaultType(genvtype, version=1)['version'])
            self.eq(1, core.getVault(geniden)['type:version'])
            # the straggler still validates against its own (v1) schema
            await core.setVaultConfigs(geniden, 'host', 'h3')
            self.eq('h3', core.getVault(geniden)['configs']['host'])
            # a new vault of the type is stamped and validated at the latest version
            await self.asyncraises(s_exc.SchemaViolation, core.addVault(_vdef('new1', genvtype, {'host': 'h'}, {})))
            newiden = await core.addVault(_vdef('new2', genvtype, {'host': 'h', 'region': 'eu'}, {}))
            self.eq(2, core.getVault(newiden)['type:version'])

            # every registered version is enumerable, oldest first, while
            # listVaultTypes still surfaces only the latest of each type
            self.eq([1, 2], [v['version'] for v in core.getVaultTypeVersions(genvtype)])
            self.eq(2, [v for v in core.listVaultTypes() if v['name'] == genvtype][0]['version'])
            self.eq([], core.getVaultTypeVersions('synapse-test:nope'))

            # $lib.vault.type exposes get(version)/versions() alongside list()
            opts = {'vars': {'vtype': genvtype}}
            self.eq(1, await core.callStorm('return($lib.vault.type.get($vtype, version=1).version)', opts=opts))
            self.eq(2, await core.callStorm('return($lib.vault.type.get($vtype).version)', opts=opts))
            self.eq([1, 2], await core.callStorm('''
                $vers = ([])
                for $vt in $lib.vault.type.versions($vtype) { $vers.append($vt.version) }
                return($vers)
            ''', opts=opts))

            # updateVault atomically replaces a vault, validating against its
            # own version and honoring rename; type/scope/owner are immutable
            vdef = core.getVault(geniden)
            vdef['configs']['host'] = 'h4'
            vdef['name'] = 'renamed'
            await core.updateVault(vdef)
            self.eq('h4', core.getVault(geniden)['configs']['host'])
            self.nn(core.getVaultByName('renamed'))

            vdef = core.getVault(geniden)
            vdef['configs'] = {'bad': 1}
            await self.asyncraises(s_exc.SchemaViolation, core.updateVault(vdef))

            # a typed vault cannot be downgraded or un-typed
            vdef = core.getVault(geniden)
            vdef['type:version'] = 0
            await self.asyncraises(s_exc.BadArg, core.updateVault(vdef))

            # dropping type:version on a typed vault trips the un-type guard
            vdef = core.getVault(geniden)
            vdef.pop('type:version')
            await self.asyncraises(s_exc.BadArg, core.updateVault(vdef))

            # type:version, when present, must be a non-negative integer
            vdef = core.getVault(geniden)
            vdef['type:version'] = None
            await self.asyncraises(s_exc.SchemaViolation, core.updateVault(vdef))

            # type, scope, and owner are immutable
            vdef = core.getVault(geniden)
            vdef['scope'] = 'global'
            await self.asyncraises(s_exc.BadArg, core.updateVault(vdef))

            vdef = core.getVault(geniden)
            vdef['owner'] = s_common.guid()
            await self.asyncraises(s_exc.BadArg, core.updateVault(vdef))

            # the onPush handler is the concurrency backstop: a stale write
            # (built from an older read, as when a config update races a
            # migration bump) that would downgrade or un-type is dropped even
            # though it bypasses the pre-push guard
            curv = core.getVault(geniden)
            stale = dict(curv, configs=dict(curv['configs'], host='stale'))
            stale['type:version'] = curv['type:version'] - 1
            self.none(await core._updateVault(stale))
            self.eq(curv['type:version'], core.getVault(geniden)['type:version'])
            self.ne('stale', core.getVault(geniden)['configs']['host'])

            stale['type:version'] = None
            self.none(await core._updateVault(stale))
            self.eq(curv['type:version'], core.getVault(geniden)['type:version'])

            # a same-version write (the normal config-update path) still applies
            same = dict(core.getVault(geniden))
            same['configs'] = dict(same['configs'], host='same')
            self.nn(await core._updateVault(same))
            self.eq('same', core.getVault(geniden)['configs']['host'])

            # an invalid schema is rejected at registration
            await self.asyncraises(s_exc.BadArg, core.addVaultType({'name': 'bad', 'version': 1,
                                                                    'schema': {'type': 'nope'}}))

            # an untyped vault (no registered type) works on every path: it is
            # stored unvalidated, carries no type:version, and freely updatable
            other = await core.addVault(_vdef('other', 'unregistered', {'whatever': 1}, {'s': 2}))
            self.notin('type:version', core.getVault(other))
            await core.setVaultConfigs(other, 'anything', 'ok')
            vdef = core.getVault(other)
            vdef['configs'] = {'totally': 'different'}
            vdef['name'] = 'other2'
            await core.updateVault(vdef)
            self.eq('different', core.getVault(other)['configs']['totally'])
            self.nn(core.getVaultByName('other2'))

            # a registered type need not define a schema; a defined schema
            # validates and an unregistered type does not
            await core.addVaultType({'name': 'noschema', 'version': 1})
            self.nn(await core.addVault(_vdef('ns', 'noschema', {'anything': 1}, {'s': 2})))

            # the schema restricts only what it declares; it can also constrain
            # the vault name (secrets here are left unvalidated)
            named = _schema(confsch)
            named['properties']['name'] = {'type': 'string', 'pattern': '^good:'}
            await core.addVaultType({'name': 'named', 'version': 1, 'schema': named})
            self.nn(await core.addVault(_vdef('good:one', 'named', {'host': 'h'}, {'anything': 'ok'})))
            await self.asyncraises(s_exc.SchemaViolation,
                                   core.addVault(_vdef('bad:one', 'named', {'host': 'h'}, {})))

            # a type with live instances cannot be deleted; the stamp must
            # always resolve to a registered type
            await self.asyncraises(s_exc.CantDelType, core.delVaultType(genvtype))

            # once the instances are gone delVaultType removes all versions;
            # persisted types survive a package drop
            for vault in [v for v in core.listVaults() if v['type'] == genvtype]:
                await core.delVault(vault['iden'])
            await core.delVaultType(genvtype)
            self.none(core.getVaultType(genvtype))
            self.none(core.getVaultType(genvtype, version=1))
            await self.asyncraises(s_exc.NoSuchName, core.delVaultType(genvtype))
            core._dropStormPkg(pkgdef)
            self.nn(core.getVaultType(pkgvtype))

            # a package can be re-added with its byte-identical vault type: the
            # persisted type is a no-op rather than a version-conflict, so a
            # deleted-and-re-added package does not raise (matches generic add)
            await core.addStormPkg(pkgdef)
            self.eq(1, core.getVaultType(pkgvtype)['version'])

            # re-declaring the same type version with a different schema is
            # rejected on the package-add path too, before anything is applied
            badpkg = copy.deepcopy(pkgdef)
            badpkg['vaults'][pkgvtype]['schema'] = copy.deepcopy(tighter)
            await self.asyncraises(s_exc.BadArg, core.addStormPkg(badpkg))
            self.eq(1, core.getVaultType(pkgvtype)['version'])

            # a package vault type must declare a version (no silent default)
            noverpkg = {'name': 'synapse-test-nover', 'version': (0, 0, 1),
                        'vaults': {'synapse-test:nover': {'schema': copy.deepcopy(schema)}}}
            await self.asyncraises(s_exc.SchemaViolation, core.addStormPkg(noverpkg))
            self.none(core.getVaultType('synapse-test:nover'))

        # registration persists across a restart (nexus-backed)
        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                await core.addVaultType({'name': 'persist:me', 'version': 3, 'schema': schema})
            async with self.getTestCore(dirn=dirn) as core:
                self.eq(3, core.getVaultType('persist:me')['version'])

    async def test_cortex_vault_type_migration(self):
        '''
        The background migration runner, fired per vault type on add and on
        boot, brings each vault up to its type's latest version by running the
        type's convergent migration callback once per vault; the callback itself
        calls $lib.vault.update.
        '''
        def _schema(configs):
            return {'type': 'object', 'properties': {'configs': configs}}

        c1 = {'type': 'object', 'properties': {'host': {'type': 'string'}},
              'required': ['host'], 'additionalProperties': False}
        c2 = {'type': 'object', 'properties': {'host': {'type': 'string'}, 'region': {'type': 'string'}},
              'required': ['host', 'region'], 'additionalProperties': False}
        c3 = {'type': 'object',
              'properties': {'host': {'type': 'string'}, 'region': {'type': 'string'}, 'tier': {'type': 'string'}},
              'required': ['host', 'region', 'tier'], 'additionalProperties': False}

        # convergent callbacks: fill whatever the current data is missing, then
        # commit. The v3 callback handles a vault coming from either v1 or v2.
        migr2 = '''
            if (not $vault.configs.region) { $vault.configs.region = "eu" }
            $lib.vault.update($vault)
        '''
        migr3 = '''
            if (not $vault.configs.region) { $vault.configs.region = "eu" }
            if (not $vault.configs.tier) { $vault.configs.tier = "gold" }
            $lib.vault.update($vault)
        '''

        async with self.getTestCore() as core:
            user = await core.auth.addUser('u')

            def _vdef(name, vtype, configs):
                return {'name': name, 'type': vtype, 'scope': None,
                        'owner': user.iden, 'configs': configs, 'secrets': {}}

            await core.addVaultType({'name': 't', 'version': 1, 'schema': _schema(c1)})
            iden = await core.addVault(_vdef('v', 't', {'host': 'h'}))
            self.eq(1, core.getVault(iden)['type:version'])

            # bump v1 -> v2 -> v3, then drive the migration deterministically.
            # The vault converges to v3 with data from both the region (v2) and
            # tier (v3) fills, proving the single convergent callback walk.
            await core.addVaultType({'name': 't', 'version': 2, 'schema': _schema(c2), 'migration': migr2})
            await core.addVaultType({'name': 't', 'version': 3, 'schema': _schema(c3), 'migration': migr3})
            await core._migrateVaultType('t')
            self.eq(3, core.getVault(iden)['type:version'])
            self.eq('eu', core.getVault(iden)['configs']['region'])
            self.eq('gold', core.getVault(iden)['configs']['tier'])

            # a migration that leaves the vault invalid against the new schema is
            # rejected; the vault stays at its own (still-valid) version
            await core.addVaultType({'name': 'bad', 'version': 1, 'schema': _schema(c1)})
            biden = await core.addVault(_vdef('b', 'bad', {'host': 'h'}))
            await core.addVaultType({'name': 'bad', 'version': 2, 'schema': _schema(c2),
                                     'migration': '$vault.configs.nope = "x" $lib.vault.update($vault)'})
            await core._migrateVaultType('bad')
            self.eq(1, core.getVault(biden)['type:version'])
            self.eq({'host': 'h'}, core.getVault(biden)['configs'])

            # a migration callback may import a loaded package's storm module
            pkgdef = {
                'name': 'synapse-test-mig',
                'version': (0, 0, 1),
                'modules': ({'name': 'synapse-test-mig.util',
                             'storm': 'function addreg(configs) { $configs.region = "eu" return($configs) }'},),
            }
            await core.addStormPkg(pkgdef)
            await core.addVaultType({'name': 'mig', 'version': 1, 'schema': _schema(c1)})
            miden = await core.addVault(_vdef('m', 'mig', {'host': 'h'}))
            migr = '$vault.configs = $lib.import("synapse-test-mig.util").addreg($vault.configs) $lib.vault.update($vault)'
            await core.addVaultType({'name': 'mig', 'version': 2, 'schema': _schema(c2), 'migration': migr})
            await core._migrateVaultType('mig')
            self.eq(2, core.getVault(miden)['type:version'])
            self.eq('eu', core.getVault(miden)['configs']['region'])

            # a package that declares its vault type via the pkgdef "vaults"
            # field can, on a version bump, migrate with a callback that imports
            # the package's own module -- the type registers only after the
            # package (and its module) load, so the import resolves
            util = 'function addreg(configs) { $configs.region = "eu" return($configs) }'
            pvtype = 'synapse-test:pkgvault'
            pkg1 = {'name': 'synapse-test-pkgvault', 'version': (0, 0, 1),
                    'modules': ({'name': 'synapse-test-pkgvault.util', 'storm': util},),
                    'vaults': {pvtype: {'version': 1, 'schema': _schema(c1)}}}
            await core.addStormPkg(pkg1)
            piden = await core.addVault(_vdef('p', pvtype, {'host': 'h'}))
            self.eq(1, core.getVault(piden)['type:version'])

            pmigr = '$vault.configs = $lib.import("synapse-test-pkgvault.util").addreg($vault.configs) $lib.vault.update($vault)'
            pkg2 = dict(pkg1, version=(0, 0, 2),
                        vaults={pvtype: {'version': 2, 'schema': _schema(c2), 'migration': pmigr}})
            await core.addStormPkg(pkg2)
            await core._migrateVaultType(pvtype)
            self.eq(2, core.getVault(piden)['type:version'])
            self.eq('eu', core.getVault(piden)['configs']['region'])

            # a callback that never calls $lib.vault.update commits nothing, so
            # the vault stays behind at its prior version (a straggler)
            await core.addVaultType({'name': 'noop', 'version': 1, 'schema': _schema(c1)})
            npiden = await core.addVault(_vdef('np', 'noop', {'host': 'h'}))
            await core.addVaultType({'name': 'noop', 'version': 2, 'schema': _schema(c2),
                                     'migration': '$lib.print(noop)'})
            await core._migrateVaultType('noop')
            self.eq(1, core.getVault(npiden)['type:version'])
            self.eq({'host': 'h'}, core.getVault(npiden)['configs'])

        # registering a type auto-fires the runner (its onPush handler schedules
        # it), which migrates a vault created before the type was versioned. A
        # fresh cortex with only this one type has a single migration event.
        async with self.getTestCore() as core:
            user = await core.auth.addUser('u')
            noneiden = await core.addVault({'name': 'n', 'type': 'later', 'scope': None,
                                            'owner': user.iden, 'configs': {'host': 'h'}, 'secrets': {}})
            self.notin('type:version', core.getVault(noneiden))

            waiter = core.waiter(1, 'core:vaults:migrated')
            await core.addVaultType({'name': 'later', 'version': 1, 'schema': _schema(c1)})
            self.true(await waiter.wait(timeout=12))
            self.eq(1, core.getVault(noneiden)['type:version'])

    async def test_cortex_vault_update_error_paths(self):
        async with self.getTestCore() as core:
            user = await core.auth.addUser('u')

            # the migration runner is a no-op for an unregistered type
            await core._migrateVaultType('nosuchvaulttype')

            schema = {
                'type': 'object',
                'properties': {
                    'configs': {'type': 'object', 'properties': {'host': {'type': 'string'}},
                                'required': ['host'], 'additionalProperties': False},
                    'secrets': {'type': 'object', 'properties': {'apikey': {'type': 'string'}},
                                'additionalProperties': False},
                },
            }
            await core.addVaultType({'name': 'dbt', 'version': 1, 'schema': schema})
            await core.addVaultType({'name': 'dbt', 'version': 2, 'schema': schema})

            # a package re-declaring an already-registered type at a lower/equal
            # version is skipped (the type stays at its current version)
            await core.addStormPkg({'name': 'redecl', 'version': (0, 0, 1),
                                    'vaults': {'dbt': {'version': 1, 'schema': schema}}})
            self.eq(2, core.getVaultType('dbt')['version'])

            iden = await core.addVault({'name': 'v0', 'type': 'dbt', 'scope': 'global',
                                        'owner': None, 'configs': {'host': 'h'}, 'secrets': {'apikey': 'k'}})
            self.eq(2, core.getVault(iden)['type:version'])

            # updateVault to a version the type does not have
            vdef = core.getVault(iden)
            vdef['type:version'] = 99
            with self.raises(s_exc.BadArg) as exc:
                await core.updateVault(vdef)
            self.isin('has no registered version 99', exc.exception.get('mesg'))

            # non-msgpack configs/secrets are rejected (untyped vault so the type
            # schema does not reject the value before the msgpack check)
            uiden = await core.addVault({'name': 'u0', 'type': 'untyped', 'scope': None,
                                         'owner': user.iden, 'configs': {}, 'secrets': {}})
            vdef = core.getVault(uiden)
            vdef['configs'] = {'x': self}
            with self.raises(s_exc.BadArg) as exc:
                await core.updateVault(vdef)
            self.eq('Vault definition must be msgpack safe.', exc.exception.get('mesg'))

            vdef = core.getVault(uiden)
            vdef['secrets'] = {'x': self}
            with self.raises(s_exc.BadArg) as exc:
                await core.updateVault(vdef)
            self.eq('Vault definition must be msgpack safe.', exc.exception.get('mesg'))

            # renaming onto an existing vault name is a DupName
            u2 = await core.addVault({'name': 'u2', 'type': 'untyped2', 'scope': None,
                                      'owner': user.iden, 'configs': {}, 'secrets': {}})
            vdef = core.getVault(u2)
            vdef['name'] = 'u0'
            await self.asyncraises(s_exc.DupName, core.updateVault(vdef))

            # the vault:update handler is a no-op when the vault is missing
            self.none(await core._updateVault({'iden': s_common.guid()}))

    async def test_cortex_vaults_errors(self):
        '''
        Simple argument checking and simple permission checking tests.
        '''
        async with self.getTestCore() as core:

            vtype1 = 'synapse-test1'
            vtype2 = 'synapse-test2'

            # Create some test users
            visi1 = await core.auth.addUser('visi1')
            visi2 = await core.auth.addUser('visi2')
            contributor = await core.auth.addRole('contributor')
            await visi1.grant(contributor.iden)

            gvault = {
                'name': 'global1',
                'type': vtype1,
                'scope': 'global',
                'owner': None,
                'configs': {},
                'secrets': {},
            }
            giden = await core.addVault(gvault)

            rvault = {
                'name': 'role1',
                'type': vtype1,
                'scope': 'role',
                'owner': contributor.iden,
                'configs': {},
                'secrets': {},
            }
            riden = await core.addVault(rvault)

            self.none(core.getVault('asdf'))

            with self.raises(s_exc.DupName) as exc:
                # type/scope/iden collision
                await core.addVault(gvault)
            self.eq(f'Vault already exists for type {vtype1}, scope global, owner None.', exc.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as exc:
                # vdef is not a dict
                await core.addVault([])
            self.eq('Invalid vault definition provided.', exc.exception.get('mesg'))

            with self.raises(s_exc.DupName) as exc:
                # name collision
                vault = s_msgpack.deepcopy(gvault)
                vault['scope'] = None
                vault['owner'] = visi1.iden
                await core.addVault(vault)
            self.eq('A config already exists with the name global1.', exc.exception.get('mesg'))

            with self.raises(s_exc.DupName) as exc:
                # name collision
                vault = s_msgpack.deepcopy(gvault)
                vault['scope'] = 'global'
                vault['owner'] = visi1.iden
                vault['type'] = 'vtest2'
                await core.addVault(vault)
            self.eq('A global config already exists with the name global1.', exc.exception.get('mesg'))

            with self.raises(s_exc.NoSuchName) as exc:
                # Non-existent vault name
                core.reqVaultByName('newp')
            self.eq('Vault not found for name: newp.', exc.exception.get('mesg'))

            with self.raises(s_exc.SchemaViolation):
                # len(name) == 0
                vault = s_msgpack.deepcopy(gvault)
                vault['name'] = ''
                await core.addVault(vault)

            with self.raises(s_exc.SchemaViolation):
                # len(name) > 256
                vault = s_msgpack.deepcopy(gvault)
                vault['name'] = 'A' * 257
                await core.addVault(vault)

            with self.raises(s_exc.SchemaViolation):
                # len(vtype) == 0
                vault = s_msgpack.deepcopy(gvault)
                vault['type'] = ''
                await core.addVault(vault)

            with self.raises(s_exc.SchemaViolation):
                # len(vtype) > 256
                vault = s_msgpack.deepcopy(gvault)
                vault['type'] = 'A' * 257
                await core.addVault(vault)

            with self.raises(s_exc.SchemaViolation):
                # scope not in (None, 'user', 'role', 'global')
                vault = s_msgpack.deepcopy(gvault)
                vault['scope'] = 'newp'
                await core.addVault(vault)

            with self.raises(s_exc.SchemaViolation):
                # data != dict
                vault = s_msgpack.deepcopy(gvault)
                vault['data'] = self
                await core.addVault(vault)

            with self.raises(s_exc.BadArg) as exc:
                # configs not msgpack safe
                vault = {
                    'name': 'unscoped1',
                    'type': vtype1,
                    'scope': None,
                    'owner': visi1.iden,
                    'configs': {'foo': self},
                    'secrets': {},
                }
                await core.addVault(vault)
            self.eq('Vault definition must be msgpack safe.', exc.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as exc:
                # secrets not msgpack safe
                vault = {
                    'name': 'unscoped1',
                    'type': vtype1,
                    'scope': None,
                    'owner': visi1.iden,
                    'configs': {},
                    'secrets': {'foo': self},
                }
                await core.addVault(vault)
            self.eq('Vault definition must be msgpack safe.', exc.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as exc:
                # Iden == None, scope != 'global'
                vault = s_msgpack.deepcopy(gvault)
                vault['owner'] = None
                vault['scope'] = None
                await core.addVault(vault)
            self.eq('Owner required for unscoped, user, and role vaults.', exc.exception.get('mesg'))

            with self.raises(s_exc.NoSuchUser) as exc:
                # user with iden does not exist
                vault = {
                    'name': 'global2',
                    'type': 'type2',
                    'scope': 'user',
                    'owner': '0123456789abcdef0123456789abcdef',
                    'configs': {},
                    'secrets': {},
                }
                await core.addVault(vault)
            self.eq('User with iden 0123456789abcdef0123456789abcdef not found.', exc.exception.get('mesg'))

            with self.raises(s_exc.NoSuchRole) as exc:
                # role with iden does not exist
                vault = s_msgpack.deepcopy(gvault)
                vault['name'] = 'role2'
                vault['scope'] = 'role'
                vault['owner'] = visi1.iden
                await core.addVault(vault)
            self.eq(f'Role with iden {visi1.iden} not found.', exc.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as exc:
                await core.setVaultSecrets(giden, 'newp', s_common.novalu)
            self.eq('Key newp not found in vault secrets.', exc.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as exc:
                await core.setVaultConfigs(giden, 'newp', s_common.novalu)
            self.eq('Key newp not found in vault configs.', exc.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as exc:
                # Invalid vault iden format
                await core.setVaultSecrets('1234', 'foo', 'bar')
            self.eq('Iden is not a valid iden: 1234.', exc.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as exc:
                # Invalid vault iden format
                await core.setVaultConfigs('1234', 'foo', 'bar')
            self.eq('Iden is not a valid iden: 1234.', exc.exception.get('mesg'))

            with self.raises(s_exc.NoSuchIden) as exc:
                # vault with iden does not exist
                await core.setVaultSecrets(visi1.iden, 'foo', 'bar')
            self.eq(f'Vault not found for iden: {visi1.iden}.', exc.exception.get('mesg'))

            with self.raises(s_exc.NoSuchIden) as exc:
                # vault with iden does not exist
                await core.setVaultConfigs(visi1.iden, 'foo', 'bar')
            self.eq(f'Vault not found for iden: {visi1.iden}.', exc.exception.get('mesg'))

            with self.raises(s_exc.NotMsgpackSafe) as exc:
                # data not msgpack safe
                await core.setVaultSecrets(giden, 'foo', self)
            self.eq('Vault secrets must be msgpack safe.', exc.exception.get('mesg'))

            with self.raises(s_exc.NotMsgpackSafe) as exc:
                # data not msgpack safe
                await core.setVaultConfigs(giden, 'foo', self)
            self.eq('Vault configs must be msgpack safe.', exc.exception.get('mesg'))

            with self.raises(s_exc.NotMsgpackSafe) as exc:
                # data not msgpack safe
                await core.setVaultSecrets(giden, self, 'bar')
            self.eq('Vault secrets must be msgpack safe.', exc.exception.get('mesg'))

            with self.raises(s_exc.NotMsgpackSafe) as exc:
                # data not msgpack safe
                await core.setVaultConfigs(giden, self, 'bar')
            self.eq('Vault configs must be msgpack safe.', exc.exception.get('mesg'))

            with self.raises(s_exc.NoSuchIden) as exc:
                # iden not valid
                await core.setVaultPerm(giden, '1234', s_cell.PERM_EDIT)
            self.eq('Iden 1234 is not a valid user or role.', exc.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as exc:
                # Invalid scope
                core._getVaultByTSI('vtype', 'newp', 'iden')
            self.eq('Invalid scope: newp.', exc.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as exc:
                # Invalid scope
                core.getVaultByType(vtype1, 'iden', 'newp')
            self.eq('Invalid scope: newp.', exc.exception.get('mesg'))

            with self.raises(s_exc.NoSuchUser) as exc:
                # Invalid user iden
                core.getVaultByType(vtype1, contributor.iden, 'role')
            self.eq(f'No user with iden {contributor.iden}.', exc.exception.get('mesg'))

            # User in role but no perm to vault
            await core.setVaultPerm(riden, visi2.iden, s_cell.PERM_DENY)
            await visi2.grant(contributor.iden)
            self.none(core.getVaultByType(vtype1, visi2.iden, 'role'))

            # Requested type/scope doesn't exist
            self.none(core.getVaultByType(vtype1, visi1.iden, 'user'))

            # Requested type doesn't exist
            self.none(core.getVaultByType(vtype2, visi1.iden))

            with self.raises(s_exc.NoSuchName) as exc:
                # Requested type/scope doesn't exist
                core.reqVaultByType(vtype1, visi1.iden, 'user')
            self.eq(f'Vault not found for type: {vtype1}.', exc.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as exc:
                await core.replaceVaultSecrets(giden, self)
            self.eq('valu must be a dictionary.', exc.exception.get('mesg'))

            with self.raises(s_exc.NotMsgpackSafe) as exc:
                await core.replaceVaultSecrets(giden, {'foo': self})
            self.eq('Vault secrets must be msgpack safe.', exc.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as exc:
                await core.replaceVaultConfigs(giden, self)
            self.eq('valu must be a dictionary.', exc.exception.get('mesg'))

            with self.raises(s_exc.NotMsgpackSafe) as exc:
                await core.replaceVaultConfigs(giden, {'foo': self})
            self.eq('Vault configs must be msgpack safe.', exc.exception.get('mesg'))

            class LongRepr:
                def __repr__(self):
                    return 'Abcd. ' * 1000

            valu = {'foo': LongRepr()}

            with self.raises(s_exc.NotMsgpackSafe) as exc:
                await core.replaceVaultSecrets(giden, valu)
            self.eq(
                "{'foo': Abcd. Abcd. Abcd. Abcd. Abcd. Abcd. Abcd. Abcd. [...]",
                exc.exception.get('valu'))

            with self.raises(s_exc.NotMsgpackSafe) as exc:
                await core.replaceVaultConfigs(giden, {'foo': LongRepr()})
            self.eq(
                "{'foo': Abcd. Abcd. Abcd. Abcd. Abcd. Abcd. Abcd. Abcd. [...]",
                exc.exception.get('valu'))

    async def test_cortex_user_scope(self):
        async with self.getTestCore() as core:  # type: s_cortex.Cortex
            udef = await core.addUser('admin')
            admin = udef.get('iden')
            await core.setUserAdmin(admin, True)
            async with core.getLocalProxy() as prox:

                # Proxy our storm requests as the admin user
                opts = {'user': admin}

                self.eq('admin', await prox.callStorm('return( $lib.auth.users.get().name  )', opts=opts))

                with self.getLoggerStream('synapse.lib.cell') as stream:

                    q = 'return( ($lib.auth.users.get().name, $lib.auth.users.add(lowuser) ))'
                    (whoami, udef) = await prox.callStorm(q, opts=opts)
                    self.eq('admin', whoami)
                    self.eq('lowuser', udef.get('name'))

                msgs = stream.jsonlines()
                mesg = [m for m in msgs if 'Added user' in m.get('message')][0]
                self.eq('Added user=lowuser', mesg.get('message'))
                self.eq('admin', mesg.get('username'))
                self.eq('lowuser', mesg['params'].get('target_username'))

                with self.getLoggerStream('synapse.lib.cell') as stream:

                    q = 'auth.user.mod lowuser --admin (true)'
                    msgs = []
                    async for mesg in prox.storm(q, opts=opts):
                        msgs.append(mesg)
                    self.stormHasNoWarnErr(msgs)

                msgs = stream.jsonlines()
                mesg = [m for m in msgs if 'Set admin' in m.get('message')][0]
                self.isin('Set admin=True for lowuser', mesg.get('message'))
                self.eq('admin', mesg.get('username'))
                self.eq('lowuser', mesg['params'].get('target_username'))

    async def test_cortex_ext_httpapi(self):
        # Cortex API tests for Extended HttpAPI
        async with self.getTestCore() as core:  # type: s_cortex.Cortex

            newp = s_common.guid()
            with self.raises(s_exc.SynErr):
                await core.setHttpApiIndx(newp, 0)

            unfo = await core.getUserDefByName('root')
            view = core.getView()
            info = await core.addHttpExtApi({
                'path': 'test/path/(hehe|haha)/(.*)',
                'owner': unfo.get('iden'),
                'view': view.iden,
            })

            info2 = await core.addHttpExtApi({
                'path': 'something/else',
                'owner': unfo.get('iden'),
                'view': view.iden,
            })

            info3 = await core.addHttpExtApi({
                'path': 'something/else/goes/here',
                'owner': unfo.get('iden'),
                'view': view.iden,
            })

            othr = s_common.guid()
            info4 = await core.addHttpExtApi({
                'iden': othr,
                'path': 'another/item',
                'owner': unfo.get('iden'),
                'view': view.iden,
            })
            self.eq(info4.get('iden'), othr)

            iden = info.get('iden')

            adef = await core.getHttpExtApi(iden)
            self.eq(adef, info)

            adef = await core.getHttpExtApi(othr)
            self.eq(adef, info4)

            adef, args = await core.getHttpExtApiByPath('test/path/hehe/wow')
            self.eq(adef, info)
            self.eq(args, ('hehe', 'wow'))

            adef, args = await core.getHttpExtApiByPath('test/path/hehe/wow/more/')
            self.eq(adef, info)
            self.eq(args, ('hehe', 'wow/more/'))

            adef, args = await core.getHttpExtApiByPath('test/path/HeHe/wow')
            self.none(adef)
            self.eq(args, ())

            async with core.getLocalProxy() as prox:
                adef, args = await prox.getHttpExtApiByPath('test/path/haha/words')
                self.eq(adef, info)
                self.eq(args, ('haha', 'words'))

            self.len(4, core._exthttpapicache)

            # Reordering / safety
            self.eq(1, await core.setHttpApiIndx(info4.get('iden'), 1))

            # Cache is cleared when reloading
            self.len(0, core._exthttpapicache)
            adef, args = await core.getHttpExtApiByPath('test/path/hehe/wow')
            self.eq(adef, info)
            self.len(1, core._exthttpapicache)

            self.eq([adef.get('iden') for adef in await core.getHttpExtApis()],
                    [info.get('iden'), info4.get('iden'), info2.get('iden'), info3.get('iden')])

            items = await core.getHttpExtApis()
            self.eq(items, (info, info4, info2, info3))

            # Tiny sleep to ensure that updated ticks forward when modified
            created = adef.get('created')
            updated = adef.get('updated')
            await asyncio.sleep(0.005)
            adef = await core.modHttpExtApi(iden, 'name', 'wow')
            self.eq(adef.get('created'), created)
            self.gt(adef.get('updated'), updated)

            # Sad path

            with self.raises(s_exc.SchemaViolation):
                await core.addHttpExtApi({
                    'iden': 'lolnope',
                    'path': 'not/gonna/happen',
                    'owner': unfo.get('iden'),
                    'view': view.iden
                })

            with self.raises(s_exc.DupIden) as ectx:
                await core.addHttpExtApi({
                    'iden': othr,
                    'path': 'bad/dup',
                    'owner': unfo.get('iden'),
                    'view': view.iden
                })
            self.eq(ectx.exception.get('iden'), othr)

            with self.raises(s_exc.SynErr):
                await core.setHttpApiIndx(newp, 0)

            with self.raises(s_exc.BadArg):
                await core.setHttpApiIndx(newp, -1)

            with self.raises(s_exc.NoSuchUser):
                await core.modHttpExtApi(iden, 'owner', newp)

            with self.raises(s_exc.NoSuchView):
                await core.modHttpExtApi(iden, 'view', newp)

            with self.raises(s_exc.BadArg):
                await core.modHttpExtApi(iden, 'created', 1234)

            with self.raises(s_exc.BadArg):
                await core.modHttpExtApi(iden, 'updated', 1234)

            with self.raises(s_exc.BadArg):
                await core.modHttpExtApi(iden, 'creator', s_common.guid())

            with self.raises(s_exc.BadArg):
                await core.modHttpExtApi(iden, 'newp', newp)

            with self.raises(s_exc.NoSuchIden):
                await core.modHttpExtApi(newp, 'path', 'a/new/path/')

            with self.raises(s_exc.NoSuchIden):
                await core.getHttpExtApi(newp)

            self.none(await core.delHttpExtApi(newp))

            with self.raises(s_exc.BadArg):
                await core.delHttpExtApi('notAGuid')

    async def test_cortex_abrv(self):

        async with self.getTestCore() as core:

            offs = core.indxabrv.offs

            self.eq(s_common.int64en(offs), core.setIndxAbrv(s_layer.INDX_PROP, 'visi', 'foo'))
            # another to check the cache...
            self.eq(s_common.int64en(offs), core.getIndxAbrv(s_layer.INDX_PROP, 'visi', 'foo'))
            self.eq(s_common.int64en(offs + 1), core.setIndxAbrv(s_layer.INDX_PROP, 'whip', None))
            self.eq(('visi', 'foo'), core.getAbrvIndx(s_common.int64en(offs)))
            self.eq(('whip', None), core.getAbrvIndx(s_common.int64en(offs + 1)))
            self.raises(s_exc.NoSuchAbrv, core.getAbrvIndx, s_common.int64en(offs + 2))

    async def test_cortex_check_nexus_init(self):
        # This test is a simple safety net for making sure no nexus events
        # happen before the nexus subsystem is initialized (initNexusSubsystem).
        # It's possible for code which calls nexus APIs to run but not do
        # anything which wouldn't be caught here. I don't think there's a good
        # way to check for that condition though.

        class Cortex(s_cortex.Cortex):
            async def initServiceStorage(self):
                self._test_pre_service_storage_index = await self.nexsroot.index()
                ret = await super().initServiceStorage()
                self._test_post_service_storage_index = await self.nexsroot.index()
                return ret

            async def initNexusSubsystem(self):
                self._test_pre_nexus_index = await self.nexsroot.index()
                ret = await super().initNexusSubsystem()
                self._test_post_nexus_index = await self.nexsroot.index()
                return ret

        conf = {
            'nexslog:en': True,
        }

        with self.getTestDir() as dirn:
            async with await Cortex.anit(dirn, conf=conf) as core:
                offs = core._test_pre_service_storage_index
                self.eq(core._test_post_service_storage_index, offs)
                self.eq(core._test_pre_nexus_index, offs)
                self.ge(core._test_post_nexus_index, core._test_pre_nexus_index)

    async def test_cortex_safemode(self):
        safemode = {'safemode': True}
        nosafe = {'safemode': False}

        # Cortex safemode disables the following functionality:
        # - crons
        # - triggers
        # - dmons
        # - storm package onloads
        # - merge tasks (e.g. for quorum)

        # Make sure we're logging the message
        with self.getLoggerStream('synapse.lib.cell') as stream:
            async with self.getTestCore(conf=safemode) as core:
                self.true(core.safemode)
                await stream.expect('Booting cortex in safe-mode.', timeout=10)
        msgs = stream.jsonlines()
        self.len(1, msgs)
        self.eq(msgs[0].get('message'), 'Booting cortex in safe-mode. Some functionality may be disabled.')
        self.eq(msgs[0].get('level'), 'WARNING')

        # Check crons, triggers, dmons in this section
        with self.getTestDir() as dirn:

            # Setup the cortex
            async with self.getTestCore(dirn=dirn) as core:
                await core.nodes('$lib.queue.add(queue:safemode:done)')
                # Add a cron job and immediately disable it
                q = '''
                cron.add hourly@:00 {
                    $now = $lib.cast(test:time, now)
                    $lib.log.warning(`SAFEMODE CRON: {$now}`)
                    [ test:str=CRON :tick=$now ]
                } |
                $job = $lib.cron.list().0
                cron.mod --enabled (false) $job.iden
                '''
                await core.callStorm(q)
                jobs = await core.listCronJobs()
                self.len(1, jobs)
                self.eq(jobs[0].get('enabled'), False)

                # Add a regular trigger
                q = '''
                $lib.log.warning(`SAFEMODE TRIGGER: {$node}`)
                $tick = :tick.value
                $str = { [( test:str=TRIGGER :hehe=$tick )] }
                $queue = $lib.queue.gen(queue:safemode)
                $queue.put($tick)
                '''
                opts = {'vars': {'query': q}}
                await core.callStorm(f'trigger.add prop:set --prop test:str:tick {{{q}}}')

                # Add an async trigger
                q = '''
                $lib.log.warning(`SAFEMODE ATRIGGER: {$node}`)
                $tick = :tick.value
                $str = { [( test:str=ATRIGGER :hehe=$tick )] }
                $queue = $lib.queue.gen(queue:safemode)
                $queue.put($tick)
                '''
                opts = {'vars': {'query': q}}
                await core.callStorm(f'trigger.add prop:set --prop test:str:tick --async {{{q}}}')

                # Add a dmon
                q = '''
                $queue = $lib.queue.gen(queue:safemode)
                $queue2 = $lib.queue.gen(queue:safemode:done)
                while (true) {
                    ($offs, $item) = $queue.get()
                    $lib.log.warning(`SAFEMODE DMON: {$item}`)
                    [ test:str=DMON :hehe=$item ]
                    $queue2.put($item)
                }
                '''
                await core.callStorm(f'$iden = $lib.dmon.add(${{{q}}}) $lib.dmon.start($iden)')

                nodes = await core.nodes('test:str')
                self.len(0, nodes)

            # Run in safemode and verify cron, trigger, and dmons don't execute
            with self.getLoggerStream('synapse.storm') as stream:
                async with self.getTestCore(dirn=dirn, conf=safemode) as core:
                    await core.callStorm('cron.mod --enabled (true) $lib.cron.list().0.iden')
                    # Increment the cron tick to get it to fire
                    core.agenda._addTickOff(60 * s_time.onesec)

                    # Add a test:str:tick to get the trigger to fire
                    await core.callStorm('[ test:str=newp :tick=1234 ]')

                    # Check for test:strs
                    nodes = await core.nodes('test:str')
                    self.len(1, nodes)
                    self.eq(nodes[0].repr(), 'newp')

                    with self.raises(TimeoutError):
                        q = await core.getCoreQueueByName('queue:safemode:done')
                        async with asyncio.timeout(2):
                            item = await core.coreQueueGet(q['iden'], wait=True)

                    # Add a dmon to make sure it doesn't start

                    await core.nodes('$lib.queue.add(queue:safemode:started)')
                    q = '''
                    $queue = $lib.queue.gen(queue:safemode)
                    $queue2 = $lib.queue.byname(queue:safemode:started)
                    while (true) {
                        $queue2.put(foo)
                        $lib.log.warning(`SAFEMODE DMON START`)
                        ($offs, $item) = $queue.get()
                    }
                    '''
                    await core.callStorm(f'$iden = $lib.dmon.add(${{{q}}}) $lib.dmon.start($iden)')

                    with self.raises(TimeoutError):
                        q = await core.getCoreQueueByName('queue:safemode:started')
                        async with asyncio.timeout(2):
                            item = await core.coreQueueGet(q['iden'], wait=True)

                stream.seek(0)
                data = stream.read()
                self.notin('SAFEMODE CRON', data)
                self.notin('SAFEMODE TRIGGER', data)
                self.notin('SAFEMODE ATRIGGER', data)
                self.notin('SAFEMODE DMON', data)

            with self.getLoggerStream('synapse.storm') as stream:
                async with self.getTestCore(dirn=dirn) as core:
                    core.agenda._addTickOff(60 * 60 * s_time.onesec)

                    q = await core.getCoreQueueByName('queue:safemode:done')
                    async with asyncio.timeout(5):
                        item = await core.coreQueueGet(q['iden'], wait=True)
                    self.len(2, item)

                    nodes = await core.nodes('test:str')
                    self.len(5, nodes)
                    self.sorteq(
                        ['newp', 'CRON', 'TRIGGER', 'DMON', 'ATRIGGER'],
                        [k.repr() for k in nodes]
                    )

                stream.seek(0)
                data = stream.read()
                self.isin('SAFEMODE CRON', data)
                self.isin('SAFEMODE TRIGGER', data)
                self.isin('SAFEMODE ATRIGGER', data)
                self.isin('SAFEMODE DMON', data)

        # Check storm package onload handlers are not executed
        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn, conf=safemode) as core:
                pkgdef = {
                    'name': 'foopkg',
                    'version': (0, 0, 1),
                    'onload': '$lib.import(foo.setup).onload()',
                    'modules': (
                        {
                            'name': 'foo.setup',
                            'storm': '''
                                function onload() {
                                    $lib.warn('foopkg onload')
                                    return()
                                }
                            ''',
                        },
                    )
                }

                waiter = core.waiter(1, 'core:pkg:onload:skipped')
                await core.addStormPkg(pkgdef)
                events = await waiter.wait(timeout=10)
                self.nn(events)
                self.len(1, events)
                self.eq(events, (('core:pkg:onload:skipped', {'pkg': 'foopkg', 'reason': 'safemode'}),))

            with self.getLoggerStream('synapse.cortex') as stream:
                async with self.getTestCore(dirn=dirn, conf=nosafe) as core:
                    self.false(core.safemode)
                    await stream.expect('foopkg onload output: foopkg onload', timeout=10)

        # Check merge tasks are not executed
        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn, conf=safemode) as core:
                alliden = core.auth.allrole.iden

                blackout = await core.auth.addUser('blackout')
                await blackout.allow(('view', 'read'))

                await core.auth.rootuser.grant(alliden)

                view = core.getView()
                qnfo = {
                    'count': 1,
                    'roles': [alliden],
                }
                await view.setViewInfo('quorum', qnfo)

                forkiden = (await view.fork()).get('iden')

                opts = {'view': forkiden}

                nodes = await core.nodes('[ test:str=fork ]', opts=opts)
                self.len(1, nodes)

                await core.callStorm('$lib.view.get().setMergeRequest()', opts=opts)
                await core.callStorm('$lib.view.get().setMergeVote()', opts=opts | {'user': blackout.iden})

                fork = core.getView(forkiden)

                self.true(await fork.isMergeReady())
                self.none(fork.mergetask)

                self.len(0, await core.nodes('test:str'))

            async with self.getTestCore(dirn=dirn, conf=nosafe) as core:

                fork = core.getView(forkiden)

                self.true(await fork.isMergeReady())
                self.nn(fork.mergetask)

                async with asyncio.timeout(5):
                    await fork.mergetask

                nodes = await core.nodes('test:str')
                self.len(1, nodes)
                self.eq(nodes[0].repr(), 'fork')

    async def test_cortex_prop_copy(self):
        async with self.getTestCore() as core:
            q = '[test:arrayprop=(ap0,) :strs=(foo, bar, baz)]'
            self.len(1, await core.nodes(q))

            q = 'test:arrayprop=(ap0,) $l=:strs $r=$l.rem(baz) return(($r, $l))'
            valu = await core.callStorm(q)
            self.true(valu[0])
            self.sorteq(valu[1], ['foo', 'bar'])

            # modifying the property value shouldn't update the node
            nodes = await core.nodes('test:arrayprop=(ap0,) $l=:strs $l.rem(baz)')
            self.len(1, nodes)
            self.propeq(nodes[0], 'strs', ['foo', 'bar', 'baz'])

            data = {
                'str': 'strval',
                'int': 1,
                'dict': {'dictkey': 'dictval'},
                'list': ('listval0', 'listval1'),
                'tuple': ('tupleval0', 'tupleval1'),
            }

            opts = {
                'vars': {
                    'data': data,
                }
            }
            q = '''
                [ test:guid=(d0,)
                    :raw=$data
                    :comp=(1, foo)
                ]
            '''
            self.len(1, await core.nodes(q, opts=opts))

            q = '''
                test:guid=(d0,)
                $d=:raw.value
                $d.list.rem(listval0)
                $d.str = foo
                $d.int = ($d.int + 1)
                $d.dict.foo = bar
                $d.tuple.append(tupleval2)
                return($d)
            '''
            valu = await core.callStorm(q)
            self.eq(valu, {
                    'str': 'foo',
                    'int': 2,
                    'dict': {'dictkey': 'dictval', 'foo': 'bar'},
                    'list': ('listval1',),
                    'tuple': ('tupleval0', 'tupleval1', 'tupleval2'),
            })

            # modifying the property value shouldn't update the node
            q = '''
                test:guid=(d0,)
                $d=:raw.value
                $d.dict = $lib.undef
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].get('raw')[1]['dict'], {'dictkey': 'dictval'})  # not propeq - indexing into prop value

            q = '''
                test:guid=(d0,)
                $c=:comp
                $c.rem((1))
                return(($c, :comp))
            '''
            valu = await core.callStorm(q)
            self.eq(valu, (
                (1, 'foo'),
                (1, 'foo'),
            ))

            # Make sure $node.props aren't modifiable either
            nodes = await core.nodes('test:guid=(d0,) $node.props.raw.list.rem(listval0)')
            self.len(1, nodes)
            self.propeq(nodes[0], 'raw', data)

    async def test_cortex_model_nexusify(self):
        '''
        Test that mainline model changes are routed through the nexus (model:set event).
        Covers: first-boot seed, hash-stable no-op, idempotence, beholder event.
        '''
        with self.getTestDir() as dirn:

            # First boot: model:set fires and cellinfo is seeded
            async with self.getTestCore(dirn=dirn) as core:
                stored_mdefs = core.cellinfo.get('cortex:model')
                self.nn(stored_mdefs)

                # Hash of persisted mdefs must match code-derived model
                mdefs = []
                for path in s_models.modeldefs:
                    if (defs := s_dyndeps.getDynLocal(path)) is not None:
                        mdefs.extend(defs)

                expected_hash = s_common.guid(s_common.flatten(mdefs))
                stored_hash = s_common.guid(s_common.flatten(stored_mdefs))
                self.eq(stored_hash, expected_hash)

                # model has the expected forms
                self.nn(core.model.forms.get('inet:asn'))

                # beholder event fires with the hash
                events = [{'event': 'model:set', 'info': {'hash': expected_hash}}]
                task = core.schedCoro(s_t_utils.waitForBehold(core, events))
                await core._push('model:set', core._mainlinemdefs)
                await asyncio.wait_for(task, timeout=5)

                nexus_index = core.nexsroot.nexslog.index()

            # Second boot (code unchanged): nexus log must not grow and hash must still match
            async with self.getTestCore(dirn=dirn) as core:
                self.eq(core.nexsroot.nexslog.index(), nexus_index)
                stored_hash2 = s_common.guid(s_common.flatten(core.cellinfo.get('cortex:model')))
                self.eq(stored_hash2, expected_hash)

    async def test_cortex_model_nexusify_mirror(self):
        '''
        A new mirror brought online from a older backup connects to the leader and
        syncs the current model via nexus model:set event.
        '''
        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')

            async with self.getTestCore(dirn=path00) as core00:
                h1 = s_common.guid(s_common.flatten(core00.cellinfo.get('cortex:model')))
                nexus_index_before = await core00.nexsroot.index()

                # Corrupt the persisted model to simulate code being ahead of persisted
                good_mdefs = core00.cellinfo.get('cortex:model')
                core00.cellinfo.set('cortex:model', list(good_mdefs) + [{}])

            # Seed the mirror from the stale leader state
            s_tools_backup.backup(path00, path01)

            # Reboot the leader: _execCellUpdates detects hash mismatch and fires model:set
            async with self.getTestCore(dirn=path00) as core00:

                self.gt(await core00.nexsroot.index(), nexus_index_before)
                self.eq(h1, s_common.guid(s_common.flatten(core00.cellinfo.get('cortex:model'))))

                url = core00.getLocalUrl()

                # Mirror boots from stale backup and receives the corrective model:set
                async with self.getTestCore(dirn=path01, conf={'parent': url}) as core01:
                    await asyncio.wait_for(core01.nexsroot.ready.wait(), timeout=12)
                    await core01.sync()

                    self.eq(h1, s_common.guid(s_common.flatten(core01.cellinfo.get('cortex:model'))))
                    self.nn(core00.model.forms.get('inet:asn'))
                    self.nn(core01.model.forms.get('inet:asn'))

    async def test_cortex_model_nexusify_promote(self):
        '''
        Promotion simulation: a mirror with a stale persisted model is promoted to
        leader. The promotion triggers _execCellUpdates which fires model:set, and
        the old leader (now mirror) receives the update.
        '''
        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')

            # Bootstrap the mirror from a backup of the leader
            async with self.getTestCore(dirn=path00) as core00:
                pass

            s_tools_backup.backup(path00, path01)

            async with self.getTestCore(dirn=path00) as core00:
                url00 = core00.getLocalUrl()

                async with self.getTestCore(dirn=path01, conf={'parent': url00}) as core01:
                    await asyncio.wait_for(core01.nexsroot.ready.wait(), timeout=12)
                    await core01.sync()

                    h1 = s_common.guid(s_common.flatten(core00.cellinfo.get('cortex:model')))
                    self.eq(h1, s_common.guid(s_common.flatten(core01.cellinfo.get('cortex:model'))))

                    # Simulate new code deployed to the mirror before promotion:
                    # corrupt its persisted model so the hash differs from the code.
                    good_mdefs = core01.cellinfo.get('cortex:model')
                    core01.cellinfo.set('cortex:model', list(good_mdefs) + [{}])

                    nexus_index_before = await core01.nexsroot.index()

                    # Promote: setCellActive(True) triggers _execCellUpdates which
                    # detects the hash mismatch and fires model:set. Clear the
                    # explicit parent pin so the handoff can promote the mirror.
                    core01.conf.pop('parent', None)
                    url01 = core01.getLocalUrl()
                    await core00.handoff(url01)
                    self.true(core01.isactive)
                    self.false(core00.isactive)

                    # model:set fired during promotion
                    self.gt(await core01.nexsroot.index(), nexus_index_before)

                    # Old leader (now mirror) syncs the model:set from the new leader
                    await asyncio.wait_for(core00.sync(), timeout=12)

                    h2 = s_common.guid(s_common.flatten(core01.cellinfo.get('cortex:model')))
                    self.eq(h2, h1)
                    self.eq(h2, s_common.guid(s_common.flatten(core00.cellinfo.get('cortex:model'))))
                    self.nn(core01.model.forms.get('inet:asn'))
                    self.nn(core00.model.forms.get('inet:asn'))

    async def test_cortex_model_nexusify_ext_resilience(self):
        '''
        A broken extended model definition (ext prop referencing a nonexistent form)
        must not wedge boot — _applyExtModel logs a warning and skips the bad entry.
        '''
        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                # Inject a bad extprop directly into storage: form does not exist.
                core.extprops.set('noexist:form:_test:extprop',
                                  ('noexist:form', '_test:extprop', ('str', {}), {}))

            with self.getLoggerStream('synapse.cortex') as stream:
                async with self.getTestCore(dirn=dirn) as core:
                    # Boot must succeed and the valid model must be intact.
                    self.nn(core.model.forms.get('inet:asn'))

                await stream.expect('ext prop (noexist:form:_test:extprop) error')

    async def test_cortex_model_persist_ignore(self):
        '''
        SYNDEV_CORTEX_MODEL_PERSIST_IGNORE lets a cortex boot past an incompatible
        persisted model snapshot by ignoring it and loading the code-derived model.
        '''
        # On a fresh cortex (nothing persisted yet at _loadModels time) the flag is a
        # no-op and must not log the warning.
        with self.getLoggerStream('synapse.cortex') as stream:
            with self.setTstEnvars(SYNDEV_CORTEX_MODEL_PERSIST_IGNORE='true'):
                async with self.getTestCore() as core:
                    self.nn(core.model.forms.get('inet:asn'))

            stream.seek(0)
            self.notin('SYNDEV_CORTEX_MODEL_PERSIST_IGNORE set', stream.read())

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:
                expected_hash = core._mainlinehash

                # Persist a snapshot that hashes differently and is incompatible with
                # the code: a type whose base type does not exist makes addModelDefs raise.
                good_mdefs = list(core.cellinfo.get('cortex:model'))
                bad_mdefs = good_mdefs + [{'types': (('_test:bogus', ('noexist:basetype', {}), {}),)}]
                core.cellinfo.set('cortex:model', bad_mdefs)

            # Without the flag, loading the persisted snapshot wedges boot.
            with self.raises(s_exc.NoSuchType):
                async with self.getTestCore(dirn=dirn): pass

            # With the flag, the snapshot is ignored and the code model is loaded.
            with self.getLoggerStream('synapse.cortex') as stream:
                with self.setTstEnvars(SYNDEV_CORTEX_MODEL_PERSIST_IGNORE='true'):
                    async with self.getTestCore(dirn=dirn) as core:
                        self.eq(core._loadedhash, core._mainlinehash)
                        self.nn(core.model.forms.get('inet:asn'))

                        # Becoming leader re-persists the current code model via model:set.
                        stored_hash = s_common.guid(s_common.flatten(core.cellinfo.get('cortex:model')))
                        self.eq(stored_hash, expected_hash)

                await stream.expect('SYNDEV_CORTEX_MODEL_PERSIST_IGNORE set')

            # The snapshot was repaired, so a subsequent boot without the flag is clean.
            async with self.getTestCore(dirn=dirn) as core:
                self.eq(core._loadedhash, core._mainlinehash)
                self.nn(core.model.forms.get('inet:asn'))

import os
import json
import asyncio
import itertools
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.layer as s_layer
import synapse.lib.queue as s_queue

import synapse.tests.utils as s_t_utils

import synapse.tools.sync_200 as s_sync
import synapse.tools.migrate_200 as s_migr

REGR_VER = '0.1.56-migr'

# Nodes that are expected to be unmigratable
NOMIGR_NDEF = [
    ["migr:test", 22],
]

def getAssetBytes(*paths):
    fp = os.path.join(*paths)
    assert os.path.isfile(fp)
    with open(fp, 'rb') as f:
        byts = f.read()
    return byts

def getAssetJson(*paths):
    byts = getAssetBytes(*paths)
    obj = json.loads(byts.decode())
    return obj

class FakeCoreApi(s_cell.CellApi):
    async def splices(self, offs, size):
        async for splice in self.cell.splices(offs, size):
            yield splice

class FakeCore(s_cell.Cell):
    cellapi = FakeCoreApi
    confdefs = {
        'lyr': {
            'type': 'string',
        },
    }

    async def __anit__(self, dirn, conf=None):
        await s_cell.Cell.__anit__(self, dirn, conf=conf)
        self.lyr = self.conf.get('lyr')
        self.splicelog = {}
        self.splicelim = -1

    async def loadSplicelog(self, splicelog):
        for lyriden, items in splicelog.items():
            self.splicelog[lyriden] = s_common.tuplify(items)

    async def setSplicelim(self, lim):
        self.splicelim = lim

    async def getSpliceBatches(self, lyriden):
        splices = self.splicelog[lyriden]['splices']
        num_splices = len(splices)
        batches = []
        nodesplices = []
        ndef = None
        for i, splice in enumerate(splices):
            splice_ndef = splice[1]['ndef']

            if (ndef is not None and splice_ndef != ndef) or i == num_splices - 1:
                batches.append((ndef, nodesplices))
                nodesplices = []

            ndef = splice_ndef
            nodesplices.append(splice)

        return batches

    async def splices(self, offs, size):
        imax = size - 1

        for i, splice in enumerate(self.splicelog[self.lyr]['splices']):
            if i < offs:
                continue

            yield splice

            if i == imax or i == self.splicelim:
                return

class SyncTest(s_t_utils.SynTest):
    @contextlib.asynccontextmanager
    async def _getFakeCoreUrl(self, lyr):
        with self.getTestDir() as dirn:

            conf = {
                'lyr': lyr,
            }

            async with await FakeCore.anit(dirn=dirn, conf=conf) as fkcore:
                with self.getRegrDir('assets', REGR_VER) as assetdir:
                    splices = getAssetJson(assetdir, 'splices.json')
                    await fkcore.loadSplicelog(splices)

                root = await fkcore.auth.getUserByName('root')
                await root.setPasswd('root')

                info = await fkcore.dmon.listen(f'tcp://127.0.0.1:0/')
                fkcore.dmon.test_addr = info

                fkurl = fkcore.getLocalUrl()
                yield fkcore, fkurl

    @contextlib.asynccontextmanager
    async def _getMigratedCoreUrl(self):
        with self.getRegrDir('cortexes', REGR_VER) as src:
            with self.getTestDir() as dest:
                conf = {
                    'src': src,
                    'dest': dest,
                }

                async with await s_migr.Migrator.anit(conf) as migr:
                    await migr.migrate()

                async with await s_cortex.Cortex.anit(dest, conf=None) as core:
                    turl = core.getLocalUrl()
                    yield core, turl

    @contextlib.asynccontextmanager
    async def _getCoreUrls(self):
        async with self._getMigratedCoreUrl() as (core, turl):
            lyr = [lyr.iden for lyr in core.view.layers][-1]

            async with self._getFakeCoreUrl(lyr) as (fkcore, fkurl):
                yield core, turl, fkcore, fkurl

    @contextlib.asynccontextmanager
    async def _getSyncSvc(self, conf_sync=None):
        async with self._getCoreUrls() as (core, turl, fkcore, fkurl):

            conf = {
                'src': fkurl,
                'dest': turl,
                'offsfile': os.path.join(core.dirn, 'migration', 'lyroffs.yaml'),
            }
            if conf_sync is not None:
                conf.update(conf_sync)

            with self.getTestDir() as dirn:
                async with await s_sync.SyncMigrator.anit(dirn, conf) as sync:
                    yield core, turl, fkcore, fkurl, sync

    async def _checkCore(self, core):
        with self.getRegrDir('assets', REGR_VER) as assetdir:
            podesj = getAssetJson(assetdir, 'splicepodes.json')
            podesj = [p for p in podesj if p[0] not in NOMIGR_NDEF]
            tpodes = s_common.tuplify(podesj)

            # check all nodes (removing empty nodedata key)
            nodes = await core.nodes('.created -meta:source:name=test')

            podes = [n.pack(dorepr=True) for n in nodes]
            podes = [(p[0], {k: v for k, v in p[1].items() if k != 'nodedata'}) for p in podes]
            self.gt(len(podes), 0)

            # handle the case where a tag with tagprops was deleted but tag:prop:del splices aren't generated
            for pode in podes:
                tags = pode[1]['tags'].keys()
                pode[1]['tagprops'] = {k: v for k, v in pode[1]['tagprops'].items() if k in tags}
                pode[1]['tagpropreprs'] = {k: v for k, v in pode[1]['tagpropreprs'].items() if k in tags}

            try:
                self.eq(podes, tpodes)
            except AssertionError:
                # print a more useful diff on error
                notincore = list(itertools.filterfalse(lambda x: x in podes, tpodes))
                notintest = list(itertools.filterfalse(lambda x: x in tpodes, podes))
                self.eq(notincore, notintest)  # should be empty, therefore equal
                raise

            # manually check node subset
            self.len(1, await core.nodes('inet:ipv4=1.2.3.4'))
            self.len(2, await core.nodes('inet:dns:a:ipv4=1.2.3.4'))

    async def test_sync_stormsvc(self):
        conf_sync = {
            'poll_s': 1,
        }
        async with self._getSyncSvc(conf_sync) as (core, turl, fkcore, fkurl, sync):
            # add sync stormsvc
            sync.dmon.share('migrsync', sync)
            root = await sync.auth.getUserByName('root')
            await root.setPasswd('root')

            info = await sync.dmon.listen('tcp://127.0.0.1:0/')
            sync.dmon.test_addr = info
            host, port = info

            surl = f'tcp://root:root@127.0.0.1:{port}/migrsync'
            await core.nodes(f'service.add migrsync {surl}')
            await core.nodes(f'$lib.service.wait(migrsync)')

            self.nn(core.getStormCmd('migrsync.status'))
            self.nn(core.getStormCmd('migrsync.startfromfile'))
            self.nn(core.getStormCmd('migrsync.startfromlast'))
            self.nn(core.getStormCmd('migrsync.stopsync'))

            # run svc operations
            lyridens = list(core.layers.keys())

            mesgs = await core.stormlist(f'migrsync.status')
            self.eq('', ''.join([x[1].get('mesg') for x in mesgs if x[0] == 'print']))
            # empty

            mesgs = await core.stormlist(f'migrsync.startfromfile')
            self.stormIsInPrint('Sync started', mesgs)
            self.stormIsInPrint(lyridens[0], mesgs)
            self.stormIsInPrint(lyridens[1], mesgs)

            mesgs = await core.stormlist(f'migrsync.status')
            self.eq(4, ''.join([x[1].get('mesg') for x in mesgs if x[0] == 'print']).count('active'))

            mesgs = await core.stormlist(f'migrsync.stopsync')
            self.stormIsInPrint('Sync stopped', mesgs)
            self.stormIsInPrint(lyridens[0], mesgs)
            self.stormIsInPrint(lyridens[1], mesgs)

            mesgs = await core.stormlist(f'migrsync.status')
            self.eq(4, ''.join([x[1].get('mesg') for x in mesgs if x[0] == 'print']).count('cancelled'))

            mesgs = await core.stormlist(f'migrsync.startfromlast')
            self.stormIsInPrint('Sync started', mesgs)
            self.stormIsInPrint(lyridens[0], mesgs)
            self.stormIsInPrint(lyridens[1], mesgs)

            mesgs = await core.stormlist(f'migrsync.status')
            self.eq(4, ''.join([x[1].get('mesg') for x in mesgs if x[0] == 'print']).count('active'))

            # enable/disable migrationMode
            self.false(core.agenda.enabled)
            self.false(core.trigson)

            mesgs = await core.stormlist(f'migrsync.migrationmode.disable')
            self.stormIsInPrint('migrationMode successfully disabled', mesgs)
            self.true(core.agenda.enabled)
            self.true(core.trigson)

            mesgs = await core.stormlist(f'migrsync.migrationmode.enable')
            self.stormIsInPrint('migrationMode successfully enabled', mesgs)
            self.false(core.agenda.enabled)
            self.false(core.trigson)

    async def test_startSyncFromFile(self):
        conf_sync = {
            'poll_s': 1,
        }
        async with self._getSyncSvc(conf_sync) as (core, turl, fkcore, fkurl, sync):
            async with sync.getLocalProxy() as syncprx:
                wlyr = core.view.layers[-1]
                seclyr = [v for k, v in core.layers.items() if k != wlyr.iden][0]
                num_splices = len(fkcore.splicelog[wlyr.iden]['splices'])

                self.true(core.trigson)
                self.true(core.agenda.enabled)

                # kick off a sync
                # note that both layers will sync since they are in the migration offs file
                # but the splices from the wlyr will be incorrectly pushed to both
                # due to fakecore handling so just check the wlyr
                await syncprx.startSyncFromFile()
                self.eq(0, sync.errcnts.get(seclyr.iden, defv=-1))

                self.false(core.trigson)
                self.false(core.agenda.enabled)

                self.true(await s_coro.event_wait(sync._pull_evnts[wlyr.iden], timeout=4))
                self.true(await s_coro.event_wait(sync._pull_evnts[seclyr.iden], timeout=4))

                self.true(await s_coro.event_wait(sync._push_evnts[wlyr.iden], timeout=2))
                self.true(await s_coro.event_wait(sync._push_evnts[seclyr.iden], timeout=2))

                self.eq(num_splices, sync.pull_offs.get(wlyr.iden))
                self.eq(num_splices, sync.push_offs.get(wlyr.iden))

                # we have read all the splices but the status is dependent on where the loop is
                status = await syncprx.status(True)
                self.true(status[wlyr.iden]['src:pullstatus'] in ('up_to_date', 'reading_at_live'))

                self.gt(sync.errcnts.get(seclyr.iden, defv=-1), 0)

                await self._checkCore(core)

                # make sure tasks are still running
                self.false(sync.pull_tasks[wlyr.iden].done())
                self.false(sync.push_tasks[wlyr.iden].done())
                self.false(sync._queues[wlyr.iden].isfini)

                # stop sync
                await syncprx.stopSync()
                await asyncio.sleep(0)

                self.true(core.trigson)
                self.true(core.agenda.enabled)

                self.true(sync.pull_tasks[wlyr.iden].done())
                self.true(sync.push_tasks[wlyr.iden].done())
                self.true(sync._queues[wlyr.iden].isfini)

                status = await syncprx.status(pprint=True)
                statusp = ' '.join([v.get('pprint') for v in status.values()])
                self.eq(4, statusp.count('cancelled'))

                # restart sync over same splices with queue cap less than total splices
                sync.q_cap = 100
                await syncprx.startSyncFromFile()
                self.eq(0, sync.errcnts.get(seclyr.iden, defv=-1))

                self.false(core.trigson)
                self.false(core.agenda.enabled)

                self.true(await s_coro.event_wait(sync._pull_evnts[wlyr.iden], timeout=5))
                self.true(await s_coro.event_wait(sync._push_evnts[wlyr.iden], timeout=5))

                status = await syncprx.status()
                self.true(status[wlyr.iden]['src:pullstatus'] in ('up_to_date', 'reading_at_live'))

                await self._checkCore(core)

                # fini the queue
                await sync._queues[wlyr.iden].fini()

                await asyncio.wait_for(sync.pull_tasks[wlyr.iden], timeout=4)

                self.eq('queue_fini', sync._pull_status[wlyr.iden])

                # run stopsync with a prx exception
                sync.dest = 'foobar'
                stopres = await syncprx.stopSync()
                self.len(2, stopres)  # returns the two layers stopped

                retn = await syncprx.enableMigrationMode()
                self.isin('encountered an error', retn)

                retn = await syncprx.disableMigrationMode()
                self.isin('encountered an error', retn)

    async def test_startSyncFromLast(self):
        conf_sync = {
            'poll_s': 1,
        }
        async with self._getSyncSvc(conf_sync) as (core, turl, fkcore, fkurl, sync):
            async with sync.getLocalProxy() as syncprx:
                wlyr = core.view.layers[-1]
                num_splices = len(fkcore.splicelog[wlyr.iden]['splices'])

                self.true(core.trigson)
                self.true(core.agenda.enabled)

                lim = 100
                await fkcore.setSplicelim(lim)

                self.eq(0, sync.pull_offs.get(wlyr.iden))
                self.eq(0, sync.push_offs.get(wlyr.iden))

                # kick off a sync and then stop it so we can resume
                await sync.startLyrSync(wlyr.iden, 0)

                self.false(core.trigson)
                self.false(core.agenda.enabled)

                await sync.stopSync()

                self.true(core.trigson)
                self.true(core.agenda.enabled)

                # resume sync from last
                await syncprx.startSyncFromLast()

                self.false(core.trigson)
                self.false(core.agenda.enabled)

                self.true(await s_coro.event_wait(sync._pull_evnts[wlyr.iden], timeout=10))
                self.true(await s_coro.event_wait(sync._push_evnts[wlyr.iden], timeout=5))

                self.eq(num_splices, sync.pull_offs.get(wlyr.iden))
                self.eq(num_splices, sync.push_offs.get(wlyr.iden))

                await self._checkCore(core)

                # make sure tasks are still running
                self.false(sync.pull_tasks[wlyr.iden].done())
                self.false(sync.push_tasks[wlyr.iden].done())
                self.false(sync._queues[wlyr.iden].isfini)

                status = await syncprx.status()
                status_exp = {
                    'src:nextoffs': num_splices,
                    'dest:nextoffs': num_splices,
                    'queue': {'isfini': False, 'len': 0},
                    'src:task': {'isdone': False, 'status': 'active'},
                    'dest:task': {'isdone': False, 'status': 'active'},
                    'src:pullstatus': 'up_to_date',
                }
                self.none(status.get('pprint'))
                self.eq(status_exp, {k: v for k, v in status.get(wlyr.iden, {}).items() if k in status_exp})

                status = await syncprx.status(pprint=True)
                self.nn(status.get(wlyr.iden, {}).get('pprint'))

                # tasks should keep running on dropped connections
                await fkcore.fini()
                await core.fini()

                self.false(sync.pull_tasks[wlyr.iden].done())
                self.false(sync.push_tasks[wlyr.iden].done())
                self.false(sync._queues[wlyr.iden].isfini)

                # trigger migrmode reset on connection drop
                sync.migrmode_evnt.clear()
                sync.schedCoro(sync._destPushLyrNodeedits(wlyr.iden))
                self.true(await s_coro.event_wait(sync.migrmode_evnt, timeout=5))

    async def test_sync_assvr(self):
        with self.getTestDir() as dirn, self.withSetLoggingMock():
            argv = [
                dirn,
                '--src', 'tcp://foo:123',
                '--dest', 'tcp://bar:456',
                '--offsfile', 'foo.yaml',
                '--telepath', 'tcp://127.0.0.1:0',
                '--https', 0,
            ]

            async with await s_sync.SyncMigrator.initFromArgv(argv) as sync:
                self.eq('tcp://foo:123', sync.src)
                self.eq('tcp://bar:456', sync.dest)
                self.eq('foo.yaml', sync.offsfile)
                self.eq(60, sync.poll_s)
                self.eq(10, sync.err_lim)
                self.eq(100000, sync.q_size)
                self.eq(90000, sync.q_cap)

                tbase = 'tcp://foo:123'
                lyriden = '75adb79a576b31a65f0a1afad5d90665'
                self.raises(s_sync.SyncInvalidTelepath, sync._getLayerUrl, 'baz://0.0.0.0:123', lyriden)
                self.eq(f'{tbase}/cortex/layer/{lyriden}', sync._getLayerUrl(tbase, lyriden))

                self.none(sync.migrmode.valu)
                await self.asyncraises(s_exc.BadTypeValu, sync.setMigrationModeOverride('foobar'))
                await sync.setMigrationModeOverride(True)
                self.true(sync.migrmode.valu)

            # check that migrmode override persists
            async with await s_sync.SyncMigrator.initFromArgv(argv) as sync:
                self.true(sync.migrmode.valu)

    async def test_sync_srcIterLyrSplices(self):
        async with self._getSyncSvc() as (core, turl, fkcore, fkurl, sync):
            wlyr = core.view.layers[-1].iden

            async with await s_telepath.openurl(os.path.join(fkurl, 'cortex', 'layer', wlyr)) as prx:
                async with await s_queue.Window.anit(maxsize=None) as queue:
                    nextoffs_exp = (len(fkcore.splicelog[wlyr]['splices']), True)

                    async def genr(offs):
                        async for splice in prx.splices(offs, -1):  # -1 to avoid max
                            yield splice

                    nextoffs = await sync._srcIterLyrSplices(genr, 0, queue)
                    self.eq(nextoffs, nextoffs_exp)
                    self.len(nextoffs[0], queue.linklist)

    async def test_sync_trnNodeSplicesToNodeedits(self):
        async with self._getSyncSvc() as (core, turl, fkcore, fkurl, sync):
            wlyr = core.view.layers[-1]
            batches = await fkcore.getSpliceBatches(wlyr.iden)

            # load the destination model into the sync service
            model = await core.getModelDict()
            sync.model.update(model)

            # generate nodeedits
            nodeedits = []
            errs = []
            for ndef, splices in batches:
                err, ne, meta = await sync._trnNodeSplicesToNodeedit(ndef, splices)
                if err is None:
                    nodeedits.append((ne, meta))
                else:
                    errs.append(err)

            # expect one error for migration module not loaded in 2.x.x cortex
            self.len(1, errs)
            self.isin('migr:test', errs[0]['mesg'])
            self.eq(len(batches) - 1, len(nodeedits))

            # feed nodeedits to 2.x.x cortex and get back the sodes
            sodes = []
            for ne, meta in nodeedits:
                sodes.extend(await wlyr.storNodeEdits([ne], meta))

            self.eq(len(nodeedits), len(sodes))

            # check that the destination cortex has all of the post-splice updated data
            await self._checkCore(core)

            # feed bad splices
            ne = await sync._trnNodeSplicesToNodeedit(('inet:fqdn', 'foo.com'), [('no:way', {})])
            self.nn(ne[0])

            info = [('prop:set', {'prop': 'nah', 'valu': 0})]
            ne = await sync._trnNodeSplicesToNodeedit(('inet:fqdn', 'foo.com'), info)
            self.nn(ne[0])

            info = [('tag:prop:set', {'prop': 'spaz', 'valu': 0})]
            ne = await sync._trnNodeSplicesToNodeedit(('inet:fqdn', 'foo.com'), info)
            self.nn(ne[0])

            # array props
            splices = [
                ('prop:set', {'ndef': ('ou:org', 'd1589a60391797c88c91efdcac050c76'), 'prop': 'names',
                              'valu': ('foo baz industries', 'bar bam company'),
                              'time': 1583285174623, 'user': '970419f1a79f8f3940a5c8cde20f40ea',
                              'prov': '5461a804fbf9ff24180921f061a93ecd'}),
            ]
            ndef = splices[0][1]['ndef']

            err, ne, meta = await sync._trnNodeSplicesToNodeedit(ndef, splices)
            self.eq(s_layer.STOR_TYPE_UTF8, ne[2][0][1][-1] & 0x7fff)  # array stortype to realtype
            sodes = await wlyr.storNodeEdits([ne], meta)
            self.len(1, sodes)

            splices = [
                ('prop:set',
                 {'ndef': ('crypto:x509:cert', '71dde169f716ed1409f7eeb1cc019393'), 'prop': 'identities:ipv6s',
                  'valu': ('2001:db8:85a3::8a2e:370:7334', '2005:db8:85a3::8a2e:370:7334'),
                  'time': 1585833034884, 'user': 'c3fefa6e343c59564d9d67a83058629e',
                  'prov': '7d93085dbb13f301762eb5e9afe82522'}),
            ]
            ndef = splices[0][1]['ndef']

            err, ne, meta = await sync._trnNodeSplicesToNodeedit(ndef, splices)
            self.eq(s_layer.STOR_TYPE_IPV6, ne[2][0][1][-1] & 0x7fff)  # array stortype to realtype
            sodes = await wlyr.storNodeEdits([ne], meta)
            self.len(1, sodes)

            # array as a primary prop
            mdef = {
                'types': (
                    ('test:array', ('array', {'type': 'inet:fqdn'}), {}),
                ),
                'forms': (
                    ('test:array', {}, (
                    )),
                ),
            }
            core.model.addDataModels([('asdf', mdef)])
            model = await core.getModelDict()
            sync.model.update(model)

            splices = [
                ('node:add',
                 {'ndef': ('test:array', ('foo.faz', 'faz.bar')), 'time': 1585833356459,
                  'user': 'c3fefa6e343c59564d9d67a83058629e', 'prov': '007462a9c62eac3a0d7840631c1ffda8'}),
            ]
            ndef = splices[0][1]['ndef']

            err, ne, meta = await sync._trnNodeSplicesToNodeedit(ndef, splices)
            self.eq(s_layer.STOR_TYPE_FQDN, ne[2][0][1][-1] & 0x7fff)  # array stortype to realtype
            sodes = await wlyr.storNodeEdits([ne], meta)
            self.len(1, sodes)

    async def test_sync_destIterLyrNodeedits(self):
        async with self._getSyncSvc() as (core, turl, fkcore, fkurl, sync):
            wlyr = core.view.layers[-1]

            async with await s_telepath.openurl(os.path.join(turl, 'layer', wlyr.iden)) as prx:
                async with await s_queue.Window.anit(maxsize=None) as queue:
                    sync.model.update(await core.getModelDict())
                    sync._push_evnts[wlyr.iden] = asyncio.Event()

                    writer = prx.storNodeEditsNoLift

                    # test that queue can be empty when task starts
                    task = sync.schedCoro(sync._destIterLyrNodeedits(writer, queue, wlyr.iden))

                    # fill up the queue with splices
                    offs = 0
                    async for splice in fkcore.splices(0, -1):
                        await queue.put((offs, splice))
                        offs += 1

                    self.true(await s_coro.event_wait(sync._push_evnts[wlyr.iden], timeout=5))
                    self.eq(0, len(queue.linklist))
                    await self._checkCore(core)

                    # put untranslatable splices into the queue
                    # make sure task stays running
                    await queue.puts([
                        (offs, ('foo', {'ndef': 'bar'})),
                        (offs + 1, ('cat', {'ndef': 'dog'})),
                    ])
                    self.true(await s_coro.event_wait(sync._push_evnts[wlyr.iden], timeout=5))
                    errs = [err async for err in sync.getLyrErrs(wlyr.iden)]
                    self.len(2, errs)
                    self.eq(2, sync.errcnts.get(wlyr.iden))
                    self.eq(offs + 1, errs[1][0])
                    self.false(task.done())

                    # reach error limit which will kill task
                    await queue.puts([(offs + i, ('foo', {'ndef': str(i)})) for i in range(3, 50)])
                    await self.asyncraises(s_sync.SyncErrLimReached, asyncio.wait_for(task, timeout=2))
                    errs = [err async for err in sync.getLyrErrs(wlyr.iden)]
                    self.len(10, errs)
                    self.eq(10, sync.errcnts.get(wlyr.iden))

                    tasksum = await sync._getTaskSummary(task)
                    self.true(tasksum.get('isdone'))
                    self.false(tasksum.get('cancelled'))
                    self.isin('Error limit reached', tasksum.get('exc'))

            async with await s_telepath.openurl(os.path.join(turl, 'layer', wlyr.iden)) as prx:
                async with await s_queue.Window.anit(maxsize=None) as queue:
                    sync.err_lim += 10
                    sync.model.update(await core.getModelDict())
                    sync._push_evnts[wlyr.iden] = asyncio.Event()

                    writer = prx.storNodeEditsNoLift

                    # fill up the queue with splices
                    offs = 0
                    async for splice in fkcore.splices(0, -1):
                        await queue.put((offs, splice))
                        offs += 1

                    # start with a fini'd proxy
                    await prx.fini()
                    task = sync.schedCoro(sync._destIterLyrNodeedits(writer, queue, wlyr.iden))
                    await asyncio.sleep(0)
                    self.true(task.done())
                    self.eq(offs, len(queue.linklist))  # pulled splices should be put back in queue

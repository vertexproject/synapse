import os
import json
import asyncio
import itertools
import contextlib

import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.queue as s_queue

import synapse.tests.utils as s_t_utils

import synapse.tools.sync_020 as s_sync
import synapse.tools.migrate_020 as s_migr

REGR_VER = '0.1.51-migr'

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

def tupleize(obj):
    '''
    Convert list objects to tuples in a nested python struct.
    '''
    if isinstance(obj, (list, tuple)):
        return tuple([tupleize(o) for o in obj])
    if isinstance(obj, dict):
        return {k: tupleize(v) for k, v in obj.items()}
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
            self.splicelog[lyriden] = tupleize(items)

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
            tpodes = tupleize(podesj)

            # check all nodes
            nodes = await core.nodes('.created -meta:source:name=test')

            podes = [n.pack(dorepr=True) for n in nodes]
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

    async def test_startSyncFromFile(self):
        conf_sync = {
            'poll_s': 1,
        }
        async with self._getSyncSvc(conf_sync) as (core, turl, fkcore, fkurl, sync):
            async with sync.getLocalProxy() as syncprx:
                wlyr = core.view.layers[-1]
                num_splices = len(fkcore.splicelog[wlyr.iden]['splices'])

                # kick off a sync
                # note that both layers will sync since they are in the migration offs file
                # but the splices from the wlyr will be incorrectly pushed to both
                # due to fakecore handling so just check the wlyr
                await syncprx.startSyncFromFile()
                await asyncio.sleep(1)

                self.eq(num_splices, sync.pull_offs.get(wlyr.iden))
                self.eq(num_splices, sync.push_offs.get(wlyr.iden))

                await self._checkCore(core)

                # make sure tasks are still running
                self.false(sync._pull_tasks[wlyr.iden].done())
                self.false(sync._push_tasks[wlyr.iden].done())
                self.false(sync._queues[wlyr.iden].isfini)

                # stop sync
                await syncprx.stopSync()

                self.true(sync._pull_tasks[wlyr.iden].done())
                self.true(sync._push_tasks[wlyr.iden].done())
                self.true(sync._queues[wlyr.iden].isfini)

                await syncprx.status()

                # restart sync over same splices
                sync.q_cap = 3
                await syncprx.startSyncFromFile()
                await asyncio.sleep(1)

                self.eq('read_to_qcap', sync._pull_status[wlyr.iden])

                await self._checkCore(core)

                # fini the queue
                await sync._queues[wlyr.iden].fini()
                await asyncio.sleep(1)
                self.eq('queue_fini', sync._pull_status[wlyr.iden])

    async def test_startSyncFromLast(self):
        conf_sync = {
            'poll_s': 1,
        }
        async with self._getSyncSvc(conf_sync) as (core, turl, fkcore, fkurl, sync):
            async with sync.getLocalProxy() as syncprx:
                wlyr = core.view.layers[-1]
                num_splices = len(fkcore.splicelog[wlyr.iden]['splices'])

                lim = 30
                await fkcore.setSplicelim(lim)

                self.eq(0, sync.pull_offs.get(wlyr.iden))
                self.eq(0, sync.push_offs.get(wlyr.iden))

                # kick off a sync
                await sync._startLyrSync(wlyr.iden, 0)
                await asyncio.sleep(1)

                self.eq(lim + 1, sync.pull_offs.get(wlyr.iden))
                self.eq(lim + 1, sync.push_offs.get(wlyr.iden))

                # resume sync from last
                await syncprx.startSyncFromLast()
                await asyncio.sleep(1)

                self.eq(num_splices, sync.pull_offs.get(wlyr.iden))
                self.eq(num_splices, sync.push_offs.get(wlyr.iden))

                await self._checkCore(core)

                # make sure tasks are still running
                self.false(sync._pull_tasks[wlyr.iden].done())
                self.false(sync._push_tasks[wlyr.iden].done())
                self.false(sync._queues[wlyr.iden].isfini)

                status = await syncprx.status()
                status_exp = {
                    'src:nextoffs': num_splices,
                    'dest:nextoffs': num_splices,
                    'queue': {'isfini': False, 'len': 0},
                    'src:task': {'isdone': False},
                    'dest:task': {'isdone': False},
                    'src:pullstatus': 'up_to_date',
                }
                self.eq(status_exp, {k: v for k, v in status.get(wlyr.iden, {}).items() if k in status_exp})

                # tasks should keep running on dropped connections
                await fkcore.fini()
                await core.fini()
                await asyncio.sleep(1)

                self.false(sync._pull_tasks[wlyr.iden].done())
                self.false(sync._push_tasks[wlyr.iden].done())
                self.false(sync._queues[wlyr.iden].isfini)

    async def test_sync_assvr(self):
        with self.getTestDir() as dirn:
            argv = [
                dirn,
                '--src', 'tcp://foo:123',
                '--dest', 'tcp://bar:456',
                '--offsfile', 'foo.yaml',
            ]

            async with await s_sync.main(argv) as sync:
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

    async def test_sync_srcPullLyrSplices(self):
        conf_sync = {
            'poll_s': 1,
        }
        async with self._getSyncSvc(conf_sync) as (core, turl, fkcore, fkurl, sync):
            async with await s_queue.Window.anit(maxsize=None) as queue:
                wlyr = core.view.layers[-1]
                num_splices = len(fkcore.splicelog[wlyr.iden]['splices'])
                sync._queues[wlyr.iden] = queue
                sync.pull_offs.set(wlyr.iden, 0)

                # artifically limit splices returned so we get multiple passes
                lim = 100
                await fkcore.setSplicelim(lim)
                task = sync.schedCoro(sync._srcPullLyrSplices(wlyr.iden))
                await asyncio.sleep(1)
                self.len(lim + 1, queue.linklist)

                await asyncio.sleep(1)
                self.len(num_splices, queue.linklist)

    async def test_sync_srcIterLyrSplices(self):
        async with self._getSyncSvc() as (core, turl, fkcore, fkurl, sync):
            wlyr = core.view.layers[-1].iden

            async with await s_telepath.openurl(os.path.join(fkurl, 'cortex', 'layer', wlyr)) as prx:
                async with await s_queue.Window.anit(maxsize=None) as queue:
                    nextoffs_exp = len(fkcore.splicelog[wlyr]['splices'])
                    nextoffs = await sync._srcIterLyrSplices(prx, 0, queue)
                    self.eq(nextoffs, nextoffs_exp)
                    self.len(nextoffs, queue.linklist)

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

            # expect one error for migration module not loaded in 0.20 cortex
            self.len(1, errs)
            self.isin('migr:test', errs[0]['mesg'])
            self.eq(len(batches) - 1, len(nodeedits))

            # feed nodeedits to 0.2.x cortex and get back the sodes
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

    async def test_sync_destIterLyrNodeedits(self):
        async with self._getSyncSvc() as (core, turl, fkcore, fkurl, sync):
            wlyr = core.view.layers[-1]

            async with await s_telepath.openurl(os.path.join(turl, 'layer', wlyr.iden)) as prx:
                async with await s_queue.Window.anit(maxsize=None) as queue:
                    await sync._loadDatamodel()

                    # test that queue can be empty when task starts
                    task = sync.schedCoro(sync._destIterLyrNodeedits(prx, queue, wlyr.iden))

                    # fill up the queue with splices
                    offs = 0
                    async for splice in fkcore.splices(0, -1):
                        await queue.put((offs, splice))
                        offs += 1

                    await asyncio.sleep(1)
                    self.eq(0, len(queue.linklist))
                    await self._checkCore(core)

                    # put untranslatable splices into the queue
                    # make sure task stays running
                    await queue.puts([
                        (offs, ('foo', {'ndef': 'bar'})),
                        (offs + 1, ('cat', {'ndef': 'dog'})),
                    ])
                    await asyncio.sleep(1)
                    errs = await sync.getLyrErrs(wlyr.iden)
                    self.len(2, errs)
                    self.eq(offs + 1, errs[1][0])
                    self.false(task.done())

                    # reach error limit which will kill task
                    await queue.puts([(offs + i, ('foo', {'ndef': str(i)})) for i in range(3, 50)])
                    await asyncio.sleep(1)
                    errs = await sync.getLyrErrs(wlyr.iden)
                    self.len(10, errs)

                    tasksum = await sync._getTaskSummary(task)
                    self.true(tasksum.get('isdone'))
                    self.false(tasksum.get('cancelled'))
                    self.isin('Error limit reached', tasksum.get('exc'))

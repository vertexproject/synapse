import os
import json
import asyncio
import logging
import contextlib

import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.queue as s_queue

import synapse.tests.utils as s_t_utils

import synapse.tools.sync_020 as s_sync
import synapse.tools.migrate_020 as s_migr

REGR_VER = '0.1.51-migr'

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
    async def test(self):
        return 'foo'

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

    async def loadSplicelog(self, splicelog):
        for lyriden, items in splicelog.items():
            self.splicelog[lyriden] = items

    async def splices(self, offs, size):
        imax = size - 1
        for i, splice in enumerate(self.splicelog[self.lyr]['splices']):
            if i < offs:
                continue

            yield splice

            if i == imax:
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

                fkcore.dmon.share(f'cortex/layer/{lyr}', fkcore)

                root = await fkcore.auth.getUserByName('root')
                await root.setPasswd('root')

                info = await fkcore.dmon.listen('tcp://127.0.0.1:0/')
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
    async def _getSyncSvc(self):
        async with self._getCoreUrls() as (core, turl, fkcore, fkurl):

            conf = {
                'src': fkurl,
                'dest': turl,
                'offsfile': 'none',
            }

            with self.getTestDir() as dirn:
                async with await s_sync.SyncMigrator.anit(dirn, conf) as sync:
                    yield core, turl, fkcore, fkurl, sync

    async def test_sync_srcIterLyrSplices(self):
        async with self._getSyncSvc() as (core, turl, fkcore, fkurl, sync):
            wlyr = core.view.layers[-1].iden

            async with await s_telepath.openurl(os.path.join(fkurl, 'cortex', 'layer', wlyr)) as prx:
                async with await s_queue.Window.anit(maxsize=None) as queue:
                    nextoffs_exp = len(fkcore.splicelog[wlyr]['splices'])
                    nextoffs = await sync._srcIterLyrSplices(prx, 0, queue)
                    self.eq(nextoffs, nextoffs_exp)
                    self.len(nextoffs, queue.linklist)

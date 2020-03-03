'''
Sync splices from an 0.1.x cortex to 0.2.x
'''
import os
import sys
import asyncio
import logging
import argparse

import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.base as s_base
import synapse.lib.queue as s_queue
import synapse.lib.config as s_config
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

class SyncMigratorApi(s_cell.CellApi):
    '''
    A telepath/cell API for the Sync service.
    '''
    async def status(self):
        return await self.cell.status()

    async def startSyncFromFile(self):
        return await self.cell.startSyncFromFile()

    async def startSyncFromLast(self):
        pass

class SyncMigrator(s_cell.Cell):
    cellapi = SyncMigratorApi
    confdefs = {
        'src': {
            'type': 'string',
            'description': 'Telepath URL for the source 0.1.x cortex.',
        },
        'dest': {
            'type': 'string',
            'description': 'Telepath URL for the destination 0.2.x cortex.',
        },
        'offsfile': {
            'type': 'string',
            'description': 'File path for the YAML file containing layer offsets.'
        }
    }

    async def __anit__(self, dirn, conf=None):
        await s_cell.Cell.__anit__(self, dirn, conf=conf)

        self.src = self.conf.get('src')
        self.dest = self.conf.get('dest')
        self.offsfile = self.conf.get('offsfile')  # TODO

        self.poll_s = 60
        self.pull_fair_iter = 100
        self.push_fair_iter = 100
        self.batch_size = 10

        self.pull_offs = await self.hive.dict(('sync:pulloffs', ))
        self.push_offs = await self.hive.dict(('sync:pushoffs', ))
        self.errors = await self.hive.dict(('sync:errors', ))  # TODO

        self.model = None  # TODO

        self._pull_tasks = {}  # lyriden: task
        self._push_tasks = {}  # lyriden: task

        self.pull_last_start = {}  # TODO
        self.push_last_start = {}  # TODO

        self._queues = {}  # lyriden: queue of splices

    async def status(self):
        pass  # TODO

    async def startSyncFromFile(self):
        # await self._startLyrSync(lyriden, nextoffs)
        pass  # TODO

    async def _startLyrSync(self, lyriden, nextoffs):
        await self._setLyrOffset('pull', lyriden, nextoffs)

        queue = self._queues.get(lyriden)
        if queue is None:
            queue = await s_queue.Window.anit(maxsize=None)
            self.onfini(queue.fini)
            self._queues[lyriden] = queue

        pulltask = self._pull_tasks.get(lyriden)
        if pulltask is None or pulltask.done():
            self._pull_tasks[lyriden] = self.schedCoro(self._srcPullLyrSplices(lyriden))

        pushtask = self._push_tasks.get(lyriden)
        if pushtask is None or pushtask.done():
            self._push_tasks[lyriden] = self.schedCoro(self._destPushLyrNodeedits(lyriden))

    async def _setLyrOffset(self, pushorpull, lyriden, offset):
        if pushorpull == 'pull':
            await self.pull_offs.set(lyriden, offset)
        elif pushorpull == 'push':
            await self.push_offs.set(lyriden, offset)

    async def _getLyrOffset(self, pushorpull, lyriden):
        if pushorpull == 'pull':
            return self.pull_offs.get(lyriden, default=0)
        elif pushorpull == 'push':
            return self.push_offs.get(lyriden, default=0)

    async def _setLyrErr(self, lyriden, offset, mesg):
        pass  # TODO

    async def _getLyrErr(self, lyriden, offset=None):
        pass  # TODO

    async def _loadDatamodel(self):
        pass  # TODO

    async def _srcPullLyrSplices(self, lyriden):
        poll_s = self.poll_s
        queue = self._queues.get(lyriden)
        async with await s_telepath.openurl(os.path.join(self.src, 'cortex', 'layer', lyriden)) as prx:
            while not self.isfini:
                startoffs = await self._getLyrOffset('pull', lyriden)
                logger.info(f'Pulling splices for layer {lyriden} starting from offset {startoffs}')
                self.pull_last_start[lyriden] = s_common.now()

                nextoffs = await self._srcIterLyrSplices(prx, startoffs, queue)

                await self._setLyrOffset('pull', lyriden, nextoffs)

                logger.info(f'All splices from {lyriden} have been read; offsets: {startoffs} -> {lastoffs}')
                await asyncio.sleep(poll_s)

    async def _srcIterLyrSplices(self, prx, startoffs, queue):
        curoffs = startoffs
        fair_iter = self.pull_fair_iter
        async for splice in prx.splices(startoffs, -1):
            await queue.put((curoffs, splice))

            curoffs += 1

            if curoffs % fair_iter == 0:
                await asyncio.sleep(0)

        return curoffs

    async def _trnSpliceToNodeedit(self, splice):
        return None, splice  # TODO

    async def _destPushLyrNodeedits(self, lyriden):
        queue = self._queues.get(lyriden)
        async with await s_telepath.openurl(os.path.join(self.dest, 'cortex', 'layer', lyriden)) as prx:
            logger.info(f'Starting {lyriden} splice queue reader')
            self.push_last_start[lyriden] = s_common.now()
            await self._destIterLyrNodeedits(prx, queue, lyriden)

    async def _destIterLyrNodeedits(self, prx, queue, lyriden):
        fair_iter = self.push_fair_iter
        batch_size = self.batch_size
        nodeddits = []
        cnt = 0
        errs = 0
        offs = -1
        async for offs, splice in queue:
            err, ne = await self._trnSpliceToNodeedit(splice)
            if err is None:
                nodeddits.append(ne)
            else:
                errs += 1
                pass  # TODO

            if len(nodeddits) >= batch_size:
                # await prx.foo(nodeddits)  # TODO
                await self._setLyrOffset('push', lyriden, offs)
                nodeddits = []

            cnt += 1
            if cnt % fair_iter == 0:
                logger.info(f'Yielding {lyriden} queue reader: read={cnt}, errs={errs}, size={len(queue.linklist)}')
                await asyncio.sleep(0)

        if len(nodeddits) > 0:
            # await prx.foo(nodeddits)  # TODO
            await self._setLyrOffset('push', lyriden, offs)

        return errs, cnt

def getParser():
    https = os.getenv('SYN_UNIV_HTTPS', '4443')
    telep = os.getenv('SYN_UNIV_TELEPATH', 'tcp://0.0.0.0:27492/')
    telen = os.getenv('SYN_UNIV_NAME', None)

    pars = argparse.ArgumentParser(prog='synapse.tools.sync_020')
    s_config.common_argparse(pars, https=https, telep=telep, telen=telen)

    return pars

async def cb(cell, opts, outp):
    await s_config.common_cb(cell, opts, outp)

async def main(argv, outp=s_output.stdout):
    pars = getParser()
    cell = await s_config.main(SyncMigrator, argv, pars=pars, cb=cb, outp=outp)
    return cell

if __name__ == '__main__':  # pragma: no cover
    asyncio.run(s_base.main(main(sys.argv[1:])))

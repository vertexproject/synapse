'''
Sync splices from an 0.1.x cortex to 2.x.x
'''
import os
import sys
import asyncio
import logging

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.cell as s_cell
import synapse.lib.time as s_time
import synapse.lib.queue as s_queue
import synapse.lib.layer as s_layer
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.slaboffs as s_slaboffs
import synapse.lib.stormsvc as s_stormsvc

logger = logging.getLogger(__name__)

class SyncInvalidTelepath(s_exc.SynErr): pass
class SyncErrLimReached(s_exc.SynErr): pass

class SyncMigratorApi(s_stormsvc.StormSvc, s_cell.CellApi):
    '''
    A telepath/cell API for the Sync service.
    '''

    _storm_svc_name = 'migrsync'
    _storm_svc_vers = s_version.version  # mirror synapse version
    _storm_svc_pkgs = ({
        'name': _storm_svc_name,
        'version': _storm_svc_vers,
        'commands': (
            {
                'name': f'{_storm_svc_name}.status',
                'descr': 'Print current sync status.',
                'cmdargs': (),
                'cmdconf': {},
                'storm': '''
                    $svc = $lib.service.get($cmdconf.svciden)
                    $retn = $svc.status(True)
                    $lib.print("")
                    for ($iden, $status) in $retn {
                        $lib.print($lib.str.concat($status.pprint, "\\n"))
                    }
                '''
            },
            {
                'name': f'{_storm_svc_name}.startfromfile',
                'descr': 'Start 2.x.x Layer sync from last 0.1.x splice offset recorded during migration.',
                'cmdargs': (),
                'cmdconf': {},
                'storm': '''
                    $svc = $lib.service.get($cmdconf.svciden)
                    $retn = $svc.startSyncFromFile()
                    $lib.print("\\nSync started for the following (Layers, offsets):")
                    for $info in $retn { $lib.print($lib.str.concat("    ", $info)) }
                    $lib.print("")
                '''
            },
            {
                'name': f'{_storm_svc_name}.startfromlast',
                'descr': 'Start 2.x.x Layer sync from last 0.1.x splice offset completed by this service.',
                'cmdargs': (),
                'cmdconf': {},
                'storm': '''
                    $svc = $lib.service.get($cmdconf.svciden)
                    $retn = $svc.startSyncFromLast()
                    $lib.print("\\nSync started for the following (Layers, offsets):")
                    for $info in $retn { $lib.print($lib.str.concat("    ", $info)) }
                    $lib.print("")
                '''
            },
            {
                'name': f'{_storm_svc_name}.stopsync',
                'descr': 'Stop 2.x.x Layer sync from 0.1.x splices',
                'cmdargs': (),
                'cmdconf': {},
                'storm': '''
                    $svc = $lib.service.get($cmdconf.svciden)
                    $retn = $svc.stopSync()
                    $lib.print("\\nSync stopped for the following Layers:")
                    for $info in $retn { $lib.print($lib.str.concat("    ", $info)) }
                    $lib.print("")
                '''
            },
            {
                'name': f'{_storm_svc_name}.migrationmode.enable',
                'descr': 'Prevent crons and triggers from running on 2.x.x Cortex',
                'cmdargs': (),
                'cmdconf': {},
                'storm': '''
                    $svc = $lib.service.get($cmdconf.svciden)
                    $retn = $svc.enableMigrationMode()
                    if $retn { $lib.print("Enabling migrationMode encountered an error: {retn}", retn=$retn) }
                    else { $lib.print("migrationMode successfully enabled") }
                '''
            },
            {
                'name': f'{_storm_svc_name}.migrationmode.disable',
                'descr': 'Allow crons and triggers to run on 2.x.x Cortex',
                'cmdargs': (),
                'cmdconf': {},
                'storm': '''
                    $svc = $lib.service.get($cmdconf.svciden)
                    $retn = $svc.disableMigrationMode()
                    if $retn { $lib.print("Disabling migrationMode encountered an error: {retn}", retn=$retn) }
                    else { $lib.print("migrationMode successfully disabled") }
                '''
            },
        ),
    },)

    async def status(self, pprint=False):
        return await self.cell.status(pprint)

    async def startSyncFromFile(self):
        return await self.cell.startSyncFromFile()

    async def startSyncFromLast(self):
        return await self.cell.startSyncFromLast()

    async def stopSync(self):
        return await self.cell.stopSync()

    async def enableMigrationMode(self):
        await self.cell.setMigrationModeOverride(True)
        return await self.cell.enableMigrationMode()

    async def disableMigrationMode(self):
        await self.cell.setMigrationModeOverride(False)
        return await self.cell.disableMigrationMode()

class SyncMigrator(s_cell.Cell):
    cellapi = SyncMigratorApi
    confdefs = {
        'src': {
            'type': 'string',
            'description': 'Telepath URL for the source 0.1.x cortex.',
        },
        'dest': {
            'type': 'string',
            'description': 'Telepath URL for the destination 2.x.x cortex.',
        },
        'offsfile': {
            'type': 'string',
            'description': 'File path for the YAML file containing layer offsets.',
        },
        'poll_s': {
            'type': 'integer',
            'description': 'The number of seconds to wait between calls to src for new splices.',
            'default': 60,
        },
        'err_lim': {
            'type': 'integer',
            'description': 'Error threshold before syncing will automatically halt.',
            'default': 10,
        },
        'queue_size': {
            'type': 'integer',
            'description': 'The max size of the push/pull queue for each layer.',
            'default': 100000,
        },
        'offs_logging': {
            'type': 'integer',
            'description': 'Log push/pull every every so many offsets.',
            'default': 10000000,
        },
    }

    async def __anit__(self, dirn, conf=None):
        await s_cell.Cell.__anit__(self, dirn, conf=conf)

        self.src = self.conf.get('src')
        self.dest = self.conf.get('dest')
        self.offsfile = self.conf.get('offsfile')
        self.poll_s = self.conf.get('poll_s')
        self.err_lim = self.conf.get('err_lim')
        self.q_size = self.conf.get('queue_size')
        self.offs_logging = self.conf.get('offs_logging')

        # Check that form or prop is not from an older model rev
        # which we know will fail - only loaded for historical splice migration
        self.form_chk = {}
        self.prop_chk = {}

        self.pull_fair_iter = 10
        self.push_fair_iter = 100

        self.q_cap = int(self.q_size * 0.9)

        self.layers = await self.hive.dict(('sync:layer', ))  # lyridens

        self.migrmode = await self.hive.open(('sync:migrmode', ))  # Override migration mode defaults with True/False
        self.migrmode_evnt = asyncio.Event()

        # if migrmode was overridden true, try to re-enable on startup
        if self.migrmode.valu:
            await self.enableMigrationMode()

        path = s_common.gendir(dirn, 'slabs', 'migrsync.lmdb')
        self.slab = await s_lmdbslab.Slab.anit(path, map_async=True)
        self.onfini(self.slab.fini)

        self.pull_offs = s_slaboffs.SlabOffs(self.slab, 'pull_offs')  # key=lyriden
        self.push_offs = s_slaboffs.SlabOffs(self.slab, 'push_offs')  # key=lyriden

        self.errors = self.slab.initdb('errors', dupsort=False)  # key=<lyriden><offset>, val=err
        self.errcnts = await self.slab.getHotCount('count:errors')

        self.model = {}

        self._pull_status = {}  # lyriden: status

        self.pull_tasks = {}  # lyriden: Task
        self.push_tasks = {}

        self.pull_last_start = {}  # lyriden: epoch
        self.push_last_start = {}

        self._pull_evnts = {}  # lyriden: event (set when up-to-date)
        self._push_evnts = {}  # lyriden: event (set when queue is empty)

        self._queues = {}  # lyriden: queue of splices

    async def status(self, pprint=False):
        '''
        Provide sync summary by layer

        Args:
            pprint (bool): Whether to include pretty-printed layer status string in result

        Returns:
            (dict): Summary info with layer idens as keys
        '''
        retn = {}
        for lyriden, _ in self.layers.items():
            pulloffs = self.pull_offs.get(lyriden)
            pushoffs = self.push_offs.get(lyriden)

            queue = self._queues.get(lyriden)
            queuestat = {}
            if queue is not None:
                queuestat = {'isfini': queue.isfini, 'len': len(queue.linklist)}

            srclaststart = self.pull_last_start.get(lyriden)
            if srclaststart is not None:
                srclaststart = s_time.repr(srclaststart)

            destlaststart = self.push_last_start.get(lyriden)
            if destlaststart is not None:
                destlaststart = s_time.repr(destlaststart)

            pullstatus = self._pull_status.get(lyriden)

            srctasksum = await self._getTaskSummary(self.pull_tasks.get(lyriden))
            desttasksum = await self._getTaskSummary(self.push_tasks.get(lyriden))

            errcnt = self.errcnts.get(lyriden, defv=0)

            retn[lyriden] = {
                'src:pullstatus': pullstatus,
                'src:nextoffs': pulloffs,
                'dest:nextoffs': pushoffs,
                'queue': queuestat,
                'src:task': srctasksum,
                'dest:task': desttasksum,
                'src:laststart': srclaststart,
                'dest:laststart': destlaststart,
                'errcnt': errcnt,
                'migrmode_override': self.migrmode.valu,
            }

            if pprint:
                outp = [
                    f'Layer: {lyriden}',
                    (
                        f'{"":^6}|{"last_start":^25}|{"task_status":^15}|{"offset":^15}|{"read_status":^22}|'
                        f'{"queue_live":^15}|{"queue_len":^15}|{"err_cnt":^15}'
                    ),
                    '-' * (128 + 7)
                ]

                # src side
                tasksum = desttasksum.get('status', '-')
                outp.append((
                    f' {"src":<5}| {srclaststart or "-":<24}| {tasksum:<14}| {pulloffs:<14,}| {pullstatus or "-":<21}|'
                    f' {"n/a":<14}| {"n/a":<14}| {"n/a":<14}'
                ))

                # dest side
                tasksum = desttasksum.get('status', '-')
                outp.append((
                    f' {"dest":<5}| {destlaststart or "-":<24}| {tasksum:<14}| {pushoffs:<14,}| {"n/a":<21}|'
                    f' {not queuestat.get("isfini", True)!s:<14}| {queuestat.get("len", 0):<14,}| {errcnt:<14}'
                ))

                retn[lyriden]['pprint'] = '\n'.join(outp)

        return retn

    async def _getTaskSummary(self, task):
        '''
        Creates a summary status dict for a Task.

        Args:
            task (Task):  Task to summarize

        Returns:
            (dict): Summary dict
        '''
        retn = {}
        if task is not None:
            done = task.done()
            retn = {'isdone': done}
            status = 'active'

            if done:
                cancelled = task.cancelled()
                retn['cancelled'] = cancelled
                status = 'cancelled' if cancelled else 'done'

                if not cancelled:
                    exc = task.exception()
                    if exc is not None:
                        retn['exc'] = str(exc)
                        status = 'exception'
                    else:
                        retn['result'] = task.result()
                        status = 'finished'

            retn['status'] = status

        return retn

    async def startSyncFromFile(self):
        '''
        Start sync from layer offsets provided in offsfile generated by migration tool, e.g.
            <lyriden>
                created: <epochms>
                nextoffs: <int>

        Returns:
            (list): Of (<lyriden>, <offset>) tuples
        '''
        lyroffs = s_common.yamlload(self.offsfile)

        retn = []
        for lyriden, info in lyroffs.items():
            await self.resetLyrErrs(lyriden)
            nextoffs = info['nextoffs']
            logger.info(f'Starting Layer splice sync for {lyriden} from file offset {nextoffs}')
            await self.startLyrSync(lyriden, nextoffs)
            retn.append((lyriden, nextoffs))

        return retn

    async def startSyncFromLast(self, lyridens=None):
        '''
        Start sync from minimum last offset stored by pull, or 0 if no offset was ever recorded.
        This can also be used to restart dead tasks.

        Args:
            lyridens (None or list): Restrict sync to a set of layers, or start all if None

        Returns:
            (list): Of (<lyriden>, <offset>) tuples
        '''
        retn = []
        for lyriden, _ in self.layers.items():
            if lyridens is None or lyriden in lyridens:
                nextoffs = self.push_offs.get(lyriden)  # SlabOffs returns 0 if iden doesn't exist
                logger.info(f'Starting Layer splice sync for {lyriden} from last offset {nextoffs}')

                await self.startLyrSync(lyriden, nextoffs)
                retn.append((lyriden, nextoffs))

        return retn

    async def startLyrSync(self, lyriden, nextoffs):
        '''
        Starts up the sync process for a given layer and starting offset.
        Always retrieves a fresh datamodel and sets migration mode.
        Creates layer queue and fires layer push/pull tasks if they do not already exist.

        Args:
            lyriden (str): Layer iden
            nextoffs (int): The layer offset to start sync from
        '''
        await self.layers.set(lyriden, nextoffs)
        self.pull_offs.set(lyriden, nextoffs)
        self.push_offs.set(lyriden, nextoffs)

        await self._loadDatamodel()

        # If migrmode valu is not overridden or overridden to True, enable
        if self.migrmode.valu is None or self.migrmode.valu:
            await self.enableMigrationMode()

        queue = self._queues.get(lyriden)
        if queue is None or queue.isfini:
            queue = await s_queue.Window.anit(maxsize=self.q_size)
            self.onfini(queue.fini)
            self._queues[lyriden] = queue

        pulltask = self.pull_tasks.get(lyriden)
        if pulltask is None or pulltask.done():
            self._pull_evnts[lyriden] = asyncio.Event()
            self.pull_tasks[lyriden] = self.schedCoro(self._srcPullLyrSplices(lyriden))

        pushtask = self.push_tasks.get(lyriden)
        if pushtask is None or pushtask.done():
            self._push_evnts[lyriden] = asyncio.Event()
            self.push_tasks[lyriden] = self.schedCoro(self._destPushLyrNodeedits(lyriden))

    async def _loadDatamodel(self):
        async with await s_telepath.openurl(self.dest) as prx:
            model = await prx.getModelDict()
            self.model.update(model)

    async def stopSync(self):
        '''
        Cancel all tasks and fini queues. Also disable migration mode on dest cortex.

        Returns:
            (list): Of layer idens that were stopped
        '''
        retn = set()

        for lyriden, task in self.pull_tasks.items():
            logger.warning(f'Cancelling {lyriden} pull task')
            task.cancel()
            retn.add(lyriden)

        for lyriden, task in self.push_tasks.items():
            logger.warning(f'Cancelling {lyriden} push task')
            task.cancel()
            retn.add(lyriden)

        for lyriden, queue in self._queues.items():
            logger.warning(f'Fini\'ing {lyriden} queue')
            await queue.fini()
            retn.add(lyriden)

        if not self.migrmode.valu:
            await self.disableMigrationMode()

        logger.info('stopSync complete')
        return list(retn)

    async def setMigrationModeOverride(self, setval):
        if setval is not None and not isinstance(setval, bool):
            raise s_exc.BadTypeValu(valu=setval, mesg='migrationModeOverride requires bool or None')
        await self.migrmode.set(setval)

    async def disableMigrationMode(self):
        retn = None
        try:
            async with await s_telepath.openurl(self.dest) as prx:
                await prx.disableMigrationMode()
            logger.info('Disabled migrationMode')
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as e:
            err = f'Disabling migration mode on dest cortex encountered an error: {e}'
            logger.exception(err)
            retn = err

        self.migrmode_evnt.clear()
        return retn

    async def enableMigrationMode(self):
        retn = None
        try:
            async with await s_telepath.openurl(self.dest) as prx:
                await prx.enableMigrationMode()
            logger.info('Enabled migrationMode')
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception as e:
            err = f'Enabling migration mode on dest cortex encountered an error: {e}'
            logger.exception(err)
            retn = err

        self.migrmode_evnt.set()
        return retn

    async def resetLyrErrs(self, lyriden):
        self.errcnts.set(lyriden, 0)
        lpref = s_common.uhex(lyriden)
        for lkey, _ in self.slab.scanByPref(lpref, db=self.errors):
            self.slab.pop(lkey, db=self.errors)

    async def _setLyrErr(self, lyriden, offset, err):
        self.errcnts.inc(lyriden)
        lkey = s_common.uhex(lyriden) + s_common.int64en(offset)
        errb = s_msgpack.en(err)
        return self.slab.put(lkey, errb, dupdata=False, overwrite=True, db=self.errors)

    async def getLyrErrs(self, lyriden):
        lpref = s_common.uhex(lyriden)
        for lkey, errb in self.slab.scanByPref(lpref, db=self.errors):
            offset = s_common.int64un(lkey[16:])
            err = s_msgpack.un(errb)
            yield offset, err

    def _getLayerUrl(self, tbase, lyriden):
        '''
        Helper for handling local/tcp urls.

        Args:
            tbase (str): Base telepath url of cell or tcp type
            lyriden (str): Layer iden

        Returns:
            (str): Url to the layer
        '''
        if tbase.startswith('cell:'):
            return os.path.join(tbase, 'layer', lyriden)
        if tbase.startswith('tcp:'):
            return os.path.join(tbase, 'cortex', 'layer', lyriden)
        raise SyncInvalidTelepath(mesg=f'Invalid telepath url base provided: {tbase}')

    async def _srcPullLyrSplices(self, lyriden):
        '''
        Open a proxy to the source layer and initiates splice reader.
        Intended to be run as a free-running task, and will poll for updates every poll_s.

        Args:
            lyriden (str): Layer iden
        '''
        trycnt = 0
        q_cap = self.q_cap
        poll_s = self.poll_s
        turl = self._getLayerUrl(self.src, lyriden)
        while not self.isfini:
            try:
                trycnt += 1
                prx = await s_telepath.openurl(turl)
                trycnt = 0

                logger.info(f'Connected to source {lyriden}')
                islive = False

                async def genr(offs):
                    async for splice in prx.splices(offs, -1):  # -1 to avoid max
                        yield splice

                while not prx.isfini:
                    queue = self._queues.get(lyriden)
                    startoffs = self.pull_offs.get(lyriden)

                    logger.debug(f'Pulling splices for layer {lyriden} starting from offset {startoffs}')
                    if islive:
                        self._pull_status[lyriden] = 'reading_at_live'
                    else:
                        self._pull_status[lyriden] = 'reading_catchup'

                    self._pull_evnts[lyriden].clear()

                    self.pull_last_start[lyriden] = s_common.now()
                    nextoffs, islive = await self._srcIterLyrSplices(genr, startoffs, queue)

                    self.pull_offs.set(lyriden, nextoffs)

                    while not islive and len(queue.linklist) > q_cap:
                        await asyncio.sleep(1)

                    if queue.isfini:
                        logger.warning(f'Queue is finid; stopping {lyriden} src pull')
                        self._pull_status[lyriden] = 'queue_fini'
                        return

                    if islive:
                        if nextoffs == startoffs:
                            logger.debug(f'All splices from {lyriden} have been read')
                            self._pull_status[lyriden] = 'up_to_date'
                            self._pull_evnts[lyriden].set()

                        await asyncio.sleep(poll_s)

            except asyncio.CancelledError:  # pragma: no cover
                raise
            except (ConnectionError, s_exc.IsFini):
                logger.exception(f'Source layer connection error cnt={trycnt}: {lyriden}')
                self._pull_status[lyriden] = 'connect_err'
                await asyncio.sleep(2 ** trycnt)

    async def _srcIterLyrSplices(self, genr, startoffs, queue):
        '''
        Iterate over available splices for a given source generator, and push into queue

        Args:
            genr (async_generator): Generator that takes an offset and yields splices
            startoffs (int): Offset to start iterating from
            queue (s_queue.Window): Layer queue for splices

        Returns:
            (int), (bool): Next offset to start from and whether splices were exhausted
        '''
        curoffs = startoffs
        fair_iter = self.pull_fair_iter
        offs_logging = self.offs_logging
        q_cap = self.q_cap
        async for splice in genr(startoffs):
            qres = await queue.put((curoffs, splice))
            if not qres:
                return curoffs, False

            curoffs += 1

            if curoffs % fair_iter == 0:
                if curoffs % offs_logging == 0:
                    logger.info(f'Source layer splice pull at offset {curoffs}')
                await asyncio.sleep(0)

            # if we are approaching the queue lim return so we can pause
            if len(queue.linklist) > q_cap:
                return curoffs, False

        return curoffs, True

    async def _trnNodeSplicesToNodeedit(self, ndef, splices):
        '''
        Translate a batch of splices for a given node into a nodeedit set

        Args:
            ndef (tuple): (<form>, <valu>)
            splices (list): [ (<edit>, {<splice info>}), ...]

        Returns:
            (tuple): (cond, nodeedit, meta)
                cond: None or error dict
                nodeedit: (<buid>, <form>, [edits]) where edits is list of (<type>, <info>)
                meta: nodeedit meta dict
        '''
        buid = s_common.buid(ndef)
        form = ndef[0]
        fval = ndef[1]
        meta = None

        stype_f = await self._destGetStortype(form=form)
        if stype_f is None:
            old_form = self.form_chk.get(form)

            if old_form is None:
                err = {'mesg': f'Unable to determine stortype type for form {form}', 'splices': splices}
                logger.warning(err['mesg'])
            else:
                err = {
                    'mesg': f'Unable to determine stortype type for form {form} from an older modelrev',
                    'splices': splices
                }

                if old_form == 0:
                    err['mesg'] += '; further errors will suppressed from logging'
                    logger.warning(err['mesg'])

                self.form_chk[form] += 1

            return err, None, None

        edits = []

        for splice in splices:
            spedit = splice[0]
            props = splice[1]

            # by definition all of these splices have the same meta (same node and same prov)
            if meta is None:
                meta = {k: v for k, v in props.items() if k in ('time', 'user', 'prov')}

            if spedit == 'node:add':
                edit = s_layer.EDIT_NODE_ADD
                edits.append((edit, (fval, stype_f), ()))

            elif spedit == 'node:del':
                edit = s_layer.EDIT_NODE_DEL
                edits.append((edit, (fval, stype_f), ()))

            elif spedit in ('prop:set', 'prop:del'):
                prop = props.get('prop')
                pval = props.get('valu')

                stype_p = await self._destGetStortype(form=form, prop=prop)
                if stype_p is None:
                    formprop = f'{form}:{prop}'
                    old_prop = self.prop_chk.get(formprop)

                    if old_prop is None:
                        err = {'mesg': f'Unable to determine stortype type for prop {formprop}', 'splices': splices}
                        logger.warning(err['mesg'])
                    else:
                        err = {
                            'mesg': f'Unable to determine stortype type for prop {formprop} from an older modelrev',
                            'splices': splices
                        }

                        if old_prop == 0:
                            err['mesg'] += '; further errors will suppressed from logging'
                            logger.warning(err['mesg'])

                        self.prop_chk[formprop] += 1

                    return err, None, None

                if spedit == 'prop:set':
                    edit = s_layer.EDIT_PROP_SET
                    edits.append((edit, (prop, pval, None, stype_p), ()))

                elif spedit == 'prop:del':
                    edit = s_layer.EDIT_PROP_DEL
                    edits.append((edit, (prop, pval, stype_p), ()))

            elif spedit in ('tag:add', 'tag:del'):
                tag = props.get('tag')
                tval = props.get('valu')
                toldv = props.get('oldv')

                if spedit == 'tag:add':
                    edit = s_layer.EDIT_TAG_SET
                    edits.append((edit, (tag, tval, toldv), ()))

                elif spedit == 'tag:del':
                    edit = s_layer.EDIT_TAG_DEL
                    edits.append((edit, (tag, tval), ()))

            elif spedit in ('tag:prop:set', 'tag:prop:del'):
                tag = props.get('tag')
                prop = props.get('prop')
                tval = props.get('valu')
                tcurv = props.get('curv')

                stype_tp = await self._destGetStortype(tagprop=prop)
                if stype_tp is None:
                    err = {'mesg': f'Unable to determine stortype type for tag prop {tag}:{prop}', 'splice': splice}
                    logger.warning(err)
                    return err, None, None

                if spedit == 'tag:prop:set':
                    edit = s_layer.EDIT_TAGPROP_SET
                    edits.append((edit, (tag, prop, tval, tcurv, stype_tp), ()))

                elif spedit == 'tag:prop:del':
                    edit = s_layer.EDIT_TAGPROP_DEL
                    edits.append((edit, (tag, prop, tval, stype_tp), ()))

            else:
                err = {'mesg': 'Unrecognized splice edit', 'splice': splice}
                logger.warning(err)
                return err, None, None

        return None, (buid, form, edits), meta

    async def _destGetStortype(self, form=None, prop=None, tagprop=None):
        '''
        Get the stortype integer for a given form, form prop, or tag prop.

        Args:
            form (str or None): Form name
            prop (str or None): Prop name (form must be specified in this case)
            tagprop (str or None): Tag prop name

        Returns:
            (int or None): Stortype integer or None if not found
        '''
        if form is not None:
            if prop is None:
                return self.model['forms'].get(form, {}).get('stortype')
            else:
                return self.model['forms'].get(form, {})['props'].get(prop, {}).get('stortype')

        elif tagprop is not None:
            return self.model['tagprops'].get(tagprop, {}).get('stortype')

    async def _destPushLyrNodeedits(self, lyriden):
        '''
        Open a proxy to the given destination layer and initiate the queue reader.
        Intended to be run as a free-running task.

        Args:
            lyriden (str): Layer iden
        '''
        trycnt = 0
        while not self.isfini:
            try:
                trycnt += 1
                prx = await s_telepath.openurl(self._getLayerUrl(self.dest, lyriden))
                trycnt = 0

                logger.info(f'Connected to destination {lyriden}')

                queue = self._queues.get(lyriden)

                self.push_last_start[lyriden] = s_common.now()
                writer = prx.storNodeEditsNoLift
                await self._destIterLyrNodeedits(writer, queue, lyriden)

                logger.warning(f'{lyriden} splice queue reader has stopped')

                if queue.isfini:
                    logger.warning(f'Queue is finid; stopping {lyriden} dest push')
                    return

            except asyncio.CancelledError:  # pragma: no cover
                raise
            except (ConnectionError, s_exc.IsFini):
                logger.exception(f'Destination layer connection error cnt={trycnt}: {lyriden}')
                await asyncio.sleep(2 ** trycnt)

                # If migrmode valu is not overridden or overridden to True, attempt to re-enable
                if self.migrmode.valu is None or self.migrmode.valu:
                    await self.enableMigrationMode()

    async def _destIterLyrNodeedits(self, writer, queue, lyriden):
        '''
        Batch available source splices in a queue as nodeedits and push to the destination layer proxy.
        Nodeedit boundaries are defined by the ndef and prov iden.
        Will run as long as queue is not fini'd.

        Args:
            writer (function): Async function that takes (nodeedits, meta) as input
            queue (s_queue.Window): Layer queue for splices
            lyriden (str): Layer iden
        '''
        fair_iter = self.push_fair_iter
        offs_logging = self.offs_logging
        err_lim = self.err_lim
        evnt = self._push_evnts[lyriden]

        ndef = None
        prov = None
        nodesplices = []
        nodespliceoffs = []

        cnt = 0
        errs = 0
        async for offs, splice in queue:
            evnt.clear()
            queuelen = len(queue.linklist)
            next_ndef = splice[1]['ndef']
            next_prov = splice[1].get('prov')

            # current splice is a new node or has new prov iden or the queue is empty
            # so create prior node nodeedit and push to destination layer
            if ndef is not None and (next_ndef != ndef or (prov is not None and next_prov != prov) or queuelen == 0):
                err, ne, meta = None, None, None

                try:
                    err, ne, meta = await self._trnNodeSplicesToNodeedit(ndef, nodesplices)
                    if err is None:
                        await writer([ne], meta)
                        self.push_offs.set(lyriden, offs + 1)

                except asyncio.CancelledError:  # pragma: no cover
                    raise
                except (ConnectionError, s_exc.IsFini):
                    # put back last and nodesplices
                    queue.linklist.appendleft((offs, splice))
                    qadd = zip(reversed(nodespliceoffs), reversed(nodesplices))
                    queue.linklist.extendleft(qadd)
                    raise
                except Exception as e:
                    err = {'mesg': s_common.excinfo(e), 'splices': nodesplices, 'nodeedits': ne, 'meta': meta}
                    logger.exception(err['mesg'])

                if err is not None:
                    errs += 1
                    await self._setLyrErr(lyriden, offs, err)
                    if err_lim != -1 and errs >= err_lim:
                        logger.error(f'Error limit reached')
                        raise SyncErrLimReached(mesg='Error limit reached - correct or increase err_lim to continue')

                nodesplices = []
                nodespliceoffs = []

            ndef = next_ndef
            prov = next_prov
            nodesplices.append(splice)
            nodespliceoffs.append(offs)

            cnt += 1

            if queuelen != 0 and queuelen % 10000 == 0:  # pragma: no cover
                logger.debug(f'{lyriden} queue reader status: read={cnt}, errs={errs}, size={queuelen}')

            if offs % offs_logging == 0 and offs != 0:  # pragma: no cover
                logger.info(f'Destination layer splice push at offset {offs} with {errs} errors')

            if queuelen == 0:
                evnt.set()
                await asyncio.sleep(0)

            elif cnt % fair_iter == 0:
                await asyncio.sleep(0)

if __name__ == '__main__':  # pragma: no cover
    asyncio.run(SyncMigrator.execmain(sys.argv[1:]))

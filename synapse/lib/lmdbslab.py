import os
import shutil
import asyncio
import threading
import collections

import logging
logger = logging.getLogger(__name__)

import lmdb

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.cache as s_cache
import synapse.lib.const as s_const
import synapse.lib.nexus as s_nexus
import synapse.lib.msgpack as s_msgpack
import synapse.lib.thishost as s_thishost
import synapse.lib.thisplat as s_thisplat
import synapse.lib.slabseqn as s_slabseqn

COPY_CHUNKSIZE = 512
PROGRESS_PERIOD = COPY_CHUNKSIZE * 1024

# By default, double the map size each time we run out of space, until this amount, and then we only increase by that
MAX_DOUBLE_SIZE = 100 * s_const.gibibyte

int64min = s_common.int64en(0)
int64max = s_common.int64en(0xffffffffffffffff)

class Hist:
    '''
    A class for storing items in a slab by time.

    Each added item is inserted into the specified db within
    the slab using the current epoch-millis time stamp as the key.
    '''

    def __init__(self, slab, name):
        self.slab = slab
        self.db = slab.initdb(name, dupsort=True)

    def add(self, item, tick=None):
        if tick is None:
            tick = s_common.now()
        lkey = tick.to_bytes(8, 'big')
        self.slab.put(lkey, s_msgpack.en(item), dupdata=True, db=self.db)

    def carve(self, tick, tock=None):

        lmax = None
        lmin = tick.to_bytes(8, 'big')
        if tock is not None:
            lmax = tock.to_bytes(8, 'big')

        for lkey, byts in self.slab.scanByRange(lmin, lmax=lmax, db=self.db):
            tick = int.from_bytes(lkey, 'big')
            yield tick, s_msgpack.un(byts)

class SlabDict:
    '''
    A dictionary-like object which stores its props in a slab via a prefix.

    It is assumed that only one SlabDict with a given prefix exists at any given
    time, but it is up to the caller to cache them.
    '''
    def __init__(self, slab, db=None, pref=b''):
        self.db = db
        self.slab = slab
        self.pref = pref
        self.info = self._getPrefProps(pref)

    def _getPrefProps(self, bidn):

        size = len(bidn)

        props = {}
        for lkey, lval in self.slab.scanByPref(bidn, db=self.db):
            name = lkey[size:].decode('utf8')
            props[name] = s_msgpack.un(lval)

        return props

    def keys(self):
        return self.info.keys()

    def items(self):
        '''
        Return a tuple of (prop, valu) tuples from the SlabDict.

        Returns:
            (((str, object), ...)): Tuple of (name, valu) tuples.
        '''
        return tuple(self.info.items())

    def get(self, name, defval=None):
        '''
        Get a name from the SlabDict.

        Args:
            name (str): The key name.
            defval (obj): The default value to return.

        Returns:
            (obj): The return value, or None.
        '''
        return self.info.get(name, defval)

    def set(self, name, valu):
        '''
        Set a name in the SlabDict.

        Args:
            name (str): The key name.
            valu (obj): A msgpack compatible value.

        Returns:
            None
        '''
        byts = s_msgpack.en(valu)
        lkey = self.pref + name.encode('utf8')
        self.slab.put(lkey, byts, db=self.db)
        self.info[name] = valu
        return valu

    def pop(self, name, defval=None):
        '''
        Pop a name from the SlabDict.

        Args:
            name (str): The name to remove.
            defval (obj): The default value to return if the name is not present.

        Returns:
            object: The object stored in the SlabDict, or defval if the object was not present.
        '''
        valu = self.info.pop(name, defval)
        lkey = self.pref + name.encode('utf8')
        self.slab.pop(lkey, db=self.db)
        return valu

    def inc(self, name, valu=1):
        curv = self.info.get(name, 0)
        curv += valu
        self.set(name, curv)
        return curv

class SlabAbrv:
    '''
    A utility for translating arbitrary bytes into fixed with id bytes
    '''

    def __init__(self, slab, name):

        self.slab = slab
        self.name2abrv = slab.initdb(f'{name}:byts2abrv')
        self.abrv2name = slab.initdb(f'{name}:abrv2byts')

        self.offs = 0

        item = self.slab.last(db=self.abrv2name)
        if item is not None:
            self.offs = s_common.int64un(item[0]) + 1

    @s_cache.memoizemethod()
    def abrvToByts(self, abrv):
        byts = self.slab.get(abrv, db=self.abrv2name)
        if byts is None:
            raise s_exc.NoSuchAbrv

        return byts

    @s_cache.memoizemethod()
    def bytsToAbrv(self, byts):
        abrv = self.slab.get(byts, db=self.name2abrv)
        if abrv is None:
            raise s_exc.NoSuchAbrv

        return abrv

    def setBytsToAbrv(self, byts):
        try:
            return self.bytsToAbrv(byts)
        except s_exc.NoSuchAbrv:
            pass

        abrv = s_common.int64en(self.offs)

        self.offs += 1

        self.slab.put(byts, abrv, db=self.name2abrv)
        self.slab.put(abrv, byts, db=self.abrv2name)

        return abrv

    def names(self):
        for byts in self.slab.scanKeys(db=self.name2abrv):
            yield byts.decode()

    def keys(self):
        for byts in self.slab.scanKeys(db=self.name2abrv):
            yield byts

    def nameToAbrv(self, name):
        return self.bytsToAbrv(name.encode())

    def abrvToName(self, byts):
        return self.abrvToByts(byts).decode()

class HotKeyVal(s_base.Base):
    '''
    A hot-loop capable keyval that only syncs on commit.
    '''
    EncFunc = staticmethod(s_msgpack.en)
    DecFunc = staticmethod(s_msgpack.un)

    async def __anit__(self, slab, name):
        await s_base.Base.__anit__(self)

        self.slab = slab
        self.cache = collections.defaultdict(int)
        self.dirty = set()
        self.db = self.slab.initdb(name)

        for lkey, lval in self.slab.scanByFull(db=self.db):
            self.cache[lkey] = self.DecFunc(lval)

        slab.on('commit', self._onSlabCommit)

        self.onfini(self.sync)

    async def _onSlabCommit(self, mesg):
        if self.dirty:
            self.sync()

    def get(self, name: str, defv=None):
        return self.cache.get(name.encode(), defv)

    def set(self, name: str, valu):
        byts = name.encode()
        self.cache[byts] = valu
        self.dirty.add(byts)
        self.slab.dirty = True
        return valu

    def delete(self, name: str):
        byts = name.encode()
        self.cache.pop(byts, None)
        self.dirty.discard(byts)
        self.slab.delete(byts, db=self.db)

    def sync(self):
        tups = [(p, self.EncFunc(self.cache[p])) for p in self.dirty]
        if not tups:
            return

        self.slab.putmulti(tups, db=self.db)
        self.dirty.clear()

    def pack(self):
        return {n.decode(): v for (n, v) in self.cache.items()}

class HotCount(HotKeyVal):
    '''
    Like HotKeyVal, but optimized for integer/count vals
    '''
    EncFunc = staticmethod(s_common.signedint64en)
    DecFunc = staticmethod(s_common.signedint64un)

    def inc(self, name: str, valu=1):
        byts = name.encode()
        self.cache[byts] += valu
        self.dirty.add(byts)

    def set(self, name: str, valu):
        byts = name.encode()
        self.cache[byts] = valu
        self.dirty.add(byts)
        self.slab.dirty = True

    def get(self, name: str, defv=0):
        return self.cache.get(name.encode(), defv)

class MultiQueue(s_base.Base):
    '''
    Allows creation/consumption of multiple durable queues in a slab.
    '''
    async def __anit__(self, slab, name, nexsroot: s_nexus.NexsRoot = None, auth=None):  # type: ignore

        await s_base.Base.__anit__(self)

        self.slab = slab
        self.auth = auth

        self.abrv = slab.getNameAbrv(f'{name}:abrv')
        self.qdata = self.slab.initdb(f'{name}:qdata')

        self.sizes = SlabDict(self.slab, db=self.slab.initdb(f'{name}:sizes'))
        self.queues = SlabDict(self.slab, db=self.slab.initdb(f'{name}:meta'))
        self.offsets = SlabDict(self.slab, db=self.slab.initdb(f'{name}:offs'))
        self.lastreqid = await HotKeyVal.anit(self.slab, 'reqid')
        self.onfini(self.lastreqid)

        self.waiters = collections.defaultdict(asyncio.Event)  # type: ignore

    def list(self):
        return [self.status(n) for n in self.queues.keys()]

    def status(self, name):

        meta = self.queues.get(name)
        if meta is None:
            mesg = f'No queue named {name}'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        return {
            'name': name,
            'meta': meta,
            'size': self.sizes.get(name),
            'offs': self.offsets.get(name),
        }

    def exists(self, name):
        return self.queues.get(name) is not None

    def size(self, name):
        return self.sizes.get(name)

    def offset(self, name):
        return self.offsets.get(name)

    async def add(self, name, info):

        if self.queues.get(name) is not None:
            mesg = f'A queue already exists with the name {name}.'
            raise s_exc.DupName(mesg=mesg, name=name)

        self.abrv.setBytsToAbrv(name.encode())

        self.queues.set(name, info)
        self.sizes.set(name, 0)
        self.offsets.set(name, 0)

    async def rem(self, name):

        if self.queues.get(name) is None:
            mesg = f'No queue named {name}.'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        await self.cull(name, 0xffffffffffffffff)

        self.queues.pop(name)
        self.offsets.pop(name)

        evnt = self.waiters.pop(name, None)
        if evnt is not None:
            evnt.set()

    async def get(self, name, offs, wait=False, cull=True):
        '''
        Return (nextoffs, item) tuple or (-1, None) for the given offset.
        '''
        async for itemoffs, item in self.gets(name, offs, wait=wait, cull=cull):
            return itemoffs, item
        return -1, None

    async def pop(self, name, offs):
        '''
        Pop a single entry from the named queue by offset.
        '''
        abrv = self.abrv.nameToAbrv(name)
        byts = self.slab.pop(abrv + s_common.int64en(offs), db=self.qdata)
        if byts is not None:
            self.sizes.set(name, self.sizes.get(name) - 1)
            return (offs, s_msgpack.un(byts))

    async def put(self, name, item, reqid=None):
        return await self.puts(name, (item,), reqid=reqid)

    async def puts(self, name, items, reqid=None):

        if self.queues.get(name) is None:
            mesg = f'No queue named {name}.'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        abrv = self.abrv.nameToAbrv(name)

        offs = retn = self.offsets.get(name, 0)

        if reqid is not None:
            if reqid == self.lastreqid.get(name):
                return retn

        self.lastreqid.set(name, reqid)

        for item in items:

            putv = self.slab.put(abrv + s_common.int64en(offs), s_msgpack.en(item), db=self.qdata)
            assert putv, 'Put failed'

            self.sizes.inc(name, 1)
            offs = self.offsets.inc(name, 1)

        # wake the sleepers
        evnt = self.waiters.get(name)
        if evnt is not None:
            evnt.set()

        return retn

    async def gets(self, name, offs, size=None, cull=False, wait=False):
        '''
        Yield (offs, item) tuples from the message queue.
        '''

        if self.queues.get(name) is None:
            mesg = f'No queue named {name}.'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        if cull and offs > 0:
            await self.cull(name, offs - 1)

        abrv = self.abrv.nameToAbrv(name)

        count = 0

        while not self.slab.isfini:

            indx = s_common.int64en(offs)

            for lkey, lval in self.slab.scanByRange(abrv + indx, abrv + int64max, db=self.qdata):

                offs = s_common.int64un(lkey[8:])

                yield offs, s_msgpack.un(lval)

                offs += 1   # in case of wait, we're at next offset
                count += 1

                if size is not None and count >= size:
                    return

            if not wait:
                return

            evnt = self.waiters[name]
            evnt.clear()

            await evnt.wait()

    async def cull(self, name, offs):
        '''
        Remove up-to (and including) the queue entry at offs.
        '''
        if self.queues.get(name) is None:
            mesg = f'No queue named {name}.'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        if offs < 0:
            return

        indx = s_common.int64en(offs)

        abrv = self.abrv.nameToAbrv(name)

        for lkey, _ in self.slab.scanByRange(abrv + int64min, abrv + indx, db=self.qdata):
            self.slab.delete(lkey, db=self.qdata)
            self.sizes.set(name, self.sizes.get(name) - 1)
            await asyncio.sleep(0)

    async def dele(self, name, minoffs, maxoffs):
        '''
        Remove queue entries from minoffs, up-to (and including) the queue entry at maxoffs.
        '''
        if self.queues.get(name) is None:
            mesg = f'No queue named {name}.'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        if minoffs < 0 or maxoffs < 0 or maxoffs < minoffs:
            return

        minindx = s_common.int64en(minoffs)
        maxindx = s_common.int64en(maxoffs)

        abrv = self.abrv.nameToAbrv(name)

        for lkey, _ in self.slab.scanByRange(abrv + minindx, abrv + maxindx, db=self.qdata):
            self.slab.delete(lkey, db=self.qdata)
            self.sizes.set(name, self.sizes.get(name) - 1)
            await asyncio.sleep(0)

    async def sets(self, name, offs, items):
        '''
        Overwrite queue entries with the values in items, starting at offs.
        '''
        if self.queues.get(name) is None:
            mesg = f'No queue named {name}.'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        if offs < 0:
            return

        abrv = self.abrv.nameToAbrv(name)
        wake = False

        for item in items:
            indx = s_common.int64en(offs)

            if offs >= self.offsets.get(name, 0):
                self.slab.put(abrv + indx, s_msgpack.en(item), db=self.qdata)
                offs = self.offsets.set(name, offs + 1)
                self.sizes.inc(name, 1)
                wake = True
            else:
                byts = self.slab.get(abrv + indx, db=self.qdata)
                self.slab.put(abrv + indx, s_msgpack.en(item), db=self.qdata)

                if byts is None:
                    self.sizes.inc(name, 1)

                offs += 1

            await asyncio.sleep(0)

        if wake:
            evnt = self.waiters.get(name)
            if evnt is not None:
                evnt.set()

class GuidStor:

    def __init__(self, slab, name):

        self.slab = slab
        self.name = name

        self.db = self.slab.initdb(name)

    def gen(self, iden):
        bidn = s_common.uhex(iden)
        return SlabDict(self.slab, db=self.db, pref=bidn)

    async def del_(self, iden):
        bidn = s_common.uhex(iden)
        for lkey, lval in self.slab.scanByPref(bidn, db=self.db):
            self.slab.pop(lkey, db=self.db)
            await asyncio.sleep(0)

    def set(self, iden, name, valu):
        bidn = s_common.uhex(iden)
        byts = s_msgpack.en(valu)
        self.slab.put(bidn + name.encode(), byts, db=self.db)

    async def dict(self, iden):
        bidn = s_common.uhex(iden)

        retn = {}
        for lkey, lval in self.slab.scanByPref(bidn, db=self.db):
            await asyncio.sleep(0)
            name = lkey[len(bidn):].decode()
            retn[name] = s_msgpack.un(lval)
        return retn

def _florpo2(i):
    '''
    Return largest power of 2 equal to or less than i
    '''
    if not (i & (i - 1)):
        return i

    return 1 << (i.bit_length() - 1)

def _ceilpo2(i):
    '''
    Return smallest power of 2 equal to or greater than i
    '''
    if not (i & (i - 1)):
        return i

    return 1 << i.bit_length()

def _roundup(i, multiple):
    return ((i + multiple - 1) // multiple) * multiple

def _mapsizeround(size):
    cutoff = _florpo2(MAX_DOUBLE_SIZE)

    if size < cutoff:
        return _ceilpo2(size)

    if size == cutoff:  # We're already the largest power of 2
        return size

    return _roundup(size, MAX_DOUBLE_SIZE)

class Slab(s_base.Base):
    '''
    A "monolithic" LMDB instance for use in a asyncio loop thread.
    '''
    # The paths of all open slabs, to prevent accidental opening of the same slab in two places
    allslabs = {}  # type: ignore
    synctask = None
    syncevnt = None  # set this event to trigger a sync

    # time between commits
    COMMIT_PERIOD = float(os.environ.get('SYN_SLAB_COMMIT_PERIOD', '0.2'))

    # warn if commit takes too long
    WARN_COMMIT_TIME_MS = int(float(os.environ.get('SYN_SLAB_COMMIT_WARN', '1.0')) * 1000)

    DEFAULT_MAPSIZE = s_const.gibibyte
    DEFAULT_GROWSIZE = None

    @classmethod
    def getSlabsInDir(clas, dirn):
        '''
        Returns all open slabs under a directory
        '''
        toppath = s_common.genpath(dirn)
        return [slab for slab in clas.allslabs.values()
                if toppath == slab.path or slab.path.startswith(toppath + os.sep)]

    @classmethod
    async def initSyncLoop(clas, inst):

        if clas.synctask is not None:
            return

        clas.syncevnt = asyncio.Event()

        coro = clas.syncLoopTask()
        loop = asyncio.get_running_loop()

        clas.synctask = loop.create_task(coro)

    @classmethod
    async def syncLoopTask(clas):
        while True:
            try:
                await s_coro.event_wait(clas.syncevnt, timeout=clas.COMMIT_PERIOD)

                clas.syncevnt.clear()

                await clas.syncLoopOnce()

            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise

            except Exception:  # pragma: no cover
                logger.exception('Slab.syncLoopTask')

    @classmethod
    async def syncLoopOnce(clas):
        for slab in list(clas.allslabs.values()):
            if slab.dirty:
                await slab.sync()
                await asyncio.sleep(0)

    @classmethod
    async def getSlabStats(clas):
        retn = []
        for slab in clas.allslabs.values():
            retn.append({
                'path': str(slab.path),
                'xactops': len(slab.xactops),
                'mapsize': slab.mapsize,
                'readonly': slab.readonly,
                'lockmemory': slab.lockmemory,
                'recovering': slab.recovering,
                'maxsize': slab.maxsize,
                'growsize': slab.growsize,
                'mapasync': slab.mapasync,

            })
        return retn

    async def __anit__(self, path, **kwargs):

        await s_base.Base.__anit__(self)

        kwargs.setdefault('map_size', self.DEFAULT_MAPSIZE)
        kwargs.setdefault('lockmemory', False)
        kwargs.setdefault('map_async', True)

        opts = kwargs

        self.path = path
        self.optspath = s_common.switchext(path, ext='.opts.yaml')

        # Make sure we don't have this lmdb DB open already.  (This can lead to seg faults)
        if path in self.allslabs:
            raise s_exc.SlabAlreadyOpen(mesg=path)

        if os.path.isfile(self.optspath):
            _opts = s_common.yamlload(self.optspath)
            if isinstance(_opts, dict):
                opts.update(_opts)

        initial_mapsize = opts.get('map_size')
        if initial_mapsize is None:
            raise s_exc.BadArg('Slab requires map_size')

        mdbpath = s_common.genpath(path, 'data.mdb')
        if os.path.isfile(mdbpath):
            mapsize = max(initial_mapsize, os.path.getsize(mdbpath))
        else:
            mapsize = initial_mapsize

        # save the transaction deltas in case of error...
        self.xactops = []
        self.max_xactops_len = opts.pop('max_replay_log', 10000)
        self.recovering = False

        opts.setdefault('max_dbs', 128)
        opts.setdefault('writemap', True)

        self.maxsize = opts.pop('maxsize', None)
        self.growsize = opts.pop('growsize', self.DEFAULT_GROWSIZE)

        self.readonly = opts.get('readonly', False)
        self.lockmemory = opts.pop('lockmemory', False)

        if self.lockmemory:
            lockmem_override = s_common.envbool('SYN_LOCKMEM_DISABLE')
            if lockmem_override:
                logger.info(f'SYN_LOCKMEM_DISABLE envar set, skipping lockmem for {self.path}')
                self.lockmemory = False

        self.mapasync = opts.setdefault('map_async', True)

        self.mapsize = _mapsizeround(mapsize)
        if self.maxsize is not None:
            self.mapsize = min(self.mapsize, self.maxsize)

        self._saveOptsFile()

        try:
            self.lenv = lmdb.open(str(path), **opts)
        except lmdb.LockError as e:  # pragma: no cover
            # This is difficult to test since it requires two processes to open the slab with
            # the same pid. In practice this typically occurs when there are two docker
            # containers running from different process namespaces, whose process pids are
            # the same, opening the same lmdb database. That isn't a supported configuration
            # and we just need to catch that error.
            mesg = f'Unable to obtain lock on {path}. Another process may have this file locked. {e}'
            raise s_exc.LmdbLock(mesg=mesg, path=path) from None

        self.allslabs[path] = self

        self.scans = set()

        self.dirty = False
        if self.readonly:
            self.xact = None
            self.txnrefcount = 0
        else:
            self._initCoXact()

        self.resizeevent = threading.Event()  # triggered when a resize event occurred
        self.lockdoneevent = asyncio.Event()  # triggered when a memory locking finished

        # LMDB layer uses these for status reporting
        self.locking_memory = False
        self.prefaulting = False
        self.memlocktask = None
        self.max_could_lock = 0
        self.lock_progress = 0
        self.lock_goal = 0

        if self.lockmemory:
            async def memlockfini():
                self.resizeevent.set()
                await self.memlocktask
            self.memlocktask = s_coro.executor(self._memorylockloop)
            self.onfini(memlockfini)
        else:
            self.lockdoneevent.set()

        self.dbnames = {None: (None, False)}  # prepopulate the default DB for speed

        self.onfini(self._onSlabFini)

        self.commitstats = collections.deque(maxlen=1000)  # stores Tuple[time, replayloglen, commit time delta]

        if not self.readonly:
            await Slab.initSyncLoop(self)

    def __repr__(self):
        return 'Slab: %r' % (self.path,)

    async def trash(self):
        '''
        Deletes underlying storage
        '''
        await self.fini()

        try:
            os.unlink(self.optspath)
        except FileNotFoundError:  # pragma: no cover
            pass

        shutil.rmtree(self.path, ignore_errors=True)

    async def getHotCount(self, name):
        item = await HotCount.anit(self, name)
        self.onfini(item)
        return item

    def getSeqn(self, name):
        return s_slabseqn.SlabSeqn(self, name)

    def getNameAbrv(self, name):
        return SlabAbrv(self, name)

    async def getMultiQueue(self, name, nexsroot=None):
        mq = await MultiQueue.anit(self, name, nexsroot=None)
        self.onfini(mq)
        return mq

    def statinfo(self):
        return {
            'locking_memory': self.locking_memory,  # whether the memory lock loop was started and hasn't ended
            'max_could_lock': self.max_could_lock,  # the maximum this system could lock
            'lock_progress': self.lock_progress,  # how much we've locked so far
            'lock_goal': self.lock_goal,  # how much we want to lock
            'prefaulting': self.prefaulting,  # whether we are right meow prefaulting
            'commitstats': list(self.commitstats),  # last X tuple(time,replaylogsize,commit time)
        }

    def _acqXactForReading(self):
        if self.isfini:  # pragma: no cover
            raise s_exc.IsFini()
        if not self.readonly:
            return self.xact
        if not self.txnrefcount:
            self._initCoXact()

        self.txnrefcount += 1
        return self.xact

    def _relXactForReading(self):
        if not self.readonly:
            return
        self.txnrefcount -= 1
        if not self.txnrefcount:
            self._finiCoXact()

    def _saveOptsFile(self):
        if self.readonly:
            return

        opts = {}
        if self.growsize is not None:
            opts['growsize'] = self.growsize
        if self.maxsize is not None:
            opts['maxsize'] = self.maxsize
        s_common.yamlmod(opts, self.optspath)

    async def sync(self):
        try:
            # do this from the loop thread only to avoid recursion
            await self.fire('commit')
            self.forcecommit()

        except lmdb.MapFullError:
            self._handle_mapfull()
            # There's no need to re-try self.forcecommit as _growMapSize does it

    async def fini(self):
        await self.fire('commit')
        return await s_base.Base.fini(self)

    async def _onSlabFini(self):
        assert s_glob.iAmLoop()

        while True:
            try:
                self._finiCoXact()
            except lmdb.MapFullError:
                self._handle_mapfull()
                continue
            break

        self.dirty = False
        self.lenv.close()
        self.allslabs.pop(self.path, None)
        del self.lenv

        if not self.allslabs:
            if self.synctask:
                self.synctask.cancel()
            self.__class__.synctask = None
            self.__class__.syncevnt = None

    def _finiCoXact(self):
        '''
        Note:
            This method may raise a MapFullError
        '''

        assert s_glob.iAmLoop()

        [scan.bump() for scan in self.scans]

        # Readonly or self.xact has already been closed
        if self.xact is None:
            return

        self.xact.commit()

        self.xactops.clear()

        del self.xact
        self.xact = None

    def _growMapSize(self, size=None):
        mapsize = self.mapsize

        if size is not None:
            mapsize += size

        elif self.growsize is not None:
            mapsize += self.growsize

        else:
            mapsize = _mapsizeround(mapsize + 1)

        if self.maxsize is not None:
            mapsize = min(mapsize, self.maxsize)
            if mapsize == self.mapsize:
                raise s_exc.DbOutOfSpace(
                    mesg=f'DB at {self.path} is at specified max capacity of {self.maxsize} and is out of space')

        logger.warning('lmdbslab %s growing map size to: %d MiB', self.path, mapsize // s_const.mebibyte)

        self.lenv.set_mapsize(mapsize)
        self.mapsize = mapsize

        self.resizeevent.set()

        return self.mapsize

    def _memorylockloop(self):
        '''
        Separate thread loop that manages the prefaulting and locking of the memory backing the data file
        '''
        if not s_thishost.get('hasmemlocking'):  # pragma: no cover
            return
        MAX_TOTAL_PERCENT = .90  # how much of all the RAM to take
        MAX_LOCK_AT_ONCE = s_const.gibibyte

        # Calculate a reasonable maximum amount of memory to lock

        s_thisplat.maximizeMaxLockedMemory()
        locked_ulimit = s_thisplat.getMaxLockedMemory()
        if locked_ulimit < s_const.gibibyte // 2:
            logger.warning(
                'Operating system limit of maximum amount of locked memory (currently %d) is \n'
                'too low for optimal performance.', locked_ulimit)

        logger.debug('memory locking thread started')

        # Note:  available might be larger than max_total in a container
        max_total = s_thisplat.getTotalMemory()
        available = s_thisplat.getAvailableMemory()

        PAGESIZE = 4096
        max_to_lock = (min(locked_ulimit,
                           int(max_total * MAX_TOTAL_PERCENT),
                           int(available * MAX_TOTAL_PERCENT)) // PAGESIZE) * PAGESIZE

        self.max_could_lock = max_to_lock

        path = s_common.genpath(self.path, 'data.mdb')  # Path to the file that gets mapped
        fh = open(path, 'r+b')
        fileno = fh.fileno()

        prev_memend = 0  # The last end of the file mapping, so we can start from there

        # Avoid spamming messages
        first_end = True
        limit_warned = False
        self.locking_memory = True

        self.resizeevent.set()

        while not self.isfini:

            self.resizeevent.wait()
            if self.isfini:
                break

            self.schedCallSafe(self.lockdoneevent.clear)
            self.resizeevent.clear()

            try:
                memstart, memlen = s_thisplat.getFileMappedRegion(path)
            except s_exc.NoSuchFile:  # pragma: no cover
                logger.warning('map not found for %s', path)

                if not self.resizeevent.is_set():
                    self.schedCallSafe(self.lockdoneevent.set)
                continue

            if memlen > max_to_lock:
                memlen = max_to_lock
                if not limit_warned:
                    logger.warning('memory locking limit reached')
                    limit_warned = True
                # Even in the event that we've hit our limit we still have to loop because further mmaps may cause
                # the base address to change, necessitating relocking what we can

            # The file might be a little bit smaller than the map because rounding (and mmap fails if you give it a
            # too-long length)
            filesize = os.fstat(fileno).st_size
            goal_end = memstart + min(memlen, filesize)
            self.lock_goal = goal_end - memstart

            self.lock_progress = 0
            prev_memend = memstart

            # Actually do the prefaulting and locking.  Only do it a chunk at a time to maintain responsiveness.
            while prev_memend < goal_end:
                new_memend = min(prev_memend + MAX_LOCK_AT_ONCE, goal_end)
                memlen = new_memend - prev_memend
                PROT = 1  # PROT_READ
                FLAGS = 0x8001  # MAP_POPULATE | MAP_SHARED (Linux only)  (for fast prefaulting)
                try:
                    self.prefaulting = True
                    with s_thisplat.mmap(0, length=new_memend - prev_memend, prot=PROT, flags=FLAGS, fd=fileno,
                                         offset=prev_memend - memstart):
                        s_thisplat.mlock(prev_memend, memlen)
                except OSError as e:
                    logger.warning('error while attempting to lock memory of %s: %s', path, e)
                    break
                finally:
                    self.prefaulting = False

                prev_memend = new_memend
                self.lock_progress = prev_memend - memstart

            if first_end:
                first_end = False
                logger.info('completed prefaulting and locking slab')

            if not self.resizeevent.is_set():
                self.schedCallSafe(self.lockdoneevent.set)

        self.locking_memory = False
        logger.debug('memory locking thread ended')

    def initdb(self, name, dupsort=False, integerkey=False, dupfixed=False):

        if name in self.dbnames:
            return name

        while True:
            try:
                if self.readonly:
                    # In a readonly environment, we can't make our own write transaction, but we
                    # can have the lmdb module create one for us by not specifying the transaction
                    db = self.lenv.open_db(name.encode('utf8'), create=False, dupsort=dupsort, integerkey=integerkey,
                                           dupfixed=dupfixed)
                else:
                    db = self.lenv.open_db(name.encode('utf8'), txn=self.xact, dupsort=dupsort, integerkey=integerkey,
                                           dupfixed=dupfixed)
                    self.dirty = True
                    self.forcecommit()

                self.dbnames[name] = (db, dupsort)
                return name
            except lmdb.MapFullError:
                self._handle_mapfull()
            except lmdb.MapResizedError:
                # This can only happen if readonly and another process added data (e.g. cortex spawn)
                # _initCoXact knows the magic to resolve this
                self._initCoXact()

    def dropdb(self, name):
        '''
        Deletes an **entire database** (i.e. a table), losing all data.
        '''
        if self.readonly:
            raise s_exc.IsReadOnly()

        while True:
            try:
                if not self.dbexists(name):
                    return

                self.initdb(name)
                db, dupsort = self.dbnames.pop(name)

                self.dirty = True
                self.xact.drop(db, delete=True)
                self.forcecommit()
                return

            except lmdb.MapFullError:
                self._handle_mapfull()

    def dbexists(self, name):
        '''
        The DB exists already if there's a key in the default DB with the name of the database
        '''
        valu = self.get(name.encode())
        return valu is not None

    def get(self, lkey, db=None):
        self._acqXactForReading()
        realdb, dupsort = self.dbnames[db]
        try:
            return self.xact.get(lkey, db=realdb)
        finally:
            self._relXactForReading()

    def last(self, db=None):
        '''
        Return the last key/value pair from the given db.
        '''
        self._acqXactForReading()
        realdb, dupsort = self.dbnames[db]
        try:
            with self.xact.cursor(db=realdb) as curs:
                if not curs.last():
                    return None
                return curs.key(), curs.value()
        finally:
            self._relXactForReading()

    def lastkey(self, db=None):
        '''
        Return the last key or None from the given db.
        '''
        self._acqXactForReading()
        realdb, _ = self.dbnames[db]
        try:
            with self.xact.cursor(db=realdb) as curs:
                if not curs.last():
                    return None
                return curs.key()
        finally:
            self._relXactForReading()

    def firstkey(self, db=None):
        '''
        Return the first key or None from the given db.
        '''
        self._acqXactForReading()
        realdb, _ = self.dbnames[db]
        try:
            with self.xact.cursor(db=realdb) as curs:
                if not curs.first():
                    return None
                return curs.key()
        finally:
            self._relXactForReading()

    def has(self, lkey, db=None):
        realdb, dupsort = self.dbnames[db]
        with self.xact.cursor(db=realdb) as curs:
            return curs.set_key(lkey)

    def hasdup(self, lkey, lval, db=None):
        realdb, dupsort = self.dbnames[db]
        with self.xact.cursor(db=realdb) as curs:
            return curs.set_key_dup(lkey, lval)

    def prefexists(self, byts, db=None):
        '''
        Returns True if a prefix exists in the db.
        '''
        realdb, _ = self.dbnames[db]
        with self.xact.cursor(db=realdb) as curs:
            if not curs.set_range(byts):
                return False

            lkey = curs.key()

            if lkey[:len(byts)] == byts:
                return True

            return False

    def rangeexists(self, lmin, lmax=None, db=None):
        '''
        Returns True if at least one key exists in the range.
        '''
        realdb, _ = self.dbnames[db]
        with self.xact.cursor(db=realdb) as curs:
            if not curs.set_range(lmin):
                return False

            lkey = curs.key()

            if lkey[:len(lmin)] >= lmin and (lmax is None or lkey[:len(lmax)] <= lmax):
                return True

            return False

    def stat(self, db=None):
        self._acqXactForReading()
        realdb, dupsort = self.dbnames[db]
        try:
            return self.xact.stat(db=realdb)
        finally:
            self._relXactForReading()

    def scanKeys(self, db=None):

        with ScanKeys(self, db) as scan:

            if not scan.first():
                return

            yield from scan.iternext()

    def scanKeysByPref(self, byts, db=None):

        with ScanKeys(self, db) as scan:

            if not scan.set_range(byts):
                return

            size = len(byts)
            for lkey in scan.iternext():

                if lkey[:size] != byts:
                    return

                yield lkey

    async def countByPref(self, byts, db=None, maxsize=None):
        '''
        Return the number of rows in the given db with the matching prefix bytes.
        '''
        count = 0
        size = len(byts)
        with ScanKeys(self, db) as scan:

            if not scan.set_range(byts):
                return 0

            for lkey in scan.iternext():

                if lkey[:size] != byts:
                    return count

                count += 1
                if maxsize is not None and maxsize == count:
                    return count

                await asyncio.sleep(0)

            return count

    def scanByDups(self, lkey, db=None):

        with Scan(self, db) as scan:

            if not scan.set_key(lkey):
                return

            for item in scan.iternext():
                if item[0] != lkey:
                    break

                yield item

    def scanByDupsBack(self, lkey, db=None):

        with ScanBack(self, db) as scan:

            if not scan.set_key(lkey):
                return

            for item in scan.iternext():

                if item[0] != lkey:
                    break

                yield item

    def scanByPref(self, byts, startkey=None, startvalu=None, db=None):
        '''
        Args:
            byts(bytes):                 prefix to match on
            startkey(Optional[bytes]):   if present, will start scanning at key=byts+startkey
            startvalu(Optional[bytes]):  if present, will start scanning at (key+startkey, startvalu)

        Notes:
            startvalu only makes sense if byts+startkey matches an entire key.
            startvalu is only value for dupsort=True dbs
        '''
        if startkey is None:
            startkey = b''

        with Scan(self, db) as scan:

            if not scan.set_range(byts + startkey, valu=startvalu):
                return

            size = len(byts)
            for lkey, lval in scan.iternext():

                if lkey[:size] != byts:
                    return

                yield lkey, lval

    def scanByPrefBack(self, byts, db=None):

        with ScanBack(self, db) as scan:

            intoff = int.from_bytes(byts, "big")
            intoff += 1
            try:
                nextbyts = intoff.to_bytes(len(byts), "big")

                if not scan.set_range(nextbyts):
                    return

            except OverflowError:
                if not scan.first():
                    return

            size = len(byts)
            for lkey, lval in scan.iternext():

                if lkey[:size] != byts:
                    return

                yield lkey, lval

    def scanByRange(self, lmin, lmax=None, db=None):

        with Scan(self, db) as scan:

            if not scan.set_range(lmin):
                return

            size = len(lmax) if lmax is not None else None

            for lkey, lval in scan.iternext():

                if lmax is not None and lkey[:size] > lmax:
                    return

                yield lkey, lval

    def scanByRangeBack(self, lmax, lmin=None, db=None):

        with ScanBack(self, db) as scan:

            if not scan.set_range(lmax):
                return

            for lkey, lval in scan.iternext():

                if lmin is not None and lkey < lmin:
                    return

                yield lkey, lval

    def scanByFull(self, db=None):

        with Scan(self, db) as scan:

            if not scan.first():
                return

            yield from scan.iternext()

    def scanByFullBack(self, db=None):

        with ScanBack(self, db) as scan:

            if not scan.first():
                return

            yield from scan.iternext()

    def _initCoXact(self):
        try:
            self.xact = self.lenv.begin(write=not self.readonly)
        except lmdb.MapResizedError:
            # This is what happens when some *other* process increased the mapsize.  setting mapsize to 0 should
            # set my mapsize to whatever the other process raised it to
            self.lenv.set_mapsize(0)
            self.mapsize = self.lenv.info()['map_size']
            self.xact = self.lenv.begin(write=not self.readonly)
        self.dirty = False

    def _logXactOper(self, func, *args, **kwargs):
        self.xactops.append((func, args, kwargs))

        if len(self.xactops) == self.max_xactops_len:
            self.syncevnt.set()

    def _runXactOpers(self):
        # re-run transaction operations in the event of an abort.  Return the last operation's return value.
        retn = None
        for (f, a, k) in self.xactops:
            retn = f(*a, **k)
        return retn

    def _handle_mapfull(self):
        [scan.bump() for scan in self.scans]

        while True:
            try:
                self.xact.abort()

                del self.xact
                self.xact = None  # Note: it is possible for us to be fini'd in _growMapSize

                self._growMapSize()

                self.xact = self.lenv.begin(write=not self.readonly)

                self.recovering = True
                self.last_retn = self._runXactOpers()
                self.recovering = False

                self.forcecommit()

            except lmdb.MapFullError:
                continue

            break

        retn, self.last_retn = self.last_retn, None
        return retn

    def _xact_action(self, calling_func, xact_func, lkey, *args, db=None, **kwargs):
        if self.readonly:
            raise s_exc.IsReadOnly()

        realdb, dupsort = self.dbnames[db]

        try:
            self.dirty = True

            if not self.recovering:
                self._logXactOper(calling_func, lkey, *args, db=db, **kwargs)

            return xact_func(self.xact, lkey, *args, db=realdb, **kwargs)

        except lmdb.MapFullError:
            return self._handle_mapfull()

    def putmulti(self, kvpairs, dupdata=False, append=False, db=None):
        '''
        Returns:
            Tuple of number of items consumed, number of items added
        '''
        if self.readonly:
            raise s_exc.IsReadOnly()

        # Log playback isn't compatible with generators
        if not isinstance(kvpairs, list):
            kvpairs = list(kvpairs)

        realdb, dupsort = self.dbnames[db]

        try:
            self.dirty = True

            if not self.recovering:
                self._logXactOper(self.putmulti, kvpairs, dupdata=dupdata, append=append, db=db)

            with self.xact.cursor(db=realdb) as curs:
                return curs.putmulti(kvpairs, dupdata=dupdata, append=append)

        except lmdb.MapFullError:
            return self._handle_mapfull()

    def copydb(self, sourcedbname, destslab, destdbname=None, progresscb=None):
        '''
        Copy an entire database in this slab to a new database in potentially another slab.

        Args:
            sourcedbname (str): name of the db in the source environment
            destslab (LmdbSlab): which slab to copy rows to
            destdbname (str): the name of the database to copy rows to in destslab
            progresscb (Callable[int]):  if not None, this function will be periodically called with the number of rows
                                         completed

        Returns:
            (int): the number of rows copied

        Note:
            If any rows already exist in the target database, this method returns an error.  This means that one cannot
            use destdbname=None unless there are no explicit databases in the destination slab.
        '''
        sourcedb, dupsort = self.dbnames[sourcedbname]

        destslab.initdb(destdbname, dupsort)
        destdb, _ = destslab.dbnames[destdbname]

        statdict = destslab.stat(db=destdbname)
        if statdict['entries'] > 0:
            raise s_exc.DataAlreadyExists()

        rowcount = 0

        for chunk in s_common.chunks(self.scanByFull(db=sourcedbname), COPY_CHUNKSIZE):
            ccount, acount = destslab.putmulti(chunk, dupdata=True, append=True, db=destdbname)
            if ccount != len(chunk) or acount != len(chunk):
                raise s_exc.BadCoreStore(mesg='Unexpected number of values written')  # pragma: no cover

            rowcount += len(chunk)
            if progresscb is not None and 0 == (rowcount % PROGRESS_PERIOD):
                progresscb(rowcount)

        return rowcount

    async def copyslab(self, dstpath, compact=True):

        dstpath = s_common.genpath(dstpath)
        if os.path.isdir(dstpath):
            raise s_exc.DataAlreadyExists()

        s_common.gendir(dstpath)

        dstoptspath = s_common.switchext(dstpath, ext='.opts.yaml')

        await self.sync()

        self.lenv.copy(str(dstpath), compact=compact)

        try:
            shutil.copy(self.optspath, dstoptspath)
        except FileNotFoundError:  # pragma: no cover
            pass

        return True

    def pop(self, lkey, db=None):
        return self._xact_action(self.pop, lmdb.Transaction.pop, lkey, db=db)

    def delete(self, lkey, val=None, db=None):
        return self._xact_action(self.delete, lmdb.Transaction.delete, lkey, val, db=db)

    def put(self, lkey, lval, dupdata=False, overwrite=True, append=False, db=None):
        return self._xact_action(self.put, lmdb.Transaction.put, lkey, lval, dupdata=dupdata, overwrite=overwrite,
                                 append=append, db=db)

    def replace(self, lkey, lval, db=None):
        '''
        Like put, but returns the previous value if existed
        '''
        return self._xact_action(self.replace, lmdb.Transaction.replace, lkey, lval, db=db)

    def forcecommit(self):
        '''
        Note:
            This method may raise a MapFullError
        '''
        if not self.dirty:
            return False

        xactopslen = len(self.xactops)

        # ok... lets commit and re-open
        starttime = s_common.now()
        self._finiCoXact()
        donetime = s_common.now()

        delta = donetime - starttime

        self.commitstats.append((starttime, xactopslen, delta))

        if self.WARN_COMMIT_TIME_MS and delta > self.WARN_COMMIT_TIME_MS:
            logger.warning(f'Commit with {xactopslen} items in {self!r} took {delta} ms.')
        self._initCoXact()
        return True

class Scan:
    '''
    A state-object used by Slab.  Not to be instantiated directly.

    Args:

        slab (Slab):  which slab the scan is over
        db (str):  name of open database on the slab
    '''
    def __init__(self, slab, db):
        self.slab = slab
        self.db, self.dupsort = slab.dbnames[db]

        self.atitem = None
        self.bumped = False
        self.curs = None

    def __enter__(self):
        self.slab._acqXactForReading()
        self.curs = self.slab.xact.cursor(db=self.db)
        self.slab.scans.add(self)
        return self

    def __exit__(self, exc, cls, tb):
        self.bump()
        self.slab.scans.discard(self)
        self.slab._relXactForReading()
        self.curs = None

    def first(self):

        if not self.curs.first():
            return False

        self.genr = self.iterfunc()
        self.atitem = next(self.genr)

        return True

    def set_key(self, lkey):

        if not self.curs.set_key(lkey):
            return False

        self.genr = self.iterfunc()
        self.atitem = next(self.genr)
        return True

    def set_range(self, lkey, valu=None):

        if valu is None:
            if not self.curs.set_range(lkey):
                return False
        else:
            if not self.curs.set_range_dup(lkey, valu):
                return False

        self.genr = self.iterfunc()
        self.atitem = next(self.genr)

        return True

    def iternext(self):

        try:

            while True:

                yield self.atitem

                if self.bumped:

                    if self.slab.isfini:
                        raise s_exc.IsFini()

                    self.bumped = False

                    self.curs = self.slab.xact.cursor(db=self.db)

                    if not self.resume():
                        raise StopIteration

                    self.genr = self.iterfunc()
                    if self.isatitem():
                        next(self.genr)

                self.atitem = next(self.genr)

        except StopIteration:
            return

    def bump(self):
        if not self.bumped:
            self.curs.close()
            self.bumped = True

    def iterfunc(self):
        return self.curs.iternext()

    def resume(self):
        item = self.atitem

        if not self.dupsort:
            return self.curs.set_range(item[0])

        if self.curs.set_range_dup(*item):
            return True

        if not self.curs.set_range(item[0]):
            return False

        # if the key is the same, we're at a previous
        # entry and need to skip dups to the next key
        if self.curs.key() == item[0]:
            return self.curs.next_nodup()

        return True

    def isatitem(self):
        '''
        Returns if the cursor is at the value in atitem
        '''
        return self.atitem == self.curs.item()

class ScanKeys(Scan):
    '''
    An iterator over the keys of the database.  If the database is dupsort, a key with multiple values with be yielded
    once for each value.
    '''
    def iterfunc(self):
        if self.dupsort:
            return Scan.iterfunc(self)

        return self.curs.iternext(keys=True, values=False)

    def resume(self):
        if self.dupsort:
            return Scan.resume(self)

        return self.curs.set_range(self.atitem)

    def isatitem(self):
        '''
        Returns if the cursor is at the value in atitem
        '''
        if self.dupsort:
            return Scan.isatitem(self)

        return self.atitem == self.curs.key()

    def iternext(self):
        if self.dupsort:
            yield from (item[0] for item in Scan.iternext(self))
            return

        yield from Scan.iternext(self)

class ScanBack(Scan):
    '''
    A state-object used by Slab.  Not to be instantiated directly.

    Scans backwards.
    '''
    def iterfunc(self):
        return self.curs.iterprev()

    def first(self):

        if not self.curs.last():
            return False

        self.genr = self.iterfunc()
        self.atitem = next(self.genr)
        return True

    def set_key(self, lkey):

        if not self.curs.set_key(lkey):
            return False

        if self.dupsort:
            self.curs.last_dup()

        self.genr = self.iterfunc()
        self.atitem = next(self.genr)
        return True

    def set_range(self, lkey):

        if not self.curs.set_range(lkey):
            if not self.curs.last():
                return False

        else:
            if self.curs.key() != lkey:
                if not self.curs.prev():
                    return False

        if self.dupsort:
            self.curs.last_dup()

        self.genr = self.iterfunc()
        self.atitem = next(self.genr)

        return True

    def resume(self):
        item = self.atitem

        if not self.dupsort:

            if self.curs.set_range(item[0]):
                return self.curs.prev()

            if not self.curs.last():
                return False

            return True

        # dupsort resume...

        # see if we get lucky and land on it
        if self.curs.set_range_dup(*item):
            return self.curs.prev()

        # if we fail to set the range, try for the last
        if not self.curs.set_range(item[0]):
            return self.curs.last()

        # if we're on the next key, step back
        if not self.curs.key() == item[0]:
            if not self.curs.prev():
                return False

        self.curs.last_dup()
        return True

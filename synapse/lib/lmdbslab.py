import os
import shutil
import asyncio
import pathlib
import functools
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
import synapse.lib.msgpack as s_msgpack
import synapse.lib.thishost as s_thishost
import synapse.lib.thisplat as s_thisplat

COPY_CHUNKSIZE = 512
PROGRESS_PERIOD = COPY_CHUNKSIZE * 1024

# By default, double the map size each time we run out of space, until this amount, and then we only increase by that
MAX_DOUBLE_SIZE = 100 * s_const.gibibyte

int64min = s_common.int64en(0)
int64max = s_common.int64en(0xffffffffffffffff)

class LmdbDatabase():
    def __init__(self, db, dupsort):
        self.db = db
        self.dupsort = dupsort

_DefaultDB = LmdbDatabase(None, False)

class Hist:
    '''
    A class for storing items in a slab by time.

    Each added item is inserted into the specified db within
    the slab using the current epoch-millis time stamp as the key.
    '''

    def __init__(self, slab, name):
        self.slab = slab
        self.db = slab.initdb(name, dupsort=True)

    def add(self, item):
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
    A dictionary-like object which stores it's props in a slab via a prefix.

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
    A utility for translating arbitrary name strings into fixed with id bytes
    '''

    def __init__(self, slab, name):

        self.slab = slab
        self.name2abrv = slab.initdb(f'{name}:name2abrv')
        self.abrv2name = slab.initdb(f'{name}:abrv2name')

        self.offs = 0

        item = self.slab.last(db=self.abrv2name)
        if item is not None:
            self.offs = s_common.int64un(item[0])

    @s_cache.memoize(10000)
    def abrvToName(self, abrv):
        byts = self.slab.get(abrv, db=self.abrv2name)
        if byts is not None:
            return byts.decode()

    @s_cache.memoize(10000)
    def nameToAbrv(self, name):

        lkey = name.encode()
        abrv = self.slab.get(lkey, db=self.name2abrv)
        if abrv is not None:
            return abrv

        abrv = s_common.int64en(self.offs)

        self.offs += 1

        self.slab.put(lkey, abrv, db=self.name2abrv)
        self.slab.put(abrv, lkey, db=self.abrv2name)

        return abrv

class MultiQueue:
    '''
    Allows creation/consumption of multiple durable queues in a slab.
    '''
    def __init__(self, slab, name):

        self.slab = slab

        self.abrv = slab.getNameAbrv(f'{name}:abrv')
        self.qdata = self.slab.initdb(f'{name}:qdata')

        self.sizes = SlabDict(self.slab, db=self.slab.initdb(f'{name}:sizes'))
        self.queues = SlabDict(self.slab, db=self.slab.initdb(f'{name}:meta'))
        self.offsets = SlabDict(self.slab, db=self.slab.initdb(f'{name}:offs'))

        self.waiters = collections.defaultdict(asyncio.Event)

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

    def add(self, name, info):

        if self.queues.get(name) is not None:
            mesg = f'A queue exists with the name {name}.'
            raise s_exc.DupName(mesg=mesg, name=name)

        item = self.queues.get(name)
        if item is None:
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

    def put(self, name, item):
        return self.puts(name, (item,))

    def puts(self, name, items):

        if self.queues.get(name) is None:
            mesg = f'No queue named {name}.'
            raise s_exc.NoSuchName(mesg=mesg, name=name)

        abrv = self.abrv.nameToAbrv(name)

        offs = retn = self.offsets.get(name, 0)

        for item in items:

            self.slab.put(abrv + s_common.int64en(offs), s_msgpack.en(item), db=self.qdata)

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
        if offs < 0:
            return

        indx = s_common.int64en(offs)
        abrv = self.abrv.nameToAbrv(name)

        for lkey, lval in self.slab.scanByRange(abrv + int64min, abrv + indx, db=self.qdata):
            self.slab.delete(lkey, db=self.qdata)
            self.sizes.set(name, self.sizes.get(name) - 1)
            await asyncio.sleep(0)

class GuidStor:

    def __init__(self, slab, name):

        self.slab = slab
        self.name = name

        self.db = self.slab.initdb(name)

    def gen(self, iden):
        bidn = s_common.uhex(iden)
        return SlabDict(self.slab, db=self.db, pref=bidn)

def _ispo2(i):
    return not (i & (i - 1)) and i

def _florpo2(i):
    '''
    Return largest power of 2 equal to or less than i
    '''
    if _ispo2(i):
        return i
    return 1 << (i.bit_length() - 1)

def _ceilpo2(i):
    '''
    Return smallest power of 2 equal to or greater than i
    '''
    if _ispo2(i):
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
    COMMIT_PERIOD = 0.5  # time between commits

    async def __anit__(self, path, **kwargs):

        await s_base.Base.__anit__(self)

        kwargs.setdefault('map_size', s_const.gibibyte)
        kwargs.setdefault('lockmemory', False)

        opts = kwargs

        self.path = pathlib.Path(path)

        self.optspath = self.path.with_suffix('.opts.yaml')

        if self.optspath.exists():
            opts.update(s_common.yamlload(self.optspath))

        initial_mapsize = opts.get('map_size')
        if initial_mapsize is None:
            raise s_exc.BadArg('Slab requires map_size')

        mdbpath = self.path / 'data.mdb'
        if mdbpath.exists():
            mapsize = max(initial_mapsize, os.path.getsize(mdbpath))
        else:
            mapsize = initial_mapsize

        # save the transaction deltas in case of error...
        self.xactops = []
        self.recovering = False

        opts.setdefault('max_dbs', 128)
        opts.setdefault('writemap', True)

        self.maxsize = opts.pop('maxsize', None)
        self.growsize = opts.pop('growsize', None)

        self.readonly = opts.get('readonly', False)
        self.lockmemory = opts.pop('lockmemory', False)

        self.mapsize = _mapsizeround(mapsize)
        if self.maxsize is not None:
            self.mapsize = min(self.mapsize, self.maxsize)

        self._saveOptsFile()

        self.lenv = lmdb.open(path, **opts)

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
        self.max_could_lock = 0
        self.lock_progress = 0
        self.lock_goal = 0

        if self.lockmemory:
            async def memlockfini():
                self.resizeevent.set()
                await self.memlocktask
            self.memlocktask = s_coro.executor(self._memorylockloop)
            self.onfini(memlockfini)

        self.dbnames = {}

        self.onfini(self._onCoFini)
        self.schedCoro(self._runSyncLoop())

    def trash(self):
        '''
        Deletes underlying storage
        '''
        try:
            os.unlink(self.optspath)
        except FileNotFoundError:  # pragma: no cover
            pass

        shutil.rmtree(self.path, ignore_errors=True)

    def getNameAbrv(self, name):
        return SlabAbrv(self, name)

    def getMultiQueue(self, name):
        return MultiQueue(self, name)

    def statinfo(self):
        return {
            'locking_memory': self.locking_memory,  # whether the memory lock loop was started and hasn't ended
            'max_could_lock': self.max_could_lock,  # the maximum this system could lock
            'lock_progress': self.lock_progress,  # how much we've locked so far
            'lock_goal': self.lock_goal,  # how much we want to lock
            'prefaulting': self.prefaulting  # whether we are right meow prefaulting
        }

    def _acqXactForReading(self):
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
        opts = {}
        if self.growsize is not None:
            opts['growsize'] = self.growsize
        if self.maxsize is not None:
            opts['maxsize'] = self.maxsize
        s_common.yamlmod(opts, self.optspath)

    async def _syncLoopOnce(self):
        try:
            # do this from the loop thread only to avoid recursion
            await self.fire('commit')
            self.forcecommit()

        except lmdb.MapFullError:
            self._handle_mapfull()
            # There's no need to re-try self.forcecommit as _growMapSize does it

    async def _runSyncLoop(self):
        while not self.isfini:
            await self.waitfini(timeout=self.COMMIT_PERIOD)
            if self.isfini:
                # There's no reason to forcecommit on fini, because there's a separate handler to already do that
                break

            await self._syncLoopOnce()

    async def _onCoFini(self):
        assert s_glob.iAmLoop()

        await self.fire('commit')

        while True:
            try:
                self._finiCoXact()
            except lmdb.MapFullError:
                self._handle_mapfull()
                continue
            break
        self.lenv.close()
        del self.lenv

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
        if not s_thishost.get('hasmemlocking'):
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

        path = self.path.absolute() / 'data.mdb'  # Path to the file that gets mapped
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

            memstart, memlen = s_thisplat.getFileMappedRegion(path)
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
            self.lock_goal = goal_end

            self.lock_progress = 0
            prev_memend = memstart

            # Actually do the prefaulting and locking.  Only do it a chunk at a time to maintain responsiveness.
            while prev_memend < goal_end:
                new_memend = min(prev_memend + MAX_LOCK_AT_ONCE, goal_end)
                memlen = new_memend - prev_memend
                PROT = 1 # PROT_READ
                FLAGS = 0x8001  # MAP_POPULATE | MAP_SHARED (Linux only)  (for fast prefaulting)
                try:
                    self.prefaulting = True
                    with s_thisplat.mmap(0, length=new_memend - prev_memend, prot=PROT, flags=FLAGS, fd=fileno,
                                         offset=prev_memend - memstart):
                        s_thisplat.mlock(prev_memend, memlen)
                finally:
                    self.prefaulting = False

                prev_memend = new_memend
                self.lock_progress = prev_memend - memstart

            if first_end:
                first_end = False
                logger.info('completed prefaulting and locking slab')

            self.schedCallSafe(self.lockdoneevent.set)

        self.locking_memory = False
        logger.debug('memory locking thread ended')

    def initdb(self, name, dupsort=False):
        while True:
            try:
                db = self.lenv.open_db(name.encode('utf8'), txn=self.xact, dupsort=dupsort)
                self.dirty = True
                self.forcecommit()
                self.dbnames[name] = (db, dupsort)
                return name
            except lmdb.MapFullError:
                self._handle_mapfull()

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
        realdb, dupsort = self.dbnames.get(db, (None, False))
        try:
            return self.xact.get(lkey, db=realdb)
        finally:
            self._relXactForReading()

    def last(self, db=None):
        '''
        Return the last key/value pair from the given db.
        '''
        self._acqXactForReading()
        realdb, dupsort = self.dbnames.get(db, (None, False))
        try:
            with self.xact.cursor(db=realdb) as curs:
                if not curs.last():
                    return None
                return curs.key(), curs.value()
        finally:
            self._relXactForReading()

    def stat(self, db=None):
        self._acqXactForReading()
        realdb, dupsort = self.dbnames.get(db, (None, False))
        try:
            return self.xact.stat(db=realdb)
        finally:
            self._relXactForReading()

    # non-scan ("atomic") interface.
    # def getByDup(self, lkey, db=None):
    # def getByPref(self, lkey, db=None):
    # def getByRange(self, lkey, db=None):

    def scanByDups(self, lkey, db=None):

        with Scan(self, db) as scan:

            if not scan.set_key(lkey):
                return

            yield from scan.iternext()

    def scanByPref(self, byts, db=None):

        with Scan(self, db) as scan:

            if not scan.set_range(byts):
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

    def scanByFull(self, db=None):

        with Scan(self, db) as scan:

            if not scan.first():
                return

            for lkey, lval in scan.iternext():
                yield lkey, lval

    # def keysByRange():
    # def valsByRange():

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

        realdb, dupsort = self.dbnames.get(db, (None, False))

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

        realdb, dupsort = self.dbnames.get(db, (None, False))

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
        sourcedb, dupsort = self.dbnames.get(sourcedbname)

        destslab.initdb(destdbname, dupsort)
        destdb, _ = destslab.dbnames.get(destdbname)

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

    def pop(self, lkey, db=None):
        return self._xact_action(self.pop, lmdb.Transaction.pop, lkey, db=db)

    def delete(self, lkey, val=None, db=None):
        return self._xact_action(self.delete, lmdb.Transaction.delete, lkey, val, db=db)

    def put(self, lkey, lval, dupdata=False, overwrite=True, db=None):
        return self._xact_action(self.put, lmdb.Transaction.put, lkey, lval, dupdata=dupdata, overwrite=overwrite,
                                 db=db)

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

        # ok... lets commit and re-open
        self._finiCoXact()
        self._initCoXact()
        return True

class Scan:
    '''
    A state-object used by Slab.  Not to be instantiated directly.
    '''
    def __init__(self, slab, db):
        self.slab = slab
        self.db, self.dupsort = slab.dbnames.get(db, (None, False))

        self.atitem = None
        self.bumped = False
        self.iterfunc = None

    def __enter__(self):
        self.slab._acqXactForReading()
        self.curs = self.slab.xact.cursor(db=self.db)
        self.slab.scans.add(self)
        return self

    def __exit__(self, exc, cls, tb):
        self.bump()
        self.slab.scans.discard(self)
        self.slab._relXactForReading()

    def last_key(self):
        '''
        Return the last key in the database.  Returns none if database is empty.
        '''
        if not self.curs.last():
            return None

        return self.curs.key()

    def first(self):

        if not self.curs.first():
            return False

        if self.dupsort:
            self.iterfunc = functools.partial(lmdb.Cursor.iternext_dup, keys=True)
        else:
            self.iterfunc = lmdb.Cursor.iternext

        self.genr = self.curs.iternext()
        self.atitem = next(self.genr)
        return True

    def set_key(self, lkey):

        if not self.curs.set_key(lkey):
            return False

        # set_key for a scan is only logical if it's a dup scan
        if self.dupsort:
            self.iterfunc = functools.partial(lmdb.Cursor.iternext_dup, keys=True)
        else:
            self.iterfunc = lmdb.Cursor.iternext

        self.genr = self.iterfunc(self.curs)
        self.atitem = next(self.genr)
        return True

    def set_range(self, lkey):

        if not self.curs.set_range(lkey):
            return False

        self.iterfunc = lmdb.Cursor.iternext
        self.genr = self.iterfunc(self.curs)
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
                    if self.dupsort:
                        self.curs.set_range_dup(*self.atitem)
                    else:
                        self.curs.set_range(self.atitem[0])

                    self.genr = self.iterfunc(self.curs)

                    if self.curs.item() == self.atitem:
                        next(self.genr)

                self.atitem = next(self.genr)

        except StopIteration:
            return

    def bump(self):
        if not self.bumped:
            self.curs.close()
            self.bumped = True

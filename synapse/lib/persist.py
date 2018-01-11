'''
Tools for persisting msgpack compatible objects.
'''
import io
import os
import time
import struct
import msgpack
import logging
import threading
import collections

import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.queue as s_queue
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

def opendir(*paths, **opts):
    '''
    Open a persistance directory by path name with options.
    '''
    path = s_common.gendir(*paths)
    return Dir(path, **opts)

megabyte = 1024000
gigabyte = 1024000000

blocksize = megabyte * 10

class Offset(s_eventbus.EventBus):
    '''
    A file backed persistant offset calculator.

    Example:

        poff = Offset(dirpath,'foo.off'):

        for off,item in pers.items():
            dostuff(item)
            poff.set(off)

    '''
    def __init__(self, *paths):
        s_eventbus.EventBus.__init__(self)

        self.fd = s_common.genfile(*paths)
        self.valu = 0

        byts = self.fd.read(8)
        if len(byts):
            self.valu, = struct.unpack('<Q', byts)

        self.onfini(self.fd.close)

    def set(self, valu):
        '''
        Set (and save) the current offset.
        '''
        self.valu = valu

        self.fd.seek(0)
        self.fd.write(struct.pack('<Q', valu))

        self.fire('pers:off', valu=valu)

    def get(self):
        '''
        Return the current offset.
        '''
        return self.valu

class Dir(s_eventbus.EventBus):
    '''
    A persistence dir may be used similar to a Write-Ahead-Log to sync
    objects based on events ( and allow desync-catch-up )
    '''

    def __init__(self, path, **opts):
        s_eventbus.EventBus.__init__(self)

        self.size = 0
        self.opts = opts
        self.last = None
        self.path = s_common.gendir(path)
        self.lock = threading.Lock()

        self.window = collections.deque()

        self.opts.setdefault('filemax', gigabyte)

        self.baseoff = opts.get('base', 0)  # base address of this file

        self.files = []
        self.pumps = {}
        self.queues = []
        self.pumpers = []

        self._initPersFiles()

        if self.files:
            self.last = self.files[-1]

        if self.last is None:
            self.last = self._addPersFile(0)

        # Update size so APIs can be used to get the size
        self.size = self.last.opts.get('baseoff') + self.last.size

        self.onfini(self._onDirFini)

    def dirSize(self):
        '''
        Get the current size of the perist Dir structure.

        Returns:
            int: The current size of the persist dir structure.
        '''
        return self.size

    def getOffsetIdens(self):
        '''
        Get a list of idens which have offset files.

        Returns:
            list: List of idens with corresponding offset files.
        '''
        fps = s_common.listdir(self.path, glob='*.off')
        fns = [os.path.split(fn)[1] for fn in fps]
        return [fn.split('.off')[0] for fn in fns]

    def pump(self, iden, func):
        '''
        Fire a new pump thread to call the given function.

        Example:

            pdir.firePumpThread( iden, core.sync )

        '''
        if self.isfini:
            raise s_common.IsFini()

        with self.lock:
            if self.pumps.get(iden):
                raise Exception('Duplicate Pump Iden: %s' % (iden,))

        self._runPumpThread(iden, func)

    def getPumpOffs(self):
        '''
        Return a dict of { iden:offset } info for the running pumps.

        Example:

            for iden,noff in pdir.getPumpOffs():
                dostuff()

        '''
        return [(iden, poff.get()) for (iden, poff) in self.pumps]

    def getIdenOffset(self, iden):
        return Offset(self.path, '%s.off' % iden)

    @s_common.firethread
    def _runPumpThread(self, iden, func):
        '''
        Fire a mirror thread to push persist events to a function.
        '''
        self.pumpers.append(threading.currentThread())

        with self.getIdenOffset(iden) as poff:

            while not self.isfini:
                noff = poff.get()
                self.pumps[iden] = noff
                try:

                    for noff, item in self.items(noff):

                        func(item)

                        poff.set(noff)
                        self.pumps[iden] = noff

                        if self.isfini:
                            return

                except Exception as e:
                    if not self.isfini:
                        logger.warning('_runPumpThread (%s): %e' % (iden, e))
                        time.sleep(1)

    def _onDirFini(self):
        [q.fini() for q in self.queues]
        [f.fini() for f in self.files]
        [p.join(timeout=1) for p in self.pumpers]

    def _initPersFiles(self):
        # initialize the individual persist files we already have...
        names = [n for n in os.listdir(self.path) if n.endswith('.cyto')]
        for name in sorted(names):
            off = int(name.split('.', 1)[0], 16)
            pers = self._addPersFile(off)

    def _addPersFile(self, baseoff):
        # MUST BE CALLED WITH LOCK OR IN CTOR
        fd = s_common.genfile(self.path, '%.16x.cyto' % baseoff)
        pers = File(fd, baseoff=baseoff)
        self.files.append(pers)
        return pers

    def add(self, item):
        '''
        Add an object to the persistant store.
        Returns (off,size) tuple within the persistance stream.

        Example:

            off,size = pers.add(item)

        '''
        with self.lock:
            base = self.last.opts.get('baseoff')
            soff, size = self.last.add(item)

            self.size = base + self.last.size

            if self.last.size >= self.opts.get('filemax'):
                self.last = self._addPersFile(self.size)

            [q.put((self.size, item)) for q in self.queues]

            return (base + soff, size)

    def items(self, off):
        '''
        Yield (nextoff,object) tuples from the file backlog and real-time
        once caught up.

        Args:
            off (int): Starting offset to use when unpacking objects from the
                       Dir object.

        Examples:
            Iterate over the items in a file and do stuff with them::

                for noff, item in pers.items(0):
                    dostuff(item)

            Iterate over the items in a file and save offset location::

                poff = pers.getIdenOffset(iden)
                for noff, item in pers.items(poff.get()):
                    dostuff(item)
                    poff.set(noff)

        Notes:
            This is a legitimate yield generator; it may not be used across
            a Telepath Proxy.

            The offset yielded by this is an absolute offset to the **next**
            item in the stream; not the item which was just yielded. As such,
            that offset value may be used to restart any sort of
            synchronization activities done with the Dir object.  The Offset
            object is provided to assist with this.

        Yields:
            ((int, object)): A tuple containing the absolute offset of the
            next object and the unpacked object itself.
        '''
        que = s_queue.Queue()
        unpk = msgpack.Unpacker(use_list=0, encoding='utf8',
                                unicode_errors='surrogatepass')

        # poff is used for iterating over persistence files when unpacking,
        # while the user supplied offset is used to return absolute offsets
        # when unpacking objects from the stream.
        poff = off

        if self.files[0].opts.get('baseoff') > off:
            raise Exception('Too Far Back') # FIXME

        logger.debug('Entering items with offset %s', off)

        for pers in self.files:

            base = pers.opts.get('baseoff')

            logger.debug('Base offset for %s - %s', pers, base)

            # do we skip this file?
            filemax = base + pers.size
            if filemax < off:
                continue

            while True:

                foff = poff - base

                logger.debug('Reading from offset %s', foff)

                byts = pers.readoff(foff, blocksize)

                # file has been closed...
                if byts is None:
                    return

                # check if we're at the edge
                if not byts:

                    with self.lock:

                        # newp! ( break out to next file )
                        if self.last != pers:
                            break

                        # if there are byts now, we whiffed
                        # the check/set race.  Go around again.
                        byts = pers.readoff(foff, blocksize)
                        if byts is None:
                            return

                        if not byts:
                            self.queues.append(que)
                            break

                unpk.feed(byts)

                try:

                    while True:
                        item = unpk.unpack()
                        # explicit is better than implicit
                        reloff = unpk.tell()
                        aboff = reloff + off
                        yield aboff, item

                except msgpack.exceptions.OutOfData:
                    pass

                poff += len(byts)

            logger.debug('Done with cached events for %s', pers)

        logger.debug('Entering real-time event pump')
        # we are now a queued real-time pump
        try:

            # this will break out on fini...
            for x in que:
                yield x

        finally:
            self.queues.remove(que)
            que.fini()

        logger.debug('Leaving items()')

class File(s_eventbus.EventBus):
    '''
    A single fd based persistence stream.

    This is mostly a helper for Dir().  All consume/resume
    behavior should be facilitated by the Dir() object.
    '''
    def __init__(self, fd=None, **opts):
        s_eventbus.EventBus.__init__(self)

        if fd is None:
            fd = io.BytesIO()

        fd.seek(0, os.SEEK_END)

        self.fd = fd

        # track these to prevent context switches
        self.size = fd.tell()
        self.fdoff = self.size

        self.opts = opts
        self.fdlock = threading.Lock()

        self.onfini(self._onFileFini)

    def _onFileFini(self):
        with self.fdlock:
            self.fd.close()

    def add(self, item):
        '''
        Add an item to the persistance storage.
        '''
        byts = s_msgpack.en(item)
        size = len(byts)

        with self.fdlock:

            if self.isfini:
                raise s_common.IsFini()

            if self.fdoff != self.size:
                self.fd.seek(0, os.SEEK_END)

            off = self.size

            self.fd.write(byts)

            self.size += len(byts)
            self.fdoff = self.size

            return (off, size)

    def readoff(self, off, size):
        '''
        Read size bytes form the given offset.
        '''
        with self.fdlock:

            if self.isfini:
                return None

            if self.fdoff != off:
                self.fd.seek(off)

            self.fd.seek(off)

            try:
                byts = self.fd.read(size)
            except ValueError as e:
                return None

            self.fdoff = off + len(byts)

            return byts

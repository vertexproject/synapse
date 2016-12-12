'''
Tools for persisting msgpack compatible objects.
'''
import time
import struct
import msgpack
import logging
import threading
import collections

import synapse.compat as s_compat
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.lib.queue as s_queue
import synapse.lib.urlhelp as s_urlhelp

from synapse.common import *

logger = logging.getLogger(__name__)

def opendir(*paths, **opts):
    '''
    Open a persistance directory by path name with options.
    '''
    path = gendir(*paths)
    return Dir(path,**opts)

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

        self.fd = genfile(*paths)
        self.valu = 0

        byts = self.fd.read(8)
        if len(byts):
            self.valu, = struct.unpack('<Q', byts)

        self.onfini( self.fd.close )

    def set(self, valu):
        '''
        Set (and save) the current offset.
        '''
        self.valu = valu

        self.fd.seek(0)
        self.fd.write( struct.pack('<Q',valu) )

        self.fire('pers:off', valu=valu)

    def get(self):
        '''
        Return the current offset.
        '''
        return self.valu

class Dir(s_eventbus.EventBus):
    '''
    A persistance dir may be used similar to a Write-Ahead-Log to sync
    objects based on events ( and allow desync-catch-up )
    '''

    def __init__(self, path, **opts):
        s_eventbus.EventBus.__init__(self)

        self.size = 0
        self.opts = opts
        self.last = None
        self.path = gendir(path)
        self.lock = threading.Lock()

        self.window = collections.deque()

        self.opts.setdefault('filemax',gigabyte) 

        self.baseoff = opts.get('base',0)  # base address of this file

        self.files = []
        self.pumps = {}
        self.queues = []
        self.pumpers = []

        self._initPersFiles()

        if self.files:
            self.last = self.files[-1]

        if self.last == None:
            self.last = self._addPersFile(0)

        self.onfini( self._onDirFini )

    def pump(self, iden, func):
        '''
        Fire a new pump thread to call the given function.

        Example:

            pdir.firePumpThread( iden, core.sync )

        '''
        if self.isfini:
            raise IsFini()

        with self.lock:
            if self.pumps.get(iden):
                raise Exception('Duplicate Pump Iden: %s' % (iden,))

        self._runPumpThread(iden,func)

    def getPumpOffs(self):
        '''
        Return a dict of { iden:offset } info for the running pumps.

        Example:

            for iden,noff in pdir.getPumpOffs():
                dostuff()

        '''
        return [ (iden,poff.get()) for (iden,poff) in self.pumps ]

    def getIdenOffset(self, iden):
        return Offset(self.path, '%s.off' % iden)

    @firethread
    def _runPumpThread(self, iden, func):
        '''
        Fire a mirror thread to push persist events to a function.
        '''
        self.pumpers.append( threading.currentThread() )

        with self.getIdenOffset(iden) as poff:

            while not self.isfini:
                noff = poff.get()
                self.pumps[iden] = noff
                try:

                    for noff,item in self.items(noff):

                        func(item)

                        poff.set(noff)
                        self.pumps[iden] = noff

                        if self.isfini:
                            return

                except Exception as e:
                    if not self.isfini:
                        logger.warning('_runPumpThread (%s): %e' % (iden,e))
                        time.sleep(1)

    def _onDirFini(self):
        [ q.fini() for q in self.queues ]
        [ f.fini() for f in self.files ]
        [ p.join(timeout=1) for p in self.pumpers ]

    def _initPersFiles(self):
        # initialize the individual persist files we already have...
        names = [ n for n in os.listdir(self.path) if n.endswith('.cyto') ]
        for name in sorted(names):
            off = int(name.split('.',1)[0],16)
            pers = self._addPersFile(off)

    def _addPersFile(self, baseoff):
        # MUST BE CALLED WITH LOCK OR IN CTOR
        fd = genfile(self.path,'%.16x.cyto' % baseoff)
        pers = File(fd,baseoff=baseoff)
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
            soff,size = self.last.add(item)

            self.size = base + self.last.size

            if self.last.size >= self.opts.get('filemax'):
                self.last = self._addPersFile(self.size)

            [ q.put((self.size,item)) for q in self.queues ]

            return (base + soff, size)

    def items(self, off):
        '''
        Yield (nextoff,item) tuples from the file backlog and real-time
        once caught up.

        NOTE: because this is a legitimate yield generator it may not be
              used across a telepath proxy.

        Example:

            for noff,item in pers.items(0):
                stuff(item)

        '''
        que = s_queue.Queue()
        unpk = msgpack.Unpacker(use_list=0,encoding='utf8')

        if self.files[0].opts.get('baseoff') > off:
            raise Exception('Too Far Back') # FIXME

        # a bit of a hack to get lengths from msgpack Unpacker
        data = {'next':0}
        def calcsize(b):
            data['next'] += len(b)

        for pers in self.files:

            base = pers.opts.get('baseoff')

            # do we skip this file?
            filemax = base + pers.size
            if filemax < off:
                continue

            while True:

                foff = off - base

                byts = pers.readoff(foff,blocksize)

                # file has been closed...
                if byts == None:
                    return

                # check if we're at the edge
                if not byts:

                    with self.lock:

                        # newp! ( break out to next file )
                        if self.last != pers:
                            break

                        # if there are byts now, we whiffed
                        # the check/set race.  Go around again.
                        byts = pers.readoff(foff,blocksize)
                        if byts == None:
                            return

                        if not byts:
                            self.queues.append(que)
                            break

                unpk.feed( byts )

                try:

                    while True:
                        item = unpk.unpack(write_bytes=calcsize)
                        yield data['next'],item

                except msgpack.exceptions.OutOfData:
                    pass

                off += len(byts)

        # we are now a queued real-time pump
        try:

            # this will break out on fini...
            for x in que:
                yield x

        finally:
            self.queues.remove(que)
            que.fini()

class File(s_eventbus.EventBus):
    '''
    A single fd based persistance stream.

    This is mostly a helper for Dir().  All consume/resume
    behavior should be facilitated by the Dir() object.
    '''
    def __init__(self, fd=None, **opts):
        s_eventbus.EventBus.__init__(self)

        if fd == None:
            fd = s_compat.BytesIO()

        fd.seek(0,os.SEEK_END)

        self.fd = fd

        # track these to prevent context switches
        self.size = fd.tell()
        self.fdoff = self.size

        self.opts = opts
        self.fdlock = threading.Lock()

        self.onfini( self._onFileFini )

    def _onFileFini(self):
        with self.fdlock:
            self.fd.close()

    def add(self, item):
        '''
        Add an item to the persistance storage.
        '''
        byts = msgenpack(item)
        size = len(byts)

        with self.fdlock:

            if self.isfini:
                raise IsFini()

            if self.fdoff != self.size:
                self.fd.seek(0,os.SEEK_END)

            off = self.size

            self.fd.write(byts)

            self.size += len(byts)
            self.fdoff = self.size

            return (off,size)

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

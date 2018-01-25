import os
import struct
import logging
import threading
import collections

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.kv as s_kv
import synapse.lib.atomic as s_atomic
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack
import synapse.lib.atomfile as s_atomfile

logger = logging.getLogger(__file__)

class Fifo(s_config.Config):

    def __init__(self, conf, xmit=None):

        s_config.Config.__init__(self)
        self.setConfOpts(conf)
        self.reqConfOpts()

        self.lock = threading.Lock()
        self.winds = s_eventbus.BusRef()

        self.atoms = s_eventbus.BusRef(ctor=self._brefAtomCtor)
        self.onfini(self.atoms.fini)

        self.seqs = self._getFifoSeqs()
        if not self.seqs:
            self.seqs.append(0)

        # open our append atom
        lseq = self.seqs[-1]
        self.atom = self.atoms.gen(lseq)

        # our next expected sequence num
        self.nseq = lseq + self.atom.size

        kvpath = self._getPathJoin('fifo.lmdb')
        self.kvstor = s_kv.KvStor(kvpath)

        self.windows = {}

        self.wind = self.getWindByIden('default')
        if xmit is not None:
            self.wind.resync(xmit=xmit)

        self._cullAtomBase(self.wind.bseq)

    def getWindByIden(self, iden):
        '''
        Return a Window() by an iden string.

        Args:
            iden (str): The window iden.

        Returns:
            (synapse.lib.fifo.Window)
        '''
        wind = self.windows.get(iden)
        if wind is None:
            wind = Window(self, iden)
            self.windows[iden] = wind

        return wind

    def ack(self, seqn):
        '''
        Acknowledge (and cull) an item in the sequence.
        '''
        retn = self.wind.ack(seqn)

        if retn:
            self._cullAtomBase(self.wind.bseq)

        return retn

    def _cullAtomBase(self, nseq):

        with self.lock:

            while self.seqs[0] < nseq:
                fseq = self.seqs.pop(0)
                path = self._getSeqPath(fseq)
                os.unlink(path)

    def resync(self, xmit=None):
        '''
        Re-synchronize this Fifo by sending all window entries.
        (optionally specify a new xmit callback)

        Args:
            xmit (func): The fifo xmit() callback.

        Example:

            def xmit(qent):
                seqn, nseq, item = qent
                dostuff()

            fifo.resync(xmit=xmit)
        '''
        return self.wind.resync(xmit=xmit)

    def _findFifoAtom(self, nseq):
        # if they specify an un-aligned sequence, find the prev
        if nseq not in self.seqs:
            nseq = [s for s in self.seqs if s <= nseq][-1]

        return nseq, self.atoms.gen(nseq)

    def _brefAtomCtor(self, nseq):
        path = self._getSeqPath(nseq)
        return s_atomfile.openAtomFile(path, memok=False)

    def puts(self, items):
        '''
        Put a list of items into the Fifo.
        This is a bulk access api for put().

        Args:
            items (list): A list of items to add
        '''
        todo = [(i, s_msgpack.en(i)) for i in items]
        with self.lock:
            [self._putItemByts(i, b) for i, b in todo]

    def put(self, item):
        '''
        Put a new item into the Fifo.

        Args:
            item (obj): The object to serialize into the Fifo.
        '''
        byts = s_msgpack.en(item)
        with self.lock:
            self._putItemByts(item, byts)

    def _putItemByts(self, item, byts):

        seqn = self.nseq

        self.atom.writeoff(self.atom.size, byts)
        self.nseq += len(byts)

        if self.atom.size >= self.maxsize:
            self.atom.fini()
            self.seqs.append(self.nseq)
            self.atom = self.atoms.gen(self.nseq)

        qent = (seqn, self.nseq, item)

        self.wind._may_put(qent)

        # see if any of our readers are caught up...
        [wind._may_put(qent) for wind in self.winds.vals()]

    def _getPathJoin(self, *names):
        dirn = self.getConfOpt('dir')
        return s_common.genpath(dirn, *names)

    @staticmethod
    @s_config.confdef(name='fifo')
    def _getFifoConf():
        return (
            ('dir', {'type': 'str', 'req': 1, 'doc': 'Path to the FIFO directory'}),

            #('file:maxsize', {'type': 'int', 'asloc': 'maxsize', 'defval': 1000000000000,
                #'doc': 'Max fifo file size'}),

            ('window:min', {'type': 'int', 'defval': 1000, 'doc': 'Minimum window size'}),
            ('window:max', {'type': 'int', 'defval': 2000, 'doc': 'Maximum window size'}),
            ('window:fill', {'type': 'int', 'defval': 10000000, 'doc': 'Window fill read size'}),
        )

    def _getSeqPath(self, nseq):
        dirn = self.getConfOpt('dir')
        base = '%.16x.fifo' % (nseq,)
        return os.path.join(dirn, base)

    def _getFifoSeqs(self):

        dirn = self.getConfOpt('dir')

        retn = []
        for name in os.listdir(dirn):

            if not name.endswith('.fifo'):
                continue

            base = name.split('.')[0]
            retn.append(int(base, 16))

        retn.sort()
        return retn

class Window(s_eventbus.EventBus):
    '''
    A read window within a Fifo.
    '''
    def __init__(self, fifo, iden, xmit=None):

        s_eventbus.EventBus.__init__(self)

        self.fifo = fifo
        self.iden = iden

        self.info = fifo.kvstor.getKvDict('fifo:wind:%s' % (iden,))

        self.wmin = fifo.getConfOpt('window:min')
        self.wmax = fifo.getConfOpt('window:max')
        self.wfill = fifo.getConfOpt('window:fill')

        self.lock = threading.RLock()

        self.caught = False

        self.filling = s_atomic.CmpSet(False)

        self._xmit = xmit

        self.unpk = s_msgpack.Unpk()
        self.dequ = collections.deque()

        # the next expected ack
        self.nack = self.info.get('nack', defval=0)

        # if the Fifo has moved past us, catch up... :(
        nmin = fifo.seqs[0]
        if self.nack < nmin:
            self._set_nack(nmin)

        self.nseq = self.nack
        self._initFifoAtom(self.nseq)

        # what's the last sequence in the window...
        self._fill()

    def _may_put(self, qent):

        # called with self.fdir.lock
        if not self.caught:
            return

        if qent[0] != self.nseq:
            self._set_caught(False)
            return

        if len(self.dequ) >= self.wmax:
            self._set_caught(False)
            return

        self._put(qent)

    def _put(self, qent):
        self.nseq = qent[1]
        self.dequ.append(qent)
        self._run_xmit(qent)

    def _initFifoAtom(self, nseq):
        self.bseq, self.atom = self.fifo._findFifoAtom(nseq)
        self.roff = nseq - self.bseq

    def _set_nack(self, nack):
        self.nack = nack
        self.info.set('nack', nack)

    def resync(self, xmit=None):
        '''
        Re-synchronize this Fifo (assuming an xmit restart).
        ( see Fifo.resync )
        '''
        if xmit is not None:
            self._xmit = xmit

        for item in self.dequ:
            self._xmit(item)

    def _run_xmit(self, item):
        if self._xmit is not None:
            try:
                self._xmit(item)
            except Exception as e:
                logger.exception('fifo xmit failed')

    # TODO: add a "selective ack" resync

    def ack(self, seqn):
        '''
        Ack a sequence from this Fifo.

        Args:
            seqn (int): The sequence number to acknowledge.
        '''

        if seqn == -1:
            self.resync()
            return False

        with self.lock:

            if seqn < self.nack:
                return False

            qent = None
            while self.dequ and self.dequ[0][0] <= seqn:
                qent = self.dequ.popleft()

            # if we pop'd a qent, set nack to the nseq
            if qent is not None:
                self._set_nack(qent[1])

            # possibly trigger filling the window
            self.fill()
            return True

    def fill(self):
        '''
        Possibly trigger filling the fifo window from bytes.
        '''
        if self.caught:
            return

        if len(self.dequ) > self.wmin:
            return

        if not self.filling.set(True):
            return

        self._fill()

    def _set_caught(self, valu):

        self.caught = valu

        if self.caught:
            self._finiFifoAtom()
        else:
            self._initFifoAtom(self.nseq)

    def _finiFifoAtom(self):
        self.atom.fini()
        self.atom = None

    def _fill(self):

        try:

            while len(self.dequ) < self.wmax:

                byts = self.atom.readoff(self.roff, self.wfill)

                blen = len(byts)

                # now we have to check if we are caught up
                if blen == 0:

                    with self.fifo.lock:

                        # an atom will only change size with fifo.lock
                        # so this will mop up the race due to not holding
                        # the lock over the call to readoff...
                        if self.roff != self.atom.size:
                            continue

                        # if we really are at the end of the file check if
                        # the fifo.nseq is the same as ours...
                        if self.nseq == self.fifo.nseq:
                            self._set_caught(True)
                            return

                    # we had a 0 read and are *not* caught up...
                    self.atom.fini()
                    self._initFifoAtom(self.nseq)
                    continue

                self.roff += len(byts)

                for size, item in self.unpk.feed(byts):
                    seqn = self.nseq
                    self.nseq += size
                    self._put((seqn, self.nseq, item))

        finally:
            self.filling.set(False)

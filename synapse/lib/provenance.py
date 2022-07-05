import hashlib
import logging
import pathlib
import contextlib

import synapse.exc as s_exc

import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.task as s_task
import synapse.lib.const as s_const
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.slabseqn as s_slabseqn

logger = logging.getLogger(__name__)

'''
Provenance tracks the reason and path how a particular hypergraph operation
occurred.

It maintains a separate stack for each asyncio task, where each stack frame is
a high-level record of how we got there.  For example, a storm query that caused
a trigger to fire that ran a storm query to delete a node will have 4 frames:
a storm frame, then a trig frame, then another storm frame, then a stormcmd frame.

To save space in the splice log, the storage system provides an iden for each
unique provenance stack.  The iden is provided on each splice.  We cache the
iden on each stack frame (which represents the iden for the stack that ends
on that stack frame).
'''

ProvenanceEnabled = True
ProvenanceStackLimit = 256

class _ProvStack:
    def __init__(self):
        # We start with a dummy frame so we don't have to special case an empty stack
        self.provs = [None]  # A stack of the provenance info
        self.idens = [(None, True)]  # A stack of the iden/written tupls for the prov stack ending in this frame

    def __len__(self):
        return len(self.provs)

    def get(self):
        '''
        Returns:
            iden, whether that iden has been written, the provstack info
        '''
        # We add an empty dict for future expansion/info
        iden, written = self.idens[-1]
        return iden, written, ({}, self.provs[1:])

    def setiden(self, identupl):
        self.idens[-1] = identupl

    def push(self, typ, **info):
        tuplinfo = tuple((k, info[k]) for k in sorted(info.keys()))
        self.provs.append((typ, tuplinfo))
        self.idens.append((None, True))

    def pop(self):
        self.provs.pop()
        self.idens.pop()

    def copy(self):
        newstack = _ProvStack()
        newstack.provs = self.provs[:]
        newstack.idens = self.idens[:]
        return newstack

s_task.vardefault('provstack', lambda: _ProvStack())

@contextlib.contextmanager
def claim(typ, **info):
    '''
    Add an entry to the provenance stack for the duration of the context
    '''
    stack = s_task.varget('provstack')
    if len(stack) > ProvenanceStackLimit:
        baseframe = stack.provs[1]
        recent_frames = stack.provs[-6:]
        raise s_exc.RecursionLimitHit(mesg='Hit provenance claim recursion limit',
                                      type=typ, info=info, baseframe=baseframe, recent_frames=recent_frames)

    if not ProvenanceEnabled:
        info = {}

    stack.push(typ, **info)

    try:
        yield
    finally:
        stack.pop()

def reset():
    '''
    Reset the stack to its initial state

    For testing purposes
    '''
    s_task.varset('provstack', _ProvStack())

def dupstack(newtask):
    '''
    Duplicate the current provenance stack onto another task
    '''
    stack = s_task.varget('provstack')
    s_task.varset('provstack', stack.copy(), newtask)

def get():
    '''
    Returns:
       A tuple of (stack iden (or None if not set), the current provenance stack)
    '''
    stack = s_task.varget('provstack')
    return stack.get()

def setiden(iden, waswritten):
    '''
    Sets the cached stack iden, waswritten for the current provenance stack.  We use waswritten to cache whether we've
    written the stack and so we can tell the snap whether to fire a prov:new event
    '''
    stack = s_task.varget('provstack')
    stack.setiden((iden, waswritten))

def _providen(prov):
    '''
    Calculates a provenance iden from a provenance stack
    '''
    return hashlib.md5(s_msgpack.en(prov)).digest()

class ProvStor(s_base.Base):
    '''
    Persistently stores provstacks so they can be retrieved by iden and sequence
    '''
    PROV_MAP_SIZE = 64 * s_const.mebibyte
    PROV_FN = 'prov.lmdb'

    async def __anit__(self, dirn, proven=True):
        await s_base.Base.__anit__(self)

        global ProvenanceEnabled
        ProvenanceEnabled = proven
        self.enabled = proven

        if self.enabled:
            path = str(pathlib.Path(dirn) / 'slabs' / self.PROV_FN)
            self.slab = await s_lmdbslab.Slab.anit(path, map_size=self.PROV_MAP_SIZE)
            self.onfini(self.slab.fini)

            self.db = self.slab.initdb('prov')

            self.provseq = s_slabseqn.SlabSeqn(self.slab, 'provs')

    def getProvStack(self, iden: bytes):
        '''
        Returns the provenance stack given the iden to it
        '''
        if not ProvenanceEnabled:
            return None

        retn = self.slab.get(iden, db=self.db)
        if retn is None:
            return None

        return s_msgpack.un(retn)

    def provStacks(self, offs, size):
        '''
        Returns a stream of provenance stacks at the given offset
        '''
        if not ProvenanceEnabled:
            return None

        for _, iden in self.provseq.slice(offs, size):
            stack = self.getProvStack(iden)
            if stack is None:
                continue
            yield (iden, stack)

    def stor(self):
        '''
        Writes the current provenance stack to storage if it wasn't already there

        Returns (iden, provstack) if was written, (None, None) if it was already there
        '''
        if not ProvenanceEnabled:
            return None, None

        if not self.enabled:
            return None, None

        iden, waswritten, provstack = get()
        if waswritten:
            return None, None

        assert iden is not None

        # Convert each frame back from (k, v) tuples to a dict
        misc, frames = provstack
        dictframes = [(typ, {k: v for (k, v) in info}) for (typ, info) in frames]
        bytz = s_msgpack.en((misc, dictframes))

        didwrite = self.slab.put(iden, bytz, overwrite=False, db=self.db)
        if didwrite:
            self.provseq.save([iden])

        setiden(iden, True)

        return s_common.ehex(iden), provstack

    def precommit(self):
        '''
        Determine the iden for the current provenance stack and return it

        Returns the iden
        '''
        if not ProvenanceEnabled:
            return None

        providen, waswritten, provstack = get()
        if providen is None:
            providen = _providen(provstack)
            setiden(providen, False)
        return s_common.ehex(providen)

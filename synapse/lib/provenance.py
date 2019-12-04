import hashlib
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

class _ProvStack:
    def __init__(self):
        # We start with a dummy frame so we don't have to special case an empty stack
        self.provs = [None]  # A stack of the provenance info
        self.idens = [None]  # A stack of the idens for the prov stack ending in this frame

    def __len__(self):
        return len(self.provs)

    def get(self):
        # We add an empty dict for future expansion/info
        return self.idens[-1], ({}, self.provs[1:])

    def setiden(self, iden):
        self.idens[-1] = iden

    def push(self, typ, **info):
        tuplinfo = tuple((k, info[k]) for k in sorted(info.keys()))
        self.provs.append((typ, tuplinfo))
        self.idens.append(None)

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

    if len(stack) > 256:
        baseframe = stack.provs[1]
        recent_frames = stack.provs[-6:]
        raise s_exc.RecursionLimitHit(mesg='Hit provenance claim recursion limit',
                                      type=typ, info=info, baseframe=baseframe, recent_frames=recent_frames)

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

def setiden(iden):
    '''
    Sets the cached stack iden for the current provenance stack
    '''
    stack = s_task.varget('provstack')
    stack.setiden(iden)

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

    async def __anit__(self, dirn):
        await s_base.Base.__anit__(self)
        path = str(pathlib.Path(dirn) / 'slabs' / self.PROV_FN)
        self.slab = await s_lmdbslab.Slab.anit(path, map_size=self.PROV_MAP_SIZE)
        self.onfini(self.slab.fini)

        self.db = self.slab.initdb('prov')

        self.provseq = s_slabseqn.SlabSeqn(self.slab, 'provs')

    def getProvStack(self, iden: bytes):
        '''
        Returns the provenance stack given the iden to it
        '''
        retn = self.slab.get(iden, db=self.db)
        if retn is None:
            return None

        return s_msgpack.un(retn)

    def provStacks(self, offs, size):
        '''
        Returns a stream of provenance stacks at the given offset
        '''
        for _, iden in self.provseq.slice(offs, size):
            stack = self.getProvStack(iden)
            if stack is None:
                continue
            yield (iden, stack)

    def getProvIden(self, provstack):
        '''
        Returns the iden corresponding to a provenance stack and stores if it hasn't seen it before
        '''
        iden = _providen(provstack)
        misc, frames = provstack
        # Convert each frame back from (k, v) tuples to a dict
        dictframes = [(typ, {k: v for (k, v) in info}) for (typ, info) in frames]
        bytz = s_msgpack.en((misc, dictframes))
        didwrite = self.slab.put(iden, bytz, overwrite=False, db=self.db)
        if didwrite:
            self.provseq.save([iden])

        return iden

    def commit(self):
        '''
        Writes the current provenance stack to storage if it wasn't already there and returns it

        Returns (Tuple[bool, str, List[]]):
            Whether the stack was not cached, the iden of the prov stack, and the provstack
        '''
        providen, provstack = get()
        wasnew = (providen is None)
        if wasnew:
            providen = self.getProvIden(provstack)
            setiden(providen)
        return wasnew, s_common.ehex(providen), provstack

    def migratePre010(self, layer):
        '''
        Ask layer to migrate its old provstack DBs into me
        '''
        layer.migrateProvPre010(self.slab)

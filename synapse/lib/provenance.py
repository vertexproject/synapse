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

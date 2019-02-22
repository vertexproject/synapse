import contextlib

import synapse.exc as s_exc

import synapse.lib.task as s_task

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
on that stack frame.
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

    if len(stack) > 256:  # pragma: no cover
        raise s_exc.RecursionLimitHit(mesg='Hit global recursion limit')

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
    Sets the stack iden for the current provenance stack
    '''
    stack = s_task.varget('provstack')
    stack.setiden(iden)

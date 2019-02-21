import contextlib

import synapse.exc as s_exc

import synapse.lib.task as s_task

'''
Provenance tracks the reason and path how a particular hypergraph operation
occurred.

It maintains a separate stack for each asyncio task, where each stack frame is
a high-level record of how we got there.  For example, a storm query that caused
a trigger to fire that ran a storm query to delete a node will have 5 frames:
a base frame, a storm frame, then a trig frame, then another storm frame, then
a stormcmd frame.

To save space in the splice log, the storage system provides an alias for each
unique provenance stack.  The alias is provided on each splice.  We cache the
alias on each stack frame (which represents the alias for the stack that ends
on that stack frame.
'''

_BaseFrame = (None, ('', {}))  # type: ignore

s_task.vardefault('provstack', lambda: [_BaseFrame])

@contextlib.contextmanager
def claim(typ, **info):
    '''
    Add an entry to the provenance stack for the duration of the context
    '''
    stack = s_task.varget('provstack')

    if len(stack) > 256:  # pragma: no cover
        breakpoint()
        raise s_exc.RecursionLimitHit(mesg='Hit global recursion limit')

    frame = (None, (typ, info))
    stack.append(frame)
    try:
        yield
    finally:
        stack.pop()

def reset():
    '''
    Reset the stack to its initial state

    For testing purposes
    '''
    s_task.varset('provstack', [_BaseFrame])

def dupstack(newtask):
    '''
    Duplicate the current provenance stack onto another task
    '''
    stack = s_task.varget('provstack')
    s_task.varset('provstack', stack[:], newtask)

def get():
    '''
    Returns:
       A tuple of (stack alias (or None if not set), the current provenance stack)
    '''
    stack = s_task.varget('provstack')
    stackalias = stack[-1][0]
    return stackalias, [frame[1] for frame in stack]

def setStackAlias(stackalias):
    '''
    Sets the stack alias for the current provenance stack
    '''
    stack = s_task.varget('provstack')
    if stack is None:
        stack = [_BaseFrame]
        s_task.varset('provstack', stack)
    stack[-1] = stackalias, stack[-1][1]

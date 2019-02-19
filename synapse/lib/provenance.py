import contextlib
import contextvars

import synapse.exc as s_exc

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

_ProvStack = contextvars.ContextVar('ProvStack', default=[(None, ('', {}))])  # type: ignore

@contextlib.contextmanager
def claim(typ, **info):
    '''
    Add an entry to the provenance stack for the duration of the context
    '''
    stack = _ProvStack.get()

    if len(stack) > 256:  # pragma: no cover
        raise s_exc.RecursionLimitHit(mesg='Hit global recursion limit')

    frame = (None, (typ, info))
    stack.append(frame)
    yield
    stack.pop()

def reset():
    '''
    Resets the stack to its initial state.

    For testing purposes
    '''
    _ProvStack.set([(None, ('', {}))])

def copy():
    '''
    Get a copy of the raw stack (solely for the sake of pasting it to a child task)
    '''
    return _ProvStack.get()[:]

def paste(stack):
    '''
    Sets the stack from a raw copy
    '''
    _ProvStack.set(stack)

def get():
    '''
    Returns:
       A tuple of the stack alias if set, the current provenance stack
    '''
    stack = _ProvStack.get()
    assert stack  # there's a base frame that shall never be popped
    stackalias = stack[-1][0]
    return stackalias, [frame[1] for frame in stack]

def setStackAlias(stackalias):
    '''
    Sets the stack alias for the current provenance stack
    '''
    stack = _ProvStack.get()
    assert stack  # there's a base frame that shall never be popped
    stack[-1] = stackalias, stack[-1][1]

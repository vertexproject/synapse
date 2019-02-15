import contextlib
import contextvars

from typing import Tuple, List, Optional, Iterator, Any, Dict

# The first entry for each frame is an alias for the stack that ends with that frame

AliasT = Any

TufoT = Tuple[str, Dict[str, Any]]

ProvFrameT = Tuple[Optional[AliasT], TufoT]  # (stackalias, tufo))

ProvStackT = List[ProvFrameT] # List[stackalias, (frametype, frameinfo)]

# Start with a base frame in case there are stors outside any claim
_ProvStack: contextvars.ContextVar = contextvars.ContextVar('ProvStack', default=[('')])

@contextlib.contextmanager
def claim(typ: str, **info: Any) -> Iterator[None]:
    '''
    Add an entry to the provenance stack for the duration of the context

    Note:  try to keep these args short, as they will go in every event
    '''
    stack: ProvStackT = _ProvStack.get()
    frame: ProvFrameT = (None, (typ, info))
    stack.append(frame)
    yield
    stack.pop()

def reset() -> None:
    '''
    Resets the stack to its initial state.

    For testing purposes
    '''
    _ProvStack.set([])

def get() -> Tuple[Optional[AliasT], List[TufoT]]:
    '''
    Returns:
       A tuple of the stack alias if set, the current provenance stack
    '''
    stack: ProvStackT = _ProvStack.get()
    assert stack  # there's a base frame that shall never be popped
    stackalias = stack[-1][0]
    return stackalias, [frame[1] for frame in stack]

def setStackAlias(stackalias: AliasT) -> None:
    stack: ProvStackT = _ProvStack.get()
    assert stack  # there's a base frame that shall never be popped
    stack[-1] = stackalias, stack[-1][1]

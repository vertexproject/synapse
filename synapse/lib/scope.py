import asyncio
import contextlib

import synapse.common as s_common

class Scope:
    '''
    The Scope object assists in creating nested varible scopes.

    Example:

        with Scope() as scope:

            scope.set('foo',10)

            with scope:
                scope.set('foo',20)
                dostuff(scope) # 'foo' is 20...

            dostuff(scope) # 'foo' is 10 again...

    '''
    def __init__(self, *frames, **vals):
        self.frames = list(frames)
        if vals:
            self.frames.append(vals)

    def __enter__(self):
        return self.enter()

    def __exit__(self, exc, cls, tb):
        self.leave()

    def enter(self, vals=None):
        '''
        Add an additional scope frame.
        '''
        if vals is None:
            vals = {}
        return self.frames.append(vals)

    def leave(self):
        '''
        Pop the current scope frame.
        '''
        return self.frames.pop()

    def set(self, name, valu):
        '''
        Set a value in the current scope frame.
        '''
        self.frames[-1][name] = valu

    def update(self, vals):
        '''
        Set multiple values in the current scope frame.
        '''
        self.frames[-1].update(vals)

    def get(self, name, defval=None):
        '''
        Retrieve a value from the closest scope frame.
        '''
        for frame in reversed(self.frames):
            valu = frame.get(name, s_common.novalu)
            if valu != s_common.novalu:
                return valu

        return defval

    def add(self, name, *vals):
        '''
        Add values as iter() compatible items in the current scope frame.
        '''
        item = self.frames[-1].get(name)
        if item is None:
            self.frames[-1][name] = item = []
        item.extend(vals)

    def pop(self, name, defval=None):
        '''
        Pop and return a value (from the last frame) of the scope.

        Args:
            name (str): The name of the scope variable.
        Returns:
            obj: The scope variable value or None
        '''
        return self.frames[-1].pop(name, None)

    def iter(self, name):
        '''
        Iterate through values added with add() from each scope frame.
        '''
        for frame in self.frames:
            vals = frame.get(name)
            if vals is None:
                continue
            for valu in vals:
                yield valu

    def __setitem__(self, name, valu):
        self.frames[-1][name] = valu

    def copy(self):
        '''
        Create a shallow copy of the current Scope.

        Returns:
            Scope: A new scope which is a copy of the current scope.
        '''
        return self.__class__(*[frame.copy() for frame in self.frames])

# set up a global scope with an empty frame
globscope = Scope(dict())


def _task_scope() -> Scope:
    '''
    Get the current task scope. If the _syn_scope is not set, set it to a new scope
    that inherits from the globscope.

    Notes:
        This must be run from inside an asyncio.Task.

    Returns:
        Scope: A Scope object.
    '''
    task = asyncio.current_task()
    scope = getattr(task, '_syn_scope', None)

    # no need to lock because it's per-task...
    if scope is None:
        scope = globscope.copy()
        task._syn_scope = scope

    return scope

def get(name, defval=None):
    '''
    Access this task's scope with default values from glob.
    '''
    return _task_scope().get(name, defval=defval)

def set(name, valu):
    '''
    Set a value in the current frame of the local task scope.
    '''
    _task_scope().set(name, valu)

def pop(name):
    '''
    Pop and return a task scope variable.
    Args:
        name (str): The task scope variable name.
    Returns:
        obj: The scope value or None
    '''
    return _task_scope().pop(name)

def update(vals):
    scope = _task_scope()
    scope.update(vals)

def ctor(name, func, *args, **kwargs):
    '''
    Add a ctor callback to the global scope.
    '''
    return globscope.ctor(name, func, *args, **kwargs)

@contextlib.contextmanager
def enter(vals=None):
    '''
    Return the task's local scope for use in a with block
    '''
    scope = _task_scope()
    scope.enter(vals)
    try:
        yield
    finally:
        scope.leave()

def clone(task: asyncio.Task) -> None:
    '''
    Clone the current task Scope onto the provided task.

    Args:
        task (asyncio.Task): The task object to attach the scope too.

    Notes:
        This must be run from an asyncio IO loop.

        If the current task does not have a scope, we clone the default global Scope.

        This will ``enter()`` the scope, and add a task callback to ``leave()`` the scope.

    Returns:
        None
    '''

    current_task = asyncio.current_task()

    if current_task is None:
        # It is possible that we are executing code started by
        # asyncio.call_soon_threadsafe (or similar mechanisms)
        # in which case there is not yet a task for us to
        # retrieve the scope from, and we can inherit directly
        # from globscope.

        parent_scope = globscope

    else:

        parent_scope = _task_scope()

    scope = parent_scope.copy()
    task._syn_scope = scope
    scope.enter()

    def taskdone(_task):
        # Leave the scope and drop any refs to objects
        # on Tasks to break possible GC cycles
        scope.leave()
        delattr(_task, '_syn_scope')

    task.add_done_callback(taskdone)

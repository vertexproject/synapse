import os
import threading
import contextlib
from synapse.common import novalu

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
        self.ctors = {}
        self.frames = list(frames)
        if vals:
            self.frames.append(vals)


    def __enter__(self):
        return self.enter()

    def __exit__(self, exc, cls, tb):
        self.leave()

    def enter(self,vals=None):

        '''
        Add an additional scope frame.
        '''
        if vals == None:
            vals = {}
        return self.frames.append(vals)

    def leave(self):
        '''
        Pop the current scope frame.
        '''
        self.frames.pop()

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
            valu = frame.get(name, novalu)
            if valu != novalu:
                return valu

        task = self.ctors.get(name)
        if task != None:
            func,args,kwargs = task
            item = func(*args,**kwargs)
            self.frames[-1][name] = item
            return item

        return defval

    def add(self, name, *vals):
        '''
        Add values as iter() compatible items in the current scope frame.
        '''
        item = self.frames[-1].get(name)
        if item == None:
            self.frames[-1][name] = item = []
        item.extend(vals)

    def ctor(self, name, func, *args, **kwargs):
        '''
        Add a constructor to be called when a specific property is not present.

        Example:

            scope.ctor('foo',FooThing)
            ...
            foo = scope.get('foo')

        '''
        self.ctors[name] = (func,args,kwargs)

    def iter(self, name):
        '''
        Iterate through values added with add() from each scope frame.
        '''
        for frame in self.frames:
            vals = frame.get(name)
            if vals == None:
                continue
            for valu in vals:
                yield valu

    def __setitem__(self, name, valu):
        self.frames[-1][name] = valu

# set up a global scope with env vars etc...
envr = dict(os.environ)
globscope = Scope(envr)

def _thr_scope():

    thrd = threading.currentThread()
    scope = getattr(thrd,'_syn_scope',None)

    # no need to lock because it's per-thread...
    if scope == None:
        scope = Scope(globscope)
        thrd._syn_scope = scope

    return scope

def get(name):
    '''
    Access this thread's scope with default values from glob.
    '''
    scope = _thr_scope()
    return scope.get(name)

def set(name,valu):
    '''
    Set a value in the current frame of the local thread scope.
    '''
    scope = _thr_scope()
    scope.set(name,valu)

def update(vals):
    scope = _thr_scope()
    scope.update(vals)

def ctor(name,func,*args,**kwargs):
    '''
    Add a ctor callback to the global scope.
    '''
    return globscope.ctor(name,func,*args,**kwargs)

@contextlib.contextmanager
def enter(vals=None):
    '''
    Return the thread's local scope for use in a with block
    '''
    scope = _thr_scope()
    scope.enter(vals)
    yield
    scope.leave()

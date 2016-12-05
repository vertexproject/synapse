import importlib

from synapse.common import *

def getDynMod(name):
    '''
    Dynamically import a python module and return a ref (or None).

    Example:

        mod = getDynMod('foo.bar')

    '''
    try:
        return importlib.import_module(name)
    except ImportError as e:
        return None

def getDynLocal(name):
    '''
    Dynamically import a python module and return a local.

    Example:

        cls = getDynLocal('foopkg.barmod.BlahClass')
        blah = cls()

    '''
    modname,objname = name.rsplit('.',1)
    mod = getDynMod(modname)
    if mod == None:
        return None
    return getattr(mod,objname,None)

def tryDynMod(name):
    '''
    Dynamically import a python module or exception.
    '''
    return importlib.import_module(name)

def tryDynLocal(name):
    '''
    Dynamically import a module and return a module local or raise an exception.
    '''
    modname,objname = name.rsplit('.',1)
    mod = tryDynMod(modname)
    return getattr(mod,objname)

def tryDynFunc(name,*args,**kwargs):
    '''
    Dynamically import a module and call a function or raise an exception.
    '''
    return tryDynLocal(name)(*args,**kwargs)

def runDynTask(task):
    '''
    Run a dynamic task and return the result.

    Example:

        foo = runDynTask( ('baz.faz.Foo', (), {} ) )

    '''
    func = getDynLocal(task[0])
    if func == None:
        raise NoSuchFunc(task[0])
    return func(*task[1],**task[2])

class CallCapt:
    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
    
def runDynEval(text, locs=None):
    '''
    Run a "dyn eval" string returning the result.

    Example:

        # dyn imports foo.bar and calls foo.bar.baz('woot', y=30)
        valu = runDynEval("foo.bar.baz('woot',y=30)"

    WARNING: duh.  this executes arbitrary code.  trusted inputs only!
    '''
    off = text.find('(')
    if off == -1:
        raise Exception('Invalid Dyn Eval: %r' % (text,))

    name = text[:off]
    args = text[off:]

    if locs == None:
        locs = {}

    capt = CallCapt()

    locs['capt'] = capt
    eval('capt%s' % (args,), locs)

    task = (name, capt.args, capt.kwargs)
    return runDynTask(task)

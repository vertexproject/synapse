import importlib

import synapse.exc as s_exc
import synapse.common as s_common

def getDynMod(name):
    '''
    Dynamically import a python module and return a ref (or None).

    Example:

        mod = getDynMod('foo.bar')

    '''
    try:
        return importlib.import_module(name)
    except ImportError:
        return None

def getDynLocal(name):
    '''
    Dynamically import a python module and return a local.

    Example:

        cls = getDynLocal('foopkg.barmod.BlahClass')
        blah = cls()

    '''
    if name.find('.') == -1:
        return None

    modname, objname = name.rsplit('.', 1)
    mod = getDynMod(modname)
    if mod is None:
        return None

    return getattr(mod, objname, None)

def getDynMeth(name):
    '''
    Retrieve and return an unbound method by python path.
    '''
    cname, fname = name.rsplit('.', 1)

    clas = getDynLocal(cname)
    if clas is None:
        return None

    return getattr(clas, fname, None)

def tryDynMod(name):
    '''
    Dynamically import a python module or exception.
    '''
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError:
        raise s_exc.NoSuchDyn(name=name)

def tryDynLocal(name):
    '''
    Dynamically import a module and return a module local or raise an exception.
    '''
    if name.find('.') == -1:
        raise s_exc.NoSuchDyn(name=name)

    modname, objname = name.rsplit('.', 1)
    mod = tryDynMod(modname)
    item = getattr(mod, objname, s_common.novalu)
    if item is s_common.novalu:
        raise s_exc.NoSuchDyn(name=name)
    return item

def tryDynFunc(name, *args, **kwargs):
    '''
    Dynamically import a module and call a function or raise an exception.
    '''
    return tryDynLocal(name)(*args, **kwargs)

def runDynTask(task):
    '''
    Run a dynamic task and return the result.

    Example:

        foo = runDynTask( ('baz.faz.Foo', (), {} ) )

    '''
    func = getDynLocal(task[0])
    if func is None:
        raise s_exc.NoSuchFunc(name=task[0])
    return func(*task[1], **task[2])

import inspect
import importlib

import synapse.exc as s_exc
import synapse.common as s_common

import logging

logger = logging.getLogger(__name__)

def getDynMod(name):
    '''
    Dynamically import a python module and return a ref (or None).

    Example:

        mod = getDynMod('foo.bar')

    '''
    try:
        return importlib.import_module(name)
    except ImportError:
        logger.exception(f'Failed to import "{name}"')
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

def getDynCoro(name):
    '''
    Dynamically import a python module and return a named awaitable function from it.

    Args:
        name: Python path and function name.

    Examples:

        Get an awaitable function and call it::

            afunc = getDynCoro('foopkg.barmod.someAsyncFunction')
            if afunc is not None:
                await afunc()

    Returns:
        The function, or None if the function does not exist.
    '''
    func = getDynLocal(name)
    if func is None or not inspect.iscoroutinefunction(func):
        return None
    return func

def reqDynCoro(name):
    '''
    Dynamically import a python module and return a named awaitable function from it.

    Args:
        name: Python path and function name.

    Examples:

        Get an awaitable function and call it::

            afunc = getDynCoro('foopkg.barmod.someAsyncFunction')
            await afunc()

    Returns:
        The awaitable function.

    Raises:
        NoSuchDyn: If the function does not exist or is not an awaitable function.
    '''
    func = getDynCoro(name)
    if func is None:
        raise s_exc.NoSuchDyn(mesg='Failed to resolve {name} to an awaitable function.', name=name)
    return func

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
    s_common.deprecated('synapse.lib.dyndeps.tryDynMod')
    return reqDynMod(name)

def reqDynMod(name):
    '''
    Dynamically import a python module or exception.
    '''
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError:
        raise s_exc.NoSuchDyn(mesg=f'Failed to import module named {name}', name=name)

def tryDynLocal(name):
    s_common.deprecated('synapse.lib.dyndeps.tryDynLocal')
    return reqDynLocal(name)

def reqDynLocal(name):
    '''
    Dynamically import a module and return a module local or raise an exception.
    '''
    if name.find('.') == -1:
        raise s_exc.NoSuchDyn(mesg='Name cannot be resolved to a local, missing ".".', name=name)

    modname, objname = name.rsplit('.', 1)
    mod = reqDynMod(modname)
    item = getattr(mod, objname, s_common.novalu)
    if item is s_common.novalu:
        raise s_exc.NoSuchDyn(mesg=f'Cannot find {objname} on {item}', name=name)
    return item

def tryDynFunc(name, *args, **kwargs):
    s_common.deprecated('synapse.lib.dyndeps.tryDynFunc')
    return reqDynFunc(name, *args, **kwargs)

def reqDynFunc(name, *args, **kwargs):
    '''
    Dynamically import a module and call a function or raise an exception.
    '''
    return reqDynLocal(name)(*args, **kwargs)

def runDynTask(task):
    '''
    Run a dynamic task and return the result.

    Example:

        foo = runDynTask( ('baz.faz.Foo', (), {} ) )

    '''
    func = getDynLocal(task[0])
    if func is None:
        raise s_exc.NoSuchFunc(mesg=f'Failed to resolve {task[0]} to a function.', name=task[0])
    return func(*task[1], **task[2])

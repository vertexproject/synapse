'''
Module which implements the synapse module API/convention.
'''
import inspect
import logging

import synapse.exc as s_exc
import synapse.dyndeps as s_dyndeps

logger = logging.getLogger(__name__)

# Python modules
synmods = {}
modlist = []
# Ctor modules
ctors = {}
ctorlist = []

def call(name, *args, **kwargs):
    '''
    Call the given function on all loaded synapse modules.

    Returns a list of name,ret,exc tuples where each module which implements
    the given function returns either ret on successful execution or exc in
    the event of an exception.

    Args:
        name (str): Name of the function to execute.
        *args (tuple): Additional positional args to use when executing the function.
        **kwargs (dict): Additional keyword args to use when executing the function.

    Example:
        Call getFooByBar with a single positional argument::

            import synapse.lib.modules as s_modules
            for name,ret,exc in s_modules.call('getFooByBar',bar):
                dostuff()

    Returns:
        list: List of name, returnval, exception information for each registered
              module.
    '''
    ret = []
    for sname,smod in modlist:
        func = getattr(smod,name,None)
        if func == None:
            continue

        try:
            val = func(*args,**kwargs)
            ret.append( (sname,val,None) )

        except Exception as e:
            ret.append( (sname,None,e) )

    #print('call: %r %r %r %r' % (name,args,kwargs,ret))
    return ret

def load(name):
    '''
    Load the given module path as a synapse module.

    Args:
        name (str): Python path to load.

    Example:
        Load the foopkg.barmod module.::

            import synapse.lib.modules as s_modules
            s_modules.load('foopkg.barmod')

    Notes:
        Users should be aware that the import process can perform arbitrary code
        execution by imported modules.

    Returns:
        The loaded module is returned.
    '''
    smod = synmods.get(name)
    if smod == None:
        logger.info('loading syn mod: %s', name)
        smod = s_dyndeps.tryDynMod(name)
        synmods[name] = smod
        modlist.append( (name,smod) )
    return smod

def load_ctor(name):
    '''
    Load the given module path as a synapse module.

    Args:
        name (str): Python path to a class ctor to load.

    Example:
        Load the foopkg.barmod.Baz ctor::

            import synapse.lib.modules as s_modules
            s_modules.load_ctor('foopkg.barmod.Baz')

    Notes:
        Users should be aware that the import process can perform arbitrary
        code execution by imported modules.  This also does not create any
        class instances upon loading.

    Returns:
        The loaded class is returned.

    Raises:
        NoSuchCtor: If the imported module does not have the listed ctor or it
                    is not a class.
    '''
    modpath, ctor = name.rsplit('.', 1)
    smod = ctors.get(name)
    if smod == None:
        smod = s_dyndeps.tryDynMod(modpath)
        cls = getattr(smod, ctor, None)
        if cls is None:
            raise s_exc.NoSuchCtor(name=name, mesg='Ctor not found')
        if not inspect.isclass(cls):
            raise s_exc.NoSuchCtor(name=name, mesg='Ctor is not a class')
        ctors[name] = smod
        ctorlist.append((name, smod))
    return ctor

def call_ctor(name, *args, **kwargs):
    '''
    Call the given function on all ctors loaded by load_ctor.

    Returns a list of name,ret,exc tuples where each ctor which implements
    the given function returns either ret on successful execution or exc in
    the event of an exception.

    Args:
        name (str): Name of the function to execute.
        *args (tuple): Additional positional args to use when executing the function.
        **kwargs (dict): Additional keyword args to use when executing the function.

    Example:
        Call getFooByBar on all loaded ctors.::

            import synapse.lib.modules as s_modules
            for name,ret,exc in s_modules.call_ctor('getFooByBar'):
                dostuff()

    Notes:
        This function does not create instances of the classes.  It is best used
        when called against @staticmethod or @classmethod functions.

    Returns:
        list: List of name, returnval, exception information for each registered
              ctor.
    '''
    ret = []
    for sname, smod in ctorlist:

        modpath, ctor = sname.rsplit('.', 1)

        cls = getattr(smod, ctor, None)
        if cls is None:
            continue
        func = getattr(cls,name,None)
        if func is None:
            continue

        try:
            val = func(*args,**kwargs)
            ret.append( (sname,val,None) )

        except Exception as e:
            ret.append( (sname,None,e) )

    return ret

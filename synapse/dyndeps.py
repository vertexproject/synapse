import importlib

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

import importlib

import synapse.common as s_common

aliases = {}

def addDynAlias(name, item):
    '''
    Add an "alias" to the dyndeps resolver system.

    Example:

        addDynAlias('foobar',FooBar)

        # ... subsequently allows ...

        x = getDynLocal('foobar')

    '''
    aliases[name] = item

def delDynAlias(name):
    '''
    Remove (and return) a dyndeps "alias" previously registered with addDynAlias()

    Example:

        delDynAlias('foobar')

    '''
    return aliases.pop(name, None)

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
    item = aliases.get(name, s_common.novalu)
    if item is not s_common.novalu:
        return item

    # this is probably a whiffd alias
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
    except ImportError as e:
        raise s_common.NoSuchDyn(name=name)

def tryDynLocal(name):
    '''
    Dynamically import a module and return a module local or raise an exception.
    '''
    item = aliases.get(name, s_common.novalu)
    if item is not s_common.novalu:
        return item

    if name.find('.') == -1:
        raise s_common.NoSuchDyn(name=name)

    modname, objname = name.rsplit('.', 1)
    mod = tryDynMod(modname)
    item = getattr(mod, objname, s_common.novalu)
    if item is s_common.novalu:
        raise s_common.NoSuchDyn(name=name)
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
        raise s_common.NoSuchFunc(name=task[0])
    return func(*task[1], **task[2])

class CallCapt:
    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

def runDynEval(text, locs=None):
    '''
    Run a "dyn eval" string returning the result.

    Example:

        # dyn imports foo.bar and calls foo.bar.baz('woot', y=30)
        valu = runDynEval("foo.bar.baz('woot',y=30)")

    WARNING: duh.  this executes arbitrary code.  trusted inputs only!
    '''
    off = text.find('(')
    if off == -1:
        raise Exception('Invalid Dyn Eval: %r' % (text,))

    name = text[:off]
    args = text[off:]

    if locs is None:
        locs = {}

    capt = CallCapt()

    locs['capt'] = capt
    eval('capt%s' % (args,), locs)

    task = (name, capt.args, capt.kwargs)
    return runDynTask(task)

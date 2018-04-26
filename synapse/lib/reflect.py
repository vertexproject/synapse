import inspect

clsskip = set([object])
def getClsNames(item):
    '''
    Return a list of "fully qualified" class names for an instance.

    Example:

        for name in getClsNames(foo):
            print(name)

    '''
    mro = inspect.getmro(item.__class__)
    mro = [c for c in mro if c not in clsskip]
    return ['%s.%s' % (c.__module__, c.__name__) for c in mro]

def getMethName(meth):
    '''
    Return a fully qualified string for the <mod>.<class>.<func> name
    of a given method.
    '''
    item = meth.__self__
    mname = item.__module__
    cname = item.__class__.__name__
    fname = meth.__func__.__name__
    return '.'.join((mname, cname, fname))

def getItemLocals(item):
    '''
    Iterate the locals of an item and yield (name,valu) pairs.

    Example:

        for name,valu in getItemLocals(item):
            dostuff()

    '''
    for name in dir(item):
        try:
            valu = getattr(item, name, None)
            yield name, valu
        except Exception as e:
            pass # various legit reasons...

def getItemInfo(item):
    '''
    Get "reflection info" dict for the given object.

    Args:
        item: Item to inspect.

    Examples:
        Find out what classes a Telepath Proxy object inherits::

            info = getItemInfo(prox)
            classes = info.get('inherits')

    Notes:
        Classes may implement a ``def _syn_reflect(self):`` function
        in order to return explicit values. The Telepath Proxy object
        is one example of doing this, in order to allow a remote caller
        to identify what classes the Proxy object represents.

    Returns:
        dict: Dictionary of reflection information.
    '''
    func = getattr(item, '_syn_reflect', None)
    if func is not None:
        return func()

    return {
        'inherits': getClsNames(item)
    }

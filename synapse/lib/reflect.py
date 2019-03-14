import inspect

import logging

logger = logging.getLogger(__name__)

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

def getItemMagic(item):
    '''
    Get, and set magic on the item's base class, for magic things we need to know for telepath

    Args:
        item:

    Returns:

    '''
    info = getattr(item, '_syn_magic', None)
    if info is not None:
        print(f'got info: {info}')
        return info
    print(f'computing info for {item}')
    info = {}

    for name in dir(item):
        if name.startswith('_'):
            continue
        attr = getattr(item, name)
        if not callable(attr):
            continue
        print(name, attr)
        if name == 'splices':
            print(type(attr))
            print(f'IS coro? {inspect.iscoroutine(attr)}')
        if inspect.isasyncgenfunction(attr):
            info[name] = {'genr': True}

    try:
        setattr(item, '_syn_magic', info)
    except Exception as e:
        logger.exception(f'Failed to set magic on {item}')

    try:
        setattr(item.__class__, '_syn_magic', info)
    except Exception as e:
        logger.exception(f'Failed to set magic on {item.__class__}')
    print(info)
    return info

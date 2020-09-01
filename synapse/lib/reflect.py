import inspect

import logging

import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

clsskip = set([object])
unwraps = {'adminapi',
           }

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
        except Exception:  # pragma: no cover
            pass # various legit reasons...

def getShareInfo(item):
    '''
    Get a dictionary of special annotations for a Telepath Proxy.

    Args:
        item:  Item to inspect.

    Notes:
        This will set the ``_syn_telemeth`` attribute on the item
        and the items class, so this data is only computed once.

    Returns:
        dict: A dictionary of methods requiring special handling by the proxy.
    '''
    key = f'_syn_sharinfo_{item.__class__.__module__}_{item.__class__.__qualname__}'
    info = getattr(item, key, None)
    if info is not None:
        return info

    meths = {}
    info = {'meths': meths,
            'syn:version': s_version.version,
            'classes': getClsNames(item),
            }

    for name in dir(item):

        if name.startswith('_'):
            continue

        attr = getattr(item, name, None)
        if not callable(attr):
            continue

        # We know we can cleanly unwrap these functions
        # for asyncgenerator inspection.
        wrapped = getattr(attr, '__syn_wrapped__', None)
        if wrapped in unwraps:
            real = inspect.unwrap(attr)
            if inspect.isasyncgenfunction(real):
                meths[name] = {'genr': True}
                continue

        if inspect.isasyncgenfunction(attr):
            meths[name] = {'genr': True}

    try:
        setattr(item, key, info)
    except Exception:  # pragma: no cover
        logger.exception(f'Failed to set magic on {item}')

    try:
        setattr(item.__class__, key, info)
    except Exception:  # pragma: no cover
        logger.exception(f'Failed to set magic on {item.__class__}')

    return info

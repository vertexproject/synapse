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
    mro = [ c for c in mro if c not in clsskip ]
    return [ '%s.%s' % (c.__module__,c.__name__) for c in mro ]

def getItemInfo(item):
    '''
    Get "reflection info" dict for the given object.

    NOTE: classes may implement _syn_reflect(self): to
          return explicit values (for example, telepath proxy)
    '''
    func = getattr(item,'_syn_reflect',None)
    if func != None:
        return func()

    return {
        'inherits':getClsNames(item)
    }


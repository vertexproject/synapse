'''
Some common utility functions for dealing with tufos.
'''

# FIXME do not delete until all functionality is ported to Node

def tufo(name, **props):
    '''
    Convenience / syntax sugar for tufo construction.

    Example:

        tuf0 = s_tufo.tufo('bar',baz='faz',derp=20)
        # tuf0 = ('bar',{'baz':'faz', 'derp':20})

    '''
    return (name, props)

def ival(tufo, name):
    '''
    Return a min,max interval tuple or None for the node.

    Args:
        tufo ((str,dict)):  A node in tuple form
        name (str):         The name of the interval to return

    Returns:
        (int,int)   An interval value ( or None )

    '''
    minv = tufo[1].get('>' + name)
    if minv is None:
        return None
    return minv, tufo[1].get('<' + name)

def equal(tuf0, tuf1):
    '''
    Since dicts are not comparible, this implements equality comparison
    for a given tufo by comparing and orders list of (prop,valu) pairs.

    Example:

        import synapse.lib.tufo as s_tufo

        tuf0 = s_tufo.tufo('foo',bar=10,baz=20)
        tuf1 = s_tufo.tufo('foo',baz=20,bar=10)

        if s_tufo.equal(tuf0,tuf1):
            print('woot')


    NOTE: This API is not particularly fast and is mostly for implementing
          tests.

    '''
    # cheapest compare first...
    if tuf0[0] != tuf1[0]:
        return False

    props0 = list(tuf0[1].items())
    props1 = list(tuf1[1].items())

    props0.sort()
    props1.sort()

    return props0 == props1

def ephem(form, fval, **props):
    props = {'%s:%s' % (form, p): v for (p, v) in props.items()}
    props[form] = fval
    props['tufo:form'] = form
    return (None, props)

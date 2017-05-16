'''
Some common utility functions for dealing with tufos.
'''

def tufo(name,**props):
    '''
    Convenience / syntax sugar for tufo construction.

    Example:

        tuf0 = s_tufo.tufo('bar',baz='faz',derp=20)
        # tuf0 = ('bar',{'baz':'faz', 'derp':20})

    '''
    return (name,props)

def props(tufo,pref=None):
    '''
    Return the relative props from the given tufo prefix.
    ( or from the form name by default )

    Example:

        import synapse.tufo as s_tufo
        tuf0 = s_tufo.tufo('bar', **{'baz':'faz', 'derp': 20, 'namespace:sound': 'quack'})
        # tuf0 = ('bar', {'namespace:ducksound': 'quack', 'derp': 20, 'baz': 'faz'})
        info = s_tufo.props(tuf0, pref='namespace')
        # info = {'ducksound': 'quack'}
        tuf1 = s_tufo.tufo('duck', **{'tufo:form': 'animal', 'animal:sound':'quack', 'animal:stype': 'duck'})
        # tuf1 = ('duck', {'tufo:form': 'animal', 'animal:stype': 'duck', 'animal:sound': 'quack'})
        info = s_tufo.props(tuf1)
        # info = {'stype': 'duck', 'sound': 'quack'}

    '''
    if pref == None:
        pref = tufo[1].get('tufo:form')

    pref = '%s:' % (pref,)
    plen = len(pref)
    return { p[plen:]:v for (p,v) in tufo[1].items() if p.startswith(pref) }

def tags(tufo,leaf=False):

    fulltags = [ p.split('|',2)[2] for p in tufo[1].keys() if p.startswith('*|') ]
    if not leaf:
        return fulltags

    # longest first
    retn = []

    # brute force rather than build a tree.  faster in small sets.
    for size,tag in sorted([ (len(t),t) for t in fulltags ], reverse=True):
        look = tag + '.'
        if any([ r.startswith(look) for r in retn]):
            continue
        retn.append(tag)

    return retn

def equal(tuf0,tuf1):
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

    props0 = list( tuf0[1].items() )
    props1 = list( tuf1[1].items() )

    props0.sort()
    props1.sort()

    return props0 == props1

def ephem(form,fval,**props):
    props = { '%s:%s' % (form,p):v for (p,v) in props.items() }
    props[form] = fval
    props['tufo:form'] = form
    return (None,props)

def tagged(tufo,tag):
    prop = '*|%s|%s' % (tufo[1].get('tufo:form'),tag)
    return tufo[1].get(prop) != None

import collections

import synapse.common as s_common

'''
Tools to help implement a hierarchical tagging system.
'''

def iterTagDown(tag,div='.'):
    '''
    Yield tags from top to bottom.

    Example:

        iterTagDown('foo.bar.baz') -> ('foo','foo.bar','foo.bar.baz')

    '''
    parts = tag.split(div)
    for i in range(len(parts)):
        yield div.join(parts[0:i+1])

def iterTagUp(tag,div='.'):
    '''
    Yield tags from top to bottom.

    Example:

        iterTagUp('foo.bar.baz') -> ('foo.bar.baz','foo.bar','foo')

    '''
    parts = tag.split(div)
    psize = len(parts)
    for i in range(psize):
        yield div.join( parts[:psize-i] )

def getTufoSubs(tufo, tag):
    '''
    Return a list of tufo props for the given tag (and down).
    '''
    props = []
    form = tufo[1].get('tufo:form')

    prop = '*|%s|%s' % (form,tag)
    if tufo[1].get(prop):
        props.append(prop)
    else:
        return props

    pref = prop + '.'

    props.extend([ p for p in tufo[1].keys() if p.startswith(pref) ])
    return props

def genTufoRows(tufo, tag, valu=None):
    '''
    Return a list of (tag,row) tuples for the given tag (and down).
    '''
    tick = s_common.now()
    if valu == None:
        valu = tick

    iden = tufo[0]
    form = tufo[1].get('tufo:form')
    props = [ (tag,'*|%s|%s' % (form,tag)) for tag in iterTagDown(tag) ]
    return [ (tag, (iden,prop,valu,tick)) for tag, prop in props if tufo[1].get(prop) == None ]

def getTufoTags(tufo):
    '''
    Return a dict of tag:val for tags on tufo.

    Example:

        tags = getTufoTags(tufo)

    '''
    return { choptag(p):v for (p,v) in tufo[1].items() if p[0] == '*' }

def tufoHasTag(tufo,tag):
    '''
    Returns True if the tufo has the given tag.

    Example:

        if tufoHasTag(tufo,'woot'):
            dostuff()

    '''
    form = tufo[1].get('tufo:form')
    prop = '*|%s|%s' % (form,tag)
    return tufo[1].get(prop) != None

def choptag(prop):
    '''
    Chop a tag property to return tag.

    Example:

        bazfaz = choptag('*|foo:bar|baz.faz')

    '''
    return prop.split('|',2)[2]

class ByTag:
    '''
    A dictionary style put/get API using tags.
    '''
    def __init__(self):
        self.byval = {}
        self.bytag = collections.defaultdict(set)

    def put(self, item, tags):
        '''
        Add an item for ByTag lookup with tags.

        Example:

            btag.put( woot, ('woots.woot0', 'foo') )

        '''
        self.byval[item] = tags
        for tag in tags:
            for name in iterTagDown(tag):
                self.bytag[name].add(item)

    def get(self, tag):
        '''
        Retrieve items by a tag.

        Example:

            for item in btag.get('foo.bar'):
                dostuff(item)

        '''
        vals = self.bytag.get(tag)
        if vals == None:
            return ()

        return list(vals)

    def pop(self, item, dval=None):
        '''
        Remove an item previously added to the ByTag.
        '''
        tags = self.byval.pop(item,None)
        if tags == None:
            return

        for tag in tags:
            for name in iterTagDown(tag):
                s = self.bytag.get(name)
                if s == None:
                    continue

                s.discard(item)
                if not s:
                    self.bytag.pop(name,None)

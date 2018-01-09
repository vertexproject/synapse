import collections

'''
Tools to help implement a hierarchical tagging system.
'''

def iterTagDown(tag, div='.'):
    '''
    Yield tags from top to bottom.

    Example:

        iterTagDown('foo.bar.baz') -> ('foo','foo.bar','foo.bar.baz')

    '''
    parts = tag.split(div)
    for i in range(len(parts)):
        yield div.join(parts[0:i + 1])

def iterTagUp(tag, div='.'):
    '''
    Yield tags from top to bottom.

    Example:

        iterTagUp('foo.bar.baz') -> ('foo.bar.baz','foo.bar','foo')

    '''
    parts = tag.split(div)
    psize = len(parts)
    for i in range(psize):
        yield div.join(parts[:psize - i])

def getTufoSubs(tufo, tag):
    '''
    Return a list of tufo props for the given tag (and down).

    Args:
        tufo ((str,dict)):  A node in tuple form
        tag (str):          A tag name

    Returns:

    '''
    prop = '#' + tag
    if not tufo[1].get(prop):
        return ()

    props = [prop]
    pref = prop + '.'

    props.extend(p for p in tufo[1].keys() if p.startswith(pref))
    return props

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
        if vals is None:
            return ()

        return list(vals)

    def pop(self, item, dval=None):
        '''
        Remove an item previously added to the ByTag.
        '''
        tags = self.byval.pop(item, None)
        if tags is None:
            return

        for tag in tags:
            for name in iterTagDown(tag):
                s = self.bytag.get(name)
                if s is None:
                    continue

                s.discard(item)
                if not s:
                    self.bytag.pop(name, None)

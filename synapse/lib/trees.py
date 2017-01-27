'''
A simple implementation of an interval tree to lookup
potentially overlapping intervals from a point.
'''

#TODO make an n-dimentional implementation using
# segment trees as well...

class IntervalTree:
    '''
    Construct an interval tree from the inputs.

    https://en.wikipedia.org/wiki/Interval_tree

    Example:

        ivals = ( ((1,30),{}),  ((18,33),{}), ... )

        itree = IntervalTree(ivals)

        for ival in itree.get(12):
            dostuff(ival)

    '''
    def __init__(self, ivals):
        self.root = self._calc_nodes(ivals)

    def _calc_nodes(self, ivals):
        '''
        Recursively construct the data structures for the tree
        given the input set of interval tufos.
        '''
        xmin = min( [ ival[0][0] for ival in ivals ] )
        xmax = max( [ ival[0][1] for ival in ivals ] )

        delta = xmax - xmin
        center = xmin + (delta / 2)

        s_left = []
        s_right = []
        s_center = []

        for ival in ivals:

            if ival[0][1] < center:
                s_left.append(ival)
                continue

            if ival[0][0] > center:
                s_right.append(ival)
                continue

            s_center.append(ival)

        def maxkey(x):
            return x[0][1]

        def minkey(x):
            return x[0][0]

        s_center_mins = list(s_center)
        s_center_mins.sort( key=minkey )

        s_center_maxs = list(s_center)
        s_center_maxs.sort( key=maxkey, reverse=True )

        node = (center, {'center_bymax':s_center_maxs,'center_bymin':s_center_mins})

        if s_left:
            node[1]['lnode'] = self._calc_nodes(s_left)

        if s_right:
            node[1]['rnode'] = self._calc_nodes(s_right)

        return node

    def get(self, valu):
        '''
        Return intervals which contain the specified value.

        Example:

            for ival in itree.get(valu):
                dostuff(ival)
        '''

        ret = []

        node = self.root

        while node != None:

            # heading left?
            if valu < node[0]:

                # eval centers, but only care if valu > min
                # ( and use ordering to short circuit eval )
                for ival in node[1].get('center_bymin'):
                    if valu < ival[0][0]:
                        break

                    ret.append(ival)

                # check if there is a left node to do
                node = node[1].get('lnode')
                continue

            # heading right?
            if valu > node[0]:

                # again eval centers but only care if val < max
                # ( and again short circuit using ordering )

                for ival in node[1].get('center_bymax'):
                    if valu > ival[0][1]:
                        break

                    ret.append(ival)

                node = node[1].get('rnode')
                continue

            # hitting a center directly means we're compltely done
            # doesn't matter if we use center_bymin or _bymax
            ret.extend( node[1].get('center_bymin') )
            break

        return ret

    # TODO put(self,ival):
    # TODO slice(self, minval, maxval):

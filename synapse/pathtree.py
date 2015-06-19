
'''
The synapse pathtree subsystem implements data structures for the
use of an arbitrary depth path/value tree.
'''
import collections

from synapse.common import *
from synapse.eventbus import EventBus
from synapse.statemach import StateMachine, keepstate

# "recursive" dictionary tree
def ddict():
    return collections.defaultdict(ddict)

class TreeNode(collections.defaultdict):

    def __init__(self, tree, path):
        self.tree = tree
        self.path = path

    # FIXME implement per-node perms for get/set
    def __missing__(self, key):
        node = TreeNode(self.tree, self.path + (key,))
        self[key] = node
        return node

    def set(self, prop, valu):
        path = self.path + (prop,)
        self.tree.set(path,valu)

    def pop(self, prop, default=None):
        path = self.path + (prop,)
        return self.tree.pop(path)

    def _pop(self, prop):
        return collections.defaultdict.pop(self,prop,None)

class PathTree(EventBus,StateMachine):
    '''
    A recursive path/value tree which propigates on set()
    '''
    def __init__(self, root=None, statefd=None):
        EventBus.__init__(self)
        if root == None:
            root = TreeNode(self,())

        self.root = root
        StateMachine.__init__(self, statefd=statefd)

        # FIXME locking
        # FIXME implement key "once" behavior for ram

    def node(self, path):
        '''
        Create or get the TreeNode at the specified path.
        '''
        node = self.root
        for p in path:
            node = node[p]
        return node

    def get(self, path):
        '''
        Retrieve a value from the Tree.

            path = ('foo','bar')

            val = tree.get( path )

        Notes:

            * If an intermediary path is specified a list
              of subkeys is returned.
        '''
        node,name = self._getParentNode(path)
        if node == None:
            return None

        valu = node.get(name)
        if isinstance(valu,TreeNode):
            valu = list( valu.keys() )

        return valu

    @keepstate
    def set(self, path, valu):
        '''
        Set a value in the Tree.

            path = ('foo','bar','baz')
            tree.set(path,10)

        Notes:

            * All intermediary tree nodes are created
              automagically

        '''
        node = self.root
        for p in path[:-1]:
            node = node[p]

        node[path[-1]] = valu

    @keepstate
    def pop(self, path):
        '''
        Remove and return an element from the Tree.

        Example:

            path = ('foo','bar','baz')
            valu = tree.pop(path)

        '''
        node,name = self._getParentNode(path)
        if node == None:
            return None

        return node._pop(name)

    @keepstate
    def update(self, path, d):
        '''
        Update values within a path (all at once).

        Example:

            path = ('foo','bar','baz')
            tree.update( path, {'foo':'bar','baz':'faz'} )

        Notes:

            * The dict will be created as needed

        '''
        cur = self.get(path)
        if cur == None:
            self.set(path,dict(d))
            return

        cur.update(d)

    def append(self, path, v):
        '''
        Append a value to a list in the Tree.

        Example:

            path = ('foo','bar','baz')
            tree.append( path, 10 )

        Notes:

            * The list will be created as needed.
        '''
        self.extend( path, (v,) )

    @keepstate
    def extend(self, path, l):
        '''
        Extend (or create) a list in the Tree.

        Example:

            path = ('foo','bar','baz')
            tree.extend( path, [1,2,3] )

        Notes:

            * The list will be created as needed.
        '''
        node,name = self._initParentNode(path)

        valu = node.get(name)
        if valu == None:
            node[name] = tuple(l)
            return

        node[name] = valu + tuple(l)

    @keepstate
    def link(self, path, dest):
        '''
        Update the tree so path1 points to the object
        at path2.  This is a *direct* object ref and can
        be used to save storage on duplicate coppies.

        Example:

            tree = Tree()

            tree.set( ('hosts','woot'), '1.2.3.4' )
            tree.link( ('baz','faz'), ('hosts','woot') )

            # the value '1.2.3.4' only occurs once in memory

        Notes:

            * For now this is best used to ref mutable types

        '''
        valu = self.get(dest)
        self.set(path,valu)

    def items(self, path):
        '''
        Traverse to a path and return (name,valu) tuples.

        Example:

            for name,valu in tree.items( ('foo','bar','baz') ):
                stuff()

        '''
        node = self._getNode(path)
        if node == None:
            return ()

        return list(node.items())

    def keys(self, path):
        '''
        Return a list of sub keys for the given path.

        Example:

            for name in tree.keys( ('foo','bar','baz') ):
                stuff(name)

        '''
        node = self._getNode(path)
        return list(node.keys())

    def subtree(self, path):
        node = self.root
        for p in path:
            node = node[p]

        return SubTree(self,path)

    def _getParentNode(self, path):
        node = self.root
        for p in path[:-1]:
            node = node.get(p)
            if node == None:
                return None,None
        return node,path[-1]

    def _initParentNode(self, path):
        node = self.root
        for p in path[:-1]:
            node = node[p]
        return node,path[-1]

    def _getNode(self, path):
        node = self.root
        for p in path:
            node = node.get(p)
            if node == None:
                return None
        return node


class SubTree(PathTree):
    '''
    A SubTree represents part of a PathTree.

    '''
    def __init__(self, realtree, realpath):
        root = realtree._getNode(realpath)
        PathTree.__init__(self, root=root)

        self.realpath = realpath
        self.realtree = realtree

    # shunt writes back up to the parent

    def set(self, path, valu):
        realpath = self.realpath + path
        return self.realtree.set(realpath,valu)

    def pop(self, path):
        realpath = self.realpath + path
        return self.realtree.pop(realpath)

    def update(self, path, x):
        realpath = self.realpath + path
        return self.realtree.update(realpath, x)

    def extend(self, path, x):
        realpath = self.realpath + path
        return self.realtree.extend(realpath, x)

    def subtree(self, path):
        realpath = self.realpath + path
        return SubTree( self.realtree, realpath )


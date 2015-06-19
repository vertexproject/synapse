import io
import unittest

import synapse.pathtree as s_pathtree

class PathTreeTest(unittest.TestCase):

    def test_pathtree_tree(self):

        tree = s_pathtree.PathTree()

        key1 = ('asdf','qwer','poiu')
        key2 = ('asdf','qwer',';lkj')
        key3 = ('asdf','qwer','.,mn')

        tree.set( key1, 20 )
        tree.set( key2, 30 )

        self.assertIsNone( tree.get( key3 ) )

        self.assertEqual( tree.get(key1), 20 )
        self.assertEqual( tree.get(key2), 30 )

        keys = tree.get( ('asdf','qwer') )
        keys.sort()

        self.assertListEqual( keys, [';lkj','poiu'] )

        key4 = ('foo','bar')
        key5 = ('foo','baz')

        tree.append( key4, 10 )
        self.assertSequenceEqual( tree.get(key4), [10,] )

        tree.append( key4, 20 )
        self.assertSequenceEqual( tree.get(key4), [10,20] )

        tree.extend( key5, [10] )
        self.assertSequenceEqual( tree.get(key5), [10] )

        tree.extend( key5, [20] )
        self.assertSequenceEqual( tree.get(key5), [10,20] )

        tree.pop(key5)

        self.assertIsNone( tree.get(key5) )

        key6 = ('baz','faz')

        tree.link( key6, key4 )

        self.assertSequenceEqual( tree.get(key6), [10,20] )

        self.assertEqual( len(tree.items( ('asdf','qwer') )), 2 )

    def test_pathtree_subtree(self):

        tree = s_pathtree.PathTree()
        tree.set( ('foo','bar','baz'), 30 )

        subt = tree.subtree( ('foo',) )

        self.assertEqual( subt.get( ('bar','baz') ), 30 )

        subt.set( ('bar','baz'), 40 )

        self.assertEqual( subt.get( ('bar','baz') ), 40 )
        self.assertEqual( tree.get( ('foo','bar','baz') ), 40 )

    def test_pathtree_saveload(self):

        fd = io.BytesIO()
        tree = s_pathtree.PathTree(statefd=fd)

        key1 = ('foo','bar','baz')
        key2 = ('foo','bar','zaz')

        tree.set( key1, 100 )
        tree.extend(key2,[1,2,3,4])

        tree.synFini()

        fd.seek(0)

        tree = s_pathtree.PathTree(statefd=fd)
        self.assertEqual( tree.get(key1), 100 )
        self.assertSequenceEqual( tree.get(key2), [1,2,3,4])

    def test_pathtree_treenode(self):
        fd = io.BytesIO()
        tree = s_pathtree.PathTree(statefd=fd)

        key1 = ('foo','bar','baz')
        node = tree.node(key1) 

        node.set('woot',10)
        self.assertEqual( tree.get( key1 + ('woot',)), 10 )
        tree.synFini()

        fd.seek(0)
        tree = s_pathtree.PathTree(statefd=fd)

        self.assertEqual( tree.get( key1 + ('woot',)), 10 )
        tree.synFini()


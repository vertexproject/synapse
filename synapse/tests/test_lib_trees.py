
import synapse.tests.utils as s_t_utils

import synapse.lib.trees as s_trees

class TreeTest(s_t_utils.SynTest):

    def test_lib_tree_interval(self):
        ivals = (
            ((-30, 50), {'name': 'foo'}),
            ((30, 100), {'name': 'bar'}),
            ((80, 100), {'name': 'baz'}),
        )

        itree = s_trees.IntervalTree(ivals)

        #import pprint
        #pprint.pprint(itree.root)

        # test a multi-level overlap
        names = [ival[1].get('name') for ival in itree.get(32)]
        self.eq(names, ['foo', 'bar'])

        # 90 ends up as a center in the tree...
        names = [ival[1].get('name') for ival in itree.get(90)]
        self.eq(names, ['bar', 'baz'])

        # test an exact overlap on min
        names = [ival[1].get('name') for ival in itree.get(80)]
        self.eq(names, ['bar', 'baz'])

        # test an exact overlap on max
        names = [ival[1].get('name') for ival in itree.get(100)]
        self.eq(names, ['bar', 'baz'])

        self.eq(itree.get(-31), [])
        self.eq(itree.get(101), [])
        self.eq(itree.get(0xffffffff), [])

    def test_tree_base(self):
        tree = s_trees.Tree()
        tree.put(('foo', 'bar'), 'hehe')
        tree.put(('foo', 'bar', 'baz'), 'haha')

        self.eq('hehe', tree.get(('foo', 'bar')))
        self.eq('haha', tree.get(('foo', 'bar', 'baz')))
        self.eq('hehe', tree.first(('foo', 'bar', 'baz')))

        self.eq('hehe', tree.first(('foo', 'bar', 'baz')))

        self.none(tree.get(('foo', 'bar', 'baz', 'faz')))
        self.eq('haha', tree.last(('foo', 'bar', 'baz', 'faz')))

        self.none(tree.get(('fake', 'newp')))
        self.none(tree.first(('fake', 'newp')))

    def test_tree_last(self):

        tree = s_trees.Tree()

        tree.put(('foo', ), True)
        tree.put(('foo', 'bar'), False)

        self.true(tree.last(('foo', )))
        self.true(tree.last(('foo', 'baz')))
        self.false(tree.last(('foo', 'bar')))

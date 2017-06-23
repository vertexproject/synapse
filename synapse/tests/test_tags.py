import unittest

import synapse.cortex as s_cortex
import synapse.lib.tags as s_tags

from synapse.tests.common import *

class TagTest(SynTest):

    def test_aspect_iter_up(self):
        tags = tuple( s_tags.iterTagUp('foo.bar.baz') )
        self.assertEqual( tags, ('foo.bar.baz','foo.bar','foo') )

    def test_aspect_iter_down(self):
        tags = tuple( s_tags.iterTagDown('foo.bar.baz') )
        self.assertEqual( tags, ('foo','foo.bar','foo.bar.baz') )

    def test_aspect_adddel(self):
        core = s_cortex.openurl('ram:///')
        tufo = core.formTufoByProp('foo','bar')
        tufo = core.addTufoTag(tufo, 'baz.faz.gaz', asof=None)

        self.nn( tufo[1].get('#baz') )
        self.nn( tufo[1].get('#baz.faz') )
        self.nn( tufo[1].get('#baz.faz.gaz') )

        tufos = core.getTufosByTag('baz.faz', form='foo')

        self.assertEqual( len(tufos), 1 )

        tufo = core.delTufoTag(tufo,'baz.faz')

        tufos = core.getTufosByTag('baz.faz', form='foo')
        self.assertEqual( len(tufos), 0 )

        tufos = core.getTufosByTag('baz.faz.gaz', form='foo')
        self.assertEqual( len(tufos), 0 )

    def test_aspect_bytag(self):
        bytag = s_tags.ByTag()

        bytag.put('foo0',('foos.foo0','bar.baz'))
        bytag.put('foo1',('foos.foo1','bar.faz'))

        vals = tuple( sorted( bytag.get('bar') ) )
        self.assertEqual( vals, ('foo0','foo1') )

        vals = tuple( sorted( bytag.get('foos') ) )
        self.assertEqual( vals, ('foo0','foo1') )

        vals = tuple( sorted( bytag.get('foos.foo0') ) )
        self.assertEqual( vals, ('foo0',) )

        vals = tuple( sorted( bytag.get('newp.foo0') ) )
        self.assertEqual( vals, () )

        bytag.pop('foo0')

        vals = tuple( sorted( bytag.get('foos') ) )
        self.assertEqual( vals, ('foo1',) )

    def test_tags_subs(self):
        tufo = ('lolz',{'tufo:form':'woot'})
        self.assertFalse( s_tags.getTufoSubs(tufo,'mytag') )

        tufo = ('lolz',{'tufo:form':'woot', '#mytag': 1})
        self.assertTrue( s_tags.getTufoSubs(tufo,'mytag') )

    def test_tags_rows(self):
        tufo = ('lolz',{'tufo:form':'woot'})
        self.assertTrue( s_tags.genTufoRows(tufo,'mytag') )

        tufo = ('lolz',{'tufo:form':'woot', '#mytag': 1})
        self.assertFalse( s_tags.genTufoRows(tufo,'mytag') )

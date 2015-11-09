import unittest

import synapse.cortex as s_cortex
import synapse.aspects as s_aspects

class AspectTest(unittest.TestCase):

    def test_aspect_iter_up(self):
        tags = tuple( s_aspects.iterTagUp('foo.bar.baz') )
        self.assertEqual( tags, ('foo.bar.baz','foo.bar','foo') )

    def test_aspect_iter_down(self):
        tags = tuple( s_aspects.iterTagDown('foo.bar.baz') )
        self.assertEqual( tags, ('foo','foo.bar','foo.bar.baz') )

    def test_aspect_adddel(self):
        core = s_cortex.openurl('ram:///')
        tufo = core.formTufoByProp('foo','bar')
        tufo = core.addTufoTag(tufo, 'baz.faz.gaz', valu=None)

        tags = s_aspects.getTufoTags(tufo)

        self.assertIsNotNone( tags.get('baz') )
        self.assertIsNotNone( tags.get('baz.faz') )
        self.assertIsNotNone( tags.get('baz.faz.gaz') )

        tufos = core.getTufosByTag('foo','baz.faz')
        self.assertEqual( len(tufos), 1 )

        tufo = core.delTufoTag(tufo,'baz.faz')

        tufos = core.getTufosByTag('foo','baz.faz')
        self.assertEqual( len(tufos), 0 )

        tufos = core.getTufosByTag('foo','baz.faz.gaz')
        self.assertEqual( len(tufos), 0 )

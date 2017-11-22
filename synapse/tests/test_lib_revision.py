from synapse.tests.common import *

import synapse.lib.revision as s_revision

class Revr(s_revision.Revisioner):

    @s_revision.step('0.0.0', '0.0.2')
    def _doRev0(self, x, y=10):
        x['foo'] = y

    @s_revision.step('0.0.2', '0.0.3')
    def _addBarInfo(self, x, y=10):
        x['bar'] = 20

class RevTest(SynTest):

    def test_revision_er(self):

        revr = Revr()

        info = {}

        v0 = (0, 0, 0)
        path = tuple(revr.runRevPath(v0, info))

        self.eq(info.get('foo'), 10)
        self.eq(info.get('bar'), 20)
        self.eq(path, ((0, 0, 2), (0, 0, 3)))

        def genexc():
            for v in revr.runRevPath((0, 1, 0)):
                pass

        self.eq(revr.chop('1.2.3'), (1, 2, 3))
        self.eq(revr.repr((1, 2, 3)), '1.2.3')
        self.raises(s_revision.NoRevPath, genexc)

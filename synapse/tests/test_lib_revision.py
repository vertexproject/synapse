# stdlib
# third party code
# custom code
import synapse.exc as s_exc
import synapse.tests.common as s_test
import synapse.lib.revision as s_revision

class Revr(s_revision.Revisioner):

    @s_revision.step('0.0.0', '0.0.2')
    def _doRev0(self, x, y=10):
        x['foo'] = y

    @s_revision.step('0.0.2', '0.0.3')
    def _addBarInfo(self, x, y=10):
        x['bar'] = 20

class RevTest(s_test.SynTest):

    def test_revision_er(self):

        revr = Revr()

        # Ensure that pre-revision events are fired
        mesgs = []
        def onRev(mesg):
            mesgs.append(mesg)

        revr.on('syn:revisioner:rev', onRev)

        info = {}

        v0 = (0, 0, 0)
        path = tuple(revr.runRevPath(v0, info))

        self.eq(info.get('foo'), 10)
        self.eq(info.get('bar'), 20)
        self.eq(path, ((0, 0, 2), (0, 0, 3)))

        def genexc():
            for v in revr.runRevPath((0, 1, 0)):
                pass

        # Ensure the revision path to self.maxver is empty
        self.eq(revr.getRevPath((0, 0, 3)), [])
        # But the path to maxver is not empty
        self.nn(revr.getRevPath((0, 0, 0)))

        self.eq(revr.chop('1.2.3'), (1, 2, 3))
        self.eq(revr.repr((1, 2, 3)), '1.2.3')
        self.raises(s_exc.NoRevPath, genexc)

        # Ensure messages were fired and captured by our handler
        self.len(2, mesgs)
        self.eq(mesgs[0][0], 'syn:revisioner:rev')
        self.eq(mesgs[0][1].get('name'), 'Revr')
        self.eq(mesgs[0][1].get('v1'), (0, 0, 0))
        self.eq(mesgs[0][1].get('v2'), (0, 0, 2))

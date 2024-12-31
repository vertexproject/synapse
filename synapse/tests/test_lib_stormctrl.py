import pickle

import synapse.lib.stormctrl as s_stormctrl

import synapse.tests.utils as s_t_utils

class StormctrlTest(s_t_utils.SynTest):
    def test_basic(self):

        # Classes inherit as expected
        self.isinstance(s_stormctrl.StormReturn(), s_stormctrl.StormCtrlFlow)
        self.isinstance(s_stormctrl.StormExit(), s_stormctrl.StormCtrlFlow)
        self.isinstance(s_stormctrl.StormBreak(), s_stormctrl.StormCtrlFlow)
        self.isinstance(s_stormctrl.StormContinue(), s_stormctrl.StormCtrlFlow)
        self.isinstance(s_stormctrl.StormStop(), s_stormctrl.StormCtrlFlow)

        # Subtypes are noted as well
        self.isinstance(s_stormctrl.StormBreak(), s_stormctrl.StormLoopCtrl)
        self.isinstance(s_stormctrl.StormContinue(), s_stormctrl.StormLoopCtrl)
        self.isinstance(s_stormctrl.StormStop(), s_stormctrl.StormGenrCtrl)

        # control flow and exist constructs inherit from the SynErrMixin
        # return does not to keep it thin. it is used often.
        self.isinstance(s_stormctrl.StormExit(), s_stormctrl._SynErrMixin)
        self.isinstance(s_stormctrl.StormBreak(), s_stormctrl._SynErrMixin)
        self.isinstance(s_stormctrl.StormContinue(), s_stormctrl._SynErrMixin)
        self.isinstance(s_stormctrl.StormStop(), s_stormctrl._SynErrMixin)
        self.false(isinstance(s_stormctrl.StormReturn(), s_stormctrl._SynErrMixin))

        # The base class cannot be used on its own.
        with self.raises(NotImplementedError):
            s_stormctrl.StormCtrlFlow()

        # The _SynErrMixin classes have several methods that let us treat
        # instance of them like SynErr exceptions.
        e = s_stormctrl.StormExit(mesg='words', foo='bar')
        self.eq(e.get('foo'), 'bar')
        self.eq(e.items(), {'mesg': 'words', 'foo': 'bar'})
        self.eq("StormExit: foo='bar' mesg='words'", str(e))
        e.set('hehe', 1234)
        e.set('foo', 'words')
        self.eq("StormExit: foo='words' hehe=1234 mesg='words'", str(e))

        e.setdefault('defv', 1)
        self.eq("StormExit: defv=1 foo='words' hehe=1234 mesg='words'", str(e))

        e.setdefault('defv', 2)
        self.eq("StormExit: defv=1 foo='words' hehe=1234 mesg='words'", str(e))

        e.update({'foo': 'newwords', 'bar': 'baz'})
        self.eq("StormExit: bar='baz' defv=1 foo='newwords' hehe=1234 mesg='words'", str(e))

        # But it does not have an errname property
        self.false(hasattr(e, 'errname'))

        # StormReturn is used to move objects around.
        e = s_stormctrl.StormReturn('weee')
        self.eq(e.item, 'weee')

    async def test_pickled_stormctrlflow(self):
        e = s_stormctrl.StormExit(mesg='words', foo='bar')
        buf = pickle.dumps(e)
        new_e = pickle.loads(buf)
        self.eq(new_e.get('foo'), 'bar')
        self.eq("StormExit: foo='bar' mesg='words'", str(new_e))

class StormCtrlFlow(Exception):
    '''
    Base class all StormCtlFlow exceptions derive from.
    '''

class _SynErrMixin:
    '''
    An exception mixin to give some control flow classes functionality like SynErr
    '''
    def __init__(self, **info):
        self.errinfo = info
        Exception.__init__(self, self._getExcMsg())

    def _getExcMsg(self):
        props = sorted(self.errinfo.items())
        displ = ' '.join(['%s=%r' % (p, v) for (p, v) in props])
        return '%s: %s' % (self.__class__.__name__, displ)

    def _setExcMesg(self):
        '''Should be called when self.errinfo is modified.'''
        self.args = (self._getExcMsg(),)

    def __setstate__(self, state):
        '''Pickle support.'''
        super(StormCtrlFlow, self).__setstate__(state)
        self._setExcMesg()

    def items(self):
        return {k: v for k, v in self.errinfo.items()}

    def get(self, name, defv=None):
        '''
        Return a value from the errinfo dict.

        Example:

            try:
                foothing()
            except SynErr as e:
                blah = e.get('blah')

        '''
        return self.errinfo.get(name, defv)

    def set(self, name, valu):
        '''
        Set a value in the errinfo dict.
        '''
        self.errinfo[name] = valu
        self._setExcMesg()

    def setdefault(self, name, valu):
        '''
        Set a value in errinfo dict if it is not already set.
        '''
        if name in self.errinfo:
            return
        self.errinfo[name] = valu
        self._setExcMesg()

    def update(self, items):
        for k, v in items.items():
            self.errinfo[k] = v
        self._setExcMesg()

class StormLoopCtrl(_SynErrMixin, Exception):
    # Control flow statements for WHILE and FOR loop control
    statement = ''

class StormGenrCtrl(_SynErrMixin, Exception):
    # Control flow statements for GENERATOR control
    statement = ''

class StormStop(StormGenrCtrl, StormCtrlFlow):
    statement = 'stop'

class StormBreak(StormLoopCtrl, StormCtrlFlow):
    statement = 'break'

class StormContinue(StormLoopCtrl, StormCtrlFlow):
    statement = 'continue'

class StormExit(_SynErrMixin, StormCtrlFlow): pass

class StormReturn(StormCtrlFlow):
    def __init__(self, item=None):
        self.item = item

class StormCtrlFlow(Exception):
    '''
    Base class all StormCtrlFlow exceptions derive from.
    '''
    def __init__(self):
        raise NotImplementedError

class _SynErrMixin(Exception):
    '''
    An exception mixin to give some control flow classes functionality like SynErr.
    '''
    def __init__(self, *args, **info):
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

    def update(self, items: dict):
        '''Update multiple items in the errinfo dict at once.'''
        self.errinfo.update(items)
        self._setExcMesg()

class StormLoopCtrl(_SynErrMixin):
    # Control flow statements for WHILE and FOR loop control
    statement = ''

class StormGenrCtrl(_SynErrMixin):
    # Control flow statements for GENERATOR control
    statement = ''

class StormStop(StormGenrCtrl, StormCtrlFlow):
    statement = 'stop'

class StormBreak(StormLoopCtrl, StormCtrlFlow):
    statement = 'break'

class StormContinue(StormLoopCtrl, StormCtrlFlow):
    statement = 'continue'

class StormExit(_SynErrMixin, StormCtrlFlow): pass

# StormReturn is kept thin since it is commonly used and just
# needs to be the container for moving an item up a frame.
class StormReturn(StormCtrlFlow):
    def __init__(self, item=None):
        self.item = item

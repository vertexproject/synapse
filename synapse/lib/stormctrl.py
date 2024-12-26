class StormCtrlFlow(Exception):
    def __init__(self, item=None, **info):
        self.item = item
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

class StormLoopCtrl(Exception):
    # Control flow statements for WHILE and FOR loop control
    statement = ''

class StormGenrCtrl(Exception):
    # Control flow statements for GENERATOR control
    statement = ''

class StormExit(StormCtrlFlow): pass
class StormStop(StormCtrlFlow, StormGenrCtrl):
    statement = 'stop'
class StormBreak(StormCtrlFlow, StormLoopCtrl):
    statement = 'break'
class StormReturn(StormCtrlFlow): pass
class StormContinue(StormCtrlFlow, StormLoopCtrl):
    statement = 'continue'

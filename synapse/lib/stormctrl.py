class StormCtrlFlow(Exception):
    def __init__(self, item=None):
        self.item = item

class StormLoopCtrl(Exception):
    # Control flow statements for WHILE and FOR loop control
    _statement = ''

class StormGenrCtrl(Exception):
    # Control flow statements for GENERATOR control
    _statement = ''

class StormExit(StormCtrlFlow): pass
class StormStop(StormCtrlFlow, StormGenrCtrl):
    _statement = 'stop'
class StormBreak(StormCtrlFlow, StormLoopCtrl):
    _statement = 'break'
class StormReturn(StormCtrlFlow): pass
class StormContinue(StormCtrlFlow, StormLoopCtrl):
    _statement = 'continue'

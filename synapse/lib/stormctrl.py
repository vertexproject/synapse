class StormCtrlFlow(Exception):
    def __init__(self, item=None):
        self.item = item

class StormLoopCtrl:
    # Control flow statements for WHILE and FOR loop control.
    pass

class StormExit(StormCtrlFlow): pass
class StormStop(StormCtrlFlow): pass
class StormBreak(StormCtrlFlow, StormLoopCtrl): pass
class StormReturn(StormCtrlFlow): pass
class StormContinue(StormCtrlFlow, StormLoopCtrl): pass

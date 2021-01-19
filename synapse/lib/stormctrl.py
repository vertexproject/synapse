class StormCtrlFlow(Exception):
    def __init__(self, item=None):
        self.item = item

class StormExit(StormCtrlFlow): pass
class StormBreak(StormCtrlFlow): pass
class StormReturn(StormCtrlFlow): pass
class StormContinue(StormCtrlFlow): pass

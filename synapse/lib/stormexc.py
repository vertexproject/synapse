class StormCtrlFlow(Exception):
    def __init__(self, item=None):
        self.item = item

class StormBreak(StormCtrlFlow):
    pass

class StormContinue(StormCtrlFlow):
    pass

class StormReturn(StormCtrlFlow):
    pass

class StormExit(StormCtrlFlow):
    pass

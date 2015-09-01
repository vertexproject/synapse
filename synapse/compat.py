'''
A module to isolate python version compatibility filth.
'''
import sys
import time
import base64

major = sys.version_info.major
minor = sys.version_info.minor
micro = sys.version_info.micro

version = (major,minor,micro)

if version < (3,0,0):
    import Queue as queue
    import sched as sched27

    class FakeSched(sched27.scheduler):
        def enter(self, delay, prio, meth, args, kwargs):
            def action():
                return meth(*args,**kwargs)
            return sched27.scheduler.enter(self, delay, prio, action, ())

    class FakeSchedMod:
        def scheduler(self):
            return FakeSched(time.time,time.sleep)

    sched = FakeSchedMod()

    def enbase64(s):
        return s.encode('base64')

    def debase64(s):
        return s.decode('base64')

    def isstr(s):
        return type(s) in (str,unicode)

else:
    import sched
    import queue

    def enbase64(b):
        return base64.b64encode(b).decode('utf8')

    def debase64(b):
        return base64.b64decode( b.encode('utf8') )

    def isstr(s):
        return isinstance(s,str)

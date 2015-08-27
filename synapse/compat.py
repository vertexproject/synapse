'''
A module to isolate python version compatibility filth.
'''
import sys
import time

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

    from urlparse import urlparse, parse_qsl

else:
    import sched
    import queue

    from urllib.parse import urlparse, parse_qsl

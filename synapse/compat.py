from __future__ import absolute_import,unicode_literals
'''
A module to isolate python version compatibility filth.
'''
import sys
import time
import base64
import collections

major = sys.version_info.major
minor = sys.version_info.minor
micro = sys.version_info.micro

version = (major,minor,micro)

if version < (3,0,0):
    import select

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

    class FakeKey:
        def __init__(self, sock):
            self.fileobj = sock

    class FakeSelector:

        def __init__(self):
            self.socks = {}

        def register(self, sock, mask):
            self.socks[sock] = mask

            def unreg():
                self.unregister(sock)

            sock.onfini( unreg )

        def unregister(self, sock):
            self.socks.pop(sock,None)

        def select(self, timeout=None):
            rlist = []
            wlist = []
            xlist = []

            for sock,mask in self.socks.items():
                if sock.isfini:
                    continue

                xlist.append(sock)
                if mask & FakeSelMod.EVENT_READ:
                    rlist.append(sock)

                if mask & FakeSelMod.EVENT_WRITE:
                    wlist.append(sock)

            try:

                rlist,wlist,xlist = select.select(rlist,wlist,xlist,timeout)
            except select.error as e:
                # mask "bad file descriptor" race and go around again...
                return []

            ret = collections.defaultdict(int)
            for sock in rlist:
                ret[sock] |= FakeSelMod.EVENT_READ

            for sock in wlist:
                ret[sock] |= FakeSelMod.EVENT_WRITE

            return [ (FakeKey(sock),mask) for sock,mask in ret.items() ]

        def close(self):
            pass

    class FakeSelMod:
        EVENT_READ = 1
        EVENT_WRITE = 2
        def DefaultSelector(self):
            return FakeSelector()

    sched = FakeSchedMod()
    selectors = FakeSelMod()

    def enbase64(s):
        return s.encode('base64')

    def debase64(s):
        return s.decode('base64')

    def isstr(s):
        return type(s) in (str,unicode)

else:
    import sched
    import queue
    import selectors

    def enbase64(b):
        return base64.b64encode(b).decode('utf8')

    def debase64(b):
        return base64.b64decode( b.encode('utf8') )

    def isstr(s):
        return isinstance(s,str)

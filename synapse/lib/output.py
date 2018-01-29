'''
Tools for easily hookable output from cli-like tools.
'''
import io
import sys

import synapse.eventbus as s_eventbus

class OutPut:

    def __init__(self):
        pass

    def printf(self, mesg, addnl=True):

        if addnl:
            mesg += '\n'

        return self._rawOutPut(mesg)

    def _rawOutPut(self, mesg):
        sys.stdout.write(mesg)

class OutPutFd(OutPut):

    def __init__(self, fd, enc='utf8'):
        OutPut.__init__(self)
        self.fd = fd
        self.enc = enc

    def _rawOutPut(self, mesg):
        self.fd.write(mesg.encode(self.enc))

class OutPutBytes(OutPutFd):

    def __init__(self):
        OutPutFd.__init__(self, io.BytesIO())

class OutPutStr(OutPut):

    def __init__(self):
        OutPut.__init__(self)
        self.mesgs = []

    def _rawOutPut(self, mesg):
        self.mesgs.append(mesg)

    def __str__(self):
        return ''.join(self.mesgs)

class OutPutBus(OutPut, s_eventbus.EventBus):
    def __init__(self):
        OutPut.__init__(self)
        s_eventbus.EventBus.__init__(self)

    def _rawOutPut(self, mesg):
        self.fire('syn:output:print', mesg=mesg)

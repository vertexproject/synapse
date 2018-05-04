'''
Tools for easily hookable output from cli-like tools.
'''
import io
import sys

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

stdout = OutPut()

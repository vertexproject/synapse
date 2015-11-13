
# FIXME: work in progress

class File:
    '''
    A File facilitates atomic seek/read operations.
    '''
    def __init__(self, fd):
        self.fd = fd
        self.off = 0
        self.lock = threading.Lock()

        fd.seek(0,os.SEEK_END)

    def seekAndRead(self, off, size):
        '''
        Seek and read as an atomic operation.
        '''
        with self.lock:
            if self.off != off:
                self.fd.seek(off)

            byts = self.fd.read(size)
            self.off = off + len(byts)
            return byts

    def seekAndWrite(self, byts):
        with self.lock:
            size = len(byts)
            if self.off != self.size:
                self.fd.seek(0,os.SEEK_END)

            self.fd.write(byts)

            self.size += size
            self.off = self.size

    def seekAndTell(self):
        '''
        Seek to the end and return tell() as an atomic operation.
        '''
        with self.lock:
            self.fd.seek(0,os.SEEK_END)
            return self.fd.tell()


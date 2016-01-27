import os
import hashlib
import tempfile
import threading

from synapse.common import *

tenmegs = 10000000

# FIXME: work in progress!

class HashSet:

    def __init__(self):
        self.hashes = [
            ('md5',hashlib.md5()),
            ('sha1',hashlib.sha1()),
            ('sha256',hashlib.sha256()),
            ('sha512',hashlib.sha512()),
        ]

class UpFile:

    def __init__(self, fd):
        self.size = 0
        self.fd = fd
        self.md5 = hashlib.md5()
        self.sha1 = hashlib.sha1()
        self.sha256 = hashlib.sha256()
        self.hashobjs = [
            ('md5',hashlib.md5()),
            ('sha1',hashlib.sha1()),
            ('sha256',hashlib.sha256()),
            ('sha512',hashlib.sha512()),
        ]

    def write(self, byts):
        self.size += len(byts)
        [ h.update(byts) for (a,h) in self.hashobjs ]
        self.fd.write(byts)

    def hashes(self):
        return [ (algo,h.hexdigest()) for (algo,h) in self.hashobjs ]

    def dump(self, fd):
        '''
        Dump <len64><bytes> to the specified fd.
        '''
        hdr = struct.pack('<Q',self.size)
        fd.write(fd)

        self.fd.seek(0)

        byts = self.fd.read(tenmegs)
        while byts:
            fd.write(byts)
            byts = self.fd.read(tenmegs)

        self.fd.close()

class Axon(EventBus):

    def __init__(self, core, fd):
        EventBus.__init__(self)

        self.lock = threading.Lock()

        #axon:spoolsize = 10000000

        fd.seek(0, os.SEEK_END)

        self.core = core
        self.offset = fd.tell()

        model = core.genDataModel()

        model.addTufoType('file')
        model.addTufoProp('file:mime', defval='unknown/unknown')

        model.addTufoProp('file:hash:md5', ptype='hash:md5')
        model.addTufoProp('file:hash:sha1', ptype='hash:sha1')
        model.addTufoProp('file:hash:sha256', ptype='hash:sha256')

        self.axfo = core.formTufoByProp('axon:self')
        self.curator = s_session.Curator(core)

    def getAxonProp(self, prop):
        return self.axfo[1].get(prop)

    def setAxonProp(self, prop, valu):
        self.axfo[1][prop] = valu
        self.core.setTufoProp(self.axfo, prop, valu)

    def hasFileHash(self, algo, valu):
        rows = self.core.getRowsByProp('file:hash:%s' % algo, valu)
        return len(rows) != 0

    #def getFileTufo(self, 

    def initUpFile(self):
        '''
        Initialize a new file upload session.

        Example:

            sid = axon.initUpFile()

        '''
        sess = self.curator.new()
        fd = tempfile.SpooledTemporaryFile(tenmegs)
        sess.local['upfile'] = UpFile(fd)
        return sess.sid

    def writeUpFile(self, sid, byts):
        '''
        Send bytes to a file upload session.

        Example:

            axon.writeUpFile(sid,byts)

        '''
        sess = self.curator.getSessBySid(sid)
        if sess == None:
            raise NoSuchSess(sid)

        upfile = sess.local.get('upfile')
        if upfile == None:
            raise NoSuch('upfile')

        upfile.write(byts)

    def finiUpFile(self, sid):
        '''
        Finalize a file upload session and save.

        Example:

            axon.finiUpFile(sid)

        '''
        sess = self.curator.getSessBySid(sid)
        if sess == None:
            raise NoSuchSess(sid)

        upfile = sess.local.pop('upfile',None)
        if upfile == None:
            raise NoSuch('upfile')

        with self.fdlock:
            self.fd.seek(0,os.SEEK_END)
            upfile.dump(self.fd)

    def seekAndRead(self, off, size):
        pass

import socket

from contextlib import contextmanager

from synapse.tests.common import *

import synapse.lib.certdir as s_certdir

class CertDirTest(SynTest):

    @contextmanager
    def getCertDir(self):
        # create a temp folder and make it a cert dir
        with self.getTestDir() as dirname:
            cdir = s_certdir.CertDir(path=dirname)
            yield cdir

    def test_certdir_ca(self):
        with self.getCertDir() as cdir:
            cdir.genCaCert('syntest')

            self.nn( cdir.getCaCert('syntest') )
            self.none( cdir.getCaCert('newpnewp') )

            self.true( cdir.isCaCert('syntest') )
            self.false( cdir.isCaCert('newpnewp') )

    def test_certdir_user(self):
        with self.getCertDir() as cdir:
            cdir.genCaCert('syntest')
            cdir.genUserCert('visi@vertex.link',signas='syntest')

            self.nn( cdir.getUserCert('visi@vertex.link') )
            self.none( cdir.getUserCert('newpnewp') )

            self.true( cdir.isUserCert('visi@vertex.link') )
            self.false( cdir.isUserCert('newpnewp') )

    def test_certdir_host(self):
        with self.getCertDir() as cdir:
            cdir.genCaCert('syntest')
            cdir.genHostCert('visi.vertex.link',signas='syntest')

            self.nn( cdir.getHostCert('visi.vertex.link') )
            self.none( cdir.getHostCert('newpnewp') )

            self.true( cdir.isHostCert('visi.vertex.link') )
            self.false( cdir.isHostCert('newpnewp') )

    def test_certdir_hostca(self):
        with self.getCertDir() as cdir:
            cdir.genCaCert('syntest')
            cdir.genHostCert('visi.vertex.link',signas='syntest')

            self.nn( cdir.getHostCaPath('visi.vertex.link') )
            self.none( cdir.getHostCaPath('newp.newp.newp') )

    def test_certdir_userca(self):
        with self.getCertDir() as cdir:
            cdir.genCaCert('syntest')
            cdir.genUserCert('visi@vertex.link',signas='syntest')

            self.eq( cdir.getUserForHost('visi','host.vertex.link'), 'visi@vertex.link')

            self.none( cdir.getUserCaPath('visi@newp.newp') )
            self.none( cdir.getUserCaPath('visi@host.vertex.link') )

    def test_certdir_hostcsr(self):
        with self.getCertDir() as cdir:
            cdir.genCaCert('syntest')
            cdir.genHostCsr('visi.vertex.link')
            path = cdir.getPathJoin('hosts','visi.vertex.link.csr')
            xcsr = cdir._loadCsrPath(path)
            cdir.signHostCsr(xcsr,'syntest')


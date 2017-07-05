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

            self.nn(cdir.getCaCert('syntest'))
            self.none(cdir.getCaCert('newpnewp'))

            self.true(cdir.isCaCert('syntest'))
            self.false(cdir.isCaCert('newpnewp'))

    def test_certdir_user(self):
        with self.getCertDir() as cdir:
            cdir.genCaCert('syntest')
            cdir.genUserCert('visi@vertex.link', signas='syntest')

            self.nn(cdir.getUserCert('visi@vertex.link'))
            self.none(cdir.getUserCert('newpnewp'))

            self.true(cdir.isUserCert('visi@vertex.link'))
            self.true(cdir.isClientCert('visi@vertex.link'))
            self.false(cdir.isUserCert('newpnewp'))
            self.false(cdir.isClientCert('newpnewp'))

    def test_certdir_host(self):
        with self.getCertDir() as cdir:
            cdir.genCaCert('syntest')
            cdir.genHostCert('visi.vertex.link', signas='syntest', sans='DNS:vertex.link,DNS:visi.vertex.link,DNS:vertex.link')

            self.none(cdir.getHostCert('newpnewp'))
            self.false(cdir.isHostCert('newpnewp'))

            self.true(cdir.isHostCert('visi.vertex.link'))
            cert = cdir.getHostCert('visi.vertex.link')
            self.nn(cert)
            self.eq(cert.get_extension_count(), 5)
            self.eq(cert.get_extension(4).get_short_name(), b'subjectAltName')
            self.eq(cert.get_extension(4).get_data(), b'0\x1f\x82\x0bvertex.link\x82\x10visi.vertex.link')  # ASN.1 encoded subjectAltName data

        # Test SAN is valid when not specified in kwargs
        with self.getCertDir() as cdir:
            cdir.genCaCert('syntest')
            cdir.genHostCert('visi.vertex.link', signas='syntest')

            self.true(cdir.isHostCert('visi.vertex.link'))
            cert = cdir.getHostCert('visi.vertex.link')
            self.nn(cert)
            self.eq(cert.get_extension_count(), 5)
            self.eq(cert.get_extension(4).get_short_name(), b'subjectAltName')
            self.eq(cert.get_extension(4).get_data(), b'0\x12\x82\x10visi.vertex.link')  # ASN.1 encoded subjectAltName data

    def test_certdir_hostca(self):
        with self.getCertDir() as cdir:
            cdir.genCaCert('syntest')
            cdir.genHostCert('visi.vertex.link', signas='syntest')

            self.nn(cdir.getHostCaPath('visi.vertex.link'))
            self.none(cdir.getHostCaPath('newp.newp.newp'))

    def test_certdir_userca(self):
        with self.getCertDir() as cdir:
            cdir.genCaCert('syntest')
            cdir.genUserCert('visi@vertex.link', signas='syntest')

            self.eq(cdir.getUserForHost('visi', 'host.vertex.link'), 'visi@vertex.link')

            self.none(cdir.getUserCaPath('visi@newp.newp'))
            self.none(cdir.getUserCaPath('visi@host.vertex.link'))

    def test_certdir_hostcsr(self):
        with self.getCertDir() as cdir:
            cdir.genCaCert('syntest')
            cdir.genHostCsr('visi.vertex.link')
            path = cdir.getPathJoin('hosts', 'visi.vertex.link.csr')
            xcsr = cdir._loadCsrPath(path)
            cdir.signHostCsr(xcsr, 'syntest')

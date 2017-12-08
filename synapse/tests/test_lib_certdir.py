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

            cert = cdir.getCaCert('syntest')

            # Make sure the ca cert was generated with the expected number of bits
            self.eq(cert.get_pubkey().bits(), cdir.crypto_numbits)

            # Make sure the ca cert was generated with the correct version number
            self.eq(cert.get_version(), 2)

    def test_certdir_user(self):
        with self.getCertDir() as cdir:
            cdir.genCaCert('syntest')
            cdir.genUserCert('visi@vertex.link', signas='syntest')

            self.none(cdir.getUserCert('newpnewp'))
            self.none(cdir.getUserKey('newpnewp'))
            self.none(cdir.getClientCert('newpnewp'))
            self.false(cdir.isUserCert('newpnewp'))
            self.false(cdir.isClientCert('newpnewp'))

            self.nn(cdir.getUserCert('visi@vertex.link'))
            self.nn(cdir.getUserKey('visi@vertex.link'))
            self.nn(cdir.getClientCert('visi@vertex.link'))

            self.true(cdir.isUserCert('visi@vertex.link'))
            self.true(cdir.isClientCert('visi@vertex.link'))

            key = cdir.getUserKey('visi@vertex.link')
            cert = cdir.getUserCert('visi@vertex.link')

            # Make sure the certs were generated with the expected number of bits
            self.eq(key.bits(), cdir.crypto_numbits)
            self.eq(cert.get_pubkey().bits(), cdir.crypto_numbits)

            # Make sure the certs were generated with the correct version number
            self.eq(cert.get_version(), 2)

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

            # Make sure the cert was generated with the correct version number
            self.eq(cert.get_version(), 2)

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

            # Make sure the ca cert was generated with the correct version number
            self.eq(cert.get_version(), 2)

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

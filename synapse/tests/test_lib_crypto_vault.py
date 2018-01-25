import synapse.lib.crypto.vault as s_vault

from synapse.tests.common import *

class VaultTest(SynTest):

    def test_lib_crypto_vault(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'vault.lmdb')

            vault = s_vault.Vault(path)

            self.none(vault.getRsaKey('visi'))

            self.nn(vault.genRsaKey('visi'))
            self.nn(vault.getRsaKey('visi'))

            rkey, cert = vault.genUserCert('visi@vertex.link')

            vault.addSignerCert(cert)

            self.true(vault.isValidCert(cert))

            tokn = s_msgpack.un(cert[0])

            # make sure we can add/get a signer cert
            signer = vault.getSignerCert(tokn[0])

            self.eq(signer[0], cert[0])
            self.none(vault.getSignerCert('asdf'))

            # revoke our self-signed as a signer...
            vault.delSignerCert(cert)
            self.false(vault.isValidCert(cert))

            auth = vault.getUserAuth('visi@vertex.link')

            # create another vault to test save/load.
            with self.getTestDir() as dirn:

                path = os.path.join(dirn, 'vault.lmdb')
                newvault = s_vault.Vault(path)

                newvault.addUserAuth(auth)

                cert = newvault.getUserCert('visi@vertex.link')

                self.nn(newvault.getRsaKey('visi@vertex.link'))
                self.nn(newvault.getUserCert('visi@vertex.link'))

                self.false(newvault.isValidCert(cert))

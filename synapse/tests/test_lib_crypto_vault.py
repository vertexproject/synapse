import hashlib

import synapse.lib.msgpack as s_msgpack
import synapse.lib.crypto.vault as s_vault

from synapse.tests.common import *

class VaultTest(SynTest):

    def test_lib_crypto_vault(self):

        with self.getTestDir() as dirn:

            path = os.path.join(dirn, 'vault.lmdb')

            vault = s_vault.Vault(path)

            #self.none(vault.getRsaKey('visi'))

            rkey = vault.genRsaKey()
            self.nn(rkey)

            iden = hashlib.sha256(rkey.public().save()).hexdigest()
            self.eq(iden, rkey.iden())

            root = vault.genRootCert()
            self.eq(root.iden(), vault.genRootCert().iden())

            cert = vault.genUserCert('visi@vertex.link')
            self.true(root.signed(cert))

            auth = vault.genUserAuth('visi@vertex.link')

            self.nn(s_msgpack.en(auth))

            # create another vault to test save/load.
            with self.getTestDir() as dirn:

                path = os.path.join(dirn, 'vault.lmdb')
                newvault = s_vault.Vault(path)

                newvault.addUserAuth(auth)

                cert = newvault.getUserCert('visi@vertex.link')

                self.false(newvault.isValidCert(cert))

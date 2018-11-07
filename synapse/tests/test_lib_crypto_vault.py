
import os
import threading
import multiprocessing


import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils
import synapse.lib.crypto.ecc as s_ecc
import synapse.lib.msgpack as s_msgpack
import synapse.lib.crypto.vault as s_vault

def addUserToVault(evt1, evt2, fp, user):
    '''
    Add a user to a vault, event driven.

    Args:
        evt1 (multiprocessing.Event): Event to wait for
        evt2 (multiprocessing.Event): Event to set upon completion
        fp (str):
        user (str):
    '''
    evt1.wait()
    with s_vault.shared(fp) as vlt:
        vlt.genUserCert(user)
    evt2.set()

class VaultTest(s_t_utils.SynTest):
    def test_lib_crypto_vault_cert(self):
        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'vault.lmdb')
            vault = s_vault.Vault(path)
            root = vault.genRootCert()

            self.isinstance(root.iden(), str)
            self.isinstance(root.getkey(), s_ecc.PriKey)
            self.isinstance(root.public(), s_ecc.PubKey)
            self.isinstance(root.toknbytes(), bytes)
            self.isinstance(root.dump(), bytes)

            # We can validate our root ca is self-signed
            signers = root.signers()
            self.isinstance(signers, tuple)
            self.len(1, signers)
            iden, data, sign = signers[0]
            self.true(root.verify(data + root.toknbytes(), sign))

            # Ensure that we can validate that one cert signed another.
            cert = vault.genUserCert('hehe@haha.com')
            self.true(root.signed(cert))

            # If we add a second CA, we don't sign new certs with that CA.
            path2 = os.path.join(dirn, 'vault2.lmdb')
            newvault = s_vault.Vault(path2)
            nroot = newvault.genRootCert()
            vault.addRootCert(nroot)
            ncert = vault.genUserCert('haha@ninja.com')
            self.true(root.signed(ncert))
            self.false(nroot.signed(ncert))

            # We can use one cert to sign another cert though
            self.none(nroot.sign(cert))
            self.true(root.signed(cert))
            self.true(nroot.signed(cert))

            # We can make a Cert without having the private key available
            tstcert = s_vault.Cert(root.cert)
            self.none(tstcert.getkey())
            self.isinstance(tstcert.public(), s_ecc.PubKey)
            # attempting to sign data with that cert fails though
            self.raises(s_exc.NoCertKey, tstcert.sign, ncert, haha=1)

            # Tear down our vaults
            newvault.fini()
            vault.fini()

    def test_lib_crypto_vault_base(self):
        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'vault.lmdb')
            vault = s_vault.Vault(path)

            # Ensure we can generate a root cert and it is persistent
            self.len(0, vault.getRootCerts())
            root = vault.genRootCert()
            self.isinstance(root, s_vault.Cert)
            self.eq(root.iden(), vault.genRootCert().iden())
            self.len(1, vault.getRootCerts())

            # Generate a user certificate and validate it was
            # signed by the root certificate
            self.none(vault.getUserCert('bobgrey@vertex.link'))
            self.none(vault.getCert('bobgrey@vertex.link'))
            cert = vault.genUserCert('bobgrey@vertex.link')
            self.isinstance(cert, s_vault.Cert)
            self.true(root.signed(cert))
            # And the certs are persistent for a user too
            self.eq(cert.iden(), vault.getUserCert('bobgrey@vertex.link').iden())
            # The certs are signed by the vault root cert
            self.true(vault.isValidCert(cert))
            # Since we have an iden, we can retrieve a cert directly
            self.nn(vault.getCert(cert.iden()))

            # Get the users auth token
            auth = vault.genUserAuth('bobgrey@vertex.link')
            self.istufo(auth)
            self.isinstance(auth[1].get('cert'), bytes)
            self.isinstance(auth[1].get('ecdsa:prvkey'), bytes)
            self.isinstance(auth[1].get('root'), bytes)
            acert = s_vault.Cert.load(auth[1].get('cert'))
            self.eq(cert.iden(), acert.iden())
            rcert = s_vault.Cert.load(auth[1].get('root'))
            self.eq(root.iden(), rcert.iden())
            # The auth token is msgpackable
            self.nn(s_msgpack.en(auth))

            # Create a second vault and load a user auth token into it
            path2 = os.path.join(dirn, 'vault2.lmdb')
            newvault = s_vault.Vault(path2)
            # The new vault does not have any CA data
            self.len(0, newvault.getRootCerts())
            ncert = newvault.addUserAuth(auth)
            self.isinstance(ncert, s_vault.Cert)
            ncert = newvault.getUserCert('bobgrey@vertex.link')
            self.eq(ncert.iden(), cert.iden())
            # This cert is not signed legitimately according to newvault
            newvault.isValidCert(ncert)

            # We can manipulate CA data
            nroot = newvault.genRootCert()
            self.nn(nroot)
            self.len(1, vault.getRootCerts())
            self.none(vault.addRootCert(nroot))
            self.len(2, vault.getRootCerts())
            # Since we added newvault's root CA to vault,
            # it can validate certs from newvault
            ncert = newvault.genUserCert('hehe@haha.com')
            self.true(vault.isValidCert(ncert))
            # But deleted certs don't go away from the DB
            self.nn(vault.getCert(nroot.iden()))
            # And we can delete root certs
            self.none(vault.delRootCert(nroot))
            self.len(1, vault.getRootCerts())
            # vault can no longer validate data from newvault
            self.false(vault.isValidCert(ncert))

            # Ensure we can make a new ECC key directly
            rkey = vault.genEccKey()
            self.isinstance(rkey, s_ecc.PriKey)

            # Tear down our vaults
            newvault.fini()
            vault.fini()

    def test_lib_crypto_vault_shared_interproc(self):
        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'vault.lmdb')

            evt1 = multiprocessing.Event()
            evt1.clear()
            evt2 = multiprocessing.Event()
            evt2.clear()

            user = 'pennywise@vertex.link'

            # Fire a process which makes a user cert in the vault after one
            # proc already obtains the advisory lock.  This will be blocked
            # by the advisory file lock.
            with s_vault.shared(path) as vault:
                # thr = doStuff(path, 'pennywise@local.link')
                proc = multiprocessing.Process(target=addUserToVault,
                                               args=(evt1, evt2, path, user))
                proc.start()

                cert = vault.genUserCert('bobgrey@vertex.link')
                self.nn(cert)
                evt1.set()
                self.none(vault.getUserCert(user))

            evt2.wait(10)
            proc.join(10)

            # Ensure that the user is present in the vault now after the
            # main process has released its lock
            with s_vault.shared(path) as vault:
                self.nn(vault.getUserCert(user))

    def test_lib_crypto_vault_shared_intraproc(self):
        self.skipTest('Skipped pending shared() locked addition')
        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'vault.lmdb')

            evt1 = threading.Event()
            evt1.clear()
            evt2 = threading.Event()
            evt2.clear()

            user = 'pennywise@vertex.link'

            func = s_common.firethread(addUserToVault)

            # Fire a thread which makes a user cert in the vault after one
            # thread already obtains the advisory lock and threading.lock.
            with s_vault.shared(path) as vault:
                thr = func(evt1, evt2, path, user)
                cert = vault.genUserCert('bobgrey@vertex.link')
                self.nn(cert)
                evt1.set()
                self.none(vault.getUserCert(user))

            evt2.wait(10)
            thr.join(10)

            # Ensure that the user is present in the vault now after the
            # main thread has released its lock
            with s_vault.shared(path) as vault:
                self.nn(vault.getUserCert(user))

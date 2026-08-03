import synapse.exc as s_exc

import synapse.lib.coro as s_coro
import synapse.lib.crypto.ecc as s_ecc
import synapse.lib.stormtypes as s_stormtypes
import synapse.lib.stormlib.cryptoutils as s_cryptoutils

@s_stormtypes.registry.registerLib
class LibEcc(s_stormtypes.Lib):
    '''
    A Storm library for generating and loading ECC keys.
    '''
    _storm_locals = (
        {'name': 'generate', 'desc': '''
        Generate a new ECC private key.

        Examples:
            Generate a key and sign a message::

                $key = $lib.crypto.ecc.generate()
                $sig = $key.sign($mesg.encode())
        ''',
         'type': {'type': 'function', '_funcname': '_generate',
                  'args': (
                      {'name': 'curve', 'type': 'str', 'default': 'P-256',
                       'desc': 'The named curve to use (P-256, P-384, or P-521).'},
                  ),
                  'returns': {'type': 'crypto:ecc:key',
                              'desc': 'A new ``crypto:ecc:key`` containing the generated private key.'}}},
        {'name': 'load', 'desc': '''
        Load an ECC public or private key.

        The encoding (DER or PEM) and whether the key is a public or private key are
        detected automatically. The key must contain a single key.

        Examples:
            Load a PEM encoded private key::

                $key = $lib.crypto.ecc.load($pem)
        ''',
         'type': {'type': 'function', '_funcname': '_load',
                  'args': (
                      {'name': 'key', 'type': ['str', 'bytes'],
                       'desc': 'A DER or PEM encoded ECC public or private key. May be a str (PEM) or bytes.'},
                  ),
                  'returns': {'type': 'crypto:ecc:key',
                              'desc': 'A new ``crypto:ecc:key`` containing the loaded key.'}}},
    )
    _storm_lib_path = ('crypto', 'ecc')

    def getObjLocals(self):
        return {
            'load': self._load,
            'generate': self._generate,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _generate(self, curve='P-256'):
        curve = await s_stormtypes.tostr(curve)

        def generate():
            return s_ecc.PriKey.generate(curve=curve)

        prikey = await s_coro.executor(generate)
        return CryptoEccKey(self.runt, prikey, True)

    @s_stormtypes.stormfunc(readonly=True)
    async def _load(self, key):
        byts = await s_cryptoutils.reqKey(key, 'key')
        try:
            keyobj = s_ecc.loadKey(byts)
        except s_cryptoutils._loaderrors as e:
            raise s_exc.BadArg(mesg=f'Invalid ECC key: {e}') from None

        return CryptoEccKey(self.runt, keyobj, isinstance(keyobj, s_ecc.PriKey))

@s_stormtypes.registry.registerType
class CryptoEccKey(s_cryptoutils.CryptoKey):
    '''
    A Storm object representing an ECC public or private key.
    '''
    _storm_typename = 'crypto:ecc:key'

    _storm_locals = (
        {'name': 'isPrivate', 'type': 'boolean',
         'desc': 'True if the object contains a private key and can sign, otherwise False.'},

        {'name': 'pubkey', 'desc': '''
        Return a new ``crypto:ecc:key`` containing only the public key.

        This raises if the key is already a public-only key.
        ''',
         'type': {'type': 'function', '_funcname': '_methPubkey',
                  'args': (),
                  'returns': {'type': 'crypto:ecc:key',
                              'desc': 'A new ``crypto:ecc:key`` containing only the public key.'}}},

        {'name': 'sign', 'desc': '''
        Compute the ECDSA signature for the given bytes.

        This raises if the key does not contain a private key.
        ''',
         'type': {'type': 'function', '_funcname': '_methSign',
                  'args': (
                      {'name': 'byts', 'type': 'bytes', 'desc': 'The bytes to sign.'},
                      {'name': 'hashalgo', 'type': 'str', 'default': 'sha256',
                       'desc': 'The hash algorithm to use (sha256, sha384, or sha512).'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'The DER encoded ECDSA signature bytes.'}}},

        {'name': 'verify', 'desc': 'Verify the ECDSA signature for the given bytes.',
         'type': {'type': 'function', '_funcname': '_methVerify',
                  'args': (
                      {'name': 'byts', 'type': 'bytes', 'desc': 'The bytes to verify.'},
                      {'name': 'signature', 'type': 'bytes', 'desc': 'The DER encoded signature bytes to verify.'},
                      {'name': 'hashalgo', 'type': 'str', 'default': 'sha256',
                       'desc': 'The hash algorithm to use (sha256, sha384, or sha512).'},
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the signature is valid, otherwise False.'}}},

        {'name': 'encode', 'desc': 'Encode the key as PEM or DER.',
         'type': {'type': 'function', '_funcname': '_methEncode',
                  'args': (
                      {'name': 'fmt', 'type': 'str', 'default': 'pem',
                       'desc': 'The encoding format: "pem" (returns a str) or "der" (returns bytes).'},
                  ),
                  'returns': {'type': ['str', 'bytes'],
                              'desc': 'The PEM encoded string or the DER encoded bytes.'}}},
    )

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSign(self, byts, hashalgo='sha256'):
        if not self.isprivate:
            raise s_exc.BadArg(mesg='Cannot sign with a public key.')

        byts = await s_cryptoutils.reqBytes(byts, 'byts')
        hashalgo = await s_stormtypes.tostr(hashalgo)

        def sign():
            return self.key.sign(byts, hashalgo=hashalgo)

        # ECDSA over the fixed NIST curves and the sha256/384/512 set has no reachable failure
        # here; the wrapper is a defensive net so that no raw error can ever reach the Storm
        # runtime if that changes.
        try:
            return await s_coro.executor(sign)
        except (ValueError, TypeError) as e:  # pragma: no cover
            raise s_exc.CryptoErr(mesg=f'ECC signing failed: {e}') from None

    @s_stormtypes.stormfunc(readonly=True)
    async def _methVerify(self, byts, signature, hashalgo='sha256'):
        byts = await s_cryptoutils.reqBytes(byts, 'byts')
        signature = await s_cryptoutils.reqBytes(signature, 'signature')
        hashalgo = await s_stormtypes.tostr(hashalgo)

        def verify():
            publ = self.key.public() if self.isprivate else self.key
            return publ.verify(byts, signature, hashalgo=hashalgo)

        try:
            return await s_coro.executor(verify)
        except (ValueError, TypeError) as e:  # pragma: no cover
            # defensive, as with sign() above: no reachable raw error given the curve/hash sets.
            raise s_exc.CryptoErr(mesg=f'ECC verification failed: {e}') from None

import synapse.exc as s_exc

import synapse.lib.coro as s_coro
import synapse.lib.crypto.rsa as s_rsa
import synapse.lib.stormtypes as s_stormtypes
import synapse.lib.stormlib.cryptoutils as s_cryptoutils

@s_stormtypes.registry.registerLib
class LibRsa(s_stormtypes.Lib):
    '''
    A Storm library for generating and loading RSA keys.
    '''
    _storm_locals = (
        {'name': 'generate', 'desc': '''
        Generate a new RSA private key.

        Examples:
            Generate a key and sign a message::

                $key = $lib.crypto.rsa.generate()
                $sig = $key.sign($mesg.encode())
        ''',
         'type': {'type': 'function', '_funcname': '_generate',
                  'args': (
                      {'name': 'bits', 'type': 'int', 'default': 2048,
                       'desc': 'The size of the RSA key to generate in bits (1024 to 8192).'},
                  ),
                  'returns': {'type': 'crypto:rsa:key',
                              'desc': 'A new ``crypto:rsa:key`` containing the generated private key.'}}},
        {'name': 'load', 'desc': '''
        Load an RSA public or private key.

        The encoding (DER or PEM) and whether the key is a public or private key are
        detected automatically. The key must contain a single key.

        Examples:
            Load a PEM encoded private key::

                $key = $lib.crypto.rsa.load($pem)
        ''',
         'type': {'type': 'function', '_funcname': '_load',
                  'args': (
                      {'name': 'key', 'type': ['str', 'bytes'],
                       'desc': 'A DER or PEM encoded RSA public or private key. May be a str (PEM) or bytes.'},
                  ),
                  'returns': {'type': 'crypto:rsa:key',
                              'desc': 'A new ``crypto:rsa:key`` containing the loaded key.'}}},
    )
    _storm_lib_path = ('crypto', 'rsa')

    def getObjLocals(self):
        return {
            'load': self._load,
            'generate': self._generate,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _generate(self, bits=2048):
        bits = await s_stormtypes.toint(bits)
        if bits < 1024 or bits > 8192:
            raise s_exc.BadArg(mesg=f'RSA key size must be between 1024 and 8192 bits, got {bits}.', bits=bits)

        def generate():
            return s_rsa.PriKey.generate(bits=bits)

        prikey = await s_coro.executor(generate)
        return CryptoRsaKey(self.runt, prikey, True)

    @s_stormtypes.stormfunc(readonly=True)
    async def _load(self, key):
        byts = await s_cryptoutils.reqKey(key, 'key')
        try:
            keyobj = s_rsa.loadKey(byts)
        except s_cryptoutils._loaderrors as e:
            raise s_exc.BadArg(mesg=f'Invalid RSA key: {e}') from None

        return CryptoRsaKey(self.runt, keyobj, isinstance(keyobj, s_rsa.PriKey))

@s_stormtypes.registry.registerType
class CryptoRsaKey(s_cryptoutils.CryptoKey):
    '''
    A Storm object representing an RSA public or private key.
    '''
    _storm_typename = 'crypto:rsa:key'

    _storm_locals = (
        {'name': 'isPrivate', 'type': 'boolean',
         'desc': 'True if the object contains a private key and can sign, otherwise False.'},

        {'name': 'pubkey', 'desc': '''
        Return a new ``crypto:rsa:key`` containing only the public key.

        This raises if the key is already a public-only key.
        ''',
         'type': {'type': 'function', '_funcname': '_methPubkey',
                  'args': (),
                  'returns': {'type': 'crypto:rsa:key',
                              'desc': 'A new ``crypto:rsa:key`` containing only the public key.'}}},

        {'name': 'sign', 'desc': '''
        Compute the RSA signature for the given bytes.

        This raises if the key does not contain a private key.
        ''',
         'type': {'type': 'function', '_funcname': '_methSign',
                  'args': (
                      {'name': 'byts', 'type': 'bytes', 'desc': 'The bytes to sign.'},
                      {'name': 'padding', 'type': 'str', 'default': 'pss',
                       'desc': 'The padding scheme to use (pss or pkcs1v15).'},
                      {'name': 'hashalgo', 'type': 'str', 'default': 'sha256',
                       'desc': 'The hash algorithm to use (sha256, sha384, or sha512).'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'The RSA signature bytes.'}}},

        {'name': 'verify', 'desc': 'Verify the RSA signature for the given bytes.',
         'type': {'type': 'function', '_funcname': '_methVerify',
                  'args': (
                      {'name': 'byts', 'type': 'bytes', 'desc': 'The bytes to verify.'},
                      {'name': 'signature', 'type': 'bytes', 'desc': 'The signature bytes to verify.'},
                      {'name': 'padding', 'type': 'str', 'default': 'pss',
                       'desc': 'The padding scheme to use (pss or pkcs1v15).'},
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
    async def _methSign(self, byts, padding='pss', hashalgo='sha256'):
        if not self.isprivate:
            raise s_exc.BadArg(mesg='Cannot sign with a public key.')

        byts = await s_cryptoutils.reqBytes(byts, 'byts')
        padding = s_cryptoutils.reqPadding(await s_stormtypes.tostr(padding))
        hashalgo = await s_stormtypes.tostr(hashalgo)

        def sign():
            return self.key.sign(byts, padding=padding, hashalgo=hashalgo)

        # the >= 1024 bit key floor and the fixed sha256/384/512 set mean cryptography cannot
        # actually raise on a sign here; the wrapper is a defensive net so that no raw error can
        # ever reach the Storm runtime if that changes.
        try:
            return await s_coro.executor(sign)
        except (ValueError, TypeError) as e:  # pragma: no cover
            raise s_exc.CryptoErr(mesg=f'RSA signing failed: {e}') from None

    @s_stormtypes.stormfunc(readonly=True)
    async def _methVerify(self, byts, signature, padding='pss', hashalgo='sha256'):
        byts = await s_cryptoutils.reqBytes(byts, 'byts')
        signature = await s_cryptoutils.reqBytes(signature, 'signature')
        padding = s_cryptoutils.reqPadding(await s_stormtypes.tostr(padding))
        hashalgo = await s_stormtypes.tostr(hashalgo)

        def verify():
            publ = self.key.public() if self.isprivate else self.key
            return publ.verify(byts, signature, padding=padding, hashalgo=hashalgo)

        try:
            return await s_coro.executor(verify)
        except (ValueError, TypeError) as e:  # pragma: no cover
            # defensive, as with sign() above: no reachable raw error given the key/hash floors.
            raise s_exc.CryptoErr(mesg=f'RSA verification failed: {e}') from None

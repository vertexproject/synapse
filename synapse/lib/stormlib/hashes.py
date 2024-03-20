import hmac
import hashlib

import synapse.exc as s_exc

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibHashes(s_stormtypes.Lib):
    '''
    A Storm Library for hashing bytes
    '''
    _storm_locals = (
        {'name': 'md5', 'desc': 'Retrieve an MD5 hash of a byte string.',
         'type': {'type': 'function', '_funcname': '_md5',
                  'args': (
                      {'name': 'byts', 'type': 'bytes', 'desc': 'The bytes to hash.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The hex digest of the MD5 hash of the input bytes.'}}},
        {'name': 'sha1', 'desc': 'Retrieve a SHA1 hash of a byte string.',
         'type': {'type': 'function', '_funcname': '_sha1',
                  'args': (
                      {'name': 'byts', 'type': 'bytes', 'desc': 'The bytes to hash.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The hex digest of the SHA1 hash of the input bytes.'}}},
        {'name': 'sha256', 'desc': 'Retrieve a SHA256 hash of a byte string.',
         'type': {'type': 'function', '_funcname': '_sha256',
                  'args': (
                      {'name': 'byts', 'type': 'bytes', 'desc': 'The bytes to hash.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The hex digest of the SHA256 hash of the input bytes.'}}},
        {'name': 'sha512', 'desc': 'Retrieve a SHA512 hash of a byte string.',
         'type': {'type': 'function', '_funcname': '_sha512',
                  'args': (
                      {'name': 'byts', 'type': 'bytes', 'desc': 'The bytes to hash.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The hex digest of the SHA512 hash of the input bytes.'}}}
    )
    _storm_lib_path = ('crypto', 'hashes')

    def getObjLocals(self):
        return {
            'md5': self._md5,
            'sha1': self._sha1,
            'sha256': self._sha256,
            'sha512': self._sha512,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _md5(self, byts):
        return hashlib.md5(byts, usedforsecurity=False).hexdigest()

    @s_stormtypes.stormfunc(readonly=True)
    async def _sha1(self, byts):
        return hashlib.sha1(byts, usedforsecurity=False).hexdigest()

    @s_stormtypes.stormfunc(readonly=True)
    async def _sha256(self, byts):
        return hashlib.sha256(byts).hexdigest()

    @s_stormtypes.stormfunc(readonly=True)
    async def _sha512(self, byts):
        return hashlib.sha512(byts).hexdigest()

@s_stormtypes.registry.registerLib
class LibHmac(s_stormtypes.Lib):
    '''
    A Storm library for computing RFC2104 HMAC values.
    '''
    _storm_locals = (
        {'name': 'digest', 'desc': '''
        Compute the digest value of a message using RFC2104 HMAC.

        Examples:
            Compute the HMAC-SHA256 digest for a message with a secret key::

                $digest = $lib.crypto.hmac.digest(key=$secretKey.encode(), mesg=$mesg.encode())
        ''',
         'type': {'type': 'function', '_funcname': '_digest',
                  'args': (
                      {'name': 'key', 'type': 'bytes', 'desc': 'The key to use for the HMAC calculation.'},
                      {'name': 'mesg', 'type': 'bytes', 'desc': 'The message to use for the HMAC calculation.'},
                      {'name': 'alg', 'type': 'str', 'default': 'sha256',
                       'desc': 'The digest algorithm to use.'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'The binary digest of the HMAC value.'}}},
    )
    _storm_lib_path = ('crypto', 'hmac')

    def getObjLocals(self):
        return {
            'digest': self._digest,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _digest(self, key, mesg, alg='sha256') -> bytes:
        key = await s_stormtypes.toprim(key)
        if not isinstance(key, bytes):
            raise s_exc.BadArg(mesg='key is not bytes.', name='key')
        mesg = await s_stormtypes.toprim(mesg)
        if not isinstance(mesg, bytes):
            raise s_exc.BadArg(mesg='mesg is not bytes.', name='mesg')
        alg = await s_stormtypes.tostr(alg)
        try:
            valu = hmac.digest(key=key, msg=mesg, digest=alg)
        except ValueError as e:
            if 'unsupported' in str(e):
                raise s_exc.BadArg(mesg=f'Invalid hmac algorithm provided: {alg}', alg=alg)
            # other value errors would raise potentially from inside of openssl, which cpython
            # raises if they occur but does not cover in the hmac stdlib test suite.
            raise s_exc.StormRuntimeError(mesg=f'Error computing hmac: {e}')  # pragma: no cover
        return valu

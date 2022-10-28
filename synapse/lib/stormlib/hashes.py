import hmac
import hashlib

import synapse.common as s_common

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

    async def _md5(self, byts):
        return hashlib.md5(byts).hexdigest()

    async def _sha1(self, byts):
        return hashlib.sha1(byts).hexdigest()

    async def _sha256(self, byts):
        return hashlib.sha256(byts).hexdigest()

    async def _sha512(self, byts):
        return hashlib.sha512(byts).hexdigest()

@s_stormtypes.registry.registerLib
class LibHmac(s_stormtypes.Lib):
    '''
    A Storm library for computing RFC2140 HMAC values.
    '''
    _storm_locals = (
        {'name': 'sign', 'desc': 'Sign a message with a key using RFC2140 HMAC.',
         'type': {'type': 'function', '_funcname': '_sign',
                  'args': (
                      {'name': 'key', 'type': 'bytes', 'desc': 'The key to use for the HMAC calculation.'},
                      {'name': 'mesg', 'type': 'bytes', 'desc': 'The mesg to sign.'},
                      {'name': 'digest', 'type': 'str', 'default': 'sha256',
                       'desc': 'The digest algorithm to use.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The hex digest of the HMAC value.'}}},
    )
    _storm_lib_path = ('crypto', 'hmac')

    def getObjLocals(self):
        return {
            'sign': self._sign,
        }

    async def _sign(self, key, mesg, digest='sha256') -> bytes:
        key = await s_stormtypes.toprim(key)
        mesg = await s_stormtypes.toprim(mesg)
        digest = await s_stormtypes.tostr(digest)
        valu = hmac.digest(key=key, msg=mesg, digest=digest)
        return valu

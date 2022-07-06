import hashlib

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

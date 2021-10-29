import binascii

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class HexLib(s_stormtypes.Lib):
    '''
    A Storm library implements helpers for hexidecimal encoded strings.
    '''
    _storm_locals = (
        {'name': 'encode', 'desc': 'Encode a bytes into a hexidecimal string.',
         'type': {'type': 'function', '_funcname': 'encode',
                  'args': (
                      {'name': 'valu', 'type': 'bytes', 'desc': 'The bytes to be encoded into a hex string.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The hex encoded string.', }
        }},
        {'name': 'decode', 'desc': 'Decode a hexidecimal string into bytes.',
         'type': {'type': 'function', '_funcname': 'decode',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'The hex string to be decoded into bytes.'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'The hex encoded string.', }
        }},
    )

    _storm_lib_path = ('hex',)

    def getObjLocals(self):
        return {
            # TODO 'dump': self.dump,
            'encode': self.encode,
            'decode': self.decode,
        }

    async def encode(self, valu):
        if not isinstance(valu, bytes):
            raise s_exc.BadArg(mesg='$lib.hex.encode() requires a bytes argument.')
        return s_common.ehex(valu)

    async def decode(self, valu):
        valu = await s_stormtypes.tostr(valu)
        try:
            return s_common.uhex(valu)
        except binascii.Error as e:
            raise s_exc.BadArg(mesg=f'$lib.hex.decode(): {e}')

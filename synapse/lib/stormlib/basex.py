import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class BaseXLib(s_stormtypes.Lib):
    '''
    A Storm library which implements helpers for encoding and decoding strings using an arbitrary charset.
    '''
    _storm_locals = (
        {'name': 'encode', 'desc': 'Encode bytes into a baseX string.',
         'type': {'type': 'function', '_funcname': 'encode',
                  'args': (
                      {'name': 'byts', 'type': 'bytes', 'desc': 'The bytes to be encoded into a string.'},
                      {'name': 'charset', 'type': 'str', 'desc': 'The charset used to encode the bytes.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The encoded string.', }
        }},
        {'name': 'decode', 'desc': 'Decode a baseX string into bytes.',
         'type': {'type': 'function', '_funcname': 'decode',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The hex string to be decoded into bytes.'},
                      {'name': 'charset', 'type': 'str', 'desc': 'The charset used to decode the string.'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'The decoded bytes.', }
        }},
    )

    _storm_lib_path = ('basex',)

    def getObjLocals(self):
        return {
            'encode': self.encode,
            'decode': self.decode,
        }

    async def encode(self, byts, charset):
        if not isinstance(byts, bytes):
            raise s_exc.BadArg(mesg='$lib.basex.encode() requires a bytes argument.')

        charset = await s_stormtypes.tostr(charset)

        retn = []
        base = len(charset)

        num = int.from_bytes(byts, 'big')
        if num == 0:
            return charset[0]

        while num:
            retn.append(charset[int(num % base)])
            num = num // base

        return ''.join(retn[::-1])

    async def decode(self, text, charset):
        text = await s_stormtypes.tostr(text)
        charset = await s_stormtypes.tostr(charset)
        alpha2num = {c: o for (o, c) in enumerate(charset)}

        retn = 0
        base = len(charset)
        for c in text:
            v = alpha2num.get(c)
            if v is None:
                mesg = f'$lib.basex.decode() string contains value not in charset: {c}'
                raise s_exc.BadArg(mesg=mesg)
            retn = (retn * base) + v

        size = (retn.bit_length() + 7) // 8
        return retn.to_bytes(size, 'big')

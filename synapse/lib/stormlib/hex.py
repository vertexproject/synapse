import binascii

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class HexLib(s_stormtypes.Lib):
    '''
    A Storm library which implements helpers for hexadecimal encoded strings.
    '''
    _storm_locals = (
        {'name': 'encode', 'desc': 'Encode bytes into a hexadecimal string.',
         'type': {'type': 'function', '_funcname': 'encode',
                  'args': (
                      {'name': 'valu', 'type': 'bytes', 'desc': 'The bytes to be encoded into a hex string.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The hex encoded string.', }
        }},
        {'name': 'decode', 'desc': 'Decode a hexadecimal string into bytes.',
         'type': {'type': 'function', '_funcname': 'decode',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'The hex string to be decoded into bytes.'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'The decoded bytes.', }
        }},
        {'name': 'toint', 'desc': 'Convert a big endian hexadecimal string to an integer.',
         'type': {'type': 'function', '_funcname': 'toint',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'The hex string to be converted.'},
                      {'name': 'signed', 'type': 'bool', 'default': False,
                       'desc': 'If true, convert to a signed integer.'},
                  ),
                  'returns': {'type': 'int', 'desc': 'The resulting integer.', }
        }},
        {'name': 'fromint', 'desc': 'Convert an integer to a big endian hexadecimal string.',
         'type': {'type': 'function', '_funcname': 'fromint',
                  'args': (
                      {'name': 'valu', 'type': 'int', 'desc': 'The integer to be converted.'},
                      {'name': 'length', 'type': 'int', 'desc': 'The number of bytes to use to represent the integer.'},
                      {'name': 'signed', 'type': 'bool', 'default': False,
                       'desc': 'If true, convert as a signed value.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The resulting hex string.', }
        }},
        {'name': 'trimext', 'desc': 'Trim sign extension bytes from a hexadecimal encoded signed integer.',
         'type': {'type': 'function', '_funcname': 'trimext',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'The hex string to trim.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The trimmed hex string.', }
        }},
        {'name': 'signext', 'desc': 'Sign extension pad a hexadecimal encoded signed integer.',
         'type': {'type': 'function', '_funcname': 'signext',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'The hex string to pad.'},
                      {'name': 'length', 'type': 'int', 'desc': 'The number of characters to pad the string to.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The sign extended hex string.', }
        }},
    )

    _storm_lib_path = ('hex',)

    def getObjLocals(self):
        return {
            # TODO 'dump': self.dump,
            'toint': self.toint,
            'encode': self.encode,
            'decode': self.decode,
            'fromint': self.fromint,
            'trimext': self.trimext,
            'signext': self.signext,
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

    async def toint(self, valu, signed=False):
        valu = await s_stormtypes.tostr(valu)
        signed = await s_stormtypes.tobool(signed)

        try:
            byts = s_common.uhex(valu)
        except binascii.Error as e:
            raise s_exc.BadArg(mesg=f'$lib.hex.toint(): {e}')

        return int.from_bytes(byts, 'big', signed=signed)

    async def fromint(self, valu, length, signed=False):
        valu = await s_stormtypes.toint(valu)
        length = await s_stormtypes.toint(length)
        signed = await s_stormtypes.tobool(signed)

        try:
            byts = valu.to_bytes(length, 'big', signed=signed)
            return s_common.ehex(byts)
        except OverflowError as e:
            raise s_exc.BadArg(mesg=f'$lib.hex.fromint(): {e}')

    async def trimext(self, valu):
        valu = await s_stormtypes.tostr(valu)

        try:
            s_common.uhex(valu)
        except binascii.Error as e:
            raise s_exc.BadArg(mesg=f'$lib.hex.trimext(): {e}')

        while len(valu) >= 4:
            bits = int(valu[:4], 16) >> 7
            if bits == 0b111111111 or bits == 0b000000000:
                valu = valu[2:]
                continue
            break
        return valu

    async def signext(self, valu, length):
        valu = await s_stormtypes.tostr(valu)
        length = await s_stormtypes.toint(length)

        try:
            if int(valu[0], 16) >> 3 == 0:
                return valu.rjust(length, '0')
            return valu.rjust(length, 'f')
        except ValueError as e:
            raise s_exc.BadArg(mesg=f'$lib.hex.signext(): {e}')

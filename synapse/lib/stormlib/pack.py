import struct

import synapse.exc as s_exc

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibPack(s_stormtypes.Lib):
    '''
    Packing / unpacking structured bytes.
    '''
    _storm_locals = (
        {'name': 'en', 'desc': 'Pack a sequence of items into an array of bytes.',
         'type': {'type': 'function', '_funcname': 'en',
                  'args': (
                      {'name': 'fmt', 'type': 'str', 'desc': 'A python struct.pack() format string.'},
                      {'name': 'items', 'type': 'list', 'desc': 'A list of values to be packed.'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'The packed byte structure.'}}},
        {'name': 'un', 'desc': 'Unpack a sequence of items from an array of bytes.',
         'type': {'type': 'function', '_funcname': 'un',
                  'args': (
                      {'name': 'fmt', 'type': 'str', 'desc': 'A python struct.unpack() format string.'},
                      {'name': 'byts', 'type': 'bytes', 'desc': 'Bytes to be unpacked'},
                      {'name': 'offs', 'type': 'int', 'default': 0, 'desc': 'The offset to begin unpacking from.'},
                  ),
                  'returns': {'type': 'list', 'desc': 'The unpacked items.'}}},
    )
    _storm_lib_path = ('pack',)

    def getObjLocals(self):
        return {
            'en': self.en,
            'un': self.un,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def en(self, fmt, items):
        fmt = await s_stormtypes.tostr(fmt)
        items = await s_stormtypes.toprim(items)

        if not (fmt.startswith('<') or fmt.startswith('>')):
            mesg = 'Pack format string must start with > or < to denote endianness.'
            raise s_exc.BadArg(mesg=mesg)

        try:
            return struct.pack(fmt, *items)
        except struct.error as e:
            raise s_exc.BadArg(mesg=str(e))

    @s_stormtypes.stormfunc(readonly=True)
    async def un(self, fmt, byts, offs=0):

        fmt = await s_stormtypes.tostr(fmt)
        offs = await s_stormtypes.toint(offs)
        byts = await s_stormtypes.toprim(byts)

        if not isinstance(byts, bytes):
            raise s_exc.BadArg(mesg='$lib.pack.un() second argument must be bytes.')

        if not (fmt.startswith('<') or fmt.startswith('>')):
            mesg = 'Pack format string must start with > or < to denote endianness.'
            raise s_exc.BadArg(mesg=mesg)

        try:
            return struct.unpack_from(fmt, byts, offset=offs)
        except struct.error as e:
            raise s_exc.BadArg(mesg=str(e))

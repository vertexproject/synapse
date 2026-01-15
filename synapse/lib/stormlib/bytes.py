import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibBytes(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with bytes.
    '''
    _storm_locals = (
        {'name': 'fromints', 'desc': '''
            Convert an iterable source of integers into bytes.

            Note:
                The integer values must be in the range 0 to 255. Values outside of this range will raise a
                BadArg.

            Examples:
                Convert a list of integers into bytes::

                    $ints = ([0x56, 0x49, 0x53, 0x49])
                    $byts = $lib.bytes.fromints($ints)

            ''',
         'type': {'type': 'function', '_funcname': '_libBytesFromInts',
                  'args': (
                      {'name': 'ints', 'type': 'generator', 'desc': 'An iterable source of integers.', },
                  ),
                  'returns': {'type': 'bytes', 'desc': 'The bytes from processing the integers.'}}},
    )

    _storm_lib_path = ('bytes',)

    def getObjLocals(self):
        return {
            'fromints': self._libBytesFromInts,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _libBytesFromInts(self, ints):
        try:
            ints = [await s_stormtypes.toint(item) async for item in s_stormtypes.toiter(ints)]
            ret = bytes(ints)
        except s_exc.SynErr as e:
            raise s_exc.BadArg(mesg=e.get('mesg'))
        except Exception as e:
            raise s_exc.BadArg(mesg=f'Failed to convert ints to bytes: {str(e)}')
        return ret

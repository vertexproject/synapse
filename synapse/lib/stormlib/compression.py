import bz2
import gzip
import zlib

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class Bzip2Lib(s_stormtypes.Lib):
    '''
    A Storm library which implements helpers for bzip2 compression.
    '''
    _storm_locals = (
        {'name': 'en', 'desc': '''
            Compress bytes using bzip2 and return them.

            Example:
                Compress bytes with bzip2::

                    $foo = $lib.compression.bzip2.en($mybytez)''',
         'type': {'type': 'function', '_funcname': 'en',
                  'args': (
                      {'name': 'valu', 'type': 'bytes', 'desc': 'The bytes to be compressed.'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'The bzip2 compressed bytes.'}}},
        {'name': 'un', 'desc': '''
            Decompress bytes using bzip2 and return them.

            Example:
                Decompress bytes with bzip2::

                $foo = $lib.compression.bzip2.un($mybytez)''',
         'type': {'type': 'function', '_funcname': 'un',
                  'args': (
                      {'name': 'valu', 'type': 'bytes', 'desc': 'The bytes to be decompressed.'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'Decompressed bytes.'}}},
    )

    _storm_lib_path = ('compression', 'bzip2')

    def getObjLocals(self):
        return {
            'en': self.en,
            'un': self.un,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def en(self, valu):
        valu = await s_stormtypes.toprim(valu)
        try:
            return bz2.compress(valu)
        except Exception as e:
            mesg = f'Error during bzip2 compression - {str(e)}: {s_common.trimText(repr(valu))}'
            raise s_exc.StormRuntimeError(mesg=mesg) from None

    async def un(self, valu):
        valu = await s_stormtypes.toprim(valu)
        try:
            return bz2.decompress(valu)
        except Exception as e:
            mesg = f'Error during bzip2 decompression - {str(e)}: {s_common.trimText(repr(valu))}'
            raise s_exc.StormRuntimeError(mesg=mesg) from None

@s_stormtypes.registry.registerLib
class GzipLib(s_stormtypes.Lib):
    '''
    A Storm library which implements helpers for gzip compression.
    '''
    _storm_locals = (
        {'name': 'en', 'desc': '''
            Compress bytes using gzip and return them.

            Example:
                Compress bytes with gzip::

                    $foo = $lib.compression.gzip.en($mybytez)''',
         'type': {'type': 'function', '_funcname': 'en',
                  'args': (
                      {'name': 'valu', 'type': 'bytes', 'desc': 'The bytes to be compressed.'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'The gzip compressed bytes.'}}},
        {'name': 'un', 'desc': '''
            Decompress bytes using gzip and return them.

            Example:
                Decompress bytes with gzip::

                $foo = $lib.compression.gzip.un($mybytez)''',
         'type': {'type': 'function', '_funcname': 'un',
                  'args': (
                      {'name': 'valu', 'type': 'bytes', 'desc': 'The bytes to be decompressed.'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'Decompressed bytes.'}}},
    )

    _storm_lib_path = ('compression', 'gzip')

    def getObjLocals(self):
        return {
            'en': self.en,
            'un': self.un,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def en(self, valu):
        valu = await s_stormtypes.toprim(valu)
        try:
            return gzip.compress(valu)
        except Exception as e:
            mesg = f'Error during gzip compression - {str(e)}: {s_common.trimText(repr(valu))}'
            raise s_exc.StormRuntimeError(mesg=mesg) from None

    async def un(self, valu):
        valu = await s_stormtypes.toprim(valu)
        try:
            return gzip.decompress(valu)
        except Exception as e:
            mesg = f'Error during gzip decompression - {str(e)}: {s_common.trimText(repr(valu))}'
            raise s_exc.StormRuntimeError(mesg=mesg) from None

@s_stormtypes.registry.registerLib
class ZlibLib(s_stormtypes.Lib):
    '''
    A Storm library which implements helpers for zlib compression.
    '''
    _storm_locals = (
        {'name': 'en', 'desc': '''
            Compress bytes using zlib and return them.

            Example:
                Compress bytes with zlib::

                    $foo = $lib.compression.zlib.en($mybytez)''',
         'type': {'type': 'function', '_funcname': 'en',
                  'args': (
                      {'name': 'valu', 'type': 'bytes', 'desc': 'The bytes to be compressed.'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'The zlib compressed bytes.'}}},
        {'name': 'un', 'desc': '''
            Decompress bytes using zlib and return them.

            Example:
                Decompress bytes with zlib::

                $foo = $lib.compression.zlib.un($mybytez)''',
         'type': {'type': 'function', '_funcname': 'un',
                  'args': (
                      {'name': 'valu', 'type': 'bytes', 'desc': 'The bytes to be decompressed.'},
                  ),
                  'returns': {'type': 'bytes', 'desc': 'Decompressed bytes.'}}},
    )

    _storm_lib_path = ('compression', 'zlib')

    def getObjLocals(self):
        return {
            'en': self.en,
            'un': self.un,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def en(self, valu):
        valu = await s_stormtypes.toprim(valu)
        try:
            return zlib.compress(valu)
        except Exception as e:
            mesg = f'Error during zlib compression - {str(e)}: {s_common.trimText(repr(valu))}'
            raise s_exc.StormRuntimeError(mesg=mesg) from None

    async def un(self, valu):
        valu = await s_stormtypes.toprim(valu)
        try:
            return zlib.decompress(valu)
        except Exception as e:
            mesg = f'Error during zlib decompression - {str(e)}: {s_common.trimText(repr(valu))}'
            raise s_exc.StormRuntimeError(mesg=mesg) from None

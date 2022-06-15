import logging

import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

@s_stormtypes.registry.registerLib
class LibCsv(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with csvtool.
    '''
    _storm_locals = (
        {'name': 'emit', 'desc': 'Emit a ``csv:row`` event to the Storm runtime for the given args.',
         'type': {'type': 'function', '_funcname': '_libCsvEmit',
                  'args': (
                      {'name': '*args', 'type': 'any', 'desc': 'Items which are emitted as a ``csv:row`` event.', },
                      {'name': 'table', 'type': 'str', 'default': None,
                       'desc': 'The name of the table to emit data too. Optional.', },
                  ),
                  'returns': {'type': 'null', }}},
    )
    _storm_lib_path = ('csv',)

    def getObjLocals(self):
        return {
            'emit': self._libCsvEmit,
            'reader': self._libCsvReader,
        }

    async def _libCsvEmit(self, *args, table=None):
        row = [await s_stormtypes.toprim(a) for a in args]
        await self.runt.snap.fire('csv:row', row=row, table=table)

    async def _libCsvReader(self, sha256, dialect='excel', **fmtparams):

        self.runt.confirm(('storm', 'lib', 'axon', 'get'))
        await self.runt.snap.core.getAxon()

        sha256 = await s_stormtypes.tostr(sha256)
        dialect = await s_stormtypes.tostr(dialect)
        fmtparams = await s_stormtypes.toprim(fmtparams)
        async for item in self.runt.snap.core.axon.csvrows(sha256, dialect, **fmtparams):
            yield item

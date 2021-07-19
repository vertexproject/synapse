import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class CellLib(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with Json data.
    '''
    _storm_locals = (
        {'name': 'getCellInfo', 'desc': 'Return metadata specific for the Cortex.',
         'type': {'type': 'function', '_funcname': '_getCellInfo', 'args': (),
                  'returns': {'type': 'dict', 'desc': 'A dictionary containing metadata.', }}},
        {'name': 'getBackupInfo', 'desc': 'Get information about recent backup activity.',
         'type': {'type': 'function', '_funcname': '_getBackupInfo', 'args': (),
                  'returns': {'type': 'dict', 'desc': 'A dictionary containing backup information.', }}},
        {'name': 'getSystemInfo', 'desc': 'Get info about the system in which the Cortex is running.',
         'type': {'type': 'function', '_funcname': '_getSystemInfo', 'args': (),
                  'returns': {'type': 'dict', 'desc': 'A dictionary containing system information.', }}},
        {'name': 'getHealthCheck', 'desc': 'Get healthcheck information about the Cortex.',
         'type': {'type': 'function', '_funcname': '_getHealthCheck', 'args': (),
                  'returns': {'type': 'dict', 'desc': 'A dictionary containing healthcheck information.', }}},
    )
    _storm_lib_path = ('cell',)

    def getObjLocals(self):
        return {
            'getCellInfo': self._getCellInfo,
            'getBackupInfo': self._getBackupInfo,
            'getSystemInfo': self._getSystemInfo,
            'getHealthCheck': self._getHealthCheck,
        }

    async def _getCellInfo(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getCellInfo() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg)
        return await self.runt.snap.core.getCellInfo()

    async def _getSystemInfo(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getSystemInfo() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg)
        return await self.runt.snap.core.getSystemInfo()

    async def _getBackupInfo(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getBackupInfo() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg)
        return await self.runt.snap.core.getBackupInfo()

    async def _getHealthCheck(self):
        if not self.runt.isAdmin():
            mesg = '$lib.cell.getHealthCheck() requires admin privs.'
            raise s_exc.AuthDeny(mesg=mesg)
        return await self.runt.snap.core.getHealthCheck()

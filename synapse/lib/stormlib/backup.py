import synapse.common as s_common
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class BackupLib(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with the backup APIs in the Cortex.
    '''
    _storm_lib_path = ('backup',)

    def getObjLocals(self):
        return {
            'run': self._runBackup,
            'list': self._listBackups,
            'del': self._delBackup,
        }

    async def _runBackup(self, name=None, wait=True):
        '''
        Run a cortex backup.

        Args:
            name (str): The name of the backup to generate.

            wait (bool): If true, wait for the backup to complete before returning.

        Returns:
            str: The name of the newly created backup.
        '''
        name = await s_stormtypes.tostr(name, noneok=True)
        wait = await s_stormtypes.tobool(wait)

        todo = s_common.todo('runBackup', name=name, wait=wait)
        gatekeys = ((self.runt.user.iden, ('backup', 'run'), None),)
        return await self.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _listBackups(self):
        '''
        Returns a list of backup names.

        Returns:
            list[str]: A list of backup names.
        '''
        todo = s_common.todo('getBackups')
        gatekeys = ((self.runt.user.iden, ('backup', 'list'), None),)
        return await self.dyncall('cortex', todo, gatekeys=gatekeys)

    async def _delBackup(self, name):
        '''
        Remove a backup by name.

        Args:
            name (str): The name of the backup to remove.
        '''
        name = await s_stormtypes.tostr(name)
        todo = s_common.todo('delBackup', name)
        gatekeys = ((self.runt.user.iden, ('backup', 'del'), None),)
        return await self.dyncall('cortex', todo, gatekeys=gatekeys)

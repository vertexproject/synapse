import synapse.common as s_common
import synapse.lib.version as s_version
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class VersionLib(s_stormtypes.Lib):

    _storm_lib_path = ('version',)

    def getObjLocals(self):
        return {
            'synapse': self._getSynVersion,
            # TODO check dep ranges etc...
        }

    async def _getSynVersion(self):
        '''
        Return the synapse version tuple for the local cortex.

        Returns:
            tuple: A version tripple.
        '''
        return s_version.version

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.version as s_version
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class VersionLib(s_stormtypes.Lib):

    _storm_lib_path = ('version',)

    def getObjLocals(self):
        return {
            'matches': self.matches,
            'synapse': self._getSynVersion,
        }

    async def _getSynVersion(self):
        '''
        Return the synapse version tuple for the local cortex.

        Returns:
            tuple: A version tripple.
        '''
        return s_version.version

    async def matches(self, vertup, reqstr):
        '''
        Return True if the given version tuple meets the requirements string.

        Returns:
            bool: True if the version meets the requirements.

        Examples:
            // Check if the synapse version is in a range
            $synver = $lib.version.synapse()
            if $lib.version.matches($synver, ">=2.9.0") {
                $dostuff()
            }
        '''
        reqstr = await s_stormtypes.tostr(reqstr)
        vertup = tuple(await s_stormtypes.toprim(vertup))
        try:
            s_version.reqVersion(vertup, reqstr)
            return True
        except s_exc.BadVersion:
            return False

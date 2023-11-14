import synapse.exc as s_exc

import synapse.lib.version as s_version
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class VersionLib(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with version information.
    '''
    _storm_locals = (
        {'name': 'synapse',
         'desc': 'The synapse version tuple for the local Cortex.',
         'type': {'type': 'function', '_funcname': '_getSynVersion',
                  'returns': {'type': 'list', 'desc': 'The version triple.', }}},
        {'name': 'commit',
         'desc': 'The synapse commit hash for the local Cortex.',
         'type': {'type': 'function', '_funcname': '_getSynCommit',
                  'returns': {'type': 'str', 'desc': 'The commit hash.', }}},
        {'name': 'matches',
         'desc': '''
            Check if the given version triple meets the requirements string.

            Examples:
                Check if the synapse version is in a range::

                    $synver = $lib.version.synapse()
                    if $lib.version.matches($synver, ">=2.9.0") {
                        $dostuff()
                    }
            ''',
         'type': {'type': 'function', '_funcname': 'matches',
                  'args': (
                      {'name': 'vertup', 'type': 'list', 'desc': 'Triple of major, minor, and patch version integers.', },
                      {'name': 'reqstr', 'type': 'str', 'desc': 'The version string to compare against.', },
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the version meets the requirements, False otherwise.', }}},
    )
    _storm_lib_path = ('version',)

    def getObjLocals(self):
        return {
            'matches': self.matches,
            'commit': self._getSynCommit,
            'synapse': self._getSynVersion,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _getSynVersion(self):
        return s_version.version

    @s_stormtypes.stormfunc(readonly=True)
    async def _getSynCommit(self):
        return s_version.commit

    @s_stormtypes.stormfunc(readonly=True)
    async def matches(self, vertup, reqstr):
        reqstr = await s_stormtypes.tostr(reqstr)
        vertup = tuple(await s_stormtypes.toprim(vertup))
        try:
            s_version.reqVersion(vertup, reqstr)
            return True
        except s_exc.BadVersion:
            return False

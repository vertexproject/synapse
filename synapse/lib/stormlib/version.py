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
         'desc': 'The synapse version string for the local Cortex.',
         'type': 'str'},
        {'name': 'commit',
         'desc': 'The synapse commit hash for the local Cortex.',
         'type': {'type': 'gtor', '_gtorfunc': '_gtorSynCommit',
                  'returns': {'type': 'str', 'desc': 'The commit hash.', }}},
        {'name': 'matches',
         'desc': '''
            Check if the given version string or triple meets the requirements string.

            Examples:
                Check if the synapse version is in a range::

                    $synver = $lib.version.synapse
                    if $lib.version.matches($synver, ">=2.9.0") {
                        $dostuff()
                    }
            ''',
         'type': {'type': 'function', '_funcname': 'matches',
                  'args': (
                      {'name': 'vertup', 'type': ['str', 'list'], 'desc': 'A version string or list of version integers.', },
                      {'name': 'reqstr', 'type': 'str', 'desc': 'The version string to compare against.', },
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the version meets the requirements, False otherwise.', }}},
    )
    _storm_lib_path = ('version',)

    def __init__(self, runt, name=()):
        s_stormtypes.Lib.__init__(self, runt, name=name)
        self.gtors |= {
            'commit': self._gtorSynCommit,
        }

    def getObjLocals(self):
        return {
            'matches': self.matches,
            'synapse': s_version.version,
        }

    async def _gtorSynVersion(self):
        return s_version.version

    async def _gtorSynCommit(self):
        return s_version.commit

    @s_stormtypes.stormfunc(readonly=True)
    async def matches(self, vertup, reqstr):
        reqstr = await s_stormtypes.tostr(reqstr)
        valu = await s_stormtypes.toprim(vertup)
        try:
            s_version.reqVersion(valu, reqstr)
            return True
        except s_exc.BadVersion:
            return False

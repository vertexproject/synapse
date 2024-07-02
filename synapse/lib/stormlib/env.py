import os

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibEnv(s_stormtypes.Lib):
    '''
    A Storm Library for accessing environment vars.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': '''
            Retrieve an environment variable.

            Notes:
                Environment variables must begin with ``SYN_STORM_ENV_`` in
                order to be accessed by this API.
        ''',
         'type': {
            'type': 'function', '_funcname': '_libEnvGet',
            'args': (
                {'name': 'name', 'type': 'str', 'desc': 'The name of the environment variable.', },
                {'name': 'default', 'type': 'obj', 'default': None,
                    'desc': 'The value to return if the environment variable is not set.', },
            ),
         'returns': {'type': 'str', 'desc': 'The environment variable string.'},
         },
        },
    )
    _storm_lib_path = ('env',)

    def getObjLocals(self):
        return {
            'get': self._libEnvGet,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _libEnvGet(self, name, default=None):

        self.runt.reqAdmin(mesg='$lib.env.get() requires admin privileges.')

        name = await s_stormtypes.tostr(name)
        default = await s_stormtypes.toprim(default)

        if not name.startswith('SYN_STORM_ENV_'):
            mesg = f'Environment variable must start with SYN_STORM_ENV_ : {name}'
            raise s_exc.BadArg(mesg=mesg)

        return os.getenv(name, default=default)

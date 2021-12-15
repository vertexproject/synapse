import logging
import ipaddress


import synapse.exc as s_exc

import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

@s_stormtypes.registry.registerLib
class LibIpv6(s_stormtypes.Lib):
    '''
    A Storm Library for providing ipv6 helpers.
    '''
    _storm_locals = (
        {'name': 'expand',
         'desc': '''
         Convert a IPv6 address to its expanded form.''',
         'type': {'type': 'function', '_funcname': '_expand',
                  'args': (
                      {'name': 'valu', 'type': 'str', 'desc': 'IPv6 Address to expand', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The expanded form.', }}},
    )
    _storm_lib_path = ('inet', 'ipv6')

    def getObjLocals(self):
        return {
            'expand': self._expand,
        }

    async def _expand(self, valu):
        valu = await s_stormtypes.tostr(valu)
        valu = valu.strip()
        try:
            ipv6 = ipaddress.IPv6Address(valu)
            return ipv6.exploded
        except ipaddress.AddressValueError as e:
            mesg = f'Error expanding ipv6: {e.args[0]}'
            raise s_exc.StormRuntimeError(mesg, valu=valu)

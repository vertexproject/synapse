import synapse.lib.crypto.coin as s_coin
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class EthereumLib(s_stormtypes.Lib):
    '''
    A Storm library which implements helpers for Ethereum.
    '''
    _storm_locals = (
        {'name': 'eip55', 'desc': 'Convert an Ethereum address to a checksummed address.',
         'type': {'type': 'function', '_funcname': 'eip55',
                  'args': (
                      {'name': 'addr', 'type': 'str', 'desc': 'The Ethereum address to be converted.'},
                  ),
                  'returns': {'type': 'list',
                              'desc': 'A list of (<bool>, <addr>) for status and checksummed address.', },
        }},
    )

    _storm_lib_path = ('crypto', 'coin', 'ethereum')

    def getObjLocals(self):
        return {
            'eip55': self.eip55,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def eip55(self, addr):
        addr = await s_stormtypes.tostr(addr)
        addr = addr.lower()
        if addr.startswith('0x'):
            addr = addr[2:]

        csum = s_coin.ether_eip55(addr)
        if csum is not None:
            return (True, csum)
        return (False, None)

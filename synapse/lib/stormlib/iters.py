import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibIters(s_stormtypes.Lib):
    '''
    A Storm library for providing iterator helpers.
    '''

    _storm_lib_path = ('iters', )
    _storm_locals = (
        {
            'name': 'enum', 'desc': 'Yield (<indx>, <item>) tuples from an iterable or generator.',
             'type': {
                'type': 'function', '_funcname': 'enum',
                'args': (
                    {'type': 'iter', 'name': 'genr', 'desc': 'An iterable or generator.'},
                ),
                'returns': {'name': 'yields', 'type': 'list',
                            'desc': 'Yields (<indx>, <item>) tuples.'},
            }
        },
    )

    def __init__(self, runt, name=()):
        s_stormtypes.Lib.__init__(self, runt, name)

    def getObjLocals(self):
        return {
            'enum': self.enum,
        }

    async def enum(self, genr):
        indx = 0
        async for item in s_stormtypes.toiter(genr):
            yield (indx, item)
            indx += 1

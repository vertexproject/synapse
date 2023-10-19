import asyncio
import inspect
import contextlib

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
        {
            'name': 'zip', 'desc': 'Yield tuples created by iterating multiple iterables in parallel.',
            'type': {
                'type': 'function', '_funcname': '_zip',
                'args': (
                    {'name': '*args', 'type': 'iter', 'desc': 'Iterables or generators.', },
                ),
                'returns': {'name': 'yields', 'type': 'list',
                            'desc': 'Yields tuples with an item from each iterable or generator.'},
            }
        },
    )

    def __init__(self, runt, name=()):
        s_stormtypes.Lib.__init__(self, runt, name)

    def getObjLocals(self):
        return {
            'enum': self.enum,
            'zip': self._zip,
        }

    async def enum(self, genr):
        indx = 0
        async for item in s_stormtypes.toiter(genr):
            yield (indx, item)
            indx += 1

    async def _zipNodegenr(self, genr):
        async for node, path in genr:
            yield node

    async def _zip(self, *args):

        async with contextlib.AsyncExitStack() as stack:
            genrs = []
            for arg in args:
                if inspect.isasyncgen(arg) and arg.__name__ == 'nodegenr':
                    agen = contextlib.aclosing(self._zipNodegenr(arg))
                    genr = await stack.enter_async_context(agen)
                else:
                    agen = contextlib.aclosing(s_stormtypes.toiter(arg))
                    genr = await stack.enter_async_context(agen
)
                genrs.append(genr)

            try:
                while True:
                    yield await asyncio.gather(*[genr.__anext__() for genr in genrs])
            except StopAsyncIteration:
                pass

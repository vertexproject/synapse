import sys
import asyncio
import contextlib

import synapse.exc as s_exc

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

    @s_stormtypes.stormfunc(readonly=True)
    async def enum(self, genr):
        indx = 0
        async for item in s_stormtypes.toiter(genr):
            yield (indx, item)
            indx += 1

    @s_stormtypes.stormfunc(readonly=True)
    async def _zip(self, *args):

        async with contextlib.AsyncExitStack() as stack:
            genrs = []
            for arg in args:
                agen = contextlib.aclosing(s_stormtypes.toiter(arg))
                genrs.append(await stack.enter_async_context(agen))

            try:
                try:
                    while True:
                        tasks = []
                        async with asyncio.TaskGroup() as tg:
                            for genr in genrs:
                                tasks.append(tg.create_task(genr.__anext__()))

                        yield [task.result() for task in tasks]

                        await asyncio.sleep(0)
                        tasks.clear()

                except* StopAsyncIteration:
                    pass

            except ExceptionGroup as eg:
                msgs = []
                for exc in eg.exceptions:
                    if isinstance(exc, s_exc.SynErr):
                        msgs.append(f'({exc.errname}: {exc.errinfo.get("mesg")})')
                    else:
                        msgs.append(f'({exc.__class__.__name__}: {str(exc)})')

                errs = len(msgs)
                errm = ', '.join(msgs)
                mesg = f'$lib.iters.zip() encountered errors in {errs} iterators during iteration: {errm}'
                raise s_exc.StormRuntimeError(mesg=mesg)

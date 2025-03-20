import asyncio

import synapse.exc as s_exc

import synapse.lib.ast as s_ast
import synapse.lib.cache as s_cache
import synapse.lib.stormctrl as s_stormctrl
import synapse.lib.stormtypes as s_stormtypes

CACHE_SIZE_MAX = 10_000
CACHE_SIZE_DEFAULT = 10_000

@s_stormtypes.registry.registerLib
class LibCache(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with Cache Objects.
    '''
    _storm_locals = (
        {'name': 'fixed', 'desc': '''
            Get a new Fixed Cache object.

            On a cache-miss when calling .get(), the callback Storm query is executed in a sub-runtime
            in the current execution context. A special variable, $cache_key, will be set
            to the key argument provided to .get().

            The callback Storm query must contain a return statement, and if it does not return a value
            when executed with the input, ``(null)`` will be set as the value.

            The fixed cache uses FIFO to evict items once the maximum size is reached.

            Examples:

                // Use a callback query with a function that modifies the outer runtime,
                // since it will run in the scope where it was defined.
                $test = foo

                function callback(key) {
                    $test = $key // this will modify $test in the outer runtime
                    return(`{$key}-val`)
                }

                $cache = $lib.cache.fixed(${ return($callback($cache_key)) })
                $value = $cache.get(bar)
                $lib.print($test) // this will equal "bar"

                // Use a callback query that will not modify the outer runtime,
                // except for variables accessible as references.
                $test = foo
                $tests = ([])

                $cache = $lib.cache.fixed(${
                    $test = $cache_key        // this will *not* modify $test in the outer runtime
                    $tests.append($cache_key) // this will modify $tests in the outer runtime
                    return(`{$cache_key}-val`)
                })

                $value = $cache.get(bar)
                $lib.print($test)  // this will equal "foo"
                $lib.print($tests) // this will equal (foo,)
            ''',
         'type': {'type': 'function', '_funcname': '_methFixedCache',
                  'args': (
                      {'name': 'callback', 'type': ['str', 'storm:query'],
                       'desc': 'A Storm query that will return a value for $cache_key on a cache miss.', },
                      {'name': 'size', 'type': 'int', 'default': CACHE_SIZE_DEFAULT,
                       'desc': 'The maximum size of the cache.', },
                  ),
                  'returns': {'type': 'cache:fixed', 'desc': 'A new ``cache:fixed`` object.'}}},
    )
    _storm_lib_path = ('cache',)

    def getObjLocals(self):
        return {
            'fixed': self._methFixedCache,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methFixedCache(self, callback, size=CACHE_SIZE_DEFAULT):
        size = await s_stormtypes.toint(size)
        callback = await s_stormtypes.tostr(callback)

        if size < 1 or size > CACHE_SIZE_MAX:
            raise s_exc.BadArg(mesg=f'Cache size must be between 1-{CACHE_SIZE_MAX}')

        try:
            query = await self.runt.getStormQuery(callback)
        except s_exc.BadSyntax as e:
            raise s_exc.BadArg(mesg=f'Invalid callback query: {e.errinfo.get("mesg")}')

        if not query.hasAstClass(s_ast.Return):
            raise s_exc.BadArg(mesg='Callback query must return a value')

        return FixedCache(self.runt, query, size=size)

@s_stormtypes.registry.registerType
class FixedCache(s_stormtypes.StormType):
    '''
    A StormLib API instance of a Storm Fixed Cache.
    '''
    _storm_locals = (
        {'name': 'query', 'desc': 'Get the callback Storm query as string.',
         'type': {'type': 'gtor', '_gtorfunc': '_gtorQuery',
                  'returns': {'type': 'str', 'desc': 'The callback Storm query text.', }}},
        {'name': 'get', 'desc': 'Get an item from the cache by key.',
         'type': {'type': 'function', '_funcname': '_methGet',
                  'args': (
                      {'name': 'key', 'type': 'any', 'desc': 'The key to lookup.'},
                  ),
                  'returns': {'type': 'any',
                              'desc': 'The value from the cache, or the callback query if it does not exist', }}},
        {'name': 'pop', 'desc': 'Pop an item from the cache.',
         'type': {'type': 'function', '_funcname': '_methPop',
                  'args': (
                      {'name': 'key', 'type': 'any', 'desc': 'The key to pop.'},
                  ),
                  'returns': {'type': 'any',
                              'desc': 'The value from the cache, or ``(null)`` if it does not exist', }}},
        {'name': 'put', 'desc': 'Put an item into the cache.',
         'type': {'type': 'function', '_funcname': '_methPut',
                  'args': (
                      {'name': 'key', 'type': 'any', 'desc': 'The key put in the cache.'},
                      {'name': 'value', 'type': 'any', 'desc': 'The value to assign to the key.'},
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'clear', 'desc': 'Clear all items from the cache.',
         'type': {'type': 'function', '_funcname': '_methClear',
                  'returns': {'type': 'null', }}},
    )
    _storm_typename = 'cache:fixed'
    _ismutable = False

    def __init__(self, runt, query, size=CACHE_SIZE_DEFAULT):
        s_stormtypes.StormType.__init__(self)
        self.runt = runt
        self.size = size
        self.query = query
        self.locls.update(self.getObjLocals())
        self.gtors.update({
            'query': self._gtorQuery,
        })

        self.cache = s_cache.FixedCache(self._runCallback, size=size)

    def __len__(self):
        return len(self.cache)

    async def stormrepr(self):
        if len(qtext := self.query.text) > 100:
            qtext = qtext[:100] + '...'
        return f'{self._storm_typename}: size={self.size} query="{qtext}"'

    def getObjLocals(self):
        return {
            'pop': self._methPop,
            'put': self._methPut,
            'get': self._methGet,
            'clear': self._methClear,
        }

    async def _gtorQuery(self):
        return self.query.text

    async def _runCallback(self, key):

        varz = self.runt.getScopeVars()
        varz['cache_key'] = key

        opts = {'vars': varz}
        async with self.runt.getCmdRuntime(self.query, opts=opts) as runt:
            try:
                async for _ in runt.execute():
                    await asyncio.sleep(0)
            except s_stormctrl.StormReturn as e:
                return await s_stormtypes.toprim(e.item)
            except s_stormctrl.StormCtrlFlow as e:
                name = e.__class__.__name__
                if hasattr(e, 'statement'):
                    name = e.statement
                exc = s_exc.StormRuntimeError(mesg=f'Storm control flow "{name}" not allowed in cache callbacks.')
                raise exc from None

    async def _reqKey(self, key):
        if s_stormtypes.ismutable(key):
            mesg = 'Mutable values are not allowed as cache keys'
            raise s_exc.BadArg(mesg=mesg, name=await s_stormtypes.torepr(key))
        return await s_stormtypes.toprim(key)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPop(self, key):
        key = await self._reqKey(key)
        return self.cache.pop(key)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPut(self, key, value):
        key = await self._reqKey(key)
        val = await s_stormtypes.toprim(value)
        self.cache.put(key, val)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methGet(self, key):
        key = await self._reqKey(key)
        return await self.cache.aget(key)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methClear(self):
        self.cache.clear()

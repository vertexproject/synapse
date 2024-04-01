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

            When the callback Storm query is executed a special variable,
            $cache_key, will be set. The query must return a value.

            The fixed cache uses FIFO to evict items once the maximum size is reached.

            Examples:

                // Use a simple query as the callback
                $cache = $lib.cache.fixed(${ return(`a value for key={$cache_key}`) })
                $value = $cache.get(mykey)  // $value = "a value for key=mykey"

                // Print the number of items in the cache
                $lib.print(`There are {$lib.len($cache)} items in the cache`)
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
                              'desc': 'The value from the cache, or $lib.null if it does not exist', }}},
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

    async def _runCallback(self, key):
        opts = {'vars': {'cache_key': key}}
        async with self.runt.getSubRuntime(self.query, opts=opts) as subr:
            try:
                async for _ in subr.execute():
                    await asyncio.sleep(0)
            except s_stormctrl.StormReturn as e:
                return await s_stormtypes.toprim(e.item)

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

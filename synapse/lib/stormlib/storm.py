import logging

import synapse.exc as s_exc

import synapse.lib.storm as s_storm
import synapse.lib.stormtypes as s_stormtypes

evaldesc = '''\
Evaluate a storm runtime value and optionally cast/coerce it.

NOTE: If storm logging is enabled, the expression being evaluated will be logged
separately.
'''

stormlogger = logging.getLogger('synapse.storm')

@s_stormtypes.registry.registerLib
class LibStorm(s_stormtypes.Lib):
    '''
    A Storm library for evaluating dynamic storm expressions.
    '''
    _storm_locals = (
        {'name': 'eval', 'desc': evaldesc,
         'type': {'type': 'function', '_funcname': '_evalStorm',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'A storm expression string.'},
                      {'name': 'cast', 'type': 'str', 'desc': 'A type to cast the result to.', 'default': None},
                  ),
                  'returns': {'type': 'any', 'desc': 'The value of the expression and optional cast.', }}},
    )
    _storm_lib_path = ('storm',)

    def getObjLocals(self):
        return {
            'eval': self._evalStorm,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _evalStorm(self, text, cast=None):

        text = await s_stormtypes.tostr(text)
        cast = await s_stormtypes.tostr(cast, noneok=True)

        if self.runt.snap.core.stormlog:
            extra = await self.runt.snap.core.getLogExtra(text=text)
            stormlogger.info(f'Executing storm query via $lib.storm.eval() {{{text}}} as [{self.runt.user.name}]', extra=extra)

        casttype = None
        if cast:

            casttype = self.runt.model.type(cast)
            if casttype is None:
                castprop = self.runt.model.prop(cast)
                if castprop is not None:
                    casttype = castprop.type

            if casttype is None:
                mesg = f'No type or property found for name: {cast}'
                raise s_exc.NoSuchType(mesg=mesg)

        asteval = await self.runt.snap.core._getStormEval(text)
        valu = await asteval.compute(self.runt, None)

        if casttype:
            valu, _ = casttype.norm(valu)

        return valu

class StormPoolSetCmd(s_storm.Cmd):
    '''
    Setup a Storm query offload mirror pool for the Cortex.
    '''
    name = 'storm.pool.set'
    def getArgParser(self):
        pars = s_storm.Cmd.getArgParser(self)
        pars.add_argument('--connection-timeout', type='int', default=2,
            help='The maximum amount of time to wait for a connection from the pool to become available.')
        pars.add_argument('--sync-timeout', type='int', default=2,
            help='The maximum amount of time to wait for the mirror to be in sync with the leader')
        pars.add_argument('url', type='str', required=True, help='The telepath URL for the AHA service pool.')
        return pars

    async def execStormCmd(self, runt, genr):

        if not self.runtsafe: # pragma: no cover
            mesg = 'storm.pool.set arguments must be runtsafe.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        if not self.runt.isAdmin(): # pragma: no cover
            mesg = 'storm.pool.set command requires global admin permissions.'
            raise s_exc.AuthDeny(mesg=mesg)

        async for node, path in genr: # pragma: no cover
            yield node, path

        opts = {
            'timeout:sync': self.opts.sync_timeout,
            'timeout:connection': self.opts.connection_timeout,
        }

        await self.runt.snap.core.setStormPool(self.opts.url, opts)
        await self.runt.printf('Storm pool configuration set.')

class StormPoolDelCmd(s_storm.Cmd):
    '''
    Remove a Storm query offload mirror pool configuration.
    '''
    name = 'storm.pool.del'

    async def execStormCmd(self, runt, genr):

        if not self.runt.isAdmin(): # pragma: no cover
            mesg = 'storm.pool.del command requires global admin permissions.'
            raise s_exc.AuthDeny(mesg=mesg)

        async for node, path in genr: # pragma: no cover
            yield node, path

        await self.runt.snap.core.delStormPool()
        await self.runt.printf('Storm pool configuration removed.')

class StormPoolGetCmd(s_storm.Cmd):
    '''
    Display the current Storm query offload mirror pool configuration.
    '''
    name = 'storm.pool.get'

    async def execStormCmd(self, runt, genr):

        if not self.runt.isAdmin(): # pragma: no cover
            mesg = 'storm.pool.get command requires global admin permissions.'
            raise s_exc.AuthDeny(mesg=mesg)

        async for node, path in genr: # pragma: no cover
            yield node, path

        item = await self.runt.snap.core.getStormPool()
        if item is None:
            await self.runt.printf('No Storm pool configuration found.')
            return

        url, opts = item

        await self.runt.printf(f'Storm Pool URL: {url}')
        await self.runt.printf(f'Sync Timeout (secs): {opts.get("timeout:sync")}')
        await self.runt.printf(f'Connection Timeout (secs): {opts.get("timeout:connection")}')

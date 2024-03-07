import logging

import synapse.exc as s_exc

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

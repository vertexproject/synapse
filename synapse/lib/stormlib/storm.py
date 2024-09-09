import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.storm as s_storm
import synapse.lib.stormctrl as s_stormctrl
import synapse.lib.stormtypes as s_stormtypes

evaldesc = '''\
Evaluate a Storm runtime value and optionally cast/coerce it.

Note:
    If Storm logging is enabled, the expression being evaluated will be logged
    separately.
'''

rundesc = '''
Run a Storm query and yield the messages output by the Storm interpreter.

Note:
    If Storm logging is enabled, the query being run will be logged separately.
'''

subqdesc = '''
Run a Storm query as a subquery of the current runtime and return back either the value of an explicit Storm return statement or a list of the NDef values.

Note:
    If Storm logging is enabled, the query being run will be logged separately.
'''

stormlogger = logging.getLogger('synapse.storm')

class StormExecCmd(s_storm.Cmd):
    '''
    Execute text or an embedded query object as Storm in the current pipeline.

    NOTE: It is recommended to avoid using this where possible to avoid potential
    query injection risks. If you must use this, take care to ensure any values
    being executed have been properly sanitized.

    Examples:

        // Add nodes using text in a variable
        $query = '[ inet:fqdn=foo.com inet:fqdn=bar.net ]'
        storm.exec $query

        // Filter nodes in the pipeline using text in a variable
        $filter = '-:asn=10'
        inet:ipv4:asn
        storm.exec $filter

        // Pivot using an embedded query
        $pivot = ${ -> inet:asn }
        inet:ipv4:asn
        storm.exec $pivot
    '''
    name = 'storm.exec'
    def getArgParser(self):
        pars = s_storm.Cmd.getArgParser(self)
        pars.add_argument('query', help='The Storm to execute.')
        return pars

    async def execStormCmd(self, runt, genr):

        if self.runtsafe:

            text = await s_stormtypes.tostr(self.opts.query)
            query = await runt.getStormQuery(text)

            extra = await self.runt.snap.core.getLogExtra(text=text, view=self.runt.snap.view.iden)
            stormlogger.info(f'Executing storm query via storm.exec {{{text}}} as [{self.runt.user.name}]', extra=extra)

            async with runt.getSubRuntime(query) as subr:
                async for subp in subr.execute(genr=genr):
                    yield subp

        else:

            item = None
            async for item in genr:
                break

            text = await s_stormtypes.tostr(self.opts.query)
            query = await runt.getStormQuery(text)

            extra = await self.runt.snap.core.getLogExtra(text=text, view=self.runt.snap.view.iden)
            stormlogger.info(f'Executing storm query via storm.exec {{{text}}} as [{self.runt.user.name}]', extra=extra)

            async with runt.getSubRuntime(query) as subr:
                async for subp in subr.execute(genr=s_common.agen(item)):
                    yield subp

                async for item in genr:
                    text = await s_stormtypes.tostr(self.opts.query)
                    query = await runt.getStormQuery(text)

                    subr.runtvars.clear()
                    subr.query = query
                    subr._initRuntVars(query)

                    extra = await self.runt.snap.core.getLogExtra(text=text, view=self.runt.snap.view.iden)
                    stormlogger.info(f'Executing storm query via storm.exec {{{text}}} as [{self.runt.user.name}]', extra=extra)

                    async for subp in subr.execute(genr=s_common.agen(item)):
                        yield subp

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
                  'returns': {'type': 'any', 'desc': 'The value of the expression and optional cast.'}}},
        {'name': 'run', 'desc': rundesc,
         'type': {'type': 'function', '_funcname': '_runStorm',
                  'args': (
                      {'name': 'query', 'type': 'str', 'desc': 'A Storm query string.'},
                      {'name': 'opts', 'type': 'dict', 'desc': 'Storm options dictionary.', 'default': None},
                  ),
                  'returns': {'name': 'yields', 'type': 'list', 'desc': 'The output messages from the Storm runtime.'}}},
        {'name': 'subquery', 'desc': subqdesc,
         'type': {'type': 'function', '_funcname': '_subquery',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'A Storm query string.'},
                      {'name': 'limit', 'type': 'int', 'desc': 'The number of nodes to allow.', 'default': 1},
                      {'name': 'opts', 'type': 'dict', 'desc': 'Storm options dictionary.', 'default': None},
                  ),
                  'returns': {'type': 'any', 'desc': 'The value of an explict Storm return or a list of the NDef values of the yielded nodes.'}}}
    )
    _storm_lib_path = ('storm',)

    def getObjLocals(self):
        return {
            'run': self._runStorm,
            'eval': self._evalStorm,
            'subquery': self._subquery
        }

    async def _runStorm(self, query, opts=None):

        opts = await s_stormtypes.toprim(opts)
        query = await s_stormtypes.tostr(query)

        if opts is None:
            opts = {}

        user = opts.get('user')
        if user is None:
            user = opts['user'] = self.runt.user.iden

        if user != self.runt.user.iden:
            self.runt.confirm(('impersonate',))

        opts.setdefault('view', self.runt.snap.view.iden)

        async for mesg in self.runt.snap.view.core.storm(query, opts=opts):
            yield mesg

    @s_stormtypes.stormfunc(readonly=True)
    async def _evalStorm(self, text, cast=None):

        text = await s_stormtypes.tostr(text)
        cast = await s_stormtypes.tostr(cast, noneok=True)

        if self.runt.snap.core.stormlog:
            extra = await self.runt.snap.core.getLogExtra(text=text, view=self.runt.snap.view.iden)
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

    @s_stormtypes.stormfunc(readonly=True)
    async def _subquery(self, text, limit=1, opts=None):
        limit = await s_stormtypes.toint(limit)
        opts = await s_stormtypes.toprim(opts)
        text = await s_stormtypes.tostr(text)

        if self.runt.snap.core.stormlog:
            extra = await self.runt.snap.core.getLogExtra(text=text, view=self.runt.snap.view.iden)
            stormlogger.info(f'Executing storm query via $lib.storm.subquery() {{{text}}} as [{self.runt.user.name}]', extra=extra)

        query = await self.runt.getStormQuery(text)
        async with self.runt.getSubRuntime(query, opts=opts) as subr:
            retn = []
            try:
                async for valunode, valupath in subr.execute():
                    retn.append(valunode.ndef[1])
                    if len(retn) > limit:
                        mesg = f'Subquery used as a value yielded too many (>{limit}) nodes. {s_common.trimText(text)}'
                        raise s_exc.StormRuntimeError(mesg=mesg, text=text)
            except s_stormctrl.StormReturn as e:
                return e.item
            return retn

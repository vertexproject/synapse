import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.storm as s_storm
import synapse.lib.stormlint as s_stormlint
import synapse.lib.stormtypes as s_stormtypes
import synapse.lib.processpool as s_processpool

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

lintdesc = '''
Lint Storm code and yield a dictionary for each finding.

Each finding has the keys rule, severity, line, column and mesg, and the
findings are sorted by line, column and rule. A syntax error yields an E001
finding. Form and property names are checked against the Cortex data model,
including extended model elements.

Example:
    Print the findings for a Storm query::

        for $finding in $lib.storm.lint($text) {
            $lib.print(`{$finding.line}:{$finding.column} {$finding.rule} {$finding.mesg}`)
        }
'''

def _lintStorm(text, includes, excludes, names, v3ready):
    linter = s_stormlint.StormLinter(enable=includes, ignore=excludes, v3ready=v3ready)
    linter.names = names
    return [f._asdict() for f in linter.lint(text)]

class StormExecCmd(s_storm.Cmd):
    '''
    Execute text or an embedded query object as Storm in the current pipeline.

    NOTE: It is recommended to avoid using this where possible to avoid potential
    query injection risks. If you must use this, take care to ensure any values
    being executed have been properly sanitized.

    NOTE: If Storm logging is enabled, the query being executed will be logged
    separately.

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

            self.runt.snap.core._logStormQuery(text, self.runt.user, info={'view': self.runt.snap.view.iden},
                                               via='storm.exec')

            async with runt.getSubRuntime(query) as subr:
                async for subp in subr.execute(genr=genr):
                    yield subp

        else:

            item = None
            async for item in genr:
                break

            text = await s_stormtypes.tostr(self.opts.query)
            query = await runt.getStormQuery(text)

            self.runt.snap.core._logStormQuery(text, self.runt.user, info={'view': self.runt.snap.view.iden},
                                               via='storm.exec')

            async with runt.getSubRuntime(query) as subr:
                async for subp in subr.execute(genr=s_common.agen(item)):
                    yield subp

                async for item in genr:
                    text = await s_stormtypes.tostr(self.opts.query)
                    query = await runt.getStormQuery(text)

                    subr.runtvars.clear()
                    subr.query = query
                    subr._initRuntVars(query)

                    self.runt.snap.core._logStormQuery(text, self.runt.user, info={'view': self.runt.snap.view.iden},
                                                       via='storm.exec')

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
        {'name': 'lint', 'desc': lintdesc,
         'type': {'type': 'function', '_funcname': '_lintStorm',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The Storm code to lint.'},
                      {'name': 'includes', 'type': 'list', 'default': None,
                       'desc': 'Rule IDs or ID prefixes to add to the default rule set, including rules which are '
                               'off by default such as S010 and S015. The default rules still run.'},
                      {'name': 'excludes', 'type': 'list', 'default': None,
                       'desc': 'Rule IDs or ID prefixes to remove from the rule set. '
                               'Applied last, after includes and v3ready.'},
                      {'name': 'v3ready', 'type': 'boolean', 'default': False,
                       'desc': 'Add every rule which reports Storm that must change for Synapse 3.x, '
                               'the same as storm.lint --v3-ready.'},
                  ),
                  'returns': {'name': 'yields', 'type': 'dict',
                              'desc': 'A dictionary for each finding, with the keys rule, severity, line, column and mesg.'}}},
    )
    _storm_lib_path = ('storm',)

    def getObjLocals(self):
        return {
            'run': self._runStorm,
            'eval': self._evalStorm,
            'lint': self._lintStorm,
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

        self.runt.snap.core._logStormQuery(text, self.runt.user, info={'view': self.runt.snap.view.iden},
                                           via='$lib.storm.eval()')

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
    async def _lintStorm(self, text, includes=None, excludes=None, v3ready=False):

        text = await s_stormtypes.tostr(text)
        v3ready = await s_stormtypes.tobool(v3ready)

        includes = await s_stormtypes.toprim(includes)
        if includes is None:
            includes = ()

        excludes = await s_stormtypes.toprim(excludes)
        if excludes is None:
            excludes = ()

        names = s_stormlint._getModelNames(self.runt.model.getModelDict())

        findings = await s_processpool.semafork(_lintStorm, text, includes, excludes, names, v3ready)
        for finding in findings:
            yield finding

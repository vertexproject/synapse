import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.storm as s_storm
import synapse.lib.stormlint as s_stormlint
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

lintdesc = '''
Lint Storm code and yield a dictionary for each finding.

Findings are checked against the data model of the Cortex, including extended model
elements. Each finding is a dictionary with the keys rule, severity, line, column and mesg,
sorted by line, column and rule. A syntax error yields an E001 finding.

The select, enable and ignore arguments match the --select, --enable and --ignore
options of the storm.lint command line tool, the keys of its [tool.stormlint]
configuration table and the arguments of the MCP storm_lint tool. Each entry is a rule
ID or an ID prefix, and an unknown rule ID or prefix raises a BadArg error.

When text is an embedded query, its text is linted, and the line and column of each
finding are relative to the text of the embedded query.

Examples:
    Print the findings for a query::

        for $finding in $lib.storm.lint.scan($text) {
            $lib.print(`{$finding.line}:{$finding.column} {$finding.rule} {$finding.mesg}`)
        }

    Lint an embedded query with only the R rules and S010, which is off by default::

        $query = ${
            if $x { [ :name=$x ] }
        }
        for $finding in $lib.storm.lint.scan($query, select=(R,), enable=(S010,)) {
            $lib.print(`{$finding.line}:{$finding.column} {$finding.rule} {$finding.mesg}`)
        }
'''

lintrulesdesc = '''
Get the lint rules used by $lib.storm.lint.scan().

Each rule is a dictionary with the keys rule (the rule ID), name, severity, default
(true when the rule runs by default) and desc (the rule description), in rule ID order.

Examples:
    Print the rules which are off by default::

        for $rule in $lib.storm.lint.rules() {
            if (not $rule.default) { $lib.print(`{$rule.rule} {$rule.name}`) }
        }
'''

async def _getLintFindings(runt, text, select, ignore, enable):

    for name, valu in (('select', select), ('ignore', ignore), ('enable', enable)):

        if valu is None and name == 'select':
            continue

        if not isinstance(valu, (list, tuple)) or not all(isinstance(v, str) for v in valu):
            raise s_exc.BadArg(mesg=f'{name} must be a list of rule IDs or ID prefixes.', name=name)

    mdef = runt.model.getModelDict()
    return await s_stormlint.lintAsync(text, select=select, ignore=ignore, enable=enable, model=mdef)

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
        inet:ip:asn
        storm.exec $filter

        // Pivot using an embedded query
        $pivot = ${ -> inet:asn }
        inet:ip:asn
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

            self.runt.view.core._logStormQuery(text, self.runt.user, info={'view': self.runt.view.iden},
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

            self.runt.view.core._logStormQuery(text, self.runt.user, info={'view': self.runt.view.iden},
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

                    self.runt.view.core._logStormQuery(text, self.runt.user, info={'view': self.runt.view.iden},
                                                       via='storm.exec')

                    async for subp in subr.execute(genr=s_common.agen(item)):
                        yield subp

class StormLintCmd(s_storm.Cmd):
    '''
    Lint Storm code against the data model of the Cortex and print the findings.

    Each finding is printed as <line>:<column>: <rule> <message>, followed by a count of
    the findings, or "All checks passed!" when there are none. When the text is an embedded
    query, the line and column of each finding are relative to the text of the embedded query.

    The --select, --enable and --ignore options each take a comma-separated list of rule IDs
    or ID prefixes, and match the options of the storm.lint command line tool. An unknown
    rule ID or prefix is an error.

    Nodes in the pipeline are passed through unchanged. When the text is not runtsafe, it is
    linted once for each node.

    Examples:

        // Lint Storm code in a variable
        storm.lint $text

        // Lint an embedded query, adding S010 which is off by default
        storm.lint ${ if $x { [ :name=$x ] } } --enable S010

        // Lint with only the R rules
        storm.lint $text --select R

        // Print the lint rules
        storm.lint --show-rules
    '''
    name = 'storm.lint'
    readonly = True

    def getArgParser(self):
        pars = s_storm.Cmd.getArgParser(self)
        pars.add_argument('text', nargs='?', default=s_common.novalu,
                          help='The Storm code or embedded query to lint.')
        pars.add_argument('--select', default=None,
                          help='Comma-separated rule IDs or prefixes to run in place of the default rules.')
        pars.add_argument('--ignore', default=None, help='Comma-separated rule IDs or prefixes to disable.')
        pars.add_argument('--enable', default=None,
                          help='Comma-separated rule IDs or prefixes to add to the selected rules, '
                               'such as rules which are off by default.')
        pars.add_argument('--show-rules', default=False, action='store_true',
                          help='Print the lint rules instead of linting.')
        return pars

    async def _getRules(self, valu):

        valu = await s_stormtypes.tostr(valu, noneok=True)
        if valu is None:
            return None

        return s_stormlint.splitRules(valu)

    async def _lintText(self, runt):

        if self.opts.text is s_common.novalu:
            raise s_exc.BadArg(mesg='storm.lint requires text to lint unless --show-rules is given.', name='text')

        text = await s_stormtypes.tostr(self.opts.text, noneok=True)
        if text is None:
            raise s_exc.BadArg(mesg='storm.lint text is null.', name='text')

        select = await self._getRules(self.opts.select)
        ignore = await self._getRules(self.opts.ignore) or ()
        enable = await self._getRules(self.opts.enable) or ()

        findings = await _getLintFindings(runt, text, select, ignore, enable)

        for f in findings:
            line, column, rule, mesg = f['line'], f['column'], f['rule'], f['mesg']
            await runt.printf(f'{line}:{column}: {rule} {mesg}')

        await runt.printf(s_stormlint.getSummary(len(findings)))

    async def execStormCmd(self, runt, genr):

        if self.opts.show_rules:

            for line in s_stormlint.getRuleTable():
                await runt.printf(line)

        elif self.runtsafe:
            await self._lintText(runt)

        else:
            async for item in genr:
                await self._lintText(runt)
                yield item

            return

        async for item in genr:
            yield item

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
    )
    _storm_lib_path = ('storm',)

    def getObjLocals(self):
        return {
            'run': self._runStorm,
            'eval': self._evalStorm,
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
            self.runt.reqAdmin()

        opts.setdefault('view', self.runt.view.iden)

        async for mesg in self.runt.view.core.storm(query, opts=opts):
            yield mesg

    @s_stormtypes.stormfunc(readonly=True)
    async def _evalStorm(self, text, cast=None):

        text = await s_stormtypes.tostr(text)
        cast = await s_stormtypes.tostr(cast, noneok=True)

        self.runt.view.core._logStormQuery(text, self.runt.user, info={'view': self.runt.view.iden},
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

        asteval = await self.runt.view.core._getStormEval(text)
        valu = await asteval.compute(self.runt, None)

        if casttype:
            valu, _ = await casttype.norm(valu)

        return valu

@s_stormtypes.registry.registerLib
class LibStormLint(s_stormtypes.Lib):
    '''
    A Storm library for linting Storm code.
    '''
    _storm_locals = (
        {'name': 'scan', 'desc': lintdesc,
         'type': {'type': 'function', '_funcname': '_scan',
                  'args': (
                      {'name': 'text', 'type': ['str', 'storm:query'],
                       'desc': 'The Storm code or embedded query to lint.'},
                      {'name': 'select', 'type': 'list', 'default': None,
                       'desc': 'Rule IDs or ID prefixes which replace the default rule set. An empty list '
                               'runs only the enabled rules.'},
                      {'name': 'ignore', 'type': 'list', 'default': None,
                       'desc': 'Rule IDs or ID prefixes to remove from the rule set, applied last.'},
                      {'name': 'enable', 'type': 'list', 'default': None,
                       'desc': 'Rule IDs or ID prefixes to add to the rule set, including rules which are '
                               'off by default such as S010 and S015.'},
                  ),
                  'returns': {'name': 'yields', 'type': 'dict', 'desc': 'A dictionary for each lint finding.'}}},
        {'name': 'rules', 'desc': lintrulesdesc,
         'type': {'type': 'function', '_funcname': '_rules',
                  'returns': {'type': 'list', 'desc': 'A dictionary for each lint rule.'}}},
    )
    _storm_lib_path = ('storm', 'lint')

    def getObjLocals(self):
        return {
            'scan': self._scan,
            'rules': self._rules,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _scan(self, text, select=None, ignore=None, enable=None):

        text = await s_stormtypes.tostr(text, noneok=True)
        if text is None:
            raise s_exc.BadArg(mesg='$lib.storm.lint.scan() requires text to lint.', name='text')

        select = await s_stormtypes.toprim(select)
        ignore = await s_stormtypes.toprim(ignore)
        enable = await s_stormtypes.toprim(enable)

        if ignore is None:
            ignore = ()

        if enable is None:
            enable = ()

        for finding in await _getLintFindings(self.runt, text, select, ignore, enable):
            yield finding

    @s_stormtypes.stormfunc(readonly=True)
    async def _rules(self):
        return s_stormlint.getRules()

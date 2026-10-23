'''
A parse-once, rule-callback linter for Storm code.
'''
import re
import inspect
import warnings
import collections

import synapse.exc as s_exc
import synapse.models as s_models
import synapse.datamodel as s_datamodel

import synapse.lib.ast as s_ast
import synapse.lib.parser as s_parser
import synapse.lib.dyndeps as s_dyndeps

severities = ('high', 'medium', 'low')

Finding = collections.namedtuple('Finding', ('rule', 'severity', 'line', 'column', 'mesg'))

# rule ID -> Rule, kept in ID order
rules = {}

noqare = re.compile(r'//\s*(?i:noqa)\b(?::\s*([\w\s,]*\w))?')

escapere = re.compile(r'\\(.)', re.DOTALL)

# characters which may follow a backslash in a python string literal
escapes = frozenset('\\\'"abfnrtv01234567xuUN\n')
fmtescapes = escapes | {'`', '{'}

constvals = {'true': '(true)', 'false': '(false)', 'null': '(null)'}

# parent nodes in which a parenthesized atom is already inside an open expression
exprparents = (s_ast.DollarExpr, s_ast.ExprNode, s_ast.ExprAndNode, s_ast.ExprOrNode, s_ast.ExprDict, s_ast.ExprList)
exprparens = (s_ast.Const, s_ast.VarValue, s_ast.VarDeref, s_ast.FuncCall, s_ast.ExprDict, s_ast.ExprList,
              s_ast.FormatString)

# values which read the inbound node
nodevals = (s_ast.PropValue, s_ast.TagValue, s_ast.TagVirtValue, s_ast.TagPropValue)

# comparisons which a prop lift supports the same as a filter
liftcmprs = frozenset(('=', '~=', '^=', '<', '>', '<=', '>=', '@=', 'in=', 'range='))

gtorcalls = (
    ('node', 'value'),
    ('node', 'form'),
    ('node', 'ndef'),
    ('lib', 'version', 'synapse'),
    ('lib', 'version', 'commit'),
)

# calls which return an object holding the request headers
httpcalls = frozenset((
    ('lib', 'inet', 'http', 'get'),
    ('lib', 'inet', 'http', 'post'),
    ('lib', 'inet', 'http', 'head'),
    ('lib', 'inet', 'http', 'request'),
    ('lib', 'axon', 'wget'),
    ('lib', 'axon', 'wput'),
))

# calls which output their arguments
printcalls = frozenset((
    ('lib', 'print'),
    ('lib', 'pprint'),
    ('lib', 'warn'),
    ('lib', 'log', 'debug'),
    ('lib', 'log', 'info'),
    ('lib', 'log', 'warning'),
    ('lib', 'log', 'error'),
))

# members of an http response or wget result which hold the request headers
reqkeys = frozenset(('request', 'request_headers', 'history'))

def _apiTable(items):
    return {tuple(name[1:].split('.')): f'{name} was removed{hint}.' for name, hint in items}

# removed libraries and Lib members, reported for any use of the longest matching prefix
removedlibs = _apiTable((
    ('$lib.str', ''),
    ('$lib.str.concat', ', use a backtick format string'),
    ('$lib.str.format', ', use a backtick format string'),
    ('$lib.str.join', ', use (sep).join(items)'),
    ('$lib.text', ', append to a list and join it, or use a backtick format string'),
    ('$lib.user', ', use $lib.auth.users.get()'),
    ('$lib.ps', ', use $lib.task'),
    ('$lib.notifications', ''),
    ('$lib.projects', ''),
    ('$lib.inet.whois', ', use a guid constructor'),
    ('$lib.bytes.put', ', use $lib.axon.put()'),
    ('$lib.bytes.has', ', use $lib.axon.has()'),
    ('$lib.bytes.size', ', use $lib.axon.size()'),
    ('$lib.bytes.hashset', ', use $lib.axon.hashset()'),
    ('$lib.bytes.upload', ', use $lib.axon.upload()'),
    ('$lib.infosec.cvss.calculate', ', use $lib.infosec.cvss.vectToScore() and set the props'),
    ('$lib.infosec.cvss.calculateFromProps', ', use $lib.infosec.cvss.vectToScore() and set the props'),
    ('$lib.infosec.cvss.vectToProps', ', use $lib.infosec.cvss.vectToScore() and set the props'),
    ('$lib.infosec.cvss.saveVectToNode', ', use $lib.infosec.cvss.vectToScore() and set the props'),
    ('$lib.cell.hotFixesApply', ''),
    ('$lib.cell.hotFixesCheck', ''),
    ('$lib.utils.buid', ''),
    ('$lib.cron.move', ', use $lib.cron.mod() with a view edit'),
    ('$lib.cron.enable', ', use $lib.cron.mod() with an enabled edit'),
    ('$lib.cron.disable', ', use $lib.cron.mod() with an enabled edit'),
    ('$lib.trigger.enable', ', use $lib.trigger.mod() with an enabled edit'),
    ('$lib.trigger.disable', ', use $lib.trigger.mod() with an enabled edit'),
))

# removed methods of dict-like objects, whose deref without a call is a key
removedcalls = _apiTable((
    ('$lib.vars.get', ', use $lib.vars.<name>'),
    ('$lib.vars.set', ', assign $lib.vars.<name>'),
    ('$lib.vars.del', ', assign $lib.undef to $lib.vars.<name>'),
    ('$lib.vars.list', ', iterate $lib.vars with a for loop'),
    ('$lib.vars.type', ', use $lib.utils.type()'),
    ('$lib.globals.get', ', use $lib.globals.<name>'),
    ('$lib.globals.set', ', assign $lib.globals.<name>'),
    ('$lib.globals.pop', ', assign $lib.undef to $lib.globals.<name>'),
    ('$lib.globals.list', ', iterate $lib.globals with a for loop'),
    ('$lib.env.get', ', use $lib.env.<NAME>'),
))

# removed methods of any vars object, such as the dict-like user vars
varcalls = {
    'get': 'read vars.<name>',
    'set': 'assign vars.<name>',
    'pop': 'assign $lib.undef to vars.<name>',
    'list': 'iterate vars with a for loop',
}

_model = None

def _getModel():
    '''
    Return the built-in data model, loaded on first use.
    '''
    global _model
    if _model is None:

        mdefs = []
        for path in s_models.modeldefs:
            mdefs.extend(s_dyndeps.getDynLocal(path))

        _model = s_datamodel.Model()
        _model.addModelDefs(mdefs)

    return _model

_modelnames = None

def _getModelNames(model=None):
    '''
    Return the form names and the form and full prop names of a model dict, or of the built-in model.
    '''
    global _modelnames
    if model is None:

        if _modelnames is None:
            modl = _getModel()
            _modelnames = (frozenset(modl.forms), frozenset(modl.props))

        return _modelnames

    forms = model['forms']
    props = set(forms)
    for form in forms.values():
        props.update(prop['full'] for prop in form['props'].values())

    return frozenset(forms), frozenset(props)

def _unparen(node):
    if isinstance(node, s_ast.DollarExpr):
        return node.kids[0]

    return node

class Rule:

    def __init__(self, iden, name, severity, func, default=True):
        self.iden = iden
        self.name = name
        self.severity = severity
        self.default = default
        self.func = func
        self.doc = inspect.cleandoc(func.__doc__ or '')

def rule(iden, name, severity, default=True):
    '''
    Decorator which registers a lint rule callback.

    The callback receives a LintContext and reports findings with ctx.report().
    Its docstring is the rule documentation. A rule with default=False only runs
    when a select or enable entry names it.
    '''
    if severity not in severities:
        raise s_exc.BadArg(mesg=f'Invalid severity for rule {iden}: {severity}')

    if iden in rules:
        raise s_exc.BadArg(mesg=f'Duplicate lint rule: {iden}', name=iden)

    def wrap(func):
        rules[iden] = Rule(iden, name, severity, func, default=default)
        items = sorted(rules.items())
        rules.clear()
        rules.update(items)
        return func

    return wrap

class LintContext:
    '''
    The state passed to each rule callback for one parsed query.
    '''
    def __init__(self, text, query, forms, props):
        self.text = text
        self.query = query
        self.lines = text.split('\n')
        self.findings = []
        self.rule = None
        self.forms = forms
        self.props = props

    def isForm(self, name):
        '''
        Return True if name is a form in the data model being linted against.
        '''
        return name in self.forms

    def isProp(self, name):
        '''
        Return True if name is a form or full prop name in the data model being linted against.
        '''
        return name in self.props

    def walk(self, cls=None, node=None, skip=None):
        '''
        Yield every AST node (pre-order) under node (default: the query), optionally only instances of cls.

        Descendants which are instances of skip are not yielded or descended into.
        '''
        if node is None:
            node = self.query

        todo = [node]
        while todo:

            node = todo.pop()
            if cls is None or isinstance(node, cls):
                yield node

            kids = node.kids
            if skip is not None:
                kids = [k for k in kids if not isinstance(k, skip)]

            todo.extend(reversed(kids))

    def parent(self, node):
        return getattr(node, 'parent', None)

    def derefPath(self, node):
        '''
        Return the names in a constant VarDeref chain ($lib.str.format -> ('lib', 'str', 'format')) or None.
        '''
        names = []
        while isinstance(node, s_ast.VarDeref):

            name = node.kids[1]
            if not isinstance(name, s_ast.Const):
                return None

            names.append(name.valu)
            node = node.kids[0]

        if not isinstance(node, s_ast.VarValue):
            return None

        names.append(node.kids[0].valu)
        return tuple(reversed(names))

    def isDeref(self, node, *names):
        '''
        Return True if node is the constant deref $<names[0]>.<names[1]>...
        '''
        return self.derefPath(node) == names

    def callPath(self, node):
        '''
        Return the deref path of the function a FuncCall invokes, or None.
        '''
        if not isinstance(node, s_ast.FuncCall):
            return None

        return self.derefPath(node.kids[0])

    def getText(self, node):
        '''
        Return the raw source text of node, or None if it has no position.
        '''
        info = node.astinfo
        if not isinstance(info, s_parser.AstInfo) or info.soff < 0:
            return None

        return node.getAstText()

    def getSrc(self, node):
        '''
        Return the raw source text of a positioned node, including the leading $ of a variable.
        '''
        soff = node.astinfo.soff
        if soff > 0 and self.text[soff - 1] == '$':
            soff -= 1

        return self.text[soff:node.astinfo.eoff]

    def getOffsPos(self, offs):
        '''
        Return the 1-based (line, column) of an offset into the text.
        '''
        line = self.text.count('\n', 0, offs) + 1
        column = offs - self.text.rfind('\n', 0, offs)
        return line, column

    def getPos(self, node):
        '''
        Return the 1-based (line, column) of node, using the nearest positioned ancestor when it has none.
        '''
        while node is not None:

            info = node.astinfo
            if isinstance(info, s_parser.AstInfo) and info.sline > 0:

                # VarValue and VarDeref positions exclude the leading $
                if info.soff > 0 and info.text[info.soff - 1] == '$':
                    return info.sline, info.scol - 1

                return info.sline, info.scol

            node = self.parent(node)

        return 1, 1

    def report(self, node, mesg, offs=None):
        '''
        Add a finding at node, or at the text offset offs when given.
        '''
        if offs is None:
            line, column = self.getPos(node)
        else:
            line, column = self.getOffsPos(offs)

        self.findings.append(Finding(self.rule.iden, self.rule.severity, line, column, mesg))

@rule('E001', 'parse-failure', 'high')
def _ruleParseFailure(ctx):
    '''
    The Storm code failed to parse. This finding is always reported and cannot be suppressed.
    '''

@rule('E002', 'invalid-escape', 'high')
def _ruleInvalidEscape(ctx):
    '''
    A double-quoted or backtick string contains a backslash escape which is not a valid Python
    string escape. Single-quoted strings do not process escapes and are not checked.
    '''
    for node in ctx.walk(s_ast.Const):

        if isinstance(node, s_ast.EmbedQuery):
            continue

        text = ctx.getText(node)
        if text is None:
            continue

        # format string text pieces follow the opening backtick or a closing brace
        prev = ctx.text[node.astinfo.soff - 1:node.astinfo.soff]
        if isinstance(ctx.parent(node), s_ast.FormatString) and prev in ('`', '}'):
            valid = fmtescapes

        elif text.startswith('"'):
            valid = escapes

        else:
            continue

        for match in escapere.finditer(text):
            if match.group(1) not in valid:
                offs = node.astinfo.soff + match.start()
                ctx.report(node, f"Invalid escape sequence '{match.group(0)}' in string.", offs=offs)

@rule('E003', 'duplicate-function', 'high')
def _ruleDuplicateFunction(ctx):
    '''
    A function is defined more than once in the same scope.
    '''
    for query in ctx.walk(s_ast.Query):

        seen = {}
        for node in query.kids:

            if not isinstance(node, s_ast.Function):
                continue

            name = node.kids[0].valu
            first = seen.get(name)
            if first is None:
                seen[name] = node
                continue

            line = ctx.getPos(first)[0]
            ctx.report(node, f'Function {name} is already defined on line {line}.')

@rule('R001', 'lib-constant', 'high')
def _ruleLibConstant(ctx):
    '''
    $lib.true, $lib.false and $lib.null were removed in 3.x. Use (true), (false) and (null).
    '''
    for node in ctx.walk(s_ast.VarDeref):

        path = ctx.derefPath(node)
        if path is None or len(path) != 2 or path[0] != 'lib' or path[1] not in constvals:
            continue

        ctx.report(node, f'$lib.{path[1]} was removed, use {constvals[path[1]]}.')

@rule('R002', 'gtor-call', 'high')
def _ruleGtorCall(ctx):
    '''
    $node.value, $node.form, $node.ndef, $lib.version.synapse and $lib.version.commit are gtors
    in 3.x and can not be called. Drop the parentheses.
    '''
    for node in ctx.walk(s_ast.FuncCall):

        path = ctx.callPath(node)
        if path in gtorcalls:
            name = '.'.join(path)
            ctx.report(node, f'${name} is not callable, drop the parentheses.')

@rule('R003', 'node-iden', 'high')
def _ruleNodeIden(ctx):
    '''
    $node.iden was removed in 3.x.
    '''
    for node in ctx.walk(s_ast.VarDeref):
        if ctx.isDeref(node, 'node', 'iden'):
            ctx.report(node, '$node.iden was removed.')

@rule('R004', 'bare-constant', 'medium')
def _ruleBareConstant(ctx):
    '''
    A bare true, false or null used as an assignment value, call argument, return value or
    function argument default is the string "true", "false" or "null". Use (true), (false) or
    (null), or quote the string.
    '''
    for node in ctx.walk():

        kind = type(node)
        if kind in (s_ast.SetVarOper, s_ast.VarListSetOper, s_ast.CallKwarg):
            valus = node.kids[1:]

        elif kind is s_ast.FuncArg:
            valus = (node.defvkid,)

        elif kind is s_ast.SetItemOper:
            valus = node.kids[2:]

        elif kind in (s_ast.Return, s_ast.CallArgs):
            valus = node.kids

        else:
            continue

        for valu in valus:

            if type(valu) is not s_ast.Const or valu.valu not in constvals:
                continue

            if ctx.getText(valu) != valu.valu:
                continue

            ctx.report(valu, f'Bare {valu.valu} is a string, use {constvals[valu.valu]} or quote it.')

def _getRemovedLib(path):
    '''
    Return the message for the longest removed $lib API prefix of a deref path, or None.
    '''
    if path[:2] == ('lib', 'gen') and len(path) > 2 and not path[2].startswith('_'):
        return f'$lib.gen.{path[2]} was removed, use a gen.* command or a guid constructor.'

    for size in range(len(path), 1, -1):
        mesg = removedlibs.get(path[:size])
        if mesg is not None:
            return mesg

    return None

def _derefTail(node):
    '''
    Return the last two constant names of a VarDeref chain ($x.vars.get -> ('vars', 'get')) or None.
    '''
    names = []
    while isinstance(node, s_ast.VarDeref) and len(names) < 2:

        name = node.kids[1]
        if not isinstance(name, s_ast.Const):
            return None

        names.append(name.valu)
        node = node.kids[0]

    if len(names) < 2:
        return None

    return tuple(reversed(names))

@rule('R005', 'removed-api', 'high')
def _ruleRemovedApi(ctx):
    '''
    A $lib API which was removed in 3.x is used, such as $lib.str, $lib.text, $lib.user,
    $lib.ps, $lib.bytes.put() or the $lib.gen helpers. The message names the replacement
    when there is one.

    $lib.vars, $lib.globals, $lib.env and user vars ($user.vars) are dict-like in 3.x, so
    calling get(), set(), pop(), list() and similar methods on them is reported. Read and
    assign $lib.globals.<name>, assign $lib.undef to delete, and iterate with a for loop.
    '''
    for node in ctx.walk(s_ast.VarDeref):

        prnt = ctx.parent(node)
        if isinstance(prnt, s_ast.VarDeref) and prnt.kids[0] is node:
            continue

        path = ctx.derefPath(node)
        if path is None:
            continue

        mesg = _getRemovedLib(path)
        if mesg is not None:
            ctx.report(node, mesg)

    for node in ctx.walk(s_ast.FuncCall):

        path = ctx.callPath(node)
        mesg = removedcalls.get(path)
        if mesg is not None:
            ctx.report(node, mesg)
            continue

        tail = _derefTail(node.kids[0])
        if tail is not None and tail[0] == 'vars' and tail[1] in varcalls:
            ctx.report(node, f'vars.{tail[1]}() was removed, vars are dict-like: {varcalls[tail[1]]}.')

@rule('P001', 'spin', 'low')
def _ruleSpin(ctx):
    '''
    The spin command discards the nodes in the pipeline. Run the query whose nodes are not
    needed in an exec { ... } block, which discards the nodes it yields, or isolate it in a
    function which uses return() or a fini block.
    '''
    for node in ctx.walk(s_ast.CmdOper):
        if node.kids[0].valu == 'spin':
            ctx.report(node, 'Avoid spin, use an exec { ... } block or isolate the query in a function.')

@rule('P002', 'spin-return', 'medium')
def _ruleSpinReturn(ctx):
    '''
    spin | return(...) runs the return after consuming every node. Use return(...) when only one
    node can flow, fini { return(...) } when more than one can, or run the query which yields the
    nodes in an exec { ... } block.
    '''
    for query in ctx.walk(s_ast.Query):
        for prev, node in zip(query.kids, query.kids[1:]):

            if not isinstance(node, s_ast.Return):
                continue

            if isinstance(prev, s_ast.CmdOper) and prev.kids[0].valu == 'spin':
                ctx.report(prev, 'Replace spin | return(...) with return(...) when only one node can flow, '
                                 'fini { return(...) } when more than one can, or run the query which '
                                 'yields the nodes in an exec { ... } block.')

@rule('S001', 'guid-seed', 'medium')
def _ruleGuidSeed(ctx):
    '''
    A guid form node is added with a value from $lib.guid(). Use a list seed such as
    [ form=(a, $b) ], or [ form=* ] for a random guid.

    The resulting guid may differ, so verify it before changing existing code.
    '''
    for node in ctx.walk(s_ast.EditNodeAdd):

        valu = node.kids[2]
        if ctx.callPath(valu) != ('lib', 'guid'):
            continue

        form = ctx.getText(node.kids[0])
        args, kwargs = valu.kids[1:]
        if not args.kids and not kwargs.kids:
            ctx.report(valu, f'Use {form}=* instead of $lib.guid().')
            continue

        ctx.report(valu, f'Use a list seed ({form}=(...)) instead of $lib.guid(), '
                         'after verifying the guid is unchanged.')

@rule('S002', 'unnecessary-parens', 'low')
def _ruleParens(ctx):
    '''
    Parens open an expression. Inside one which is already open, a literal, variable, call, or
    nested dict or list needs no parens of its own, and a lone variable assigned, passed as an
    argument or returned needs none either: ($y) is just $y.

    Parens are still required around a literal value such as (true) or (10), a dict or list
    literal used as a value, and grouping which changes precedence. Grouping a compound
    sub-expression is never reported.
    '''
    for node in ctx.walk(s_ast.DollarExpr):

        prnt = ctx.parent(node)
        kid = node.kids[0]

        nested = isinstance(prnt, exprparents) or (isinstance(prnt, s_ast.UnaryExprNode) and prnt.kids[0].valu == 'not')
        if isinstance(prnt, s_ast.DollarExpr) or (nested and isinstance(kid, exprparens)):
            ctx.report(node, 'Unnecessary parens inside an expression which is already open.')
            continue

        if not isinstance(kid, (s_ast.VarValue, s_ast.VarDeref)):
            continue

        kind = type(prnt)
        if kind in (s_ast.SetVarOper, s_ast.CallKwarg):
            isvalu = prnt.kids[1] is node

        elif kind is s_ast.SetItemOper:
            isvalu = prnt.kids[2] is node

        else:
            isvalu = kind in (s_ast.CallArgs, s_ast.Return)

        if isvalu:
            ctx.report(node, f'Unnecessary parens around a variable, use {ctx.getSrc(kid)}.')

@rule('S003', 'edge-yield', 'low')
def _ruleEdgeYield(ctx):
    '''
    An edge edit uses a subquery which only yields a variable. Use the variable directly,
    such as +(refs)> $v instead of +(refs)> { yield $v }.
    '''
    for node in ctx.walk((s_ast.EditEdgeAdd, s_ast.EditEdgeDel)):

        subq = node.kids[1]
        if not isinstance(subq, s_ast.SubQuery):
            continue

        opers = subq.kids[0].kids
        if len(opers) != 1 or not isinstance(opers[0], s_ast.YieldValu):
            continue

        valu = opers[0].kids[0]
        if not isinstance(valu, s_ast.VarValue):
            continue

        edge = ctx.text[node.astinfo.soff:subq.astinfo.soff].rstrip()
        ctx.report(node, f'Use {edge} ${valu.kids[0].valu} instead of a subquery which only yields it.')

@rule('S004', 'return-null', 'low')
def _ruleReturnNull(ctx):
    '''
    return((null)) and return($lib.null) return the same value as return().
    '''
    for node in ctx.walk(s_ast.Return):

        if not node.kids:
            continue

        valu = node.kids[0]
        if isinstance(valu, s_ast.DollarExpr):
            valu = valu.kids[0]
            if type(valu) is not s_ast.Const or valu.valu is not None:
                continue

        elif not ctx.isDeref(valu, 'lib', 'null'):
            continue

        ctx.report(node, 'Use return() to return (null).')

@rule('S005', 'lib-list-dict', 'low')
def _ruleLibListDict(ctx):
    '''
    $lib.list() and $lib.dict() should be list and dict literals such as ([]) and ({}).
    '''
    for node in ctx.walk(s_ast.FuncCall):

        path = ctx.callPath(node)
        if path == ('lib', 'list'):
            ctx.report(node, 'Use a list literal such as ([]) instead of $lib.list().')

        elif path == ('lib', 'dict'):
            ctx.report(node, 'Use a dict literal such as ({}) instead of $lib.dict().')

@rule('S006', 'print-kwargs', 'low')
def _rulePrintKwargs(ctx):
    '''
    $lib.print() and $lib.warn() format their message with kwargs. Use a backtick format string.
    '''
    for node in ctx.walk(s_ast.FuncCall):

        path = ctx.callPath(node)
        if path not in (('lib', 'print'), ('lib', 'warn')) or not node.kids[2].kids:
            continue

        ctx.report(node, f'Use a backtick format string instead of $lib.{path[1]}() kwargs.')

def _ifVarBody(node):
    '''
    Return the (name, opers) of an if statement with no else which tests only a variable, or None.
    '''
    if len(node.kids) != 1:
        return None

    cond, body = node.kids[0].kids
    cond = _unparen(cond)
    if not isinstance(cond, s_ast.VarValue):
        return None

    return cond.kids[0].valu, body.kids[0].kids

def _isVar(node, name):
    return isinstance(node, s_ast.VarValue) and node.kids[0].valu == name

@rule('S008', 'guarded-for', 'low')
def _ruleGuardedFor(ctx):
    '''
    An if statement which only guards a for loop over the variable it tests. An empty or null
    value iterates zero times, so the guard is not needed.

    The guard is only redundant when no node is in the pipeline, because a for loop over an empty
    or null value drops the inbound node. Verify it before changing existing code.
    '''
    for node in ctx.walk(s_ast.IfStmt):

        info = _ifVarBody(node)
        if info is None:
            continue

        name, opers = info
        if len(opers) != 1 or not isinstance(opers[0], s_ast.ForLoop) or not _isVar(opers[0].kids[1], name):
            continue

        ctx.report(node, f'Drop the if guard, a for loop over an empty ${name} iterates zero times, '
                         'if no node is in the pipeline.')

@rule('S010', 'guarded-prop-set', 'low', default=False)
def _ruleGuardedPropSet(ctx):
    '''
    An if statement which only sets a property to the variable it tests. Use ?= which skips a
    null value.

    The if statement also skips a value which is not null but is false, such as 0, an empty
    string or an empty list, while ?= sets it, and ?= also skips a value which fails to norm.
    Verify the value can not be one of those before changing existing code.

    This rule is off by default. Turn it on with enable.
    '''
    for node in ctx.walk(s_ast.IfStmt):

        info = _ifVarBody(node)
        if info is None:
            continue

        name, opers = info
        if len(opers) != 1 or type(opers[0]) is not s_ast.EditPropSet:
            continue

        prop, cmpr, valu = opers[0].kids
        if cmpr.valu not in ('=', '?=') or not _isVar(valu, name):
            continue

        ctx.report(node, f'Use [ {ctx.getSrc(prop)}?=${name} ] instead of an if statement, '
                         f'if ${name} can not be a false non-null value or fail to norm.')

@rule('S011', 'subquery-lift-value', 'low')
def _ruleSubqueryLiftValue(ctx):
    '''
    A property is set from a subquery which only lifts a form by its primary value. Set the
    property to the value directly, using an as cast when it needs norming into the form type.
    '''
    for node in ctx.walk(s_ast.EditPropSet):

        prop, cmpr, valu = node.kids
        if not isinstance(valu, s_ast.SubQuery):
            continue

        opers = valu.kids[0].kids
        if len(opers) != 1 or type(opers[0]) is not s_ast.LiftPropBy:
            continue

        name, lcmpr, lvalu = opers[0].kids
        if lcmpr.valu != '=' or not isinstance(name, s_ast.Const) or not ctx.isForm(name.valu):
            continue

        dest = ctx.getSrc(prop) + cmpr.valu + ctx.getSrc(lvalu)
        ctx.report(valu, f'Use {dest} as {name.valu} (or {dest} when the property is {name.valu} typed) '
                         'instead of a subquery which lifts by value.')

def _readsNode(ctx, valu):
    '''
    Return True if a value is a subquery or reads the inbound node.
    '''
    for node in ctx.walk(node=valu):

        if isinstance(node, (s_ast.SubQuery, *nodevals)):
            return True

        if isinstance(node, s_ast.VarValue) and node.kids[0].valu in ('node', 'path'):
            return True

    return False

@rule('S012', 'lift-filter', 'low')
def _ruleLiftFilter(ctx):
    '''
    A query lifts a form and then filters on one of its properties by a value which does not
    read the node. Lift by the property instead.
    '''
    for query in ctx.walk(s_ast.Query):

        if len(query.kids) < 2:
            continue

        lift, filt = query.kids[:2]
        if type(lift) is not s_ast.LiftProp or not isinstance(filt, s_ast.FiltOper) or filt.kids[0].valu != '+':
            continue

        cond = filt.kids[1]
        if type(cond) is not s_ast.RelPropCond:
            continue

        prop, cmpr, valu = cond.kids
        if len(prop.kids) != 1 or cmpr.valu not in liftcmprs or _readsNode(ctx, valu):
            continue

        full = ctx.getSrc(lift) + ctx.getSrc(prop)
        if not ctx.isProp(full):
            continue

        ctx.report(lift, f'Lift by {full}{ctx.text[prop.astinfo.eoff:cond.astinfo.eoff]} instead of filtering.')

@rule('S014', 'try-cast', 'low')
def _ruleTryCast(ctx):
    '''
    A try block calls $lib.cast(). Use $lib.trycast() and check its result instead.
    '''
    for node in ctx.walk(s_ast.TryCatch):
        for call in ctx.walk(s_ast.FuncCall, node=node.kids[0], skip=s_ast.Function):
            if ctx.callPath(call) == ('lib', 'cast'):
                ctx.report(call, 'Use $lib.trycast() instead of $lib.cast() in a try block.')

def _getBinds(ctx, node, paths):
    '''
    Return the names a scope assigns, and the names it assigns from a call to one of the paths.
    '''
    names = set()
    binds = set()
    for oper in ctx.walk((s_ast.SetVarOper, s_ast.VarListSetOper, s_ast.ForLoop), node=node, skip=s_ast.Function):

        dest = oper.kids[0]
        if isinstance(dest, s_ast.VarList):
            names.update(dest.valu)
            continue

        names.add(dest.valu)
        if isinstance(oper, s_ast.SetVarOper) and ctx.callPath(oper.kids[1]) in paths:
            binds.add(dest.valu)

    return names, binds

def _getScopes(ctx, paths):
    '''
    Return a (node, binds) pair for the module scope and then for each function scope.

    binds are the names in scope which are assigned from a call to one of the paths. A function
    sees the module binds it does not assign or take as a parameter.
    '''
    _, modbinds = _getBinds(ctx, ctx.query, paths)

    scopes = [(ctx.query, modbinds)]
    for func in ctx.walk(s_ast.Function):

        names, binds = _getBinds(ctx, func.kids[2], paths)
        names.update(arg.kids[0].valu for arg in func.kids[1].kids)
        binds.update(modbinds - names)
        scopes.append((func.kids[2], binds))

    return scopes

@rule('S015', 'return-import', 'medium', default=False)
def _ruleReturnImport(ctx):
    '''
    A function returns a module from $lib.import(). In a privsep module the returned module
    inherits root privileges, and binding the import as $__name does not prevent that. Never
    return an imported module.

    This rule is off by default. Turn it on with enable.
    '''
    for scope, imports in _getScopes(ctx, (('lib', 'import'),))[1:]:
        for node in ctx.walk(s_ast.Return, node=scope, skip=s_ast.Function):

            if not node.kids:
                continue

            valu = _unparen(node.kids[0])
            isvar = isinstance(valu, s_ast.VarValue) and valu.kids[0].valu in imports
            if isvar or ctx.callPath(valu) == ('lib', 'import'):
                ctx.report(node, 'Never return a module from $lib.import(), in a privsep module it inherits root '
                                 'privileges even when bound as $__name.')

def _getLeaks(ctx, node, names):
    '''
    Yield (node, name) for each part of a print argument which exposes the request headers: a variable
    in names, used whole or through its request, request_headers or history member, or a direct call
    to one of the httpcalls, for which name is None.
    '''
    if isinstance(node, s_ast.FuncCall):
        if ctx.callPath(node) in httpcalls:
            yield node, None

        return

    for valu in ctx.walk(s_ast.VarValue, node=node, skip=(s_ast.Function, s_ast.FuncCall)):

        name = valu.kids[0].valu
        if name not in names:
            continue

        # the whole object, or a member which holds the request headers
        parent = ctx.parent(valu)
        if isinstance(parent, s_ast.VarDeref) and parent.kids[0] is valu:

            key = parent.kids[1]
            if not isinstance(key, s_ast.Const) or key.valu not in reqkeys:
                continue

        yield valu, name

def _getAncestors(ctx, node, scope):
    '''
    Yield the node and each of its parents up to, but not including, the scope.
    '''
    while node is not scope:
        yield node
        node = ctx.parent(node)

def _isBranch(ctx, node):
    '''
    Return True if the node is a block which may not run: an if clause or else query, a try body or
    catch block, a switch case, a loop, a subquery or an empty block.
    '''
    if isinstance(node, (s_ast.ForLoop, s_ast.WhileLoop, s_ast.SubQuery, s_ast.EmptyBlock)):
        return True

    return isinstance(ctx.parent(node), (s_ast.IfStmt, s_ast.TryCatch, s_ast.SwitchCase))

def _getLive(ctx, scope, names, paths, call):
    '''
    Return the names which hold the result of a call to one of the paths at the call.

    A name is live when its latest assignment in the scope before the call is from one of the paths,
    or when the scope does not assign it before the call (a module bind). A later assignment from
    anything else ends it, unless the assignment is in a branch which does not also contain the call.
    A bind after the call is live too when it is in a loop which contains the call, since the next
    iteration reaches the call with it.
    '''
    last = {}
    carried = set()
    off = call.astinfo.soff
    inside = {id(node) for node in _getAncestors(ctx, call, scope)}
    for oper in ctx.walk((s_ast.SetVarOper, s_ast.VarListSetOper, s_ast.ForLoop), node=scope, skip=s_ast.Function):

        soff = oper.astinfo.soff
        dest = oper.kids[0]
        isbind = isinstance(oper, s_ast.SetVarOper) and ctx.callPath(oper.kids[1]) in paths

        if soff >= off:
            loops = (s_ast.ForLoop, s_ast.WhileLoop)
            if isbind and any(isinstance(node, loops) and id(node) in inside for node in _getAncestors(ctx, oper, scope)):
                carried.add(dest.valu)

            continue

        if not isbind and any(_isBranch(ctx, node) and id(node) not in inside for node in _getAncestors(ctx, oper, scope)):
            continue

        for name in (dest.valu if isinstance(dest, s_ast.VarList) else (dest.valu,)):
            if name in names and soff >= last.get(name, (-1,))[0]:
                last[name] = (soff, isbind)

    return {name for name in names if name in carried or last.get(name, (0, True))[1]}

def _followCalls(ctx, scopes):
    '''
    Add the parameters of the functions defined in the query which are passed a response to the
    binds of the function scopes, until no more are added.

    A parameter is added when any call to the function passes a live response or a direct call to
    one of the httpcalls in that position, whichever call it is. scopes is the result of _getScopes().
    '''
    funcs = {}
    for func, (_, binds) in zip(ctx.walk(s_ast.Function), scopes[1:]):
        funcs[(func.kids[0].valu,)] = ([arg.kids[0].valu for arg in func.kids[1].kids], binds)

    changed = True
    while changed:
        changed = False

        for scope, binds in scopes:
            for call in ctx.walk(s_ast.FuncCall, node=scope, skip=s_ast.Function):

                func = funcs.get(ctx.callPath(call))
                if func is None:
                    continue

                params, fbinds = func
                live = _getLive(ctx, scope, binds, httpcalls, call)

                args = [*zip(params, call.kids[1].kids), *((kwarg.kids[0].valu, kwarg.kids[1]) for kwarg in call.kids[2].kids)]
                for name, arg in args:

                    isvar = isinstance(arg, s_ast.VarValue) and arg.kids[0].valu in live
                    if name in params and name not in fbinds and (isvar or ctx.callPath(arg) in httpcalls):
                        fbinds.add(name)
                        changed = True

@rule('S016', 'print-http-resp', 'medium', default=False)
def _rulePrintHttpResp(ctx):
    '''
    An HTTP response or $lib.axon.wget() result is printed or logged. It includes the request
    headers, which carry credentials such as an API key. Print fields such as its code and reason
    instead.

    The rule follows variables assigned from $lib.inet.http calls and $lib.axon.wget() or
    $lib.axon.wput() in the same scope, until the variable is assigned something else. An assignment
    in an if, try, switch, loop, subquery or empty block only ends it for a print in the same block.
    A parameter of a function defined in the same query is followed when any call to the function
    passes it a response. Suppress a finding for an object which is known to hold no credentials
    with a noqa comment.

    This rule is off by default. Turn it on with enable.
    '''
    scopes = _getScopes(ctx, httpcalls)
    _followCalls(ctx, scopes)

    for scope, resps in scopes:
        for call in ctx.walk(s_ast.FuncCall, node=scope, skip=s_ast.Function):

            if ctx.callPath(call) not in printcalls:
                continue

            live = _getLive(ctx, scope, resps, httpcalls, call)

            args = [*call.kids[1].kids, *(kwarg.kids[1] for kwarg in call.kids[2].kids)]
            for arg in args:
                for node, name in _getLeaks(ctx, arg, live):

                    if name is None:
                        ctx.report(node, 'The result of this call includes the request headers, such as API '
                                         'credentials. Print fields such as its code and reason instead.')
                        continue

                    ctx.report(node, f'${name} includes the request headers, such as API credentials. Print '
                                     f'fields such as ${name}.code and ${name}.reason instead.')


class StormLinter:
    '''
    Lint Storm code with the registered rules.

    select replaces the default rule set, so only the selected rules run. enable adds rules to the
    selected set, mostly to turn on rules which are off by default, and ignore removes rules from it.
    Each entry is a rule ID or an ID prefix, and includes the rules it matches whether or not they
    are on by default.

    model is a data model dict, in the shape returned by getModelDict(), which rules that check form
    and prop names use instead of the built-in data model.
    '''
    def __init__(self, select=None, ignore=(), enable=(), model=None):

        if select is None:
            idens = {r.iden for r in rules.values() if r.default}
        else:
            idens = self._resolve(select)

        idens.update(self._resolve(enable))
        idens.difference_update(self._resolve(ignore))

        self.rules = [r for r in rules.values() if r.iden in idens]
        self.model = model
        self.names = None

    def _resolve(self, entries):

        idens = set()
        for entry in entries:

            match = [iden for iden in rules if entry and iden.startswith(entry)]
            if not match:
                raise s_exc.BadArg(mesg=f'Unknown lint rule or prefix: {entry!r}', name=entry)

            idens.update(match)

        return idens

    def lint(self, text):
        '''
        Lint Storm text and return a list of Finding tuples sorted by (line, column, rule).
        '''
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', SyntaxWarning)
                query = s_parser.parseQuery(text)

        except s_exc.BadSyntax as e:
            line = e.errinfo.get('line') or 1
            column = e.errinfo.get('column') or 1
            r = rules['E001']
            return [Finding(r.iden, r.severity, line, column, e.errinfo.get('mesg'))]

        if self.names is None:
            self.names = _getModelNames(self.model)

        ctx = LintContext(text, query, *self.names)
        for r in self.rules:
            ctx.rule = r
            r.func(ctx)

        findings = [f for f in ctx.findings if not self._isNoqa(ctx.lines, f)]
        return sorted(findings, key=lambda f: (f.line, f.column, f.rule))

    def _isNoqa(self, lines, finding):

        match = noqare.search(lines[finding.line - 1])
        if match is None:
            return False

        codes = match.group(1)
        if codes is None:
            return True

        return any(finding.rule.startswith(c) for c in re.split(r'[\s,]+', codes))

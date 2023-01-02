import ast

import lark  # type: ignore
import regex  # type: ignore

import synapse.exc as s_exc

import synapse.lib.ast as s_ast
import synapse.lib.coro as s_coro
import synapse.lib.cache as s_cache
import synapse.lib.datfile as s_datfile

# TL;DR:  *rules* are the internal nodes of an abstract syntax tree (AST), *terminals* are the leaves

# Note: this file is coupled strongly to synapse/lib/storm.lark.  Any changes to that file will probably require
# changes here

# For easier-to-understand syntax errors
terminalEnglishMap = {
    'AS': 'as',
    'ABSPROP': 'absolute or universal property',
    'ABSPROPNOUNIV': 'absolute property',
    'ALLTAGS': '#',
    'AND': 'and',
    'BACKQUOTE': '`',
    'BASEPROP': 'base property name',
    'BOOL': 'boolean',
    'BREAK': 'break',
    'BYNAME': 'named comparison operator',
    'CATCH': 'catch',
    'CASEBARE': 'case value',
    'CCOMMENT': 'C comment',
    'CMDOPT': 'command line option',
    'CMDNAME': 'command name',
    'CMDRTOKN': 'An unquoted string parsed as a cmdr arg',
    'CMPR': 'comparison operator',
    'CMPROTHER': 'comparison operator',
    'COLON': ':',
    'COMMA': ',',
    'COMMASPACE': ',',
    'COMMANOSPACE': ',',
    'CONTINUE': 'continue',
    'CPPCOMMENT': 'c++ comment',
    'DEFAULTCASE': 'default case',
    'DOLLAR': '$',
    'DOT': '.',
    'DOUBLEQUOTEDSTRING': 'double-quoted string',
    'ELIF': 'elif',
    'EQNOSPACE': '=',
    'EQSPACE': '=',
    'EQUAL': '=',
    'EXPRDIVIDE': '/',
    'EXPRMINUS': '-',
    'EXPRNEG': '-',
    'EXPRPLUS': '+',
    'EXPRPOW': '**',
    'EXPRTIMES': '*',
    'FOR': 'for',
    'FORMATSTRING': 'backtick-quoted format string',
    'FORMATTEXT': 'text within a format string',
    'FUNCTION': 'function',
    'HASH': '#',
    'HEXNUMBER': 'number',
    'IF': 'if',
    'IN': 'in',
    'LBRACE': '{',
    'LISTTOKN': 'unquoted list value',
    'LPAR': '(',
    'LSQB': '[',
    'MODSET': '+= or -=',
    'NONQUOTEWORD': 'unquoted value',
    'NOT': 'not',
    'NUMBER': 'number',
    'OR': 'or',
    'PROPS': 'absolute property name',
    'RBRACE': '}',
    'RELNAME': 'relative property name',
    'EXPRRELNAME': 'relative property name',
    'RPAR': ')',
    'RSQB': ']',
    'RSQBNOSPACE': ']',
    'SETTAGOPER': '?',
    'SINGLEQUOTEDSTRING': 'single-quoted string',
    'SWITCH': 'switch',
    'TRY': 'try',
    'TAGMATCH': 'tag name potentially with asterisks',
    'TRIPLEQUOTEDSTRING': 'triple-quoted string',
    'TRYSET': '?=',
    'TRYSETPLUS': '?+=',
    'TRYSETMINUS': '?-=',
    'UNIVNAME': 'universal property',
    'EXPRUNIVNAME': 'universal property',
    'VARTOKN': 'variable',
    'EXPRVARTOKN': 'variable',
    'VBAR': '|',
    'WHILE': 'while',
    'WHITETOKN': 'An unquoted string terminated by whitespace',
    'WILDCARD': '*',
    'YIELD': 'yield',
    '_ARRAYCONDSTART': '*[',
    '_COLONDOLLAR': ':$',
    '_DEREF': '*',
    '_EDGEADDN1INIT': '+(',
    '_EDGEADDN2FINI': ')+',
    '_EDGEN1FINI': ')>',
    '_EDGEN1INIT': '-(',
    '_EDGEN2INIT': '<(',
    '_EDGEN2FINI': ')-',
    '_ELSE': 'else',
    '_EMBEDQUERYSTART': '${',
    '_EMIT': 'emit',
    '_FINI': 'fini',
    '_HASH': '#',
    '_EXPRHASH': '#',
    '_HASHSPACE': '#',
    '_EXPRHASHSPACE': '#',
    '_INIT': 'init',
    '_LEFTJOIN': '<+-',
    '_LEFTPIVOT': '<-',
    '_LPARNOSPACE': '(',
    '_RETURN': 'return',
    '_RIGHTJOIN': '-+>',
    '_RIGHTPIVOT': '->',
    '_STOP': 'stop',
    '_TAGSEGNOVAR': 'tag segment potentially with asterisks',
    '_WALKNPIVON1': '-->',
    '_WALKNPIVON2': '<--',
    '$END': 'end of input',
}

class AstConverter(lark.Transformer):
    '''
    Convert AST from parser into synapse AST, depth first.

    If a method with a name that matches the current rule exists, that will be called, otherwise __default__ will be
    used
    '''
    def __init__(self, text):
        lark.Transformer.__init__(self)

        # Keep the original text for error printing and weird subquery argv parsing
        self.text = text

    @classmethod
    def _convert_children(cls, children):
        return [cls._convert_child(k) for k in children]

    @classmethod
    def _convert_child(cls, child):
        if not isinstance(child, lark.lexer.Token):
            return child
        tokencls = terminalClassMap.get(child.type, s_ast.Const)
        newkid = tokencls(child.value)
        return newkid

    def __default__(self, treedata, children, treemeta):
        assert treedata in ruleClassMap, f'Unknown grammar rule: {treedata}'
        cls = ruleClassMap[treedata]
        newkids = self._convert_children(children)
        return cls(newkids)

    @lark.v_args(meta=True)
    def subquery(self, meta, kids):
        assert len(kids) <= 2
        hasyield = (len(kids) == 2)
        kid = self._convert_child(kids[-1])
        kid.hasyield = hasyield

        return kid

    def _parseJsonToken(self, meta, tokn):
        if isinstance(tokn, lark.lexer.Token) and tokn.type == 'VARTOKN' and not tokn.value[0] in ('"', "'"):
            valu = tokn.value
            try:
                valu = float(valu) if '.' in valu else int(valu, 0)
            except ValueError as e:
                mesg = f"Unexpected unquoted string in JSON expression at line {meta.line} col {meta.column}"
                raise s_exc.BadSyntax(mesg=mesg, at=meta.start_pos, line=meta.line, column=meta.column)

            return s_ast.Const(valu)
        else:
            return self._convert_child(tokn)

    @lark.v_args(meta=True)
    def exprlist(self, meta, kids):
        kids = [self._parseJsonToken(meta, k) for k in kids]
        return s_ast.ExprList(kids=kids)

    @lark.v_args(meta=True)
    def exprdict(self, meta, kids):
        kids = [self._parseJsonToken(meta, k) for k in kids]
        return s_ast.ExprDict(kids=kids)

    @lark.v_args(meta=True)
    def trycatch(self, meta, kids):
        kids = self._convert_children(kids)
        return s_ast.TryCatch(kids=kids)

    @lark.v_args(meta=True)
    def catchblock(self, meta, kids):
        kids = self._convert_children(kids)
        return s_ast.CatchBlock(kids=kids)

    @lark.v_args(meta=True)
    def baresubquery(self, meta, kids):
        assert len(kids) == 1

        epos = meta.end_pos
        spos = meta.start_pos

        subq = s_ast.SubQuery(kids)
        subq.text = self.text[spos:epos]

        return subq

    @lark.v_args(meta=True)
    def argvquery(self, meta, kids):
        assert len(kids) == 1

        epos = meta.end_pos
        spos = meta.start_pos

        argq = s_ast.ArgvQuery(kids)
        argq.text = self.text[spos:epos]

        return argq

    def yieldvalu(self, kids):
        kid = self._convert_child(kids[-1])
        return s_ast.YieldValu(kids=[kid])

    @lark.v_args(meta=True)
    def evalvalu(self, meta, kids):
        return self._convert_child(kids[0])

    @lark.v_args(meta=True)
    def lookup(self, meta, kids):
        kids = self._convert_children(kids)
        look = s_ast.Lookup(kids=kids)
        return look

    @lark.v_args(meta=True)
    def search(self, meta, kids):
        kids = self._convert_children(kids)
        look = s_ast.Search(kids=kids)
        return look

    @lark.v_args(meta=True)
    def query(self, meta, kids):
        kids = self._convert_children(kids)

        if kids:
            epos = meta.end_pos
            spos = meta.start_pos
        else:
            epos = spos = 0

        quer = s_ast.Query(kids=kids)
        quer.text = self.text[spos:epos]

        return quer

    @lark.v_args(meta=True)
    def embedquery(self, meta, kids):
        assert len(kids) == 1
        text = kids[0].text
        ast = s_ast.EmbedQuery(text, kids)
        return ast

    @lark.v_args(meta=True)
    def emit(self, meta, kids):
        kids = self._convert_children(kids)
        return s_ast.Emit(kids)

    @lark.v_args(meta=True)
    def stop(self, meta, kids):
        return s_ast.Stop()

    @lark.v_args(meta=True)
    def funccall(self, meta, kids):
        argkids = []
        kwargkids = []
        kwnames = set()
        indx = 1
        kcnt = len(kids)
        while indx < kcnt:

            kid = self._convert_child(kids[indx])

            if indx + 2 < kcnt and isinstance(kids[indx + 1], lark.lexer.Token) and kids[indx + 1].type in ('EQNOSPACE', 'EQUAL', 'EQSPACE'):
                kid = s_ast.CallKwarg((kid, self._convert_child(kids[indx + 2])))
                indx += 3
            else:
                indx += 1

            if isinstance(kid, s_ast.CallKwarg):
                name = kid.kids[0].valu
                if name in kwnames:
                    mesg = f"Duplicate keyword argument '{name}' in function call at line {meta.line} col {meta.column}"
                    raise s_exc.BadSyntax(mesg=mesg, at=meta.start_pos, line=meta.line, column=meta.column)

                kwnames.add(name)
                kwargkids.append(kid)
            else:
                if kwargkids:
                    mesg = f'Positional argument follows keyword argument in function call at line {meta.line} col {meta.column}'
                    raise s_exc.BadSyntax(mesg=mesg, at=meta.start_pos, line=meta.line, column=meta.column)
                argkids.append(kid)

        args = s_ast.CallArgs(kids=argkids)
        kwargs = s_ast.CallKwargs(kids=kwargkids)
        return s_ast.FuncCall(kids=[kids[0], args, kwargs])

    def varlist(self, kids):
        kids = self._convert_children(kids)
        return s_ast.VarList([k.valu for k in kids])

    def operrelprop_pivot(self, kids, isjoin=False):
        kids = self._convert_children(kids)
        relprop, rest = kids[0], kids[1:]
        if not rest:
            return s_ast.PropPivotOut(kids=kids, isjoin=isjoin)
        pval = s_ast.RelPropValue(kids=(relprop,))
        return s_ast.PropPivot(kids=(pval, *kids[1:]), isjoin=isjoin)

    def operrelprop_join(self, kids):
        return self.operrelprop_pivot(kids, isjoin=True)

    def stormcmdargs(self, kids):
        newkids = []
        for kid in kids:
            if isinstance(kid, lark.lexer.Token) and kid.type == 'EQNOSPACE':
                continue
            newkids.append(self._convert_child(kid))
        return s_ast.List(kids=newkids)

    @lark.v_args(meta=True)
    def funcargs(self, meta, kids):
        '''
        A list of function parameters (as part of a function definition)
        '''
        kids = self._convert_children(kids)
        newkids = []

        names = set()
        kwfound = False

        indx = 0
        kcnt = len(kids)

        while indx < kcnt:
            if indx + 2 < kcnt and isinstance(kids[indx + 1], s_ast.Const) and kids[indx + 1].valu == '=':
                kid = s_ast.CallKwarg((kids[indx], kids[indx + 2]))
                indx += 3
            else:
                kid = kids[indx]
                indx += 1

            newkids.append(kid)

            if isinstance(kid, s_ast.CallKwarg):
                name = kid.kids[0].valu
                kwfound = True
                # Make sure no repeated kwarg
            else:
                name = kid.valu
                # Make sure no positional follows a kwarg
                if kwfound:
                    mesg = f"Positional parameter '{name}' follows keyword parameter in definition at line {meta.line} col {meta.column}"
                    raise s_exc.BadSyntax(mesg=mesg, at=meta.start_pos, line=meta.line, column=meta.column)

            if name in names:
                mesg = f"Duplicate parameter '{name}' in function definition at line {meta.line} col {meta.column}"
                raise s_exc.BadSyntax(mesg=mesg, at=meta.start_pos, line=meta.line, column=meta.column)

            names.add(name)

        return s_ast.FuncArgs(newkids)

    def cmdrargs(self, kids):
        argv = []
        indx = 0

        kcnt = len(kids)
        while indx < kcnt:

            kid = kids[indx]
            indx += 1

            if isinstance(kid, s_ast.SubQuery):
                argv.append(kid.text)
                continue

            # this one should never happen, but is here in case
            if isinstance(kid, s_ast.Const):  # pragma: no cover
                argv.append(kid.valu)
                continue

            if isinstance(kid, lark.lexer.Token):

                if kid == '=':
                    argv[-1] += kid

                    if kcnt >= indx:
                        nextkid = kids[indx]
                        if isinstance(nextkid, s_ast.SubQuery):
                            argv[-1] += nextkid.text
                        elif isinstance(nextkid, s_ast.Const):  #pragma: no cover
                            argv[-1] += nextkid.valu
                        else:
                            argv[-1] += str(nextkid)

                        indx += 1
                    continue
                else:
                    argv.append(str(kid))
                    continue

            # pragma: no cover
            mesg = f'Unhandled AST node type in cmdrargs: {kid!r}'
            raise s_exc.BadSyntax(mesg=mesg)

        return argv

    @classmethod
    def _tagsplit(cls, tag):
        if '$' not in tag:
            return [s_ast.Const(tag)]

        segs = tag.split('.')
        kids = [s_ast.VarValue(kids=[s_ast.Const(seg[1:])]) if seg[0] == '$' else s_ast.Const(seg)
                for seg in segs]
        return kids

    def varderef(self, kids):
        assert kids and len(kids) in (3, 4)
        if kids[2] == '$':
            tokencls = terminalClassMap.get(kids[3].type, s_ast.Const)
            newkid = s_ast.VarValue(kids=[tokencls(kids[3])])
        else:
            newkid = self._convert_child(kids[2])
        return s_ast.VarDeref(kids=(kids[0], newkid))

    def tagname(self, kids):
        assert kids and len(kids) == 1
        kid = kids[0]
        if not isinstance(kid, lark.lexer.Token):
            return self._convert_child(kid)

        valu = kid.value
        if '*' in valu:
            mesg = f"Invalid wildcard usage in tag {valu}"
            raise s_exc.BadSyntax(mesg=mesg, tag=valu)

        kids = self._tagsplit(valu)
        return s_ast.TagName(kids=kids)

    def switchcase(self, kids):
        newkids = []

        it = iter(kids)

        varvalu = next(it)
        newkids.append(varvalu)

        for casekid, sqkid in zip(it, it):
            subquery = self._convert_child(sqkid)
            if casekid.type == 'DEFAULTCASE':
                caseentry = s_ast.CaseEntry(kids=[subquery])
            else:
                casekid = self._convert_child(casekid)
                caseentry = s_ast.CaseEntry(kids=[casekid, subquery])

            newkids.append(caseentry)

        return s_ast.SwitchCase(newkids)


with s_datfile.openDatFile('synapse.lib/storm.lark') as larkf:
    _grammar = larkf.read().decode()

LarkParser = lark.Lark(_grammar, regex=True, start=['query', 'lookup', 'cmdrargs', 'evalvalu', 'search'],
                       maybe_placeholders=False, propagate_positions=True, parser='lalr')

class Parser:
    '''
    Storm query parser
    '''
    def __init__(self, text, offs=0):

        self.offs = offs
        assert text is not None
        self.text = text.strip()
        self.size = len(self.text)

    def _larkToSynExc(self, e):
        '''
        Convert lark exception to synapse BadSyntax exception
        '''
        mesg = regex.split('[\n]', str(e))[0]
        at = len(self.text)
        line = None
        column = None
        token = None
        if isinstance(e, lark.exceptions.UnexpectedToken):
            expected = sorted(set(terminalEnglishMap[t] for t in e.expected))
            at = e.pos_in_stream
            line = e.line
            column = e.column
            token = e.token.value
            valu = terminalEnglishMap.get(e.token.type, e.token.value)
            mesg = f"Unexpected token '{valu}' at line {line}, column {column}," \
                   f' expecting one of: {", ".join(expected)}'

        elif isinstance(e, lark.exceptions.VisitError):
            # Lark unhelpfully wraps an exception raised from AstConverter in a VisitError.  Unwrap it.
            origexc = e.orig_exc
            if not isinstance(origexc, s_exc.SynErr):
                raise e.orig_exc # pragma: no cover
            origexc.errinfo['text'] = self.text
            return s_exc.BadSyntax(**origexc.errinfo)

        elif isinstance(e, lark.exceptions.UnexpectedCharacters):  # pragma: no cover
            expected = sorted(set(terminalEnglishMap[t] for t in e.allowed))
            mesg += f'.  Expecting one of: {", ".join(expected)}'
            at = e.pos_in_stream
            line = e.line
            column = e.column
        elif isinstance(e, lark.exceptions.UnexpectedEOF):  # pragma: no cover
            expected = sorted(set(terminalEnglishMap[t] for t in e.expected))
            mesg += ' ' + ', '.join(expected)
            line = e.line
            column = e.column

        return s_exc.BadSyntax(at=at, text=self.text, mesg=mesg, line=line, column=column, token=token)

    def eval(self):
        try:
            tree = LarkParser.parse(self.text, start='evalvalu')
            newtree = AstConverter(self.text).transform(tree)

        except lark.exceptions.LarkError as e:
            raise self._larkToSynExc(e) from None

        newtree.text = self.text
        return newtree

    def query(self):
        '''
        Parse the storm query

        Returns (s_ast.Query):  instance of parsed query
        '''
        try:
            tree = LarkParser.parse(self.text, start='query')
            newtree = AstConverter(self.text).transform(tree)

        except lark.exceptions.LarkError as e:
            raise self._larkToSynExc(e) from None

        newtree.text = self.text
        return newtree

    def lookup(self):
        try:
            tree = LarkParser.parse(self.text, start='lookup')
            newtree = AstConverter(self.text).transform(tree)

        except lark.exceptions.LarkError as e:
            raise self._larkToSynExc(e) from None

        newtree.text = self.text
        return newtree

    def search(self):
        try:
            tree = LarkParser.parse(self.text, start='search')
            newtree = AstConverter(self.text).transform(tree)

        except lark.exceptions.LarkError as e:
            raise self._larkToSynExc(e) from None

        newtree.text = self.text
        return newtree

    def cmdrargs(self):
        '''
        Parse command args that might have storm queries as arguments
        '''
        try:
            tree = LarkParser.parse(self.text, start='cmdrargs')
            return AstConverter(self.text).transform(tree)
        except lark.exceptions.LarkError as e:
            raise self._larkToSynExc(e) from None

def parseQuery(text, mode='storm'):
    '''
    Parse a storm query and return the Lark AST.  Cached here to speed up unit tests
    '''
    if mode == 'lookup':
        return Parser(text).lookup()

    if mode == 'autoadd':
        look = Parser(text).lookup()
        look.autoadd = True
        return look

    if mode == 'search':
        return Parser(text).search()

    return Parser(text).query()

def parseEval(text):
    return Parser(text).eval()

async def _forkedParseQuery(args):
    return await s_coro.forked(parseQuery, args[0], mode=args[1])

async def _forkedParseEval(text):
    return await s_coro.forked(parseEval, text)

evalcache = s_cache.FixedCache(_forkedParseEval, size=100)
querycache = s_cache.FixedCache(_forkedParseQuery, size=100)

def massage_vartokn(x):
    return s_ast.Const('' if not x else (x[1:-1] if x[0] == "'" else (unescape(x) if x[0] == '"' else x)))

# For AstConverter, one-to-one replacements from lark to synapse AST
terminalClassMap = {
    'ABSPROP': s_ast.AbsProp,
    'ABSPROPNOUNIV': s_ast.AbsProp,
    'ALLTAGS': lambda _: s_ast.TagMatch(''),
    'BREAK': lambda _: s_ast.BreakOper(),
    'CONTINUE': lambda _: s_ast.ContinueOper(),
    'DOUBLEQUOTEDSTRING': lambda x: s_ast.Const(unescape(x)),  # drop quotes and handle escape characters
    'FORMATTEXT': lambda x: s_ast.Const(format_unescape(x)),  # handle escape characters
    'TRIPLEQUOTEDSTRING': lambda x: s_ast.Const(x[3:-3]), # drop the triple 's
    'NUMBER': lambda x: s_ast.Const(s_ast.parseNumber(x)),
    'HEXNUMBER': lambda x: s_ast.Const(s_ast.parseNumber(x)),
    'BOOL': lambda x: s_ast.Bool(x == 'true'),
    'SINGLEQUOTEDSTRING': lambda x: s_ast.Const(x[1:-1]),  # drop quotes
    'TAGMATCH': lambda x: s_ast.TagMatch(kids=AstConverter._tagsplit(x)),
    'NONQUOTEWORD': massage_vartokn,
    'VARTOKN': massage_vartokn,
    'EXPRVARTOKN': massage_vartokn,
}

# For AstConverter, one-to-one replacements from lark to synapse AST
ruleClassMap = {
    'abspropcond': s_ast.AbsPropCond,
    'arraycond': s_ast.ArrayCond,
    'andexpr': s_ast.AndCond,
    'condsubq': s_ast.SubqCond,
    'dollarexpr': s_ast.DollarExpr,
    'reqdollarexpr': s_ast.DollarExpr,
    'edgeaddn1': s_ast.EditEdgeAdd,
    'edgedeln1': s_ast.EditEdgeDel,
    'edgeaddn2': lambda kids: s_ast.EditEdgeAdd(kids, n2=True),
    'edgedeln2': lambda kids: s_ast.EditEdgeDel(kids, n2=True),
    'editnodeadd': s_ast.EditNodeAdd,
    'editparens': s_ast.EditParens,
    'initblock': s_ast.InitBlock,
    'finiblock': s_ast.FiniBlock,
    'formname': s_ast.FormName,
    'editpropdel': lambda kids: s_ast.EditPropDel(kids[1:]),
    'editpropset': s_ast.EditPropSet,
    'edittagadd': s_ast.EditTagAdd,
    'edittagdel': lambda kids: s_ast.EditTagDel(kids[1:]),
    'edittagpropset': s_ast.EditTagPropSet,
    'edittagpropdel': lambda kids: s_ast.EditTagPropDel(kids[1:]),
    'editunivdel': lambda kids: s_ast.EditUnivDel(kids[1:]),
    'editunivset': s_ast.EditPropSet,
    'expror': s_ast.ExprOrNode,
    'exprand': s_ast.ExprAndNode,
    'exprnot': s_ast.UnaryExprNode,
    'exprunary': s_ast.UnaryExprNode,
    'exprcmp': s_ast.ExprNode,
    'exprpow': s_ast.ExprNode,
    'exprproduct': s_ast.ExprNode,
    'exprsum': s_ast.ExprNode,
    'filtoper': s_ast.FiltOper,
    'filtopermust': lambda kids: s_ast.FiltOper([s_ast.Const('+')] + kids),
    'filtopernot': lambda kids: s_ast.FiltOper([s_ast.Const('-')] + kids),
    'forloop': s_ast.ForLoop,
    'formatstring': s_ast.FormatString,
    'whileloop': s_ast.WhileLoop,
    'formjoin_formpivot': lambda kids: s_ast.FormPivot(kids, isjoin=True),
    'formjoin_pivotout': lambda _: s_ast.PivotOut(isjoin=True),
    'formjoinin_pivotin': lambda kids: s_ast.PivotIn(kids, isjoin=True),
    'formjoinin_pivotinfrom': lambda kids: s_ast.PivotInFrom(kids, isjoin=True),
    'formpivot_': s_ast.FormPivot,
    'formpivot_pivotout': s_ast.PivotOut,
    'formpivot_pivottotags': s_ast.PivotToTags,
    'formpivot_jointags': lambda kids: s_ast.PivotToTags(kids, isjoin=True),
    'formpivotin_': s_ast.PivotIn,
    'formpivotin_pivotinfrom': s_ast.PivotInFrom,
    'formtagprop': s_ast.FormTagProp,
    'hasabspropcond': s_ast.HasAbsPropCond,
    'hasrelpropcond': s_ast.HasRelPropCond,
    'hastagpropcond': s_ast.HasTagPropCond,
    'ifstmt': s_ast.IfStmt,
    'ifclause': s_ast.IfClause,
    'kwarg': lambda kids: s_ast.CallKwarg(kids=tuple(kids)),
    'liftbytag': s_ast.LiftTag,
    'liftformtag': s_ast.LiftFormTag,
    'liftprop': s_ast.LiftProp,
    'liftpropby': s_ast.LiftPropBy,
    'lifttagtag': s_ast.LiftTagTag,
    'liftbyarray': s_ast.LiftByArray,
    'liftbytagprop': s_ast.LiftTagProp,
    'liftbyformtagprop': s_ast.LiftFormTagProp,
    'looklist': s_ast.LookList,
    'n1walk': s_ast.N1Walk,
    'n2walk': s_ast.N2Walk,
    'n1walknpivo': s_ast.N1WalkNPivo,
    'n2walknpivo': s_ast.N2WalkNPivo,
    'notcond': s_ast.NotCond,
    'opervarlist': s_ast.VarListSetOper,
    'orexpr': s_ast.OrCond,
    'rawpivot': s_ast.RawPivot,
    'return': s_ast.Return,
    'relprop': lambda kids: s_ast.RelProp([s_ast.Const(k.valu.lstrip(':')) if isinstance(k, s_ast.Const) else k for k in kids]),
    'relpropcond': s_ast.RelPropCond,
    'relpropvalu': lambda kids: s_ast.RelPropValue([s_ast.Const(k.valu.lstrip(':')) if isinstance(k, s_ast.Const) else k for k in kids]),
    'relpropvalue': s_ast.RelPropValue,
    'setitem': s_ast.SetItemOper,
    'setvar': s_ast.SetVarOper,
    'stormcmd': lambda kids: s_ast.CmdOper(kids=kids if len(kids) == 2 else (kids[0], s_ast.Const(tuple()))),
    'stormfunc': s_ast.Function,
    'tagcond': s_ast.TagCond,
    'tagprop': s_ast.TagProp,
    'tagvalu': s_ast.TagValue,
    'tagpropvalu': s_ast.TagPropValue,
    'tagvalucond': s_ast.TagValuCond,
    'tagpropcond': s_ast.TagPropCond,
    'valulist': s_ast.List,
    'vareval': s_ast.VarEvalOper,
    'varvalue': s_ast.VarValue,
    'univprop': s_ast.UnivProp,
    'univpropvalu': s_ast.UnivPropValue,
    'wordtokn': lambda kids: s_ast.Const(''.join([str(k.valu) for k in kids]))
}

def format_unescape(valu):
    repl = valu.replace('\\`', '`').replace('\\{', '{')
    return unescape(f"'''{repl}'''")

def unescape(valu):
    '''
    Parse a string for backslash-escaped characters and omit them.
    The full list of escaped characters can be found at
    https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals
    '''
    try:
        ret = ast.literal_eval(valu)
    except ValueError as e:
        mesg = f"Invalid character in string {repr(valu)}: {e}"
        raise s_exc.BadSyntax(mesg=mesg, valu=repr(valu)) from None

    assert isinstance(ret, str)
    return ret

# TODO: use existing storm parser and remove this
CmdStringGrammar = r'''
%import common.WS -> _WS
%import common.ESCAPED_STRING

cmdstring: _WS? valu [/.+/]
valu: alist | DOUBLEQUOTEDSTRING | SINGLEQUOTEDSTRING | JUSTCHARS
DOUBLEQUOTEDSTRING: ESCAPED_STRING
SINGLEQUOTEDSTRING: /'[^']*'/
alist: "(" _WS? valu (_WS? "," _WS? valu)* _WS? ")"
// Disallow trailing comma
JUSTCHARS: /[^()=\[\]{}'"\s]*[^,()=\[\]{}'"\s]/
'''

CmdStringParser = lark.Lark(CmdStringGrammar,
                            start='cmdstring',
                            regex=True,
                            propagate_positions=True)

def parse_cmd_string(text, off):
    '''
    Parse a command line string which may be quoted.
    '''
    tree = CmdStringParser.parse(text[off:])
    valu, newoff = CmdStringer().transform(tree)
    return valu, off + newoff


@lark.v_args(meta=True)
class CmdStringer(lark.Transformer):

    def valu(self, meta, kids):
        assert len(kids) == 1
        kid = kids[0]
        if isinstance(kid, lark.lexer.Token):
            if kid.type in ('DOUBLEQUOTEDSTRING', 'SINGLEQUOTEDSTRING'):
                valu = kid.value[1:-1]
            else:
                valu = kid.value
                try:
                    intval = int(valu)
                    valu = intval
                except Exception:
                    pass
        else:
            valu = kid[0]

        return valu, meta.end_pos

    def cmdstring(self, meta, kids):
        return kids[0]

    def alist(self, meta, kids):
        return [k[0] for k in kids], meta.end_pos

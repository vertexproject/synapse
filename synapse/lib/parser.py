import ast
import hashlib
import collections

import lark  # type: ignore
import regex  # type: ignore

import synapse.exc as s_exc
import synapse.common as s_common

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
    'EMBEDPROPS': 'absolute property name with embed properties',
    'EQNOSPACE': '=',
    'EQSPACE': '=',
    'EQUAL': '=',
    'EXPRDIVIDE': '/',
    'EXPRMINUS': '-',
    'EXPRMODULO': '%',
    'EXPRNEG': '-',
    'EXPRPLUS': '+',
    'EXPRPOW': '**',
    'EXPRTAGSEGNOVAR': 'non-variable tag segment',
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
    'MCASEBARE': 'case multi-value',
    'MODSET': '+= or -=',
    'MODSETMULTI': '++= or --=',
    'NONQUOTEWORD': 'unquoted value',
    'NOTOP': 'not',
    'NULL': 'null',
    'NUMBER': 'number',
    'OCTNUMBER': 'number',
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
    'TAGSEGNOVAR': 'non-variable tag segment',
    'TRY': 'try',
    'TRIPLEQUOTEDSTRING': 'triple-quoted string',
    'TRYSET': '?=',
    'TRYMODSET': '?+= or ?-=',
    'TRYMODSETMULTI': '?++= or ?--=',
    'UNIVNAME': 'universal property',
    'UNSET': 'unset',
    'EXPRUNIVNAME': 'universal property',
    'VARTOKN': 'variable',
    'EXPRVARTOKN': 'variable',
    'VBAR': '|',
    'WHILE': 'while',
    'WHITETOKN': 'An unquoted string terminated by whitespace',
    'WILDCARD': '*',
    'WILDPROPS': 'property name potentially with wildcards',
    'WILDTAGSEGNOVAR': 'tag segment potentially with asterisks',
    'YIELD': 'yield',
    '_ARRAYCONDSTART': '*[',
    '_COLONDOLLAR': ':$',
    '_COLONNOSPACE': ':',
    '_DEREF': '*',
    '_EDGEADDN1INIT': '+(',
    '_EDGEADDN2FINI': ')+',
    '_EDGEN1FINI': ')>',
    '_EDGEN1INIT': '-(',
    '_EDGEN2INIT': '<(',
    '_EDGEN2FINI': ')-',
    '_EDGEN1JOINFINI': ')+>',
    '_EDGEN2JOININIT': '<+(',
    '_ELSE': 'else',
    '_EMBEDQUERYSTART': '${',
    '_EXPRCOLONNOSPACE': ':',
    '_EMIT': 'emit',
    '_EMPTY': 'empty',
    '_FINI': 'fini',
    '_HASH': '#',
    '_HASHSPACE': '#',
    '_INIT': 'init',
    '_LEFTJOIN': '<+-',
    '_LEFTPIVOT': '<-',
    '_LPARNOSPACE': '(',
    '_MATCHHASH': '#',
    '_MATCHHASHWILD': '#',
    '_NOT': 'not',
    '_RETURN': 'return',
    '_REVERSE': 'reverse',
    '_RIGHTJOIN': '-+>',
    '_RIGHTPIVOT': '->',
    '_STOP': 'stop',
    '_WALKNJOINN1': '--+>',
    '_WALKNJOINN2': '<+--',
    '_WALKNPIVON1': '-->',
    '_WALKNPIVON2': '<--',
    '$END': 'end of input',
}

AstInfo = collections.namedtuple('AstInfo', ('text', 'soff', 'eoff', 'sline', 'eline', 'scol', 'ecol', 'isterm'))

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
        self.texthash = s_common.queryhash(text)

    def metaToAstInfo(self, meta, isterm=False):
        if isinstance(meta, lark.tree.Meta) and meta.empty:
            return AstInfo(self.text, -1, -1, -1, -1, -1, -1, isterm)
        return AstInfo(self.text,
            meta.start_pos, meta.end_pos,
            meta.line, meta.end_line,
            meta.column, meta.end_column, isterm)

    def raiseBadSyntax(self, mesg, astinfo):
        raise s_exc.BadSyntax(mesg=mesg,
            # keep around for backward compatiblity
            at=astinfo.soff,
            line=astinfo.sline,
            column=astinfo.scol,
            highlight={
                'hash': self.texthash,
                'lines': (astinfo.sline, astinfo.eline),
                'columns': (astinfo.scol, astinfo.ecol),
                'offsets': (astinfo.soff, astinfo.eoff),
            })

    def _convert_children(self, children):
        return [self._convert_child(k) for k in children]

    def _convert_child(self, child):
        if not isinstance(child, lark.lexer.Token):
            return child

        tokencls = terminalClassMap.get(child.type, s_ast.Const)

        # Tokens have similar fields to meta
        astinfo = self.metaToAstInfo(child, isterm=True)
        return tokencls(astinfo, child.value)

    def __default__(self, treedata, children, treemeta):
        assert treedata in ruleClassMap, f'Unknown grammar rule: {treedata}'
        return ruleClassMap[treedata](self.metaToAstInfo(treemeta), self._convert_children(children))

    @lark.v_args(meta=True)
    def subquery(self, meta, kids):
        assert len(kids) <= 2
        hasyield = (len(kids) == 2)
        kid = self._convert_child(kids[-1])
        kid.hasyield = hasyield

        return kid

    def _parseJsonToken(self, tokn):

        if isinstance(tokn, lark.lexer.Token) and tokn.type == 'VARTOKN' and not tokn.value[0] in ('"', "'"):

            valu = tokn.value
            astinfo = self.metaToAstInfo(tokn)

            try:
                valu = float(valu) if '.' in valu else int(valu, 0)
            except ValueError as e:
                self.raiseBadSyntax('Unexpected unquoted string in JSON expression', astinfo)

            return s_ast.Const(astinfo, valu)
        else:
            return self._convert_child(tokn)

    @lark.v_args(meta=True)
    def exprlist(self, meta, kids):
        kids = [self._parseJsonToken(k) for k in kids]
        astinfo = self.metaToAstInfo(meta, isterm=True)
        return s_ast.ExprList(astinfo, kids=kids)

    @lark.v_args(meta=True)
    def exprdict(self, meta, kids):
        kids = [self._parseJsonToken(k) for k in kids]
        astinfo = self.metaToAstInfo(meta, isterm=True)
        return s_ast.ExprDict(astinfo, kids=kids)

    @lark.v_args(meta=True)
    def yieldvalu(self, meta, kids):
        kid = self._convert_child(kids[-1])
        astinfo = self.metaToAstInfo(meta)
        return s_ast.YieldValu(astinfo, kids=[kid])

    @lark.v_args(meta=True)
    def evalvalu(self, meta, kids):
        return self._convert_child(kids[0])

    @lark.v_args(meta=True)
    def embedquery(self, meta, kids):
        assert len(kids) == 1
        astinfo = AstInfo(self.text,
            meta.start_pos + 2, meta.end_pos - 1,
            meta.line, meta.end_line,
            meta.column, meta.end_column, False)

        kids[0].astinfo = astinfo

        return s_ast.EmbedQuery(astinfo, kids[0].getAstText(), kids=kids)

    @lark.v_args(meta=True)
    def funccall(self, meta, kids):

        astinfo = self.metaToAstInfo(meta)

        argkids = []
        kwargkids = []
        kwnames = set()
        indx = 1
        kcnt = len(kids)

        todo = collections.deque(kids)

        namekid = todo.popleft()

        while todo:

            kid = self._convert_child(todo.popleft())

            # look ahead for name = <valu> kwargs...
            if len(todo) >= 2:

                nextkid = todo[0]
                if isinstance(nextkid, lark.lexer.Token) and nextkid.type in ('EQNOSPACE', 'EQUAL', 'EQSPACE'):
                    todo.popleft()
                    valukid = self._convert_child(todo.popleft())

                    if kid.valu in kwnames:
                        self.raiseBadSyntax(f'Duplicate keyword argument "{kid.valu}" in function call', kid.astinfo)

                    kwnames.add(kid.valu)
                    kwargkids.append(s_ast.CallKwarg(kid.astinfo, (kid, valukid)))

                    continue

            if kwargkids:
                self.raiseBadSyntax('Positional argument follows keyword argument in function call', kid.astinfo)

            argkids.append(kid)

        args = s_ast.CallArgs(astinfo, kids=argkids)
        kwargs = s_ast.CallKwargs(astinfo, kids=kwargkids)
        return s_ast.FuncCall(astinfo, kids=[namekid, args, kwargs])

    @lark.v_args(meta=True)
    def varlist(self, meta, kids):
        kids = self._convert_children(kids)
        astinfo = self.metaToAstInfo(meta)
        return s_ast.VarList(astinfo, [k.valu for k in kids])

    @lark.v_args(meta=True)
    def operrelprop_pivot(self, meta, kids, isjoin=False):
        kids = self._convert_children(kids)
        astinfo = self.metaToAstInfo(meta)
        relprop, rest = kids[0], kids[1:]
        if not rest:
            return s_ast.PropPivotOut(astinfo, kids=kids, isjoin=isjoin)
        pval = s_ast.RelPropValue(astinfo, kids=(relprop,))
        return s_ast.PropPivot(astinfo, kids=(pval, *kids[1:]), isjoin=isjoin)

    @lark.v_args(meta=True)
    def operrelprop_join(self, meta, kids):
        return self.operrelprop_pivot(meta, kids, isjoin=True)

    @lark.v_args(meta=True)
    def stormcmdargs(self, meta, kids):
        newkids = []
        for kid in kids:
            if isinstance(kid, lark.lexer.Token) and kid.type == 'EQNOSPACE':
                continue
            newkids.append(self._convert_child(kid))
        astinfo = self.metaToAstInfo(meta)
        return s_ast.List(astinfo, kids=newkids)

    @lark.v_args(meta=True)
    def funcargs(self, meta, kids):
        '''
        A list of function parameters (as part of a function definition)
        '''
        kids = self._convert_children(kids)
        astinfo = self.metaToAstInfo(meta)

        newkids = []
        kwnames = set()
        kwfound = False

        todo = collections.deque(kids)

        while todo:

            kid = todo.popleft()

            if kid.valu in kwnames:
                mesg = f'Duplicate parameter "{kid.valu}" in function definition'
                self.raiseBadSyntax(mesg, kid.astinfo)

            kwnames.add(kid.valu)

            # look ahead for name = <default> kwarg decls
            if len(todo) >= 2:

                nextkid = todo[0]
                if isinstance(nextkid, s_ast.Const) and nextkid.valu == '=':
                    todo.popleft()
                    valukid = todo.popleft()

                    kwfound = True

                    newkids.append(s_ast.CallKwarg(kid.astinfo, (kid, valukid)))
                    continue

            if kwfound:
                mesg = f'Positional parameter "{kid.valu}" follows keyword parameter in definition'
                self.raiseBadSyntax(mesg, astinfo)

            newkids.append(kid)

        return s_ast.FuncArgs(astinfo, newkids)

    @lark.v_args(meta=True)
    def cmdrargs(self, meta, kids):
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
            self.raiseBadSyntax(mesg, kid.astinfo)

        return argv

    @lark.v_args(meta=True)
    def varderef(self, meta, kids):
        assert kids and len(kids) in (3, 4)
        astinfo = self.metaToAstInfo(meta)
        if kids[2] == '$':
            tokencls = terminalClassMap.get(kids[3].type, s_ast.Const)
            kidfo = self.metaToAstInfo(kids[3], isterm=True)
            newkid = s_ast.VarValue(kidfo, kids=[tokencls(kids[3], kids[3])])
        else:
            newkid = self._convert_child(kids[2])
        return s_ast.VarDeref(astinfo, kids=(kids[0], newkid))

    @lark.v_args(meta=True)
    def caseentry(self, meta, kids):
        assert kids and len(kids) >= 2
        astinfo = self.metaToAstInfo(meta)
        newkids = self._convert_children(kids)

        defcase = False

        if len(kids) == 2 and kids[0].type == 'DEFAULTCASE':
            defcase = True
            # Strip off the "Const: *" node
            newkids = [newkids[1]]

        return s_ast.CaseEntry(astinfo, kids=newkids, defcase=defcase)

    @lark.v_args(meta=True)
    def switchcase(self, meta, kids):
        kids = self._convert_children(kids)

        astinfo = self.metaToAstInfo(meta)

        # Check that we only have one default case
        defcase = [k for k in kids[1:] if k.defcase]

        deflen = len(defcase)
        if deflen > 1:
            mesg = f'Switch statements cannot have more than one default case. Found {deflen}.'
            raise self.raiseBadSyntax(mesg, astinfo)

        return s_ast.SwitchCase(astinfo, kids)

    @lark.v_args(meta=True)
    def liftreverse(self, meta, kids):
        assert len(kids) == 1
        astinfo = self.metaToAstInfo(meta)
        kids[0].reverseLift(astinfo)
        return kids[0]

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
        self.text = text
        self.size = len(self.text)

    def _larkToSynExc(self, e):
        '''
        Convert lark exception to synapse BadSyntax exception
        '''
        mesg = regex.split('[\n]', str(e))[0]
        soff = eoff = len(self.text)
        sline = eline = None
        scol = ecol = None
        token = None
        if isinstance(e, lark.exceptions.UnexpectedToken):
            expected = sorted(set(terminalEnglishMap[t] for t in e.expected))
            token = e.token.value
            soff = e.pos_in_stream
            eoff = soff + len(token)

            lines = token.splitlines()
            sline = e.line
            eline = sline + len(lines) - 1

            scol = e.column
            if len(lines) > 1:
                ecol = len(lines[-1])
            else:
                ecol = scol + len(token)

            valu = terminalEnglishMap.get(e.token.type, token)
            mesg = f"Unexpected token '{valu}' at line {sline}, column {scol}," \
                   f' expecting one of: {", ".join(expected)}'

        elif isinstance(e, lark.exceptions.VisitError):
            # Lark unhelpfully wraps an exception raised from AstConverter in a VisitError.  Unwrap it.
            origexc = e.orig_exc
            if not isinstance(origexc, s_exc.SynErr):
                raise e.orig_exc # pragma: no cover
            origexc.set('text', self.text)
            return s_exc.BadSyntax(**origexc.errinfo)

        elif isinstance(e, lark.exceptions.UnexpectedCharacters):  # pragma: no cover
            expected = sorted(set(terminalEnglishMap[t] for t in e.allowed))
            mesg += f'.  Expecting one of: {", ".join(expected)}'
            soff = eoff = e.pos_in_stream
            sline = eline = e.line
            scol = ecol = e.column
        elif isinstance(e, lark.exceptions.UnexpectedEOF):  # pragma: no cover
            expected = sorted(set(terminalEnglishMap[t] for t in e.expected))
            mesg += ' ' + ', '.join(expected)
            sline = eline = e.line
            scol = ecol = e.column

        highlight = {
            'hash': s_common.queryhash(self.text),
            'lines': (sline, eline),
            'columns': (scol, ecol),
            'offsets': (soff, eoff),
        }
        return s_exc.BadSyntax(at=soff, text=self.text, mesg=mesg, line=sline,
                               column=scol, token=token, highlight=highlight)

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
    return await s_coro._parserforked(parseQuery, args[0], mode=args[1])

async def _forkedParseEval(text):
    return await s_coro._parserforked(parseEval, text)

evalcache = s_cache.FixedCache(_forkedParseEval, size=100)
querycache = s_cache.FixedCache(_forkedParseQuery, size=100)

def massage_vartokn(astinfo, x):
    return s_ast.Const(astinfo, '' if not x else (x[1:-1] if x[0] == "'" else (unescape(x) if x[0] == '"' else x)))

# For AstConverter, one-to-one replacements from lark to synapse AST
terminalClassMap = {
    'ALLTAGS': lambda astinfo, _: s_ast.TagMatch(astinfo, ''),
    'BREAK': lambda astinfo, _: s_ast.BreakOper(astinfo),
    'CONTINUE': lambda astinfo, _: s_ast.ContinueOper(astinfo),
    'DOUBLEQUOTEDSTRING': lambda astinfo, x: s_ast.Const(astinfo, unescape(x)),  # drop quotes and handle escape characters
    'FORMATTEXT': lambda astinfo, x: s_ast.Const(astinfo, format_unescape(x)),  # handle escape characters
    'TRIPLEQUOTEDSTRING': lambda astinfo, x: s_ast.Const(astinfo, x[3:-3]), # drop the triple 's
    'NUMBER': lambda astinfo, x: s_ast.Const(astinfo, s_ast.parseNumber(x)),
    'HEXNUMBER': lambda astinfo, x: s_ast.Const(astinfo, s_ast.parseNumber(x)),
    'OCTNUMBER': lambda astinfo, x: s_ast.Const(astinfo, s_ast.parseNumber(x)),
    'BOOL': lambda astinfo, x: s_ast.Bool(astinfo, x == 'true'),
    'NULL': lambda astinfo, x: s_ast.Const(astinfo, None),
    'SINGLEQUOTEDSTRING': lambda astinfo, x: s_ast.Const(astinfo, x[1:-1]),  # drop quotes
    'NONQUOTEWORD': massage_vartokn,
    'VARTOKN': massage_vartokn,
    'EXPRVARTOKN': massage_vartokn,
}

# For AstConverter, one-to-one replacements from lark to synapse AST
ruleClassMap = {
    'abspropcond': s_ast.AbsPropCond,
    'argvquery': s_ast.ArgvQuery,
    'arraycond': s_ast.ArrayCond,
    'andexpr': s_ast.AndCond,
    'baresubquery': s_ast.SubQuery,
    'catchblock': s_ast.CatchBlock,
    'condsetoper': s_ast.CondSetOper,
    'condtrysetoper': lambda astinfo, kids: s_ast.CondSetOper(astinfo, kids, errok=True),
    'condsubq': s_ast.SubqCond,
    'dollarexpr': s_ast.DollarExpr,
    'edgeaddn1': s_ast.EditEdgeAdd,
    'edgedeln1': s_ast.EditEdgeDel,
    'edgeaddn2': lambda astinfo, kids: s_ast.EditEdgeAdd(astinfo, kids, n2=True),
    'edgedeln2': lambda astinfo, kids: s_ast.EditEdgeDel(astinfo, kids, n2=True),
    'editnodeadd': s_ast.EditNodeAdd,
    'editparens': s_ast.EditParens,
    'emit': s_ast.Emit,
    'initblock': s_ast.InitBlock,
    'emptyblock': s_ast.EmptyBlock,
    'finiblock': s_ast.FiniBlock,
    'formname': s_ast.FormName,
    'editpropdel': lambda astinfo, kids: s_ast.EditPropDel(astinfo, kids[1:]),
    'editpropset': s_ast.EditPropSet,
    'editcondpropset': s_ast.EditCondPropSet,
    'editpropsetmulti': s_ast.EditPropSetMulti,
    'edittagadd': s_ast.EditTagAdd,
    'edittagdel': lambda astinfo, kids: s_ast.EditTagDel(astinfo, kids[1:]),
    'edittagpropset': s_ast.EditTagPropSet,
    'edittagpropdel': lambda astinfo, kids: s_ast.EditTagPropDel(astinfo, kids[1:]),
    'editunivdel': lambda astinfo, kids: s_ast.EditUnivDel(astinfo, kids[1:]),
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
    'filtopermust': lambda astinfo, kids: s_ast.FiltOper(astinfo, [s_ast.Const(astinfo, '+')] + kids),
    'filtopernot': lambda astinfo, kids: s_ast.FiltOper(astinfo, [s_ast.Const(astinfo, '-')] + kids),
    'forloop': s_ast.ForLoop,
    'formatstring': s_ast.FormatString,
    'formjoin_formpivot': lambda astinfo, kids: s_ast.FormPivot(astinfo, kids, isjoin=True),
    'formjoin_pivotout': lambda astinfo, _: s_ast.PivotOut(astinfo, isjoin=True),
    'formjoinin_pivotin': lambda astinfo, kids: s_ast.PivotIn(astinfo, kids, isjoin=True),
    'formjoinin_pivotinfrom': lambda astinfo, kids: s_ast.PivotInFrom(astinfo, kids, isjoin=True),
    'formpivot_': s_ast.FormPivot,
    'formpivot_pivotout': s_ast.PivotOut,
    'formpivot_pivottotags': s_ast.PivotToTags,
    'formpivot_jointags': lambda astinfo, kids: s_ast.PivotToTags(astinfo, kids, isjoin=True),
    'formpivotin_': s_ast.PivotIn,
    'formpivotin_pivotinfrom': s_ast.PivotInFrom,
    'formtagprop': s_ast.FormTagProp,
    'hasabspropcond': s_ast.HasAbsPropCond,
    'hasrelpropcond': s_ast.HasRelPropCond,
    'hastagpropcond': s_ast.HasTagPropCond,
    'ifstmt': s_ast.IfStmt,
    'ifclause': s_ast.IfClause,
    'kwarg': lambda astinfo, kids: s_ast.CallKwarg(astinfo, kids=tuple(kids)),
    'liftbytag': s_ast.LiftTag,
    'liftformtag': s_ast.LiftFormTag,
    'liftprop': s_ast.LiftProp,
    'liftpropby': s_ast.LiftPropBy,
    'lifttagtag': s_ast.LiftTagTag,
    'liftbyarray': s_ast.LiftByArray,
    'liftbytagprop': s_ast.LiftTagProp,
    'liftbyformtagprop': s_ast.LiftFormTagProp,
    'looklist': s_ast.LookList,
    'lookup': s_ast.Lookup,
    'n1join': lambda astinfo, kids: s_ast.N1Walk(astinfo, kids, isjoin=True),
    'n2join': lambda astinfo, kids: s_ast.N2Walk(astinfo, kids, isjoin=True),
    'n1walk': s_ast.N1Walk,
    'n2walk': s_ast.N2Walk,
    'n1walknjoin': lambda astinfo, kids: s_ast.N1WalkNPivo(astinfo, kids, isjoin=True),
    'n2walknjoin': lambda astinfo, kids: s_ast.N2WalkNPivo(astinfo, kids, isjoin=True),
    'n1walknpivo': s_ast.N1WalkNPivo,
    'n2walknpivo': s_ast.N2WalkNPivo,
    'notcond': s_ast.NotCond,
    'opervarlist': s_ast.VarListSetOper,
    'orexpr': s_ast.OrCond,
    'query': s_ast.Query,
    'rawpivot': s_ast.RawPivot,
    'return': s_ast.Return,
    'relprop': lambda astinfo, kids: s_ast.RelProp(astinfo, [s_ast.Const(k.astinfo, k.valu.lstrip(':')) if isinstance(k, s_ast.Const) else k for k in kids]),
    'relpropcond': s_ast.RelPropCond,
    'relpropvalu': lambda astinfo, kids: s_ast.RelPropValue(astinfo, [s_ast.Const(k.astinfo, k.valu.lstrip(':')) if isinstance(k, s_ast.Const) else k for k in kids]),
    'relpropvalue': s_ast.RelPropValue,
    'search': s_ast.Search,
    'setitem': lambda astinfo, kids: s_ast.SetItemOper(astinfo, [kids[0], kids[1], kids[3]]),
    'setvar': s_ast.SetVarOper,
    'stop': s_ast.Stop,
    'stormcmd': lambda astinfo, kids: s_ast.CmdOper(astinfo, kids=kids if len(kids) == 2 else (kids[0], s_ast.Const(astinfo, tuple()))),
    'stormfunc': s_ast.Function,
    'tagcond': s_ast.TagCond,
    'tagname': s_ast.TagName,
    'tagmatch': s_ast.TagMatch,
    'tagprop': s_ast.TagProp,
    'tagvalu': s_ast.TagValue,
    'tagpropvalu': s_ast.TagPropValue,
    'tagvalucond': s_ast.TagValuCond,
    'tagpropcond': s_ast.TagPropCond,
    'trycatch': s_ast.TryCatch,
    'univprop': s_ast.UnivProp,
    'univpropvalu': s_ast.UnivPropValue,
    'valulist': s_ast.List,
    'vareval': s_ast.VarEvalOper,
    'varvalue': s_ast.VarValue,
    'whileloop': s_ast.WhileLoop,
    'wordtokn': lambda astinfo, kids: s_ast.Const(astinfo, ''.join([str(k.valu) for k in kids]))
}

escape_re = regex.compile(r"(?<!\\)((\\\\)*)'")

def format_unescape(valu):
    repl = valu.replace('\\`', '`').replace('\\{', '{')
    repl = escape_re.sub(r"\1\'", repl)
    return unescape(f"'''{repl}'''")

def unescape(valu):
    '''
    Parse a string for backslash-escaped characters and omit them.
    The full list of escaped characters can be found at
    https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals
    '''
    try:
        ret = ast.literal_eval(valu)
    except (SyntaxError, ValueError) as e:
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

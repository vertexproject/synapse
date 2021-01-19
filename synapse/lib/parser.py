import ast
import lark  # type: ignore
import regex  # type: ignore

import synapse.exc as s_exc

import synapse.lib.ast as s_ast
import synapse.lib.cache as s_cache
import synapse.lib.datfile as s_datfile

# TL;DR:  *rules* are the internal nodes of an abstract syntax tree (AST), *terminals* are the leaves

# Note: this file is coupled strongly to synapse/lib/storm.lark.  Any changes to that file will probably require
# changes here

# For easier-to-understand syntax errors
terminalEnglishMap = {
    'ABSPROP': 'absolute or universal property',
    'ABSPROPNOUNIV': 'absolute property',
    'ALLTAGS': '#',
    'AND': 'and',
    'BOOL': 'boolean',
    'BREAK': 'break',
    'CASEBARE': 'case value',
    'CCOMMENT': 'C comment',
    'CMDOPT': 'command line option',
    'CMDNAME': 'command name',
    'CMDRTOKN': 'An unquoted string parsed as a cmdr arg',
    'WHITETOKN': 'An unquoted string terminated by whitespace',
    'CMPR': 'comparison operator',
    'BYNAME': 'named comparison operator',
    'COLON': ':',
    'COMMA': ',',
    'CONTINUE': 'continue',
    'FINI': 'fini',
    'INIT': 'init',
    'CPPCOMMENT': 'c++ comment',
    'DEREFMATCHNOSEP': 'key or variable',
    'DOLLAR': '$',
    'DOT': '.',
    'DOUBLEQUOTEDSTRING': 'double-quoted string',
    'ELIF': 'elif',
    'ELSE': 'else',
    'EQUAL': '=',
    'EXPRCMPR': 'expression comparison operator',
    'EXPRDIVIDE': '/',
    'EXPRMINUS': '-',
    'EXPRPLUS': '+',
    'EXPRTIMES': '*',
    'FILTPREFIX': '+ or -',
    'FOR': 'for',
    'FUNCTION': 'function',
    'HEXNUMBER': 'number',
    'IF': 'if',
    'IN': 'in',
    'LBRACE': '[',
    'LISTTOKN': 'An unquoted list-compatible string.',
    'LPAR': '(',
    'LSQB': '{',
    'NONQUOTEWORD': 'unquoted value',
    'NOT': 'not',
    'NUMBER': 'number',
    'OR': 'or',
    'PROPNAME': 'property name',
    'PROPS': 'absolute property name',
    'BASEPROP': 'base property name',
    'RBRACE': ']',
    'RELNAME': 'relative property',
    'RPAR': ')',
    'RSQB': '}',
    'SETOPER': '= or ?=',
    'SETTAGOPER': '?',
    'SINGLEQUOTEDSTRING': 'single-quoted string',
    'SWITCH': 'switch',
    'TAG': 'plain tag name',
    'TAGMATCH': 'tag name with asterisks',
    'UNIVNAME': 'universal property',
    'VARTOKN': 'variable',
    'VBAR': '|',
    'WHILE': 'while',
    'WORDTOKN': 'A whitespace tokenized string',
    'YIELD': 'yield',
    '_ARRAYCONDSTART': '*[',
    '_DEREF': '*',
    '_EDGEADDN1INIT': '+(',
    '_EDGEADDN1FINI': ')>',
    '_EDGEDELN1INIT': '-(',
    '_EDGEDELN1FINI': ')>',
    '_EDGEADDN2INIT': '<(',
    '_EDGEADDN2FINI': ')+',
    '_EDGEDELN2INIT': '<(',
    '_EDGEDELN2FINI': ')-',
    '_EMBEDQUERYSTART': '${',
    '_LEFTJOIN': '<+-',
    '_LEFTPIVOT': '<-',
    '_WALKNPIVON1': '-->',
    '_WALKNPIVON2': '<--',
    '_N1WALKINIT': '-(',
    '_N1WALKFINI': ')>',
    '_N2WALKINIT': '<(',
    '_N2WALKFINI': ')-',
    '_ONLYTAGPROP': '#:',
    '_RETURN': 'return',
    '_RIGHTJOIN': '-+>',
    '_RIGHTPIVOT': '->',
    '_TRYSET': '?=',
    '_WS': 'whitespace',
    '_WSCOMM': 'whitespace or comment'
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
    def subquery(self, kids, meta):
        assert len(kids) <= 2
        hasyield = (len(kids) == 2)
        kid = self._convert_child(kids[-1])
        kid.hasyield = hasyield

        return kid

    @lark.v_args(meta=True)
    def baresubquery(self, kids, meta):
        assert len(kids) == 1

        epos = getattr(meta, 'end_pos', 0)
        spos = getattr(meta, 'start_pos', 0)

        subq = s_ast.SubQuery(kids)
        subq.text = self.text[spos:epos]

        return subq

    @lark.v_args(meta=True)
    def argvquery(self, kids, meta):
        assert len(kids) == 1

        epos = getattr(meta, 'end_pos', 0)
        spos = getattr(meta, 'start_pos', 0)

        argq = s_ast.ArgvQuery(kids)
        argq.text = self.text[spos:epos]

        return argq

    def looklist(self, kids):
        kids = self._convert_children(kids)
        return s_ast.Lookup(kids)

    def yieldvalu(self, kids):
        kid = self._convert_child(kids[-1])
        return s_ast.YieldValu(kids=[kid])

    @lark.v_args(meta=True)
    def lookup(self, kids, meta):
        kids = self._convert_children(kids)
        look = s_ast.Lookup(kids=kids)
        return look

    @lark.v_args(meta=True)
    def query(self, kids, meta):
        kids = self._convert_children(kids)

        epos = getattr(meta, 'end_pos', 0)
        spos = getattr(meta, 'start_pos', 0)

        quer = s_ast.Query(kids=kids)
        quer.text = self.text[spos:epos]

        return quer

    @lark.v_args(meta=True)
    def embedquery(self, kids, meta):
        assert len(kids) == 1
        text = kids[0].text
        ast = s_ast.EmbedQuery(text, kids)
        return ast

    def funccall(self, kids):
        kids = self._convert_children(kids)
        arglist = [k for k in kids[1:] if not isinstance(k, s_ast.CallKwarg)]
        args = s_ast.CallArgs(kids=arglist)

        kwarglist = [k for k in kids[1:] if isinstance(k, s_ast.CallKwarg)]
        kwargs = s_ast.CallKwargs(kids=kwarglist)
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
        kids = self._convert_children(kids)
        argv = []

        for kid in kids:
            if isinstance(kid, s_ast.SubQuery):
                argv.append(s_ast.Const(kid.text))
            else:
                argv.append(self._convert_child(kid))

        return s_ast.List(kids=argv)

    def cmdrargs(self, kids):
        argv = []

        for kid in kids:

            if isinstance(kid, s_ast.SubQuery):
                argv.append(kid.text)
                continue

            # this one should never happen, but is here in case
            if isinstance(kid, s_ast.Const): # pragma: no cover
                argv.append(kid.valu)
                continue

            if isinstance(kid, lark.lexer.Token):
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
        assert kids and len(kids) == 2
        newkid = kids[1]
        if newkid[0] == '$':
            tokencls = terminalClassMap.get(newkid.type, s_ast.Const)
            newkid = s_ast.VarValue(kids=[tokencls(newkid[1:])])
        else:
            newkid = self._convert_child(kids[1])
        return s_ast.VarDeref(kids=(kids[0], newkid))

    def tagprop(self, kids):
        kids = self._convert_children(kids)
        return s_ast.TagProp(kids=kids)

    def formtagprop(self, kids):
        kids = self._convert_children(kids)
        return s_ast.FormTagProp(kids=kids)

    def tagname(self, kids):
        assert kids and len(kids) == 1
        kid = kids[0]
        if not isinstance(kid, lark.lexer.Token):
            return self._convert_child(kid)

        kids = self._tagsplit(kid.value)
        return s_ast.TagName(kids=kids)

    def valulist(self, kids):
        kids = self._convert_children(kids)
        return s_ast.List(kids=kids)

    def univpropvalu(self, kids):
        kids = self._convert_children(kids)
        return s_ast.UnivPropValue(kids=kids)

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

QueryParser = lark.Lark(_grammar, regex=True, start='query', propagate_positions=True)
LookupParser = lark.Lark(_grammar, regex=True, start='lookup', propagate_positions=True)
CmdrParser = lark.Lark(_grammar, regex=True, start='cmdrargs', propagate_positions=True)

_eofre = regex.compile(r'''Terminal\('(\w+)'\)''')

class Parser:
    '''
    Storm query parser
    '''
    def __init__(self, text, offs=0):

        self.offs = offs
        assert text is not None
        self.text = text.strip()
        self.size = len(self.text)

    def _eofParse(self, mesg):
        '''
        Takes a string like "Unexpected end of input! Expecting a terminal of: [Terminal('FOR'), ...] and returns
        a unique'd set of terminal names.
        '''
        return sorted(set(_eofre.findall(mesg)))

    def _larkToSynExc(self, e):
        '''
        Convert lark exception to synapse badGrammar exception
        '''
        mesg = regex.split('[\n!]', e.args[0])[0]
        at = len(self.text)
        if isinstance(e, lark.exceptions.UnexpectedCharacters):
            mesg += f'.  Expecting one of: {", ".join(terminalEnglishMap[t] for t in sorted(set(e.allowed)))}'
            at = e.pos_in_stream
        elif isinstance(e, lark.exceptions.ParseError):
            if mesg == 'Unexpected end of input':
                mesg += f'.  Expecting one of: {", ".join(terminalEnglishMap[t] for t in self._eofParse(e.args[0]))}'

        return s_exc.BadSyntax(at=at, text=self.text, mesg=mesg)

    def query(self):
        '''
        Parse the storm query

        Returns (s_ast.Query):  instance of parsed query
        '''
        try:
            tree = QueryParser.parse(self.text)
        except lark.exceptions.LarkError as e:
            raise self._larkToSynExc(e) from None
        newtree = AstConverter(self.text).transform(tree)
        newtree.text = self.text
        return newtree

    def lookup(self):
        try:
            tree = LookupParser.parse(self.text)
        except lark.exceptions.LarkError as e:
            raise self._larkToSynExc(e) from None
        newtree = AstConverter(self.text).transform(tree)
        newtree.text = self.text
        return newtree

    def cmdrargs(self):
        '''
        Parse command args that might have storm queries as arguments
        '''
        try:
            tree = CmdrParser.parse(self.text)
        except lark.exceptions.LarkError as e:
            raise self._larkToSynExc(e) from None
        return AstConverter(self.text).transform(tree)

@s_cache.memoize(size=100)
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

    return Parser(text).query()

def massage_vartokn(x):
    return s_ast.Const('' if not x else (x[1:-1] if x[0] == "'" else (unescape(x) if x[0] == '"' else x)))

# For AstConverter, one-to-one replacements from lark to synapse AST
terminalClassMap = {
    'ABSPROP': s_ast.AbsProp,
    'ABSPROPNOUNIV': s_ast.AbsProp,
    'ALLTAGS': lambda _: s_ast.TagMatch(''),
    'BREAK': lambda _: s_ast.BreakOper(),
    'CONTINUE': lambda _: s_ast.ContinueOper(),
    'DEREFMATCHNOSEP': massage_vartokn,
    'DOUBLEQUOTEDSTRING': lambda x: s_ast.Const(unescape(x)),  # drop quotes and handle escape characters
    'NUMBER': lambda x: s_ast.Const(s_ast.parseNumber(x)),
    'HEXNUMBER': lambda x: s_ast.Const(s_ast.parseNumber(x)),
    'BOOL': lambda x: s_ast.Bool(x == 'true'),
    'SINGLEQUOTEDSTRING': lambda x: s_ast.Const(x[1:-1]),  # drop quotes
    'TAGMATCH': lambda x: s_ast.TagMatch(kids=AstConverter._tagsplit(x)),
    'VARTOKN': massage_vartokn,
}

# For AstConverter, one-to-one replacements from lark to synapse AST
ruleClassMap = {
    'abspropcond': s_ast.AbsPropCond,
    'arraycond': s_ast.ArrayCond,
    'andexpr': s_ast.AndCond,
    'condsubq': s_ast.SubqCond,
    'dollarexpr': s_ast.DollarExpr,
    'edgeaddn1': s_ast.EditEdgeAdd,
    'edgedeln1': s_ast.EditEdgeDel,
    'edgeaddn2': lambda kids: s_ast.EditEdgeAdd(kids, n2=True),
    'edgedeln2': lambda kids: s_ast.EditEdgeDel(kids, n2=True),
    'editnodeadd': s_ast.EditNodeAdd,
    'editparens': s_ast.EditParens,
    'initblock': s_ast.InitBlock,
    'finiblock': s_ast.FiniBlock,
    'formname': s_ast.FormName,
    'editpropdel': s_ast.EditPropDel,
    'editpropset': s_ast.EditPropSet,
    'edittagadd': s_ast.EditTagAdd,
    'edittagdel': s_ast.EditTagDel,
    'edittagpropset': s_ast.EditTagPropSet,
    'edittagpropdel': s_ast.EditTagPropDel,
    'editunivdel': s_ast.EditUnivDel,
    'editunivset': s_ast.EditPropSet,
    'expror': s_ast.ExprOrNode,
    'exprand': s_ast.ExprAndNode,
    'exprnot': s_ast.UnaryExprNode,
    'exprcmp': s_ast.ExprNode,
    'exprproduct': s_ast.ExprNode,
    'exprsum': s_ast.ExprNode,
    'filtoper': s_ast.FiltOper,
    'forloop': s_ast.ForLoop,
    'whileloop': s_ast.WhileLoop,
    'formjoin_formpivot': lambda kids: s_ast.FormPivot(kids, isjoin=True),
    'formjoin_pivotout': lambda _: s_ast.PivotOut(isjoin=True),
    'formjoinin_pivotin': lambda kids: s_ast.PivotIn(kids, isjoin=True),
    'formjoinin_pivotinfrom': lambda kids: s_ast.PivotInFrom(kids, isjoin=True),
    'formpivot_': s_ast.FormPivot,
    'formpivot_pivotout': s_ast.PivotOut,
    'formpivot_pivottotags': s_ast.PivotToTags,
    'formpivotin_': s_ast.PivotIn,
    'formpivotin_pivotinfrom': s_ast.PivotInFrom,
    'funcargs': s_ast.FuncArgs,
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
    'n1walk': s_ast.N1Walk,
    'n2walk': s_ast.N2Walk,
    'n1walknpivo': s_ast.N1WalkNPivo,
    'n2walknpivo': s_ast.N2WalkNPivo,
    'notcond': s_ast.NotCond,
    'opervarlist': s_ast.VarListSetOper,
    'orexpr': s_ast.OrCond,
    'rawpivot': s_ast.RawPivot,
    'return': s_ast.Return,
    'relprop': s_ast.RelProp,
    'relpropcond': s_ast.RelPropCond,
    'relpropvalu': s_ast.RelPropValue,
    'relpropvalue': s_ast.RelPropValue,
    'setitem': s_ast.SetItemOper,
    'setvar': s_ast.SetVarOper,
    'stormcmd': lambda kids: s_ast.CmdOper(kids=kids if len(kids) == 2 else (kids[0], s_ast.Const(tuple()))),
    'stormfunc': s_ast.Function,
    'tagcond': s_ast.TagCond,
    'tagvalu': s_ast.TagValue,
    'tagpropvalu': s_ast.TagPropValue,
    'tagvalucond': s_ast.TagValuCond,
    'tagpropcond': s_ast.TagPropCond,
    'vareval': s_ast.VarEvalOper,
    'varvalue': s_ast.VarValue,
    'univprop': s_ast.UnivProp
}

def unescape(valu):
    '''
    Parse a string for backslash-escaped characters and omit them.
    The full list of escaped characters can be found at
    https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals
    '''
    ret = ast.literal_eval(valu)
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
    Parse in a command line string which may be quoted.
    '''
    tree = CmdStringParser.parse(text[off:])
    valu, newoff = CmdStringer().transform(tree)
    return valu, off + newoff


@lark.v_args(meta=True)
class CmdStringer(lark.Transformer):

    def valu(self, kids, meta):
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

    def cmdstring(self, kids, meta):
        return kids[0]

    def alist(self, kids, meta):
        return [k[0] for k in kids], meta.end_pos

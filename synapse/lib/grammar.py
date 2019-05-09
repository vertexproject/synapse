import lark  # type: ignore
import regex  # type: ignore

import synapse.exc as s_exc

import synapse.lib.ast as s_ast
import synapse.lib.datfile as s_datfile

# TL;DR:  *rules* are the internal nodes of an abstract syntax tree (AST), *terminals* are the leaves

# Note: this file is coupled strongly to synapse/lib/storm.lark.  Any changes to that file will probably require
# changes here

# For AstConverter, one-to-one replacements from lark to synapse AST
ruleClassMap = {
    'abspropcond': s_ast.AbsPropCond,
    'condsubq': s_ast.SubqCond,
    'dollarexpr': s_ast.DollarExpr,
    'editnodeadd': s_ast.EditNodeAdd,
    'editpropdel': s_ast.EditPropDel,
    'editpropset': s_ast.EditPropSet,
    'edittagadd': s_ast.EditTagAdd,
    'edittagdel': s_ast.EditTagDel,
    'editunivdel': s_ast.EditUnivDel,
    'editunivset': s_ast.EditPropSet,
    'exprcmp': s_ast.ExprNode,
    'exprproduct': s_ast.ExprNode,
    'exprsum': s_ast.ExprNode,
    'filtoper': s_ast.FiltOper,
    'forloop': s_ast.ForLoop,
    'formjoin_formpivot': lambda kids: s_ast.FormPivot(kids, isjoin=True),
    'formjoin_pivotout': lambda _: s_ast.PivotOut(isjoin=True),
    'formjoinin_pivotin': lambda kids: s_ast.PivotIn(kids, isjoin=True),
    'formjoinin_pivotinfrom': lambda kids: s_ast.PivotInFrom(kids, isjoin=True),
    'formpivot_': s_ast.FormPivot,
    'formpivot_pivotout': s_ast.PivotOut,
    'formpivot_pivottotags': s_ast.PivotToTags,
    'formpivotin_': s_ast.PivotIn,
    'formpivotin_pivotinfrom': s_ast.PivotInFrom,
    'hasabspropcond': s_ast.HasAbsPropCond,
    'hasrelpropcond': s_ast.HasRelPropCond,
    'kwarg': lambda kids: s_ast.CallKwarg(kids=tuple(kids)),
    'liftbytag': s_ast.LiftTag,
    'liftformtag': s_ast.LiftFormTag,
    'liftprop': s_ast.LiftProp,
    'liftpropby': s_ast.LiftPropBy,
    'lifttagtag': s_ast.LiftTagTag,
    'notcond': s_ast.NotCond,
    'opervarlist': s_ast.VarListSetOper,
    'query': s_ast.Query,
    'relpropcond': s_ast.RelPropCond,
    'relpropvalu': s_ast.RelPropValue,
    'relpropvalue': s_ast.RelPropValue,
    'stormcmd': lambda kids: s_ast.CmdOper(kids=kids if len(kids) == 2 else (kids[0], s_ast.Const(tuple()))),
    'tagcond': s_ast.TagCond,
    'tagpropvalue': s_ast.TagPropValue,
    'tagvalucond': s_ast.TagValuCond,
    'valuvar': s_ast.VarSetOper,
    'varderef': s_ast.VarDeref,
    'vareval': s_ast.VarEvalOper,
    'varvalue': s_ast.VarValue,
    'orexpr': s_ast.OrCond,
    'andexpr': s_ast.AndCond
}

# For AstConverter, one-to-one replacements from lark to synapse AST
terminalClassMap = {
    'ABSPROP': s_ast.AbsProp,
    'ABSPROPNOUNIV': s_ast.AbsProp,
    'BREAK': lambda _: s_ast.BreakOper(),
    'CMDNAME': s_ast.Const,
    'CMPR': s_ast.Const,
    'CONTINUE': lambda _: s_ast.ContinueOper(),
    'EXPRCMPR': s_ast.Const,
    'EXPRDIVIDE': s_ast.Const,
    'EXPRMINUS': s_ast.Const,
    'EXPRPLUS': s_ast.Const,
    'EXPRTIMES': s_ast.Const,
    'DOUBLEQUOTEDSTRING': lambda x: s_ast.Const(x[1:-1]),  # drop quotes
    'FILTPREFIX': s_ast.Const,
    'NONCMDQUOTE': s_ast.Const,
    'NONQUOTEWORD': s_ast.Const,
    'NUMBER': s_ast.Const,
    'PROPNAME': s_ast.Const,
    'RELPROP': lambda x: s_ast.RelProp(x[1:]),  # drop leading :
    'SINGLEQUOTEDSTRING': lambda x: s_ast.Const(x[1:-1]),  # drop quotes
    'TAGMATCH': s_ast.TagMatch,
    'UNIVPROP': s_ast.UnivProp,
    'VARCHARS': s_ast.Const,
    'VARTOKN': s_ast.Const,
    'ALLTAGS': lambda _: s_ast.TagMatch('')
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

    def _convert_children(self, children):
        return [self._convert_child(k) for k in children]

    def _convert_child(self, child):
        if not isinstance(child, lark.lexer.Token):
            return child
        assert child.type in terminalClassMap, f'Unknown grammar terminal: {child.type}'
        tokencls = terminalClassMap[child.type]
        newkid = tokencls(child.value)
        return newkid

    def __default__(self, treedata, children, treemeta):
        assert treedata in ruleClassMap, f'Unknown grammar rule: {treedata}'
        cls = ruleClassMap[treedata]
        newkids = self._convert_children(children)
        return cls(newkids)

    @lark.v_args(meta=True)
    def subquery(self, kids, meta):
        assert len(kids) == 1
        kids = self._convert_children(kids)
        ast = s_ast.SubQuery(kids)

        # Keep the text of the subquery in case used by command
        ast.text = self.text[meta.start_pos:meta.end_pos]
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
            if isinstance(kid, s_ast.Const):
                newkid = kid.valu
            elif isinstance(kid, s_ast.SubQuery):
                newkid = kid.text
            else:
                assert False, 'Unexpected rule'  # pragma: no cover
            argv.append(newkid)

        return s_ast.Const(tuple(argv))

    def tagname(self, kids):
        assert kids and len(kids) == 1
        kid = kids[0]
        if kid.type == 'TAG':
            return s_ast.TagName(kid.value)

        assert kid.type == 'VARTOKN'
        kids = self._convert_children(kids)
        return s_ast.VarValue(kids)

    def valulist(self, kids):
        kids = self._convert_children(kids)
        return s_ast.List(None, kids=kids)

    def univpropvalu(self, kids):
        kids = self._convert_children(kids)
        return s_ast.UnivPropValue(kids=kids)

    def switchcase(self, kids):
        newkids = []

        it = iter(kids)

        varvalu = next(it)
        newkids.append(varvalu)
        assert isinstance(varvalu, s_ast.VarValue)

        for casekid, sqkid in zip(it, it):
            subquery = self._convert_child(sqkid)
            if casekid.valu == '*':
                caseentry = s_ast.CaseEntry(kids=[subquery])
            else:
                casekid = self._convert_child(casekid)
                caseentry = s_ast.CaseEntry(kids=[casekid, subquery])

            newkids.append(caseentry)

        return s_ast.SwitchCase(newkids)

    def casevalu(self, kids):
        assert len(kids) == 1
        kid = kids[0]

        if kid.type == 'DOUBLEQUOTEDSTRING':
            return self._convert_child(kid)

        return s_ast.Const(kid.value[:-1])  # drop the trailing ':'


with s_datfile.openDatFile('synapse.lib/storm.lark') as larkf:
    _grammar = larkf.read().decode()

QueryParser = lark.Lark(_grammar, start='query', propagate_positions=True)
CmdrParser = lark.Lark(_grammar, start='query', propagate_positions=True, keep_all_tokens=True)
StormCmdParser = lark.Lark(_grammar, start='stormcmdargs', propagate_positions=True)

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
        Convert lark exception to synapse badGrammar exception
        '''
        mesg = regex.split('[\n!]', e.args[0])[0]
        at = len(self.text)
        if isinstance(e, lark.exceptions.UnexpectedCharacters):
            mesg += f'.  Expecting one of: {", ".join(t for t in e.allowed)}'
            at = e.pos_in_stream

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

    def stormcmdargs(self):
        '''
        Parse command args that might have storm queries as arguments
        '''
        try:
            tree = StormCmdParser.parse(self.text)
        except lark.exceptions.LarkError as e:
            raise self._larkToSynExc(e) from None
        newtree = AstConverter(self.text).transform(tree)
        assert isinstance(newtree, s_ast.Const)
        return newtree.valu


# TODO:  commonize with storm.lark
scmdre = regex.compile('[a-z][a-z0-9.]+')
univre = regex.compile(r'\.[a-z][a-z0-9]*([:.][a-z0-9]+)*')
propre = regex.compile(r'[a-z][a-z0-9]*(:[a-z0-9]+)+([:.][a-z][a-z0-9]+)*')
formre = regex.compile(r'[a-z][a-z0-9]*(:[a-z0-9]+)+')

def isPropName(name):
    return propre.fullmatch(name) is not None

def isCmdName(name):
    return scmdre.fullmatch(name) is not None

def isUnivName(name):
    return univre.fullmatch(name) is not None

def isFormName(name):
    return formre.fullmatch(name) is not None

floatre = regex.compile(r'\s*-?\d+(\.\d+)?')

def parse_float(text, off):
    match = floatre.match(text[off:])
    if match is None:
        raise s_exc.BadSyntax(at=off, mesg='Invalid float')

    s = match.group(0)

    return float(s), len(s) + off

def nom(txt, off, cset, trim=True):
    '''
    Consume chars in set from the string and return (subtxt,offset).

    Example:

        text = "foo(bar)"
        chars = set('abcdefghijklmnopqrstuvwxyz')

        name,off = nom(text,0,chars)

    Note:

    This really shouldn't be used for new code
    '''
    if trim:
        while len(txt) > off and txt[off] in whites:
            off += 1

    r = ''
    while len(txt) > off and txt[off] in cset:
        r += txt[off]
        off += 1

    if trim:
        while len(txt) > off and txt[off] in whites:
            off += 1

    return r, off

def meh(txt, off, cset):
    r = ''
    while len(txt) > off and txt[off] not in cset:
        r += txt[off]
        off += 1
    return r, off

whites = set(' \t\n')
alphaset = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')

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

CmdStringParser = lark.Lark(CmdStringGrammar,
                            start='cmdstring',
                            propagate_positions=True)

def parse_cmd_string(text, off):
    '''
    Parse in a command line string which may be quoted.
    '''
    tree = CmdStringParser.parse(text[off:])
    valu, newoff = CmdStringer().transform(tree)
    return valu, off + newoff

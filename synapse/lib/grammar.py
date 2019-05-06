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
    'kwarg': lambda kids: s_ast.CallKwarg(kids=tuple(kids)),
    'liftbytag': s_ast.LiftTag,
    'liftformtag': s_ast.LiftFormTag,
    'liftprop': s_ast.LiftProp,
    'liftpropby': s_ast.LiftPropBy,
    'lifttagtag': s_ast.LiftTagTag,
    'opervarlist': s_ast.VarListSetOper,
    'query': s_ast.Query,
    'relpropvalu': s_ast.RelPropValue,
    'stormcmd': lambda kids: s_ast.CmdOper(kids=kids if len(kids) == 2 else (kids[0], s_ast.Const(tuple()))),
    'tagpropvalue': s_ast.TagPropValue,
    'valuvar': s_ast.VarSetOper,
    'vareval': s_ast.VarEvalOper,
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
    'NOT_': s_ast.Const,
    'PROPNAME': s_ast.Const,
    'RELPROP': lambda x: s_ast.RelProp(x[1:]),  # drop leading :
    'SINGLEQUOTEDSTRING': lambda x: s_ast.Const(x[1:-1]),  # drop quotes
    'TAGMATCH': lambda x: s_ast.TagMatch(x[1:]),  # drop leading '#'
    'UNIVPROP': s_ast.UnivProp,
    'VARCHARS': s_ast.Const,
    'VARTOKN': s_ast.Const,
}

class TmpVarCall:
    '''
    A temporary holder to collect varcall context
    '''
    def __init__(self, kids):
        self.kids = kids

    def repr(self):
        return f'{self.__class__.__name__}: {self.kids}'

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

    def cond(self, kids):
        kids = self._convert_children(kids)
        first, cmprvalu = kids[0], kids[1:]

        if isinstance(first, s_ast.RelProp):
            if not cmprvalu:
                return s_ast.HasRelPropCond(kids=kids)

            prop = s_ast.RelPropValue(kids=(first, ))
            return s_ast.RelPropCond(kids=(prop, ) + tuple(cmprvalu))

        elif isinstance(first, s_ast.Const) and first.valu == 'not':
            return s_ast.NotCond(kids=(cmprvalu))

        elif isinstance(first, s_ast.TagMatch):
            if not cmprvalu:
                return s_ast.TagCond(kids=kids)

            return s_ast.TagValuCond(kids=kids)

        elif isinstance(first, s_ast.AbsProp):
            if not cmprvalu:
                return s_ast.HasAbsPropCond(kids=kids)
            else:
                return s_ast.AbsPropCond(kids=kids)

        elif isinstance(first, s_ast.UnivProp):
            prop = s_ast.RelPropValue(kids=(first, ))
            if not cmprvalu:
                return s_ast.HasRelPropCond(kids=prop)
            else:
                return s_ast.RelPropCond(kids=(prop, ) + tuple(cmprvalu))

        elif isinstance(first, (s_ast.OrCond, s_ast.AndCond, s_ast.HasRelPropCond, s_ast.NotCond, s_ast.SubqCond)):
            assert len(kids) == 1
            return first

        assert False, 'Unknown first child of cond'  # pragma: no cover

    def condexpr(self, kids):
        if len(kids) == 1:
            return kids[0]
        assert len(kids) == 3
        operand1, operand2 = kids[0], kids[2]
        oper = kids[1].value

        if oper == 'and':
            return s_ast.AndCond(kids=[operand1, operand2])
        if oper == 'or':
            return s_ast.OrCond(kids=[operand1, operand2])

        assert False, 'Unknown condexpr operator'  # pragma: no cover

    def varvalu(self, kids):
        # FIXME really should be restructured; emulating old code for now

        varv = s_ast.VarValue(kids=self._convert_children([kids[0]]))
        for kid in kids[1:]:
            if isinstance(kid, lark.lexer.Token):
                assert kid.type == 'VARDEREF'
                varv = s_ast.VarDeref(kids=[varv, s_ast.Const(kid.value[1:])])
            elif isinstance(kid, TmpVarCall):
                callkids = self._convert_children(kid.kids)
                arglist = [k for k in callkids if not isinstance(k, s_ast.CallKwarg)]
                args = s_ast.CallArgs(kids=arglist)

                kwarglist = [k for k in callkids if isinstance(k, s_ast.CallKwarg)]
                kwargs = s_ast.CallKwargs(kids=kwarglist)
                varv = s_ast.FuncCall(kids=[varv, args, kwargs])
            else:
                assert False, 'Unexpected rule'  # pragma: no cover

        return varv

    def varcall(self, kids):
        '''
        Defer the conversion until the parent varvalu
        '''
        return TmpVarCall(kids)

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
        return self.varvalu(kids)

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


# Cached lark parsers so lark doesn't re-parse the grammar file for every instance
LarkQueryParser = None
LarkStormCmdParser = None

class Parser:
    '''
    Storm query parser
    '''

    def __init__(self, text, offs=0):

        global LarkQueryParser
        global LarkStormCmdParser

        if LarkQueryParser is None:
            with s_datfile.openDatFile('synapse.lib/storm.lark') as larkf:
                grammar = larkf.read().decode()

            LarkQueryParser = lark.Lark(grammar, start='query', propagate_positions=True)
            LarkStormCmdParser = lark.Lark(grammar, start='stormcmdargs', propagate_positions=True)

        self.queryparser = LarkQueryParser
        self.stormcmdparser = LarkStormCmdParser

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
            tree = self.queryparser.parse(self.text)
        except lark.exceptions.LarkError as e:
            raise self._larkToSynExc(e)
        newtree = AstConverter(self.text).transform(tree)
        newtree.text = self.text
        return newtree

    def stormcmdargs(self):
        '''
        Parse command args that might have storm queries as arguments
        '''
        try:
            tree = self.stormcmdparser.parse(self.text)
        except lark.exceptions.LarkError as e:
            raise self._larkToSynExc(e)
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

class CmdStringer(lark.Transformer):

    def valu(self, kids):
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

        return valu.end_pos

    def cmdstring(self, kids):
        return kids[0]

    def alist(self, kids):
        return [k[0] for k in kids].end_pos

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

import lark
import synapse.exc as s_exc

import synapse.lib.ast as s_ast

ruleClassMap = {
    'query': s_ast.Query,
    'liftbytag': s_ast.LiftTag,
    'liftprop': s_ast.LiftProp,
    'liftpropby': s_ast.LiftPropBy,
    'liftformtag': s_ast.LiftFormTag,
    'editpropdel': s_ast.EditPropDel,
    'edittagdel': s_ast.EditTagDel,
    'lifttagtag': s_ast.LiftTagTag,
    'editnodeadd': s_ast.EditNodeAdd,
    'editpropset': s_ast.EditPropSet,
    'edittagadd': s_ast.EditTagAdd,
    'editunivdel': s_ast.EditUnivDel,
    'editunivset': s_ast.EditPropSet,
    'filtoper': s_ast.FiltOper,
    'formpivot_pivottotags': s_ast.PivotToTags,
    'formpivot_pivotout': s_ast.PivotOut,
    'formpivot_': s_ast.FormPivot,
    'formpivotin_': s_ast.PivotIn,
    'formpivotin_pivotinfrom': s_ast.PivotInFrom,
    'formjoinin_pivotinfrom': lambda kids: s_ast.PivotInFrom(kids, isjoin=True),
    'formjoinin_pivotin': lambda kids: s_ast.PivotIn(kids, isjoin=True),
    'formjoin_pivotout': lambda _: s_ast.PivotOut(isjoin=True),
    'formjoin_formpivot': lambda kids: s_ast.FormPivot(kids, isjoin=True),
    'tagpropvalue': s_ast.TagPropValue,
    'valuvar': s_ast.VarSetOper,
    'vareval': s_ast.VarEvalOper,
    'opervarlist': s_ast.VarListSetOper,
    'relpropvalu': s_ast.RelPropValue,
    'forloop': s_ast.ForLoop,
    'condsubq': s_ast.SubqCond
}

terminalClassMap = {
    'PROPNAME': s_ast.Const,
    'CMPR': s_ast.Const,
    'NONQUOTEWORD': s_ast.Const,
    'RELPROP': lambda x: s_ast.RelProp(x[1:]),  # no leading :
    'CMDNAME': s_ast.Const,
    'VARTOKN': s_ast.Const,
    'ABSPROP': s_ast.AbsProp,
    'ABSPROPNOUNIV': s_ast.AbsProp,
    'NONCMDQUOTE': s_ast.Const,
    'FILTPREFIX': s_ast.Const,
    'DOUBLEQUOTEDSTRING': lambda x: s_ast.Const(x[1:-1]),  # no quotes
    'UNIVPROP': s_ast.UnivProp,
    'TAGMATCH': lambda x: s_ast.TagMatch(x[1:]),  # no leading #
    'NOT_': s_ast.Const,
    'BREAK': lambda x: s_ast.BreakOper(),
    'CONTINUE': lambda x: s_ast.ContinueOper(),
}

class TmpVarCall:
    def __init__(self, kids, meta):
        self.kids = kids

    def repr(self):
        return f'{self.__class__.__name__}: {self.kids}'

@lark.v_args(meta=True)
class AstConverter(lark.Transformer):

    def __init__(self, text):
        lark.Transformer.__init__(self)

        # Keep the text for error printing, weird subquery argv parsing
        self.text = text

    def _convert_children(self, children):
        return [self._convert_child(k) for k in children]

    def _convert_child(self, child):
        if not isinstance(child, lark.lexer.Token):
            return child
        if child.type not in terminalClassMap:
            breakpoint()
        tokencls = terminalClassMap[child.type]
        newkid = tokencls(child.value)
        return newkid

    def __default__(self, treedata, children, treemeta):
        if treedata not in ruleClassMap:
            breakpoint()
        cls = ruleClassMap[treedata]
        newkids = self._convert_children(children)
        return cls(newkids)

    def subquery(self, kids, meta):
        assert len(kids) == 1
        kids = self._convert_children(kids)
        ast = s_ast.SubQuery(kids)

        # Keep the text of the subquery in case used by command
        ast.text = self.text[meta.start_pos:meta.end_pos]
        return ast

    def cond(self, kids, meta):
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

        breakpoint()


    def condexpr(self, kids, meta):
        if len(kids) == 1:
            return kids[0]
        assert len(kids) == 3
        operand1, operand2 = kids[0], kids[2]
        oper = kids[1].value

        if oper == 'and':
            return s_ast.AndCond(kids=[operand1, operand2])
        if oper == 'or':
            return s_ast.OrCond(kids=[operand1, operand2])
        breakpoint()

    # def formpivot(self, kids, meta):
    #     kids = self._convert_children(kids)
    #     if len(kids) == 0:
    #         return s_ast.PivotOut()
    #     # more to add
    #     breakpoint()

    def varvalu(self, kids, meta):
        # FIXME really should be restructured; emulating old code for now

        varv = s_ast.VarValue(kids=self._convert_children([kids[0]]))
        for kid in kids[1:]:
            if isinstance(kid, lark.lexer.Token):
                if kid.type == 'VARDEREF':
                    varv = s_ast.VarDeref(kids=[varv, s_ast.Const(kid.value[1:])])
                else:
                    breakpoint()
            elif isinstance (kid, TmpVarCall):
                callkids = self._convert_children(kid.kids)
                args = s_ast.CallArgs(kids=callkids)
                # FIXME: kwargs
                kwargs = s_ast.CallKwargs(kids=[])
                varv = s_ast.FuncCall(kids=[varv, args, kwargs])
            else:
                breakpoint()

        return varv

    def varcall(self, kids, meta):
        # defer the conversion until the parent varvalu
        return TmpVarCall(kids, meta)

    def varlist(self, kids, meta):
        kids = self._convert_children(kids)
        return s_ast.VarList([k.valu for k in kids])

    def operrelprop_pivot(self, kids, meta, isjoin=False):
        kids = self._convert_children(kids)
        relprop, rest = kids[0], kids[1:]
        if not rest:
            return s_ast.PropPivotOut(kids=kids, isjoin=isjoin)
        pval = s_ast.RelPropValue(kids=(relprop,))
        return s_ast.PropPivot(kids=(pval, *kids[1:]), isjoin=isjoin)

    def operrelprop_join(self, kids, meta):
        return self.operrelprop_pivot(kids, meta, isjoin=True)

    def stormcmd(self, kids, meta):
        kids = self._convert_children(kids)

        argv = []

        for kid in kids[1:]:
            if isinstance(kid, s_ast.Const):
                newkid = kid.valu
            elif isinstance(kid, s_ast.SubQuery):
                newkid = kid.text
            argv.append(newkid)

        return s_ast.CmdOper(kids=(kids[0], s_ast.Const(tuple(argv))))

    def tagname(self, kids, meta):
        assert kids and len(kids) == 1
        kid = kids[0]
        if kid.type == 'TAG':
            return s_ast.TagName(kid.value)
        assert kid.type == 'VARTOKN'
        return self.varvalu(kids, meta)

    def valulist(self, kids, meta):
        kids = self._convert_children(kids)
        return s_ast.List(None, kids=kids)

    def univpropvalu(self, kids, meta):
        kids = self._convert_children(kids)
        return s_ast.UnivPropValue(kids=kids)

    def switchcase(self, kids, meta):
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

    def casevalu(self, kids, meta):
        assert len(kids) == 1
        kid = kids[0]

        if kid.type == 'DOUBLEQUOTEDSTRING':
            return self._convert_child(kid)

        return s_ast.Const(kid.value[:-1])  # drop the trailing ':'

class Parser:

    with open('synapse/lib/storm.g') as grammar:
        parser = lark.Lark(grammar, start='query', debug=True, propagate_positions=True)

    def __init__(self, text, offs=0):
        self.offs = offs
        assert text is not None
        self.text = text.strip()
        self.size = len(self.text)

    def query(self):
        try:
            tree = self.parser.parse(self.text)
        except lark.exceptions.LarkError as e:
            raise s_exc.BadSyntax() from e
        newtree = AstConverter(self.text).transform(tree)
        return newtree

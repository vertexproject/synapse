import lark

import synapse.lib.ast as s_ast

optcast = {
    'limit': int,
    'uniq': bool,
    'graph': bool,
}

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
    'VARDEREF': s_ast.VarDeref,
}

class AstConverter(lark.Transformer):

    def _convert_children(self, children):
        kids = []
        for k in children:
            if not isinstance(k, lark.lexer.Token):
                kids.append(k)
                continue
            if k.type not in terminalClassMap:
                breakpoint()
            tokencls = terminalClassMap[k.type]
            newkid = tokencls(k.value)
            kids.append(newkid)
        return kids

    def __default__(self, treedata, children, treemeta):
        if treedata not in ruleClassMap:
            breakpoint()
        cls = ruleClassMap[treedata]
        newkids = self._convert_children(children)
        return cls(newkids)

    def cmdargv(self, kids):
        kids = self._convert_children(kids)
        return kids[0].value()

    def cond(self, kids):
        kids = self._convert_children(kids)
        first, cmprvalu = kids[0], kids[1:]

        if isinstance(first, s_ast.RelProp):
            prop = s_ast.RelPropValue(kids=(first, ))
            return s_ast.RelPropCond(kids=(prop, ) + tuple(cmprvalu))

        elif isinstance(first, s_ast.TagName):
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

        breakpoint()

    # def formpivot(self, kids):
    #     kids = self._convert_children(kids)
    #     if len(kids) == 0:
    #         return s_ast.PivotOut()
    #     # more to add
    #     breakpoint()

    def varvalu(self, kids):
        kids = self._convert_children(kids)
        for kid in kids[1:]:
            breakpoint()
        varv = s_ast.VarValue(kids=[kids[0]])
        return varv

    def varcall(self, kids):
        assert len(kids) == 1
        kids = self._convert_children(kids)
        return s_ast.FuncCall(kids=kids)

    def operrelprop_pivot(self, kids):
        kids = self._convert_children(kids)
        relprop, rest = kids[0], kids[1:]
        if not rest:
            return s_ast.PropPivotOut(kids=kids)
        breakpoint()
        pval = s_ast.RelPropValue(kids=(relprop,))
        return s_ast.PropPivot(kids=(pval, *kids))

    def stormcmd(self, kids):
        kids = self._convert_children(kids)
        assert kids
        argv = s_ast.Const(tuple(kids[1:]))
        return s_ast.CmdOper(kids=(kids[0], argv))

    def tagname(self, kids):
        assert kids and len(kids) == 1
        kid = kids[0]
        if kid.type == 'TAG':
            return s_ast.TagName(kid.value)
        assert kid.type == 'VARTOKN'
        return self.varvalu(kids)

    def queryoption(self, kids):
        opt = kids[0].value
        valu = kids[1].value

        cast = optcast.get(opt)
        if cast is None:
            raise s_exc.NoSuchOpt(name=opt)

        try:
            valu = cast(valu)
        except Exception:
            raise s_exc.BadOptValu(name=opt, valu=valu)

        # FIXME:  need to plumb in some generic context or make a node for this
        # query.opts[name] = valu
        raise lark.Discard

    def valulist(self, kids):
        kids = self._convert_children(kids)
        assert kids
        return s_ast.List(None, kids=kids)

class Parser:
    def __init__(self, parseinfo, text, offs=0):
        self.offs = offs
        assert text is not None
        self.text = text.strip()
        self.size = len(self.text)

        self.stormcmds = set(parseinfo['stormcmds'])
        self.modelinfo = parseinfo['modelinfo']

        # FIXME:  insert propnames, stormcmds into grammar
        grammar = open('synapse/lib/storm.g').read()

        # FIXME:  memoize this
        self.parser = lark.Lark(grammar, start='query')

    def query(self):
        tree = self.parser.parse(self.text)
        newtree = AstConverter().transform(tree)
        return newtree

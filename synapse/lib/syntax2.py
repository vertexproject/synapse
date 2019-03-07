import lark

import synapse.lib.ast as s_ast

ruleClassMap = {
    'query': s_ast.Query,
    'liftbytag': s_ast.LiftTag,
    'liftprop': s_ast.LiftProp,
    'liftpropby': s_ast.LiftPropBy,
    'liftformtag': s_ast.LiftFormTag,
    'edittagdel': s_ast.EditTagDel,
    'lifttagtag': s_ast.LiftTagTag,
    'editnodeadd': s_ast.EditNodeAdd,
    'editunivdel': s_ast.EditUnivDel,
    'filtoper': s_ast.FiltOper,
}

terminalClassMap = {
    'PROPNAME': s_ast.Const,
    'CMPR': s_ast.Const,
    'NONQUOTEWORD': s_ast.Const,
    'RELPROP': lambda x: s_ast.RelProp(x[1:]),  # no leading :
    'CMDNAME': s_ast.Const,
    'VARTOKN': s_ast.Const,
    'ABSPROP': s_ast.AbsProp,
    'NONCMDQUOTE': s_ast.Const,
    'FILTPREFIX': s_ast.Const,
    'DOUBLEQUOTEDSTRING': lambda x: s_ast.Const(x[1:-1]),  # no quotes
    'UNIVPROP': s_ast.UnivProp,
}

class AstConverter(lark.Transformer):

    def _convert_children(self, children):
        kids = []
        for k in children:
            # if k is None:
            #     continue
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
        return cls(kids=newkids)

    def cmdargv(self, kids):
        kids = self._convert_children(kids)
        return kids[0].value()

    def cond(self, kids):
        kids = self._convert_children(kids)
        if isinstance(kids[0], s_ast.RelProp):
            prop = s_ast.RelPropValue(kids=(kids[0], ))
            return s_ast.RelPropCond(kids=(prop, ) + tuple(kids[1:]))
        breakpoint()

    def formpivot(self, kids):
        kids = self._convert_children(kids)
        if len(kids) == 0:
            return s_ast.PivotOut()
        # more to add

    def varvalu(self, kids):
        kids = self._convert_children(kids)
        for kid in kids[1:]:
            breakpoint()
        varv = s_ast.VarValue(kids=[kids[0]])
        return varv

    def operrelprop(self, kids):
        kids = self._convert_children(kids)
        # FIXME
        breakpoint()

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

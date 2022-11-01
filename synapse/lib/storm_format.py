import lark  # type: ignore

import pygments.lexer   # type: ignore
import pygments.token as p_t  # type: ignore

TerminalPygMap = {
    'ABSPROP': p_t.Name,
    'ABSPROPNOUNIV': p_t.Name,
    'ALLTAGS': p_t.Operator,
    'AND': p_t.Keyword,
    'BACKQUOTE': p_t.Punctuation,
    'BASEPROP': p_t.Name,
    'BOOL': p_t.Keyword,
    'BREAK': p_t.Keyword,
    'BYNAME': p_t.Operator,
    'CASEBARE': p_t.Literal.String,
    'CCOMMENT': p_t.Comment,
    'CMDOPT': p_t.Literal.String,
    'CMDNAME': p_t.Keyword,
    'CMDRTOKN': p_t.Literal.String,
    'CMPR': p_t.Operator,
    'CMPROTHER': p_t.Operator,
    'COLON': p_t.Punctuation,
    'COMMA': p_t.Punctuation,
    'COMMASPACE': p_t.Punctuation,
    'COMMANOSPACE': p_t.Punctuation,
    'CONTINUE': p_t.Keyword,
    'CPPCOMMENT': p_t.Comment,
    'DEFAULTCASE': p_t.Keyword,
    'DOLLAR': p_t.Punctuation,
    'DOT': p_t.Punctuation,
    'DOUBLEQUOTEDSTRING': p_t.Literal.String,
    'ELIF': p_t.Keyword,
    'EQNOSPACE': p_t.Punctuation,
    'EQSPACE': p_t.Punctuation,
    'EQUAL': p_t.Punctuation,
    'EXPRDIVIDE': p_t.Operator,
    'EXPRMINUS': p_t.Operator,
    'EXPRNEG': p_t.Operator,
    'EXPRPLUS': p_t.Operator,
    'EXPRPOW': p_t.Operator,
    'EXPRTIMES': p_t.Operator,
    'FOR': p_t.Keyword,
    'FORMATSTRING': p_t.Literal.String,
    'FORMATTEXT': p_t.Literal.String,
    'FUNCTION': p_t.Keyword,
    'HASH': p_t.Punctuation,
    'HEXNUMBER': p_t.Literal.Number,
    'IF': p_t.Keyword,
    'IN': p_t.Keyword,
    'LBRACE': p_t.Punctuation,
    'LISTTOKN': p_t.Literal.String,
    'LPAR': p_t.Punctuation,
    'LSQB': p_t.Punctuation,
    'MODSET': p_t.Operator,
    'NONQUOTEWORD': p_t.Literal,
    'NOT': p_t.Keyword,
    'NUMBER': p_t.Literal.Number,
    'OR': p_t.Keyword,
    'PROPS': p_t.Name,
    'RBRACE': p_t.Punctuation,
    'RELNAME': p_t.Name,
    'EXPRRELNAME': p_t.Name,
    'RPAR': p_t.Punctuation,
    'RSQB': p_t.Punctuation,
    'RSQBNOSPACE': p_t.Punctuation,
    'SETTAGOPER': p_t.Operator,
    'SINGLEQUOTEDSTRING': p_t.Literal.String,
    'SWITCH': p_t.Keyword,
    'TAGMATCH': p_t.Name,
    'TRIPLEQUOTEDSTRING': p_t.Literal.String,
    'TRYSET': p_t.Operator,
    'TRYSETMINUS': p_t.Operator,
    'TRYSETPLUS': p_t.Operator,
    'UNIVNAME': p_t.Name,
    'EXPRUNIVNAME': p_t.Name,
    'VARTOKN': p_t.Name.Variable,
    'EXPRVARTOKN': p_t.Name.Variable,
    'VBAR': p_t.Punctuation,
    'WHILE': p_t.Keyword,
    'WHITETOKN': p_t.Literal.String,
    'WILDCARD': p_t.Name,
    'YIELD': p_t.Keyword,
    '_ARRAYCONDSTART': p_t.Punctuation,
    '_COLONDOLLAR': p_t.Punctuation,
    '_DEREF': p_t.Punctuation,
    '_EDGEADDN1FINI': p_t.Punctuation,
    '_EDGEADDN2FINI': p_t.Punctuation,
    '_EDGEN1FINI': p_t.Punctuation,
    '_EDGEN1INIT': p_t.Punctuation,
    '_EDGEN2INIT': p_t.Punctuation,
    '_EDGEN2FINI': p_t.Punctuation,
    '_ELSE': p_t.Keyword,
    '_EMBEDQUERYSTART': p_t.Punctuation,
    '_EMIT': p_t.Keyword,
    '_FINI': p_t.Keyword,
    '_HASH': p_t.Punctuation,
    '_EXPRHASH': p_t.Punctuation,
    '_HASHSPACE': p_t.Punctuation,
    '_EXPRHASHSPACE': p_t.Punctuation,
    '_INIT': p_t.Keyword,
    '_LEFTJOIN': p_t.Punctuation,
    '_LEFTPIVOT': p_t.Punctuation,
    '_LPARNOSPACE': p_t.Punctuation,
    '_RETURN': p_t.Keyword,
    '_RIGHTJOIN': p_t.Punctuation,
    '_RIGHTPIVOT': p_t.Punctuation,
    '_STOP': p_t.Keyword,
    '_TAGSEGNOVAR': p_t.Name,
    '_WALKNPIVON1': p_t.Punctuation,
    '_WALKNPIVON2': p_t.Punctuation,
    '$END': p_t.Punctuation,
}

class StormLexer(pygments.lexer.Lexer):
    def __init__(self, parser):
        super().__init__()
        self.parser = parser

    def _yield_tree(self, tree):
        for node in tree.children:
            if isinstance(node, lark.Tree):
                yield from self._yield_tree(node)
            else:
                yield node

    def get_tokens_unprocessed(self, text):
        tree = self.parser.parse(text, start='query')
        for ltoken in self._yield_tree(tree):
            typ = TerminalPygMap[ltoken.type]
            yield ltoken.start_pos, typ, ltoken.value

def highlight_storm(parser, text):  # pragma: no cover
    '''
    Prints a storm query with syntax highlighting
    '''
    from pygments import highlight
    from pygments.formatters import Terminal256Formatter  # type: ignore

    print(highlight(text, StormLexer(parser), Terminal256Formatter()), end='')

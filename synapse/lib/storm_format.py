import lark  # type: ignore

import pygments.lexer   # type: ignore
import pygments.token as p_t  # type: ignore

TerminalPygMap = {
    'ABSPROP': p_t.Name,
    'ABSPROPNOUNIV': p_t.Name,
    'ALLTAGS': p_t.Operator,
    'AND': p_t.Keyword,
    'BREAK': p_t.Keyword,
    'BASEPROP': p_t.Name,
    'BYNAME': p_t.Operator,
    'CASEBARE': p_t.Literal.String,
    'CCOMMENT': p_t.Comment,
    'CMDNAME': p_t.Keyword,
    'CMPR': p_t.Operator,
    'COLON': p_t.Punctuation,
    'COMMA': p_t.Punctuation,
    'CONTINUE': p_t.Keyword,
    'CPPCOMMENT': p_t.Comment,
    'DEFAULTCASE': p_t.Keyword,
    'DEREFMATCHNOSEP': p_t.Name,
    'DOLLAR': p_t.Punctuation,
    'DOT': p_t.Punctuation,
    'DOUBLEQUOTEDSTRING': p_t.Literal.String,
    'ELIF': p_t.Keyword,
    'ELSE': p_t.Keyword,
    'EQUAL': p_t.Punctuation,
    'EXPRCMPR': p_t.Operator,
    'EXPRDIVIDE': p_t.Operator,
    'EXPRMINUS': p_t.Operator,
    'EXPRPLUS': p_t.Operator,
    'EXPRTIMES': p_t.Operator,
    'FILTPREFIX': p_t.Operator,
    'FOR': p_t.Keyword,
    'FUNCTION': p_t.Keyword,
    'IF': p_t.Keyword,
    'IN': p_t.Keyword,
    'LBRACE': p_t.Punctuation,
    'LPAR': p_t.Punctuation,
    'LSQB': p_t.Punctuation,
    'NONCMDQUOTE': p_t.Literal,
    'NONQUOTEWORD': p_t.Literal,
    'NOT': p_t.Keyword,
    'NUMBER': p_t.Literal.Number,
    'OR': p_t.Keyword,
    'PROPNAME': p_t.Name,
    'PROPS': p_t.Name,
    'RBRACE': p_t.Punctuation,
    'RELNAME': p_t.Name,
    '_RETURN': p_t.Keyword,
    'RPAR': p_t.Punctuation,
    'RSQB': p_t.Punctuation,
    'SETOPER': p_t.Operator,
    'SINGLEQUOTEDSTRING': p_t.Literal.String,
    'SWITCH': p_t.Keyword,
    'TAG': p_t.Name,
    'TAGMATCH': p_t.Name,
    'UNIVNAME': p_t.Name,
    'UNIVPROP': p_t.Name,
    'VARTOKN': p_t.Name.Variable,
    'VBAR': p_t.Punctuation,
    'WHILE': p_t.Keyword,
    'YIELD': p_t.Keyword,
    '_EXPRSTART': p_t.Punctuation,
    '_DEREF': p_t.Punctuation,
    '_LEFTJOIN': p_t.Punctuation,
    '_LEFTPIVOT': p_t.Punctuation,
    '_ONLYTAGPROP': p_t.Name,
    '_RIGHTJOIN': p_t.Punctuation,
    '_RIGHTPIVOT': p_t.Punctuation,
    '_WS': p_t.Whitespace,
    '_WSCOMM': p_t.Whitespace,
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
        tree = self.parser.parse(text)
        for ltoken in self._yield_tree(tree):
            typ = TerminalPygMap[ltoken.type]
            yield ltoken.pos_in_stream, typ, ltoken.value

def highlight_storm(parser, text):  # pragma: no cover
    '''
    Prints a storm query with syntax highlighting
    '''
    from pygments import highlight
    from pygments.formatters import Terminal256Formatter  # type: ignore

    print(highlight(text, StormLexer(parser), Terminal256Formatter()), end='')

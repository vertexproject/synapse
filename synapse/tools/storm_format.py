# pragma: no cover

import lark  # type: ignore

import pygments.lexer   # type: ignore
import pygments.token as p_t  # type: ignore

TerminalPygMap = {
    'ABSPROP': p_t.Name,
    'ABSPROPNOUNIV': p_t.Name,
    'AND_': p_t.Operator.Word,
    'BREAK': p_t.Keyword,
    'CCOMMENT': p_t.Comment,
    'CMDNAME': p_t.Keyword,
    'CMPR': p_t.Operator,
    'CONTINUE': p_t.Keyword,
    'CPPCOMMENT': p_t.Comment,
    'DOUBLEQUOTEDSTRING': p_t.Literal.String,
    'FILTPREFIX': p_t.Operator,
    'HASH': p_t.Punctuation,
    'LSQB': p_t.Punctuation,
    'MINUS': p_t.Punctuation,
    'NONCMDQUOTE': p_t.Literal,
    'NONQUOTEWORD': p_t.Literal,
    'NOT_': p_t.Operator.Word,
    'OR_': p_t.Operator.Word,
    'PROPNAME': p_t.Name,
    'PROPS': p_t.Name,
    'RELPROP': p_t.Name,
    'RSQB': p_t.Punctuation,
    'TAG': p_t.Name,
    'TAGMATCH': p_t.Name,
    'UNIVNAME': p_t.Name,
    'UNIVPROP': p_t.Name,
    'VARCHARS': p_t.Name.Variable,
    'VARDEREF': p_t.Name.Variable,
    'VARSETS': p_t.Name.Variable,
    'VARTOKN': p_t.Name.Variable,
    '_WS': p_t.Whitespace,
    '_WSCOMM': p_t.Whitespace
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
            typ = TerminalPygMap.get(ltoken.type, p_t.Text)
            yield ltoken.pos_in_stream, typ, ltoken.value

def highlight_storm(parser, text):
    from pygments import highlight
    from pygments.formatters import Terminal256Formatter  # type: ignore

    print(highlight(text, StormLexer(parser), Terminal256Formatter()), end='')

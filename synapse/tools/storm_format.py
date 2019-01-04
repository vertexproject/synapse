import lark

import pygments.lexer
import pygments.token as p_t

TerminalPygMap = {
    'HASH': p_t.Punctuation,
    'MINUS': p_t.Punctuation,
    'LSQB': p_t.Punctuation,
    'RSQB': p_t.Punctuation,
    'TAG': p_t.Name,
    '_WSCOMM': p_t.Comment,
    '_WS': p_t.Comment,
    'PROPNAME': p_t.Name,
    'CMPR': p_t.Operator,
    'NONQUOTEWORD': p_t.Literal,
    'VARTOKN': p_t.Name
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
            # yield ltoken.pos_in_stream, typ, f'({typ}:{ltoken.type}:{ltoken.value})'
            yield ltoken.pos_in_stream, typ, ltoken.value

def highlight_storm(parser, text):
    from pygments import highlight
    from pygments.formatters import Terminal256Formatter

    print(highlight(text, StormLexer(parser), Terminal256Formatter()), end='')

def tst_highlight_storm():
    from synapse.tests.test_grammar import _Queries

    grammar = open('synapse/lib/storm.g').read()

    parser = lark.Lark(grammar, start='query', keep_all_tokens=True)

    for i, query in enumerate(_Queries):
        if i == 0:
            continue
        if i > 25:
            break
        highlight_storm(parser, query)

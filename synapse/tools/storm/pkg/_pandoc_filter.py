import sys
import json

import packaging.version as p_version
import packaging.specifiers as p_specifiers

PANDOC_API_REQVERS = '>=1.23.0,<1.24.0'

def walk(elem):
    '''
    Walk the pandoc AST, yielding (type, content) tuples.
    Ref: https://pandoc.org/using-the-pandoc-api.html#walking-the-ast
    '''

    if isinstance(elem, list):
        for subelem in elem:
            yield from walk(subelem)
        return

    if isinstance(elem, dict):
        if 't' in elem:
            yield elem['t'], elem.get('c')
        for v in elem.values():
            yield from walk(v)
        return


def _inlines_to_md(inlines):
    '''
    Render a list of pandoc Inline AST nodes back to markdown source text. Only
    the inline kinds that show up inside RST table cells in our docs are
    handled; anything unexpected falls back to its ``Str``-equivalent text so
    the cell still renders something sensible.
    '''
    out = []
    for node in inlines or ():
        t = node.get('t')
        c = node.get('c')

        if t == 'Str':
            out.append(c)
        elif t in ('Space', 'SoftBreak'):
            out.append(' ')
        elif t == 'LineBreak':
            out.append(' ')
        elif t == 'Code':
            # c is [(id, classes, kvs), text]
            out.append(f'`{c[1]}`')
        elif t == 'Strong':
            out.append('**' + _inlines_to_md(c) + '**')
        elif t == 'Emph':
            out.append('*' + _inlines_to_md(c) + '*')
        elif t == 'Link':
            # c is [(id, classes, kvs), inlines, (url, title)]
            text = _inlines_to_md(c[1])
            url = c[2][0]
            out.append(f'[{text}]({url})')
        elif t == 'RawInline':
            # c is [format, text] -- pass markdown through verbatim
            fmt, text = c
            if fmt in ('markdown', 'html'):
                out.append(text)
        elif t == 'Quoted':
            # c is [QuoteType, inlines]
            qt = c[0].get('t') if isinstance(c[0], dict) else c[0]
            quote = "'" if qt == 'SingleQuote' else '"'
            out.append(quote + _inlines_to_md(c[1]) + quote)
        elif t == 'Span':
            # c is [(id, classes, kvs), inlines] -- pass content through
            out.append(_inlines_to_md(c[1]))
        else:
            # Best-effort fallback: try to render any nested inlines.
            if isinstance(c, list):
                out.append(_inlines_to_md(c))

    return ''.join(out)


def _cell_to_md(cell):
    '''
    Render a pandoc table Cell (``[attrs, align, rowSpan, colSpan, blocks]``)
    to a single line of markdown source suitable for inclusion inside a pipe
    table cell. Pipes inside the rendered content are escaped so the cell does
    not appear to span columns.
    '''
    blocks = cell[4] if len(cell) >= 5 else []
    parts = []

    def render_block(block):
        if not isinstance(block, dict):
            return ''

        t = block.get('t')
        c = block.get('c')
        if t in ('Plain', 'Para'):
            return _inlines_to_md(c)

        if t == 'LineBlock':
            return ' '.join(_inlines_to_md(line) for line in c or ())

        # Container blocks (BlockQuote, Div, list items, ...) hold inner
        # blocks. Recurse so cells that pandoc wrapped in a BlockQuote
        # render their inline content rather than crashing the inline
        # walker on a list of blocks.
        if t == 'BlockQuote':
            return ' '.join(render_block(b) for b in c or ())

        if t == 'Div':
            inner = c[1] if isinstance(c, list) and len(c) >= 2 else []
            return ' '.join(render_block(b) for b in inner)

        return ''

    for block in blocks:
        rendered = render_block(block)
        if rendered:
            parts.append(rendered)

    text = ' '.join(p for p in parts if p)
    text = text.replace('\n', ' ').strip()
    out = []
    prev = ''
    for ch in text:
        if ch == '|' and prev != '\\':
            out.append('\\|')
        else:
            out.append(ch)
        prev = ch

    return ''.join(out)


def _table_to_pipe_md(table_content):
    '''
    Convert a pandoc Table node's ``c`` payload into a tightly-formatted
    markdown pipe table. Returns the markdown source as a string. Tables that
    span multiple body sections are flattened into a single body.
    '''
    # Table c layout: [attrs, caption, colspecs, head, bodies, foot]
    _attrs, _caption, colspecs, head, bodies, _foot = table_content

    def rows_of(section_rows):
        # Each row is [attrs, [cells]]; cells are the 5-tuple Cell nodes.
        out = []
        for row in section_rows or ():
            cells = row[1] if len(row) >= 2 else []
            out.append([_cell_to_md(cell) for cell in cells])

        return out

    head_rows = rows_of(head[1] if head and len(head) >= 2 else [])

    body_rows = []
    for body in bodies or ():
        # Body layout: [attrs, rowHeadColumns, intermediate_head_rows, body_rows]
        if len(body) >= 4:
            body_rows.extend(rows_of(body[2]))
            body_rows.extend(rows_of(body[3]))

    if head_rows:
        header = head_rows[0]
    elif body_rows:
        header = body_rows.pop(0)
    else:
        header = ['' for _ in colspecs or ()]

    ncols = max(len(header), max((len(r) for r in body_rows), default=0))
    header = header + [''] * (ncols - len(header))

    lines = ['| ' + ' | '.join(header) + ' |']
    lines.append('|' + '|'.join('---' for _ in range(ncols)) + '|')
    for row in body_rows:
        row = row + [''] * (ncols - len(row))
        lines.append('| ' + ' | '.join(row) + ' |')

    return '\n'.join(lines)


def _rewrite_tables(blocks):
    '''
    Walk a list of top-level blocks in place, replacing Table nodes with a
    RawBlock ``markdown`` containing a tight pipe-table rendering. Recurses
    into block containers (Div, BlockQuote, list items, etc.) so nested tables
    are picked up too.
    '''
    for i, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue

        t = block.get('t')
        if t == 'Table':
            md = _table_to_pipe_md(block['c'])
            blocks[i] = {'t': 'RawBlock', 'c': ['markdown', md]}
            continue

        c = block.get('c')
        if t in ('Div', 'BlockQuote'):
            # c is [attrs, blocks] for Div, [blocks] for BlockQuote.
            inner = c[1] if t == 'Div' else c
            _rewrite_tables(inner)
        elif t in ('OrderedList', 'BulletList'):
            # OrderedList: [listAttributes, [[blocks], ...]]
            # BulletList:  [[[blocks], ...]]
            items = c[1] if t == 'OrderedList' else c
            for item in items or ():
                _rewrite_tables(item)
        elif t == 'DefinitionList':
            for term, defs in c or ():
                for def_ in defs or ():
                    _rewrite_tables(def_)


def main():
    '''
    A pandoc filter reads the intermediate JSON-formatted AST generated from the source, makes any modifications,
    and then writes the JSON-formatted AST to be used to generate the target.

    Ref: https://pandoc.org/filters.html

    Usage:

       pandoc -f rst -t markdown --filter ./synapse/tools/storm/pkg/_pandoc_filter.py -o foo.md foo.rst
    '''

    ast = json.load(sys.stdin)

    spec = p_specifiers.SpecifierSet(PANDOC_API_REQVERS)
    vers = p_version.Version('.'.join(str(part) for part in ast['pandoc-api-version']))
    if vers not in spec:
        raise Exception(f'Pandoc API version {vers} does not match required version {PANDOC_API_REQVERS}')

    for type_, content in walk(ast['blocks']):

        if type_ != 'DefinitionList':
            continue

        # An RST term with multiple definitions gets combined into one -> split
        # ( Only Para types should get split )
        for term, defs in content:

            newdefs = []
            newdef = []

            for def_ in defs[0]:

                if def_['t'] == 'Para' and newdef:
                    # we are on a new paragraph so save the
                    # previous term/def group
                    newdefs.append(newdef.copy())
                    newdef.clear()

                newdef.append(def_)

            if newdef:
                newdefs.append(newdef.copy())

            defs.clear()
            defs.extend(newdefs)

    # Replace every Table with a RawBlock holding a tight pipe-table
    # rendering. Pandoc's markdown writer otherwise emits multiline / simple /
    # grid tables that downstream consumers (e.g. Optic) cannot parse.
    _rewrite_tables(ast['blocks'])

    sys.stdout.write(json.dumps(ast))

    return 0

if __name__ == '__main__':
    sys.exit(main())

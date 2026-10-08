import math
import regex
import decimal
import mistletoe

from mistletoe import block_token
from mistletoe.markdown_renderer import MarkdownRenderer

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.config as s_config

# A pandoc fenced div: `::: {.class key="value"}` ... `:::`. Only the braced opening form is
# recognized; a bare `::: classname` is left as ordinary markdown.
FENCE_OPEN = regex.compile(r'^::: *\{(.*)\}\s*$')
FENCE_CLOSE = regex.compile(r'^:::\s*$')

# A code fence line, as CommonMark reads one: three or more backticks or tildes, indented at most
# three spaces. A backtick fence's info string may not hold a backtick.
CODE_FENCE_LINE = regex.compile(r'^ {0,3}(`{3,}|~{3,})(.*?)\s*$')

# A `.class` in a pandoc attribute string. The leading token boundary keeps a dot inside an
# attribute value (`src="foo.png"`) from reading as a class.
ATTR_CLASS = regex.compile(r'(?:^|\s)\.([\w-]+)')
# One token of an opening fence's attribute list: a `key=value` pair (whose value may be quoted, and
# so may contain spaces) or any other non-whitespace run. Splitting on whitespace alone would break a
# quoted value in half.
ATTR_TOKEN = regex.compile(r'[\w-]+=(?:"(?:[^"\\]|\\.)*"|\S+)|\S+')
ATTR_PAIR = regex.compile(r'([\w-]+)=(?:"((?:[^"\\]|\\.)*)"|(\S+))')

HEADING_TEXT = regex.compile(r'^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$')
CODE_FENCE = regex.compile(r'^(`{3,}|~{3,})[ \t]*(\S*)[ \t]*\n(.*?)\n?\1[ \t]*$', regex.DOTALL)
LIST_ITEM = regex.compile(r'^[ \t]*(?:[-*+]|\d+[.)])[ \t]+(.*)$')

class FencedDiv(block_token.BlockToken):
    '''
    A pandoc fenced div. A container: its children are the block tokens between the fences.

    The attribute text is captured as `info` and given no meaning here.
    '''
    def __init__(self, result):
        self.info, lines = result
        self.children = block_token.tokenize(lines)

    @classmethod
    def start(cls, line):
        return FENCE_OPEN.match(line) is not None

    @classmethod
    def read(cls, lines):
        match = FENCE_OPEN.match(next(lines))

        # A bare `:::` closes the innermost open div, so without the depth count a nested div's own
        # close ended this one and the outer close came back out as a stray paragraph.
        #
        # Nothing inside a code fence is a fence line: a code block showing markdown is content, and
        # counting its `:::` lines ended the div there, taking the blocks after it in as content.
        depth = 1
        inner = []
        code = None
        for line in lines:

            if code is not None:
                if isCodeFenceClose(line, code):
                    code = None

            elif (code := codeFenceOpen(line)) is not None:
                pass

            elif FENCE_OPEN.match(line):
                depth += 1

            elif FENCE_CLOSE.match(line):
                depth -= 1
                if depth == 0:
                    break

            inner.append(line)

        return (match.group(1), inner)

def codeFenceOpen(line):
    '''
    The fence a line opens a code block with (its run of backticks or tildes), or None.
    '''
    match = CODE_FENCE_LINE.match(line)
    if match is None:
        return None

    fence, info = match.groups()
    if fence[0] == '`' and '`' in info:
        return None

    return fence

def isCodeFenceClose(line, fence):
    '''
    Whether a line closes the code block `fence` opened: the same character, at least as many, and
    nothing after.
    '''
    match = CODE_FENCE_LINE.match(line)
    if match is None or match.group(2):
        return False

    close = match.group(1)
    return close[0] == fence[0] and len(close) >= len(fence)

class MdRenderer(MarkdownRenderer):
    '''
    Registers FencedDiv for parsing.

    Only ever used as a parsing context: this module never renders a document from an AST, since a
    re-render would reformat blocks the caller did not touch (mistletoe normalises GFM tables).
    '''
    def __init__(self, *extras, **kwargs):
        MarkdownRenderer.__init__(self, FencedDiv, *extras, **kwargs)

    # Required for `FencedDiv` to register as a token type, which is the only reason this renderer
    # exists. Never called: a block is written back from its own source.
    def render_fenced_div(self, token, max_line_length):  # pragma: no cover
        yield f'::: {{{token.info}}}'
        yield from self.blocks_to_lines(token.children, max_line_length=max_line_length)
        yield ':::'

def _typename(tok):
    return type(tok).__name__.lower().replace('_', '')

def _spans(toks, total):
    '''
    [(tok, start, end)] source line spans, 0-based and end-exclusive.

    mistletoe gives a 1-based line_number for where a token starts; the end is where the next sibling
    starts, or total for the last one.
    '''
    out = []
    for indx, tok in enumerate(toks):

        start = tok.line_number - 1
        if indx + 1 < len(toks):
            end = toks[indx + 1].line_number - 1
        else:
            end = total

        out.append((tok, start, end))

    return out

class Block:
    '''
    One top-level piece of a markdown document, which owns its source.

    `text` is the authoritative value: every richer accessor a subclass adds reads it and writes it
    back, so a block nothing touched comes back out byte for byte.

    `tail` is the whitespace that followed the block in the source. `inner` says that `tail` was a
    separator between blocks rather than the end of the document: the two are otherwise
    indistinguishable, and `joinBlocks` has to tell them apart. False for a block a caller built.
    '''
    kind = 'block'

    def __init__(self, text, tail='', inner=False):
        self.text = text
        self.tail = tail
        self.inner = inner

    def __repr__(self):
        return f'{self.__class__.__name__}({self.text!r})'

class Heading(Block):
    kind = 'heading'

    def getLevel(self):
        match = HEADING_TEXT.match(self.text)
        if match is None:
            return None

        return len(match.group(1))

    def getValu(self):
        match = HEADING_TEXT.match(self.text)
        if match is None:
            return None

        return match.group(2)

    def setLevel(self, level):
        if level < 1 or level > 6:
            mesg = f'markdown heading level must be 1-6, got {level}'
            raise s_exc.BadArg(mesg=mesg, level=level)

        self._setParts(level, self.getValu())

    def setValu(self, valu):
        self._setParts(self.getLevel(), valu)

    def _setParts(self, level, valu):
        # A setext heading (`Title` over `=====`) has no `#` run to rewrite in place.
        if level is None or valu is None:
            mesg = 'this heading is not an atx heading (## style); set its text instead'
            raise s_exc.BadArg(mesg=mesg, text=self.text)

        self.text = f'{"#" * level} {valu}'

class Paragraph(Block):
    kind = 'paragraph'

    def getValu(self):
        return self.text

    def setValu(self, valu):
        self.text = fmtParagraph(valu)

class Code(Block):
    kind = 'code'

    def _parts(self):
        match = CODE_FENCE.match(self.text)
        if match is None:
            return None, None

        return match.group(2), match.group(3)

    def getLang(self):
        return self._parts()[0]

    def getValu(self):
        return self._parts()[1]

    def setLang(self, lang):
        self._setParts(lang, self.getValu())

    def setValu(self, valu):
        self._setParts(self.getLang(), valu)

    def _setParts(self, lang, valu):
        if valu is None:
            mesg = 'this code block is indented rather than fenced; set its text instead'
            raise s_exc.BadArg(mesg=mesg, text=self.text)

        self.text = fmtCode(valu, lang or '')

class List(Block):
    kind = 'list'

    def getOrdered(self):
        return regex.match(r'^[ \t]*\d+[.)][ \t]', self.text) is not None

    def getItems(self):
        out = []
        for line in self.text.split('\n'):
            match = LIST_ITEM.match(line)
            if match is not None:
                out.append(match.group(1))

        return out

    def isFlat(self):
        '''
        Whether every line of this list is a top level item.

        A nested item or a lazy continuation line cannot be recovered from the flat list `getItems`
        returns, so rebuilding from one would drop it.
        '''
        for line in self.text.split('\n'):

            if not line.strip():
                continue

            match = LIST_ITEM.match(line)
            if match is None or line[:len(line) - len(line.lstrip())] != '':
                return False

        return True

    def _reqFlat(self):
        if not self.isFlat():
            mesg = 'this list has nested items or continuation lines; set its text instead'
            raise s_exc.BadArg(mesg=mesg, text=self.text)

    def setItems(self, items):
        self._reqFlat()
        self.text = fmtList(items, self.getOrdered())

    def setOrdered(self, ordered):
        self._reqFlat()
        self.text = fmtList(self.getItems(), ordered)

class Table(Block):
    '''
    A GFM pipe table.

    Rows are appended as text rather than rendered from a row model, so adding one leaves every
    existing row exactly as it was.
    '''
    kind = 'table'

    def __init__(self, text, tail='', coldefs=None):
        Block.__init__(self, text, tail=tail)
        self._coldefs = coldefs

    def setText(self, text):
        '''
        Replace the whole table. The columns a constructor was given describe the text it built.
        '''
        self.text = text
        self._coldefs = None

    def getColumns(self):
        if self._coldefs is not None:
            return list(self._coldefs)

        # parsed: recover the names from the header row and the justification from the delimiter row
        lines = self.text.split('\n')
        if len(lines) < 2:
            return []

        names = _tableCells(lines[0])
        justs = [_justifyOf(cell) for cell in _tableCells(lines[1])]

        out = []
        for indx, name in enumerate(names):
            cdef = {'name': name}
            if indx < len(justs) and justs[indx] is not None:
                cdef['justify'] = justs[indx]

            out.append(cdef)

        return out

    def getRows(self):
        '''
        The rows as they are written, each a list of cell values.

        The header and the delimiter row are not rows: a table's columns are `getColumns()`. A cell
        is handed back as its markdown, escapes and all.
        '''
        return [_tableCells(line) for line in self.text.split('\n')[2:] if line.strip()]

    def addRow(self, cells):
        coldefs = self.getColumns()
        if len(cells) != len(coldefs):
            mesg = f'markdown table has {len(coldefs)} columns, got a row of {len(cells)}'
            raise s_exc.BadArg(mesg=mesg, columns=len(coldefs), cells=len(cells))

        self.text = f'{self.text}\n{fmtRow(cells, coldefs)}'

    def sortRows(self, indx, reverse=False):
        '''
        Reorder the rows by one column, in place.

        The header and delimiter rows stay where they are and each row moves whole, so a sort never
        rewrites a cell.

        Rows order by cell text, except a column where every filled cell reads as a number, which
        orders numerically -- inferred from the cells, since markdown has nowhere to write a column
        type. An empty cell is the smallest value, and a row too short to have the cell counts as
        empty.
        '''
        lines = self.text.split('\n')
        head, rows = lines[:2], [line for line in lines[2:] if line.strip()]

        def cellvalu(line):
            cells = _tableCells(line)
            return cells[indx] if indx < len(cells) else ''

        cells = [cellvalu(line) for line in rows]
        filled = [cell for cell in cells if cell != '']

        numeric = bool(filled) and all(NUMERIC_CELL.match(cell) for cell in filled)

        def sortkey(item):
            cell = item[0]

            # Ranked ahead of every value rather than compared against them, so an empty cell never
            # compares a str against a number.
            if cell == '':
                rank, valu = 0, ''
            else:
                rank, valu = 1, decimal.Decimal(cell) if numeric else cell

            # The row position breaks a tie and reverses with everything else, so two rows the sort
            # cannot tell apart swap when the column is reversed.
            return (rank, valu, item[1])

        keyed = sorted(zip(cells, range(len(rows)), rows), key=sortkey, reverse=reverse)

        self.text = '\n'.join(head + [line for (_, _, line) in keyed])

class Div(Block):
    '''
    A pandoc fenced div, which is a container: its `valu` is the source between the fences.
    '''
    kind = 'div'

    def getInfo(self):
        match = FENCE_OPEN.match(self.text.split('\n')[0])
        if match is None:
            return ''

        return match.group(1)

    def getClasses(self):
        return ATTR_CLASS.findall(self.getInfo())

    def setClasses(self, classes):
        '''
        Replace the classes on the opening fence, keeping everything else on it and its content.

        Rewritten token by token rather than rebuilt from `getClasses`/`getAttrs`, which between them
        do not describe a whole fence: `#fig1` is neither a class nor a `key=value` pair, and neither
        is a bare flag, so rebuilding from those would drop a hand-authored anchor.
        '''
        parts = [f'.{name}' for name in (classes or ())]

        for token in ATTR_TOKEN.findall(self.getInfo()):
            if not token.startswith('.'):
                parts.append(token)

        lines = self.text.split('\n')
        lines[0] = f'::: {{{" ".join(parts)}}}'

        self.text = '\n'.join(lines)

    def getAttrs(self):
        out = {}
        for name, quoted, bare in ATTR_PAIR.findall(self.getInfo()):
            out[name] = unescapeAttr(quoted) if quoted else bare

        return out

    def getValu(self):
        lines = self.text.split('\n')

        # everything between the fences; a div whose closing fence is missing keeps its whole tail
        if lines and FENCE_CLOSE.match(lines[-1]):
            lines = lines[:-1]

        return '\n'.join(lines[1:])

    def setValu(self, valu):
        # A div whose closing fence is missing runs to the end of the document, so rewriting it would
        # replace everything after the mistyped fence.
        lines = self.text.split('\n')
        if not (lines and FENCE_CLOSE.match(lines[-1])):
            mesg = 'this fenced div was never closed, so it holds the rest of the document'
            raise s_exc.BadArg(mesg=mesg, text=self.text)

        self.text = reqDivText(f'::: {{{self.getInfo()}}}\n{valu}\n:::')

KINDS = {
    'heading': Heading,
    'setextheading': Heading,
    'paragraph': Paragraph,
    'codefence': Code,
    'list': List,
    'table': Table,
    'fenceddiv': Div,
}

def parse(text):
    '''
    (document, lines) for text. The lines are kept so a block can own its exact source.
    '''
    lines = text.splitlines(keepends=True)
    with MdRenderer():
        doc = mistletoe.Document(list(lines))

    return doc, lines

def _readsAsOne(block, tail, nextblock):
    '''
    Whether `block` and `nextblock` joined by `tail` parse back as a single block.

    Asked by re-parsing the pair rather than by reasoning about kinds: which token interrupts which is
    the parser's own business, not a table to keep in step with it here.
    '''
    _, blocks = parseBlocks(f'{block.text}{tail}{nextblock.text}\n')

    return len(blocks) < 2

def joinBlocks(blocks, lead=''):
    '''
    The source for a list of blocks.

    Separators come from what was parsed, so an untouched document is byte identical. They are
    normalised only where leaving them would change meaning: two blocks that would read as one need a
    blank line between them (see `_readsAsOne`), and blank lines left at the end by a removal collapse
    to a single newline. A single newline between blocks is a boundary the parser itself honoured, so
    it is kept.

    Duck typed on `text` and `tail`, so it takes either Blocks or the Storm objects wrapping them.
    '''
    if not blocks:
        return lead

    parts = [lead]
    last = len(blocks) - 1

    for indx, block in enumerate(blocks):

        parts.append(block.text)

        if indx == last:
            # A tail of exactly one separator is what a block carried between blocks, so a removal
            # that leaves it at the end collapses it. Anything longer is what the document itself ended
            # with and is kept: normalising that rewrote a body on its first save.
            if block.tail == '\n\n':
                parts.append('\n')
            else:
                parts.append(block.tail)
            continue

        tail = block.tail or '\n'

        if tail.count('\n') < 2:
            # A separator this block did not parse with a successor is a boundary the caller made and
            # gets a blank line. One it did parse with is only widened where the pair would now read as
            # a single block.
            if not getattr(block, 'inner', False) or _readsAsOne(block, tail, blocks[indx + 1]):
                tail = '\n\n'

        parts.append(tail)

    return ''.join(parts)

def unwrapBlocks(blocks):
    '''
    The same blocks, with every storm block replaced by a plain block of its content.

    For a consumer that does not understand pandoc fenced divs. A div that is not a storm block is
    left alone: it carries no data, so its fence is presumably meaningful to whoever wrote it.
    '''
    out = []
    for block in blocks:

        if isinstance(block, StormBlock):
            out.append(Block(block.getValu(), tail=block.tail))
            continue

        out.append(block)

    return out

def parseBlocks(text):
    '''
    (lead, blocks) for text.

    Blank lines are not blocks: they are absorbed as the preceding block's `tail` (or as the
    document's `lead`), so a block index counts what a reader counts.
    '''
    doc, lines = parse(text)

    lead = ''
    blocks = []

    for tok, start, end in _spans(doc.children, len(lines)):

        src = ''.join(lines[start:end])

        if _typename(tok) == 'blankline':
            if blocks:
                blocks[-1].tail += src
            else:
                lead += src

            continue

        body = src.rstrip('\n')
        ctor = KINDS.get(_typename(tok), Block)
        block = ctor(body, tail=src[len(body):])

        blocks.append(promoteDiv(block))

    for block in blocks[:-1]:
        block.inner = True

    return lead, blocks

# -- block source formatting -----------------------------------------------------------------

def escapeGfmCell(text):
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('\\', '\\\\')
    text = text.replace('|', '\\|')
    text = regex.sub(r'\n+', ' ', text)
    return text.strip()

def fmtHeading(text, level):
    if level < 1 or level > 6:
        mesg = f'markdown heading level must be 1-6, got {level}'
        raise s_exc.BadArg(mesg=mesg, level=level)

    return f'{"#" * level} {text}'

def fmtParagraph(text):
    return regex.sub(r'\n+', ' ', text).strip()

def fmtList(items, ordered):

    # A str is iterable, so without this a list built from one comes out as a bullet per character.
    if not isinstance(items, (list, tuple)):
        mesg = 'markdown list items must be a list'
        raise s_exc.BadArg(mesg=mesg, items=items)

    lines = []
    for indx, item in enumerate(items):
        item = str(item)
        if ordered:
            lines.append(f'{indx + 1}. {item}')
        else:
            lines.append(f'- {item}')

    return '\n'.join(lines)

def fmtCode(text, lang):
    fence = '```'
    while fence in text:
        fence += '`'

    return f'{fence}{lang}\n{text}\n{fence}'

def _escInline(text, char):
    '''
    Inline text with a backslash and one delimiter escaped, and newlines collapsed.

    The backslash goes first, or the escape this adds would itself be escaped. A newline is collapsed
    rather than escaped because it would end the inline construct.
    '''
    text = fmtParagraph(text).replace('\\', '\\\\')

    return text.replace(char, f'\\{char}')

def fmtImage(url, alt='', title=None, attrs=None):
    '''
    A markdown image: `![alt](url "title"){attrs}`.

    The alt escapes brackets the way a markdown serializer does, so a reader scanning for images with
    a regex has to allow for those escapes. `attrs` is a pandoc attribute block (`{width=50%}`) and is
    appended as authored.
    '''
    if regex.search(r'[\s()]', url):
        # a bare url ends at whitespace or an unbalanced paren, where the angle form does not
        url = f'<{url}>'

    text = f'![{_escInline(alt, "]")}]({url}'

    if title is not None:
        text += f' "{_escInline(title, chr(34))}"'

    text += ')'

    if attrs is not None:
        text += attrs

    return text

# What we write for each alignment; GFM encodes it in the delimiter row and nowhere else. Reading is
# not restricted to these: see `_justifyOf`.
JUSTIFY_DELIMS = {
    'left': ':---',
    'center': ':---:',
    'right': '---:',
}

def _justifyOf(cell):
    '''
    The alignment a delimiter cell encodes, by its colons -- any number of dashes between them, since
    GFM puts no upper bound on them.

    Not mistletoe's `Table.column_align`, whose `parse_align` reports left and unaligned as the same
    `None`, so a document round-tripped through it would lose every `:---` we wrote.
    '''
    cell = cell.strip()

    if cell.startswith(':') and cell.endswith(':'):
        return 'center'

    if cell.startswith(':'):
        return 'left'

    if cell.endswith(':'):
        return 'right'

    return None

def _tableCells(line):
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]

    if line.endswith('|'):
        line = line[:-1]

    return [cell.strip() for cell in regex.split(r'(?<!\\)\|', line)]

def fmtCell(valu, cdef):
    '''
    One table cell, padded or trimmed to its column's `width`.

    A value longer than the width is cut to fit and ends in `...`, which is a change to the markdown
    the caller stores rather than to how a reader draws it. A column with no width keeps its values
    whole.
    '''
    if valu is None:
        valu = ''

    text = escapeGfmCell(str(valu))

    width = cdef.get('width')
    if width is None:
        return text

    if len(text) > width:
        # `trim` is the only overflow a GFM cell can do: wrapping one value onto several physical
        # lines would turn one logical row into several table rows.
        return text[:max(0, width - 3)] + '...'

    return text.ljust(width)

def fmtRow(cells, coldefs):
    out = []
    for indx, cdef in enumerate(coldefs):
        valu = cells[indx] if indx < len(cells) else ''
        out.append(fmtCell(valu, cdef))

    return f'| {" | ".join(out)} |'

def fmtDelimiter(coldefs):
    cells = [JUSTIFY_DELIMS.get(cdef.get('justify'), '---') for cdef in coldefs]
    return f'| {" | ".join(cells)} |'

# A cell that reads as a number, so a column of them sorts as numbers rather than as text.
# Deliberately narrow: no `nan`, no `inf`, no underscores and no thousands separators.
NUMERIC_CELL = regex.compile(r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$')

# What a markdown table column is: a header, and how its cells are drawn. Anything else a caller hangs
# on a column -- a storm table's `prop`, say -- is dropped here.
# What a column declaration keeps.
COLUMN_KEYS = ('name', 'justify', 'width')

# Accepted on a column and validated, but never kept: a GFM cell can only do one of the values each
# of these has (see `normColumns`), so storing the one that fits says nothing.
COLUMN_DROPPED = ('overflow', 'newlines')

# The narrowest column that keeps a character of a value it trims.
COLUMN_MIN_WIDTH = 4

def normColumns(columns):
    '''
    Column definitions for a table, from names or dicts.

    A column here is presentation only: where a cell's value comes from belongs to the storm layer,
    which is the layer that has nodes.
    '''
    coldefs = []
    for col in columns:
        if isinstance(col, str):
            coldefs.append({'name': col})
            continue

        if isinstance(col, dict):
            if col.get('name') is None:
                mesg = 'markdown table column dict requires a "name"'
                raise s_exc.BadArg(mesg=mesg, column=col)

            # A `$lib.tabular` column means the same thing here, so a coldef written for one
            # prints through the other. A GFM cell is a single line, so of each key's values only
            # the one that fits a line is accepted, which is what this already does either way.
            for (key, fits, rest) in (('overflow', 'trim', 'wrap'), ('newlines', 'replace', 'split')):
                valu = col.get(key)
                if valu is not None and valu != fits:
                    mesg = (f'markdown table column {key} must be "{fits}", got {valu!r}; a GFM cell'
                            f' is one line, so "{rest}" has nowhere to put the rest')
                    raise s_exc.BadArg(mesg=mesg, column=col)

            # Coerced once here rather than at every use: a Storm caller writing `width: "5"` would
            # otherwise fail deep in cell formatting comparing an int to a str.
            col = dict(col)

            width = col.get('width')
            if width is not None:
                try:
                    col['width'] = int(width)
                except (TypeError, ValueError):
                    mesg = f'markdown table column width must be an integer, got {width!r}'
                    raise s_exc.BadArg(mesg=mesg, column=col) from None

                # A trimmed cell ends in `...`, so below this a cut value keeps none of itself.
                if col['width'] < COLUMN_MIN_WIDTH:
                    mesg = f'markdown table column width must be at least {COLUMN_MIN_WIDTH}, got {width!r}'
                    raise s_exc.BadArg(mesg=mesg, column=col)

            # A typo'd justify would otherwise fall back to an unaligned delimiter, silently losing
            # the alignment the caller asked for.
            justify = col.get('justify')
            if justify is not None and justify not in JUSTIFY_DELIMS:
                mesg = f'markdown table column justify must be one of {sorted(JUSTIFY_DELIMS)}, got {justify!r}'
                raise s_exc.BadArg(mesg=mesg, column=col)

            coldefs.append({k: v for (k, v) in col.items() if k in COLUMN_KEYS})
            continue

        mesg = 'markdown table column must be a str or dict'
        raise s_exc.BadArg(mesg=mesg, column=col)

    return coldefs

def newTable(columns, rows=None):
    '''
    A Table block with its header and delimiter rows, plus any rows given up front.
    '''
    coldefs = normColumns(columns)

    header = fmtRow([cdef['name'] for cdef in coldefs], coldefs)
    text = f'{header}\n{fmtDelimiter(coldefs)}'

    tabl = Table(text, coldefs=coldefs)

    for row in rows or ():
        tabl.addRow(row)

    return tabl

def newDiv(classes, attrs=None, valu=''):
    '''
    A Div block with a pandoc opening fence built from classes and attributes.
    '''
    parts = [f'.{name}' for name in (classes or ())]

    for name, valv in (attrs or {}).items():
        parts.append(f'{name}="{escapeAttr(valv)}"')

    return Div(reqDivText(f'::: {{{" ".join(parts)}}}\n{valu}\n:::'))

def reqDivText(text):
    '''
    The source of a fenced div about to be written, refused if it would not read back as that div.

    Content holding a fence line of its own (an unclosed `::: {...}`, or one inside a code fence) moves
    where the div ends, so the blocks after it would be read as its content and their data purged as
    orphans. Asked by re-parsing it with a block after it, as `_readsAsOne` does.
    '''
    _, blocks = parseBlocks(f'{text}\n\n.\n')

    if len(blocks) != 2 or blocks[0].text != text:
        mesg = 'fenced div content holds a fence line of its own, so it would not read back as one div'
        raise s_exc.BadArg(mesg=mesg, text=text)

    return text

def unescapeAttr(valu):
    '''
    The value inside the quotes of an opening fence, as it was before escaping.
    '''
    return regex.sub(r'\\(.)', r'\1', valu)

def escapeAttr(valu):
    '''
    An attribute value as it goes inside the quotes of an opening fence.

    A quote is escaped so the value reads back whole. A newline cannot be escaped at all, since the
    fence is one line, and would leave a div that no longer parses as one.
    '''
    valu = str(valu)

    if '\n' in valu or '\r' in valu:
        mesg = 'a fenced div attribute cannot contain a newline'
        raise s_exc.BadArg(mesg=mesg, valu=valu)

    return valu.replace('\\', '\\\\').replace('"', '\\"')

# -- storm blocks -----------------------------------------------------------------------------

# A storm block's data: what a block needs to rebuild itself, which lives outside the markdown. Core
# owns these keys; a caller may extend the schema with its own.
BLOCK_DATA_SCHEMA = {
    'type': 'object',
    'properties': {
        # Which storm block this is, and what selects the renderer. not `kind`, which is what a block
        # is as markdown and is `stormblock` for every one of these.
        'type': {'type': 'string'},

        # -- the source half: how the values are obtained, the same for every type ------------------
        # The query as it was written, which may name variables: a reader sees what its author wrote,
        # and a rebuild binds `vars` and runs it.
        'query': {'type': 'string'},
        # The values `query` names, bound when it is re-run. Primitives only, since block data is
        # stored as JSON.
        'vars': {'type': 'object'},
        # The mode `query` was written in. Absent means storm. A lookup query is raw values, so a
        # re-run that lost this would run something else entirely.
        'mode': {'enum': ['storm', 'lookup']},
        # When the content was last built by running the query, in epoch micros.
        'updated': {'type': 'integer'},

        # -- the render half: how those values become content, which is the type's own business ----

        # Everything the type's renderer needs, and nothing here knows what that is. The renderer
        # validates its own opts (`synapse.lib.stormlib.markdown.STORM_BLOCK_TYPES`), which is what
        # lets a type core cannot render carry opts core has no schema for.
        'opts': {'type': 'object'},
    },
    'additionalProperties': True,
}

# A storm variable name, as `$name` accepts it. A name the sigil cannot spell is one the query can
# never reference.
VAR_NAME_RE = regex.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')

# ...and the names a runtime already owns. Binding one of these would shadow it for the whole query.
VAR_NAME_RESERVED = ('lib', 'node', 'path')

_blockDataValidator = None

def reqBlockData(data):
    '''
    Validate a storm block's data against the core schema, and hand it back.

    Core validates its own keys and lets a caller add its own, whose shape core has no business
    knowing.
    '''
    global _blockDataValidator

    if _blockDataValidator is None:
        _blockDataValidator = s_config.getJsValidator(BLOCK_DATA_SCHEMA)

    if not isinstance(data, dict):
        mesg = f"a storm block's data must be a dict, got {type(data).__name__}"
        raise s_exc.BadArg(mesg=mesg)

    _blockDataValidator(data)

    reqBlockVars(data.get('vars') or {})

    return data

def reqBlockVars(varz):
    '''
    The variables a storm block's query runs with, validated and handed back.
    '''
    if not isinstance(varz, dict):
        mesg = f'storm block vars must be a dict, got {type(varz).__name__}'
        raise s_exc.BadArg(mesg=mesg)

    for name, valu in varz.items():

        if not VAR_NAME_RE.fullmatch(name):
            mesg = f'a storm block variable name must be a storm variable name, got {name!r}'
            raise s_exc.BadArg(mesg=mesg, name=name)

        if name in VAR_NAME_RESERVED:
            mesg = f'a storm block variable may not be named {name}, which the runtime owns'
            raise s_exc.BadArg(mesg=mesg, name=name)

        _reqVarValu(valu, name)

    return varz

def _reqVarValu(valu, path):
    '''
    Refuse a var value JSON cannot carry. Nested lists and dicts are values like any other; `path`
    names where a bad one sits (`tags.2`), since it is otherwise hard to find.
    '''
    if valu is None or isinstance(valu, (str, bool, int)):
        return

    if isinstance(valu, float):
        if not math.isfinite(valu):
            mesg = f'a storm block variable must be a finite number, {path} is {valu}'
            raise s_exc.BadArg(mesg=mesg, name=path)

        return

    if isinstance(valu, (list, tuple)):
        for indx, item in enumerate(valu):
            _reqVarValu(item, f'{path}.{indx}')

        return

    if isinstance(valu, dict):
        for key, item in valu.items():
            if not isinstance(key, str):
                mesg = f'a storm block variable key must be a string, {path} has {key!r}'
                raise s_exc.BadArg(mesg=mesg, name=path)

            _reqVarValu(item, f'{path}.{key}')

        return

    mesg = f'a storm block variable must be JSON, {path} is {type(valu).__name__}'
    raise s_exc.BadArg(mesg=mesg, name=path)

# A storm block's leading `## Title`: what `getTitle` reads and what `getBody` returns the rest of.
BLOCK_TITLE_RE = regex.compile(r'^## ([^\n]+)(?:\n+|$)')

class StormBlock(Div):
    '''
    A block backed by a Storm query: a fenced div carrying an `iden`, whose content can be rebuilt by
    running the query its data carries.

    The data travels with the block rather than being tracked alongside it, so a block removed from a
    document takes its data with it.
    '''
    kind = 'stormblock'

    def __init__(self, text, tail='', data=None):
        Div.__init__(self, text, tail=tail)
        self.data = dict(data or {})

    def getIden(self):
        return self.getAttrs().get('iden')

    def getTitle(self):
        '''
        The block's editable `## Title`, so a rebuild puts back the one an author has since edited.
        '''
        match = BLOCK_TITLE_RE.match(self.getValu())
        if match is None:
            return None

        return match.group(1)

    def getBody(self):
        '''
        The block's content below its title, which is the half a rebuild replaces.
        '''
        valu = self.getValu()

        match = BLOCK_TITLE_RE.match(valu)
        if match is None:
            return valu

        return valu[match.end():]

    def setTitle(self, title):
        '''
        Retitle the block, or remove its title heading when given None.
        '''
        self._setTitled(self.getBody(), title)

    def setContent(self, body, title=None):
        '''
        Replace the block's content, keeping the fence -- and therefore the iden -- as it was.
        '''
        if title is None:
            title = self.getTitle()

        self._setTitled(body, title)

    def _setTitled(self, body, title):

        if title is None:
            self.setValu(body)
            return

        if not body:
            self.setValu(f'## {title}')
            return

        self.setValu(f'## {title}\n\n{body}')

def promoteDiv(block):
    '''
    A div carrying an `iden` is a storm block: the iden is what says its content can be rebuilt.

    One rule in one place, so a block's kind never depends on whether the div was parsed or built. Its
    data is loaded separately, so a promoted div starts with none.
    '''
    if not isinstance(block, Div) or isinstance(block, StormBlock):
        return block

    if block.getAttrs().get('iden') is None:
        return block

    return StormBlock(block.text, tail=block.tail)

def newStormBlock(classes, iden=None, valu='', attrs=None, data=None):
    '''
    A StormBlock with a pandoc opening fence built from classes, an iden, and any other attributes.
    '''
    if iden is None:
        iden = s_common.guid()

    attrs = dict(attrs or {})
    attrs['iden'] = iden

    div = newDiv(classes, attrs=attrs, valu=valu)

    return StormBlock(div.text, tail=div.tail, data=data)

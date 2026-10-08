import synapse.exc as s_exc
import synapse.lib.mdparse as s_mdparse
import synapse.tests.utils as s_test

class MdParseTest(s_test.SynTest):

    def _body(self):
        # three table formats coexist in real bodies: the frontend's `| --- |`, a width-tracking one,
        # and whatever a human typed. None of them may be reformatted.
        return '\n'.join((
            '# Threat Triage',
            '',
            '::: {.story-table iden="' + 'a' * 32 + '"}',
            '## Known Tools',
            '',
            '| Software | First seen |',
            '|----------|------------|',
            '| beacon.exe | 2024/01/01 |',
            ':::',
            '',
            'Prose between.',
            '',
            '| a | b |',
            '| --- | --- |',
            '| x | y |',
            '',
            '```mermaid',
            'graph TD',
            '  A --> B',
            '```',
            '',
        ))

    def test_mdparse_blocks(self):

        lead, blocks = s_mdparse.parseBlocks(self._body())

        self.eq('', lead)

        # blank lines are not blocks: they are the whitespace between them, so an index counts what a
        # reader counts
        # the div carries an iden, which is what makes it a storm block rather than a plain div
        self.eq(['heading', 'stormblock', 'paragraph', 'table', 'code'], [b.kind for b in blocks])

        # every block owns the source it came from, verbatim
        self.eq('# Threat Triage', blocks[0].text)
        self.eq('\n\n', blocks[0].tail)
        self.true(blocks[1].text.endswith(':::'))
        self.isin('|----------|------------|', blocks[1].text)

    def test_mdparse_joins_back_exactly(self):
        # the whole point: a document nothing touched comes back byte for byte, so no table is
        # reformatted and no diff appears that nobody made
        for text in (self._body(),
                     '# Title\n\nIntro.',
                     '\n\n# Leading blank lines\n',
                     'no trailing newline',
                     '',
                     'a\n\n\n\nfour newlines between\n',
                     # ...including a body written with no blank lines between its blocks. Every
                     # separator here is one newline, and each is a boundary the parser itself
                     # honours: normalising them rewrote such a body on its first save.
                     '# Heading\nParagraph text\n',
                     '# A\n## B\n',
                     '# H\n- one\n- two\n',
                     'para\n> quote\n',
                     'para\n```\ncode\n```\n'):

            lead, blocks = s_mdparse.parseBlocks(text)
            self.eq(text, s_mdparse.joinBlocks(blocks, lead=lead))

    def test_mdparse_join_separates_what_a_caller_brought_together(self):
        # the last block of a body carries no trailing newline, so appending onto it would leave the
        # two blocks one newline apart -- which markdown reads as one block
        lead, blocks = s_mdparse.parseBlocks('first')
        blocks.append(s_mdparse.Paragraph('second'))
        self.eq('first\n\nsecond', s_mdparse.joinBlocks(blocks, lead=lead))

        # and a removal at the end does not leave a run of blank lines behind
        lead, blocks = s_mdparse.parseBlocks('first\n\nsecond\n')
        blocks.pop()
        self.eq('first\n', s_mdparse.joinBlocks(blocks, lead=lead))

        # a removal in the middle is the other way two blocks come together: the paragraph above
        # carried a single newline because a heading followed it, and the paragraph now below it
        # would be read as a continuation of that paragraph
        lead, blocks = s_mdparse.parseBlocks('para1\n# H\n\npara2\n')
        blocks.pop(1)
        self.eq('para1\n\npara2\n', s_mdparse.joinBlocks(blocks, lead=lead))

        # ...where the same removal between blocks that cannot read as one keeps what was parsed
        lead, blocks = s_mdparse.parseBlocks('# A\n# B\n# C\n')
        blocks.pop(1)
        self.eq('# A\n# C\n', s_mdparse.joinBlocks(blocks, lead=lead))

        # the last block's lone newline is the document's ending rather than a separator, so a block
        # appended after it gets the blank line an author would have written -- which is the same
        # tail value that is left alone above, and the only thing telling them apart is `inner`
        lead, blocks = s_mdparse.parseBlocks('# Triage\n')
        self.eq([False], [b.inner for b in blocks])

        blocks.append(s_mdparse.Heading('## Infrastructure'))
        self.eq('# Triage\n\n## Infrastructure', s_mdparse.joinBlocks(blocks, lead=lead))

        lead, blocks = s_mdparse.parseBlocks('# Triage\n## Infrastructure\n')
        self.eq([True, False], [b.inner for b in blocks])

    def test_mdparse_fence_is_not_a_directive(self):
        # a ::: inside a code fence must not parse as a fenced div -- the line-scan regex this
        # replaces got that wrong
        text = '\n'.join((
            '```markdown',
            '::: {.story-table iden="' + 'b' * 32 + '"}',
            ':::',
            '```',
            '',
        ))

        lead, blocks = s_mdparse.parseBlocks(text)
        self.eq(['code'], [b.kind for b in blocks])

    def test_mdparse_heading(self):

        lead, blocks = s_mdparse.parseBlocks('## Findings\n')
        head = blocks[0]

        self.eq(2, head.getLevel())
        self.eq('Findings', head.getValu())

        head.setLevel(4)
        self.eq('#### Findings', head.text)

        head.setValu('Conclusions')
        self.eq('#### Conclusions', head.text)

        with self.raises(s_exc.BadArg):
            head.setLevel(7)

        # a closing hash run is part of the syntax, not the text
        lead, blocks = s_mdparse.parseBlocks('## Padded ##\n')
        self.eq('Padded', blocks[0].getValu())

        # a setext heading has no `#` run to rewrite, so it says so rather than corrupting itself
        lead, blocks = s_mdparse.parseBlocks('Title\n=====\n')
        self.eq('heading', blocks[0].kind)
        self.none(blocks[0].getLevel())
        with self.raises(s_exc.BadArg):
            blocks[0].setValu('Nope')

    def test_mdparse_code(self):

        lead, blocks = s_mdparse.parseBlocks('```storm\ninet:fqdn\n```\n')
        code = blocks[0]

        self.eq('storm', code.getLang())
        self.eq('inet:fqdn', code.getValu())

        code.setLang('python')
        self.eq('```python\ninet:fqdn\n```', code.text)

        code.setValu('import synapse')
        self.eq('```python\nimport synapse\n```', code.text)

        # a fence widens past a backtick run in the body
        code.setValu('a ``` b')
        self.eq('````python\na ``` b\n````', code.text)

    def test_mdparse_list(self):

        lead, blocks = s_mdparse.parseBlocks('- alpha\n- beta\n')
        node = blocks[0]

        self.false(node.getOrdered())
        self.eq(['alpha', 'beta'], node.getItems())

        node.setOrdered(True)
        self.eq('1. alpha\n2. beta', node.text)

        node.setItems(['one', 'two', 'three'])
        self.eq('1. one\n2. two\n3. three', node.text)

    def test_mdparse_table_sort(self):

        text = '| Name | N |\n| --- | --- |\n| beta | 2 |\n| alpha | 10 |\n| gamma | 1 |\n'
        lead, blocks = s_mdparse.parseBlocks(text)

        tabl = blocks[0]
        tabl.sortRows(0)

        self.eq(['alpha', 'beta', 'gamma'], [row[0] for row in tabl.getRows()])

        # the header and the delimiter are not rows: they stay where they are
        self.true(tabl.text.startswith('| Name | N |\n| --- | --- |\n'))

        # ...and a row moved whole, so its other cells came with it
        self.eq(['10', '2', '1'], [row[1] for row in tabl.getRows()])

        tabl.sortRows(0, reverse=True)
        self.eq(['gamma', 'beta', 'alpha'], [row[0] for row in tabl.getRows()])

        # a column whose cells all read as numbers is compared as numbers, where its text would say
        # '10' before '2'. Inferred from the cells, since a column type cannot survive the round trip
        # through markdown.
        tabl.sortRows(1)
        self.eq(['1', '2', '10'], [row[1] for row in tabl.getRows()])

        tabl.sortRows(1, reverse=True)
        self.eq(['10', '2', '1'], [row[1] for row in tabl.getRows()])

        # ...and one cell that does not is enough to make it a column of text again
        lead, blocks = s_mdparse.parseBlocks(
            '| A | B |\n| --- | --- |\n| a | 10 |\n| b | 2 |\n| c | many |\n')
        blocks[0].sortRows(1)
        self.eq(['10', '2', 'many'], [row[1] for row in blocks[0].getRows()])

        # nan and inf are not numbers a reader would call numbers in a cell
        lead, blocks = s_mdparse.parseBlocks('| A |\n| --- |\n| 10 |\n| nan |\n| 2 |\n')
        blocks[0].sortRows(0)
        self.eq([['10'], ['2'], ['nan']], blocks[0].getRows())

        # an empty cell is the smallest value -- first ascending, last descending -- which is what
        # the table view in Optic does with one. A row too short to have the cell counts as empty
        # rather than raising, since a hand-edited table can carry a short row.
        text = '| A | B |\n| --- | --- |\n| b |\n| a | 2 |\n| c |  |\n'

        lead, blocks = s_mdparse.parseBlocks(text)
        blocks[0].sortRows(1)
        self.eq(['b', 'c', 'a'], [row[0] for row in blocks[0].getRows()])

        # ...and the two rows the sort cannot tell apart swap when it is reversed, as they do in
        # Optic's table view
        lead, blocks = s_mdparse.parseBlocks(text)
        blocks[0].sortRows(1, reverse=True)
        self.eq(['a', 'c', 'b'], [row[0] for row in blocks[0].getRows()])

        # a sort is stable, so rows it cannot tell apart keep the order they arrived in
        lead, blocks = s_mdparse.parseBlocks('| A | B |\n| --- | --- |\n| x | 1 |\n| x | 2 |\n| x | 3 |\n')
        blocks[0].sortRows(0)
        self.eq(['1', '2', '3'], [row[1] for row in blocks[0].getRows()])

    def test_mdparse_table(self):

        lead, blocks = s_mdparse.parseBlocks('| L | C | R |\n| :--- | :---: | ---: |\n| a | b | c |\n')
        tabl = blocks[0]

        # justification is recovered from the delimiter row, which is the only place GFM keeps it
        self.eq([{'name': 'L', 'justify': 'left'},
                 {'name': 'C', 'justify': 'center'},
                 {'name': 'R', 'justify': 'right'}], tabl.getColumns())

        # GFM puts no upper bound on the dashes, so a table written by hand or by another generator
        # aligns the same as the one we emit
        lead, blocks = s_mdparse.parseBlocks('| L | C | R |\n| :- | :-------: | -----: |\n| a | b | c |\n')
        self.eq([{'name': 'L', 'justify': 'left'},
                 {'name': 'C', 'justify': 'center'},
                 {'name': 'R', 'justify': 'right'}], blocks[0].getColumns())

        # ...and a delimiter with no colons at all has no alignment to recover
        lead, blocks = s_mdparse.parseBlocks('| A |\n| ----- |\n| a |\n')
        self.eq([{'name': 'A'}], blocks[0].getColumns())

        # a row is appended, so every row already in the table is untouched and the delimiter keeps
        # the alignment a re-render would have dropped
        tabl.addRow(('x', 'y', 'z'))
        self.eq('| L | C | R |\n| :--- | :---: | ---: |\n| a | b | c |\n| x | y | z |', tabl.text)

        with self.raises(s_exc.BadArg):
            tabl.addRow(('too', 'few'))

        # a table built here starts from its header
        tabl = s_mdparse.newTable(('A', {'name': 'B', 'justify': 'right'}))
        self.eq('| A | B |\n| --- | ---: |', tabl.text)

        # a null cell is empty rather than padded, since a column with no width pads nothing
        tabl.addRow(('x|y', None))
        self.eq('| A | B |\n| --- | ---: |\n| x\\|y |  |', tabl.text)

    def test_mdparse_div(self):

        text = '::: {.story-table .wide iden="' + 'c' * 32 + '" count=3}\n## T\n\n| A |\n| --- |\n:::'
        lead, blocks = s_mdparse.parseBlocks(text + '\n')
        div = blocks[0]

        self.eq(['story-table', 'wide'], div.getClasses())
        self.eq({'iden': 'c' * 32, 'count': '3'}, div.getAttrs())
        self.eq('## T\n\n| A |\n| --- |', div.getValu())

        # setting the content keeps the opening fence exactly as it was, idens and all
        div.setValu('## T\n\n| A |\n| --- |\n| 1 |')
        self.isin('iden="' + 'c' * 32 + '"', div.text)
        self.isin('| 1 |', div.text)

        # a div whose closing fence never arrived keeps its tail rather than losing a line
        lead, blocks = s_mdparse.parseBlocks('::: {.story-table}\n## T\n\nmore text\n')
        self.isin('more text', blocks[0].getValu())

        div = s_mdparse.newDiv(('story-image',), attrs={'iden': 'd' * 32}, valu='![x](y)')
        self.eq('::: {.story-image iden="' + 'd' * 32 + '"}\n![x](y)\n:::', div.text)

        # content holding a fence line of its own would move where the div ends, taking the blocks
        # after it in as content; refused on both writers rather than written. An unclosed code
        # fence is one too: it holds the div's own closing fence.
        for valu in ('See below.\n\n::: {.callout}\nunterminated', ':::', '```\nunclosed code'):

            with self.raises(s_exc.BadArg):
                s_mdparse.newDiv(('storm-block',), attrs={'iden': 'e' * 32}, valu=valu)

            with self.raises(s_exc.BadArg):
                div.setValu(valu)

        # ...and a div left as it was
        self.eq('::: {.story-image iden="' + 'd' * 32 + '"}\n![x](y)\n:::', div.text)

        # balanced content still builds: a nested div, a code fence, and a code fence showing fence
        # lines, which are the code block's content rather than fences
        for valu in ('::: {.note}\ninner\n:::', '```\ncode\n```', 'plain text', '```\n:::\n```',
                     '```\n::: {.a}\n```', '~~~~\n:::\n~~~\n:::\n~~~~', '````\n```\n:::\n````'):
            div.setValu(valu)
            self.eq(valu, div.getValu())

        # a backtick fence's info string cannot hold a backtick, so this is not a code fence
        with self.raises(s_exc.BadArg):
            div.setValu('```py `x`\n:::\n```')

        # read back where it was written: the code fence's `:::` does not end the block holding it
        text = '::: {.storm-block iden="' + 'a' * 32 + '"}\n```\n:::\n```\n:::\n\nafter\n'
        lead, blocks = s_mdparse.parseBlocks(text)
        self.eq(['stormblock', 'paragraph'], [b.kind for b in blocks])
        self.eq('```\n:::\n```', blocks[0].getValu())

    def test_mdparse_cells(self):

        self.eq('a\\|b', s_mdparse.escapeGfmCell('a|b'))
        self.eq('&lt;b&gt;', s_mdparse.escapeGfmCell('<b>'))
        self.eq('one two', s_mdparse.escapeGfmCell('one\ntwo'))

        # width and overflow: a GFM cell is one line, so trimming is the only thing that fits
        self.eq('he...', s_mdparse.fmtCell('hello world', {'name': 'T', 'width': 5}))
        self.eq('hi   ', s_mdparse.fmtCell('hi', {'name': 'T', 'width': 5}))
        self.eq('hello world', s_mdparse.fmtCell('hello world', {'name': 'T'}))

        # `$lib.tabular` spells these the same way, so a coldef written for one prints through the
        # other -- but only at the value a single-line cell can do, and neither is kept
        self.eq([{'name': 'T', 'width': 5}],
                s_mdparse.normColumns([{'name': 'T', 'width': 5, 'overflow': 'trim',
                                        'newlines': 'replace'}]))

        with self.raises(s_exc.BadArg):
            s_mdparse.normColumns([{'name': 'T', 'overflow': 'wrap'}])

        with self.raises(s_exc.BadArg):
            s_mdparse.normColumns([{'name': 'T', 'newlines': 'split'}])

        # a typo'd value is refused rather than quietly ignored, which is what it was before
        with self.raises(s_exc.BadArg):
            s_mdparse.normColumns([{'name': 'T', 'overflow': 'trimm'}])

        # a trimmed cell ends in `...`, so a narrower column would keep none of the value
        self.eq('v...', s_mdparse.fmtCell('vertex.link', s_mdparse.normColumns([{'name': 'T', 'width': 4}])[0]))
        for width in (3, 1, 0, -1):
            with self.raises(s_exc.BadArg):
                s_mdparse.normColumns([{'name': 'T', 'width': width}])

        with self.raises(s_exc.BadArg):
            s_mdparse.normColumns([{'justify': 'left'}])

        with self.raises(s_exc.BadArg):
            s_mdparse.normColumns([(1, 2)])

    def test_mdparse_generic_blocks(self):
        # anything without a richer type is still a block that keeps its source and can be moved
        text = '> quoted\n\n<div>html</div>\n\n---\n'
        lead, blocks = s_mdparse.parseBlocks(text)

        self.eq(['block', 'block', 'block'], [b.kind for b in blocks])
        self.eq('> quoted', blocks[0].text)

        blocks.reverse()
        self.eq('---\n\n<div>html</div>\n\n> quoted\n', s_mdparse.joinBlocks(blocks, lead=lead))

    def test_mdparse_storm_block(self):

        block = s_mdparse.newStormBlock(('storm-table',), valu='## Tools\n\n| A |\n| --- |')

        self.eq('stormblock', block.kind)
        self.len(32, block.getIden())
        self.eq('Tools', block.getTitle())
        self.eq({}, block.data)

        # rewriting the content keeps the fence, so the iden survives an edit
        iden = block.getIden()
        block.setContent('| A |\n| --- |\n| 1 |')
        self.isin(f'iden="{iden}"', block.text)
        self.isin('| 1 |', block.text)
        self.eq('Tools', block.getTitle())

        # ...and the title can be replaced along with it
        block.setContent('| B |\n| --- |', title='Renamed')
        self.eq('Renamed', block.getTitle())

        # the title moves on its own, leaving the content where it is
        block.setTitle('Tools')
        self.eq('Tools', block.getTitle())
        self.eq('| B |\n| --- |', block.getBody())

        # ...and removing it leaves the content and nothing else
        block.setTitle(None)
        self.none(block.getTitle())
        self.eq('| B |\n| --- |', block.getValu())

        # a block that is only a title has no body to keep hold of
        block = s_mdparse.newStormBlock(('storm-table',), iden='d' * 32, valu='## T')
        self.eq('', block.getBody())
        block.setTitle('Renamed')
        self.eq('::: {.storm-table iden="' + 'd' * 32 + '"}\n## Renamed\n:::', block.text)

        # a block with no title keeps none rather than growing one
        block = s_mdparse.newStormBlock(('storm-table',), iden='b' * 32, valu='| A |\n| --- |')
        self.none(block.getTitle())
        block.setContent('| A |\n| --- |\n| 2 |')
        self.eq('::: {.storm-table iden="' + 'b' * 32 + '"}\n| A |\n| --- |\n| 2 |\n:::', block.text)

        # a parsed div carrying an iden is a storm block: the iden says its content came from somewhere
        lead, blocks = s_mdparse.parseBlocks('::: {.story-table iden="' + 'c' * 32 + '"}\n## T\n:::\n')
        self.eq('stormblock', blocks[0].kind)
        self.eq('c' * 32, blocks[0].getIden())

        # ...where a div without one is just a div
        lead, blocks = s_mdparse.parseBlocks('::: {.note}\nplain\n:::\n')
        self.eq('div', blocks[0].kind)

    def test_mdparse_block_vars(self):

        # a var is bound into a runtime by name, so a name the `$` sigil cannot spell is one the
        # query can never reference: refused where it is stored rather than binding nothing
        for name in ('x = (0) | [inet:fqdn=pwned.com] //', 'one two', 'a-b', '', '1x', 'a.b'):
            with self.raises(s_exc.BadArg) as cm:
                s_mdparse.reqBlockVars({name: 'hi'})

            self.isin('storm variable name', cm.exception.get('mesg'))

        self.eq({'_a1': 'hi'}, s_mdparse.reqBlockVars({'_a1': 'hi'}))

        # ...and a name the runtime already owns would shadow it for the whole query
        for name in ('lib', 'node', 'path'):
            with self.raises(s_exc.BadArg) as cm:
                s_mdparse.reqBlockVars({name: 'hi'})

            self.isin('which the runtime owns', cm.exception.get('mesg'))

        # block data is stored as JSON, so a value is anything JSON holds, nested lists and dicts
        # included: a query is handed a list to iterate, or a dict to look things up in
        varz = {'a': 3, 'b': True, 'c': 'x', 'd': 1.5, 'e': None, 'f': ['x', 2, None],
                'g': {'k': [{'deep': True}], 'n': {}}, 'h': ('tuple', 'from', 'storm')}
        self.eq(varz, s_mdparse.reqBlockVars(varz))

        # ...but only that, and a bad value says where it sits
        for valu, where in (({'x': float('nan')}, 'a.x'), ([1, float('inf')], 'a.1'),
                            ({'k': [object()]}, 'a.k.0'), ({1: 'x'}, 'a'), (b'raw', 'a')):
            with self.raises(s_exc.BadArg) as cm:
                s_mdparse.reqBlockVars({'a': valu})

            self.eq(where, cm.exception.get('name'))

        with self.raises(s_exc.BadArg) as cm:
            s_mdparse.reqBlockVars(('a', 'b'))

        self.isin('must be a dict', cm.exception.get('mesg'))

    def test_mdparse_data(self):

        self.nn(s_mdparse.reqBlockData({'type': 'table', 'query': 'inet:fqdn'}))

        # a caller's own keys ride along: core validates its own and knows nothing of the rest
        self.nn(s_mdparse.reqBlockData({'type': 'table', 'config': {'cdefs': {'form': 'inet:fqdn'}}}))

        with self.raises(s_exc.BadArg):
            s_mdparse.reqBlockData('nope')

        # A kind core does not know is a kind someone else rebuilds: an enum here would make this the
        # registry of every consumer's block types. It still has to be a kind.
        self.nn(s_mdparse.reqBlockData({'type': 'chart', 'form': 'inet:fqdn'}))

        with self.raises(s_exc.SchemaViolation):
            s_mdparse.reqBlockData({'type': (1)})

        with self.raises(s_exc.SchemaViolation):
            s_mdparse.reqBlockData({'mode': 'newp'})

        # a var has to be storable as JSON, since that is what a data is: a list is, bytes are not
        self.eq({'nodes': ['a', 'b']}, s_mdparse.reqBlockData({'vars': {'nodes': ['a', 'b']}})['vars'])

        with self.raises(s_exc.BadArg):
            s_mdparse.reqBlockData({'vars': {'nodes': b'ab'}})

    def test_mdparse_hostile_source(self):

        # a fenced div nests: a bare ::: closes the innermost one, so an outer div survives the round
        # trip rather than having its own close read as a paragraph
        text = '::: {.outer}\n::: {.inner}\nhi\n:::\n:::\n\nAfter.\n'
        lead, blocks = s_mdparse.parseBlocks(text)
        self.eq(text, s_mdparse.joinBlocks(blocks, lead=lead))
        self.eq(('div', 'paragraph'), tuple(b.kind for b in blocks))

        # an attribute value is quoted, so a quote in it is escaped and reads back whole
        div = s_mdparse.newDiv(['story-table'], attrs={'title': 'a "b" c'})
        self.eq({'title': 'a "b" c'}, div.getAttrs())

        # ...and a newline cannot be escaped into a one line fence at all
        with self.raises(s_exc.BadArg):
            s_mdparse.newDiv(['story-table'], attrs={'title': 'a\nb'})

        # a dot inside an attribute value is not a class
        self.eq(['story-table'], s_mdparse.newDiv(['story-table'], attrs={'src': 'foo.png'}).getClasses())

        # re-classing a div keeps its attributes and its content: the opening fence is rebuilt by the
        # same writer that wrote it, so an attribute the caller never looked at survives.
        text = '::: {.old-class iden="' + 'a' * 32 + '" title="T"}\n## T\n\n| a |\n| - |\n:::\n'
        lead, blocks = s_mdparse.parseBlocks(text)

        div = blocks[0]
        div.setClasses(['storm-block'])

        self.eq(['storm-block'], div.getClasses())
        self.eq({'iden': 'a' * 32, 'title': 'T'}, div.getAttrs())
        self.eq('## T\n\n| a |\n| - |', div.getValu())

        # ...and it is still a div which reads back as what it now says it is
        lead, blocks = s_mdparse.parseBlocks(s_mdparse.joinBlocks(blocks, lead=lead))
        self.eq(['storm-block'], blocks[0].getClasses())

        # everything else on the fence survives, not just what getAttrs describes: a pandoc `#id`
        # is neither a class nor a key=value pair, and nor is a bare flag, so rebuilding the fence
        # from those two dropped a hand-authored anchor -- one way, since the Stories migration
        # re-classes every legacy block.
        text = '::: {#fig1 .old-class key="v w" iden="' + 'b' * 32 + '" .other flagged}\nbody\n:::\n'
        lead, blocks = s_mdparse.parseBlocks(text)

        div = blocks[0]
        div.setClasses(['storm-block'])

        self.eq('::: {.storm-block #fig1 key="v w" iden="' + 'b' * 32 + '" flagged}',
                div.text.split('\n')[0])

        self.eq(['storm-block'], div.getClasses())
        self.eq({'key': 'v w', 'iden': 'b' * 32}, div.getAttrs())
        self.eq('body', div.getValu())

        # an empty fenced code block is still fenced, and still knows its language
        lead, blocks = s_mdparse.parseBlocks('```python\n```\n')
        self.eq('python', blocks[0].getLang())
        self.eq('', blocks[0].getValu())

        # a nested list cannot be rebuilt from the flat items it reports, so it refuses rather than
        # flattening the nesting and dropping the continuation line
        lead, blocks = s_mdparse.parseBlocks('- alpha\n  - beta\n- delta\n  continued\n')
        with self.raises(s_exc.BadArg):
            blocks[0].setOrdered(True)

        with self.raises(s_exc.BadArg):
            blocks[0].setItems(('one', 'two'))

        # a flat one still edits
        lead, blocks = s_mdparse.parseBlocks('- alpha\n- beta\n')
        blocks[0].setOrdered(True)
        self.eq('1. alpha\n2. beta', blocks[0].text)

        # a div whose closing fence is missing holds the rest of the document, so rewriting it would
        # take that content with it
        lead, blocks = s_mdparse.parseBlocks('::: {.story-table iden="x"}\n| A |\n\nAfter.\n')
        self.len(1, blocks)
        with self.raises(s_exc.BadArg):
            blocks[0].setValu('| B |')

        # a body with trailing blank lines is not rewritten by a round trip
        text = '# A\n\nB\n\n\n'
        lead, blocks = s_mdparse.parseBlocks(text)
        self.eq(text, s_mdparse.joinBlocks(blocks, lead=lead))

    def test_mdparse_block_edges(self):
        # A block owns its own source, so every accessor has to cope with source that does not have the
        # shape its kind usually does -- an indented code block, a table with no delimiter row, a div
        # with no attributes. None of them may raise on the way to answering.

        # a heading's text is whatever it was parsed from; asked for the text of something that is not
        # a heading, it answers with nothing rather than a slice of the wrong string
        self.none(s_mdparse.Heading('not a heading at all').getValu())

        # ...and the repr names the kind, for a traceback that has one in it
        self.eq("Heading('# One')", repr(s_mdparse.Heading('# One')))

        # a paragraph's text is settable, and is re-wrapped as a paragraph
        lead, blocks = s_mdparse.parseBlocks('One para.\n')
        blocks[0].setValu('Another para,\nwith a newline in the source.')
        self.eq('Another para, with a newline in the source.', blocks[0].text)

        # an indented code block is a generic block: the parser only calls something a `code` block when
        # it is fenced, since a fence is what carries the lang
        lead, blocks = s_mdparse.parseBlocks('    indented = True\n')
        self.eq('block', blocks[0].kind)

        # ...so a code block asked about source with no fence in it answers with nothing, and setting a
        # lang on one refuses: there is no fence to put the lang on, and adding one would rewrite the
        # block rather than edit it
        code = s_mdparse.Code('    indented = True')
        self.none(code.getValu())
        self.none(code.getLang())

        with self.raises(s_exc.BadArg):
            code.setLang('python')

        # a list with a blank line between its items is still that list's items
        lead, blocks = s_mdparse.parseBlocks('- alpha\n\n- beta\n')
        self.eq(('alpha', 'beta'), tuple(blocks[0].getItems()))

        # a blank line inside a list's source is not an item, and does not make the list unflat
        loose = s_mdparse.List('- alpha\n\n- beta')
        self.true(loose.isFlat())
        self.eq(['alpha', 'beta'], loose.getItems())

        # a table needs a delimiter row before it has columns
        self.eq([], s_mdparse.Table('| A | B |').getColumns())

        # ...and a div with no attribute block has no info to read
        self.eq('', s_mdparse.Div(':::\ncontent\n:::').getInfo())

    def test_mdparse_justify_delimiters(self):
        # Alignment is read off the delimiter row, which a human writes with however many dashes they
        # like. The canonical four are matched outright; anything else is read from the colons.
        text = '\n'.join((
            '| A | B | C | D |',
            '|:-----|------:|:----:|-----|',
            '| w | x | y | z |',
            '',
        ))

        lead, blocks = s_mdparse.parseBlocks(text)
        cols = blocks[0].getColumns()

        self.eq(['left', 'right', 'center', None], [c.get('justify') for c in cols])
        self.eq(['A', 'B', 'C', 'D'], [c.get('name') for c in cols])

        # ...and the canonical spellings, which are what this layer writes
        text = '| A | B | C | D |\n| :--- | ---: | :---: | --- |\n| w | x | y | z |\n'
        lead, blocks = s_mdparse.parseBlocks(text)
        self.eq(['left', 'right', 'center', None],
                [c.get('justify') for c in blocks[0].getColumns()])

    def test_mdparse_fmt_image(self):

        self.eq('![](/img.png)', s_mdparse.fmtImage('/img.png'))
        self.eq('![a map](/img.png)', s_mdparse.fmtImage('/img.png', alt='a map'))

        # a pandoc link title, which the story export carries through verbatim
        self.eq('![a](/img.png "cap")', s_mdparse.fmtImage('/img.png', alt='a', title='cap'))

        # the sizing attribute the editor writes, appended as authored
        self.eq('![a](/img.png){width=50%}',
                s_mdparse.fmtImage('/img.png', alt='a', attrs='{width=50%}'))

        # a backslash is escaped before the bracket, so the escape is not doubled
        self.eq('![a\\\\b](/img.png)', s_mdparse.fmtImage('/img.png', alt='a\\b'))
        self.eq('![a\\]b](/img.png)', s_mdparse.fmtImage('/img.png', alt='a]b'))
        self.eq('![a](/img.png "he said \\"hi\\"")',
                s_mdparse.fmtImage('/img.png', alt='a', title='he said "hi"'))

        # a newline would end the inline construct, so both texts collapse
        self.eq('![a b](/img.png)', s_mdparse.fmtImage('/img.png', alt='a\nb'))
        self.eq('![a](/img.png "c d")', s_mdparse.fmtImage('/img.png', alt='a', title='c\nd'))

        # a url that would not survive bare is wrapped, which CommonMark reads back the same
        self.eq('![a](</my img.png>)', s_mdparse.fmtImage('/my img.png', alt='a'))
        self.eq('![a](</i(1).png>)', s_mdparse.fmtImage('/i(1).png', alt='a'))

        # what it emits parses back as one block, and round-trips
        text = s_mdparse.fmtImage('/img.png', alt='a map', title='cap', attrs='{width=50%}')
        lead, blocks = s_mdparse.parseBlocks(text + '\n')
        self.len(1, blocks)
        self.eq(text, blocks[0].text)

import unittest.mock as mock

import synapse.exc as s_exc
import synapse.lib.json as s_json
import synapse.tests.utils as s_test
import synapse.lib.stormlib.markdown as s_markdown

BODY = '\n'.join((
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
    '| :--- | ---: |',
    '| x | y |',
    '',
))

class MarkdownTest(s_test.SynTest):

    async def test_stormlib_markdown_doc_build(self):

        async with self.getTestCore() as core:

            # blocks are built, then added; the doc is the blocks
            valu = await core.callStorm('''
                $md = $lib.markdown
                $doc = $md.doc()

                $doc.add($md.heading("Findings", (2)))
                $doc.add($md.paragraph("Two suspect domains."))
                $doc.add($md.list(("alpha", "beta")))
                $doc.add($md.code("inet:fqdn", "storm"))

                $tabl = $md.table(("FQDN", "Created"))
                $tabl.addRow(("evil.com", "2024/01/01"))
                $doc.add($tabl)

                return($doc.text)
            ''')
            self.eq(
                '## Findings\n\n'
                'Two suspect domains.\n\n'
                '- alpha\n- beta\n\n'
                '```storm\ninet:fqdn\n```\n\n'
                '| FQDN | Created |\n| --- | --- |\n| evil.com | 2024/01/01 |',
                valu,
            )

            self.eq('', await core.callStorm('return($lib.markdown.doc().text)'))

            # a doc is its source, so it prints and serializes as markdown
            self.eq('## Hi', await core.callStorm('''
                $doc = $lib.markdown.doc()
                $doc.add($lib.markdown.heading(Hi, (2)))
                return($doc)
            '''))

            # add() appends by default and inserts at a position
            valu = await core.callStorm('''
                $md = $lib.markdown
                $doc = $md.doc()
                $doc.add($md.paragraph(second))
                $doc.add($md.paragraph(first), indx=(0))
                $doc.add($md.paragraph(third), indx=(-1))
                return($doc.text)
            ''')
            self.eq('first\n\nsecond\n\nthird', valu)

            # a position past the end appends rather than raising
            valu = await core.callStorm('''
                $md = $lib.markdown
                $doc = $md.doc()
                $doc.add($md.paragraph(one))
                $doc.add($md.paragraph(two), indx=(7))
                return($doc.text)
            ''')
            self.eq('one\n\ntwo', valu)

            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    $md = $lib.markdown
                    $doc = $md.doc()
                    $doc.add($md.paragraph(one))
                    $doc.add($md.paragraph(two), indx=(-4))
                ''')

            # only a block can be added
            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.markdown.doc().add("## not a block")')

    async def test_stormlib_markdown_doc_parse(self):

        async with self.getTestCore() as core:
            opts = {'vars': {'body': BODY}}

            # a document nothing touched comes back byte for byte: no table is reformatted
            self.true(await core.callStorm(
                'return($($lib.markdown.parse($body).text = $body))', opts=opts))

            # blank lines are not blocks, so a position counts what a reader counts
            valu = await core.callStorm('''
                $out = ([])
                for $block in $lib.markdown.parse($body).blocks { $out.append($block.type) }
                return($out)
            ''', opts=opts)
            self.eq(('heading', 'stormblock', 'paragraph', 'table'), valu)

            # a block is its source
            valu = await core.callStorm('return($lib.markdown.parse($body).blocks.0)', opts=opts)
            self.eq('# Threat Triage', valu)

            # nothing to parse is an empty document, not the string "None"
            self.eq('', await core.callStorm('return($lib.markdown.parse($nope).text)',
                                             opts={'vars': {'nope': None}}))

    async def test_stormlib_markdown_blocks_are_the_document(self):

        async with self.getTestCore() as core:
            opts = {'vars': {'body': BODY}}

            # the list is the document's own, so popping from it changes the document
            valu = await core.callStorm('''
                $doc = $lib.markdown.parse($body)
                $doc.blocks.pop((0))
                return($doc.text)
            ''', opts=opts)
            self.notin('# Threat Triage', valu)
            self.isin('Prose between.', valu)

            # pop plus add is a move, and the block's source is carried verbatim, so an element keeps
            # its iden and a table keeps its formatting
            valu = await core.callStorm('''
                $doc = $lib.markdown.parse($body)
                $doc.add($doc.blocks.pop((1)), indx=(0))
                return($doc.text)
            ''', opts=opts)
            self.true(valu.startswith('::: {.story-table iden="' + 'a' * 32 + '"}'))
            self.isin('|----------|------------|', valu)

            # a block the document already holds is refused rather than added twice: one block in
            # two positions renders twice and edits in both places
            with self.raises(s_exc.BadArg) as ctx:
                await core.callStorm('''
                    $doc = $lib.markdown.parse($body)
                    $doc.add($doc.blocks.1)
                ''', opts=opts)
            self.isin('already in this document', ctx.exception.get('mesg'))

            # ...and so is a second storm block wearing an iden this document has already given out,
            # since one iden names one block's data
            with self.raises(s_exc.BadArg) as ctx:
                await core.callStorm('''
                    $doc = $lib.markdown.parse($body)
                    $doc.add($lib.markdown.stormprint(${ $lib.print(hi) }, iden=$iden))
                ''', opts={'vars': {'body': BODY, 'iden': 'a' * 32}})
            self.isin('already has a storm block with iden', ctx.exception.get('mesg'))

            # the list is the document's own, so what an append, an extend or an assignment puts in
            # is refused where `add()` would refuse it, at the call rather than at the next save
            for q in ('$doc.blocks.append($doc.blocks.1)',
                      '$doc.blocks.extend(($lib.markdown.paragraph(ok), $doc.blocks.1))',
                      '$doc.blocks.0 = $doc.blocks.1'):
                with self.raises(s_exc.BadArg) as ctx:
                    await core.callStorm(f'$doc = $lib.markdown.parse($body) {q}', opts=opts)
                self.isin('already in this document', ctx.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as ctx:
                await core.callStorm('''
                    $doc = $lib.markdown.parse($body)
                    $doc.blocks.append($lib.markdown.stormprint(${ $lib.print(hi) }, iden=$iden))
                ''', opts={'vars': {'body': BODY, 'iden': 'a' * 32}})
            self.isin('already has a storm block with iden', ctx.exception.get('mesg'))

            for q in ('$doc.blocks.append(oops)', '$doc.blocks.extend((oops,))', '$doc.blocks.0 = oops'):
                with self.raises(s_exc.BadArg) as ctx:
                    await core.callStorm(f'$doc = $lib.markdown.parse($body) {q}', opts=opts)
                self.isin('holds markdown blocks', ctx.exception.get('mesg'))

            # ...an extend refused part way puts none of it in
            valu = await core.callStorm('''
                $doc = $lib.markdown.parse($body)
                $size = $doc.blocks.size()
                try { $doc.blocks.extend(($lib.markdown.paragraph(first), oops)) } catch BadArg as err {}
                return(($size, $doc.blocks.size()))
            ''', opts=opts)
            self.eq(valu[0], valu[1])

            # ...and a block new to the document goes in each way, as an edit to it
            valu = await core.callStorm('''
                $doc = $lib.markdown.parse($body)
                $doc.blocks.append($lib.markdown.paragraph(appended))
                $doc.blocks.extend(($lib.markdown.paragraph(extended),))
                $doc.blocks.0 = $lib.markdown.heading(Replaced, (1))
                $doc.blocks.1 = $doc.blocks.1
                return($doc.text)
            ''', opts=opts)
            self.true(valu.startswith('# Replaced'))
            self.true(valu.rstrip().endswith('appended\n\nextended'))

            # ...while taking one out needs no check, and assigning nothing is how
            valu = await core.callStorm('''
                $doc = $lib.markdown.parse($body)
                $size = $doc.blocks.size()
                $doc.blocks.0 = $lib.undef
                return(($size, $doc.blocks.size()))
            ''', opts=opts)
            self.eq(valu[0] - 1, valu[1])

            # an index past the end is the same error a plain list gives
            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('$doc = $lib.markdown.parse($body) $doc.blocks.99 = $lib.markdown.paragraph(x)',
                                     opts=opts)

            # and the same objects go into another document
            valu = await core.callStorm('''
                $doc = $lib.markdown.parse($body)
                $other = $lib.markdown.doc()
                for $block in $doc.blocks {
                    if ($block.type = "table") { $other.add($block) }
                }
                return($other.text)
            ''', opts=opts)
            # the block brought its trailing whitespace with it, which is why the source it came
            # from is not disturbed either
            self.eq('| a | b |\n| :--- | ---: |\n| x | y |\n', valu)

    async def test_stormlib_markdown_block_types(self):

        async with self.getTestCore() as core:

            # heading: level and text, both ways
            valu = await core.callStorm('''
                $head = $lib.markdown.heading(Findings, (2))
                $level = $head.level
                $head.level = (4)
                $head.valu = Conclusions
                return(($level, $head.valu, $head.text))
            ''')
            self.eq((2, 'Conclusions', '#### Conclusions'), valu)

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.markdown.heading(x, (7))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$head = $lib.markdown.heading(x) $head.level = (0)')

            # code: language and body
            valu = await core.callStorm('''
                $code = $lib.markdown.code("inet:fqdn", storm)
                $code.lang = python
                $code.valu = "import synapse"
                return(($code.lang, $code.valu, $code.text))
            ''')
            self.eq(('python', 'import synapse', '```python\nimport synapse\n```'), valu)

            # list: items and ordering
            valu = await core.callStorm('''
                $list = $lib.markdown.list((alpha, beta))
                $ordered = $list.ordered
                $list.ordered = (true)
                $list.items = (one, two)
                return(($ordered, $list.items, $list.text))
            ''')
            self.eq((False, ('one', 'two'), '1. one\n2. two'), valu)

            # a str where items belong would otherwise be a bullet per character
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.markdown.list("nope").text)')

            # paragraph: newlines collapse
            self.eq('one two', await core.callStorm('return($lib.markdown.paragraph("one\\ntwo").valu)'))

            # image: a standalone one is a paragraph, so it reads back as the block a body parses to
            valu = await core.callStorm('''
                $img = $lib.markdown.image("/img.png", alt="a map", title=cap, attrs="{width=50%}")
                return(($img.type, $img.text))
            ''')
            self.eq(('paragraph', '![a map](/img.png "cap"){width=50%}'), valu)

            self.eq('![](/img.png)', await core.callStorm('return($lib.markdown.image("/img.png").text)'))

            # what it emits goes into a document and comes back out as one block
            valu = await core.callStorm('''
                $doc = $lib.markdown.doc()
                $doc.add($lib.markdown.image("/img.png", alt="a map"))
                $doc = $lib.markdown.parse($doc.text)
                return(($lib.len($doc.blocks), $doc.blocks.0.type, $doc.blocks.0.text))
            ''')
            self.eq((1, 'paragraph', '![a map](/img.png)'), valu)

            # text is settable on any block, and is the block's whole source
            self.eq('> quoted', await core.callStorm('''
                $block = $lib.markdown.raw("placeholder")
                $block.text = "> quoted"
                return($block.text)
            '''))

    async def test_stormlib_markdown_table(self):

        async with self.getTestCore() as core:

            valu = await core.callStorm('''
                $tabl = $lib.markdown.table(("A", "B"))
                $tabl.addRow((1, 2))
                $tabl.addRows((("x|y", "z"), ("c", (null))))
                return(({"text": $tabl.text, "rows": $tabl.rows}))
            ''')
            self.eq('| A | B |\n| --- | --- |\n| 1 | 2 |\n| x\\|y | z |\n| c |  |', valu['text'])

            # the rows read back as a plain list, each a list of cells as they are written -- a cell
            # carrying a `|` keeps the escape that is in the table
            self.eq([['1', '2'], ['x\\|y', 'z'], ['c', '']], valu['rows'])

            # ...and a table parsed from a body reads its rows the same way
            self.eq([['x', 'y']], await core.callStorm(
                'return($lib.markdown.parse("| a | b |\\n| - | - |\\n| x | y |\\n").blocks.0.rows)'))

            # a table with no rows yet has none, rather than reading its delimiter row as one
            self.eq([], await core.callStorm('return($lib.markdown.table((A, B)).rows)'))

            # justify reaches the GFM delimiter row, which is the only place alignment lives in
            # pipe-table text
            valu = await core.callStorm('''
                $cols = (({"name": "L", "justify": "left"}), ({"name": "R", "justify": "right"}))
                return($lib.markdown.table($cols).text)
            ''')
            self.eq('| L | R |\n| :--- | ---: |', valu)

            valu = await core.callStorm(
                'return($lib.markdown.table((({"name": "C", "justify": "center"}),)).text)')
            self.eq('| C |\n| :---: |', valu)

            # width and overflow are honoured per cell; a GFM cell is one line, so wrap is refused
            valu = await core.callStorm('''
                $tabl = $lib.markdown.table((({"name": "T", "width": 5, "overflow": "trim"}),))
                $tabl.addRow(("hello world",))
                return($tabl.text)
            ''')
            self.eq('| T     |\n| --- |\n| he... |', valu)

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.markdown.table((({"name": "T", "overflow": "wrap"}),))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.markdown.table((({"justify": "left"}),))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.markdown.table(("A", "B")).addRow((1,))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.markdown.table(("A",)).addRow("nope")')

            # rows can come in with the columns, for a caller that already has them
            valu = await core.callStorm('''
                return($lib.markdown.table((A, B), rows=((1, 2), (3, 4))).text)
            ''')
            self.eq('| A | B |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |', valu)

            # a width or a justify written as a bareword reaches python as a str, so both are coerced
            # and checked once rather than failing deep in cell formatting
            valu = await core.callStorm('''
                $cols = (({"name": "T", "width": "5", "overflow": "trim"}),)
                return($lib.markdown.table($cols, rows=(("hello world",),)).text)
            ''')
            self.eq('| T     |\n| --- |\n| he... |', valu)

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.markdown.table((({"name": "T", "width": "wide"}),))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.markdown.table((({"name": "T", "justify": "centre"}),))')

            # a plain table keeps only what it draws: a storm table's `prop` says which value fills a
            # cell, which is not a markdown question, so it does not ride into the table
            valu = await core.callStorm('''
                $cols = (({"name": "N", "prop": ":name", "justify": "right"}),)
                return($lib.markdown.table($cols).columns)
            ''')
            self.eq(({'name': 'N', 'justify': 'right'},), valu)

            # a row appended to a parsed table leaves every row already in it exactly as it was
            valu = await core.callStorm('''
                $doc = $lib.markdown.parse($body)
                for $block in $doc.blocks {
                    if ($block.type = "table") { $block.addRow((q, r)) }
                }
                return($doc.text)
            ''', opts={'vars': {'body': BODY}})
            self.isin('|----------|------------|', valu)
            self.isin('| a | b |\n| :--- | ---: |\n| x | y |\n| q | r |', valu)

    async def test_stormlib_markdown_div(self):

        async with self.getTestCore() as core:

            valu = await core.callStorm('''
                $div = $lib.markdown.div((story-table,), attrs=({"iden": "abc"}), valu="## Tools")
                return(($div.text, $div.classes, $div.attrs, $div.valu, $div.type))
            ''')
            self.eq('::: {.story-table iden="abc"}\n## Tools\n:::', valu[0])
            self.eq(('story-table',), valu[1])
            self.eq({'iden': 'abc'}, valu[2])
            self.eq('## Tools', valu[3])

            # an iden makes it a storm block, in hand as much as parsed out of a body: one rule, so a
            # block's kind never depends on how it was obtained
            self.eq('stormblock', valu[4])

            valu = await core.callStorm('''
                $div = $lib.markdown.div((note,), valu="## Tools")
                return($div.type)
            ''')
            self.eq('div', valu)

            # setting the classes rebuilds the fence around its attributes and content, and a single
            # class may be given as a string
            valu = await core.callStorm('''
                $div = $lib.markdown.div((note,), attrs=({"iden": "abc"}), valu="## Tools")
                $div.classes = (story-table, wide)
                $many = ($div.classes, $div.text)
                $div.classes = aside
                return(($many, $div.classes, $div.attrs, $div.valu))
            ''')
            self.eq(('story-table', 'wide'), valu[0][0])
            self.eq('::: {.story-table .wide iden="abc"}\n## Tools\n:::', valu[0][1])
            self.eq(('aside',), valu[1])
            self.eq({'iden': 'abc'}, valu[2])
            self.eq('## Tools', valu[3])

            # setting the content keeps the opening fence, so a block keeps its iden. The body's div
            # carries one, so it parses as a storm block rather than a plain div.
            valu = await core.callStorm('''
                $doc = $lib.markdown.parse($body)
                for $block in $doc.blocks {
                    if ($block.type = "stormblock") { $block.valu = "## Known Tools\\n\\nrebuilt" }
                }
                return($doc.text)
            ''', opts={'vars': {'body': BODY}})
            self.isin('::: {.story-table iden="' + 'a' * 32 + '"}\n## Known Tools\n\nrebuilt\n:::', valu)

    async def test_stormlib_markdown_stormtable(self):

        async with self.getTestCore() as core:

            await core.nodes('[ risk:threat=(apt1, t) :name=APT1 :tag=t.apt1 ]'
                             ' [ +(used)> { [ it:software=(t, webc2) :name=WEBC2 ] } ]')

            valu = await core.callStorm('''
                $threat = (null)
                risk:threat:name=APT1
                $threat = $node
                spin |

                $block = $lib.markdown.stormtable(${ risk:threat=$threat -(used)> it:software },
                                                  columns=(({"name": "Software", "prop": ":name"}),),
                                                  title="Known tools",
                                                  vars=({"threat": $threat.repr()}))

                return(({"type": $block.type, "classes": $block.classes, "iden": $block.iden,
                         "text": $block.text, "data": $block.data, "columns": $block.data.opts.columns}))
            ''')

            self.eq('stormblock', valu['type'])
            self.eq(('storm-block',), valu['classes'])
            self.len(32, valu['iden'])
            self.isin(f'iden="{valu["iden"]}"', valu['text'])
            self.isin('## Known tools', valu['text'])
            self.isin('| WEBC2 |', valu['text'])

            # the data keeps the query as written, with the values its variables were bound to
            data = valu['data']
            self.eq('table', data['type'])
            self.eq('risk:threat=$threat -(used)> it:software', data['query'])
            self.len(32, data['vars']['threat'])
            self.eq('storm', data['mode'])
            self.nn(data['updated'])
            # stored in the normalised form, which says what kind of value fills the column
            self.eq([{'name': 'Software', 'type': 'prop', 'prop': 'name'}], data['opts']['columns'])
            self.eq(data['opts']['columns'], valu['columns'])

            # ...and it runs with those values bound, which is what a rebuild does
            nodes = await core.nodes(data['query'], opts={'vars': data['vars']})
            self.len(1, nodes)
            self.eq('it:software', nodes[0].form.name)

    async def test_stormlib_markdown_stormtable_sort(self):
        '''
        A table's rows are ordered by the values behind one column's cells, not by the text they
        display, and the order is stored so a rebuild reproduces it.
        '''
        async with self.getTestCore() as core:

            # addresses whose display strings sort the other way round: lexically 10.0.0.1 and
            # 200.1.1.1 come before 9.9.9.9, and by address they do not
            await core.nodes('[ inet:dns:a=(a.com, 9.9.9.9) ] | spin |'
                             ' [ inet:dns:a=(b.com, 10.0.0.1) ] | spin |'
                             ' [ inet:dns:a=(c.com, 1.2.3.4) ] | spin |'
                             ' [ inet:dns:a=(d.com, 200.1.1.1) ]')

            def _cells(text):
                return [line.split('|')[1].strip() for line in text.split('\n')
                        if line.startswith('|')][2:]

            async def _table(sort):
                return await core.callStorm('''
                    $block = $lib.markdown.stormtable(${ inet:dns:a }, columns=(ip, fqdn), sort=$sort)
                    return(({"text": $block.text, "opts": $block.data.opts}))
                ''', opts={'vars': {'sort': sort}})

            valu = await _table('ip')
            self.eq(['1.2.3.4', '9.9.9.9', '10.0.0.1', '200.1.1.1'], _cells(valu['text']))

            # stored beside the columns, in the shape Optic's table keeps its own sort state in
            self.eq([{'name': 'ip', 'direction': 'asc'}], valu['opts']['sort'])

            valu = await _table({'name': 'ip', 'direction': 'desc'})
            self.eq(['200.1.1.1', '10.0.0.1', '9.9.9.9', '1.2.3.4'], _cells(valu['text']))

            # a decimal string orders by the number it spells, where its text says '10' before '9'
            await core.nodes('[ econ:purchase=(a,) :price=10 ] | spin |'
                             ' [ econ:purchase=(b,) :price=9 ] | spin |'
                             ' [ econ:purchase=(c,) :price=100 ]')

            text = await core.callStorm('''
                return($lib.markdown.stormtable(${ econ:purchase }, columns=(price,), sort=price).text)
            ''')
            self.eq(['9', '10', '100'], _cells(text))

            # a row with nothing in the column is the smallest value: first ascending and last
            # descending, which is where Optic's own table view puts an empty cell
            await core.nodes('[ econ:purchase=(d,) ]')

            async def _prices(direction):
                text = await core.callStorm('''
                    $sort = ({"name": "price", "direction": $direction})
                    return($lib.markdown.stormtable(${ econ:purchase }, columns=(price,), sort=$sort).text)
                ''', opts={'vars': {'direction': direction}})

                return _cells(text)

            self.eq(['', '9', '10', '100'], await _prices('asc'))
            self.eq(['100', '10', '9', ''], await _prices('desc'))

            # a sort naming a column the table does not have is dropped rather than refused, which is
            # what Optic does with a stored sort whose column has gone
            valu = await _table('newp')
            self.eq([{'name': 'newp', 'direction': 'asc'}], valu['opts']['sort'])
            self.eq(_cells((await _table(None))['text']), _cells(valu['text']))

            # ...and a column can be named by position, for a caller holding the columns but not the
            # headers they will be drawn with
            valu = await _table({'index': 0, 'direction': 'desc'})
            self.eq(['200.1.1.1', '10.0.0.1', '9.9.9.9', '1.2.3.4'], _cells(valu['text']))
            self.eq([{'index': 0, 'direction': 'desc'}], valu['opts']['sort'])

            # an index past the end is dropped, the same as a name the table does not have
            valu = await _table({'index': 7})
            self.eq(_cells((await _table(None))['text']), _cells(valu['text']))

            with self.raises(s_exc.BadArg):
                await _table({'name': 'ip', 'index': 0})

            with self.raises(s_exc.BadArg):
                await _table({'index': -1})

            with self.raises(s_exc.BadArg):
                await _table({'index': 'newp'})

            with self.raises(s_exc.BadArg):
                await _table({'name': 'ip', 'direction': 'sideways'})

            with self.raises(s_exc.BadArg):
                await _table({'direction': 'asc'})

            with self.raises(s_exc.BadArg):
                await _table(10)

    async def test_stormlib_markdown_stormtable_sort_column_kinds(self):
        '''
        A column read straight off the node sorts by what it reads: the primary value, a metadata or
        virtual property, or one bound of a tag's interval.
        '''
        async with self.getTestCore() as core:

            def _cells(text, indx=1):
                return [line.split('|')[indx].strip() for line in text.split('\n')
                        if line.startswith('|')][2:]

            async def _table(query, columns, sort, form=None):
                return await core.callStorm('''
                    return($lib.markdown.stormtable($query, columns=$columns, sort=$sort, form=$form).text)
                ''', opts={'vars': {'query': query, 'columns': columns, 'sort': sort, 'form': form}})

            await core.nodes('[ inet:fqdn=b.com +#seen=(2020, 2024) ] | spin |'
                             ' [ inet:fqdn=a.com +#seen=(2022, 2023) ] | spin |'
                             ' [ inet:fqdn=c.com ]')

            form = ({'name': 'fqdn', 'type': 'form'},)
            text = await _table('inet:fqdn:domain=com', form, {'name': 'fqdn', 'direction': 'desc'}, form='inet:fqdn')
            self.eq(['c.com', 'b.com', 'a.com'], _cells(text))

            # the tag's min unless the column picks the max, and a node without the tag sorts first
            cols = (form[0], {'name': 'seen', 'type': 'tag', 'tag': 'seen'})
            text = await _table('inet:fqdn:domain=com', cols, 'seen', form='inet:fqdn')
            self.eq(['c.com', 'b.com', 'a.com'], _cells(text))

            cols = (form[0], {'name': 'seen', 'type': 'tag', 'tag': 'seen', 'index': 1})
            text = await _table('inet:fqdn:domain=com', cols, 'seen', form='inet:fqdn')
            self.eq(['c.com', 'a.com', 'b.com'], _cells(text))

            # .created is the order the nodes were made in
            cols = (form[0], {'name': 'created', 'type': 'meta', 'meta': 'created'})
            text = await _table('inet:fqdn:domain=com', cols, {'name': 'created', 'direction': 'desc'},
                                form='inet:fqdn')
            self.eq(['c.com', 'a.com', 'b.com'], _cells(text))

            # a column assembled rather than read, such as an edge count, sorts by the cell it draws
            await core.nodes('inet:fqdn=b.com [ +(refs)> { [ inet:fqdn=x.net inet:fqdn=y.net ] } ]')
            await core.nodes('inet:fqdn=a.com [ +(refs)> { inet:fqdn=x.net } ]')

            cols = (form[0], {'name': 'refs', 'type': 'edge', 'edge': ('refs',)})
            text = await _table('inet:fqdn:domain=com', cols, {'name': 'refs', 'direction': 'desc'},
                                form='inet:fqdn')
            self.eq(['b.com', 'a.com', 'c.com'], _cells(text))

            # a virt sorts by its value, where the text says 443 before 80
            await core.nodes('[ inet:server=tcp://1.2.3.4:443 inet:server=tcp://1.2.3.4:80'
                             ' inet:server=tcp://1.2.3.4:8080 ]')

            cols = ({'name': 'port', 'type': 'virt', 'virt': 'port'},)
            text = await _table('inet:server', cols, 'port', form='inet:server')
            self.eq(['80', '443', '8080'], _cells(text))

    async def test_stormlib_markdown_stormtable_filters(self):
        '''
        A column filter holds rows back from the table, at build and on every rebuild, so a table
        captured with one keeps meaning what its author saw.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ it:software=(a,) :name=WEBC2 :type=backdoor ] | spin |'
                             ' [ it:software=(b,) :name=GETMAIL :type=exfil ] | spin |'
                             ' [ it:software=(c,) :name=MAPIGET :type=exfil ]')

            def _cells(text):
                return [line.split('|')[1].strip() for line in text.split('\n')
                        if line.startswith('|')][2:]

            async def _table(filters):
                return await core.callStorm('''
                    $cols = (({"name": "Software", "prop": "name"}),
                             ({"name": "Role", "prop": "type"}))
                    $block = $lib.markdown.stormtable(${ it:software }, columns=$cols,
                                                      sort=Software, filters=$filters)
                    return(({"text": $block.text, "opts": $block.data.opts}))
                ''', opts={'vars': {'filters': filters}})

            valu = await _table(({'name': 'Role', 'hide': ('exfil',)},))
            self.eq(['WEBC2'], _cells(valu['text']))

            # stored beside the columns, so the rebuild reads the same answer
            self.eq([{'name': 'Role', 'hide': ['exfil']}], valu['opts']['filters'])

            # ...and the rows it drew is what it says it drew, not what the query yielded
            rows = await core.callStorm('''
                $cols = (({"name": "Software", "prop": "name"}), ({"name": "Role", "prop": "type"}))
                $hide = ({"name": "Role", "hide": ["exfil"]})
                $block = $lib.markdown.stormtable(${ it:software }, columns=$cols, filters=($hide,))
                return($block.refresh())
            ''')
            self.eq(1, rows)

            # a single filter need not be wrapped in a list, and is stored as one
            valu = await _table({'name': 'Role', 'hide': ('exfil',)})
            self.eq(['WEBC2'], _cells(valu['text']))
            self.eq([{'name': 'Role', 'hide': ['exfil']}], valu['opts']['filters'])

            # a column named by position, for a caller holding the columns and not their headers
            valu = await _table(({'index': 1, 'hide': ('backdoor',)},))
            self.eq(['GETMAIL', 'MAPIGET'], _cells(valu['text']))

            # several values, and several columns at once
            valu = await _table(({'name': 'Role', 'hide': ('exfil', 'backdoor')},))
            self.eq([], _cells(valu['text']))

            valu = await _table(({'name': 'Role', 'hide': ('exfil',)},
                                 {'name': 'Software', 'hide': ('WEBC2',)}))
            self.eq([], _cells(valu['text']))

            # a filter naming a column the table does not have is dropped rather than refused, the
            # same as a sort whose column has gone
            valu = await _table(({'name': 'newp', 'hide': ('exfil',)},))
            self.eq(['GETMAIL', 'MAPIGET', 'WEBC2'], _cells(valu['text']))
            self.eq([{'name': 'newp', 'hide': ['exfil']}], valu['opts']['filters'])

            valu = await _table(({'index': 7, 'hide': ('exfil',)},))
            self.eq(['GETMAIL', 'MAPIGET', 'WEBC2'], _cells(valu['text']))

            # an empty cell is a value a column can hold back, which is what a missing one displays as
            await core.nodes('[ it:software=(d,) :name=NONAME ]')
            valu = await _table(({'name': 'Role', 'hide': ('',)},))
            self.notin('NONAME', valu['text'])

            # a value handed over as the number a column of them displays
            await core.nodes('[ econ:purchase=(a,) :price=10 ] | spin | [ econ:purchase=(b,) :price=9 ]')
            text = await core.callStorm('''
                $hide = ({"name": "price", "hide": [10]})
                return($lib.markdown.stormtable(${ econ:purchase }, columns=(price,),
                                                filters=($hide,)).text)
            ''')
            self.eq(['9'], _cells(text))

            for filters in (({'name': 'Role'},),
                            ({'name': 'Role', 'hide': 'exfil'},),
                            ({'name': 'Role', 'index': 1, 'hide': ()},),
                            ({'hide': ()},),
                            ({'index': -1, 'hide': ()},),
                            ({'index': 'newp', 'hide': ()},),
                            (10,)):
                with self.raises(s_exc.BadArg):
                    await _table(filters)

    async def test_stormlib_markdown_stormtable_filters_refresh(self):
        # The filter is the author's, so a rebuild holds the same values back -- but a value the
        # graph grew since is not one of them, and shows.
        async with self.getTestCore() as core:

            await core.nodes('[ it:software=(a,) :name=WEBC2 :type=backdoor ] | spin |'
                             ' [ it:software=(b,) :name=GETMAIL :type=exfil ]')

            valu = await core.callStorm('''
                $cols = (({"name": "Software", "prop": "name"}), ({"name": "Role", "prop": "type"}))
                $hide = ({"name": "Role", "hide": ["exfil"]})

                $doc = $lib.markdown.doc()
                $block = $lib.markdown.stormtable(${ it:software }, columns=$cols, sort=Software,
                                                  filters=($hide,))
                $doc.add($block)

                $before = $doc.text

                [ it:software=(c,) :name=MAPIGET :type=exfil ] | spin |
                [ it:software=(d,) :name=TARSIP :type=recon ] | spin |

                $rows = $block.refresh()

                return(({"before": $before, "after": $doc.text, "rows": $rows}))
            ''')

            self.isin('| WEBC2 |', valu['before'])
            self.notin('GETMAIL', valu['before'])

            # the rebuilt table holds back the same values, so the exfil tools stay out
            self.notin('GETMAIL', valu['after'])
            self.notin('MAPIGET', valu['after'])

            # ...and a role nobody filtered arrives, rather than being held back for not having been
            # there when the filter was set
            self.isin('| TARSIP |', valu['after'])
            self.isin('| WEBC2 |', valu['after'])
            self.eq(2, valu['rows'])

    async def test_stormlib_markdown_stormtable_sort_refresh(self):
        # The order is the author's, so a rebuild puts the rows back in it rather than in whatever
        # order the query lifts them next.
        async with self.getTestCore() as core:

            await core.nodes('[ inet:dns:a=(a.com, 9.9.9.9) ] | spin | [ inet:dns:a=(c.com, 1.2.3.4) ]')

            # the block rebuilds itself in the same runtime that built it, which is where its data
            # lives -- a parsed body carries none, so it is not the thing to refresh
            valu = await core.callStorm('''
                $doc = $lib.markdown.doc()
                $block = $lib.markdown.stormtable(${ inet:dns:a }, columns=(ip,), sort=ip)
                $doc.add($block)

                $before = $doc.text

                // a row that lifts in the middle and sorts to the end
                [ inet:dns:a=(b.com, 250.1.1.1) ]
                spin |

                $block.refresh()
                return(({"before": $before, "after": $doc.text}))
            ''')

            self.lt(valu['before'].index('1.2.3.4'), valu['before'].index('9.9.9.9'))

            after = valu['after']
            self.lt(after.index('1.2.3.4'), after.index('9.9.9.9'))
            self.lt(after.index('9.9.9.9'), after.index('250.1.1.1'))

    async def test_stormlib_markdown_table_sort(self):
        # A plain table has only its cell text to order by, and sorting never rewrites a cell.
        async with self.getTestCore() as core:

            text = await core.callStorm('''
                $tabl = $lib.markdown.table(("Name", "N"))
                $tabl.addRows((("beta", "2"), ("alpha", "10"), ("gamma", "1")))
                $tabl.sort(Name)
                return($tabl.text)
            ''')
            self.eq(['alpha', 'beta', 'gamma'],
                    [line.split('|')[1].strip() for line in text.split('\n')][2:])

            # ...and the header row is not one of the rows it orders
            self.true(text.startswith('| Name | N |\n| --- | --- |\n'))

            text = await core.callStorm('''
                $tabl = $lib.markdown.table(("Name", "N"))
                $tabl.addRows((("beta", "2"), ("alpha", "10")))
                $tabl.sort(Name, direction=desc)

                // a row added after a sort is appended, as a row always is
                $tabl.addRow(("aaa", "3"))
                return($tabl.text)
            ''')
            self.eq(['beta', 'alpha', 'aaa'],
                    [line.split('|')[1].strip() for line in text.split('\n')][2:])

            # a column whose cells all read as numbers orders by the number
            text = await core.callStorm('''
                $tabl = $lib.markdown.table(("Name", "Count"))
                $tabl.addRows((("beta", "2"), ("alpha", "10"), ("gamma", "1")))
                $tabl.sort(Count)
                return($tabl.text)
            ''')
            self.eq(['1', '2', '10'], [line.split('|')[2].strip() for line in text.split('\n')][2:])

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.markdown.table(("A",)).sort(A, direction=sideways))')

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.markdown.table(("A",)).sort(newp))')

    async def test_stormlib_markdown_stormtable_refresh(self):

        async with self.getTestCore() as core:

            await core.nodes('[ risk:threat=(apt1, t) :name=APT1 :tag=t.apt1 ]'
                             ' [ +(used)> { [ it:software=(t, webc2) :name=WEBC2 ] } ]')

            # the query re-runs with its stored vars bound, in a fresh runtime, and the block is
            # rebuilt where it stands: same iden, same title, same position
            valu = await core.callStorm('''
                $threat = (null)
                risk:threat:name=APT1
                $threat = $node
                spin |

                $doc = $lib.markdown.doc()
                $doc.add($lib.markdown.paragraph(before))
                $block = $lib.markdown.stormtable(${ risk:threat=$threat -(used)> it:software },
                                                  columns=(({"name": "Software", "prop": ":name"}),),
                                                  title="Known tools",
                                                  vars=({"threat": $threat.repr()}))
                $doc.add($block)

                risk:threat:name=APT1 [ +(used)> { [ it:software=(t, getmail) :name=GETMAIL ] } ]
                spin |

                $count = $block.refresh()
                return(({"count": $count, "iden": $block.iden, "md": $doc.text}))
            ''')

            self.eq(2, valu['count'])
            self.isin('| WEBC2 |', valu['md'])
            self.isin('| GETMAIL |', valu['md'])
            self.isin('## Known tools', valu['md'])
            self.isin(f'iden="{valu["iden"]}"', valu['md'])
            self.true(valu['md'].startswith('before\n\n'))

            # A rebuild may never edit the graph, whatever the caller's own runtime allows: a stored
            # query that tries is refused rather than quietly writing.
            with self.raises(s_exc.IsReadOnly):
                await core.callStorm('''
                    $block = $lib.markdown.stormtable(${ it:software }, title=T)
                    $data = $block.data
                    $data.query = "[ it:software=(t, evil) :name=EVIL ]"
                    $block.data = $data
                    $block.refresh()
                ''')

            self.len(0, await core.nodes('it:software:name=EVIL'))

            # a block with nothing to re-run, a kind that does not rebuild, and a lookup query (which
            # is raw values rather than Storm) each say so
            for data in ({'type': 'table'},
                            {'type': 'table', 'query': 'it:software', 'mode': 'lookup'}):
                with self.raises(s_exc.BadArg):
                    await core.callStorm('''
                        $block = $lib.markdown.stormtable(${ it:software })
                        $block.data = $data
                        $block.refresh()
                    ''', opts={'vars': {'data': data}})

            # a caller's own fence vocabulary is kept, since a document format is not core's to name
            valu = await core.callStorm('''
                $block = $lib.markdown.stormtable(${ it:software }, classes=(story-table,),
                                                  iden=$iden)
                return($block.text)
            ''', opts={'vars': {'iden': 'd' * 32}})
            self.true(valu.startswith('::: {.story-table iden="' + 'd' * 32 + '"}'))

            # a query given as a string works too, for a caller that built it itself
            valu = await core.callStorm('''
                $block = $lib.markdown.stormtable("it:software:name=WEBC2")
                return($block.text)
            ''')
            self.isin('| it:software |', valu)

    async def test_stormlib_markdown_stormblock_refresh_kinds(self):

        async with self.getTestCore() as core:

            body = '::: {.storm-chart iden=abc}\nchart\n:::\n'

            # a kind core does not rebuild says so, rather than rebuilding it as a table
            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    $doc = $lib.markdown.parse($body)
                    $block = $doc.blocks.0
                    $block.data = ({"type": "chart", "query": "inet:fqdn"})
                    $block.refresh()
                ''', opts={'vars': {'body': body}})

    async def test_stormlib_markdown_doc_node_open(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ] [ inet:fqdn=bad.net +#suspect ]')
            await core.nodes('[ meta:story=* :id=abc :title="Triage" :body="# Triage\\n" ]')

            # content goes through the body, which is a markdown:doc like any other
            valu = await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                $doc.add($lib.markdown.heading('Infrastructure', (2)))
                $doc.add($lib.markdown.paragraph('Two domains stood out.'))
                return(({"pending": $doc.text, "stored": $doc.node.props.body}))
            ''')
            # a pending edit is invisible on the node until save
            self.eq('# Triage\n\n## Infrastructure\n\nTwo domains stood out.', valu['pending'])
            self.eq('# Triage\n', valu['stored'])

            valu = await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                $doc.add($lib.markdown.heading('Infrastructure', (2)))
                $doc.save()
                return($doc.orphans())
            ''')
            self.eq([], valu)

            nodes = await core.nodes('meta:story:id=abc')
            self.eq('# Triage\n\n## Infrastructure', nodes[0].get('body')[1])

            # the interface that declares `updated` is what makes the stamp possible, and a body
            # change is what makes it right
            self.nn(nodes[0].get('updated'))

            # a form that does not implement doc:document is not a document, and says so
            with self.raises(s_exc.BadArg):
                await core.callStorm('inet:fqdn=evil.com $lib.markdown.load($node)')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.markdown.load("not a node")')

    async def test_stormlib_markdown_doc_node_blockdata(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ] [ inet:fqdn=bad.net +#suspect ]')
            await core.nodes('[ meta:story=* :id=abc :title=T ]')

            # a storm block's data is written by save, under the iden it belongs to
            valu = await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                $block = $lib.markdown.stormtable(${ inet:fqdn#suspect },
                                                  columns=(({"name": "Domain", "type": "form"}),),
                                                  title="Suspect domains")
                $doc.add($block)
                $doc.save()
                return(({"iden": $block.iden, "stored": $doc.node.data.list(), "md": $doc.text}))
            ''')

            self.isin('| evil.com |', valu['md'])
            # nodedata comes back as (name, valu) pairs, named for the block's iden
            self.len(1, valu['stored'])
            stored = dict(valu['stored'])
            data = stored[f'md:block:{valu["iden"]}']
            self.eq('table', data['type'])
            self.eq('inet:fqdn#suspect', data['query'])

            # ...and it comes back attached to the block when the document is opened again, which is
            # what lets a refresh work with nothing else in hand
            valu = await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                for $block in $doc.blocks {
                    if ($block.type = "stormblock") {
                        return(({"iden": $block.iden, "query": $block.data.query}))
                    }
                }
            ''')
            self.len(32, valu['iden'])
            self.eq('inet:fqdn#suspect', valu['query'])

            # a refresh rebuilds it in place from what was stored
            await core.nodes('[ inet:fqdn=third.org +#suspect ]')
            valu = await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                for $block in $doc.blocks {
                    if ($block.type = "stormblock") { $block.refresh() }
                }
                $doc.save()
                return($doc.text)
            ''')
            self.isin('| third.org |', valu)
            self.isin('## Suspect domains', valu)

            # dropping the block from the body leaves its data orphaned, and save reports that
            # rather than deciding what to do about it
            valu = await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                for $block in $doc.blocks {
                    if ($block.type = "stormblock") { $doc.blocks.rem($block) }
                }
                $doc.save()
                return(({"orphans": $doc.orphans(), "stored": $doc.node.data.list()}))
            ''')
            self.len(1, valu['orphans'])
            # still stored: removing it is policy, and policy is the caller's
            self.len(1, valu['stored'])

            nodes = await core.nodes('meta:story:id=abc')
            self.notin('story', nodes[0].get('body')[1])

    async def test_stormlib_markdown_table_refresh_keeps_its_form(self):
        # A table's stored query is not always a lift of one form -- what a reader typed in a query bar
        # may yield far more than the table they built from it -- so a rebuild projects the rows the
        # table is of and drops the rest. Without it, a column naming a prop of the stored form raises
        # on the first node that does not have it.
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com ] | spin')
            await core.nodes('[ it:software=(tool, webc2) :name=WEBC2 ] | spin')

            valu = await core.callStorm('''
                $cols = (({"name": "Domain", "type": "form"}), ({"name": "Zone", "prop": "zone"}))
                $block = $lib.markdown.stormtable(${ inet:fqdn }, columns=$cols, title=Domains)

                // ...and then the query it stores turns out to be the broader lift the reader ran
                $data = $block.data
                $data.template = ".created"
                $data.query = ".created"
                $block.data = $data

                $rows = $block.refresh()

                return(({"rows": $rows, "md": $block.text}))
            ''')

            # every fqdn the broader query yielded, and nothing of the other form
            self.isin('| evil.com | evil.com |', valu['md'])
            self.isin('| com |  |', valu['md'])
            self.notin('WEBC2', valu['md'])

            # ...and the count is what the block shows, not what the query produced
            self.eq(2, valu['rows'])

            # There is no such thing as a table that never knew one form: a query yielding several is
            # refused at build time, so the filter is never absent by accident.
            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    return($lib.markdown.stormtable(${ inet:fqdn it:software }, title=Everything).valu)
                ''')

            # Named, the filter applies on the build as well, so what a caller sees built is what a
            # refresh reproduces rather than a wider table that narrows on its first rebuild.
            valu = await core.callStorm('''
                $block = $lib.markdown.stormtable(${ inet:fqdn it:software }, form=it:software,
                                                  columns=(({"name": "Software", "prop": "name"}),))
                return(({"built": $block.text, "rows": $block.refresh(), "after": $block.text}))
            ''')
            self.isin('WEBC2', valu['built'])
            self.notin('evil.com', valu['built'])
            self.eq(1, valu['rows'])
            self.eq(valu['built'], valu['after'])

    async def test_stormlib_markdown_block_as_a_value(self):
        # A block is a Storm value as well as an object: it prints as its source, and it compares equal
        # to itself and to that source -- which is what makes `$doc.blocks.rem($block)` and
        # `$doc.blocks.index($block)` work on a list of them.
        async with self.getTestCore() as core:

            text = '# One\n\nTwo.\n'

            msgs = await core.stormlist('''
                $doc = $lib.markdown.parse($text)
                $lib.print($doc)
                $lib.print($doc.blocks.0)
            ''', opts={'vars': {'text': text}})

            self.stormIsInPrint('# One', msgs)
            self.stormIsInPrint('Two.', msgs)

            valu = await core.callStorm('''
                $doc = $lib.markdown.parse($text)

                $head = $doc.blocks.0
                $same = $doc.blocks.0
                $other = $doc.blocks.1

                return(({"self": ($head = $same), "other": ($head = $other),
                         "source": ($head = "# One"), "nothing": ($head = (null)),
                         "byindx": ($doc.blocks.index((1)) = $other),
                         "has": $doc.blocks.has($head), "rem": $doc.blocks.rem($other)}))
            ''', opts={'vars': {'text': text}})

            # the same block, and a different one
            self.true(valu['self'])
            self.false(valu['other'])

            # ...and its own source, while a value of another type is simply not equal to it
            self.true(valu['source'])
            self.false(valu['nothing'])

            # ...which is what the list operations lean on: `index()` hands a block back, `has()` finds
            # one, and `rem()` takes one out of the document
            self.true(valu['byindx'])
            self.true(valu['has'])
            self.true(valu['rem'])

            # a paragraph's text is settable, like every block's own value
            valu = await core.callStorm('''
                $doc = $lib.markdown.parse($text)
                $doc.blocks.0.valu = $para
                return($doc.text)
            ''', opts={'vars': {'text': 'One.\n', 'para': 'Two, with\nnewlines collapsed.'}})
            self.eq('Two, with newlines collapsed.\n', valu)

    async def test_stormlib_markdown_column_defaults(self):
        # A column says as little as it needs to. What it leaves out is defaulted from what it does say,
        # and the header a table shows when a column has no name is the thing it projects.
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ] | spin')
            await core.nodes('[ risk:threat=(a,) :name=APT1 ] | spin')
            await core.nodes('risk:threat [ +(used)> { inet:fqdn=evil.com } ] | spin')

            # a column with a name and nothing else names its own prop
            valu = await core.callStorm('''
                $cols = (({"name": "zone"}),)
                return($lib.markdown.stormtable(${ inet:fqdn#suspect }, columns=$cols).valu)
            ''')
            self.isin('| zone |', valu)
            self.isin('| evil.com |', valu)

            # ...and a column given as a bare string is that same column, spelled shorter
            valu = await core.callStorm('''
                $block = $lib.markdown.stormtable(${ inet:fqdn#suspect }, columns=(zone,))
                return(($block.valu, $block.data.opts.columns))
            ''')
            self.isin('| zone |', valu[0])
            self.isin('| evil.com |', valu[0])
            self.eq([{'name': 'zone', 'type': 'prop', 'prop': 'zone'}], valu[1])

            # a prop path spells out which kind of value it means: `*` is the primary value, a leading
            # dot is metadata, and a leading colon is just a prop
            valu = await core.callStorm('''
                $cols = (({"name": "Domain", "type": "form"}),
                         ({"name": "Added", "prop": ".created"}),
                         ({"name": "Zone", "prop": ":zone"}))

                $block = $lib.markdown.stormtable(${ inet:fqdn#suspect }, columns=$cols)
                return(($block.valu, $block.data.opts.columns))
            ''')

            self.eq([{'name': 'Domain', 'type': 'form'},
                     {'name': 'Added', 'type': 'meta', 'meta': 'created'},
                     {'name': 'Zone', 'type': 'prop', 'prop': 'zone'}], valu[1])

            self.isin('| Domain | Added | Zone |', valu[0])
            self.isin('| evil.com |', valu[0])

            # the primary value under a name of the caller's own, which is the column a `prop` of the
            # row form used to spell as well
            valu = await core.callStorm('''
                $cols = (({"name": "Domain", "type": "form"}),)
                $block = $lib.markdown.stormtable(${ inet:fqdn#suspect }, columns=$cols)
                return(($block.valu, $block.data.opts.columns))
            ''')
            self.isin('| evil.com |', valu[0])
            self.eq([{'name': 'Domain', 'type': 'form'}], valu[1])

            # an edge column with no name is headed by the walk it counts, in the direction it counts it
            valu = await core.callStorm('''
                $out = ("used", "inet:fqdn")
                $inb = ("used", "risk:threat", (true))

                $cols = (({"type": "edge", "edge": $out}),)
                $frm = $lib.markdown.stormtable(${ risk:threat }, columns=$cols).valu

                $cols = (({"type": "edge", "edge": $inb}),)
                $tos = $lib.markdown.stormtable(${ inet:fqdn#suspect }, columns=$cols).valu

                return(($frm, $tos))
            ''')
            # `>` is escaped on the way into a GFM cell, which is what makes it render as `>` rather
            # than get eaten as markup. The target comes with the verb, as it does in the table
            # view, so the two agree on what an unnamed edge column is headed with.
            self.isin('| -(used)&gt; inet:fqdn |', valu[0])
            self.isin('| &lt;(used)- risk:threat |', valu[1])

            # a path variable can name its type, so the cell reprs through it rather than str()-ing
            valu = await core.callStorm('''
                $cols = (({"name": "Rank", "type": "pathvar", "pathvar": "rank", "pathvartype": "int"}),)
                return($lib.markdown.stormtable(${ inet:fqdn#suspect $rank=(42) }, columns=$cols).valu)
            ''')
            self.isin('| Rank |', valu)
            self.isin('| 42 |', valu)

            # ...and a path variable the row never had is an empty cell, not a missing column
            valu = await core.callStorm('''
                $cols = (({"name": "Why", "type": "pathvar", "pathvar": "why"}),)
                return($lib.markdown.stormtable(${ inet:fqdn#suspect }, columns=$cols).valu)
            ''')
            self.isin('| Why |', valu)

            # a list path variable writes the way an array prop does -- storm's own tuple spelling,
            # which is what the table view shows -- rather than as a python list
            valu = await core.callStorm('''
                $cols = (({"name": "Seen", "type": "pathvar", "pathvar": "seen"}),)
                return($lib.markdown.stormtable(${ inet:fqdn#suspect $seen=(alpha, beta) },
                                                columns=$cols).valu)
            ''')
            self.isin('| (alpha, beta) |', valu)

            # an embed walks a pivot path, and a path which does not resolve is an empty cell rather
            # than an error: a tld has no `:domain` to walk to
            valu = await core.callStorm('''
                $cols = (({"name": "Domain", "type": "form"}),
                         ({"name": "Parent zone", "type": "embed", "embed": "domain::zone"}))
                return($lib.markdown.stormtable(${ inet:fqdn }, columns=$cols).valu)
            ''')
            # neither resolves here (`evil.com`'s own zone is itself, and a tld has no `:domain` at
            # all), which is an empty cell rather than an error
            self.isin('| evil.com |  |', valu)
            self.isin('| com |  |', valu)

            # ...and a column which is neither a name nor a definition is a caller mistake
            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    $cols = ((42),)
                    $lib.markdown.stormtable(${ inet:fqdn }, columns=$cols)
                ''')

            # A column dict carrying only how it is drawn names no source at all: it defaults to a
            # prop column with no prop, which is the same mistake said in the column's own words.
            with self.raises(s_exc.BadArg) as errs:
                await core.callStorm('''
                    $cols = (({"justify": "left"}),)
                    $lib.markdown.stormtable(${ inet:fqdn }, columns=$cols)
                ''')

            self.isin('requires a "prop"', errs.exception.errinfo.get('mesg'))

            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    $cols = (({"type": "prop"}),)
                    $lib.markdown.stormtable(${ inet:fqdn }, columns=$cols)
                ''')

    async def test_stormlib_markdown_doc_edges(self):
        # The document API's own corners: a document form with no `:id`, and nodedata that is not a
        # block's.
        async with self.getTestCore() as core:

            # a document is the node it was loaded from, whatever else that node does or does not
            # carry -- version and id are the caller's business, not this API's
            await core.nodes('[ doc:policy=(noid,) :title="No id" :body="# One" ] | spin')

            self.eq('# One', await core.callStorm(
                'return($lib.markdown.load({ doc:policy:title="No id" }).text)'))

            # nodedata which is not a block's is not an orphan of one
            await core.nodes('[ meta:story=* :id=abc :title=T ] | spin')

            valu = await core.callStorm('''
                $story = { meta:story:id=abc }
                $story.data.set(unrelated, ({"keep": "me"}))

                $doc = $lib.markdown.load($story)
                $doc.add($lib.markdown.stormtable(${ meta:story }, title=T))
                $doc.save()

                $doc.blocks.pop()
                $doc.save()

                return(({"orphans": $doc.orphans(), "kept": $story.data.get(unrelated)}))
            ''')

            self.len(1, valu['orphans'])
            self.eq({'keep': 'me'}, valu['kept'])

            # a document opened from another document's node is the same document: `$doc.node` hands
            # back a node object, and `doc()` takes one as readily as it takes the pipeline's
            valu = await core.callStorm('''
                $doc = $lib.markdown.load({ meta:story:id=abc })
                $again = $lib.markdown.load($doc.node)
                return(($doc.text = $again.text))
            ''')
            self.true(valu)

    async def test_stormlib_markdown_block_nodes(self):
        # `nodes()` is what a kind core has no renderer for needs: the query re-run with the block's
        # stored vars bound, read-only, handed back as nodes. It does not care what `type` says, which
        # is the whole point -- the owner supplies only the drawing.
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ] | spin')
            await core.nodes('[ inet:fqdn=bad.net +#suspect ] | spin')

            # a kind core cannot render still hands over its rows
            valu = await core.callStorm('''
                $block = $lib.markdown.div((storm-mermaid,), attrs=({"iden": $lib.guid()}))
                $block.data = ({"type": "mermaid", "query": "inet:fqdn#suspect"})

                $names = ([])
                for $n in $block.nodes() { $names.append($n.repr()) }

                $sorted = ([])
                for $name in $lib.sorted($names) { $sorted.append($name) }

                return(({"names": $sorted, "able": $block.refreshable}))
            ''')

            self.eq(['bad.net', 'evil.com'], valu['names'])

            # ...while `refresh()` still refuses it, because that is a question about rendering
            self.false(valu['able'])

            # the stored vars are bound, the same way refresh() binds them
            valu = await core.callStorm('''
                $block = $lib.markdown.div((storm-chart,), attrs=({"iden": $lib.guid()}))
                $block.data = ({"type": "chart", "query": "inet:fqdn#$tag", "vars": ({"tag": "suspect"})})
                return($lib.len($block.nodes()))
            ''')
            self.eq(2, valu)

            # ...and it cannot edit the graph, whatever the caller's runtime allows
            with self.raises(s_exc.IsReadOnly):
                await core.callStorm('''
                    $block = $lib.markdown.div((storm-chart,), attrs=({"iden": $lib.guid()}))
                    $block.data = ({"type": "chart", "query": "[ inet:fqdn=made.by.nodes ]"})
                    $block.nodes()
                ''')

            self.len(0, await core.nodes('inet:fqdn=made.by.nodes'))

            # a block with no data, and a lookup-mode query, refuse for the same reasons refresh() does
            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('''
                    $built = $lib.markdown.stormtable(${ inet:fqdn }, iden=$iden, title=T)
                    $lib.markdown.parse($built.text).block($iden).nodes()
                ''', opts={'vars': {'iden': 'a' * 32}})

            self.isin('has no data to rebuild from', cm.exception.get('mesg'))

            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('''
                    $block = $lib.markdown.div((storm-table,), attrs=({"iden": $lib.guid()}))
                    $block.data = ({"type": "table", "query": "evil.com", "mode": "lookup"})
                    $block.nodes()
                ''')

            self.isin('lookup-mode', cm.exception.get('mesg'))

            # a table can use it too: same rows core would project, before projecting them
            valu = await core.callStorm('''
                $block = $lib.markdown.stormtable(${ inet:fqdn#suspect }, title=T)
                return(($lib.len($block.nodes()), $block.refresh()))
            ''')
            self.eq((2, 2), valu)

            # ...and it is readonly safe, since it only reads
            valu = await core.callStorm('''
                $block = $lib.markdown.div((storm-mermaid,), attrs=({"iden": $lib.guid()}))
                $block.data = ({"type": "mermaid", "query": "inet:fqdn#suspect"})
                return($lib.len($block.nodes()))
            ''', opts={'readonly': True})
            self.eq(2, valu)

    async def test_stormlib_markdown_block_query_return(self):
        # a `return()` ends the block's own query: it is not a way out of the function building or
        # refreshing the block, and what the query made before it is what the block holds
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ] | spin')

            valu = await core.callStorm('''
                function build() {
                    $block = $lib.markdown.stormprint(${ $lib.print(early) return((99)) $lib.print(late) })
                    return(($block.text))
                }
                return($build())
            ''')
            self.isin('early', valu)
            self.notin('late', valu)

            # a table's rows are yielded nodes, and a `return()` comes before its node is, so the
            # table is empty -- but it is still the table the function goes on to return
            valu = await core.callStorm('''
                function build() {
                    $block = $lib.markdown.stormtable(${ inet:fqdn#suspect return((77)) }, form=inet:fqdn, title=T)
                    return(($block.text))
                }
                return($build())
            ''')
            self.isin('## T', valu)

            # ...and a refresh, the block's and the document's, rebuilds rather than leaving early
            valu = await core.callStorm('''
                function refresh() {
                    $doc = $lib.markdown.doc()
                    $doc.add($lib.markdown.stormprint(${ if (true) { $lib.print(early) return() } $lib.print(late) }))
                    $doc.add($lib.markdown.stormtable(${ inet:fqdn#suspect }, title=T))
                    $rows = $doc.blocks.0.refresh()
                    $done = $doc.refresh()
                    return(({"rows": $rows, "done": $done, "md": $doc.text}))
                }
                return($refresh())
            ''')
            self.eq(1, valu['rows'])
            self.len(2, valu['done']['rebuilt'])
            self.eq({}, valu['done']['failed'])
            self.isin('early', valu['md'])
            self.isin('evil.com', valu['md'])

    async def test_stormlib_markdown_block_data_sources(self):
        # A block's data lives outside the markdown, so parsing the markdown does not recover it.
        # Three things put it in a caller's hands, and this pins all three plus what the fourth case
        # (text alone) does instead of pretending.
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ] [ inet:fqdn=bad.net +#suspect ] | spin')
            await core.nodes('[ meta:story=* :id=abc :title=T ] | spin')

            cols = ({'name': 'Domain', 'type': 'form'},)

            # 1. built in this runtime: the data is on the block that was just built
            valu = await core.callStorm('''
                $block = $lib.markdown.stormtable(${ inet:fqdn#suspect }, columns=$cols, title=Domains)
                return(({"data": $block.data, "able": $block.refreshable, "md": $block.text}))
            ''', opts={'vars': {'cols': cols}})

            self.eq('table', valu['data']['type'])
            self.true(valu['able'])

            body = valu['md']

            # 2. saved to a node, then reopened from it: `save` wrote the data to nodedata, and
            # `doc(node=...)` reads it back onto the block it belongs to
            await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                $doc.add($lib.markdown.stormtable(${ inet:fqdn#suspect }, columns=$cols, title=Domains))
                $doc.save()
            ''', opts={'vars': {'cols': cols}})

            valu = await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                $block = $doc.blocks.0
                return(({"query": $block.data.query, "able": $block.refreshable}))
            ''')
            self.eq('inet:fqdn#suspect', valu['query'])
            self.true(valu['able'])

            # 3. the same markdown parsed with no node behind it: the block is there and keeps its
            # iden, but there is nowhere to read its data back from, so it says it cannot rebuild
            # rather than rebuilding something else
            valu = await core.callStorm('''
                $doc = $lib.markdown.parse($body)
                $block = $doc.blocks.0
                return(({"data": $block.data, "cols": $block.data.opts.columns, "able": $block.refreshable,
                         "iden": $block.iden}))
            ''', opts={'vars': {'body': body}})

            self.eq({}, valu['data'])
            self.false(valu['able'])

            # no data at all, rather than a kind with no columns -- reading a render option off an
            # unloaded block gives null, which is the honest answer
            self.none(valu['cols'])

            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('''
                    $doc = $lib.markdown.parse($body)
                    $doc.blocks.0.refresh()
                ''', opts={'vars': {'body': body}})

            # ...and it says the cause, rather than reporting the type it could not find as a renderer
            self.isin('has no data to rebuild from', cm.exception.get('mesg'))

            # ...and a caller holding that data out of band hands it over, keyed by the iden the
            # markdown does carry -- which is what makes the block addressable at all
            valu = await core.callStorm('''
                $doc = $lib.markdown.parse($body)
                $block = $doc.blocks.0
                $block.data = ({"type": "table", "query": "inet:fqdn#suspect", "columns": $cols})
                $count = $block.refresh()
                return(({"count": $count, "able": $block.refreshable, "iden": $block.iden,
                         "md": $doc.text}))
            ''', opts={'vars': {'body': body, 'cols': cols}})

            self.eq(2, valu['count'])
            self.true(valu['able'])
            self.isin('| evil.com |', valu['md'])
            self.isin(f'iden="{valu["iden"]}"', valu['md'])

    async def test_stormlib_markdown_stormnode(self):

        async with self.getTestCore() as core:

            await core.nodes('''
                [ inet:fqdn=evil.com +#cno.mal=(2021, 2022) +#aka.apt1 ]
            ''')

            # a single node as a flipped name/value table: what it is, its value, then its props,
            # its metadata and its tags
            valu = await core.callStorm('''
                inet:fqdn=evil.com
                $blk = $lib.markdown.stormnode($node, title="The domain")
                return(({"iden": $blk.iden, "classes": $blk.classes, "text": $blk.text,
                         "data": $blk.data}))
            ''')

            self.len(32, valu['iden'])
            self.eq(('storm-block',), valu['classes'])
            self.eq('node', valu['data']['type'])
            self.eq('inet:fqdn="evil.com"', valu['data']['query'])

            text = valu['text']
            self.isin('## The domain', text)
            self.isin('| name | value |', text)
            self.isin('| form | inet:fqdn |', text)
            self.isin('| inet:fqdn | evil.com |', text)
            self.isin('| :host | evil |', text)
            self.isin('| .created |', text)
            self.isin('| #cno.mal | (2021-01-01T00:00:00Z, 2022-01-01T00:00:00Z) |', text)
            self.isin('| #aka.apt1 | (null, null) |', text)

            # ...and it rebuilds, which is what a table could already do and a node could not
            text = await core.callStorm('''
                inet:fqdn=evil.com
                $doc = $lib.markdown.doc()
                $blk = $lib.markdown.stormnode($node)
                $doc.add($blk)
                inet:fqdn=evil.com [ +#newtag ]
                $doc.block($blk.iden).refresh()
                return($doc.text)
            ''')
            self.isin('| #newtag |', text)

            # a node that has since been deleted leaves the block saying so, rather than rebuilding
            # an empty table that reads as a node with no properties
            await core.nodes('[ inet:fqdn=gone.com ] | spin')

            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('''
                    $blk = (null)
                    inet:fqdn=gone.com
                    $blk = $lib.markdown.stormnode($node)
                    spin |

                    $doc = $lib.markdown.doc()
                    $doc.add($blk)

                    inet:fqdn=gone.com | delnode | spin |

                    $doc.block($blk.iden).refresh()
                ''')
            self.isin('found no node', cm.exception.get('mesg'))

            # a form whose repr does not lift it back has no query to rebuild from, and says so
            # rather than storing one that raises on every refresh
            await core.nodes('[ inet:dns:a=(evil.com, 1.2.3.4) ] | spin')

            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('inet:dns:a $lib.markdown.stormnode($node)')

            self.isin('cannot be lifted by its repr', cm.exception.get('mesg'))
            self.eq('inet:dns:a', cm.exception.get('form'))

            # ...and it takes a node, not a string naming one
            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('$lib.markdown.stormnode("inet:fqdn=evil.com")')

            self.isin('takes a node', cm.exception.get('mesg'))

    async def test_stormlib_markdown_block_row_bound(self):

        async with self.getTestCore() as core:

            # a query is re-run against a graph that has grown since it was written, and the rows go
            # into the document body, so a block that would rebuild enormous refuses instead
            await core.nodes('for $i in $lib.range((10)) { [ inet:fqdn=`{$i}.link` ] }')

            with mock.patch.object(s_markdown, 'BLOCK_MAX_ROWS', 4):
                with self.raises(s_exc.BadArg) as cm:
                    await core.callStorm('return($lib.markdown.stormtable(${ inet:fqdn }).text)')

                self.isin('add a limit to its query', cm.exception.get('mesg'))
                self.eq(4, cm.exception.get('limit'))

                # ...and one sitting exactly on the bound is fine, so the refusal is off-by-none
                valu = await core.callStorm(
                    'return($lib.markdown.stormtable(${ inet:fqdn | limit 4 }).text)')

                # the header and the delimiter are not rows
                rows = [line for line in valu.split('\n')
                        if line.startswith('| ') and '---' not in line]
                self.len(5, rows)

    async def test_stormlib_markdown_doc_block_data_name(self):
        # A block's data is nodedata named for its iden, under one prefix. Not a parameter: a
        # document's blocks are addressed the same way wherever the document lives.
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ]')
            await core.nodes('[ meta:story=* :id=abc :title=T ]')

            iden = await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                $block = $lib.markdown.stormtable(${ inet:fqdn#suspect })
                $doc.add($block)
                $doc.save()
                return($block.iden)
            ''')

            names = await core.callStorm('''
                meta:story:id=abc
                $names = ([])
                // `spin |`: a `for` in a node pipeline yields once per item, so a bare `return`
                // after it hands back the list as it stood on the first nodedata key.
                for ($name, $valu) in $node.data.list() { $names.append($name) }
                spin |
                return($names)
            ''')
            self.eq([f'md:block:{iden}'], sorted(names))

            # ...and it is read back from there, which is what a rebuild needs
            self.eq('inet:fqdn#suspect', await core.callStorm('''
                $doc = $lib.markdown.load({ meta:story:id=abc })
                return($doc.block($iden).data.query)
            ''', opts={'vars': {'iden': iden}}))

            # data under any other name is not this document's, and is not an orphan of it either
            await core.callStorm('''
                meta:story:id=abc
                $node.data.set($name, ({"type": "table", "query": "inet:fqdn"}))
            ''', opts={'vars': {'name': 'newp:block:' + 'a' * 32}})

            self.eq((), tuple(await core.callStorm('''
                return($lib.markdown.load({ meta:story:id=abc }).orphans())
            ''')))

    async def test_stormlib_markdown_doc_node_save_is_idempotent(self):

        async with self.getTestCore() as core:

            await core.nodes('[ meta:story=* :id=abc :title=T :body="# T\\n" ]')

            # a save that changes nothing does not stamp anything either
            first = await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                $doc.add($lib.markdown.paragraph(prose))
                $doc.save()
                return($doc.node.props.updated)
            ''')
            self.nn(first)

            again = await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                $doc.save()
                return(({"orphans": $doc.orphans(), "updated": $doc.node.props.updated}))
            ''')
            self.eq([], again['orphans'])
            self.eq(first, again['updated'])

    async def test_stormlib_markdown_doc_unwrap(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ]')

            # A document built with no node at all is the outbound case: a chat message, a file. Its
            # storm blocks still carry their data in memory, and nothing writes it.
            valu = await core.callStorm('''
                $md = $lib.markdown
                $doc = $md.doc()
                $doc.add($md.heading('Suspect infrastructure', (2)))
                $doc.add($md.stormtable(${ inet:fqdn#suspect }, title="Domains"))

                return(({"fenced": $doc.text, "plain": $doc.unwrap(), "node": $doc.node}))
            ''')

            self.isin('::: {.storm-block', valu['fenced'])
            self.isin('| evil.com |', valu['fenced'])

            # unwrapped: the content survives, the fence does not
            self.notin(':::', valu['plain'])
            self.notin('storm-block', valu['plain'])
            self.isin('## Suspect infrastructure', valu['plain'])
            self.isin('## Domains', valu['plain'])
            self.isin('| evil.com |', valu['plain'])

            # ...and with no node there is nothing to save to, which says so rather than half-working
            self.none(valu['node'])

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.markdown.doc().save()')

            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.markdown.doc().orphans()')

            # a div that is not a storm block carries no data, so its fence is left alone
            valu = await core.callStorm('''
                $md = $lib.markdown
                $doc = $md.parse($body)
                return($doc.unwrap())
            ''', opts={'vars': {'body': '::: {.note}\nCareful.\n:::\n\n'
                                        '::: {.storm-table iden="' + 'a' * 32 + '"}\n| a |\n| - |\n:::\n'}})
            self.isin('::: {.note}', valu)
            self.notin('storm-table', valu)
            self.isin('| a |', valu)

            # a ::: inside a code fence is sample text, not a directive, so unwrapping leaves it
            valu = await core.callStorm('''
                return($lib.markdown.parse($body).unwrap())
            ''', opts={'vars': {'body': '```markdown\n::: {.storm-table iden="'
                                        + 'b' * 32 + '"}\n:::\n```\n'}})
            self.isin('::: {.storm-table', valu)

    async def test_stormlib_markdown_stormtable_form(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ]')
            await core.nodes('[ inet:url="http://evil.com/" +#suspect ]')

            # the form the rows shared, for a consumer that puts them back in a typed view
            valu = await core.callStorm('''
                $block = $lib.markdown.stormtable(${ inet:fqdn#suspect })
                return($block.data.opts.form)
            ''')
            self.eq('inet:fqdn', valu)

            # A mixed lift is refused rather than labelled with whichever arrived first: a table is
            # of one form, its columns name that form's props, and rendering them all gives a table
            # whose columns cannot apply to most of its rows.
            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('return($lib.markdown.stormtable(${ #suspect }).data.opts.form)')

            self.isin('name the one you meant with form=', cm.exception.get('mesg'))
            self.eq(['inet:fqdn', 'inet:url'], cm.exception.get('forms'))

            # ...and naming it settles both which form the table is of and which rows it keeps, on
            # the build as well as on every rebuild
            valu = await core.callStorm('''
                $block = $lib.markdown.stormtable(${ #suspect }, form=inet:url)
                return(({"form": $block.data.opts.form, "text": $block.valu}))
            ''')
            self.eq('inet:url', valu['form'])
            self.isin('http://evil.com/', valu['text'])
            self.notin('| evil.com |', valu['text'])

            # A query yielding nothing has no form to take, and is refused for the same reason a
            # mixed one is: a table with no form never filters on a rebuild and is headed `Node`
            # forever, so a document written before its data exists would carry a permanently
            # mis-shaped table.
            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('return($lib.markdown.stormtable(${ inet:fqdn#newp }).valu)')

            self.isin('no rows to take it from', cm.exception.get('mesg'))

            # ...and naming it builds the empty table the author meant, ready for the rows to arrive
            valu = await core.callStorm('''
                $block = $lib.markdown.stormtable(${ inet:fqdn#newp }, form=inet:fqdn)
                return(({"form": $block.data.opts.form, "text": $block.valu}))
            ''')
            self.eq('inet:fqdn', valu['form'])
            self.eq('| inet:fqdn |\n| --- |', valu['text'])

    async def test_stormlib_markdown_block_without_a_stored_form(self):
        '''A table block stored before a table had to know its form still rebuilds.

        Every table written before `opts.form` became mandatory has none, and so does one the Stories
        editor wrote, which builds its block data itself. Requiring a form on the rebuild turned all
        of them into blocks that could never refresh again -- an empty query or a query that had come
        to yield several forms raised, where both used to render.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#keep ]')
            await core.nodes('[ it:software=(s,) :name=WEBC2 +#keep ]')

            async def rebuild(query):
                return await core.callStorm('''
                    $doc = $lib.markdown.doc()
                    $cols = (({"name": "V", "type": "form"}),)
                    $blk = $lib.markdown.div((storm-table,), attrs=({"iden": $lib.guid()}),
                                             valu="stale")
                    $blk.data = ({"type": "table", "query": $query, "opts": ({"columns": $cols})})
                    $doc.add($blk)
                    $blk.refresh()
                    return($blk.valu)
                ''', opts={'vars': {'query': query}})

            # Nothing to filter to, so it keeps every row -- including a query that has come to span
            # forms. The it:software row shows its guid, since a `*` column is the primary value and
            # a formless table has no form whose props it could have named instead.
            valu = await rebuild('#keep')
            self.isin('| evil.com |', valu)
            self.len(4, valu.split('\n'))

            # ...and an empty result renders an empty table rather than refusing
            self.eq('| V |\n| --- |', await rebuild('inet:fqdn#nope'))

    async def test_stormlib_markdown_stormtable_form_must_be_a_form(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#keep ]')

            # A form= naming nothing used to build a table headed with the typo whose every row was
            # filtered out, for the life of the document, without ever saying why.
            with self.raises(s_exc.NoSuchForm) as cm:
                await core.callStorm('return($lib.markdown.stormtable(${ inet:fqdn#keep }, form=newp.newp).valu)')

            self.isin('which is not a form', cm.exception.get('mesg'))

            # ...and the same for a query that yields nothing, where the typo is even quieter
            with self.raises(s_exc.NoSuchForm):
                await core.callStorm('return($lib.markdown.stormtable(${ inet:fqdn#nope }, form=inet:fdqn).valu)')

            # the primary value is a form column, not a prop of either spelling that looks like it
            for prop in ('*', 'inet:fqdn'):
                with self.raises(s_exc.BadArg) as cm:
                    await core.callStorm('''
                        return($lib.markdown.stormtable(${ inet:fqdn#keep }, form=inet:fqdn,
                                                        columns=(({"name": "fqdn", "prop": $prop}),)).valu)
                    ''', opts={'vars': {'prop': prop}})

                self.isin('{"type": "form"}', cm.exception.get('mesg'))

    async def test_stormlib_markdown_stormtable_form_keeps_subforms(self):
        '''A table is of one form, and a node of a form that inherits it belongs to that table.'''

        async with self.getTestCore() as core:

            await core.nodes('[ inet:server=tcp://1.2.3.4:443 ]')

            # `inet:server` is what `inet:banner:server` is typed as; a form filter that compared
            # names rather than formtypes would drop a subform's rows on the build and on the rebuild.
            valu = await core.callStorm('''
                $blk = $lib.markdown.stormtable(${ inet:server }, form=inet:server)
                return(({"built": $blk.valu, "rows": $blk.nodes()}))
            ''')
            self.isin('tcp://1.2.3.4:443', valu['built'])

    async def test_stormlib_markdown_doc_refresh_contains_a_bad_block(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=cdn.evil.link +#keep ]')

            # A document-wide refresh is not all-or-nothing. A block whose query no longer runs --
            # its node deleted, a prop the form no longer has -- keeps the content it has and warns,
            # so one casualty of a moving graph does not make a document permanently unrefreshable.
            msgs = await core.stormlist('''
                $md = $lib.markdown
                $doc = $md.doc()

                $doc.add($md.stormtable(${ inet:fqdn#keep }, columns=(({"name": "D", "type": "form"}),)))
                $gone = $md.div((storm-node,), attrs=({"iden": $lib.guid()}))
                $gone.data = ({"type": "node", "query": "inet:fqdn=gone.newp"})
                $doc.add($gone)

                $chart = $md.div((storm-chart,), attrs=({"iden": $lib.guid()}), valu="<chart>")
                $chart.data = ({"type": "chart"})
                $doc.add($chart)

                $lib.print($doc.refresh())
                $lib.print($doc.text)
            ''')

            self.stormIsInWarn('could not rebuild: a node storm block found no node', msgs)

            prints = [m[1]['mesg'] for m in msgs if m[0] == 'print']

            # the failure is in the return as well as in a warning, since a callStorm caller never
            # sees a warning
            self.isin('a node storm block found no node', prints[0])

            # ...and the table that can rebuild did
            self.isin('cdn.evil.link', prints[1])

            # the chart is untouched, as it was before: core has no renderer for it
            self.isin('<chart>', prints[1])

            # ...and a stored query that does not parse is the same kind of casualty. It reads like
            # a refusal about the caller -- the parser said no -- but each block carries its own
            # query and is parsed on its own, so one unparsable block took the whole document down
            # and nothing could refresh it again without editing that block.
            msgs = await core.stormlist('''
                $md = $lib.markdown
                $doc = $md.doc()

                $doc.add($md.stormtable(${ inet:fqdn#keep }, columns=(({"name": "D", "type": "form"}),)))

                $bad = $md.div((storm-block,), attrs=({"iden": $lib.guid()}), valu="<stale>")
                $bad.data = ({"type": "node", "query": "inet:fqdn=("})
                $doc.add($bad)

                $lib.print($doc.refresh())
                $lib.print($doc.text)
            ''')

            self.stormIsInWarn('could not rebuild', msgs)

            prints = [m[1]['mesg'] for m in msgs if m[0] == 'print']

            self.isin('failed', prints[0])
            self.isin('cdn.evil.link', prints[1])
            self.isin('<stale>', prints[1])

    async def test_stormlib_markdown_doc_save_confirms_before_writing(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            await visi.addRule((True, ('node', 'add')))
            await visi.addRule((True, ('node', 'prop', 'set')))

            opts = {'user': visi.iden}

            # `node.data.set` is withheld, so the block data cannot be written. A save that wrote the
            # body first would leave a fence in it whose data was never stored: unrebuildable, and
            # indistinguishable from one someone typed by hand.
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    [ doc:report=(perm, 1) :title=T :id=perm ]
                    $md = $lib.markdown
                    $doc = $md.load($node)
                    $doc.add($md.stormtable(${ inet:fqdn }, form=inet:fqdn))
                    $doc.save()
                ''', opts=opts)

            # Nothing was written: no body, and therefore no orphan fence.
            self.none(await core.callStorm('doc:report:id=perm return(:body)'))

    async def test_stormlib_markdown_doc_block_vars(self):
        # A document has no vars of its own: a block carries what it binds, and setting a name
        # across a whole document is one call that writes it onto every storm block.
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#cno.mal ] [ inet:fqdn=bad.net +#aka.apt1 ] | spin')

            # every storm block ends up carrying what was set, and a refresh binds it
            valu = await core.callStorm('''
                $doc = $lib.markdown.doc()
                $doc.add($lib.markdown.heading(Domains, (2)))
                $doc.add($lib.markdown.stormtable("inet:fqdn#$tag", vars=({"tag": "aka.apt1"})))

                $count = $doc.setBlockVars(({"tag": "cno.mal"}))
                $doc.refresh()

                return(({"count": $count, "text": $doc.text, "vars": $doc.blocks.1.vars}))
            ''')
            self.eq(1, valu['count'])
            self.eq({'tag': 'cno.mal'}, valu['vars'])
            self.isin('| evil.com |', valu['text'])
            self.notin('| bad.net |', valu['text'])

            # `set` replaces, so a name the call does not carry is gone from the block
            valu = await core.callStorm('''
                $doc = $lib.markdown.doc()
                $doc.add($lib.markdown.stormtable("inet:fqdn#$tag | limit $limit",
                                                  vars=({"tag": "aka.apt1", "limit": (1)})))
                $doc.setBlockVars(({"tag": "cno.mal"}))
                return($doc.blocks.0.vars)
            ''')
            self.eq({'tag': 'cno.mal'}, valu)

            # ...where `update` leaves what it does not name, which is what re-pointing a document
            # without disturbing a block's own settings needs
            valu = await core.callStorm('''
                $doc = $lib.markdown.doc()
                $doc.add($lib.markdown.stormtable("inet:fqdn#$tag | limit $limit",
                                                  vars=({"tag": "aka.apt1", "limit": (1)})))
                $count = $doc.modBlockVars(({"tag": "cno.mal"}))
                $doc.refresh()
                return(({"count": $count, "vars": $doc.blocks.0.vars, "text": $doc.text}))
            ''')
            self.eq(1, valu['count'])
            self.eq({'tag': 'cno.mal', 'limit': 1}, valu['vars'])
            self.isin('| evil.com |', valu['text'])

            # ...and `pop` takes names off every block
            valu = await core.callStorm('''
                $doc = $lib.markdown.doc()
                $doc.add($lib.markdown.stormtable("inet:fqdn#$tag | limit $limit",
                                                  vars=({"tag": "aka.apt1", "limit": (1)})))
                $count = $doc.popBlockVars((limit, nope))
                return(({"count": $count, "vars": $doc.blocks.0.vars}))
            ''')
            self.eq(1, valu['count'])
            self.eq({'tag': 'aka.apt1'}, valu['vars'])

            # a document of prose has nothing to set, and says so rather than raising
            valu = await core.callStorm(
                'return($lib.markdown.parse($body).setBlockVars(({"tag": "cno.mal"})))',
                opts={'vars': {'body': '# Title\n\nprose\n'}})
            self.eq(0, valu)

            # the vars travel with the blocks, so a refresh a year later binds what the author bound
            await core.nodes('[ meta:story=* :id=abc :title=T ] | spin')
            await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                $doc.add($lib.markdown.stormtable("inet:fqdn#$tag", vars=({"tag": "cno.mal"})))
                $doc.save()
            ''')

            valu = await core.callStorm('''
                meta:story:id=abc
                return($lib.markdown.load($node).blocks.0.vars)
            ''')
            self.eq({'tag': 'cno.mal'}, valu)

            # ...stored with the block's own data, so there is no second key to know about
            names = await core.callStorm('''
                meta:story:id=abc
                $names = ([])
                // `spin |`: a `for` in a node pipeline yields once per item, so a bare `return`
                // after it hands back the list as it stood on the first nodedata key.
                for ($name, $valu) in $node.data.list() { $names.append($name) }
                spin |
                return($names)
            ''')
            self.len(1, names)
            self.true(names[0].startswith(s_markdown.BLOCK_PREFIX))

            # a var a query could never name is refused where it is set rather than at the next save
            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    $doc = $lib.markdown.doc()
                    $doc.add($lib.markdown.stormtable("inet:fqdn", vars=({"tag": "cno.mal"})))
                    $doc.setBlockVars(({"not a name": "x"}))
                ''')

            # ...while a nested value is one a query can iterate or index, and is kept as written
            valu = await core.callStorm('''
                $doc = $lib.markdown.doc()
                $doc.add($lib.markdown.stormprint(${ for $t in $tags { $lib.print($t.name) } }, vars=({"tags": ([])})))
                $doc.setBlockVars(({"tags": ([({"name": "cno.mal"}), ({"name": "cno.threat"})])}))
                $block = $doc.blocks.0
                $block.refresh()
                return(($block.vars, $block.text))
            ''')
            self.eq({'tags': [{'name': 'cno.mal'}, {'name': 'cno.threat'}]}, valu[0])
            self.isin('cno.mal', valu[1])
            self.isin('cno.threat', valu[1])

    async def test_stormlib_markdown_stormtable_default_columns(self):

        async with self.getTestCore() as core:

            await core.nodes('[ entity:contact=* :name=bob :email=bob@vertex.link :type=business ]')
            await core.nodes('[ meta:feed=* :name=vtx :type=osint ]')
            await core.nodes('[ inet:fqdn=evil.com ]')

            # naming no columns takes the ones the form declares, so a table built in Storm shows
            # what the node view shows
            valu = await core.callStorm('''
                $block = $lib.markdown.stormtable(${ entity:contact })
                return(({"text": $block.valu, "columns": $block.data.opts.columns}))
            ''')

            self.isin('| :name | :email | :type |', valu['text'])
            self.isin('| bob | bob@vertex.link | business |', valu['text'])
            self.eq(['prop', 'prop', 'prop'], [col['type'] for col in valu['columns']])
            self.eq(['name', 'email', 'type'], [col['prop'] for col in valu['columns']])

            # ...and a declared column whose path steps through a prop is an embed here, which is
            # the shape difference the two vocabularies have
            valu = await core.callStorm('return($lib.markdown.stormtable(${ meta:feed }).data.opts.columns)')
            self.eq({'name': ':source::name', 'type': 'embed', 'embed': 'source::name'},
                    {k: v for (k, v) in valu[1].items() if k in ('name', 'type', 'embed')})

            # a form declaring none still falls back to one column of primary values
            valu = await core.callStorm('return($lib.markdown.stormtable(${ inet:fqdn=evil.com }).valu)')
            self.isin('| inet:fqdn |', valu)
            self.isin('| evil.com |', valu)

            # a declaration core cannot project is skipped rather than refusing the table
            self.eq([{'type': 'prop', 'prop': 'name'}],
                    s_markdown.displayStormColumns({'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'newp', 'opts': {}},
                    )}))

    async def test_stormlib_markdown_stormblock_build(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ] [ inet:fqdn=bad.net +#suspect ] | spin')

            # the query writes the markdown itself, one print per line
            valu = await core.callStorm('''
                $doc = $lib.markdown.doc()
                $block = $lib.markdown.stormprint(${
                    inet:fqdn#$tag $lib.print(`- {$node.repr()}`)
                }, vars=({"tag": "suspect"}), title=Infrastructure, iden=abc)
                $doc.add($block)
                return(({"md": $doc.text, "iden": $block.iden, "type": $block.type,
                         "classes": $block.classes, "data": $block.data}))
            ''')

            self.eq('abc', valu['iden'])
            self.eq('stormblock', valu['type'])
            self.eq(('storm-block',), valu['classes'])
            self.eq('print', valu['data']['type'])
            self.eq({'tag': 'suspect'}, valu['data']['vars'])
            self.isin('::: {.storm-block iden="abc"}', valu['md'])
            self.isin('## Infrastructure', valu['md'])
            self.isin('- evil.com\n- bad.net', valu['md'])

            # ...and it rebuilds itself, which is what makes it more than a paragraph
            valu = await core.callStorm('''
                $doc = $lib.markdown.doc()
                $block = $lib.markdown.stormprint(${ inet:fqdn#suspect $lib.print($node.repr()) })
                $doc.add($block)
                [ inet:fqdn=new.org +#suspect ] | spin |
                return(($block.refresh(), $doc.text))
            ''')
            self.eq(3, valu[0])
            self.isin('new.org', valu[1])

            # the print messages are the content rather than the caller's own messages
            msgs = await core.stormlist('''
                $lib.markdown.stormprint(${ inet:fqdn#suspect $lib.print(nope) })
            ''')
            self.stormNotInPrint('nope', msgs)

            # a caller's own fence vocabulary is kept, since a document format is not core's to name
            valu = await core.callStorm('''
                return($lib.markdown.stormprint(${ $lib.print(hi) }, classes=(story-print,)).text)
            ''')
            self.true(valu.startswith('::: {.story-print iden="'))

            # ...and it may not edit the graph, whatever the caller's own runtime allows
            with self.raises(s_exc.IsReadOnly):
                await core.callStorm('''
                    $lib.markdown.stormprint(${ [ inet:fqdn=made.by.print ] })
                ''')

            self.len(0, await core.nodes('inet:fqdn=made.by.print'))

    async def test_stormlib_markdown_block_title(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ]')

            # the title a block was built with reads back, and setting it retitles the block
            valu = await core.callStorm('''
                $doc = $lib.markdown.doc()
                $block = $lib.markdown.stormtable(${ inet:fqdn#suspect }, iden=abc, title=Domains)
                $doc.add($block)

                $was = $block.title
                $block.title = 'Suspect domains'

                return(({"was": $was, "now": $block.title, "md": $doc.text}))
            ''')
            self.eq('Domains', valu['was'])
            self.eq('Suspect domains', valu['now'])
            self.isin('## Suspect domains', valu['md'])
            self.isin('| evil.com |', valu['md'])

            # a rebuild keeps the title it finds, so one set here outlives the rows
            valu = await core.callStorm('''
                $doc = $lib.markdown.doc()
                $block = $lib.markdown.stormtable(${ inet:fqdn#suspect }, title=Domains)
                $doc.add($block)
                $block.title = Renamed
                $block.refresh()
                return($block.title)
            ''')
            self.eq('Renamed', valu)

            # a block built without one has none, and null takes one away
            valu = await core.callStorm('''
                $doc = $lib.markdown.doc()
                $bare = $lib.markdown.stormtable(${ inet:fqdn#suspect })
                $titled = $lib.markdown.stormtable(${ inet:fqdn#suspect }, title=Domains)
                $doc.add($bare)
                $doc.add($titled)

                $titled.title = (null)

                return(({"bare": $bare.title, "dropped": $titled.title, "md": $titled.text}))
            ''')
            self.none(valu['bare'])
            self.none(valu['dropped'])
            self.notin('##', valu['md'])
            self.isin('| evil.com |', valu['md'])

            # ...and titling one that has none puts the heading above the rows it already holds
            valu = await core.callStorm('''
                $bare = $lib.markdown.stormtable(${ inet:fqdn#suspect })
                $bare.title = Domains
                return(({"title": $bare.title, "md": $bare.valu}))
            ''')
            self.eq('Domains', valu['title'])
            self.true(valu['md'].startswith('## Domains\n'))
            self.isin('| evil.com |', valu['md'])

    async def test_stormlib_markdown_doc_purge_orphans(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ]')
            await core.nodes('[ meta:story=* :id=abc :title=T :body="# Triage\\n" ] | spin')

            await core.callStorm('''
                $doc = $lib.markdown.load({ meta:story:id=abc })
                $doc.add($lib.markdown.stormtable(${ inet:fqdn#suspect }, title=Domains))
                $doc.save()
            ''')

            # dropping the block leaves its data where it was: a save never destroys one, because a
            # block leaves the body the moment its fence is mistyped
            valu = await core.callStorm('''
                $doc = $lib.markdown.load({ meta:story:id=abc })
                $iden = $doc.blocks.1.iden
                $doc.blocks.pop((1))
                $doc.save()
                $doc = $lib.markdown.load({ meta:story:id=abc })
                return(($iden, $doc.orphans()))
            ''')
            self.eq([valu[0]], valu[1])

            # and the block coming back finds its data exactly where it left it
            valu = await core.callStorm('''
                $doc = $lib.markdown.load({ meta:story:id=abc })
                $doc.add($lib.markdown.stormtable(${ inet:fqdn#suspect }, title=Domains,
                                                  iden=$iden))
                $doc.save()
                $doc = $lib.markdown.load({ meta:story:id=abc })
                return(($doc.orphans(), $doc.block($iden).data.type))
            ''', opts={'vars': {'iden': valu[0]}})
            self.eq(([], 'table'), valu)

            # the sweep is the other half, and it is the caller's to call
            valu = await core.callStorm('''
                $doc = $lib.markdown.load({ meta:story:id=abc })
                $iden = $doc.blocks.1.iden
                $doc.blocks.pop((1))
                $doc.save()
                $doc = $lib.markdown.load({ meta:story:id=abc })
                $gone = $doc.purgeOrphans()
                return(($iden, $gone, $doc.orphans(), $doc.purgeOrphans()))
            ''')
            self.eq([valu[0]], valu[1])
            self.eq([], valu[2])
            self.eq([], valu[3])

            # data stored as null is still a key the sweep removes, rather than one it reports
            # purged and then lists again
            valu = await core.callStorm('''
                meta:story:id=abc
                $node.data.set("md:block:ffffffffffffffffffffffffffffffff", (null))
                $doc = $lib.markdown.load($node)
                return(($doc.orphans(), $doc.purgeOrphans(), $doc.orphans()))
            ''')
            self.eq((['f' * 32], ['f' * 32], []), valu)

    async def test_stormlib_markdown_doc_swallowed_block(self):
        '''
        A storm block that no longer reads as one, because a block above it opens a fence it never
        closes, keeps its data: the text still names it, so fixing the markdown brings it back.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ]')
            await core.nodes('[ meta:story=* :id=abc :title=T :body="# Triage\\n" ] | spin')

            iden = await core.callStorm('''
                $doc = $lib.markdown.load({ meta:story:id=abc })
                $blk = $lib.markdown.stormtable(${ inet:fqdn#suspect }, title=Domains)
                $doc.add($blk)
                $doc.save()
                return($blk.iden)
            ''')

            # written the way the editor writes it: straight to the body, past save()'s check
            body = (await core.nodes('meta:story:id=abc'))[0].get('body')[1]
            await core.nodes('meta:story:id=abc [ :body=$body ]',
                             opts={'vars': {'body': f'::: {{.note}}\n\n{body}'}})

            valu = await core.callStorm('''
                $doc = $lib.markdown.load({ meta:story:id=abc })
                return(({"block": $doc.block($iden), "orphans": $doc.orphans(),
                         "purged": $doc.purgeOrphans(), "data": $doc.node.data.get(`md:block:{$iden}`)}))
            ''', opts={'vars': {'iden': iden}})

            self.none(valu['block'])
            self.eq([], valu['orphans'])
            self.eq([], valu['purged'])
            self.eq('table', valu['data']['type'])

            # ...and once the text no longer names it at all, it is an orphan like any other
            await core.nodes('meta:story:id=abc [ :body="# Triage\\n" ]')
            self.eq([iden], await core.callStorm(
                'return($lib.markdown.load({ meta:story:id=abc }).orphans())'))

    async def test_stormlib_markdown_doc_save_reads_back(self):
        '''
        A save refuses text whose storm blocks would not read back as the ones the document holds,
        rather than storing a body in which a block above swallows them.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ meta:story=* :id=abc :title=T :body="# Triage\\n" ] | spin')

            await core.callStorm('''
                $doc = $lib.markdown.load({ meta:story:id=abc })
                $doc.add($lib.markdown.stormprint(${ $lib.print(hi) }))
                $doc.save()
            ''')

            body = (await core.nodes('meta:story:id=abc'))[0].get('body')[1]

            for block in (
                "$lib.markdown.paragraph('::: {.note}')",
                "$lib.markdown.paragraph('```')",
                "$lib.markdown.paragraph('<!-- draft')",
                '$lib.markdown.heading("ACME\\n::: {.note}")',
            ):
                with self.raises(s_exc.BadArg) as cm:
                    await core.callStorm(f'''
                        $doc = $lib.markdown.load({{ meta:story:id=abc }})
                        $doc.add({block}, indx=(0))
                        $doc.save()
                    ''')
                self.isin('does not read back', cm.exception.get('mesg'))

                # refused before anything was written
                self.eq(body, (await core.nodes('meta:story:id=abc'))[0].get('body')[1])

            # a block's own text, set to one that never closes, is refused the same way
            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    $doc = $lib.markdown.load({ meta:story:id=abc })
                    $doc.blocks.0.text = "```"
                    $doc.save()
                ''')

            # ...while text that reads back differently but loses no storm block is left alone
            await core.callStorm('''
                $doc = $lib.markdown.load({ meta:story:id=abc })
                $doc.add($lib.markdown.heading("ACME\\nCorp"), indx=(0))
                $doc.save()
            ''')

    async def test_stormlib_markdown_table_text_sets_its_columns(self):

        async with self.getTestCore() as core:

            # the columns a constructor was given go with the text they described
            valu = await core.callStorm('''
                $tabl = $lib.markdown.table(([({"name": "A"}), ({"name": "B"})]))
                $tabl.text = "| X | Y | Z |\\n| --- | --- | --- |"
                $tabl.addRow((1, 2, 3))
                return(($tabl.columns, $tabl.rows))
            ''')
            self.eq([{'name': 'X'}, {'name': 'Y'}, {'name': 'Z'}], valu[0])
            self.eq([['1', '2', '3']], valu[1])

    async def test_stormlib_markdown_doc_blocks_outlive_a_clear(self):

        async with self.getTestCore() as core:

            # a `$doc.blocks` taken before a clear() or a new text is still the document's list
            valu = await core.callStorm('''
                $doc = $lib.markdown.parse("# Old")
                $blocks = $doc.blocks

                $doc.clear()
                $blocks.extend(($lib.markdown.paragraph(cleared),))
                $cleared = $doc.text

                $doc.text = "# Newer"
                $blocks.0 = $lib.markdown.paragraph(replaced)

                return(($cleared, $doc.text))
            ''')
            self.eq(('cleared', 'replaced'), valu)

    async def test_stormlib_markdown_doc_clear(self):
        '''
        `clear()` empties a document, for a caller that rebuilds one from scratch rather than
        editing what it wrote last time.
        '''
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ]')
            await core.nodes('[ meta:story=* :id=abc :title=T :body="# Old\\n" ] | spin')

            iden = await core.callStorm('''
                $md = $lib.markdown
                $doc = $md.load({ meta:story:id=abc })

                $blk = $md.stormtable(${ inet:fqdn#suspect }, title='Domains')
                $doc.add($blk)
                $doc.save()

                return($blk.iden)
            ''')

            # everything goes, the lead whitespace with it, and the document chains like `add`
            valu = await core.callStorm('''
                $md = $lib.markdown
                $doc = $md.load({ meta:story:id=abc })

                $doc.clear()

                return(({"text": $doc.text, "blocks": $lib.len($doc.blocks)}))
            ''')
            self.eq({'text': '', 'blocks': 0}, valu)

            # ...and it is a pending edit like any other: nothing reaches the node until save(), so
            # the body still carries the block that was saved above
            body = (await core.nodes('meta:story:id=abc'))[0].get('body')[1]
            self.isin('::: {.storm-block', body)

            # cleared and rebuilt, which is the point of it
            valu = await core.callStorm('''
                $md = $lib.markdown
                $doc = $md.load({ meta:story:id=abc })

                $doc.clear()
                $doc.add($md.heading('Today', (2)))
                $doc.save()

                return($doc.node.props.body)
            ''')
            self.eq('## Today', valu.strip())

            # The block data of what was removed is left where it was written, the same as for any
            # other removal -- and is now an orphan, which is how a caller finds it.
            self.eq((iden,), tuple(await core.callStorm('''
                return($lib.markdown.load({ meta:story:id=abc }).orphans())
            ''')))

    async def test_stormlib_markdown_doc_refresh(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ]')
            await core.nodes('[ meta:story=* :id=abc :title=T :body="# Triage\\n" ] | spin')

            await core.callStorm('''
                $doc = $lib.markdown.load({ meta:story:id=abc })
                $doc.add($lib.markdown.stormtable(${ inet:fqdn#suspect }, title=Domains))
                $doc.add($lib.markdown.paragraph('prose is not refreshable'))
                $blk = $lib.markdown.div(('storm-newpkind',), attrs=({"iden": $lib.guid()}),
                                         valu=held)
                $blk.data = ({"type": "newpkind", "query": "inet:fqdn#suspect"})
                $doc.add($blk)
                $doc.save()
            ''')

            # every block that can rebuild does, and a kind core has no renderer for is skipped
            # rather than taking the whole document down with it
            valu = await core.callStorm('''
                [ inet:fqdn=bad.net +#suspect ] | spin |
                $doc = $lib.markdown.load({ meta:story:id=abc })
                $done = $doc.refresh()
                $doc.save()
                return(($done.rebuilt, $doc.text))
            ''')
            # keyed by iden and valued with the rows it drew, so a document that rebuilt every block
            # with nothing in it can still be told apart from one that rebuilt them full
            self.eq([2], list(valu[0].values()))
            self.len(32, list(valu[0])[0])
            self.isin('bad.net', valu[1])
            self.isin('held', valu[1])
            self.isin('prose is not refreshable', valu[1])

    async def test_stormlib_markdown_stormimage(self):

        async with self.getTestCore() as core:

            await core.nodes('[ file:bytes=* :sha256=' + ('aa' * 32) + ' :name=one ]')

            opts = {'vars': {'url': '/api/v3/optic/files/by/sha256/{valu}'}}

            # the query names the file to show, so which one is a storm question
            valu = await core.callStorm('''
                $block = $lib.markdown.stormimage(${ file:bytes:name=$name return(:sha256) },
                                                  urltmpl=$url, alt=Evidence, title=Files,
                                                  vars=({"name": "one"}))
                return(({"text": $block.valu, "data": $block.data, "type": $block.type,
                         "refreshable": $block.refreshable}))
            ''', opts=opts)

            self.eq('stormblock', valu['type'])
            self.true(valu['refreshable'])
            self.eq('image', valu['data']['type'])
            self.eq({'name': 'one'}, valu['data']['vars'])
            self.eq('/api/v3/optic/files/by/sha256/{valu}', valu['data']['opts']['urltmpl'])
            self.isin('## Files', valu['text'])
            self.isin('![Evidence](/api/v3/optic/files/by/sha256/' + 'aa' * 32 + ')', valu['text'])

            # the default fence class, and the attrs carried onto the image
            valu = await core.callStorm('''
                $doc = $lib.markdown.doc()
                $doc.add($lib.markdown.stormimage(${ file:bytes return(:sha256) }, urltmpl=$url,
                                                  attrs="{width=50%}"))
                return($doc.text)
            ''', opts=opts)
            self.isin('::: {.storm-block', valu)
            self.isin('{width=50%}', valu)

            # a rebuild draws what the query names now, and reports that it drew one
            valu = await core.callStorm('''
                $doc = $lib.markdown.doc()
                $block = $lib.markdown.stormimage(${ file:bytes:name=$name return(:sha256) },
                                                  urltmpl=$url, vars=({"name": "one"}))
                $doc.add($block)
                [ file:bytes=* :sha256=''' + 'cc' * 32 + ''' :name=two ] | spin |
                $block.setVar(name, two)
                return(($block.refresh(), $block.valu))
            ''', opts=opts)
            self.eq(1, valu[0])
            self.isin('cc' * 32, valu[1])

            # a query that names nothing leaves the block empty rather than raising: the file may
            # simply not be there yet
            valu = await core.callStorm('''
                $block = $lib.markdown.stormimage(${ file:bytes:name=nope return(:sha256) },
                                                  urltmpl=$url)
                return(($block.valu, $block.refresh()))
            ''', opts=opts)
            self.eq(('', 0), tuple(valu))

            # ...but a query that returns something that is not a sha256 says so
            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('''
                    $lib.markdown.stormimage(${ return(([1, 2])) }, urltmpl=$url)
                ''', opts=opts)
            self.isin('must return a sha256', cm.exception.get('mesg'))

            # no urltmpl means it cannot rebuild, and says which piece is missing
            with self.raises(s_exc.BadArg) as ctx:
                await core.callStorm('''
                    $doc = $lib.markdown.doc()
                    $block = $lib.markdown.div(('storm-image',), attrs=({"iden": $lib.guid()}))
                    $block.data = ({"type": "image", "query": "file:bytes return(:sha256)"})
                    $doc.add($block)
                    $block.refresh()
                ''')
            self.isin('urltmpl', ctx.exception.errinfo.get('mesg'))

    async def test_stormlib_markdown_block_type_docs(self):
        # Each block type documents the one value its `type` has, and that is the value it returns.
        ctors = dict(s_markdown.BLOCK_TYPES)
        ctors['block'] = s_markdown.MarkdownBlock

        for name, ctor in ctors.items():
            desc = ctor._storm_locals[0]['desc']
            self.eq('type', ctor._storm_locals[0]['name'])
            self.isin(f'always `{name}`', desc)

        async with self.getTestCore() as core:

            valu = await core.callStorm('''
                $doc = $lib.markdown.parse($body)
                $out = ([])
                for $block in $doc.blocks { $out.append(($block.type, $lib.utils.type($block))) }
                return($out)
            ''', opts={'vars': {'body': BODY}})

            self.gt(len(valu), 1)
            for (name, typename) in valu:
                self.eq(ctors[name]._storm_typename, typename)

        # a storm block's type is easily mistaken for the renderer its data names, so it says which
        self.isin('$block.data.type', s_markdown.MarkdownStormBlock._storm_locals[0]['desc'])
        for renderer in s_markdown.STORM_BLOCK_TYPES:
            self.isin(f'`{renderer}`', s_markdown.MarkdownStormBlock._storm_locals[0]['desc'])

    async def test_stormlib_markdown_registered_kinds(self):
        """A kind core has a renderer for is refreshable and has its opts validated. A kind it does
        not is neither -- which is what lets a caller carry opts core has no schema for."""

        async def render(items, data, model):
            return 'rendered', len(items)

        schema = {'type': 'object', 'properties': {'axis': {'type': 'string'}},
                  'additionalProperties': False}

        self.none(s_markdown.STORM_BLOCK_TYPES.get('newpchart'))
        s_markdown.STORM_BLOCK_TYPES['newpchart'] = {'render': render, 'opts': schema,
                                                   'run': s_markdown.runBlockNodes}

        try:
            async with self.getTestCore() as core:

                await core.nodes('[ inet:fqdn=evil.com +#suspect ]')

                valu = await core.callStorm('''
                    $doc = $lib.markdown.doc()
                    $block = $lib.markdown.div(('storm-newpchart',), attrs=({"iden": "abc"}))
                    $block.data = ({"type": "newpchart", "query": "inet:fqdn#suspect",
                                    "opts": ({"axis": "x"})})
                    $doc.add($block)
                    return(($block.refreshable, $block.refresh(), $block.valu))
                ''')
                self.eq((True, 1, 'rendered'), valu)

                # the kind's own schema, enforced where core writes a block's data
                with self.raises(s_exc.SchemaViolation):
                    await core.callStorm('''
                        $block = $lib.markdown.div(('storm-newpchart',), attrs=({"iden": "abc"}))
                        $block.data = ({"type": "newpchart", "opts": ({"nope": "x"})})
                    ''')

                # an UNregistered kind keeps opts core validates nothing about
                await core.callStorm('''
                    $block = $lib.markdown.div(('storm-newpmap',), attrs=({"iden": "abc"}))
                    $block.data = ({"type": "newpmap", "opts": ({"nope": "x"})})
                ''')

        finally:
            s_markdown.STORM_BLOCK_TYPES.pop('newpchart', None)
            s_markdown._optsValidators.pop('newpchart', None)

    async def test_stormlib_markdown_readonly_and_perms(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ]')
            await core.nodes('[ meta:story=* :id=abc :title=T :body="# Triage\\n" ] | spin')

            # building and reading a document is safe in a read-only runtime, which is what a preview
            # or a safe-mode evaluation runs in
            valu = await core.callStorm('''
                $md = $lib.markdown
                $doc = $md.parse($body)
                $doc.add($md.heading(Findings, (2)))
                $doc.add($md.stormtable(${ inet:fqdn#suspect }, title=Domains))
                return($doc.text)
            ''', opts={'readonly': True, 'vars': {'body': '# Triage\n'}})
            self.isin('## Findings', valu)
            self.isin('| evil.com |', valu)

            # ...as is opening one from a node, and reading it
            valu = await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                return(({"md": $doc.text, "orphans": $doc.orphans()}))
            ''', opts={'readonly': True})
            self.eq('# Triage\n', valu['md'])

            # ...including resolving one block by iden, which is a lookup over the list already
            # parsed. It was the one reader missing `readonly=True`, so a safe-mode preview that
            # addressed a block raised `IsReadOnly` while reading the whole document did not.
            iden = 'f' * 32
            valu = await core.callStorm('''
                $doc = $lib.markdown.parse($body)
                return(($doc.block($iden).data.type, $doc.block($miss)))
            ''', opts={'readonly': True,
                       'vars': {'body': f'::: {{.storm-block iden="{iden}"}}\nhi\n:::\n',
                                'iden': iden, 'miss': 'a' * 32}})
            self.eq((None, None), valu)

            # every way of setting a block's vars only edits it in memory, so all of them run here
            valu = await core.callStorm('''
                $block = $lib.markdown.stormprint(${ $lib.print($tag) }, vars=({"tag": "a"}))
                $block.setVar(tag, b)
                $block.setVar(other, c)
                $block.popVar(other)
                return($block.vars)
            ''', opts={'readonly': True})
            self.eq({'tag': 'b'}, valu)

            # writing is not
            for meth in ('save()', 'purgeOrphans()'):
                with self.raises(s_exc.IsReadOnly):
                    await core.callStorm(f'''
                        meta:story:id=abc
                        $lib.markdown.load($node).{meth}
                    ''', opts={'readonly': True})

            # a document API is not a way around the prop perms: the same write through `$node.props`
            # confirms `node.prop.set.meta:story.body`, so this does too
            user = await core.auth.addUser('lowly')
            await user.addRule((True, ('view', 'read')))

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('''
                    meta:story:id=abc
                    $doc = $lib.markdown.load($node)
                    $doc.add($lib.markdown.paragraph(sneaky))
                    $doc.save()
                ''', opts={'user': user.iden})

            await user.addRule((True, ('node', 'prop', 'set', 'meta:story', 'body')))
            await user.addRule((True, ('node', 'prop', 'set', 'meta:story', 'updated')))

            await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                $doc.add($lib.markdown.paragraph(allowed))
                $doc.save()
            ''', opts={'user': user.iden})

            nodes = await core.nodes('meta:story:id=abc')
            self.isin('allowed', nodes[0].get('body')[1])

    async def test_stormlib_markdown_column_names_match_the_table_view(self):
        '''
        An unnamed column's header is spelled the same here as it is in Optic's table view
        (`TableCDefs.generateColTitle`), so a column nobody named reads the same whether the table
        was drawn in a browser or rebuilt from its block data.

        The cases are a fixture the browser side runs too
        (`frontend/src/ts/optic/projections/__tests__/column-name-agreement.test.ts`), so a change to
        either spelling fails on both sides. They live in different languages in different
        repositories, and they drifted apart for `tag`, `embed` and `edge` -- which renamed such a
        column on every refresh, and dropped a stored sort on one, since a sort names its column by
        that name.
        '''
        path = self.getTestFilePath('markdown', 'column-names.json')
        with open(path) as fd:
            cases = s_json.load(fd)

        self.gt(len(cases), 0)

        async with self.getTestCore() as core:

            # the lift as a plain string, which `queryText` accepts: an embedded query would not
            # see `$form`, since a block's query runs with the block's own vars
            query = '''
                return($lib.markdown.stormtable($form, columns=($col,),
                                                form=$form).data.opts.columns)
            '''

            for case in cases:
                valu = await core.callStorm(query, opts={'vars': {'col': case['column'],
                                                                  'form': case['form']}})
                self.eq(case['title'], valu[0]['name'], msg=case['name'])

    async def test_stormlib_markdown_stormtable_column_kinds(self):

        async with self.getTestCore() as core:

            await core.nodes('''
                [ inet:fqdn=evil.com
                    +#aka.feye.thr.apt1
                    +#cno.infra.anon.tor=(2021, 2022)
                ]
            ''')
            await core.nodes('[ it:software=(tool, webc2) :name=WEBC2 ]')
            await core.nodes('inet:fqdn=evil.com [ +(uses)> { it:software:name=WEBC2 } ]')

            # every kind the Optic table view can put on a table, in one table
            cols = (
                {'name': 'Domain', 'type': 'form'},
                {'name': 'Host', 'type': 'prop', 'prop': 'host'},
                {'name': 'Added', 'type': 'meta', 'meta': 'created'},
                {'name': 'Tor since', 'type': 'tag', 'tag': 'cno.infra.anon.tor', 'index': 0},
                {'name': 'Tor until', 'type': 'tag', 'tag': 'cno.infra.anon.tor', 'index': 1},
                {'name': 'Clusters', 'type': 'tagglob', 'tagglob': 'aka.**'},
                {'name': 'Tools', 'type': 'edge', 'edge': ('uses', 'it:software', False)},
                {'name': 'Zone name', 'type': 'embed', 'embed': 'zone::host'},
                {'name': 'Why', 'type': 'pathvar', 'pathvar': 'why'},
            )

            valu = await core.callStorm('''
                $items = ([])
                inet:fqdn=evil.com
                $why = "seen in traffic"
                $items.append($node)
                spin |

                return($lib.markdown.stormtable(${ inet:fqdn=evil.com $why="seen in traffic" },
                                                columns=$cols).valu)
            ''', opts={'vars': {'cols': cols}})

            self.isin('| Domain | Host | Added | Tor since | Tor until | Clusters | Tools | Zone name | Why |',
                      valu)

            row = [cell.strip() for cell in valu.split('\n')[-1].strip('|').split('|')]

            self.eq('evil.com', row[0])                     # form: the primary value
            self.eq('evil', row[1])                         # prop
            self.true(row[2].startswith('20'))              # meta: .created
            self.eq('2021-01-01T00:00:00Z', row[3])         # tag: the ival min
            self.eq('2022-01-01T00:00:00Z', row[4])         # ...and its max
            self.eq('#aka.feye.thr.apt1', row[5])           # tagglob: the leaf tag it matched
            self.eq('1', row[6])                            # edge: how many
            self.eq('evil', row[7])                         # embed: a prop of the node it pivots to
            self.eq('seen in traffic', row[8])              # pathvar: from the path it arrived on

            # several matching tags, which is where the separator shows: `#` prefixed and space
            # separated, the way a tag is written in Storm and drawn in the table view. A comma-joined
            # list of bare names read as prose rather than as tags.
            await core.nodes('inet:fqdn=evil.com [ +#aka.mitre.apt1 +#aka.crowd.panda ]')

            valu = await core.callStorm('''
                return($lib.markdown.stormtable(${ inet:fqdn=evil.com },
                                                columns=$cols).valu)
            ''', opts={'vars': {'cols': ({'name': 'Clusters', 'type': 'tagglob',
                                          'tagglob': 'aka.**'},)}})

            row = [cell.strip() for cell in valu.split('\n')[-1].strip('|').split('|')]
            self.eq('#aka.crowd.panda #aka.feye.thr.apt1 #aka.mitre.apt1', row[0])

            # a column with no name is named in the vocabulary of its kind
            valu = await core.callStorm('''
                $cols = (({"type": "form"}), ({"type": "prop", "prop": "host"}),
                         ({"type": "tag", "tag": "aka.feye.thr.apt1"}),
                         ({"type": "tagglob", "tagglob": "cno.**"}),
                         ({"type": "meta", "meta": "created"}),
                         ({"type": "pathvar", "pathvar": "why"}))
                return($lib.markdown.stormtable(${ inet:fqdn=evil.com }, columns=$cols).data.opts.columns)
            ''')
            # the form column takes the form, which is what the table view heads it with; the rest
            # are named in the vocabulary of their own kind -- and spelled the way the table view
            # spells them, so a column nobody named is headed the same whether it was drawn in a
            # browser or rebuilt here. A tag column with no `index` names the tag itself; one that
            # picks an interval bound says which (`#(tag).min`).
            self.eq(['inet:fqdn', ':host', '#aka.feye.thr.apt1', '#cno.**', '.created', '$why'],
                    [col['name'] for col in valu])

            # ...and `Node` is only reachable through a table built with no query behind it, since a
            # storm table always knows its form: named, or taken from rows that agree.
            self.eq('Node', s_markdown.normStormColumns(None)[0]['name'])

            # a kind that names nothing to read says so, rather than rendering an empty column
            for cols in ((({'type': 'tag'}),), (({'type': 'edge'}),), (({'type': 'embed'}),),
                         (({'type': 'pathvar'}),), (({'type': 'newp', 'prop': 'host'}),)):

                with self.raises(s_exc.BadArg):
                    await core.callStorm('''
                        return($lib.markdown.stormtable(${ inet:fqdn=evil.com }, columns=$cols).valu)
                    ''', opts={'vars': {'cols': cols}})

            # ...as does a tag column asking for a bound that does not exist
            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    $cols = (({"type": "tag", "tag": "aka", "index": (2)}),)
                    return($lib.markdown.stormtable(${ inet:fqdn=evil.com }, columns=$cols).valu)
                ''')

            # A tag index is a position, so only 1 is the interval's end. The builder refuses anything
            # else, but a caller assembling coldefs itself reaches the projection directly -- and an
            # index it does not understand has to read as the start rather than silently as the end.
            node = (await core.nodes('inet:fqdn=evil.com'))[0]

            mint = await s_markdown.projectCell(
                node, None, {'type': 'tag', 'tag': 'cno.infra.anon.tor', 'index': 0}, core.model)
            maxt = await s_markdown.projectCell(
                node, None, {'type': 'tag', 'tag': 'cno.infra.anon.tor', 'index': 1}, core.model)

            self.ne(mint, maxt)

            for indx in (2, 7, -1):
                valu = await s_markdown.projectCell(
                    node, None, {'type': 'tag', 'tag': 'cno.infra.anon.tor', 'index': indx},
                    core.model)
                self.eq(mint, valu)

            # an embed names a pivot path and a property
            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    $cols = (({"type": "embed", "embed": "zone"}),)
                    return($lib.markdown.stormtable(${ inet:fqdn=evil.com }, columns=$cols).valu)
                ''')

            # a virt reads a virtual property of the primary value, which a prop path cannot name
            await core.nodes('[ inet:server=tcp://1.2.3.4:443 ]')
            valu = await core.callStorm('''
                $cols = (({"name": "Server", "type": "form"}),
                         ({"name": "Port", "type": "virt", "virt": "port"}))
                return($lib.markdown.stormtable(${ inet:server }, columns=$cols).valu)
            ''')
            self.isin('| Server | Port |', valu)
            self.isin('| 443 |', valu)

            # a cell with nothing behind it is empty rather than absent: an unset tag, a verb with no
            # edges, a path variable this row never had
            valu = await core.callStorm('''
                $verbs = ([])
                $verbs.append(newp)
                $cols = (({"name": "T", "type": "tag", "tag": "newp.nope"}),
                         ({"name": "E", "type": "edge", "edge": $verbs}),
                         ({"name": "P", "type": "pathvar", "pathvar": "nope"}))
                return($lib.markdown.stormtable(${ inet:fqdn=evil.com }, columns=$cols).valu)
            ''')
            self.isin('|  | 0 |  |', valu)

            # ...but a column naming a virt or a prop the model does not have is a broken column, and
            # says so rather than rendering blanks, the same way the table view refuses to build one
            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('''
                    $cols = (({"name": "V", "type": "virt", "virt": "newp"}),)
                    return($lib.markdown.stormtable(${ inet:fqdn=evil.com }, columns=$cols).valu)
                ''')

            self.isin('is not one', cm.exception.get('mesg'))

            with self.raises(s_exc.NoSuchProp):
                await core.callStorm('''
                    $cols = (({"name": "P", "type": "prop", "prop": "newp"}),)
                    return($lib.markdown.stormtable(${ inet:fqdn=evil.com }, columns=$cols).valu)
                ''')

            # ...and a table over a query that yielded nothing says so too. It has no row to check a
            # column against, and it is exactly the table a Story written before its data exists is
            # made of -- so the typo surfaces now rather than the month the data arrives.
            for col in ({'name': 'V', 'type': 'virt', 'virt': 'newp'},
                        {'name': 'M', 'type': 'meta', 'meta': 'newp'}):

                with self.raises(s_exc.BadArg) as cm:
                    await core.callStorm('''
                        return($lib.markdown.stormtable(${ inet:fqdn#nope }, columns=($col,),
                                                        form=inet:fqdn).valu)
                    ''', opts={'vars': {'col': col}})

                self.isin('is not one', cm.exception.get('mesg'))

            # a virt the form does have is fine with no rows at all
            self.isin('| Port |', await core.callStorm('''
                $cols = (({"name": "Port", "type": "virt", "virt": "port"}),)
                return($lib.markdown.stormtable(${ inet:server#nope }, columns=$cols,
                                                form=inet:server).valu)
            '''))

    async def test_stormlib_markdown_doc_text_and_block(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ]')

            first = '# One\n'
            second = '# Two\n\nprose\n'

            # a document's text is the same name a block uses for its source, and setting it re-parses
            valu = await core.callStorm('''
                $md = $lib.markdown
                $doc = $md.parse($first)

                $was = $doc.text
                $doc.text = $second

                $types = ([])
                for $block in $doc.blocks { $types.append($block.type) }

                return(({"was": $was, "now": $doc.text, "types": $types}))
            ''', opts={'vars': {'first': first, 'second': second}})
            self.eq(first, valu['was'])
            self.eq(second, valu['now'])
            self.eq(('heading', 'paragraph'), valu['types'])

            # a block is found by the durable name an automation keeps between runs
            valu = await core.callStorm('''
                $md = $lib.markdown
                $doc = $md.doc()
                $doc.add($md.heading(Findings, (2)))
                $doc.add($md.stormtable(${ inet:fqdn#suspect }, iden=abc, title=Domains))

                return(({"found": $doc.block(abc).iden, "newp": $doc.block(newp)}))
            ''')
            self.eq('abc', valu['found'])
            self.none(valu['newp'])

            # ...and it is the same object, so rebuilding through it changes the document
            valu = await core.callStorm('''
                $md = $lib.markdown
                $doc = $md.doc()
                $doc.add($md.stormtable(${ inet:fqdn#suspect }, iden=abc, title=Domains))

                [ inet:fqdn=worse.com +#suspect ]
                spin |

                $doc.block(abc).refresh()
                return($doc.text)
            ''')
            self.isin('| worse.com |', valu)

    async def test_stormlib_markdown_doc_document_iface(self):
        # `doc:document` is the whole requirement: it declares :body, which is the only prop a
        # document reads or writes. What else a form implements is nobody's business here.
        async with self.getTestCore() as core:

            await core.nodes('[ doc:policy=* :id=pol :title="A policy" :body="# One\\n" ] | spin')

            text = await core.callStorm('''
                doc:policy:id=pol
                $doc = $lib.markdown.load($node)
                $doc.add($lib.markdown.paragraph(added))
                $doc.save()
                return($doc.text)
            ''')
            self.eq('# One\n\nadded', text)

            # ...and a form without it is refused at the door
            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('[ inet:fqdn=evil.com ] $lib.markdown.load($node)')

            self.isin('doc:document', cm.exception.get('mesg'))

    async def test_stormlib_markdown_coverage_corners(self):
        # The corners the ordinary paths do not reach: a block's vars set wholesale, an empty array
        # cell, a column that only a hand-assembled config can carry, and the refusals that are about
        # the caller rather than the data.
        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ] | spin')
            await core.nodes('[ risk:threat=(t,) :name=T :names=() ] | spin')
            await core.nodes('[ meta:story=* :id=abc :title=T :body="# Triage\\n" ] | spin')

            # a block's vars, set wholesale rather than one at a time
            valu = await core.callStorm('''
                $blk = $lib.markdown.stormtable(${ inet:fqdn#$tag }, vars=({"tag": "suspect"}))
                $blk.vars = ({"tag": "newp"})
                return($blk.vars)
            ''')
            self.eq({'tag': 'newp'}, valu)

            # block data checked with no block to put it on, handed back as it would be stored
            valu = await core.callStorm('''
                return($lib.markdown.reqBlockData(({"type": "table", "query": "inet:fqdn"})))
            ''')
            self.eq('table', valu['type'])
            self.eq('inet:fqdn', valu['query'])

            with self.raises(s_exc.SchemaViolation):
                await core.callStorm('return($lib.markdown.reqBlockData(({"type": "table", "query": 10})))')

            # an array prop writes storm's own tuple spelling, the way the node view writes one --
            # including the two shapes a list does not have a spelling for
            await core.nodes('[ risk:threat=(one,) :name=One :names=(alpha,) ] | spin')

            valu = await core.callStorm('''
                $cols = (({"name": "Threat", "prop": "name"}), ({"name": "Aliases", "prop": "names"}))
                return($lib.markdown.stormtable(${ risk:threat }, columns=$cols).valu)
            ''')
            self.isin('| T | () |', valu)
            self.isin('| One | (alpha,) |', valu)

            # a block with no data at all is skipped by a save rather than stored as an empty one: a
            # document parsed from text has blocks and no data
            valu = await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                $doc.text = $lib.markdown.stormtable(${ inet:fqdn#suspect }).text
                $doc.save()
                return(($lib.len($doc.blocks), $doc.node.data.list()))
            ''')
            self.eq(1, valu[0])
            self.eq((), tuple(valu[1]))

            # a table whose stored form is one the model no longer has falls back to a single column
            # of primary values rather than refusing to rebuild -- the form left, the document did not
            valu = await core.callStorm('''
                $blk = $lib.markdown.stormtable(${ inet:fqdn#suspect })
                $blk.data = ({"type": "table", "query": "inet:fqdn#suspect",
                              "opts": ({"form": "newp:form"})})
                $doc = $lib.markdown.doc()
                $doc.add($blk)
                $blk.refresh()
                return($blk.valu)
            ''')
            self.isin('| newp:form |', valu)

            # a virt column on a table with no stored form, over a query that has come to span forms,
            # is checked against each row's type -- there is no one form to check it against first,
            # and what a virt means differs row by row
            await core.nodes('[ inet:server="tcp://1.2.3.4:80" +#suspect ] | spin')

            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('''
                    $cols = ([({"name": "V", "type": "virt", "virt": "port"})])
                    $blk = $lib.markdown.stormtable(${ inet:server#suspect })
                    $blk.data = ({"type": "table", "query": "#suspect",
                                  "opts": ({"columns": $cols})})
                    $doc = $lib.markdown.doc()
                    $doc.add($blk)
                    $blk.refresh()
                ''')

            self.isin('is not one', cm.exception.get('mesg'))
            self.eq('inet:fqdn', cm.exception.get('form'))

            # ...and a print block is bounded by what it printed, however many nodes it ran over
            with mock.patch.object(s_markdown, 'BLOCK_MAX_ROWS', 1):
                with self.raises(s_exc.BadArg) as cm:
                    await core.callStorm('''
                        $lib.markdown.stormprint(${ inet:fqdn $lib.print($node.repr()) })
                    ''')

                self.isin('at most 1 lines', cm.exception.get('mesg'))

            # a virt or meta column that only a hand-assembled config can carry: normStormColumns
            # refuses one, so this is the check on the way out, where a config written by hand or by
            # an older Optic arrives
            for col in ({'name': 'V', 'type': 'virt', 'virt': 'newp'},
                        {'name': 'M', 'type': 'meta', 'meta': 'newp'}):

                with self.raises(s_exc.BadArg) as cm:
                    await core.callStorm('''
                        $blk = $lib.markdown.div((storm-table,), attrs=({"iden": $lib.guid()}))
                        $cols = ([$col])
                        $blk.data = ({"type": "table", "query": "inet:fqdn#suspect",
                                      "opts": ({"columns": $cols, "form": "inet:fqdn"})})
                        $doc = $lib.markdown.doc()
                        $doc.add($blk)
                        $blk.refresh()
                    ''', opts={'vars': {'col': col}})

                self.isin('is not one', cm.exception.get('mesg'))

            # a print block is bounded the way a table is, and stops at the line that overflows, though
            # its query never yields a node
            with mock.patch.object(s_markdown, 'BLOCK_MAX_ROWS', 2):
                with self.raises(s_exc.BadArg) as cm:
                    await core.callStorm('''
                        $lib.markdown.stormprint(${
                            for $i in $lib.range((1000000000000)) { $lib.print($i) }
                        })
                    ''')

                self.isin('at most 2 lines', cm.exception.get('mesg'))

                # a print from a function the query calls lands on the same bound
                with self.raises(s_exc.BadArg) as cm:
                    await core.callStorm('''
                        $lib.markdown.stormprint(${
                            function say(n) { $lib.print($n) return() }
                            for $i in $lib.range((1000000000000)) { $say($i) }
                        })
                    ''')

                self.isin('at most 2 lines', cm.exception.get('mesg'))

            # a warning is not a line of the block, and the block keeps what it printed
            valu = await core.callStorm('''
                $blk = $lib.markdown.stormprint(${ $lib.warn(woot) $lib.print(hehe) })
                return($blk.valu)
            ''')
            self.isin('hehe', valu)
            self.notin('woot', valu)

            # an image query that runs to the end without returning names no file, rather than
            # answering with whatever its last node was
            valu = await core.callStorm('''
                $blk = $lib.markdown.stormimage(${ inet:fqdn#suspect }, urltmpl="/f/{valu}")
                return(($blk.valu, $blk.data.query))
            ''')
            self.eq('', valu[0])

            # a document-wide refresh swallows a block whose query no longer runs, but not a refusal
            # that is about how the query was asked to run: a rebuild may never edit the graph, and
            # that is the same answer for every block in the document
            with self.raises(s_exc.IsReadOnly):
                await core.callStorm('''
                    $blk = $lib.markdown.stormtable(${ inet:fqdn#suspect })
                    $blk.data = ({"type": "table", "query": "[ inet:fqdn=made.by.refresh ]"})

                    $doc = $lib.markdown.doc()
                    $doc.add($blk)
                    $doc.refresh()
                ''')

            self.len(0, await core.nodes('inet:fqdn=made.by.refresh'))

            # ...and stormnode takes a node object as readily as the pipeline's own
            valu = await core.callStorm('''
                meta:story:id=abc
                $doc = $lib.markdown.load($node)
                return($lib.markdown.stormnode($doc.node).data.query)
            ''')
            self.true(valu.startswith('meta:story='))

    async def test_stormlib_markdown_block_refreshable(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ]')

            # `kind` says what a block is, `data` says what made it, and `refreshable` says whether core
            # can remake the content from that data -- three separate questions
            valu = await core.callStorm('''
                $md = $lib.markdown

                $out = ([])

                $tabl = $md.stormtable(${ inet:fqdn#suspect })
                $out.append(($tabl.type, $tabl.refreshable))

                // a kind core does not rebuild
                $chart = $md.div(('storm-chart',), attrs=({"iden": $lib.guid()}))
                $chart.data = ({"type": "chart", "query": "inet:fqdn"})
                $out.append(($chart.type, $chart.refreshable))

                // a table with nothing to re-run
                $bare = $md.div(('storm-table',), attrs=({"iden": $lib.guid()}))
                $bare.data = ({"type": "table"})
                $out.append(($bare.type, $bare.refreshable))

                // a lookup-mode query is raw values, turned into lifts a layer above core
                $look = $md.div(('storm-table',), attrs=({"iden": $lib.guid()}))
                $look.data = ({"type": "table", "query": "vertex.link", "mode": "lookup"})
                $out.append(($look.type, $look.refreshable))

                // ...and a plain block is not a storm block at all
                $out.append(($md.paragraph(prose).type, (false)))

                return($out)
            ''')

            self.eq([
                ('stormblock', True),
                ('stormblock', False),
                ('stormblock', False),
                ('stormblock', False),
                ('paragraph', False),
            ], valu)

            # ...and the flag agrees with what refresh() does, which is the point of having it
            with self.raises(s_exc.BadArg):
                await core.callStorm('''
                    $block = $lib.markdown.div(('storm-table',), attrs=({"iden": $lib.guid()}))
                    $block.data = ({"type": "table"})
                    $block.refresh()
                ''')

    async def test_stormlib_markdown_block_type_selects_the_renderer(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:fqdn=evil.com +#suspect ]')

            await core.nodes('[ meta:story=* :id=abc :title=T ] | spin')

            # There is one Storm type for a storm block; what it is is in its data, and its `type` is
            # what selects the renderer. So a block keeps its type however it arrived -- and what it can
            # answer depends on whether its data came with it, since block data lives beside the markdown
            # rather than in it.
            valu = await core.callStorm('''
                $md = $lib.markdown
                $built = $md.stormtable(${ inet:fqdn#suspect }, iden=deadbeef, title=T)

                // parsed from bare text: the same kind, and nothing to rebuild from
                $bare = $md.parse($built.text).block(deadbeef)

                return(({"builttype": $built.type, "baretype": $bare.type,
                         "builtcols": $built.data.opts.columns, "barecols": $bare.data.opts.columns,
                         "builtref": $built.refreshable, "bareref": $bare.refreshable}))
            ''')

            self.eq('stormblock', valu['builttype'])
            self.eq('stormblock', valu['baretype'])

            self.eq([{'name': 'inet:fqdn', 'type': 'form'}], valu['builtcols'])
            self.true(valu['builtref'])

            # ...where the block parsed from text alone knows it is a storm block and nothing more
            self.none(valu['barecols'])
            self.false(valu['bareref'])

            # ...and a document opened from a node loads that data back, so the same block is
            # refreshable again on the next open
            valu = await core.callStorm('''
                $story = (null)
                meta:story:id=abc
                $story = $node
                spin |

                $doc = $lib.markdown.load($story)
                $doc.add($lib.markdown.stormtable(${ inet:fqdn#suspect }, iden=deadbeef, title=T))
                $doc.save()

                $again = $lib.markdown.load($story).block(deadbeef)

                return(({"cols": $again.data.opts.columns, "ref": $again.refreshable,
                         "type": $again.data.type}))
            ''')
            self.eq([{'name': 'inet:fqdn', 'type': 'form'}], valu['cols'])
            self.true(valu['ref'])
            self.eq('table', valu['type'])

            # ...and a rebuild of it works through the document, which is the whole point of the iden
            valu = await core.callStorm('''
                $md = $lib.markdown
                $doc = $md.doc()
                $doc.add($md.stormtable(${ inet:fqdn#suspect }, iden=abc, title=T))

                [ inet:fqdn=worse.com +#suspect ]
                spin |

                return($doc.block(abc).refresh())
            ''')
            self.eq(2, valu)

            # a kind core has no renderer for says so in those terms: `type` selects the renderer, and
            # rebuilding a chart is whoever wrote it's business
            with self.raises(s_exc.BadArg) as cm:
                await core.callStorm('''
                    $block = $lib.markdown.div(('storm-chart',), attrs=({"iden": $lib.guid()}))
                    $block.data = ({"type": "chart", "query": "inet:fqdn"})
                    $block.refresh()
                ''')

            self.isin('does not render a chart', cm.exception.get('mesg'))

            # ...and it rebuilds by setting the content itself, which keeps the fence and the iden
            content = '## Chart\n\n![chart](/api/v3/optic/files/by/sha256/aa)'

            valu = await core.callStorm('''
                $md = $lib.markdown
                $block = $md.div(('storm-chart',), attrs=({"iden": "abc"}))
                $block.data = ({"type": "chart", "query": "inet:fqdn"})

                $block.valu = $content

                return($block.text)
            ''', opts={'vars': {'content': content}})
            self.isin('iden="abc"', valu)
            self.isin('![chart]', valu)

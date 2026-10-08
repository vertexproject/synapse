import decimal
import asyncio
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.cache as s_cache
import synapse.lib.config as s_config
import synapse.lib.mdparse as s_mdparse
import synapse.lib.stormctrl as s_stormctrl
import synapse.lib.stormtypes as s_stormtypes

def getBlockLocals(name, desc=''):
    '''
    The locals every block type documents, since a Storm type documents its own.

    Built per type so each one's `type` says the value it always has.
    '''
    return (
        {'name': 'type', 'desc': f'The type of block this is, which is always `{name}`.{desc}',
         'type': {'type': 'gtor', '_gtorfunc': '_getType',
                  'returns': {'type': 'str', 'desc': 'The block type.'}}},
        {'name': 'text', 'desc': "The block's markdown source, which is the value of the block.",
         'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_getText', '_storfunc': '_setText',
                  'returns': {'type': 'str', 'desc': 'The markdown source.'}}},
    )

@s_stormtypes.registry.registerType
class MarkdownBlock(s_stormtypes.Prim):
    '''
    A block of markdown: one top-level piece of a document.

    A block is its source, so printing one or returning it from Storm gives that source.
    '''
    _storm_typename = 'markdown:block'
    _storm_locals = getBlockLocals('block')

    def __init__(self, block, runt=None, path=None):
        s_stormtypes.Prim.__init__(self, block, path=path)
        self.runt = runt
        self.gtors.update({
            'type': self._getType,
            'text': self._getText,
        })
        self.stors.update({
            'text': self._setText,
        })
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {}

    # A block is its source everywhere it is asked for one. Duck typed for mdparse.joinBlocks, which
    # takes either a Block or one of these.
    @property
    def text(self):
        return self.valu.text

    @property
    def tail(self):
        return self.valu.tail

    @property
    def inner(self):
        return self.valu.inner

    async def value(self):
        return self.text

    async def stormrepr(self):
        return self.text

    async def _getText(self):
        return self.text

    def __eq__(self, othr):
        # $doc.blocks is a real list whose has/index/rem convert what they are given to a primitive,
        # which for a block is its source. So a block compares equal to that source and to nothing else.
        return isinstance(othr, str) and self.text == othr

    async def _getType(self):
        return self.valu.kind

    @s_stormtypes.stormfunc(readonly=True)
    async def _setText(self, valu):
        self.valu.text = await s_stormtypes.tostr(valu)

@s_stormtypes.registry.registerType
class MarkdownHeading(MarkdownBlock):
    '''
    A markdown heading.
    '''
    _storm_typename = 'markdown:heading'
    _storm_locals = getBlockLocals('heading') + (
        {'name': 'level', 'desc': 'The heading level (1-6).',
         'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_getLevel', '_storfunc': '_setLevel',
                  'returns': {'type': 'int', 'desc': 'The heading level.'}}},
        {'name': 'valu', 'desc': 'The heading text.',
         'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_getValu', '_storfunc': '_setValu',
                  'returns': {'type': 'str', 'desc': 'The heading text.'}}},
    )

    def __init__(self, block, runt=None, path=None):
        MarkdownBlock.__init__(self, block, runt=runt, path=path)
        self.gtors.update({'level': self._getLevel, 'valu': self._getValu})
        self.stors.update({'level': self._setLevel, 'valu': self._setValu})

    async def _getLevel(self):
        return self.valu.getLevel()

    @s_stormtypes.stormfunc(readonly=True)
    async def _setLevel(self, valu):
        self.valu.setLevel(await s_stormtypes.toint(valu))

    async def _getValu(self):
        return self.valu.getValu()

    @s_stormtypes.stormfunc(readonly=True)
    async def _setValu(self, valu):
        self.valu.setValu(await s_stormtypes.tostr(valu))

@s_stormtypes.registry.registerType
class MarkdownParagraph(MarkdownBlock):
    '''
    A markdown paragraph.
    '''
    _storm_typename = 'markdown:paragraph'
    _storm_locals = getBlockLocals('paragraph') + (
        {'name': 'valu', 'desc': 'The paragraph text, with newlines collapsed to spaces when set.',
         'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_getValu', '_storfunc': '_setValu',
                  'returns': {'type': 'str', 'desc': 'The paragraph text.'}}},
    )

    def __init__(self, block, runt=None, path=None):
        MarkdownBlock.__init__(self, block, runt=runt, path=path)
        self.gtors.update({'valu': self._getValu})
        self.stors.update({'valu': self._setValu})

    async def _getValu(self):
        return self.valu.getValu()

    @s_stormtypes.stormfunc(readonly=True)
    async def _setValu(self, valu):
        self.valu.setValu(await s_stormtypes.tostr(valu))

@s_stormtypes.registry.registerType
class MarkdownCode(MarkdownBlock):
    '''
    A fenced markdown code block.
    '''
    _storm_typename = 'markdown:code'
    _storm_locals = getBlockLocals('code') + (
        {'name': 'lang', 'desc': 'The code language on the fence.',
         'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_getLang', '_storfunc': '_setLang',
                  'returns': {'type': 'str', 'desc': 'The code language.'}}},
        {'name': 'valu', 'desc': 'The code itself, without the fences.',
         'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_getValu', '_storfunc': '_setValu',
                  'returns': {'type': 'str', 'desc': 'The code.'}}},
    )

    def __init__(self, block, runt=None, path=None):
        MarkdownBlock.__init__(self, block, runt=runt, path=path)
        self.gtors.update({'lang': self._getLang, 'valu': self._getValu})
        self.stors.update({'lang': self._setLang, 'valu': self._setValu})

    async def _getLang(self):
        return self.valu.getLang()

    @s_stormtypes.stormfunc(readonly=True)
    async def _setLang(self, valu):
        self.valu.setLang(await s_stormtypes.tostr(valu))

    async def _getValu(self):
        return self.valu.getValu()

    @s_stormtypes.stormfunc(readonly=True)
    async def _setValu(self, valu):
        self.valu.setValu(await s_stormtypes.tostr(valu))

@s_stormtypes.registry.registerType
class MarkdownList(MarkdownBlock):
    '''
    A markdown list.
    '''
    _storm_typename = 'markdown:list'
    _storm_locals = getBlockLocals('list') + (
        {'name': 'items', 'desc': 'The list items.',
         'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_getItems', '_storfunc': '_setItems',
                  'returns': {'type': 'list', 'desc': 'The list items.'}}},
        {'name': 'ordered', 'desc': 'True if the list is ordered (numbered).',
         'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_getOrdered', '_storfunc': '_setOrdered',
                  'returns': {'type': 'boolean', 'desc': 'True if the list is ordered.'}}},
    )

    def __init__(self, block, runt=None, path=None):
        MarkdownBlock.__init__(self, block, runt=runt, path=path)
        self.gtors.update({'items': self._getItems, 'ordered': self._getOrdered})
        self.stors.update({'items': self._setItems, 'ordered': self._setOrdered})

    async def _getItems(self):
        return self.valu.getItems()

    @s_stormtypes.stormfunc(readonly=True)
    async def _setItems(self, valu):
        self.valu.setItems(await s_stormtypes.toprim(valu, use_list=True))

    async def _getOrdered(self):
        return self.valu.getOrdered()

    @s_stormtypes.stormfunc(readonly=True)
    async def _setOrdered(self, valu):
        self.valu.setOrdered(await s_stormtypes.tobool(valu))

@s_stormtypes.registry.registerType
class MarkdownTable(MarkdownBlock):
    '''
    A GFM markdown table.

    Rows are appended to the source, so adding one leaves every row already in the table exactly as it
    was.
    '''
    _storm_typename = 'markdown:table'
    _storm_locals = getBlockLocals('table') + (
        {'name': 'columns', 'desc': 'The column definitions.',
         'type': {'type': 'gtor', '_gtorfunc': '_getColumns',
                  'returns': {'type': 'list', 'desc': 'The normalized column definition dicts.'}}},
        {'name': 'rows', 'desc': '''
            The rows of the table, each a list of cell values as they are written.

            A plain list, to read and to iterate: rows go in through `addRow()`, and appending to this
            one writes nothing.
            ''',
         'type': {'type': 'gtor', '_gtorfunc': '_getRows',
                  'returns': {'type': 'list', 'desc': 'The rows.'}}},
        {'name': 'addRow', 'desc': 'Add a row of cell values.',
         'type': {'type': 'function', '_funcname': '_methAddRow',
                  'args': (
                      {'name': 'data', 'type': 'list',
                       'desc': 'The row cell values, one per column.'},
                  ),
                  'returns': {'type': 'markdown:table', 'desc': 'The table (for chaining).'}}},
        {'name': 'addRows', 'desc': 'Add multiple rows of cell values.',
         'type': {'type': 'function', '_funcname': '_methAddRows',
                  'args': (
                      {'name': 'data', 'type': 'list', 'desc': 'A list of rows to add.'},
                  ),
                  'returns': {'type': 'markdown:table', 'desc': 'The table (for chaining).'}}},
        {'name': 'sort', 'desc': '''
            Put the rows in the order of one column.

            The header stays where it is and each row moves whole, so a sort never rewrites a cell.
            Rows order by the text in the column, except a column where every cell reads as a number,
            which orders numerically. An empty cell is the smallest value: first ascending, last
            descending. Rows added afterwards are appended rather than sorted into place.

            Examples:
                Sort a table by its first column::

                    $tabl.sort("Software")

                    // ...or the other way
                    $tabl.sort("Software", direction=desc)
            ''',
         'type': {'type': 'function', '_funcname': '_methSort',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the column to sort by.'},
                      {'name': 'direction', 'type': 'str', 'default': 'asc',
                       'desc': 'The sort direction, `asc` or `desc`.'},
                  ),
                  'returns': {'type': 'markdown:table', 'desc': 'The table (for chaining).'}}},
    )

    def __init__(self, block, runt=None, path=None):
        MarkdownBlock.__init__(self, block, runt=runt, path=path)
        self.gtors.update({'columns': self._getColumns, 'rows': self._getRows})

    def getObjLocals(self):
        return {
            'addRow': self._methAddRow,
            'addRows': self._methAddRows,
            'sort': self._methSort,
        }

    async def _getRows(self):
        return self.valu.getRows()

    async def _getColumns(self):
        return self.valu.getColumns()

    @s_stormtypes.stormfunc(readonly=True)
    async def _setText(self, valu):
        self.valu.setText(await s_stormtypes.tostr(valu))

    @s_stormtypes.stormfunc(readonly=True)
    async def _methAddRow(self, data):
        data = await s_stormtypes.toprim(data)
        if not isinstance(data, (list, tuple)):
            mesg = 'markdown table row must be a list of cell values'
            raise s_exc.BadArg(mesg=mesg, data=data)

        self.valu.addRow(data)
        return self

    @s_stormtypes.stormfunc(readonly=True)
    async def _methAddRows(self, data):
        data = await s_stormtypes.toprim(data)
        for row in data:
            await self._methAddRow(row)

        return self

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSort(self, name, direction='asc'):

        name = await s_stormtypes.tostr(name)
        direction = await s_stormtypes.tostr(direction)

        if direction not in ('asc', 'desc'):
            mesg = f'a markdown table sort direction is "asc" or "desc", got {direction}'
            raise s_exc.BadArg(mesg=mesg, direction=direction)

        names = [col['name'] for col in self.valu.getColumns()]
        if name not in names:
            mesg = f'a markdown table has no column named {name}'
            raise s_exc.BadArg(mesg=mesg, name=name, columns=names)

        self.valu.sortRows(names.index(name), reverse=direction == 'desc')

        return self

DIV_LOCALS = (
    {'name': 'classes', 'desc': '''
        The classes on the opening fence.

        Setting them rebuilds the fence around what it already carries: the block keeps its iden, its
        data and every attribute, and only its classes change.
        ''',
     'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_getClasses', '_storfunc': '_setClasses',
              'returns': {'type': 'list', 'desc': 'The class names.'}}},
    {'name': 'attrs', 'desc': 'The key=value attributes on the opening fence.',
     'type': {'type': 'gtor', '_gtorfunc': '_getAttrs',
              'returns': {'type': 'dict', 'desc': 'The attributes.'}}},
    {'name': 'valu', 'desc': 'The markdown between the fences.',
     'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_getValu', '_storfunc': '_setValu',
              'returns': {'type': 'str', 'desc': 'The contained markdown.'}}},
)

@s_stormtypes.registry.registerType
class MarkdownDiv(MarkdownBlock):
    '''
    A fenced div: `::: {.class key="value"}` ... `:::`.
    '''
    _storm_typename = 'markdown:div'
    _storm_locals = getBlockLocals('div') + DIV_LOCALS

    def __init__(self, block, runt=None, path=None):
        MarkdownBlock.__init__(self, block, runt=runt, path=path)
        self.gtors.update({'classes': self._getClasses, 'attrs': self._getAttrs,
                           'valu': self._getValu})
        self.stors.update({'valu': self._setValu, 'classes': self._setClasses})

    async def _getClasses(self):
        return self.valu.getClasses()

    @s_stormtypes.stormfunc(readonly=True)
    async def _setClasses(self, valu):
        valu = await s_stormtypes.toprim(valu)

        if isinstance(valu, str):
            valu = (valu,)

        self.valu.setClasses([await s_stormtypes.tostr(name) for name in valu])

    async def _getAttrs(self):
        return self.valu.getAttrs()

    async def _getValu(self):
        return self.valu.getValu()

    @s_stormtypes.stormfunc(readonly=True)
    async def _setValu(self, valu):
        self.valu.setValu(await s_stormtypes.tostr(valu))

# What the block is, which `$block.data.type` does not change: that names how it rebuilds.
STORMBLOCK_TYPE_DESC = (' It names the block, not how it rebuilds, which is `$block.data.type`'
                        ' (`table`, `image`, `node` or `print`).')

STORMBLOCK_LOCALS = (
    {'name': 'refreshable', 'desc': '''
        Whether `refresh()` would rebuild this block.

        True when core has a renderer for the block's `data.type` (`table`, `image`, `node`, `print`)
        and it has a query to re-run in a mode core runs. `refresh()` raises with the reason when this
        answers false, so a caller sweeping a document can either filter or ask and be told.
        ''',
     'type': {'type': 'gtor', '_gtorfunc': '_getRefreshable',
              'returns': {'type': 'boolean', 'desc': 'True when refresh() would rebuild it.'}}},
    {'name': 'iden', 'desc': 'The block iden, which its data is stored under.',
     'type': {'type': 'gtor', '_gtorfunc': '_getIden',
              'returns': {'type': 'str', 'desc': 'The iden.'}}},
    {'name': 'title', 'desc': '''
        The block's `## Title` heading, or null when it has none.

        Setting it retitles the block and leaves its content alone; setting it to null removes the
        heading. A rebuild keeps the title it finds, so one set here survives `refresh()`.

        Examples:
            Retitle a block::

                $doc.block($iden).title = 'Known tools'
        ''',
     'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_getTitle', '_storfunc': '_setTitle',
              'returns': {'type': 'str', 'desc': 'The title, or null when it has none.'}}},
    {'name': 'data', 'desc': '''
        The data this block needs to rebuild itself, which lives outside the markdown.

        The source half is the same for every type: `type` (which names the renderer), `query` (as
        written, and may name variables), `vars`, `mode`, and `updated`. The render half is `opts`,
        which belongs to the type: a `table` keeps `columns` and the `form` its rows shared. A caller
        may add its own keys to either.

        Populated for a block this runtime built and for a document opened from a node. A document
        parsed from text alone starts with empty data, for a caller to assign here.
        ''',
     'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_getBlockData', '_storfunc': '_setBlockData',
              'returns': {'type': 'dict', 'desc': 'The data.'}}},
    {'name': 'vars', 'desc': '''
        The values this block's query names, bound when it runs.

        These are what `$block.data.vars` holds. A document has no vars of its own: see
        `$doc.setBlockVars()` to set the same names on every block at once.
        ''',
     'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_getVars', '_storfunc': '_setVars',
              'returns': {'type': 'dict', 'desc': 'The block\'s own vars.'}}},
    {'name': 'setVar', 'desc': '''
        Set one of this block's vars, leaving the rest as they are.

        Examples:
            Point a block at a different subject::

                $block.setVar(threat, $threat.repr())
        ''',
     'type': {'type': 'function', '_funcname': '_methSetVar',
              'args': (
                  {'name': 'name', 'type': 'str', 'desc': 'The variable name.'},
                  {'name': 'valu', 'type': 'prim', 'desc': 'The value to bind: anything JSON holds, lists and dicts included.'},
              ),
              'returns': {'type': 'null', 'desc': 'Returns null.'}}},
    {'name': 'popVar', 'desc': '''
        Remove one of this block's vars, leaving the rest as they are.
        ''',
     'type': {'type': 'function', '_funcname': '_methPopVar',
              'args': (
                  {'name': 'name', 'type': 'str', 'desc': 'The variable name.'},
              ),
              'returns': {'type': 'null', 'desc': 'Returns null.'}}},
    {'name': 'nodes', 'desc': '''
        Re-run this block's query and hand back the nodes, without touching its content.

        What `refresh()` runs, minus the rendering: the query with its variables bound, in a read only
        runtime, whatever `type` says. Path variables are not carried.
        ''',
     'type': {'type': 'function', '_funcname': '_methNodes',
              'returns': {'type': 'list', 'desc': 'The nodes the query produced.'}}},
    {'name': 'refresh', 'desc': '''
        Re-run this block's query and rebuild its content where it stands.

        The query runs with its stored variables bound, in a read only runtime. The opening fence is
        untouched, so the block keeps its iden, its position and its data. A type that knows what form
        it is of keeps only those rows, since its stored query may be a broader lift.
        ''',
     'type': {'type': 'function', '_funcname': '_methRefresh',
              'returns': {'type': 'int', 'desc': 'The number of rows it rebuilt.'}}},
)

@s_stormtypes.registry.registerType
class MarkdownStormBlock(MarkdownDiv):
    '''
    A block whose content came from a Storm query: a fenced div carrying an iden, plus the data that
    says how to rebuild it. The data travels with the block, so a block dropped from a document takes
    its data with it.
    '''
    _storm_typename = 'markdown:stormblock'
    _storm_locals = getBlockLocals('stormblock', desc=STORMBLOCK_TYPE_DESC) + DIV_LOCALS + STORMBLOCK_LOCALS

    def __init__(self, block, runt=None, path=None):
        MarkdownDiv.__init__(self, block, runt=runt, path=path)

        self.gtors.update({'iden': self._getIden, 'title': self._getTitle,
                           'data': self._getBlockData, 'vars': self._getVars,
                           'refreshable': self._getRefreshable})
        self.stors.update({'data': self._setBlockData, 'vars': self._setVars,
                           'title': self._setTitle})

    def getObjLocals(self):
        return {'nodes': self._methNodes, 'refresh': self._methRefresh,
                'setVar': self._methSetVar, 'popVar': self._methPopVar}

    async def _getVars(self):
        return dict(self.valu.data.get('vars') or {})

    @s_stormtypes.stormfunc(readonly=True)
    async def _setVars(self, valu):
        valu = await s_stormtypes.toprim(valu)
        await self._editVars(lambda varz: valu)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSetVar(self, name, valu):
        name = await s_stormtypes.tostr(name)
        valu = await s_stormtypes.toprim(valu)
        await self._editVars(lambda varz: {**varz, name: valu})

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPopVar(self, name):
        name = await s_stormtypes.tostr(name)
        await self._editVars(lambda varz: {k: v for (k, v) in varz.items() if k != name})

    async def _editVars(self, func):
        '''
        Replace this block's vars with what `func` makes of them, validated.

        One path for all three setters, so a var that cannot be stored is refused where it is set
        rather than at the next save.
        '''
        data = dict(self.valu.data)
        data['vars'] = func(data.get('vars') or {})
        self.valu.data = reqBlockData(data)

    async def _getIden(self):
        return self.valu.getIden()

    async def _getTitle(self):
        return self.valu.getTitle()

    @s_stormtypes.stormfunc(readonly=True)
    async def _setTitle(self, valu):
        self.valu.setTitle(await s_stormtypes.tostr(valu, noneok=True))

    async def _getBlockData(self):
        return dict(self.valu.data)

    @s_stormtypes.stormfunc(readonly=True)
    async def _setBlockData(self, valu):
        valu = await s_stormtypes.toprim(valu)
        self.valu.data = reqBlockData(valu)

    def _reqQuery(self):
        '''
        The query text to re-run, or an error saying why this block has none.

        Everything a re-run needs regardless of the block's type: `nodes()` stops here, and `refresh()`
        goes on to ask whether core can render the result.
        '''
        data = self.valu.data

        # A block's data lives beside the markdown, so a document parsed from bare text has blocks
        # with none. Said plainly, since the cause is elsewhere.
        if not data:
            mesg = f'storm block {self.valu.getIden()} has no data to rebuild from'
            raise s_exc.BadArg(mesg=mesg, iden=self.valu.getIden())

        # A lookup query is raw values rather than Storm, and is turned into lifts a layer above this
        # one, so running its text here would run something else entirely.
        if data.get('mode') == 'lookup':
            mesg = 'a lookup-mode storm block cannot be refreshed yet'
            raise s_exc.BadArg(mesg=mesg, mode='lookup')

        text = data.get('query')
        if text is None:
            mesg = f'storm block {self.valu.getIden()} has no query to re-run'
            raise s_exc.BadArg(mesg=mesg, iden=self.valu.getIden())

        return text

    def _reqRefreshable(self):
        '''
        The query text to re-run, or an error saying why this block cannot be rebuilt by core.

        The one place the rule lives: `refreshable` answers it as a boolean, and this raises with the
        reason.
        '''
        text = self._reqQuery()

        # A type core has no entry for belongs to whoever wrote it, which rebuilds by setting the
        # block's content directly from `nodes()`.
        data = self.valu.data
        if STORM_BLOCK_TYPES.get(data.get('type')) is None:
            mesg = f'core does not render a {data.get("type")} storm block'
            raise s_exc.BadArg(mesg=mesg, type=data.get('type'))

        return text

    async def _getRefreshable(self):
        try:
            self._reqRefreshable()
        except s_exc.BadArg:
            return False

        return True

    def _runVars(self):
        '''
        What this block's query runs with: exactly what is stored beside the query.

        There is no second scope to merge, since a document has no vars of its own. `markdown:doc` has
        `setBlockVars()` and friends for setting the same names across a whole document in one call.
        '''
        return dict(self.valu.data.get('vars') or {})

    @s_stormtypes.stormfunc(readonly=True)
    async def _methNodes(self):

        text = self._reqQuery()

        if self.runt is None:  # pragma: no cover
            mesg = 'this block has no runtime to run its query with'
            raise s_exc.BadArg(mesg=mesg)

        items = await runBlockNodes(self.runt, text, self._runVars())

        return s_stormtypes.List([s_stormtypes.Node(node) for (node, path) in items])

    @s_stormtypes.stormfunc(readonly=True)
    async def _methRefresh(self):

        data = self.valu.data

        text = self._reqRefreshable()

        if self.runt is None:  # pragma: no cover
            mesg = 'this block has no runtime to run its query with'
            raise s_exc.BadArg(mesg=mesg)

        rend = STORM_BLOCK_TYPES[data['type']]

        items = await rend['run'](self.runt, text, self._runVars())

        text, count = await rend['render'](items, data, self.runt.model)

        self.valu.setContent(text)

        # Stamped on the way out, so a document says when each of its blocks last saw the graph.
        data = dict(data)
        data['updated'] = s_common.now()
        self.valu.data = reqBlockData(data)

        # What the block shows, which is not always what the query yielded: a renderer that keeps only
        # some rows is the one that can say how many it drew.
        return count

BLOCK_TYPES = {
    'stormblock': MarkdownStormBlock,
    'heading': MarkdownHeading,
    'paragraph': MarkdownParagraph,
    'code': MarkdownCode,
    'list': MarkdownList,
    'table': MarkdownTable,
    'div': MarkdownDiv,
}

def wrapBlock(block, runt=None, path=None):
    '''
    The Storm object for an mdparse Block.
    '''
    ctor = BLOCK_TYPES.get(block.kind, MarkdownBlock)
    return ctor(block, runt=runt, path=path)

# The interface a node must implement to hold a markdown document: it declares the `body` the markdown
# lives in. Nothing here knows about a particular form.
DOCUMENT_IFACE = 'doc:document'

# Where a storm block's data is stored, as nodedata named for the block's iden. one name and not a
# parameter, so a document's blocks are addressed the same way wherever the document lives.
BLOCK_PREFIX = 'md:block:'

# The fence class every storm block is written with. one class for every type, because what makes a
# fenced div a storm block is its `iden` (`mdparse.promoteDiv`) and what kind it is lives in the data
# that iden addresses. A class per type would be a second copy of `data.type` with nothing keeping the
# two honest. A caller with its own vocabulary still passes `classes=`.
STORM_BLOCK_CLASS = 'storm-block'

# The most rows a block may rebuild from. A stored query is re-run against a graph that has grown
# since, so without a bound a table written as `inet:fqdn` rebuilds as large as the Cortex. Refusing
# beats truncating: a table silently showing the first N rows of many is a table that lies.
BLOCK_MAX_ROWS = 5000

# The column kinds a storm table can project, and the field each names its source with.
COLUMN_KINDS = {
    'form': None,          # the node's primary value
    'prop': 'prop',        # a secondary property, or a dotted virtual property of one
    'virt': 'virt',        # a virtual property of the row form's own type (`.port` of an inet:server)
    'meta': 'meta',        # a metadata property, which every node has (`.created`, `.updated`)
    'tag': 'tag',          # one bound of a tag's interval, `index` naming which
    'tagglob': 'tagglob',  # the leaf tags matching a glob
    'edge': 'edge',        # how many light edges of a verb the node has
    'embed': 'embed',      # a property of a node this one pivots to
    'pathvar': 'pathvar',  # a variable from the path the node arrived on
}

# The column a storm table falls back on when the form declares none: one column of primary values.
# There is no form to name a column after until the query has run, so the header is the generic "Node".
DEFAULT_COLUMN = {'type': 'form'}

def displayStormColumns(display):
    '''
    Storm table columns for what a form's `display` declares, which is a different shape: the model
    says `{"type": "prop", "opts": {"name": ...}}` and has only the one type, whose `name` may be an
    embed path. A type the model grows later is skipped rather than refused.
    '''
    out = []
    for col in display.get('columns', ()):

        if col.get('type') != 'prop':
            continue

        name = col.get('opts', {}).get('name')
        if name is None:  # pragma: no cover
            continue

        if '::' in name:
            out.append({'type': 'embed', 'embed': name})
        else:
            out.append({'type': 'prop', 'prop': name})

    return out

def defaultStormColumns(model, form):
    '''
    The columns a storm table falls back on when the caller named none: the ones the form declares,
    and one column of primary values for a form that declares nothing. Resolved once, at build, and
    stored concrete, so a form that later declares different ones does not reshape a written table.
    '''
    if model is None or form is None:
        return [DEFAULT_COLUMN]

    # `stormtable` refuses a form the model does not have upstream, so this is for a caller assembling
    # columns itself against a form that has since been removed.
    formtype = model.type(form)
    if formtype is None:
        return [DEFAULT_COLUMN]

    display = formtype.info.get('display')
    if display is None:
        return [DEFAULT_COLUMN]

    return displayStormColumns(display) or [DEFAULT_COLUMN]

def _getColType(col):
    '''
    The kind a column names, from its `type` or from the shape of what it carries.

    A column may be written as a prop path instead -- `:name`, `.name`, a dotted virtual property --
    which is normalised into the prop-ish kinds here.
    '''
    kind = col.get('type')
    if kind is not None:
        if kind not in COLUMN_KINDS:
            mesg = f'unknown storm table column type {kind}, expected one of {sorted(COLUMN_KINDS)}'
            raise s_exc.BadArg(mesg=mesg, type=kind)

        return kind

    for kind, field in COLUMN_KINDS.items():
        if field is not None and col.get(field) is not None:
            return kind

    # a column with neither a type nor a source names its prop with its header
    return 'prop'

def _defColName(col, form=None):
    '''
    The header for a column a caller did not name, in the vocabulary of the kind it is.

    `col` is a normalised column, so its `type` names its kind.

    A form column shows the row's primary value, so its header is the form, which is only knowable once
    the rows have arrived. `Node` is the fallback for a mixed lift or a table built without a query.
    '''
    kind = col['type']

    if kind == 'form':
        return form if form is not None else 'Node'

    if kind == 'prop':
        return f':{col["prop"].lstrip(":")}'

    if kind in ('virt', 'meta'):
        return f'.{col[COLUMN_KINDS[kind]]}'

    # The three below are spelled as the Optic table view spells them, so a column nobody named is
    # headed the same whether it was drawn in a browser or rebuilt here. Differing renamed such a
    # column on every refresh, and dropped any stored sort that named it.
    if kind == 'tag':
        indx = col.get('index')
        if indx is None:
            return f'#{col["tag"]}'

        bound = 'min' if indx == 0 else 'max'
        return f'#({col["tag"]}).{bound}'

    if kind == 'tagglob':
        return f'#{col["tagglob"]}'

    if kind == 'edge':
        verb, target = col['edge'][0], None
        if len(col['edge']) > 1:
            target = col['edge'][1]

        arrow = f'<({verb})-' if len(col['edge']) > 2 and col['edge'][2] else f'-({verb})>'

        return f'{arrow} {target if target else "*"}'

    if kind == 'embed':
        return f':{col["embed"]}'

    return f'${col["pathvar"]}'

def normStormColumns(columns, form=None, model=None):
    '''
    Column definitions for a storm table: what fills each column's cells, plus how they are drawn.

    A column names its source by kind (see COLUMN_KINDS) or as a prop path: `:name` (or a bare name)
    for a secondary property, `.name` for a metadata property, and a dotted tail for a virtual
    property. The primary value is not a prop, and is named by its kind alone.

    Naming no columns takes the form's own declared display columns.
    '''
    columns = columns or defaultStormColumns(model, form)

    out = []
    for col in columns:

        if isinstance(col, str):
            col = {'name': col, 'prop': col}

        if not isinstance(col, dict):
            mesg = 'storm table column must be a str or dict'
            raise s_exc.BadArg(mesg=mesg, column=col)

        col = dict(col)
        kind = _getColType(col)

        prop = None
        if kind == 'prop':
            prop = col.get('prop') or col.get('name')

        # The prop path spellings, normalised into the kind each one means. A column carrying no path
        # is left alone: the required-field check below names what it is missing.
        if prop is not None:

            # The primary value is not a prop, and has one spelling. Refused rather than read as a
            # property nothing has, since both of these look like they name it.
            if prop == '*' or prop == form:
                mesg = ('a storm table column for the primary value is {"type": "form"},'
                        f' not a "prop" of {prop!r}')
                raise s_exc.BadArg(mesg=mesg, column=col)

            if prop.startswith('.'):
                kind, col['meta'] = 'meta', prop[1:]
                col.pop('prop', None)

            else:
                col['prop'] = prop.lstrip(':')

        col['type'] = kind

        field = COLUMN_KINDS[kind]
        if field is not None and col.get(field) is None:
            mesg = f'a {kind} storm table column requires a "{field}"'
            raise s_exc.BadArg(mesg=mesg, column=col)

        if kind == 'tag' and col.get('index') not in (None, 0, 1):
            mesg = 'a tag storm table column index must be 0 (min) or 1 (max)'
            raise s_exc.BadArg(mesg=mesg, column=col)

        # Checked here as well as against each row, since a table over a query that yielded nothing has
        # no row to check against and its typo would otherwise surface a month later.
        if kind == 'meta' and model is not None and col['meta'] not in model.metatypes:
            mesg = f'a meta storm table column names a metadata property, and {col["meta"]} is not one'
            raise s_exc.BadArg(mesg=mesg, name=col['meta'], metas=sorted(model.metatypes))

        if kind == 'virt' and model is not None and form is not None:

            formtype = model.type(form)
            if formtype is not None and col['virt'] not in formtype.virts:
                mesg = f'a virt storm table column names a virtual property of {form}, and {col["virt"]} is not one'
                raise s_exc.BadArg(mesg=mesg, name=col['virt'], form=form,
                                   virts=sorted(formtype.virts))

        if col.get('name') is None:
            col['name'] = _defColName(col, form=form)

        # the markdown half is validated and coerced by the table's own norm, which keeps only what it
        # draws -- so the source half is carried over from the column as written, minus the keys that
        # norm accepted and deliberately did not keep
        (coldef,) = s_mdparse.normColumns([col])
        drop = s_mdparse.COLUMN_KEYS + s_mdparse.COLUMN_DROPPED
        coldef.update({k: v for (k, v) in col.items() if k not in drop})

        out.append(coldef)

    return out

def fmtCellValu(valu):
    '''
    A cell's display value, as a string.

    An array prop reprs as a list of its elements, which is not a display value: it is written in
    Storm's own tuple spelling instead, as `(a, b)`, `(a,)` for one, and `()` for none.
    '''
    if not isinstance(valu, (list, tuple)):
        return str(valu)

    if not valu:
        return '()'

    if len(valu) == 1:
        return f'({valu[0]},)'

    return f'({", ".join(str(v) for v in valu)})'

async def projectCell(node, path, col, model):
    '''
    One cell for a node, from the column that says which of its values to show.
    '''
    kind = col['type']

    if kind == 'form':
        return node.repr()

    if kind == 'prop':
        prop = col['prop']

        # A column named for the node's own form is the primary value. A single-form table norms this
        # to a `form` column before anything is projected and a mixed one cannot carry a form-specific
        # prop, so this is for a caller that assembled coldefs itself.
        if prop == node.form.name:  # pragma: no cover
            return node.repr()

        return fmtCellValu(node.repr(prop, ''))

    # `virt` and `meta` are both read as `.name` but are not the same namespace: a virt belongs to the
    # row's own type and a meta to every node. normStormColumns checks both against the model, so this
    # is the case it cannot: a table with no stored form whose virts differ row by row.
    if kind == 'virt':
        name = col['virt']
        if name not in node.form.type.virts:
            mesg = f'a virt storm table column names a virtual property of {node.form.name}, and {name} is not one'
            raise s_exc.BadArg(mesg=mesg, name=name, form=node.form.name,
                               virts=sorted(node.form.type.virts))

        return fmtCellValu(node.repr(f'.{name}', ''))

    if kind == 'meta':
        return fmtCellValu(node.repr(f'.{col["meta"]}', ''))

    if kind == 'tag':
        ival = node.getTag(col['tag'])
        if ival is None:
            return ''

        # `== 1` rather than truthiness: an index is a position. normStormColumns rejects anything
        # outside (None, 0, 1), so this only matters for a caller assembling coldefs itself.
        valu = ival[1] if col.get('index') == 1 else ival[0]
        if valu is None:
            return ''

        return model.type('time').repr(valu)

    if kind == 'tagglob':
        globs = s_cache.TagGlobs()
        globs.add(col['tagglob'], True)

        # leafed, as the node card and the table view are: a matching parent whose child also matches
        # would otherwise be listed twice over
        tags = [tag for (tag, valu) in node.getTags(leaf=True) if globs.get(tag)]

        # `#` prefixed and space separated, as a tag is written in Storm. A comma-joined list read as
        # prose rather than as tags.
        return ' '.join(f'#{tag}' for tag in sorted(tags))

    if kind == 'edge':
        edge = col['edge']

        verb = edge[0]
        form = edge[1] if len(edge) > 1 else None
        n2 = bool(edge[2]) if len(edge) > 2 else False

        counts = node.getEdgeCounts(verb, n2=n2).get(verb, {})
        if form is not None:
            return str(counts.get(form, 0))

        return str(sum(counts.values()))

    if kind == 'embed':
        return await _embedCell(node, col['embed'])

    # runBlockNodes always yields a path with its node, so this is for a caller projecting rows it
    # assembled itself.
    if path is None:  # pragma: no cover
        return ''

    # `getVar` answers with the novalu sentinel for a name the path never had -- and ignores its own
    # `defv` doing it -- so the sentinel is what gets checked rather than None.
    valu = path.getVar(col['pathvar'])
    if valu is None or valu is s_common.novalu:
        return ''

    if (styp := model.type(col.get('pathvartype'))) is not None:
        return styp.repr(valu)

    return fmtCellValu(valu)

async def _embedCell(node, embed):
    '''
    A property of the node this one pivots to, through the `::` path an embed names.
    '''
    if '::' not in embed:
        mesg = f'an embed column names a pivot path and a property, as "org::name", got {embed}'
        raise s_exc.BadArg(mesg=mesg, embed=embed)

    steps, prop = embed.rsplit('::', 1)

    # the walk itself is the node's, so an embed column resolves exactly the pivots an embed does
    embeds = await node.getEmbeds({steps: (prop,)})

    info = embeds.get(steps)
    if info is None:
        return ''

    step = await node.view.getNodeByNid(s_common.int64en(info['$nid']))
    if step is None:  # pragma: no cover
        return ''

    return fmtCellValu(step.repr(prop, ''))

def reqTableForm(items, form=None):
    '''
    The one form a table is of, from the rows its query yielded.

    A table is always of a single form, and the renderer keeps only the rows belonging to it, so a
    rebuild against a grown graph still describes the same table. When the caller names the form, the
    rows are filtered to it.

    Otherwise the rows have to agree. A lift spanning several forms is refused rather than guessed, and
    so is one yielding nothing: a table built without a form never filters on a rebuild and is headed
    `Node` forever.
    '''
    forms = {node.form.name for (node, path) in items}

    if form is not None:
        # `formtypes` rather than an equality check, so a node of a form that inherits the named one
        # still belongs. The same rule the renderer applies on a rebuild.
        return form, [(node, path) for (node, path) in items if form in node.form.formtypes]

    if len(forms) > 1:
        mesg = (f'a storm table is of one form, and this query yielded {" and ".join(sorted(forms))}:'
                ' name the one you meant with form=')
        raise s_exc.BadArg(mesg=mesg, forms=sorted(forms))

    if forms:
        return forms.pop(), items

    mesg = ('a storm table is of one form, and this query yielded no rows to take it from:'
            ' name it with form=')
    raise s_exc.BadArg(mesg=mesg)

async def projectRow(node, path, columns, model):
    '''
    One table row of display values for a node, one cell per column.
    '''
    row = []
    for col in columns:
        row.append(await projectCell(node, path, col, model))

    return row

# The two types whose stored value is a decimal string, so putting them in order means reading the
# number rather than the text: '10' sorts before '9' otherwise. Everything else is stored as a number
# or as a tuple of them, and already orders correctly.
SORT_DECIMAL_TYPES = ('hugenum', 'econ:price')

# The order values of different shapes take relative to one another, so a column holding more than one
# is still totally ordered rather than raising. Missing is not in here: it is carried separately, so
# it can sort last in both directions.
_sortranks = {bool: 0, int: 0, float: 0, decimal.Decimal: 0, str: 1, bytes: 2}

def sortValu(valu):
    """
    A cell's stored value as something totally ordered.

    Sorting stored values rather than display strings is what makes an IP address, a price and a time
    order by what they are rather than by how they are written. Values of different shapes are ranked
    by shape first, so a column holding a mix orders deterministically instead of raising.
    """
    # A poly property answers with (type, value), so the value arrives already saying what it is.
    if isinstance(valu, tuple) and len(valu) == 2 and valu[0] in SORT_DECIMAL_TYPES:
        return (0, decimal.Decimal(valu[1]))

    if isinstance(valu, (tuple, list)):
        return (3, tuple(sortValu(item) for item in valu))

    return (_sortranks.get(type(valu), 4), valu)

async def sortCell(node, path, col, model):
    """
    The value a sort orders a row by: what is behind the cell, where there is such a thing.

    A column whose cell is assembled rather than read -- a tagglob, an edge count, an embed -- has no
    single stored value, so it orders by the text it displays.
    """
    kind = col['type']

    if kind == 'form':
        return node.ndef[1]

    if kind == 'prop':
        return node.get(col['prop'])

    if kind == 'meta':
        return node.get(f'.{col["meta"]}')

    if kind == 'virt':
        return node.get(f'.{col["virt"]}')

    if kind == 'tag':
        ival = node.getTag(col['tag'])
        if ival is None:
            return None

        return ival[1] if col.get('index') == 1 else ival[0]

    return await projectCell(node, path, col, model)

async def sortItems(items, col, direction, model):
    """
    The rows in the order a sort puts them, ordered by the values behind one column's cells.

    A row with nothing in the column sorts as the smallest value: first ascending and last descending.
    """
    reverse = direction == 'desc'

    keyed = []
    for indx, (node, path) in enumerate(items):

        valu = await sortCell(node, path, col, model)

        # Ranked ahead of every value rather than compared against them, so an empty cell never has
        # to compare against a number.
        if valu is None or valu == '':
            key = (0, ())
        else:
            key = (1, sortValu(valu))

        # The lift position breaks a tie and reverses along with everything else, so two rows the sort
        # cannot tell apart swap when the column is reversed.
        keyed.append(((*key, indx), (node, path)))

    keyed.sort(key=lambda item: item[0], reverse=reverse)

    return [item for (_, item) in keyed]

def normStormSort(sort, columns):
    '''
    A table's sort order: which of its columns the rows are in the order of, and which way.

    Written as a column name, `({"name": ..., "direction": "asc"|"desc"})` to say which way, or
    `({"index": (2)})` to name a column by position. A list of those is accepted and stored, but only
    the first is applied.

    A sort naming a column the table does not have is dropped rather than refused, which keeps a table
    whose columns were edited rendering instead of raising.
    '''
    if sort is None:
        return None

    if not isinstance(sort, (list, tuple)):
        sort = [sort]

    names = [col['name'] for col in columns]

    out = []
    for item in sort:

        if isinstance(item, str):
            item = {'name': item}

        if not isinstance(item, dict):
            mesg = 'a storm table sort must be a str or dict'
            raise s_exc.BadArg(mesg=mesg, sort=item)

        name = item.get('name')
        indx = item.get('index')

        if (name is None) == (indx is None):
            mesg = ('a storm table sort names one of the table columns, by "name" or by "index"'
                    ' and not both')
            raise s_exc.BadArg(mesg=mesg, sort=item, columns=names)

        direction = item.get('direction', 'asc')
        if direction not in ('asc', 'desc'):
            mesg = f'a storm table sort direction is "asc" or "desc", got {direction}'
            raise s_exc.BadArg(mesg=mesg, direction=direction)

        if name is not None:
            out.append({'name': name, 'direction': direction})
            continue

        indx = s_common.intify(indx)
        if indx is None or indx < 0:
            mesg = f'a storm table sort index is a column position, got {item.get("index")}'
            raise s_exc.BadArg(mesg=mesg, sort=item)

        out.append({'index': indx, 'direction': direction})

    return out or None

def normStormFilter(filters, columns):
    '''
    A table's column filters: which of a column's values are held back from its rows.

    Written as `({"name": ..., "hide": (...)})`, or `({"index": (2), "hide": (...)})` to name a column
    by position. The values are the cell text a reader sees, since that is all a markdown table holds.

    Values are hidden rather than kept so that a rebuild shows a value the graph grew after the filter
    was set: a filter says what its author had seen and did not want, not what may ever appear. A
    filter naming a column the table does not have is dropped rather than refused, the same as a sort.
    '''
    if filters is None:
        return None

    if not isinstance(filters, (list, tuple)):
        filters = [filters]

    names = [col['name'] for col in columns]

    out = []
    for item in filters:

        if not isinstance(item, dict):
            mesg = 'a storm table filter must be a dict'
            raise s_exc.BadArg(mesg=mesg, filter=item)

        name = item.get('name')
        indx = item.get('index')

        if (name is None) == (indx is None):
            mesg = ('a storm table filter names one of the table columns, by "name" or by "index"'
                    ' and not both')
            raise s_exc.BadArg(mesg=mesg, filter=item, columns=names)

        hide = item.get('hide')
        if not isinstance(hide, (list, tuple)):
            mesg = 'a storm table filter hides a list of cell values'
            raise s_exc.BadArg(mesg=mesg, filter=item)

        # The cell values as a table writes them, so a caller may hand over the numbers a column of
        # them displays. An empty cell is what a missing value shows as.
        hide = ['' if valu is None else str(valu) for valu in hide]

        if name is not None:
            out.append({'name': name, 'hide': hide})
            continue

        indx = s_common.intify(indx)
        if indx is None or indx < 0:
            mesg = f'a storm table filter index is a column position, got {item.get("index")}'
            raise s_exc.BadArg(mesg=mesg, filter=item)

        out.append({'index': indx, 'hide': hide})

    return out or None

def _filterHides(filters, columns):
    '''
    What each column holds back, by column position. A filter naming a column the table does not have
    is dropped, the same as a sort.
    '''
    hides = {}

    for item in filters or ():

        indx = item.get('index')
        if indx is None:
            indx = next((i for (i, col) in enumerate(columns) if col['name'] == item['name']), None)

        if indx is None or indx >= len(columns):
            continue

        hides.setdefault(indx, set()).update(item['hide'])

    return hides

def _sortColumn(sort, columns):
    '''
    The column a sort orders by, or None when it names one the table does not have.
    '''
    if not sort:
        return None, None

    direction = sort[0]['direction']

    indx = sort[0].get('index')
    if indx is not None:
        if indx < len(columns):
            return columns[indx], direction

        return None, None

    name = sort[0]['name']
    for col in columns:
        if col['name'] == name:
            return col, direction

    return None, None

async def projectTable(items, columns, model, form=None, sort=None, filters=None):
    '''
    A markdown Table of nodes projected through `columns`, from the (node, path) pairs a query yielded.

    `form` only names a column the caller did not name, so it is optional: a block stored before a
    table had to know its form has none to read, and requiring one would leave it unable to rebuild.

    `sort` orders the rows before they are projected, so the order comes from the values rather than
    from the strings they display.

    `filters` hold back the rows whose cell in a column is one of the values that column hides.
    '''
    columns = normStormColumns(columns, form=form, model=model)

    sortcol, direction = _sortColumn(normStormSort(sort, columns), columns)
    if sortcol is not None:
        items = await sortItems(items, sortcol, direction, model)

    hides = _filterHides(normStormFilter(filters, columns), columns)

    tabl = s_mdparse.newTable(columns)
    for node, path in items:

        cells = await projectRow(node, path, columns, model)

        # A filter is over rows: a cell a column holds back takes its whole row out of the table.
        if any(cells[indx] in hide for (indx, hide) in hides.items()):
            continue

        tabl.addRow(cells)

    return tabl

async def renderBlockTable(items, data, model):
    '''
    The markdown for a `table` storm block: the rows its query lifted, projected through its columns,
    and how many rows that was.
    '''
    opts = data.get('opts') or {}

    # A table's stored query is not always a lift of one form: one added from a tabular view of
    # `.created` re-runs as every form in the graph. So the rows a rebuild projects are the ones the
    # table is of. `formtypes` rather than equality, so an inheriting form still belongs.
    form = opts.get('form')
    if form is not None:
        items = [(node, path) for (node, path) in items if form in node.form.formtypes]

    else:
        # A block stored before a table had to name its form. Nothing to filter to, so it keeps every
        # row, and the form is taken from the rows only to name the columns.
        forms = {node.form.name for (node, path) in items}
        if len(forms) == 1:
            form = forms.pop()

    tabl = await projectTable(items, opts.get('columns'), model, form=form, sort=opts.get('sort'),
                              filters=opts.get('filters'))

    # The rows it drew, which a filter makes fewer than the query yielded.
    return tabl.text, len(tabl.getRows())

# A stored column filter: which column, named by `name` or by `index`, and the cell values it holds
# back. Open for the same reason as the column above.
STORM_FILTER_SCHEMA = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'index': {'type': 'integer'},
        'hide': {'type': 'array'},
    },
    'additionalProperties': True,
}

# The render options a `table` keeps. A rebuild does not need `form` -- the query says what it lifts
# -- but it is what defaults the columns, and what a consumer putting the rows back in a typed view
# reads.
# One stored column: which value fills its cells, and how it is drawn.
#
# Deliberately loose, and nothing here is required. What is stored is the column as declared, not as
# normalised: `{"name": "Host", "prop": ":host"}` is a whole column, and which kind it is falls out
# of the path when the table renders. This is also a read gate (`MarkdownDoc.initBlockData` runs
# `reqBlockData` over every block a document opens), so anything refused here is a document that will
# not open. The vocabulary is enforced where it can say what is wrong instead, by `_getColType` at build
# and rebuild; a caller keeping its own keys on a column relies on the same openness.
STORM_COLUMN_SCHEMA = {
    'type': 'object',
    'properties': {
        'type': {'type': 'string'},
        'name': {'type': 'string'},
        'justify': {'type': 'string'},
        'width': {'type': 'integer'},
        'prop': {'type': 'string'},
        'virt': {'type': 'string'},
        'meta': {'type': 'string'},
        'tag': {'type': 'string'},
        'tagglob': {'type': 'string'},
        'embed': {'type': 'string'},
        'pathvar': {'type': 'string'},
        'edge': {'type': 'array'},
    },
    'additionalProperties': True,
}

# A stored sort: which column the rows are in the order of, named by `name` or by `index`, and which
# way. Open for the same reason as the column above.
STORM_SORT_SCHEMA = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'index': {'type': 'integer'},
        'direction': {'type': 'string'},
    },
    'additionalProperties': True,
}

TABLE_OPTS_SCHEMA = {
    'type': 'object',
    'properties': {
        'columns': {'type': 'array', 'items': STORM_COLUMN_SCHEMA},
        'form': {'type': 'string'},
        'sort': {'type': 'array', 'items': STORM_SORT_SCHEMA},
        'filters': {'type': 'array', 'items': STORM_FILTER_SCHEMA},
    },
    'additionalProperties': True,
}

async def renderBlockImage(valu, data, model):
    '''
    The markdown for an `image` storm block: the image its query named, and 1 if it drew one.

    The query returns the sha256 of the file to show. The URL is built from a template in the block's
    opts, since the route that serves a file is the deployment's business.
    '''
    opts = data.get('opts') or {}

    urltmpl = opts.get('urltmpl')
    if urltmpl is None:
        mesg = 'an image storm block needs an urltmpl in its opts to rebuild'
        raise s_exc.BadArg(mesg=mesg)

    alt = opts.get('alt') or ''
    attrs = opts.get('attrs')

    # A query that returned nothing leaves the block empty rather than drawing a hole in the URL: the
    # file it names may simply not be there yet.
    if valu is None:
        return '', 0

    if not isinstance(valu, str):
        mesg = f'an image storm block query must return a sha256, got {valu.__class__.__name__}'
        raise s_exc.BadArg(mesg=mesg)

    return s_mdparse.fmtImage(urltmpl.replace('{valu}', valu), alt=alt, attrs=attrs), 1

# The render options an `image` keeps: where the bytes are served from, and how the image is drawn.
IMAGE_OPTS_SCHEMA = {
    'type': 'object',
    'properties': {
        'urltmpl': {'type': 'string'},
        'alt': {'type': 'string'},
        'attrs': {'type': 'string'},
    },
    'additionalProperties': True,
}

async def renderBlockNode(items, data, model):
    '''
    The markdown for a `node` storm block: one node as a flipped name/value table, and how many it drew.

    Flipped because the subject is a single node: a row per property reads down the page where a wide
    single-row table would run off it. The rows are what it is, its value, its secondary props, its
    metadata, and its tags.

    Renders the first row its query yields, so a stored lift that has come to match several still
    rebuilds.
    '''
    if not items:
        # A node that has been deleted leaves the block saying so, rather than an empty table that
        # reads as a node with no properties.
        mesg = 'a node storm block found no node to rebuild from'
        raise s_exc.BadArg(mesg=mesg)

    node, path = items[0]

    rows = [
        ['form', node.form.name],
        [node.form.name, node.repr()],
    ]

    for name in sorted(node.getProps()):

        # Secondary props only: an embed needs a resolved sub-node and a virt is a derived part of a
        # prop already listed.
        prop = node.form.prop(name)
        if prop is None or prop.isrunt:  # pragma: no cover
            continue

        valu = node.repr(name, None)
        if valu is None:  # pragma: no cover
            continue

        rows.append([f':{name}', valu])

    for name in sorted(node.getMetaDict()):
        valu = node.repr(f'.{name}', None)
        if valu is not None:
            rows.append([f'.{name}', valu])

    for tag, ival in sorted(node.getTags()):
        rows.append([f'#{tag}', fmtTagIval(ival, model)])

    tabl = s_mdparse.newTable([{'name': 'name'}, {'name': 'value'}])
    for row in rows:
        tabl.addRow(row)

    return tabl.text, 1

def fmtTagIval(ival, model):
    '''
    A tag's interval the way a node view shows one: `(min, max)`, with `null` for an unbounded end.

    A tag's interval is always the (min, max, duration) triple, with every part None on a tag that
    has no interval, so the duration is the only part left out.
    '''
    timetype = model.type('time')
    parts = [timetype.repr(part) if part is not None else 'null' for part in ival[:2]]

    return f'({parts[0]}, {parts[1]})'

# A `node` block renders one node's own properties, so it has nothing to configure.
NODE_OPTS_SCHEMA = {
    'type': 'object',
    'additionalProperties': True,
}

# A `print` block's query writes its own markdown, so there is nothing to configure either.
PRINT_OPTS_SCHEMA = {
    'type': 'object',
    'additionalProperties': True,
}

async def renderBlockPrint(items, data, model):
    '''
    The lines a block's query printed, as the markdown it wrote.

    No projection: the query is the renderer, which is why this type takes no opts.
    '''
    return '\n'.join(items), len(items)

async def runBlockNodes(runt, text, varz):
    '''
    Run a storm block's query and hand back the (node, path) pairs it yielded.

    The paths come along because a column may name one of their variables.

    Read-only is forced rather than inherited: neither building a block nor rebuilding one may edit the
    graph. Both go through here, so a block shows the same rows built as rebuilt. Bounded at
    BLOCK_MAX_ROWS, and refuses rather than truncating: a truncated table is a table that lies.
    '''
    items = []
    query = await runt.getStormQuery(text)

    async with runt.getCmdRuntime(query, opts={'vars': varz or {}}) as subr:
        subr.readonly = True

        # A `return()` ends the block's query, not whatever built or refreshed the block.
        try:
            async for item in subr.execute():

                items.append(item)

                if len(items) > BLOCK_MAX_ROWS:
                    mesg = f'a storm block may rebuild from at most {BLOCK_MAX_ROWS} rows; add a limit to its query'
                    raise s_exc.BadArg(mesg=mesg, limit=BLOCK_MAX_ROWS)

        except s_stormctrl.StormReturn:
            pass

    return items

async def runBlockPrints(runt, text, varz):
    '''
    Run a storm block's query and hand back the lines it printed.

    The same guarantees `runBlockNodes` gives -- read-only, forced rather than inherited, and bounded
    -- with the query's print messages as the result instead of its nodes. They are captured rather
    than forwarded, since they are the block's content.
    '''
    lines = []
    query = await runt.getStormQuery(text)

    async with runt.getCmdRuntime(query, opts={'vars': varz or {}}) as subr:

        subr.readonly = True

        # Its own bus, sharing only the warn-once set: `print` fires on the bus, and the caller's is
        # where it would otherwise land.
        subr.bus = subr
        subr._warnonce_keys = runt.bus._warnonce_keys

        # A `return()` ends the block's query, not whatever built or refreshed the block.
        async def execute():
            try:
                async for _ in subr.execute():
                    await asyncio.sleep(0)

            except s_stormctrl.StormReturn:
                pass

        # Cancelled rather than raised in: the bus logs what a handler raises, and a query that prints
        # without yielding a node gives the caller nowhere else to stop it.
        def onprint(mesg):
            lines.append(mesg[1].get('mesg'))

            if len(lines) > BLOCK_MAX_ROWS:
                task.cancel()

        with subr.onWith('print', onprint):
            task = subr.schedCoro(execute())
            await asyncio.wait((task,))

        # the query's own error, unless it was cancelled for printing too much
        if len(lines) <= BLOCK_MAX_ROWS:
            task.result()

    if len(lines) > BLOCK_MAX_ROWS:
        mesg = f'a storm block may print at most {BLOCK_MAX_ROWS} lines; print less'
        raise s_exc.BadArg(mesg=mesg, limit=BLOCK_MAX_ROWS)

    return lines

async def runBlockValu(runt, text, varz):
    '''
    Run a storm block's query and hand back the value it returned.

    `runBlockNodes` for a block that is about one thing rather than a set of them. Read-only and
    forced, like every other block runner.
    '''
    query = await runt.getStormQuery(text)

    async with runt.getCmdRuntime(query, opts={'vars': varz or {}}) as subr:

        subr.readonly = True

        try:
            async for _ in subr.execute():
                await asyncio.sleep(0)

        except s_stormctrl.StormReturn as e:
            return await s_stormtypes.toprim(e.item)

    return None

# The storm block types core can rebuild, keyed by the `type` a block's data carries. A type supplies
# all three keys:
#
#   run     what running the block's query hands back  (nodes, a value, the lines it printed)
#   render  how that becomes markdown, and how much of it it drew
#   opts    the JSON schema for the render half of the block's data
#
# Splitting `run` from `render` is what lets a type be about something other than a set of nodes
# without refresh() growing a branch per type. A type core has no entry for is rebuilt by whoever owns
# it, setting the block's content itself and keeping the fence and the iden by doing so.
STORM_BLOCK_TYPES = {
    'table': {'render': renderBlockTable, 'opts': TABLE_OPTS_SCHEMA, 'run': runBlockNodes},
    'image': {'render': renderBlockImage, 'opts': IMAGE_OPTS_SCHEMA, 'run': runBlockValu},
    'node': {'render': renderBlockNode, 'opts': NODE_OPTS_SCHEMA, 'run': runBlockNodes},
    'print': {'render': renderBlockPrint, 'opts': PRINT_OPTS_SCHEMA, 'run': runBlockPrints},
}

_optsValidators = {}

def reqBlockData(data):
    '''
    A storm block's data, validated and handed back.

    Two halves, validated by whoever owns them: the source half by `mdparse`, and the `opts` by the
    renderer the `type` names. A `type` core has no renderer for keeps opts core validates nothing
    about, which is what makes a caller's own type legal data.
    '''
    data = s_mdparse.reqBlockData(data)

    rend = STORM_BLOCK_TYPES.get(data.get('type'))
    if rend is None:
        return data

    valid = _optsValidators.get(data['type'])
    if valid is None:
        valid = _optsValidators[data['type']] = s_config.getJsValidator(rend['opts'])

    valid(data.get('opts') or {})

    return data

async def queryText(query):
    '''
    The text a storm block stores as its query.

    An embed query knows its own text. A plain string is accepted too, for a caller that built the
    query itself.
    '''
    if isinstance(query, s_stormtypes.Query):
        return query.text.strip()

    return (await s_stormtypes.tostr(query)).strip()

def nodeLift(node):
    '''
    The query that lifts `node` again, or an error saying why it has none.

    A comp form reprs as its parts rather than as a value the form takes, so there is no `form=<value>`
    that finds it: refused here rather than stored as a query that raises on every refresh.
    '''
    valu = node.repr()

    if not isinstance(valu, str):
        mesg = f'a {node.form.name} node cannot be lifted by its repr, so it has no query to rebuild from'
        raise s_exc.BadArg(mesg=mesg, form=node.form.name)

    valu = valu.replace('\\', '\\\\').replace('"', '\\"')

    return f'{node.form.name}="{valu}"'

class MarkdownBlockList(s_stormtypes.List):
    '''
    `$doc.blocks`: the document's own list, so a change to it is a change to the document.

    Everything that puts a block in goes through the document's own checks, as `add()` does: an
    append on a plain list would take a string, the same block twice, or a second storm block with
    an iden the document already gave out, and the text would only fail on the way out. Taking one
    out, or reordering, needs no check.
    '''
    def __init__(self, doc):
        s_stormtypes.List.__init__(self, doc.blocks)
        self.doc = doc

    def getObjLocals(self):
        locls = s_stormtypes.List.getObjLocals(self)
        locls.update({'append': self._methListAppend, 'extend': self._methListExtend})
        return locls

    @s_stormtypes.stormfunc(readonly=True)
    async def _methListAppend(self, valu):
        await self.doc._methAdd(valu)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methListExtend(self, valu):
        # all or nothing: each is checked against the ones before it as well as the document
        adds = []
        async for item in s_stormtypes.toiter(valu, noneok=True):
            self.doc._reqBlock(item, blocks=self.valu + adds)
            adds.append(item)

        self.valu.extend(adds)

    @s_stormtypes.stormfunc(readonly=True)
    async def setitem(self, name, valu):

        if valu is s_stormtypes.undef:
            return await s_stormtypes.List.setitem(self, name, valu)

        indx = await s_stormtypes.toint(name)

        try:
            have = self.valu[indx]
        except IndexError as e:
            raise s_exc.StormRuntimeError(mesg=str(e), len=len(self.valu), indx=indx) from None

        # checked against the others: the block it replaces is going
        self.doc._reqBlock(valu, blocks=[b for b in self.valu if b is not have])

        self.valu[indx] = valu

@s_stormtypes.registry.registerType
class MarkdownDoc(s_stormtypes.Prim):
    '''
    A markdown document, as the ordered list of blocks that make it up.

    The blocks are the document: `$doc.blocks` hands out the blocks themselves, so popping, adding and
    reordering them there changes the document.
    '''
    _storm_typename = 'markdown:doc'
    _storm_locals = (
        {'name': 'setBlockVars', 'desc': '''
            Replace the vars of every storm block in this document.

            A document has no vars of its own, so a value shared across one is set on its blocks. Point
            in time: a block added afterwards carries what its ctor was handed.

            Examples:
                Point every block in a document at one threat::

                    $doc.setBlockVars(({"threat": $threat.repr()}))
            ''',
         'type': {'type': 'function', '_funcname': '_methSetBlockVars',
                  'args': (
                      {'name': 'vars', 'type': 'dict',
                       'desc': 'The vars to store on each storm block. A value is anything JSON holds, nested included.'},
                  ),
                  'returns': {'type': 'int', 'desc': 'How many storm blocks were set.'}}},
        {'name': 'modBlockVars', 'desc': '''
            Merge these vars into every storm block's, leaving the names they do not share alone.

            Examples:
                Re-point every block, keeping whatever else each carries::

                    $doc.modBlockVars(({"threat": $threat.repr()}))
                    $doc.refresh()
            ''',
         'type': {'type': 'function', '_funcname': '_methModBlockVars',
                  'args': (
                      {'name': 'vars', 'type': 'dict',
                       'desc': 'The vars to merge into each storm block. A value is anything JSON holds, nested included.'},
                  ),
                  'returns': {'type': 'int', 'desc': 'How many storm blocks were updated.'}}},
        {'name': 'popBlockVars', 'desc': '''
            Remove these names from every storm block's vars.

            Examples:
                Take a var out of the whole document::

                    $doc.popBlockVars((tag,))
            ''',
         'type': {'type': 'function', '_funcname': '_methPopBlockVars',
                  'args': (
                      {'name': 'names', 'type': 'list', 'desc': 'The variable names to remove.'},
                  ),
                  'returns': {'type': 'int', 'desc': 'How many storm blocks were changed.'}}},
        {'name': 'blocks', 'desc': '''
            The blocks of the document, in order.

            The list is the document's own, so it can be manipulated in place. A block put in with
            `append`, `extend` or an assignment is refused for the same reasons `add()` refuses one.

            Examples:
                Drop the first block::

                    $doc.blocks.pop((0))

                Move the last block to the front::

                    $doc.add($doc.blocks.pop(), indx=(0))
            ''',
         'type': {'type': 'gtor', '_gtorfunc': '_getBlocks',
                  'returns': {'type': 'list', 'desc': 'The document blocks.'}}},
        {'name': 'add', 'desc': '''
            Add a block to the document.

            Appends by default. Pass an `indx` to insert before the block at that position. A block
            the document already holds is refused, so popping one is how it moves.
            ''',
         'type': {'type': 'function', '_funcname': '_methAdd',
                  'args': (
                      {'name': 'block', 'type': 'markdown:block', 'desc': 'The block to add.'},
                      {'name': 'indx', 'type': 'int', 'default': -1,
                       'desc': 'Insert before this position. -1 appends.'},
                  ),
                  'returns': {'type': 'markdown:doc', 'desc': 'The document (for chaining).'}}},
        {'name': 'clear', 'desc': '''
            Remove every block from the document, leaving it empty.

            The block data of what was removed is not touched, the same as for any other removal:
            `orphans()` names those and `purgeOrphans()` drops them.

            Examples:
                Rebuild a document from scratch::

                    $doc = $lib.markdown.load($node)
                    $doc.clear()
                    $doc.add($lib.markdown.heading('Today', (2)))
                    $doc.save()
            ''',
         'type': {'type': 'function', '_funcname': '_methClear',
                  'args': (),
                  'returns': {'type': 'markdown:doc', 'desc': 'The document (for chaining).'}}},
        {'name': 'text', 'desc': '''
            The markdown source of the document, which is its blocks joined back together.

            Settable: assigning a document's text re-parses it into blocks.

            Examples:
                Read the source out::

                    $body = $doc.text

                ...and replace the whole document with other markdown::

                    $doc.text = $body
            ''',
         'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_getText', '_storfunc': '_setText',
                  'returns': {'type': 'str', 'desc': 'The markdown source.'}}},
        {'name': 'unwrap', 'desc': '''
            The markdown source with every storm block replaced by its content: no `:::` fences, for a
            consumer that does not understand them.

            A div that is not a storm block is left alone, since its fence is presumably meaningful to
            whoever wrote it.

            Examples:
                Send a document somewhere that speaks plain markdown::

                    $lib.inet.http.post($url, json=({"text": $doc.unwrap()}))
            ''',
         'type': {'type': 'function', '_funcname': '_methUnwrap',
                  'returns': {'type': 'str', 'desc': 'The markdown source, without the fences.'}}},
        {'name': 'node', 'desc': 'The node this document was opened from, or null.',
         'type': {'type': 'gtor', '_gtorfunc': '_getNode',
                  'returns': {'type': 'node', 'desc': 'The node, or null.'}}},
        {'name': 'save', 'desc': '''
            Write the document back to the node it was opened from: the body, the `updated` stamp, and
            the data of every storm block in it. A save that changes nothing stamps nothing.

            Refused when the text would not read back as the storm blocks the document holds, as when a
            heading or paragraph's text opens a fence that swallows the blocks after it.

            Examples:
                Add a table to a story and save it::

                    $doc = $lib.markdown.load($node)
                    $doc.add($lib.markdown.stormtable(${ inet:fqdn#suspect }))
                    $doc.save()
            ''',
         'type': {'type': 'function', '_funcname': '_methSave',
                  'returns': {'type': 'null', 'desc': 'Returns null.'}}},
        {'name': 'block', 'desc': '''
            The storm block carrying `iden`, or null.

            An iden is the durable name of a block: everything else about it moves -- its position, its
            content, its title -- so this is how one is found again.

            Examples:
                Rebuild one block, leaving the rest of the document alone::

                    $doc.block($iden).refresh()
            ''',
         'type': {'type': 'function', '_funcname': '_methBlock',
                  'args': (
                      {'name': 'iden', 'type': 'str', 'desc': 'The block iden.'},
                  ),
                  'returns': {'type': ['markdown:stormblock', 'null'],
                              'desc': 'The block, or null when the document has no such block.'}}},
        {'name': 'orphans', 'desc': '''
            The idens whose block data is stored on the node but whose blocks are no longer in the
            document. Nothing removes them: that is the caller's policy.

            An iden the document's text still names is not an orphan, even where its fence no longer
            reads as a storm block: mistyped, nested, or inside a block above it that never closes.
            Its data comes back into use once the markdown is fixed.
            ''',
         'type': {'type': 'function', '_funcname': '_methOrphans',
                  'returns': {'type': 'list', 'desc': 'The orphaned idens.'}}},
        {'name': 'purgeOrphans', 'desc': '''
            Delete the block data `orphans()` reports, and hand back the idens removed.

            Kept separate from `save()`: a block stops being in the document the moment its fence is
            mistyped, so a save that swept would destroy a block's query while its author was typing.
            ''',
         'type': {'type': 'function', '_funcname': '_methPurgeOrphans',
                  'returns': {'type': 'list', 'desc': 'The idens whose data was deleted.'}}},
        {'name': 'refresh', 'desc': '''
            Re-run the stored query of every block in the document that can rebuild itself.

            A block that does not rebuild is skipped rather than raising, and keeps the content it has.
            A refusal about the caller rather than the data (a permission, a read-only runtime) raises
            instead, since it is the same answer for every block.

            Answers with both halves: `rebuilt`, mapping each iden to the number of rows it drew,
            and `failed`, mapping an iden to the reason it did not.

            Examples:
                Refresh a document and report what did not come back::

                    $done = $doc.refresh()
                    for ($iden, $mesg) in $done.failed { $lib.warn(`{$iden}: {$mesg}`) }

                Notice the blocks that rebuilt with nothing in them::

                    for ($iden, $rows) in $done.rebuilt {
                        if ($rows = (0)) { $lib.warn(`{$iden} is empty`) }
                    }
            ''',
         'type': {'type': 'function', '_funcname': '_methRefresh',
                  'returns': {'type': 'dict',
                              'desc': 'The rows each iden `rebuilt`, and why each `failed` one did not.'}}},
    )

    def __init__(self, runt, text=None, node=None, path=None):
        s_stormtypes.Prim.__init__(self, None, path=path)

        self.runt = runt
        self.lead = ''
        self.blocks = []

        self.docnode = node

        if node is not None:
            text = self._getBodyValu()

        # what is on the node, so a save that changes nothing writes nothing
        self.saved = text or ''

        if text:
            self.lead, blocks = s_mdparse.parseBlocks(text)
            self.blocks = [wrapBlock(b, runt=runt) for b in blocks]

        self.gtors.update({'blocks': self._getBlocks, 'node': self._getNode,
                           'text': self._getText})
        self.stors.update({'text': self._setText})
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'add': self._methAdd,
            'clear': self._methClear,
            'unwrap': self._methUnwrap,
            'save': self._methSave,
            'block': self._methBlock,
            'orphans': self._methOrphans,
            'purgeOrphans': self._methPurgeOrphans,
            'refresh': self._methRefresh,
            'setBlockVars': self._methSetBlockVars,
            'modBlockVars': self._methModBlockVars,
            'popBlockVars': self._methPopBlockVars,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSetBlockVars(self, vars):
        vars = await s_stormtypes.toprim(vars)

        return await self._editBlockVars(lambda varz: vars)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methModBlockVars(self, vars):
        vars = await s_stormtypes.toprim(vars)

        return await self._editBlockVars(lambda varz: {**varz, **vars})

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPopBlockVars(self, names):
        names = set(await s_stormtypes.toprim(names))

        return await self._editBlockVars(lambda varz: {k: v for (k, v) in varz.items()
                                                       if k not in names})

    async def _editBlockVars(self, func):
        '''
        Apply `func` to the vars of every storm block in the document, and say how many it touched.

        A document has no vars of its own, so setting the same name across one is this rather than a
        second scope to merge. A block that is not a storm block has no vars and is skipped.
        '''
        count = 0

        for block in self.blocks:

            if not isinstance(block, MarkdownStormBlock):
                continue

            await block._editVars(func)
            count += 1

        return count

    def _getBodyValu(self):
        # An interface prop is poly typed, so a read comes back as (typename, value).
        valu = self.docnode.get(self._reqBodyProp())
        if valu is None:
            return None

        return valu[1]

    def _reqBodyProp(self):
        if DOCUMENT_IFACE not in self.docnode.form.ifaces:
            mesg = f'{self.docnode.form.name} does not implement {DOCUMENT_IFACE}, so it holds no markdown'
            raise s_exc.BadArg(mesg=mesg, form=self.docnode.form.name, iface=DOCUMENT_IFACE)

        return 'body'

    def _confirmSet(self, node, name):
        '''
        Confirm a prop write costs what the same edit costs in a query.

        These go through the node API rather than `$node.props`, where the confirm would otherwise
        happen, so a document API must not be a way around the prop perms.
        '''
        prop = node.form.prop(name)
        self.runt.confirm(prop.setperm, gateiden=node.view.wlyr.iden)

    def _confirmData(self, node, name, dele=False):
        verb = 'del' if dele else 'set'
        self.runt.confirm(('node', 'data', verb, name), gateiden=node.view.wlyr.iden)

    def _reqNode(self):
        if self.docnode is None:
            mesg = 'this markdown:doc was not opened from a node, so there is nothing to save it to'
            raise s_exc.BadArg(mesg=mesg)

        return self.docnode

    async def initBlockData(self):
        '''
        Attach each stored block's data to the storm block it belongs to.

        A block whose data is missing keeps an empty dict: still addressable, just with nothing to
        rebuild itself from.
        '''
        if self.docnode is None:
            return

        for block in self.blocks:

            if not isinstance(block, MarkdownStormBlock):
                continue

            data = await self.docnode.getData(f'{BLOCK_PREFIX}{block.valu.getIden()}')
            if data is not None:
                block.valu.data = reqBlockData(data)

    def _reqReadsBack(self, text):
        '''
        Refuse text whose storm blocks do not read back as the ones this document holds.

        A heading or paragraph whose text opens a fence, or a div whose text never closes one, reads
        back as a block that swallows the ones after it: stored, those blocks would be text inside it.
        '''
        held = [b.valu.getIden() for b in self.blocks if isinstance(b, MarkdownStormBlock)]
        back = [b.getIden() for b in s_mdparse.parseBlocks(text)[1] if isinstance(b, s_mdparse.StormBlock)]

        if back != held:
            mesg = ('this markdown document does not read back as the storm blocks it holds: the text of a '
                    'block opens a fence (:::, ``` or <!--) that it never closes')
            raise s_exc.BadArg(mesg=mesg, held=held, back=back)

    async def _getNode(self):
        if self.docnode is None:
            return None

        return s_stormtypes.Node(self.docnode)

    def _blockData(self):
        '''
        The block data this document would write, as (iden, name, data) in document order.
        '''
        out = []
        for block in self.blocks:

            if not isinstance(block, MarkdownStormBlock):
                continue

            data = block.valu.data
            if not data:
                continue

            iden = block.valu.getIden()
            out.append((iden, f'{BLOCK_PREFIX}{iden}', reqBlockData(data)))

        return out

    async def _methSave(self):

        node = self._reqNode()

        text = await self.value()

        writing = text != self.saved
        datas = self._blockData()

        if writing:
            self._reqReadsBack(text)

        # every permission first, and every block's data validated, before anything is written. A check
        # that fired partway through left a body full of fences whose data was never stored:
        # unrebuildable, and indistinguishable from fences someone typed by hand.
        if writing:
            self._confirmSet(node, self._reqBodyProp())

            if node.form.prop('updated') is not None:
                self._confirmSet(node, 'updated')

        for (iden, name, data) in datas:
            self._confirmData(node, name)

        if writing:
            await node.set(self._reqBodyProp(), text)
            self.saved = text

            # Stamped only when the interface declares it, and only alongside a body change.
            if node.form.prop('updated') is not None:
                await node.set('updated', 'now')

        for (iden, name, data) in datas:
            await node.setData(name, data)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methBlock(self, iden):

        iden = await s_stormtypes.tostr(iden)

        for block in self.blocks:
            if isinstance(block, MarkdownStormBlock) and block.valu.getIden() == iden:
                return block

        return None

    @s_stormtypes.stormfunc(readonly=True)
    async def _methOrphans(self):

        node = self._reqNode()
        text = await self.value()

        names = []
        genr = node.iterDataKeys()
        async with contextlib.aclosing(genr):
            async for name in genr:
                names.append(name)

        out = []
        seen = set()

        for name in names:

            if not name.startswith(BLOCK_PREFIX):
                continue

            iden = name[len(BLOCK_PREFIX):]

            # Named in the text, which every block's fence is. So is one that no longer reads as a storm
            # block (mistyped, nested, or swallowed by an unclosed fence above it): it gets its data back
            # once the markdown is fixed.
            if iden in seen or iden in text:
                continue

            seen.add(iden)
            out.append(iden)

        return out

    async def _dropData(self, node, iden):
        '''
        Remove `iden`'s stored data.

        Popped whatever it holds: an orphan is named by a key the node has, and one holding null is
        still a key, which would otherwise be reported purged and then listed again.
        '''
        name = f'{BLOCK_PREFIX}{iden}'
        self._confirmData(node, name, dele=True)
        await node.popData(name)

    async def _methPurgeOrphans(self):

        node = self._reqNode()

        idens = await self._methOrphans()
        for iden in idens:
            await self._dropData(node, iden)

        return idens

    @s_stormtypes.stormfunc(readonly=True)
    async def _methRefresh(self):

        rebuilt = {}
        failed = {}

        for block in self.blocks:

            if not isinstance(block, MarkdownStormBlock):
                continue

            # A type core cannot rebuild is not an error here the way it is on one block: a caller
            # asking a whole document to refresh is asking for what can be, not for all or nothing.
            if not await block._getRefreshable():
                continue

            iden = block.valu.getIden()

            # ...and neither is a block that cannot rebuild for a reason `refreshable` could not have
            # known: a deleted node, a prop the form no longer has, a query past the row bound. Those
            # are ordinary consequences of a graph moving on, so the block keeps what it has and the
            # rest of the document still refreshes.
            try:
                rows = await block._methRefresh()

            # ...but not a refusal about the caller rather than one block: a permission denied or a
            # read-only runtime is the same answer for every block, so swallowing it would turn one
            # wrong answer into a document that quietly refreshed nothing.
            #
            # A query that does not parse is not one of those, though it reads like one: each block is
            # parsed on its own, so an unparsable one is data about that block and lands in `failed`.
            except (s_exc.AuthDeny, s_exc.IsReadOnly):
                raise

            except s_exc.SynErr as e:
                mesg = f'markdown block {iden} could not rebuild: {e.get("mesg")}'
                await self.runt.warn(mesg, log=False)
                failed[iden] = e.get('mesg')
                continue

            rebuilt[iden] = rows

        # Both halves, because a warning is invisible to a `callStorm` caller. Rows rather than a
        # list of idens: a document whose blocks all came back empty rebuilt every one of them.
        return {'rebuilt': rebuilt, 'failed': failed}

    async def value(self):
        return s_mdparse.joinBlocks(self.blocks, lead=self.lead)

    async def stormrepr(self):
        return await self.value()

    async def _getBlocks(self):
        # the document's own list, so pop/append/reverse on it change the document
        return MarkdownBlockList(self)

    def _reqAddable(self, block, blocks=None):
        '''
        Refuse a block the document already holds.

        A block is a mutable object, so the same one in two positions is one block that renders twice
        and edits in both places; for a storm block, one iden would also name two blocks and
        `block()` could only ever answer with the first. Popping a block is how it moves.
        '''
        iden = block.valu.getIden() if isinstance(block, MarkdownStormBlock) else None

        for have in (self.blocks if blocks is None else blocks):

            if have is block:
                mesg = 'that markdown block is already in this document, pop it before adding it back'
                raise s_exc.BadArg(mesg=mesg, iden=iden)

            if iden is None or not isinstance(have, MarkdownStormBlock):
                continue

            if have.valu.getIden() == iden:
                mesg = f'this document already has a storm block with iden {iden}'
                raise s_exc.BadArg(mesg=mesg, iden=iden)

    def _reqBlock(self, block, blocks=None):
        '''
        Refuse anything the document cannot hold: a value that is not a markdown block, or one
        `_reqAddable` refuses. The one check every way of putting a block in goes through.
        '''
        if not isinstance(block, MarkdownBlock):
            mesg = 'a markdown document holds markdown blocks, e.g. $lib.markdown.paragraph(...)'
            raise s_exc.BadArg(mesg=mesg, name=block.__class__.__name__)

        self._reqAddable(block, blocks=blocks)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methAdd(self, block, indx=-1):

        self._reqBlock(block)

        indx = await s_stormtypes.toint(indx)

        if indx == -1 or indx >= len(self.blocks):
            self.blocks.append(block)
            return self

        if indx < 0:
            mesg = f'markdown block index must be -1 (append) or a position, got {indx}'
            raise s_exc.BadArg(mesg=mesg, indx=indx)

        self.blocks.insert(indx, block)
        return self

    @s_stormtypes.stormfunc(readonly=True)
    async def _methClear(self):
        # emptied in place, so a `$doc.blocks` handed out earlier is still this document's list
        self.lead = ''
        self.blocks.clear()

        return self

    @s_stormtypes.stormfunc(readonly=True)
    async def _getText(self):
        return await self.value()

    @s_stormtypes.stormfunc(readonly=True)
    async def _setText(self, valu):

        text = await s_stormtypes.tostr(valu, noneok=True) or ''

        self.lead = ''
        self.blocks.clear()

        if text:
            self.lead, blocks = s_mdparse.parseBlocks(text)
            self.blocks.extend(wrapBlock(b, runt=self.runt) for b in blocks)

        await self.initBlockData()

    @s_stormtypes.stormfunc(readonly=True)
    async def _methUnwrap(self):
        blocks = s_mdparse.unwrapBlocks([b.valu for b in self.blocks])
        return s_mdparse.joinBlocks(blocks, lead=self.lead)

def newStormBlockData(styp, query, varz, opts):
    '''
    The data a storm block stores, validated.

    The source half is the same for every type; `opts` is the render half, which belongs to the type
    that renders from it.
    '''
    return reqBlockData({
        'type': styp,
        'query': query,
        'vars': varz,
        'mode': 'storm',
        'updated': s_common.now(),
        'opts': opts,
    })

def titledBlock(valu, title):
    '''
    A block's content under the `## Title` an author sees, when it has one.
    '''
    if title is None:
        return valu

    return f'## {title}\n\n{valu}'

@s_stormtypes.registry.registerLib
class LibMarkdown(s_stormtypes.Lib):
    '''
    A Storm Library for building markdown documents.

    The block constructors here and the blocks in `$doc.blocks` are the same types of object, so a block
    can be built, adjusted and then added, or moved from one document to another.

    A storm block stores the query it was built from, so refreshing one re-runs that query as whoever
    asked for the refresh and with their permissions, in a read only runtime. It may call any library
    that runtime allows, and a table's `pathvar` column writes a runtime variable into the document, so
    a block's content is whatever its query could reach.
    '''
    _storm_locals = (
        {'name': 'doc', 'desc': '''
            Construct an empty markdown document.

            Blocks go in with `$doc.add()`; `$doc.text` is the markdown. There is nowhere to save it:
            see `load()` for a document attached to a node.

            Examples:
                Build a document from nothing::

                    $doc = $lib.markdown.doc()
                    $doc.add($lib.markdown.heading('Findings', (2)))
            ''',
         'type': {'type': 'function', '_funcname': '_methDoc',
                  'args': (),
                  'returns': {'type': 'markdown:doc', 'desc': 'The document.'}}},
        {'name': 'parse', 'desc': '''
            Parse markdown source into a document.

            There is nowhere to read a storm block's data back from, so the blocks parse with empty
            data: still addressable by iden, but with nothing to rebuild themselves from until a caller
            assigns `$block.data`.

            Examples:
                Take a document apart::

                    $doc = $lib.markdown.parse($text)
                    for $block in $doc.blocks { $lib.print($block.type) }
            ''',
         'type': {'type': 'function', '_funcname': '_methParse',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'Markdown source to parse into blocks.'},
                  ),
                  'returns': {'type': 'markdown:doc', 'desc': 'The document.'}}},
        {'name': 'load', 'desc': '''
            Load the markdown document a node holds.

            The form must implement `doc:document`. The document comes back with each storm block's
            data attached, ready for `$doc.save()`, and saves back to the node it was loaded from.

            Examples:
                Open a report, add to it, and save::

                    $doc = $lib.markdown.load($node)
                    $doc.add($lib.markdown.paragraph('One more finding.'))
                    $doc.save()
            ''',
         'type': {'type': 'function', '_funcname': '_methLoad',
                  'args': (
                      {'name': 'node', 'type': 'node', 'desc': 'A node holding a markdown document.'},
                  ),
                  'returns': {'type': 'markdown:doc', 'desc': 'The document.'}}},
        {'name': 'heading', 'desc': 'Construct a markdown heading block.',
         'type': {'type': 'function', '_funcname': '_methHeading',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The heading text.'},
                      {'name': 'level', 'type': 'int', 'default': 1, 'desc': 'The heading level (1-6).'},
                  ),
                  'returns': {'type': 'markdown:heading', 'desc': 'The heading block.'}}},
        {'name': 'paragraph', 'desc': 'Construct a markdown paragraph block (newlines collapsed to spaces).',
         'type': {'type': 'function', '_funcname': '_methParagraph',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The paragraph text.'},
                  ),
                  'returns': {'type': 'markdown:paragraph', 'desc': 'The paragraph block.'}}},
        {'name': 'list', 'desc': 'Construct a markdown list block.',
         'type': {'type': 'function', '_funcname': '_methList',
                  'args': (
                      {'name': 'items', 'type': 'list', 'desc': 'The list items.'},
                      {'name': 'ordered', 'type': 'boolean', 'default': False,
                       'desc': 'Render an ordered (numbered) list.'},
                  ),
                  'returns': {'type': 'markdown:list', 'desc': 'The list block.'}}},
        {'name': 'code', 'desc': 'Construct a fenced markdown code block.',
         'type': {'type': 'function', '_funcname': '_methCode',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The code text.'},
                      {'name': 'lang', 'type': 'str', 'default': '', 'desc': 'The code language.'},
                  ),
                  'returns': {'type': 'markdown:code', 'desc': 'The code block.'}}},
        {'name': 'image', 'desc': '''
            Construct a markdown image block.

            A standalone image is a paragraph in markdown, which is what this returns.

            Examples:
                An image with alt text and a sizing attribute::

                    $doc.add($lib.markdown.image($url, alt='Diagram', attrs='{width=50%}'))
            ''',
         'type': {'type': 'function', '_funcname': '_methImage',
                  'args': (
                      {'name': 'url', 'type': 'str', 'desc': 'The image URL.'},
                      {'name': 'alt', 'type': 'str', 'default': '', 'desc': 'The image alt text.'},
                      {'name': 'title', 'type': 'str', 'default': None,
                       'desc': 'An optional link title, which readers show as a tooltip.'},
                      {'name': 'attrs', 'type': 'str', 'default': None,
                       'desc': 'An optional attribute block (`{width=50%}`), appended as written.'},
                  ),
                  'returns': {'type': 'markdown:paragraph', 'desc': 'The image block.'}}},
        {'name': 'table', 'desc': 'Construct a GFM markdown table block.',
         'type': {'type': 'function', '_funcname': '_methTable',
                  'args': (
                      {'name': 'columns', 'type': 'list',
                       'desc': 'Column names (str) or coldef dicts ({"name", "justify", "width"}). '
                               'A "width" (at least 4) trims a longer value to fit it.'},
                      {'name': 'rows', 'type': 'list', 'default': None,
                       'desc': 'Rows to add, for a table whose rows are already in hand.'},
                  ),
                  'returns': {'type': 'markdown:table', 'desc': 'The table block.'}}},
        {'name': 'div', 'desc': '''
            Construct a fenced div block.

            An `iden` in `attrs` makes it a `markdown:stormblock` instead, the same as it would be
            parsed out of a body. Use `stormprint()` for a block core rebuilds from what its query
            prints; this is what a type of your own is built from, with `$block.data` saying what it is.
            ''',
         'type': {'type': 'function', '_funcname': '_methDiv',
                  'args': (
                      {'name': 'classes', 'type': 'list', 'desc': 'The classes for the opening fence.'},
                      {'name': 'attrs', 'type': 'dict', 'default': None,
                       'desc': 'key=value attributes for the opening fence.'},
                      {'name': 'valu', 'type': 'str', 'default': '',
                       'desc': 'The markdown to contain.'},
                  ),
                  'returns': {'type': 'markdown:div',
                              'desc': 'The div block, or a markdown:stormblock if attrs carry an iden.'}}},
        {'name': 'stormprint', 'desc': '''
            Construct a storm block whose content is whatever its query prints.

            The query writes the markdown itself, one `$lib.print()` per line, so content core has no
            projection for needs no renderer and no columns. Use `stormtable` or `stormimage` when the
            content is a table or an image.

            The query runs in a read only runtime, and its print messages become the content rather
            than reaching the caller.

            Examples:
                A summary line that rebuilds itself::

                    $block = $lib.markdown.stormprint(${
                        $count = $lib.len($lib.list(...))
                        $lib.print(`**{$count}** domains carry #{$tag}.`)
                    }, vars=({"tag": $tag}))

                A bullet list::

                    $block = $lib.markdown.stormprint(${
                        inet:fqdn#suspect $lib.print(`- {$node.repr()}`)
                    })
            ''',
         'type': {'type': 'function', '_funcname': '_methStormPrint',
                  'args': (
                      {'name': 'query', 'type': ['str', 'storm:query'],
                       'desc': 'The query whose print messages are the content.'},
                      {'name': 'vars', 'type': 'dict', 'default': None,
                       'desc': 'Values to bind when the query runs, now and on every refresh.'},
                      {'name': 'title', 'type': 'str', 'default': None,
                       'desc': 'An editable `## Title` above the content.'},
                      {'name': 'classes', 'type': 'list', 'default': None,
                       'desc': 'The classes for the opening fence. Defaults to `storm-block`.'},
                      {'name': 'iden', 'type': 'str', 'default': None,
                       'desc': 'The block iden. Defaults to a new guid.'},
                  ),
                  'returns': {'type': 'markdown:stormblock', 'desc': 'The storm block.'}}},
        {'name': 'stormtable', 'desc': '''
            Construct a storm block whose content is a table projected from a Storm query.

            The block keeps what it needs to rebuild itself: the query as written (which may name
            variables) and the values it was written against. `$block.refresh()` re-runs it.

            A column says which value of each node fills its cells, by type::

                ({"name": "Domain", "type": "form"})                       // the primary value
                ({"name": "Host", "type": "prop", "prop": "host"})         // a secondary property
                ({"name": "Port", "type": "virt", "virt": "port"})         // a virt of the row's type
                ({"name": "Added", "type": "meta", "meta": "created"})     // a metadata property
                ({"name": "Since", "type": "tag", "tag": "aka.apt1"})      // a tag interval bound
                ({"name": "Infra", "type": "tagglob", "tagglob": "cno.**"})  // the leaf tags matching
                ({"name": "Org", "type": "embed", "embed": "org::name"})   // a prop it pivots to
                ({"name": "Why", "type": "pathvar", "pathvar": "why"})     // a variable from the path

            A `prop` takes the property name with or without its leading `:`. A `tag` column takes an
            `index`, 0 for the interval's start and 1 for its end; a `pathvar` takes a `pathvartype`
            to repr the value with.

            Naming no columns takes the ones the row form declares in its `display`, resolved once at
            build and stored concrete.

            A table is of one form, and a rebuild keeps only the rows belonging to it. That form is
            taken from the rows, so a query yielding several -- or none -- is refused unless `form`
            names the one meant.

            An `edge` column counts light edges, and takes `(verb, form, n2)`: the verb, the target
            form to count, and whether to walk the edge in reverse. It is built as its own variable,
            since Storm has no inline tuple inside a dict::

                $used = (used, it:software, (false))
                ({"name": "Tools", "type": "edge", "edge": $used})     // tools it used

                $usedby = (used, risk:threat, (true))
                ({"name": "Threats", "type": "edge", "edge": $usedby}) // threats that used it

            A column of the first three types has a shorter spelling, as a prop path: `:name` (or a
            bare name) is a secondary property, `.name` a metadata property, and a dotted tail a
            virtual property of either. The primary value is `{"type": "form"}` and nothing else.

            A column is drawn by the same keys `table()` takes: `name` for the header, `justify`
            (`left`, `center` or `right`), and `width`, which trims a longer value to fit and stores
            it trimmed. A `width` is at least 4: a trimmed value ends in `...`.

            Examples:
                A table of the software a threat used, able to rebuild itself later::

                    $query = ${ risk:threat=$threat -(used)> it:software }
                    $vars = ({"threat": $threat.repr()})

                    $name = ({"name": "Software", "prop": "name"})
                    $vers = ({"name": "Version", "prop": "version"})

                    $block = $lib.markdown.stormtable($query, columns=($name, $vers),
                                                      title="Known tools", vars=$vars)

                The same table, newest software first, which a rebuild reproduces::

                    $sort = ({"name": "Version", "direction": "desc"})
                    $block = $lib.markdown.stormtable($query, columns=($name, $vers), sort=$sort)

                ...without the rows whose version reads `0.0.0`, on the build and on every rebuild::

                    $hide = ({"name": "Version", "hide": ["0.0.0"]})
                    $block = $lib.markdown.stormtable($query, columns=($name, $vers),
                                                      filters=($hide,))
            ''',
         'type': {'type': 'function', '_funcname': '_methStormTable',
                  'args': (
                      {'name': 'query', 'type': ['str', 'storm:query'],
                       'desc': 'The query whose nodes fill the table.'},
                      {'name': 'columns', 'type': 'list', 'default': None,
                       'desc': '''The columns to project.

                       Defaults to the columns the row form itself declares, and to one column of
                       primary values for a form that declares none.'''},
                      {'name': 'title', 'type': 'str', 'default': None,
                       'desc': 'A heading to put above the table, inside the block.'},
                      {'name': 'vars', 'type': 'dict', 'default': None,
                       'desc': '''The values the query was written against, bound again on a rebuild.

                       Primitives only. A variable the query names but this does not carry raises
                       `NoSuchVar` when the block rebuilds.'''},
                      {'name': 'classes', 'type': 'list', 'default': None,
                       'desc': 'The fence classes. Defaults to (storm-block,).'},
                      {'name': 'iden', 'type': 'str', 'default': None,
                       'desc': 'The block iden. Defaults to a new guid.'},
                      {'name': 'form', 'type': 'str', 'default': None,
                       'desc': '''The form the table is of.

                       The rows are filtered to it, on the build and on every rebuild. Omit it when
                       the query yields one form and it is taken from the rows; required when it
                       yields several, or none at all.'''},
                      {'name': 'sort', 'type': ['str', 'dict', 'list'], 'default': None,
                       'desc': '''The column the rows are in the order of.

                       A column name to sort ascending, or `({"name": ..., "direction": "desc"})` to
                       say which way. `({"index": (2)})` names a column by position instead. Stored
                       with the columns, so a rebuild puts the rows back in the same order.

                       The order is taken from the values rather than from the text of the cells. A
                       row with nothing in the column sorts first ascending and last descending.'''},
                      {'name': 'filters', 'type': 'list', 'default': None,
                       'desc': '''The values a column holds back, as `({"name": ..., "hide": (...)})`.

                       `({"index": (2), "hide": (...)})` names a column by position instead. A row
                       whose cell in that column is one of those values is left out of the table,
                       here and on every rebuild.

                       The values are the cell text a reader sees, which is all a markdown table
                       holds. Values are hidden rather than kept so a rebuild still shows one the
                       graph grew afterwards.'''},
                  ),
                  'returns': {'type': 'markdown:stormblock', 'desc': 'The storm block.'}}},
        {'name': 'stormnode', 'desc': '''
            Construct a storm block showing one node, as a flipped name/value table.

            What it is, its value, its secondary properties, its metadata and its tags, a row each. The
            block stores the lift that finds the node again, so `$block.refresh()` shows it as it is
            now.

            A form whose repr does not lift it back -- a comp form -- is refused rather than stored
            with a query that would raise on every refresh.

            Examples:
                A node block for the domain a Story is about::

                    inet:fqdn=evil.com
                    $doc.add($lib.markdown.stormnode($node, title='The domain'))
            ''',
         'type': {'type': 'function', '_funcname': '_methStormNode',
                  'args': (
                      {'name': 'node', 'type': 'node', 'desc': 'The node to show.'},
                      {'name': 'title', 'type': 'str', 'default': None,
                       'desc': 'An editable `## Title` above the table.'},
                      {'name': 'classes', 'type': 'list', 'default': None,
                       'desc': 'The classes for the opening fence. Defaults to `storm-block`.'},
                      {'name': 'iden', 'type': 'str', 'default': None,
                       'desc': 'The block iden. Defaults to a new guid.'},
                  ),
                  'returns': {'type': 'markdown:stormblock', 'desc': 'The storm block.'}}},
        {'name': 'stormimage', 'desc': '''
            Construct a storm block whose content is the image a Storm query names.

            The query returns the sha256 of the file to show -- `return(:sha256)` -- and a refresh
            re-runs it, so the block follows whatever the query now names. `{valu}` in `urltmpl` is
            replaced by that sha256, since core has no idea what route serves a file.

            A query that returns nothing leaves the block empty rather than raising.

            Examples:
                An image block over a route that serves files by sha256::

                    $url = "/api/v3/optic/files/by/sha256/{valu}"
                    $lib.markdown.stormimage(${
                        media:screenshot:host=$host +.created@=(-1 day, now)
                        return(:file:sha256)
                    }, urltmpl=$url, title='Latest screenshot', vars=({"host": $host}))
            ''',
         'type': {'type': 'function', '_funcname': '_methStormImage',
                  'args': (
                      {'name': 'query', 'type': ['str', 'storm:query'],
                       'desc': 'The query returning the sha256 of the file to show.'},
                      {'name': 'urltmpl', 'type': 'str',
                       'desc': 'The URL template, where {valu} is filled with the sha256.'},
                      {'name': 'title', 'type': 'str', 'default': None,
                       'desc': 'An optional `## Title` above the image.'},
                      {'name': 'alt', 'type': 'str', 'default': None,
                       'desc': 'The alt text for the image.'},
                      {'name': 'attrs', 'type': 'str', 'default': None,
                       'desc': 'An optional attribute block (`{width=50%}`), appended to the image.'},
                      {'name': 'vars', 'type': 'dict', 'default': None,
                       'desc': '''The values the query was written against, bound again on a rebuild.

                       Primitives only. A variable the query names but this does not carry raises
                       `NoSuchVar` when the block rebuilds.'''},
                      {'name': 'classes', 'type': 'list', 'default': None,
                       'desc': 'The classes for the opening fence. Defaults to `storm-block`.'},
                      {'name': 'iden', 'type': 'str', 'default': None,
                       'desc': 'The block iden. Defaults to a new guid.'},
                  ),
                  'returns': {'type': 'markdown:stormblock', 'desc': 'The storm block.'}}},
        {'name': 'reqBlockData', 'desc': '''
            Validate a storm block's data, and hand it back.

            The check `$block.data =` and `$doc.save()` make, for a caller holding block data with no
            block to put it on. Raises rather than answering false, since a caller about to store the
            data wants the reason.

            Examples:
                Validate data before storing it::

                    $lib.markdown.reqBlockData(({"type": "table", "query": "inet:fqdn"}))
            ''',
         'type': {'type': 'function', '_funcname': '_methReqBlockData',
                  'args': (
                      {'name': 'data', 'type': 'dict', 'desc': "The storm block's data."},
                  ),
                  'returns': {'type': 'dict', 'desc': 'The data.'}}},
        {'name': 'raw', 'desc': 'Construct a block from markdown source, as it is written.',
         'type': {'type': 'function', '_funcname': '_methRaw',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The markdown source.'},
                  ),
                  'returns': {'type': 'markdown:block', 'desc': 'The block.'}}},
    )
    _storm_lib_path = ('markdown',)

    def getObjLocals(self):
        return {
            'doc': self._methDoc,
            'load': self._methLoad,
            'parse': self._methParse,
            'heading': self._methHeading,
            'paragraph': self._methParagraph,
            'list': self._methList,
            'code': self._methCode,
            'image': self._methImage,
            'table': self._methTable,
            'div': self._methDiv,
            'raw': self._methRaw,
            'reqBlockData': self._methReqBlockData,
            'stormprint': self._methStormPrint,
            'stormnode': self._methStormNode,
            'stormtable': self._methStormTable,
            'stormimage': self._methStormImage,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methStormPrint(self, query, vars=None, title=None, classes=None, iden=None):

        varz = await s_stormtypes.toprim(vars) or {}
        title = await s_stormtypes.tostr(title, noneok=True)
        classes = await s_stormtypes.toprim(classes) or (STORM_BLOCK_CLASS,)
        iden = await s_stormtypes.tostr(iden, noneok=True)

        text = await queryText(query)

        lines = await runBlockPrints(self.runt, text, varz)

        data = newStormBlockData('print', text, varz, {})

        valu = titledBlock('\n'.join(lines), title)

        block = s_mdparse.newStormBlock(classes, iden=iden, valu=valu, data=data)

        return MarkdownStormBlock(block, runt=self.runt)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methReqBlockData(self, data):
        data = await s_stormtypes.toprim(data)
        return reqBlockData(data)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methStormNode(self, node, title=None, classes=None, iden=None):

        title = await s_stormtypes.tostr(title, noneok=True)
        classes = await s_stormtypes.toprim(classes) or (STORM_BLOCK_CLASS,)
        iden = await s_stormtypes.tostr(iden, noneok=True)

        if isinstance(node, s_stormtypes.Node):
            node = node.valu

        if not hasattr(node, 'form'):
            mesg = f'$lib.markdown.stormnode() takes a node, got {node.__class__.__name__}'
            raise s_exc.BadArg(mesg=mesg)

        text = nodeLift(node)

        items = await runBlockNodes(self.runt, text, {})

        data = newStormBlockData('node', text, {}, {})

        valu, _ = await renderBlockNode(items, data, self.runt.model)

        valu = titledBlock(valu, title)

        block = s_mdparse.newStormBlock(classes, iden=iden, valu=valu, data=data)

        return MarkdownStormBlock(block, runt=self.runt)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methStormTable(self, query, columns=None, title=None, vars=None, classes=None,
                              iden=None, form=None, sort=None, filters=None):

        columns = await s_stormtypes.toprim(columns)
        title = await s_stormtypes.tostr(title, noneok=True)
        varz = await s_stormtypes.toprim(vars) or {}
        classes = await s_stormtypes.toprim(classes) or (STORM_BLOCK_CLASS,)
        iden = await s_stormtypes.tostr(iden, noneok=True)
        form = await s_stormtypes.tostr(form, noneok=True)
        sort = await s_stormtypes.toprim(sort)
        filters = await s_stormtypes.toprim(filters)

        # Validated before the query runs, so a bad column is refused without doing the work first.
        # The result is discarded: the columns are normed again once the rows name their form.
        normStormColumns(columns)

        text = await queryText(query)

        # Run through the same path a rebuild takes rather than running the embed query in the
        # caller's runtime: the block is built from the text and bindings it stores.
        items = await runBlockNodes(self.runt, text, varz)

        # Checked against the model before it is used to filter: a form= naming nothing would drop
        # every row for the life of the document and never say why.
        if form is not None and self.runt.model.form(form) is None:
            mesg = f'a storm table cannot be of {form}, which is not a form'
            raise s_exc.NoSuchForm(mesg=mesg, form=form)

        # Filtered here as well as on a rebuild, so the table a caller sees built is the table a
        # refresh reproduces.
        form, items = reqTableForm(items, form=form)

        columns = normStormColumns(columns, form=form, model=self.runt.model)

        # reqTableForm named the form or refused, so a rebuild always has one to filter on and a
        # header is never left at the generic `Node`.
        opts = {'columns': columns, 'form': form}

        # Stored, so a rebuild puts the rows back in the order the author chose.
        if (sort := normStormSort(sort, columns)) is not None:
            opts['sort'] = sort

        # ...and leaves out the rows it left out.
        if (filters := normStormFilter(filters, columns)) is not None:
            opts['filters'] = filters

        data = newStormBlockData('table', text, varz, opts)

        tabl = await projectTable(items, columns, self.runt.model, form=form, sort=sort,
                                  filters=filters)

        valu = titledBlock(tabl.text, title)

        block = s_mdparse.newStormBlock(classes, iden=iden, valu=valu, data=data)

        return MarkdownStormBlock(block, runt=self.runt)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methStormImage(self, query, urltmpl, title=None, alt=None, attrs=None,
                              vars=None, classes=None, iden=None):

        urltmpl = await s_stormtypes.tostr(urltmpl)
        title = await s_stormtypes.tostr(title, noneok=True)
        alt = await s_stormtypes.tostr(alt, noneok=True)
        attrs = await s_stormtypes.tostr(attrs, noneok=True)
        varz = await s_stormtypes.toprim(vars) or {}
        classes = await s_stormtypes.toprim(classes) or (STORM_BLOCK_CLASS,)
        iden = await s_stormtypes.tostr(iden, noneok=True)

        text = await queryText(query)

        items = await runBlockValu(self.runt, text, varz)

        opts = {'urltmpl': urltmpl}
        for name, valu in (('alt', alt), ('attrs', attrs)):
            if valu is not None:
                opts[name] = valu

        data = newStormBlockData('image', text, varz, opts)

        # Built through the renderer a refresh will use, so the block shows the same image the first
        # time as every time after.
        valu, _ = await renderBlockImage(items, data, self.runt.model)

        valu = titledBlock(valu, title)

        block = s_mdparse.newStormBlock(classes, iden=iden, valu=valu, data=data)

        return MarkdownStormBlock(block, runt=self.runt)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methDoc(self):
        return MarkdownDoc(self.runt)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methParse(self, text):

        # A document with no body yet is an empty one, not the string "None"
        text = await s_stormtypes.tostr(text, noneok=True)

        return MarkdownDoc(self.runt, text=text)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methLoad(self, node):

        if isinstance(node, s_stormtypes.Node):
            node = node.valu

        if not hasattr(node, 'form'):
            mesg = f'$lib.markdown.load() takes a node, got {node.__class__.__name__}'
            raise s_exc.BadArg(mesg=mesg)

        doc = MarkdownDoc(self.runt, node=node)
        await doc.initBlockData()

        return doc

    @s_stormtypes.stormfunc(readonly=True)
    async def _methHeading(self, text, level=1):
        text = await s_stormtypes.tostr(text)
        level = await s_stormtypes.toint(level)
        return MarkdownHeading(s_mdparse.Heading(s_mdparse.fmtHeading(text, level)), runt=self.runt)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methParagraph(self, text):
        text = await s_stormtypes.tostr(text)
        return MarkdownParagraph(s_mdparse.Paragraph(s_mdparse.fmtParagraph(text)), runt=self.runt)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methList(self, items, ordered=False):
        items = await s_stormtypes.toprim(items)
        ordered = await s_stormtypes.tobool(ordered)
        return MarkdownList(s_mdparse.List(s_mdparse.fmtList(items, ordered)), runt=self.runt)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methCode(self, text, lang=''):
        text = await s_stormtypes.tostr(text)
        lang = await s_stormtypes.tostr(lang)
        return MarkdownCode(s_mdparse.Code(s_mdparse.fmtCode(text, lang)), runt=self.runt)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methImage(self, url, alt='', title=None, attrs=None):
        url = await s_stormtypes.tostr(url)
        alt = await s_stormtypes.tostr(alt)
        title = await s_stormtypes.tostr(title, noneok=True)
        attrs = await s_stormtypes.tostr(attrs, noneok=True)
        text = s_mdparse.fmtImage(url, alt=alt, title=title, attrs=attrs)
        return MarkdownParagraph(s_mdparse.Paragraph(text), runt=self.runt)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methTable(self, columns, rows=None):
        columns = await s_stormtypes.toprim(columns)
        rows = await s_stormtypes.toprim(rows)
        return MarkdownTable(s_mdparse.newTable(columns, rows=rows), runt=self.runt)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methDiv(self, classes, attrs=None, valu=''):
        classes = await s_stormtypes.toprim(classes)
        attrs = await s_stormtypes.toprim(attrs)
        valu = await s_stormtypes.tostr(valu)

        # An `iden` attribute makes it a storm block, the same as it would parsed out of a body, so the
        # kind is wrapped for rather than assumed.
        block = s_mdparse.promoteDiv(s_mdparse.newDiv(classes, attrs=attrs, valu=valu))

        return wrapBlock(block, runt=self.runt)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methRaw(self, text):
        text = await s_stormtypes.tostr(text)
        return MarkdownBlock(s_mdparse.Block(text), runt=self.runt)

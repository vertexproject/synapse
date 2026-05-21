import copy
import textwrap
import itertools

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.schemas as s_schemas
import synapse.lib.stormtypes as s_stormtypes

justers = {
    'left': str.ljust,
    'center': str.center,
    'right': str.rjust,
}

@s_stormtypes.registry.registerLib
class LibTabular(s_stormtypes.Lib):
    '''
    A Storm Library for creating printable tables.
    '''
    _storm_locals = (
        {'name': 'printer', 'desc': '''
        Construct a new printer.

        Examples:
            Create a simple table using the default separators::

                $conf = ({
                    "columns": [
                        {"name": "Year", "width": 4},
                        {"name": "Author", "width": 20},
                        {"name": "Title", "width": 12},
                    ]
                })

                $printer = $lib.tabular.printer($conf)

                $lib.print($printer.header())

                for ($year, $author, $title, $publisher) in $data {
                    $lib.print($printer.row(($year, $author, $title))
                }

            Create a configuration with custom separators and column options::

                $conf = ({
                    "separators": {
                        "row:outline": true,
                        "column:outline": true,
                        "header:row": "#",
                        "data:row": "*",
                        "column": "+",
                    },
                    "columns": [
                        {"name": "Year", "width": 4, "justify": "right"},
                        {"name": "Author", "width": 20, "justify": "center"},
                        {"name": "Title", "width": 12, "overflow": "wrap"},
                    ]
                })

                $printer = $lib.tabular.printer($conf)
        ''',
         'type': {'type': 'function', '_funcname': '_methPrinter',
                  'args': (
                      {'name': 'conf', 'type': 'dict',
                       'desc': 'The table configuration dictionary.'},
                  ),
                  'returns': {'type': 'tabular:printer',
                              'desc': 'The newly constructed tabular:printer.'}}},
        {'name': 'schema', 'desc': '''
        Get a copy of the table configuration schema.

        Examples:
            Print a human-readable version of the schema::

                $schema = $lib.tabular.schema()
                $lib.print($lib.yaml.save($schema))
        ''',
         'type': {'type': 'function', '_funcname': '_methSchema',
                  'returns': {'type': 'dict',
                              'desc': 'The table configuration schema.'}}},
    )
    _storm_lib_path = ('tabular',)

    def getObjLocals(self):
        return {
            'printer': self._methPrinter,
            'schema': self._methSchema,
        }

    async def _methSchema(self):
        return copy.deepcopy(s_schemas.tabularConfSchema)

    async def _methPrinter(self, conf):
        conf = await s_stormtypes.toprim(conf)
        conf.setdefault('separators', {})
        conf = s_schemas.reqValidTabularConf(conf)
        return TabularPrinter(self.runt, conf)

@s_stormtypes.registry.registerType
class TabularPrinter(s_stormtypes.StormType):
    '''
    A Storm object for printing tabular data using a defined configuration.
    '''
    _storm_typename = 'tabular:printer'
    _storm_locals = (
        {'name': 'row', 'desc': 'Create a new row string from a data list.',
         'type': {'type': 'function', '_funcname': 'row',
                  'args': (
                      {'name': 'data', 'type': 'list',
                       'desc': 'The data to create the row from; length must match the number of configured columns.'},
                  ),
                  'returns': {'type': 'str', 'desc': 'The row string.'}}},
        {'name': 'header',
         'desc': 'Create a header row string.',
         'type': {'type': 'function', '_funcname': 'header',
                  'returns': {'type': 'str', 'desc': 'The header row string.'}}},
    )

    def __init__(self, runt, conf):
        s_stormtypes.StormType.__init__(self, None)
        self.runt = runt
        self.conf = conf

        self.firstrow = True

        self.seprconf = conf['separators']

        self.colconf = conf['columns']
        self.colcnt = len(self.colconf)
        self.colwidths = [coldef.get('width') or len(coldef['name']) for coldef in self.colconf]

        self.locls.update({
            'row': self.row,
            'header': self.header,
        })

    def _formatRowLine(self, lineitems, pad=' '):
        sepr = self.seprconf['column']
        endstr = sepr if self.seprconf['column:outline'] else ''
        return f'{endstr}{pad}{f"{pad}{sepr}{pad}".join(lineitems)}{pad}{endstr}'

    def _makeSeparatorRowStr(self, rowsepr):
        if rowsepr:
            lineitems = (width * rowsepr for width in self.colwidths)
            return self._formatRowLine(lineitems, pad=rowsepr)
        return None

    def _makeDataRowStrs(self, values):

        items = []
        for coldef, valu in zip(self.colconf, values):
            width = coldef.get('width')
            valu = str(valu) if valu is not None else ''

            if width is None:
                if coldef['newlines'] == 'split':
                    items.append(valu.split('\n'))
                else:
                    items.append([valu.replace('\n', ' ')])
                continue

            valu = valu.replace('\n', ' ')

            if len(valu) <= width:
                items.append([justers[coldef['justify']](valu, width)])
                continue

            if coldef['overflow'] == 'trim':
                items.append([s_common.trimText(valu, n=width)])
                continue

            items.append([justers[coldef['justify']](item, width) for item in textwrap.wrap(valu, width)])

        rowstrs = []
        for lineitems in itertools.zip_longest(*items, fillvalue=None):
            lineitems = ([item or self.colwidths[i] * ' ' for i, item in enumerate(lineitems)])
            rowstrs.append(self._formatRowLine(lineitems))

        return rowstrs

    async def header(self):
        rowstrs = self._makeDataRowStrs([col['name'] for col in self.colconf])

        if seprstr := self._makeSeparatorRowStr(self.seprconf['header:row']):
            rowstrs.append(seprstr)
            if self.seprconf['row:outline']:
                rowstrs.insert(0, seprstr)

        return '\n'.join(rowstrs)

    async def row(self, data):
        data = await s_stormtypes.toprim(data)

        if not isinstance(data, (list, tuple)):
            raise s_exc.BadArg(mesg='tabular:printer row() requires a list argument')

        if len(data) != self.colcnt:
            mesg = 'tabular:printer row() requires data length to equal column count'
            raise s_exc.BadArg(mesg=mesg, length=len(data), column_length=self.colcnt)

        rowstrs = self._makeDataRowStrs(data)

        if seprstr := self._makeSeparatorRowStr(self.seprconf['data:row']):
            if self.seprconf['row:outline']:
                rowstrs.append(seprstr)
            elif self.firstrow:
                self.firstrow = False
            else:
                rowstrs.insert(0, seprstr)

        return '\n'.join(rowstrs)

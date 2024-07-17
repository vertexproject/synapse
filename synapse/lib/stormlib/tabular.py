import copy
import textwrap
import itertools

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.config as s_config
import synapse.lib.stormtypes as s_stormtypes

reqValidTableConf = s_config.getJsValidator(schema := {
    'type': 'object',
    'properties': {
        'separators': {
            'type': 'object',
            'properties': {
                'row:outline': {'type': 'boolean', 'default': False},
                'column:outline': {'type': 'boolean', 'default': False},
                'header:row': {'type': 'string', 'default': '='},
                'data:row': {'type': 'string', 'default': '-'},
                'column': {'type': 'string', 'default': '|'},
            },
            'additionalProperties': False,
        },
        'columns': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string', 'description': 'TODO'},  # todo: descriptions?
                    'width': {'type': 'number', 'default': None, 'exclusiveMinimum': 0},
                    'justify': {'type': 'string', 'default': 'left', 'enum': ['left', 'center', 'right']},
                    'overflow': {'type': 'string', 'default': 'trim', 'enum': ['wrap', 'trim']},
                },
                'required': ['name'],
                'minItems': 1,
                'additionalProperties': False,
            },
        },
    },
    'required': ['columns'],
    'additionalProperties': False,
})

justers = {
    'left': str.ljust,
    'center': str.center,
    'right': str.rjust,
}

@s_stormtypes.registry.registerLib
class TabularLib(s_stormtypes.Lib):
    '''
    TODO
    $columns = ([
        {"name": "woot", "width": 20, "justify": right},
        {"name": "hehe", "width" 30},
    ])
    $printer = $lib.tabular.printer($columns)
    '''
    _storm_locals = (
        {'name': 'printer', 'desc': 'Construct a new printer.',
         'type': {'type': 'function', '_funcname': 'printer',
                  'args': (
                      {'name': 'conf', 'type': 'list',
                       'desc': 'TODO'},
                  ),
                  'returns': {'type': 'tabular:printer',
                              'desc': 'The newly constructed tabular:printer.'}}},
        {'name': 'schema', 'desc': 'TODO',
         'type': {'type': 'gtor', '_gtorfunc': '_gtorSchema',
                  'returns': {'type': 'dict',
                              'desc': 'TODO'}}},
    )
    _storm_lib_path = ('tabular',)

    def getObjLocals(self):
        return {
            'printer': self._methPrinter,
            'schema': self._methSchema,
        }

    async def _methSchema(self):
        return copy.deepcopy(schema)

    async def _methPrinter(self, conf):
        conf = await s_stormtypes.toprim(conf)
        conf.setdefault('separators', {})
        conf = reqValidTableConf(conf)
        return TabularPrinter(self.runt, conf)

@s_stormtypes.registry.registerType
class TabularPrinter(s_stormtypes.StormType):
    '''
    TODO
    $lib.print($printer.header())
    for $row in $rows {
        $lib.print($printer.row($row))
    }
    '''
    _storm_typename = 'tabular:printer'
    _storm_locals = (
        {'name': 'row',
         'desc': 'TODO',
         'type': {'type': 'function', '_funcname': 'row',
                  'args': (
                      {'name': 'data', 'type': 'list',
                       'desc': 'TODO'},
                  ),
                  'returns': {'type': 'str', 'desc': 'TODO'}}},
        {'name': 'header',
         'desc': 'TODO',
         'type': {'type': 'function', '_funcname': 'header',
                  'returns': {'type': 'str', 'desc': 'TODO'}}},
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

    def _makeRowItems(self, values: list):
        '''
        Justify, trim/wrap, and fill cells.
        Returns list of string lines for each column.
        '''

        items = []
        for coldef, valu in zip(self.colconf, values):
            width = coldef.get('width')
            valu = str(valu) if valu is not None else ''

            if width is None:
                items.append([valu])
                continue

            if len(valu) <= width:
                items.append([justers[coldef['justify']](valu, width)])
                continue

            if coldef['overflow'] == 'trim':
                items.append([s_common.trimText(valu, n=width)])
                continue

            items.append([justers[coldef['justify']](item, width) for item in textwrap.wrap(valu, width)])

        rowitems = []
        for lineitems in itertools.zip_longest(*items, fillvalue=None):
            rowitems.append([item or self.colwidths[i] * ' ' for i, item in enumerate(lineitems)])

        return rowitems

    def _formatRowLine(self, lineitems, sepr, doends, pad=' '):
        endstr = sepr if doends else ''
        return f'{endstr}{pad}{f"{pad}{sepr}{pad}".join(lineitems)}{pad}{endstr}'

    def _separator(self, colsepr, rowsepr, doends):
        lineitems = (width * rowsepr for width in self.colwidths)
        return self._formatRowLine(lineitems, colsepr, doends, pad=rowsepr)

    async def header(self):
        colsepr = self.seprconf['column']  # fixme: dont need to pass this around
        colends = self.seprconf['column:outline']  # fixme: don't need to pass this around

        # fixme: change to _makeRowStrs(values, colsepr, colends)
        rowitems = self._makeRowItems([col['name'] for col in self.colconf])
        rowstrs = [self._formatRowLine(lineitems, colsepr, colends) for lineitems in rowitems]

        if rowsepr := self.seprconf['header:row']:
            rowstrs.append(seprstr := self._separator(colsepr, rowsepr, colends))
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

        colsepr = self.seprconf['column']  # fixme: don't need to pass this around
        colends = self.seprconf['column:outline']  # fixme: don't need to pass this around

        # fixme: change to _makeRowStrs(values, colsepr, colends)
        rowitems = self._makeRowItems(data)
        rowstrs = [self._formatRowLine(lineitems, colsepr, colends) for lineitems in rowitems]

        if rowsepr := self.seprconf['data:row']:
            seprstr = self._separator(colsepr, rowsepr, colends)
            if self.seprconf['row:outline']:
                rowstrs.append(seprstr)
            elif self.firstrow:
                self.firstrow = False
            else:
                rowstrs.insert(0, seprstr)

        return '\n'.join(rowstrs)

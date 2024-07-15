import textwrap
import itertools

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.config as s_config
import synapse.lib.stormtypes as s_stormtypes

reqValidColumns = s_config.getJsValidator({
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'width': {'type': 'number', 'exclusiveMinimum': 0},
            'justify': {'type': 'string', 'default': 'left', 'enum': ['left', 'center', 'right']},
            'overflow': {'type': 'string', 'default': 'trim', 'enum': ['wrap', 'trim']},
        },
        'required': ['name', 'width'],
        'minItems': 1,
    },
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
                  'returns': {'type': 'tabular:printer',
                              'desc': 'The newly constructed tabular:printer.'}}},
    )
    _storm_lib_path = ('tabular',)

    def getObjLocals(self):
        return {
            'printer': self._methPrinter,
        }

    async def _methPrinter(self, columns):
        columns = await s_stormtypes.toprim(columns)
        columns = reqValidColumns(columns)
        return TabularPrinter(self.runt, columns)

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
        {'name': 'separator',
         'desc': 'TODO',
         'type': {'type': 'function', '_funcname': 'separator',
                  'args': (
                      {'name': 'char', 'type': 'str', 'default': '-',
                       'desc': 'TODO'},
                  ),
                  'returns': {'type': 'str', 'desc': 'TODO'}}},
    )

    def __init__(self, runt, columns):
        s_stormtypes.StormType.__init__(self, None)
        self.runt = runt
        self.columns = columns
        self.colcnt = len(columns)
        self.fillers = [' ' * coldef['width'] for coldef in columns]

        self.locls.update({
            'row': self.row,
            'header': self.header,
            'separator': self.separator,
        })

    def _makeRow(self, values):

        items = []
        for coldef, valu in zip(self.columns, values):
            width = coldef['width']
            valu = str(valu) if valu is not None else ''

            if len(valu) <= width:
                items.append([justers[coldef['justify']](valu, width)])
                continue

            if coldef['overflow'] == 'trim':
                items.append([s_common.trimText(valu, n=width)])
                continue

            items.append([justers[coldef['justify']](item, width) for item in textwrap.wrap(valu, width)])

        printrows = []
        for lineitems in itertools.zip_longest(*items, fillvalue=None):
            printrows.append(f'| {" | ".join(item or self.fillers[i] for i, item in enumerate(lineitems))} |')

        return '\n'.join(printrows)

    async def separator(self, char='-'):
        char = await s_stormtypes.tostr(char)
        if len(char) != 1:
            raise s_exc.BadArg(mesg='tabular:printer separator() requires char argument to be a single character')
        return self._makeRow([None] * self.colcnt).replace(' ', char)

    async def header(self):
        return self._makeRow([col['name'] for col in self.columns])

    async def row(self, data):
        data = await s_stormtypes.toprim(data)

        if not isinstance(data, (list, tuple)):
            raise s_exc.BadArg(mesg='tabular:printer row() requires a list argument')

        if len(data) != self.colcnt:
            mesg = 'tabular:printer row() requires data length to equal column count'
            raise s_exc.BadArg(mesg=mesg, length=len(data), column_length=self.colcnt)

        return self._makeRow(data)

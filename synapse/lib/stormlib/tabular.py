import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class TabularLib(s_stormtypes.Lib):
    '''
    TODO
    $columns = ([
        {"name": "woot", "width": 20, "justify": right},
        {"name": "hehe", "width" 30},
    ])
    $printer = $lib.tabular.printer($columns)

    $lib.print($printer.header())
    for $row in $rows {
        $lib.print($printer.row($row))
    }
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
        pass

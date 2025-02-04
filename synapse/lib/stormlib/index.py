import synapse.lib.stormtypes as s_stormtypes

stormcmds = (
    {
        'name': 'index.count.prop',
        'descr': '''
            Display the number of properties or property values in the view.

            Examples:

                // Display the number of file:path:ext properties in the view.
                index.count.prop file:path:ext

                // Display the number of file:path:ext properties with the value
                // "exe" in the view.
                index.count.prop file:path:ext --value exe

        ''',
        'cmdargs': (
            ('prop', {'help': 'The name of the form or property to count.'}),
            ('--value', {'help': 'The specific value to count instances of.',
                         'default': s_stormtypes.undef}),
        ),
        'storm': '''

        $conf = (
            {"columns": [
                {"name": "Count", "width": 12},
                {"name": "Layer Iden", "width": 32},
                {"name": "Layer Name"},
            ],
            "separators": {
                'data:row': ''
            },
        })
        $printer = $lib.tabular.printer($conf)

        $lib.print($printer.header())

        $total = (0)
        for $layer in $lib.view.get().layers {

            $count = $layer.getPropCount($cmdopts.prop, valu=$cmdopts.value)

            $total = ($total + $count)

            $lib.print($printer.row(($count, $layer.iden, $layer.name)))
        }
        $lib.print(`Total: {$total}`)
        ''',
    },
)

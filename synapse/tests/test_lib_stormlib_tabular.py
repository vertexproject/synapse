import synapse.exc as s_exc
import synapse.tests.utils as s_test

def printlines(mesgs):
    return [part for m in mesgs if m[0] == 'print' for part in m[1]['mesg'].split('\n')]

class TabularTest(s_test.SynTest):

    async def test_stormlib_tabular(self):

        async with self.getTestCore() as core:

            opts = {
                'vars': {
                    'rows': [
                        (1973, 'Issac Asimov', 'The Gods Themselves'),
                        (1974, 'Arthur C. Clarke', 'Rendezvous with Rama'),
                        (1975, 'Ursula K. Le Guin', 'The Dispossessed'),
                        (1976, 'Joe Haldeman', 'The Forever War'),
                    ],
                },
            }

            # get schema

            mesgs = await core.stormlist('$lib.print($lib.yaml.save($lib.tabular.schema()))')
            self.stormHasNoWarnErr(mesgs)
            self.stormIsInPrint('column:outline', mesgs)

            # single line defaults

            mesgs = await core.stormlist('''
                $printer = $lib.tabular.printer(({
                    "columns": [
                        {"name": "Year", "width": 6, "justify": "right"},
                        {"name": "Author", "width": 20, "justify": "center"},
                        {"name": "Title", "width": 12},
                    ]
                }))

                $lib.print($printer.header())
                for $row in $rows {
                    $lib.print($printer.row($row))
                }
            ''', opts=opts)
            self.stormHasNoWarnErr(mesgs)
            self.eq([
                '   Year |        Author        | Title        ',
                '========|======================|==============',
                '   1973 |     Issac Asimov     | The Gods ... ',
                '--------|----------------------|--------------',
                '   1974 |   Arthur C. Clarke   | Rendezvou... ',
                '--------|----------------------|--------------',
                '   1975 |  Ursula K. Le Guin   | The Dispo... ',
                '--------|----------------------|--------------',
                '   1976 |     Joe Haldeman     | The Forev... ',
            ], printlines(mesgs))

            # custom separators

            mesgs = await core.stormlist('''
                $printer = $lib.tabular.printer(({
                    "separators": {
                        "row:outline": true,
                        "column:outline": true,
                        "header:row": "#",
                        "data:row": "*",
                        "column": "+",
                    },
                    "columns": [
                        {"name": "Year", "width": 6, "justify": "right"},
                        {"name": "Author", "width": 20, "justify": "center"},
                        {"name": "Title", "width": 12},
                    ]
                }))

                $lib.print($printer.header())
                for $row in $rows {
                    $lib.print($printer.row($row))
                }
            ''', opts=opts)
            self.stormHasNoWarnErr(mesgs)
            self.eq([
                '+########+######################+##############+',
                '+   Year +        Author        + Title        +',
                '+########+######################+##############+',
                '+   1973 +     Issac Asimov     + The Gods ... +',
                '+********+**********************+**************+',
                '+   1974 +   Arthur C. Clarke   + Rendezvou... +',
                '+********+**********************+**************+',
                '+   1975 +  Ursula K. Le Guin   + The Dispo... +',
                '+********+**********************+**************+',
                '+   1976 +     Joe Haldeman     + The Forev... +',
                '+********+**********************+**************+',
            ], printlines(mesgs))

            # no col separators or end width

            mesgs = await core.stormlist('''
                $printer = $lib.tabular.printer(({
                    "separators": {
                        "header:row": "",
                        "data:row": "",
                        "column": "",
                    },
                    "columns": [
                        {"name": "Year", "width": 6, "justify": "right"},
                        {"name": "Author", "width": 20, "justify": "center"},
                        {"name": "Title"},
                    ]
                }))

                $lib.print($printer.header())
                for $row in $rows {
                    $lib.print($printer.row($row))
                }
            ''', opts=opts)
            self.stormHasNoWarnErr(mesgs)
            self.eq([
                '   Year         Author         Title ',
                '   1973      Issac Asimov      The Gods Themselves ',
                '   1974    Arthur C. Clarke    Rendezvous with Rama ',
                '   1975   Ursula K. Le Guin    The Dispossessed ',
                '   1976      Joe Haldeman      The Forever War ',
            ], printlines(mesgs))

            # wraps

            mesgs = await core.stormlist('''
                $printer = $lib.tabular.printer(({
                    "columns": [
                        {"name": "Year", "width": 6, "justify": "right"},
                        {"name": "Author", "width": 10, "justify": "center", "overflow": "wrap"},
                        {"name": "Title", "width": 10, "overflow": "wrap"},
                    ]
                }))

                $lib.print($printer.header())
                for $row in $rows {
                    $lib.print($printer.row($row))
                }
            ''', opts=opts)
            self.stormHasNoWarnErr(mesgs)
            self.eq([
                '   Year |   Author   | Title      ',
                '========|============|============',
                '   1973 |   Issac    | The Gods   ',
                '        |   Asimov   | Themselves ',
                '--------|------------|------------',
                '   1974 | Arthur C.  | Rendezvous ',
                '        |   Clarke   | with Rama  ',
                '--------|------------|------------',
                '   1975 | Ursula K.  | The Dispos ',
                '        |  Le Guin   | sessed     ',
                '--------|------------|------------',
                '   1976 |    Joe     | The        ',
                '        |  Haldeman  | Forever    ',
                '        |            | War        ',
            ], printlines(mesgs))

            # newlines

            mesgs = await core.stormlist('''
                $printer = $lib.tabular.printer(({
                    "columns": [
                        {"name": "Foo", "width": 10},
                        {"name": "Bar", "width": 10, "newlines": "split"},
                        {"name": "Baz", "newlines": "split"},
                    ],
                }))

                $lib.print($printer.header())
                $lib.print($printer.row(("aaa\\nbbb", "ccc\\nddd", "eee\\nfff")))
                $lib.print($printer.row(("a", "dummy", "row")))
            ''', opts=opts)
            self.stormHasNoWarnErr(mesgs)
            self.eq([
                ' Foo        | Bar        | Baz ',
                '============|============|=====',
                ' aaa bbb    | ccc ddd    | eee ',
                '            |            | fff ',
                '------------|------------|-----',
                ' a          | dummy      | row ',
            ], printlines(mesgs))

            # reprs

            mesgs = await core.stormlist('''
                $printer = $lib.tabular.printer(({
                    "separators": {"header:row": "", "data:row": ""},
                    "columns": [{"name": "Foo", "width": 20}],
                }))

                $lib.print($printer.row(($lib.null,)))
                $lib.print($printer.row((({"bar": "baz"}),)))
                $lib.print($printer.row((${ps:name=cool},)))
            ''', opts=opts)
            self.stormHasNoWarnErr(mesgs)
            self.eq([
                "                      ",
                " {'bar': 'baz'}       ",
                " ps:name=cool         ",
            ], printlines(mesgs))

            # sad

            with self.raises(s_exc.SchemaViolation):
                await core.nodes('$lib.tabular.printer(({"columns": [{"name": "newp", "width": -43}]}))')

            with self.raises(s_exc.BadArg) as ecm:
                await core.nodes('''
                    $printer = $lib.tabular.printer(({
                        "columns": [{"name": "Foo", "width": 20}],
                    }))
                    $printer.row(({"yeah": "no"}))
                ''')
            self.eq('tabular:printer row() requires a list argument', ecm.exception.errinfo['mesg'])

            with self.raises(s_exc.BadArg) as ecm:
                await core.nodes('''
                    $printer = $lib.tabular.printer(({
                        "columns": [{"name": "Foo", "width": 20}],
                    }))
                    $printer.row((too, many, items))
                ''')
            self.eq('tabular:printer row() requires data length to equal column count', ecm.exception.errinfo['mesg'])

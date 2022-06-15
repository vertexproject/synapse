import synapse.common as s_common

import synapse.tests.utils as s_test

class CsvTest(s_test.SynTest):

    async def test_storm_csv_emit(self):
        async with self.getTestCore() as core:
            await core.nodes('[test:str=1234 :tick=2001]')
            await core.nodes('[test:str=9876 :tick=3001]')

            q = "test:str " \
                "$tick=$node.repr(tick) " \
                "$lib.csv.emit($node.form(), $node.value(), $tick, table=mytable)"

            mesgs = await core.stormlist(q, {'show': ('err', 'csv:row')})
            csv_rows = [m for m in mesgs if m[0] == 'csv:row']
            self.len(2, csv_rows)
            csv_rows.sort(key=lambda x: x[1].get('row')[1])
            self.eq(csv_rows[0],
                    ('csv:row', {'row': ['test:str', '1234', '2001/01/01 00:00:00.000'],
                                 'table': 'mytable'}))
            self.eq(csv_rows[1],
                    ('csv:row', {'row': ['test:str', '9876', '3001/01/01 00:00:00.000'],
                                 'table': 'mytable'}))

            q = 'test:str $hehe=$node.props.hehe $lib.csv.emit(:tick, $hehe)'
            mesgs = await core.stormlist(q, {'show': ('err', 'csv:row')})
            csv_rows = [m for m in mesgs if m[0] == 'csv:row']
            self.len(2, csv_rows)
            self.eq(csv_rows[0], ('csv:row', {'row': [978307200000, None], 'table': None}))
            self.eq(csv_rows[1], ('csv:row', {'row': [32535216000000, None], 'table': None}))

            # Sad path case...
            q = '''
                [ test:str=woot ]
                $lib.csv.emit($path)
            '''
            mesgs = await core.stormlist(q, {'show': ('err', 'csv:row')})
            err = mesgs[-2]
            self.eq(err[1][0], 'NoSuchType')

    async def test_storm_csv_reader(self):
        async with self.getTestCore() as core:
            fp = self.getTestFilePath('addresses.csv')
            with s_common.genfile(fp) as fd:
                buf = fd.read()
            size, sha256 = await core.axon.put(buf)
            sha256 = s_common.ehex(sha256)
            q = '''
            $genr = $lib.csv.reader($sha256)
            for $row in $genr {
                $lib.print($row)
            }
            '''
            msgs = await core.stormlist(q, opts={'vars': {'sha256': sha256}})
            for m in msgs:
                print(m)

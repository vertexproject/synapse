import synapse.exc as s_exc
import synapse.tests.utils as s_test

import synapse.lib.stormlib.stats as s_stormlib_stats

chartnorm = '''
40 | 5 | ##################################################
30 | 4 | ########################################
20 | 3 | ##############################
10 | 2 | ####################
 0 | 1 | ##########
'''.strip()

chartrev = '''
 0 | 1 | ##########
10 | 2 | ####################
20 | 3 | ##############################
30 | 4 | ########################################
40 | 5 | ##################################################
'''.strip()

chartsize = '''
40 | 5 | ##################################################
30 | 4 | ########################################
20 | 3 | ##############################
'''.strip()

chartsizerev = '''
 0 | 1 | ##########
10 | 2 | ####################
20 | 3 | ##############################
'''.strip()

chartwidth = '''
40 | 5 | ##########
30 | 4 | ########
20 | 3 | ######
10 | 2 | ####
 0 | 1 | ##
'''.strip()

chartlabelwidth = '''
4 | 5 | ##################################################
3 | 4 | ########################################
2 | 3 | ##############################
1 | 2 | ####################
0 | 1 | ##########
'''.strip()

chartchar = '''
40 | 5 | ++++++++++++++++++++++++++++++++++++++++++++++++++
30 | 4 | ++++++++++++++++++++++++++++++++++++++++
20 | 3 | ++++++++++++++++++++++++++++++
10 | 2 | ++++++++++++++++++++
 0 | 1 | ++++++++++
'''.strip()


class StatsTest(s_test.SynTest):

    async def test_stormlib_stats_countby(self):

        async with self.getTestCore() as core:

            q = '''
            $i = (0)
            for $x in $lib.range(5) {
                for $y in $lib.range(($x + 1)) {
                    [ inet:ipv4=$i :asn=($x * 10) ]
                    $i = ($i + 1)
                }
            }
            '''
            await core.nodes(q)

            msgs = await core.stormlist('inet:ipv4 | stats.countby :asn')
            self.stormIsInPrint(chartnorm, msgs)

            msgs = await core.stormlist('inet:ipv4 -> inet:asn | stats.countby')
            self.stormIsInPrint(chartnorm, msgs)

            msgs = await core.stormlist('inet:ipv4 | stats.countby :asn --reverse')
            self.stormIsInPrint(chartrev, msgs)

            msgs = await core.stormlist('inet:ipv4 | stats.countby :asn --size 3')
            self.stormIsInPrint(chartsize, msgs)

            msgs = await core.stormlist('inet:ipv4 | stats.countby :asn --size 3 --reverse')
            self.stormIsInPrint(chartsizerev, msgs)

            msgs = await core.stormlist(f'inet:ipv4 | stats.countby :asn --bar-width 10')
            self.stormIsInPrint(chartwidth, msgs)

            msgs = await core.stormlist(f'inet:ipv4 | stats.countby :asn --label-max-width 1')
            self.stormIsInPrint(chartlabelwidth, msgs)

            msgs = await core.stormlist('inet:ipv4 | stats.countby :asn --char "+"')
            self.stormIsInPrint(chartchar, msgs)

            msgs = await core.stormlist('stats.countby foo')
            self.stormIsInPrint('No values to display!', msgs)

            self.len(0, await core.nodes('inet:ipv4 | stats.countby :asn'))
            self.len(15, await core.nodes('inet:ipv4 | stats.countby :asn --yield'))

            with self.raises(s_exc.BadArg):
                self.len(15, await core.nodes('inet:ipv4 | stats.countby :asn --label-max-width "-1"'))

            with self.raises(s_exc.BadArg):
                self.len(15, await core.nodes('inet:ipv4 | stats.countby :asn --bar-width "-1"'))

            with self.raises(s_exc.BadArg):
                self.len(15, await core.nodes('inet:ipv4 | stats.countby ({})'))

    async def test_stormlib_stats_tally(self):

        async with self.getTestCore() as core:

            q = '''
                $tally = $lib.stats.tally()

                $tally.inc(foo)
                $tally.inc(foo)

                $tally.inc(bar)
                $tally.inc(bar, 3)

                for ($name, $valu) in $tally {
                    [ test:comp=($valu, $name) ]
                }

                $lib.print('tally: foo={foo} baz={baz}', foo=$tally.get(foo), baz=$tally.get(baz))
                $lib.print('tally.len()={v}', v=$lib.len($tally))
            '''
            mesgs = await core.stormlist(q)
            nodes = [m[1] for m in mesgs if m[0] == 'node']
            self.len(2, nodes)
            self.eq(nodes[0][0], ('test:comp', (2, 'foo')))
            self.eq(nodes[1][0], ('test:comp', (4, 'bar')))
            self.stormIsInPrint('tally: foo=2 baz=0', mesgs)
            self.stormIsInPrint('tally.len()=2', mesgs)

            q = '''
                $tally = $lib.stats.tally()
                $tally.inc(foo, 1)
                $tally.inc(bar, 2)
                $tally.inc(baz, 3)
                return($tally.sorted())
            '''
            vals = await core.callStorm(q)
            self.eq(vals, [('foo', 1), ('bar', 2), ('baz', 3)])

            q = '''
                $tally = $lib.stats.tally()
                $tally.inc(foo, 1)
                $tally.inc(bar, 2)
                $tally.inc(baz, 3)
                return($tally.sorted(reverse=$lib.true))
            '''
            vals = await core.callStorm(q)
            self.eq(vals, [('baz', 3), ('bar', 2), ('foo', 1)])

            q = '''
                $tally = $lib.stats.tally()
                $tally.inc(foo, 1)
                $tally.inc(bar, 2)
                $tally.inc(baz, 3)
                return($tally.sorted(byname=$lib.true))
            '''
            vals = await core.callStorm(q)
            self.eq(vals, [('bar', 2), ('baz', 3), ('foo', 1)])

            q = '''
                $tally = $lib.stats.tally()
                $tally.inc(foo, 1)
                $tally.inc(bar, 2)
                $tally.inc(baz, 3)
                return($tally.sorted(byname=$lib.true, reverse=$lib.true))
            '''
            vals = await core.callStorm(q)
            self.eq(vals, [('foo', 1), ('baz', 3), ('bar', 2)])

            tally = s_stormlib_stats.StatTally()
            await tally.inc('foo')

            async for (name, valu) in tally:
                self.eq((name, valu), ('foo', 1))

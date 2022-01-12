import synapse.common as s_common

import synapse.tests.utils as s_test


class StormScrapeTest(s_test.SynTest):

    async def test_storm_lib_scrape_iface(self):
        pkgdef = {
            'name': 'foobar',
            'modules': [
                {'name': 'contextscrape',
                 'interfaces': ['scrape'],
                 'storm': '''
                 function scrape(text, form, unique) {
                    for ($sform, $svalu, $snfo) in $lib.scrape.context($text, form=$form, unique=$unique) {
                        emit ($snfo.offset, ($sform, $svalu, $snfo) )
                    }
                 }
                 '''},
                {'name': 'foobar',
                 'modconf': {'nameRegex': '(Name\\:\\s)(?<valu>[a-z0-9]+)\\s',
                             'form': 'ps:name'},
                 'interfaces': ['scrape'],
                 'storm': '''
                    $modRe = $modconf.nameRegex
                    $modForm = $modconf.form
                    /*
                    Example of a generic storm module implementing a scrape interface using
                    a common helper function that produces offset and raw_value information.
                    */
                    function scrape(text, form, unique) {
                        if ($form = $lib.null or $form = $modForm) {
                            for ($valu, $info) in $lib.scrape.genMatches($text, $modRe, unique=$unique) {
                                ($ok, $valu) = $lib.trycast($modForm, $valu)
                                if $ok {
                                    emit ($info.offset, ($modForm, $valu, $info))
                                }
                            }
                        }
                    }
                    '''
                 },
            ],
        }

        conf = {'provenance:en': False}
        async with self.getTestCore(conf=conf) as core:
            self.none(core.modsbyiface.get('scrape'))

            mods = await core.getStormIfaces('scrape')
            self.len(0, mods)
            self.len(0, core.modsbyiface.get('scrape'))

            await core.loadStormPkg(pkgdef)

            mods = await core.getStormIfaces('scrape')
            self.len(2, mods)
            self.len(2, core.modsbyiface.get('scrape'))

            text = '''
            NAME: billy
            IP: 8.7.6.5
            domain: foo.bar[.]com
            Homepage: http[:]//1.2[.]3.4/billy.html

            NAME: Alice
            IP: 3.0.0.9
            domain: foo.boofle.com
            Homepage: httpx://1.2[.]3.4/alice.html
            '''
            todo = s_common.todo('scrape', text, form=None, unique=False)
            vals = [r async for r in core.view.mergeStormIface('scrape', todo)]
            print('whoo')
            for v in vals:
                print(v)
            print('fin')

    async def test_storm_lib_scrape(self):

        async with self.getTestCore() as core:

            # Backwards compatibility $lib.scrape() adopters
            text = 'foo.bar comes from 1.2.3.4 which also knows about woot.com and its bad ness!'
            query = '''for ($form, $ndef) in $lib.scrape($text, $scrape_form, $refang)
            { $lib.print('{f}={n}', f=$form, n=$ndef) }
            '''
            varz = {'text': text, 'scrape_form': None, 'refang': True}
            msgs = await core.stormlist(query, opts={'vars': varz})
            self.stormIsInWarn('$lib.scrape() is deprecated. Use $lib.scrape.ndefs().', msgs)
            self.stormIsInPrint('inet:ipv4=16909060', msgs)
            self.stormIsInPrint('inet:fqdn=foo.bar', msgs)
            self.stormIsInPrint('inet:fqdn=woot.com', msgs)

            # $lib.scrape.ndefs()
            text = 'foo.bar comes from 1.2.3.4 which also knows about woot.com and its bad ness!'
            query = '''for ($form, $ndef) in $lib.scrape.ndefs($text, $scrape_form, $refang)
            { $lib.print('{f}={n}', f=$form, n=$ndef) }
            '''
            varz = {'text': text, 'scrape_form': None, 'refang': True}
            msgs = await core.stormlist(query, opts={'vars': varz})
            self.stormIsInPrint('inet:ipv4=16909060', msgs)
            self.stormIsInPrint('inet:fqdn=foo.bar', msgs)
            self.stormIsInPrint('inet:fqdn=woot.com', msgs)

            varz = {'text': text, 'scrape_form': 'inet:fqdn', 'refang': True}
            msgs = await core.stormlist(query, opts={'vars': varz})
            self.stormNotInPrint('inet:ipv4=16909060', msgs)
            self.stormIsInPrint('inet:fqdn=foo.bar', msgs)
            self.stormIsInPrint('inet:fqdn=woot.com', msgs)

            text = text + ' and then there was another 1.2.3.4 that happened at woot.com '
            query = '''$tally = $lib.stats.tally() for ($form, $ndef) in $lib.scrape.ndefs($text, unique=$unique)
            { $valu=$lib.str.format('{f}={n}', f=$form, n=$ndef) $tally.inc($valu) }
            fini { return ( $tally ) }
            '''
            varz = {'text': text, 'unique': True}
            result = await core.callStorm(query, opts={'vars': varz})
            self.eq(result, {'inet:ipv4=16909060': 1, 'inet:fqdn=foo.bar': 1, 'inet:fqdn=woot.com': 1})

            varz = {'text': text, 'unique': False}
            result = await core.callStorm(query, opts={'vars': varz})
            self.eq(result, {'inet:ipv4=16909060': 2, 'inet:fqdn=foo.bar': 1, 'inet:fqdn=woot.com': 2})

            # $lib.scrape.context() - this is currently just wrapping s_scrape.contextscrape
            query = '''$list = $lib.list() for $info in $lib.scrape.context($text, unique=$unique)
            { $list.append($info) }
            fini { return ( $list ) }
            '''
            varz = {'text': text, 'unique': True}
            results = await core.callStorm(query, opts={'vars': varz})
            self.len(3, results)
            ndefs = set()
            for (form, valu, info) in results:
                ndefs.add((form, valu))
                self.isinstance(info, dict)
                self.isinstance(form, str)
                self.isinstance(valu, (str, int))
                self.isin('offset', info)
                self.isin('raw_valu', info)
            self.eq(ndefs, {('inet:fqdn', 'woot.com'), ('inet:fqdn', 'foo.bar'),
                            ('inet:ipv4', 16909060,)})

            varz = {'text': text, 'unique': False}
            results = await core.callStorm(query, opts={'vars': varz})
            self.len(5, results)

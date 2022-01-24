import synapse.common as s_common

import synapse.tests.utils as s_test


class StormScrapeTest(s_test.SynTest):

    async def test_storm_lib_scrape_iface(self):
        pkgdef = {
            'name': 'scrapedemo',
            'modules': [
                {'name': 'scrapename',
                 'modconf': {'nameRegex': '(Name\\:\\s)(?<valu>[a-z0-9]+)\\s',
                             'form': 'ps:name',
                             },
                 'interfaces': ['scrape'],
                 'storm': '''
                    $modRe = $modconf.nameRegex
                    $modForm = $modconf.form
                    /*
                    Example of a generic storm module implementing a scrape interface using
                    a common helper function that produces offset and match information.

                    The helper does require a named match for valu this is extracted.
                    */
                    function scrape(text) {
                        $ret = $lib.list()
                        for ($valu, $info) in $lib.scrape.genMatches($text, $modRe) {
                            $ret.append(($modForm, $valu, $info))
                        }
                        return ( $ret )
                    }
                    '''
                 },
                {'name': 'scrape_hzzp_text',
                 'modconf': {'nameRegex': '(?P<valu>http[s]?://(?(?=[,.]+[ \'\"\t\n\r\f\v])|[^ \'\"\t\n\r\f\v])+)',
                             'form': 'inet:url',
                             'fangs': (
                                 ('hzzp[:]\\', 'http://'),
                                 ('hzzps[:]\\', 'https://'),
                             )
                             },
                 'interfaces': ['scrape'],
                 'storm': '''
                    $modRe = $modconf.nameRegex
                    $modForm = $modconf.form
                    $modFangs = $modconf.fangs
                    /*
                    Example of an storm module that scraps and matches on hzzp enfanged urls.
                    */
                    function scrape(text) {
                        $ret = $lib.list()
                        for ($valu, $info) in $lib.scrape.genMatches($text, $modRe, fangs=$modFangs) {
                            $ret.append(($modForm, $valu, $info))
                        }
                        return ( $ret )
                    }
                    '''
                 },
            ],
        }

        text = '''
        NAME: billy
        IP: 8.7.6.5
        domain: foo.bar[.]com
        Homepage: http[:]//1.2[.]3.4/billy.html

        NAME: Alice
        IP: 3.0.0.9
        domain: foo.boofle.com
        Homepage: hxxps://1.2[.]3.4/alice.html

        NAME: Mallory
        IP: 8.6.7.5
        domain: newp.net
        Homepage: hzzps[:]\\giggles.com/mallory.html

        NAME: Mallory
        IP: 8.6.7.5
        domain: newpers.net
        Homepage: hzzps[:]\\giggles.com/mallory.html
        '''
        q = '''for ($form, $valu, $info) in $lib.scrape.context($text) {
                        $lib.print('{f}={v} {i}', f=$form, v=$valu, i=$info)
                    }'''

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

            msgs = await core.stormlist(q, opts={'vars': {'text': text}})
            self.stormIsInPrint('ps:name=alice', msgs)
            self.stormIsInPrint('inet:fqdn=foo.bar.com', msgs)
            self.stormIsInPrint('inet:url=https://1.2.3.4/alice.html', msgs)
            self.stormIsInPrint('inet:url=https://giggles.com/mallory.html', msgs)
            self.stormIsInPrint("'match': 'hzzps[:]\\\\giggles.com/mallory.html'", msgs)

            cq = '''$ret=$lib.list()
            for ($form, $valu) in $lib.scrape.ndefs($text) {
                $ret.append(($form, $valu))
            }
            fini { return ($ret) }
            '''
            ndefs = await core.callStorm(cq, opts={'vars': {'text': text}})
            self.eq(ndefs, (('inet:url', 'http://1.2.3.4/billy.html'),
                            ('inet:url', 'https://1.2.3.4/alice.html'),
                            ('inet:ipv4', 134678021),
                            ('inet:ipv4', 16909060),
                            ('inet:ipv4', 50331657),
                            ('inet:ipv4', 134612741),
                            ('inet:fqdn', 'foo.bar.com'),
                            ('inet:fqdn', 'foo.boofle.com'),
                            ('inet:fqdn', 'newp.net'),
                            ('inet:fqdn', 'giggles.com'),
                            ('inet:fqdn', 'newpers.net'),
                            ('ps:name', 'billy'),
                            ('ps:name', 'alice'),
                            ('ps:name', 'mallory'),
                            ('inet:url', 'https://giggles.com/mallory.html')))

        conf = {'provenance:en': False, 'storm:interface:scrape': False, }
        async with self.getTestCore(conf=conf) as core:

            await core.loadStormPkg(pkgdef)

            mods = await core.getStormIfaces('scrape')
            self.len(2, mods)
            self.len(2, core.modsbyiface.get('scrape'))

            msgs = await core.stormlist(q, opts={'vars': {'text': text}})
            self.stormNotInPrint('ps:name=alice', msgs)
            self.stormIsInPrint('inet:fqdn=foo.bar.com', msgs)
            self.stormIsInPrint('inet:url=https://1.2.3.4/alice.html', msgs)

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
            # self.stormIsInPrint('inet:ipv4=16909060', msgs)
            self.stormIsInPrint('inet:ipv4=1.2.3.4', msgs)
            self.stormIsInPrint('inet:fqdn=foo.bar', msgs)
            self.stormIsInPrint('inet:fqdn=woot.com', msgs)

            # $lib.scrape.ndefs()
            text = 'foo.bar comes from 1.2.3.4 which also knows about woot.com and its bad ness!'
            query = '''for ($form, $ndef) in $lib.scrape.ndefs($text)
            { $lib.print('{f}={n}', f=$form, n=$ndef) }
            '''
            varz = {'text': text}
            msgs = await core.stormlist(query, opts={'vars': varz})
            self.stormIsInPrint('inet:ipv4=16909060', msgs)
            self.stormIsInPrint('inet:fqdn=foo.bar', msgs)
            self.stormIsInPrint('inet:fqdn=woot.com', msgs)

            text = text + ' and then there was another 1.2.3.4 that happened at woot.com '
            query = '''$tally = $lib.stats.tally() for ($form, $ndef) in $lib.scrape.ndefs($text)
            { $valu=$lib.str.format('{f}={n}', f=$form, n=$ndef) $tally.inc($valu) }
            fini { return ( $tally ) }
            '''
            varz = {'text': text}
            result = await core.callStorm(query, opts={'vars': varz})
            self.eq(result, {'inet:ipv4=16909060': 1, 'inet:fqdn=foo.bar': 1, 'inet:fqdn=woot.com': 1})

            # $lib.scrape.context() - this is currently just wrapping s_scrape.contextscrape
            query = '''$list = $lib.list() for $info in $lib.scrape.context($text)
            { $list.append($info) }
            fini { return ( $list ) }
            '''
            varz = {'text': text, 'unique': True}
            results = await core.callStorm(query, opts={'vars': varz})
            self.len(5, results)
            ndefs = set()
            for (form, valu, info) in results:
                ndefs.add((form, valu))
                self.isinstance(info, dict)
                self.isinstance(form, str)
                self.isinstance(valu, (str, int))
                self.isin('offset', info)
                self.isin('match', info)
            self.eq(ndefs, {('inet:fqdn', 'woot.com'), ('inet:fqdn', 'foo.bar'),
                            ('inet:ipv4', 16909060,)})

            varz = {'text': text, 'unique': False}
            results = await core.callStorm(query, opts={'vars': varz})
            self.len(5, results)

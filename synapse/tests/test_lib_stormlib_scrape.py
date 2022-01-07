import synapse.tests.utils as s_test


class StormScrapeTest(s_test.SynTest):

    async def test_storm_lib_scrape_iface(self):
        pkgdef = {
            'name': 'foobar',
            'modules': [
                {'name': 'foobar',
                 'modconf': {'pkgRegex': ''},
                 'interfaces': ['scrape'],
                 'storm': '''
                    function scrape(text, form, unique) {
                        for $match in $lib.regex.find
                        for $token in $tokens { $looks.append( (inet:fqdn, $token) ) }
                            return($looks)
                    }
                    '''
                 },
        ],
        }

    async def test_storm_lib_scrape(self):

        async with self.getTestCore() as core:

            # Backwards compatibility $lib.scrape() adopters
            text = 'foo.bar comes from 1.2.3.4 which also knows about woot.com and its bad ness!'
            query = '''for ($form, $ndef) in $lib.scrape($text, $ptype, $refang)
            { $lib.print('{f}={n}', f=$form, n=$ndef) }
            '''
            varz = {'text': text, 'ptype': None, 'refang': True}
            msgs = await core.stormlist(query, opts={'vars': varz})
            self.stormIsInWarn('$lib.scrape() is deprecated. Use $lib.scrape.ndefs().', msgs)
            self.stormIsInPrint('inet:ipv4=1.2.3.4', msgs)
            self.stormIsInPrint('inet:fqdn=foo.bar', msgs)
            self.stormIsInPrint('inet:fqdn=woot.com', msgs)

            # $lib.scrape.ndefs()
            text = 'foo.bar comes from 1.2.3.4 which also knows about woot.com and its bad ness!'
            query = '''for ($form, $ndef) in $lib.scrape.ndefs($text, $ptype, $refang)
            { $lib.print('{f}={n}', f=$form, n=$ndef) }
            '''
            varz = {'text': text, 'ptype': None, 'refang': True}
            msgs = await core.stormlist(query, opts={'vars': varz})
            self.stormIsInPrint('inet:ipv4=1.2.3.4', msgs)
            self.stormIsInPrint('inet:fqdn=foo.bar', msgs)
            self.stormIsInPrint('inet:fqdn=woot.com', msgs)

            varz = {'text': text, 'ptype': 'inet:fqdn', 'refang': True}
            msgs = await core.stormlist(query, opts={'vars': varz})
            self.stormNotInPrint('inet:ipv4=1.2.3.4', msgs)
            self.stormIsInPrint('inet:fqdn=foo.bar', msgs)
            self.stormIsInPrint('inet:fqdn=woot.com', msgs)

            text = text + ' and then there was another 1.2.3.4 that happened at woot.com '
            query = '''$tally = $lib.stats.tally() for ($form, $ndef) in $lib.scrape.ndefs($text, unique=$unique)
            { $valu=$lib.str.format('{f}={n}', f=$form, n=$ndef) $tally.inc($valu) }
            fini { return ( $tally ) }
            '''
            varz = {'text': text, 'unique': True}
            result = await core.callStorm(query, opts={'vars': varz})
            self.eq(result, {'inet:ipv4=1.2.3.4': 1, 'inet:fqdn=foo.bar': 1, 'inet:fqdn=woot.com': 1})

            varz = {'text': text, 'unique': False}
            result = await core.callStorm(query, opts={'vars': varz})
            self.eq(result, {'inet:ipv4=1.2.3.4': 2, 'inet:fqdn=foo.bar': 1, 'inet:fqdn=woot.com': 2})

            # $lib.scrape.context() - this is currently just wrapping s_scrape.contextscrape
            query = '''$list = $lib.list() for $info in $lib.scrape.context($text, unique=$unique)
            { $list.append($info) }
            fini { return ( $list ) }
            '''
            varz = {'text': text, 'unique': True}
            results = await core.callStorm(query, opts={'vars': varz})
            self.len(3, results)
            for r in results:
                self.isinstance(r, dict)
                self.isin('valu', r)
                self.isin('form', r)
                self.isin('offset', r)
                self.isin('raw_valu', r)

            varz = {'text': text, 'unique': False}
            results = await core.callStorm(query, opts={'vars': varz})
            self.len(5, results)

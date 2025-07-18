import synapse.exc as s_exc
import synapse.tests.utils as s_t_utils

class LangModuleTest(s_t_utils.SynTest):

    async def test_model_language(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                lang:translation=*
                    :input=(lang:phrase, Hola)
                    :input:lang={[ lang:language=({"code": "es"}) ]}
                    :output=Hi
                    :output:lang={[ lang:language=({"code": "en.us"}) ]}
                    :desc=Greetings
                    :engine=*
            ]''')
            self.len(1, nodes)

            self.eq(nodes[0].get('input'), ('lang:phrase', 'Hola'))
            self.eq(nodes[0].get('output'), 'Hi')
            self.eq(nodes[0].get('input:lang'), '0eae93b46d1c1951525424769faa5205')
            self.eq(nodes[0].get('output:lang'), 'a8eeae81da6c305c9cf6e4962bd106b2')
            self.eq(nodes[0].get('desc'), 'Greetings')

            # FIXME nodeprop indexing...
            # self.len(1, await core.nodes('lang:phrase <- *'))
            # self.len(1, await core.nodes('lang:translation -> lang:phrase'))

            self.len(1, await core.nodes('lang:translation -> it:software'))
            self.len(2, await core.nodes('lang:translation -> lang:language'))

            self.none(await core.callStorm('return($lib.gen.langByCode(neeeeewp, try=$lib.true))'))
            with self.raises(s_exc.BadTypeValu):
                await core.callStorm('return($lib.gen.langByCode(neeeeewp))')

            nodes = await core.nodes('[ lang:phrase="For   The  People" ]')
            self.len(1, nodes)
            self.eq('For   The  People', nodes[0].repr())

            nodes = await core.nodes('''
                [ lang:statement=*
                    :time=20150823
                    :speaker={[ ps:person=({"name": "visi"}) ]}
                    :text="We should be handing out UNCs like candy."
                    :transcript={[ ou:meet=* ]}
                    :transcript:offset=02:00
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('time'), 1440288000000000)
            self.eq(nodes[0].get('transcript:offset'), 120000000)
            self.eq(nodes[0].get('text'), 'We should be handing out UNCs like candy.')
            self.len(1, await core.nodes('lang:statement :speaker -> ps:person +:name=visi'))
            self.len(1, await core.nodes('lang:statement :transcript -> ou:meet'))

    async def test_hashtag(self):

        async with self.getTestCore() as core:

            self.len(1, await core.nodes('[ lang:hashtag="#🫠" ]'))
            self.len(1, await core.nodes('[ lang:hashtag="#🫠🫠" ]'))
            self.len(1, await core.nodes('[ lang:hashtag="#·bar"]'))
            self.len(1, await core.nodes('[ lang:hashtag="#foo·"]'))
            self.len(1, await core.nodes('[ lang:hashtag="#foo〜"]'))
            self.len(1, await core.nodes('[ lang:hashtag="#hehe" ]'))
            self.len(1, await core.nodes('[ lang:hashtag="#foo·bar"]'))  # note the interpunct
            self.len(1, await core.nodes('[ lang:hashtag="#foo〜bar"]'))  # note the wave dash
            self.len(1, await core.nodes('[ lang:hashtag="#fo·o·······b·ar"]'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ lang:hashtag="foo" ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ lang:hashtag="#foo#bar" ]')

            # All unicode whitespace from:
            # https://www.compart.com/en/unicode/category/Zl
            # https://www.compart.com/en/unicode/category/Zp
            # https://www.compart.com/en/unicode/category/Zs
            whitespace = [
                '\u0020', '\u00a0', '\u1680', '\u2000', '\u2001', '\u2002', '\u2003', '\u2004',
                '\u2005', '\u2006', '\u2007', '\u2008', '\u2009', '\u200a', '\u202f', '\u205f',
                '\u3000', '\u2028', '\u2029',
            ]
            for char in whitespace:
                with self.raises(s_exc.BadTypeValu):
                    await core.callStorm(f'[ lang:hashtag="#foo{char}bar" ]')

                with self.raises(s_exc.BadTypeValu):
                    await core.callStorm(f'[ lang:hashtag="#{char}bar" ]')

                # These are allowed because strip=True
                await core.callStorm(f'[ lang:hashtag="#foo{char}" ]')
                await core.callStorm(f'[ lang:hashtag=" #foo{char}" ]')

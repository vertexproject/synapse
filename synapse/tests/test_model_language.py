import synapse.exc as s_exc
import synapse.tests.utils as s_t_utils

class LangModuleTest(s_t_utils.SynTest):

    async def test_model_language(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                lang:translation=*
                    :input=Hola
                    :input:lang={[ lang:language=({"code": "es"}) ]}
                    :output=Hi
                    :output:lang={[ lang:language=({"code": "en-US"}) :name=english :names=(merican,) ]}
                    :desc=Greetings
                    :engine=* as it:software
                lang:phrase=Hola
            ]''')
            self.len(2, nodes)

            self.propeq(nodes[0], 'input', 'Hola')
            self.propeq(nodes[0], 'output', 'Hi')
            self.propeq(nodes[0], 'input:lang', '83e8f5fe6992924a7e88916cf8b5ba36')
            self.propeq(nodes[0], 'output:lang', '474dde882125a6b245841f39d28e1b97')
            self.propeq(nodes[0], 'desc', 'Greetings')

            self.len(1, await core.nodes('lang:phrase -> lang:translation:input'))

            self.len(1, await core.nodes('lang:translation :input as lang:phrase -> lang:phrase'))

            self.len(1, await core.nodes('lang:translation -> it:software'))
            self.len(2, await core.nodes('lang:translation -> lang:language'))

            nodes = await core.nodes('lang:language:code=en-US -> lang:name')
            self.sorteq(['english', 'merican'], [n.repr() for n in nodes])

            nodes = await core.nodes('[ lang:phrase="For   The  People" ]')
            self.len(1, nodes)
            self.eq('For   The  People', nodes[0].repr())

    async def test_model_lang_code(self):

        async with self.getTestCore() as core:

            # lang:code is now a BCP-47 form with canonical casing + subtag props
            nodes = await core.nodes('[ lang:code="EN-us" ]')
            self.len(1, nodes)
            self.eq(('lang:code', 'en-US'), nodes[0].ndef)
            self.propeq(nodes[0], 'language', 'en')
            self.propeq(nodes[0], 'region', 'US')
            self.none(nodes[0].get('script'))

            nodes = await core.nodes('[ lang:code="zh-hant-hk" ]')
            self.len(1, nodes)
            self.eq(('lang:code', 'zh-Hant-HK'), nodes[0].ndef)
            self.propeq(nodes[0], 'language', 'zh')
            self.propeq(nodes[0], 'script', 'Hant')
            self.propeq(nodes[0], 'region', 'HK')

            # numeric (UN M.49) region
            nodes = await core.nodes('[ lang:code="es-419" ]')
            self.eq(('lang:code', 'es-419'), nodes[0].ndef)
            self.propeq(nodes[0], 'region', '419')

            # single subtag language has no region/script subs
            nodes = await core.nodes('[ lang:code=PT ]')
            self.eq(('lang:code', 'pt'), nodes[0].ndef)
            self.propeq(nodes[0], 'language', 'pt')
            self.none(nodes[0].get('region'))

            # private use tag is preserved (lowercased) with no subs
            nodes = await core.nodes('[ lang:code="x-Klingon" ]')
            self.eq(('lang:code', 'x-klingon'), nodes[0].ndef)

            # extension subtags after a singleton are lowercased
            nodes = await core.nodes('[ lang:code="EN-A-BBB" ]')
            self.eq(('lang:code', 'en-a-bbb'), nodes[0].ndef)
            self.propeq(nodes[0], 'language', 'en')

            # subtag props are queryable
            self.len(1, await core.nodes('lang:code:region=HK'))
            self.len(1, await core.nodes('lang:code:language=zh'))
            self.len(1, await core.nodes('lang:code +:script=Hant'))

            # canonical casing dedups equivalent tags
            self.len(1, await core.nodes('[ lang:code="zh-HANT-hk" ]'))
            self.len(1, await core.nodes('lang:code=zh-Hant-HK'))

            # the subtag props are computed and may not be set directly
            with self.raises(s_exc.ReadOnlyProp):
                await core.nodes('lang:code=pt [ :region=BR ]')

            # malformed tags are rejected (the original unescaped-separator bug)
            for bad in ('', 'pt.br', 'pt--br', 'e', 'pt-b', 'en_US', 'en-', '-en', 'toolongsubtag'):
                with self.raises(s_exc.BadTypeValu):
                    await core.nodes('[ lang:code=$valu ]', opts={'vars': {'valu': bad}})

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

            # lang:hashtag is now a text type: case preserving but case insensitive
            nodes = await core.nodes('[ lang:hashtag="#HaShTaG" ]')
            self.eq(nodes[0].ndef, ('lang:hashtag', '#HaShTaG'))
            self.len(1, await core.nodes('[ lang:hashtag="#hashtag" ]'))
            self.len(1, await core.nodes('lang:hashtag="#HASHTAG"'))

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

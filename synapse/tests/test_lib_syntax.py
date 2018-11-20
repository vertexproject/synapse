import synapse.exc as s_exc
import synapse.datamodel as s_datamodel
import synapse.tests.utils as s_t_utils
import synapse.lib.syntax as s_syntax

class StormSyntaxTest(s_t_utils.SynTest):

    def test_storm_syntax_basic(self):
        insts = s_syntax.parse('''foo("lol",bar=20) baz(10, faz="lol")''')

        self.eq(insts[0][0], 'foo')
        self.eq(insts[0][1]['args'][0], 'lol')
        self.eq(insts[0][1]['kwlist'][0], ('bar', 20))

        self.eq(insts[1][0], 'baz')
        self.eq(insts[1][1]['args'][0], 10)
        self.eq(insts[1][1]['kwlist'][0], ('faz', 'lol'))

    def test_storm_syntax_uppercase_and_underscore(self):
        insts = s_syntax.parse('foo_Foo("lol",bar_Bar=20)')
        self.eq(insts[0], ('foo_Foo', {'args': ['lol'], 'kwlist': [('bar_Bar', 20)]}))

    def test_storm_syntax_macro_eq(self):
        ###########################################################
        insts = s_syntax.parse('foo:bar')
        self.eq(insts[0], s_syntax.oper('lift', 'foo:bar', None, by='has'))

        ###########################################################
        insts = s_syntax.parse('foo:bar=10')
        self.eq(insts[0], s_syntax.oper('lift', 'foo:bar', 10, by='eq'))

        ###########################################################
        insts = s_syntax.parse('foo:bar="woot"')
        self.eq(insts[0], s_syntax.oper('lift', 'foo:bar', 'woot', by='eq'))

        insts = s_syntax.parse("foo:bar='woot'")
        self.eq(insts[0], s_syntax.oper('lift', 'foo:bar', 'woot', by='eq'))

        ###########################################################
        #insts = s_syntax.parse('baz.faz/foo:bar@2015,+1year#30')
        #self.eq(insts[0], ('lift',{'cmp':'has','from':'baz.faz','prop':'foo:bar','when':('2015','+1year'),'limit':30}))

        ###########################################################
        #insts = s_syntax.parse('baz.faz/foo:bar@2015,+1year#30="woot"')
        #self.eq(insts[0], ('lift',{'cmp':'eq','from':'baz.faz','prop':'foo:bar','valu':'woot','when':('2015','+1year'),'limit':30}))

        ###########################################################
        #insts = s_syntax.parse('baz.faz/foo:bar@2015#30="woot"')
        #self.eq(insts[0], ('lift',{'cmp':'eq','from':'baz.faz','prop':'foo:bar','valu':'woot','when':('2015',None),'limit':30}))

    def test_storm_syntax_gele(self):

        insts = s_syntax.parse('foo:bar>=10')
        self.eq(insts[0], s_syntax.oper('lift', 'foo:bar', 10, by='ge'))

        insts = s_syntax.parse('foo:bar<=10')
        self.eq(insts[0], s_syntax.oper('lift', 'foo:bar', 10, by='le'))

    def test_storm_syntax_lifteq(self):
        insts = s_syntax.parse('foo:bar join("foo:bar","baz:quux")')
        self.eq(insts[0], s_syntax.oper('lift', 'foo:bar', None, by='has'))
        self.eq(insts[1], ('join', {'args': ['foo:bar', 'baz:quux'], 'kwlist': []}))

    def test_storm_syntax_liftlift(self):
        insts = s_syntax.parse('foo:bar baz:faz')
        self.eq(insts[0], s_syntax.oper('lift', 'foo:bar', None, by='has'))
        self.eq(insts[1], s_syntax.oper('lift', 'baz:faz', None, by='has'))

    def test_storm_syntax_regex(self):
        insts = s_syntax.parse('+foo:bar~="hehe" -foo:bar~="hoho"')
        self.eq(insts[0], ('filt', {'prop': 'foo:bar', 'mode': 'must', 'cmp': 're', 'valu': 'hehe'}))
        self.eq(insts[1], ('filt', {'prop': 'foo:bar', 'mode': 'cant', 'cmp': 're', 'valu': 'hoho'}))
        # Real world example with and without quotes around the regex valu
        insts = s_syntax.parse('#sig.mal.pennywise totags() +syn:tag~="bhv.aka" fromtags()')
        self.eq(len(insts), 4)
        self.eq(insts[0], ('alltag', {'args': ('sig.mal.pennywise',), 'kwlist': []}))
        self.eq(insts[1], ('totags', {'args': [], 'kwlist': []}))
        self.eq(insts[2], ('filt', {'cmp': 're', 'prop': 'syn:tag', 'mode': 'must', 'valu': 'bhv.aka'}))
        self.eq(insts[3], ('fromtags', {'args': [], 'kwlist': []}))
        # And without quotes
        insts = s_syntax.parse('#sig.mal.pennywise totags() +syn:tag~=bhv.aka fromtags()')
        self.eq(len(insts), 4)
        self.eq(insts[0], ('alltag', {'args': ('sig.mal.pennywise',), 'kwlist': []}))
        self.eq(insts[1], ('totags', {'args': [], 'kwlist': []}))
        self.eq(insts[2], ('filt', {'cmp': 're', 'prop': 'syn:tag', 'mode': 'must', 'valu': 'bhv.aka'}))
        self.eq(insts[3], ('fromtags', {'args': [], 'kwlist': []}))

    def test_storm_syntax_by(self):
        insts = s_syntax.parse('woot/foo:bar*baz="hehe"')
        opts = {'from': 'woot', 'by': 'baz'}
        self.eq(insts[0], s_syntax.oper('lift', 'foo:bar', 'hehe', **opts))

        insts = s_syntax.parse('woot/foo:bar*baz')
        self.eq(insts[0], s_syntax.oper('lift', 'foo:bar', None, **opts))

    def test_storm_syntax_pivot(self):
        insts = s_syntax.parse('foo:bar -> hehe.haha/baz:faz')
        self.eq(insts[0], ('pivot', {'args': ['foo:bar', 'baz:faz'], 'kwlist': [('from', 'hehe.haha')]}))

        insts = s_syntax.parse(' -> baz:faz')
        self.eq(insts[0], ('pivot', {'args': ('baz:faz',), 'kwlist': []}))

    def test_storm_syntax_join(self):
        insts = s_syntax.parse('foo:bar <- hehe.haha/baz:faz')
        self.eq(insts[0], ('join', {'args': ['foo:bar', 'baz:faz'], 'kwlist': [('from', 'hehe.haha')]}))

        insts = s_syntax.parse(' <- baz:faz')
        self.eq(insts[0], ('join', {'args': ('baz:faz',), 'kwlist': []}))

    def test_storm_syntax_whites(self):
        insts = s_syntax.parse('inet:fqdn     =      "1.2.3.4"')
        self.eq(insts[0], s_syntax.oper('lift', 'inet:fqdn', '1.2.3.4', by='eq'))

    def test_storm_syntax_comp_opts(self):
        valu, off = s_syntax.parse_valu('(foo,bar,baz=faz)')
        self.eq(valu, ['foo', 'bar', ('baz', 'faz')])

        valu, off = s_syntax.parse_valu('(foo, bar, baz=faz)')
        self.eq(valu, ['foo', 'bar', ('baz', 'faz')])

        valu, off = s_syntax.parse_valu('(   foo   ,    bar   ,   baz    =     faz    )')
        self.eq(valu, ['foo', 'bar', ('baz', 'faz')])

    def test_storm_syntax_edit(self):
        inst0 = s_syntax.parse('[inet:ipv4=127.0.0.1 inet:ipv4=127.0.0.2]')
        inst1 = s_syntax.parse('   [   inet:ipv4   =    127.0.0.1  inet:ipv4   =   127.0.0.2   ]   ')
        self.eq(inst0, inst1)

    def test_storm_syntax_oper_args(self):

        oper = s_syntax.parse(' woot( (1,2), lol, "hehe haha", one=(3,4), two=5, three=whee) ')[0]
        args = oper[1].get('args')
        opts = dict(oper[1].get('kwlist'))

        self.eq(args[0], [1, 2])
        self.eq(args[1], 'lol')
        self.eq(args[2], 'hehe haha')

        self.eq(opts.get('one'), [3, 4])
        self.eq(opts.get('two'), 5)
        self.eq(opts.get('three'), 'whee')

    def test_lib_syntax_int(self):
        self.eq(s_syntax.parse_int('  30 ', 0), (30, 5))
        self.eq(s_syntax.parse_int(' -30 ', 0), (-30, 5))

        self.eq(s_syntax.parse_int('  0xfF  ', 0), (15, 5))
        self.eq(s_syntax.parse_int('  0b01101001  ', 0), (105, 14))

        self.eq(s_syntax.parse_int(' -0xfF  ', 0), (-15, 5))
        self.eq(s_syntax.parse_int(' -0b01101001  ', 0), (-105, 14))

        self.eq(s_syntax.parse_int('  1.0 ', 0), (1.0, 6))
        self.eq(s_syntax.parse_int('  1.2 ', 0), (1.2, 6))
        self.eq(s_syntax.parse_int('  0.2 ', 0), (0.2, 6))
        self.eq(s_syntax.parse_int('  0.0 ', 0), (0.0, 6))
        self.eq(s_syntax.parse_int(' -1.2 ', 0), (-1.2, 6))
        self.eq(s_syntax.parse_int(' -0.2 ', 0), (-0.2, 6))
        self.eq(s_syntax.parse_int(' -0.0 ', 0), (0.0, 6))

        self.raises(s_exc.BadSyntaxError, s_syntax.parse_int, '0x', 0)
        self.raises(s_exc.BadSyntaxError, s_syntax.parse_int, 'asdf', 0)
        self.raises(s_exc.BadSyntaxError, s_syntax.parse_int, '0xzzzz', 0)
        self.raises(s_exc.BadSyntaxError, s_syntax.parse_int, '0bbbbb', 0)

    def test_lib_syntax_float(self):

        valu, off = s_syntax.parse_float('  1 ', 0)
        self.eq((valu, off), (1.0, 4))
        self.eq(valu, 1.0)
        self.eq(valu, 1)
        self.true(valu is not 1)

        self.eq(s_syntax.parse_float('  1.0 ', 0), (1.0, 6))
        self.eq(s_syntax.parse_float('  1.2 ', 0), (1.2, 6))
        self.eq(s_syntax.parse_float('  0.2 ', 0), (0.2, 6))
        self.eq(s_syntax.parse_float('  0.0 ', 0), (0.0, 6))
        self.eq(s_syntax.parse_float(' -1.2 ', 0), (-1.2, 6))
        self.eq(s_syntax.parse_float(' -0.2 ', 0), (-0.2, 6))
        self.eq(s_syntax.parse_float(' -0.0 ', 0), (0.0, 6))

        self.raises(s_exc.BadSyntaxError, s_syntax.parse_float, 'asdf', 0)
        self.raises(s_exc.BadSyntaxError, s_syntax.parse_float, '1.asdf', 0)

    def test_lib_syntax_term(self):
        self.raises(s_exc.BadSyntaxError, s_syntax.parse, '}')

    async def test_lib_syntax_query(self):
        async with self.getTestCore() as core:
            def q(text):
                parseinfo = {
                    'stormcmds': list(core.stormcmds.keys()),
                    'modelinfo': core.model.getModelInfo(),
                }
                retn = s_syntax.Parser(parseinfo, text).query()
                retn.init(core)
                return retn
            self.len(1, q('teststr=4').kids)
            self.len(1, q('teststr="4"').kids)
            self.len(1, q("teststr='4'").kids)
            self.len(2, q('inet:ipv4=1.2.3.0/24 +{ :asn -> inet:asn +:name~="visi k" }').kids)
            self.raises(s_exc.BadStormSyntax, q, '[x&f]')

    async def test_lib_syntax_query_client(self):
        '''
        Make sure we can do Parser stuff on client
        '''
        async with self.getTestDmon(mirror='dmoncore') as dmon, \
                await self.agetTestProxy(dmon, 'core') as core:

            parseinfo = await s_syntax.getRemoteParseInfo(core)
            retn = s_syntax.Parser(parseinfo, 'teststr=4').query()
            retn.init(core)
            return retn

    async def test_lib_syntax_stormcmd(self):
        async with self.getTestCore() as core:
            parseinfo = {
                'stormcmds': list(core.stormcmds.keys()),
                'modelinfo': core.model.getModelInfo(),
            }
            retn = s_syntax.Parser(parseinfo, ('''cmd.cmd 'he{}o' "o'leary" {[teststr='foo']}''')).stormcmd()
            self.eq(retn, ['cmd.cmd', 'he{}o', "o'leary", "{[teststr='foo']}"])

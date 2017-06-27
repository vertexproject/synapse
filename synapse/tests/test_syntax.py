from synapse.tests.common import *

import synapse.lib.syntax as s_syntax

class StormSyntaxTest(SynTest):

    def test_storm_syntax_basic(self):
        insts = s_syntax.parse('foo("lol",bar=20) baz(10,faz="lol")')

        self.assertEqual( insts[0][0], 'foo' )
        self.assertEqual( insts[0][1]['args'][0], 'lol' )
        self.assertEqual( insts[0][1]['kwlist'][0], ('bar',20) )

        self.assertEqual( insts[1][0], 'baz' )
        self.assertEqual( insts[1][1]['args'][0], 10 )
        self.assertEqual( insts[1][1]['kwlist'][0], ('faz','lol') )

    def test_storm_syntax_uppercase_and_underscore(self):
        insts = s_syntax.parse('foo_Foo("lol",bar_Bar=20)')
        self.eq(insts[0], ('foo_Foo',{'args':['lol'],'kwlist':[('bar_Bar',20)]}))

    def test_storm_syntax_macro_eq(self):
        ###########################################################
        insts = s_syntax.parse('foo:bar')
        self.eq(insts[0], s_syntax.oper('lift','foo:bar', None, by='has'))

        ###########################################################
        insts = s_syntax.parse('foo:bar=10')
        self.eq(insts[0], s_syntax.oper('lift','foo:bar', 10, by='eq'))

        ###########################################################
        insts = s_syntax.parse('foo:bar="woot"')
        self.eq(insts[0], s_syntax.oper('lift','foo:bar', 'woot', by='eq'))

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
        self.eq(insts[0],s_syntax.oper('lift', 'foo:bar', None, by='has'))
        self.eq(insts[1],('join',{'args':['foo:bar','baz:quux'],'kwlist':[]}))

    def test_storm_syntax_liftlift(self):
        insts = s_syntax.parse('foo:bar baz:faz')
        self.eq(insts[0], s_syntax.oper('lift','foo:bar', None, by='has'))
        self.eq(insts[1], s_syntax.oper('lift','baz:faz', None, by='has'))

    def test_storm_syntax_regex(self):
        insts = s_syntax.parse('+foo:bar~="hehe" -foo:bar~="hoho"')
        self.eq(insts[0],('filt',{'prop':'foo:bar','mode':'must','cmp':'re','valu':'hehe'}))
        self.eq(insts[1],('filt',{'prop':'foo:bar','mode':'cant','cmp':'re','valu':'hoho'}))
        self.eq({'woot':10},{'woot':10})

    def test_storm_syntax_by(self):
        insts = s_syntax.parse('woot/foo:bar*baz="hehe"')
        opts = {'from':'woot', 'by':'baz'}
        self.eq(insts[0], s_syntax.oper('lift','foo:bar','hehe', **opts))

        insts = s_syntax.parse('woot/foo:bar*baz')
        self.eq(insts[0], s_syntax.oper('lift','foo:bar',None,**opts))

    def test_storm_syntax_pivot(self):
        insts = s_syntax.parse('foo:bar -> hehe.haha/baz:faz')
        self.eq(insts[0], ('pivot',{'args':['baz:faz','foo:bar'],'kwlist':[('from','hehe.haha')]}))

    def test_storm_syntax_whites(self):
        insts = s_syntax.parse('inet:fqdn     =      "1.2.3.4"')
        self.eq(insts[0], s_syntax.oper('lift','inet:fqdn','1.2.3.4',by='eq'))

from synapse.tests.common import *

import synapse.swarm.syntax as s_syntax

class SwarmSyntaxTest(SynTest):

    def test_swarm_syntax_basic(self):
        insts = s_syntax.parse('foo("lol",bar=20) baz(10,faz="lol")')

        self.assertEqual( insts[0][0], 'foo' )
        self.assertEqual( insts[0][1]['args'][0], 'lol' )
        self.assertEqual( insts[0][1]['kwlist'][0], ('bar',20) )

        self.assertEqual( insts[1][0], 'baz' )
        self.assertEqual( insts[1][1]['args'][0], 10 )
        self.assertEqual( insts[1][1]['kwlist'][0], ('faz','lol') )

    def test_swarm_syntax_uppercase_and_underscore(self):
        insts = s_syntax.parse('foo_Foo("lol",bar_Bar=20)')

        self.assertEqual( insts[0][0], 'foo_Foo' )
        self.assertEqual( insts[0][1]['args'][0], 'lol' )
        self.assertEqual( insts[0][1]['kwlist'][0], ('bar_Bar',20) )

    def test_swarm_syntax_macro_eq(self):
        ###########################################################
        insts = s_syntax.parse('foo:bar')
        self.assertEqual( insts[0][0], 'has' )
        self.assertEqual( insts[0][1]['args'][0], 'foo:bar' )

        kwargs = dict(insts[0][1].get('kwlist'))

        self.assertIsNone( kwargs.get('from') )
        self.assertIsNone( kwargs.get('when') )
        self.assertIsNone( kwargs.get('limit') )

        ###########################################################
        insts = s_syntax.parse('foo:bar=10')
        self.assertEqual( insts[0][0], 'eq' )
        self.assertEqual( insts[0][1]['args'][0], 'foo:bar' )

        kwargs = dict(insts[0][1].get('kwlist'))
        self.assertEqual( kwargs.get('valu'), 10 )

        ###########################################################
        insts = s_syntax.parse('foo:bar="woot"')
        self.assertEqual( insts[0][0], 'eq' )
        self.assertEqual( insts[0][1]['args'][0], 'foo:bar' )

        kwargs = dict(insts[0][1].get('kwlist'))
        self.assertEqual( kwargs.get('valu'), 'woot' )

        ###########################################################
        insts = s_syntax.parse('baz.faz/foo:bar@2015,+1year#30="woot"')

        self.assertEqual( insts[0][0], 'eq' )
        self.assertEqual( insts[0][1]['args'][0], 'foo:bar' )

        kwargs = dict(insts[0][1].get('kwlist'))
        self.assertEqual( kwargs.get('limit'), 30)
        self.assertEqual( kwargs.get('from'), 'baz.faz' )
        self.assertEqual( kwargs.get('when'), ('2015','+1year'))

        ###########################################################
        insts = s_syntax.parse('baz.faz/foo:bar@2015#30="woot"')
        kwargs = dict(insts[0][1].get('kwlist'))
        self.assertEqual( kwargs.get('when'), ('2015',None))

    def test_swarm_syntax_gele(self):
        insts = s_syntax.parse('foo:bar>=10')
        kwargs = dict(insts[0][1].get('kwlist'))

        self.assertEqual( kwargs.get('valu'), 10)
        self.assertEqual( kwargs.get('cmp'), 'ge')

        insts = s_syntax.parse('foo:bar<=10')
        kwargs = dict(insts[0][1].get('kwlist'))

        self.assertEqual( kwargs.get('valu'), 10)
        self.assertEqual( kwargs.get('cmp'), 'le')

    def test_swarm_syntax_lifteq(self):
        insts = s_syntax.parse('foo:bar join("foo:bar","baz:quux")')
        self.assertEqual( insts, [
            ('has',{'args':['foo:bar'],'kwlist':[('cmp','has')],'mode':'lift'}),
            ('join',{'args':['foo:bar','baz:quux'],'kwlist':[]}),
        ])

    def test_swarm_syntax_liftlift(self):
        insts = s_syntax.parse('foo:bar baz:faz')
        self.assertEqual( insts, [
            ('has',{'args':['foo:bar'],'kwlist':[('cmp','has')],'mode':'lift'}),
            ('has',{'args':['baz:faz'],'kwlist':[('cmp','has')],'mode':'lift'}),
        ])

    def test_swarm_syntax_regex(self):
        insts = s_syntax.parse('+foo:bar~="hehe" -foo:bar~="hoho"')
        self.assertEqual( insts, [
            ('re',{'args':['foo:bar'],'kwlist':[('cmp','re'),('valu','hehe')],'mode':'must'}),
            ('re',{'args':['foo:bar'],'kwlist':[('cmp','re'),('valu','hoho')],'mode':'cant'}),
        ])

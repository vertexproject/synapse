from synapse.tests.common import *

import synapse.lib.scope as s_scope

class GeneTest(SynTest):

    def test_lib_scope(self):
        syms = {'foo':'woot','bar':30,'baz':[1,2]}
        scope = s_scope.Scope(**syms)

        self.eq( scope.get('bar'), 30 )
        self.eq( scope.get('foo'), 'woot' )
        self.eq( tuple( scope.iter('baz') ), (1,2) )

        with scope:

            scope.set('bar',20)
            scope.add('baz',3,4)

            self.eq( scope.get('bar'), 20 )
            self.eq( scope.get('foo'), 'woot' )
            self.eq( tuple( scope.iter('baz') ), (1,2,3,4) )

        self.eq( scope.get('bar'), 30 )
        self.eq( scope.get('foo'), 'woot' )
        self.eq( tuple( scope.iter('baz') ), (1,2) )

    def test_lib_scope_enter(self):

        with s_scope.enter({'woot':10}):
            self.eq( s_scope.get('woot'), 10 )
            self.assertIsNone( s_scope.get('newp') )

        self.assertIsNone( s_scope.get('woot') )
        self.assertIsNone( s_scope.get('newp') )

    def test_lib_scope_get_defval(self):
        syms = {'foo': None, 'bar': 123}
        scope = s_scope.Scope(**syms)
        self.eq(scope.get('foo'), None)
        self.eq(scope.get('foo', defval=None), None)
        self.eq(scope.get('bar'), 123)
        self.eq(scope.get('bar', defval=123), 123)
        self.eq(scope.get('boo'), None)
        self.eq(scope.get('boo', defval=None), None)

        scope.enter({'bar': 321})
        self.eq(scope.get('bar'), 321)
        self.eq(scope.get('bar', defval=321), 321)
        scope.leave()
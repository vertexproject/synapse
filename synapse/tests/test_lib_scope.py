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

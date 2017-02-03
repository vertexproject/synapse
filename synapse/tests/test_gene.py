from synapse.tests.common import *

import synapse.gene as s_gene

class GeneTest(SynTest):

    def test_gene_eval(self):

        def baz(x):
            return x + 20

        syms = {'foo:bar':10,'foo:baz':baz,'foo:faz':'woot'}

        self.eq( s_gene.eval('foo:bar & 1', syms=syms), 0 )
        self.eq( s_gene.eval('foo:bar ^ 2', syms=syms), 8 )
        self.eq( s_gene.eval('foo:bar | 1', syms=syms), 11 )

        self.eq( s_gene.eval('foo:bar', syms=syms), 10 )
        self.eq( s_gene.eval('foo:bar + 0x0a', syms=syms), 20 )
        self.eq( s_gene.eval('foo:baz(0x0a)', syms=syms), 30 )

        self.eq( s_gene.eval('20 == foo:bar + 0x0a', syms=syms), 1 )
        self.eq( s_gene.eval('foo:faz == "woot"', syms=syms), 1 )
        self.eq( s_gene.eval("foo:faz == 'woot'", syms=syms), 1 )

        self.eq( s_gene.eval('foo:baz(10) + 10', syms=syms), 40 )

        self.eq( s_gene.eval('foo:baz(10) < 100', syms=syms), 1 )
        self.eq( s_gene.eval('foo:baz(10) <= 100', syms=syms), 1 )

        self.eq( s_gene.eval('foo:baz(10) > 1', syms=syms), 1 )
        self.eq( s_gene.eval('foo:baz(10) >= 1', syms=syms), 1 )

        # FIXME operator precedence
        #self.eq( s_gene.eval('foo:bar + 0x0a == 20', syms=syms), 1 )

    def test_gene_lab(self):
        glab = s_gene.GeneLab()
        expr0 = glab.getGeneExpr('foo == 10')
        expr1 = glab.getGeneExpr('foo == 10')
        self.eq( id(expr0), id(expr1) )
        self.eq( expr0({'foo':10}), 1 )

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

        self.eq( s_gene.eval('foo:bar + 0x0a == 20', syms=syms), 1 )

    def test_gene_prec(self):
        self.eq( s_gene.eval('5 + 3 * 2'), 11 )
        self.eq( s_gene.eval('(5 + 3) * 2'), 16 )
        self.eq( s_gene.eval('9 / 3 <= 1 + 2'), 1)

    def test_gene_comp(self):
        self.eq( s_gene.eval('5 < 4 + 4'), 1 )
        self.eq( s_gene.eval('5 <= 4 + 4'), 1 )
        self.eq( s_gene.eval('5 > 8 - 4 - 2'), 1 )
        self.eq( s_gene.eval('5 >= 8 - 4 - 2'), 1 )

    def test_gene_call(self):

        def foo(x,y,z):
            return x + y + z

        syms = { 'foo':foo }

        self.eq( s_gene.eval('foo(1,2,3)',syms=syms), 6 )
        self.eq( s_gene.eval('foo(foo(1,2,3),9+9,3>2)',syms=syms), 25 )

    def test_gene_pow(self):
        self.eq( s_gene.eval(' 5 + 2**3 '), 13 )

    def test_gene_landlor(self):
        self.eq( s_gene.eval(' 10 > 3 && 10 + 10 > 19 '), 1 )
        self.eq( s_gene.eval(' 10 < 3 || 10 + 10 > 19 '), 1 )

        self.eq( s_gene.eval(' 10 < 3 && 10 + 10 > 19 '), 0 )
        self.eq( s_gene.eval(' 10 < 3 || 10 + 10 < 19 '), 0 )

    def test_gene_shift(self):
        self.eq( s_gene.eval(' 1 << 2 + 1'), 8 )
        self.eq( s_gene.eval(' 0x80 >> 0x00000004'), 8 )

    def test_gene_lab(self):
        glab = s_gene.GeneLab()
        expr0 = glab.getGeneExpr('foo == 10')
        expr1 = glab.getGeneExpr('foo == 10')
        self.eq( id(expr0), id(expr1) )
        self.eq( expr0({'foo':10}), 1 )

    def test_gene_noname(self):
        self.assertRaises( NoSuchName, s_gene.eval('x + 20') )

import synapse.lib.dark as s_dark

from synapse.tests.common import *

class DarkTest(SynTest):

    def test_dark_gendarkrows(self):
        iden = '12345678' * 4
        valus = ['a', 'b', 'c']

        dark_iden = iden[::-1]
        for idx, (i, p, v, t) in enumerate(list(s_dark.genDarkRows(iden, 'hehe', valus))):
            self.eq(i, dark_iden)
            self.eq(p, '_:dark:hehe')
            self.eq(v, valus[idx])

import os
import binascii
import unittest

import synapse.cortex as cortex

from binascii import hexlify
from synapse.common import *

class CortexTest(unittest.TestCase):

    def test_cortex_ram(self):
        self.runcore( cortex.open('ram://') )

    def test_cortex_sqlite3(self):
        core = cortex.open('sqlite:///:memory:?table=woot')
        self.runcore( core )
        self.runrange( core )

    def test_cortex_postgres(self):
        db = os.getenv('SYN_COR_PG_DB')
        if db == None:
            raise unittest.SkipTest('no SYN_COR_PG_DB')

        link = ('postgres',{'path':'/%s' % db})
        core = cortex.openlink(link)

        self.runcore( core )
        self.runrange( core )

    def runcore(self, core):

        id1 = hexlify(guid()).decode('utf8')
        id2 = hexlify(guid()).decode('utf8')

        rows = [
            (id1,'foo','bar',30),
            (id1,'baz','faz1',30),
            (id1,'gronk',80,30),

            (id2,'foo','bar',99),
            (id2,'baz','faz2',99),
            (id2,'gronk',90,99),
        ]

        core.addRows( rows )

        self.assertEqual( core.getSizeByProp('foo'), 2 )
        self.assertEqual( core.getSizeByProp('baz',valu='faz1'), 1 )
        self.assertEqual( core.getSizeByProp('foo',mintime=80,maxtime=100), 1 )

        self.assertEqual( len(core.getRowsByProp('foo')), 2 )
        self.assertEqual( len(core.getRowsByProp('foo',valu='bar')), 2 )

        self.assertEqual( len(core.getRowsByProp('baz')), 2 )
        self.assertEqual( len(core.getRowsByProp('baz',valu='faz1')), 1 )
        self.assertEqual( len(core.getRowsByProp('baz',valu='faz2')), 1 )

        self.assertEqual( len(core.getRowsByProp('gronk',valu=90)), 1 )

        self.assertEqual( len(core.getRowsById(id1)), 3)

        self.assertEqual( len(core.getJoinByProp('baz')), 6 )
        self.assertEqual( len(core.getJoinByProp('baz',valu='faz1')), 3 )
        self.assertEqual( len(core.getJoinByProp('baz',valu='faz2')), 3 )

        self.assertEqual( len(core.getRowsByProp('baz',mintime=0,maxtime=80)), 1 )
        self.assertEqual( len(core.getJoinByProp('baz',mintime=0,maxtime=80)), 3 )

        self.assertEqual( len(core.getRowsByProp('baz',limit=1)), 1 )
        self.assertEqual( len(core.getJoinByProp('baz',limit=1)), 3 )

        core.delRowsById(id1)

        self.assertEqual( len(core.getRowsById(id1)), 0 )

        core.fini()

    def runrange(self, core):

        rows = [
            (guid(),'rg',10,99),
            (guid(),'rg',30,99),
        ]

        core.addRows( rows )

        self.assertEqual( core.getSizeBy('range','rg','0,20'), 1 )
        self.assertEqual( len( core.getRowsBy('range','rg','0,20')), 1 )


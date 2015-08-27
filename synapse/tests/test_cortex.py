import os
import binascii
import unittest

import synapse.cortex as s_cortex

from synapse.common import *
from synapse.cores.common import NoSuchJob

class CortexTest(unittest.TestCase):

    def test_cortex_ram(self):
        core = s_cortex.openurl('ram://')
        self.runcore( core )
        self.runrange( core )

    def test_cortex_sqlite3(self):
        core = s_cortex.openurl('sqlite:///:memory:?table=woot')
        self.runcore( core )
        self.runrange( core )

    def test_cortex_postgres(self):
        db = os.getenv('SYN_COR_PG_DB')
        if db == None:
            raise unittest.SkipTest('no SYN_COR_PG_DB')

        table = 'syn_test_%s' % guidstr()

        link = ('postgres',{'path':'/%s' % db, 'table':table})
        core = s_cortex.openlink(link)

        try:
            self.runcore( core )
            self.runrange( core )
        finally:
            with core.cursor() as c:
                c.execute('DROP TABLE %s' % (table,))

    def runcore(self, core):

        id1 = guidstr()
        id2 = guidstr()
        id3 = guidstr()

        rows = [
            (id1,'foo','bar',30),
            (id1,'baz','faz1',30),
            (id1,'gronk',80,30),

            (id2,'foo','bar',99),
            (id2,'baz','faz2',99),
            (id2,'gronk',90,99),

            (id3,'a','a',99),
            (id3,'b','b',99),
            (id3,'c',90,99),
        ]

        core.addRows( rows )

        tufo = core.getTufoByProp('baz','faz1')

        self.assertEqual( tufo[0], id1 )
        self.assertEqual( tufo[1].get('foo'), 'bar')
        self.assertEqual( tufo[1].get('baz'), 'faz1')
        self.assertEqual( tufo[1].get('gronk'), 80 )

        self.assertEqual( core.getSizeByProp('foo:newp'), 0 )
        self.assertEqual( len(core.getRowsByProp('foo:newp')), 0 )

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

        self.assertEqual( len(core.getRowsByProp('b',valu='b')), 1 )
        core.delRowsByProp('b',valu='b')
        self.assertEqual( len(core.getRowsByProp('b',valu='b')), 0 )

        self.assertEqual( len(core.getRowsByProp('a',valu='a')), 1 )
        core.delJoinByProp('c',valu=90)
        self.assertEqual( len(core.getRowsByProp('a',valu='a')), 0 )

        def addtufo(event):
            tufo = event[1].get('tufo')
            core.addTufoProps(tufo, woot='woot')

        def addfqdn(event):
            t = event[1].get('tufo')
            fqdn = t[1].get('fqdn')
            core.addTufoProps(t,tld=fqdn.split('.')[-1])

        core.on('cortex:tufo:add', addtufo)
        core.on('cortex:tufo:add:fqdn', addfqdn)

        tufo = core.formTufoByProp('fqdn','woot.com')

        self.assertEqual( tufo[1].get('tld'), 'com')
        self.assertEqual( tufo[1].get('woot'), 'woot')

        core.fini()

    def runrange(self, core):

        rows = [
            (guidstr(),'rg',10,99),
            (guidstr(),'rg',30,99),
        ]

        core.addRows( rows )

        self.assertEqual( core.getSizeBy('range','rg',(0,20)), 1 )
        self.assertEqual( len( core.getRowsBy('range','rg',(0,20))), 1 )

    def test_cortex_choptag(self):

        t0 = tuple(s_cortex.choptag('foo'))
        t1 = tuple(s_cortex.choptag('foo.bar'))
        t2 = tuple(s_cortex.choptag('foo.bar.baz'))

        self.assertEqual( t0, ('foo',))
        self.assertEqual( t1, ('foo','foo.bar'))
        self.assertEqual( t2, ('foo','foo.bar','foo.bar.baz'))

    def test_cortex_meta(self):
        meta = s_cortex.MetaCortex()

        meta.addCortex('foo.bar','ram:///',tags=('woot.hehe',))
        meta.addCortex('foo.baz','ram:///',tags=('woot.hoho',))

        self.assertIsNotNone( meta.getCortex('foo.bar') )
        self.assertIsNotNone( meta.getCortex('foo.baz') )

        self.assertEqual( len( meta.getCortexes('woot') ), 2 )
        self.assertEqual( len( meta.getCortexes('woot.hoho') ), 1 )
        self.assertEqual( len( meta.getCortexes('woot.hehe') ), 1 )

        meta.fini()

    def test_cortex_meta_query(self):

        meta = s_cortex.MetaCortex()

        meta.addCortex('foo.bar','ram:///',tags=('woot.hehe',))
        meta.addCortex('foo.baz','ram:///',tags=('woot.hoho',))

        core0 = meta.getCortex('foo.bar')
        core1 = meta.getCortex('foo.baz')

        id0 = guidstr()
        id1 = guidstr()
        id2 = guidstr()
        id3 = guidstr()

        rows0 = (
            (id0,'a',10,99),
            (id1,'x',10,80),
            (id1,'ha','ho',80),
        )
        rows1 = (
            (id2,'c',10,99),
            (id3,'x',10,80),
            (id3,'ha','ho',80),
        )

        j0 = core0.addRows(rows0, async=True)
        j1 = core1.addRows(rows1, async=True)

        self.assertTrue( core0.waitForJob(j0, timeout=3) )
        self.assertTrue( core1.waitForJob(j1, timeout=3) )

        tufos = meta.getTufosByQuery('foo:x=10')
        self.assertEqual( len(tufos), 2 )

        tfdict = dict(tufos)
        self.assertEqual( tfdict.get(id1).get('ha'), 'ho')
        self.assertEqual( tfdict.get(id3).get('ha'), 'ho')

        res = meta.getRowsByQuery('foo.bar:ha="ho"')
        self.assertEqual( len(res), 1 )

        res = meta.getRowsByQuery('foo:ha')
        size = meta.getSizeByQuery('foo:ha')
        self.assertEqual( size, 2 )
        self.assertEqual( len(res), 2 )

        res = meta.getRowsByQuery('foo:x=10')
        size = meta.getSizeByQuery('foo:x=10')
        self.assertEqual( size, 2 )
        self.assertEqual( len(res), 2 )

        res = meta.getRowsByQuery('foo.baz:x=10')
        size = meta.getSizeByQuery('foo.baz:x=10')
        self.assertEqual( size, 1 )
        self.assertEqual( len(res), 1 )

        res = meta.getRowsByQuery('foo:x*range=(8,40)')
        size = meta.getSizeByQuery('foo:x*range=(8,40)')
        self.assertEqual( size, 2 )
        self.assertEqual( len(res), 2 )

        res = meta.getJoinByQuery('foo:x=10')
        self.assertEqual( len(res), 4 )

        size = meta.getSizeByQuery('newp:newp=3')
        self.assertEqual( size , 0 )

        rows = meta.getRowsByQuery('newp:newp=3')
        self.assertEqual( len(rows), 0 )

        join = meta.getJoinByQuery('newp:newp=3')
        self.assertEqual( len(join), 0 )

        meta.fini()

    def test_cortex_meta_query_parser(self):
        meta = s_cortex.MetaCortex()

        qinfo = meta._parseQuery('foo:bar')

        self.assertEqual( qinfo.get('tag'), 'foo' )
        self.assertEqual( qinfo.get('prop'), 'bar' )

        qinfo = meta._parseQuery('foo:bar=30')
        self.assertEqual( qinfo.get('tag'), 'foo' )
        self.assertEqual( qinfo.get('prop'), 'bar' )
        self.assertEqual( qinfo.get('valu'), 30 )

        qinfo = meta._parseQuery('foo:bar@2015,2016=30')
        self.assertEqual( qinfo.get('tag'), 'foo' )
        self.assertEqual( qinfo.get('prop'), 'bar' )
        self.assertEqual( qinfo.get('valu'), 30 )
        #self.assertEqual( qinfo.get('mintime'), 30 )
        #self.assertEqual( qinfo.get('maxtime'), 30 )

        qinfo = meta._parseQuery('foo:bar#100="hehe"')
        self.assertEqual( qinfo.get('tag'), 'foo' )
        self.assertEqual( qinfo.get('prop'), 'bar' )
        self.assertEqual( qinfo.get('valu'), 'hehe' )
        self.assertEqual( qinfo.get('limit'), 100 )

        qinfo = meta._parseQuery('foo:bar#100*range=(10,30)')
        self.assertEqual( qinfo.get('by'), 'range' )
        self.assertEqual( qinfo.get('tag'), 'foo' )
        self.assertEqual( qinfo.get('prop'), 'bar' )
        self.assertEqual( qinfo.get('valu'), (10,30) )
        self.assertEqual( qinfo.get('limit'), 100 )

        meta.fini()

    def test_cortex_async_nosuchjob(self):

        id1 = guidstr()
        core = s_cortex.openurl('ram://')
        self.assertRaises( NoSuchJob, core.getAsyncReturn, 'foo' )
        core.fini()

    def test_cortex_async_result(self):
        id1 = guidstr()
        core = s_cortex.openurl('ram://')

        rows = [
            (id1,'foo','bar',30),
            (id1,'baz','faz1',30),
            (id1,'gronk',80,30),
        ]
        core.addRows( rows )
        jid = core.callAsyncApi('getRowsById',id1)
        rows = core.getAsyncReturn(jid)

        self.assertEqual( len(rows), 3 )

        core.fini()

    def test_cortex_meta_getnames(self):
        meta = s_cortex.MetaCortex()

        meta.addCortex('foo.bar','ram:///',tags=('woot.hehe',))
        meta.addCortex('foo.baz','ram:///',tags=('woot.hoho',))

        names = meta.getCortexNames()
        names.sort()

        self.assertEqual( ('foo.bar','foo.baz'), tuple(names) )

        meta.fini()

    def test_cortex_meta_addmeta(self):
        id1 = guidstr()
        meta = s_cortex.MetaCortex()

        meta.addCortex('foo.bar','ram:///',tags=('woot.hehe',))
        meta.addCortex('foo.baz','ram:///',tags=('woot.hoho',))

        rows = (
            (id1,'woot',20,80),
            (id1,'foo','bar',80),
        )

        meta.addMetaRows('foo.bar',rows)
        self.assertEqual( meta.getSizeByQuery('foo:woot'), 1 )

        meta.fini()

    def test_cortex_meta_corapi(self):
        id1 = guidstr()
        meta = s_cortex.MetaCortex()

        meta.addCortex('foo.bar','ram:///',tags=('woot.hehe',))
        meta.addCortex('foo.baz','ram:///',tags=('woot.hoho',))

        rows = (
            (id1,'woot',20,80),
            (id1,'foo','bar',80),
        )

        meta.addMetaRows('foo.bar',rows)
        self.assertEqual( meta.callCorApi('foo.bar','getSizeByProp','woot'), 1 )

        meta.fini()

    def test_cortex_meta_noname(self):
        meta = s_cortex.MetaCortex()
        self.assertRaises( s_cortex.NoSuchName, meta.addMetaRows, 'hehe', [] )
        meta.fini()

    def test_cortex_meta_query_event(self):
        meta = s_cortex.MetaCortex()
        meta.addCortex('foo.bar','ram:///',tags=('woot.hehe',))
        meta.addCortex('foo.baz','ram:///',tags=('woot.hoho',))

        def metaqueryrows(event):
            query = event[1].get('query')
            query['limit'] = 1

        def metaqueryjoin(event):
            query = event[1].get('query')
            query['valu'] = 99

        meta.on('meta:query:rows',metaqueryrows)
        meta.on('meta:query:join',metaqueryjoin)

        id1 = guidstr()
        id2 = guidstr()
        rows = [ 
            (id1,'foo',10,10),
            (id1,'haha',10,10),

            (id2,'foo',20,20),
            (id2,'haha',20,20),
        ]
        meta.addMetaRows('foo.bar',rows)

        rows = meta.getRowsByQuery('foo:foo')
        self.assertEqual( len(rows), 1 )

        rows = meta.getJoinByQuery('foo:foo')
        self.assertEqual( len(rows), 0 )

    def test_cortex_meta_query_perm(self):
        meta = s_cortex.MetaCortex()
        meta.addCortex('foo.bar','ram:///',tags=('woot.hehe',))
        meta.addCortex('foo.baz','ram:///',tags=('woot.hoho',))

        def newp(event):
            event[1]['allow'] = False

        meta.on('meta:query:rows',newp)
        meta.on('meta:query:join',newp)

        id1 = guidstr()
        id2 = guidstr()
        rows = [ 
            (id1,'foo',10,10),
            (id1,'haha',10,10),

            (id2,'foo',20,20),
            (id2,'haha',20,20),
        ]
        meta.addMetaRows('foo.bar',rows)

        rows = meta.getRowsByQuery('foo:foo')
        self.assertEqual( len(rows), 0 )

        rows = meta.getJoinByQuery('foo:foo')
        self.assertEqual( len(rows), 0 )

    def test_cortex_meta_del(self):
        meta = s_cortex.MetaCortex()
        meta.addCortex('foo.bar','ram:///',tags=('woot.hehe',))

        meta.delCortex('foo.bar')
        self.assertIsNone( meta.getCortex('foo.bar') )
        meta.fini()

    def test_cortex_notok(self):
        meta = s_cortex.MetaCortex()
        meta.addCortex('foo.bar','ram:///',tags=('woot.hehe',))
        meta.addCortex('foo.baz','ram:///',tags=('woot.hehe',))

        id1 = guidstr()
        meta.addMetaRows('foo.bar',(
            (id1,'foo',10,10),
            (id1,'haha',10,10),
        ))

        id2 = guidstr()
        meta.addMetaRows('foo.baz',(
            (id2,'foo',20,20),
            (id2,'haha',20,20),
        ))

        core = meta.getCortex('foo.bar')
        oldmeth = core.getRowsByProp

        def dorked(*args,**kwargs):
            raise Exception('hi')

        core.isok = False
        core.getRowsByProp = dorked

        rows = meta.getRowsByQuery('foo:foo')

        self.assertEqual( len(rows), 1 )
        self.assertFalse( meta.coreok.get('foo.bar') )

        core.isok = True
        core.getRowsByProp = oldmeth
        meta._tryCoreOk('foo.bar')

        self.assertTrue( meta.coreok.get('foo.bar') )

        rows = meta.getRowsByQuery('foo:foo')
        self.assertEqual( len(rows), 2 )


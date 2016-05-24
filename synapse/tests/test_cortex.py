import os
import logging
import binascii
import unittest

import synapse.link as s_link
import synapse.compat as s_compat
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.tags as s_tags

from synapse.tests.common import *

class CortexTest(SynTest):

    def test_cortex_ram(self):
        core = s_cortex.openurl('ram://')
        self.assertTrue( hasattr( core.link, '__call__' ) )
        self.runcore( core )
        self.runjson( core )
        self.runrange( core )

    def test_cortex_sqlite3(self):
        core = s_cortex.openurl('sqlite:///:memory:')
        self.runcore( core )
        self.runjson( core )
        self.runrange( core )

    def test_cortex_postgres(self):
        db = os.getenv('SYN_COR_PG_DB')
        if db == None:
            raise unittest.SkipTest('no SYN_COR_PG_DB')

        table = 'syn_test_%s' % guid()

        link = s_link.chopLinkUrl('postgres:///%s/%s' % (db,table))
        core = s_cortex.openlink(link)

        try:
            self.runcore( core )
            self.runjson( core )
            self.runrange( core )
        finally:
            with core.cursor() as c:
                c.execute('DROP TABLE %s' % (table,))

    def runcore(self, core):

        id1 = guid()
        id2 = guid()
        id3 = guid()
        id4 = guid()

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

            (id4,'lolint',80,30),
            (id4,'lolstr','hehe',30),

        ]

        core.addRows( rows )

        tufo = core.getTufoByProp('baz','faz1')

        self.assertEqual( len(core.getRowsByIdProp(id1,'baz')), 1)

        #pivo = core.getPivotByProp('baz','foo', valu='bar')
        #self.assertEqual( tuple(sorted([r[2] for r in pivo])), ('faz1','faz2'))

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

        core.setRowsByIdProp(id4,'lolstr','haha')
        self.assertEqual( len(core.getRowsByProp('lolstr','hehe')), 0 )
        self.assertEqual( len(core.getRowsByProp('lolstr','haha')), 1 )

        core.setRowsByIdProp(id4,'lolint', 99)
        self.assertEqual( len(core.getRowsByProp('lolint', 80)), 0 )
        self.assertEqual( len(core.getRowsByProp('lolint', 99)), 1 )

        core.delRowsByIdProp(id4,'lolint')
        core.delRowsByIdProp(id4,'lolstr')

        self.assertEqual( len(core.getRowsByProp('lolint')), 0 )
        self.assertEqual( len(core.getRowsByProp('lolstr')), 0 )

        core.delRowsById(id1)

        self.assertEqual( len(core.getRowsById(id1)), 0 )

        self.assertEqual( len(core.getRowsByProp('b',valu='b')), 1 )
        core.delRowsByProp('b',valu='b')
        self.assertEqual( len(core.getRowsByProp('b',valu='b')), 0 )

        self.assertEqual( len(core.getRowsByProp('a',valu='a')), 1 )
        core.delJoinByProp('c',valu=90)
        self.assertEqual( len(core.getRowsByProp('a',valu='a')), 0 )

        def formtufo(event):
            props = event[1].get('props')
            props['woot'] = 'woot'

        def formfqdn(event):
            fqdn = event[1].get('valu')
            event[1]['props']['tld'] = fqdn.split('.')[-1]

        core.on('tufo:form', formtufo)
        core.on('tufo:form:fqdn', formfqdn)

        tufo = core.formTufoByProp('fqdn','woot.com')

        self.assertEqual( tufo[1].get('tld'), 'com')
        self.assertEqual( tufo[1].get('woot'), 'woot')

        core.fini()

    def runrange(self, core):

        rows = [
            (guid(),'rg',10,99),
            (guid(),'rg',30,99),
        ]

        core.addRows( rows )

        self.assertEqual( core.getSizeBy('range','rg',(0,20)), 1 )
        self.assertEqual( len( core.getRowsBy('range','rg',(0,20))), 1 )

    def runjson(self, core):

        thing = {
            'foo':{
                'bar':10,
                'baz':'faz',
                'blah':[ 99,100 ],
                'gronk':[ 99,100 ],
            },
            'x':10,
            'y':20,
        }

        core.addJsonItem('hehe', thing)

        thing['x'] = 40
        thing['x'] = 50

        core.addJsonItem('hehe', thing)

        for iden,item in core.getJsonItems('hehe:foo:bar', valu='faz'):

            self.assertEqual( item['foo']['blah'][0], 99 )

    def test_cortex_choptag(self):

        t0 = tuple(s_cortex.choptag('foo'))
        t1 = tuple(s_cortex.choptag('foo.bar'))
        t2 = tuple(s_cortex.choptag('foo.bar.baz'))

        self.assertEqual( t0, ('foo',))
        self.assertEqual( t1, ('foo','foo.bar'))
        self.assertEqual( t2, ('foo','foo.bar','foo.bar.baz'))

    #def test_cortex_meta(self):
        #meta = s_cortex.MetaCortex()

        #dmon = s_daemon.Daemon()

        #link = dmon.listen('tcp://127.0.0.1:0/')

        #dmon.share('core0', s_cortex.openurl('ram:///') )
        #dmon.share('core1', s_cortex.openurl('ram:///') )

        #core0 = s_telepath.openurl('tcp://127.0.0.1:%d/core0' % link[1]['port'] )
        #core1 = s_telepath.openurl('tcp://127.0.0.1:%d/core1' % link[1]['port'] )

        #meta.addLocalCore('foo.bar',core0,tags=('woot.hehe',))
        #meta.addLocalCore('foo.baz',core1,tags=('woot.hoho',))

        #self.assertIsNotNone( meta.getCortex('foo.bar') )
        #self.assertIsNotNone( meta.getCortex('foo.baz') )

        #self.assertEqual( len( meta.getCortexes('woot') ), 2 )
        #self.assertEqual( len( meta.getCortexes('woot.hoho') ), 1 )
        #self.assertEqual( len( meta.getCortexes('woot.hehe') ), 1 )

        #meta.fini()

    def newp_cortex_meta_query(self):

        meta = s_cortex.MetaCortex()

        meta.addCortex('foo.bar','ram:///',tags=('woot.hehe',))
        meta.addCortex('foo.baz','ram:///',tags=('woot.hoho',))

        core0 = meta.getCortex('foo.bar')
        core1 = meta.getCortex('foo.baz')

        id0 = guid()
        id1 = guid()
        id2 = guid()
        id3 = guid()

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

        core0.addRows(rows0)
        core1.addRows(rows1)

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

    def newp_cortex_meta_query_parser(self):
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

    def newp_cortex_meta_getnames(self):
        meta = s_cortex.MetaCortex()

        meta.addCortex('foo.bar','ram:///',tags=('woot.hehe',))
        meta.addCortex('foo.baz','ram:///',tags=('woot.hoho',))

        names = meta.getCortexNames()
        names.sort()

        self.assertEqual( ('foo.bar','foo.baz'), tuple(names) )

        meta.fini()

    def newp_cortex_meta_addmeta(self):
        id1 = guid()
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

    def newp_cortex_meta_corapi(self):
        id1 = guid()
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

    def newp_cortex_meta_noname(self):
        meta = s_cortex.MetaCortex()
        self.assertRaises( s_cortex.NoSuchName, meta.addMetaRows, 'hehe', [] )
        meta.fini()

    def newp_cortex_meta_query_event(self):
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

        id1 = guid()
        id2 = guid()
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

    def newp_cortex_meta_query_perm(self):
        meta = s_cortex.MetaCortex()
        meta.addCortex('foo.bar','ram:///',tags=('woot.hehe',))
        meta.addCortex('foo.baz','ram:///',tags=('woot.hoho',))

        def newp(event):
            event[1]['allow'] = False

        meta.on('meta:query:rows',newp)
        meta.on('meta:query:join',newp)

        id1 = guid()
        id2 = guid()
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

    def newp_cortex_meta_del(self):
        meta = s_cortex.MetaCortex()
        meta.addCortex('foo.bar','ram:///',tags=('woot.hehe',))

        meta.delCortex('foo.bar')
        self.assertIsNone( meta.getCortex('foo.bar') )
        meta.fini()

    def newp_cortex_meta_notok(self):
        meta = s_cortex.MetaCortex()
        meta.addCortex('foo.bar','ram:///',tags=('woot.hehe',))
        meta.addCortex('foo.baz','ram:///',tags=('woot.hehe',))

        id1 = guid()
        meta.addMetaRows('foo.bar',(
            (id1,'foo',10,10),
            (id1,'haha',10,10),
        ))

        id2 = guid()
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

    def newp_cortex_meta_badname(self):
        meta = s_cortex.MetaCortex()
        self.assertRaises( s_cortex.InvalidParam, meta.addCortex, 30, 'ram:///' )

    def test_cortex_tufo_tag(self):
        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo','bar',baz='faz')
        core.addTufoTag(foob,'zip.zap')

        self.assertIsNotNone( foob[1].get('*|foo|zip') )
        self.assertIsNotNone( foob[1].get('*|foo|zip.zap') )

        self.assertEqual( len(core.getTufosByTag('foo','zip')), 1 )
        self.assertEqual( len(core.getTufosByTag('foo','zip.zap')), 1 )

        core.delTufoTag(foob,'zip')

        self.assertIsNone( foob[1].get('*|foo|zip') )
        self.assertIsNone( foob[1].get('*|foo|zip.zap') )

        self.assertEqual( len(core.getTufosByTag('foo','zip')), 0 )
        self.assertEqual( len(core.getTufosByTag('foo','zip.zap')), 0 )

    def test_cortex_tufo_setprops(self):
        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo','bar',baz='faz')
        self.assertEqual( foob[1].get('foo:baz'), 'faz' )
        core.setTufoProps(foob,baz='zap')
        core.setTufoProps(foob,faz='zap')

        self.assertEqual( len(core.getTufosByProp('foo:baz',valu='zap')), 1 )
        self.assertEqual( len(core.getTufosByProp('foo:faz',valu='zap')), 1 )


    def test_cortex_tufo_setprop(self):
        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo','bar',baz='faz')
        self.assertEqual( foob[1].get('foo:baz'), 'faz' )

        core.setTufoProp(foob,'baz','zap')

        self.assertEqual( len(core.getTufosByProp('foo:baz',valu='zap')), 1 )

    def test_cortex_tufo_list(self):

        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo','bar',baz='faz')

        core.addTufoList(foob,'hehe', 1, 2, 3)

        self.assertIsNotNone( foob[1].get('tufo:list:hehe') )

        vals = core.getTufoList(foob,'hehe')
        vals.sort()

        self.assertEqual( tuple(vals), (1,2,3) )

        core.delTufoListValu(foob,'hehe', 2)

        vals = core.getTufoList(foob,'hehe')
        vals.sort()

        self.assertEqual( tuple(vals), (1,3) )

        core.fini()

    def test_cortex_tufo_del(self):

        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo','bar',baz='faz')

        self.assertIsNotNone( core.getTufoByProp('foo', valu='bar') )
        self.assertIsNotNone( core.getTufoByProp('foo:baz', valu='faz') )

        core.addTufoList(foob, 'blahs', 'blah1' )
        core.addTufoList(foob, 'blahs', 'blah2' )

        blahs = core.getTufoList(foob,'blahs')

        self.assertEqual( len(blahs), 2 )

        core.delTufoByProp('foo','bar')

        self.assertIsNone( core.getTufoByProp('foo', valu='bar') )
        self.assertIsNone( core.getTufoByProp('foo:baz', valu='faz') )

        blahs = core.getTufoList(foob,'blahs')
        self.assertEqual( len(blahs), 0 )


    def test_cortex_ramhost(self):
        core0 = s_cortex.openurl('ram:///foobar')
        core1 = s_cortex.openurl('ram:///foobar')
        self.assertEqual( id(core0), id(core1) )

        core0.fini()

        core0 = s_cortex.openurl('ram:///foobar')
        core1 = s_cortex.openurl('ram:///bazfaz')

        self.assertNotEqual( id(core0), id(core1) )

        core0.fini()
        core1.fini()

        core0 = s_cortex.openurl('ram:///')
        core1 = s_cortex.openurl('ram:///')

        self.assertNotEqual( id(core0), id(core1) )

        core0.fini()
        core1.fini()

        core0 = s_cortex.openurl('ram://')
        core1 = s_cortex.openurl('ram://')

        self.assertNotEqual( id(core0), id(core1) )

        core0.fini()
        core1.fini()

    def test_cortex_keys(self):
        core = s_cortex.openurl('ram://')
        model = core.genDataModel()

        model.addTufoForm('woot')
        model.addTufoProp('woot','bar', ptype='int')
        model.addTufoProp('woot','foo', defval='foo')

        woot = core.formTufoByProp('woot','haha')

        self.assertEqual( 0, len(core.getTufosByProp('woot:bar')) )

        keyvals = ( ('bar',10), ('bar',20) )
        core.addTufoKeys(woot, keyvals)

        self.assertEqual( 1, len(core.getTufosByProp('woot:bar',10)) )
        self.assertEqual( 1, len(core.getTufosByProp('woot:bar',20)) )

        core.delTufo(woot)

        self.assertEqual( 0, len(core.getTufosByProp('woot:bar',10)) )
        self.assertEqual( 0, len(core.getTufosByProp('woot:bar',20)) )
        
        core.fini()

    def test_cortex_savefd(self):
        fd = s_compat.BytesIO()
        core0 = s_cortex.openurl('ram://', savefd=fd)

        t0 = core0.formTufoByProp('foo','one', baz='faz')
        t1 = core0.formTufoByProp('foo','two', baz='faz')

        core0.setTufoProps(t0,baz='gronk')

        core0.delTufoByProp('foo','two')
        core0.fini()

        fd.seek(0)

        core1 = s_cortex.openurl('ram://', savefd=fd)
        self.assertIsNone( core1.getTufoByProp('foo','two') )

        t0 = core1.getTufoByProp('foo','one')
        self.assertIsNotNone( t0 )

        self.assertEqual( t0[1].get('foo:baz'), 'gronk' )

    def test_cortex_stats(self):
        rows = [
            (guid(), 'foo:bar', 1, 99),
            (guid(), 'foo:bar', 2, 99),
            (guid(), 'foo:bar', 3, 99),
            (guid(), 'foo:bar', 5, 99),
            (guid(), 'foo:bar', 8, 99),
            (guid(), 'foo:bar', 13, 99),
            (guid(), 'foo:bar', 21, 99),
        ]

        core = s_cortex.openurl('ram://')
        core.addRows(rows)

        self.assertEqual( core.getStatByProp('sum','foo:bar'), 53 )
        self.assertEqual( core.getStatByProp('count','foo:bar'), 7 )

        self.assertEqual( core.getStatByProp('min','foo:bar'), 1 )
        self.assertEqual( core.getStatByProp('max','foo:bar'), 21 )

        self.assertEqual( core.getStatByProp('average','foo:bar'), 7.571428571428571 )

        self.assertEqual( core.getStatByProp('any','foo:bar'), True)
        self.assertEqual( core.getStatByProp('all','foo:bar'), True)

        histo = core.getStatByProp('histo','foo:bar')
        self.assertEqual( histo.get(13), 1 )

    def test_cortex_fire_set(self):

        core = s_cortex.openurl('ram://')

        props = {'foo:bar':'lol'}
        tufo = core.formTufoByProp('foo', 'hehe', bar='lol')

        events = ['tufo:set','tufo:props:foo','tufo:set:foo:bar']
        wait = self.getTestWait(core,len(events),*events)

        core.setTufoProps(tufo,bar='hah')

        evts = wait.wait()

        self.assertEqual( evts[0][0], 'tufo:set')
        self.assertEqual( evts[0][1]['tufo'][0], tufo[0])
        self.assertEqual( evts[0][1]['props']['foo:bar'], 'hah' )

        self.assertEqual( evts[1][0], 'tufo:props:foo')
        self.assertEqual( evts[1][1]['tufo'][0], tufo[0])
        self.assertEqual( evts[1][1]['props']['foo:bar'], 'hah' )

        self.assertEqual( evts[2][0], 'tufo:set:foo:bar')
        self.assertEqual( evts[2][1]['tufo'][0], tufo[0])
        self.assertEqual( evts[2][1]['valu'], 'hah' )

        core.fini()

    def test_cortex_tags(self):
        core = s_cortex.openurl('ram://')

        core.genDataModel().addTufoForm('foo')

        hehe = core.formTufoByProp('foo','hehe')

        core.addTufoTag(hehe,'lulz.rofl')

        lulz = core.getTufoByProp('syn:tag','lulz')

        self.assertIsNone( lulz[1].get('syn:tag:up') )
        self.assertEqual( lulz[1].get('syn:tag:doc'), '')
        self.assertEqual( lulz[1].get('syn:tag:title'), '')
        self.assertEqual( lulz[1].get('syn:tag:depth'), 0 )

        rofl = core.getTufoByProp('syn:tag','lulz.rofl')

        self.assertEqual( rofl[1].get('syn:tag:doc'), '')
        self.assertEqual( rofl[1].get('syn:tag:title'), '')
        self.assertEqual( rofl[1].get('syn:tag:up'), 'lulz' )

        self.assertEqual( rofl[1].get('syn:tag:depth'), 1 )

        core.delTufo(lulz)
        # tag and subs should be wiped

        self.assertIsNone( core.getTufoByProp('syn:tag','lulz') )
        self.assertIsNone( core.getTufoByProp('syn:tag','lulz.rofl') )

        self.assertEqual( len(core.getTufosByTag('foo','lulz')), 0 )
        self.assertEqual( len(core.getTufosByTag('foo','lulz.rofl')), 0 )

        core.fini()

    def test_cortex_sync(self):
        core0 = s_cortex.openurl('ram://')
        core1 = s_cortex.openurl('ram://')

        core0.on('core:sync', core1.sync )

        tufo0 = core0.formTufoByProp('foo','bar',baz='faz')
        tufo1 = core1.getTufoByProp('foo','bar')

        self.assertEqual( tufo1[1].get('foo'), 'bar' )
        self.assertEqual( tufo1[1].get('foo:baz'), 'faz' )

        tufo0 = core0.addTufoTag(tufo0,'hehe')
        tufo1 = core1.getTufoByProp('foo','bar')

        self.assertTrue( s_tags.tufoHasTag(tufo1,'hehe') )

        core0.delTufoTag(tufo0,'hehe')
        tufo1 = core1.getTufoByProp('foo','bar')

        self.assertFalse( s_tags.tufoHasTag(tufo1,'hehe') )

        core0.delTufo(tufo0)
        tufo1 = core1.getTufoByProp('foo','bar')

        self.assertIsNone( tufo1 )

    def test_cortex_splice(self):
        core = s_cortex.openurl('ram://')

        ####################################################################
        info = {'form':'foo','valu':'bar','props':{'baz':'faz'}}

        splice,retval = core.splice('visi','tufo:add',info, note='hehehaha')

        self.assertEqual( len(core.getTufosByProp('foo',valu='bar')), 1 )
        self.assertIsNotNone( splice[1].get('syn:splice:reqtime') )

        self.assertEqual( splice[1].get('syn:splice:user'), 'visi' )
        self.assertEqual( splice[1].get('syn:splice:note'), 'hehehaha' )
        self.assertEqual( splice[1].get('syn:splice:perm'), 'tufo:add:foo' )
        self.assertEqual( splice[1].get('syn:splice:action'), 'tufo:add' )

        self.assertEqual( splice[1].get('syn:splice:on:foo'), 'bar' )
        self.assertEqual( splice[1].get('syn:splice:act:form'), 'foo' )
        self.assertEqual( splice[1].get('syn:splice:act:valu'), 'bar' )

        self.assertEqual( retval[1].get('foo'), 'bar' )
        self.assertEqual( retval[1].get('foo:baz'), 'faz' )

        ####################################################################
        info = {'form':'foo','valu':'bar','prop':'baz','pval':'gronk'}
        splice,retval = core.splice('visi','tufo:set',info)

        self.assertEqual( retval[1].get('foo:baz'), 'gronk')
        self.assertEqual( len(core.getTufosByProp('foo:baz',valu='gronk')), 1 )

        self.assertEqual( splice[1].get('syn:splice:on:foo'), 'bar' )
        self.assertEqual( splice[1].get('syn:splice:act:form'), 'foo' )
        self.assertEqual( splice[1].get('syn:splice:act:valu'), 'bar' )
        self.assertEqual( splice[1].get('syn:splice:act:prop'), 'baz' )
        self.assertEqual( splice[1].get('syn:splice:act:pval'), 'gronk' )

        ####################################################################
        info = {'form':'foo','valu':'bar','tag':'lol'}
        splice,retval = core.splice('visi','tufo:tag:add',info)

        self.assertTrue( s_tags.tufoHasTag(retval,'lol') )
        self.assertEqual( len(core.getTufosByTag('foo','lol')), 1 )

        self.assertEqual( splice[1].get('syn:splice:on:foo'), 'bar' )
        self.assertEqual( splice[1].get('syn:splice:act:tag'), 'lol' )
        self.assertEqual( splice[1].get('syn:splice:act:form'), 'foo' )
        self.assertEqual( splice[1].get('syn:splice:act:valu'), 'bar' )

        ####################################################################
        info = {'form':'foo','valu':'bar','tag':'lol'}
        splice,retval = core.splice('visi','tufo:tag:del',info)

        self.assertFalse( s_tags.tufoHasTag(retval,'lol') )
        self.assertEqual( len(core.getTufosByTag('foo','lol')), 0 )

        self.assertEqual( splice[1].get('syn:splice:on:foo'), 'bar' )
        self.assertEqual( splice[1].get('syn:splice:act:tag'), 'lol' )
        self.assertEqual( splice[1].get('syn:splice:act:form'), 'foo' )
        self.assertEqual( splice[1].get('syn:splice:act:valu'), 'bar' )

        ####################################################################
        info = {'form':'foo','valu':'bar'}
        splice,retval = core.splice('visi','tufo:del',info)

        self.assertEqual( len(core.getTufosByProp('foo',valu='bar')), 0 )

        self.assertEqual( splice[1].get('syn:splice:on:foo'), 'bar' )
        self.assertEqual( splice[1].get('syn:splice:act:form'), 'foo' )
        self.assertEqual( splice[1].get('syn:splice:act:valu'), 'bar' )

        core.fini()

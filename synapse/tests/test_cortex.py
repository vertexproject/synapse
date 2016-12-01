import os
import unittest

import synapse.compat as s_compat
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.exc as s_exc
import synapse.lib.userauth as s_userauth
import synapse.lib.tags as s_tags
import synapse.lib.types as s_types

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
        table = 'syn_test_%s' % guid()
        core = self.open_cortex_postgres(table)
        try:
            self.runcore( core )
            self.runjson( core )
            self.runrange( core )
        finally:
            with core.cursor() as c:
                c.execute('DROP TABLE %s' % (table,))

    def open_cortex_postgres(self, table=None, pool=None):
        db = os.getenv('SYN_COR_PG_DB')
        if db == None:
            raise unittest.SkipTest('no SYN_COR_PG_DB')
        if not db.startswith('postgres://'):
            db = 'postgres:///%s' % (db)
        fini = None
        if not table:
            table = 'syn_test_%s' % guid()

            def fini():
                with core.cursor() as c:
                    c.connection.rollback()
                    c.execute('DROP TABLE %s' % (table,))
        url = db + '/' + table
        if pool:
            url += '?pool=' + str(pool)
        core = s_cortex.openurl(url)
        if fini:
            core.onfini(fini)
        return core

    def runcore(self, core):

        id1 = guid()
        id2 = guid()
        id3 = guid()
        id4 = guid()
        id5 = guid()
        id6 = guid()
        id7 = guid()

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

            (id5, 'longstr','abcdefghijklmnopqrstuvwxyz0123456789',50),
            (id5, 'foop','bar',50),
            (id6, 'longstr','abcdefghijklmnopqrstuvwxyz0123459999',50),
            (id6, 'foop','bar',50),
            (id7, 'longstr','abcdefghijklmnopqrstuvwxyz012345',50),
            (id7, 'foop','bar',50),

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

        self.assertEqual( len(core.getRowsByProp('longstr',valu='abcdefghijklmnopqrstuvwxyz012345')), 1 )
        self.assertEqual( len(core.getRowsByProp('longstr',valu='abcdefghijklmnopqrstuvwxyz0123456789')), 1 )

        self.assertEqual( len(core.getJoinByProp('longstr',valu='abcdefghijklmnopqrstuvwxyz012345')), 2 )
        self.assertEqual( len(core.getJoinByProp('longstr',valu='abcdefghijklmnopqrstuvwxyz0123456789')), 2 )

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

        # Test incTufoProp
        self.assertEqual( tufo[1].get('fqdn:inctest'), None )

        tufo = core.incTufoProp(tufo, 'inctest')
        self.assertEqual( tufo[1].get('fqdn:inctest'), 1 )

        tufo = core.incTufoProp(tufo, 'inctest', incval=-1)
        self.assertEqual( tufo[1].get('fqdn:inctest'), 0 )

        # Test maxTufoProp
        self.assertEqual(tufo[1].get('fqdn:maxtest'), None)

        tufo = core.maxTufoProp(tufo, 'maxtest', 0)
        self.assertEqual(tufo[1].get('fqdn:maxtest'), 0)

        tufo = core.maxTufoProp(tufo, 'maxtest', 20)
        self.assertEqual(tufo[1].get('fqdn:maxtest'), 20)

        tufo = core.maxTufoProp(tufo, 'maxtest', 10)
        self.assertEqual(tufo[1].get('fqdn:maxtest'), 20)

        # Test minTufoProp
        self.assertEqual(tufo[1].get('fqdn:mintest'), None)

        tufo = core.minTufoProp(tufo, 'mintest', 0)
        self.assertEqual(tufo[1].get('fqdn:mintest'), 0)

        tufo = core.minTufoProp(tufo, 'mintest', -20)
        self.assertEqual(tufo[1].get('fqdn:mintest'), -20)

        tufo = core.minTufoProp(tufo, 'mintest', -10)
        self.assertEqual(tufo[1].get('fqdn:mintest'), -20)

        core.fini()

    def runrange(self, core):

        rows = [
            (guid(),'rg',10,99),
            (guid(),'rg',30,99),
    ]

        core.addRows( rows )

        self.assertEqual( core.getSizeBy('range','rg',(0,20)), 1 )
        self.assertEqual( core.getRowsBy('range','rg',(0,20))[0][2], 10 )

        self.assertEqual( core.getSizeBy('ge','rg',20), 1 )
        self.assertEqual( core.getRowsBy('ge','rg',20)[0][2], 30)

        self.assertEqual( core.getSizeBy('le','rg',20), 1 )
        self.assertEqual( core.getRowsBy('le','rg',20)[0][2], 10 )

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

    def test_cortex_tufo_chop_subprops(self):
        core = s_cortex.openurl('ram://')

        class PairType(s_types.DataType):
            '''
            silly type for representing a pair like "a!b".
            it has subprops 'first' and 'second'.
            '''
            subprops = (
                s_common.tufo('first', ptype='str'),
                s_common.tufo('second', ptype='str'),
            )

            def norm(self, valu):
                return self.chop(valu)[0]

            def chop(self, valu):
                if self.info.get('lower'):
                    valu = valu.lower()

                first, _, second = valu.partition('!')
                return valu, {
                    'first': first,
                    'second': second,
                }

            def parse(self, text):
                return self.norm(text)

            def repr(self, valu):
                return valu

        core.addType(PairType(core, 'pair'))

        core.addTufoForm('foo')
        core.addTufoProp('foo', 'bar', ptype='pair')
        core.addTufoProp('foo', 'bar:first')
        core.addTufoProp('foo', 'bar:second')

        t0 = core.formTufoByProp('foo', 'blah', bar='A!B')
        self.assertEqual(t0[1].get('foo:bar'), 'A!B')
        self.assertEqual(t0[1].get('foo:bar:first'), 'A')
        self.assertEqual(t0[1].get('foo:bar:second'), 'B')

    def test_cortex_choptag(self):
        t0 = tuple(s_cortex.choptag('foo'))
        t1 = tuple(s_cortex.choptag('foo.bar'))
        t2 = tuple(s_cortex.choptag('foo.bar.baz'))

        self.assertEqual( t0, ('foo',))
        self.assertEqual( t1, ('foo','foo.bar'))
        self.assertEqual( t2, ('foo','foo.bar','foo.bar.baz'))

    def test_cortex_timeout_postgres(self):
        with self.open_cortex_postgres() as core:
            core.select('select pg_sleep(%s)', [0.001], timeout=0.100)
            self.assertRaises(s_exc.HitMaxTime, core.select, 'select pg_sleep(%s)', [0.100], timeout=0.001)

        with self.open_cortex_postgres(pool=10) as core:
            for i in range(10):
                core.select('select pg_sleep(%s)', [0.002], timeout=0.200)
                self.assertRaises(s_exc.HitMaxTime, core.select, 'select pg_sleep(%s)', [0.200], timeout=0.002)

    def test_cortex_tufo_by_default(self):
        core = s_cortex.openurl('sqlite:///:memory:')

        fooa = core.formTufoByProp('foo','bar',p0=4)
        foob = core.formTufoByProp('foo','baz',p0=5)

        self.assertEqual( len(core.getTufosBy('in', 'foo:p0', [4])), 1)

        fooc = core.formTufoByProp('foo','faz',p0=5)
        food = core.formTufoByProp('foo','haz',p0=6)
        fooe = core.formTufoByProp('foo','gaz',p0=7)
        self.assertEqual( len(core.getTufosBy('in', 'foo:p0', [5])), 2)
        self.assertEqual( len(core.getTufosBy('in', 'foo:p0', [4,5])), 3)
        self.assertEqual( len(core.getTufosBy('in', 'foo:p0', [4,5,6,7], limit=4)), 4)
        self.assertEqual( len(core.getTufosBy('in', 'foo:p0', [5], limit=1)), 1)
        self.assertEqual( len(core.getTufosBy('in', 'foo:p0', [], limit=1)), 0)

    def test_cortex_tufo_by_postgres(self):
        table = 'syn_test_%s' % guid()
        core = self.open_cortex_postgres(table)
        try:
            fooa = core.formTufoByProp('foo','bar',p0=4)
            foob = core.formTufoByProp('foo','baz',p0=5)

            self.assertEqual( len(core.getTufosBy('in', 'foo:p0', [4])), 1)

            fooc = core.formTufoByProp('foo','faz',p0=5)
            self.assertEqual( len(core.getTufosBy('in', 'foo:p0', [5])), 2)
            self.assertEqual( len(core.getTufosBy('in', 'foo:p0', [4,5])), 3)
            self.assertEqual( len(core.getTufosBy('in', 'foo:p0', [5], limit=1)), 1)

            bara = core.formTufoByProp('bar', 'longstra',p0='abcdefghijklmnopqrstuvwxyz0123456789'),
            barb = core.formTufoByProp('bar', 'longstrb',p0='abcdefghijklmnopqrstuvwxyz0123459999'),
            barc = core.formTufoByProp('bar', 'longstrc',p0='abcdefghijklmnopqrstuvwxyz012345'),

            self.assertEqual( len(core.getTufosBy('range', 'bar:p0', ('abcdefghijklmnopqrstuvwxyz0123450','abcdefghijklmnopqrstuvwxyz0123458'))),  1)
            self.assertEqual( len(core.getTufosBy('in', 'bar:p0', ['abcdefghijklmnopqrstuvwxyz0123456789'])),  1)
        finally:
            with core.cursor() as c:
                c.execute('DROP TABLE %s' % (table,))


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

    def test_cortex_tufo_pop(self):
        with s_cortex.openurl('ram://') as core:
            foo0 = core.formTufoByProp('foo','bar',woot='faz')
            foo1 = core.formTufoByProp('foo','baz',woot='faz')

            self.assertEqual( 2, len(core.popTufosByProp('foo:woot', valu='faz')))
            self.assertEqual( 0, len(core.getTufosByProp('foo')))

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


    def test_cortex_tufo_frob(self):
        with s_cortex.openurl('ram://') as core:
            core.addTufoForm('inet:ipv4', ptype='inet:ipv4')
            core.addTufoProp('inet:ipv4', 'five', ptype='inet:ipv4')

            iden, props = core.formTufoByFrob('inet:ipv4', 0x01020304, five='5.5.5.5')
            self.assertEqual(props['inet:ipv4'], 16909060)
            self.assertEqual(props['inet:ipv4:five'], 84215045)

            tufo = core.formTufoByFrob('inet:ipv4', '1.2.3.4')
            self.assertEqual(tufo[0], iden)

            tufo = core.getTufoByFrob('inet:ipv4:five', 0x05050505)
            self.assertEqual(tufo[0], iden)

            tufo = core.getTufoByFrob('inet:ipv4', '1.2.3.4')
            self.assertEqual(tufo[0], iden)

            core.setTufoFrob(tufo, 'is_true', True)
            self.assertIs(tufo[1]['inet:ipv4:is_true'], 1)


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

        core.addTufoForm('woot')
        core.addTufoProp('woot','bar', ptype='int')
        core.addTufoProp('woot','foo', defval='foo')

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

        core.addTufoForm('foo')

        hehe = core.formTufoByProp('foo','hehe')

        wait = TestWaiter(core, 2, 'tufo:tag:add')
        core.addTufoTag(hehe,'lulz.rofl')
        wait.wait()

        wait = TestWaiter(core, 1, 'tufo:tag:add')
        core.addTufoTag(hehe,'lulz.rofl.zebr')
        wait.wait()

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

        wait = TestWaiter(core, 2, 'tufo:tag:del')
        core.delTufoTag(hehe,'lulz.rofl')
        wait.wait()

        wait = TestWaiter(core, 1, 'tufo:tag:del')
        core.delTufo(lulz)
        wait.wait()
        # tag and subs should be wiped

        self.assertIsNone( core.getTufoByProp('syn:tag','lulz') )
        self.assertIsNone( core.getTufoByProp('syn:tag','lulz.rofl') )
        self.assertIsNone( core.getTufoByProp('syn:tag','lulz.rofl.zebr') )

        self.assertEqual( len(core.getTufosByTag('foo','lulz')), 0 )
        self.assertEqual( len(core.getTufosByTag('foo','lulz.rofl')), 0 )
        self.assertEqual( len(core.getTufosByTag('foo','lulz.rofl.zebr')), 0 )

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

        core0.setTufoProp(tufo0,'baz','lol')
        tufo1 = core1.getTufoByProp('foo','bar')

        self.assertEqual( tufo1[1].get('foo:baz'), 'lol' )

        core0.delTufo(tufo0)
        tufo1 = core1.getTufoByProp('foo','bar')

        self.assertIsNone( tufo1 )

    def test_cortex_splice(self):
        core = s_cortex.openurl('ram://')
        core.addTufoForm('foo', ptype='int')
        core.addTufoProp('foo', 'baz', ptype='int')

        ####################################################################
        info = {'form':'foo','valu':'123','props':{'baz':'456'}}

        splice,retval = core.splice('visi','tufo:add',info, note='hehehaha')

        self.assertEqual( len(core.getTufosByProp('foo',valu=123)), 1 )
        self.assertIsNotNone( splice[1].get('syn:splice:reqtime') )

        self.assertEqual( splice[1].get('syn:splice:user'), 'visi' )
        self.assertEqual( splice[1].get('syn:splice:note'), 'hehehaha' )
        self.assertEqual( splice[1].get('syn:splice:perm'), 'tufo:add:foo' )
        self.assertEqual( splice[1].get('syn:splice:action'), 'tufo:add' )

        self.assertEqual( splice[1].get('syn:splice:on:foo'), 123 )
        self.assertEqual( splice[1].get('syn:splice:act:form'), 'foo' )
        self.assertEqual( splice[1].get('syn:splice:act:valu'), 123 )

        self.assertEqual( retval[1].get('foo'), 123 )
        self.assertEqual( retval[1].get('foo:baz'), 456 )

        ####################################################################
        info = {'form':'foo','valu':'123','prop':'baz','pval':'789'}
        splice,retval = core.splice('visi','tufo:set',info)

        self.assertEqual( retval[1].get('foo:baz'), 789)
        self.assertEqual( len(core.getTufosByProp('foo:baz',valu=789)), 1 )

        self.assertEqual( splice[1].get('syn:splice:on:foo'), 123 )
        self.assertEqual( splice[1].get('syn:splice:act:form'), 'foo' )
        self.assertEqual( splice[1].get('syn:splice:act:valu'), 123 )
        self.assertEqual( splice[1].get('syn:splice:act:prop'), 'baz' )
        self.assertEqual( splice[1].get('syn:splice:act:pval'), 789 )

        ####################################################################
        info = {'form':'foo','valu':'123','tag':'lol'}
        splice,retval = core.splice('visi','tufo:tag:add',info)

        self.assertTrue( s_tags.tufoHasTag(retval,'lol') )
        self.assertEqual( len(core.getTufosByTag('foo','lol')), 1 )

        self.assertEqual( splice[1].get('syn:splice:on:foo'), 123 )
        self.assertEqual( splice[1].get('syn:splice:act:tag'), 'lol' )
        self.assertEqual( splice[1].get('syn:splice:act:form'), 'foo' )
        self.assertEqual( splice[1].get('syn:splice:act:valu'), 123 )

        ####################################################################
        info = {'form':'foo','valu':'123','tag':'lol'}
        splice,retval = core.splice('visi','tufo:tag:del',info)

        self.assertFalse( s_tags.tufoHasTag(retval,'lol') )
        self.assertEqual( len(core.getTufosByTag('foo','lol')), 0 )

        self.assertEqual( splice[1].get('syn:splice:on:foo'), 123 )
        self.assertEqual( splice[1].get('syn:splice:act:tag'), 'lol' )
        self.assertEqual( splice[1].get('syn:splice:act:form'), 'foo' )
        self.assertEqual( splice[1].get('syn:splice:act:valu'), 123 )

        ####################################################################
        info = {'form':'foo','valu':'123'}
        splice,retval = core.splice('visi','tufo:del',info)

        self.assertEqual( len(core.getTufosByProp('foo',valu=123)), 0 )

        self.assertEqual( splice[1].get('syn:splice:on:foo'), 123 )
        self.assertEqual( splice[1].get('syn:splice:act:form'), 'foo' )
        self.assertEqual( splice[1].get('syn:splice:act:valu'), 123 )

        core.fini()

    def test_cortex_splice_userauth(self):
        with s_cortex.openurl('ram:///') as auth_core:
            with s_userauth.UserAuth(auth_core) as auth:
                with s_cortex.openurl('ram:///', userauth=auth) as core:
                    info1 = {'form': 'foo', 'valu': 'bar'}
                    self.assertRaises(s_exc.NoSuchUser, core.splice, 'bobo', 'tufo:add', info1)

                    auth.addUser('bobo')
                    splice, retval = core.splice('bobo', 'tufo:add', info1)
                    self.assertEqual(splice[1]['syn:splice:action'], 'tufo:add')
                    self.assertEqual(splice[1]['syn:splice:status'], 'pend')
                    self.assertFalse(retval)

                    auth.addUserRule('bobo', 'tufo:add:foo')
                    splice, retval = core.splice('bobo', 'tufo:add', info1)
                    self.assertEqual(splice[1]['syn:splice:action'], 'tufo:add')
                    self.assertEqual(splice[1]['syn:splice:status'], 'done')
                    self.assertEqual(retval[1]['tufo:form'], 'foo')
                    self.assertEqual(retval[1]['foo'], 'bar')

                    info2 = {'form': 'foo', 'valu': 'bar', 'prop': 'baz', 'pval': 'qux'}
                    splice, retval = core.splice('bobo', 'tufo:set', info2)
                    self.assertEqual(splice[1]['syn:splice:action'], 'tufo:set')
                    self.assertEqual(splice[1]['syn:splice:status'], 'pend')
                    self.assertFalse(retval)

                    auth.addUserRule('bobo', 'tufo:set:foo:baz')
                    splice, retval = core.splice('bobo', 'tufo:set', info2)
                    self.assertEqual(splice[1]['syn:splice:action'], 'tufo:set')
                    self.assertEqual(splice[1]['syn:splice:status'], 'done')
                    self.assertEqual(retval[1]['foo:baz'], 'qux')

                    info3 = {'form': 'foo', 'valu': 'bar', 'tag': 'test'}
                    splice, retval = core.splice('bobo', 'tufo:tag:add', info3)
                    self.assertEqual(splice[1]['syn:splice:action'], 'tufo:tag:add')
                    self.assertEqual(splice[1]['syn:splice:status'], 'pend')
                    self.assertFalse(retval)

                    auth.addUserRule('bobo', 'tufo:tag:add:foo|*')
                    splice, retval = core.splice('bobo', 'tufo:tag:add', info3)
                    self.assertEqual(splice[1]['syn:splice:action'], 'tufo:tag:add')
                    self.assertEqual(splice[1]['syn:splice:status'], 'done')
                    self.assertTrue('*|foo|test' in retval[1])

                    splice, retval = core.splice('bobo', 'tufo:tag:del', info3)
                    self.assertEqual(splice[1]['syn:splice:action'], 'tufo:tag:del')
                    self.assertEqual(splice[1]['syn:splice:status'], 'pend')
                    self.assertFalse(retval)

                    auth.addUserRule('bobo', 'tufo:tag:del:foo|*')
                    splice, retval = core.splice('bobo', 'tufo:tag:del', info3)
                    self.assertEqual(splice[1]['syn:splice:action'], 'tufo:tag:del')
                    self.assertEqual(splice[1]['syn:splice:status'], 'done')
                    self.assertFalse('*|foo|test' in retval[1])

                    splice, retval = core.splice('bobo', 'tufo:del', info1)
                    self.assertEqual(splice[1]['syn:splice:action'], 'tufo:del')
                    self.assertEqual(splice[1]['syn:splice:status'], 'pend')
                    self.assertFalse(retval)

                    auth.addUserRule('bobo', 'tufo:del:foo')
                    splice, retval = core.splice('bobo', 'tufo:del', info1)
                    self.assertEqual(splice[1]['syn:splice:action'], 'tufo:del')
                    self.assertEqual(splice[1]['syn:splice:status'], 'done')
                    self.assertEqual(retval[1]['foo'], 'bar')


    def test_cortex_dict(self):
        core = s_cortex.openurl('ram://')
        core.addTufoForm('foo:bar', ptype='int')
        core.addTufoForm('baz:faz', ptype='int', defval=22)

        modl = core.getModelDict()
        self.assertEqual( modl['forms'][-2:], ['foo:bar','baz:faz'] )
        self.assertEqual( modl['props']['foo:bar'][1]['ptype'], 'int')
        self.assertEqual( modl['props']['baz:faz'][1]['defval'], 22)

        core.fini()

    def test_cortex_comp(self):
        core = s_cortex.openurl('ram://')

        fields = (('fqdn','inet:fqdn'),('ipv4','inet:ipv4'),('time','time:epoch'))
        core.addSubType('dns:a','comp',fields=fields)

        core.addTufoForm('dns:a',ptype='dns:a')
        core.addTufoProp('dns:a','fqdn',ptype='inet:fqdn')
        core.addTufoProp('dns:a','ipv4',ptype='inet:ipv4')
        core.addTufoProp('dns:a','time',ptype='time:epoch')

        arec = ('wOOt.com',0x01020304,0x00404040)

        dnsa = core.formTufoByProp('dns:a', arec)

        fval = s_types.enMsgB64( ('woot.com',0x01020304,0x00404040) )

        self.assertEqual( dnsa[1].get('dns:a'), fval)
        self.assertEqual( dnsa[1].get('dns:a:fqdn'), 'woot.com')
        self.assertEqual( dnsa[1].get('dns:a:ipv4'), 0x01020304)
        self.assertEqual( dnsa[1].get('dns:a:time'), 0x00404040)

        core.fini()

    def test_cortex_enforce(self):

        with s_cortex.openurl('ram://') as core:

            core.addTufoForm('foo:bar', ptype='inet:email')

            core.addTufoForm('foo:baz', ptype='inet:email')
            core.addTufoProp('foo:baz', 'fqdn', ptype='inet:fqdn')
            core.addTufoProp('foo:baz', 'haha', ptype='int')

            cofo = core.getTufoByProp('syn:core','self')
            self.assertIsNotNone( cofo )
            self.assertFalse( core.enforce )

            core.setConfOpt('enforce',True)

            self.assertTrue( core.enforce )

            tufo0 = core.formTufoByProp('foo:bar','foo@bar.com', hehe=10, haha=20)
            tufo1 = core.formTufoByProp('foo:baz','foo@bar.com', hehe=10, haha=20)

            # did it remove the non-declared props and subprops?
            self.assertIsNone( tufo0[1].get('foo:bar:fqdn') )
            self.assertIsNone( tufo0[1].get('foo:bar:hehe') )
            self.assertIsNone( tufo0[1].get('foo:bar:haha') )

            # did it selectivly keep the declared props and subprops
            self.assertEqual( tufo1[1].get('foo:baz:haha'), 20 )
            self.assertEqual( tufo1[1].get('foo:baz:fqdn'), 'bar.com' )

            self.assertIsNone( tufo1[1].get('foo:baz:hehe') )
            self.assertIsNone( tufo1[1].get('foo:baz:user') )

            tufo0 = core.setTufoProps(tufo0, fqdn='visi.com', hehe=11 )
            tufo1 = core.setTufoProps(tufo1, fqdn='visi.com', hehe=11, haha=21 )

            self.assertIsNone( tufo0[1].get('foo:bar:fqdn') )
            self.assertIsNone( tufo0[1].get('foo:bar:hehe') )

            self.assertIsNone( tufo1[1].get('foo:baz:hehe') )

            self.assertEqual( tufo1[1].get('foo:baz:haha'), 21 )
            self.assertEqual( tufo1[1].get('foo:baz:fqdn'), 'visi.com' )


    def test_cortex_ramtyperange(self):
        with s_cortex.openurl('ram://') as core:

            core.formTufoByProp('foo:bar',10)
            core.formTufoByProp('foo:bar','baz')

            tufs = core.getTufosBy('range','foo:bar', (5,15))

            self.eq( len(tufs), 1 )

    def test_cortex_minmax(self):

        with s_cortex.openurl('ram://') as core:

            core.addTufoForm('foo')
            core.addTufoProp('foo','min', ptype='int:min')
            core.addTufoProp('foo','max', ptype='int:max')

            props = {'min':20,'max':20}
            tufo0 = core.formTufoByProp('foo', 'derp', **props)

            tufo0 = core.setTufoProp(tufo0,'min', 30)
            self.eq( tufo0[1].get('foo:min'), 20 )

            tufo0 = core.setTufoProp(tufo0,'min', 10)
            self.eq( tufo0[1].get('foo:min'), 10 )

            tufo0 = core.setTufoProp(tufo0,'max', 10)
            self.eq( tufo0[1].get('foo:max'), 20 )

            tufo0 = core.setTufoProp(tufo0,'max', 30)
            self.eq( tufo0[1].get('foo:max'), 30 )

    def test_cortex_minmax_epoch(self):

        with s_cortex.openurl('ram://') as core:

            core.addTufoForm('foo')
            core.addTufoProp('foo','min', ptype='time:epoch:min')
            core.addTufoProp('foo','max', ptype='time:epoch:max')

            props = {'min':20,'max':20}
            tufo0 = core.formTufoByProp('foo', 'derp', **props)

            tufo0 = core.setTufoProp(tufo0,'min', 30)
            self.eq( tufo0[1].get('foo:min'), 20 )

            tufo0 = core.setTufoProp(tufo0,'min', 10)
            self.eq( tufo0[1].get('foo:min'), 10 )

            tufo0 = core.setTufoProp(tufo0,'max', 10)
            self.eq( tufo0[1].get('foo:max'), 20 )

            tufo0 = core.setTufoProp(tufo0,'max', 30)
            self.eq( tufo0[1].get('foo:max'), 30 )

    def test_cortex_by_type(self):

        with s_cortex.openurl('ram://') as core:

            core.addTufoForm('foo')
            core.addTufoProp('foo','min', ptype='time:epoch:min')
            core.addTufoProp('foo','max', ptype='time:epoch:max')

            core.addTufoForm('bar')
            core.addTufoProp('bar','min', ptype='time:epoch:min')
            core.addTufoProp('bar','max', ptype='time:epoch:max')

            core.addTufoForm('baz')
            core.addTufoProp('baz','min', ptype='time:epoch')
            core.addTufoProp('baz','max', ptype='time:epoch')

            props = {'min':20,'max':20}

            tufo0 = core.formTufoByProp('foo', 'hurr', **props)
            tufo1 = core.formTufoByProp('bar', 'durr', **props)
            tufo2 = core.formTufoByProp('baz', 'durr', **props)

            want = tuple(sorted([tufo0[0],tufo1[0]]))

            res0 = core.getTufosByPropType('time:epoch:min', valu=20)
            self.eq( tuple(sorted([r[0] for r in res0])), want )

    def test_cortex_caching(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar', asdf=2)
            tufo1 = core.formTufoByProp('foo','baz', asdf=2)

            answ0 = core.getTufosByProp('foo')
            answ1 = core.getTufosByProp('foo', valu='bar')

            self.eq( len(answ0), 2 )
            self.eq( len(answ1), 1 )

            self.eq( len(core.cache_fifo), 0 )
            self.eq( len(core.cache_bykey), 0 )
            self.eq( len(core.cache_byiden), 0 )
            self.eq( len(core.cache_byprop), 0 )

            core.setConfOpt('caching',1)

            self.eq( core.caching, 1 )

            answ0 = core.getTufosByProp('foo')

            self.eq( len(answ0), 2 )
            self.eq( len(core.cache_fifo), 1 )
            self.eq( len(core.cache_bykey), 1 )
            self.eq( len(core.cache_byiden), 2 )
            self.eq( len(core.cache_byprop), 1 )

            #self.eq( len(answ1), 1 )
            #answ1 = core.getTufosByProp('foo', valu='bar')

    def test_cortex_caching_set(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar', qwer=10)
            tufo1 = core.formTufoByProp('foo','baz', qwer=10)

            core.setConfOpt('caching',1)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)
            tufs3 = core.getTufosByProp('foo:qwer', valu=10, limit=2)

            self.assertEqual( len(tufs0), 2 )
            self.assertEqual( len(tufs1), 2 )
            self.assertEqual( len(tufs2), 0 )
            self.assertEqual( len(tufs3), 2 )

            # inspect the details of the cache data structures when setTufoProps
            # causes an addition or removal...
            self.assertIsNotNone( core.cache_bykey.get( ('foo:qwer',10,None) ) )
            self.assertIsNotNone( core.cache_bykey.get( ('foo:qwer',None,None) ) )

            # we should have hit the unlimited query and not created a new cache hit...
            self.assertIsNone( core.cache_bykey.get( ('foo:qwer',10,2) ) )

            self.assertIsNotNone( core.cache_byiden.get( tufo0[0] ) )
            self.assertIsNotNone( core.cache_byiden.get( tufo1[0] ) )

            self.assertIsNotNone( core.cache_byprop.get( ('foo:qwer',10) ) )
            self.assertIsNotNone( core.cache_byprop.get( ('foo:qwer',None) ) )

            core.setTufoProp(tufo0,'qwer',11)

            # the cached results should be updated
            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            self.assertEqual( len(tufs0), 2 )
            self.assertEqual( len(tufs1), 1 )
            self.assertEqual( len(tufs2), 1 )

            self.assertEqual( tufs1[0][0], tufo1[0] )
            self.assertEqual( tufs2[0][0], tufo0[0] )

    def test_cortex_caching_add_tufo(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar', qwer=10)
            tufo1 = core.formTufoByProp('foo','baz', qwer=10)

            core.setConfOpt('caching',1)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            self.assertEqual( len(tufs0), 2 )
            self.assertEqual( len(tufs1), 2 )
            self.assertEqual( len(tufs2), 0 )

            tufo2 = core.formTufoByProp('foo','lol', qwer=10)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            self.assertEqual( len(tufs0), 3 )
            self.assertEqual( len(tufs1), 3 )
            self.assertEqual( len(tufs2), 0 )

    def test_cortex_caching_del_tufo(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar', qwer=10)
            tufo1 = core.formTufoByProp('foo','baz', qwer=10)

            core.setConfOpt('caching',1)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            self.assertEqual( len(tufs0), 2 )
            self.assertEqual( len(tufs1), 2 )
            self.assertEqual( len(tufs2), 0 )

            core.delTufo( tufo0 )
            #tufo2 = core.formTufoByProp('foo','lol', qwer=10)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            self.assertEqual( len(tufs0), 1 )
            self.assertEqual( len(tufs1), 1 )
            self.assertEqual( len(tufs2), 0 )

    def test_cortex_caching_atlimit(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar', qwer=10)
            tufo1 = core.formTufoByProp('foo','baz', qwer=10)

            core.setConfOpt('caching',1)

            tufs0 = core.getTufosByProp('foo:qwer', limit=2)
            tufs1 = core.getTufosByProp('foo:qwer', valu=10, limit=2)

            self.assertEqual( len(tufs0), 2 )
            self.assertEqual( len(tufs1), 2 )

            # when an entry is deleted from a cache result that was at it's limit
            # it should be fully invalidated

            core.delTufo(tufo0)

            self.assertIsNone( core.cache_bykey.get( ('foo:qwer',None,2) ) )
            self.assertIsNone( core.cache_bykey.get( ('foo:qwer',10,2) ) )

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar', qwer=10)
            tufo1 = core.formTufoByProp('foo','baz', qwer=10)

            core.setConfOpt('caching',1)

            tufs0 = core.getTufosByProp('foo:qwer', limit=2)
            tufs1 = core.getTufosByProp('foo:qwer', valu=10, limit=2)

            self.assertEqual( len(tufs0), 2 )
            self.assertEqual( len(tufs1), 2 )

            tufo2 = core.formTufoByProp('foo','baz', qwer=10)

            # when an entry is added from a cache result that was at it's limit
            # it should *not* be invalidated

            self.assertIsNotNone( core.cache_bykey.get( ('foo:qwer',None,2) ) )
            self.assertIsNotNone( core.cache_bykey.get( ('foo:qwer',10,2) ) )

    def test_cortex_caching_under_limit(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar', qwer=10)
            tufo1 = core.formTufoByProp('foo','baz', qwer=10)

            core.setConfOpt('caching',1)

            tufs0 = core.getTufosByProp('foo:qwer', limit=9)
            tufs1 = core.getTufosByProp('foo:qwer', valu=10, limit=9)

            self.assertEqual( len(tufs0), 2 )
            self.assertEqual( len(tufs1), 2 )

            # when an entry is deleted from a cache result that was under it's limit
            # it should be removed but *not* invalidated

            core.delTufo(tufo0)

            self.assertIsNotNone( core.cache_bykey.get( ('foo:qwer',None,9) ) )
            self.assertIsNotNone( core.cache_bykey.get( ('foo:qwer',10,9) ) )

            tufs0 = core.getTufosByProp('foo:qwer', limit=9)
            tufs1 = core.getTufosByProp('foo:qwer', valu=10, limit=9)

            self.assertEqual( len(tufs0), 1 )
            self.assertEqual( len(tufs1), 1 )


    def test_cortex_caching_oneref(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar')

            core.setConfOpt('caching',1)

            ref0 = core.getTufosByProp('foo',valu='bar')[0]
            ref1 = core.getTufosByProp('foo',valu='bar')[0]

            self.eq( id(ref0), id(ref1) )

    def test_cortex_caching_tags(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar')
            tufo1 = core.formTufoByProp('foo','baz')

            core.addTufoTag(tufo0,'hehe')

            core.setConfOpt('caching',1)

            tufs0 = core.getTufosByTag('foo','hehe')

            core.addTufoTag(tufo1,'hehe')

            tufs1 = core.getTufosByTag('foo','hehe')
            self.eq( len(tufs1), 2 )

            core.delTufoTag(tufo0,'hehe')

            tufs2 = core.getTufosByTag('foo','hehe')
            self.eq( len(tufs2), 1 )

    def test_cortex_caching_new(self):

        with s_cortex.openurl('ram://') as core:

            core.setConfOpt('caching',1)

            tufo0 = core.formTufoByProp('foo','bar')
            tufo1 = core.formTufoByProp('foo','bar')

            self.assertTrue(tufo0[1].get('.new'))
            self.assertFalse(tufo1[1].get('.new'))

    def test_savecore(self):
        with s_cortex.openurl('ram://') as savecore:
            def savefilter(evtfo):
                return not any(prop == 'prop' and valu == 'bogus' for iden, prop, valu, when in evtfo[1]['rows'])

            # test save
            with s_cortex.openurl('ram://', savecore=savecore, savefilter=savefilter) as core:
                wait = TestWaiter(savecore.loadbus, 1, 'core:save:add:rows')
                core.formTufoByProp('prop', 'valu')
                core.formTufoByProp('prop', 'bogus')
                wait.wait()
                save = savecore.getTufoByProp('prop', valu='valu')
                self.assertEqual(save[1]['tufo:form'], 'prop')
                self.assertEqual(save[1]['prop'], 'valu')
                self.assertIsNone(savecore.getTufoByProp('prop', valu='bogus'))

            # test load
            with s_cortex.openurl('ram://', savecore=savecore) as core:
                load = core.getTufoByProp('prop', valu='valu')
                self.assertEqual(save[0], load[0])
                self.assertEqual(load[1]['prop'], 'valu')

            # test inc
            with s_cortex.openurl('ram://', savecore=savecore) as core:
                wait = TestWaiter(savecore.loadbus, 1, 'core:save:set:rows:by:idprop')
                tufo = core.formTufoByProp('prop', 'valu')
                core.incTufoProp(tufo, 'cnt')
                wait.wait()
                save = savecore.getTufoByProp('prop', valu='valu')
                self.assertEqual(save[1]['tufo:form'], 'prop')
                self.assertEqual(save[1]['prop'], 'valu')
                self.assertEqual(save[1]['prop:cnt'], 1)

            # test min
            with s_cortex.openurl('ram://', savecore=savecore) as core:
                wait = TestWaiter(savecore.loadbus, 1, 'core:save:set:rows:by:idprop')
                tufo = core.formTufoByProp('prop', 'valu')
                core.minTufoProp(tufo, 'min', 1)
                wait.wait()
                save = savecore.getTufoByProp('prop', valu='valu')
                self.assertEqual(save[1]['tufo:form'], 'prop')
                self.assertEqual(save[1]['prop'], 'valu')
                self.assertEqual(save[1]['prop:min'], 1)

            # test max
            with s_cortex.openurl('ram://', savecore=savecore) as core:
                wait = TestWaiter(savecore.loadbus, 1, 'core:save:set:rows:by:idprop')
                tufo = core.formTufoByProp('prop', 'valu')
                core.incTufoProp(tufo, 'max', 1)
                wait.wait()
                save = savecore.getTufoByProp('prop', valu='valu')
                self.assertEqual(save[1]['tufo:form'], 'prop')
                self.assertEqual(save[1]['prop'], 'valu')
                self.assertEqual(save[1]['prop:max'], 1)

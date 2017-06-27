from __future__ import absolute_import,unicode_literals

import binascii
import os
import tempfile
import unittest

import synapse.compat as s_compat
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.tags as s_tags
import synapse.lib.types as s_types
import synapse.lib.threads as s_threads

import synapse.models.syn as s_models_syn
import synapse.cores.lmdb as lmdb

from synapse.tests.common import *

class FakeType(s_types.IntType):
    pass

import synapse.lib.module as s_module

class CoreTestModule(s_module.CoreModule):

    def initCoreModule(self):

        def formipv4(form, valu, props, mesg):
            props['inet:ipv4:asn'] = 10

        self.onFormNode('inet:ipv4',formipv4)
        self.addConfDef('foobar', defval=False, asloc='foobar')

        self.revCoreModl()

    @s_module.modelrev('test',0)
    def _testRev0(self):
        self.core.addType('test:type1',subof='str')

    @s_module.modelrev('test',1)
    def _testRev1(self):
        self.core.addType('test:type2',subof='str')

class CortexTest(SynTest):

    def test_cortex_ram(self):
        core = s_cortex.openurl('ram://')
        self.true( hasattr( core.link, '__call__' ) )
        self.runcore( core )
        self.runjson( core )
        self.runrange( core )
        self.runidens( core )
        self.rundsets( core )
        self.runsnaps( core )
        self.rundarks(core)

    def test_cortex_sqlite3(self):
        core = s_cortex.openurl('sqlite:///:memory:')
        self.runcore( core )
        self.runjson( core )
        self.runrange( core )
        self.runidens( core )
        self.rundsets( core )
        self.runsnaps( core )
        self.rundarks(core)

    lmdb_file = 'test.lmdb'
    lmdb_url = 'lmdb:///%s' % lmdb_file
    def test_cortex_lmdb(self):
        core = s_cortex.openurl(CortexTest.lmdb_url)
        self.runcore( core )
        self.runjson( core )
        self.runrange( core )
        self.runidens( core )
        self.rundsets( core )
        self.runsnaps( core )
        self.rundarks(core)

        # Test load an existing db
        core = s_cortex.openurl(CortexTest.lmdb_url)

    def tearDown(self):
        try:
            os.remove(CortexTest.lmdb_file)
            os.remove(CortexTest.lmdb_file + '-lock')
        except OSError:
            pass

    def test_cortex_postgres(self):
        with self.getPgCore() as core:
            self.runcore( core )
            self.runjson( core )
            self.runrange( core )
            self.runidens( core )
            self.rundsets( core )
            self.runsnaps( core )
            self.rundarks(core)

    def rundsets(self, core):
        tufo = core.formTufoByProp('lol:zonk',1)
        core.addTufoDset(tufo,'violet')

        self.eq( len( core.eval('dset(violet)') ), 1 )
        self.eq( len( core.getTufosByDset('violet') ), 1 )
        self.eq( core.getTufoDsets(tufo)[0][0], 'violet' )

        core.delTufoDset(tufo,'violet')

        self.eq( len( core.getTufosByDset('violet') ), 0 )
        self.eq( len(core.getTufoDsets(tufo)), 0 )

    def rundarks(self, core):

        tufo = core.formTufoByProp('lol:zonk', 1)
        core.addTufoDark(tufo, 'hidden', 'color')
        # Duplicate call for code coverage.
        core.addTufoDark(tufo, 'hidden', 'color')

        self.eq(len(core.getTufosByDark('hidden', 'color')), 1)
        self.eq(len(core.getTufosByDark('hidden')), 1)
        self.eq(len(core.getTufosByDark('hidden', 'secret')), 0)
        self.eq(len(core.getTufosByDark('knight')), 0)

        self.eq(len(core.getTufosBy('dark', 'hidden', 'color')), 1)
        self.eq(core.getTufoDarkNames(tufo)[0][0], 'hidden')
        self.eq(core.getTufoDarkValus(tufo, 'hidden')[0][0], 'color')

        core.delTufoDark(tufo, 'hidden', 'color')

        self.eq(core.getTufoDarkNames(tufo), [])
        self.eq(len(core.getTufosByDark('hidden', 'color')), 0)
        self.eq(len(core.getTufosBy('dark', 'hidden', 'color')), 0)
        self.eq(len(core.getTufoDarkValus(tufo, 'hidden')), 0)


    def runsnaps(self, core):

        with core.getCoreXact():
            for i in range(1500):
                tufo = core.formTufoByProp('lol:foo', i)
                core.addTufoDset(tufo,'zzzz')
                core.addTufoDark(tufo, 'animal', 'duck')

        #############################################

        answ = core.snapTufosByProp('lol:foo', valu=100)

        self.eq( answ.get('count'), 1 )
        self.eq( answ.get('tufos')[0][1].get('lol:foo'), 100 )

        #############################################

        answ = core.snapTufosByProp('lol:foo')
        snap = answ.get('snap')

        core.finiSnap( snap )
        self.none( core.getSnapNext(snap) )

        #############################################

        answ = core.snapTufosByProp('lol:foo')

        res = []

        snap = answ.get('snap')
        tufs = answ.get('tufos')

        self.eq( answ.get('count'), 1500 )

        while tufs:
            res.extend(tufs)
            tufs = core.getSnapNext(snap)

        self.eq(len(res),1500)
        self.none( core.getSnapNext(snap) )

        #############################################

        answ = core.snapTufosByDset('zzzz')

        res = []

        snap = answ.get('snap')
        tufs = answ.get('tufos')

        self.eq( answ.get('count'), 1500 )

        while tufs:
            res.extend(tufs)
            tufs = core.getSnapNext(snap)

        self.eq(len(res),1500)
        self.none( core.getSnapNext(snap) )

        #############################################

        answ = core.snapTufosByDark('animal', 'duck')

        res = []

        snap = answ.get('snap')
        tufs = answ.get('tufos')

        self.eq(answ.get('count'), 1500)

        while tufs:
            res.extend(tufs)
            tufs = core.getSnapNext(snap)

        self.eq(len(res), 1500)
        self.none(core.getSnapNext(snap))

        answ = core.snapTufosByDark('animal')

        res = []

        snap = answ.get('snap')
        tufs = answ.get('tufos')

        self.eq(answ.get('count'), 1500)

        while tufs:
            res.extend(tufs)
            tufs = core.getSnapNext(snap)

        self.eq(len(res), 1500)
        self.none(core.getSnapNext(snap))

        answ = core.snapTufosByDark('plant', 'tree')

        snap = answ.get('snap')
        tufs = answ.get('tufos')

        self.eq(answ.get('count'), 0)
        self.eq(len(tufs), 0)
        self.none(core.getSnapNext(snap))

    def runidens(self, core):
        t0 = core.formTufoByProp('inet:ipv4', 0)
        t1 = core.formTufoByProp('inet:ipv4', 0x01020304)
        t2 = core.formTufoByProp('inet:ipv4', 0x7f000001)

        # re-form to ditch things like .new=1
        t0 = core.formTufoByProp('inet:ipv4', 0)
        t1 = core.formTufoByProp('inet:ipv4', 0x01020304)
        t2 = core.formTufoByProp('inet:ipv4', 0x7f000001)

        idens = [ t0[0], t1[0], t2[0] ]
        self.sorteq( core.getTufosByIdens(idens), [t0,t1,t2] )

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

        self.eq( len(core.getRowsByIdProp(id1,'baz')), 1)

        #pivo = core.getPivotByProp('baz','foo', valu='bar')
        #self.eq( tuple(sorted([r[2] for r in pivo])), ('faz1','faz2'))

        self.eq( tufo[0], id1 )
        self.eq( tufo[1].get('foo'), 'bar')
        self.eq( tufo[1].get('baz'), 'faz1')
        self.eq( tufo[1].get('gronk'), 80 )

        self.eq( core.getSizeByProp('foo:newp'), 0 )
        self.eq( len(core.getRowsByProp('foo:newp')), 0 )

        self.eq( core.getSizeByProp('foo'), 2 )
        self.eq( core.getSizeByProp('baz',valu='faz1'), 1 )
        self.eq( core.getSizeByProp('foo',mintime=80,maxtime=100), 1 )

        self.eq( len(core.getRowsByProp('foo')), 2 )
        self.eq( len(core.getRowsByProp('foo',valu='bar')), 2 )

        self.eq( len(core.getRowsByProp('baz')), 2 )
        self.eq( len(core.getRowsByProp('baz',valu='faz1')), 1 )
        self.eq( len(core.getRowsByProp('baz',valu='faz2')), 1 )

        self.eq( len(core.getRowsByProp('gronk',valu=90)), 1 )

        self.eq( len(core.getRowsById(id1)), 3)

        self.eq( len(core.getJoinByProp('baz')), 6 )
        self.eq( len(core.getJoinByProp('baz',valu='faz1')), 3 )
        self.eq( len(core.getJoinByProp('baz',valu='faz2')), 3 )

        self.eq( len(core.getRowsByProp('baz',mintime=0,maxtime=80)), 1 )
        self.eq( len(core.getJoinByProp('baz',mintime=0,maxtime=80)), 3 )

        self.eq( len(core.getRowsByProp('baz',limit=1)), 1 )
        self.eq( len(core.getJoinByProp('baz',limit=1)), 3 )

        core.setRowsByIdProp(id4,'lolstr','haha')
        self.eq( len(core.getRowsByProp('lolstr','hehe')), 0 )
        self.eq( len(core.getRowsByProp('lolstr','haha')), 1 )

        core.setRowsByIdProp(id4,'lolint', 99)
        self.eq( len(core.getRowsByProp('lolint', 80)), 0 )
        self.eq( len(core.getRowsByProp('lolint', 99)), 1 )

        core.delRowsByIdProp(id4,'lolint')
        core.delRowsByIdProp(id4,'lolstr')

        self.eq( len(core.getRowsByProp('lolint')), 0 )
        self.eq( len(core.getRowsByProp('lolstr')), 0 )

        core.delRowsById(id1)

        self.eq( len(core.getRowsById(id1)), 0 )

        self.eq( len(core.getRowsByProp('b',valu='b')), 1 )
        core.delRowsByProp('b',valu='b')
        self.eq( len(core.getRowsByProp('b',valu='b')), 0 )

        self.eq( len(core.getRowsByProp('a',valu='a')), 1 )
        core.delJoinByProp('c',valu=90)
        self.eq( len(core.getRowsByProp('a',valu='a')), 0 )

        def formtufo(event):
            props = event[1].get('props')
            props['woot'] = 'woot'

        def formfqdn(event):
            fqdn = event[1].get('valu')
            event[1]['props']['sfx'] = fqdn.split('.')[-1]
            event[1]['props']['fqdn:inctest'] = 0

        core.on('node:form', formtufo)
        core.on('node:form', formfqdn, form='fqdn')

        tufo = core.formTufoByProp('fqdn','woot.com')

        self.eq( tufo[1].get('sfx'), 'com')
        self.eq( tufo[1].get('woot'), 'woot')

        self.eq( tufo[1].get('fqdn:inctest'), 0)

        tufo = core.incTufoProp(tufo, 'inctest')

        self.eq( tufo[1].get('fqdn:inctest'), 1 )

        tufo = core.incTufoProp(tufo, 'inctest', incval=-1)

        self.eq( tufo[1].get('fqdn:inctest'), 0 )

        bigstr = binascii.hexlify( os.urandom(80000) ).decode('utf8')
        tufo = core.formTufoByProp('zoot:suit','foo', bar=bigstr)

        self.eq( tufo[1].get('zoot:suit:bar'), bigstr )
        self.eq( len( core.getTufosByProp('zoot:suit:bar',valu=bigstr) ), 1 )

    def runrange(self, core):

        rows = [
            (guid(),'rg',10,99),
            (guid(),'rg',30,99),
        ]

        core.addRows( rows )

        self.eq( core.getSizeBy('range','rg',(0,20)), 1 )
        self.eq( core.getRowsBy('range','rg',(0,20))[0][2], 10 )

        # range is inclusive of `min`, exclusive of `max`
        self.eq( core.getSizeBy('range','rg',(9,11)), 1 )
        self.eq( core.getSizeBy('range','rg',(10,12)), 1 )
        self.eq( core.getSizeBy('range','rg',(8,10)), 0 )

        self.eq( core.getSizeBy('ge','rg',20), 1 )
        self.eq( core.getRowsBy('ge','rg',20)[0][2], 30)

        self.eq( core.getSizeBy('le','rg',20), 1 )
        self.eq( core.getRowsBy('le','rg',20)[0][2], 10 )

        rows = [
            (guid(),'rg',-42,99),
            (guid(),'rg',-1,99),
            (guid(),'rg',0,99),
            (guid(),'rg',1,99),
            (guid(),'rg',lmdb.MIN_INT_VAL,99),
            (guid(),'rg',lmdb.MAX_INT_VAL,99),
        ]
        core.addRows( rows )
        self.assertEqual( core.getSizeBy('range','rg',(lmdb.MIN_INT_VAL+1,-42)), 0 )
        self.assertEqual( core.getSizeBy('range','rg',(lmdb.MIN_INT_VAL,-42)), 1 )
        self.assertEqual( core.getSizeBy('le','rg',-42), 2 )
        # TODO: Need to implement lt for all the cores
        if 0:
            self.assertEqual( core.getSizeBy('lt','rg',-42), 1 )
        self.assertEqual( core.getSizeBy('range','rg',(-42, 0)), 2 )
        self.assertEqual( core.getSizeBy('range','rg',(-1, 2)), 3 )
        if 0:
            self.assertEqual( core.getSizeBy('lt','rg',0), 3 )
        self.assertEqual( core.getSizeBy('le','rg',0), 4 )
        # This is broken for RAM and SQLite
        if 0:
            self.assertEqual( core.getSizeBy('ge','rg',-1, limit=3), 3 )
        self.assertEqual( core.getSizeBy('ge','rg',30), 2 )
        self.assertEqual( core.getSizeBy('ge','rg',lmdb.MAX_INT_VAL), 1 )

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

            self.eq( item['foo']['blah'][0], 99 )

    def test_pg_encoding(self):
        with self.getPgCore() as core:
            res = core.select('SHOW SERVER_ENCODING')[0][0]
            self.eq(res, 'UTF8')

    def test_cortex_choptag(self):
        t0 = tuple(s_cortex.choptag('foo'))
        t1 = tuple(s_cortex.choptag('foo.bar'))
        t2 = tuple(s_cortex.choptag('foo.bar.baz'))

        self.eq( t0, ('foo',))
        self.eq( t1, ('foo','foo.bar'))
        self.eq( t2, ('foo','foo.bar','foo.bar.baz'))

    def test_cortex_tufo_by_default(self):
        core = s_cortex.openurl('sqlite:///:memory:')

        # BY IN
        fooa = core.formTufoByProp('foo','bar',p0=4)
        foob = core.formTufoByProp('foo','baz',p0=5)

        self.eq( len(core.getTufosBy('in', 'foo:p0', [4])), 1)

        fooc = core.formTufoByProp('foo','faz',p0=5)
        food = core.formTufoByProp('foo','haz',p0=6)
        fooe = core.formTufoByProp('foo','gaz',p0=7)
        self.eq( len(core.getTufosBy('in', 'foo:p0', [5])), 2)
        self.eq( len(core.getTufosBy('in', 'foo:p0', [4,5])), 3)
        self.eq( len(core.getTufosBy('in', 'foo:p0', [4,5,6,7], limit=4)), 4)
        self.eq( len(core.getTufosBy('in', 'foo:p0', [5], limit=1)), 1)
        self.eq( len(core.getTufosBy('in', 'foo:p0', [], limit=1)), 0)

        # BY CIDR
        tlib = s_types.TypeLib()

        ipint,_ = tlib.getTypeParse('inet:ipv4', '192.168.0.1')
        ipa = core.formTufoByProp('inet:ipv4', ipint)
        ipint,_ = tlib.getTypeParse('inet:ipv4', '192.168.255.254')
        ipa = core.formTufoByProp('inet:ipv4', ipint)

        ipint,_ = tlib.getTypeParse('inet:ipv4', '192.167.255.254')
        ipb = core.formTufoByProp('inet:ipv4', ipint)

        ips = ['10.2.1.%d' % d for d in range(1,33)]
        for ip in ips:
            ipint,_ = tlib.getTypeParse('inet:ipv4', ip)
            ipc = core.formTufoByProp('inet:ipv4', ipint)

        self.eq( len(core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.4/32')), 1)
        self.eq( len(core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.4/31')), 2)
        self.eq( len(core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.1/30')), 4)
        self.eq( len(core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.2/30')), 4)
        self.eq( len(core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.1/29')), 8)
        self.eq( len(core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.1/28')), 16)

        self.eq( len(core.getTufosBy('inet:cidr', 'inet:ipv4', '192.168.0.0/16')), 2)

    def test_cortex_tufo_by_postgres(self):

        with self.getPgCore() as core:

            fooa = core.formTufoByProp('foo','bar',p0=4)
            foob = core.formTufoByProp('foo','baz',p0=5)

            self.eq( len(core.getTufosBy('in', 'foo:p0', [4])), 1)

            fooc = core.formTufoByProp('foo','faz',p0=5)

            self.eq( len(core.getTufosBy('in', 'foo:p0', [5])), 2)
            self.eq( len(core.getTufosBy('in', 'foo:p0', [4,5])), 3)
            self.eq( len(core.getTufosBy('in', 'foo:p0', [5], limit=1)), 1)

    def test_cortex_tufo_tag(self):
        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo','bar',baz='faz')
        core.addTufoTag(foob,'zip.zap')

        self.nn( foob[1].get('*|foo|zip') )
        self.nn( foob[1].get('*|foo|zip.zap') )

        self.eq( len(core.getTufosByTag('foo','zip')), 1 )
        self.eq( len(core.getTufosByTag('foo','zip.zap')), 1 )
        self.eq(len(core.getTufosByDark('tag', 'zip')), 1)
        self.eq(len(core.getTufosByDark('tag', 'zip.zap')), 1)

        core.delTufoTag(foob,'zip')

        self.none( foob[1].get('*|foo|zip') )
        self.none( foob[1].get('*|foo|zip.zap') )

        self.eq( len(core.getTufosByTag('foo','zip')), 0 )
        self.eq( len(core.getTufosByTag('foo','zip.zap')), 0 )
        self.eq(len(core.getTufosByDark('tag', 'zip')), 0)
        self.eq(len(core.getTufosByDark('tag', 'zip.zap')), 0)

    def test_cortex_tufo_setprops(self):
        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo','bar',baz='faz')
        self.eq( foob[1].get('foo:baz'), 'faz' )
        core.setTufoProps(foob,baz='zap')
        core.setTufoProps(foob,faz='zap')

        self.eq( len(core.getTufosByProp('foo:baz',valu='zap')), 1 )
        self.eq( len(core.getTufosByProp('foo:faz',valu='zap')), 1 )

    def test_cortex_tufo_pop(self):
        with s_cortex.openurl('ram://') as core:
            foo0 = core.formTufoByProp('foo','bar',woot='faz')
            foo1 = core.formTufoByProp('foo','baz',woot='faz')

            self.eq( 2, len(core.popTufosByProp('foo:woot', valu='faz')))
            self.eq( 0, len(core.getTufosByProp('foo')))

    def test_cortex_tufo_setprop(self):
        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo','bar',baz='faz')
        self.eq( foob[1].get('foo:baz'), 'faz' )

        core.setTufoProp(foob,'baz','zap')

        self.eq( len(core.getTufosByProp('foo:baz',valu='zap')), 1 )

    def test_cortex_tufo_list(self):

        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo','bar',baz='faz')

        core.addTufoList(foob,'hehe', 1, 2, 3)

        self.nn( foob[1].get('tufo:list:hehe') )

        vals = core.getTufoList(foob,'hehe')
        vals.sort()

        self.eq( tuple(vals), (1,2,3) )

        core.delTufoListValu(foob,'hehe', 2)

        vals = core.getTufoList(foob,'hehe')
        vals.sort()

        self.eq( tuple(vals), (1,3) )

        core.fini()

    def test_cortex_tufo_del(self):

        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo','bar',baz='faz')

        self.nn( core.getTufoByProp('foo', valu='bar') )
        self.nn( core.getTufoByProp('foo:baz', valu='faz') )

        core.addTufoList(foob, 'blahs', 'blah1' )
        core.addTufoList(foob, 'blahs', 'blah2' )

        blahs = core.getTufoList(foob,'blahs')

        self.eq( len(blahs), 2 )

        core.delTufoByProp('foo','bar')

        self.none( core.getTufoByProp('foo', valu='bar') )
        self.none( core.getTufoByProp('foo:baz', valu='faz') )

        blahs = core.getTufoList(foob,'blahs')
        self.eq( len(blahs), 0 )

    def test_cortex_ramhost(self):
        core0 = s_cortex.openurl('ram:///foobar')
        core1 = s_cortex.openurl('ram:///foobar')
        self.eq( id(core0), id(core1) )

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
        self.none( core1.getTufoByProp('foo','two') )

        t0 = core1.getTufoByProp('foo','one')
        self.nn( t0 )

        self.eq( t0[1].get('foo:baz'), 'gronk' )

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

        self.eq( core.getStatByProp('sum','foo:bar'), 53 )
        self.eq( core.getStatByProp('count','foo:bar'), 7 )

        self.eq( core.getStatByProp('min','foo:bar'), 1 )
        self.eq( core.getStatByProp('max','foo:bar'), 21 )

        self.eq( core.getStatByProp('mean','foo:bar'), 7.571428571428571 )

        self.eq( core.getStatByProp('any','foo:bar'), 1)
        self.eq( core.getStatByProp('all','foo:bar'), 1)

        histo = core.getStatByProp('histo','foo:bar')
        self.eq( histo.get(13), 1 )

        self.assertRaises( NoSuchStat, core.getStatByProp, 'derp', 'inet:ipv4' )

    def test_cortex_fire_set(self):

        core = s_cortex.openurl('ram://')

        tufo = core.formTufoByProp('foo', 'hehe', bar='lol')

        msgs = wait = core.waiter(1,'node:set')

        core.setTufoProps(tufo,bar='hah')

        evts = wait.wait(timeout=2)

        self.eq( evts[0][0], 'node:set')
        self.eq( evts[0][1]['node'][0], tufo[0])
        self.eq( evts[0][1]['form'], 'foo' )
        self.eq( evts[0][1]['valu'], 'hehe' )
        self.eq( evts[0][1]['prop'], 'foo:bar' )
        self.eq( evts[0][1]['newv'], 'hah')
        self.eq( evts[0][1]['oldv'], 'lol')

        core.fini()

    def test_cortex_tags(self):
        core = s_cortex.openurl('ram://')

        core.addTufoForm('foo')

        hehe = core.formTufoByProp('foo','hehe')

        wait = core.waiter(2, 'node:tag:add')
        core.addTufoTag(hehe,'lulz.rofl')
        wait.wait(timeout=2)

        wait = core.waiter(1, 'node:tag:add')
        core.addTufoTag(hehe,'lulz.rofl.zebr')
        wait.wait(timeout=2)

        lulz = core.getTufoByProp('syn:tag','lulz')

        self.none( lulz[1].get('syn:tag:up') )
        self.eq( lulz[1].get('syn:tag:doc'), '')
        self.eq( lulz[1].get('syn:tag:title'), '')
        self.eq( lulz[1].get('syn:tag:depth'), 0 )
        self.eq(lulz[1].get('syn:tag:base'), 'lulz')

        rofl = core.getTufoByProp('syn:tag','lulz.rofl')

        self.eq( rofl[1].get('syn:tag:doc'), '')
        self.eq( rofl[1].get('syn:tag:title'), '')
        self.eq( rofl[1].get('syn:tag:up'), 'lulz' )

        self.eq( rofl[1].get('syn:tag:depth'), 1 )
        self.eq( rofl[1].get('syn:tag:base'), 'rofl')

        tags = core.getTufosByProp('syn:tag:base', 'rofl')

        self.eq(len(tags), 1)

        wait = core.waiter(2, 'node:tag:del')
        core.delTufoTag(hehe,'lulz.rofl')
        wait.wait(timeout=2)

        wait = core.waiter(1, 'node:tag:del')
        core.delTufo(lulz)
        wait.wait(timeout=2)
        # tag and subs should be wiped

        self.none( core.getTufoByProp('syn:tag','lulz') )
        self.none( core.getTufoByProp('syn:tag','lulz.rofl') )
        self.none( core.getTufoByProp('syn:tag','lulz.rofl.zebr') )

        self.eq( len(core.getTufosByTag('foo','lulz')), 0 )
        self.eq( len(core.getTufosByTag('foo','lulz.rofl')), 0 )
        self.eq( len(core.getTufosByTag('foo','lulz.rofl.zebr')), 0 )

        core.fini()

    def test_cortex_splices(self):
        core0 = s_cortex.openurl('ram://')
        core1 = s_cortex.openurl('ram://')

        core0.on('splice',core1.splice)

        tufo0 = core0.formTufoByProp('foo','bar',baz='faz')
        tufo1 = core1.getTufoByProp('foo','bar')

        self.eq( tufo1[1].get('foo'), 'bar' )
        self.eq( tufo1[1].get('foo:baz'), 'faz' )

        tufo0 = core0.addTufoTag(tufo0,'hehe')
        tufo1 = core1.getTufoByProp('foo','bar')

        self.true( s_tags.tufoHasTag(tufo1,'hehe') )

        core0.delTufoTag(tufo0,'hehe')
        tufo1 = core1.getTufoByProp('foo','bar')

        self.assertFalse( s_tags.tufoHasTag(tufo1,'hehe') )

        core0.setTufoProp(tufo0,'baz','lol')
        tufo1 = core1.getTufoByProp('foo','bar')

        self.eq( tufo1[1].get('foo:baz'), 'lol' )

        core0.delTufo(tufo0)
        tufo1 = core1.getTufoByProp('foo','bar')

        self.none( tufo1 )

    def test_cortex_dict(self):
        core = s_cortex.openurl('ram://')
        core.addTufoForm('foo:bar', ptype='int')
        core.addTufoForm('baz:faz', ptype='int', defval=22)

        modl = core.getModelDict()
        self.eq( modl['forms'][-2:], ['foo:bar','baz:faz'] )
        self.eq( modl['props']['foo:bar'][1]['ptype'], 'int')
        self.eq( modl['props']['baz:faz'][1]['defval'], 22)

        core.fini()

    def test_cortex_comp(self):
        core = s_cortex.openurl('ram://')

        fields = 'fqdn,inet:fqdn|ipv4,inet:ipv4|time,time:epoch'
        core.addType('foo:a',subof='comp',fields=fields)

        core.addTufoForm('foo:a',ptype='foo:a')
        core.addTufoProp('foo:a','fqdn',ptype='inet:fqdn')
        core.addTufoProp('foo:a','ipv4',ptype='inet:ipv4')
        core.addTufoProp('foo:a','time',ptype='time:epoch')

        arec = ('wOOt.com',0x01020304,0x00404040)

        dnsa = core.formTufoByProp('foo:a', arec)

        fval = guid(('woot.com',0x01020304,0x00404040))

        self.eq( dnsa[1].get('foo:a'), fval)
        self.eq( dnsa[1].get('foo:a:fqdn'), 'woot.com')
        self.eq( dnsa[1].get('foo:a:ipv4'), 0x01020304)
        self.eq( dnsa[1].get('foo:a:time'), 0x00404040)

        core.fini()

    def test_cortex_enforce(self):

        with s_cortex.openurl('ram://') as core:

            core.addTufoForm('foo:bar', ptype='inet:email')

            core.addTufoForm('foo:baz', ptype='inet:email')
            core.addTufoProp('foo:baz', 'fqdn', ptype='inet:fqdn')
            core.addTufoProp('foo:baz', 'haha', ptype='int')

            cofo = core.getTufoByProp('syn:core','self')
            self.nn( cofo )
            self.assertFalse( core.enforce )

            core.setConfOpt('enforce',True)

            self.true( core.enforce )

            tufo0 = core.formTufoByProp('foo:bar','foo@bar.com', hehe=10, haha=20)
            tufo1 = core.formTufoByProp('foo:baz','foo@bar.com', hehe=10, haha=20)

            # did it remove the non-declared props and subprops?
            self.none( tufo0[1].get('foo:bar:fqdn') )
            self.none( tufo0[1].get('foo:bar:hehe') )
            self.none( tufo0[1].get('foo:bar:haha') )

            # did it selectivly keep the declared props and subprops
            self.eq( tufo1[1].get('foo:baz:haha'), 20 )
            self.eq( tufo1[1].get('foo:baz:fqdn'), 'bar.com' )

            self.none( tufo1[1].get('foo:baz:hehe') )
            self.none( tufo1[1].get('foo:baz:user') )

            tufo0 = core.setTufoProps(tufo0, fqdn='visi.com', hehe=11 )
            tufo1 = core.setTufoProps(tufo1, fqdn='visi.com', hehe=11, haha=21 )

            self.none( tufo0[1].get('foo:bar:fqdn') )
            self.none( tufo0[1].get('foo:bar:hehe') )

            self.none( tufo1[1].get('foo:baz:hehe') )

            self.eq( tufo1[1].get('foo:baz:haha'), 21 )
            self.eq( tufo1[1].get('foo:baz:fqdn'), 'visi.com' )


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

            tufo0 = core.formTufoByProp('foo','bar')
            tufo0 = core.addTufoTag(tufo0,'hehe')

            self.eq( len( core.getTufosByTag('foo','hehe') ), 1 )
            core.delTufoTag(tufo0,'hehe')

            tufo0 = core.getTufoByProp('foo','bar')
            self.noprop( tufo0[1], '*|foo|hehe')

    def test_cortex_caching_set(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar', qwer=10)
            tufo1 = core.formTufoByProp('foo','baz', qwer=10)

            core.setConfOpt('caching',1)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)
            tufs3 = core.getTufosByProp('foo:qwer', valu=10, limit=2)

            self.eq( len(tufs0), 2 )
            self.eq( len(tufs1), 2 )
            self.eq( len(tufs2), 0 )
            self.eq( len(tufs3), 2 )

            # inspect the details of the cache data structures when setTufoProps
            # causes an addition or removal...
            self.nn( core.cache_bykey.get( ('foo:qwer',10,None) ) )
            self.nn( core.cache_bykey.get( ('foo:qwer',None,None) ) )

            # we should have hit the unlimited query and not created a new cache hit...
            self.none( core.cache_bykey.get( ('foo:qwer',10,2) ) )

            self.nn( core.cache_byiden.get( tufo0[0] ) )
            self.nn( core.cache_byiden.get( tufo1[0] ) )

            self.nn( core.cache_byprop.get( ('foo:qwer',10) ) )
            self.nn( core.cache_byprop.get( ('foo:qwer',None) ) )

            core.setTufoProp(tufo0,'qwer',11)

            # the cached results should be updated
            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            self.eq( len(tufs0), 2 )
            self.eq( len(tufs1), 1 )
            self.eq( len(tufs2), 1 )

            self.eq( tufs1[0][0], tufo1[0] )
            self.eq( tufs2[0][0], tufo0[0] )

    def test_cortex_caching_add_tufo(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar', qwer=10)
            tufo1 = core.formTufoByProp('foo','baz', qwer=10)

            core.setConfOpt('caching',1)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            self.eq( len(tufs0), 2 )
            self.eq( len(tufs1), 2 )
            self.eq( len(tufs2), 0 )

            tufo2 = core.formTufoByProp('foo','lol', qwer=10)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            self.eq( len(tufs0), 3 )
            self.eq( len(tufs1), 3 )
            self.eq( len(tufs2), 0 )

    def test_cortex_caching_del_tufo(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar', qwer=10)
            tufo1 = core.formTufoByProp('foo','baz', qwer=10)

            core.setConfOpt('caching',1)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            self.eq( len(tufs0), 2 )
            self.eq( len(tufs1), 2 )
            self.eq( len(tufs2), 0 )

            core.delTufo( tufo0 )
            #tufo2 = core.formTufoByProp('foo','lol', qwer=10)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            self.eq( len(tufs0), 1 )
            self.eq( len(tufs1), 1 )
            self.eq( len(tufs2), 0 )

    def test_cortex_caching_atlimit(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar', qwer=10)
            tufo1 = core.formTufoByProp('foo','baz', qwer=10)

            core.setConfOpt('caching',1)

            tufs0 = core.getTufosByProp('foo:qwer', limit=2)
            tufs1 = core.getTufosByProp('foo:qwer', valu=10, limit=2)

            self.eq( len(tufs0), 2 )
            self.eq( len(tufs1), 2 )

            # when an entry is deleted from a cache result that was at it's limit
            # it should be fully invalidated

            core.delTufo(tufo0)

            self.none( core.cache_bykey.get( ('foo:qwer',None,2) ) )
            self.none( core.cache_bykey.get( ('foo:qwer',10,2) ) )

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar', qwer=10)
            tufo1 = core.formTufoByProp('foo','baz', qwer=10)

            core.setConfOpt('caching',1)

            tufs0 = core.getTufosByProp('foo:qwer', limit=2)
            tufs1 = core.getTufosByProp('foo:qwer', valu=10, limit=2)

            self.eq( len(tufs0), 2 )
            self.eq( len(tufs1), 2 )

            tufo2 = core.formTufoByProp('foo','baz', qwer=10)

            # when an entry is added from a cache result that was at it's limit
            # it should *not* be invalidated

            self.nn( core.cache_bykey.get( ('foo:qwer',None,2) ) )
            self.nn( core.cache_bykey.get( ('foo:qwer',10,2) ) )

    def test_cortex_caching_under_limit(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo','bar', qwer=10)
            tufo1 = core.formTufoByProp('foo','baz', qwer=10)

            core.setConfOpt('caching',1)

            tufs0 = core.getTufosByProp('foo:qwer', limit=9)
            tufs1 = core.getTufosByProp('foo:qwer', valu=10, limit=9)

            self.eq( len(tufs0), 2 )
            self.eq( len(tufs1), 2 )

            # when an entry is deleted from a cache result that was under it's limit
            # it should be removed but *not* invalidated

            core.delTufo(tufo0)

            self.nn( core.cache_bykey.get( ('foo:qwer',None,9) ) )
            self.nn( core.cache_bykey.get( ('foo:qwer',10,9) ) )

            tufs0 = core.getTufosByProp('foo:qwer', limit=9)
            tufs1 = core.getTufosByProp('foo:qwer', valu=10, limit=9)

            self.eq( len(tufs0), 1 )
            self.eq( len(tufs1), 1 )


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

            self.true(tufo0[1].get('.new'))
            self.assertFalse(tufo1[1].get('.new'))

    def test_cortex_reqstor(self):
        with s_cortex.openurl('ram://') as core:
            self.assertRaises( BadPropValu, core.formTufoByProp, 'foo:bar', True )

    def test_cortex_events(self):
        with s_cortex.openurl('ram://') as core:

            tick = now()

            tufo0 = core.addTufoEvent('foo', bar=10, baz='thing')

            tock = now()

            id0 = tufo0[0]
            rows = core.getRowsById(id0)

            self.eq(len(rows), 4)
            self.true(rows[0][-1] >= tick)
            self.true(rows[0][-1] <= tock)

    def test_cortex_tlib_persistence(self):
        with self.getTestDir() as path:

            savefile = genpath(path,'savefile.mpk')

            with s_cortex.openurl('ram://',savefile=savefile) as core:

                core.formTufoByProp('syn:type','foo',subof='bar')
                core.formTufoByProp('syn:type','bar',ctor='synapse.tests.test_cortex.FakeType')

                self.eq( core.getTypeParse('foo','30')[0], 30 )
                self.eq( core.getTypeParse('bar','30')[0], 30 )

            with s_cortex.openurl('ram://',savefile=savefile) as core:
                self.eq( core.getTypeParse('foo','30')[0], 30 )
                self.eq( core.getTypeParse('bar','30')[0], 30 )

    def test_cortex_splicefd(self):
        with self.getTestDir() as path:
            with genfile(path,'savefile.mpk') as fd:
                with s_cortex.openurl('ram://') as core:
                    core.addSpliceFd(fd)

                    tuf0 = core.formTufoByProp('inet:fqdn','woot.com')
                    tuf1 = core.formTufoByProp('inet:fqdn','newp.com')

                    core.addTufoTag(tuf0,'foo.bar')
                    # this should leave the tag foo
                    core.delTufoTag(tuf0,'foo.bar')

                    core.delTufo(tuf1)

                fd.seek(0)

                with s_cortex.openurl('ram://') as core:

                    core.eatSpliceFd(fd)

                    self.none( core.getTufoByProp('inet:fqdn','newp.com') )
                    self.nn( core.getTufoByProp('inet:fqdn','woot.com') )

                    self.eq( len(core.getTufosByTag('inet:fqdn', 'foo.bar')), 0 )
                    self.eq( len(core.getTufosByTag('inet:fqdn', 'foo')), 1)

    def test_cortex_addmodel(self):
        with s_cortex.openurl('ram://') as core:
            core.addDataModel('a.foo.module',
                {
                    'prefix':'foo',

                    'types':(
                        ('foo:bar',{'subof':'str:lwr'}),
                    ),

                    'forms':(
                        ('foo:baz',{'ptype':'foo:bar'},[
                            ('faz',{'ptype':'str:lwr'}),
                        ]),
                    ),
                })

            tyfo = core.getTufoByProp('syn:type','foo:bar')
            self.eq( tyfo[1].get('syn:type:subof'), 'str:lwr' )

            fofo = core.getTufoByProp('syn:form','foo:baz')
            self.eq( fofo[1].get('syn:form:ptype'),'foo:bar' )

            pofo = core.getTufoByProp('syn:prop','foo:baz:faz')
            self.eq( pofo[1].get('syn:prop:ptype'),'str:lwr' )

            tuf0 = core.formTufoByProp('foo:baz', 'AAA', faz='BBB')
            self.eq( tuf0[1].get('foo:baz'), 'aaa' )
            self.eq( tuf0[1].get('foo:baz:faz'), 'bbb' )

            self.nn( core.getTufoByProp('syn:model', 'a.foo.module') )
            self.nn( core.getTufoByProp('syn:type', 'foo:bar') )
            self.nn( core.getTufoByProp('syn:form', 'foo:baz') )
            self.nn( core.getTufoByProp('syn:prop', 'foo:baz:faz') )

        with s_cortex.openurl('ram://') as core:
            core.addDataModels([('a.foo.module',
                {
                    'prefix':'foo',
                    'version':201612201147,

                    'types':(
                        ('foo:bar',{'subof':'str:lwr'}),
                    ),

                    'forms':(
                        ('foo:baz',{'ptype':'foo:bar'},[
                            ('faz',{'ptype':'str:lwr'}),
                        ]),
                    ),
                })])

            tuf0 = core.formTufoByProp('foo:baz', 'AAA', faz='BBB')
            self.eq( tuf0[1].get('foo:baz'), 'aaa' )
            self.eq( tuf0[1].get('foo:baz:faz'), 'bbb' )

            self.nn( core.getTufoByProp('syn:model', 'a.foo.module') )
            self.nn( core.getTufoByProp('syn:type', 'foo:bar') )
            self.nn( core.getTufoByProp('syn:form', 'foo:baz') )
            self.nn( core.getTufoByProp('syn:prop', 'foo:baz:faz') )

    def test_cortex_splicepump(self):

        with s_cortex.openurl('ram://') as core0:

            with s_cortex.openurl('ram://') as core1:

                with core0.getSplicePump(core1):
                    core0.formTufoByProp('inet:fqdn','woot.com')

                self.nn( core1.getTufoByProp('inet:fqdn','woot.com') )

    def test_cortex_xact_deadlock(self):
        N = 100
        prop = 'testform'
        fd = tempfile.NamedTemporaryFile()
        dmon = s_daemon.Daemon()
        pool = s_threads.Pool(size=4, maxsize=8)
        wait = s_eventbus.Waiter(pool, 1, 'pool:work:fini')

        with s_cortex.openurl('sqlite:///%s' % fd.name) as core:

            def populate():
                for i in range(N):
                    #print('wrote %d tufos' % i)
                    core.formTufoByProp(prop, str(i), **{})

            dmon.share('core', core)
            link = dmon.listen('tcp://127.0.0.1:0/core')
            prox = s_telepath.openurl('tcp://127.0.0.1:%d/core' % link[1]['port'])

            pool.wrap(populate)()
            for i in range(N):
                tufos = prox.getTufosByProp(prop)
                #print('got %d tufos' % len(tufos))

            wait.wait()
            pool.fini()

    def test_coretex_logging(self):

        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('log:save',1)

            try:
                raise NoSuchPath(path='foo/bar')
            except NoSuchPath as exc:
                core.logCoreExc(exc,subsys='hehe')

            print(repr(core.getTufosByProp('syn:log')))

            tufo = core.getTufoByProp('syn:log:subsys',valu='hehe')

            self.eq( tufo[1].get('syn:log:subsys'), 'hehe' )
            self.eq( tufo[1].get('syn:log:exc'), 'synapse.exc.NoSuchPath' )
            self.eq( tufo[1].get('syn:log:info:path'), 'foo/bar' )

            self.nn( tufo[1].get('syn:log:time') )

            core.setConfOpt('log:level', logging.ERROR)

            try:
                raise NoSuchPath(path='foo/bar')
            except NoSuchPath as exc:
                core.logCoreExc(exc,subsys='haha', level=logging.WARNING)

            self.none( core.getTufoByProp('syn:log:subsys', valu='haha') )

    def test_cortex_seed(self):

        with s_cortex.openurl('ram:///') as core:

            def seedFooBar(prop,valu,**props):
                return core.formTufoByProp('inet:fqdn',valu,**props)

            core.addSeedCtor('foo:bar', seedFooBar)
            tufo = core.formTufoByProp('foo:bar','woot.com')
            self.eq( tufo[1].get('inet:fqdn'), 'woot.com' )

    def test_cortex_bytype(self):
        with s_cortex.openurl('ram:///') as core:
            core.formTufoByProp('inet:dns:a','woot.com/1.2.3.4')
            self.eq( len( core.eval('inet:ipv4*type="1.2.3.4"')), 2 )

    def test_cortex_seq(self):
        with s_cortex.openurl('ram:///') as core:

            core.formTufoByProp('syn:seq','foo')
            node = core.formTufoByProp('syn:seq','bar', nextvalu=10, width=4)

            self.eq( core.nextSeqValu('foo'), 'foo0' )
            self.eq( core.nextSeqValu('foo'), 'foo1' )

            self.eq( core.nextSeqValu('bar'), 'bar0010' )
            self.eq( core.nextSeqValu('bar'), 'bar0011' )

            self.raises(NoSuchSeq, core.nextSeqValu, 'lol' )

    def test_cortex_ingest(self):

        data = { 'results':{'fqdn':'woot.com','ipv4':'1.2.3.4'} }

        with s_cortex.openurl('ram:///') as core:

            idef = {
                'ingest':{
                    'forms':[
                        ['inet:fqdn',{'path':'results/fqdn'}]
                    ]
                }
            }

            core.setGestDef('test:whee', idef)

            self.nn( core.getTufoByProp('syn:ingest','test:whee') )
            self.none( core.getTufoByProp('inet:fqdn','woot.com') )
            self.none( core.getTufoByProp('inet:ipv4','1.2.3.4') )

            core.addGestData('test:whee', data)

            self.nn( core.getTufoByProp('inet:fqdn','woot.com') )
            self.none( core.getTufoByProp('inet:ipv4','1.2.3.4') )

            idef['ingest']['forms'].append( ('inet:ipv4',{'path':'results/ipv4'}) )

            core.setGestDef('test:whee', idef)
            core.addGestData('test:whee', data)

            self.nn( core.getTufoByProp('inet:fqdn','woot.com') )
            self.nn( core.getTufoByProp('inet:ipv4','1.2.3.4') )


    def test_cortex_tagform(self):

        with s_cortex.openurl('ram:///') as core:

            core.setConfOpt('enforce', 1)

            node = core.formTufoByProp('inet:fqdn', 'vertex.link')

            core.addTufoTag(node,'foo.bar')

            tdoc = core.getTufoByProp('syn:tagform', ('foo.bar','inet:fqdn'))

            self.nn(tdoc)

            self.eq( tdoc[1].get('syn:tagform:tag'), 'foo.bar' )
            self.eq( tdoc[1].get('syn:tagform:form'), 'inet:fqdn' )

            self.eq( tdoc[1].get('syn:tagform:doc'), '??' )
            self.eq( tdoc[1].get('syn:tagform:title'), '??' )

    def test_cortex_splices_errs(self):

        splices = [ ('newp:fake',{}) ]
        with s_cortex.openurl('ram:///') as core:
            core.on('splice',splices.append)
            core.formTufoByProp('inet:fqdn','vertex.link')

        with s_cortex.openurl('ram:///') as core:
            errs = core.splices( splices )
            self.eq( len(errs), 1 )
            self.eq( errs[0][0][0], 'newp:fake' )
            self.nn( core.getTufoByProp('inet:fqdn','vertex.link') )

    def test_cortex_norm_fail(self):
        with s_cortex.openurl('ram:///') as core:
            core.formTufoByProp('inet:netuser','vertex.link/visi')
            self.raises( BadTypeValu, core.eval, 'inet:netuser="totally invalid input"' )

    def test_cortex_local(self):
        splices = []
        with s_cortex.openurl('ram:///') as core:

            core.on('splice',splices.append)
            node = core.formTufoByProp('syn:splice',None)

            self.nn(node)
            self.nn(node[0])

        self.eq( len(splices), 0 )

    def test_cortex_module(self):

        with s_cortex.openurl('ram:///') as core:

            node = core.formTufoByProp('inet:ipv4','1.2.3.4')
            self.eq( node[1].get('inet:ipv4:asn'), -1 )

            mods = ( ('synapse.tests.test_cortex.CoreTestModule', {'foobar':True}), )

            core.setConfOpt('rev:model',1)
            core.setConfOpt('modules', mods)

            # directly access the module so we can confirm it gets fini()
            modu = core.coremods.get('synapse.tests.test_cortex.CoreTestModule')

            self.true( modu.foobar )

            self.nn( core.getTypeInst('test:type1') )
            self.nn( core.getTypeInst('test:type2') )
            self.none( core.getTypeInst('test:type3') )

            self.eq( core.getModlVers('test'), 1 )

            node = core.formTufoByProp('inet:ipv4','1.2.3.5')
            self.eq( node[1].get('inet:ipv4:asn'), 10 )

        self.true( modu.isfini )

    def test_cortex_modlvers(self):

        with s_cortex.openurl('ram:///') as core:

            self.eq( core.getModlVers('hehe'), -1 )

            core.setModlVers('hehe', 10)
            self.eq( core.getModlVers('hehe'), 10 )

            core.setModlVers('hehe', 20)
            self.eq( core.getModlVers('hehe'), 20 )

    def test_cortex_modlrevs(self):

        with s_cortex.openurl('ram:///') as core:

            def v0():
                core.formTufoByProp('inet:fqdn', 'foo.com')

            def v1():
                core.formTufoByProp('inet:fqdn', 'bar.com')

            def v2():
                core.formTufoByProp('inet:fqdn', 'baz.com')
                return 3

            def v3():
                core.formTufoByProp('inet:fqdn', 'newp.com')

            revs = [ (0,v0), (1,v1) ]

            core.setConfOpt('rev:model',0)
            self.raises(NoRevAllow, core.revModlVers, 'grok', revs )

            core.setConfOpt('rev:model',1)

            core.revModlVers('grok', revs)

            self.nn( core.getTufoByProp('inet:fqdn','foo.com') )
            self.nn( core.getTufoByProp('inet:fqdn','bar.com') )
            self.none( core.getTufoByProp('inet:fqdn','baz.com') )

            self.eq( core.getModlVers('grok'), 1 )

            core.delTufo( core.getTufoByProp('inet:fqdn','foo.com') )
            core.delTufo( core.getTufoByProp('inet:fqdn','bar.com') )

            revs.extend(((2,v2), (3,v3)))
            core.revModlVers('grok', revs)

            self.none(core.getTufoByProp('inet:fqdn','newp.com'))
            self.none(core.getTufoByProp('inet:fqdn','foo.com'))
            self.none(core.getTufoByProp('inet:fqdn','bar.com'))
            self.nn(core.getTufoByProp('inet:fqdn','baz.com'))

            self.eq( core.getModlVers('grok'), 3 )

    def test_cortex_isnew(self):
        with self.getTestDir() as dirn:
            path = os.path.join(dirn,'test.db')
            with s_cortex.openurl('sqlite:///%s' % (path,)) as core:
                self.true( core.isnew )

            with s_cortex.openurl('sqlite:///%s' % (path,)) as core:
                self.false( core.isnew )

    def test_cortex_notguidform(self):

        with s_cortex.openurl('ram:///') as core:

            self.raises( NotGuidForm, core.addTufoEvents, 'inet:fqdn', [{}])

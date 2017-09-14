from __future__ import absolute_import, unicode_literals

import os
import gzip
import hashlib
import binascii
import tempfile
import unittest

import synapse.link as s_link
import synapse.common as s_common
import synapse.compat as s_compat
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.cores.ram as s_cores_ram
import synapse.cores.lmdb as s_cores_lmdb
import synapse.cores.sqlite as s_cores_sqlite
import synapse.cores.common as s_cores_common
import synapse.cores.storage as s_cores_storage
import synapse.cores.postgres as s_cores_postgres

import synapse.lib.tags as s_tags
import synapse.lib.tufo as s_tufo
import synapse.lib.types as s_types
import synapse.lib.threads as s_threads

import synapse.models.syn as s_models_syn

from synapse.tests.common import *

class FakeType(s_types.IntType):
    pass

import synapse.lib.module as s_module

class CoreTestModule(s_module.CoreModule):

    def initCoreModule(self):

        def formipv4(form, valu, props, mesg):
            props['inet:ipv4:asn'] = 10

        self.onFormNode('inet:ipv4', formipv4)
        self.addConfDef('foobar', defval=False, asloc='foobar')

    @staticmethod
    def getBaseModels():
        return (
            ('test', {
                'types': (
                    ('test:type1', {'subof': 'str'}),
                    ('test:type2', {'subof': 'str'}),
                ),
            }),
        )

    @s_module.modelrev('test', 201707200101)
    def _testRev0(self):
        self.core.formTufoByProp('inet:fqdn', 'rev0.com')

    @s_module.modelrev('test', 201707210101)
    def _testRev1(self):
        self.core.formTufoByProp('inet:fqdn', 'rev1.com')

class CoreTestDataModelModuleV0(s_module.CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('foo:bar', {'subof': 'str', 'doc': 'A foo bar!'}),
            ),
            'forms': (
                ('foo:bar', {}, (

                )),
            ),
        }
        name = 'test'
        return ((name, modl),)

class CoreTestDataModelModuleV1(s_module.CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('foo:bar', {'subof': 'str', 'doc': 'A foo bar!'}),
            ),
            'forms': (
                ('foo:bar', {}, (
                    ('duck', {'defval': 'mallard', 'ptype': 'str', 'doc': 'Duck value!'}),
                )),
            ),
        }
        name = 'test'
        return ((name, modl),)

    @s_module.modelrev('test', 201707210101)
    def _testRev1(self):
        '''
        This revision adds the 'duck' property to our foo:bar nodes with its default value.
        '''
        rows = []
        tick = s_common.now()
        for iden, p, v, t in self.core.getRowsByProp('foo:bar'):
            rows.append((iden, 'foo:bar:duck', 'mallard', tick))
        self.core.addRows(rows)

##############################################################################
# Test Cortex's backed by different storage layers
#
# These are broken out to facilitate easy testing of issues which may be
# related to a specific storage layer implementation, so the entire CortexTest
# test suite does not have to be run at once.
#
# Additional tests may be added to the basic_core_expectations function to
# run them across all Cortex types.
##############################################################################

class CortexBaseTest(SynTest):
    def test_cortex_ram(self):
        with s_cortex.openurl('ram://') as core:
            self.true(hasattr(core.link, '__call__'))
            self.basic_core_expectations(core, 'ram')

    def test_cortex_sqlite3(self):
        with s_cortex.openurl('sqlite:///:memory:') as core:
            self.basic_core_expectations(core, 'sqlite')

    def test_cortex_lmdb(self):
        with self.getTestDir() as path:
            fn = 'test.lmdb'
            fp = os.path.join(path, fn)
            lmdb_url = 'lmdb:///%s' % fp

            with s_cortex.openurl(lmdb_url) as core:
                self.basic_core_expectations(core, 'lmdb')

            # Test load an existing db
            core = s_cortex.openurl(lmdb_url)
            self.false(core.isnew)

    def test_cortex_postgres(self):
        with self.getPgCore() as core:
            self.basic_core_expectations(core, 'postgres')

    def basic_core_expectations(self, core, storetype):
        '''
        Run basic tests against a Cortex instance.

        This should be a minimal test too ensure that a Storage and Cortex combination is working properly.

        Args:
            core (s_cores_common.Cortex): Cortex instance to test.
            storetype (str): String to check the getStoreType api against.
        '''
        self.eq(core.getStoreType(), storetype)
        self.runcore(core)
        self.runjson(core)
        self.runrange(core)
        self.runtufobydefault(core)
        self.runidens(core)
        self.rundsets(core)
        self.runsnaps(core)
        self.rundarks(core)
        self.runblob(core)
        self.runstore(core)

    def rundsets(self, core):
        tufo = core.formTufoByProp('lol:zonk', 1)
        core.addTufoDset(tufo, 'violet')

        self.eq(len(core.eval('dset(violet)')), 1)
        self.eq(len(core.getTufosByDset('violet')), 1)
        self.eq(core.getTufoDsets(tufo)[0][0], 'violet')

        core.delTufoDset(tufo, 'violet')

        self.eq(len(core.getTufosByDset('violet')), 0)
        self.eq(len(core.getTufoDsets(tufo)), 0)

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
                core.addTufoDset(tufo, 'zzzz')
                core.addTufoDark(tufo, 'animal', 'duck')

        #############################################

        answ = core.snapTufosByProp('lol:foo', valu=100)

        self.eq(answ.get('count'), 1)
        self.eq(answ.get('tufos')[0][1].get('lol:foo'), 100)

        #############################################

        answ = core.snapTufosByProp('lol:foo')
        snap = answ.get('snap')

        core.finiSnap(snap)
        self.none(core.getSnapNext(snap))

        #############################################

        answ = core.snapTufosByProp('lol:foo')

        res = []

        snap = answ.get('snap')
        tufs = answ.get('tufos')

        self.eq(answ.get('count'), 1500)

        while tufs:
            res.extend(tufs)
            tufs = core.getSnapNext(snap)

        self.eq(len(res), 1500)
        self.none(core.getSnapNext(snap))

        #############################################

        answ = core.snapTufosByDset('zzzz')

        res = []

        snap = answ.get('snap')
        tufs = answ.get('tufos')

        self.eq(answ.get('count'), 1500)

        while tufs:
            res.extend(tufs)
            tufs = core.getSnapNext(snap)

        self.eq(len(res), 1500)
        self.none(core.getSnapNext(snap))

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

        idens = [t0[0], t1[0], t2[0]]
        self.sorteq(core.getTufosByIdens(idens), [t0, t1, t2])

    def runcore(self, core):

        id1 = guid()
        id2 = guid()
        id3 = guid()
        id4 = guid()

        rows = [
            (id1, 'foo', 'bar', 30),
            (id1, 'baz', 'faz1', 30),
            (id1, 'gronk', 80, 30),

            (id2, 'foo', 'bar', 99),
            (id2, 'baz', 'faz2', 99),
            (id2, 'gronk', 90, 99),

            (id3, 'a', 'a', 99),
            (id3, 'b', 'b', 99),
            (id3, 'c', 90, 99),

            (id4, 'lolint', 80, 30),
            (id4, 'lolstr', 'hehe', 30),

        ]

        core.addRows(rows)

        tufo = core.getTufoByProp('baz', 'faz1')

        self.eq(len(core.getRowsByIdProp(id1, 'baz')), 1)
        self.eq(len(core.getRowsByIdProp(id1, 'baz', 'faz1')), 1)
        self.eq(len(core.getRowsByIdProp(id1, 'baz', 'faz2')), 0)
        self.eq(len(core.getRowsByIdProp(id1, 'gronk', 80)), 1)
        self.eq(len(core.getRowsByIdProp(id1, 'gronk', 8080)), 0)

        self.eq(tufo[0], id1)
        self.eq(tufo[1].get('foo'), 'bar')
        self.eq(tufo[1].get('baz'), 'faz1')
        self.eq(tufo[1].get('gronk'), 80)

        self.eq(core.getSizeByProp('foo:newp'), 0)
        self.eq(len(core.getRowsByProp('foo:newp')), 0)

        self.eq(core.getSizeByProp('foo'), 2)
        self.eq(core.getSizeByProp('baz', valu='faz1'), 1)
        self.eq(core.getSizeByProp('foo', mintime=80, maxtime=100), 1)

        self.eq(len(core.getRowsByProp('foo')), 2)
        self.eq(len(core.getRowsByProp('foo', valu='bar')), 2)

        self.eq(len(core.getRowsByProp('baz')), 2)
        self.eq(len(core.getRowsByProp('baz', valu='faz1')), 1)
        self.eq(len(core.getRowsByProp('baz', valu='faz2')), 1)

        self.eq(len(core.getRowsByProp('gronk', valu=90)), 1)

        self.eq(len(core.getRowsById(id1)), 3)

        self.eq(len(core.getJoinByProp('baz')), 6)
        self.eq(len(core.getJoinByProp('baz', valu='faz1')), 3)
        self.eq(len(core.getJoinByProp('baz', valu='faz2')), 3)

        self.eq(len(core.getRowsByProp('baz', mintime=0, maxtime=80)), 1)
        self.eq(len(core.getJoinByProp('baz', mintime=0, maxtime=80)), 3)

        self.eq(len(core.getRowsByProp('baz', limit=1)), 1)
        self.eq(len(core.getJoinByProp('baz', limit=1)), 3)

        core.setRowsByIdProp(id4, 'lolstr', 'haha')
        self.eq(len(core.getRowsByProp('lolstr', 'hehe')), 0)
        self.eq(len(core.getRowsByProp('lolstr', 'haha')), 1)

        core.setRowsByIdProp(id4, 'lolint', 99)
        self.eq(len(core.getRowsByProp('lolint', 80)), 0)
        self.eq(len(core.getRowsByProp('lolint', 99)), 1)

        # Run delRowsByIdProp without the valu set
        core.delRowsByIdProp(id4, 'lolint')
        core.delRowsByIdProp(id4, 'lolstr')

        self.eq(len(core.getRowsByProp('lolint')), 0)
        self.eq(len(core.getRowsByProp('lolstr')), 0)

        # Now run delRowsByIdProp with valu set
        core.setRowsByIdProp(id4, 'lolstr', 'haha')
        core.setRowsByIdProp(id4, 'lolint', 99)

        core.delRowsByIdProp(id4, 'lolint', 80)
        self.eq(len(core.getRowsByProp('lolint', 99)), 1)
        core.delRowsByIdProp(id4, 'lolint', 99)
        self.eq(len(core.getRowsByProp('lolint', 99)), 0)

        core.delRowsByIdProp(id4, 'lolstr', 'hehe')
        self.eq(len(core.getRowsByProp('lolstr', 'haha')), 1)
        core.delRowsByIdProp(id4, 'lolstr', 'haha')
        self.eq(len(core.getRowsByProp('lolstr', 'haha')), 0)

        core.delRowsById(id1)

        self.eq(len(core.getRowsById(id1)), 0)

        self.eq(len(core.getRowsByProp('b', valu='b')), 1)
        core.delRowsByProp('b', valu='b')
        self.eq(len(core.getRowsByProp('b', valu='b')), 0)

        self.eq(len(core.getRowsByProp('a', valu='a')), 1)
        core.delJoinByProp('c', valu=90)
        self.eq(len(core.getRowsByProp('a', valu='a')), 0)

        def formtufo(event):
            props = event[1].get('props')
            props['woot'] = 'woot'

        def formfqdn(event):
            fqdn = event[1].get('valu')
            event[1]['props']['sfx'] = fqdn.split('.')[-1]
            event[1]['props']['fqdn:inctest'] = 0

        core.on('node:form', formtufo)
        core.on('node:form', formfqdn, form='fqdn')

        tufo = core.formTufoByProp('fqdn', 'woot.com')

        self.eq(tufo[1].get('sfx'), 'com')
        self.eq(tufo[1].get('woot'), 'woot')

        self.eq(tufo[1].get('fqdn:inctest'), 0)

        tufo = core.incTufoProp(tufo, 'inctest')

        self.eq(tufo[1].get('fqdn:inctest'), 1)

        tufo = core.incTufoProp(tufo, 'inctest', incval=-1)

        self.eq(tufo[1].get('fqdn:inctest'), 0)

        bigstr = binascii.hexlify(os.urandom(80000)).decode('utf8')
        tufo = core.formTufoByProp('zoot:suit', 'foo', bar=bigstr)

        self.eq(tufo[1].get('zoot:suit:bar'), bigstr)
        self.eq(len(core.getTufosByProp('zoot:suit:bar', valu=bigstr)), 1)

        tufo = core.formTufoByProp('hehe', 'haha', foo='bar', baz='faz')
        self.eq(tufo[1].get('hehe'), 'haha')
        self.eq(tufo[1].get('hehe:foo'), 'bar')
        self.eq(tufo[1].get('hehe:baz'), 'faz')

        tufo = core.delTufoProp(tufo, 'foo')
        self.none(tufo[1].get('hehe:foo'))

        self.eq(len(core.eval('hehe:foo')), 0)
        self.eq(len(core.eval('hehe:baz')), 1)

        # Disable on() events registered in the test.
        core.off('node:form', formtufo)
        core.off('node:form', formfqdn)

    def runrange(self, core):

        rows = [
            (guid(), 'rg', 10, 99),
            (guid(), 'rg', 30, 99),
        ]

        core.addRows(rows)

        self.eq(core.getSizeBy('range', 'rg', (0, 20)), 1)
        self.eq(core.getRowsBy('range', 'rg', (0, 20))[0][2], 10)

        # range is inclusive of `min`, exclusive of `max`
        self.eq(core.getSizeBy('range', 'rg', (9, 11)), 1)
        self.eq(core.getSizeBy('range', 'rg', (10, 12)), 1)
        self.eq(core.getSizeBy('range', 'rg', (8, 10)), 0)

        self.eq(core.getSizeBy('ge', 'rg', 20), 1)
        self.eq(core.getRowsBy('ge', 'rg', 20)[0][2], 30)
        self.eq(len(core.getRowsBy('ge', 'rg', 10)), 2)
        self.eq(len(core.getRowsBy('ge', 'rg', 20)), 1)
        self.eq(len(core.getRowsBy('gt', 'rg', 31)), 0)
        self.eq(len(core.getRowsBy('gt', 'rg', 10)), 1)
        self.eq(len(core.getRowsBy('gt', 'rg', 9)), 2)
        self.eq(core.getRowsBy('gt', 'rg', 20)[0][2], 30)

        self.eq(core.getSizeBy('le', 'rg', 20), 1)
        self.eq(core.getRowsBy('le', 'rg', 20)[0][2], 10)
        self.eq(len(core.getRowsBy('le', 'rg', 10)), 1)
        self.eq(len(core.getRowsBy('le', 'rg', 30)), 2)
        self.eq(len(core.getRowsBy('lt', 'rg', 31)), 2)
        self.eq(len(core.getRowsBy('lt', 'rg', 11)), 1)
        self.eq(len(core.getRowsBy('lt', 'rg', 10)), 0)
        self.eq(len(core.getRowsBy('lt', 'rg', 9)), 0)
        self.eq(core.getRowsBy('lt', 'rg', 20)[0][2], 10)

        rows = [
            (guid(), 'rg', -42, 99),
            (guid(), 'rg', -1, 99),
            (guid(), 'rg', 0, 99),
            (guid(), 'rg', 1, 99),
            (guid(), 'rg', s_cores_lmdb.MIN_INT_VAL, 99),
            (guid(), 'rg', s_cores_lmdb.MAX_INT_VAL, 99),
        ]
        core.addRows(rows)
        self.eq(core.getSizeBy('range', 'rg', (s_cores_lmdb.MIN_INT_VAL + 1, -42)), 0)
        self.eq(core.getSizeBy('range', 'rg', (s_cores_lmdb.MIN_INT_VAL, -42)), 1)
        self.eq(core.getSizeBy('le', 'rg', -42), 2)
        # TODO: Need to implement lt for all the cores
        if 0:
            self.eq(core.getSizeBy('lt', 'rg', -42), 1)
        self.eq(core.getSizeBy('range', 'rg', (-42, 0)), 2)
        self.eq(core.getSizeBy('range', 'rg', (-1, 2)), 3)
        if 0:
            self.eq(core.getSizeBy('lt', 'rg', 0), 3)
        self.eq(core.getSizeBy('le', 'rg', 0), 4)
        # This is broken for RAM and SQLite
        if 0:
            self.eq(core.getSizeBy('ge', 'rg', -1, limit=3), 3)
        self.eq(core.getSizeBy('ge', 'rg', 30), 2)
        self.eq(core.getSizeBy('ge', 'rg', s_cores_lmdb.MAX_INT_VAL), 1)

    def runjson(self, core):

        thing = {
            'foo': {
                'bar': 10,
                'baz': 'faz',
                'blah': [99, 100],
                'gronk': [99, 100],
            },
            'x': 10,
            'y': 20,
        }

        core.addJsonItem('hehe', thing)

        thing['x'] = 40
        thing['x'] = 50

        core.addJsonItem('hehe', thing)

        for iden, item in core.getJsonItems('hehe:foo:bar', valu='faz'):

            self.eq(item['foo']['blah'][0], 99)

    def runblob(self, core):
        # Do we have default cortex blob values?
        self.true(core.hasBlobValu('syn:core:created'))

        kvs = (
            ('syn:meta', 1),
            ('foobar:thing', 'a string',),
            ('storage:sekrit', {'oh': 'my!', 'key': (1, 2)}),
            ('syn:bytes', b'0xdeadb33f'),
            ('knight:weight', 1.234),
            ('knight:saidni', False),
            ('knight:has:fleshwound', True),
            ('knight:has:current_queue', None),
        )

        # Basic store / retrieve tests
        for k, v in kvs:
            r = core.setBlobValu(k, v)
            self.eq(v, r)
            self.true(core.hasBlobValu(k))
        for k, v in kvs:
            self.eq(core.getBlobValu(k), v)

        # Missing a value
        self.false(core.hasBlobValu('syn:totallyfake'))

        # getkeys
        keys = core.getBlobKeys()
        self.isinstance(keys, list)
        self.isin('syn:core:created', keys)
        self.isin('syn:meta', keys)
        self.isin('knight:has:current_queue', keys)
        self.notin('totally-false', keys)

        # update a value and get the updated value back
        self.eq(core.getBlobValu('syn:meta'), 1)
        core.setBlobValu('syn:meta', 2)
        self.eq(core.getBlobValu('syn:meta'), 2)

        # msgpack'd output expected
        testv = [1, 2, 3]
        core.setBlobValu('test:list', testv)
        self.eq(core.getBlobValu('test:list'), tuple(testv))

        # Cannot store invalid items
        for obj in [object, set(testv), self.eq]:
            self.raises(TypeError, core.setBlobValu, 'test:bad', obj)

        # Ensure that trying to get a value which doesn't exist returns None.
        self.true(core.getBlobValu('test:bad') is None)
        # but does work is a default value is provided!
        self.eq(core.getBlobValu('test:bad', 123456), 123456)

        # Ensure we can delete items from the store
        self.eq(core.delBlobValu('test:list'), tuple(testv))
        self.false(core.hasBlobValu('test:list'))
        self.eq(core.getBlobValu('test:list'), None)
        # And deleting a value which doesn't exist raises a NoSuchName
        self.raises(NoSuchName, core.delBlobValu, 'test:deleteme')

    def runstore(self, core):
        '''
        Run generic storage layer tests on the core.store object
        '''

        # Ensure that genStoreRows() is implemented and generates boundary rows based on idens.
        rows = []
        tick = now()
        newrows = [
            ('00000000000000000000000000000000', 'tufo:form', 'inet:asn', tick),
            ('00000000000000000000000000000000', 'inet:asn', 1, tick),
            ('00000000000000000000000000000000', 'inet:asn:name', 'Lagavulin Internet Co.', tick),
            ('ffffffffffffffffffffffffffffffff', 'tufo:form', 'inet:asn', tick),
            ('ffffffffffffffffffffffffffffffff', 'inet:asn', 200, tick),
            ('ffffffffffffffffffffffffffffffff', 'inet:asn:name', 'Laphroaig Byte Minery Limited', tick)
        ]
        core.addRows(newrows)
        for _rows in core.store.genStoreRows(slicebytes=2):
            rows.extend(_rows)
        # A default cortex may have a few thousand rows in it - ensure we get at least 1000 rows here.
        self.gt(len(rows), 1000)
        self.isinstance(rows[0], tuple)
        self.eq(len(rows[0]), 4)
        # Sort rows by idens
        rows.sort(key=lambda x: x[0])
        bottom_rows = rows[:3]
        bottom_rows.sort(key=lambda x: x[1])
        self.eq(bottom_rows, [
            ('00000000000000000000000000000000', 'inet:asn', 1, tick),
            ('00000000000000000000000000000000', 'inet:asn:name', 'Lagavulin Internet Co.', tick),
            ('00000000000000000000000000000000', 'tufo:form', 'inet:asn', tick),
        ])
        top_rows = rows[-3:]
        top_rows.sort(key=lambda x: x[1])
        self.eq(top_rows, [
            ('ffffffffffffffffffffffffffffffff', 'inet:asn', 200, tick),
            ('ffffffffffffffffffffffffffffffff', 'inet:asn:name', 'Laphroaig Byte Minery Limited', tick),
            ('ffffffffffffffffffffffffffffffff', 'tufo:form', 'inet:asn', tick),
        ])

    def runtufobydefault(self, core):
        # Failures should be expected for unknown names
        self.raises(NoSuchGetBy, core.getTufosBy, 'clowns', 'inet:ipv4', 0x01020304)

        # BY IN
        fooa = core.formTufoByProp('default_foo', 'bar', p0=4)
        foob = core.formTufoByProp('default_foo', 'baz', p0=5)
        self.eq(len(core.getTufosBy('in', 'default_foo:p0', [4])), 1)

        fooc = core.formTufoByProp('default_foo', 'faz', p0=5)
        food = core.formTufoByProp('default_foo', 'haz', p0=6)
        fooe = core.formTufoByProp('default_foo', 'gaz', p0=7)
        self.eq(len(core.getTufosBy('in', 'default_foo:p0', [5])), 2)
        self.eq(len(core.getTufosBy('in', 'default_foo:p0', [4, 5])), 3)
        self.eq(len(core.getTufosBy('in', 'default_foo:p0', [4, 5, 6, 7], limit=4)), 4)
        self.eq(len(core.getTufosBy('in', 'default_foo:p0', [5], limit=1)), 1)
        self.eq(len(core.getTufosBy('in', 'default_foo:p0', [], limit=1)), 0)

        # By IN requiring type normalization
        foof = core.formTufoByProp('inet:ipv4', '10.2.3.6')

        self.eq(len(core.getTufosBy('in', 'inet:ipv4', [0x0a020306])), 1)
        self.eq(len(core.getTufosBy('in', 'inet:ipv4', [0x0a020305, 0x0a020307])), 0)
        self.eq(len(core.getTufosBy('in', 'inet:ipv4', [0x0a020305, 0x0a020306, 0x0a020307])), 1)
        self.eq(len(core.getTufosBy('in', 'inet:ipv4', ['10.2.3.6'])), 1)
        self.eq(len(core.getTufosBy('in', 'inet:ipv4', ['10.2.3.5', '10.2.3.7'])), 0)
        self.eq(len(core.getTufosBy('in', 'inet:ipv4', ['10.2.3.5', '10.2.3.6', '10.2.3.7'])), 1)

        # By IN using COMP type nodes
        nmb1 = core.formTufoByProp('inet:netmemb', '(vertex.link/pennywise,vertex.link/eldergods)')
        nmb2 = core.formTufoByProp('inet:netmemb', ('vertex.link/invisig0th', 'vertex.link/eldergods'))
        nmb3 = core.formTufoByProp('inet:netmemb', ['vertex.link/pennywise', 'vertex.link/clowns'])

        self.eq(len(core.getTufosBy('in', 'inet:netmemb', ['(vertex.link/pennywise,vertex.link/eldergods)'])), 1)
        self.eq(len(core.getTufosBy('in', 'inet:netmemb:group', ['vertex.link/eldergods'])), 2)
        self.eq(len(core.getTufosBy('in', 'inet:netmemb:group', ['vertex.link/eldergods'])), 2)
        self.eq(len(core.getTufosBy('in', 'inet:netmemb:group', ['vertex.link/eldergods', 'vertex.link/clowns'])), 3)
        self.eq(len(core.getTufosBy('in', 'inet:netmemb', ['(vertex.link/pennywise,vertex.link/eldergods)', ('vertex.link/pennywise', 'vertex.link/clowns')])), 2)

        # By LT/LE/GE/GT
        self.eq(len(core.getTufosBy('lt', 'default_foo:p0', 6)), 3)
        self.eq(len(core.getTufosBy('le', 'default_foo:p0', 6)), 4)
        self.eq(len(core.getTufosBy('le', 'default_foo:p0', 7)), 5)
        self.eq(len(core.getTufosBy('gt', 'default_foo:p0', 6)), 1)
        self.eq(len(core.getTufosBy('ge', 'default_foo:p0', 6)), 2)
        self.eq(len(core.getTufosBy('ge', 'default_foo:p0', 5)), 4)

        # By LT/LE/GE/GT requiring type normalization
        foog = core.formTufoByProp('inet:ipv4', '10.2.3.5')
        fooh = core.formTufoByProp('inet:ipv4', '10.2.3.7')
        fooi = core.formTufoByProp('inet:ipv4', '10.2.3.8')
        fooj = core.formTufoByProp('inet:ipv4', '10.2.3.9')

        self.eq(len(core.getTufosBy('lt', 'inet:ipv4', 0x0a020306)), 1)
        self.eq(len(core.getTufosBy('le', 'inet:ipv4', 0x0a020306)), 2)
        self.eq(len(core.getTufosBy('le', 'inet:ipv4', 0x0a020307)), 3)
        self.eq(len(core.getTufosBy('gt', 'inet:ipv4', 0x0a020306)), 3)
        self.eq(len(core.getTufosBy('ge', 'inet:ipv4', 0x0a020306)), 4)
        self.eq(len(core.getTufosBy('ge', 'inet:ipv4', 0x0a020305)), 5)

        self.eq(len(core.getTufosBy('lt', 'inet:ipv4', '10.2.3.6')), 1)
        self.eq(len(core.getTufosBy('le', 'inet:ipv4', '10.2.3.6')), 2)
        self.eq(len(core.getTufosBy('le', 'inet:ipv4', '10.2.3.7')), 3)
        self.eq(len(core.getTufosBy('gt', 'inet:ipv4', '10.2.3.6')), 3)
        self.eq(len(core.getTufosBy('ge', 'inet:ipv4', '10.2.3.6')), 4)
        self.eq(len(core.getTufosBy('ge', 'inet:ipv4', '10.2.3.5')), 5)

        # By RANGE
        # t0/t1 came in from the old test_cortex_ramtyperange test
        t0 = core.formTufoByProp('foo:bar', 10)
        t1 = core.formTufoByProp('foo:bar', 'baz')
        tufs = core.getTufosBy('range', 'foo:bar', (5, 15))
        self.eq(len(tufs), 1)
        self.eq(tufs[0][0], t0[0])
        # Do a range lift requiring prop normalization (using a built-in data type) to work
        t2 = core.formTufoByProp('inet:ipv4', '1.2.3.3')
        tufs = core.getTufosBy('range', 'inet:ipv4', (0x01020301, 0x01020309))
        self.eq(len(tufs), 1)
        self.eq(t2[0], tufs[0][0])
        tufs = core.getTufosBy('range', 'inet:ipv4', ('1.2.3.1', '1.2.3.9'))
        self.eq(len(tufs), 1)
        self.eq(t2[0], tufs[0][0])
        # RANGE test cleanup
        for tufo in [t0, t1, t2]:
            if tufo[1].get('.new'):
                core.delTufo(tufo)

        # By HAS - the valu is dropped by the _tufosByHas handler.
        self.eq(len(core.getTufosBy('has', 'default_foo:p0', valu=None)), 5)
        self.eq(len(core.getTufosBy('has', 'default_foo:p0', valu=5)), 5)
        self.eq(len(core.getTufosBy('has', 'default_foo', valu='foo')), 5)
        self.eq(len(core.getTufosBy('has', 'default_foo', valu='knight')), 5)

        self.eq(len(core.getTufosBy('has', 'inet:ipv4', valu=None)), 5)
        self.eq(len(core.getTufosBy('has', 'syn:tag', valu=None)), 0)

        # By TAG
        core.addTufoTag(fooa, 'color.white')
        core.addTufoTag(fooa, 'color.black')
        core.addTufoTag(foog, 'color.green')
        core.addTufoTag(foog, 'color.blue')
        core.addTufoTag(fooh, 'color.green')
        core.addTufoTag(fooh, 'color.red')
        core.addTufoTag(fooi, 'color.white')

        self.eq(len(core.getTufosBy('tag', 'inet:ipv4', 'color')), 3)
        self.eq(len(core.getTufosBy('tag', None, 'color')), 4)
        self.eq(len(core.getTufosBy('tag', 'default_foo', 'color.white')), 1)
        self.eq(len(core.getTufosBy('tag', 'default_foo', 'color.black')), 1)
        self.eq(len(core.getTufosBy('tag', 'inet:ipv4', 'color.green')), 2)
        self.eq(len(core.getTufosBy('tag', 'inet:ipv4', 'color.white')), 1)
        self.eq(len(core.getTufosBy('tag', None, 'color.white')), 2)

        # By EQ
        self.eq(len(core.getTufosBy('eq', 'default_foo', 'bar')), 1)
        self.eq(len(core.getTufosBy('eq', 'default_foo', 'blah')), 0)
        self.eq(len(core.getTufosBy('eq', 'default_foo:p0', 5)), 2)
        self.eq(len(core.getTufosBy('eq', 'inet:ipv4', 0x0a020306)), 1)
        self.eq(len(core.getTufosBy('eq', 'inet:ipv4', '10.2.3.6')), 1)
        self.eq(len(core.getTufosBy('eq', 'inet:ipv4:asn', -1)), 5)
        self.eq(len(core.getTufosBy('eq', 'inet:ipv4', 0x0)), 0)
        self.eq(len(core.getTufosBy('eq', 'inet:ipv4', '0.0.0.0')), 0)
        self.eq(len(core.getTufosBy('eq', 'inet:netmemb', '(vertex.link/pennywise,vertex.link/eldergods)')), 1)
        self.eq(len(core.getTufosBy('eq', 'inet:netmemb', ('vertex.link/invisig0th', 'vertex.link/eldergods'))), 1)

        # By TYPE - this requires data model introspection
        fook = core.formTufoByProp('inet:dns:a', 'derry.vertex.link/10.2.3.6')
        fool = core.formTufoByProp('inet:url', 'https://derry.vertex.link/clowntown.html', ipv4='10.2.3.6')
        # self.eq(len(core.getTufosBy('type', 'inet:ipv4', None)), 7)
        self.eq(len(core.getTufosBy('type', 'inet:ipv4', '10.2.3.6')), 3)
        self.eq(len(core.getTufosBy('type', 'inet:ipv4', 0x0a020306)), 3)

        # By TYPE using COMP nodes
        self.eq(len(core.getTufosBy('type', 'inet:netmemb', '(vertex.link/pennywise,vertex.link/eldergods)')), 1)
        self.eq(len(core.getTufosBy('type', 'inet:netmemb', ('vertex.link/invisig0th', 'vertex.link/eldergods'))), 1)
        self.eq(len(core.getTufosBy('type', 'inet:netuser', 'vertex.link/invisig0th')), 2)

        # BY CIDR
        tlib = s_types.TypeLib()

        ipint, _ = tlib.getTypeParse('inet:ipv4', '192.168.0.1')
        ipa = core.formTufoByProp('inet:ipv4', ipint)
        ipint, _ = tlib.getTypeParse('inet:ipv4', '192.168.255.254')
        ipa = core.formTufoByProp('inet:ipv4', ipint)

        ipint, _ = tlib.getTypeParse('inet:ipv4', '192.167.255.254')
        ipb = core.formTufoByProp('inet:ipv4', ipint)

        ips = ['10.2.1.%d' % d for d in range(1, 33)]
        for ip in ips:
            ipint, _ = tlib.getTypeParse('inet:ipv4', ip)
            ipc = core.formTufoByProp('inet:ipv4', ipint)

        # Validate the content we get from cidr lookups is correctly bounded
        nodes = core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.4/32')
        self.eq(len(nodes), 1)
        nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
        test_repr = core.getTypeRepr('inet:ipv4', nodes[0][1].get('inet:ipv4'))
        self.eq(test_repr, '10.2.1.4')

        nodes = core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.4/31')
        self.eq(len(nodes), 2)
        nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
        test_repr = core.getTypeRepr('inet:ipv4', nodes[0][1].get('inet:ipv4'))
        self.eq(test_repr, '10.2.1.4')
        test_repr = core.getTypeRepr('inet:ipv4', nodes[-1][1].get('inet:ipv4'))
        self.eq(test_repr, '10.2.1.5')

        # 10.2.1.1/30 is 10.2.1.0 -> 10.2.1.3 but we don't have 10.2.1.0 in the core
        nodes = core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.1/30')
        self.eq(len(nodes), 3)
        nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
        test_repr = core.getTypeRepr('inet:ipv4', nodes[0][1].get('inet:ipv4'))
        self.eq(test_repr, '10.2.1.1')
        test_repr = core.getTypeRepr('inet:ipv4', nodes[-1][1].get('inet:ipv4'))
        self.eq(test_repr, '10.2.1.3')

        # 10.2.1.2/30 is 10.2.1.0 -> 10.2.1.3 but we don't have 10.2.1.0 in the core
        nodes = core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.2/30')
        self.eq(len(nodes), 3)
        nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
        test_repr = core.getTypeRepr('inet:ipv4', nodes[0][1].get('inet:ipv4'))
        self.eq(test_repr, '10.2.1.1')
        test_repr = core.getTypeRepr('inet:ipv4', nodes[-1][1].get('inet:ipv4'))
        self.eq(test_repr, '10.2.1.3')

        # 10.2.1.1/29 is 10.2.1.0 -> 10.2.1.7 but we don't have 10.2.1.0 in the core
        nodes = core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.1/29')
        self.eq(len(nodes), 7)
        nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
        test_repr = core.getTypeRepr('inet:ipv4', nodes[0][1].get('inet:ipv4'))
        self.eq(test_repr, '10.2.1.1')
        test_repr = core.getTypeRepr('inet:ipv4', nodes[-1][1].get('inet:ipv4'))
        self.eq(test_repr, '10.2.1.7')

        # 10.2.1.8/29 is 10.2.1.8 -> 10.2.1.15
        nodes = core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.8/29')
        self.eq(len(nodes), 8)
        nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
        test_repr = core.getTypeRepr('inet:ipv4', nodes[0][1].get('inet:ipv4'))
        self.eq(test_repr, '10.2.1.8')
        test_repr = core.getTypeRepr('inet:ipv4', nodes[-1][1].get('inet:ipv4'))
        self.eq(test_repr, '10.2.1.15')

        # 10.2.1.1/28 is 10.2.1.0 -> 10.2.1.15 but we don't have 10.2.1.0 in the core
        nodes = core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.1/28')
        self.eq(len(nodes), 15)
        nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
        test_repr = core.getTypeRepr('inet:ipv4', nodes[0][1].get('inet:ipv4'))
        self.eq(test_repr, '10.2.1.1')
        test_repr = core.getTypeRepr('inet:ipv4', nodes[-1][1].get('inet:ipv4'))
        self.eq(test_repr, '10.2.1.15')

        # 192.168.0.0/16 is 192.168.0.0 -> 192.168.255.255 but we only have two nodes in this range
        nodes = core.getTufosBy('inet:cidr', 'inet:ipv4', '192.168.0.0/16')
        self.eq(len(nodes), 2)
        nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
        test_repr = core.getTypeRepr('inet:ipv4', nodes[0][1].get('inet:ipv4'))
        self.eq(test_repr, '192.168.0.1')
        test_repr = core.getTypeRepr('inet:ipv4', nodes[-1][1].get('inet:ipv4'))
        self.eq(test_repr, '192.168.255.254')

##############################################################################
# Test Cortex APIs which are not exercised in the CortexBaseTests.
#
# This is appropriate for things which are not going to be storage-layer
# dependent.
##############################################################################

class CortexTest(SynTest):

    def test_pg_encoding(self):
        with self.getPgCore() as core:
            res = core.store.select('SHOW SERVER_ENCODING')[0][0]
            self.eq(res, 'UTF8')

    def test_cortex_choptag(self):
        t0 = tuple(s_cortex.choptag('foo'))
        t1 = tuple(s_cortex.choptag('foo.bar'))
        t2 = tuple(s_cortex.choptag('foo.bar.baz'))

        self.eq(t0, ('foo',))
        self.eq(t1, ('foo', 'foo.bar'))
        self.eq(t2, ('foo', 'foo.bar', 'foo.bar.baz'))

    def test_cortex_tufo_tag(self):
        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo', 'bar', baz='faz')
        core.addTufoTag(foob, 'zip.zap')

        self.nn(foob[1].get('#zip'))
        self.nn(foob[1].get('#zip.zap'))

        self.eq(len(core.getTufosByTag('zip', form='foo')), 1)
        self.eq(len(core.getTufosByTag('zip.zap', form='foo')), 1)

        core.delTufoTag(foob, 'zip')

        self.none(foob[1].get('#zip'))
        self.none(foob[1].get('#zip.zap'))

        self.eq(len(core.getTufosByTag('zip', form='foo')), 0)
        self.eq(len(core.getTufosByTag('zip.zap', form='foo')), 0)

    def test_cortex_tufo_setprops(self):
        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo', 'bar', baz='faz')
        self.eq(foob[1].get('foo:baz'), 'faz')
        core.setTufoProps(foob, baz='zap')
        core.setTufoProps(foob, faz='zap')

        self.eq(len(core.getTufosByProp('foo:baz', valu='zap')), 1)
        self.eq(len(core.getTufosByProp('foo:faz', valu='zap')), 1)

        # Try using setprops with an built-in model which type subprops
        t0 = core.formTufoByProp('inet:netuser', 'vertex.link/pennywise')
        self.notin('inet:netuser:email', t0[1])
        props = {'email': 'pennywise@vertex.link'}
        core.setTufoProps(t0, **props)
        self.isin('inet:netuser:email', t0[1])
        t1 = core.getTufoByProp('inet:email', 'pennywise@vertex.link')
        self.nn(t1)

    def test_cortex_tufo_pop(self):
        with s_cortex.openurl('ram://') as core:
            foo0 = core.formTufoByProp('foo', 'bar', woot='faz')
            foo1 = core.formTufoByProp('foo', 'baz', woot='faz')

            self.eq(2, len(core.popTufosByProp('foo:woot', valu='faz')))
            self.eq(0, len(core.getTufosByProp('foo')))

    def test_cortex_tufo_setprop(self):
        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo', 'bar', baz='faz')
        self.eq(foob[1].get('foo:baz'), 'faz')

        core.setTufoProp(foob, 'baz', 'zap')

        self.eq(len(core.getTufosByProp('foo:baz', valu='zap')), 1)

    def test_cortex_tufo_list(self):

        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo', 'bar', baz='faz')

        core.addTufoList(foob, 'hehe', 1, 2, 3)

        self.nn(foob[1].get('tufo:list:hehe'))

        vals = sorted(core.getTufoList(foob, 'hehe'))

        self.eq(tuple(vals), (1, 2, 3))

        core.delTufoListValu(foob, 'hehe', 2)

        vals = core.getTufoList(foob, 'hehe')
        vals.sort()

        self.eq(tuple(vals), (1, 3))

        core.fini()

    def test_cortex_tufo_del(self):

        core = s_cortex.openurl('ram://')
        foob = core.formTufoByProp('foo', 'bar', baz='faz')

        self.nn(core.getTufoByProp('foo', valu='bar'))
        self.nn(core.getTufoByProp('foo:baz', valu='faz'))

        core.addTufoList(foob, 'blahs', 'blah1')
        core.addTufoList(foob, 'blahs', 'blah2')

        blahs = core.getTufoList(foob, 'blahs')

        self.eq(len(blahs), 2)

        core.delTufoByProp('foo', 'bar')

        self.none(core.getTufoByProp('foo', valu='bar'))
        self.none(core.getTufoByProp('foo:baz', valu='faz'))

        blahs = core.getTufoList(foob, 'blahs')
        self.eq(len(blahs), 0)

    def test_cortex_ramhost(self):
        core0 = s_cortex.openurl('ram:///foobar')
        core1 = s_cortex.openurl('ram:///foobar')
        self.eq(id(core0), id(core1))

        core0.fini()

        core0 = s_cortex.openurl('ram:///foobar')
        core1 = s_cortex.openurl('ram:///bazfaz')

        self.ne(id(core0), id(core1))

        core0.fini()
        core1.fini()

        core0 = s_cortex.openurl('ram:///')
        core1 = s_cortex.openurl('ram:///')

        self.ne(id(core0), id(core1))

        core0.fini()
        core1.fini()

        core0 = s_cortex.openurl('ram://')
        core1 = s_cortex.openurl('ram://')

        self.ne(id(core0), id(core1))

        core0.fini()
        core1.fini()

    def test_cortex_savefd(self):
        fd = s_compat.BytesIO()
        core0 = s_cortex.openurl('ram://', savefd=fd)

        self.true(core0.isnew)
        myfo0 = core0.myfo[0]

        created = core0.getBlobValu('syn:core:created')

        t0 = core0.formTufoByProp('foo', 'one', baz='faz')
        t1 = core0.formTufoByProp('foo', 'two', baz='faz')

        core0.setTufoProps(t0, baz='gronk')

        core0.delTufoByProp('foo', 'two')
        # Try persisting an blob store value
        core0.setBlobValu('syn:test', 1234)
        self.eq(core0.getBlobValu('syn:test'), 1234)
        core0.fini()

        fd.seek(0)

        core1 = s_cortex.openurl('ram://', savefd=fd)

        self.false(core1.isnew)
        myfo1 = core1.myfo[0]
        self.eq(myfo0, myfo1)

        self.none(core1.getTufoByProp('foo', 'two'))

        t0 = core1.getTufoByProp('foo', 'one')
        self.nn(t0)

        self.eq(t0[1].get('foo:baz'), 'gronk')

        # Retrieve the stored blob value
        self.eq(core1.getBlobValu('syn:test'), 1234)
        self.eq(core1.getBlobValu('syn:core:created'), created)

        # Persist a value which will be overwritten by a storage layer event
        core1.setBlobValu('syn:core:sqlite:version', -2)
        core1.hasBlobValu('syn:core:sqlite:version')

        fd.seek(0)
        time.sleep(1)

        core2 = s_cortex.openurl('sqlite:///:memory:', savefd=fd)

        self.false(core2.isnew)
        myfo2 = core2.myfo[0]
        self.eq(myfo0, myfo2)

        self.none(core2.getTufoByProp('foo', 'two'))

        t0 = core2.getTufoByProp('foo', 'one')
        self.nn(t0)

        self.eq(t0[1].get('foo:baz'), 'gronk')

        # blobstores persist across storage types with savefiles
        self.eq(core2.getBlobValu('syn:test'), 1234)
        self.eq(core2.getBlobValu('syn:core:created'), created)
        # Ensure that storage layer values may trump whatever was in a savefile
        self.ge(core2.getBlobValu('syn:core:sqlite:version'), 0)

        core2.fini()

        fd.seek(0)

        # Ensure the storage layer init events persisted across savefile reload
        core3 = s_cortex.openurl('ram://', savefd=fd)
        self.ge(core3.hasBlobValu('syn:core:sqlite:version'), 0)

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

        self.eq(core.getStatByProp('sum', 'foo:bar'), 53)
        self.eq(core.getStatByProp('count', 'foo:bar'), 7)

        self.eq(core.getStatByProp('min', 'foo:bar'), 1)
        self.eq(core.getStatByProp('max', 'foo:bar'), 21)

        self.eq(core.getStatByProp('mean', 'foo:bar'), 7.571428571428571)

        self.eq(core.getStatByProp('any', 'foo:bar'), 1)
        self.eq(core.getStatByProp('all', 'foo:bar'), 1)

        histo = core.getStatByProp('histo', 'foo:bar')
        self.eq(histo.get(13), 1)

        self.raises(NoSuchStat, core.getStatByProp, 'derp', 'inet:ipv4')

    def test_cortex_fire_set(self):

        core = s_cortex.openurl('ram://')

        tufo = core.formTufoByProp('foo', 'hehe', bar='lol')

        msgs = wait = core.waiter(1, 'node:prop:set')

        core.setTufoProps(tufo, bar='hah')

        evts = wait.wait(timeout=2)

        self.eq(evts[0][0], 'node:prop:set')
        self.eq(evts[0][1]['node'][0], tufo[0])
        self.eq(evts[0][1]['form'], 'foo')
        self.eq(evts[0][1]['valu'], 'hehe')
        self.eq(evts[0][1]['prop'], 'foo:bar')
        self.eq(evts[0][1]['newv'], 'hah')
        self.eq(evts[0][1]['oldv'], 'lol')

        core.fini()

    def test_cortex_tags(self):
        core = s_cortex.openurl('ram://')

        core.addType('foo', subof='str')
        core.addTufoForm('foo')

        hehe = core.formTufoByProp('foo', 'hehe')

        wait = core.waiter(2, 'node:tag:add')
        core.addTufoTag(hehe, 'lulz.rofl')
        wait.wait(timeout=2)

        wait = core.waiter(1, 'node:tag:add')
        core.addTufoTag(hehe, 'lulz.rofl.zebr')
        wait.wait(timeout=2)

        wait = self.getTestWait(core, 1, 'node:tag:add')
        core.addTufoTag(hehe, 'duck.quack.rofl')
        wait.wait(timeout=2)

        lulz = core.getTufoByProp('syn:tag', 'lulz')

        self.none(lulz[1].get('syn:tag:up'))
        self.eq(lulz[1].get('syn:tag:doc'), '')
        self.eq(lulz[1].get('syn:tag:title'), '')
        self.eq(lulz[1].get('syn:tag:depth'), 0)
        self.eq(lulz[1].get('syn:tag:base'), 'lulz')

        rofl = core.getTufoByProp('syn:tag', 'lulz.rofl')

        self.eq(rofl[1].get('syn:tag:doc'), '')
        self.eq(rofl[1].get('syn:tag:title'), '')
        self.eq(rofl[1].get('syn:tag:up'), 'lulz')

        self.eq(rofl[1].get('syn:tag:depth'), 1)
        self.eq(rofl[1].get('syn:tag:base'), 'rofl')

        tags = core.getTufosByProp('syn:tag:base', 'rofl')

        self.eq(len(tags), 2)

        wait = core.waiter(2, 'node:tag:del')
        core.delTufoTag(hehe, 'lulz.rofl')
        wait.wait(timeout=2)

        wait = core.waiter(1, 'node:tag:del')
        core.delTufo(lulz)
        wait.wait(timeout=2)
        # tag and subs should be wiped

        self.none(core.getTufoByProp('syn:tag', 'lulz'))
        self.none(core.getTufoByProp('syn:tag', 'lulz.rofl'))
        self.none(core.getTufoByProp('syn:tag', 'lulz.rofl.zebr'))

        self.eq(len(core.getTufosByTag('lulz', form='foo')), 0)
        self.eq(len(core.getTufosByTag('lulz.rofl', form='foo')), 0)
        self.eq(len(core.getTufosByTag('lulz.rofl.zebr', form='foo')), 0)

        # Now we need to retag a node, ensure that the tag is on the node and the syn:tag nodes exist again
        wait = core.waiter(1, 'node:tag:add')
        node = core.addTufoTag(hehe, 'lulz.rofl.zebr')
        wait.wait(timeout=2)

        self.isin('#lulz.rofl.zebr', node[1])
        self.nn(core.getTufoByProp('syn:tag', 'lulz'))
        self.nn(core.getTufoByProp('syn:tag', 'lulz.rofl'))
        self.nn(core.getTufoByProp('syn:tag', 'lulz.rofl.zebr'))

        # Recreate expected results from #320 to ensure
        # we're also doing the same via storm
        self.eq(len(core.eval('[inet:fqdn=w00t.com +#some.tag]')), 1)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0)')), 2)
        self.eq(len(core.eval('syn:tag=some')), 1)
        self.eq(len(core.eval('syn:tag=some.tag')), 1)
        self.eq(len(core.eval('syn:tag=some delnode(force=1)')), 0)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0)')), 0)
        self.eq(len(core.eval('inet:fqdn=w00t.com [ +#some.tag ]')), 1)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0)')), 2)
        self.eq(len(core.eval('syn:tag=some')), 1)
        self.eq(len(core.eval('syn:tag=some.tag')), 1)
        core.fini()

    def test_cortex_splices(self):
        core0 = s_cortex.openurl('ram://')
        core1 = s_cortex.openurl('ram://')

        # Form a tufo before we start sending splices
        tufo_before1 = core0.formTufoByProp('foo', 'before1')
        tufo_before2 = core0.formTufoByProp('foo', 'before2')
        core0.addTufoTag(tufo_before2, 'hoho')  # this will not be synced
        core0.on('splice', core1.splice)
        core0.delTufo(tufo_before1)

        # Add node by forming it
        tufo0 = core0.formTufoByProp('foo', 'bar', baz='faz')
        tufo1 = core1.getTufoByProp('foo', 'bar')
        self.eq(tufo1[1].get('foo'), 'bar')
        self.eq(tufo1[1].get('foo:baz'), 'faz')

        # Add tag to existing node
        tufo0 = core0.addTufoTag(tufo0, 'hehe')
        tufo1 = core1.getTufoByProp('foo', 'bar')
        self.true(s_tags.tufoHasTag(tufo1, 'hehe'))

        # Del tag from existing node
        core0.delTufoTag(tufo0, 'hehe')
        tufo1 = core1.getTufoByProp('foo', 'bar')
        self.false(s_tags.tufoHasTag(tufo1, 'hehe'))

        # Set prop on existing node
        core0.setTufoProp(tufo0, 'baz', 'lol')
        tufo1 = core1.getTufoByProp('foo', 'bar')
        self.eq(tufo1[1].get('foo:baz'), 'lol')

        # Del existing node
        core0.delTufo(tufo0)
        tufo1 = core1.getTufoByProp('foo', 'bar')
        self.none(tufo1)

        # Tag a node in first core, assert it was formed and tagged in second core
        core0.addTufoTag(tufo_before2, 'hehe')
        tufo1 = core1.getTufoByProp('foo', 'before2')
        self.true(s_tags.tufoHasTag(tufo1, 'hehe'))
        self.false(s_tags.tufoHasTag(tufo1, 'hoho'))
        core0.delTufoTag(tufo_before2, 'hehe')
        tufo1 = core1.getTufoByProp('foo', 'before2')
        self.false(s_tags.tufoHasTag(tufo1, 'hehe'))
        self.false(s_tags.tufoHasTag(tufo1, 'hoho'))

    def test_cortex_dict(self):
        core = s_cortex.openurl('ram://')
        core.addTufoForm('foo:bar', ptype='int')
        core.addTufoForm('baz:faz', ptype='int', defval=22)

        modl = core.getModelDict()
        self.eq(modl['forms'][-2:], ['foo:bar', 'baz:faz'])
        self.eq(modl['props']['foo:bar'][1]['ptype'], 'int')
        self.eq(modl['props']['baz:faz'][1]['defval'], 22)

        core.fini()

    def test_cortex_comp(self):
        core = s_cortex.openurl('ram://')

        fields = 'fqdn,inet:fqdn|ipv4,inet:ipv4|time,time:epoch'
        core.addType('foo:a', subof='comp', fields=fields)

        core.addTufoForm('foo:a', ptype='foo:a')
        core.addTufoProp('foo:a', 'fqdn', ptype='inet:fqdn')
        core.addTufoProp('foo:a', 'ipv4', ptype='inet:ipv4')
        core.addTufoProp('foo:a', 'time', ptype='time:epoch')

        arec = ('wOOt.com', 0x01020304, 0x00404040)

        dnsa = core.formTufoByProp('foo:a', arec)

        fval = guid(('woot.com', 0x01020304, 0x00404040))

        self.eq(dnsa[1].get('foo:a'), fval)
        self.eq(dnsa[1].get('foo:a:fqdn'), 'woot.com')
        self.eq(dnsa[1].get('foo:a:ipv4'), 0x01020304)
        self.eq(dnsa[1].get('foo:a:time'), 0x00404040)

        core.fini()

    def test_cortex_enforce(self):

        with s_cortex.openurl('ram://') as core:

            core.addTufoForm('foo:bar', ptype='inet:email')

            core.addTufoForm('foo:baz', ptype='inet:email')
            core.addTufoProp('foo:baz', 'fqdn', ptype='inet:fqdn')
            core.addTufoProp('foo:baz', 'haha', ptype='int')

            cofo = core.getTufoByProp('syn:core', 'self')
            self.nn(cofo)
            self.false(core.enforce)

            self.true(core.isSetPropOk('foo:bar:customprop'))
            self.true(core.isSetPropOk('foo:baz:fqdn'))
            self.true(core.isSetPropOk('foo:baz:haha'))
            self.true(core.isSetPropOk('foo:baz:duck'))

            core.setConfOpt('enforce', True)

            self.true(core.enforce)

            self.false(core.isSetPropOk('foo:bar:customprop'))
            self.true(core.isSetPropOk('foo:baz:fqdn'))
            self.true(core.isSetPropOk('foo:baz:haha'))
            self.false(core.isSetPropOk('foo:baz:duck'))

            tufo0 = core.formTufoByProp('foo:bar', 'foo@bar.com', hehe=10, haha=20)
            tufo1 = core.formTufoByProp('foo:baz', 'foo@bar.com', hehe=10, haha=20)

            # did it remove the non-declared props and subprops?
            self.none(tufo0[1].get('foo:bar:fqdn'))
            self.none(tufo0[1].get('foo:bar:hehe'))
            self.none(tufo0[1].get('foo:bar:haha'))

            # did it selectivly keep the declared props and subprops
            self.eq(tufo1[1].get('foo:baz:haha'), 20)
            self.eq(tufo1[1].get('foo:baz:fqdn'), 'bar.com')

            self.none(tufo1[1].get('foo:baz:hehe'))
            self.none(tufo1[1].get('foo:baz:user'))

            tufo0 = core.setTufoProps(tufo0, fqdn='visi.com', hehe=11)
            tufo1 = core.setTufoProps(tufo1, fqdn='visi.com', hehe=11, haha=21)

            self.none(tufo0[1].get('foo:bar:fqdn'))
            self.none(tufo0[1].get('foo:bar:hehe'))

            self.none(tufo1[1].get('foo:baz:hehe'))

            self.eq(tufo1[1].get('foo:baz:haha'), 21)
            self.eq(tufo1[1].get('foo:baz:fqdn'), 'visi.com')

            # Prevent the core from storing new types it does not know about
            self.raises(NoSuchForm, core.formTufoByProp, 'foo:duck', 'something')
            # Ensure that we cannot form nodes from Types alone - we must use forms
            self.raises(NoSuchForm, core.formTufoByProp, 'str', 'we all float down here')
            self.raises(NoSuchForm, core.formTufoByProp, 'inet:srv4', '1.2.3.4:8080')

    def test_cortex_minmax(self):

        with s_cortex.openurl('ram://') as core:

            core.addTufoForm('foo', ptype='str')
            core.addTufoProp('foo', 'min', ptype='int:min')
            core.addTufoProp('foo', 'max', ptype='int:max')

            props = {'min': 20, 'max': 20}
            tufo0 = core.formTufoByProp('foo', 'derp', **props)

            tufo0 = core.setTufoProp(tufo0, 'min', 30)
            self.eq(tufo0[1].get('foo:min'), 20)

            tufo0 = core.setTufoProp(tufo0, 'min', 10)
            self.eq(tufo0[1].get('foo:min'), 10)

            tufo0 = core.setTufoProp(tufo0, 'max', 10)
            self.eq(tufo0[1].get('foo:max'), 20)

            tufo0 = core.setTufoProp(tufo0, 'max', 30)
            self.eq(tufo0[1].get('foo:max'), 30)

    def test_cortex_minmax_epoch(self):

        with s_cortex.openurl('ram://') as core:

            core.addTufoForm('foo', ptype='str')
            core.addTufoProp('foo', 'min', ptype='time:epoch:min')
            core.addTufoProp('foo', 'max', ptype='time:epoch:max')

            props = {'min': 20, 'max': 20}
            tufo0 = core.formTufoByProp('foo', 'derp', **props)

            tufo0 = core.setTufoProp(tufo0, 'min', 30)
            self.eq(tufo0[1].get('foo:min'), 20)

            tufo0 = core.setTufoProp(tufo0, 'min', 10)
            self.eq(tufo0[1].get('foo:min'), 10)

            tufo0 = core.setTufoProp(tufo0, 'max', 10)
            self.eq(tufo0[1].get('foo:max'), 20)

            tufo0 = core.setTufoProp(tufo0, 'max', 30)
            self.eq(tufo0[1].get('foo:max'), 30)

    def test_cortex_by_type(self):

        with s_cortex.openurl('ram://') as core:

            core.addTufoForm('foo', ptype='str')
            core.addTufoProp('foo', 'min', ptype='time:epoch:min')
            core.addTufoProp('foo', 'max', ptype='time:epoch:max')

            core.addTufoForm('bar', ptype='str')
            core.addTufoProp('bar', 'min', ptype='time:epoch:min')
            core.addTufoProp('bar', 'max', ptype='time:epoch:max')

            core.addTufoForm('baz', ptype='str')
            core.addTufoProp('baz', 'min', ptype='time:epoch')
            core.addTufoProp('baz', 'max', ptype='time:epoch')

            props = {'min': 20, 'max': 20}

            tufo0 = core.formTufoByProp('foo', 'hurr', **props)
            tufo1 = core.formTufoByProp('bar', 'durr', **props)
            tufo2 = core.formTufoByProp('baz', 'durr', **props)

            want = tuple(sorted([tufo0[0], tufo1[0]]))

            res0 = core.getTufosByPropType('time:epoch:min', valu=20)
            self.eq(tuple(sorted([r[0] for r in res0])), want)

    def test_cortex_caching(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo', 'bar', asdf=2)
            tufo1 = core.formTufoByProp('foo', 'baz', asdf=2)

            answ0 = core.getTufosByProp('foo')
            answ1 = core.getTufosByProp('foo', valu='bar')

            self.eq(len(answ0), 2)
            self.eq(len(answ1), 1)

            self.eq(len(core.cache_fifo), 0)
            self.eq(len(core.cache_bykey), 0)
            self.eq(len(core.cache_byiden), 0)
            self.eq(len(core.cache_byprop), 0)

            core.setConfOpt('caching', 1)

            self.eq(core.caching, 1)

            answ0 = core.getTufosByProp('foo')

            self.eq(len(answ0), 2)
            self.eq(len(core.cache_fifo), 1)
            self.eq(len(core.cache_bykey), 1)
            self.eq(len(core.cache_byiden), 2)
            self.eq(len(core.cache_byprop), 1)

            tufo0 = core.formTufoByProp('foo', 'bar')
            tufo0 = core.addTufoTag(tufo0, 'hehe')

            self.eq(len(core.getTufosByTag('hehe', form='foo')), 1)
            core.delTufoTag(tufo0, 'hehe')

            tufo0 = core.getTufoByProp('foo', 'bar')
            self.noprop(tufo0[1], '#hehe')

    def test_cortex_caching_set(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo', 'bar', qwer=10)
            tufo1 = core.formTufoByProp('foo', 'baz', qwer=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)
            tufs3 = core.getTufosByProp('foo:qwer', valu=10, limit=2)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)
            self.eq(len(tufs2), 0)
            self.eq(len(tufs3), 2)

            # inspect the details of the cache data structures when setTufoProps
            # causes an addition or removal...
            self.nn(core.cache_bykey.get(('foo:qwer', 10, None)))
            self.nn(core.cache_bykey.get(('foo:qwer', None, None)))

            # we should have hit the unlimited query and not created a new cache hit...
            self.none(core.cache_bykey.get(('foo:qwer', 10, 2)))

            self.nn(core.cache_byiden.get(tufo0[0]))
            self.nn(core.cache_byiden.get(tufo1[0]))

            self.nn(core.cache_byprop.get(('foo:qwer', 10)))
            self.nn(core.cache_byprop.get(('foo:qwer', None)))

            core.setTufoProp(tufo0, 'qwer', 11)

            # the cached results should be updated
            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 1)
            self.eq(len(tufs2), 1)

            self.eq(tufs1[0][0], tufo1[0])
            self.eq(tufs2[0][0], tufo0[0])

    def test_cortex_caching_add_tufo(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo', 'bar', qwer=10)
            tufo1 = core.formTufoByProp('foo', 'baz', qwer=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)
            self.eq(len(tufs2), 0)

            tufo2 = core.formTufoByProp('foo', 'lol', qwer=10)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            self.eq(len(tufs0), 3)
            self.eq(len(tufs1), 3)
            self.eq(len(tufs2), 0)

    def test_cortex_caching_del_tufo(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo', 'bar', qwer=10)
            tufo1 = core.formTufoByProp('foo', 'baz', qwer=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            # Ensure we have cached the tufos we're deleting.
            self.nn(core.cache_byiden.get(tufo0[0]))
            self.nn(core.cache_byiden.get(tufo1[0]))

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)
            self.eq(len(tufs2), 0)

            # Delete an uncached object - here the tufo contents was cached
            # during lifts but the object itself is a different tuple id()
            core.delTufo(tufo0)

            tufs0 = core.getTufosByProp('foo:qwer')
            tufs1 = core.getTufosByProp('foo:qwer', valu=10)
            tufs2 = core.getTufosByProp('foo:qwer', valu=11)

            self.eq(len(tufs0), 1)
            self.eq(len(tufs1), 1)
            self.eq(len(tufs2), 0)

            # Delete an object which was actually cached during lift
            core.delTufo(tufs0[0])
            tufs0 = core.getTufosByProp('foo:qwer')
            self.eq(len(tufs0), 0)

    def test_cortex_caching_atlimit(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo', 'bar', qwer=10)
            tufo1 = core.formTufoByProp('foo', 'baz', qwer=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('foo:qwer', limit=2)
            tufs1 = core.getTufosByProp('foo:qwer', valu=10, limit=2)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)

            # when an entry is deleted from a cache result that was at it's limit
            # it should be fully invalidated

            core.delTufo(tufo0)

            self.none(core.cache_bykey.get(('foo:qwer', None, 2)))
            self.none(core.cache_bykey.get(('foo:qwer', 10, 2)))

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo', 'bar', qwer=10)
            tufo1 = core.formTufoByProp('foo', 'baz', qwer=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('foo:qwer', limit=2)
            tufs1 = core.getTufosByProp('foo:qwer', valu=10, limit=2)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)

            tufo2 = core.formTufoByProp('foo', 'baz', qwer=10)

            # when an entry is added from a cache result that was at it's limit
            # it should *not* be invalidated

            self.nn(core.cache_bykey.get(('foo:qwer', None, 2)))
            self.nn(core.cache_bykey.get(('foo:qwer', 10, 2)))

    def test_cortex_caching_under_limit(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo', 'bar', qwer=10)
            tufo1 = core.formTufoByProp('foo', 'baz', qwer=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('foo:qwer', limit=9)
            tufs1 = core.getTufosByProp('foo:qwer', valu=10, limit=9)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)

            # when an entry is deleted from a cache result that was under it's limit
            # it should be removed but *not* invalidated

            core.delTufo(tufo0)

            self.nn(core.cache_bykey.get(('foo:qwer', None, 9)))
            self.nn(core.cache_bykey.get(('foo:qwer', 10, 9)))

            tufs0 = core.getTufosByProp('foo:qwer', limit=9)
            tufs1 = core.getTufosByProp('foo:qwer', valu=10, limit=9)

            self.eq(len(tufs0), 1)
            self.eq(len(tufs1), 1)

    def test_cortex_caching_oneref(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo', 'bar')

            core.setConfOpt('caching', 1)

            ref0 = core.getTufosByProp('foo', valu='bar')[0]
            ref1 = core.getTufosByProp('foo', valu='bar')[0]

            self.eq(id(ref0), id(ref1))

    def test_cortex_caching_tags(self):

        with s_cortex.openurl('ram://') as core:

            tufo0 = core.formTufoByProp('foo', 'bar')
            tufo1 = core.formTufoByProp('foo', 'baz')

            core.addTufoTag(tufo0, 'hehe')

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByTag('hehe', form='foo')

            core.addTufoTag(tufo1, 'hehe')

            tufs1 = core.getTufosByTag('hehe', form='foo')
            self.eq(len(tufs1), 2)

            core.delTufoTag(tufo0, 'hehe')

            tufs2 = core.getTufosByTag('hehe', form='foo')
            self.eq(len(tufs2), 1)

    def test_cortex_caching_new(self):

        with s_cortex.openurl('ram://') as core:

            core.setConfOpt('caching', 1)

            tufo0 = core.formTufoByProp('foo', 'bar')
            tufo1 = core.formTufoByProp('foo', 'bar')

            self.true(tufo0[1].get('.new'))
            self.false(tufo1[1].get('.new'))

    def test_cortex_caching_disable(self):

        with s_cortex.openurl('ram://') as core:

            core.setConfOpt('caching', 1)

            tufo = core.formTufoByProp('foo', 'bar')

            self.nn(core.cache_byiden.get(tufo[0]))
            self.nn(core.cache_bykey.get(('foo', 'bar', 1)))
            self.nn(core.cache_byprop.get(('foo', 'bar')))
            self.eq(len(core.cache_fifo), 1)

            core.setConfOpt('caching', 0)

            self.none(core.cache_byiden.get(tufo[0]))
            self.none(core.cache_bykey.get(('foo', 'bar', 1)))
            self.none(core.cache_byprop.get(('foo', 'bar')))
            self.eq(len(core.cache_fifo), 0)

    def test_cortex_reqstor(self):
        with s_cortex.openurl('ram://') as core:
            self.raises(BadPropValu, core.formTufoByProp, 'foo:bar', True)

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

    def test_cortex_splicefd(self):
        with self.getTestDir() as path:
            with genfile(path, 'savefile.mpk') as fd:
                with s_cortex.openurl('ram://') as core:
                    core.addSpliceFd(fd)

                    tuf0 = core.formTufoByProp('inet:fqdn', 'woot.com')
                    tuf1 = core.formTufoByProp('inet:fqdn', 'newp.com')

                    core.addTufoTag(tuf0, 'foo.bar')
                    # this should leave the tag foo
                    core.delTufoTag(tuf0, 'foo.bar')

                    core.delTufo(tuf1)

                fd.seek(0)

                with s_cortex.openurl('ram://') as core:

                    core.eatSpliceFd(fd)

                    self.none(core.getTufoByProp('inet:fqdn', 'newp.com'))
                    self.nn(core.getTufoByProp('inet:fqdn', 'woot.com'))

                    self.eq(len(core.getTufosByTag('foo.bar', form='inet:fqdn')), 0)
                    self.eq(len(core.getTufosByTag('foo', form='inet:fqdn')), 1)

    def test_cortex_addmodel(self):

        with s_cortex.openurl('ram://') as core:

            core.addDataModel('a.foo.module',
                {
                    'prefix': 'foo',

                    'types': (
                        ('foo:bar', {'subof': 'str:lwr'}),
                    ),

                    'forms': (
                        ('foo:baz', {'ptype': 'foo:bar'}, [
                            ('faz', {'ptype': 'str:lwr'}),
                        ]),
                    ),
                })

            tyfo = core.getTufoByProp('syn:type', 'foo:bar')
            self.eq(tyfo[1].get('syn:type:subof'), 'str:lwr')

            fofo = core.getTufoByProp('syn:form', 'foo:baz')
            self.eq(fofo[1].get('syn:form:ptype'), 'foo:bar')

            pofo = core.getTufoByProp('syn:prop', 'foo:baz:faz')
            self.eq(pofo[1].get('syn:prop:ptype'), 'str:lwr')

            tuf0 = core.formTufoByProp('foo:baz', 'AAA', faz='BBB')
            self.eq(tuf0[1].get('foo:baz'), 'aaa')
            self.eq(tuf0[1].get('foo:baz:faz'), 'bbb')

            self.nn(core.getTufoByProp('syn:type', 'foo:bar'))
            self.nn(core.getTufoByProp('syn:form', 'foo:baz'))
            self.nn(core.getTufoByProp('syn:prop', 'foo:baz:faz'))

        with s_cortex.openurl('ram://') as core:
            core.addDataModels([('a.foo.module',
                {
                    'prefix': 'foo',
                    'version': 201612201147,

                    'types': (
                        ('foo:bar', {'subof': 'str:lwr'}),
                    ),

                    'forms': (
                        ('foo:baz', {'ptype': 'foo:bar'}, [
                            ('faz', {'ptype': 'str:lwr'}),
                        ]),
                    ),
                })])

            tuf0 = core.formTufoByProp('foo:baz', 'AAA', faz='BBB')
            self.eq(tuf0[1].get('foo:baz'), 'aaa')
            self.eq(tuf0[1].get('foo:baz:faz'), 'bbb')

            self.nn(core.getTufoByProp('syn:type', 'foo:bar'))
            self.nn(core.getTufoByProp('syn:form', 'foo:baz'))
            self.nn(core.getTufoByProp('syn:prop', 'foo:baz:faz'))

    def test_cortex_splicepump(self):

        with s_cortex.openurl('ram://') as core0:

            with s_cortex.openurl('ram://') as core1:

                with core0.getSplicePump(core1):
                    core0.formTufoByProp('inet:fqdn', 'woot.com')

                self.nn(core1.getTufoByProp('inet:fqdn', 'woot.com'))

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

    def test_cortex_seed(self):

        with s_cortex.openurl('ram:///') as core:

            def seedFooBar(prop, valu, **props):
                return core.formTufoByProp('inet:fqdn', valu, **props)

            core.addSeedCtor('foo:bar', seedFooBar)
            tufo = core.formTufoByProp('foo:bar', 'woot.com')
            self.eq(tufo[1].get('inet:fqdn'), 'woot.com')

    def test_cortex_bytype(self):
        with s_cortex.openurl('ram:///') as core:
            core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            self.eq(len(core.eval('inet:ipv4*type="1.2.3.4"')), 2)

    def test_cortex_seq(self):
        with s_cortex.openurl('ram:///') as core:

            core.formTufoByProp('syn:seq', 'foo')
            node = core.formTufoByProp('syn:seq', 'bar', nextvalu=10, width=4)

            self.eq(core.nextSeqValu('foo'), 'foo0')
            self.eq(core.nextSeqValu('foo'), 'foo1')

            self.eq(core.nextSeqValu('bar'), 'bar0010')
            self.eq(core.nextSeqValu('bar'), 'bar0011')

            self.raises(NoSuchSeq, core.nextSeqValu, 'lol')

    def test_cortex_ingest(self):

        data = {'results': {'fqdn': 'woot.com', 'ipv4': '1.2.3.4'}}

        with s_cortex.openurl('ram:///') as core:

            idef = {
                'ingest': {
                    'forms': [
                        ['inet:fqdn', {'path': 'results/fqdn'}]
                    ]
                }
            }

            core.setGestDef('test:whee', idef)

            self.nn(core.getTufoByProp('syn:ingest', 'test:whee'))
            self.none(core.getTufoByProp('inet:fqdn', 'woot.com'))
            self.none(core.getTufoByProp('inet:ipv4', '1.2.3.4'))

            core.addGestData('test:whee', data)

            self.nn(core.getTufoByProp('inet:fqdn', 'woot.com'))
            self.none(core.getTufoByProp('inet:ipv4', '1.2.3.4'))

            idef['ingest']['forms'].append(('inet:ipv4', {'path': 'results/ipv4'}))

            core.setGestDef('test:whee', idef)
            core.addGestData('test:whee', data)

            self.nn(core.getTufoByProp('inet:fqdn', 'woot.com'))
            self.nn(core.getTufoByProp('inet:ipv4', '1.2.3.4'))

    def test_cortex_tagform(self):

        with s_cortex.openurl('ram:///') as core:

            core.setConfOpt('enforce', 1)

            node = core.formTufoByProp('inet:fqdn', 'vertex.link')

            core.addTufoTag(node, 'foo.bar')

            tdoc = core.getTufoByProp('syn:tagform', ('foo.bar', 'inet:fqdn'))

            self.nn(tdoc)

            self.eq(tdoc[1].get('syn:tagform:tag'), 'foo.bar')
            self.eq(tdoc[1].get('syn:tagform:form'), 'inet:fqdn')

            self.eq(tdoc[1].get('syn:tagform:doc'), '??')
            self.eq(tdoc[1].get('syn:tagform:title'), '??')

    def test_cortex_splices_errs(self):

        splices = [('newp:fake', {})]
        with s_cortex.openurl('ram:///') as core:
            core.on('splice', splices.append)
            core.formTufoByProp('inet:fqdn', 'vertex.link')

        with s_cortex.openurl('ram:///') as core:
            errs = core.splices(splices)
            self.eq(len(errs), 1)
            self.eq(errs[0][0][0], 'newp:fake')
            self.nn(core.getTufoByProp('inet:fqdn', 'vertex.link'))

    def test_cortex_norm_fail(self):
        with s_cortex.openurl('ram:///') as core:
            core.formTufoByProp('inet:netuser', 'vertex.link/visi')
            self.raises(BadTypeValu, core.eval, 'inet:netuser="totally invalid input"')

    def test_cortex_local(self):
        splices = []
        with s_cortex.openurl('ram:///') as core:

            core.on('splice', splices.append)
            node = core.formTufoByProp('syn:splice', None)

            self.nn(node)
            self.nn(node[0])

        self.eq(len(splices), 0)

    def test_cortex_module(self):

        with s_cortex.openurl('ram:///') as core:

            node = core.formTufoByProp('inet:ipv4', '1.2.3.4')
            self.eq(node[1].get('inet:ipv4:asn'), -1)

            mods = (('synapse.tests.test_cortex.CoreTestModule', {'foobar': True}), )

            core.setConfOpt('rev:model', 1)
            core.setConfOpt('modules', mods)

            # directly access the module so we can confirm it gets fini()
            modu = core.coremods.get('synapse.tests.test_cortex.CoreTestModule')

            self.true(modu.foobar)

            self.nn(core.getTypeInst('test:type1'))
            self.nn(core.getTypeInst('test:type2'))
            self.none(core.getTypeInst('test:type3'))

            self.eq(core.getModlVers('test'), 201707210101)

            node = core.formTufoByProp('inet:ipv4', '1.2.3.5')
            self.eq(node[1].get('inet:ipv4:asn'), 10)

        self.true(modu.isfini)

    def test_cortex_modlvers(self):

        with s_cortex.openurl('ram:///') as core:

            self.eq(core.getModlVers('hehe'), -1)

            core.setModlVers('hehe', 10)
            self.eq(core.getModlVers('hehe'), 10)

            core.setModlVers('hehe', 20)
            self.eq(core.getModlVers('hehe'), 20)

    def test_cortex_modlrevs(self):

        with s_cortex.openurl('ram:///') as core:

            def v0():
                core.formTufoByProp('inet:fqdn', 'foo.com')

            def v1():
                core.formTufoByProp('inet:fqdn', 'bar.com')

            def v2():
                core.formTufoByProp('inet:fqdn', 'baz.com')

            core.setConfOpt('rev:model', 0)
            self.raises(NoRevAllow, core.revModlVers, 'grok', 0, v0)

            core.setConfOpt('rev:model', 1)

            self.true(core.revModlVers('grok', 0, v0))
            self.true(core.revModlVers('grok', 1, v1))

            self.nn(core.getTufoByProp('inet:fqdn', 'foo.com'))
            self.nn(core.getTufoByProp('inet:fqdn', 'bar.com'))
            self.none(core.getTufoByProp('inet:fqdn', 'baz.com'))

            self.eq(core.getModlVers('grok'), 1)

            core.setModlVers('grok', 2)
            core.revModlVers('grok', 2, v2)

            self.none(core.getTufoByProp('inet:fqdn', 'baz.com'))

    def test_cortex_isnew(self):
        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'test.db')
            with s_cortex.openurl('sqlite:///%s' % (path,)) as core:
                self.true(core.isnew)

            with s_cortex.openurl('sqlite:///%s' % (path,)) as core:
                self.false(core.isnew)

    def test_cortex_notguidform(self):

        with s_cortex.openurl('ram:///') as core:

            self.raises(NotGuidForm, core.addTufoEvents, 'inet:fqdn', [{}])

    def test_cortex_getbytag(self):

        with s_cortex.openurl('ram:///') as core:

            node0 = core.formTufoByProp('inet:user', 'visi')
            node1 = core.formTufoByProp('inet:ipv4', 0x01020304)

            core.addTufoTag(node0, 'foo')
            core.addTufoTag(node1, 'foo')

            self.eq(len(core.getTufosByTag('foo')), 2)
            self.eq(len(core.getTufosByTag('foo', form='inet:user')), 1)
            self.eq(len(core.getTufosByTag('foo', form='inet:ipv4')), 1)

    def test_cortex_tag_ival(self):

        splices = []
        with s_cortex.openurl('ram:///') as core:

            core.on('splice', splices.append)

            node = core.eval('[ inet:ipv4=1.2.3.4 +#foo.bar@20171217 ]')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), (1513468800000, 1513468800000))

            node = core.eval('[ inet:ipv4=1.2.3.4 +#foo.bar@2018 ]')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), (1513468800000, 1514764800000))

            node = core.eval('[ inet:ipv4=1.2.3.4 +#foo.bar@2011-2018 ]')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), (1293840000000, 1514764800000))

            node = core.eval('[ inet:ipv4=1.2.3.4 +#foo.bar@2012 ]')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), (1293840000000, 1514764800000))

            node = core.eval('[ inet:ipv4=1.2.3.4 +#foo.bar@2012-2013 ]')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), (1293840000000, 1514764800000))

        with s_cortex.openurl('ram:///') as core:
            core.splices(splices)
            core.on('splice', splices.append)
            node = core.eval('inet:ipv4=1.2.3.4')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), (1293840000000, 1514764800000))
            core.eval('inet:ipv4=1.2.3.4 [ -#foo.bar ]')

        with s_cortex.openurl('ram:///') as core:
            core.splices(splices)
            node = core.eval('inet:ipv4=1.2.3.4')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), None)

    def test_cortex_module_datamodel_migration(self):
        self.skipTest('Needs global model registry available')
        with s_cortex.openurl('ram:///') as core:

            # Enforce data model consistency.
            core.setConfOpt('enforce', 1)

            mods = (('synapse.tests.test_cortex.CoreTestDataModelModuleV0', {}),)
            core.setConfOpt('modules', mods)

            self.eq(core.getModlVers('test'), 0)
            self.nn(core.getTypeInst('foo:bar'))

            node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
            self.eq(node[1].get('tufo:form'), 'foo:bar')
            self.eq(node[1].get('foo:bar'), 'I am a bar foo.')
            self.none(node[1].get('foo:bar:duck'))

            # Test a module which will bump the module version and do a
            # migration as well as add a property type.
            mods = (('synapse.tests.test_cortex.CoreTestDataModelModuleV1', {}),)
            core.setConfOpt('modules', mods)

            self.eq(core.getModlVers('test'), 201707210101)

            node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
            self.eq(node[1].get('foo:bar:duck'), 'mallard')

            node = core.formTufoByProp('foo:bar', 'I am a robot', duck='mandarin')
            self.eq(node[1].get('foo:bar:duck'), 'mandarin')

    def test_cortex_splice_propdel(self):

        with s_cortex.openurl('ram:///') as core:
            tufo = core.formTufoByProp('hehe', 'haha', foo='bar', baz='faz')
            splice = ('splice', {'act': 'node:prop:del', 'form': 'hehe', 'valu': 'haha', 'prop': 'foo'})
            core.splice(splice)

            self.eq(len(core.eval('hehe:foo')), 0)
            self.eq(len(core.eval('hehe:baz')), 1)

    def test_cortex_module_datamodel_migration_persistent(self):

        # Show that while the data model itself is not persistent, we can run modelrev
        # functions to modify the DB (present in CoreTestDataModelModuleV1) when we have
        # a model change which may affect persistent data.

        with self.getTestDir() as dirn:

            # Test with a safefile based ram cortex
            savefile = os.path.join(dirn, 'savefile.mpk')

            with s_cortex.openurl('ram://', savefile=savefile) as core:
                # Enforce data model consistency.
                core.setConfOpt('enforce', 1)

                mods = (('synapse.tests.test_cortex.CoreTestDataModelModuleV0', {}),)
                core.setConfOpt('modules', mods)

                self.eq(core.getModlVers('test'), 0)
                self.nn(core.getTypeInst('foo:bar'))

                node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
                self.eq(node[1].get('tufo:form'), 'foo:bar')
                self.eq(node[1].get('foo:bar'), 'I am a bar foo.')
                self.none(node[1].get('foo:bar:duck'))

            with s_cortex.openurl('ram://', savefile=savefile) as core:
                self.eq(core.getModlVers('test'), 0)
                node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
                self.false(node[1].get('.new'))

                # Show the model is not yet present
                self.none(core.getTypeInst('foo:bar'))
                mods = (('synapse.tests.test_cortex.CoreTestDataModelModuleV1', {}),)
                core.setConfOpt('modules', mods)
                # Show the model is now loaded
                self.nn(core.getTypeInst('foo:bar'))

                self.eq(core.getModlVers('test'), 201707210101)
                self.true('foo:bar:duck' in core.props)

                node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
                self.eq(node[1].get('foo:bar:duck'), 'mallard')
                node2 = core.formTufoByProp('foo:bar', 'I am a robot', duck='mandarin')
                self.eq(node2[1].get('foo:bar:duck'), 'mandarin')

            # Test with a SQLite backed cortex
            path = os.path.join(dirn, 'testmodelmigration.db')

            with s_cortex.openurl('sqlite:///%s' % (path,)) as core:
                # Enforce data model consistency.
                core.setConfOpt('enforce', 1)

                mods = (('synapse.tests.test_cortex.CoreTestDataModelModuleV0', {}),)
                core.setConfOpt('modules', mods)

                self.eq(core.getModlVers('test'), 0)
                self.nn(core.getTypeInst('foo:bar'))

                node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
                self.eq(node[1].get('tufo:form'), 'foo:bar')
                self.eq(node[1].get('foo:bar'), 'I am a bar foo.')
                self.none(node[1].get('foo:bar:duck'))

            with s_cortex.openurl('sqlite:///%s' % (path,)) as core:
                self.eq(core.getModlVers('test'), 0)
                node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
                self.false(node[1].get('.new'))

                # Show the model is not yet present
                self.none(core.getTypeInst('foo:bar'))
                mods = (('synapse.tests.test_cortex.CoreTestDataModelModuleV1', {}),)
                core.setConfOpt('modules', mods)
                # Show the model is now loaded
                self.nn(core.getTypeInst('foo:bar'))

                self.eq(core.getModlVers('test'), 201707210101)
                self.true('foo:bar:duck' in core.props)

                node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
                self.eq(node[1].get('foo:bar:duck'), 'mallard')
                node2 = core.formTufoByProp('foo:bar', 'I am a robot', duck='mandarin')
                self.eq(node2[1].get('foo:bar:duck'), 'mandarin')

    def test_cortex_lift_by_cidr(self):

        with s_cortex.openurl('ram:///') as core:
            # Add a bunch of nodes
            for n in range(0, 256):
                r = core.formTufoByProp('inet:ipv4', '192.168.1.{}'.format(n))
                r = core.formTufoByProp('inet:ipv4', '192.168.2.{}'.format(n))
                r = core.formTufoByProp('inet:ipv4', '192.168.200.{}'.format(n))

            # Confirm we have nodes
            self.eq(len(core.eval('inet:ipv4="192.168.1.0"')), 1)
            self.eq(len(core.eval('inet:ipv4="192.168.1.255"')), 1)
            self.eq(len(core.eval('inet:ipv4="192.168.2.0"')), 1)
            self.eq(len(core.eval('inet:ipv4="192.168.2.255"')), 1)
            self.eq(len(core.eval('inet:ipv4="192.168.200.0"')), 1)

            # Do cidr lifts
            nodes = core.eval('inet:ipv4*inet:cidr=192.168.2.0/24')
            nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
            self.eq(len(nodes), 256)
            test_repr = core.getTypeRepr('inet:ipv4', nodes[10][1].get('inet:ipv4'))
            self.eq(test_repr, '192.168.2.10')
            test_repr = core.getTypeRepr('inet:ipv4', nodes[0][1].get('inet:ipv4'))
            self.eq(test_repr, '192.168.2.0')
            test_repr = core.getTypeRepr('inet:ipv4', nodes[-1][1].get('inet:ipv4'))
            self.eq(test_repr, '192.168.2.255')

            nodes = core.eval('inet:ipv4*inet:cidr=192.168.200.0/24')
            self.eq(len(nodes), 256)
            test_repr = core.getTypeRepr('inet:ipv4', nodes[10][1].get('inet:ipv4'))
            self.true(test_repr.startswith('192.168.200.'))

            nodes = core.eval('inet:ipv4*inet:cidr=192.168.1.0/24')
            self.eq(len(nodes), 256)
            nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
            test_repr = core.getTypeRepr('inet:ipv4', nodes[10][1].get('inet:ipv4'))
            self.eq(test_repr, '192.168.1.10')

            # Try a complicated /24
            nodes = core.eval('inet:ipv4*inet:cidr=192.168.1.1/24')
            self.eq(len(nodes), 256)
            nodes.sort(key=lambda x: x[1].get('inet:ipv4'))

            test_repr = core.getTypeRepr('inet:ipv4', nodes[0][1].get('inet:ipv4'))
            self.eq(test_repr, '192.168.1.0')
            test_repr = core.getTypeRepr('inet:ipv4', nodes[255][1].get('inet:ipv4'))
            self.eq(test_repr, '192.168.1.255')

            # Try a /23
            nodes = core.eval('inet:ipv4*inet:cidr=192.168.0.0/23')
            self.eq(len(nodes), 256)
            test_repr = core.getTypeRepr('inet:ipv4', nodes[10][1].get('inet:ipv4'))
            self.true(test_repr.startswith('192.168.1.'))

            # Try a /25
            nodes = core.eval('inet:ipv4*inet:cidr=192.168.1.0/25')
            nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
            self.eq(len(nodes), 128)
            test_repr = core.getTypeRepr('inet:ipv4', nodes[-1][1].get('inet:ipv4'))
            self.true(test_repr.startswith('192.168.1.127'))

            # Try a /25
            nodes = core.eval('inet:ipv4*inet:cidr=192.168.1.128/25')
            nodes.sort(key=lambda x: x[1].get('inet:ipv4'))
            self.eq(len(nodes), 128)
            test_repr = core.getTypeRepr('inet:ipv4', nodes[0][1].get('inet:ipv4'))
            self.true(test_repr.startswith('192.168.1.128'))

            # Try a /16
            nodes = core.eval('inet:ipv4*inet:cidr=192.168.0.0/16')
            self.eq(len(nodes), 256 * 3)

    def test_cortex_formtufosbyprops(self):

        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)
            with s_daemon.Daemon() as dmon:
                dmon.share('core', core)
                link = dmon.listen('tcp://127.0.0.1:0/core')
                with s_cortex.openurl('tcp://127.0.0.1:%d/core' % link[1]['port']) as prox:
                    items = (
                        ('inet:fqdn', 'vertex.link', {'zone': 1}),
                        ('inet:url', 'bad', {}),
                        ('bad', 'good', {'wat': 3}),
                    )
                    actual = prox.formTufosByProps(items)

                    self.isinstance(actual, tuple)
                    self.eq(len(actual), 3)

                    self.isinstance(actual[0], tuple)
                    self.eq(len(actual[0]), 2)
                    self.eq(actual[0][1]['tufo:form'], 'inet:fqdn')
                    self.eq(actual[0][1]['inet:fqdn'], 'vertex.link')
                    self.eq(actual[0][1]['inet:fqdn:zone'], 1)

                    self.isinstance(actual[1], tuple)
                    self.eq(actual[1][0], None)
                    self.eq(actual[1][1]['tufo:form'], 'syn:err')
                    self.eq(actual[1][1]['syn:err'], 'BadTypeValu')
                    for s in ['BadTypeValu', 'name=', 'inet:url', 'valu=', 'bad']:
                        self.isin(s, actual[1][1]['syn:err:errmsg'])

                    self.isinstance(actual[2], tuple)
                    self.eq(actual[2][0], None)
                    self.eq(actual[2][1]['tufo:form'], 'syn:err')
                    self.eq(actual[2][1]['syn:err'], 'NoSuchForm')
                    for s in ['NoSuchForm', 'name=', 'bad']:
                        self.isin(s, actual[2][1]['syn:err:errmsg'])

    def test_cortex_reqprops(self):

        with s_cortex.openurl('ram:///') as core:

            core.addDataModel('woot', {
                'forms': (
                    ('hehe:haha', {'ptype': 'str'}, (
                        ('hoho', {'ptype': 'str', 'req': 1}),
                    )),
                ),
            })

            core.setConfOpt('enforce', 0)

            # Required prop not provided but enforce=0.
            t0 = core.formTufoByProp('hehe:haha', 'lulz')
            self.nn(t0)

            # enable enforce
            core.setConfOpt('enforce', 1)

            # fails without required prop present
            self.raises(PropNotFound, core.formTufoByProp, 'hehe:haha', 'rofl')

            # Works with required prop present
            t0 = core.formTufoByProp('hehe:haha', 'rofl', hoho='wonk')
            self.nn(t0)

    def test_cortex_runts(self):

        with s_cortex.openurl('ram:///') as core:

            core.addDataModel('hehe', {'forms': (
                ('hehe:haha', {'ptype': 'str'}, (
                    ('hoho', {'ptype': 'int'}),
                )),
            )})

            core.addRuntNode('hehe:haha', 'woot', hoho=20, lulz='rofl')

            # test that nothing hit the storage layer...
            self.eq(len(core.getRowsByProp('hehe:haha')), 0)

            node = core.getTufoByProp('hehe:haha', 'woot')
            self.nn(node)

            # check that it is ephemeral
            self.none(node[0])

            # check that all props made it in
            self.eq(node[1].get('hehe:haha:hoho'), 20)
            self.eq(node[1].get('hehe:haha:lulz'), 'rofl')

            # check that only model'd props are indexed
            self.nn(core.getTufoByProp('hehe:haha:hoho', 20))
            self.none(core.getTufoByProp('hehe:haha:lulz', 'rofl'))

class StorageTest(SynTest):

    def test_nonexist_ctor(self):
        self.raises(NoSuchImpl, s_cortex.openstore, 'delaylinememory:///')

    def test_storage_xact_spliced(self):

        # Ensure that spliced events don't get fired through a
        # StoreXct without a Cortex
        eventd = {}

        def foo(event):
            eventd[event[0]] = eventd.get(event[0], 0) + 1

        with s_cortex.openstore('ram:///') as store:
            store.on('foo', foo)
            store.on('splice', foo)
            with store.getCoreXact() as xact:
                xact.fire('foo', key='valu')
                xact.fire('bar', key='valu')
                xact.spliced('foo', key='valu')
        self.eq(eventd, {'foo': 1})

    def test_storage_confopts(self):
        conf = {'rev:storage': 0}

        with s_cortex.openstore('ram:///', storconf=conf) as stor:
            self.eq(stor.getConfOpt('rev:storage'), 0)

    def test_storage_rowmanipulation(self):
        with self.getTestDir() as temp:
            finl = os.path.join(temp, 'test.db')
            url = 'sqlite:///%s' % finl

            with s_cortex.openstore(url) as store:
                self.isinstance(store, s_cores_storage.Storage)
                # Add rows directly to the storage object
                rows = []
                tick = s_common.now()
                rows.append(('1234', 'foo:bar:baz', 'yes', tick))
                rows.append(('1234', 'tufo:form', 'foo:bar', tick))
                store.addRows(rows)

            # Retrieve the node via the Cortex interface
            with s_cortex.openurl(url) as core:
                node = core.getTufoByIden('1234')
                self.nn(node)
                self.eq(node[1].get('tufo:form'), 'foo:bar')
                self.eq(node[1].get('foo:bar:baz'), 'yes')

    def test_storage_row_manipulation(self):
        # Add rows to an new cortex db
        with self.getTestDir() as temp:
            finl = os.path.join(temp, 'test.db')
            url = 'sqlite:///%s' % finl

            with s_cortex.openstore(url) as store:
                self.isinstance(store, s_cores_storage.Storage)
                # Add rows directly to the storage object
                rows = []
                tick = s_common.now()
                rows.append(('1234', 'foo:bar:baz', 'yes', tick))
                rows.append(('1234', 'tufo:form', 'foo:bar', tick))
                store.addRows(rows)

            # Retrieve the node via the Cortex interface
            with s_cortex.openurl(url) as core:
                node = core.getTufoByIden('1234')
                self.nn(node)
                self.eq(node[1].get('tufo:form'), 'foo:bar')
                self.eq(node[1].get('foo:bar:baz'), 'yes')

    def test_storage_handler_misses(self):
        with s_cortex.openstore('ram:///') as store:
            self.raises(NoSuchGetBy, store.getJoinsBy, 'clowns', 'inet:ipv4', 0x01020304)
            self.raises(NoSuchGetBy, store.reqJoinByMeth, 'clowns')
            self.raises(NoSuchGetBy, store.reqRowsByMeth, 'clowns')
            self.raises(NoSuchGetBy, store.reqSizeByMeth, 'clowns')

    def test_storage_handler_defaults(self):
        with s_cortex.openstore('ram:///') as store:
            self.nn(store.reqJoinByMeth('range'))
            self.nn(store.reqRowsByMeth('range'))
            self.nn(store.reqSizeByMeth('range'))

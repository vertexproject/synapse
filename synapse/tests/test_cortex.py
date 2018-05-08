import io
import os
import gzip
import hashlib
import binascii
import tempfile
import unittest

import synapse.axon as s_axon
import synapse.link as s_link
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.cores.lmdb as s_cores_lmdb
import synapse.cores.common as s_cores_common
import synapse.cores.storage as s_cores_storage

import synapse.lib.iq as s_iq
import synapse.lib.auth as s_auth
import synapse.lib.tags as s_tags
import synapse.lib.tufo as s_tufo
import synapse.lib.types as s_types
import synapse.lib.threads as s_threads
import synapse.lib.version as s_version

from synapse.tests.common import *

class FakeType(s_types.IntType):
    pass

import synapse.lib.module as s_module

class CoreTestModule(s_module.CoreModule):

    def initCoreModule(self):

        self.added = []
        self.deled = []

        def formipv4(form, valu, props, mesg):
            props['inet:ipv4:asn'] = 10

        self.onFormNode('inet:ipv4', formipv4)
        self.addConfDef('foobar', defval=False, asloc='foobar')

        self.onNodeAdd(self.added.append, form='ou:org')
        self.onNodeDel(self.deled.append, form='ou:org')

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
            lmdb_url = 'lmdb:///%s?lmdb:mapsize=%d' % (fp, s_iq.TEST_MAP_SIZE)

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
        self.addTstForms(core)
        self.runcore(core)
        self.runjson(core)
        self.runrange(core)
        self.runtufobydefault(core)
        self.runidens(core)
        self.rundsets(core)
        self.runsnaps(core)
        self.rundarks(core)
        self.runblob(core)
        # runstore should be run last as it may do destructive actions to data in the Cortex.
        self.runstore(core)

    def rundsets(self, core):
        tufo = core.formTufoByProp('intform', 1)
        core.addTufoDset(tufo, 'violet')

        self.eq(len(core.eval('dset(violet)')), 1)
        self.eq(len(core.getTufosByDset('violet')), 1)
        self.eq(core.getTufoDsets(tufo)[0][0], 'violet')

        core.delTufoDset(tufo, 'violet')

        self.eq(len(core.getTufosByDset('violet')), 0)
        self.eq(len(core.getTufoDsets(tufo)), 0)

    def rundarks(self, core):

        tufo = core.formTufoByProp('intform', 1)
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
                tufo = core.formTufoByProp('intform', i)
                core.addTufoDset(tufo, 'zzzz')
                core.addTufoDark(tufo, 'animal', 'duck')

        #############################################

        answ = core.snapTufosByProp('intform', valu=100)

        self.eq(answ.get('count'), 1)
        self.eq(answ.get('tufos')[0][1].get('intform'), 100)

        #############################################

        answ = core.snapTufosByProp('intform')
        snap = answ.get('snap')

        core.finiSnap(snap)
        self.none(core.getSnapNext(snap))

        #############################################

        answ = core.snapTufosByProp('intform')

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

        # Cleanup dark properties added during this test
        for i in range(1500):
            tufo = core.getTufoByProp('intform', i)
            core.delTufoDark(tufo, 'animal', 'duck')

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
        # Expect an empty list of idens to return an empty list.
        self.eq(core.getTufosByIdens([]), [])

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
            event[1]['props']['inet:fqdn:sfx'] = fqdn.split('.')[-1]
            event[1]['props']['inet:fqdn:inctest'] = 0

        core.on('node:form', formtufo)
        core.on('node:form', formfqdn, form='inet:fqdn')

        tufo = core.formTufoByProp('inet:fqdn', 'woot.com')

        self.eq(tufo[1].get('inet:fqdn:sfx'), 'com')
        self.eq(tufo[1].get('woot'), 'woot')

        self.eq(tufo[1].get('inet:fqdn:inctest'), 0)

        tufo = core.incTufoProp(tufo, 'inctest')

        self.eq(tufo[1].get('inet:fqdn:inctest'), 1)

        tufo = core.incTufoProp(tufo, 'inctest', incval=-1)

        self.eq(tufo[1].get('inet:fqdn:inctest'), 0)

        bigstr = binascii.hexlify(os.urandom(80000)).decode('utf8')
        tufo = core.formTufoByProp('strform', 'foo', bar=bigstr)

        self.eq(tufo[1].get('strform'), 'foo')
        self.eq(tufo[1].get('strform:bar'), bigstr)

        self.eq(len(core.getTufosByProp('strform:bar', valu=bigstr)), 1)

        tufo = core.formTufoByProp('strform', 'haha', foo='bar', bar='faz')
        self.eq(tufo[1].get('strform'), 'haha')
        self.eq(tufo[1].get('strform:foo'), 'bar')
        self.eq(tufo[1].get('strform:bar'), 'faz')

        tufo = core.delTufoProp(tufo, 'foo')
        self.none(tufo[1].get('strform:foo'))

        self.eq(len(core.eval('strform:foo')), 0)
        self.eq(len(core.eval('strform:bar')), 2)

        # Calling formTufoByProp twice with different props will
        # smash the most recent props in that are valid to set
        tufo = core.formTufoByProp('strform', 'haha', foo='foo', bar='bar')
        self.eq(tufo[1].get('strform'), 'haha')
        self.eq(tufo[1].get('strform:foo'), 'foo')
        self.eq(tufo[1].get('strform:bar'), 'bar')

        # Ensure we can store data at the boundary of 64 bit integers
        node = core.formTufoByProp('intform', -9223372036854775808)
        self.nn(node)
        core.delTufo(node)
        node = core.formTufoByProp('intform', 9223372036854775807)
        self.nn(node)
        core.delTufo(node)
        self.raises(BadTypeValu, core.formTufoByProp, 'intform', -9223372036854775809)
        self.raises(BadTypeValu, core.formTufoByProp, 'intform', 9223372036854775808)

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
        self.eq(core.getSizeBy('range', 'rg', (-42, 0)), 2)
        self.eq(core.getSizeBy('range', 'rg', (-1, 2)), 3)
        self.eq(core.getSizeBy('le', 'rg', 0), 4)
        self.eq(core.getSizeBy('ge', 'rg', 30), 2)
        self.eq(core.getSizeBy('ge', 'rg', s_cores_lmdb.MAX_INT_VAL), 1)

        # TODO: Need to implement lt for all the cores
        # self.eq(core.getSizeBy('lt', 'rg', -42), 1)
        # self.eq(core.getSizeBy('lt', 'rg', 0), 3)
        # TODO: This is broken for RAM and SQLite
        # self.eq(core.getSizeBy('ge', 'rg', -1, limit=3), 3)

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
        cvers = core.getBlobValu('syn:core:synapse:version')
        self.eq(cvers, s_version.version)

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
        self.gt(core.store.getSize(), 1000)
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

        # form some nodes for doing in-place prop updates on with store.updateProperty()
        nodes = [core.formTufoByProp('inet:tcp4', '10.1.2.{}:80'.format(i)) for i in range(10)]
        ret = core.store.updateProperty('inet:tcp4:port', 'inet:tcp4:gatenumber')
        self.eq(ret, 10)

        # Ensure prop and propvalu indexes are updated
        self.len(10, core.getRowsByProp('inet:tcp4:gatenumber'))
        self.len(10, core.getRowsByProp('inet:tcp4:gatenumber', 80))
        self.len(0, core.getRowsByProp('inet:tcp4:port'))
        self.len(0, core.getRowsByProp('inet:tcp4:port', 80))

        # Join operations typically involving pivoting by iden so this ensures that iden based indexes are updated
        unodes = core.getTufosByProp('inet:tcp4:gatenumber')
        self.len(10, unodes)
        for node in unodes:
            self.isin('node:created', node[1])
            self.isin('inet:tcp4', node[1])
            self.isin('inet:tcp4:ipv4', node[1])
            self.isin('inet:tcp4:gatenumber', node[1])
            self.notin('inet:tcp4:port', node[1])

        # Do a updatePropertValu call to replace a named property with another valu
        unodes = core.getTufosByProp('tufo:form', 'inet:tcp4')
        self.len(10, unodes)
        n = core.store.updatePropertyValu('tufo:form', 'inet:tcp4', 'inet:stateful4')
        self.eq(n, 10)
        unodes = core.getTufosByProp('tufo:form', 'inet:tcp4')
        self.len(0, unodes)
        unodes = core.getTufosByProp('inet:tcp4')
        self.len(10, unodes)
        for node in unodes:
            self.eq(node[1].get('tufo:form'), 'inet:stateful4')
            self.isin('inet:tcp4', node[1])
        unodes = core.getTufosByProp('tufo:form', 'inet:stateful4')
        self.len(10, unodes)
        for node in unodes:
            self.eq(node[1].get('tufo:form'), 'inet:stateful4')
            self.isin('inet:tcp4', node[1])

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
        self.eq(len(core.getTufosBy('in', 'default_foo:p0', [4, 5, 6, 7], limit=1)), 1)
        self.eq(len(core.getTufosBy('in', 'default_foo:p0', [4, 5, 6, 7], limit=0)), 0)
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
        nmb1 = core.formTufoByProp('inet:web:memb', '(vertex.link/pennywise,vertex.link/eldergods)')
        nmb2 = core.formTufoByProp('inet:web:memb', ('vertex.link/invisig0th', 'vertex.link/eldergods'))
        nmb3 = core.formTufoByProp('inet:web:memb', ['vertex.link/pennywise', 'vertex.link/clowns'])

        self.eq(len(core.getTufosBy('in', 'inet:web:memb', ['(vertex.link/pennywise,vertex.link/eldergods)'])), 1)
        self.eq(len(core.getTufosBy('in', 'inet:web:memb:group', ['vertex.link/eldergods'])), 2)
        self.eq(len(core.getTufosBy('in', 'inet:web:memb:group', ['vertex.link/eldergods'])), 2)
        self.eq(len(core.getTufosBy('in', 'inet:web:memb:group', ['vertex.link/eldergods', 'vertex.link/clowns'])), 3)
        self.eq(len(core.getTufosBy('in', 'inet:web:memb', ['(vertex.link/pennywise,vertex.link/eldergods)', ('vertex.link/pennywise', 'vertex.link/clowns')])), 2)

        # By LT/LE/GE/GT
        self.eq(len(core.getTufosBy('lt', 'default_foo:p0', 6)), 3)
        self.eq(len(core.getTufosBy('le', 'default_foo:p0', 6)), 4)
        self.eq(len(core.getTufosBy('le', 'default_foo:p0', 7)), 5)
        self.eq(len(core.getTufosBy('gt', 'default_foo:p0', 6)), 1)
        self.eq(len(core.getTufosBy('ge', 'default_foo:p0', 6)), 2)
        self.eq(len(core.getTufosBy('ge', 'default_foo:p0', 5)), 4)
        # By LT/LE/GE/GT with limits
        self.len(1, core.getTufosBy('lt', 'default_foo:p0', 6, limit=1))
        self.len(1, core.getTufosBy('le', 'default_foo:p0', 6, limit=1))
        self.len(1, core.getTufosBy('le', 'default_foo:p0', 7, limit=1))
        self.len(1, core.getTufosBy('gt', 'default_foo:p0', 6, limit=1))
        self.len(1, core.getTufosBy('ge', 'default_foo:p0', 6, limit=1))
        self.len(1, core.getTufosBy('ge', 'default_foo:p0', 5, limit=1))
        self.len(0, core.getTufosBy('lt', 'default_foo:p0', 6, limit=0))
        self.len(0, core.getTufosBy('le', 'default_foo:p0', 6, limit=0))
        self.len(0, core.getTufosBy('le', 'default_foo:p0', 7, limit=0))
        self.len(0, core.getTufosBy('gt', 'default_foo:p0', 6, limit=0))
        self.len(0, core.getTufosBy('ge', 'default_foo:p0', 6, limit=0))
        self.len(0, core.getTufosBy('ge', 'default_foo:p0', 5, limit=0))

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
        t0 = core.formTufoByProp('intform', 10)
        tufs = core.getTufosBy('range', 'intform', (5, 15))
        self.eq(len(tufs), 1)
        self.eq(tufs[0][0], t0[0])
        self.len(0, core.getTufosBy('range', 'intform', (5, 15), limit=0))
        # Do a range lift requiring prop normalization (using a built-in data type) to work
        t2 = core.formTufoByProp('inet:ipv4', '1.2.3.3')
        tufs = core.getTufosBy('range', 'inet:ipv4', (0x01020301, 0x01020309))
        self.eq(len(tufs), 1)
        self.eq(t2[0], tufs[0][0])
        tufs = core.getTufosBy('range', 'inet:ipv4', ('1.2.3.1', '1.2.3.9'))
        self.eq(len(tufs), 1)
        self.eq(t2[0], tufs[0][0])
        # RANGE test cleanup
        for tufo in [t0, t2]:
            if tufo[1].get('.new'):
                core.delTufo(tufo)

        # By HAS - the valu is dropped by the _tufosByHas handler.
        self.eq(len(core.getTufosBy('has', 'default_foo:p0', valu=None)), 5)
        self.eq(len(core.getTufosBy('has', 'default_foo:p0', valu=5)), 5)
        self.eq(len(core.getTufosBy('has', 'default_foo', valu='foo')), 5)
        self.eq(len(core.getTufosBy('has', 'default_foo', valu='knight')), 5)

        self.eq(len(core.getTufosBy('has', 'inet:ipv4', valu=None)), 5)
        self.eq(len(core.getTufosBy('has', 'syn:tag', valu=None)), 0)

        self.len(1, core.getTufosBy('has', 'default_foo', valu='knight', limit=1))
        self.len(0, core.getTufosBy('has', 'default_foo', valu='knight', limit=0))

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
        self.len(1, core.getTufosBy('tag', None, 'color.white', limit=1))
        self.len(0, core.getTufosBy('tag', None, 'color.white', limit=0))

        # By EQ
        self.eq(len(core.getTufosBy('eq', 'default_foo', 'bar')), 1)
        self.eq(len(core.getTufosBy('eq', 'default_foo', 'blah')), 0)
        self.eq(len(core.getTufosBy('eq', 'default_foo:p0', 5)), 2)
        self.eq(len(core.getTufosBy('eq', 'inet:ipv4', 0x0a020306)), 1)
        self.eq(len(core.getTufosBy('eq', 'inet:ipv4', '10.2.3.6')), 1)
        self.eq(len(core.getTufosBy('eq', 'inet:ipv4:asn', -1)), 5)
        self.eq(len(core.getTufosBy('eq', 'inet:ipv4', 0x0)), 0)
        self.eq(len(core.getTufosBy('eq', 'inet:ipv4', '0.0.0.0')), 0)
        self.eq(len(core.getTufosBy('eq', 'inet:web:memb', '(vertex.link/pennywise,vertex.link/eldergods)')), 1)
        self.eq(len(core.getTufosBy('eq', 'inet:web:memb', ('vertex.link/invisig0th', 'vertex.link/eldergods'))), 1)
        self.len(1, core.getTufosBy('eq', 'inet:ipv4:asn', -1, limit=1))
        self.len(0, core.getTufosBy('eq', 'inet:ipv4:asn', -1, limit=0))

        # By TYPE - this requires data model introspection
        fook = core.formTufoByProp('inet:dns:a', 'derry.vertex.link/10.2.3.6')
        fool = core.formTufoByProp('inet:url', 'https://derry.vertex.link/clowntown.html', ipv4='10.2.3.6')
        # self.eq(len(core.getTufosBy('type', 'inet:ipv4', None)), 7)
        self.eq(len(core.getTufosBy('type', 'inet:ipv4', '10.2.3.6')), 3)
        self.eq(len(core.getTufosBy('type', 'inet:ipv4', 0x0a020306)), 3)
        self.len(1, core.getTufosBy('type', 'inet:ipv4', '10.2.3.6', limit=1))
        self.len(0, core.getTufosBy('type', 'inet:ipv4', '10.2.3.6', limit=0))

        # By TYPE using COMP nodes
        self.eq(len(core.getTufosBy('type', 'inet:web:memb', '(vertex.link/pennywise,vertex.link/eldergods)')), 1)
        self.eq(len(core.getTufosBy('type', 'inet:web:memb', ('vertex.link/invisig0th', 'vertex.link/eldergods'))), 1)
        self.eq(len(core.getTufosBy('type', 'inet:web:acct', 'vertex.link/invisig0th')), 2)

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
        # Ensure limits are respected
        self.len(1, core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.8/29', limit=1))
        self.len(0, core.getTufosBy('inet:cidr', 'inet:ipv4', '10.2.1.8/29', limit=0))

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

    def test_cortex_datamodel_runt_consistency(self):
        with self.getRamCore() as core:

            uniprops = core.getUnivProps()

            nodes = core.getTufosByProp('syn:form')
            for node in nodes:
                self.isin('syn:form:ptype', node[1])
                if 'syn:form:doc' in node[1]:
                    self.isinstance(node[1].get('syn:form:doc'), str)
                if 'syn:form:local' in node[1]:
                    self.isinstance(node[1].get('syn:form:local'), int)

            nodes = core.getTufosByProp('syn:prop')
            for node in nodes:
                prop = node[1].get('syn:prop')
                if prop not in uniprops:
                    self.isin('syn:prop:form', node[1])

                if 'syn:prop:glob' in node[1]:
                    continue
                self.isin('syn:prop:req', node[1])
                self.isin('syn:prop:ptype', node[1])
                if 'syn:prop:doc' in node[1]:
                    self.isinstance(node[1].get('syn:prop:doc'), str)
                if 'syn:prop:base' in node[1]:
                    self.isinstance(node[1].get('syn:prop:base'), str)
                if 'syn:prop:title' in node[1]:
                    self.isinstance(node[1].get('syn:prop:title'), str)
                if 'syn:prop:defval' in node[1]:
                    dv = node[1].get('syn:prop:defval')
                    if dv is None:
                        continue
                    self.true(s_common.canstor(dv))

            # Some nodes are local, some are not
            node = core.getTufoByProp('syn:form', 'inet:ipv4')
            self.eq(node[1].get('syn:form:local'), None)
            node = core.getTufoByProp('syn:form', 'syn:splice')
            self.eq(node[1].get('syn:form:local'), 1)

            # Check a few specific nodes
            node = core.getTufoByProp('syn:prop', 'inet:ipv4')
            self.isin('syn:prop:doc', node[1])
            self.isin('syn:prop:base', node[1])
            self.notin('syn:prop:relname', node[1])
            node = core.getTufoByProp('syn:prop', 'inet:ipv4:type')
            self.isin('syn:prop:doc', node[1])
            self.isin('syn:prop:base', node[1])
            self.isin('syn:prop:relname', node[1])

            # universal prop nodes
            node = core.getTufoByProp('syn:prop', 'node:ndef')
            self.eq(node[1].get('syn:prop:univ'), 1)
            # The node:ndef value is a stable guid :)
            self.eq(node[1].get('node:ndef'), 'd20cb4873e36db4670073169f87abc32')

            # Ensure things bubbled up during node / datamodel creation
            self.eq(core.getPropInfo('strform', 'doc'), 'A test str form')
            self.eq(core.getPropInfo('intform', 'doc'), 'The base integer type')
            self.eq(core.getTufoByProp('syn:prop', 'strform')[1].get('syn:prop:doc'), 'A test str form')
            self.eq(core.getTufoByProp('syn:prop', 'intform')[1].get('syn:prop:doc'), 'The base integer type')

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
        with self.getRamCore() as core:
            foob = core.formTufoByProp('strform', 'bar', foo='faz')
            core.addTufoTag(foob, 'zip.zap')

            self.nn(foob[1].get('#zip'))
            self.nn(foob[1].get('#zip.zap'))

            self.eq(len(core.getTufosByTag('zip', form='strform')), 1)
            self.eq(len(core.getTufosByTag('zip.zap', form='strform')), 1)

            core.delTufoTag(foob, 'zip')

            self.none(foob[1].get('#zip'))
            self.none(foob[1].get('#zip.zap'))

            self.eq(len(core.getTufosByTag('zip', form='strform')), 0)
            self.eq(len(core.getTufosByTag('zip.zap', form='strform')), 0)

    def test_cortex_tufo_setprops(self):
        with self.getRamCore() as core:
            foob = core.formTufoByProp('strform', 'bar', foo='faz')
            self.eq(foob[1].get('strform:foo'), 'faz')
            core.setTufoProps(foob, foo='zap')
            core.setTufoProps(foob, bar='zap')

            self.eq(len(core.getTufosByProp('strform:foo', valu='zap')), 1)
            self.eq(len(core.getTufosByProp('strform:bar', valu='zap')), 1)

            # Try using setprops with an built-in model which type subprops
            t0 = core.formTufoByProp('inet:web:acct', 'vertex.link/pennywise')
            self.notin('inet:web:acct:email', t0[1])
            props = {'email': 'pennywise@vertex.link'}
            core.setTufoProps(t0, **props)
            self.isin('inet:web:acct:email', t0[1])
            t1 = core.getTufoByProp('inet:email', 'pennywise@vertex.link')
            self.nn(t1)

            # Trying settufoprops on a ro prop doens't change anything
            self.eq(t0[1].get('inet:web:acct:user'), 'pennywise')
            t0 = core.setTufoProps(t0, user='ninja')
            self.eq(t0[1].get('inet:web:acct:user'), 'pennywise')

            # Try forming a node from its normalize value and then setting
            # ro props after the fact. Also ensure those secondary props which
            # may trigger autoadds are generating the autoadds and do not retain
            # those non-model seconadry props.
            core.addDataModels([
                ('test:foo', {
                    'forms': (
                        ('test:roprop', {'ptype': 'guid'}, (
                            ('hehe', {'ptype': 'int', 'ro': 1}),
                        )),
                    ),
                })
            ])

            # Ensure that splices for changes on ro properties on a node are reflected
            node = core.formTufoByProp('test:roprop', '*')

            self.nn(node[1].get('test:roprop'))
            self.none(node[1].get('test:roprop:hehe'))

            node = core.setTufoProps(node, hehe=10)
            self.eq(node[1].get('test:roprop:hehe'), 10)

            node = core.setTufoProps(node, hehe=20)
            self.eq(node[1].get('test:roprop:hehe'), 10)

    def test_cortex_tufo_pop(self):
        with self.getRamCore() as core:
            foo0 = core.formTufoByProp('strform', 'bar', foo='faz')
            foo1 = core.formTufoByProp('strform', 'baz', foo='faz')

            self.eq(2, len(core.popTufosByProp('strform:foo', valu='faz')))
            self.eq(0, len(core.getTufosByProp('strform')))

    def test_cortex_tufo_setprop(self):
        with self.getRamCore() as core:
            foob = core.formTufoByProp('strform', 'bar', foo='faz')
            self.eq(foob[1].get('strform:foo'), 'faz')

            core.setTufoProp(foob, 'foo', 'zap')

            self.eq(len(core.getTufosByProp('strform:foo', valu='zap')), 1)

    def test_cortex_tufo_list(self):

        with self.getRamCore() as core:
            foob = core.formTufoByProp('strform', 'bar', foo='faz')

            core.addTufoList(foob, 'hehe', 1, 2, 3)

            self.nn(foob[1].get('tufo:list:hehe'))

            vals = core.getTufoList(foob, 'hehe')
            vals.sort()

            self.eq(tuple(vals), (1, 2, 3))

            core.delTufoListValu(foob, 'hehe', 2)

            vals = core.getTufoList(foob, 'hehe')
            vals.sort()

            self.eq(tuple(vals), (1, 3))

    def test_cortex_tufo_del(self):

        with self.getRamCore() as core:
            foob = core.formTufoByProp('strform', 'bar', foo='faz')

            self.nn(core.getTufoByProp('strform', valu='bar'))
            self.nn(core.getTufoByProp('strform:foo', valu='faz'))

            core.addTufoList(foob, 'blahs', 'blah1')
            core.addTufoList(foob, 'blahs', 'blah2')

            blahs = core.getTufoList(foob, 'blahs')

            self.eq(len(blahs), 2)

            core.delTufoByProp('strform', 'bar')

            self.none(core.getTufoByProp('strform', valu='bar'))
            self.none(core.getTufoByProp('strform:foo', valu='faz'))

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
        fd = io.BytesIO()
        core0 = s_cortex.openurl('ram://', savefd=fd)
        self.addTstForms(core0)

        self.true(core0.isnew)
        myfo0 = core0.myfo[0]

        created = core0.getBlobValu('syn:core:created')

        t0 = core0.formTufoByProp('strform', 'one', foo='faz')
        t1 = core0.formTufoByProp('strform', 'two', foo='faz')

        core0.setTufoProps(t0, foo='gronk')

        core0.delTufoByProp('strform', 'two')
        # Try persisting an blob store value
        core0.setBlobValu('syn:test', 1234)
        self.eq(core0.getBlobValu('syn:test'), 1234)
        core0.fini()

        fd.seek(0)

        core1 = s_cortex.openurl('ram://', savefd=fd)

        self.false(core1.isnew)
        myfo1 = core1.myfo[0]
        self.eq(myfo0, myfo1)

        self.none(core1.getTufoByProp('strform', 'two'))

        t0 = core1.getTufoByProp('strform', 'one')
        self.nn(t0)

        self.eq(t0[1].get('strform:foo'), 'gronk')

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

        self.none(core2.getTufoByProp('strform', 'two'))

        t0 = core2.getTufoByProp('strform', 'one')
        self.nn(t0)

        self.eq(t0[1].get('strform:foo'), 'gronk')

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

        # Stats props both accept a valu and are normed
        self.nn(core.formTufoByProp('inet:ipv4', 0x01020304))
        self.nn(core.formTufoByProp('inet:ipv4', 0x05060708))
        self.eq(core.getStatByProp('count', 'inet:ipv4'), 2)
        self.eq(core.getStatByProp('count', 'inet:ipv4', 0x01020304), 1)
        self.eq(core.getStatByProp('count', 'inet:ipv4', '1.2.3.4'), 1)

    def test_cortex_fire_set(self):

        with self.getRamCore() as core:

            tufo = core.formTufoByProp('strform', 'hehe', bar='lol')

            msgs = wait = core.waiter(1, 'node:prop:set')

            core.setTufoProps(tufo, bar='hah')

            evts = wait.wait(timeout=2)

            self.eq(evts[0][0], 'node:prop:set')
            self.eq(evts[0][1]['node'][0], tufo[0])
            self.eq(evts[0][1]['form'], 'strform')
            self.eq(evts[0][1]['valu'], 'hehe')
            self.eq(evts[0][1]['prop'], 'strform:bar')
            self.eq(evts[0][1]['newv'], 'hah')
            self.eq(evts[0][1]['oldv'], 'lol')

    def test_cortex_tags(self):
        core = s_cortex.openurl('ram://')
        core.setConfOpt('caching', 1)

        core.addTufoForm('foo', ptype='str')

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
        self.len(2, tags)
        tags = core.getTufosByProp('syn:tag:base', 'rofl', limit=1)
        self.len(1, tags)
        tags = core.getTufosByProp('syn:tag:base', 'rofl', limit=0)
        self.len(0, tags)

        wait = core.waiter(2, 'node:tag:del')
        hehe = core.delTufoTag(hehe, 'lulz.rofl')
        self.nn(hehe)
        self.isin('#lulz', hehe[1])
        self.notin('#lulz.rofl', hehe[1])
        self.notin('#lulz.rofl.zebr', hehe[1])
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

        # Ensure we're making nodes which have a timebox
        node = core.addTufoTag(node, 'foo.bar@20171217')
        self.eq(s_tufo.ival(node, '#foo.bar'), (1513468800000, 1513468800000))
        # Ensure the times argument is respected
        node = core.addTufoTag(node, 'foo.duck', times=(1513382400000, 1513468800000))
        self.eq(s_tufo.ival(node, '#foo.duck'), (1513382400000, 1513468800000))

        # Recreate expected results from #320 to ensure
        # we're also doing the same via storm
        self.eq(len(core.eval('[inet:fqdn=w00t.com +#some.tag]')), 1)
        self.eq(len(core.eval('inet:fqdn=w00t.com')), 1)
        self.eq(len(core.eval('inet:fqdn=w00t.com +node:created<1')), 0)
        self.eq(len(core.eval('inet:fqdn=w00t.com +node:created>1')), 1)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0)')), 2)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0, limit=3)')), 2)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0, limit=2)')), 2)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0, limit=1)')), 1)
        self.eq(len(core.eval('inet:fqdn=w00t.com totags(leaf=0, limit=0)')), 0)
        self.raises(BadOperArg, core.eval, 'inet:fqdn=w00t.com totags(leaf=0, limit=-1)')
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

        with self.getRamCore() as core0, self.getRamCore() as core1:

            # Form a tufo before we start sending splices
            tufo_before1 = core0.formTufoByProp('strform', 'before1')
            tufo_before2 = core0.formTufoByProp('strform', 'before2')
            core0.addTufoTag(tufo_before2, 'hoho')  # this will not be synced

            # Start sending splices
            def splicecore(mesg):
                core1.splice(mesg[1].get('mesg'))

            core0.on('splice', splicecore)
            core0.delTufo(tufo_before1)

            # Add node by forming it
            tufo0 = core0.formTufoByProp('strform', 'bar', foo='faz')
            tufo1 = core1.getTufoByProp('strform', 'bar')

            self.eq(tufo1[1].get('strform'), 'bar')
            self.eq(tufo1[1].get('strform:foo'), 'faz')

            # Add tag to existing node
            tufo0 = core0.addTufoTag(tufo0, 'hehe')
            tufo1 = core1.getTufoByProp('strform', 'bar')

            self.true(s_tufo.tagged(tufo1, 'hehe'))

            # Del tag from existing node
            core0.delTufoTag(tufo0, 'hehe')
            tufo1 = core1.getTufoByProp('strform', 'bar')
            self.false(s_tufo.tagged(tufo1, 'hehe'))

            # Set prop on existing node
            core0.setTufoProp(tufo0, 'foo', 'lol')
            tufo1 = core1.getTufoByProp('strform', 'bar')
            self.eq(tufo1[1].get('strform:foo'), 'lol')

            # Del existing node
            core0.delTufo(tufo0)
            tufo1 = core1.getTufoByProp('strform', 'bar')
            self.none(tufo1)

            # Tag a node in first core, ensure it does not get formed in the second core.
            # This is because only node:add splices make nodes.
            core0.addTufoTag(tufo_before2, 'hehe')
            tufo1 = core1.getTufoByProp('strform', 'before2')
            self.none(tufo1)
            core0.delTufoTag(tufo_before2, 'hehe')
            tufo1 = core1.getTufoByProp('strform', 'before2')
            self.none(tufo1)

            # Add a complicated node which fires a bunch of autoadd nodes and
            # ensure they are populated in the second core
            postref_tufo = core0.formTufoByProp('inet:web:postref',
                                                (('vertex.link/user', 'mypost 0.0.0.0'),
                                                 ('inet:ipv4', 0)))
            self.nn(core1.getTufoByProp('inet:web:post',
                                        ('vertex.link/user', 'mypost 0.0.0.0')))
            self.eq(postref_tufo[1]['tufo:form'], 'inet:web:postref')
            self.eq(postref_tufo[1]['inet:web:postref'], '804ec63392f4ea031bb3fd004dee209d')
            self.eq(postref_tufo[1]['inet:web:postref:post'], '68bc4607f0518963165536921d6e86fa')
            self.eq(postref_tufo[1]['inet:web:postref:xref'], 'inet:ipv4=0.0.0.0')
            self.eq(postref_tufo[1]['inet:web:postref:xref:prop'], 'inet:ipv4')
            self.eq(postref_tufo[1]['inet:web:postref:xref:intval'], 0)

            # Ensure we got the deconflicted node that was already made, not a new node
            post_tufo = core1.formTufoByProp('inet:web:post',
                                             ('vertex.link/user', 'mypost 0.0.0.0'))
            self.notin('.new', post_tufo[1])
            self.eq(post_tufo[1]['inet:web:post'], postref_tufo[1]['inet:web:postref:post'])
            # Ensure that subs on the autoadd node are formed properly
            self.eq(post_tufo[1].get('inet:web:post:acct'), 'vertex.link/user')
            self.eq(post_tufo[1].get('inet:web:post:text'), 'mypost 0.0.0.0')
            # Ensure multiple subs were made into nodes
            self.nn(core1.getTufoByProp('inet:web:acct', 'vertex.link/user'))
            self.nn(core1.getTufoByProp('inet:user', 'user'))
            self.nn(core1.getTufoByProp('inet:fqdn', 'vertex.link'))
            self.nn(core1.getTufoByProp('inet:fqdn', 'link'))

    def test_cortex_splices_user(self):
        splices = []
        with self.getRamCore() as core:  # type: s_cores_common.Cortex
            def add_splice(mesg):
                splice = mesg[1].get('mesg')
                splices.append(splice)
            core.on('splice', add_splice)

            t0 = core.formTufoByProp('strform', 'hi')
            t0 = core.setTufoProp(t0, 'baz', 123)
            t0 = core.addTufoTag(t0, 'hello.gaiz')
            t0 = core.delTufoTag(t0, 'hello.gaiz')

            t0 = core.setTufoIval(t0, 'dude', (1, 2))
            t0 = core.delTufoIval(t0, 'dude')

            users = {splice[1].get('user') for splice in splices}
            self.eq(users, {'root@localhost'})

            with s_auth.runas('evil.haxx0r'):
                t0 = core.delTufoProp(t0, 'baz')

            users = {splice[1].get('user') for splice in splices}
            self.eq(users, {'root@localhost', 'evil.haxx0r'})

            with s_auth.runas('bob.grey@vertex.link'):
                t0 = core.delTufo(t0)
                self.none(t0)

            users = {splice[1].get('user') for splice in splices}
            self.eq(users, {'root@localhost', 'evil.haxx0r',
                            'bob.grey@vertex.link'})

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

        with self.getRamCore() as core:
            # Disable enforce for first set of tests
            core.setConfOpt('enforce', 0)

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

            # we can make nodes from props (not forms!)
            node0 = core.formTufoByProp('foo:baz:fqdn', 'woot.com')
            self.nn(node0)
            self.eq(node0[1].get('tufo:form'), 'foo:baz:fqdn')
            self.eq(node0[1].get('foo:baz:fqdn'), 'woot.com')

            # Now re-enable enforce
            core.setConfOpt('enforce', 1)

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
            # Ensure that we cannot form nodes from non-form prop's which do not have ctors
            self.raises(NoSuchForm, core.formTufoByProp, 'foo:baz:fqdn', 'woot.com')

    def test_cortex_minmax(self):

        with self.getRamCore() as core:

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

        with self.getRamCore() as core:

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

        with self.getRamCore() as core:

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

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar', baz=2)
            tufo1 = core.formTufoByProp('strform', 'baz', baz=2)

            answ0 = core.getTufosByProp('strform')
            answ1 = core.getTufosByProp('strform', valu='bar')

            self.eq(len(answ0), 2)
            self.eq(len(answ1), 1)

            self.eq(len(core.cache_fifo), 0)
            self.eq(len(core.cache_bykey), 0)
            self.eq(len(core.cache_byiden), 0)
            self.eq(len(core.cache_byprop), 0)

            core.setConfOpt('caching', 1)

            self.eq(core.caching, 1)

            answ0 = core.getTufosByProp('strform')

            self.eq(len(answ0), 2)
            self.eq(len(core.cache_fifo), 1)
            self.eq(len(core.cache_bykey), 1)
            self.eq(len(core.cache_byiden), 2)
            self.eq(len(core.cache_byprop), 1)

            tufo0 = core.formTufoByProp('strform', 'bar')
            tufo0 = core.addTufoTag(tufo0, 'hehe')

            self.eq(len(core.getTufosByTag('hehe', form='strform')), 1)
            core.delTufoTag(tufo0, 'hehe')

            tufo0 = core.getTufoByProp('strform', 'bar')
            self.noprop(tufo0[1], '#hehe')

    def test_cortex_caching_set(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar', baz=10)
            tufo1 = core.formTufoByProp('strform', 'baz', baz=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('strform:baz')
            tufs1 = core.getTufosByProp('strform:baz', valu=10)
            tufs2 = core.getTufosByProp('strform:baz', valu=11)
            tufs3 = core.getTufosByProp('strform:baz', valu=10, limit=2)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)
            self.eq(len(tufs2), 0)
            self.eq(len(tufs3), 2)

            # inspect the details of the cache data structures when setTufoProps
            # causes an addition or removal...
            self.nn(core.cache_bykey.get(('strform:baz', 10, None)))
            self.nn(core.cache_bykey.get(('strform:baz', None, None)))

            # we should have hit the unlimited query and not created a new cache hit...
            self.none(core.cache_bykey.get(('strform:baz', 10, 2)))

            self.nn(core.cache_byiden.get(tufo0[0]))
            self.nn(core.cache_byiden.get(tufo1[0]))

            self.nn(core.cache_byprop.get(('strform:baz', 10)))
            self.nn(core.cache_byprop.get(('strform:baz', None)))

            core.setTufoProp(tufo0, 'baz', 11)

            # the cached results should be updated
            tufs0 = core.getTufosByProp('strform:baz')
            tufs1 = core.getTufosByProp('strform:baz', valu=10)
            tufs2 = core.getTufosByProp('strform:baz', valu=11)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 1)
            self.eq(len(tufs2), 1)

            self.eq(tufs1[0][0], tufo1[0])
            self.eq(tufs2[0][0], tufo0[0])

    def test_cortex_caching_add_tufo(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar', baz=10)
            tufo1 = core.formTufoByProp('strform', 'baz', baz=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('strform:baz')
            tufs1 = core.getTufosByProp('strform:baz', valu=10)
            tufs2 = core.getTufosByProp('strform:baz', valu=11)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)
            self.eq(len(tufs2), 0)

            tufo2 = core.formTufoByProp('strform', 'lol', baz=10)

            tufs0 = core.getTufosByProp('strform:baz')
            tufs1 = core.getTufosByProp('strform:baz', valu=10)
            tufs2 = core.getTufosByProp('strform:baz', valu=11)

            self.eq(len(tufs0), 3)
            self.eq(len(tufs1), 3)
            self.eq(len(tufs2), 0)

    def test_cortex_caching_del_tufo(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar', baz=10)
            tufo1 = core.formTufoByProp('strform', 'baz', baz=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('strform:baz')
            tufs1 = core.getTufosByProp('strform:baz', valu=10)
            tufs2 = core.getTufosByProp('strform:baz', valu=11)

            # Ensure we have cached the tufos we're deleting.
            self.nn(core.cache_byiden.get(tufo0[0]))
            self.nn(core.cache_byiden.get(tufo1[0]))

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)
            self.eq(len(tufs2), 0)

            # Delete an uncached object - here the tufo contents was cached
            # during lifts but the object itself is a different tuple id()
            core.delTufo(tufo0)

            tufs0 = core.getTufosByProp('strform:baz')
            tufs1 = core.getTufosByProp('strform:baz', valu=10)
            tufs2 = core.getTufosByProp('strform:baz', valu=11)

            self.eq(len(tufs0), 1)
            self.eq(len(tufs1), 1)
            self.eq(len(tufs2), 0)

            # Delete an object which was actually cached during lift
            core.delTufo(tufs0[0])
            tufs0 = core.getTufosByProp('strform:baz')
            self.eq(len(tufs0), 0)

    def test_cortex_caching_del_tufo_prop(self):
        with self.getRamCore() as core:
            core.setConfOpt('caching', 1)
            t0 = core.formTufoByProp('strform', 'stuff', baz=10)
            self.eq(t0[1].get('strform:baz'), 10)
            core.delTufoProp(t0, 'baz')
            t0 = core.getTufoByProp('strform', 'stuff')
            self.eq(t0[1].get('strform:baz'), None)

    def test_cortex_caching_atlimit(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar', baz=10)
            tufo1 = core.formTufoByProp('strform', 'baz', baz=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('strform:baz', limit=2)
            tufs1 = core.getTufosByProp('strform:baz', valu=10, limit=2)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)

            # when an entry is deleted from a cache result that was at it's limit
            # it should be fully invalidated

            core.delTufo(tufo0)

            self.none(core.cache_bykey.get(('strform:baz', None, 2)))
            self.none(core.cache_bykey.get(('strform:baz', 10, 2)))

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar', baz=10)
            tufo1 = core.formTufoByProp('strform', 'baz', baz=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('strform:baz', limit=2)
            tufs1 = core.getTufosByProp('strform:baz', valu=10, limit=2)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)

            tufo2 = core.formTufoByProp('strform', 'baz', baz=10)

            # when an entry is added from a cache result that was at it's limit
            # it should *not* be invalidated

            self.nn(core.cache_bykey.get(('strform:baz', None, 2)))
            self.nn(core.cache_bykey.get(('strform:baz', 10, 2)))

    def test_cortex_caching_under_limit(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar', baz=10)
            tufo1 = core.formTufoByProp('strform', 'baz', baz=10)

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByProp('strform:baz', limit=9)
            tufs1 = core.getTufosByProp('strform:baz', valu=10, limit=9)

            self.eq(len(tufs0), 2)
            self.eq(len(tufs1), 2)

            # when an entry is deleted from a cache result that was under it's limit
            # it should be removed but *not* invalidated

            core.delTufo(tufo0)

            self.nn(core.cache_bykey.get(('strform:baz', None, 9)))
            self.nn(core.cache_bykey.get(('strform:baz', 10, 9)))

            tufs0 = core.getTufosByProp('strform:baz', limit=9)
            tufs1 = core.getTufosByProp('strform:baz', valu=10, limit=9)

            self.eq(len(tufs0), 1)
            self.eq(len(tufs1), 1)

    def test_cortex_caching_oneref(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar')

            core.setConfOpt('caching', 1)

            ref0 = core.getTufosByProp('strform', valu='bar')[0]
            ref1 = core.getTufosByProp('strform', valu='bar')[0]

            self.eq(id(ref0), id(ref1))

    def test_cortex_caching_tags(self):

        with self.getRamCore() as core:

            tufo0 = core.formTufoByProp('strform', 'bar')
            tufo1 = core.formTufoByProp('strform', 'baz')

            core.addTufoTag(tufo0, 'hehe')

            core.setConfOpt('caching', 1)

            tufs0 = core.getTufosByTag('hehe', form='strform')

            core.addTufoTag(tufo1, 'hehe')

            tufs1 = core.getTufosByTag('hehe', form='strform')
            self.eq(len(tufs1), 2)

            core.delTufoTag(tufo0, 'hehe')

            tufs2 = core.getTufosByTag('hehe', form='strform')
            self.eq(len(tufs2), 1)

    def test_cortex_caching_new(self):

        with self.getRamCore() as core:

            core.setConfOpt('caching', 1)

            tufo0 = core.formTufoByProp('strform', 'bar')
            tufo1 = core.formTufoByProp('strform', 'bar')

            self.true(tufo0[1].get('.new'))
            self.false(tufo1[1].get('.new'))

    def test_cortex_caching_disable(self):

        with self.getRamCore() as core:

            core.setConfOpt('caching', 1)

            tufo = core.formTufoByProp('strform', 'bar')

            self.nn(core.cache_byiden.get(tufo[0]))
            self.nn(core.cache_bykey.get(('strform', 'bar', 1)))
            self.nn(core.cache_byprop.get(('strform', 'bar')))
            self.eq(len(core.cache_fifo), 1)

            core.setConfOpt('caching', 0)

            self.none(core.cache_byiden.get(tufo[0]))
            self.none(core.cache_bykey.get(('strform', 'bar', 1)))
            self.none(core.cache_byprop.get(('strform', 'bar')))
            self.eq(len(core.cache_fifo), 0)

    def test_cortex_reqstor(self):
        # Ensure that the cortex won't let us store data that is invalid
        # This requires us to disable enforcement, since otherwise all
        # data is normed and that fails with BadTypeValu instead
        with self.getRamCore() as core:
            core.setConfOpt('enforce', 0)
            self.raises(BadPropValu, core.formTufoByProp, 'foo:bar', True)

    def test_cortex_splicefd(self):
        with self.getTestDir() as path:
            with genfile(path, 'savefile.mpk') as fd:
                with self.getRamCore() as core:
                    core.addSpliceFd(fd)

                    tuf0 = core.formTufoByProp('inet:fqdn', 'woot.com')
                    tuf1 = core.formTufoByProp('inet:fqdn', 'newp.com')

                    core.addTufoTag(tuf0, 'foo.bar')
                    # this should leave the tag foo
                    core.delTufoTag(tuf0, 'foo.bar')

                    core.delTufo(tuf1)

                fd.seek(0)

                with self.getRamCore() as core:

                    core.eatSpliceFd(fd)

                    self.none(core.getTufoByProp('inet:fqdn', 'newp.com'))
                    self.nn(core.getTufoByProp('inet:fqdn', 'woot.com'))

                    self.eq(len(core.getTufosByTag('foo.bar', form='inet:fqdn')), 0)
                    self.eq(len(core.getTufosByTag('foo', form='inet:fqdn')), 1)

    def test_cortex_addmodel(self):

        with self.getRamCore() as core:

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

        with self.getRamCore() as core:
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
                    tufo0 = core0.formTufoByProp('inet:fqdn', 'woot.com')

                tufo1 = core1.getTufoByProp('inet:fqdn', 'woot.com')
                self.nn(tufo1)

                # node:created rows are not sent with the splice and will be created by the target core
                self.ge(tufo1[1]['node:created'], tufo0[1]['node:created'])

    def test_cortex_xact_deadlock(self):
        N = 100
        fd = tempfile.NamedTemporaryFile()
        evnt = threading.Event()
        dmon = s_daemon.Daemon()
        pool = s_threads.Pool(size=4, maxsize=8)

        with s_cortex.openurl('sqlite:///%s' % fd.name) as core:

            def populate():
                for i in range(N):
                    core.formTufoByProp('inet:ipv4', str(i), **{})
                evnt.set()

            dmon.share('core', core)
            link = dmon.listen('tcp://127.0.0.1:0/core')
            prox = s_telepath.openurl('tcp://127.0.0.1:%d/core' % link[1]['port'])

            pool.call(populate)
            for i in range(N):
                tufos = prox.getTufosByProp('inet:ipv4')

            self.true(evnt.wait(timeout=3))
            pool.fini()

    def test_cortex_seed(self):

        with self.getRamCore() as core:

            def seedFooBar(prop, valu, **props):
                return core.formTufoByProp('inet:fqdn', valu, **props)

            core.addSeedCtor('foo:bar', seedFooBar)
            tufo = core.formTufoByProp('foo:bar', 'woot.com')
            self.eq(tufo[1].get('inet:fqdn'), 'woot.com')

    def test_cortex_bytype(self):
        with self.getRamCore() as core:
            core.formTufoByProp('inet:dns:a', 'woot.com/1.2.3.4')
            self.eq(len(core.eval('inet:ipv4*type="1.2.3.4"')), 2)

    def test_cortex_seq(self):
        with self.getRamCore() as core:

            core.formTufoByProp('syn:seq', 'foo')
            node = core.formTufoByProp('syn:seq', 'bar', nextvalu=10, width=4)

            self.eq(core.nextSeqValu('foo'), 'foo0')
            self.eq(core.nextSeqValu('foo'), 'foo1')

            self.eq(core.nextSeqValu('bar'), 'bar0010')
            self.eq(core.nextSeqValu('bar'), 'bar0011')

            self.raises(NoSuchSeq, core.nextSeqValu, 'lol')

    def test_cortex_ingest(self):

        data = {'results': {'fqdn': 'woot.com', 'ipv4': '1.2.3.4'}}

        with self.getRamCore() as core:

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

        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:fqdn', 'vertex.link')

            core.addTufoTag(node, 'foo.bar')

            tdoc = core.getTufoByProp('syn:tagform', ('foo.bar', 'inet:fqdn'))

            self.nn(tdoc)

            self.eq(tdoc[1].get('syn:tagform:tag'), 'foo.bar')
            self.eq(tdoc[1].get('syn:tagform:form'), 'inet:fqdn')

            self.eq(tdoc[1].get('syn:tagform:doc'), '??')
            self.eq(tdoc[1].get('syn:tagform:title'), '??')

    def test_cortex_splices_errs(self):

        splices = [
            ('newp:fake', {}),
            ('node:add', {'form': 'inet:fqdn', 'valu': 'vertex.link'})
        ]

        with self.getRamCore() as core:
            errs = core.splices(splices)
            self.eq(len(errs), 1)
            self.eq(errs[0][0][0], 'newp:fake')
            self.nn(core.getTufoByProp('inet:fqdn', 'vertex.link'))

    def test_cortex_norm_fail(self):
        with self.getRamCore() as core:
            core.formTufoByProp('inet:web:acct', 'vertex.link/visi')
            self.raises(BadTypeValu, core.eval, 'inet:web:acct="totally invalid input"')

    def test_cortex_local(self):
        splices = []
        with self.getRamCore() as core:

            core.on('splice', splices.append)
            node = core.formTufoByProp('syn:splice', None)

            self.nn(node)
            self.nn(node[0])

        self.eq(len(splices), 0)

    def test_cortex_module(self):

        with self.getRamCore() as core:

            node = core.formTufoByProp('inet:ipv4', '1.2.3.4')
            self.eq(node[1].get('inet:ipv4:asn'), -1)

            mods = (('synapse.tests.test_cortex.CoreTestModule', {'foobar': True}), )

            core.setConfOpt('rev:model', 1)
            core.setConfOpt('modules', mods)

            # Get a list of modules which are loaded in the Cortex
            modules = core.getCoreMods()
            self.gt(len(modules), 2)
            self.isin('synapse.models.syn.SynMod', modules)
            self.isin('synapse.tests.test_cortex.CoreTestModule', modules)

            # directly access the module so we can confirm it gets fini()
            modu = core.coremods.get('synapse.tests.test_cortex.CoreTestModule')

            self.true(modu.foobar)

            self.nn(core.getTypeInst('test:type1'))
            self.nn(core.getTypeInst('test:type2'))
            self.none(core.getTypeInst('test:type3'))

            self.eq(core.getModlVers('test'), 201707210101)

            node = core.formTufoByProp('inet:ipv4', '1.2.3.5')
            self.eq(node[1].get('inet:ipv4:asn'), 10)

            iden = guid()
            node = core.formTufoByProp('ou:org', iden)
            core.delTufo(node)

            self.len(1, modu.added)
            self.len(1, modu.deled)

            self.eq(modu.added[0][0], node[0])
            self.eq(modu.deled[0][0], node[0])

        self.true(modu.isfini)

    def test_cortex_modlvers(self):

        with self.getRamCore() as core:

            self.eq(core.getModlVers('hehe'), -1)

            core.setModlVers('hehe', 10)
            self.eq(core.getModlVers('hehe'), 10)

            core.setModlVers('hehe', 20)
            self.eq(core.getModlVers('hehe'), 20)

    def test_cortex_modlrevs(self):

        with self.getRamCore() as core:

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

    def test_cortex_getbytag(self):

        with self.getRamCore() as core:

            node0 = core.formTufoByProp('inet:user', 'visi')
            node1 = core.formTufoByProp('inet:ipv4', 0x01020304)

            core.addTufoTag(node0, 'foo')
            core.addTufoTag(node1, 'foo')

            self.eq(len(core.getTufosByTag('foo')), 2)
            self.eq(len(core.getTufosByTag('foo', form='inet:user')), 1)
            self.eq(len(core.getTufosByTag('foo', form='inet:ipv4')), 1)

    def test_cortex_tag_ival(self):

        splices = []
        def append(mesg):
            splices.append(mesg[1].get('mesg'))

        with self.getRamCore() as core:

            core.on('splice', append)

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

        with self.getRamCore() as core:
            core.splices(splices)
            core.on('splice', append)
            node = core.eval('inet:ipv4=1.2.3.4')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), (1293840000000, 1514764800000))
            core.eval('inet:ipv4=1.2.3.4 [ -#foo.bar ]')

        with self.getRamCore() as core:
            core.splices(splices)
            node = core.eval('inet:ipv4=1.2.3.4')[0]
            self.eq(s_tufo.ival(node, '#foo.bar'), None)

    def test_cortex_module_datamodel_migration(self):
        self.skipTest('Needs global model registry available')
        with self.getRamCore() as core:

            # Enforce data model consistency.
            core.setConfOpt('enforce', 1)

            mods = (('synapse.tests.test_cortex.CoreTestDataModelModuleV0', {}),)
            core.setConfOpt('modules', mods)

            self.eq(core.getModlVers('test'), 0)
            self.nn(core.getTypeInst('foo:bar'))

            node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
            self.eq(node[1].get('tufo:form'), 'foo:bar')
            self.gt(node[1].get('node:created'), 1483228800000)
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

        with self.getRamCore() as core:
            tufo = core.formTufoByProp('strform', 'haha', foo='bar', bar='faz')
            splice = ('node:prop:del', {'form': 'strform', 'valu': 'haha', 'prop': 'foo'})
            core.splice(splice)

            self.eq(len(core.eval('strform:foo')), 0)
            self.eq(len(core.eval('strform:bar')), 1)

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
                self.gt(node[1].get('node:created'), 1483228800000)
                self.eq(node[1].get('foo:bar'), 'I am a bar foo.')
                self.none(node[1].get('foo:bar:duck'))

            with s_cortex.openurl('ram://', savefile=savefile) as core:
                self.eq(core.getModlVers('test'), 0)
                # We are unable to form a node with the custom type with enforce enabled
                self.raises(NoSuchForm, core.formTufoByProp, 'foo:bar', 'I am a bar foo.')
                # But if we disable we can get the node which exists in the cortex
                core.setConfOpt('enforce', 0)
                node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
                self.false(node[1].get('.new'))
                # Re-enable type enforcement
                core.setConfOpt('enforce', 1)

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
                self.gt(node[1].get('node:created'), 1483228800000)
                self.eq(node[1].get('foo:bar'), 'I am a bar foo.')
                self.none(node[1].get('foo:bar:duck'))

            with s_cortex.openurl('sqlite:///%s' % (path,)) as core:
                self.eq(core.getModlVers('test'), 0)
                # We are unable to form a node with the custom type with enforce enabled
                self.raises(NoSuchForm, core.formTufoByProp, 'foo:bar', 'I am a bar foo.')
                # But if we disable we can get the node which exists in the cortex
                core.setConfOpt('enforce', 0)
                node = core.formTufoByProp('foo:bar', 'I am a bar foo.')
                self.false(node[1].get('.new'))
                # Re-enable type enforcement
                core.setConfOpt('enforce', 1)

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

        with self.getRamCore() as core:
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

        with self.getRamCore() as core:
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
                    self.gt(actual[0][1]['node:created'], 1483228800000)
                    self.eq(actual[0][1]['inet:fqdn'], 'vertex.link')
                    self.eq(actual[0][1]['inet:fqdn:zone'], 1)

                    self.isinstance(actual[1], tuple)
                    self.eq(actual[1][0], None)
                    self.eq(actual[1][1]['tufo:form'], 'syn:err')
                    # NOTE: ephemeral data does not get node:created
                    self.eq(actual[1][1]['syn:err'], 'BadTypeValu')
                    for s in ['BadTypeValu', 'name=', 'inet:url', 'valu=', 'bad']:
                        self.isin(s, actual[1][1]['syn:err:errmsg'])

                    self.isinstance(actual[2], tuple)
                    self.eq(actual[2][0], None)
                    self.eq(actual[2][1]['tufo:form'], 'syn:err')
                    # NOTE: ephemeral data does not get node:created
                    self.eq(actual[2][1]['syn:err'], 'NoSuchForm')
                    for s in ['NoSuchForm', 'name=', 'bad']:
                        self.isin(s, actual[2][1]['syn:err:errmsg'])

    def test_cortex_reqprops(self):

        with self.getRamCore() as core:
            core.setConfOpt('enforce', 0)
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

        with self.getRamCore() as core:

            core.addDataModel('hehe', {'forms': (
                ('hehe:haha', {'ptype': 'str'}, (
                    ('hoho', {'ptype': 'int'}),
                )),
            )})

            core.addRuntNode('hehe:haha', 'woot', props={'hoho': 20, 'lulz': 'rofl'})

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

            node = core.addRuntNode('hehe:haha', 'ohmy')
            self.eq(node[1].get('hehe:haha:hoho'), None)

    def test_cortex_trigger(self):

        with self.getRamCore() as core:

            node = core.formTufoByProp('syn:trigger', '*', on='node:add form=inet:fqdn', run='[ #foo ]', en=1)
            self.eq(node[1].get('syn:trigger:on'), 'node:add form=inet:fqdn')
            self.eq(node[1].get('syn:trigger:run'), '[ #foo ]')

            node = core.formTufoByProp('syn:trigger', '*', on='node:tag:add form=inet:fqdn tag=foo', run='[ #baz ]', en=1)

            node = core.formTufoByProp('inet:fqdn', 'vertex.link')

            self.nn(node[1].get('#foo'))
            self.nn(node[1].get('#baz'))

    def test_cortex_auth(self):

        conf = {'auth:en': 1, 'auth:admin': 'rawr@vertex.link'}

        with self.getDirCore(conf=conf) as core:

            self.true(core.auth.users.get('rawr@vertex.link').admin)

            visi = core.auth.addUser('visi@vertex.link')
            newb = core.auth.addUser('newb@vertex.link')

            visi.addRule(('node:add', {'form': 'inet:ipv4'}))
            visi.addRule(('node:del', {'form': 'inet:ipv4'}))
            visi.addRule(('node:prop:set', {'form': 'inet:ipv4', 'prop': 'cc'}))

            visi.addRule(('node:tag:add', {'tag': 'foo'}))
            visi.addRule(('node:tag:del', {'tag': 'foo'}))

            with s_auth.runas('newp@fake.com'):
                retn = core.ask('[ inet:ipv4=1.2.3.4 ]')
                self.eq(retn['oplog'][-1]['excinfo']['err'], 'NoSuchUser')

            with s_auth.runas('newb@vertex.link'):
                retn = core.ask('[ inet:ipv4=1.2.3.4 ]')
                self.eq(retn['oplog'][-1]['excinfo']['err'], 'AuthDeny')

            with s_auth.runas('visi@vertex.link'):
                retn = core.ask('[ inet:ipv4=1.2.3.4 ]')
                self.eq(retn['data'][0][1].get('inet:ipv4'), 0x01020304)

            with s_auth.runas('newb@vertex.link'):
                retn = core.ask('inet:ipv4=1.2.3.4 delnode(force=1)')
                self.eq(retn['oplog'][-1]['excinfo']['err'], 'AuthDeny')

            with s_auth.runas('newb@vertex.link'):
                retn = core.ask('inet:ipv4=1.2.3.4 [ :cc=us ]')
                self.eq(retn['oplog'][-1]['excinfo']['err'], 'AuthDeny')

            with s_auth.runas('visi@vertex.link'):
                retn = core.ask('inet:ipv4=1.2.3.4 [ :cc=us ]')
                self.eq(retn['data'][0][1].get('inet:ipv4:cc'), 'us')

            with s_auth.runas('newb@vertex.link'):
                retn = core.ask('inet:ipv4=1.2.3.4 [ +#foo ]')
                self.eq(retn['oplog'][-1]['excinfo']['err'], 'AuthDeny')

            with s_auth.runas('visi@vertex.link'):
                retn = core.ask('inet:ipv4=1.2.3.4 [ +#foo ]')
                self.nn(retn['data'][0][1].get('#foo'))

            with s_auth.runas('newb@vertex.link'):
                retn = core.ask('inet:ipv4=1.2.3.4 [ -#foo ]')
                self.eq(retn['oplog'][-1]['excinfo']['err'], 'AuthDeny')

            with s_auth.runas('visi@vertex.link'):
                retn = core.ask('inet:ipv4=1.2.3.4 [ -#foo ]')
                self.none(retn['data'][0][1].get('#foo'))

            with s_auth.runas('newb@vertex.link'):
                retn = core.ask('inet:ipv4=1.2.3.4 delnode(force=1)')
                self.eq(retn['oplog'][-1]['excinfo']['err'], 'AuthDeny')

            with s_auth.runas('visi@vertex.link'):
                retn = core.ask('inet:ipv4=1.2.3.4 delnode(force=1)')
                self.len(0, core.eval('inet:ipv4'))

            with s_auth.runas('newb@vertex.link'):
                self.len(1, core.splices([('node:add', {'form': 'inet:ipv4', 'valu': 0x01020304})]))

            self.none(core.getTufoByProp('inet:ipv4', 0x01020304))

            with s_auth.runas('visi@vertex.link'):
                self.len(0, core.splices([('node:add', {'form': 'inet:ipv4', 'valu': 0x01020304})]))

            self.nn(core.getTufoByProp('inet:ipv4', 0x01020304))

            with s_auth.runas('rawr@vertex.link'):

                retn = core.ask('inet:ipv4=1.2.3.4 delnode(force=1)')
                self.eq(retn['oplog'][-1]['excinfo']['err'], 'AuthDeny')

                retn = core.ask('inet:ipv4=1.2.3.4 sudo() delnode(force=1)')
                self.none(retn['oplog'][-1].get('excinfo'))

    def test_cortex_formtufobytufo(self):
        with self.getRamCore() as core:
            _t0iden = guid()
            _t0 = (_t0iden, {'tufo:form': 'inet:ipv4', 'inet:ipv4': '1.2.3.4', 'inet:ipv4:asn': 1024})
            t0 = core.formTufoByTufo(_t0)
            form, valu = s_tufo.ndef(t0)
            self.eq(form, 'inet:ipv4')
            self.eq(valu, 0x01020304)
            self.eq(t0[1].get('inet:ipv4:asn'), 1024)
            self.eq(t0[1].get('inet:ipv4:cc'), '??')
            self.ne(t0[0], _t0iden)

            t1 = core.formTufoByTufo((None, {'tufo:form': 'strform', 'strform': 'oh hai',
                                             'strform:haha': 1234, 'strform:foo': 'sup'}))

            form, valu = s_tufo.ndef(t1)
            self.gt(t1[1]['node:created'], 1483228800000)
            self.eq(form, 'strform')
            self.eq(valu, 'oh hai')
            self.eq(t1[1].get('strform:foo'), 'sup')
            self.none(t1[1].get('strform:bar'))
            self.none(t1[1].get('strform:baz'))
            self.none(t1[1].get('strform:haha'))

    def test_cortex_universal_props(self):
        with self.getRamCore() as core:
            myfo = core.myfo

            node = core.getTufoByProp('node:ndef', '90ec8b92deda626d31e2d63e8dbf48be')
            self.eq(node[0], myfo[0])

            node = core.getTufoByProp('tufo:form', 'syn:core')
            self.eq(node[0], myfo[0])

            nodes = core.getTufosByProp('node:created', myfo[1].get('node:created'))
            self.ge(len(nodes), 1)
            rvalu = core.getPropRepr('node:created', myfo[1].get('node:created'))
            self.isinstance(rvalu, str)
            nodes2 = core.getTufosByProp('node:created', rvalu)
            self.eq(len(nodes), len(nodes2))

            # We can have a data model which has a prop which is a ndef type
            modl = {
                'types': (
                    ('ndefxref', {'subof': 'comp', 'fields': 'ndef,node:ndef|strdude,strform|time,time'}),
                ),
                'forms': (
                    ('ndefxref', {}, (
                        ('ndef', {'req': 1, 'ro': 1, 'doc': 'ndef to a node', 'ptype': 'ndef'}),
                        ('strdude', {'req': 1, 'ro': 1, 'doc': 'strform thing', 'ptype': 'strform'}),
                        ('time', {'req': 1, 'ro': 1, 'doc': 'time thing was seen', 'ptype': 'time'})
                    )),
                )
            }
            core.addDataModel('unitst', modl)

            # Make an node which refers to another node by its node:ndef value
            node = core.formTufoByProp('ndefxref', '(90ec8b92deda626d31e2d63e8dbf48be,"hehe","2017")')
            self.nn(node)
            self.isin('.new', node[1])

            # We can also provide values which will be prop-normed by the NDefType
            # This means we can create arbitrary linkages which may eventually exist
            nnode = core.formTufoByProp('ndefxref', '((syn:core,self),"hehe","2017")')
            self.notin('.new', nnode[1])
            self.eq(node[0], nnode[0])
            self.nn(core.getTufoByProp('strform', 'hehe'))

            # Use storm to pivot across this node to the ndef node
            nodes = core.eval('ndefxref :ndef->node:ndef')
            self.len(1, nodes)
            self.eq(nodes[0][0], myfo[0])

            # Use storm to pivot from the ndef node to the ndefxref node
            nodes = core.eval('syn:core=self node:ndef->ndefxref:ndef')
            self.len(1, nodes)
            self.eq(nodes[0][0], node[0])

            # Lift nodes by node:created text timestamp
            nodes = core.eval('node:created>={}'.format(rvalu))
            self.ge(len(nodes), 3)

            # We can add a new universal prop via API
            nprop = core.addPropDef('node:tstfact',
                                    ro=1,
                                    univ=1,
                                    ptype='str:lwr',
                                    doc='A fact about a node.',
                                    )
            self.isinstance(nprop, tuple)
            self.isin('node:tstfact', core.getUnivProps())
            self.notin('node:tstfact', core.unipropsreq)
            self.nn(core.getPropDef('node:tstfact'))

            node = core.formTufoByProp('inet:ipv4', 0x01020304)
            self.nn(node)
            self.notin('node:tstfact', node[1])
            # Set the non-required prop via setTufoProps()
            node = core.setTufoProps(node, **{'node:tstfact': ' THIS node is blue.  '})
            self.eq(node[1].get('node:tstfact'), 'this node is blue.')

            # The uniprop is ro and cannot be changed once set
            node = core.setTufoProps(node, **{'node:tstfact': 'hehe'})
            self.eq(node[1].get('node:tstfact'), 'this node is blue.')

            # We can have a mutable, non ro universal prop on a node though!
            nprop = core.addPropDef('node:tstopinion',
                                    univ=1,
                                    ptype='str:lwr',
                                    doc='A opinion about a node.',
                                    )
            node = core.setTufoProps(node, **{'node:tstopinion': ' THIS node is good Ash.  '})
            self.eq(node[1].get('node:tstopinion'), 'this node is good ash.')

            # We can change the prop of the uniprop on this node.
            node = core.setTufoProps(node, **{'node:tstopinion': 'this node is BAD ash.'})
            self.eq(node[1].get('node:tstopinion'), 'this node is bad ash.')

            # Lastly - we can add a universal prop which is required but breaks node creation
            # Do NOT do this in the real world - its a bad idea.
            nprop = core.addPropDef('node:tstevil',
                                    univ=1,
                                    req=1,
                                    ptype='bool',
                                    doc='No more nodes!',
                                    )
            self.nn(nprop)
            self.raises(PropNotFound, core.formTufoByProp, 'inet:ipv4', 0x01020305)
            # We can add a node:add handler to populate this new universal prop though!
            def foo(mesg):
                fulls = mesg[1].get('props')
                fulls['node:tstevil'] = 1
            core.on('node:form', foo)
            # We can form nodes again, but they're all evil.
            node = core.formTufoByProp('inet:ipv4', 0x01020305)
            self.nn(node)
            self.eq(node[1].get('node:tstevil'), 1)
            core.off('node:form', foo)

            # We cannot add a universal prop which is associated with a form
            self.raises(BadPropConf, core.addPropDef, 'node:poorform', univ=1, req=1, ptype='bool', form='file:bytes')

    def test_cortex_gettasks(self):
        with self.getRamCore() as core:

            def f1(mesg):
                pass

            def f2(mesg):
                pass

            core.on('task:hehe:haha', f1)
            core.on('task:hehe:haha', f2)
            core.on('task:wow', f1)

            tasks = core.getCoreTasks()
            self.len(2, tasks)
            self.isin('hehe:haha', tasks)
            self.isin('wow', tasks)

    def test_cortex_dynalias(self):
        conf = {
            'ctors': [
                [
                    'core',
                    'syn:cortex',
                    {
                        'url': 'ram:///',
                        'storm:query:log:en': 1,
                        'modules': [
                            [
                                'synapse.tests.test_cortex.CoreTestModule',
                                {'foobar': True}
                            ]
                        ]
                    }
                ]
            ],
            'share': [
                [
                    'core',
                    {}
                ]
            ],
            'listen': [
                'tcp://0.0.0.0:0/'
            ]
        }

        with s_daemon.Daemon() as dmon:
            dmon.loadDmonConf(conf)
            link = dmon.links()[0]
            port = link[1].get('port')
            with s_cortex.openurl('tcp://0.0.0.0/core', port=port) as prox:
                self.isin('synapse.tests.test_cortex.CoreTestModule', prox.getCoreMods())
                self.eq(prox.getConfOpt('storm:query:log:en'), 1)

    def test_cortex_axon(self):
        self.skipLongTest()

        visihash = hashlib.sha256(b'visi').digest()
        craphash = hashlib.sha256(b'crap').digest()
        foobarhash = hashlib.sha256(b'foobar').digest()

        with self.getAxonCore() as env:
            env.core.setConfOpt('cellpool:timeout', 3)

            core = s_telepath.openurl(env.core_url)
            env.add('_core_prox', core, fini=True)  # ensure the Proxy object is fini'd

            wants = core._axonclient_wants([visihash, craphash, foobarhash])
            self.len(3, wants)
            self.istufo(core.formNodeByBytes(b'visi'))
            with io.BytesIO(b'foobar') as fd:
                self.istufo(core.formNodeByFd(fd))
            wants = core._axonclient_wants([visihash, craphash, foobarhash])
            self.len(1, wants)

            # Pull out the axon config an shut it down
            axonpath = os.path.split(env.axon.getCellPath())[0]
            axonconf = env.axon.getConfOpts()
            env.axon.fini()
            env.axon.waitfini(timeout=30)

            # Make sure that it doesn't work
            self.raises(Exception, core._axonclient_wants, [visihash, craphash, foobarhash], timeout=2)
            # Turn the axon back on
            w = env.core.cellpool.waiter(1, 'cell:add')
            axon = s_axon.AxonCell(axonpath, axonconf)
            env.add('axon', axon, fini=True)
            self.true(axon.cellpool.neurwait(timeout=3))
            # Make sure the api still works.
            self.nn(w.wait(4))
            wants = core._axonclient_wants([visihash, craphash, foobarhash])

            self.len(1, wants)

            neurhost, neurport = env.neuron.getCellAddr()
            axonauth = env.axon.getCellAuth()
            axonauth = enbase64(s_msgpack.en(axonauth))
            # Ensure that Axon fns do not execute on a core without an axon
            with self.getRamCore() as othercore:
                othercore.setConfOpt('cellpool:timeout', 3)
                self.raises(NoSuchOpt, othercore.formNodeByBytes, b'visi', name='visi.bin')
                with io.BytesIO(b'foobar') as fd:
                    self.raises(NoSuchOpt, othercore.formNodeByFd, fd, name='foobar.exe')

                othercore.setConfOpt('cellpool:conf', {'fake': 'fake'})
                self.false(othercore.axon_ready)
                self.false(othercore.cellpool_ready)
                othercore.setConfOpt('cellpool:conf', {'auth': axonauth})
                self.false(othercore.axon_ready)
                self.false(othercore.cellpool_ready)
                othercore.setConfOpt('cellpool:conf', {'auth': axonauth, 'host': neurhost})
                self.false(othercore.cellpool_ready)
                self.false(othercore.axon_ready)

                othercore.setConfOpt('cellpool:conf', {'auth': axonauth, 'host': neurhost, 'port': neurport + 99})
                self.false(othercore.cellpool_ready)
                self.false(othercore.axon_ready)

                othercore.setConfOpt('cellpool:conf', {'auth': axonauth, 'host': neurhost, 'port': neurport})
                self.true(othercore.cellpool_ready)
                self.false(othercore.axon_ready)

                othercore.setConfOpt('axon:name', 'axon@localhost')
                self.true(othercore.axon_ready)

                wants = othercore._axonclient_wants([visihash, craphash, foobarhash])
                self.len(1, wants)
                self.istufo(othercore.formNodeByBytes(b'crap'))
                wants = othercore._axonclient_wants([visihash, craphash, foobarhash])
                self.len(0, wants)

            # ensure that we can configure a cellpool/axon via conf options
            conf = {
                'cellpool:conf': {'auth': axonauth, 'host': neurhost, 'port': neurport},
                'axon:name': 'axon@localhost',
                'cellpool:timeout': 6,
            }
            with s_cortex.openurl('ram://', conf) as rcore:
                wants = rcore._axonclient_wants([visihash, craphash, foobarhash])
                self.len(0, wants)

    def test_cortex_splice_examples(self):

        with self.getRamCore() as core:

            node_add_splice = ('node:add', {
                    'form': 'inet:fqdn',
                    'valu': 'vertex.link',
                    'tags': ['hehe.haha'],
                    'props': {'expires': '2017'},
                })
            node_add_splice_props = ('node:add', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'props': {'expires': '2018'},
            })
            node_add_splice_tags = ('node:add', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'tags': ('foo.bar',
                         'oh.my')
            })
            node_prop_set_splice = ('node:prop:set', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'prop': 'expires',
                'newv': '2019',
            })
            node_prop_del_splice = ('node:prop:del', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'prop': 'expires',
            })
            node_tag_add_splice = ('node:tag:add', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'tag': 'hehe.haha',
            })
            node_tag_add_splice2 = ('node:tag:add', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'tag': 'hehe.woah',
                'ival': (1514764800000, 1546300800000),
            })
            node_tag_del_splice = ('node:tag:del', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'tag': 'hehe.woah',
            })
            node_tag_del_splice2 = ('node:tag:del', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'tag': 'hehe',
            })
            node_ival_set_splice = ('node:ival:set', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'prop': '#woah',
                'ival': (100, 200)
            })
            node_ival_del_splice = ('node:ival:del', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
                'prop': '#woah',
            })
            node_del_splice = ('node:del', {
                'form': 'inet:fqdn',
                'valu': 'vertex.link',
            })

            splices = (node_add_splice,)

            core.splices(splices)
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.nn(node)
            self.nn(node[1].get('#hehe.haha'))
            self.eq(node[1].get('inet:fqdn:expires'), 1483228800000)

            core.splice(node_add_splice_props)
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.eq(node[1].get('inet:fqdn:expires'), 1514764800000)

            core.splice(node_add_splice_tags)
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.true(s_tufo.tagged(node, 'foo.bar'))
            self.true(s_tufo.tagged(node, 'oh.my'))

            core.splices((node_prop_set_splice,))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.eq(node[1].get('inet:fqdn:expires'), 1546300800000)

            core.splices((node_prop_del_splice,))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.none(node[1].get('inet:fqdn:expires'))

            core.splices((node_tag_add_splice, node_tag_add_splice2))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.true(s_tufo.tagged(node, 'hehe'))
            self.true(s_tufo.tagged(node, 'hehe.haha'))
            self.true(s_tufo.tagged(node, 'hehe.woah'))
            ival = s_tufo.ival(node, '#hehe.woah')
            self.len(2, ival)

            core.splices((node_tag_del_splice,))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.true(s_tufo.tagged(node, 'hehe'))
            self.true(s_tufo.tagged(node, 'hehe.haha'))
            self.false(s_tufo.tagged(node, 'hehe.woah'))

            core.splices((node_tag_del_splice2,))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.false(s_tufo.tagged(node, 'hehe'))
            self.false(s_tufo.tagged(node, 'hehe.haha'))
            self.false(s_tufo.tagged(node, 'hehe.woah'))

            core.splices((node_ival_set_splice,))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.eq(node[1].get('<#woah'), 200)
            self.eq(node[1].get('>#woah'), 100)

            core.splices((node_ival_del_splice,))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.none(node[1].get('<#woah'))
            self.none(node[1].get('>#woah'))

            core.splices((node_del_splice,))
            node = core.getTufoByProp('inet:fqdn', 'vertex.link')
            self.none(node)

            # set / del splices do not make nodes
            events = []
            core.link(events.append)
            splices = (
                node_prop_set_splice,
                node_prop_del_splice,
                node_ival_del_splice,
                node_ival_set_splice,
                node_tag_add_splice,
                node_tag_add_splice2,
                node_tag_del_splice,
                node_tag_del_splice2,
                node_del_splice
            )
            core.splices(splices)
            self.eq(events, [])
            core.unlink(events.append)

    def test_cortex_aware(self):
        with self.getSslCore(configure_roles=True) as proxies:
            uprox, rprox = proxies  # type: s_cores_common.CoreApi, s_cores_common.CoreApi

            # The core is inaccessible
            self.raises(NoSuchMeth, uprox.delRowsByProp, 'strform', )

            self.gt(len(uprox.getCoreMods()), 1)
            self.len(1, uprox.eval('[strform="bob grey"]'))
            data = rprox.ask('sudo() [strform=pennywise] addtag(clown)')
            self.len(1, data.get('data'))

            node = rprox.getTufoByProp('strform', 'bob grey')
            self.istufo(node)
            nodes = rprox.getTufosByProp('strform')
            self.len(2, nodes)

            node = uprox.addTufoTags(node, ['alias'])
            self.true(s_tufo.tagged(node, 'alias'))

            node = rprox.delTufoTag(node, 'alias')
            self.false(s_tufo.tagged(node, 'alias'))

            node = uprox.setTufoProp(node, 'foo', 'bar')
            self.eq(node[1].get('strform:foo'), 'bar')

            # Splices can go in
            msgs = [('node:add', {'form': 'intform', 'valu': 0})]
            logs = uprox.splices(msgs)
            self.len(0, logs)
            node = rprox.getTufoByProp('intform', 0)
            self.istufo(node)

            iden = node[0]
            # Can retrieve raw rows
            rows = uprox.getRowsBy('range', 'intform', (-1, 1))
            self.len(1, rows)
            rows = uprox.getRowsByProp('intform')
            self.len(1, rows)
            rows = uprox.getRowsById(iden)
            self.gt(len(rows), 1)
            rows = uprox.getRowsByIdProp(iden, 'intform')
            self.len(1, rows)

            # Can retrieve by getTufo APIs
            node[1].pop('.new', None)
            self.eq(node, uprox.getTufoByIden(iden))
            self.eq((node,), uprox.getTufosByIdens((iden,)))
            nodes = uprox.getTufosByTag('clown')
            self.len(1, nodes)

            nodes = uprox.getTufosBy('range', 'intform', (-1, 1))
            self.len(1, nodes)

            items = (('strform', 'a', {}),
                     ('notaform', 2, {}),
                     )
            ret = rprox.formTufosByProps(items)
            self.len(2, ret)
            self.nn(ret[0][0])  # real node
            self.none(ret[1][0])  # ephemeral node

            # Metadata APIs
            self.true(rprox.isDataModl('tst'))
            self.true(rprox.isDataType('intform'))
            self.isinstance(rprox.getConfDefs(), dict)
            self.isinstance(rprox.getModelDict(), dict)
            self.eq(rprox.getPropNorm('intform', '2')[0], 2)
            self.eq(rprox.getPropRepr('intform', 2)[0], '2')
            self.eq(rprox.getTypeNorm('intform', '2')[0], 2)
            self.eq(rprox.getTypeRepr('intform', 2)[0], '2')
            uniprops = rprox.getUnivProps()
            self.isinstance(uniprops, tuple)

            self.raises(s_exc.AuthDeny, uprox.getConfOpts)
            self.isinstance(rprox.getConfOpts(), dict)

            name, modl = 'woot', {
                'forms': (
                    ('hehe:haha', {'ptype': 'str'}, (
                        ('hoho', {'ptype': 'str', 'req': 1}),
                    )),
                ),
            }
            self.raises(s_exc.AuthDeny, uprox.addDataModel, name, modl)
            rprox.addDataModel(name, modl)
            self.true(rprox.isDataModl(name))

            # formNodeByBytes/formNodeByFd support used by pushfile
            self.istufo(uprox.formNodeByBytes(b'woot', stor=False))
            with io.BytesIO(b'foobar') as fd:
                self.istufo(uprox.formNodeByFd(fd, stor=False))

            node = uprox.formTufoByProp('syn:trigger', '*', user='user@localhost',
                                       on='node:add form=intform', run='[ #foo ]', en=1)
            self.istufo(node)
            node = uprox.eval('[intform=443]')[0]
            self.true(s_tufo.tagged(node, 'foo'))

            # Destructive to the test state - run last
            isok, retn = rprox.authReact(('auth:del:user', {'user': 'user@localhost'}))
            self.true(isok)
            msgs = [('node:add', {'form': 'intform', 'valu': 100})]
            logs = uprox.splices(msgs)
            self.eq(logs[0][1]['err'], 'NoSuchUser')

            logs = rprox.splices(msgs)
            self.eq(logs, ())
            node = rprox.eval('intform=100')[0]
            self.false(s_tufo.tagged(node, 'foo'))

            # Tear down the proxies
            rprox.fini()
            uprox.fini()

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
                rows.append(('1234', 'node:created', 1483228800000, tick))
                store.addRows(rows)

            # Retrieve the node via the Cortex interface
            with s_cortex.openurl(url) as core:
                node = core.getTufoByIden('1234')
                self.nn(node)
                self.eq(node[1].get('tufo:form'), 'foo:bar')
                self.eq(node[1].get('node:created'), 1483228800000)
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
                rows.append(('1234', 'node:created', 1483228800000, tick))
                store.addRows(rows)

            # Retrieve the node via the Cortex interface
            with s_cortex.openurl(url) as core:
                node = core.getTufoByIden('1234')
                self.nn(node)
                self.eq(node[1].get('tufo:form'), 'foo:bar')
                self.eq(node[1].get('node:created'), 1483228800000)
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

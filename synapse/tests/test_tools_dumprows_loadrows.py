# -*- coding: utf-8 -*-
"""
synapse - test_tools_dumprows_loadrows.py
Created on 7/26/17.

Unittests for the dumprows and loadrows tools.
"""
import gzip

import synapse.lib.const as s_const
import synapse.lib.msgpack as s_msgpack

import synapse.tools.dumprows as s_dumprows
import synapse.tools.loadrows as s_loadrows

from synapse.tests.common import *

log = logging.getLogger(__name__)

class DumpRowsTest(SynTest):

    def make_sql_genrows_json(self, fp):
        d = {'slicebytes': 2, 'incvalu': 4}
        with open(fp, 'wb') as f:
            f.write(json.dumps(d, indent=2, sort_keys=True).encode())

    def test_simple_use(self):
        self.thisHostMustNot(platform='darwin')
        outp = self.getTestOutp()
        with self.getTestDir() as temp:
            fp = os.path.join(temp, 'dumpfile.mpk')
            new_db = os.path.join(temp, 'test.db')
            sqlite_url = 'sqlite:///{}'.format(new_db)
            with s_cortex.openurl(sqlite_url) as core:
                self.true(core.isnew)
                core.setBlobValu('syn:test:tel', 8675309)
                with core.getCoreXact():
                    core.formTufoByProp('inet:ipv4', 0x01020304)
                    for i in range(1000):
                        core.formTufoByProp('inet:ipv4', i)

            # Now dump that sqlite core
            argv = ['-s', sqlite_url, '-o', fp]
            ret = s_dumprows.main(argv, outp)
            self.eq(ret, 0)

            # Now ensure our .mpk file is correct
            with open(fp, 'rb') as fd:
                gen = s_msgpack.iterfd(fd)
                evt = next(gen)
                self.eq(evt[0], 'syn:cortex:rowdump:info')
                self.eq(evt[1].get('rows:compress'), False)
                self.eq(evt[1].get('synapse:rows:output'), fp)
                self.eq(evt[1].get('synapse:cortex:input'), sqlite_url)
                self.eq(evt[1].get('synapse:cortex:blob_store'), False)
                self.eq(evt[1].get('synapse:cortex:revstore'), False)
                self.eq(evt[1].get('python:version'), version)
                self.isin('synapse:version', evt[1])
                first_data = next(gen)
                self.eq(first_data[0], 'core:save:add:rows')
                self.isin('rows', first_data[1])
                rows = first_data[1].get('rows')
                self.isinstance(rows, tuple)
                self.isinstance(rows[0], tuple)
                self.eq(len(rows[0]), 4)
                # Expensive but worth checking
                event_types = set()
                event_types.add(first_data[0])
                total_rows = 0
                for evt in gen:
                    event_types.add(evt[0])
                    if 'rows' in evt[1]:
                        total_rows = total_rows + len(evt[1].get('rows'))
                self.gt(total_rows + len(first_data[1]['rows']), 1000)
                self.eq(event_types, {'core:save:add:rows'})

    def test_simple_compress(self):
        self.thisHostMustNot(platform='darwin')
        outp = self.getTestOutp()
        with self.getTestDir() as temp:
            fp = os.path.join(temp, 'dumpfile.mpk')
            new_db = os.path.join(temp, 'test.db')
            sqlite_url = 'sqlite:///{}'.format(new_db)
            with s_cortex.openurl(sqlite_url) as core:
                self.true(core.isnew)
                core.setBlobValu('syn:test:tel', 8675309)
                core.formTufoByProp('inet:ipv4', 0x01020304)
            # Now dump that sqlite core
            argv = ['-s', sqlite_url, '-o', fp, '--compress']
            ret = s_dumprows.main(argv, outp)
            self.eq(ret, 0)

            # Now ensure our .mpk file is correct
            with open(fp, 'rb') as fd:
                gen = s_msgpack.iterfd(fd)
                evt = next(gen)
                self.eq(evt[0], 'syn:cortex:rowdump:info')
                self.eq(evt[1].get('rows:compress'), True)
                evt = next(gen)
                self.eq(evt[0], 'core:save:add:rows')
                self.isin('rows', evt[1])
                rows = evt[1].get('rows')
                # we decode the rows blob not in place but separately here
                rows = s_msgpack.un(gzip.decompress(rows))
                self.isinstance(rows, tuple)
                self.isinstance(rows[0], tuple)
                self.eq(len(rows[0]), 4)
                # Expensive but worth checking
                event_types = set()
                event_types.add(evt[0])
                for evt in gen:
                    event_types.add(evt[0])
                self.eq(event_types, {'core:save:add:rows'})

    def test_blob_dump(self):
        self.thisHostMustNot(platform='darwin')
        outp = self.getTestOutp()
        with self.getTestDir() as temp:
            fp = os.path.join(temp, 'dumpfile.mpk')
            new_db = os.path.join(temp, 'test.db')
            sqlite_url = 'sqlite:///{}'.format(new_db)
            with s_cortex.openurl(sqlite_url) as core:
                self.true(core.isnew)
                core.setBlobValu('syn:test:tel', 8675309)
                core.formTufoByProp('inet:ipv4', 0x01020304)

            # Now dump that sqlite core
            argv = ['-s', sqlite_url, '-o', fp, '--dump-blobstore']
            ret = s_dumprows.main(argv, outp)
            self.eq(ret, 0)

            # Now ensure our .mpk file is correct
            with open(fp, 'rb') as fd:
                gen = s_msgpack.iterfd(fd)
                evt = next(gen)
                self.eq(evt[0], 'syn:cortex:rowdump:info')
                self.eq(evt[1].get('synapse:cortex:blob_store'), True)
                evt = next(gen)
                self.eq(evt[0], 'core:save:add:rows')
                self.isin('rows', evt[1])
                rows = evt[1].get('rows')
                self.isinstance(rows, tuple)
                self.isinstance(rows[0], tuple)
                self.eq(len(rows[0]), 4)
                # Expensive but worth checking
                event_types = set()
                event_types.add(evt[0])
                for evt in gen:
                    event_types.add(evt[0])
                self.eq(event_types, {'core:save:add:rows', 'syn:core:blob:set'})

    def test_dump_force(self):
        self.thisHostMustNot(platform='darwin')
        outp = self.getTestOutp()
        with self.getTestDir() as temp:
            fp = os.path.join(temp, 'dumpfile.mpk')
            new_db = os.path.join(temp, 'test.db')
            sqlite_url = 'sqlite:///{}'.format(new_db)
            with s_cortex.openurl(sqlite_url) as core:
                self.true(core.isnew)
                core.setBlobValu('syn:test:tel', 8675309)
                core.formTufoByProp('inet:ipv4', 0x01020304)

            # Now dump that sqlite core
            argv = ['-s', sqlite_url, '-o', fp]
            ret = s_dumprows.main(argv, outp)
            self.eq(ret, 0)

            outp = self.getTestOutp()
            argv = ['-s', sqlite_url, '-o', fp]
            ret = s_dumprows.main(argv, outp)
            self.eq(ret, 1)
            self.true('Cannot overwrite a backup.' in str(outp))

            outp = self.getTestOutp()
            # Now dump that sqlite core
            argv = ['-s', sqlite_url, '-o', fp, '-f']
            ret = s_dumprows.main(argv, outp)
            self.eq(ret, 0)

    def test_dump_largecore(self):
        self.skipLongTest()
        self.thisHostMustNot(platform='darwin')
        # This ensure we're executing the "dump rows
        # when we have N number of bytes cached codepath.
        # Unfortunately this is a bit slow (2-4 seconds).
        ntufos = 40000
        outp = self.getTestOutp()
        with self.getTestDir() as temp:
            fp = os.path.join(temp, 'dumpfile.mpk')
            new_db = os.path.join(temp, 'test.db')
            sqlite_url = 'sqlite:///{}'.format(new_db)
            with s_cortex.openurl(sqlite_url) as core:
                self.true(core.isnew)
                rows = []
                tick = now()
                for i in range(1, ntufos):
                    iden = guid()
                    rows.append((iden, 'tufo:form', 'inet:asn', tick))
                    rows.append((iden, 'inet:asn', i, tick))
                    rows.append((iden, 'inet:asn:name', '??', tick))
                core.addRows(rows)
                q = 'SELECT count(1) from {}'.format(core.store._getTableName())
                num_core_rows = core.store.select(q)[0][0]

            # Now dump that sqlite core
            argv = ['-s', sqlite_url, '-o', fp]
            ret = s_dumprows.main(argv, outp)
            self.eq(ret, 0)

            stat = os.stat(fp)
            self.gt(stat.st_size, s_const.mebibyte * 4)

            # Now ensure our .mpk file is correct
            with open(fp, 'rb') as fd:
                msgpk_rows = 0
                for evt in s_msgpack.iterfd(fd):
                    if 'rows' in evt[1]:
                        msgpk_rows = msgpk_rows + len(evt[1].get('rows'))
            self.eq(num_core_rows, msgpk_rows)

class LoadRowsTest(SynTest):

    def make_sql_genrows_json(self, fp):
        d = {'slicebytes': 2, 'incvalu': 4}
        with open(fp, 'wb') as f:
            f.write(json.dumps(d, indent=2, sort_keys=True).encode())

    def test_savefile_load(self):
        self.thisHostMustNot(platform='darwin')
        outp = self.getTestOutp()
        with self.getTestDir() as temp:
            # Prepare a savefile to load from a ram core
            fp = os.path.join(temp, 'savefile.mpk')
            new_db = os.path.join(temp, 'test.db')
            sqlite_url = 'sqlite:///{}'.format(new_db)
            with s_cortex.openurl('ram:///', savefile=fp) as core:
                self.true(core.isnew)
                node = core.formTufoByProp('inet:ipv4', 0x01020304)
                self.true('.new' in node[1])
                core.setBlobValu('foo:bar', ('tufo', {'test': 'value'}))
                rammyfo = core.myfo
            argv = ['-s', sqlite_url, '-i', fp]
            # Execute loadrows tool to create the sqlite store and load the rows
            ret = s_loadrows.main(argv, outp)
            self.eq(ret, 0)
            self.true('Restoring from a savefile' in str(outp))
            with s_cortex.openurl(sqlite_url) as core:
                self.false(core.isnew)
                self.eq(core.myfo[0], rammyfo[0])
                node = core.formTufoByProp('inet:ipv4', 0x01020304)
                self.true('.new' not in node[1])
                self.eq(core.getBlobValu('foo:bar'), ('tufo', {'test': 'value'}))

    def test_dumprows_load(self):
        self.thisHostMustNot(platform='darwin')
        outp = self.getTestOutp()
        with self.getTestDir() as temp:
            # Make a sqlite cortex and the associated dupmfile for it
            fp = os.path.join(temp, 'dumpfile.mpk')
            genrows_json_fp = os.path.join(temp, 'genrows.json')
            self.make_sql_genrows_json(genrows_json_fp)
            old_db = os.path.join(temp, 'old.db')
            new_db = os.path.join(temp, 'new.db')
            sqlite_url_old = 'sqlite:///{}'.format(old_db)
            sqlite_url_new = 'sqlite:///{}'.format(new_db)

            with s_cortex.openurl(sqlite_url_old) as core:
                self.true(core.isnew)
                node = core.formTufoByProp('inet:ipv4', 0x01020304)
                self.true('.new' in node[1])
                core.setBlobValu('foo:bar', ('tufo', {'test': 'value'}))

            # Dump that core and its blobstore to a dumpfile
            dump_argv = ['-s', sqlite_url_old, '-o', fp, '--dump-blobstore', '-e', genrows_json_fp]
            ret = s_dumprows.main(dump_argv, outp)
            self.eq(ret, 0)

            # Execute loadrows tool to create the sqlite store and load the rows
            argv = ['-s', sqlite_url_new, '-i', fp]
            ret = s_loadrows.main(argv, outp)
            self.eq(ret, 0)
            self.true('Restoring from a dumprows file' in str(outp))
            # Make sure the output is valid
            with s_cortex.openurl(sqlite_url_new) as core:
                self.false(core.isnew)
                node = core.formTufoByProp('inet:ipv4', 0x01020304)
                self.true('.new' not in node[1])
                self.eq(core.getBlobValu('foo:bar'), ('tufo', {'test': 'value'}))

    def test_dumprows_load_compressed(self):
        self.thisHostMustNot(platform='darwin')
        outp = self.getTestOutp()
        with self.getTestDir() as temp:
            # Make a sqlite cortex and the associated dupmfile for it
            fp = os.path.join(temp, 'dumpfile.mpk')
            genrows_json_fp = os.path.join(temp, 'genrows.json')
            self.make_sql_genrows_json(genrows_json_fp)
            old_db = os.path.join(temp, 'old.db')
            new_db = os.path.join(temp, 'new.db')
            sqlite_url_old = 'sqlite:///{}'.format(old_db)
            sqlite_url_new = 'sqlite:///{}'.format(new_db)

            with s_cortex.openurl(sqlite_url_old) as core:
                self.true(core.isnew)
                node = core.formTufoByProp('inet:ipv4', 0x01020304)
                self.true('.new' in node[1])
                core.setBlobValu('foo:bar', ('tufo', {'test': 'value'}))

            # Dump that core and its blobstore to a dumpfile
            dump_argv = ['-s', sqlite_url_old, '-o', fp, '--dump-blobstore', '--compress', '-e', genrows_json_fp]
            ret = s_dumprows.main(dump_argv, self.getTestOutp())
            self.eq(ret, 0)

            # Execute loadrows tool to create the sqlite store and load the rows
            argv = ['-s', sqlite_url_new, '-i', fp]
            ret = s_loadrows.main(argv, outp)
            self.eq(ret, 0)
            self.true('Gzip row compression enabled' in str(outp))
            # Make sure the output is valid
            with s_cortex.openurl(sqlite_url_new) as core:
                self.false(core.isnew)
                node = core.formTufoByProp('inet:ipv4', 0x01020304)
                self.true('.new' not in node[1])
                self.eq(core.getBlobValu('foo:bar'), ('tufo', {'test': 'value'}))

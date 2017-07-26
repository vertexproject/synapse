# -*- coding: utf-8 -*-
# XXX Update Docstring
"""
synapse - test_tools_dumprows_loadrows.py
Created on 7/26/17.

Unittests for the dumprows and loadrows tools.
"""
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
        outp = self.getTestOutp()
        with self.getTestDir() as temp:
            fp = os.path.join(temp, 'savefile.msgpk')
            with s_cortex.openurl(fp, savefile=fp) as core:
                self.true(core.isnew)

    def test_simple_compress(self):
        outp = self.getTestOutp()

    def test_blob_dump(self):
        outp = self.getTestOutp()

    def test_revstore_use(self):
        outp = self.getTestOutp()


class LoadRowsTest(SynTest):

    def make_sql_genrows_json(self, fp):
        d = {'slicebytes': 2, 'incvalu': 4}
        with open(fp, 'wb') as f:
            f.write(json.dumps(d, indent=2, sort_keys=True).encode())

    def test_savefile_load(self):
        outp = self.getTestOutp()
        with self.getTestDir() as temp:
            # Prepare a savefile to load from a ram core
            fp = os.path.join(temp, 'savefile.msgpk')
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
        outp = self.getTestOutp()
        with self.getTestDir() as temp:
            # Make a sqlite cortex and the associated dupmfile for it
            fp = os.path.join(temp, 'dumpfile.msgpk')
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
        outp = self.getTestOutp()
        with self.getTestDir() as temp:
            # Make a sqlite cortex and the associated dupmfile for it
            fp = os.path.join(temp, 'dumpfile.msgpk')
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

'''
Unittests for cortex migration scripts.
'''
import zipfile
import argparse
# Synapse code
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath
from synapse.tests.common import *
# Test code
from scripts import migrate_add_tag_base

ASSETS_FP = getTestPath('assets')

class Migration_Base(SynTest):
    def get_dmon_config(self, fp):
        dconf = {
            'vars': {
                'cortex_url': 'sqlite:///{}'.format(fp)
            },
            'ctors': [
                [
                    'core',
                    'ctor://synapse.cortex.openurl(cortex_url)'
                ],
            ],
            'share': [
                [
                    'core',
                    {}
                ]
            ],
            'listen': [
                'tcp://127.0.0.1:36001'
            ]
        }
        return dconf

    def get_cortex_bytes(self, asset_fn):
        fp = os.path.join(ASSETS_FP, asset_fn)
        self.true(os.path.isfile(fp))
        with zipfile.ZipFile(fp) as zf:
            buf = zf.read('test.db')  # type: bytes
        return buf

    def get_cortex_fp(self, fdir, asset_fn):
        buf = self.get_cortex_bytes(asset_fn)
        fp = os.path.abspath(os.path.join(fdir, 'test.db'))
        with open(fp, 'wb') as f:
            f.write(buf)
        return fp

    @contextlib.contextmanager
    def get_dmon_core(self, asset_fn):
        with self.getTestDir() as fdir:
            core_fp = self.get_cortex_fp(fdir=fdir, asset_fn=asset_fn)
            dconf = self.get_dmon_config(fp=core_fp)
            with s_daemon.Daemon() as dmon:
                dmon.loadDmonConf(dconf)
                yield s_telepath.openurl(url='tcp://127.0.0.1:36001/core')

    @contextlib.contextmanager
    def get_file_core(self, asset_fn):
        with self.getTestDir() as fdir:
            core_fp = self.get_cortex_fp(fdir=fdir, asset_fn=asset_fn)
            c_url = 'sqlite:///{}'.format(core_fp)
            yield s_cortex.openurl(c_url)

class TagBaseMigration(Migration_Base):

    def test_migration_tagbase_core_nodes(self):
        with self.getTestDir() as fdir:
            core_fp = self.get_cortex_fp(fdir=fdir, asset_fn='test_tag_base.zip')
            self.true(os.path.isfile(core_fp))
            c_url = 'sqlite:///{}'.format(core_fp)
            core = s_cortex.openurl(c_url)
            nodes = migrate_add_tag_base.get_nodes_to_migrate(core)
            self.true(len(nodes) == 16)
            self.true(isinstance(nodes, list))

    def test_migration_tagbase_core_nodes_dmon(self):
        with self.getTestDir() as fdir:
            core_fp = self.get_cortex_fp(fdir=fdir, asset_fn='test_tag_base.zip')
            dconf = self.get_dmon_config(fp=core_fp)

            dmon = s_daemon.Daemon()
            dmon.loadDmonConf(dconf)

            core = s_telepath.openurl(url='tcp://127.0.0.1:36001/core')
            nodes = migrate_add_tag_base.get_nodes_to_migrate(core)
            self.true(len(nodes) == 16)
            self.true(isinstance(nodes, tuple))

            dmon.fini()

    def test_migration_tagbase_node_conversion(self):
        with self.get_file_core(asset_fn='test_tag_base.zip') as core:
            nodes = migrate_add_tag_base.get_nodes_to_migrate(core)
            self.eq(len(nodes), 16)
            migrate_add_tag_base.upgrade_tagbase_xact(core, nodes)
            nodes = migrate_add_tag_base.get_nodes_to_migrate(core)
            self.eq(len(nodes), 0)

    def test_migration_tagbase_node_conversion_dmon(self):
        with self.get_dmon_core(asset_fn='test_tag_base.zip') as core:
            nodes = migrate_add_tag_base.get_nodes_to_migrate(core)
            self.eq(len(nodes), 16)
            migrate_add_tag_base.upgrade_tagbase_no_xact(core, nodes)
            nodes = migrate_add_tag_base.get_nodes_to_migrate(core)
            self.eq(len(nodes), 0)

    def test_migration_tagbase_main(self):
        with self.getTestDir() as fdir:
            core_fp = self.get_cortex_fp(fdir=fdir, asset_fn='test_tag_base.zip')
            self.true(os.path.isfile(core_fp))

            core_url = 'sqlite:///{}'.format(core_fp)

            ns = argparse.Namespace(core=core_url, verbose=True)

            r = migrate_add_tag_base.main(options=ns)
            self.eq(r, 0)
            core = s_cortex.openurl(core_url)
            nodes = migrate_add_tag_base.get_nodes_to_migrate(core)
            self.true(len(nodes) == 0)
            nodes = core.eval('syn:tag')
            self.true(len(nodes) == 16)
            for node in nodes:
                self.eq(node[1].get('syn:tag:base'), node[1].get('syn:tag').split('.')[-1])

    def test_migration_tagbase_main_dmon(self):
        with self.getTestDir() as fdir:
            core_fp = self.get_cortex_fp(fdir=fdir, asset_fn='test_tag_base.zip')
            dconf = self.get_dmon_config(fp=core_fp)

            with s_daemon.Daemon() as dmon:
                dmon.loadDmonConf(dconf)

                ns = argparse.Namespace(core='tcp://127.0.0.1:36001/core', verbose=True)
                r = migrate_add_tag_base.main(options=ns)
                self.eq(r, 0)
                core = s_telepath.openurl(url='tcp://127.0.0.1:36001/core')
                nodes = migrate_add_tag_base.get_nodes_to_migrate(core)
                self.true(len(nodes) == 0)
                nodes = core.eval('syn:tag')
                self.true(len(nodes) == 16)
                for node in nodes:
                    self.eq(node[1].get('syn:tag:base'), node[1].get('syn:tag').split('.')[-1])
